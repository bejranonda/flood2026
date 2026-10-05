"""E-7D-IN, the build: fit the chosen inflow family per dam and horizon exactly as tested (2018–2024, ERA5 as every rain
input) and export what production needs — ridge parameters, the per-model and per-lead rain scaling learned on the first
half of the forecast window, the choice per horizon (the family where it beat persistence by ≥ 10 % on the first half,
persistence elsewhere) and the scored second-half errors and error quantiles (the band). Reads the cache written by
research/2026-10-05_e7d_inflow.py; no new requests.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$PWD/data:/app/data:ro" \
       -v "$CACHE:/cache" worker python - FAMILY < research/2026-10-05_e7d_inflow_build.py   (FAMILY e.g. D_E4, L_E3, KF_E4)"""
import datetime as dt, json, math, os, sys
import numpy as np
from floodwatch import db

FAM = sys.argv[1] if len(sys.argv) > 1 else "D_E4"
fam, src = FAM.split("_")
CACHE = "/cache/e7d_in"
MODELS = ["best_match", "ecmwf_ifs025", "gfs_seamless", "icon_seamless"]
SOURCES = {"bm": ["best_match"], "ec": ["ecmwf_ifs025"], "gfs": ["gfs_seamless"], "icon": ["icon_seamless"], "E3": MODELS[:3], "E4": MODELS}
LEADS = list(range(1, 8))
GATE = 0.10


def ridge_params(X, y, alpha=1.0):
    X, y = np.asarray(X, float), np.asarray(y, float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return {"mu": mu.tolist(), "sd": sd.tolist(), "w": w.tolist(), "ymean": float(y.mean())}


def apply(p, x):
    return float(((np.asarray(x, float) - np.array(p["mu"])) / np.array(p["sd"])) @ np.array(p["w"]) + p["ymean"])


with db.connect_readonly() as c:
    dams = [dict(r) for r in c.execute("SELECT dam_id, name_th FROM dam WHERE agency='RID' ORDER BY dam_id").fetchall()]
# family R keeps what is served now (the Q58 model's dams and horizons) and only changes its rain — the change that passed
# the two-sample gate (research/2026-10-05_e7d_inflow_narrow.log, "S·rain(E4)")
served = json.load(open("/app/src/floodwatch/data/reservoir_models.json"))
served_pass = {m["dam_id"]: {h: ((m.get("op_gain") or {}).get("3" if h <= 3 else "7") or -1e9) >= 10.0 for h in LEADS} for m in served.values()}
build = {}
for dam in dams:
    path = f"{CACHE}/dam_{dam['dam_id']}.json"
    if not os.path.exists(path):
        continue
    data = json.load(open(path))
    days = data["era_days"]; pos = {d: i for i, d in enumerate(days)}; n = len(days)
    I = np.full(n, np.nan); REL = np.full(n, np.nan); ST = np.full(n, np.nan)
    for key, arr in (("dam_inflow", I), ("dam_released", REL), ("dam_storage", ST)):
        for d, v in data[key].items():
            if d in pos:
                arr[pos[d]] = v
    res_by_m = {}  # the balance residual by month, 2018–2024 (the loss term the storage test used)
    for t in range(1, n - 1):
        if days[t][:4] <= "2024" and np.isfinite(ST[t]) and np.isfinite(ST[t + 1]) and np.isfinite(I[t]) and np.isfinite(REL[t]):
            res_by_m.setdefault(int(days[t][5:7]), []).append(ST[t + 1] - ST[t] - (I[t] - REL[t]))
    loss = {str(mo): round(float(np.median(v)), 3) for mo, v in res_by_m.items() if len(v) >= 30}
    E = np.array(data["era"], float)
    fdays = data["fdays"]; fpos = {d: i for i, d in enumerate(fdays)}
    doy = np.array([dt.date.fromisoformat(d).timetuple().tm_yday for d in days])
    issue = [pos[d] for d in fdays if d in pos and pos[d] + 7 < n and pos[d] >= 40 and np.isfinite(I[pos[d]])
             and np.isfinite(I[pos[d] - 1]) and np.isfinite(I[pos[d] + 7])]
    if len(issue) < 40:
        continue
    half = len(issue) // 2
    A, B = issue[:half], issue[half:]
    a_days = sorted({days[t] for t in A})
    scale = {}
    for m in MODELS:
        for k in [0] + LEADS:
            ok = [d for d in a_days if d in fpos and data["fc"][m][str(k)][fpos[d]] is not None]
            num = sum(E[pos[d]] for d in ok); den = sum(data["fc"][m][str(k)][fpos[d]] for d in ok)
            scale[(m, k)] = (num / den) if den > 0 and len(ok) >= 10 else None

    def frain(m, j, lead):
        d = days[j]
        v = data["fc"][m][str(lead)][fpos[d]] if d in fpos else None
        sc = scale[(m, lead)]
        return np.nan if v is None or sc is None else v * sc

    def mean_of(vals):
        vals = [v for v in vals if np.isfinite(v)]
        return float(np.mean(vals)) if vals else np.nan

    def known(t, ms):
        pr = E[: t + 1].copy()
        for j in range(max(0, t - 4), t + 1):
            v = mean_of([frain(m, j, 0) for m in ms])
            if np.isfinite(v):
                pr[j] = v
        return pr, np.array([mean_of([frain(m, t + k, k) for m in ms]) for k in LEADS])

    def m30(t):
        w = I[max(0, t - 29): t + 1]; w = w[np.isfinite(w)]
        return float(w.mean()) if len(w) else float(I[t])

    def xrow(t, pr, F, h, log=False):  # identical to research/2026-10-05_e7d_inflow.py
        it, it1 = I[t], I[t - 1]
        wet = pr[t - 29: t + 1].sum(); Fh = F[:h].sum(); Fl = F[max(0, h - 2):h].sum()
        sea = [math.sin(2 * math.pi * doy[t] / 365.25), math.cos(2 * math.pi * doy[t] / 365.25)]
        base = [math.log1p(max(it, 0)), math.log1p(max(it1, 0))] if log else [it, it1, math.sqrt(max(it, 0))]
        return base + [pr[t], pr[t - 2:t + 1].sum(), pr[t - 6:t + 1].sum(), wet, Fh, Fl, Fh * wet / 100.0] + sea

    def kfrow(t, pr, F, h):
        M = m30(t)
        return [I[t] - M, F[:h].sum(), F[max(0, h - 2):h].sum(), pr[t - 29:t + 1].sum(), F[:h].sum() * pr[t - 29:t + 1].sum() / 100.0]

    tr = [t for t in range(35, n - 8) if days[t][:4] <= "2024" and np.isfinite(I[t]) and np.isfinite(I[t - 1])]
    if fam == "R":
        if dam["dam_id"] not in served_pass:
            continue
        rr = [t for t in tr if t >= 8]
        XR = np.array([[1.0, I[t - 1], math.sqrt(max(I[t - 1], 0)), E[t], E[t - 1], E[t - 2], E[t - 3], E[t - 7:t - 3].sum()] for t in rr])
        betaR = [float(b) for b in np.linalg.lstsq(XR, I[rr], rcond=None)[0]]
    out = {"dam_id": dam["dam_id"], "name_th": dam["name_th"], "family": FAM, "models": SOURCES[src],
           "scale": {m: {str(k): (None if scale[(m, k)] is None else round(scale[(m, k)], 4)) for k in [0] + LEADS} for m in SOURCES[src]},
           "horizons": {}, "test_from": days[B[0]], "test_to": days[B[-1]], "test_days": len(B), "choose_days": len(A),
           "points": [[round(p[0][0], 4), round(p[0][1], 4), round(p[1], 1)] for p in data["pts"]], "loss_by_month": loss}
    for h in LEADS:
        rows = [t for t in tr if np.isfinite(I[t + h])]
        Fe = {t: E[t + 1: t + 8] for t in rows}
        y = np.array([I[t + h] for t in rows])
        if fam == "D":
            par = ridge_params([xrow(t, E, Fe[t], h) for t in rows], y)
        elif fam == "L":
            par = ridge_params([xrow(t, E, Fe[t], h, log=True) for t in rows], np.log1p(np.maximum(y, 0)))
        elif fam == "KF":
            par = ridge_params([kfrow(t, E, Fe[t], h) for t in rows], y - np.array([m30(t) for t in rows]))
        elif fam == "R":
            par = {"beta": [round(b, 6) for b in betaR]}
        else:
            raise SystemExit(f"family {fam} has no build (only D, L, KF)")

        def pred(t):
            pr, F = known(t, SOURCES[src])
            if not np.isfinite(F[:h]).all():
                return np.nan
            if fam == "R":
                rain, prev = list(pr) + list(F), I[t]
                for k in range(1, h + 1):
                    j = t + k
                    prev = max(0.0, float(np.array([1.0, prev, math.sqrt(max(prev, 0)), rain[j], rain[j - 1], rain[j - 2], rain[j - 3],
                                                    sum(rain[j - 7:j - 3])]) @ np.array(par["beta"])))
                v = prev
            elif fam == "D":
                v = apply(par, xrow(t, pr, F, h))
            elif fam == "L":
                v = float(np.expm1(apply(par, xrow(t, pr, F, h, log=True))))
            else:
                v = m30(t) + apply(par, kfrow(t, pr, F, h))
            return max(0.0, v)
        eA = [abs(pred(t) - I[t + h]) for t in A]; pA = [abs(I[t] - I[t + h]) for t in A]
        eB = [I[t + h] - pred(t) for t in B]; pB = [I[t + h] - I[t] for t in B]  # observed − predicted: mid + band = range
        if not (np.isfinite(eA).all() and np.isfinite(eB).all()):
            out["horizons"][str(h)] = {"use": "persistence", "why": "no forecast at this lead"}
            continue
        use = (FAM if served_pass[dam["dam_id"]][h] else "persistence") if fam == "R" else \
            (FAM if np.mean(eA) < (1 - GATE) * np.mean(pA) else "persistence")
        out["horizons"][str(h)] = {"use": use, "params": par, "mae_choose": [round(float(np.mean(eA)), 3), round(float(np.mean(pA)), 3)],
                                   "mae_test": [round(float(np.mean(np.abs(eB))), 3), round(float(np.mean(np.abs(pB))), 3)],
                                   "band_model": [round(float(np.quantile(eB, .1)), 3), round(float(np.quantile(eB, .9)), 3)],
                                   "band_persist": [round(float(np.quantile(pB, .1)), 3), round(float(np.quantile(pB, .9)), 3)]}
    build[dam["dam_id"]] = out
    used = [h for h, v in out["horizons"].items() if v["use"] != "persistence"]
    print(f"{dam['name_th']:18s} {FAM} at days {','.join(used) or '–'}" + "".join(
        f" · {h}d test {v['mae_test'][0]:.2f} vs {v['mae_test'][1]:.2f}" for h, v in out["horizons"].items() if h in ("3", "7") and "mae_test" in v), flush=True)
print("BUILD_JSON", json.dumps(build, ensure_ascii=False))
