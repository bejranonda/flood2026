#!/usr/bin/env python3
"""Score HII's archived official forecasts (D-050) against what happened, next to "no change" and our own model.

Run on the server once issues have aged past the lead time (e.g. after 3+ days of collection):
    docker compose run --rm --no-deps -v "$PWD/scripts:/scripts" worker python /scripts/score_hii_forecast.py
For each station and lead (24/48/72 h): MAE of HII, of persistence, and of our median forecast issued nearest to
HII's issue time. Only stations/leads with matched observations are printed; nothing is written anywhere."""
from floodwatch import db, forecast

LEADS = (24, 48, 72)
SQL = """
SELECT e.code, e.unit, e.issue_time, e.value,
       round(extract(epoch FROM e.valid_time - e.issue_time) / 3600) AS lead,
       (SELECT CASE WHEN e.unit='m' THEN level_msl ELSE discharge END FROM observation o WHERE o.code=e.code
          AND o.quality_flag='ok' AND o.obs_time BETWEEN e.valid_time - interval '30 min' AND e.valid_time + interval '30 min'
          ORDER BY abs(extract(epoch FROM o.obs_time - e.valid_time)) LIMIT 1) AS obs,
       (SELECT CASE WHEN e.unit='m' THEN level_msl ELSE discharge END FROM observation o WHERE o.code=e.code
          AND o.quality_flag='ok' AND o.obs_time BETWEEN e.issue_time - interval '90 min' AND e.issue_time
          ORDER BY o.obs_time DESC LIMIT 1) AS obs0,
       (SELECT (f.payload->'path'->(round(extract(epoch FROM e.valid_time - f.issue_time) / 3600)::int - 1)->'q'->>2)::float
          FROM forecast_run f WHERE f.code=e.code AND e.unit='m'
          AND f.issue_time BETWEEN e.issue_time - interval '1 hour' AND e.issue_time + interval '1 hour'
          ORDER BY abs(extract(epoch FROM f.issue_time - e.issue_time)) LIMIT 1) AS ours
FROM external_forecast e
WHERE e.source='hii_fews' AND e.valid_time < now()
  AND round(extract(epoch FROM e.valid_time - e.issue_time) / 3600) = ANY(%s)
"""

with db.connect() as c:
    rows = c.execute(SQL, (list(LEADS),)).fetchall()
by = {}
for r in rows:
    if r["obs"] is None or r["obs0"] is None:
        continue
    by.setdefault((r["code"], r["unit"]), []).append(r)
if not by:
    print("No matched forecasts yet: HII issues must be older than the shortest lead (24 h) and have observations.")
for (code, unit), rs in sorted(by.items()):
    hii = forecast.score_external([(r["lead"], r["value"], r["obs"], r["obs0"]) for r in rs])
    ours = forecast.score_external([(r["lead"], r["ours"], r["obs"], r["obs0"]) for r in rs if r["ours"] is not None])
    issues = len({r["issue_time"] for r in rs})
    for lead, s in hii.items():
        o = ours.get(lead)
        print(f"{code:7} +{lead:>2}h issues={issues:<3} n={s['n']:<3} HII MAE {s['mae']:.3f} {unit} (skill {s['skill'] if s['skill'] is None else round(s['skill'], 2)})"
              f" | no-change {s['mae_persistence']:.3f}" + (f" | ours {o['mae']:.3f} (n={o['n']})" if o else ""))
