"""E-7D-DOWN — the river below Kaeng Krachan, days 1–7, given a 7-day release plan, future rain and other parameters
(owner 2026-10-05: "plan reservoir discharge release for 7 days in advance together with future rain and other parameters,
so we need the good prediction for the impact tab for this forecast time period … Try validating many possibilities,
models, theories, inputs, parameters"; "7-day prediction is first for impact analysis for reservoir management only").

What the scenarios use now (D-101, scenarios.daily_downstream): impact.whatif per day — today's local inflows and the
diversion held, the point's rating curve, the release that reaches the point that day (whole-day travel time) — and one
safety margin per point from the replay, which scores the chain at the point's own lag (~1–2 days), not at days 3–7.

Hindcast: every issue day d of the past year (all of day d known), the actual releases of days d+1…d+7 stand in for the
plan (the release is the decision, so knowing it is not cheating); the target is each point's daily mean level on d+k.
  references   keep (today's daily mean) · MR mean reversion toward the 30-day mean
  chain        WA the production chain (absolute) · WN the chain anchored on today's level (only its change is added)
               · GN today + g·ΔQ (cm per m³/s of release change reaching the point, fitted)
  regression   RR ridge per point and lead on Δlevel: release change reaching the point (that day and summed), anomaly to
               the 30-day mean, yesterday's change, rain today / past 3 days / past 30 days (wetness), forecast rain
               1…k and k−1…k, forecast × wetness, season, spring–neap tide phase (14.77 days) · RN the same without the
               release terms (what the release explains) · AR WN corrected by a ridge on its own error (same inputs)
  analogs      AN the 20 most similar training days (anomaly, change, release change, forecast rain, wetness)
  blend        BL mean(AR, RR)
  constrained  GR today + g·ΔQ + γ·forecast rain 1…k (γ ≥ 0) · GW the same with γ·rain × wetness · GM today + g·ΔQ + ρ·(30-day
               mean − today) — one or two coefficients each (the 14-input ridges overfit one mostly dry year)
  hybrid       HY per point: the anchored chain where the dam's release passes one-to-one (B.18), the gain elsewhere — the
               point's method picked on one sample and confirmed on the other
Two disjoint samples: issue days in odd months vs even months; each scored with every fit (ratings, lags, ridges) made
on the other sample, training days whose 7-day target reaches into the scored sample dropped; rain = ERA5 (observed,
an upper bound for the rain terms). The release-aware method is picked on one sample and confirmed on the other.
Operational check: fits on the days before the forecast archive (2026-07-06), the archived forecasts (4-model mean, scaled
per lead on the first half) as future rain, first half picks, second half scores.
Per point and lead the MAE and the 90 % absolute error are printed: the margin a plan must keep on that day.
Run (CACHE writable, outside the repo):
  docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$PWD/data:/app/data:ro" \
    -v "$CACHE:/cache" worker python - < research/2026-10-05_e7d_down.py"""
import datetime as dt, json, math, os, time, urllib.request
import numpy as np
from floodwatch import db, impact

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"
CACHE = "/cache/e7d_down"
os.makedirs(CACHE, exist_ok=True)
CASE = impact.CASES["kaeng-krachan"]
CODES = [p["code"] for p in CASE["points"]]
MODELS = ["best_match", "ecmwf_ifs025", "gfs_seamless", "icon_seamless"]
LEADS = list(range(1, 8))
CMS = 1e6 / 86400.0


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return json.loads(r.read())
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))


def ridge(X, y, alpha=3.0):
    X = np.asarray(X, float); y = np.asarray(y, float)
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return lambda Xn: ((np.atleast_2d(np.asarray(Xn, float)) - mu) / sd) @ w + y.mean()


# ---------------- data ----------------
with db.connect_readonly() as c:
    raw = {code: c.execute(impact.HOURLY_SQL, (code,)).fetchall() for code in CODES}
    rel = {r["d"]: float(r["v"]) for r in c.execute(
        "SELECT dam_date::text AS d, released_mcm AS v FROM dam_daily WHERE dam_id=%s AND released_mcm IS NOT NULL",
        (CASE["dam_ids"]["RID"],)).fetchall()}
    meta = {r["code"]: dict(r) for r in c.execute("SELECT code, bank_msl, lat, lon FROM station WHERE code = ANY(%s)", (CODES,)).fetchall()}
t0 = min(r[0]["t"] for r in raw.values() if r)
t1 = max(r[-1]["t"] for r in raw.values() if r)
N = int((t1 - t0).total_seconds() // 3600) + 1
H, Q = {}, {}
for code, rows in raw.items():
    h, q = np.full(N, np.nan), np.full(N, np.nan)
    for r in rows:
        k = int((r["t"] - t0).total_seconds() // 3600)
        h[k] = r["h"] if r["h"] is not None else np.nan
        q[k] = r["q"] if r["q"] is not None else np.nan
    H[code], Q[code] = h, q
local_day = [(t0 + dt.timedelta(hours=i + 7)).date().isoformat() for i in range(N)]
DAYS = sorted(set(local_day))
DPOS = {d: i for i, d in enumerate(DAYS)}
hours_of = {}
for i, d in enumerate(local_day):
    hours_of.setdefault(d, []).append(i)
def dmean(x, d, need=12):
    v = x[hours_of.get(d, [])]
    v = v[np.isfinite(v)]
    return float(v.mean()) if len(v) >= need else np.nan
HD = {c_: np.array([dmean(H[c_], d) for d in DAYS]) for c_ in CODES}
end_hour = {d: max(hs) for d, hs in hours_of.items()}
print(f"hourly {t0:%Y-%m-%d} … {t1:%Y-%m-%d}, {len(DAYS)} days; releases {len(rel)} days", flush=True)

# rain: the home HydroBASINS lev08 basins of the points (the land between the dam and the city), ERA5 + forecast archive
rain_path = f"{CACHE}/rain.json"
if os.path.exists(rain_path):
    RAIN = json.load(open(rain_path))
else:
    g = json.load(open("data/basins/hydrobasins_lev08_th.geojson"))
    def inside(pt, geom):
        x, y = pt[1], pt[0]
        for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]):
            ring, cc = poly[0], False
            for i in range(len(ring)):
                x1, y1 = ring[i - 1]; x2, y2 = ring[i]
                if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
                    cc = not cc
            if cc:
                return True
        return False
    homes = {}
    for code in CODES:
        m = meta.get(code) or {}
        if m.get("lat") is None:
            continue
        f = next((f for f in g["features"] if inside((m["lat"], m["lon"]), f["geometry"])), None)
        if f:
            pts = [p for poly in (f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]) for p in poly[0]]
            homes[f["properties"]["HYBAS_ID"]] = ((sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)), f["properties"]["SUB_AREA"])
    pts = list(homes.values()); wsum = sum(a for _, a in pts)
    era, fdays, fcp = {}, None, {m: [] for m in MODELS}
    for (lat, lon), a in pts:
        d = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}&start_date=2025-08-01"
                f"&end_date=2026-10-05&daily=precipitation_sum&timezone=Asia%2FBangkok")["daily"]
        for t, v in zip(d["time"], d["precipitation_sum"]):
            era[t] = era.get(t, 0.0) + (v or 0.0) * a / wsum
        time.sleep(0.4)
        for m in MODELS:
            hv = ",".join(["precipitation"] + [f"precipitation_previous_day{n}" for n in LEADS])
            hh = get(f"https://previous-runs-api.open-meteo.com/v1/forecast?latitude={lat:.3f}&longitude={lon:.3f}&hourly={hv}"
                     f"&past_days=92&forecast_days=1&timezone=Asia%2FBangkok&models={m}")["hourly"]
            dd = sorted({t[:10] for t in hh["time"]})
            fdays = fdays or dd
            idx = {x: i for i, x in enumerate(fdays)}
            per = {}
            for n in [0] + LEADS:
                key = "precipitation" if n == 0 else f"precipitation_previous_day{n}"
                tot, cnt = [0.0] * len(fdays), [0] * len(fdays)
                for t, v in zip(hh["time"], hh.get(key) or []):
                    if v is not None and t[:10] in idx:
                        tot[idx[t[:10]]] += v; cnt[idx[t[:10]]] += 1
                per[str(n)] = [tot[i] if cnt[i] >= 20 else None for i in range(len(fdays))]
            fcp[m].append((a, per))
            time.sleep(0.4)
    fc = {}
    for m in MODELS:
        fc[m] = {}
        for n in [0] + LEADS:
            vals = []
            for i in range(len(fdays)):
                num = den = 0.0
                for a, per in fcp[m]:
                    if per[str(n)][i] is not None:
                        num += per[str(n)][i] * a; den += a
                vals.append(num / den if den > 0 else None)
            fc[m][str(n)] = vals
    RAIN = {"era": era, "fdays": fdays, "fc": fc, "pts": pts}
    json.dump(RAIN, open(rain_path, "w"))
ERA = np.array([RAIN["era"].get(d, np.nan) for d in DAYS])
FPOS = {d: i for i, d in enumerate(RAIN["fdays"])}
print(f"rain: {len(RAIN['pts'])} basins between the dam and the city; forecast archive {RAIN['fdays'][0]} … {RAIN['fdays'][-1]}", flush=True)

REL = np.array([rel.get(d, np.nan) for d in DAYS])
SPRING_REF = dt.date(2000, 1, 6)
def tide_phase(i):
    x = ((dt.date.fromisoformat(DAYS[i]) - SPRING_REF).days % 14.765) / 14.765
    return [math.sin(2 * math.pi * x), math.cos(2 * math.pi * x)]
def season(i):
    y = dt.date.fromisoformat(DAYS[i]).timetuple().tm_yday
    return [math.sin(2 * math.pi * y / 365.25), math.cos(2 * math.pi * y / 365.25)]

# issue days: 35 days of history, releases known d…d+7
ISSUE = [i for i in range(35, len(DAYS) - 7) if all(np.isfinite(REL[i + k]) for k in range(0, 8)) and DAYS[i] in end_hour]


def fit_chain(train_days):
    """Ratings and lags from the hours of the training days only (as build_state fits them on the year)."""
    mask = np.zeros(N, bool)
    for i in train_days:
        for k in range(0, 8):
            if i + k < len(DAYS):
                mask[hours_of[DAYS[i + k]]] = True
    Hm = {c_: np.where(mask, H[c_], np.nan) for c_ in CODES}
    Qm = {c_: np.where(mask, Q[c_], np.nan) for c_ in CODES}
    q18, q10, q16 = Qm["B.18"], Qm["B.10"], Qm["B.16"]
    fits = {"B.10": impact.lag_fit(q18, q10), "B.16": impact.lag_fit(q18, q16)}
    for p in CASE["points"]:
        if p["role"] == "city":
            fits[p["code"]] = impact.lag_fit(q18, Hm[p["code"]])
    lags = {"B.18": 0, "B.10": fits["B.10"][0] if fits["B.10"] else 32}
    lags["B.16"] = max(lags["B.10"], fits["B.16"][0] if fits["B.16"] else 43)
    for p in CASE["points"]:
        if p["role"] == "city":
            lags[p["code"]] = max(lags["B.16"], fits[p["code"]][0] if fits[p["code"]] else 48)
    ratings = {}
    for p in CASE["points"]:
        code = p["code"]
        if p["role"] == "city":
            ratings[code] = impact.fit_rating(impact.shift(Qm[p["rating_from"]], lags[code] - lags[p["rating_from"]]), Hm[code])
        else:
            ratings[code] = impact.fit_rating(Qm[code], Hm[code])
    return lags, ratings


def state_at(i, lags, ratings):
    idx = end_hour[DAYS[i]]
    pts = []
    for p in CASE["points"]:
        code = p["code"]
        up = {"after_diversion": ("B.18", lags["B.10"]), "river": ("B.10", lags["B.16"] - lags["B.10"])}.get(p["role"])
        pts.append({**p, "rating": ratings[code], "lag_h": lags[code], "bank": (meta.get(code) or {}).get("bank_msl"),
                    "q_now": impact._last(Q[code], idx), "h_now": impact._last(H[code], idx),
                    "q_up_lagged": impact._last(Q[up[0]], idx - up[1]) if up else None})
    D = impact.diversion_now(Q["B.18"][:idx + 1], Q["B.10"][:idx + 1], lags["B.10"]) or 0.0
    return {"points": pts, "diversion_default": D, "dam": {"released_mcm": REL[i]}}


def reach(i, k, lagd):
    """The release that reaches a point with travel time `lagd` whole days on day i+k (before day 1: today's)."""
    j = k - lagd
    return REL[i + j] if j >= 1 else REL[i]


def rain_known(i, src):
    """(past rain series to day i, forecast rain for days i+1…i+7) as known at the end of day i."""
    pr = ERA[: i + 1].copy()
    if src == "obs":
        return pr, ERA[i + 1: i + 8].copy()
    def f(day_i, lead):
        d = DAYS[day_i] if day_i < len(DAYS) else None
        vals = []
        for m in MODELS:
            v = RAIN["fc"][m][str(lead)][FPOS[d]] if d in FPOS else None
            sc = SCALE.get((m, lead))
            if v is not None and sc is not None:
                vals.append(v * sc)
        return float(np.mean(vals)) if vals else np.nan
    for j in range(max(0, i - 4), i + 1):
        v = f(j, 0)
        if np.isfinite(v):
            pr[j] = v
    return pr, np.array([f(i + k, k) for k in LEADS])


SCALE = {}
COEF = {}


def features(i, k, code, lagd, pr, F, with_rel=True):
    h = HD[code]
    a30 = h[i] - np.nanmean(h[i - 29: i + 1]); d1 = h[i] - h[i - 1]
    dr = reach(i, k, lagd) - REL[i]; dr_sum = sum(reach(i, j, lagd) - REL[i] for j in range(1, k + 1))
    wet = float(np.nansum(pr[i - 29: i + 1])); Fk = float(np.nansum(F[:k])); Fl = float(np.nansum(F[max(0, k - 2):k]))
    x = [a30, d1, pr[i], float(np.nansum(pr[i - 2: i + 1])), wet, Fk, Fl, Fk * wet / 100.0] + season(i + k) + tide_phase(i + k)
    return ([dr, dr_sum] if with_rel else []) + x


def evaluate(train, test, src_test):
    """All candidates fitted on `train`, predictions on `test` (rain source for the test: obs or fc)."""
    lags, ratings = fit_chain(train)
    lagd = {c_: int(round(lags[c_] / 24.0)) for c_ in CODES}
    wi_cache = {}
    def wi(i, r):
        key = (i, round(float(r), 3))
        if key not in wi_cache:
            st = state_at(i, lags, ratings)
            wi_cache[key] = {row["code"]: (row["level"][1] if row["level"] else np.nan) for row in impact.whatif(st, float(r))["rows"]}
        return wi_cache[key]
    out = {}
    for code in CODES:
        h = HD[code]
        tr_rows = {k: [i for i in train if np.isfinite(h[i]) and np.isfinite(h[i - 1]) and np.isfinite(h[i + k])
                       and np.isfinite(np.nanmean(h[i - 29:i + 1]))] for k in LEADS}
        te_rows = {k: [i for i in test if np.isfinite(h[i]) and np.isfinite(h[i - 1]) and np.isfinite(h[i + k])] for k in LEADS}
        res = {}
        for k in LEADS:
            trr, ter = tr_rows[k], te_rows[k]
            if len(trr) < 40 or len(ter) < 15:
                continue
            P = {}
            # training quantities (observed rain for training rows)
            Xr = [features(i, k, code, lagd[code], ERA[: i + 1], ERA[i + 1: i + 8]) for i in trr]
            Xn = [features(i, k, code, lagd[code], ERA[: i + 1], ERA[i + 1: i + 8], with_rel=False) for i in trr]
            y = np.array([h[i + k] - h[i] for i in trr])
            fR, fN = ridge(Xr, y), ridge(Xn, y)
            anom = np.array([np.nanmean(h[i - 29:i + 1]) - h[i] for i in trr])
            rho = float(np.sum(anom * y) / max(np.sum(anom ** 2), 1e-9))
            dq = np.array([(reach(i, k, lagd[code]) - REL[i]) * CMS for i in trr])
            g = float(np.sum(dq * y) / np.sum(dq ** 2)) if np.sum(dq ** 2) > 0 else 0.0
            Fk_tr = np.array([float(np.nansum(ERA[i + 1: i + 1 + k])) for i in trr])
            wet_tr = np.array([float(np.nansum(ERA[i - 29: i + 1])) for i in trr])
            res_g = y - g * dq
            gam = max(0.0, float(np.sum(Fk_tr * res_g) / max(np.sum(Fk_tr ** 2), 1e-9)))
            fw = Fk_tr * wet_tr / 100.0
            gamw = max(0.0, float(np.sum(fw * res_g) / max(np.sum(fw ** 2), 1e-9)))
            rhog = float(np.sum(anom * res_g) / max(np.sum(anom ** 2), 1e-9))
            COEF.setdefault(code, {})[k] = {"g_cm_per_cms": round(100 * g, 3), "gamma_cm_per_mm": round(100 * gam, 3), "rho": round(rhog, 3)}
            wn_tr = np.array([h[i] + wi(i, reach(i, k, lagd[code]))[code] - wi(i, REL[i])[code] for i in trr])
            okw = np.isfinite(wn_tr)
            fA = ridge(np.array(Xr)[okw], (np.array([h[i + k] for i in trr]) - wn_tr)[okw]) if okw.sum() > 30 else None
            Zt = np.array([[x[2], x[3], x[0], x[7], x[6]] for x in Xr])  # anomaly, change, release change, forecast, wetness
            zmu, zsd = Zt.mean(0), Zt.std(0) + 1e-9
            for i in ter:
                pr, F = rain_known(i, src_test)
                if not np.isfinite(F[:k]).all():
                    continue
                xr = features(i, k, code, lagd[code], pr, F); xn = features(i, k, code, lagd[code], pr, F, with_rel=False)
                wa = wi(i, reach(i, k, lagd[code]))[code]; w0 = wi(i, REL[i])[code]
                wn = h[i] + wa - w0 if np.isfinite(wa) and np.isfinite(w0) else np.nan
                zq = (np.array([xr[2], xr[3], xr[0], xr[7], xr[6]]) - zmu) / zsd
                dist = np.sqrt((((Zt - zmu) / zsd - zq) ** 2).sum(1)); nn = np.argsort(dist)[:20]
                pred = {"keep": h[i], "MR": h[i] + rho * (np.nanmean(h[i - 29:i + 1]) - h[i]), "WA": wa, "WN": wn,
                        "GN": h[i] + g * (reach(i, k, lagd[code]) - REL[i]) * CMS, "RR": h[i] + float(fR(xr)[0]),
                        "RN": h[i] + float(fN(xn)[0]), "AR": (wn + float(fA(xr)[0])) if fA is not None and np.isfinite(wn) else np.nan,
                        "AN": h[i] + float(np.mean(y[nn]))}
                pred["BL"] = float(np.mean([pred["AR"], pred["RR"]])) if np.isfinite(pred["AR"]) else np.nan
                Fk = float(np.nansum(F[:k])); wet_i = float(np.nansum(pr[i - 29: i + 1]))
                pred["GR"] = pred["GN"] + gam * Fk
                pred["GW"] = pred["GN"] + gamw * Fk * wet_i / 100.0
                pred["GM"] = pred["GN"] + rhog * (np.nanmean(h[i - 29:i + 1]) - h[i])
                pred["HY"] = pred["WN"] if code == "B.18" else pred["GN"]
                P[i] = {m: pred[m] - h[i + k] for m in pred}
            res[k] = P
        out[code] = res
    return out, lags


def summarize(errs, days_set=None):
    """{code: {k: {method: (MAE cm, p90 cm, n)}}} over the issue days in days_set (all when None)."""
    out = {}
    for code, per in errs.items():
        out[code] = {}
        for k, P in per.items():
            ds = [i for i in P if days_set is None or i in days_set]
            if not ds:
                continue
            meths = [m for m in P[ds[0]] if all(np.isfinite(P[i][m]) for i in ds)]
            out[code][k] = {m: (100 * float(np.mean([abs(P[i][m]) for i in ds])), 100 * float(np.quantile([abs(P[i][m]) for i in ds], 0.9)), len(ds))
                            for m in meths}
    return out


RELEASE_AWARE = ["WA", "WN", "GN", "RR", "AR", "AN", "BL", "GR", "GW", "GM", "HY"]
month = lambda i: int(DAYS[i][5:7])
S1 = [i for i in ISSUE if month(i) % 2 == 1]
S2 = [i for i in ISSUE if month(i) % 2 == 0]
def purge(train, test):
    tset = set(test)
    return [i for i in train if not any((i + k) in tset for k in range(0, 8)) and not any((i - k) in tset for k in range(1, 8))]
print(f"issue days {len(ISSUE)}: odd months {len(S1)}, even months {len(S2)}", flush=True)
E1, lags1 = evaluate(purge(S2, S1), S1, "obs")
E2, lags2 = evaluate(purge(S1, S2), S2, "obs")
s1, s2 = summarize(E1), summarize(E2)
print(f"lags (h) fitted on even months: {lags1} · on odd months: {lags2}", flush=True)

def table(summ, title):
    print(f"\n=== {title}: MAE cm (90 % abs error) per point and lead day")
    for code in CODES:
        for k in LEADS:
            r = summ.get(code, {}).get(k)
            if not r:
                continue
            keep = r["keep"][0]
            print(f"{code:7s} d{k} n {r['keep'][2]:3d} · keep {keep:5.1f} · " + " · ".join(
                f"{m} {v[0]:5.1f} ({v[1]:5.1f})" for m, v in r.items() if m != "keep"), flush=True)
table(s1, "sample 1 (odd months; fits on even months; observed rain)")
table(s2, "sample 2 (even months; fits on odd months; observed rain)")

def pick(summ):
    """The release-aware method with the lowest error summed over points and leads 3 and 7."""
    tot = {}
    for m in RELEASE_AWARE:
        v = [summ[c_][k][m][0] for c_ in summ for k in (3, 7) if k in summ[c_] and m in summ[c_][k]]
        if len(v) == sum(1 for c_ in summ for k in (3, 7) if k in summ[c_]):
            tot[m] = sum(v)
    return min(tot, key=tot.get) if tot else None, tot
p1, t1_ = pick(s1); p2, t2_ = pick(s2)
print("coefficients (last fit):", json.dumps(COEF), flush=True)
def pick_point(summ, code):
    v = {m: sum(summ[code][k][m][0] for k in (3, 7) if k in summ[code] and m in summ[code][k]) for m in RELEASE_AWARE if m != "HY"}
    return min(v, key=v.get) if v else None
for code in CODES:
    a, b = pick_point(s1, code), pick_point(s2, code)
    print(f"per-point pick {code}: sample 1 → {a}, sample 2 → {b}" + (" (agree)" if a == b else ""), flush=True)
print(f"\nrelease-aware pick on sample 1: {p1} {t1_} · on sample 2: {p2} {t2_}", flush=True)
for name, (pk, summ) in {"picked on 1, scored on 2": (p1, s2), "picked on 2, scored on 1": (p2, s1)}.items():
    for k in (1, 3, 5, 7):
        rows = [summ[c_][k] for c_ in CODES if k in summ.get(c_, {}) and pk in summ[c_][k]]
        if rows:
            m_ = sum(r[pk][0] for r in rows); wa = sum(r["WA"][0] for r in rows if "WA" in r); kp = sum(r["keep"][0] for r in rows)
            print(f"{name}: {pk} day {k}: summed MAE {m_:.1f} cm vs production chain {wa:.1f} ({100 * (m_ / wa - 1):+.0f} %) vs keep {kp:.1f} ({100 * (m_ / kp - 1):+.0f} %)", flush=True)

# ---------------- operational check: the forecast archive window ----------------
fwin = [i for i in ISSUE if DAYS[i] in FPOS and DAYS[i] >= RAIN["fdays"][0]]
if len(fwin) >= 30:
    half = len(fwin) // 2
    a_days = [DAYS[i] for i in fwin[:half]]
    for m in MODELS:
        for n_ in [0] + LEADS:
            ok = [d for d in a_days if RAIN["fc"][m][str(n_)][FPOS[d]] is not None and np.isfinite(RAIN["era"].get(d, np.nan))]
            num = sum(RAIN["era"][d] for d in ok); den = sum(RAIN["fc"][m][str(n_)][FPOS[d]] for d in ok)
            SCALE[(m, n_)] = num / den if den > 0 and len(ok) >= 10 else None
    train = [i for i in ISSUE if DAYS[i] < RAIN["fdays"][0] and i + 7 < fwin[0]]
    EO, lagsO = evaluate(train, fwin, "fc")
    sA, sB = summarize(EO, set(fwin[:half])), summarize(EO, set(fwin[half:]))
    table(sB, f"OPERATIONAL second half ({DAYS[fwin[half]]} … {DAYS[fwin[-1]]}; fits before {RAIN['fdays'][0]}; forecast rain, 4-model mean)")
    pO, tO = pick(sA)
    print("operational coefficients:", json.dumps(COEF), flush=True)
    print(f"\noperational: release-aware pick on the first half: {pO}", flush=True)
    for k in LEADS:
        rows = [sB[c_][k] for c_ in CODES if k in sB.get(c_, {}) and pO in sB[c_][k]]
        if rows:
            m_ = sum(r[pO][0] for r in rows); wa = sum(r["WA"][0] for r in rows if "WA" in r); kp = sum(r["keep"][0] for r in rows)
            print(f"operational day {k}: {pO} summed MAE {m_:.1f} cm · production chain {wa:.1f} ({100 * (m_ / wa - 1):+.0f} %) · keep {kp:.1f}", flush=True)
    for m_ in ("HY", "GN", "GR", "GW", "GM", "WN"):
        for k in (1, 3, 5, 7):
            rows = [sB[c_][k] for c_ in CODES if k in sB.get(c_, {}) and m_ in sB[c_][k]]
            if rows:
                v = sum(r[m_][0] for r in rows); kp = sum(r["keep"][0] for r in rows); wa = sum(r["WA"][0] for r in rows)
                print(f"operational {m_} day {k}: summed MAE {v:.1f} cm · vs keep {100 * (v / kp - 1):+.0f} % · vs production chain {100 * (v / wa - 1):+.0f} %", flush=True)
    print("MARGINS_JSON", json.dumps({"picked": pO, "per_point": {c_: {k: {m: [round(v[0], 1), round(v[1], 1)] for m, v in sB[c_][k].items() if m in (pO, "WA", "keep", "HY", "GN", "WN", "GR")}
                                                                       for k in sB.get(c_, {})} for c_ in CODES}}))
print("SUMMARY_JSON", json.dumps({"s1": {c_: {k: {m: [round(v[0], 1), round(v[1], 1)] for m, v in r.items()} for k, r in per.items()} for c_, per in s1.items()},
                                  "s2": {c_: {k: {m: [round(v[0], 1), round(v[1], 1)] for m, v in r.items()} for k, r in per.items()} for c_, per in s2.items()},
                                  "pick": [p1, p2]}))
