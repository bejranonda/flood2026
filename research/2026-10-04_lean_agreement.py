"""Lean only when the measured pace and the model's median agree? (owner 2026-10-04, T.13 / BKK017: "I follow the dash
trendline in chart … How we can calculate differently between description and chart?"). On archived "?" rows: the lean
record and coverage for (a) the measured pace alone (v0.24.0), (b) the pace AND the model median (>= 1 cm the same way).
Run: docker compose exec -T worker python - < research/2026-10-04_lean_agreement.py"""
import collections as C, datetime as dt, math
from floodwatch import db, risks
from floodwatch.risks import _pace
with db.connect() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation WHERE obs_time > now() - interval '33 days'
                          AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
tab = {h: C.Counter() for h in (24, 48, 72)}
for r in runs:
    ser, t0 = hourly.get(r["code"]) or {}, r["issue_time"].replace(minute=0, second=0, microsecond=0)
    if r["now"] is None: continue
    r24, r6 = _pace(ser, t0, 24), _pace(ser, t0, 6)
    lean = None
    if r24 and r6 and (r24 > 0) == (r6 > 0):
        rate = math.copysign(min(abs(r24), abs(r6)), r24)
        if abs(rate * 24) >= 0.02: lean = "up" if rate > 0 else "down"
    for h, p in ((24, r["p24"]), (48, r["p48"]), (72, r["p72"])):
        if not p or not p.get("q"): continue
        q = p["q"]; lo, med, hi = q[1] - r["now"], q[2] - r["now"], q[3] - r["now"]
        d = "steady" if abs(med) <= max(0.02, (hi - lo) / 2) else ("up" if med > 0 else "down")
        if (d != "steady" and p.get("method") not in (None, "persistence") and ((lo > 0) if d == "up" else (hi < 0))) or max(abs(lo), abs(hi)) <= 0.05:
            continue
        y = ser.get(t0 + dt.timedelta(hours=h))
        if y is None: continue
        act = y - r["now"]; tab[h]["unsure"] += 1
        if lean:
            ok = act > 0 if lean == "up" else act < 0
            tab[h]["a_n"] += 1; tab[h]["a_ok"] += ok
            for thr in (0.01, 0.02, 0.03, 0.05):
                if (med >= thr) if lean == "up" else (med <= -thr):
                    tab[h][f"b{thr}_n"] += 1; tab[h][f"b{thr}_ok"] += ok
for h, t in tab.items():
    print(f"+{h} h: unsure rows {t['unsure']} | (a) pace only: leans {100*t['a_n']/t['unsure']:.0f}%, right {100*t['a_ok']/max(1,t['a_n']):.1f}%")
    for thr in (0.01, 0.02, 0.03, 0.05):
        n, ok = t[f"b{thr}_n"], t[f"b{thr}_ok"]
        print(f"     (b) model line moves >= {thr*100:.0f} cm the same way: leans {100*n/t['unsure']:.0f}%, right {100*ok/max(1,n):.1f}%")
