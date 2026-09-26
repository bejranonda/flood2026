"""FastAPI backend + static Thai web app. Run: uvicorn floodwatch.api:app --host 127.0.0.1 --port 3000"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import os
import re
import secrets
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from floodwatch import __version__, ai, db, point
from floodwatch.config import DATUM_SUSPECT, RAIN_POINTS
from floodwatch.forecast import classify_status

app = FastAPI(title="BKK FloodWatch API", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
WEB_DIR = Path(os.environ.get("WEB_DIR", Path(__file__).resolve().parents[3] / "web"))
CACHE = {"Cache-Control": "public, max-age=60, stale-while-revalidate=300"}
STALE_MIN = 180  # observation older than this is shown as stale
UNKNOWN_AFTER_MIN = 24 * 60  # older than this, the last status says nothing about now -> "unknown"


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
    return _json({"version": __version__, "now": dt.datetime.now(dt.timezone.utc).isoformat(), "latest_observation": _iso(last),
                  "latest_observation_age_min": _age_min(last),
                  "sources": [{k: (_iso(v) if isinstance(v, dt.datetime) else v) for k, v in r.items()} for r in rows]},
                 cache=False)


STATIONS_SQL = """
SELECT s.code, s.name_th, s.name_en, s.lat, s.lon, s.bank_msl, s.ground_msl, s.agency, s.province, s.amphoe,
       s.river, s.coord_source, s.coord_precision_km, o.obs_time, o.level_msl, o.discharge, o.situation_level,
       f.payload->>'trend12' AS trend12, (f.payload->>'delta12_median')::float AS delta12,
       f.payload->'recovery' AS recovery, f.issue_time AS forecast_time, q.raw_time, q.raw_flag
FROM station s
LEFT JOIN LATERAL (SELECT obs_time, level_msl, discharge, situation_level FROM observation
                   WHERE code=s.code AND level_msl IS NOT NULL AND quality_flag='ok'
                   ORDER BY obs_time DESC LIMIT 1) o ON true
LEFT JOIN LATERAL (SELECT payload, issue_time FROM forecast_run WHERE code=s.code
                   ORDER BY issue_time DESC LIMIT 1) f ON true
LEFT JOIN LATERAL (SELECT obs_time AS raw_time, quality_flag AS raw_flag FROM observation WHERE code=s.code
                   ORDER BY obs_time DESC LIMIT 1) q ON true
WHERE (%(all)s OR s.in_focus) AND s.code !~ '^TEST'
"""


def _station_row(r: dict) -> dict:
    """One station for the UI. Misleading values are filtered, never the station: `notes` says what and why."""
    r = dict(r)
    notes = []
    if r["code"] in DATUM_SUSPECT:  # values not m MSL (KI-210): hide the level, keep the station
        notes.append("datum_suspect")
        r.update(level_msl=None, trend12=None, delta12=None, recovery=None)
    status, pct = classify_status(r["level_msl"], r["bank_msl"], r["ground_msl"])
    age = _age_min(r["obs_time"])
    if age is None or age > UNKNOWN_AFTER_MIN:
        status = "unknown"
        notes.append("no_recent_data")
    elif age > STALE_MIN:
        notes.append("stale")
    if r.get("raw_flag") not in (None, "ok") and (r["obs_time"] is None or r["raw_time"] > r["obs_time"]):
        notes.append("suspect_values_hidden")  # newest reading failed QC (e.g. BKK003 stuck at 7.45 m): KI-211
    if r["bank_msl"] is None:
        notes.append("no_bank")
    if r.get("lat") is None:
        notes.append("no_location")
    elif r.get("coord_source") == "osm_approx":
        notes.append("approx_location")
    return {
        "code": r["code"], "name_th": r["name_th"] or r["code"], "name_en": r["name_en"], "lat": r["lat"],
        "lon": r["lon"], "bank_msl": r["bank_msl"], "agency": r["agency"], "province": r["province"],
        "amphoe": r["amphoe"], "river": r["river"], "level_msl": r["level_msl"], "discharge": r["discharge"],
        "obs_time": _iso(r["obs_time"]), "age_min": age, "stale": age is None or age > STALE_MIN,
        "status": status, "pct_bank": None if pct is None else round(pct, 1),
        "freeboard_m": None if (r["level_msl"] is None or r["bank_msl"] is None) else round(r["bank_msl"] - r["level_msl"], 2),
        "trend12": r["trend12"], "delta12_median": r["delta12"], "recovery": r["recovery"],
        "forecast_time": _iso(r["forecast_time"]), "notes": notes,
        "coord_precision_km": r.get("coord_precision_km"),
    }


@app.get("/api/stations")
def stations(scope: str = Query("focus", pattern="^(focus|all)$")):
    with db.connect() as c:
        rows = c.execute(STATIONS_SQL, {"all": scope == "all"}).fetchall()
    return _json({"generated": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "stations": [_station_row(r) for r in rows]})  # all stations; bad values filtered per station


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
        fb = _feedback_counts(c, code).get(code)
    if code in DATUM_SUSPECT:  # KI-210: the station is shown, its non-MSL values are not
        obs, fc = [], None
    return _json({"station": _station_row(rows[0]), "feedback7d": fb,
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


def _load_chainage() -> dict:
    """River km from the mouth for Chao Phraya gauges (scripts/build_chainage.py; approximate, ±10 km near branches)."""
    try:
        from importlib import resources
        import json as _j
        return _j.loads(resources.files("floodwatch").joinpath("data/chaophraya_chainage.json").read_text())["stations"]
    except Exception:
        return {}


CHAINAGE = _load_chainage()

STATS_SQL = """
SELECT s.in_focus, s.lat IS NOT NULL AS has_coords, s.bank_msl IS NOT NULL AS has_bank, o.obs_time
FROM station s
LEFT JOIN LATERAL (SELECT obs_time FROM observation WHERE code=s.code AND level_msl IS NOT NULL
                   AND quality_flag='ok' ORDER BY obs_time DESC LIMIT 1) o ON true
"""


def _freshness(times: list[dt.datetime | None]) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    ages = [None if t is None else (now - t).total_seconds() / 3600 for t in times]
    return {"total": len(ages), "h1": sum(a is not None and a <= 1 for a in ages),
            "h3": sum(a is not None and a <= 3 for a in ages), "h24": sum(a is not None and a <= 24 for a in ages),
            "older": sum(a is not None and a > 24 for a in ages), "never": sum(a is None for a in ages)}


@app.get("/api/stats")
def stats():
    """Compact network summary: reporting freshness (focus area and the whole HII network), status and trend
    counts for the focus area, metadata gaps, and the rain forecast for Bangkok."""
    return _json(_stats_data())


def _stats_data() -> dict:
    with db.connect() as c:
        rows = c.execute(STATS_SQL).fetchall()
        focus = [_station_row(r) for r in c.execute(STATIONS_SQL, {"all": False}).fetchall()]
        rain = c.execute(
            """SELECT max(mm) AS mm24 FROM (SELECT point, sum(precip_mm) AS mm FROM weather_forecast
               WHERE issue_time=(SELECT max(issue_time) FROM weather_forecast) AND point LIKE 'bkk%%'
                 AND valid_time BETWEEN now() AND now() + interval '24 hours' GROUP BY point) x""").fetchone()
    status = {k: 0 for k in ("critical", "warning", "watch", "normal", "unknown")}
    trend = {k: 0 for k in ("rising", "falling", "steady", "unknown")}
    for s in focus:
        status[s["status"]] += 1
        trend[s["trend12"] if s["trend12"] in trend else "unknown"] += 1
    frows = [r for r in rows if r["in_focus"]]
    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(), "version": __version__,
        "focus": {**_freshness([r["obs_time"] for r in frows]), "status": status, "trend12": trend,
                  "no_coords": sum(not r["has_coords"] for r in frows),
                  "no_bank": sum(not r["has_bank"] for r in frows)},
        "network": _freshness([r["obs_time"] for r in rows]),
        "rain_bkk_next24_mm_max": None if rain["mm24"] is None else round(rain["mm24"], 1),
    }


@app.get("/api/profile")
def profile():
    """Chao Phraya main stem, north to south: level vs bank at each gauge (1-D, no interpolation between gauges;
    APPROACH §2.9). chainage_km = approximate river km from the mouth along HII's centreline (±10 km near
    branches); stations without chainage fall back to latitude order."""
    with db.connect() as c:
        rows = c.execute(STATIONS_SQL + " AND s.river='แม่น้ำเจ้าพระยา' AND s.lat IS NOT NULL", {"all": False}).fetchall()
    items = [_station_row(r) for r in rows]
    for s in items:
        s["chainage_km"] = (CHAINAGE.get(s["code"]) or {}).get("chainage_km")
    items.sort(key=lambda s: (-(s["chainage_km"] if s["chainage_km"] is not None else s["lat"] * 100)))
    return _json({"river": "แม่น้ำเจ้าพระยา", "order": "north_to_south", "dist": "river_km_from_mouth_approx",
                  "stations": items})


# ---- Citizen feedback (privacy: no names/contacts, IP never stored; notes never published) ----
# Shared by all uvicorn workers; kept in .env, never in the DB, so stored hashes cannot be brute-forced back to
# IPs. With the date it makes the hash unlinkable across days. Fallback (unset): per process, weaker rate limit.
_SALT = os.environ.get("FEEDBACK_SALT", "").encode() or secrets.token_bytes(16)
FEEDBACK_PER_HOUR = 10


class FeedbackIn(BaseModel):
    code: str | None = Field(None, max_length=32)
    verdict: Literal["matches", "higher", "lower", "unsure"] | None = None
    depth: Literal["none", "ankle", "knee", "waist", "above"] | None = None
    note: str | None = Field(None, max_length=280)
    lat: float | None = Field(None, ge=5, le=21)
    lon: float | None = Field(None, ge=97, le=106)
    loc_source: Literal["gps", "pin"] | None = None
    website: str | None = Field(None, max_length=200)  # honeypot: humans never fill it


def _client_hash(request: Request) -> str:
    ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    return hashlib.sha256(_SALT + day.encode() + ip.encode()).hexdigest()[:32]


@app.post("/api/feedback")
def feedback(body: FeedbackIn, request: Request):
    if body.website:
        return _json({"ok": True}, cache=False)  # silently drop bots
    if not body.verdict and not body.depth and not (body.note or "").strip():
        raise HTTPException(422, "empty feedback")
    note = re.sub(r"[\x00-\x1f\x7f]", " ", body.note or "").strip() or None
    lat = None if body.lat is None or body.lon is None else round(body.lat, 3)
    lon = None if lat is None else round(body.lon, 3)
    who = _client_hash(request)
    with db.connect() as c:
        n = c.execute("SELECT count(*) AS n FROM user_feedback WHERE client_hash=%s AND created_at > now() - interval '1 hour'",
                      (who,)).fetchone()["n"]
        if n >= FEEDBACK_PER_HOUR:
            raise HTTPException(429, "too many reports, please try later")
        snap: dict = {}
        if body.code:
            rows = c.execute(STATIONS_SQL + " AND s.code=%(code)s", {"all": True, "code": body.code}).fetchall()
            if not rows:
                raise HTTPException(404, "unknown station")
            r = _station_row(rows[0])
            snap = {k: r[k] for k in ("level_msl", "obs_time", "status", "freeboard_m", "trend12", "delta12_median",
                                      "recovery", "forecast_time")}
        rules = ai.triage_rules(note)
        c.execute("""INSERT INTO user_feedback (code, verdict, depth, note, lat, lon, snapshot, client_hash,
                                                loc_source, rule_label)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (body.code, body.verdict, body.depth, note, lat, lon, Jsonb(snap), who,
                   body.loc_source if lat is not None else None, Jsonb(rules)))
        c.commit()
    # Instant, rule-based: if the note sounds like an emergency, the page shows hotlines right away.
    return _json({"ok": True, "urgent": rules["urgent"]}, cache=False)


def _feedback_counts(c, code: str | None = None, days: int = 7) -> dict:
    rows = c.execute(
        """SELECT code, verdict, depth, count(*) AS n FROM user_feedback
           WHERE created_at > now() - make_interval(days => %s) AND (%s::text IS NULL OR code=%s)
           GROUP BY 1, 2, 3""", (days, code, code)).fetchall()
    out: dict = {}
    for r in rows:
        d = out.setdefault(r["code"] or "_location", {"verdict": {}, "depth": {}, "n": 0})
        d["n"] += r["n"]
        if r["verdict"]:
            d["verdict"][r["verdict"]] = d["verdict"].get(r["verdict"], 0) + r["n"]
        if r["depth"]:
            d["depth"][r["depth"]] = d["depth"].get(r["depth"], 0) + r["n"]
    for d in out.values():  # flag for operator review, never an automatic model change
        v = d["verdict"]
        off = v.get("higher", 0) + v.get("lower", 0)
        d["review"] = off >= 3 and off > v.get("matches", 0)
    return out


@app.get("/api/feedback/summary")
def feedback_summary(days: int = Query(7, ge=1, le=90)):
    """Counts only (no notes, no locations): what users said about each station."""
    with db.connect() as c:
        return _json({"days": days, "stations": _feedback_counts(c, None, days)})


@app.get("/api/point")
def point_check(lat: float = Query(..., ge=5, le=21), lon: float = Query(..., ge=97, le=106)):
    """What can be said about a place with no gauge: gauges around it, an area category (not a water level),
    nearby citizen evidence and warnings (APPROACH §2.10, D-021)."""
    with db.connect() as c:
        rows = [_station_row(r) for r in c.execute(STATIONS_SQL, {"all": False}).fetchall()]
        box = {"lat0": lat - 0.01, "lat1": lat + 0.01, "lon0": lon - 0.01, "lon1": lon + 0.01}
        traffy = c.execute("""SELECT count(*) AS n FROM crowd_report WHERE is_flood AND report_time > now() - interval '6 hours'
                              AND lat BETWEEN %(lat0)s AND %(lat1)s AND lon BETWEEN %(lon0)s AND %(lon1)s""", box).fetchone()["n"]
        depths = {r["depth"]: r["n"] for r in c.execute(
            """SELECT depth, count(*) AS n FROM user_feedback WHERE depth IS NOT NULL AND lat IS NOT NULL
               AND created_at > now() - interval '24 hours'
               AND lat BETWEEN %(lat0)s AND %(lat1)s AND lon BETWEEN %(lon0)s AND %(lon1)s GROUP BY 1""", box).fetchall()}
        pt = min(RAIN_POINTS, key=lambda k: (RAIN_POINTS[k][0] - lat) ** 2 + (RAIN_POINTS[k][1] - lon) ** 2)
        rain = c.execute("""SELECT sum(precip_mm) AS mm FROM weather_forecast WHERE point=%s
                            AND issue_time=(SELECT max(issue_time) FROM weather_forecast)
                            AND valid_time BETWEEN now() AND now() + interval '24 hours'""", (pt,)).fetchone()["mm"]
    out = point.assess(lat, lon, rows, traffy, depths, None if rain is None else round(rain, 1))
    out["rain_point"] = pt
    return _json(out)


@app.get("/api/summary")
def summary():
    """One deterministic Thai sentence for the header and for sharing. Never AI-written (D-022)."""
    return _json({"text": ai.summary_text(_stats_data()), "by": "template"})


CANONICAL_HOST = "flood.autobahn.bot"      # main domain (D-017)
LEGACY_HOST = "flood.bejranonda.com"       # alias, same tunnel
# Off by default: while the main domain challenges non-browser clients (KI-506) a redirect would send link-preview
# crawlers and API users from the working alias into the challenge. Set REDIRECT_LEGACY_HOST=1 once Q18 is done.
REDIRECT_LEGACY = os.environ.get("REDIRECT_LEGACY_HOST", "0") == "1"


def _host(request: Request) -> str:
    return request.headers.get("host", "").split(":")[0].lower()


def page_for_host(html: str, host: str) -> str:
    """The alias declares itself canonical, so crawlers that open it are not sent to a host that challenges them."""
    if host == LEGACY_HOST:
        return html.replace(f"https://{CANONICAL_HOST}/", f"https://{LEGACY_HOST}/")
    return html


def legacy_redirect_target(host: str, path: str, query: str) -> str | None:
    """301 target for the legacy host when enabled. /api/health stays reachable for uptime monitors."""
    if not REDIRECT_LEGACY or host != LEGACY_HOST or path == "/api/health":
        return None
    return f"https://{CANONICAL_HOST}{path}" + (f"?{query}" if query else "")


@app.middleware("http")
async def legacy_redirect(request: Request, call_next):
    target = legacy_redirect_target(_host(request), request.url.path, request.url.query)
    if target:
        return RedirectResponse(target, status_code=301)
    return await call_next(request)


@app.get("/")
def index(request: Request):
    html = page_for_host((WEB_DIR / "index.html").read_text(), _host(request))
    return HTMLResponse(html, headers={"Cache-Control": "public, max-age=300"})


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
