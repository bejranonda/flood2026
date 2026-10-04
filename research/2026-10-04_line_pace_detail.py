"""Detail for the trend-carrying line (research/2026-10-04_line_candidates.py: on "?" rows the measured pace continued
with τ = 24 h damping beat the served median: direction 75 % vs 61–67 %, MAE lower at all horizons).
Split by served method (persistence = "no change" model vs a real model), by word class of the new line
(small 3–10 cm / clear ≥ 10 cm / flat < 3 cm), and the 50 % band's coverage when it moves with the line.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-04_line_pace_detail.py"""
import collections as C, datetime as dt, math
from floodwatch import db, risks
from floodwatch.risks import _pace
with db.connect() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation WHERE obs_time > now() - interval '33 days'
                          AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
TAU = 24
sc = C.defaultdict(C.Counter)
for r in runs:
    ser, t0 = hourly.get(r["code"]) or {}, r["issue_time"].replace(minute=0, second=0, microsecond=0)
    if r["now"] is None: continue
    r24, r6 = _pace(ser, t0, 24), _pace(ser, t0, 6)
    if r24 is None or r6 is None: continue
    rate = 0.0 if r24 == 0 or r6 == 0 or (r24 > 0) != (r6 > 0) else math.copysign(min(abs(r24), abs(r6)), r24)
    for h, p in ((24, r["p24"]), (48, r["p48"]), (72, r["p72"])):
        if not p or not p.get("q"): continue
        q = p["q"]; lo, med, hi = q[1] - r["now"], q[2] - r["now"], q[3] - r["now"]
        d = "steady" if abs(med) <= max(0.02, (hi - lo) / 2) else ("up" if med > 0 else "down")
        if (d != "steady" and p.get("method") not in (None, "persistence") and ((lo > 0) if d == "up" else (hi < 0))) or max(abs(lo), abs(hi)) <= 0.05:
            continue
        y = ser.get(t0 + dt.timedelta(hours=h))
        if y is None: continue
        act = (y - r["now"]) * 100
        new = rate * TAU * (1 - math.exp(-h / TAU)) * 100
        meth = "persistence" if p.get("method") in (None, "persistence") else "model"
        for key, line in ((("old", meth, h), med * 100), (("new", meth, h), new)):
            s = sc[key]; s["n"] += 1; s["ae"] += abs(line - act)
            cls = "flat" if abs(line) < 3 else "small" if abs(line) < 10 else "clear"
            s[cls + "_n"] += 1
            s[cls + "_ok"] += (abs(act) < 5) if cls == "flat" else ((act > 0) == (line > 0) and act != 0)
            sh = line / 100 - med  # move the band with the line
            s["cov_n"] += 1; s["cov"] += (lo + sh) * 100 <= act <= (hi + sh) * 100
for h in (24, 48, 72):
    print(f"\n=== +{h} h, '?' rows with a measured pace")
    for meth in ("persistence", "model"):
        for which in ("old", "new"):
            s = sc[(which, meth, h)]
            if not s["n"]: continue
            f = lambda k: f"{100*s[k+'_ok']/max(1,s[k+'_n']):3.0f}% of {s[k+'_n']:5d}"
            print(f"{meth:11s} {which}: n {s['n']:5d} MAE {s['ae']/s['n']:5.1f} | small 3–10 right {f('small')} | clear ≥10 right {f('clear')}"
                  f" | flat within ±5 {f('flat')} | 50% band holds {100*s['cov']/s['cov_n']:3.0f}%")
