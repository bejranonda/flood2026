"""How often did the SERVED likely ranges hold? (Q52; the half-window test showed 50 % bands holding 37-41 % and 90 % bands
71-79 % on unseen hours, research/2026-10-04_bands_by_trend_s1.log.) Archived forecast runs of the last 30 days (4 a day
per gauge, risks.LEAN_SQL) against the hourly measured level h hours later; split by the served method.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice -n 19 python - < research/2026-10-04_band_coverage_live.py"""
import collections as C, datetime as dt
from floodwatch import db, risks

with db.connect_readonly() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation
                          WHERE obs_time > now() - interval '33 days' AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
acc = C.defaultdict(C.Counter)
for r in runs:
    ser, t0 = hourly.get(r["code"]) or {}, r["issue_time"].replace(minute=0, second=0, microsecond=0)
    for h, p in ((24, r["p24"]), (48, r["p48"]), (72, r["p72"])):
        if not p or not p.get("q"):
            continue
        y = ser.get(t0 + dt.timedelta(hours=h))
        if y is None:
            continue
        q = p["q"]
        kind = "no change" if p.get("method") in (None, "persistence") else "model"
        for key in ((h, "all"), (h, kind)):
            a = acc[key]
            a["n"] += 1
            a["in50"] += q[1] <= y <= q[3]
            a["in90"] += q[0] <= y <= q[4]
            a["w50"] += (q[3] - q[1]) * 100
            a["below"] += y < q[1]
            a["above"] += y > q[3]
for key in sorted(acc):
    a = acc[key]
    n = a["n"]
    print(f"+{key[0]} h {key[1]:9s} n {n:6d} · 50 % band held {100 * a['in50'] / n:4.1f}% (outside: below {100 * a['below'] / n:4.1f}%, "
          f"above {100 * a['above'] / n:4.1f}%; mean width {a['w50'] / n:5.1f} cm) · 90 % band held {100 * a['in90'] / n:4.1f}%")
