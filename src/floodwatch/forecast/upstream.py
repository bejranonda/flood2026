"""Upstream gauges learned from the data (D-064), for gauges off the Chao Phraya chain.

Bangkok's `star` model reads the two nearest gauges up the Chao Phraya by river km. Outside it there is no national
river network in the app, so each gauge gets up to K gauges from its own HII basin, within MAX_KM, whose 24 h change
best *leads* its own 24 h change (lag 1-48 h). Rules:
- learned only on hours before the backtest window (cutoff), so the backtest never sees what chose its inputs;
- a gauge whose best lag is 0 (the same place, e.g. another agency's gauge beside it) is not upstream;
- only changes are compared, so a datum offset between agencies cancels; levels are never mixed (KI-217).
"""
from __future__ import annotations

import datetime as dt
import logging
import math

import numpy as np

log = logging.getLogger(__name__)

K = 2
MAX_KM = 250.0
MAX_LAG = 48
MIN_R = 0.5
MIN_PAIRS = 180 * 24  # ~180 days of hourly pairs


def _d24(x: np.ndarray) -> np.ndarray:
    o = np.full(len(x), np.nan)
    o[24:] = x[24:] - x[:-24]
    return o


def score(target: np.ndarray, cand: np.ndarray, max_lag: int = MAX_LAG) -> tuple[int, float]:
    """Best (lag hours, correlation) of the candidate's 24 h change `lag` hours earlier against the target's
    24 h change, lags 0..max_lag, for two series on the same hourly grid. (0, -1.0) when too few pairs."""
    a, b = _d24(np.asarray(target, float)), _d24(np.asarray(cand, float))
    best = (0, -1.0)
    for lag in range(0, max_lag + 1):
        x, y = (b[: len(b) - lag], a[lag:]) if lag else (b, a)
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < MIN_PAIRS or np.std(x[m]) == 0 or np.std(y[m]) == 0:
            continue
        r = float(np.corrcoef(x[m], y[m])[0, 1])
        if r > best[1]:
            best = (lag, r)
    return best


def _km(a: dict, b: dict) -> float:
    p = math.pi / 180
    h = (math.sin((b["lat"] - a["lat"]) * p / 2) ** 2
         + math.cos(a["lat"] * p) * math.cos(b["lat"] * p) * math.sin((b["lon"] - a["lon"]) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


def _window(t: np.ndarray, y: np.ndarray, lo: int, hi: int) -> np.ndarray:
    out = np.full(hi - lo, np.nan)
    idx = t.astype(int) - lo
    ok = (idx >= 0) & (idx < hi - lo)
    out[idx[ok]] = y[ok]
    return out


def learn(series: dict[str, tuple[np.ndarray, np.ndarray]], meta: dict[str, dict], cutoff_h: int,
          targets: set[str] | None = None) -> dict[str, list[list]]:
    """{target: [[upstream code, lag h, r], ...]} (best first, at most K) from hourly series (absolute hours, values).
    Only hours before `cutoff_h` are used. Targets without a qualifying gauge are left out."""
    out: dict[str, list[list]] = {}
    for code in sorted(targets if targets is not None else series):
        m = meta.get(code) or {}
        if code not in series or not m.get("basin") or m.get("lat") is None:
            continue
        t0, y0 = series[code]
        picks = []
        for cand, (t1, y1) in series.items():
            n = meta.get(cand) or {}
            if cand == code or n.get("basin") != m["basin"] or n.get("lat") is None or _km(m, n) > MAX_KM:
                continue
            lo = int(max(t0[0], t1[0])) if len(t0) and len(t1) else cutoff_h
            if cutoff_h - lo < MIN_PAIRS:
                continue
            lag, r = score(_window(t0, y0, lo, cutoff_h), _window(t1, y1, lo, cutoff_h))
            if lag >= 1 and r >= MIN_R:
                picks.append([cand, lag, round(r, 3)])
        if picks:
            out[code] = sorted(picks, key=lambda p: -p[2])[:K]
    return out


def run_all() -> int:
    """Daily: learn upstream gauges for every gauge outside the focus area, basin by basin (bounded memory),
    and store them in collector_state 'upstream_learned'."""
    from floodwatch import db
    from floodwatch.forecast import EVAL_HOURS, LOOKBACK_DAYS, hourly_grid
    cutoff_h = int(dt.datetime.now(dt.timezone.utc).timestamp() // 3600) - EVAL_HOURS
    with db.connect() as c:
        rows = c.execute("""SELECT code, basin, lat, lon, in_focus FROM station WHERE code !~ '^TEST'
                            AND agency IS DISTINCT FROM 'BMA' AND basin IS NOT NULL AND lat IS NOT NULL""").fetchall()
    by_basin: dict[str, list[dict]] = {}
    for r in rows:
        by_basin.setdefault(r["basin"], []).append(r)
    learned: dict[str, list[list]] = {}
    for basin, gauges in by_basin.items():
        targets = {g["code"] for g in gauges if not g["in_focus"]}
        if len(gauges) < 2 or not targets:
            continue
        series = {}
        with db.connect() as c:
            for g in gauges:
                obs = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                                   AND level_msl IS NOT NULL AND obs_time > now() - make_interval(days => %s)
                                   ORDER BY obs_time""", (g["code"], LOOKBACK_DAYS)).fetchall()
                t, y = hourly_grid([o["obs_time"] for o in obs], [o["level_msl"] for o in obs])
                if len(t):
                    series[g["code"]] = (t, y)
        meta = {g["code"]: {"basin": basin, "lat": g["lat"], "lon": g["lon"]} for g in gauges}
        learned.update(learn(series, meta, cutoff_h, targets))
    with db.connect() as c:
        db.set_state(c, "upstream_learned", learned)
        c.commit()
    log.info("upstream_learn: %d gauges got upstream inputs", len(learned))
    return len(learned)
