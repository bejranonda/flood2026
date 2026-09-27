"""Experiment 2026-09-27 (results: research/2026-09-27_forecast_48h.md §4). Run:
    docker compose run --rm --no-deps -v $PWD/research/validation:/exp worker python /exp/exp_48h_neighbours_2026-09-27.py
45 days, test on them). Designs: own AR · network STAR (upstream gauges + C.13 dam release) · proximity STAR (3 nearest
long-record gauges by distance, any direction) · non-parametric k-NN analogue AR on the network features."""
import numpy as np
from floodwatch import db, forecast

TEST_H = forecast.EVAL_HOURS
UP = {"CPY011": ["CPY008", "CPY007"], "CPY014": ["CPY011", "CPY012"], "C.12": ["CPY014", "CPY011"],
      "CPY015": ["CPY014", "C.12"], "BKK021": ["CPY014"]}

def series(c, code, col="level_msl"):
    rows = c.execute(f"SELECT obs_time, {col} AS v FROM observation WHERE code=%s AND quality_flag='ok' AND {col} IS NOT NULL "
                     "AND obs_time > now() - interval '370 days' ORDER BY obs_time", (code,)).fetchall()
    return [r["obs_time"] for r in rows], [float(r["v"]) for r in rows]
def on_grid(t_ref, times, vals):
    t, y = forecast.hourly_grid(times, vals); m = {int(a): b for a, b in zip(t, y)}
    return np.array([m.get(int(a), np.nan) for a in t_ref])
def lagdiff(x, k):
    o = np.full_like(x, np.nan); o[k:] = x[k:] - x[:-k]; return o
def ridge(X, y, lam=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9; Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return lambda Xn: ((Xn - mu) / sd) @ w + y.mean()
def knn(Xtr, ytr, Xte, k=25):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9; A = (Xtr - mu) / sd; B = (Xte - mu) / sd
    out = np.empty(len(B))
    for i in range(0, len(B), 200):  # chunks keep memory small
        d = ((B[i:i + 200, None, :] - A[None, :, :]) ** 2).sum(-1)
        idx = np.argpartition(d, k, axis=1)[:, :k]; out[i:i + 200] = ytr[idx].mean(1)
    return out
rm = lambda e: float(np.sqrt(np.mean(e ** 2)))

with db.connect() as c:
    long = {r["code"]: (r["lat"], r["lon"]) for r in c.execute(
        """SELECT o.code, s.lat, s.lon FROM observation o JOIN station s USING(code) WHERE o.quality_flag='ok' AND s.lat IS NOT NULL
           AND o.obs_time > now()-interval '370 days' GROUP BY o.code, s.lat, s.lon HAVING count(*) > 5000""").fetchall()}
    qt, qv = series(c, "C.13", "discharge")
    for tgt, ups in UP.items():
        la, lo = long[tgt]
        near = sorted((((la - a) ** 2 + ((lo - b) * np.cos(np.radians(la))) ** 2) ** 0.5 * 111, k) for k, (a, b) in long.items() if k != tgt)[:3]
        t, y = forecast.hourly_grid(*series(c, tgt)); n = len(y); split = n - TEST_H
        eta = forecast.fit_tide(t[:split], y[:split]); ybar = forecast.trailing_mean(y, 25)
        q = on_grid(t, qt, qv); upl = {u: on_grid(t, *series(c, u)) for u in ups}; nbl = {k: on_grid(t, *series(c, k)) for _, k in near}
        line = [f"== {tgt}: network={ups}+C.13 · proximity={[f'{k}({d:.1f}km)' for d, k in near]}"]
        for h in (24, 48):
            own = [(eta(t + h) - eta(t)) if eta else np.zeros(n), lagdiff(y, 6), lagdiff(y, 24), y - ybar]
            net = own + [q, lagdiff(q, 24), lagdiff(q, 48)] + [f(x, k) for x in upl.values() for f, k in ((lagdiff, 24), (lagdiff, 48))]
            prox = own + [f(x, k) for x in nbl.values() for f, k in ((lagdiff, 24), (lagdiff, 48))]
            tg = np.full(n, np.nan); tg[:-h] = y[h:] - y[:-h]
            res = {"persistence": None}
            for name, cols in (("own AR", own), ("network STAR", net), ("proximity STAR", prox)):
                X = np.column_stack(cols); ok = np.isfinite(X).all(1) & np.isfinite(tg)
                tr = ok & (np.arange(n) < split - h); te = ok & (np.arange(n) >= split)
                res[name] = rm(tg[te] - ridge(X[tr], tg[tr])(X[te]))
                if name == "network STAR":
                    res["persistence"] = rm(tg[te]); res["k-NN analogue"] = rm(tg[te] - knn(X[tr], tg[tr], X[te]))
            line.append(f"  +{h}h RMSE cm: " + " | ".join(f"{k} {v*100:.1f}" for k, v in res.items()))
        print("\n".join(line))
