"""Do "rebound" forecasts come true? (live 2026-10-04 21:20 UTC: 50 rows forecast >= 20 cm rise in 24 h; 12 at gauges whose
water fell strongly, e.g. PAS001 measured -61 cm, forecast +59 cm.) Archived runs of 30 days (risks.LEAN_SQL) against the
hourly level 24 h later, split by the measured 24 h change at issue time.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice -n 10 python - < research/2026-10-04_rebound_check.py"""
import collections as C, datetime as dt
from floodwatch import db, risks
from floodwatch.risks import _pace

with db.connect_readonly() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation
                          WHERE obs_time > now() - interval '33 days' AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
acc = C.defaultdict(C.Counter)
for r in runs:
    p = r["p24"]
    if not p or not p.get("q") or r["now"] is None:
        continue
    ser, t0 = hourly.get(r["code"]) or {}, r["issue_time"].replace(minute=0, second=0, microsecond=0)
    y0, y24 = ser.get(t0 - dt.timedelta(hours=24)), ser.get(t0 + dt.timedelta(hours=24))
    if y0 is None or y24 is None:
        continue
    past = (r["now"] - y0) * 100
    med = (p["q"][2] - r["now"]) * 100
    if med < 20:
        continue
    act = (y24 - r["now"]) * 100
    key = "after a measured fall >= 20 cm" if past <= -20 else "after a fall 5-20 cm" if past <= -5 else "after steady/rising"
    a = acc[(key, p.get("method"))]
    a["n"] += 1
    a["rose10"] += act >= 10
    a["kept_falling"] += act < 0
    a["err"] += abs(act - med)
for (key, m), a in sorted(acc.items()):
    n = a["n"]
    print(f"forecast >= +20 cm, {key:32s} method {m:12s} n {n:5d} · rose >= 10 cm {100*a['rose10']/n:4.0f}% · kept falling {100*a['kept_falling']/n:4.0f}% · mean error {a['err']/n:5.1f} cm")
