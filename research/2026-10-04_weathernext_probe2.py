"""Does a literal point (a constant ST_INTERSECTS) let BigQuery prune by geography? Probe 1 joined a list of points and
processed 56 GB for one init (research/2026-10-04_weathernext_probe.log). One init, one literal point. D-069: research only."""
import os
from datetime import datetime, timedelta, timezone
from floodwatch import gcp

key = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
proj, ds = os.environ["WEATHERNEXT_PROJECT"], os.environ["WEATHERNEXT_DATASET"]
billing = gcp.project_of(key) or proj
tok = gcp.access_token(key)
init = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
sql = f"""SELECT COUNT(*) AS n, SUM(f.total_precipitation_1hr_mean) * 1000 AS mm_mean
  FROM `{proj}.{ds}.weathernext_3_0_0_0p1deg` AS t, t.forecast AS f
  WHERE t.init_time = TIMESTAMP('{init}') AND f.hours BETWEEN 1 AND 72
    AND ST_INTERSECTS(t.geography_polygon, ST_GEOGPOINT(100.5, 13.75))"""
r = gcp.bq_query(sql, tok, billing, 120_000)
print(f"literal point, init {init}: {gcp.bq_rows(r)} — {int(r.get('totalBytesProcessed', 0)) / 1e6:.1f} MB processed, "
      f"cacheHit={r.get('cacheHit')}")
