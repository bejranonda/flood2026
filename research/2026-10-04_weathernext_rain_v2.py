"""WeatherNext 3 vs Open-Meteo rain at our 9 Bangkok-region rain points, judged against measured HII rain — the cheap way.
Probe 2 (research/2026-10-04_weathernext_probe2.log): one LITERAL point per query is pruned by geography (11.8 MB per init);
a join with a list of points scanned the whole partition (56 GB per init, probe 1). So: one query per point, the init
times as literals, a running byte total with a hard stop. Past data only, research only; nothing shown or served (D-069).
Run: docker compose run --rm --no-deps -T -v "$PWD/research:/r:ro" worker python /r/2026-10-04_weathernext_rain_v2.py [days]"""
import json, os, sys
from datetime import datetime, timedelta, timezone
import psycopg
from floodwatch import gcp
from floodwatch.config import RAIN_POINTS

CAP_GB = 15.0
key = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
proj, ds = os.environ["WEATHERNEXT_PROJECT"], os.environ["WEATHERNEXT_DATASET"]
billing = gcp.project_of(key) or proj
tok = gcp.access_token(key)
TABLE = f"`{proj}.{ds}.weathernext_3_0_0_0p1deg`"
total = 0


def q(sql):
    global total
    try:
        r = gcp.bq_query(sql, tok, billing, 180_000)
    except Exception as e:  # a long IN-list was refused with HTTP 403 (run 1); print the reason, never a secret
        body = getattr(e, "read", lambda: b"")().decode(errors="replace")[:300]
        sys.exit(f"query refused: {e} {body}")
    total += int(r.get("totalBytesProcessed", 0))
    if total > CAP_GB * 1e9:
        sys.exit(f"cap {CAP_GB} GB reached")
    return gcp.bq_rows(r)


now = datetime.now(timezone.utc)
# 1) archive depth at one point (literal predicates only)
lat0, lon0 = list(RAIN_POINTS.values())[0]
for back in ((30, 90, 180, 365) if "--archive" in sys.argv else ()):
    d = (now - timedelta(days=back)).strftime("%Y-%m-%d 00:00:00")
    rows = q(f"""SELECT COUNT(*) AS n FROM {TABLE} AS t, t.forecast AS f WHERE t.init_time = TIMESTAMP('{d}')
                 AND f.hours = 24 AND ST_INTERSECTS(t.geography_polygon, ST_GEOGPOINT({lon0}, {lat0}))""")
    print(f"archive {back:3d} days back ({d}): {'yes' if rows and int(rows[0]['n']) else 'no'}  [total {total / 1e9:.2f} GB]")

# 2) next-day rain per point: 00 UTC run of the day before, hours 17-40 = the Bangkok day 00-24 ICT
days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
inits = [(now - timedelta(days=d)).strftime("%Y-%m-%d 00:00:00") for d in range(1, days + 2)]
wn = {}
BATCH = 3  # 61 literal init times in one IN-list were refused (HTTP 403, run 1); 3 per query pass (22 MB)
for k, (la, lo) in RAIN_POINTS.items():
    for i in range(0, len(inits), BATCH):
        lit = ", ".join(f"TIMESTAMP('{x}')" for x in inits[i:i + BATCH])
        for r in q(f"""SELECT DATE(f.time, 'Asia/Bangkok') AS day, SUM(f.total_precipitation_1hr_mean) * 1000 AS mean_mm,
                         SUM(f.total_precipitation_1hr_p90) * 1000 AS p90_mm, COUNT(*) AS n
                       FROM {TABLE} AS t, t.forecast AS f
                       WHERE t.init_time IN ({lit}) AND f.hours BETWEEN 17 AND 40
                         AND ST_INTERSECTS(t.geography_polygon, ST_GEOGPOINT({lo}, {la}))
                       GROUP BY 1"""):
            if int(r["n"]) >= 24:
                wn[(k, r["day"])] = (float(r["mean_mm"]), float(r["p90_mm"]))
    print(f"point {k}: {sum(1 for x in wn if x[0] == k)} days  [total {total / 1e9:.2f} GB]", flush=True)

with psycopg.connect(os.environ["DATABASE_URL"]) as con:
    con.execute("SET default_transaction_read_only = on")
    om = {(p, str(d)): float(v) for p, d, v in con.execute(
        """SELECT point, (valid_time AT TIME ZONE 'Asia/Bangkok')::date, sum(day1) FROM rain_hindcast
           WHERE point = ANY(%s) AND valid_time > now() - make_interval(days => %s) GROUP BY 1, 2 HAVING count(*) = 24""",
        (list(RAIN_POINTS), days + 2))}
    obs = {}
    for k, (la, lo) in RAIN_POINTS.items():
        for d, v in con.execute(
                """SELECT day, avg(mm) FROM (SELECT code, (obs_time AT TIME ZONE 'Asia/Bangkok')::date AS day, sum(rain_1h) AS mm
                   FROM rain_obs WHERE obs_time > now() - make_interval(days => %s) AND rain_1h IS NOT NULL
                     AND (lat - %s)^2 + ((lon - %s) * cos(radians(%s)))^2 < (10/111.0)^2
                   GROUP BY 1, 2 HAVING count(*) >= 20) x GROUP BY 1""", (days + 2, la, lo, la)):
            obs[(k, str(d))] = float(v)
rows = [(k, wn[k][0], wn[k][1], om[k], obs[k]) for k in wn if k in om and k in obs]


def score(i):
    mae = sum(abs(r[i] - r[4]) for r in rows) / len(rows)
    bias = sum(r[i] - r[4] for r in rows) / len(rows)
    out = {"mae_mm": round(mae, 2), "bias_mm": round(bias, 2)}
    for thr in (10, 35):
        ev = [r for r in rows if r[4] >= thr]
        fc = [r for r in rows if r[i] >= thr]
        out[f">={thr}mm"] = {"observed_days": len(ev), "caught": sum(r[i] >= thr for r in ev), "forecast_days": len(fc),
                             "false_alarms": sum(r[4] < thr for r in fc)}
    return out


print(json.dumps({"pairs": len(rows), "days": days, "processed_gb": round(total / 1e9, 2),
                  "weathernext_mean": score(1) if rows else None, "weathernext_p90": score(2) if rows else None,
                  "openmeteo_day1": score(3) if rows else None}, indent=1))
