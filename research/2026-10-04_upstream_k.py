"""Q52 experiment E1/E2: more learned upstream gauges for star (Q47) and a shorter history requirement for learning them.
Gauges outside the focus area and off the Chao Phraya chain (learned upstream, forecast/upstream.py: K = 2, ≥ 180 days of
pairs, same basin, 24 h change leads by 1–48 h, r ≥ 0.5). Upstream lists are re-learned here on hours before each
gauge's backtest window only (no leakage), then star is scored with the honest protocol (q52_harness).
Variants: K2/180 d (today's rule), K3/180 d, K4/180 d, K2/90 d, K4/90 d.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker python - 150 1 < research/2026-10-04_upstream_k.py"""
import sys
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F
from floodwatch.forecast import upstream as U

N, K = int(sys.argv[1]), int(sys.argv[2])
VARIANTS = {"K2/180d (today)": (2, 180), "K3/180d": (3, 180), "K4/180d": (4, 180), "K2/90d": (2, 90), "K4/90d": (4, 90)}
sc = H.Score()
with db.connect_readonly() as c:
    chain = F._chainage()
    codes = [x for x in H.sample_codes(c, N * 3, K, "NOT s.in_focus AND s.agency IS DISTINCT FROM 'BMA'") if x not in chain][:N]
    meta = {r["code"]: r for r in c.execute("""SELECT code, COALESCE(basin22, basin) AS basin, lat, lon, in_focus, river_system
                                              FROM station WHERE code !~ '^TEST' AND agency IS DISTINCT FROM 'BMA'
                                              AND lat IS NOT NULL""").fetchall()}
    basin_series, cache, done = {}, {}, 0
    for code in codes:
        m = meta.get(code)
        if not m or not m["basin"]:
            continue
        t, y = H.load_series(c, code)
        if len(y) < 24 * 60:
            continue
        exo = F.load_exo(c, code, m["lat"], m["lon"], cache, m["in_focus"])
        if not exo:
            continue
        b = m["basin"]
        if b not in basin_series:
            raw = {g: H.load_raw(c, g) for g, mm in meta.items() if mm["basin"] == b}
            basin_series = {b: (raw, {g: F.hourly_grid(*v) for g, v in raw.items() if v[0]})}  # one basin in memory
        raw, series = basin_series[b]
        bmeta = {g: {"basin": b, "lat": meta[g]["lat"], "lon": meta[g]["lon"], "system": meta[g]["river_system"]} for g in series}
        own, split = F._backtest_errors(t, y, None)
        cutoff = int(t[split])
        done += 1
        for name, (k, days) in VARIANTS.items():
            U.K, U.MIN_PAIRS = k, days * 24
            ups = (U.learn(series, bmeta, cutoff, {code}).get(code) or [])
            ex = F.align_exo(t, {**exo, "up": [raw[u[0]] for u in ups]})
            sc.add(name, own, H.star_errs(t, y, ex, own, split))
            sc.tot[name][0]["ups"] += len(ups)
        if done % 20 == 0:
            print("…", done, flush=True)
print(f"sample {K}: gauges {done}; upstream gauges used per variant:", {v: sc.tot[v][0]["ups"] for v in VARIANTS})
print(sc.report())
