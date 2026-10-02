#!/usr/bin/env python3
"""WeatherNext 3 rain vs Open-Meteo rain at our 9 Bangkok-region rain points, judged against measured HII rain.
Research only, past data only (>= 1 h old = CC BY 4.0). WeatherNext real-time rain is never shown or served (D-069).

Needs the owner steps in docs/OWNER_ACTIONS.md (WNEXT): service-account key in certs/, .env WEATHERNEXT_PROJECT/_DATASET.
Run in the worker container (stdlib + openssl; no Google libraries):

    docker compose run --rm --no-deps -v "$PWD/research:/r:ro" worker python /r/2026-10-02_weathernext_rain.py schema
    docker compose run --rm --no-deps -v "$PWD/research:/r:ro" worker python /r/2026-10-02_weathernext_rain.py run [days=60]

`schema` prints the table's columns (field names in the docs are ⚠️ until seen). `run` first does a dry run and stops if
the query would scan more than MAX_GB (BigQuery sandbox: 1 TB of queries per month), then compares daily totals:
WeatherNext (issued 00 UTC the day before; mean and p90 of 64 members) vs Open-Meteo previous-day forecast (rain_hindcast.day1)
vs the mean of HII rain gauges within 10 km of the point. Prints JSON only (no key, no token).
"""
from __future__ import annotations

import json
import os
import sys

import psycopg

from floodwatch import gcp
from floodwatch.config import RAIN_POINTS

MAX_GB = 50
TABLE = "weathernext_3_0_0_0p1deg"


def env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"{name} is empty (see docs/OWNER_ACTIONS.md, WNEXT)")
    return v


def main(mode: str, days: int) -> None:
    key = env("GOOGLE_APPLICATION_CREDENTIALS")
    proj, ds = env("WEATHERNEXT_PROJECT"), env("WEATHERNEXT_DATASET")
    billing = gcp.project_of(key) or proj
    tok = gcp.access_token(key)
    if mode == "schema":
        import urllib.request
        req = urllib.request.Request(f"{gcp.BQ}/projects/{proj}/datasets/{ds}/tables/{TABLE}",
                                     headers={"Authorization": f"Bearer {tok}"})
        t = json.load(urllib.request.urlopen(req, timeout=60))

        def walk(fields, pre=""):
            for f in fields:
                print(f"{pre}{f['name']}  {f['type']}  {f.get('mode', '')}")
                walk(f.get("fields", []), pre + "  ")
        walk(t["schema"]["fields"])
        print("rows:", t.get("numRows"), "bytes:", t.get("numBytes"), "partitioning:", t.get("timePartitioning"))
        return

    pts = ", ".join(f"STRUCT('{k}' AS point, ST_GEOGPOINT({lo}, {la}) AS g)" for k, (la, lo) in RAIN_POINTS.items())
    sql = f"""
      WITH pts AS (SELECT * FROM UNNEST([{pts}]))
      SELECT p.point, DATE(f.time, 'Asia/Bangkok') AS day,
             SUM(f.total_precipitation_1hr_mean) * 1000 AS wn_mean_mm,
             SUM(f.total_precipitation_1hr_p90) * 1000 AS wn_p90_mm, COUNT(*) AS hours
      FROM `{proj}.{ds}.{TABLE}` AS t, t.forecast AS f, pts AS p
      WHERE t.init_time >= TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), DAY), INTERVAL {days + 2} DAY)
        AND t.init_time < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
        AND EXTRACT(HOUR FROM t.init_time) = 0
        AND f.hours BETWEEN 17 AND 40          -- the next Bangkok day (00-24 ICT = 17-41 h after 00 UTC the day before)
        AND ST_INTERSECTS(t.geography_polygon, p.g)
      GROUP BY 1, 2"""
    dry = gcp._post(f"{gcp.BQ}/projects/{billing}/queries",
                    json.dumps({"query": sql, "useLegacySql": False, "dryRun": True}).encode(),
                    {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}, 90)
    gb = int(dry.get("totalBytesProcessed", 0)) / 1e9
    print(f"dry run: {gb:.1f} GB", file=sys.stderr)
    if gb > MAX_GB:
        sys.exit(f"query would scan {gb:.1f} GB > {MAX_GB} GB; narrow it (fewer days) before running")
    wn = {(r["point"], r["day"]): r for r in gcp.bq_rows(gcp.bq_query(sql, tok, billing, 120_000))}

    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        om = {(p, str(d)): v for p, d, v in con.execute(
            """SELECT point, (valid_time AT TIME ZONE 'Asia/Bangkok')::date, sum(day1) FROM rain_hindcast
               WHERE point = ANY(%s) AND valid_time > now() - make_interval(days => %s) GROUP BY 1, 2 HAVING count(*) = 24""",
            (list(RAIN_POINTS), days + 2))}
        obs = {}
        for k, (la, lo) in RAIN_POINTS.items():
            for d, v in con.execute(
                    """SELECT day, avg(mm) FROM (SELECT code, (obs_time AT TIME ZONE 'Asia/Bangkok')::date day, sum(rain_1h) mm
                       FROM rain_obs WHERE obs_time > now() - make_interval(days => %s) AND rain_1h IS NOT NULL
                         AND (lat - %s)^2 + ((lon - %s) * cos(radians(%s)))^2 < (10/111.0)^2
                       GROUP BY 1, 2 HAVING count(*) >= 20) x GROUP BY 1""", (days + 2, la, lo, la)):
                obs[(k, str(d))] = v
    rows = [(k, float(wn[k]["wn_mean_mm"]), float(wn[k]["wn_p90_mm"]), om[k], obs[k]) for k in wn if k in om and k in obs]

    def score(i):
        mae = sum(abs(r[i] - r[4]) for r in rows) / len(rows)
        hit = {}
        for thr in (10, 35):
            ev = [r for r in rows if r[4] >= thr]
            fc = [r for r in rows if r[i] >= thr]
            hit[f">={thr}mm"] = {"observed_days": len(ev), "caught": sum(r[i] >= thr for r in ev), "forecast_days": len(fc),
                                 "false_alarms": sum(r[4] < thr for r in fc)}
        return {"mae_mm": round(mae, 2), **hit}
    print(json.dumps({"pairs": len(rows), "days": days, "scanned_gb": round(gb, 1),
                      "weathernext_mean": score(1) if rows else None, "weathernext_p90": score(2) if rows else None,
                      "openmeteo_day1": score(3) if rows else None}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "schema", int(sys.argv[2]) if len(sys.argv) > 2 else 60)
