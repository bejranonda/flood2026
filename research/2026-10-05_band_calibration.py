"""Q54 (owner 2026-10-05: "Yes" — widen the 48/72 h ranges so they hold as stated). Honest calibration of the served bands:
one factor per horizon and kind (real model / "no change"), scaling the 50 % and 90 % offsets around the median, the
smallest factor that makes coverage reach 50 % / 90 %, never below 1 (a band may widen, never narrow). Fitted on the
FIRST half of the archived runs (risks.LEAN_SQL, one per gauge per 6 h), judged on the SECOND half.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice -n 10 python - < research/2026-10-05_band_calibration.py"""
import collections as C, datetime as dt
import numpy as np
from floodwatch import db, risks

with db.connect_readonly() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=31)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation
                          WHERE obs_time > now() - interval '33 days' AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
cases = C.defaultdict(list)  # (h, kind) -> [(issue_time, q0..q4 offsets from the median, actual offset)]
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
        cases[(h, kind)].append((r["issue_time"], q - q[2], y - q[2]))
GRID = np.round(np.arange(1.0, 4.01, 0.05), 2)


def cover(rows, k50, k90):
    off = np.array([x[1] for x in rows]); a = np.array([x[2] for x in rows])
    in50 = (a >= k50 * off[:, 1]) & (a <= k50 * off[:, 3])
    in90 = (a >= k90 * off[:, 0]) & (a <= k90 * off[:, 4])
    return in50.mean(), in90.mean(), np.mean(k50 * (off[:, 3] - off[:, 1])) * 100, np.mean(k90 * (off[:, 4] - off[:, 0])) * 100


for key in sorted(cases):
    rows = sorted(cases[key], key=lambda x: x[0])
    mid = rows[len(rows) // 2][0]
    A = [x for x in rows if x[0] < mid]; B = [x for x in rows if x[0] >= mid]
    k50 = next((k for k in GRID if cover(A, k, 1)[0] >= 0.50), GRID[-1])
    k90 = next((k for k in GRID if cover(A, 1, k)[1] >= 0.90), GRID[-1])
    b0 = cover(B, 1.0, 1.0); b1 = cover(B, k50, k90)
    print(f"+{key[0]} h {key[1]:9s} fit on {len(A):5d} (to {mid:%d %b %H:%M}), judged on {len(B):5d}: factors 50 % ×{k50:.2f}, 90 % ×{k90:.2f} | "
          f"second half — today: 50 % held {100*b0[0]:4.1f}% (width {b0[2]:5.1f} cm), 90 % held {100*b0[1]:4.1f}% | "
          f"calibrated: 50 % held {100*b1[0]:4.1f}% (width {b1[2]:5.1f} cm), 90 % held {100*b1[1]:4.1f}% (width {b1[3]:5.1f} cm)")
