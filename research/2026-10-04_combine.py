"""Step 2 of Q52 (owner 2026-10-04: "reduce the uncertainty of prediction"): does averaging the candidate forecasts beat
picking one? Honest split: the backtest window is cut in two halves by time; the method (and the 10 % gate) is chosen on
the first half (A) and scored on the second (B). Pipelines: today's (pick the best single method), and today's plus
fixed combinations: avg_all (mean of every non-persistence method), avg_best2 (mean of the 2 best on A), and
avg_all_p (all methods including persistence). Averaging forecasts = averaging their errors on the same hours.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - 200 < research/2026-10-04_combine.py"""
import collections as C, random, sys
import numpy as np
from floodwatch import db, forecast as F
random.seed(11)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
rmse = lambda v: float(np.sqrt(np.mean(np.square(v))))
tot = {h: C.defaultdict(C.Counter) for h in F.HORIZONS}
with db.connect() as c:
    codes = [r["code"] for r in c.execute("""SELECT DISTINCT code FROM forecast_run WHERE issue_time > now() - interval '3 hours'""")]
    sample = random.sample(codes, min(N, len(codes)))
    meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus FROM station WHERE code = ANY(%s)", (sample,)).fetchall()}
    cache, done = {}, 0
    for code in sample:
        m = meta.get(code)
        rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                            AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (code, F.LOOKBACK_DAYS)).fetchall()
        if not m or len(rows) < 24 * 30:
            continue
        t, y = F.hourly_grid([r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows])
        exo = F.load_exo(c, code, m["lat"], m["lon"], cache, m["in_focus"])
        errs, _ = F._backtest_errors(t, y, F.align_exo(t, exo) if exo else None)
        done += 1
        for h in F.HORIZONS:
            rws = F.common_rows(errs[h])
            if len(rws) < 60:
                continue
            e = {k: np.array([v[i] for i in rws]) for k, v in errs[h].items()}
            half = len(rws) // 2
            A = {k: v[:half] for k, v in e.items()}; B = {k: v[half:] for k, v in e.items()}
            cand = [k for k in e if k != "persistence"]
            best2 = sorted(cand, key=lambda k: rmse(A[k]))[:2]
            combos = {"avg_all": cand, "avg_best2": best2, "avg_all_p": list(e)}
            for k, ms in combos.items():
                if len(ms) >= 2:
                    A[k] = np.mean([A[x] for x in ms], axis=0); B[k] = np.mean([B[x] for x in ms], axis=0)
            pipes = {"today": cand, "+avg_all": cand + ["avg_all"], "+avg_best2": cand + ["avg_best2"],
                     "+avg_all_p": cand + ["avg_all_p"], "+all combos": cand + list(combos)}
            pB = rmse(B["persistence"])
            for name, ms in pipes.items():
                ms = [x for x in ms if x in A]
                best = min(ms, key=lambda x: rmse(A[x])) if ms else "persistence"
                chosen = best if rmse(A[best]) < (1 - F.SKILL_GATE) * rmse(A["persistence"]) else "persistence"
                s = tot[h][name]
                s["n"] += 1; s["sumB"] += rmse(B[chosen]); s["sumP"] += pB
                s["model"] += chosen != "persistence"
                s["won_B"] += chosen != "persistence" and rmse(B[chosen]) < (1 - F.SKILL_GATE) * pB
                s["worse_B"] += chosen != "persistence" and rmse(B[chosen]) > pB
                s["combo"] += chosen.startswith("avg")
        if done % 25 == 0: print("…", done, flush=True)
print("gauges", done)
for h in F.HORIZONS:
    print(f"\n=== +{h} h (choose on first half, score on second)")
    for name, s in tot[h].items():
        n = s["n"]
        print(f"{name:12s} n {n:4d} · error vs 'no change' {100*(s['sumB']/s['sumP']-1):+5.1f}% · served a model {s['model']:4d}"
              f" (a combination {s['combo']:4d}) · held ≥10 % gain on B {s['won_B']:4d} · worse than no change on B {s['worse_B']:3d}")
