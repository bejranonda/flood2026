"""Spike 2026-10-03 for the จับตา tab (spec docs/superpowers/specs/2026-10-03-watch-tab-satellite-design.md §2).
Run: docker compose exec -T worker python - < research/2026-10-03_verify_bank.py"""
import collections as C, datetime as dt
from floodwatch import db
with db.connect() as c:
    banks = {r["code"]: (r["bank_msl"], r["region"]) for r in c.execute("SELECT code, bank_msl, NULL AS region FROM station WHERE bank_msl IS NOT NULL")}
    runs = c.execute("""SELECT DISTINCT ON (code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6)
        code, issue_time, payload->'path' AS path, (payload->>'level_now')::float AS now
        FROM forecast_run WHERE issue_time < now() - interval '48 hours' ORDER BY code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6, issue_time""").fetchall()
    obs = C.defaultdict(list)
    for r in c.execute("SELECT code AS station_code, obs_time, level_msl FROM observation WHERE obs_time > '2026-09-26' AND level_msl IS NOT NULL"):
        obs[r["station_code"]].append((r["obs_time"], r["level_msl"]))
tab = {24: C.Counter(), 48: C.Counter()}
for r in runs:
    b = banks.get(r["code"])
    if not b or r["now"] is None or not r["path"] or r["now"] >= b[0]:
        continue  # only gauges below the bank at issue time: "will it reach the bank?"
    bank = b[0]
    for H in (24, 48):
        qs = [p for p in r["path"][:H] if p.get("q")]
        if not qs: continue
        top = lambda k: max(p["q"][k] for p in qs)
        cat = ">50%" if top(2) >= bank else "25-50%" if top(3) >= bank else "5-25%" if top(4) >= bank else "<5%"
        t0, t1 = r["issue_time"], r["issue_time"] + dt.timedelta(hours=H)
        vals = [v for t, v in obs[r["code"]] if t0 < t <= t1]
        if len(vals) < H / 3: continue
        tab[H][(cat, max(vals) >= bank)] += 1
for H, t in tab.items():
    print(f"--- reaches bank within {H} h (gauges below bank at issue; one run per gauge per 6 h)")
    for cat in ("<5%", "5-25%", "25-50%", ">50%"):
        y, n = t[(cat, True)], t[(cat, False)]
        print(f"  {cat:7} runs={y+n:6}  reached={y:5}  rate={100*y/max(1,y+n):5.1f}%")
