"""FastAPI backend + static Thai web app. Run: uvicorn floodwatch.api:app --host 127.0.0.1 --port 3000"""
from __future__ import annotations

import datetime as dt
import math
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from floodwatch import db
from floodwatch.forecast import classify_status

app = FastAPI(title="BKK FloodWatch API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
WEB_DIR = Path(os.environ.get("WEB_DIR", Path(__file__).resolve().parents[3] / "web"))
CACHE = {"Cache-Control": "public, max-age=60, stale-while-revalidate=300"}
STALE_MIN = 180  # observation older than this is shown as stale


def _json(data, cache: bool = True) -> JSONResponse:
    return JSONResponse(data, headers=CACHE if cache else {"Cache-Control": "no-store"})


def _age_min(t: dt.datetime | None) -> float | None:
    return None if t is None else round((dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 60, 1)


def _iso(t):
    return t.isoformat() if t else None


@app.get("/api/health")
def health():
    with db.connect() as c:
        rows = c.execute("SELECT * FROM source_health ORDER BY source").fetchall()
        last = c.execute("SELECT max(obs_time) AS t FROM observation").fetchone()["t"]
    return _json({"now": dt.datetime.now(dt.timezone.utc).isoformat(), "latest_observation": _iso(last),
                  "latest_observation_age_min": _age_min(last),
                  "sources": [{k: (_iso(v) if isinstance(v, dt.datetime) else v) for k, v in r.items()} for r in rows]},
                 cache=False)


STATIONS_SQL = """
SELECT s.code, s.name_th, s.name_en, s.lat, s.lon, s.bank_msl, s.ground_msl, s.agency, s.province, s.amphoe,
       s.river, o.obs_time, o.level_msl, o.discharge, o.situation_level,
       f.payload->>'trend12' AS trend12, (f.payload->>'delta12_median')::float AS delta12,
       f.payload->'recovery' AS recovery, f.issue_time AS forecast_time
FROM station s
LEFT JOIN LATERAL (SELECT obs_time, level_msl, discharge, situation_level FROM observation
                   WHERE code=s.code AND level_msl IS NOT NULL AND quality_flag='ok'
                   ORDER BY obs_time DESC LIMIT 1) o ON true
LEFT JOIN LATERAL (SELECT payload, issue_time FROM forecast_run WHERE code=s.code
                   ORDER BY issue_time DESC LIMIT 1) f ON true
WHERE (%(all)s OR s.in_focus)
"""


def _station_row(r: dict) -> dict:
    status, pct = classify_status(r["level_msl"], r["bank_msl"], r["ground_msl"])
    age = _age_min(r["obs_time"])
    return {
        "code": r["code"], "name_th": r["name_th"] or r["code"], "name_en": r["name_en"], "lat": r["lat"],
        "lon": r["lon"], "bank_msl": r["bank_msl"], "agency": r["agency"], "province": r["province"],
        "amphoe": r["amphoe"], "river": r["river"], "level_msl": r["level_msl"], "discharge": r["discharge"],
        "obs_time": _iso(r["obs_time"]), "age_min": age, "stale": age is None or age > STALE_MIN,
        "status": status, "pct_bank": None if pct is None else round(pct, 1),
        "freeboard_m": None if (r["level_msl"] is None or r["bank_msl"] is None) else round(r["bank_msl"] - r["level_msl"], 2),
        "trend12": r["trend12"], "delta12_median": r["delta12"], "recovery": r["recovery"],
        "forecast_time": _iso(r["forecast_time"]),
    }


@app.get("/api/stations")
def stations(scope: str = Query("focus", pattern="^(focus|all)$")):
    with db.connect() as c:
        rows = c.execute(STATIONS_SQL, {"all": scope == "all"}).fetchall()
    return _json({"generated": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "stations": [_station_row(r) for r in rows if r["level_msl"] is not None or r["code"] == "BKK008"]})


@app.get("/api/stations/{code}")
def station(code: str, days: int = Query(7, ge=1, le=35)):
    with db.connect() as c:
        rows = c.execute(STATIONS_SQL + " AND s.code=%(code)s", {"all": True, "code": code}).fetchall()
        if not rows:
            raise HTTPException(404, "unknown station")
        obs = c.execute(
            """SELECT obs_time, level_msl, discharge FROM observation WHERE code=%s AND quality_flag='ok'
               AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (code, days)).fetchall()
        fc = c.execute("SELECT payload FROM forecast_run WHERE code=%s ORDER BY issue_time DESC LIMIT 1",
                       (code,)).fetchone()
    return _json({"station": _station_row(rows[0]),
                  "observations": [[_iso(o["obs_time"]), o["level_msl"], o["discharge"]] for o in obs],
                  "forecast": fc["payload"] if fc else None})


def _haversine_km(a_lat, a_lon, b_lat, b_lon) -> float:
    p = math.pi / 180
    h = (math.sin((b_lat - a_lat) * p / 2) ** 2
         + math.cos(a_lat * p) * math.cos(b_lat * p) * math.sin((b_lon - a_lon) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


@app.get("/api/near")
def near(lat: float = Query(..., ge=5, le=21), lon: float = Query(..., ge=97, le=106), n: int = Query(3, ge=1, le=10)):
    """Nearest stations by distance. ⚠️ Polder/controlling-water-body logic not implemented yet (APPROACH §13)."""
    with db.connect() as c:
        rows = c.execute(STATIONS_SQL, {"all": False}).fetchall()
    items = [(_haversine_km(lat, lon, r["lat"], r["lon"]), r) for r in rows if r["lat"] is not None and r["level_msl"] is not None]
    items.sort(key=lambda x: x[0])
    return _json({"note": "nearest_by_distance_only", "stations": [{**_station_row(r), "distance_km": round(d, 1)}
                                                                   for d, r in items[:n]]})


@app.get("/api/reports")
def reports(hours: int = Query(6, ge=1, le=48)):
    """Aggregated Traffy flood reports per ~1 km cell (privacy: counts only; KI-107)."""
    with db.connect() as c:
        rows = c.execute(
            """SELECT round(lat::numeric, 2) AS lat, round(lon::numeric, 2) AS lon, count(*) AS n
               FROM crowd_report WHERE is_flood AND report_time > now() - make_interval(hours => %s)
               GROUP BY 1, 2 ORDER BY n DESC""", (hours,)).fetchall()
    return _json({"hours": hours, "cells": [[float(r["lat"]), float(r["lon"]), r["n"]] for r in rows]})


@app.get("/api/rain")
def rain():
    with db.connect() as c:
        rows = c.execute(
            """SELECT point, sum(precip_mm) FILTER (WHERE valid_time <= now() + interval '24 hours') AS mm24,
                      sum(precip_mm) FILTER (WHERE valid_time <= now() + interval '72 hours') AS mm72,
                      max(issue_time) AS issue
               FROM weather_forecast WHERE issue_time=(SELECT max(issue_time) FROM weather_forecast)
                 AND valid_time > now() GROUP BY point""").fetchall()
    return _json({"source": "Open-Meteo", "points": [{"point": r["point"], "mm24": r["mm24"], "mm72": r["mm72"],
                                                      "issue_time": _iso(r["issue"])} for r in rows]})


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "public, max-age=300"})


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
