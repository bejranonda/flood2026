"""Experiment 2026-09-27 (results: research/2026-09-27_forecast_48h.md): does forecast rain improve 24/48 h levels?
Inputs (download into this folder first, keyless, non-commercial):
  rain_<ID>.json: historical-forecast-api.open-meteo.com/v1/forecast?latitude=..&longitude=..&start_date=2025-09-20&end_date=2026-09-27&hourly=precipitation&timezone=UTC
  prev_<ID>.json: previous-runs-api.open-meteo.com/v1/forecast?...&hourly=precipitation_previous_day1,precipitation_previous_day2&timezone=UTC
  IDs/points: BKK021 13.854,100.603 · C12 13.788,100.513 · CPY014 13.947,100.482
Run: docker compose run --rm --no-deps -v $PWD/research/validation:/exp worker python /exp/exp_48h_rain_2026-09-27.py
Honest version: rain for the next 0-24 h comes from the run issued ~1 day earlier, 24-48 h from ~2 days earlier
(never fresher than what we would have had). Same split as exp_48h_upstream: train before, test on the last 45 days."""
import json, datetime as dt, numpy as np
from floodwatch import db, forecast
TEST_H = forecast.EVAL_HOURS
T = {"BKK021": "BKK021", "C.12": "C12", "CPY014": "CPY014"}
def ridge(X, y, lam=1.0):
    mu, sd = X.mean(0), X.std(0) + 1e-9; Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return lambda Xn: ((Xn - mu) / sd) @ w + y.mean()
def lagdiff(x, k):
    o = np.full_like(x, np.nan); o[k:] = x[k:] - x[:-k]; return o
with db.connect() as c:
    for code, f in T.items():
        rows = c.execute("SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok' AND level_msl IS NOT NULL AND obs_time > now()-interval '370 days' ORDER BY obs_time", (code,)).fetchall()
        t, y = forecast.hourly_grid([r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows]); n = len(y); split = n - TEST_H
        def load(fn, key):
            d = json.load(open(fn))["hourly"]
            m = {int(dt.datetime.fromisoformat(a).replace(tzinfo=dt.timezone.utc).timestamp() // 3600): (b or 0.0) for a, b in zip(d["time"], d[key])}
            return np.concatenate([[0], np.cumsum(np.array([m.get(int(a), 0.0) for a in t]))])
        cs = load(f"/exp/rain_{f}.json", "precipitation")               # observed-like (for past 24 h rain only)
        c1 = load(f"/exp/prev_{f}.json", "precipitation_previous_day1")  # issued ~1 day before the hour
        c2 = load(f"/exp/prev_{f}.json", "precipitation_previous_day2")  # issued ~2 days before the hour
        past24 = np.array([cs[i + 1] - cs[max(0, i - 23)] for i in range(n)])
        eta = forecast.fit_tide(t[:split], y[:split]); ybar = forecast.trailing_mean(y, 25)
        rm = lambda e: float(np.sqrt(np.mean(e ** 2)))
        for h in (24, 48):
            # honest: next 0-24 h from the run 1 day older, 24-48 h from the run 2 days older (never newer than issue time)
            fut = np.array([(c1[min(n, i + 1 + min(h, 24))] - c1[i + 1]) + ((c2[min(n, i + 1 + h)] - c2[min(n, i + 25)]) if h > 24 else 0) for i in range(n)])
            base = [(eta(t + h) - eta(t)) if eta else np.zeros(n), lagdiff(y, 6), lagdiff(y, 24), y - ybar]
            Xb = np.column_stack(base); Xr = np.column_stack(base + [past24, fut])
            tg = np.full(n, np.nan); tg[:-h] = y[h:] - y[:-h]
            ok = np.isfinite(Xr).all(1) & np.isfinite(tg); tr = ok & (np.arange(n) < split - h); te = ok & (np.arange(n) >= split)
            e0 = tg[te]; eb = tg[te] - ridge(Xb[tr], tg[tr])(Xb[te]); er = tg[te] - ridge(Xr[tr], tg[tr])(Xr[te])
            wet = te & (fut >= 35)  # test hours followed by heavy rain (TMD "ฝนหนัก")
            ew0 = tg[wet]; ewr = tg[wet] - ridge(Xr[tr], tg[tr])(Xr[wet]) if wet.sum() else np.array([np.nan])
            print(f"{code} +{h}h n={te.sum()}: persistence {rm(e0)*100:.1f} | own {rm(eb)*100:.1f} | own+rain {rm(er)*100:.1f} cm"
                  f" || heavy-rain hours n={int(wet.sum())}: persistence {rm(ew0)*100:.1f} vs own+rain {rm(ewr)*100:.1f} cm")
