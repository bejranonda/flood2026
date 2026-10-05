"""Q52 experiment E-Q (owner 2026-10-05: "not only the water level … but also inflow, reservoir and much more"): discharge
(flow, m³/s) forecasts for the RID gauges that measure it — the same ladder (persistence / tide / trend / recent / star)
on log(1 + Q), honest protocol (train before the window, choose on the first half, score on the second), two disjoint
samples. Exogenous inputs as in production (upstream levels, rain, Flood Hub). The error is in log units ≈ relative error.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker python - < research/2026-10-05_discharge_forecast.py"""
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F

WHERE = """s.agency='RID' AND s.lat IS NOT NULL AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code AND o.discharge IS NOT NULL
           AND o.discharge > 0 AND o.obs_time > now() - interval '12 hours')"""


def load_q(c, code):
    rows = c.execute("""SELECT obs_time, discharge FROM observation WHERE code=%s AND quality_flag='ok' AND discharge IS NOT NULL
                        AND discharge >= 0 AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (code, F.LOOKBACK_DAYS)).fetchall()
    return F.hourly_grid([r["obs_time"] for r in rows], [float(np.log1p(r["discharge"])) for r in rows])


with db.connect_readonly() as c:
    for k in (1, 2):
        sc = H.Score()
        codes = H.sample_codes(c, 100, k, where=WHERE)
        meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus, agency FROM station WHERE code = ANY(%s)", (codes,)).fetchall()}
        cache, done, rel = {}, 0, []
        for code in codes:
            s = meta.get(code)
            if not s:
                continue
            t, yq = load_q(c, code)
            if len(yq) < 24 * 60 or np.isfinite(yq).sum() < 24 * 60:
                continue
            exo = F.load_exo(c, code, s["lat"], s["lon"], cache, s["in_focus"], s["agency"])
            if not exo:
                continue
            ex = F.align_exo(t, exo)
            own, split = F._backtest_errors(t, yq, None)
            sc.add("flow ladder (log Q)", own, H.star_errs(t, yq, ex, own, split))
            p24 = own.get(24, {}).get("persistence")
            if p24:
                rel.append(float(np.sqrt(np.mean(np.square(list(p24.values()))))))
            done += 1
            if done % 20 == 0:
                print("…", done, flush=True)
        print(f"\n=== sample {k}: {done} RID gauges with discharge · persistence 24 h RMSE in log Q: median {np.median(rel):.3f}"
              f" (≈ {100 * (np.exp(np.median(rel)) - 1):.0f} % of the flow)")
        print(sc.report(horizons=(12, 24, 48, 72)))
