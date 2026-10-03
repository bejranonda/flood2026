"""FastAPI backend + static Thai web app. Run: uvicorn floodwatch.api:app --host 127.0.0.1 --port 3000"""
from __future__ import annotations

import datetime as dt
import hashlib
import logging
import math
import os
import re
import secrets
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from floodwatch import __version__, ai, db, explain, geocode, point
from floodwatch.config import DATUM_SUSPECT
from floodwatch import rain_cells, regions
from floodwatch import rivers as rivers_mod
from floodwatch.forecast import change_summary, classify_status

PRIVATE_QUERY_PATHS = ("/api/geocode", "/api/point", "/api/reverse", "/api/near", "/api/explain")


class RedactQuery(logging.Filter):
    """Access logs must not keep what people search for or where they are (D-032): drop the query string of these
    endpoints from uvicorn's access record (args = client, method, path, http version, status)."""
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str) and "?" in args[2]:
            path = args[2].split("?", 1)[0]
            if path in PRIVATE_QUERY_PATHS:
                record.args = (*args[:2], path + "?…", *args[3:])
        return True


logging.getLogger("uvicorn.access").addFilter(RedactQuery())

app = FastAPI(title="BKK FloodWatch API", description="Water levels of canals and rivers across Thailand (1,000+ gauges) compared with the bank, with backtested 12–48 h forecasts. Free, no key. Not an official warning.", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
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


# Live feeds whose newest *reading* (not the fetch) must be recent; beyond this the source stopped upstream although the
# fetch succeeds (2026-10-01: the BMA relay answered every 10 min with readings stuck at 17:10 UTC for 4.5 h).
DATA_STALE_AFTER_H = {"bma_klong": 1.0, "hii_waterlevel": 3.0, "hii_rain": 3.0}


def stale_sources(rows: list[dict], now: dt.datetime) -> list[str]:
    return sorted(r["source"] for r in rows if r["source"] in DATA_STALE_AFTER_H and r.get("last_data_time")
                  and (now - r["last_data_time"]).total_seconds() > DATA_STALE_AFTER_H[r["source"]] * 3600)


@app.get("/api/health")
def health():
    with db.connect() as c:
        rows = c.execute("SELECT * FROM source_health ORDER BY source").fetchall()
        # flagged and future-stamped readings are not "latest" (KI-247: 28 HII rows stamped ~21 h ahead)
        last = c.execute("""SELECT max(obs_time) AS t FROM observation WHERE quality_flag='ok'
                            AND obs_time <= now() + interval '15 minutes'""").fetchone()["t"]
    now = dt.datetime.now(dt.timezone.utc)
    return _json({"version": __version__, "now": now.isoformat(), "latest_observation": _iso(last),
                  "stale_sources": stale_sources(rows, now),  # for an uptime monitor: a non-empty list = data stopped
                  "latest_observation_age_min": _age_min(last),
                  "sources": [{k: (_iso(v) if isinstance(v, dt.datetime) else v) for k, v in r.items()} for r in rows]},
                 cache=False)


STATIONS_SQL = """
SELECT s.code, s.in_focus, s.name_th, s.name_en, s.lat, s.lon, s.bank_msl, s.ground_msl, s.critical_msl, s.warning_msl, s.agency, s.province, s.amphoe,
       s.river, s.coord_source, s.coord_precision_km, o.obs_time, o.level_msl, o.discharge, o.situation_level,
       f.payload->>'trend12' AS trend12, (f.payload->>'delta12_median')::float AS delta12,
       f.payload->'recovery' AS recovery, f.issue_time AS forecast_time, q.raw_time, q.raw_flag, h.first_time,
       (f.payload->>'level_now')::float AS fc_now, f.payload->'path'->11->'q' AS q12, f.payload->'path'->23->'q' AS q24,
       f.payload->'path'->47->'q' AS q48,
       f.payload->'skill'->'12' AS sk12, f.payload->'skill'->'24' AS sk24, f.payload->'skill'->'48' AS sk48,
       f.payload->'outlook24' AS outlook24,
       p.prev_time, p.prev_level,
       (SELECT value->s.code FROM collector_state WHERE key='erratic_gauges') AS erratic,
       (SELECT value->s.code FROM collector_state WHERE key='observed24') AS observed24
FROM station s
LEFT JOIN LATERAL (SELECT obs_time, level_msl, discharge, situation_level FROM observation
                   WHERE code=s.code AND level_msl IS NOT NULL AND quality_flag='ok'
                   ORDER BY obs_time DESC LIMIT 1) o ON true
LEFT JOIN LATERAL (SELECT payload, issue_time FROM forecast_run WHERE code=s.code
                   ORDER BY issue_time DESC LIMIT 1) f ON true
LEFT JOIN LATERAL (SELECT obs_time AS raw_time, quality_flag AS raw_flag FROM observation WHERE code=s.code
                   ORDER BY obs_time DESC LIMIT 1) q ON true
LEFT JOIN LATERAL (SELECT obs_time AS first_time FROM observation WHERE code=s.code
                   ORDER BY obs_time ASC LIMIT 1) h ON true
LEFT JOIN LATERAL (SELECT obs_time AS prev_time, level_msl AS prev_level FROM observation
                   WHERE code=s.code AND quality_flag='ok' AND level_msl IS NOT NULL
                     AND obs_time BETWEEN o.obs_time - interval '3 hours' AND o.obs_time - interval '1 hour'
                   ORDER BY obs_time ASC LIMIT 1) p ON true
WHERE (%(all)s OR s.in_focus) AND s.code !~ '^TEST'
"""


ROWS_TTL_S = 60  # the station list is shared by all requests for a minute (collectors refresh every 10 min)
_rows_cache: dict[bool, tuple[float, list]] = {}
_rows_lock = threading.Lock()


def _station_rows(all_: bool) -> list[dict]:
    """STATIONS_SQL once per minute, shared by /stations, /stats, /point, /near, /profile and station sheets.
    2026-09-30: ~10 requests/s each ran the 2-3 s query; 39 ran at once, Postgres hit max_connections (40),
    /api/health returned 500 and the worker restarted 452 times (KI-246). The lock makes a burst wait for one query."""
    hit = _rows_cache.get(all_)
    if hit and time.monotonic() - hit[0] < ROWS_TTL_S:
        return hit[1]
    with _rows_lock:
        hit = _rows_cache.get(all_)
        if hit and time.monotonic() - hit[0] < ROWS_TTL_S:
            return hit[1]
        with db.connect() as c:
            rows = c.execute(STATIONS_SQL, {"all": all_}).fetchall()
        _rows_cache[all_] = (time.monotonic(), rows)
        return rows


_memo_cache: dict = {}
_memo_lock = threading.RLock()  # re-entrant: a memoised payload may use another (twins inside the list)


def _memo(key, fn, ttl: float = ROWS_TTL_S):
    """The same payload for everyone for `ttl` seconds (list, stats, street cells): one DB round per minute instead
    of one per visitor (KI-246). Ages inside the payload may be up to a minute old; the UI rounds to minutes."""
    hit = _memo_cache.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    with _memo_lock:
        hit = _memo_cache.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        val = fn()
        _memo_cache[key] = (time.monotonic(), val)
        return val


def bma_status(level: float | None, bank: float | None, warning: float | None,
               critical: float | None) -> tuple[str, float | None]:
    """BMA canal gauges are judged by BMA's own drainage levels, not only the bank (D-038, owner 2026-09-26).
    Canals rarely overtop their walls; streets flood when the canal is too full to take the drains' water. On
    2026-09-26 60 % of gauges near flooded streets were above BMA 'critical' vs 18 % above the bank.
    critical (red) = over the bank · warning (orange) = over BMA critical ("คลองเต็ม") ·
    watch (amber) = over BMA warning ("คลองเริ่มเต็ม") · normal (blue) = below both ("คลองยังรับน้ำได้")."""
    if level is None:
        return "unknown", None
    over = None if critical is None else round(level - critical, 2)
    if bank is not None and level > bank:
        return "critical", over
    if critical is not None and level > critical:
        return "warning", over
    if warning is not None and level > warning:
        return "watch", over
    if bank is None and critical is None:
        return "unknown", over
    return "normal", over


def _observed_change(r: dict) -> dict:
    lvl, prev, t, tp = r.get("level_msl"), r.get("prev_level"), r.get("obs_time"), r.get("prev_time")
    if lvl is None or prev is None or t is None or tp is None:
        return {"change_m": None, "change_hours": None}
    return {"change_m": round(lvl - prev, 2), "change_hours": round((t - tp).total_seconds() / 3600, 1)}


TREND_WORDS = {"small_fall", "fall", "strong_fall", "small_rise", "rise", "strong_rise"}


def follow_measured(ch: dict | None, obs24: dict | None, sk: dict | None, h: int = 24) -> dict | None:
    """12/24 h rows follow the measured 24 h trend where no model gives a direction (owner 2026-09-28, D-060: "there
    is a trend of lowering water level in the chart, but it said ทรงตัว and ? ไม่แน่ชัด"). The row then says what the
    level has been doing (qc.observed24), with the range this gauge showed after such trends (forecast.continuation)
    and how often they continued (`hit`, shown in the ⓘ; canals ~6 in 10, rivers ~9 in 10)."""
    if not ch or not obs24 or obs24.get("level") not in TREND_WORDS:
        return ch
    lk = ch.get("likely")
    agrees = not lk or (lk[1] < 0 if ch.get("dir") == "falling" else lk[0] > 0 if ch.get("dir") == "rising" else False)
    if ch.get("method") != "persistence" and ch.get("level") != "steady" and agrees:
        return ch  # a model that beat "no change" and sees a direction its whole likely range agrees with keeps its word
    d = "fall" if obs24["level"].endswith("fall") else "rise"
    c = ((sk or {}).get("cont") or {}).get(d) or {}
    # The number is the measured trend continued and damped (as forecast "tide_trend": slope·h·e^(−h/48)), so word,
    # number and label say the same thing (owner 2026-09-28: keep numbers; "prove the consistency"). The past range
    # after such trends often leans the other way (canals rebound), so it is not printed next to the word.
    rate = obs24["change_cm"] / 100 / (obs24.get("hours") or 24)
    v = round(rate * h * math.exp(-h / 48.0), 2)
    cm = abs(round(v * 100))
    if cm < 1:
        return ch
    size = "small_" if cm < 5 else "strong_" if cm >= 20 else ""
    return {**ch, "dir": "falling" if d == "fall" else "rising", "level": size + d, "basis": "measured_trend",
            "median": v, "likely": [v, v], "range90": None, "wide": False,
            "hit": c.get("hit"), "hit_n": c.get("n")}


def _model_direction(ch: dict | None) -> str | None:
    """The direction a backtested model proved for a row (the keep-condition of follow_measured), else None."""
    if not ch or ch.get("basis") == "measured_trend" or ch.get("method") in (None, "persistence") or ch.get("level") == "steady":
        return None
    lk = ch.get("likely")
    if ch.get("dir") == "falling" and (not lk or lk[1] < 0):
        return "falling"
    if ch.get("dir") == "rising" and (not lk or lk[0] > 0):
        return "rising"
    return None


def reconcile_rows(raw: dict, followed: dict) -> dict:
    """A measured-trend row (D-060 heuristic) never contradicts a direction a model proved at another horizon of the
    same gauge: it falls back to the model's own reading there (2026-10-01: TRD001 read ⬆ / ⬇ / ⬆ at 12/24/48 h;
    63 of 719 gauges flipped, 43 of them model vs measured). Model vs model stays (tides, rain arriving later)."""
    proven = {_model_direction(c) for c in followed.values()} - {None}
    out = {}
    for h, c in followed.items():
        flip = c and c.get("basis") == "measured_trend" and c.get("dir") in ("rising", "falling") and \
            ({"rising", "falling"} - {c["dir"]}) & proven
        out[h] = raw.get(h) if flip else c
    return out


def _change_fields(r: dict, status: str) -> dict:
    """Rise/fall, how much and how sure at +12 h and +24 h, from the stored forecast (D-047). Nothing for a gauge
    whose data are too old to judge; a peak window only where a tide model makes the path vary (outlook24)."""
    if status == "unknown" or r.get("fc_now") is None:
        return {"change12": None, "change24": None, "change48": None, "peak_h": None}
    o = r.get("outlook24") or {}
    c48 = change_summary(r.get("q48"), r["fc_now"], r.get("sk48"))
    obs = r.get("observed24")
    # 48 h everywhere a forecast exists (owner 2026-09-27, amends D-050). `proven` (medium confidence) is kept
    # for API users only: since D-056 the UI shows a direction whenever a real model beat "no change" and ignores it.
    raw = {12: change_summary(r.get("q12"), r["fc_now"], r.get("sk12")),
           24: change_summary(r.get("q24"), r["fc_now"], r.get("sk24")),
           48: None if not c48 else {**c48, "proven": c48["confidence"] == "medium"}}
    rows = reconcile_rows(raw, {h: follow_measured(c, obs, r.get(f"sk{h}"), h) for h, c in raw.items()})
    return {"change12": rows[12], "change24": rows[24], "change48": rows[48],
            # A peak 1-2 h out means "highest now, falling after": saying "สูงสุดราว …" there would mislead.
            "peak_h": o.get("peak_h") if (o.get("varies") and (o.get("peak_h") or 0) >= 3) else None}


def upstream_map(learned: dict, chain: dict) -> dict[str, list[dict]]:
    """{gauge: [{code, lag_h}]}: learned upstream gauges (same basin and river system, leading change; forecast.upstream)
    and, on the Chao Phraya chain, the gauges up the river (travel time not learned there)."""
    from floodwatch.forecast import upstream_of
    out = {k: [{"code": u[0], "lag_h": int(u[1])} for u in v] for k, v in (learned or {}).items()}
    for code in chain:
        if code not in out:
            ups = upstream_of(code, chain)
            if ups:
                out[code] = [{"code": u, "lag_h": None} for u in ups]
    return out


def _upstream() -> dict[str, list[dict]]:
    def build():
        from floodwatch.forecast import _chainage
        try:
            with db.connect() as c:
                learned = db.get_state(c, "upstream_learned") or {}
        except Exception:  # never let this optional line break the station list
            logging.getLogger(__name__).exception("upstream map unavailable")
            learned = {}
        return upstream_map(learned, _chainage())
    return _memo(("upstream_map",), build, ttl=600)


def _station_row(r: dict) -> dict:
    """One station for the UI. Misleading values are filtered, never the station: `notes` says what and why."""
    r = dict(r)
    notes = []
    if r["code"] in DATUM_SUSPECT:  # values not m MSL (KI-210): hide the level, keep the station
        notes.append("datum_suspect")
        r.update(level_msl=None, trend12=None, delta12=None, recovery=None, q12=None, q24=None, q48=None)
    elif r.get("erratic"):  # jumps back and forth (pumps at the sensor, or a faulty sensor), or stuck at one value
        notes.append("stuck" if (r["erratic"] or {}).get("kind") == "stuck" else "erratic")  # KI-237, KI-241
        r.update(level_msl=None, trend12=None, delta12=None, recovery=None, q12=None, q24=None, q48=None, fc_now=None)
    if notes:  # datum_suspect / erratic: no measured change either
        r["observed24"] = None
    status, pct = classify_status(r["level_msl"], r["bank_msl"], r["ground_msl"])
    basis, over_crit = "bank", None
    if r.get("agency") == "BMA":
        status, over_crit = bma_status(r["level_msl"], r["bank_msl"], r.get("warning_msl"), r.get("critical_msl"))
        basis = "bma_thresholds"
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
        "region": regions.region_of(r["province"]), "water": point.water_word(r), "in_focus": r.get("in_focus"),
        "upstream": _upstream().get(r["code"]),
        "lon": r["lon"], "bank_msl": r["bank_msl"], "agency": r["agency"], "province": r["province"],
        "amphoe": r["amphoe"], "river": r["river"], "level_msl": r["level_msl"], "discharge": r["discharge"],
        "obs_time": _iso(r["obs_time"]), "age_min": age, "stale": age is None or age > STALE_MIN,
        "status": status, "pct_bank": None if pct is None else round(pct, 1),
        "freeboard_m": None if (r["level_msl"] is None or r["bank_msl"] is None) else round(r["bank_msl"] - r["level_msl"], 2),
        "trend12": r["trend12"], "delta12_median": r["delta12"], "recovery": r["recovery"],
        **_change_fields(r, status),
        "forecast_time": _iso(r["forecast_time"]), "notes": notes,
        "coord_precision_km": r.get("coord_precision_km"),
        # When our record of this gauge begins. New gauges (e.g. BMA since 2026-09-26) have no chart or forecast yet;
        # the UI says so instead of showing an empty chart that looks like lost data.
        "status_basis": basis,  # "bank" or "bma_thresholds" (D-038): the UI names the yardstick
        "bma_critical_msl": r.get("critical_msl") if basis == "bma_thresholds" else None,
        "over_bma_critical_m": over_crit,
        "history_since": _iso(r.get("first_time")),
        # Observed change over the last 1-3 h: a trend from readings, available after an hour, long before a
        # forecast (which needs 7 days). Not a prediction; the UI says "ที่ผ่านมา" (owner: users want the trend).
        **_observed_change(r),
        # What the level did over the last 24 h, measured (qc.observed24): {change_cm, r2, level}; a fact, not a forecast.
        # Few cm matter in a flood (owner 2026-09-28), so small steady changes get their own words in the UI.
        "observed24": r.get("observed24"),
        "history_days": None if r.get("first_time") is None else round(_age_min(r["first_time"]) / 1440, 1),
    }


STREET_HOURS, STREET_KM = 6, 1.0


def _street_reports(c) -> list[tuple[float, float]]:
    """Traffy flood reports of the last STREET_HOURS (locations only; KI-107)."""
    return [(r["lat"], r["lon"]) for r in c.execute(
        """SELECT lat, lon FROM crowd_report WHERE is_flood AND lat IS NOT NULL
           AND report_time > now() - make_interval(hours => %s)""", (STREET_HOURS,)).fetchall()]


def street_counts(items: list[dict], reports: list[tuple[float, float]]) -> None:
    """Add `street_reports_6h` to each station: street-flood reports within STREET_KM. A khlong gauge measures the
    canal against its bank, not the street: canals are often pumped down while streets flood from rain the drains
    can't take (KNOWLEDGE §4), so both facts are shown side by side instead of one hiding the other (D-036)."""
    deg = STREET_KM / 111.0
    for s in items:
        if s.get("lat") is None or s.get("lon") is None:
            s["street_reports_6h"] = None
            continue
        s["street_reports_6h"] = sum(1 for la, lo in reports if abs(la - s["lat"]) <= deg and abs(lo - s["lon"]) <= deg * 1.03
                                     and point.haversine_km(s["lat"], s["lon"], la, lo) <= STREET_KM)


def _traffy_age_min(c) -> float | None:
    r = c.execute("SELECT last_success FROM source_health WHERE source='traffy'").fetchone()
    return _age_min(r["last_success"]) if r else None


TWIN_KM = 0.3  # two agencies' gauges this close measure the same place (E.29A RID / URTU07 EGAT, 2026-09-30)


def find_twins(rows: list[dict]) -> dict[str, dict]:
    """{code: {code, name_th, agency}} of the nearest other-agency gauge within TWIN_KM. Linked in the UI, never
    merged: each keeps its own bank and datum (KI-217)."""
    placed = [r for r in rows if r.get("lat") is not None and r.get("lon") is not None]
    cells: dict[tuple[int, int], list[dict]] = {}
    for r in placed:
        cells.setdefault((int(r["lat"] * 100), int(r["lon"] * 100)), []).append(r)  # ~1 km cells
    out = {}
    for r in placed:
        ci, cj = int(r["lat"] * 100), int(r["lon"] * 100)
        best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for o in cells.get((ci + di, cj + dj), []):
                    if o["code"] == r["code"] or o.get("agency") == r.get("agency"):
                        continue
                    d = _haversine_km(r["lat"], r["lon"], o["lat"], o["lon"])
                    if d <= TWIN_KM and (best is None or d < best[0]):
                        best = (d, o)
        if best:
            o = best[1]
            out[r["code"]] = {"code": o["code"], "name_th": o.get("name_th") or o["code"], "agency": o.get("agency")}
    return out


def _twins() -> dict[str, dict]:
    return _memo(("twins",), lambda: find_twins(_station_rows(True)))


@app.get("/api/stations")
def stations(scope: str = Query("all", pattern="^(focus|all)$")):
    # Rebuilt whenever the shared rows refresh, so the list and a pin panel come from the same snapshot (a separate
    # 60 s memo on top of the 60 s rows cache let them differ by up to 2 min: C1 findings 2026-10-01).
    all_ = scope == "all"
    _station_rows(all_)
    stamp = (_rows_cache.get(all_) or (0.0,))[0]
    hit = _memo_cache.get(("stations", scope))
    if not hit or hit[2] != stamp:
        with _memo_lock:
            hit = _memo_cache.get(("stations", scope))
            if not hit or hit[2] != stamp:
                hit = (time.monotonic(), _stations_data(scope), stamp)
                _memo_cache[("stations", scope)] = hit
    return _json(hit[1])


def _stations_data(scope: str) -> dict:
    with db.connect() as c:
        rows = _station_rows(scope == "all")
        reps, tage = _street_reports(c), _traffy_age_min(c)
    tw = _twins()
    items = [{**_station_row(r), "twin": tw.get(r["code"])} for r in rows]  # all stations; bad values filtered per station
    street_counts(items, reps)
    return {"generated": dt.datetime.now(dt.timezone.utc).isoformat(), "stations": items,
            "street_source": {"name": "Traffy Fondue", "hours": STREET_HOURS, "km": STREET_KM,
                              "last_update_age_min": tage}}


@app.get("/api/stations/{code}")
def station(code: str, days: int = Query(7, ge=1, le=35)):
    with db.connect() as c:
        rows = [r for r in _station_rows(True) if r["code"] == code]
        if not rows:
            raise HTTPException(404, "unknown station")
        obs = c.execute(
            """SELECT obs_time, level_msl, discharge FROM observation WHERE code=%s AND quality_flag='ok'
               AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (code, days)).fetchall()
        fc = c.execute("SELECT payload FROM forecast_run WHERE code=%s ORDER BY issue_time DESC LIMIT 1",
                       (code,)).fetchone()
        fb = _feedback_counts(c, code).get(code)
        reps, tage = _street_reports(c), _traffy_age_min(c)
    srow = {**_station_row(rows[0]), "twin": _twins().get(code)}
    street_counts([srow], reps)
    srow["street_source_age_min"] = tage
    if code in DATUM_SUSPECT:  # KI-210: the station is shown, its non-MSL values are not
        obs, fc = [], None
    elif {"erratic", "stuck"} & set(srow["notes"]):  # KI-237/241: the measured chart shows why; a forecast would mislead
        fc = None
    return _json({"station": srow, "feedback7d": fb,
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
        rows = _station_rows(True)
    items = [(_haversine_km(lat, lon, r["lat"], r["lon"]), r) for r in rows if r["lat"] is not None and r["level_msl"] is not None]
    items.sort(key=lambda x: x[0])
    return _json({"note": "nearest_by_distance_only", "stations": [{**_station_row(r), "distance_km": round(d, 1)}
                                                                   for d, r in items[:n]]})


@app.get("/api/reports")
def reports(hours: int = Query(6, ge=1, le=48)):
    """Aggregated Traffy flood reports per ~1 km cell (privacy: counts only; KI-107)."""
    return _json(_memo(("reports", hours), lambda: _reports_data(hours)))


def _reports_data(hours: int) -> dict:
    with db.connect() as c:
        rows = c.execute(
            """SELECT round(lat::numeric, 2) AS lat, round(lon::numeric, 2) AS lon, count(*) AS n
               FROM crowd_report WHERE is_flood AND report_time > now() - make_interval(hours => %s)
               GROUP BY 1, 2 ORDER BY n DESC""", (hours,)).fetchall()
        tage = _traffy_age_min(c)
    return {"hours": hours, "cells": [[float(r["lat"]), float(r["lon"]), r["n"]] for r in rows],
            "last_update_age_min": tage}


# Bangkok-area rain points by region chip (config.RAIN_POINTS); 0.5° cells get the region of their nearest gauge
RAIN_POINT_REGION = {"bkk_central": "bkk", "bkk_east": "bkk", "bkk_north": "bkk", "bkk_west": "bkk",
                     "samut_sakhon_nakhon_pathom": "metro", "nonthaburi_pathum": "metro",
                     "ayutthaya": "up", "chainat": "up", "nakhon_sawan": "up"}


def rain_by_region(points: list[dict], measured: list[dict], cell_region: dict[str, str]) -> dict:
    """For the summary line of each region chip (owner 2026-10-01: "There is no rain in panel anymore?"): the wettest
    forecast point/cell (mm in the next 24 h) and the wettest rain gauge (mm in the last 24 h); "all" = the country."""
    out: dict[str, dict] = {}
    for p in points:
        if p.get("mm24") is None:
            continue
        for r in {RAIN_POINT_REGION.get(p["point"]) or cell_region.get(p["point"]), "all"} - {None}:
            o = out.setdefault(r, {"forecast_mm24": None, "measured": None})
            if o["forecast_mm24"] is None or p["mm24"] > o["forecast_mm24"]:
                o["forecast_mm24"] = round(p["mm24"], 1)
    for m in measured:
        if m.get("rain_24h") is None:
            continue
        for r in {regions.region_of(m.get("province")), "all"} - {None}:
            o = out.setdefault(r, {"forecast_mm24": None, "measured": None})
            if o["measured"] is None or m["rain_24h"] > o["measured"]["rain_24h"]:
                o["measured"] = {k: m.get(k) for k in ("code", "name_th", "province", "rain_24h", "rain_1h")}
    return out


RAIN_OBS_SQL = """SELECT DISTINCT ON (code) code, obs_time, rain_1h, rain_24h, lat, lon, name_th, province FROM rain_obs
                  WHERE obs_time > now() - interval '3 hours' ORDER BY code, obs_time DESC"""


def point_regions(rows: list[dict]) -> dict[str, str]:
    """Region of each 0.5° cell and each fine (~8 km) point, from the gauges they serve."""
    out = {}
    for r in rows:
        reg = regions.region_of(r.get("province"))
        if r.get("lat") is None or not reg:
            continue
        out.setdefault(rain_cells.cell_of(r["lat"], r["lon"])[0], reg)
        for pid in rain_cells.fine_points([r]):
            out.setdefault(pid, reg)
    return out


def _cell_regions() -> dict[str, str]:
    return _memo(("cell_regions",), lambda: point_regions(_station_rows(True)), ttl=3600)


def _fine_ids() -> set[str]:
    """Fine points that have a forecast (the pin panel falls back to the Bangkok points without one)."""
    def build():
        with db.connect() as c:
            return {r["point"] for r in c.execute(
                "SELECT DISTINCT point FROM weather_forecast WHERE left(point, 2) = 'f_' AND issue_time > now() - interval '3 hours'").fetchall()}
    return _memo(("fine_ids",), build, ttl=600)


@app.get("/api/rain")
def rain():
    return _json(_memo(("rain",), _rain_data))  # every visitor's 5-min refresh reads it: shared for 60 s (KI-246)


def _rain_data() -> dict:
    with db.connect() as c:
        rows = c.execute(
            f"""SELECT w.point, sum(w.precip_mm) FILTER (WHERE w.valid_time <= now() + interval '24 hours') AS mm24,
                      sum(w.precip_mm) FILTER (WHERE w.valid_time <= now() + interval '72 hours') AS mm72,
                      max(w.issue_time) AS issue
               FROM weather_forecast w JOIN ({rain_cells.LATEST_ISSUE}) l ON l.point=w.point AND l.t=w.issue_time
               WHERE w.valid_time > now() GROUP BY w.point""").fetchall()
        measured = c.execute(RAIN_OBS_SQL).fetchall()
    pts = [{"point": r["point"], "mm24": r["mm24"], "mm72": r["mm72"], "issue_time": _iso(r["issue"])} for r in rows]
    return {"source": "Open-Meteo (forecast) · HII rain gauges (measured)", "points": pts,
            "by_region": rain_by_region(pts, measured, _cell_regions())}


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
    return _json(_memo(("stats",), _stats_data))


def _stats_data() -> dict:
    with db.connect() as c:
        rows = c.execute(STATS_SQL).fetchall()
        focus = [_station_row(r) for r in _station_rows(False)]
        rain = c.execute(
            f"""SELECT max(mm) AS mm24 FROM (SELECT w.point, sum(w.precip_mm) AS mm FROM weather_forecast w
               JOIN ({rain_cells.LATEST_ISSUE}) l ON l.point=w.point AND l.t=w.issue_time WHERE w.point LIKE 'bkk%%'
                 AND w.valid_time BETWEEN now() AND now() + interval '24 hours' GROUP BY w.point) x""").fetchone()
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


_RIVER_KM: dict = {"t": 0.0, "v": {}}


def _river_km() -> dict:
    """River km per gauge for every river with a profile (collector hii_geo, weekly; rivers.river_km), cached 10 min.
    Before the first run the Chao Phraya falls back to the hand-checked chainage file (scripts/build_chainage.py)."""
    if time.time() - _RIVER_KM["t"] > 600:
        with db.connect() as c:
            row = c.execute("SELECT value FROM collector_state WHERE key='river_km'").fetchone()
        v = (row or {}).get("value") or {}
        if "แม่น้ำเจ้าพระยา" not in v and CHAINAGE:
            v = {**v, "แม่น้ำเจ้าพระยา": {"stations": {k: {"km": x["chainage_km"]} for k, x in CHAINAGE.items()}}}
        _RIVER_KM.update(t=time.time(), v=v)
    return _RIVER_KM["v"]


@app.get("/api/rivers")
def rivers_list():
    """Rivers with a profile (>= 8 gauges with a bank, D-072): name, gauges on it, the region most of them are in."""
    kms = _river_km()
    rows = _station_rows(True)
    out = []
    for name, d in kms.items():
        codes = set(d.get("stations") or {})
        regs = Counter(regions.region_of(r.get("province")) for r in rows if r["code"] in codes)
        regs.pop(None, None)
        out.append({"river": name, "n": len(codes), "region": regs.most_common(1)[0][0] if regs else None,
                    "agree": d.get("agree")})
    out.sort(key=lambda x: (x["river"] != "แม่น้ำเจ้าพระยา", -x["n"]))
    return _json({"rivers": out}, cache=True)


@app.get("/api/profile")
def profile(river: str = Query("แม่น้ำเจ้าพระยา", max_length=60)):
    """One river, upstream to downstream: level vs bank and the tested forecast at each gauge (1-D, no interpolation
    between gauges; APPROACH §2.9). chainage_km = approximate river km from the mouth or confluence along HII's river
    line (±10 km near branches; rivers.py). BMA gauges never join an HII/RID chain (KI-217)."""
    kms = _river_km()
    if river not in kms:
        raise HTTPException(status_code=404, detail="no profile for this river")
    rows = [_station_row(r) for r in _station_rows(True) if r["river"] == river and r["lat"] is not None]
    items = rivers_mod.profile(rows, river, kms[river].get("stations") or {})
    return _json({"river": river, "order": "upstream_to_downstream", "dist": "river_km_from_mouth_approx",
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
    return _json(_point_out(lat, lon))


@app.get("/api/explain")
def explain_point(lat: float = Query(..., ge=5, le=21), lon: float = Query(..., ge=97, le=106), q: str = Query(...),
                  part: str = Query("lines")):
    """A resident question about a pin (D-068). part=lines: the rule story (a few easy sentences) and the rule lines with
    the numbers, from the same data as /api/point, at once. part=gist: GLM's warm retelling of the story, only if
    explain.check passes (else null). The pin never goes to GLM."""
    if q not in explain.QUESTIONS or part not in ("lines", "gist"):
        raise HTTPException(status_code=400, detail="unknown question")
    out = _point_out(lat, lon)
    lines, story = explain.answer(q, out), explain.narrative(q, out)
    if part == "gist":
        return _json({"q": q, "gist": explain.gist(q, lines, story)})
    return _json({"q": q, "question": explain.QUESTIONS[q], "story": story, "lines": lines,
                  "ai": os.environ.get("AI_EXPLAIN", "1") == "1" and ai.available()})


def _point_out(lat: float, lon: float) -> dict:
    with db.connect() as c:
        rows = [_station_row(r) for r in _station_rows(True)]
        box = {"lat0": lat - 0.01, "lat1": lat + 0.01, "lon0": lon - 0.01, "lon1": lon + 0.01}
        traffy = c.execute("""SELECT count(*) AS n FROM crowd_report WHERE is_flood AND report_time > now() - interval '6 hours'
                              AND lat BETWEEN %(lat0)s AND %(lat1)s AND lon BETWEEN %(lon0)s AND %(lon1)s""", box).fetchone()["n"]
        depths = {r["depth"]: r["n"] for r in c.execute(
            """SELECT depth, count(*) AS n FROM user_feedback WHERE depth IS NOT NULL AND lat IS NOT NULL
               AND created_at > now() - interval '24 hours'
               AND lat BETWEEN %(lat0)s AND %(lat1)s AND lon BETWEEN %(lon0)s AND %(lon1)s GROUP BY 1""", box).fetchall()}
        rain_rows = c.execute(RAIN_OBS_SQL).fetchall()
        # satellite-flooded cells near the pin (GISTDA 7-day layer, D-071): ~1.3 km box, images at most 10 days old
        sat_cells = c.execute("""SELECT lat, lon, area_m2, img_from, img_to FROM sat_flood
                                 WHERE lat BETWEEN %(a0)s AND %(a1)s AND lon BETWEEN %(o0)s AND %(o1)s
                                   AND (img_to IS NULL OR img_to > current_date - 10)""",
                              {"a0": lat - 0.012, "a1": lat + 0.012, "o0": lon - 0.012, "o1": lon + 0.012}).fetchall()
        pt = rain_cells.rain_point_at(lat, lon, _fine_ids())  # ~8 km point (Bangkok region), Bangkok point, or 0.5° cell
        rain = c.execute("""SELECT sum(precip_mm) AS mm FROM weather_forecast WHERE point=%s
                            AND issue_time=(SELECT max(issue_time) FROM weather_forecast WHERE point=%s)
                            AND valid_time BETWEEN now() AND now() + interval '24 hours'""", (pt, pt)).fetchone()["mm"]
    measured = point.measured_rain(lat, lon, rain_rows, dt.datetime.now(dt.timezone.utc))
    out = point.assess(lat, lon, rows, traffy, depths, None if rain is None else round(rain, 1), measured)
    out["rain_point"] = pt
    out["satellite"] = point.satellite_seen(lat, lon, sat_cells)
    out["forecast"]["plain"] = explain.plain(out)  # the panel's everyday-words line (D-068), by template
    return out


GEOCODE_PER_HOUR = 30
_geo_hits: dict[str, list[float]] = {}  # per process, in memory: client hash -> recent call times (never the query)


@app.get("/api/reverse")
def reverse_geocode(lat: float = Query(..., ge=5, le=21), lon: float = Query(..., ge=97, le=106)):
    """Subdistrict, district, province for the point panel (issue #3). The page shows the panel first and fills this
    in when it arrives, so a slow or failed lookup never delays the answer; failures return area=null."""
    try:
        with db.connect() as c:
            area = geocode.reverse(lat, lon, c)
    except Exception:
        area = None
    return _json({"area": area}, cache=True)


@app.get("/api/geocode")
def geocode_search(request: Request, q: str = Query(..., min_length=2, max_length=100)):
    """Find a place (ซอย, ถนน, ย่าน) in the Bangkok region so the point check can open there. OpenStreetMap
    Nominatim via our server; the query is neither logged nor stored (geocode.py)."""
    who, now = _client_hash(request), dt.datetime.now().timestamp()
    recent = [t for t in _geo_hits.get(who, []) if now - t < 3600]
    if len(recent) >= GEOCODE_PER_HOUR:
        raise HTTPException(429, "too many searches, please try later")
    _geo_hits[who] = recent + [now]
    if len(_geo_hits) > 5000:
        _geo_hits.clear()
    try:
        with db.connect() as c:
            results = geocode.search(q.strip(), c)
    except Exception:
        raise HTTPException(503, "place search unavailable")  # deliberately without the query or the error text
    return JSONResponse({"results": results, "attribution": "© OpenStreetMap contributors"},
                        headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/summary")
def summary():
    """One deterministic Thai sentence for the header and for sharing. Never AI-written (D-022)."""
    return _json({"text": ai.summary_text(_stats_data()), "by": "template"})


CANONICAL_HOST = "flood.autobahn.bot"      # main domain (D-017)
LEGACY_HOST = "flood.bejranonda.com"       # alias, same tunnel
# Off by default: while the main domain challenges non-browser clients (KI-506) a redirect would send link-preview
# crawlers and API users from the working alias into the challenge. On since 2026-09-26 for pages only (D-034).
REDIRECT_LEGACY = os.environ.get("REDIRECT_LEGACY_HOST", "0") == "1"


def _host(request: Request) -> str:
    return request.headers.get("host", "").split(":")[0].lower()


def page_for_host(html: str, host: str) -> str:
    """The alias declares itself canonical, so crawlers that open it are not sent to a host that challenges them."""
    if host == LEGACY_HOST:
        return html.replace(f"https://{CANONICAL_HOST}/", f"https://{LEGACY_HOST}/")
    return html


def legacy_redirect_target(host: str, path: str, query: str) -> str | None:
    """301 target for the legacy host when enabled (owner, 2026-09-26: "move all to flood.autobahn.bot", D-034/D-035).
    Everything moves, API included (the main domain's bot challenge is off since 17:33 UTC). Only /api/health stays
    on the alias so an uptime monitor pointed at the old host keeps working."""
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
    html = page_for_host((WEB_DIR / "index.html").read_text(), _host(request)).replace("__VERSION__", f"v{__version__}")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})  # revalidate: a release reaches open phones at once (KI-253)


ROBOTS_TXT = """User-agent: *
Allow: /
Disallow: /api/docs
Disallow: /api/openapi.json
Disallow: /api/point
Disallow: /api/explain
Sitemap: https://{host}/sitemap.xml
"""
SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://{host}/</loc><changefreq>hourly</changefreq></url></urlset>
"""


@app.get("/robots.txt", include_in_schema=False)
def robots(request: Request):
    """Crawlers may read the page and its data; the docs and the per-coordinate point check (one DB-heavy call per
    coordinate, KI-246) are kept out of search indexes."""
    host = LEGACY_HOST if _host(request) == LEGACY_HOST else CANONICAL_HOST
    return Response(ROBOTS_TXT.format(host=host), media_type="text/plain", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    """One URL: every view (station, point check) is a #fragment of the home page, which crawlers do not treat as a page."""
    host = LEGACY_HOST if _host(request) == LEGACY_HOST else CANONICAL_HOST
    return Response(SITEMAP_XML.format(host=host), media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    ico = WEB_DIR / "favicon.ico"
    if ico.exists():
        return FileResponse(ico, media_type="image/x-icon", headers={"Cache-Control": "public, max-age=86400"})
    return FileResponse(WEB_DIR / "favicon.svg", media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
def apple_touch_icon():
    return FileResponse(WEB_DIR / "apple-touch-icon.png", media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

