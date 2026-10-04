"""Can the chart's line carry the visible trend on "?" rows? (owner 2026-10-04: "How to make the chart and description
consistency?"; research/2026-10-04_line_words.py showed a rising line against a measured fall was right 13–18 %).
Candidate lines at +h on archived "?" rows (30 days): the served median; the measured pace continued with damping
rate·τ·(1−e^(−h/τ)) for τ = 12/24/48 h; and "fix only when they disagree" (served median unless it goes against the
measured pace or is flat while the pace is clear, then the damped pace). Score: MAE (cm), direction right (strict sign,
moves ≥ 3 cm), flat right (line < 3 cm and water within ±5 cm).
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-04_line_candidates.py"""
import collections as C, datetime as dt, math
from floodwatch import db, risks
from floodwatch.risks import _pace
with db.connect() as c:
    runs = c.execute(risks.LEAN_SQL, {"since": dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)}).fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation WHERE obs_time > now() - interval '33 days'
                          AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
damp = lambda rate, h, tau: rate * tau * (1 - math.exp(-h / tau))
score = {h: C.defaultdict(lambda: C.Counter()) for h in (24, 48, 72)}
def add(h, name, pred, act):
    s = score[h][name]; s["n"] += 1; s["ae"] += abs(pred - act)
    if abs(pred) >= 3:
        s["dn"] += 1; s["dok"] += (act > 0) == (pred > 0) and act != 0
    else:
        s["fn"] += 1; s["fok"] += abs(act) < 5
for r in runs:
    ser, t0 = hourly.get(r["code"]) or {}, r["issue_time"].replace(minute=0, second=0, microsecond=0)
    if r["now"] is None: continue
    r24, r6 = _pace(ser, t0, 24), _pace(ser, t0, 6)
    rate = None
    if r24 is not None and r6 is not None:
        rate = 0.0 if r24 == 0 or r6 == 0 or (r24 > 0) != (r6 > 0) else math.copysign(min(abs(r24), abs(r6)), r24)
    for h, p in ((24, r["p24"]), (48, r["p48"]), (72, r["p72"])):
        if not p or not p.get("q"): continue
        q = p["q"]; lo, med, hi = q[1] - r["now"], q[2] - r["now"], q[3] - r["now"]
        d = "steady" if abs(med) <= max(0.02, (hi - lo) / 2) else ("up" if med > 0 else "down")
        if (d != "steady" and p.get("method") not in (None, "persistence") and ((lo > 0) if d == "up" else (hi < 0))) or max(abs(lo), abs(hi)) <= 0.05:
            continue
        y = ser.get(t0 + dt.timedelta(hours=h))
        if y is None: continue
        act, m = (y - r["now"]) * 100, med * 100
        add(h, "served median", m, act)
        add(h, "no change", 0.0, act)
        if rate is None: 
            for tau in (12, 24, 48): add(h, f"pace τ{tau}", m, act)
            for tau in (12, 24, 48): add(h, f"fix-if-disagree τ{tau}", m, act)
            continue
        clear = abs(rate * 24) >= 0.02
        for tau in (12, 24, 48):
            pc = damp(rate, h, tau) * 100
            add(h, f"pace τ{tau}", pc, act)
            disagree = clear and (abs(m) < 3 or (m > 0) != (rate > 0))
            add(h, f"fix-if-disagree τ{tau}", pc if disagree else m, act)
for h in (24, 48, 72):
    print(f"\n=== +{h} h, '?' rows")
    for name, s in score[h].items():
        print(f"{name:24s} n {s['n']:5d} · MAE {s['ae']/s['n']:5.1f} cm · direction right {100*s['dok']/max(1,s['dn']):3.0f}% of {s['dn']:5d}"
              f" · flat right {100*s['fok']/max(1,s['fn']):3.0f}% of {s['fn']:5d}")
