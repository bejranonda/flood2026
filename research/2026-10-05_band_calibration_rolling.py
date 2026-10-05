"""Q54, step 2: a fixed factor learned in the flood peak over-widens later (research/2026-10-05_band_calibration.log). Rolling
test, no future: for each day D, the factor comes from the cases of the W days before D (issue time + h before D starts, so the
outcome was known), never below 1; coverage is judged on day D. Compared with no calibration: mean |coverage − target| over
days, and mean width. W = 2, 3, 5 days.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice -n 10 python - < research/2026-10-05_band_calibration_rolling.py"""
import collections as C, datetime as dt
import numpy as np
from floodwatch import db, risks

with db.connect_readonly() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=31)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation
                          WHERE obs_time > now() - interval '33 days' AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
cases = C.defaultdict(list)
for r in runs:
    t0 = r["issue_time"].replace(minute=0, second=0, microsecond=0)
    ser = hourly.get(r["code"]) or {}
    for h, p in ((24, r["p24"]), (48, r["p48"]), (72, r["p72"])):
        if not p or not p.get("q"):
            continue
        y = ser.get(t0 + dt.timedelta(hours=h))
        if y is None:
            continue
        q = np.array(p["q"], float)
        kind = "no change" if p.get("method") in (None, "persistence") else "model"
        cases[(h, kind)].append((t0, t0 + dt.timedelta(hours=h), q - q[2], y - q[2]))
GRID = np.round(np.arange(1.0, 4.01, 0.05), 2)


def cov(rows, k50, k90):
    off = np.array([x[2] for x in rows]); a = np.array([x[3] for x in rows])
    return (((a >= k50 * off[:, 1]) & (a <= k50 * off[:, 3])).mean(), ((a >= k90 * off[:, 0]) & (a <= k90 * off[:, 4])).mean(),
            np.mean(k50 * (off[:, 3] - off[:, 1])) * 100)


for key in sorted(cases):
    rows = cases[key]
    days = sorted({x[0].date() for x in rows})
    res = C.defaultdict(list)
    for d in days:
        test = [x for x in rows if x[0].date() == d]
        if len(test) < 50:
            continue
        start = dt.datetime.combine(d, dt.time(), tzinfo=dt.timezone.utc)
        c0 = cov(test, 1, 1)
        res["none"].append((abs(c0[0] - .5), abs(c0[1] - .9), c0[2], c0[0], c0[1]))
        for W in (2, 3, 5):
            fit = [x for x in rows if x[1] < start and x[0] >= start - dt.timedelta(days=W)]  # outcome known before D
            if len(fit) < 100:
                continue
            k50 = next((k for k in GRID if cov(fit, k, 1)[0] >= .5), GRID[-1])
            k90 = next((k for k in GRID if cov(fit, 1, k)[1] >= .9), GRID[-1])
            c1 = cov(test, k50, k90)
            res[f"W{W}"].append((abs(c1[0] - .5), abs(c1[1] - .9), c1[2], c1[0], c1[1]))
    out = []
    for name, v in res.items():
        a = np.array(v)
        out.append(f"{name}: {len(v)} days, |cov−50%| {100*a[:,0].mean():4.1f} pts, |cov−90%| {100*a[:,1].mean():4.1f} pts, "
                   f"50 % held {100*a[:,3].mean():4.1f}%, 90 % held {100*a[:,4].mean():4.1f}%, width {a[:,2].mean():5.1f} cm")
    print(f"+{key[0]} h {key[1]}:\n   " + "\n   ".join(out))
