"""E-7D-IN-LONG, the build: what passed the gate, fitted exactly as tested (owner 2026-10-06: "best performance / less
errors at the end"; "Check, test and validate before releasing").
Reads the per-dam errors of research/2026-10-06_e7d_inflow_long.log and the strategy that passed
(research/2026-10-06_e7d_inflow_long_strategies.log), applies the same rule per dam and horizon on the 2025 choosing
window, and fits only the chosen family and rain source on 2018–2024 (ERA5 as every rain input). Exports per dam:
the family per horizon ("D_E3", "R_bm", … or persistence), its parameters, the per-model and per-lead rain scales learned on
2025, the 2026 scored errors (model vs persistence) and bands as quantiles of (observed − predicted) on 2026, the monthly
loss term and the catchment points — src/floodwatch/data/reservoir_inflow7.json. No requests: the caches only.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$PWD/research:/research:ro" \
       -v "$CACHE:/cache" worker python - STRATEGY < research/2026-10-06_e7d_inflow_long_build.py   (STRATEGY: Ce, C, F:D_E3, S·rain…)"""
import datetime as dt, json, math, os, sys
import numpy as np

STRATEGY = sys.argv[1] if len(sys.argv) > 1 else "Ce"
GATE = 0.10
MODELS = ["best_match", "ecmwf_ifs025", "gfs_seamless"]
SOURCES = {"bm": ["best_match"], "ec": ["ecmwf_ifs025"], "gfs": ["gfs_seamless"], "E3": MODELS}
LEADS = list(range(1, 8))
SERVABLE = lambda k: k == "P" or k.split("_")[0] in ("R", "D", "L", "KF")
log = open("/research/2026-10-06_e7d_inflow_long.log").read().split("\n")
PER = json.loads(next(l for l in log if l.startswith("PER_DAM_JSON "))[len("PER_DAM_JSON "):])


def choose(r, h):
    a = r["A"][h]
    if STRATEGY == "S+KF_ec@3":  # the change that passed: KF_ec on days 3–7 where persistence is served (…_long_narrow.log)
        ok = int(h) >= 3 and r["served"][h] == "P" and a.get("KF_ec") is not None and a["KF_ec"] < (1 - GATE) * a["P"]
        return "KF_ec" if ok else "KEEP"
    if STRATEGY in ("C", "Ce"):
        c = [(v, k) for k, v in a.items() if v is not None and k != "P" and (STRATEGY == "C" or SERVABLE(k))]
        b = min(c)[1] if c else "P"
        return b if a[b] < (1 - GATE) * a["P"] else "P"
    if STRATEGY.startswith("F:"):
        f = STRATEGY[2:]
        return f if a.get(f) is not None and a[f] < (1 - GATE) * a["P"] else "P"
    if STRATEGY.startswith("S"):  # the served dams and horizons, the rain named after the dot
        return r["served"][h]
    raise SystemExit(f"unknown strategy {STRATEGY}")


def ridge_params(X, y, alpha=1.0):
    X, y = np.asarray(X, float), np.asarray(y, float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return {"mu": mu.tolist(), "sd": sd.tolist(), "w": w.tolist(), "ymean": float(y.mean())}


def apply(p, x):
    return float(((np.asarray(x, float) - np.array(p["mu"])) / np.array(p["sd"])) @ np.array(p["w"]) + p["ymean"])


build = {}
for dam_id, r in PER.items():
    if not all(SERVABLE(choose(r, str(h))) or choose(r, str(h)) == "KEEP" for h in LEADS):
        print(f"{r['dam']}: a chosen candidate cannot run in production — skipped (persistence)", flush=True)
        continue
    chosen = {str(h): choose(r, str(h)) for h in LEADS}
    if all(v in ("P", "KEEP") for v in chosen.values()):
        continue
    data = json.load(open(f"/cache/e7d_in/dam_{dam_id}.json"))
    lg = json.load(open(f"/cache/e7d_in_long/dam_{dam_id}.json"))
    days = data["era_days"]; pos = {d: i for i, d in enumerate(days)}; n = len(days)
    I = np.full(n, np.nan); REL = np.full(n, np.nan); ST = np.full(n, np.nan)
    for key, arr in (("dam_inflow", I), ("dam_released", REL), ("dam_storage", ST)):
        for d, v in data[key].items():
            if d in pos:
                arr[pos[d]] = v
    E = np.array(data["era"], float)
    doy = np.array([dt.date.fromisoformat(d).timetuple().tm_yday for d in days])
    fdays = sorted(set(data["fdays"]) | set(lg["days"])); fpos = {d: i for i, d in enumerate(fdays)}
    fc = {m: {} for m in MODELS}
    for m in MODELS:
        for k in ["0"] + [str(x) for x in LEADS]:
            col = [None] * len(fdays)
            for d, v in zip(data["fdays"], data["fc"][m][k]):
                col[fpos[d]] = v
            for d, v in zip(lg["days"], lg["fc"][m][k]):
                if v is not None:
                    col[fpos[d]] = v
            fc[m][k] = col
    issue = [pos[d] for d in fdays if d in pos and pos[d] + 7 < n and pos[d] >= 40 and np.isfinite(I[pos[d]]) and np.isfinite(I[pos[d] - 1])
             and np.isfinite(I[pos[d] + 7])]
    last25 = max(lg["days"])
    A = [t for t in issue if days[t][:4] == "2025" and days[t + 7] <= last25 and days[t - 4] >= lg["days"][0]]
    B = [t for t in issue if days[t][:4] == "2026" and days[t - 4] >= "2026-07-06"]
    a_days = sorted({days[t + k] for t in A for k in range(0, 8)})
    scale = {}
    for m in MODELS:
        for k in [0] + LEADS:
            ok = [d for d in a_days if d in fpos and fc[m][str(k)][fpos[d]] is not None]
            num = sum(E[pos[d]] for d in ok); den = sum(fc[m][str(k)][fpos[d]] for d in ok)
            scale[(m, k)] = (num / den) if den > 0 and len(ok) >= 10 else None

    def frain(m, j, lead):
        d = days[j]
        v = fc[m][str(lead)][fpos[d]] if d in fpos else None
        sc = scale[(m, lead)]
        return np.nan if v is None or sc is None else v * sc

    def known(t, ms):
        pr = E[: t + 1].copy()
        for j in range(max(0, t - 4), t + 1):
            vals = [x for x in (frain(m, j, 0) for m in ms) if np.isfinite(x)]
            if vals:
                pr[j] = float(np.mean(vals))
        F = []
        for k in LEADS:
            vals = [x for x in (frain(m, t + k, k) for m in ms) if np.isfinite(x)]
            F.append(float(np.mean(vals)) if vals else np.nan)
        return pr, np.array(F)

    def m30(t):
        w = I[max(0, t - 29): t + 1]; w = w[np.isfinite(w)]
        return float(w.mean()) if len(w) else float(I[t])

    def xrow(t, pr, F, h, log=False):  # identical to research/2026-10-05_e7d_inflow.py and reservoir.features7
        it, it1 = I[t], I[t - 1]
        wet = pr[t - 29: t + 1].sum(); Fh = F[:h].sum(); Fl = F[max(0, h - 2):h].sum()
        sea = [math.sin(2 * math.pi * doy[t] / 365.25), math.cos(2 * math.pi * doy[t] / 365.25)]
        base = [math.log1p(max(it, 0)), math.log1p(max(it1, 0))] if log else [it, it1, math.sqrt(max(it, 0))]
        return base + [pr[t], pr[t - 2:t + 1].sum(), pr[t - 6:t + 1].sum(), wet, Fh, Fl, Fh * wet / 100.0] + sea

    def kfrow(t, pr, F, h):
        M = m30(t)
        return [I[t] - M, F[:h].sum(), F[max(0, h - 2):h].sum(), pr[t - 29:t + 1].sum(), F[:h].sum() * pr[t - 29:t + 1].sum() / 100.0]

    tr = [t for t in range(35, n - 8) if days[t][:4] <= "2024" and np.isfinite(I[t]) and np.isfinite(I[t - 1])]
    rr = [t for t in tr if t >= 8]
    XR = np.array([[1.0, I[t - 1], math.sqrt(max(I[t - 1], 0)), E[t], E[t - 1], E[t - 2], E[t - 3], E[t - 7:t - 3].sum()] for t in rr])
    betaR = [round(float(b), 6) for b in np.linalg.lstsq(XR, I[rr], rcond=None)[0]]
    res_by_m = {}
    for t in range(1, n - 1):
        if days[t][:4] <= "2024" and np.isfinite(ST[t]) and np.isfinite(ST[t + 1]) and np.isfinite(I[t]) and np.isfinite(REL[t]):
            res_by_m.setdefault(int(days[t][5:7]), []).append(ST[t + 1] - ST[t] - (I[t] - REL[t]))
    loss = {str(mo): round(float(np.median(v)), 3) for mo, v in res_by_m.items() if len(v) >= 30}
    out = {"dam_id": int(dam_id), "name_th": r["dam"], "family": next((v for v in chosen.values() if v not in ("P", "KEEP")), "P"), "models": MODELS,
           "scale": {m: {str(k): (None if scale[(m, k)] is None else round(scale[(m, k)], 4)) for k in [0] + LEADS} for m in MODELS},
           "horizons": {}, "test_from": days[B[0]], "test_to": days[B[-1]], "test_days": len(B), "choose_days": len(A),
           "points": [[round(p[0][0], 4), round(p[0][1], 4), round(p[1], 1)] for p in data["pts"]], "loss_by_month": loss,
           "strategy": STRATEGY, "source": "research/2026-10-06_e7d_inflow_long_build.py (E-7D-IN-LONG)"}
    out["persist_bands"] = {}
    for h in LEADS:
        pBall = [I[t + h] - I[t] for t in B]
        out["persist_bands"][str(h)] = [round(float(np.quantile(pBall, .1)), 3), round(float(np.quantile(pBall, .9)), 3)]
    for h in LEADS:
        name = chosen[str(h)]
        if name == "KEEP":
            continue
        if name == "P":
            pB = [I[t + h] - I[t] for t in B]
            out["horizons"][str(h)] = {"use": "persistence", "family": None,
                                       "band_persist": [round(float(np.quantile(pB, .1)), 3), round(float(np.quantile(pB, .9)), 3)]}
            continue
        fam, src = name.split("_")
        rows = [t for t in tr if np.isfinite(I[t + h])]
        Fe = {t: E[t + 1: t + 8] for t in rows}
        y = np.array([I[t + h] for t in rows])
        if fam == "D":
            par = ridge_params([xrow(t, E, Fe[t], h) for t in rows], y)
        elif fam == "L":
            par = ridge_params([xrow(t, E, Fe[t], h, log=True) for t in rows], np.log1p(np.maximum(y, 0)))
        elif fam == "KF":
            par = ridge_params([kfrow(t, E, Fe[t], h) for t in rows], y - np.array([m30(t) for t in rows]))
        else:
            par = {"beta": betaR}

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
                return prev
            if fam == "D":
                return max(0.0, apply(par, xrow(t, pr, F, h)))
            if fam == "L":
                return max(0.0, float(np.expm1(apply(par, xrow(t, pr, F, h, log=True)))))
            return max(0.0, m30(t) + apply(par, kfrow(t, pr, F, h)))
        eB = [I[t + h] - pred(t) for t in B]; pB = [I[t + h] - I[t] for t in B]
        ok = [e for e in eB if np.isfinite(e)]
        out["horizons"][str(h)] = {"use": name, "family": name, "params": par,
                                   "mae_test": [round(float(np.mean(np.abs(ok))), 3), round(float(np.mean(np.abs(pB))), 3)],
                                   "band_model": [round(float(np.quantile(ok, .1)), 3), round(float(np.quantile(ok, .9)), 3)],
                                   "band_persist": [round(float(np.quantile(pB, .1)), 3), round(float(np.quantile(pB, .9)), 3)]}
    build[dam_id] = out
    print(f"{r['dam']:18s} " + " ".join(f"{h}:{chosen[str(h)]}" for h in LEADS) +
          "".join(f" · {h}d {v['mae_test'][0]:.2f} vs {v['mae_test'][1]:.2f}" for h, v in out["horizons"].items() if h in ("3", "7") and "mae_test" in v), flush=True)
print("BUILD_JSON", json.dumps(build, ensure_ascii=False))
