"""Text (measured trend, damped) vs graph (model median) vs the reading h hours later, archived runs 26 Sep - now."""
import datetime as dt, math, collections as C
import numpy as np
from floodwatch import db, qc
TREND = {"small_rise", "rise", "strong_rise", "small_fall", "fall", "strong_fall"}
now = dt.datetime.now(dt.timezone.utc); since = dt.datetime(2026, 9, 24, tzinfo=dt.timezone.utc)
with db.connect() as c:
    runs = c.execute("""WITH pick AS (SELECT DISTINCT ON (code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6) id
          FROM forecast_run WHERE issue_time < now() - interval '12 hours'
          ORDER BY code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6, issue_time)
        SELECT f.code, f.issue_time, (f.payload->>'level_now')::float AS now,
               (f.payload->'path'->11->'q'->>2)::float AS m12, (f.payload->'path'->23->'q'->>2)::float AS m24,
               (f.payload->'path'->47->'q'->>2)::float AS m48, f.payload->'path'->23->>'method' AS meth
        FROM forecast_run f JOIN pick USING (id)""").fetchall()
    hourly = C.defaultdict(dict)
    for r in c.execute("""SELECT code, date_trunc('hour', obs_time) t, avg(level_msl) v FROM observation
                          WHERE obs_time > %s AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1,2""", (since,)):
        hourly[r["code"]][r["t"]] = r["v"]
H = dt.timedelta(hours=1)
err = {h: C.defaultdict(list) for h in (12, 24, 48)}
for r in runs:
    t0 = r["issue_time"].replace(minute=0, second=0, microsecond=0); ser = hourly.get(r["code"], {})
    w = [((k) * 3600.0, ser[t0 - (24 - k) * H]) for k in range(25) if (t0 - (24 - k) * H) in ser]
    o = qc.observed24(w) if len(w) >= 12 else None
    if not o or o["level"] not in TREND or r["now"] is None:
        continue
    rate = o["change_cm"] / 100 / 24
    # the last 6 h: is the trend still going?
    w6 = [v for k, v in w if k >= 18 * 3600]
    for h, m in ((12, r["m12"]), (24, r["m24"]), (48, r["m48"])):
        y = ser.get(t0 + h * H)
        if y is None or m is None:
            continue
        actual = y - r["now"]
        # last 6 h fitted slope (m/h)
        x6 = [(k, v) for k, v in w if k >= 18 * 3600]
        if len(x6) >= 4:
            kk = np.array([k for k, _ in x6]) / 3600; vv = np.array([v for _, v in x6])
            r6 = float(np.polyfit(kk, vv, 1)[0])
        else:
            r6 = rate
        same = (r6 > 0) == (rate > 0)
        variants = {"text": rate * h * math.exp(-h / 48),
                    "recent6": r6 * h * math.exp(-h / 48),
                    "min24_6": (math.copysign(min(abs(rate), abs(r6)), rate) if same else 0.0) * h * math.exp(-h / 48),
                    "min24_6_d24": (math.copysign(min(abs(rate), abs(r6)), rate) if same else 0.0) * h * math.exp(-h / 24),
                    "text_d24": rate * h * math.exp(-h / 24)}
        text = variants["text"]
        e = err[h]
        for k, v in variants.items():
            e["v_" + k].append(abs(v - actual))
            if abs(v) >= 0.10: e["vb_" + k].append(abs(v - actual))
            if abs(actual) >= 0.02 and abs(v) > 0.005: e["vd_" + k].append((v > 0) == (actual > 0))
            if abs(text) >= 0.10: e["vt_" + k].append(abs(v - actual))
        e["text"].append(abs(text - actual)); e["graph"].append(abs((m - r["now"]) - actual)); e["zero"].append(abs(actual))
        e["text_dir_ok"].append((text > 0) == (actual > 0) if abs(actual) >= 0.02 else None)
        big = abs(text) >= 0.10
        if big:
            e["big_text"].append(abs(text - actual)); e["big_graph"].append(abs((m - r["now"]) - actual))
            e["big_meth_persist"].append(r["meth"] == "persistence")
for h, e in err.items():
    ok = [x for x in e["text_dir_ok"] if x is not None]
    print(f"+{h} h: cases {len(e['text'])}  MAE text {100*np.mean(e['text']):.1f} cm | graph {100*np.mean(e['graph']):.1f} | no change {100*np.mean(e['zero']):.1f}"
          f" | text direction right {100*np.mean(ok):.0f}% of {len(ok)}")
    if e["big_text"]:
        print(f"      text >= 10 cm ({len(e['big_text'])} cases, {100*np.mean(e['big_meth_persist']):.0f}% with a persistence graph): "
              f"MAE text {100*np.mean(e['big_text']):.1f} cm | graph {100*np.mean(e['big_graph']):.1f}")

for h, e in err.items():
    print(f"+{h} h variants: MAE all | MAE where current text >= 10 cm | direction right")
    for k in ("text", "recent6", "min24_6", "min24_6_d24", "text_d24"):
        print(f"   {k:12} {100*np.mean(e['v_'+k]):5.1f} | {100*np.mean(e['vt_'+k]):5.1f} | {100*np.mean(e['vd_'+k]):3.0f}% of {len(e['vd_'+k])}")
