"""Experiment 2026-09-27 (results: research/2026-09-27_forecast_48h.md). Run: docker compose run --rm --no-deps -v $PWD/research/validation:/exp worker python /exp/exp_48h_upstream_2026-09-27.py
Can upstream information improve our 24/48 h forecast? Honest split: fit on data before the test window,
score on the last 45 days (the production backtest window). Compares: persistence, production (forecast.evaluate),
and a ridge regression with tide + own trend + upstream (C.13 dam discharge, upstream gauges)."""
import datetime as dt
import numpy as np
from floodwatch import db, forecast

TEST_H = forecast.EVAL_HOURS
UP = {  # target -> upstream gauges (level) used as features; C.13 discharge is always offered
    "CPY011": ["CPY008", "CPY007"],
    "CPY014": ["CPY011", "CPY012"],
    "C.12":   ["CPY014", "CPY011"],
    "CPY015": ["CPY014", "C.12"],
    "BKK021": ["CPY014"],
}

def series(c, code, col="level_msl"):
    rows = c.execute(f"SELECT obs_time, {col} AS v FROM observation WHERE code=%s AND quality_flag='ok' AND {col} IS NOT NULL "
                     "AND obs_time > now() - interval '370 days' ORDER BY obs_time", (code,)).fetchall()
    return [r["obs_time"] for r in rows], [float(r["v"]) for r in rows]

def on_grid(t_ref, times, vals):
    t, y = forecast.hourly_grid(times, vals)
    m = {int(a): b for a, b in zip(t, y)}
    return np.array([m.get(int(a), np.nan) for a in t_ref])

def lagdiff(x, k):
    out = np.full_like(x, np.nan); out[k:] = x[k:] - x[:-k]; return out

def ridge(X, y, lam=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return lambda Xn: ((Xn - mu) / sd) @ w + y.mean()

with db.connect() as c:
    qt, qv = series(c, "C.13", "discharge")
    for tgt, ups in UP.items():
        tt, yy = series(c, tgt)
        t, y = forecast.hourly_grid(tt, yy)
        n = len(y)
        if n < TEST_H + 24 * 60:
            print(tgt, "too short", n); continue
        split = n - TEST_H
        prod = forecast.evaluate(t, y)  # production: best of persistence/tide/tide_trend on the last 45 days
        eta = forecast.fit_tide(t[:split], y[:split])  # tide fitted on training data only
        q = on_grid(t, qt, qv)
        upl = [on_grid(t, *series(c, u)) for u in ups]
        ybar = forecast.trailing_mean(y, 25)
        res = {}
        for h in (24, 48):
            feats = {"tide": (eta(t + h) - eta(t)) if eta else np.zeros(n),
                     "d6": lagdiff(y, 6), "d24": lagdiff(y, 24), "dev": y - ybar,
                     "q": q, "dq24": lagdiff(q, 24), "dq48": lagdiff(q, 48)}
            for u, x in zip(ups, upl):
                feats[f"{u}_d24"] = lagdiff(x, 24); feats[f"{u}_d48"] = lagdiff(x, 48)
            X = np.column_stack(list(feats.values()))
            target = np.full(n, np.nan); target[:-h] = y[h:] - y[:-h]
            ok = np.isfinite(X).all(1) & np.isfinite(target)
            tr = ok & (np.arange(n) < split - h)      # training rows never see the test window
            te = ok & (np.arange(n) >= split)
            if tr.sum() < 500 or te.sum() < 100:
                res[h] = None; continue
            f = ridge(X[tr], target[tr])
            err_new = target[te] - f(X[te]); err_per = target[te]
            # same rows without upstream features (to isolate what upstream adds)
            own = [i for i, k in enumerate(feats) if k in ("tide", "d6", "d24", "dev")]
            f2 = ridge(X[tr][:, own], target[tr])
            err_own = target[te] - f2(X[te][:, own])
            rm = lambda e: float(np.sqrt(np.mean(e ** 2)))
            p = prod.get(h)
            res[h] = dict(n=int(te.sum()), persist=rm(err_per), prod=(p["method"], p["rmse"][p["method"]]) if p else None,
                          own=rm(err_own), upstream=rm(err_new),
                          p90_upstream=float(np.quantile(np.abs(err_new), 0.9)))
        print(f"== {tgt} (upstream: {', '.join(ups)} + C.13 Q)")
        for h, r in res.items():
            if not r: print(f"  +{h}h: not enough rows"); continue
            pm, pr = r["prod"] if r["prod"] else ("-", float('nan'))
            sk = lambda v: 1 - v / r["persist"]
            print(f"  +{h}h n={r['n']}: persistence {r['persist']*100:.1f} cm | production[{pm}] {pr*100:.1f} cm (skill {sk(pr):+.2f}) | "
                  f"own-ridge {r['own']*100:.1f} cm ({sk(r['own']):+.2f}) | +upstream {r['upstream']*100:.1f} cm ({sk(r['upstream']):+.2f}) | 90% |err| {r['p90_upstream']*100:.0f} cm")
