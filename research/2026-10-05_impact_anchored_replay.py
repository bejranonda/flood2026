"""D-099 pilot, validation step 2: the absolute what-if (mass balance + rating curve) lost to "keep today's level" by 3-4x
(B.10 44 vs 13 cm). Anchored variant: start from the measured level and add only what the rating curve says the extra
flow adds — h_i(t+lag) ≈ h_i(t) + rating_i(q_i(t) + ΔQ) − rating_i(q_i(t)), ΔQ = the flow change at B.18 already on its way
(q18(t) − q18(t − lag_i)), diversion held. Ratings and lags fitted on the first 60 % of the year, judged on the last 40 %;
all cases and the big-change subset (|ΔQ| >= 15 m³/s); compared with keeping today's level.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice -n 10 python - < research/2026-10-05_impact_anchored_replay.py"""
import datetime as dt
import numpy as np
from floodwatch import db, impact

with db.connect_readonly() as c:
    now = dt.datetime.now(dt.timezone.utc)
    codes = ["B.18", "B.10", "B.16", "B.15", "PCH001"]
    raw = {code: c.execute(impact.HOURLY_SQL, (code,)).fetchall() for code in codes}
t0 = min(r[0]["t"] for r in raw.values())
n = int((now.replace(minute=0, second=0, microsecond=0) - t0).total_seconds() // 3600) + 1
H, Q = {}, {}
for code, rows in raw.items():
    h, q = np.full(n, np.nan), np.full(n, np.nan)
    for r in rows:
        k = int((r["t"] - t0).total_seconds() // 3600)
        if 0 <= k < n:
            h[k] = r["h"] if r["h"] is not None else np.nan
            q[k] = r["q"] if r["q"] is not None else np.nan
    H[code], Q[code] = h, q
cut = int(n * 0.6)
q18 = Q["B.18"]
lag = {"B.10": impact.best_lag(q18[:cut], Q["B.10"][:cut]) or 30}
lag["B.16"] = max(lag["B.10"], impact.best_lag(q18[:cut], Q["B.16"][:cut]) or 37)
for cc in ("B.15", "PCH001"):
    lag[cc] = max(lag["B.16"], impact.best_lag(q18[:cut], H[cc][:cut]) or 43)
rat = {"B.10": impact.fit_rating(Q["B.10"][:cut], H["B.10"][:cut]), "B.16": impact.fit_rating(Q["B.16"][:cut], H["B.16"][:cut])}
for cc in ("B.15", "PCH001"):
    rat[cc] = impact.fit_rating(np.roll(Q["B.16"], lag[cc] - lag["B.16"])[:cut], H[cc][:cut])
print("lags", lag)
for code in ("B.10", "B.16", "B.15", "PCH001"):
    qsrc = Q[code] if code in ("B.10", "B.16") else np.roll(Q["B.16"], lag[code] - lag["B.16"])
    acc = {"all": [0, 0.0, 0.0, 0], "big": [0, 0.0, 0.0, 0]}
    for t in range(max(cut, 96), n - lag[code] - 1, 3):
        dq = q18[t] - q18[t - lag[code]]
        obs, hn, qn = H[code][t + lag[code]], H[code][t], qsrc[t]
        if not all(np.isfinite(v) for v in (dq, obs, hn, qn)) or rat[code] is None:
            continue
        pred = hn + impact.level_at(rat[code], max(0.0, qn + dq)) - impact.level_at(rat[code], qn)
        for key in ("all",) + (("big",) if abs(dq) >= 15 else ()):
            a = acc[key]; a[0] += 1; a[1] += abs(pred - obs); a[2] += abs(hn - obs)
            a[3] += (pred + rat[code]["res"][0] - rat[code]["rmse"]) <= obs <= (pred + rat[code]["res"][1] + rat[code]["rmse"])
    for key, a in acc.items():
        if a[0]:
            print(f"{code:7s} {key:3s} n {a[0]:4d} · anchored model {100*a[1]/a[0]:5.1f} cm · keep today's level {100*a[2]/a[0]:5.1f} cm")

# --- step 3: learned pass-through gain (how much of a B.18 change reached each point), fitted on the first 60 % --------
print("\nlearned gain:")
for code in ("B.10", "B.16", "B.15", "PCH001"):
    qsrc = Q[code] if code in ("B.10", "B.16") else np.roll(Q["B.16"], lag[code] - lag["B.16"])
    xs, ys = [], []
    for t in range(96, cut - lag[code], 3):  # the first 60 %: dq at B.18 vs the level change lag hours later
        dq = q18[t] - q18[t - lag[code]]
        dh = H[code][t + lag[code]] - H[code][t]
        if np.isfinite(dq) and np.isfinite(dh):
            xs.append(dq); ys.append(dh)
    xs, ys = np.array(xs), np.array(ys)
    g = float(np.sum(xs * ys) / np.sum(xs * xs)) if len(xs) > 50 else 0.0  # m of level per m³/s at B.18, through the origin
    acc = {"all": [0, 0.0, 0.0], "big": [0, 0.0, 0.0]}
    for t in range(max(cut, 96), n - lag[code] - 1, 3):
        dq = q18[t] - q18[t - lag[code]]
        obs, hn = H[code][t + lag[code]], H[code][t]
        if not all(np.isfinite(v) for v in (dq, obs, hn)):
            continue
        pred = hn + g * dq
        for key in ("all",) + (("big",) if abs(dq) >= 15 else ()):
            a = acc[key]; a[0] += 1; a[1] += abs(pred - obs); a[2] += abs(hn - obs)
    print(f"{code:7s} gain {100*g:5.2f} cm per m³/s (fit n {len(xs)})", " · ".join(
        f"{k}: n {a[0]} model {100*a[1]/max(1,a[0]):5.1f} cm vs keep {100*a[2]/max(1,a[0]):5.1f} cm" for k, a in acc.items() if a[0]))
