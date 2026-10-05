"""D-101 pilot, inflow for the 7-day scenarios (owner 2026-10-05: "Rain-driven"). Honest test: can catchment rain forecast
Kaeng Krachan's daily inflow better than holding today's inflow (persistence) or HII's day-of-year average (climatology)?
Catchment = HydroBASINS level-8 basins upstream of the dam (data/basins, D-066); rain = Open-Meteo ERA5 archive (keyless) at
the largest sub-basins' centroids, area-weighted; inflow/release/storage = HII daily (dam 13). Fit 2018-2024, test 2025-2026.
Recursive multi-step with *observed* rain = an upper bound (a rain forecast is worse than observed rain) — stated as such.
Also: does storage change equal inflow − release (water-balance check)? Read-only; nothing stored.
Run: python3 research/2026-10-05_kk_inflow_model.py  (writes research/2026-10-05_kk_inflow_model.log via tee)"""
import datetime as dt, json, math, sys, time, urllib.request
import numpy as np

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"
DAM = (12.917017, 99.629886)
S = "/tmp/claude-0/-root-flood2026/93e50846-6b6c-4485-9a01-04687012d56f/scratchpad"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


# --- 1. catchment from HydroBASINS lev08 --------------------------------------------------------------------------------
g = json.load(open("data/basins/hydrobasins_lev08_th.geojson"))
feats = g["features"]
props0 = feats[0]["properties"]
print("HydroBASINS lev08: features", len(feats), "| fields", [k for k in props0 if k in ("HYBAS_ID", "NEXT_DOWN", "SUB_AREA", "UP_AREA", "MAIN_BAS")])


def inside(pt, geom):
    x, y = pt[1], pt[0]  # lon, lat
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        ring = poly[0]
        c = False
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


by_id = {f["properties"]["HYBAS_ID"]: f for f in feats}
home = next((f for f in feats if inside(DAM, f["geometry"])), None)
if not home:
    sys.exit("dam point not in any lev08 basin")
up, queue = [home], [home["properties"]["HYBAS_ID"]]
while queue:
    cur = queue.pop()
    for f in feats:
        if f["properties"].get("NEXT_DOWN") == cur:
            up.append(f); queue.append(f["properties"]["HYBAS_ID"])
area = sum(f["properties"].get("SUB_AREA", 0) for f in up)
up.sort(key=lambda f: -f["properties"].get("SUB_AREA", 0))
pts = [(centroid(f["geometry"]), f["properties"]["SUB_AREA"]) for f in up[:4]]
print(f"catchment: {len(up)} basins, {area:.0f} km² (HydroBASINS UP_AREA at the dam basin {home['properties'].get('UP_AREA')}) | rain points (lat, lon, km²):",
      [(round(p[0][0], 3), round(p[0][1], 3), round(p[1])) for p in pts])

# --- 2. rain (ERA5 archive) -------------------------------------------------------------------------------------------
days = None
rain = np.zeros(0)
for (lat, lon), a in pts:
    d = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}&start_date=2018-01-01"
            f"&end_date=2026-10-04&daily=precipitation_sum&timezone=Asia%2FBangkok")["daily"]
    if days is None:
        days, rain = d["time"], np.zeros(len(d["time"]))
    r = np.array([np.nan if v is None else v for v in d["precipitation_sum"]], float)
    rain += np.nan_to_num(r) * a / sum(p[1] for p in pts)
    time.sleep(0.5)
idx = {d: i for i, d in enumerate(days)}
print(f"ERA5 rain: {len(days)} days {days[0]}..{days[-1]}, mean {rain.mean():.1f} mm/d, max {rain.max():.0f} mm/d")

# --- 3. HII inflow, release, storage, climatology ------------------------------------------------------------------------
inflow, release, storage, clim = {}, {}, {}, {}
for y in range(2018, 2027):
    for kind, store in (("dam_inflow", inflow), ("dam_released", release), ("dam_storage", storage)):
        d = get(f"https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam_yearly_graph?data_type={kind}&dam_id=13&year={y}")["data"]
        for x in d["graph_data"][0]["data"]:
            if x.get("value") is not None:
                store[x["date"][:10]] = float(x["value"])
        if kind == "dam_inflow":
            for x in d.get("average_inflow") or []:
                clim[x["date"][5:10]] = float(x["value"])
        time.sleep(0.4)
print(f"HII: inflow {len(inflow)} days, release {len(release)}, storage {len(storage)}, climatology days {len(clim)}")

# --- 4. water balance: Δstorage vs inflow − release ---------------------------------------------------------------------
pairs = []
for d, s in storage.items():
    nxt = (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()
    if nxt in storage and d in inflow and d in release:
        pairs.append((storage[nxt] - s, inflow[d] - release[d]))
p = np.array(pairs)
res = p[:, 0] - p[:, 1]
print(f"water balance ({len(p)} days): Δstorage − (inflow − release): median {np.median(res):+.2f}, IQR {np.quantile(res, .25):+.2f}..{np.quantile(res, .75):+.2f} ล้าน ลบ.ม./วัน;"
      f" r {np.corrcoef(p[:, 0], p[:, 1])[0, 1]:.3f} → " + ("the balance closes: HII's inflow is consistent with its storage" if abs(np.median(res)) < 0.5 else "a systematic gap (losses/evaporation or an inflow definition)"))

# --- 5. inflow model ---------------------------------------------------------------------------------------------------
all_days = [d for d in days if d in inflow]
D = np.array([inflow[d] for d in all_days]); R = np.array([rain[idx[d]] for d in all_days])
n = len(D)
LAGS = 7


def feats_at(t, inflow_prev):
    # inflow yesterday (given), rain today..t-3, rain t-4..t-7 summed; sqrt transforms tame the skew
    return [1.0, inflow_prev, math.sqrt(inflow_prev), R[t], R[t - 1], R[t - 2], R[t - 3], R[t - 4:t - 7:-1].sum() if t >= 7 else 0.0]


def fit(train_idx):
    X = np.array([feats_at(t, D[t - 1]) for t in train_idx]); y = D[train_idx]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def forecast(beta, t0, h):
    """Recursive: from day t0 (inflow known) h days ahead with observed rain (upper bound)."""
    prev = D[t0]
    for k in range(1, h + 1):
        prev = max(0.0, float(np.array(feats_at(t0 + k, prev)) @ beta))
    return prev


def split(year_from, year_to):
    return [t for t in range(LAGS, n) if year_from <= int(all_days[t][:4]) <= year_to]


for train_years, test_years in (((2018, 2024), (2025, 2026)), ((2018, 2023), (2024, 2024))):
    tr, te = split(*train_years), split(*test_years)
    beta = fit(tr)
    print(f"\nfit {train_years[0]}-{train_years[1]} (n {len(tr)}), test {test_years[0]}-{test_years[1]} (n {len(te)}):")
    print("  coefficients [1, inflow(t-1), √inflow(t-1), rain t, t-1, t-2, t-3, Σ t-4..7]:", np.round(beta, 3).tolist())
    for h in (1, 2, 3, 5, 7):
        rows = [(forecast(beta, t, h), D[t], D[t + h], clim.get(all_days[t + h][5:10], np.nan)) for t in te if t + h < n]
        a = np.array(rows)
        m_model, m_pers = np.abs(a[:, 0] - a[:, 2]).mean(), np.abs(a[:, 1] - a[:, 2]).mean()
        m_clim = np.nanmean(np.abs(a[:, 3] - a[:, 2]))
        worse = (np.abs(a[:, 0] - a[:, 2]) > np.abs(a[:, 1] - a[:, 2])).mean()
        big = a[:, 2] >= 10
        print(f"  h={h} d: MAE model {m_model:.2f} · persistence {m_pers:.2f} · climatology {m_clim:.2f} ล้าน ลบ.ม./วัน"
              f" → {100 * (1 - m_model / m_pers):+.0f} % vs persistence; worse on {100 * worse:.0f} % of days;"
              f" inflow ≥ 10: model {np.abs(a[big, 0] - a[big, 2]).mean():.2f} vs persistence {np.abs(a[big, 1] - a[big, 2]).mean():.2f} (n {big.sum()})")
    if train_years == (2018, 2024):
        q = {}
        for h in range(1, 8):
            e = np.array([forecast(beta, t, h) - D[t + h] for t in te if t + h < n])
            q[h] = (float(np.quantile(e, .1)), float(np.quantile(e, .9)))
        print("  residual 10–90 % by horizon (for the band):", {h: (round(v[0], 1), round(v[1], 1)) for h, v in q.items()})
        print("  BETA_JSON", json.dumps({"beta": np.round(beta, 5).tolist(), "band": q, "points": [(round(p[0][0], 3), round(p[0][1], 3), round(p[1])) for p in pts]}))
print("\nNote: multi-step skill uses observed rain for the coming days — the ceiling for a rain forecast; operational skill is lower.")

# --- 6. the honest alternative: hold today's inflow, band = persistence's own errors by horizon (test years) -------------
te = split(2025, 2026)
print("\npersistence band (inflow(t+h) − inflow(t), 2025-2026, 10–90 %):")
band = {}
for h in range(1, 8):
    e = np.array([D[t + h] - D[t] for t in te if t + h < n])
    band[h] = (float(np.quantile(e, .1)), float(np.quantile(e, .9)))
    print(f"  h={h}: {band[h][0]:+.2f} .. {band[h][1]:+.2f} ล้าน ลบ.ม./วัน (n {len(e)})")
print("  PERSIST_BAND_JSON", json.dumps({str(h): [round(v[0], 3), round(v[1], 3)] for h, v in band.items()}))
hi = [t for t in te if D[t] >= 10 and t + 7 < n]
print(f"  on days with inflow ≥ 10 (n {len(hi)}): 7-day change 10–90 % {np.quantile([D[t+7]-D[t] for t in hi], .1):+.1f} .. {np.quantile([D[t+7]-D[t] for t in hi], .9):+.1f}")
print("\nhigh-inflow regime (inflow(t) ≥ 10, all years 2018-2026 for sample size), persistence band by horizon:")
hi_all = [t for t in range(LAGS, n) if D[t] >= 10]
regime = {}
for h in range(1, 8):
    e = np.array([D[t + h] - D[t] for t in hi_all if t + h < n])
    regime[h] = (float(np.quantile(e, .1)), float(np.quantile(e, .9)))
    print(f"  h={h}: {regime[h][0]:+.1f} .. {regime[h][1]:+.1f} (n {len(e)})")
print("  HIGH_BAND_JSON", json.dumps({str(h): [round(v[0], 2), round(v[1], 2)] for h, v in regime.items()}))
