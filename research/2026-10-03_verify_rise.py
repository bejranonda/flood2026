"""Spike 2026-10-03 for the จับตา tab (spec docs/superpowers/specs/2026-10-03-watch-tab-satellite-design.md §2).
Run: docker compose exec -T worker python - < research/2026-10-03_verify_rise.py"""
import collections as C, datetime as dt
from floodwatch import db
with db.connect() as c:
    runs = c.execute("""SELECT DISTINCT ON (code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6)
        code, issue_time, payload->'path' AS path, (payload->>'level_now')::float AS now
        FROM forecast_run WHERE issue_time < now() - interval '24 hours'
        ORDER BY code, date_trunc('day', issue_time), extract(hour from issue_time)::int / 6, issue_time""").fetchall()
    obs = C.defaultdict(list)
    for r in c.execute("SELECT code, obs_time, level_msl FROM observation WHERE obs_time > '2026-09-26' AND level_msl IS NOT NULL"):
        obs[r["code"]].append((r["obs_time"], r["level_msl"]))
tab = C.Counter()
for r in runs:
    p = [x for x in (r["path"] or []) if x.get("h") == 24 and x.get("q")]
    if not p or r["now"] is None: continue
    med = p[0]["q"][2] - r["now"]
    if med < 0.20: continue
    t = r["issue_time"] + dt.timedelta(hours=24)
    v = [l for ti, l in obs[r["code"]] if abs((ti - t).total_seconds()) <= 1800]
    if not v: continue
    d = v[0] - r["now"]
    tab["n"] += 1; tab["rose>=10"] += d >= 0.10; tab["rose>=20"] += d >= 0.20; tab["rose>0"] += d > 0
print({k: v for k, v in tab.items()}, {k: round(v / tab['n'], 2) for k, v in tab.items() if k != 'n'})
