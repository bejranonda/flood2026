"""WeatherNext 3: what one forecast run costs to read, and how far back the archive goes (research only, past data only,
D-069). Every query is a single init time and prints totalBytesProcessed; nothing is shown or served.
Run: docker compose run --rm --no-deps -T -v "$PWD/research:/r:ro" worker python /r/2026-10-04_weathernext_probe.py"""
import json, os, sys
from datetime import datetime, timedelta, timezone
from floodwatch import gcp
from floodwatch.config import RAIN_POINTS

key = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
proj, ds = os.environ["WEATHERNEXT_PROJECT"], os.environ["WEATHERNEXT_DATASET"]
billing = gcp.project_of(key) or proj
tok = gcp.access_token(key)
TABLE = "weathernext_3_0_0_0p1deg"
total = 0


def q(sql):
    global total
    r = gcp.bq_query(sql, tok, billing, 120_000)
    b = int(r.get("totalBytesProcessed", 0))
    total += b
    return gcp.bq_rows(r), b


def one(init, pts):
    p = ", ".join(f"STRUCT('{k}' AS point, ST_GEOGPOINT({lo}, {la}) AS g)" for k, (la, lo) in pts)
    sql = f"""WITH pts AS (SELECT * FROM UNNEST([{p}]))
      SELECT p.point, COUNT(*) AS n, SUM(f.total_precipitation_1hr_mean) * 1000 AS mm_mean
      FROM `{proj}.{ds}.{TABLE}` AS t, t.forecast AS f, pts AS p
      WHERE t.init_time = TIMESTAMP('{init}') AND f.hours BETWEEN 1 AND 72 AND ST_INTERSECTS(t.geography_polygon, p.g)
      GROUP BY 1"""
    return q(sql)


now = datetime.now(timezone.utc)
y = (now - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
rows, b = one(y, list(RAIN_POINTS.items()))
print(f"1) init {y}, {len(RAIN_POINTS)} points: {len(rows)} rows, {b / 1e6:.1f} MB processed")
for r in rows[:3]:
    print("   ", r)
if b > 2e9:
    sys.exit("too costly per init: stop")
first = list(RAIN_POINTS.items())[:1]
for back in (30, 90, 180, 365, 540):
    d = (now - timedelta(days=back)).strftime("%Y-%m-%d 00:00:00")
    rows, b = one(d, first)
    print(f"2) init {d}: {'has data' if rows and int(rows[0]['n']) > 0 else 'no data'} ({b / 1e6:.1f} MB)")
    if total > 10e9:
        sys.exit("cumulative cap reached")
print(f"total processed {total / 1e9:.2f} GB")
