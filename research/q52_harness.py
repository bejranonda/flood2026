"""Shared harness for the Q52 forecast experiments (owner 2026-10-04: "improve the model forecasting performance … not fake
the result and error or uncertainty"). The honest protocol of research/2026-10-04_star_variants.py, reusable:

- the gauge's own methods come from forecast._backtest_errors (rolling origin over the backtest window);
- a star variant is trained only on hours before the window and tested on the window;
- the served method (best + the 10 % gate) is chosen on the first half of the window (A) and scored on the second (B);
- variants are picked on gauge sample 1 and confirmed on the disjoint sample 2 (same seed for every experiment).

Mount it read-only and import it from a research script:
  docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
      -v "$PWD/research:/research:ro" worker python - ARGS < research/<experiment>.py
"""
from __future__ import annotations

import collections as C
import random

import numpy as np

from floodwatch import forecast as F

rmse = lambda v: float(np.sqrt(np.mean(np.square(v))))


def sample_codes(c, n: int, k: int, where: str = "TRUE") -> list[str]:
    """Disjoint sample k (1, 2, …) of n gauges with a fresh forecast run; `where` filters on station columns."""
    codes = sorted(r["code"] for r in c.execute(
        f"""SELECT DISTINCT f.code FROM forecast_run f JOIN station s USING (code)
            WHERE f.issue_time > now() - interval '3 hours' AND ({where})"""))
    random.Random(23).shuffle(codes)
    return codes[(k - 1) * n: k * n]


def load_raw(c, code: str, days: int = F.LOOKBACK_DAYS) -> tuple[list, list]:
    """(datetimes, levels) as load_exo reads them."""
    rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                        AND level_msl IS NOT NULL AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""",
                     (code, days)).fetchall()
    return [r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows]


def load_series(c, code: str, days: int = F.LOOKBACK_DAYS) -> tuple[np.ndarray, np.ndarray]:
    return F.hourly_grid(*load_raw(c, code, days))


def ridge(X: np.ndarray, y: np.ndarray):
    return F._ridge(X, y)


def star_errs(t, y, ex, own, split, feats=None, fit=ridge) -> dict:
    """{h: {issue hour: error}} for a star variant. `feats(t, yf, eta, ybf, h, ex)` builds the feature rows
    (default: the production forecast.star_features)."""
    feats = feats or F.star_features
    eta = F.fit_tide(t[:split], y[:split])
    yf = F._ffill(y, F.OWN_FFILL_H)
    ybf = F.trailing_mean(yf, 25)
    out = {}
    for h in F.HORIZONS:
        X, tg = feats(t, yf, eta, ybf, h, ex), F._star_target(y, h)
        ok = np.isfinite(X).all(1) & np.isfinite(tg)
        idx = np.arange(len(y))
        tr = ok & (idx < split - h)
        te = [i for i in range(split, len(y)) if ok[i] and i in own[h]["persistence"]]
        if tr.sum() < F.STAR_MIN_TRAIN or len(te) < 0.5 * len(own[h]["persistence"]):
            continue
        f = fit(X[tr], tg[tr])
        out[h] = {i: float(tg[i] - p) for i, p in zip(te, f(X[te]))}
    return out


class Score:
    """Per variant and horizon: the served (gated) method chosen on A, scored on B."""

    def __init__(self):
        self.tot = C.defaultdict(lambda: C.defaultdict(C.Counter))
        self.ratio = C.defaultdict(lambda: C.defaultdict(list))

    def add(self, variant: str, own: dict, star: dict, require_star: bool = False) -> None:
        for h in F.HORIZONS:
            errs = {**own[h], **({"star": star[h]} if h in star else {})}
            if require_star and "star" not in errs:
                continue
            rws = F.common_rows(errs)
            if len(rws) < 60:
                continue
            e = {k: np.array([v[i] for i in rws]) for k, v in errs.items()}
            half = len(rws) // 2
            A = {k: x[:half] for k, x in e.items()}
            B = {k: x[half:] for k, x in e.items()}
            cand = [k for k in e if k != "persistence"]
            best = min(cand, key=lambda x: rmse(A[x])) if cand else "persistence"
            chosen = best if rmse(A[best]) < (1 - F.SKILL_GATE) * rmse(A["persistence"]) else "persistence"
            pB = rmse(B["persistence"])
            s = self.tot[variant][h]
            s["n"] += 1
            s["sumB"] += rmse(B[chosen])
            s["sumP"] += pB
            s["model"] += chosen != "persistence"
            s["star"] += chosen == "star"
            s["held"] += chosen != "persistence" and rmse(B[chosen]) < (1 - F.SKILL_GATE) * pB
            s["worse"] += chosen != "persistence" and rmse(B[chosen]) > pB
            self.ratio[variant][h].append(rmse(B[chosen]) / pB if pB > 0 else 1.0)

    def report(self, horizons=(6, 12, 24, 48, 72)) -> str:
        lines = []
        for h in horizons:
            lines.append(f"\n=== +{h} h (chosen on the first half, scored on the second)")
            for v, per in self.tot.items():
                s = per[h]
                if not s["n"]:
                    continue
                lines.append(f"{v:22s} n {s['n']:4d} · error vs no-change {100 * (s['sumB'] / max(s['sumP'], 1e-12) - 1):+5.1f}% "
                             f"(per-gauge mean {100 * (np.mean(self.ratio[v][h]) - 1):+5.1f}%) · served a model {s['model']:4d} "
                             f"(star {s['star']:4d}) · held ≥10 % {s['held']:4d} · worse {s['worse']:3d}")
        return "\n".join(lines)
