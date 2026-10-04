"""Words that follow the chart's line (owner 2026-10-04: "we should say the trend if we can see the trend, not always '?' …
น่าจะขึ้นเล็กน้อย / น่าจะลงเล็กน้อย / น่าจะขึ้น / น่าจะลง … How to make the chart and description consistency? … validate").
On archived "?" rows (30 days, 4 runs a day per gauge): bucket by how far the chart's dashed line (model median) moves at
+h and by the measured trend at issue; report how the water actually moved.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-04_line_words.py"""
import collections as C, datetime as dt, math, statistics as S
from floodwatch import db, risks
from floodwatch.risks import _pace
with db.connect() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation WHERE obs_time > now() - interval '33 days'
                          AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]

def bucket(m):  # chart-line move in cm
    return "down" if m <= -10 else "down_small" if m <= -3 else "flat" if m < 3 else "up_small" if m < 10 else "up"

rows = C.defaultdict(list)  # (h, bucket, measured) -> actual changes (cm)
for r in runs:
    ser, t0 = hourly.get(r["code"]) or {}, r["issue_time"].replace(minute=0, second=0, microsecond=0)
    if r["now"] is None: continue
    r24, r6 = _pace(ser, t0, 24), _pace(ser, t0, 6)
    meas = "none"
    if r24 is not None and r6 is not None:
        rate = 0.0 if r24 == 0 or r6 == 0 or (r24 > 0) != (r6 > 0) else math.copysign(min(abs(r24), abs(r6)), r24)
        meas = "up" if rate * 24 >= 0.02 else "down" if rate * 24 <= -0.02 else "steady"
    for h, p in ((24, r["p24"]), (48, r["p48"]), (72, r["p72"])):
        if not p or not p.get("q"): continue
        q = p["q"]; lo, med, hi = q[1] - r["now"], q[2] - r["now"], q[3] - r["now"]
        d = "steady" if abs(med) <= max(0.02, (hi - lo) / 2) else ("up" if med > 0 else "down")
        if (d != "steady" and p.get("method") not in (None, "persistence") and ((lo > 0) if d == "up" else (hi < 0))) or max(abs(lo), abs(hi)) <= 0.05:
            continue  # not a "?" row
        y = ser.get(t0 + dt.timedelta(hours=h))
        if y is None: continue
        rows[(h, bucket(med * 100), meas)].append((y - r["now"]) * 100)

def stats(v, b):
    n = len(v)
    if not n: return ""
    up, down, still = sum(a > 0 for a in v) / n, sum(a < 0 for a in v) / n, sum(abs(a) < 5 for a in v) / n
    way = up if b.startswith("up") else down if b.startswith("down") else still
    return f"n {n:5d} · went the line's way {100*way:3.0f}% · |change| median {S.median(abs(a) for a in v):4.0f} cm · within ±5 cm {100*still:3.0f}%"

for h in (24, 48, 72):
    print(f"\n=== +{h} h ('?' rows) — 'the line's way' = up/down by sign, flat = within ±5 cm")
    for b in ("up", "up_small", "flat", "down_small", "down"):
        allv = [a for (hh, bb, m), v in rows.items() if hh == h and bb == b for a in v]
        print(f"{b:10s} all            {stats(allv, b)}")
        for m in ("up", "down", "steady", "none"):
            v = rows.get((h, b, m)) or []
            if len(v) >= 30: print(f"{'':10s} measured {m:6s} {stats(v, b)}")
