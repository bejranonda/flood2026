"""E-SAME — the old and the new `star` on the same days, at the gauges every model generation forecast (owner 2026-10-06:
"Continue all the rest to finish"; HANDOFF next step 1). As issued, star-0.4 was level with "no change" on these gauges
in its first day and a half (MODELS §12b) while older generations gained 2–7 % in their own weeks — different weeks,
so that could be the recession rather than the model. Here both run on the same days.

Read-only (`db.connect_readonly()`, D-096). Gauges: those with forecast runs from all four generations (mvp-0.1, star-0.2,
star-0.3, star-0.4). Per gauge, the honest protocol of MODELS §5d: the gauge's own methods from the rolling backtest;
`star` trained only on hours before the 45-day window; the served method (best + the 10 % gate) chosen on the window's
first half (A) and scored on the second (B). Two `star` versions, identical but for the inputs v0.25.0 added (D-092):
  old = without the 7/30-day means and the 1/3/72 h changes (star_features columns 4–8 dropped)
  new = as served today.
Scored on all of B and on its last 7 days (the recession). Per horizon: the served pipeline's error vs "no change", the
gauges whose new pipeline is worse — and better — than the old one beyond chance (`model_gate.made_worse`, blocks of the
horizon, D-107).
Sample 2 (`others`, added after sample 1 showed a 12 h exception — new inputs worse beyond chance at 9 gauges, better at
3): 300 other gauges with live runs, drawn at random (seed 23), as the confirmation sample (MODELS §5d).
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice python - [others] \
       < research/2026-10-06_star_same_days.py"""
import collections as C
import json
import random
import sys

import numpy as np

from floodwatch import db, forecast as F, model_gate

NEW_COLS = [4, 5, 6, 7, 8]  # y − 7-day mean, y − 30-day mean, 1/3/72 h changes (D-092)
LAST_H = 7 * 24
SAMPLE = sys.argv[1] if len(sys.argv) > 1 else "all4"
rmse = lambda v: float(np.sqrt(np.mean(np.square(v)))) if len(v) else float("nan")


def star_errs(t, y, ex, errs, split, old):
    eta = F.fit_tide(t[:split], y[:split])
    yf = F._ffill(y, F.OWN_FFILL_H)
    ybf = F.trailing_mean(yf, 25)
    out = {}
    for h in F.HORIZONS:
        X, tg = F.star_features(t, yf, eta, ybf, h, ex), F._star_target(y, h)
        if old:
            X = np.delete(X, NEW_COLS, axis=1)
        ok = np.isfinite(X).all(1) & np.isfinite(tg)
        idx = np.arange(len(y))
        tr = ok & (idx < split - h)
        te = [i for i in range(split, len(y)) if ok[i] and i in errs[h]["persistence"]]
        if tr.sum() < F.STAR_MIN_TRAIN or len(te) < 0.5 * len(errs[h]["persistence"]):
            continue
        f = F._ridge(X[tr], tg[tr])
        out[h] = {i: float(tg[i] - p) for i, p in zip(te, f(X[te]))}
    return out


def served(own_h, st_h):
    """The pipeline: errors of the method chosen on A (best + the 10 % gate), on the rows of B; and its name."""
    errs = {**own_h, **({"star": st_h} if st_h else {})}
    rws = F.common_rows(errs)
    if len(rws) < 60:
        return None
    half = len(rws) // 2
    A = {k: np.array([v[i] for i in rws[:half]]) for k, v in errs.items()}
    cand = [k for k in errs if k != "persistence"]
    best = min(cand, key=lambda k: rmse(A[k])) if cand else "persistence"
    chosen = best if rmse(A[best]) < (1 - F.SKILL_GATE) * rmse(A["persistence"]) else "persistence"
    rb = rws[half:]
    return chosen, rb, np.array([errs[chosen][i] for i in rb]), np.array([errs["persistence"][i] for i in rb])


acc = {(v, h, part): C.defaultdict(float) for v in ("old", "new") for h in F.HORIZONS for part in ("B", "last7")}
pairs = C.defaultdict(lambda: C.Counter())
with db.connect_readonly() as c:
    c.execute("SET statement_timeout = '120s'")
    all4 = sorted(r["code"] for r in c.execute(
        "SELECT code FROM forecast_run GROUP BY code HAVING count(DISTINCT version) = 4").fetchall())
    if SAMPLE == "others":
        live = sorted(r["code"] for r in c.execute(
            "SELECT DISTINCT code FROM forecast_run WHERE issue_time > now() - interval '3 hours'").fetchall())
        codes = [x for x in live if x not in set(all4)]
        random.Random(23).shuffle(codes)
        codes = sorted(codes[:300])
    else:
        codes = all4
    meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus FROM station WHERE code = ANY(%s)",
                                            (codes,)).fetchall()}
    print(f"sample {SAMPLE}: {len(codes)} gauges", flush=True)
    cache, done = {}, 0
    for code in codes:
        m = meta.get(code)
        rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                            AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""",
                         (code, F.LOOKBACK_DAYS)).fetchall()
        if not m or len(rows) < 24 * 30:
            continue
        t, y = F.hourly_grid([r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows])
        exo = F.load_exo(c, code, m["lat"], m["lon"], cache, m["in_focus"])
        ex = F.align_exo(t, exo) if exo else None
        if ex is None:
            continue
        own, split = F._backtest_errors(t, y, None)
        st = {"old": star_errs(t, y, ex, own, split, True), "new": star_errs(t, y, ex, own, split, False)}
        done += 1
        for h in F.HORIZONS:
            res = {v: served(own[h], st[v].get(h)) for v in ("old", "new")}
            if not all(res.values()):
                continue
            for v, (chosen, rb, e, p) in res.items():
                last = np.array([i >= len(y) - LAST_H for i in rb])
                for part, sel in (("B", np.ones(len(rb), bool)), ("last7", last)):
                    if sel.sum() < 24:
                        continue
                    a = acc[(v, h, part)]
                    a["n"] += 1
                    a["model"] += chosen != "persistence"
                    a["sum_e"] += rmse(e[sel])
                    a["sum_p"] += rmse(p[sel])
            (_, rb, e_old, _), (_, rb2, e_new, _) = res["old"], res["new"]
            if rb == rb2:
                worse = model_gate.made_worse(e_new, e_old, block=h, metric="rmse")
                better = model_gate.made_worse(e_old, e_new, block=h, metric="rmse")
                pairs[h]["n"] += 1
                pairs[h]["worse"] += worse["worse"]
                pairs[h]["better"] += better["worse"]
                pairs[h]["same_method"] += res["old"][0] == res["new"][0] and res["old"][0] != "star"
        if done % 25 == 0:
            print("…", done, flush=True)

print(f"gauges scored: {done}")
out = {}
for part in ("B", "last7"):
    print(f"\n=== {'second half of the 45-day window (B)' if part == 'B' else 'the last 7 days of B (the recession)'}: "
          "served pipeline, error vs \"no change\" (summed RMSE)")
    for h in F.HORIZONS:
        line = [f"+{h:2d} h"]
        for v in ("old", "new"):
            a = acc[(v, h, part)]
            if not a["n"]:
                continue
            r = (a["sum_e"] / a["sum_p"] - 1) * 100
            out[f"{part}|{v}|{h}"] = {"n": int(a["n"]), "vs_no_change_pct": round(r, 1),
                                      "model_served": int(a["model"])}
            line.append(f"{v}: {r:+5.1f} % (n {int(a['n'])}, model {int(a['model'])})")
        print("  ".join(line))
print("\n=== new vs old on B, gauge by gauge, beyond chance (> 3 % and a block bootstrap, D-107)")
for h in F.HORIZONS:
    s = pairs[h]
    out[f"pairs|{h}"] = dict(s)
    print(f"+{h:2d} h  gauges {s['n']:4d} · new worse {s['worse']:3d} · new better {s['better']:3d} · "
          f"same non-star method {s['same_method']:3d}")
print("SUMMARY_JSON", json.dumps(out))
