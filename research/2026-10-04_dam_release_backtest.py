"""Do large-dam releases (beyond the Chao Phraya Dam) improve forecasts in other basins? (owner 2026-10-04: "consider
การปล่อยน้ำเขื่อน more than เจ้าพระยา, to improve the forecasting models in the other regions and basins").
Data: HII analyst/dam (50 large dams, sub_basin_id) + analyst/dam_yearly_graph?data_type=dam_released (daily MCM/day).
Test: gauges in the same HII sub-basin as a dam; the 45-day rolling backtest (forecast.evaluate) with the release as an
extra input (lagged one day, so the model never sees a release before it is reported) vs without.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$PWD/research:/out" worker python /out/2026-10-04_dam_release_backtest.py"""
import datetime as dt, json, time
import numpy as np, requests
from floodwatch import db, forecast as F
UA = {"User-Agent": "BKKFloodWatch/0.23 (+https://flood.autobahn.bot; open-source flood monitor)"}
B = "https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst"
dams = [d for d in requests.get(f"{B}/dam", headers=UA, timeout=60).json()["data"]["dam_daily"]]
rel = {}
for d in dams:
    did, ser = d["dam"]["id"], {}
    for y in (2025, 2026):
        try:
            g = requests.get(f"{B}/dam_yearly_graph", params={"data_type": "dam_released", "dam_id": did, "year": y}, headers=UA, timeout=60).json()
            for p in (g["data"]["graph_data"] or [{}])[0].get("data") or []:
                if p.get("value") is not None:
                    ser[p["date"][:10]] = float(p["value"])
        except Exception as e:
            print("dam", did, y, e)
        time.sleep(1.0)
    rel[did] = {"name": d["dam"]["dam_name"]["th"], "sub": d["dam"].get("sub_basin_id"), "series": ser}
print("dams with release history:", sum(1 for v in rel.values() if len(v["series"]) > 200), "of", len(rel))
out = []
with db.connect() as c:
    st = c.execute("SELECT code, lat, lon, in_focus, sub_basin FROM station WHERE sub_basin IS NOT NULL AND agency <> 'BMA'").fetchall()
    by_sub = {}
    for s in st:
        by_sub.setdefault(s["sub_basin"], []).append(s)
    cache = {}
    for did, d in rel.items():
        if len(d["series"]) < 200 or d["sub"] not in by_sub:
            continue
        for s in by_sub[d["sub"]][:4]:
            rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                                AND obs_time > now() - interval '370 days' ORDER BY obs_time""", (s["code"],)).fetchall()
            if len(rows) < 24 * 90:
                continue
            exo = F.load_exo(c, s["code"], s["lat"], s["lon"], cache, s["in_focus"])
            if not exo:
                continue
            t, y = F.hourly_grid([r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows])
            # the release of day D (Thai date) becomes known on day D+1: shift by one day
            r = np.array([d["series"].get((dt.datetime.fromtimestamp(h * 3600, dt.timezone.utc) + dt.timedelta(hours=7) - dt.timedelta(days=1)).strftime("%Y-%m-%d"), np.nan) for h in t])
            base = F.evaluate(t, y, F.align_exo(t, exo))
            exd = F.align_exo(t, exo); exd["extra"] = [r, F._lagdiff(r, 24), F._lagdiff(r, 72)]
            withd = F.evaluate(t, y, exd)
            res = {"code": s["code"], "dam": d["name"]}
            for h in (24, 48, 72):
                if h in base and h in withd:
                    res[h] = {"base": min(base[h]["rmse"].values()), "dam": min(withd[h]["rmse"].values()),
                              "persist": base[h]["rmse"]["persistence"], "chosen": withd[h]["method"]}
            out.append(res)
            print(s["code"], d["name"], {h: (round(v["base"] * 100, 1), round(v["dam"] * 100, 1)) for h, v in res.items() if isinstance(v, dict)}, flush=True)
json.dump(out, open("/out/2026-10-04_dam_release_backtest.json", "w"), ensure_ascii=False)
for h in (24, 48, 72):
    v = [(x[h]["base"], x[h]["dam"]) for x in out if h in x]
    if v:
        g = [(b - d) / b for b, d in v]
        print(f"+{h} h: {len(v)} gauges, error {100*np.mean(g):.1f}% lower on average (median {100*np.median(g):.1f}%), "
              f">5% better at {sum(x > 0.05 for x in g)}, worse at {sum(x < -0.01 for x in g)}")
