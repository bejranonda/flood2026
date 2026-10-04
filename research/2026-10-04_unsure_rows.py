"""Why so many "? ไม่แน่ชัด" rows, and what would be right instead? (owner 2026-10-04: "Why many stations say ? ไม่แน่ชัด, even
we can see the trend from graphs. Could we think about average trend in long term or not.")
For archived runs (one per gauge per 6 h) whose row at h would read "? ไม่แน่ชัด" (not a proven direction, likely range
wider than ±5 cm), compare the reading h hours later with: (a) the model's median sign, (b) the measured 72 h straight-
line trend, (c) the measured 24 h trend. Run: docker compose exec -T worker python - < research/2026-10-04_unsure_rows.py"""
import collections as C, datetime as dt
import numpy as np
from floodwatch import db
H = (24, 48, 72)
with db.connect() as c:
    runs = c.execute("""WITH pick AS (SELECT DISTINCT ON (code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6) id
          FROM forecast_run WHERE issue_time < now() - interval '24 hours'
          ORDER BY code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6, issue_time)
        SELECT f.code, f.issue_time, (f.payload->>'level_now')::float AS now,
               f.payload->'path'->23 AS p24, f.payload->'path'->47 AS p48, f.payload->'path'->71 AS p72,
               f.payload->'skill' AS skill
        FROM forecast_run f JOIN pick USING (id)""").fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation
                          WHERE obs_time > '2026-09-20' AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1, 2"""):
        hourly[r["code"]][r["t"]] = r["v"]
Hh = dt.timedelta(hours=1)
def slope(ser, t0, hours):
    pts = [(k, ser[t0 - k * Hh]) for k in range(hours + 1) if (t0 - k * Hh) in ser]
    if len(pts) < hours * 0.6: return None
    k = np.array([-p[0] for p in pts], float); v = np.array([p[1] for p in pts])
    return float(np.polyfit(k, v, 1)[0])  # m/h
res = {h: C.Counter() for h in H}
for r in runs:
    t0 = r["issue_time"].replace(minute=0, second=0, microsecond=0); ser = hourly.get(r["code"], {})
    if r["now"] is None: continue
    s72, s24 = slope(ser, t0, 72), slope(ser, t0, 24)
    for h, p in zip(H, (r["p24"], r["p48"], r["p72"])):
        if not p or not p.get("q"): continue
        q = p["q"]; d = [v - r["now"] for v in q]; med, lo, hi = d[2], d[1], d[3]
        half = (hi - lo) / 2
        direction = "steady" if abs(med) <= max(0.02, half) else ("up" if med > 0 else "down")
        method = p.get("method")
        proven = direction != "steady" and method not in (None, "persistence") and ((lo > 0) if direction == "up" else (hi < 0))
        narrow = max(abs(lo), abs(hi)) <= 0.05
        if proven or narrow: continue                      # the row was not "? ไม่แน่ชัด"
        y = ser.get(t0 + h * Hh)
        if y is None: continue
        act = y - r["now"]
        if abs(act) < 0.02: res[h]["actual_flat"] += 1; continue  # under 2 cm: no direction to get right
        res[h]["n"] += 1
        if abs(med) >= 0.01: res[h]["med_n"] += 1; res[h]["med_ok"] += (med > 0) == (act > 0)
        for name, sl in (("t72", s72), ("t24", s24)):
            if sl is not None and abs(sl * 24) >= 0.02:     # a measured trend of at least 2 cm a day
                res[h][name + "_n"] += 1; res[h][name + "_ok"] += (sl > 0) == (act > 0)
                pred = sl * h * np.exp(-h / 48); res[h][name + "_mae"] += abs(pred - act); res[h]["med_mae_" + name] += abs(med - act)
for h, c in res.items():
    pc = lambda a, b: f"{100 * c[a] / c[b]:.0f}% of {c[b]}" if c[b] else "-"
    print(f"+{h} h unsure rows with a real change: {c['n']} (under 2 cm: {c['actual_flat']}) | model median sign right {pc('med_ok','med_n')}"
          f" | 72 h trend right {pc('t72_ok','t72_n')} | 24 h trend right {pc('t24_ok','t24_n')}")
    for nm in ("t72", "t24"):
        if c[nm + "_n"]:
            print(f"     {nm}: mean error continuing it {100 * c[nm + '_mae'] / c[nm + '_n']:.1f} cm vs model median {100 * c['med_mae_' + nm] / c[nm + '_n']:.1f} cm")
