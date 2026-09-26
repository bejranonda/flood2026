"""Collectors: fetch -> archive raw -> parse -> QC -> store -> report health. One function per source."""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
import urllib.parse

from floodwatch import archive, db
from floodwatch.config import EXTRA_STATIONS, RAIN_POINTS, settings
from floodwatch.collectors import parsing
from floodwatch.httpclient import fetch

log = logging.getLogger(__name__)
HII = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public"
CHART = "https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst"


def _run(source: str, fn) -> None:
    """Run one collector with health bookkeeping; never raise (circuit-breaker style isolation)."""
    try:
        data_time = fn()
        db.record_health(source, True, data_time=data_time)
    except Exception as e:  # logged + recorded; other collectors keep running
        log.exception("collector %s failed", source)
        db.record_health(source, False, error=f"{type(e).__name__}: {e}")


def _get_json(source: str, url: str, **kw) -> tuple[object, str]:
    r = fetch(url, **kw)
    sha, _ = archive.store(source, url, r.status, r.body)
    if not 200 <= r.status < 300:  # Traffy answers 201
        raise RuntimeError(f"HTTP {r.status}")
    return json.loads(r.body), sha


def hii_waterlevel() -> dt.datetime | None:
    payload, sha = _get_json("hii_waterlevel_load", f"{HII}/waterlevel_load")
    stations, obs = parsing.parse_waterlevel_load(payload, sha)
    with db.connect() as c:
        for s in stations:
            db.upsert_station(c, s)
        db.insert_observations(c, obs)
        c.commit()
    log.info("hii_waterlevel: %d stations, %d observations", len(stations), len(obs))
    return max((o["obs_time"] for o in obs), default=None)


def hii_rain() -> dt.datetime | None:
    payload, _ = _get_json("hii_rain_24h", f"{HII}/rain_24h")
    rows = parsing.parse_rain(payload)
    with db.connect() as c, c.cursor() as cur:
        cur.executemany(
            """INSERT INTO rain_obs (code, obs_time, rain_1h, rain_24h, lat, lon, name_th, province)
               VALUES (%(code)s,%(obs_time)s,%(rain_1h)s,%(rain_24h)s,%(lat)s,%(lon)s,%(name_th)s,%(province)s)
               ON CONFLICT DO NOTHING""", rows)
        c.commit()
    log.info("hii_rain: %d focus rain stations", len(rows))
    return max((r["obs_time"] for r in rows), default=None)


def hii_history(days: int = 30, pause_s: float = 1.5) -> dt.datetime | None:
    """Backfill/refresh history for focus stations: waterlevel_graph (hourly, with discharge) by numeric id,
    or the chart XHR (10-min) for stations missing from the latest-values feed (e.g. BKK008)."""
    with db.connect() as c:
        stations = c.execute(
            "SELECT code, hii_id, bank_msl, ground_msl FROM station WHERE in_focus ORDER BY code").fetchall()
    known = {s["code"] for s in stations}
    end = dt.datetime.now(parsing.ICT)
    start = (end - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    end_s = urllib.parse.quote(end.strftime("%Y-%m-%d %H:%M"))
    total, latest = 0, None
    for s in stations:
        try:
            if s["code"].startswith(("BKK", "CPY", "BKC", "AIT")):
                rows, sha = _get_json("hii_chart", f"{CHART}/{urllib.parse.quote(s['code'])}")
                obs, _, _ = parsing.parse_chart(s["code"], rows, sha)
            elif s["hii_id"]:
                url = (f"{HII}/waterlevel_graph?station_type=tele_waterlevel&station_id={s['hii_id']}"
                       f"&start_date={start}&end_date={end_s}")
                payload, sha = _get_json("hii_waterlevel_graph", url)
                obs = parsing.parse_waterlevel_graph(s["code"], payload, s["bank_msl"], s["ground_msl"], sha)
            else:
                continue
        except Exception as e:
            log.warning("history %s failed: %s", s["code"], e)
            continue
        with db.connect() as c:
            total += db.insert_observations(c, obs)
            c.commit()
        for o in obs:
            if latest is None or o["obs_time"] > latest:
                latest = o["obs_time"]
        time.sleep(pause_s)
    for code in EXTRA_STATIONS:  # stations only the chart XHR serves
        if code in known:
            continue
        rows, sha = _get_json("hii_chart", f"{CHART}/{code}")
        obs, bank, ground = parsing.parse_chart(code, rows, sha)
        with db.connect() as c:
            db.upsert_station(c, {"code": code, "hii_id": None, "name_th": None, "name_en": None, "lat": None,
                                  "lon": None, "bank_msl": bank, "ground_msl": ground, "critical_msl": None,
                                  "agency": "HII", "province": "กรุงเทพมหานคร", "amphoe": None, "river": None,
                                  "basin": None, "in_focus": True, "meta_source": "hii_chart"})
            total += db.insert_observations(c, obs)
            c.commit()
    log.info("hii_history: %d rows for %d stations", total, len(stations))
    return latest


def openmeteo() -> dt.datetime | None:
    issue = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    n = 0
    for point, (lat, lon) in RAIN_POINTS.items():
        url = ("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
            {"latitude": lat, "longitude": lon, "hourly": "precipitation", "forecast_days": 7, "past_days": 1,
             "timezone": "Asia/Bangkok"}))
        payload, _ = _get_json("openmeteo_forecast", url)
        rows = parsing.parse_openmeteo(point, payload, issue)
        with db.connect() as c, c.cursor() as cur:
            cur.executemany(
                """INSERT INTO weather_forecast (point, issue_time, valid_time, model, precip_mm)
                   VALUES (%(point)s,%(issue_time)s,%(valid_time)s,%(model)s,%(precip_mm)s) ON CONFLICT DO NOTHING""",
                rows)
            c.commit()
        n += len(rows)
    log.info("openmeteo: %d hourly values (issue %s)", n, issue)
    return issue


def traffy() -> dt.datetime | None:
    payload, _ = _get_json("traffy_public", "https://publicapi.traffy.in.th/share/teamchadchart/search?limit=500")
    rows = parsing.parse_traffy(payload)
    with db.connect() as c, c.cursor() as cur:
        cur.executemany(
            """INSERT INTO crowd_report (ticket_id, report_time, lat, lon, state, is_flood)
               VALUES (%(ticket_id)s,%(report_time)s,%(lat)s,%(lon)s,%(state)s,%(is_flood)s)
               ON CONFLICT (ticket_id) DO UPDATE SET state=EXCLUDED.state""", rows)
        c.commit()
    log.info("traffy: %d reports (%d flood-related)", len(rows), sum(r["is_flood"] for r in rows))
    return max((r["report_time"] for r in rows), default=None)


def bma_dds() -> dt.datetime | None:
    """BMA blocks non-Thai IPs (KI-101). Only runs through a configured Thai egress (D-014).
    Archives the raw page so a parser can be written once the real format is visible."""
    if not settings.thai_egress_proxy:
        raise RuntimeError("skipped: THAI_EGRESS_PROXY not set (BMA blocks non-Thai IPs)")
    r = fetch("https://dds.bangkok.go.th/", via_thai_egress=True)
    archive.store("bma_dds", r.url, r.status, r.body, ext="html")
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status}")
    return dt.datetime.now(dt.timezone.utc)


def run(source: str) -> None:
    _run(source, {"hii_waterlevel": hii_waterlevel, "hii_rain": hii_rain, "hii_history": hii_history,
                  "openmeteo": openmeteo, "traffy": traffy, "bma_dds": bma_dds}[source])
