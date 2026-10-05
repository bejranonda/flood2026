"""E-7D-IN — reservoir inflow 1–7 days ahead for the impact tab's 7-day release planning (owner 2026-10-05: "plan reservoir
discharge release for 7 days in advance together with future rain and other parameters … 7-day prediction is first for
impact analysis for reservoir management only … Try validating many possibilities, models, theories, inputs, parameters";
"If the other rain model is not better, you can limit to 6 days"). Served now (D-102): the Q58 recursive rain model at the
horizons where it beat persistence by ≥ 10 % with forecast rain, persistence elsewhere (Kaeng Krachan: persistence to 3 d).

Every candidate sees only what is known at issue day t: inflow up to t; past rain = ERA5 up to t−5 and the forecast
system's own lead-0 rain for t−4…t (ERA5 arrives ~5 days late); rain for t+1…t+7 = archived forecasts (Open-Meteo previous
runs) at their real lead, scaled per model and lead to ERA5's total on the first half of the window. Rain sources: bm
(best_match), ec (ECMWF IFS 0.25°), gfs, icon (leads ≤ 6), E3 (mean of bm, ec, gfs), E4 (+ icon; lead 7 from the other three).
  baselines   P persistence · CL climatology (day of year ±7, 2018–2024) · K damped toward the 30-day mean · KC damped
              toward climatology
  statistical D_r direct ridge per horizon (inflow t, t−1, √, rain past 1/3/7/30 days, forecast sum 1…h and h−1…h,
              forecast × wetness, season) · L_r the same in log space · KF_r damped persistence + rain terms
  recursive   R (the Q58 form, best_match; served now where it passed) · R4 (E4 rain)
  analogs     AN4: the 20 most similar training days (inflow, wetness, forecast rain), their inflow *change* after h days
  theory      HB_r: HBV-style soil bucket (runoff = rain·(S/Smax)^β, evaporation 3.5 mm/d) + linear-reservoir routing,
              calibrated per dam on 2018–2024 (grid over Smax, β, k; scale and base by least squares), run with past rain to
              t, forecast rain after; its error at t decays by k^h (state updating)
  blends      BL1 mean(D_E4, P) · BL2 mean(D_E4, L_E4, KF_E4) · BL3 mean(D_E4, HB_E4)
Choices, each scored on the second half of the window:
  C  per dam and horizon, the best candidate on the first half if ≥ 10 % better than P there, else P
  G  one candidate per horizon for all dams, chosen on the *other* sample's first half (picked on 1, confirmed on 2)
  S  what we serve now
Fit 2018-01…2024-12 (ERA5 as every rain input). Two disjoint samples of RID dams (alternating in dam_id order). Gate (the
owner's two-sample rule): G or C better than persistence AND than served-now at 3 d and 7 d in both samples, with no more
dams made worse than served-now. Also scored: the 7-day storage error with the actual releases as the plan and the
monthly loss term — the number the release plan stands on.
Run (CACHE = a writable folder outside the repo):
  docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$PWD/data:/app/data:ro" \
    -v "$CACHE:/cache" worker python - [dam_id …] < research/2026-10-05_e7d_inflow.py"""
import datetime as dt, json, math, os, sys, time, urllib.request
import numpy as np
from floodwatch import db

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"
CACHE = "/cache/e7d_in"
os.makedirs(CACHE, exist_ok=True)
MODELS = ["best_match", "ecmwf_ifs025", "gfs_seamless", "icon_seamless"]  # ICON's archive has leads 0–6 only
E3 = MODELS[:3]
LEADS = list(range(1, 8))
GATE = 0.10
ONLY = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return json.loads(r.read())
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))


g = json.load(open("data/basins/hydrobasins_lev08_th.geojson"))
feats = g["features"]


def inside(pt, geom):
    x, y = pt[1], pt[0]
    for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]):
        ring, c = poly[0], False
        for i in range(len(ring)):
            x1, y1 = ring[i - 1]; x2, y2 = ring[i]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
                c = not c
        if c:
            return True
    return False


def centroid(geom):
    pts = [p for poly in (geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]) for p in poly[0]]
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


def load(dam):
    path = f"{CACHE}/dam_{dam['dam_id']}.json"
    if os.path.exists(path):
        return json.load(open(path))
    pts = catchment(dam["lat"], dam["lon"])
    if not pts:
        return None
    wsum = sum(a for _, a in pts)
    era_days, era = None, None
    fdays, fc_pts = None, {m: [] for m in MODELS}
    for (lat, lon), a in pts:
        d = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}&start_date=2018-01-01"
                f"&end_date=2026-10-05&daily=precipitation_sum&timezone=Asia%2FBangkok")["daily"]
        if era_days is None:
            era_days, era = d["time"], [0.0] * len(d["time"])
        for i, v in enumerate(d["precipitation_sum"]):
            era[i] += (v or 0.0) * a / wsum
        time.sleep(0.4)
        for m in MODELS:
            hv = ",".join(["precipitation"] + [f"precipitation_previous_day{n}" for n in LEADS])
            h = get(f"https://previous-runs-api.open-meteo.com/v1/forecast?latitude={lat:.3f}&longitude={lon:.3f}&hourly={hv}"
                    f"&past_days=92&forecast_days=1&timezone=Asia%2FBangkok&models={m}")["hourly"]
            dd = sorted({t[:10] for t in h["time"]})
            if fdays is None:
                fdays = dd
            idx = {x: i for i, x in enumerate(fdays)}
            per = {}
            for n in [0] + LEADS:  # a day counts only when ≥ 20 of its hours exist; a missing lead stays missing (not 0 mm)
                key = "precipitation" if n == 0 else f"precipitation_previous_day{n}"
                tot, cnt = [0.0] * len(fdays), [0] * len(fdays)
                for t, v in zip(h["time"], h.get(key) or []):
                    if v is not None and t[:10] in idx:
                        tot[idx[t[:10]]] += v; cnt[idx[t[:10]]] += 1
                per[str(n)] = [tot[i] if cnt[i] >= 20 else None for i in range(len(fdays))]
            fc_pts[m].append((a, per))
            time.sleep(0.4)
    fc = {}
    for m in MODELS:  # area-weighted over the points that have the day
        fc[m] = {}
        for n in [0] + LEADS:
            vals = []
            for i in range(len(fdays)):
                num = den = 0.0
                for a, per in fc_pts[m]:
                    v = per[str(n)][i]
                    if v is not None:
                        num += v * a; den += a
                vals.append(num / den if den > 0 else None)
            fc[m][str(n)] = vals
    hii = {"dam_inflow": {}, "dam_released": {}, "dam_storage": {}}
    for y in range(2018, 2027):
        for kind, store in hii.items():
            dd_ = get(f"https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam_yearly_graph?data_type={kind}&dam_id={dam['dam_id']}&year={y}")["data"]
            for x in dd_["graph_data"][0]["data"]:
                if x.get("value") is not None:
                    store[x["date"][:10]] = float(x["value"])
            time.sleep(0.25)
    out = {"pts": pts, "era_days": era_days, "era": era, "fdays": fdays, "fc": fc, **hii}
    json.dump(out, open(path, "w"))
    return out


def ridge(X, y, alpha=1.0):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    A = Z.T @ Z + alpha * np.eye(Z.shape[1])
    w = np.linalg.solve(A, Z.T @ (y - y.mean()))
    return lambda Xn: (np.atleast_2d(Xn) - mu) / sd @ w + y.mean()


with db.connect_readonly() as c:
    dams = [dict(r) for r in c.execute("SELECT dam_id, name_th, lat, lon FROM dam WHERE agency='RID' ORDER BY dam_id").fetchall()]
served = json.load(open("/app/src/floodwatch/data/reservoir_models.json"))
served_pass = {m["dam_id"]: {h: ((m.get("op_gain") or {}).get("3" if h <= 3 else "7") or -1e9) >= 10.0 for h in LEADS}
               for m in served.values()}
if ONLY:
    dams = [d for d in dams if d["dam_id"] in ONLY]
print(f"RID dams: {len(dams)}", flush=True)
HS = LEADS
SOURCES = {"bm": ["best_match"], "ec": ["ecmwf_ifs025"], "gfs": ["gfs_seamless"], "icon": ["icon_seamless"], "E3": E3, "E4": MODELS}
PET = 3.5


def hbv_run(P, Smax, beta, k, S0=None, Q0=0.0):
    """Daily soil bucket + linear-reservoir routing; returns routed runoff (mm/day) and the states."""
    S = Smax * 0.5 if S0 is None else S0
    Q = Q0
    out, Ss = np.empty(len(P)), np.empty(len(P))
    for i, p in enumerate(P):
        frac = min(1.0, max(S, 0.0) / Smax)
        peff = p * frac ** beta
        et = PET * min(1.0, max(S, 0.0) / (0.7 * Smax))
        S = min(Smax, max(0.0, S + p - peff - et))
        Q = k * Q + (1 - k) * peff
        out[i], Ss[i] = Q, S
    return out, Ss


results = []
for dam in dams:
    try:
        data = load(dam)
        if not data:
            print(f"{dam['name_th']}: no basin", flush=True); continue
        days = data["era_days"]; pos = {d: i for i, d in enumerate(days)}; n = len(days)
        I = np.full(n, np.nan); REL = np.full(n, np.nan); ST = np.full(n, np.nan)
        for key, arr in (("dam_inflow", I), ("dam_released", REL), ("dam_storage", ST)):
            for d, v in data[key].items():
                if d in pos:
                    arr[pos[d]] = v
        E = np.array(data["era"], float)
        fdays = data["fdays"]; fpos = {d: i for i, d in enumerate(fdays)}
        doy = np.array([dt.date.fromisoformat(d).timetuple().tm_yday for d in days])
        issue = [pos[d] for d in fdays if d in pos and pos[d] + 7 < n and pos[d] >= 40 and np.isfinite(I[pos[d]])
                 and np.isfinite(I[pos[d] - 1]) and np.isfinite(I[pos[d] + 7])]
        if len(issue) < 40:
            print(f"{dam['name_th']}: only {len(issue)} issue days", flush=True); continue
        half = len(issue) // 2
        A_set, B_set = set(issue[:half]), set(issue[half:])
        a_days = sorted({days[t] for t in issue[:half]})
        scale = {}
        for m in MODELS:
            for k_ in [0] + LEADS:
                ok = [d for d in a_days if d in fpos and data["fc"][m][str(k_)][fpos[d]] is not None]
                num = sum(E[pos[d]] for d in ok); den = sum(data["fc"][m][str(k_)][fpos[d]] for d in ok)
                scale[(m, k_)] = (num / den) if den > 0 and len(ok) >= 10 else None

        def frain(m, j, lead):
            d = days[j]
            v = data["fc"][m][str(lead)][fpos[d]] if d in fpos else None
            sc = scale[(m, lead)]
            return np.nan if v is None or sc is None else v * sc

        def mean_of(vals):
            vals = [v for v in vals if np.isfinite(v)]
            return float(np.mean(vals)) if vals else np.nan

        RAIN = {}
        for src, ms in SOURCES.items():
            for t in issue:
                pr = E[: t + 1].copy()
                for j in range(max(0, t - 4), t + 1):
                    v = mean_of([frain(m, j, 0) for m in ms])
                    if np.isfinite(v):
                        pr[j] = v
                F = np.array([mean_of([frain(m, t + k_, k_) for m in ms]) for k_ in LEADS])
                RAIN[(src, t)] = (pr, F)

        # climatology and the 30-day mean
        trn = np.array([d[:4] <= "2024" for d in days])
        clim = {}
        for dy in range(1, 367):
            w = np.isfinite(I) & trn & (np.minimum(np.abs(doy - dy), 366 - np.abs(doy - dy)) <= 7)
            clim[dy] = float(np.nanmean(I[w])) if w.any() else np.nan
        CL = np.array([clim[x] for x in doy])
        def m30(t):
            w = I[max(0, t - 29): t + 1]; w = w[np.isfinite(w)]
            return float(w.mean()) if len(w) else float(I[t])

        tr = [t for t in range(35, n - 8) if days[t][:4] <= "2024" and np.isfinite(I[t]) and np.isfinite(I[t - 1])]
        def xrow(t, pr, F, h, log=False):
            it, it1 = I[t], I[t - 1]
            wet = pr[t - 29: t + 1].sum(); Fh = F[:h].sum(); Fl = F[max(0, h - 2):h].sum()
            sea = [math.sin(2 * math.pi * doy[t] / 365.25), math.cos(2 * math.pi * doy[t] / 365.25)]
            base = [math.log1p(max(it, 0)), math.log1p(max(it1, 0))] if log else [it, it1, math.sqrt(max(it, 0))]
            return base + [pr[t], pr[t - 2:t + 1].sum(), pr[t - 6:t + 1].sum(), wet, Fh, Fl, Fh * wet / 100.0] + sea
        fits = {}
        for h in HS:
            rows = [t for t in tr if np.isfinite(I[t + h])]
            Fe = {t: E[t + 1: t + 8] for t in rows}
            y = np.array([I[t + h] for t in rows])
            fits[("D", h)] = ridge(np.array([xrow(t, E, Fe[t], h) for t in rows]), y)
            fits[("L", h)] = ridge(np.array([xrow(t, E, Fe[t], h, log=True) for t in rows]), np.log1p(np.maximum(y, 0)))
            xk = np.array([I[t] - m30(t) for t in rows]); yk = y - np.array([m30(t) for t in rows])
            fits[("K", h)] = float(np.sum(xk * yk) / max(np.sum(xk ** 2), 1e-9))
            ok = [i for i, t in enumerate(rows) if np.isfinite(CL[t]) and np.isfinite(CL[t + h])]
            xc = np.array([I[rows[i]] - CL[rows[i]] for i in ok]); yc = np.array([y[i] - CL[rows[i] + h] for i in ok])
            fits[("KC", h)] = float(np.sum(xc * yc) / max(np.sum(xc ** 2), 1e-9))
            fits[("KF", h)] = ridge(np.array([[I[t] - m30(t), Fe[t][:h].sum(), Fe[t][max(0, h - 2):h].sum(), E[t - 29:t + 1].sum(),
                                               Fe[t][:h].sum() * E[t - 29:t + 1].sum() / 100.0] for t in rows]), yk)
            # analogs: standardized (inflow, inflow t−1, rain past 7, wetness, forecast 1…h), the change after h days
            Z = np.array([[I[t], I[t - 1], E[t - 6:t + 1].sum(), E[t - 29:t + 1].sum(), Fe[t][:h].sum()] for t in rows])
            fits[("AN", h)] = (Z, Z.mean(0), Z.std(0) + 1e-9, y - np.array([I[t] for t in rows]))
        rr = [t for t in tr if t >= 8]
        XR = np.array([[1.0, I[t - 1], math.sqrt(max(I[t - 1], 0)), E[t], E[t - 1], E[t - 2], E[t - 3], E[t - 7:t - 3].sum()] for t in rr])
        betaR, *_ = np.linalg.lstsq(XR, I[rr], rcond=None)
        # the conceptual model: calibrate on 2018–2024
        cal = np.array([t for t in range(n) if days[t][:4] <= "2024"])
        best = None
        for Smax in (80.0, 150.0, 300.0, 500.0):
            for beta in (1.0, 2.0, 4.0):
                for k in (0.5, 0.75, 0.9, 0.97):
                    q, _ = hbv_run(E[cal], Smax, beta, k)
                    m_ = np.isfinite(I[cal]) & (np.arange(len(cal)) > 60)
                    Xq = np.column_stack([q[m_], np.ones(m_.sum())])
                    ab, *_ = np.linalg.lstsq(Xq, I[cal][m_], rcond=None)
                    err = float(np.mean(np.abs(Xq @ ab - I[cal][m_])))
                    if best is None or err < best[0]:
                        best = (err, Smax, beta, k, ab)
        _, Smax, beta, kH, abH = best
        qE, SE = hbv_run(E, Smax, beta, kH)  # ERA5 pass: states to start each forecast from (t−5)

        def hb_pred(t, pr, F):
            j0 = t - 5
            q, s_ = hbv_run(np.concatenate([pr[j0 + 1: t + 1], F]), Smax, beta, kH, S0=SE[j0], Q0=qE[j0])
            model = abH[0] * q + abH[1]
            e0 = I[t] - model[4]  # index 4 = day t
            return {h: max(0.0, float(model[4 + h] + e0 * kH ** h)) for h in HS}

        def predict(name, t):
            out = {}
            fam, src = (name.split("_") + [None])[:2]
            pr, F = RAIN[(src or "bm", t)]
            for h in HS:
                if src and not np.isfinite(F[:h]).all():
                    out[h] = np.nan; continue
                if fam == "P": v = I[t]
                elif fam == "CL": v = CL[t + h]
                elif fam == "K": M = m30(t); v = M + fits[("K", h)] * (I[t] - M)
                elif fam == "KC": v = CL[t + h] + fits[("KC", h)] * (I[t] - CL[t]) if np.isfinite(CL[t]) and np.isfinite(CL[t + h]) else np.nan
                elif fam == "D": v = float(fits[("D", h)](xrow(t, pr, F, h))[0])
                elif fam == "L": v = float(np.expm1(fits[("L", h)](xrow(t, pr, F, h, log=True))[0]))
                elif fam == "KF":
                    M = m30(t)
                    v = M + float(fits[("KF", h)]([I[t] - M, F[:h].sum(), F[max(0, h - 2):h].sum(), pr[t - 29:t + 1].sum(),
                                                   F[:h].sum() * pr[t - 29:t + 1].sum() / 100.0])[0])
                elif fam == "AN":
                    Z, mu, sd, dy_ = fits[("AN", h)]
                    zq = (np.array([I[t], I[t - 1], pr[t - 6:t + 1].sum(), pr[t - 29:t + 1].sum(), F[:h].sum()]) - mu) / sd
                    dist = np.sqrt((((Z - mu) / sd - zq) ** 2).sum(1)); nn = np.argsort(dist)[:20]
                    w = 1.0 / (dist[nn] + 1e-6); v = I[t] + float(np.sum(w * dy_[nn]) / np.sum(w))
                elif fam == "R":
                    rain = list(pr) + list(F); prev = I[t]
                    for k_ in range(1, h + 1):
                        j = t + k_
                        prev = max(0.0, float(np.array([1.0, prev, math.sqrt(max(prev, 0)), rain[j], rain[j - 1], rain[j - 2], rain[j - 3],
                                                        sum(rain[j - 7:j - 3])]) @ betaR))
                    v = prev
                elif fam == "HB":
                    v = hb_pred(t, pr, F)[h] if np.isfinite(F).all() else np.nan
                    if not np.isfinite(F).all():  # icon at lead 7: run to its last lead only
                        Fc = np.where(np.isfinite(F), F, 0.0); v = hb_pred(t, pr, Fc)[h] if h <= 6 else np.nan
                out[h] = max(0.0, v) if np.isfinite(v) else np.nan
            return out

        names = ["P", "CL", "K", "KC", "R_bm", "R_E4", "AN_E4"] + [f"{f}_{r}" for f in ("D", "L", "KF", "HB") for r in SOURCES]
        preds = {nm: {t: predict(nm, t) for t in issue} for nm in names}
        for nm, members in (("BL1", ["D_E4", "P"]), ("BL2", ["D_E4", "L_E4", "KF_E4"]), ("BL3", ["D_E4", "HB_E4"])):
            preds[nm] = {t: {h: float(np.mean([preds[m][t][h] for m in members])) for h in HS} for t in issue}
            names.append(nm)
        row = {"dam_id": dam["dam_id"], "dam": dam["name_th"], "hbv": {"Smax": Smax, "beta": beta, "k": kH, "fit_mae": round(best[0], 3)},
               "A": {}, "B": {}, "served": {}}
        for h in HS:
            for half_, S_ in (("A", A_set), ("B", B_set)):
                ts = [t for t in issue if t in S_]
                row[half_][h] = {nm: (float(np.mean([abs(preds[nm][t][h] - I[t + h]) for t in ts]))
                                      if all(np.isfinite(preds[nm][t][h]) for t in ts) else None) for nm in names}
            row["served"][h] = "R_bm" if served_pass.get(dam["dam_id"], {}).get(h, False) else "P"
        # 7-day storage error for a choice {h: name}, actual releases as the plan, monthly loss (2018–2024)
        res_by_m = {}
        for t in range(1, n - 1):
            if trn[t] and np.isfinite(ST[t]) and np.isfinite(ST[t + 1]) and np.isfinite(I[t]) and np.isfinite(REL[t]):
                res_by_m.setdefault(int(days[t][5:7]), []).append(ST[t + 1] - ST[t] - (I[t] - REL[t]))
        loss = {mo: float(np.median(v)) for mo, v in res_by_m.items() if len(v) >= 30}
        def storage_err(choice):
            errs = []
            for t in sorted(B_set):
                if not (np.isfinite(ST[t]) and np.isfinite(ST[t + 7]) and all(np.isfinite(REL[t + k_]) for k_ in range(7))):
                    continue
                infl = [I[t]] + [preds[choice[k_]][t][k_] for k_ in range(1, 7)]
                if not all(np.isfinite(infl)):
                    continue
                errs.append(abs(ST[t] + sum(infl[k_] - REL[t + k_] + loss.get(int(days[t + k_][5:7]), 0.0) for k_ in range(7)) - ST[t + 7]))
            return float(np.mean(errs)) if errs else None
        row["storage_err"] = storage_err
        row["preds"], row["issue"] = None, None
        results.append(row)
        b3, b7 = row["B"][3], row["B"][7]
        top = lambda b: sorted(((v, k_) for k_, v in b.items() if v is not None and k_ != "P"))[:3]
        print(f"{dam['name_th']:18s} B n {len(B_set):3d} · P 3d {b3['P']:.3f} 7d {b7['P']:.3f} · best 3d " +
              ", ".join(f"{k_} {100 * (v / b3['P'] - 1):+.0f}%" for v, k_ in top(b3)) + " · best 7d " +
              ", ".join(f"{k_} {100 * (v / b7['P'] - 1):+.0f}%" for v, k_ in top(b7)) +
              f" · HBV fit MAE {best[0]:.2f} (Smax {Smax:.0f}, β {beta:.0f}, k {kH})", flush=True)
    except Exception as e:
        import traceback
        print(f"{dam['name_th']}: failed ({type(e).__name__}: {str(e)[:160]})", flush=True)
        traceback.print_exc()

# ---------------- the two samples, the choices, the gate ----------------
order = sorted(results, key=lambda r: r["dam_id"])
samples = {1: order[0::2], 2: order[1::2]}
names = list(order[0]["B"][1].keys()) if order else []
def tot(rows, half_, h, nm):
    vals = [r[half_][h][nm] for r in rows]
    return None if any(v is None for v in vals) else sum(vals)
glob = {}
for s, rows in samples.items():  # G: chosen on the other sample's first half
    other = samples[2 if s == 1 else 1]
    for h in HS:
        cand = [(tot(other, "A", h, nm), nm) for nm in names if nm != "P" and other and tot(other, "A", h, nm) is not None]
        glob[(s, h)] = min(cand)[1] if cand else "P"
print("\n=== E-7D-IN: inflow error on the second half of the window (scored) vs persistence")
summary = {}
for s, rows in samples.items():
    if not rows:
        continue
    for h in HS:
        P = sum(r["B"][h]["P"] for r in rows)
        def pick_c(r):
            a = r["A"][h]
            c_ = [(v, k_) for k_, v in a.items() if v is not None and k_ != "P"]
            b = min(c_)[1] if c_ else "P"
            return b if a[b] < (1 - GATE) * a["P"] else "P"
        C = sum(r["B"][h][pick_c(r)] for r in rows)
        Gn = glob[(s, h)]; G_ = sum((r["B"][h][Gn] if r["B"][h][Gn] is not None else r["B"][h]["P"]) for r in rows)
        S_ = sum(r["B"][h][r["served"][h]] for r in rows)
        wC = sum(1 for r in rows if r["B"][h][pick_c(r)] > r["B"][h]["P"])
        wG = sum(1 for r in rows if (r["B"][h][Gn] or 0) > r["B"][h]["P"])
        wS = sum(1 for r in rows if r["B"][h][r["served"][h]] > r["B"][h]["P"])
        alone = sorted(((tot(rows, "B", h, nm) / P - 1, nm) for nm in names if nm != "P" and tot(rows, "B", h, nm) is not None))[:6]
        summary[(s, h)] = {"P": P, "C": C, "G": G_, "S": S_, "wC": wC, "wG": wG, "wS": wS, "G_name": Gn}
        print(f"sample {s} · {h} d · dams {len(rows):2d} · C {100 * (C / P - 1):+6.1f} % (worse {wC:2d}) · G={Gn} {100 * (G_ / P - 1):+6.1f} % (worse {wG:2d})"
              f" · served now {100 * (S_ / P - 1):+6.1f} % (worse {wS:2d}) · best alone: " + ", ".join(f"{nm} {100 * v:+.0f}" for v, nm in alone), flush=True)
    st = {"P": [], "C": [], "G": [], "S": []}
    for r in rows:
        pc = {}
        for h in HS:
            a = r["A"][h]; c_ = [(v, k_) for k_, v in a.items() if v is not None and k_ != "P"]
            b = min(c_)[1] if c_ else "P"; pc[h] = b if a[b] < (1 - GATE) * a["P"] else "P"
        vals = {"P": r["storage_err"]({h: "P" for h in HS}), "C": r["storage_err"](pc),
                "G": r["storage_err"]({h: (glob[(s, h)] if r["B"][h][glob[(s, h)]] is not None else "P") for h in HS}),
                "S": r["storage_err"](r["served"])}
        if all(v is not None for v in vals.values()):
            for k_, v in vals.items():
                st[k_].append(v)
    if st["P"]:
        sp = sum(st["P"])
        print(f"sample {s} · 7-day storage error (actual releases as the plan, loss term) · dams {len(st['P'])} · "
              + " · ".join(f"{k_} {100 * (sum(v) / sp - 1):+.1f} %" for k_, v in st.items() if k_ != "P") + f" vs persistence ({sp / len(st['P']):.2f} ล้าน ลบ.ม. mean)")
for choice in ("C", "G"):
    ok = all(summary[(s, h)][choice] < summary[(s, h)]["P"] and summary[(s, h)][choice] < summary[(s, h)]["S"]
             and summary[(s, h)]["w" + choice] <= summary[(s, h)]["wS"] for s in samples for h in (3, 7) if (s, h) in summary)
    print(f"GATE {choice} (better than persistence and served-now at 3 d and 7 d in both samples, no more dams worse): {'PASS' if ok else 'FAIL'}")
print("PER_DAM_JSON", json.dumps({r["dam_id"]: {"dam": r["dam"], "hbv": r["hbv"], "served": r["served"],
                                                "A": {h: {k_: (None if v is None else round(v, 4)) for k_, v in r["A"][h].items()} for h in HS},
                                                "B": {h: {k_: (None if v is None else round(v, 4)) for k_, v in r["B"][h].items()} for h in HS}}
                                  for r in results}, ensure_ascii=False))
