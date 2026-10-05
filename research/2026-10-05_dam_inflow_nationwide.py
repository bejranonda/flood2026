"""Owner 2026-10-05: forecast "not only the water level … but also inflow, reservoir and much more parameters", nationwide.
Honest test for every RID dam with coordinates in our `dam` table: can catchment rain (ERA5 via Open-Meteo, keyless) +
yesterday's inflow forecast daily inflow better than persistence or HII's day-of-year average? Catchment = HydroBASINS lev08
basins upstream of the dam point (D-066); fit 2018-2024, test 2025-2026; recursive multi-step with observed rain = an upper
bound. Also the water-balance closure per dam. Read-only; nothing stored.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$PWD/data:/app/data:ro" worker python - < research/2026-10-05_dam_inflow_nationwide.py
     (ONLY="name|name" re-runs a subset; the first run's 21 failures were an unguarded None in HII's average_inflow)"""
import json, math, time, urllib.request
import numpy as np
from floodwatch import db

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"


def get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


g = json.load(open("data/basins/hydrobasins_lev08_th.geojson"))
feats = g["features"]


def inside(pt, geom):
    x, y = pt[1], pt[0]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        ring, c = poly[0], False
        for i in range(len(ring)):
            x1, y1 = ring[i - 1]; x2, y2 = ring[i]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
                c = not c
        if c:
            return True
    return False


def centroid(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    pts = [p for poly in polys for p in poly[0]]
    return (sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts))


def catchment(lat, lon):
    home = next((f for f in feats if inside((lat, lon), f["geometry"])), None)
    if not home:
        return None
    up, queue = [home], [home["properties"]["HYBAS_ID"]]
    while queue:
        cur = queue.pop()
        for f in feats:
            if f["properties"].get("NEXT_DOWN") == cur:
                up.append(f); queue.append(f["properties"]["HYBAS_ID"])
    up.sort(key=lambda f: -f["properties"].get("SUB_AREA", 0))
    return [(centroid(f["geometry"]), f["properties"]["SUB_AREA"]) for f in up[:3]], sum(f["properties"].get("SUB_AREA", 0) for f in up)


with db.connect_readonly() as c:
    dams = [dict(r) for r in c.execute("SELECT dam_id, name_th, lat, lon FROM dam WHERE agency='RID' ORDER BY dam_id").fetchall()]
import os
only = [x for x in os.environ.get("ONLY", "").split("|") if x]  # re-run a subset (names), appending to the log
if only:
    dams = [d for d in dams if d["name_th"] in only]
print(f"RID dams with coordinates: {len(dams)}" + (f" (subset of {len(only)})" if only else ""))
summary = []
for dam in dams:
    try:
        cat = catchment(dam["lat"], dam["lon"])
        if not cat:
            print(f"{dam['name_th']}: no HydroBASINS basin at the dam point"); continue
        pts, area = cat
        days, rain = None, None
        for (lat, lon), a in pts:
            d = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}&start_date=2018-01-01&end_date=2026-10-04&daily=precipitation_sum&timezone=Asia%2FBangkok")["daily"]
            if days is None:
                days, rain = d["time"], np.zeros(len(d["time"]))
            rain += np.nan_to_num(np.array([np.nan if v is None else v for v in d["precipitation_sum"]], float)) * a / sum(p[1] for p in pts)
            time.sleep(0.3)
        idx = {d: i for i, d in enumerate(days)}
        inflow, release, storage, clim = {}, {}, {}, {}
        for y in range(2018, 2027):
            for kind, store in (("dam_inflow", inflow), ("dam_released", release), ("dam_storage", storage)):
                dd = get(f"https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam_yearly_graph?data_type={kind}&dam_id={dam['dam_id']}&year={y}")["data"]
                for x in dd["graph_data"][0]["data"]:
                    if x.get("value") is not None:
                        store[x["date"][:10]] = float(x["value"])
                if kind == "dam_inflow":
                    for x in dd.get("average_inflow") or []:
                        if x.get("value") is not None and x.get("date"):
                            clim[x["date"][5:10]] = float(x["value"])
                time.sleep(0.25)
        all_days = [d for d in days if d in inflow]
        if len(all_days) < 1500:
            print(f"{dam['name_th']}: only {len(all_days)} inflow days"); continue
        D = np.array([inflow[d] for d in all_days]); R = np.array([rain[idx[d]] for d in all_days]); n = len(D)
        # water balance
        import datetime as _dt
        nxt = lambda d: (_dt.date.fromisoformat(d) + _dt.timedelta(days=1)).isoformat()
        wb = [(storage[nxt(d)] - storage[d], inflow[d] - release[d]) for d in all_days
              if nxt(d) in storage and d in release and d in storage]
        wb = np.array(wb) if wb else np.zeros((0, 2))
        wb_med = float(np.median(wb[:, 0] - wb[:, 1])) if len(wb) else float("nan")

        def feats_at(t, prev):
            return [1.0, prev, math.sqrt(max(prev, 0.0)), R[t], R[t - 1], R[t - 2], R[t - 3], R[t - 4:t - 7:-1].sum() if t >= 7 else 0.0]
        tr = [t for t in range(7, n) if int(all_days[t][:4]) <= 2024]
        te = [t for t in range(7, n) if int(all_days[t][:4]) >= 2025]
        X = np.array([feats_at(t, D[t - 1]) for t in tr]); beta, *_ = np.linalg.lstsq(X, D[tr], rcond=None)

        def fc(t0, h):
            prev = D[t0]
            for k in range(1, h + 1):
                prev = max(0.0, float(np.array(feats_at(t0 + k, prev)) @ beta))
            return prev
        res = {}
        for h in (1, 3, 7):
            a = np.array([(fc(t, h), D[t], D[t + h], clim.get(all_days[t + h][5:10], np.nan)) for t in te if t + h < n])
            res[h] = (np.abs(a[:, 0] - a[:, 2]).mean(), np.abs(a[:, 1] - a[:, 2]).mean(), np.nanmean(np.abs(a[:, 3] - a[:, 2])))
        gain = {h: 100 * (1 - res[h][0] / res[h][1]) for h in res}
        summary.append((dam["name_th"], area, D.mean(), gain, res, wb_med))
        print(f"{dam['name_th']:16s} catchment {area:6.0f} km² · mean inflow {D.mean():5.1f} · rain-model vs persistence: "
              f"1d {gain[1]:+4.0f} %  3d {gain[3]:+4.0f} %  7d {gain[7]:+4.0f} %  (MAE 7d: model {res[7][0]:.2f} · persist {res[7][1]:.2f} · clim {res[7][2]:.2f}) · balance gap {wb_med:+.2f}")
    except Exception as e:
        print(f"{dam['name_th']}: failed ({type(e).__name__}: {str(e)[:60]})")
print("\nSUMMARY: dams where the rain model beats persistence by ≥ 10 % at 3 days:",
      [s[0] for s in summary if s[3][3] >= 10], "| at 7 days:", [s[0] for s in summary if s[3][7] >= 10], f"| of {len(summary)} tested")
print("climatology beats persistence at 7 days for:", [s[0] for s in summary if s[4][7][2] < s[4][7][1]])
