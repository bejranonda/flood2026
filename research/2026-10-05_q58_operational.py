"""Q58, operational test (owner 2026-10-05: "continue testing"): can a rain-driven model forecast the big reservoirs' daily
inflow 1–7 days ahead with the rain *forecasts* available at the time — not the observed rain the first test used?
- Dams: the 16 RID dams whose rain model beat persistence ≥ 10 % at 7 days with observed ERA5 rain (research
  2026-10-05_dam_inflow_nationwide.log), plus Kaeng Krachan as the control;
- fit (ERA5 rain, 2018–2024) as before; forecast rain = Open-Meteo "previous runs" (the forecast for day D issued N days
  before, N = 1…7), 92 days 2026-07-06…10-06 at the same catchment points; a multiplicative lead-bias correction learned
  on the first 46 days (lead-N total vs lead-0 total), applied to the last 46 days — the scored period;
- scored against persistence (hold today's inflow) and the observed-rain upper bound on the same days;
- loss term: the water-balance residual Δstorage − (inflow − release) by calendar month (2018–2026 median) per dam; the
  7-day storage outlook error with and without it, on 2025–2026 days, inflow held (what the scenarios do).
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$PWD/data:/app/data:ro" worker python - < research/2026-10-05_q58_operational.py"""
import datetime as dt, json, math, time, urllib.request
import numpy as np
from floodwatch import db

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"
PASSED = ["ภูมิพล", "อุบลรัตน์", "สิรินธร", "สิริกิติ์", "ศรีนครินทร์", "วชิราลงกรณ", "แม่งัดสมบูรณ์ชล", "รัชชประภา", "ห้วยหลวง", "ลำนางรอง",
          "ขุนด่านปราการชล", "กิ่วคอหมา", "แควน้อยบำรุงแดน", "แม่กวงอุดมธารา", "ลำปาว", "น้ำอูน", "แก่งกระจาน"]


def get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
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
    return [(centroid(f["geometry"]), f["properties"]["SUB_AREA"]) for f in up[:3]]


with db.connect_readonly() as c:
    dams = [dict(r) for r in c.execute("SELECT dam_id, name_th, lat, lon FROM dam WHERE agency='RID' AND name_th = ANY(%s) ORDER BY dam_id", (PASSED,)).fetchall()]
print(f"dams: {len(dams)}")
LEADS = list(range(1, 8))
results, build = [], {}
for dam in dams:
    try:
        pts = catchment(dam["lat"], dam["lon"])
        if not pts:
            print(f"{dam['name_th']}: no basin"); continue
        wsum = sum(p[1] for p in pts)
        # ERA5 (fit) and previous-runs (test) rain, area-weighted
        days, rain = None, None
        fdays, fc = None, {n: None for n in [0] + LEADS}
        for (lat, lon), a in pts:
            d = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}&start_date=2018-01-01&end_date=2026-10-05&daily=precipitation_sum&timezone=Asia%2FBangkok")["daily"]
            if days is None:
                days, rain = d["time"], np.zeros(len(d["time"]))
            rain += np.nan_to_num(np.array([np.nan if v is None else v for v in d["precipitation_sum"]], float)) * a / wsum
            time.sleep(0.3)
            hv = ",".join(["precipitation"] + [f"precipitation_previous_day{n}" for n in LEADS])
            h = get(f"https://previous-runs-api.open-meteo.com/v1/forecast?latitude={lat:.3f}&longitude={lon:.3f}&hourly={hv}&past_days=92&forecast_days=1&timezone=Asia%2FBangkok")["hourly"]
            dd = sorted({t[:10] for t in h["time"]})
            if fdays is None:
                fdays = dd
                fc = {n: np.zeros(len(dd)) for n in [0] + LEADS}
            idx = {d_: i for i, d_ in enumerate(dd)}
            for n in [0] + LEADS:
                key = "precipitation" if n == 0 else f"precipitation_previous_day{n}"
                for t, v in zip(h["time"], h[key]):
                    if v is not None:
                        fc[n][idx[t[:10]]] += v * a / wsum
            time.sleep(0.3)
        inflow, release, storage = {}, {}, {}
        for y in range(2018, 2027):
            for kind, store in (("dam_inflow", inflow), ("dam_released", release), ("dam_storage", storage)):
                dd_ = get(f"https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam_yearly_graph?data_type={kind}&dam_id={dam['dam_id']}&year={y}")["data"]
                for x in dd_["graph_data"][0]["data"]:
                    if x.get("value") is not None:
                        store[x["date"][:10]] = float(x["value"])
                time.sleep(0.2)
        all_days = [d_ for d_ in days if d_ in inflow]
        D = np.array([inflow[d_] for d_ in all_days]); R = np.array([rain[days.index(d_)] for d_ in all_days]) if False else None
        di = {d_: i for i, d_ in enumerate(days)}
        R = np.array([rain[di[d_]] for d_ in all_days]); n = len(D)
        pos = {d_: i for i, d_ in enumerate(all_days)}

        def feats_at(t, prev, rr):
            return [1.0, prev, math.sqrt(max(prev, 0.0)), rr[t], rr[t - 1], rr[t - 2], rr[t - 3], rr[t - 4:t - 7:-1].sum() if t >= 7 else 0.0]
        tr = [t for t in range(7, n) if int(all_days[t][:4]) <= 2024]
        X = np.array([feats_at(t, D[t - 1], R) for t in tr]); beta, *_ = np.linalg.lstsq(X, D[tr], rcond=None)
        # operational period: the 92 forecast days that have inflow; bias correction from the first half
        fd = [d_ for d_ in fdays if d_ in pos and pos[d_] + 7 < n and pos[d_] >= 7]
        half = len(fd) // 2
        fidx = {d_: i for i, d_ in enumerate(fdays)}
        corr = {}
        for lead in LEADS:
            a = sum(fc[lead][fidx[d_]] for d_ in fd[:half]); b = sum(fc[0][fidx[d_]] for d_ in fd[:half])
            corr[lead] = (b / a) if a > 0 else 1.0

        def fc_inflow(t0, h, rain_fn):
            prev = D[t0]
            for k in range(1, h + 1):
                rr = np.array([rain_fn(t0 + k - j, k - j) if (t0 + k - j) > t0 else R[t0 + k - j] for j in range(0, 8)])  # rr[0]=day t0+k … rr[7]
                row = [1.0, prev, math.sqrt(max(prev, 0.0)), rr[0], rr[1], rr[2], rr[3], rr[4:8].sum()]
                prev = max(0.0, float(np.array(row) @ beta))
            return prev
        obs_rain = lambda t, lead: R[t]
        def fcst_rain(t, lead):  # forecast for day all_days[t] at lead `lead` (≥ 1), bias-corrected
            d_ = all_days[t]
            if d_ not in fidx or lead < 1:
                return R[t]
            return fc[min(lead, 7)][fidx[d_]] * corr[min(lead, 7)]
        def fcst_raw(t, lead):
            d_ = all_days[t]
            return fc[min(lead, 7)][fidx[d_]] if d_ in fidx and lead >= 1 else R[t]
        test = fd[half:]
        row = {"dam": dam["name_th"], "n": len(test)}
        for h in (1, 3, 7):
            e_p = np.mean([abs(D[pos[d_]] - D[pos[d_] + h]) for d_ in test])
            e_o = np.mean([abs(fc_inflow(pos[d_], h, obs_rain) - D[pos[d_] + h]) for d_ in test])
            e_f = np.mean([abs(fc_inflow(pos[d_], h, fcst_rain) - D[pos[d_] + h]) for d_ in test])
            e_r = np.mean([abs(fc_inflow(pos[d_], h, fcst_raw) - D[pos[d_] + h]) for d_ in test])
            row[h] = (e_p, e_o, e_f, e_r)
        # loss term by month and the 7-day storage outlook (inflow held), 2025–2026
        res_by_m = {}
        for d_ in all_days:
            nx = (dt.date.fromisoformat(d_) + dt.timedelta(days=1)).isoformat()
            if nx in storage and d_ in storage and d_ in release:
                res_by_m.setdefault(int(d_[5:7]), []).append(storage[nx] - storage[d_] - (inflow[d_] - release[d_]))
        loss = {m: float(np.median(v)) for m, v in res_by_m.items() if len(v) >= 30}
        e0 = e1 = cnt = 0
        for d_ in all_days:
            t = pos[d_]
            if int(d_[:4]) < 2025 or t + 7 >= n:
                continue
            d7 = all_days[t + 7]
            if d_ not in storage or d7 not in storage or any(all_days[t + k] not in release for k in range(7)):
                continue
            s_plain = storage[d_] + sum(D[t] - release[all_days[t + k]] for k in range(7))
            s_loss = s_plain + sum(loss.get(int(all_days[t + k][5:7]), 0.0) for k in range(7))
            e0 += abs(s_plain - storage[d7]); e1 += abs(s_loss - storage[d7]); cnt += 1
        row["storage7"] = (e0 / cnt, e1 / cnt, cnt) if cnt else None
        row["loss"] = loss
        results.append(row)
        gain = lambda h, i: 100 * (1 - row[h][i] / row[h][0])
        print(f"{dam['name_th']:16s} n {row['n']:3d} · vs persistence — observed rain: 1d {gain(1,1):+4.0f} % 3d {gain(3,1):+4.0f} % 7d {gain(7,1):+4.0f} %"
              f" · forecast rain (bias-corr): 1d {gain(1,2):+4.0f} % 3d {gain(3,2):+4.0f} % 7d {gain(7,2):+4.0f} %"
              f" · raw forecast: 7d {gain(7,3):+4.0f} % · bias lead7 ×{corr[7]:.2f}"
              + (f" · storage 7d MAE {row['storage7'][0]:.1f} → with loss {row['storage7'][1]:.1f} (n {row['storage7'][2]})" if row["storage7"] else ""), flush=True)
        # for the build: bias factors per lead, the model's residual band per horizon on the test days, persistence's band
        band_m, band_p = {}, {}
        for h in range(1, 8):
            em = np.array([fc_inflow(pos[d_], h, fcst_rain) - D[pos[d_] + h] for d_ in test])
            ep = np.array([D[pos[d_]] - D[pos[d_] + h] for d_ in test])
            band_m[str(h)] = [round(float(np.quantile(em, .1)), 3), round(float(np.quantile(em, .9)), 3)]
            band_p[str(h)] = [round(float(np.quantile(ep, .1)), 3), round(float(np.quantile(ep, .9)), 3)]
        gains = {str(h): round(100 * (1 - row[h][2] / row[h][0]), 1) for h in (1, 3, 7)}
        build[dam["name_th"]] = {"dam_id": dam["dam_id"], "beta": [round(float(b), 5) for b in beta], "loss_by_month": {str(k): round(v, 3) for k, v in loss.items()},
                                 "op_gain": gains, "bias": {str(k): round(v, 3) for k, v in corr.items()}, "band_model": band_m, "band_persist": band_p,
                                 "test_days": len(test), "test_from": test[0], "test_to": test[-1],
                                 "points": [(round(p[0][0], 3), round(p[0][1], 3), round(p[1])) for p in pts]}
    except Exception as e:
        print(f"{dam['name_th']}: failed ({type(e).__name__}: {str(e)[:80]})", flush=True)
ok3 = [r["dam"] for r in results if r[3][2] < 0.9 * r[3][0]]
ok7 = [r["dam"] for r in results if r[7][2] < 0.9 * r[7][0]]
print(f"\nSUMMARY (last 46 forecast days, forecast rain): ≥ 10 % better than persistence at 3 d: {ok3}; at 7 d: {ok7}; of {len(results)}")
print("loss term helps the 7-day storage outlook for:", [r["dam"] for r in results if r["storage7"] and r["storage7"][1] < r["storage7"][0]])
print("BUILD_JSON", json.dumps(build, ensure_ascii=False))
