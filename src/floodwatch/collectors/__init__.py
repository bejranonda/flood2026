"""Collectors: fetch -> archive raw -> parse -> QC -> store -> report health. One function per source."""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
import urllib.parse

from floodwatch import archive, db
from floodwatch.config import DATUM_SUSPECT, EXTRA_STATIONS, FOCUS_PROVINCES, RAIN_POINTS, settings
from floodwatch.collectors import parsing
from floodwatch.httpclient import fetch

log = logging.getLogger(__name__)
HII = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public"
CHART = "https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst"
LOOKBACK_RAIN_DAYS = 370  # rain history for training, as long as the level history (forecast.LOOKBACK_DAYS)
BACKFILL_DAYS = 365  # waterlevel_graph serves at most one year (checked 2026-09-26: C.12 from 2025-09-26)


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
    log.info("hii_rain: %d rain stations", len(rows))
    return max((r["obs_time"] for r in rows), default=None)


def _graph(s: dict, days: int, end: dt.datetime) -> list[dict]:
    start = (end - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    url = (f"{HII}/waterlevel_graph?station_type=tele_waterlevel&station_id={s['hii_id']}"
           f"&start_date={start}&end_date={urllib.parse.quote(end.strftime('%Y-%m-%d %H:%M'))}")
    payload, sha = _get_json("hii_waterlevel_graph", url)
    return parsing.parse_waterlevel_graph(s["code"], payload, s["bank_msl"], s["ground_msl"], sha)


def hii_backfill(max_stations: int = 12, pause_s: float = 1.0) -> dt.datetime | None:
    """One-time 365-day history per HII-network station (D-018; every gauge in Thailand since v0.16, D-064), a few
    stations per call so the single worker loop keeps its 10-min collectors on time. Focus gauges first. A no-op
    once every station is done."""
    with db.connect() as c:
        stations = c.execute("SELECT code, hii_id, bank_msl, ground_msl FROM station WHERE hii_id IS NOT NULL "
                             "AND code !~ '^TEST' AND agency IS DISTINCT FROM 'BMA' "
                             "ORDER BY in_focus DESC, code").fetchall()
        done = set(db.get_state(c, "hii_graph_backfilled") or [])
    todo = [s for s in stations if s["code"] not in done][:max_stations]
    end = dt.datetime.now(parsing.ICT)
    for s in todo:
        try:
            obs = _graph(s, BACKFILL_DAYS, end)
        except Exception as e:
            log.warning("backfill %s failed: %s", s["code"], e)
            continue
        with db.connect() as c:
            n = db.insert_observations(c, obs)
            done.add(s["code"])
            db.set_state(c, "hii_graph_backfilled", sorted(done))
            c.commit()
        log.info("hii_backfill %s: %d rows", s["code"], n)
        time.sleep(pause_s)
    if todo:
        log.info("hii_backfill: %d/%d stations done", len(done & {s["code"] for s in stations}), len(stations))
    return None


HISTORY_SLICES = 6  # hii_history runs every 6 h: each nationwide gauge is refilled once a day


def history_slice(codes: list[str], run_no: int, slices: int = HISTORY_SLICES) -> list[str]:
    """The nationwide gauges one hii_history run refills: every `slices`-th code, rotating with the run number."""
    return codes[run_no % slices::slices]


def hii_history(pause_s: float = 0.7) -> dt.datetime | None:
    """Refresh recent history: api-v3 waterlevel_graph (hourly/10-min, with discharge, by numeric id) for the last
    3 days, plus the 10-min chart XHR for the tidal BKK/CPY/BKC/AIT gauges and for stations missing from the
    latest-values feed. Focus gauges every run; the rest of the HII network in rotating slices (D-064), so one run
    stays short (the latest-values feed already brings them an hourly value every 10 min). Backfill: hii_backfill."""
    with db.connect() as c:
        # HII stations only: BMA gauges (agency BMA, codes WL.*) have no HII chart and come from bma_klong. Without this
        # filter the 199 BMA codes each cost ~10 s of HTTP 500 retries and starved the worker loop (2026-09-26).
        rows = c.execute(
            "SELECT code, hii_id, bank_msl, ground_msl, in_focus FROM station WHERE code !~ '^TEST' "
            "AND agency IS DISTINCT FROM 'BMA' AND (in_focus OR hii_id IS NOT NULL) ORDER BY code").fetchall()
        run_no = int(db.get_state(c, "hii_history_slice") or 0)
        db.set_state(c, "hii_history_slice", run_no + 1)
        c.commit()
    part = set(history_slice([r["code"] for r in rows if not r["in_focus"]], run_no))
    stations = [r for r in rows if r["in_focus"] or r["code"] in part]
    known = {r["code"] for r in rows}
    end = dt.datetime.now(parsing.ICT)
    total, latest = 0, None
    for s in stations:
        obs: list[dict] = []
        try:
            if s["hii_id"]:
                obs += _graph(s, 3, end)
            if s["code"].startswith(("BKK", "CPY", "BKC", "AIT")) or not s["hii_id"]:
                rows, sha = _get_json("hii_chart", f"{CHART}/{urllib.parse.quote(s['code'])}")
                obs += parsing.parse_chart(s["code"], rows, sha)[0]
        except Exception as e:
            log.warning("history %s failed: %s", s["code"], e)
        if not obs:
            continue
        with db.connect() as c:
            total += db.insert_observations(c, obs)
            c.commit()
        for o in obs:
            if latest is None or o["obs_time"] > latest:
                latest = o["obs_time"]
        time.sleep(pause_s)
    coords = None
    for code in EXTRA_STATIONS:  # stations only the chart XHR serves
        if code in known:
            continue
        try:
            rows, sha = _get_json("hii_chart", f"{CHART}/{code}")
            obs, bank, ground = parsing.parse_chart(code, rows, sha)
        except Exception as e:
            log.warning("extra station %s failed: %s", code, e)
            continue
        if coords is None:
            try:
                map_rows, _ = _get_json("hii_map_feed", "https://tiwrm.hii.or.th/thaiwater_l5/public/json/telemetering/wl/warning")
                coords = {m["code"]: m for m in parsing.parse_map_feed(map_rows)}
            except Exception:
                coords = {}
        m = coords.get(code, {})
        with db.connect() as c:
            db.upsert_station(c, {"code": code, "hii_id": None, "name_th": m.get("name_th"), "name_en": None,
                                  "lat": m.get("lat"), "lon": m.get("lon"), "bank_msl": m.get("bank_msl") or bank,
                                  "ground_msl": m.get("ground_msl") or ground, "critical_msl": None,
                                  "agency": "HII", "province": m.get("province") or "กรุงเทพมหานคร",
                                  "amphoe": m.get("amphoe"), "river": None, "basin": m.get("basin"),
                                  "in_focus": True, "meta_source": "hii_chart"})
            total += db.insert_observations(c, obs)
            c.commit()
    log.info("hii_history: %d rows for %d stations", total, len(stations))
    return latest


def hii_stations() -> dt.datetime | None:
    """Add stations that only the HII chart site serves (missing from waterlevel_load: e.g. BKK004, BKK007,
    ATG*, MOU*), and take coordinates for them from the HII map feed. See docs/KNOWN_ISSUES.md KI-207."""
    map_rows, _ = _get_json("hii_map_feed", "https://tiwrm.hii.or.th/thaiwater_l5/public/json/telemetering/wl/warning")
    coords = {m["code"]: m for m in parsing.parse_map_feed(map_rows)}
    with db.connect() as c:
        have = {r["code"] for r in c.execute("SELECT code FROM station").fetchall()}
        unavailable: dict[str, str] = db.get_state(c, "hii_chart_unavailable") or {}
    retry_before = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)).isoformat()
    added = coordinated = failed = skipped = 0
    for province in FOCUS_PROVINCES:
        listing, _ = _get_json("hii_chart_stationlist",
                               "https://tiwrm.hii.or.th/thaiwater_l5/public/queryStation?" + urllib.parse.urlencode({"prov": province}))
        for item in listing:
            code = (item.get("code") or "").strip()
            if not code or code in have or code.startswith("TEST"):  # HII test gauges (KI-209)
                continue
            if unavailable.get(code, "") > retry_before:  # known-broken codes: retry once a day, not every run
                skipped += 1
                continue
            try:
                rows, sha = _get_json("hii_chart", f"{CHART}/{urllib.parse.quote(code)}", retries=1)
                obs, bank, ground = parsing.parse_chart(code, rows, sha)
            except Exception:  # the chart endpoint answers HTTP 500 for many codes (e.g. GLF001, CPY013): KI-207
                obs = []
            if not any(o["level_msl"] is not None for o in obs):
                failed += 1
                unavailable[code] = dt.datetime.now(dt.timezone.utc).isoformat()
                time.sleep(0.5)
                continue
            unavailable.pop(code, None)
            m = coords.get(code, {})
            with db.connect() as c:
                db.upsert_station(c, {"code": code, "hii_id": None, "name_th": item.get("name"), "name_en": None,
                                      "lat": m.get("lat"), "lon": m.get("lon"),
                                      "bank_msl": m.get("bank_msl") or bank, "ground_msl": m.get("ground_msl") or ground,
                                      "critical_msl": None, "agency": "HII", "province": province,
                                      "amphoe": m.get("amphoe"), "river": None, "basin": m.get("basin"),
                                      "in_focus": True, "meta_source": "hii_chart"})
                db.insert_observations(c, obs)
                c.commit()
            added += 1
            coordinated += 1 if m else 0
            have.add(code)
            time.sleep(0.5)
    with db.connect() as c:
        db.set_state(c, "hii_chart_unavailable", unavailable)
        # Existing stations without coordinates (e.g. BKK008, added from the chart list) take them from the map
        # feed too; name/amphoe/bank only fill gaps. Every change is versioned in station_version.
        located = 0
        for code, m in coords.items():
            r = c.execute("""UPDATE station SET lat=%(lat)s, lon=%(lon)s, name_th=COALESCE(name_th, %(name_th)s),
                               amphoe=COALESCE(amphoe, %(amphoe)s), bank_msl=COALESCE(bank_msl, %(bank_msl)s),
                               ground_msl=COALESCE(ground_msl, %(ground_msl)s), updated_at=now()
                             WHERE code=%(code)s AND lat IS NULL RETURNING bank_msl, ground_msl""", m).fetchone()
            if r:
                located += 1
                c.execute("""INSERT INTO station_version (code, bank_msl, ground_msl, lat, lon, source)
                             VALUES (%s,%s,%s,%s,%s,'hii_map_feed') ON CONFLICT DO NOTHING""",
                          (code, r["bank_msl"], r["ground_msl"], m["lat"], m["lon"]))
        c.commit()
    if located:
        log.info("hii_stations: coordinates added from the map feed for %d existing stations", located)
    approx = _apply_approx_coords()
    if approx:
        log.info("hii_stations: approximate OSM positions applied to %d stations", approx)
    log.info("hii_stations: added %d chart-only stations (%d with coordinates); %d unavailable via chart, "
             "%d skipped (failed < 24 h ago)", added, coordinated, failed, skipped)
    return None


def _apply_approx_coords() -> int:
    """Curated approximate positions (src/floodwatch/data/station_coords_approx.json, OSM, KI-207) for stations no
    HII feed locates. Only fills missing coordinates; marked coord_source='osm_approx' so the UI can say so."""
    from importlib import resources
    data = json.loads(resources.files("floodwatch").joinpath("data/station_coords_approx.json").read_text())
    n = 0
    with db.connect() as c:
        for code, m in data["stations"].items():
            r = c.execute("""UPDATE station SET lat=%s, lon=%s, coord_source='osm_approx', coord_precision_km=%s,
                               updated_at=now() WHERE code=%s AND lat IS NULL RETURNING code""",
                          (m["lat"], m["lon"], m["precision_km"], code)).fetchone()
            if r:
                c.execute("""INSERT INTO station_version (code, lat, lon, source) VALUES (%s,%s,%s,%s)
                             ON CONFLICT DO NOTHING""", (code, m["lat"], m["lon"], f"osm_approx {m['osm']}"))
                n += 1
        c.commit()
    return n


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
    # limit=40: under flood load Traffy's gateway gives up at 60 s and 50 tickets took 51 s (2026-09-26 18:10 UTC);
    # limit=500 had failed with HTTP 502 for 3 h. The newest 40 every 10 min, upserted, keeps up with the stream.
    payload, _ = _get_json("traffy_public", "https://publicapi.traffy.in.th/share/teamchadchart/search?limit=40",
                           retries=1)  # optional layer, polled again in 10 min: never hold the worker loop
    rows = parsing.parse_traffy(payload)
    with db.connect() as c, c.cursor() as cur:
        cur.executemany(
            """INSERT INTO crowd_report (ticket_id, report_time, lat, lon, state, is_flood)
               VALUES (%(ticket_id)s,%(report_time)s,%(lat)s,%(lon)s,%(state)s,%(is_flood)s)
               ON CONFLICT (ticket_id) DO UPDATE SET state=EXCLUDED.state""", rows)
        c.commit()
    log.info("traffy: %d reports (%d flood-related)", len(rows), sum(r["is_flood"] for r in rows))
    return max((r["report_time"] for r in rows), default=None)


BMA_RELAY = "https://flood69.peoplesparty.or.th/api/klongmap"


def bma_klong() -> dt.datetime | None:
    """BMA khlong gauges (~199, Bangkok) via the People's Party relay, which copies BMA's KlongMap every 5 min.
    BMA itself is unreachable from this host (SOURCES §2c); the owner chose to use and show the relay (Q24, D-031).
    Latest values only: history builds up from our own polling. Attribution to BMA and the relay in the UI."""
    payload, sha = _get_json("bma_klong", BMA_RELAY, retries=1)  # optional layer: never hold the worker loop
    stations, obs = parsing.parse_bma_klongmap(payload, sha)
    if len(stations) < 50:  # a relay change or an error page in JSON clothing: keep the last good data
        raise RuntimeError(f"only {len(stations)} BMA stations in the relay payload")
    with db.connect() as c:
        for s in stations:
            db.upsert_station(c, s)
        db.insert_observations(c, obs)
        c.commit()
    log.info("bma_klong: %d stations, %d readings", len(stations), len(obs))
    return max((o["obs_time"] for o in obs), default=None)


BMA_HISTORY_DAYS = 365
BMA_REFRESH_PER_RUN = 20  # gauges per run in the daily refresh: ~20-40 s, so the 10-min collectors stay on time (KI-239)
BMA_MAX_FAILURES = 3      # a gauge failing this many backfill runs in a row is set aside, so it cannot block the queue


def bma_history(max_stations: int = 5, pause_s: float = 1.0) -> dt.datetime | None:
    """History for BMA canal gauges from HII (D-054): `waterlevel_graph?station_type=canal` serves the same BMA values
    as the relay, back to at least 2024. First a one-year hourly backfill, a few gauges per run; afterwards a daily
    3-day refresh that fills gaps when the relay was down, spread over runs (BMA_REFRESH_PER_RUN each). Same BMA datum
    as the relay (never mixed with HII MSL). The HII feed is fetched only when there is work (KI-239)."""
    today = dt.datetime.now(dt.timezone.utc).date()
    with db.connect() as c:
        codes = [r["code"] for r in c.execute("SELECT code FROM station WHERE agency='BMA' AND code LIKE 'WL.%%' ORDER BY code").fetchall()]
        state = db.get_state(c, "bma_history") or {}
    state = {"done": [], "missing": [], "failed": [], "failures": {}, "refreshed": None, "refresh_day": None,
             "refresh_done": [], **state}
    pending = [x for x in codes if x not in state["done"] and x not in state["missing"] and x not in state["failed"]]
    if not pending and state.get("refreshed") == today.isoformat():
        return None  # nothing to do today: no request to HII
    if not pending and state.get("refresh_day") != today.isoformat():
        state["refresh_day"], state["refresh_done"] = today.isoformat(), []
    feed, _ = _get_json("hii_canal_waterlevel", f"{HII}/canal_waterlevel")
    ids = {r["station"]["canal_oldcode"]: r["station"]["id"] for r in feed.get("data") or [] if r.get("station")}
    if pending:
        todo, start = pending[:max_stations], today - dt.timedelta(days=BMA_HISTORY_DAYS)
    else:
        left = [x for x in codes if x in ids and x not in state["refresh_done"]]
        todo, start = left[:BMA_REFRESH_PER_RUN], today - dt.timedelta(days=3)
    newest = None
    with db.connect() as c:
        for code in todo:
            if code not in ids:
                if pending:
                    state["missing"].append(code)  # not in HII's canal feed: relay history only
                continue
            url = f"{HII}/waterlevel_graph?" + urllib.parse.urlencode(
                {"station_type": "canal", "station_id": ids[code], "start_date": start.isoformat(), "end_date": today.isoformat()})
            try:
                payload, sha = _get_json("hii_canal_graph", url)
                rows = parsing.parse_canal_graph(code, payload, sha)
            except Exception as e:  # one gauge failing must not stop the others; it is retried next run
                log.warning("bma_history %s: %s", code, e)
                if pending:
                    n = state["failures"][code] = state["failures"].get(code, 0) + 1
                    if n >= BMA_MAX_FAILURES:
                        state["failed"].append(code)  # set aside: relay history only (retry by clearing the state)
                else:
                    state["refresh_done"].append(code)  # the next daily refresh tries again
                continue
            db.insert_observations(c, rows)
            (state["done"] if pending else state["refresh_done"]).append(code)
            state["failures"].pop(code, None)
            db.set_state(c, "bma_history", state)  # progress survives an interrupted run
            c.commit()
            if rows:
                newest = max(filter(None, [newest, rows[-1]["obs_time"]]))
            time.sleep(pause_s)
        if not pending and all(x in state["refresh_done"] for x in codes if x in ids):
            state["refreshed"] = today.isoformat()
        db.set_state(c, "bma_history", state)
        c.commit()
    log.info("bma_history: %d gauges (%s), %d still pending", len(todo), "backfill" if pending else "refresh",
             max(0, len(pending) - len(todo)) if pending else len([x for x in codes if x in ids and x not in state["refresh_done"]]))
    return newest


FEWS = "https://fews2.hii.or.th/model-output/data_portal"
# HII's official forecasts for our area (D-050): (FEWS folder, FEWS code, our code, unit). Collected and scored,
# not shown until they beat "no change" and our own model on the archived record.
FEWS_FORECASTS = [("hii_waterlevel", "CPY011", "CPY011", "m"), ("hii_waterlevel", "CPY014", "CPY014", "m"),
                  ("hii_waterlevel", "PAS008", "PAS008", "m"), ("rid_discharge", "C13", "C.13", "m3/s"),
                  ("rid_discharge", "C2", "C.2", "m3/s"), ("rid_discharge", "C3", "C.3", "m3/s"),
                  ("rid_discharge", "C7A", "C.7A", "m3/s"), ("rid_discharge", "C35", "C.35", "m3/s")]


def openmeteo_prev() -> dt.datetime | None:
    """Rain forecast history for training (D-052): one year on the first run, then the last few days each day."""
    today = dt.datetime.now(dt.timezone.utc).date()
    newest = None
    with db.connect() as c:
        for point, (lat, lon) in RAIN_POINTS.items():
            last = c.execute("SELECT max(valid_time) AS t FROM rain_hindcast WHERE point=%s", (point,)).fetchone()["t"]
            start = today - dt.timedelta(days=LOOKBACK_RAIN_DAYS) if last is None else last.date() - dt.timedelta(days=3)
            url = ("https://previous-runs-api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
                {"latitude": lat, "longitude": lon, "start_date": start.isoformat(), "end_date": today.isoformat(),
                 "hourly": "precipitation_previous_day1,precipitation_previous_day2", "timezone": "UTC"}))
            payload, _ = _get_json("openmeteo_prev", url)
            rows = parsing.parse_openmeteo_prev(point, payload)
            with c.cursor() as cur:
                cur.executemany("""INSERT INTO rain_hindcast (point, valid_time, day1, day2)
                                   VALUES (%(point)s, %(valid_time)s, %(day1)s, %(day2)s)
                                   ON CONFLICT (point, valid_time) DO UPDATE SET day1=EXCLUDED.day1, day2=EXCLUDED.day2""", rows)
            c.commit()
            if rows:
                newest = max(filter(None, [newest, rows[-1]["valid_time"]]))
    return newest


def cell_requests(cells: dict[str, tuple[float, float]], base: str, params: dict,
                  digits: int = 1) -> list[tuple[list[str], str]]:
    """One Open-Meteo request per batch of cells (comma-separated coordinates; the answer is a list in this order)."""
    from floodwatch import rain_cells
    out = []
    for ids in rain_cells.batches(sorted(cells)):
        q = {"latitude": ",".join(f"{cells[i][0]:.{digits}f}" for i in ids),
             "longitude": ",".join(f"{cells[i][1]:.{digits}f}" for i in ids), **params}
        out.append((ids, f"{base}?{urllib.parse.urlencode(q)}"))
    return out


def _cells() -> dict[str, tuple[float, float]]:
    from floodwatch import rain_cells
    with db.connect() as c:
        return rain_cells.all_cells(c.execute(
            "SELECT in_focus, lat, lon FROM station WHERE code !~ '^TEST' AND agency IS DISTINCT FROM 'BMA'").fetchall())


def openmeteo_cells() -> dt.datetime | None:
    """Rain forecast for the 0.5° cells of gauges outside the focus area (D-064), every 3 h, 50 cells per request.
    One issue time per run; readers take each point's latest issue (rain_cells.LATEST_ISSUE)."""
    from floodwatch import rain_cells
    issue = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    n = 0
    for ids, url in cell_requests(_cells(), "https://api.open-meteo.com/v1/forecast",
                                  {"hourly": "precipitation", "forecast_days": 4, "past_days": 1, "timezone": "UTC"}):
        payload, _ = _get_json("openmeteo_cells", url)
        rows = [r for cid, p in rain_cells.split_payload(payload, ids) for r in parsing.parse_openmeteo(cid, p, issue)]
        with db.connect() as c, c.cursor() as cur:
            cur.executemany(
                """INSERT INTO weather_forecast (point, issue_time, valid_time, model, precip_mm)
                   VALUES (%(point)s,%(issue_time)s,%(valid_time)s,%(model)s,%(precip_mm)s) ON CONFLICT DO NOTHING""",
                rows)
            c.commit()
        n += len(rows)
        time.sleep(1.0)
    log.info("openmeteo_cells: %d hourly values (issue %s)", n, issue)
    return issue


def openmeteo_fine() -> dt.datetime | None:
    """Rain forecast for Bangkok and its neighbours at Open-Meteo's own ~8 km grid (Q42, v0.16.4): ~111 points,
    50 per request, hourly, next 48 h. Shown to people (pin panel, region line); the forecast model keeps RAIN_POINTS."""
    from floodwatch import rain_cells
    with db.connect() as c:
        pts = rain_cells.fine_points(c.execute(
            "SELECT province, lat, lon FROM station WHERE lat IS NOT NULL AND code !~ '^TEST'").fetchall())
    issue = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    n = 0
    for ids, url in cell_requests(pts, "https://api.open-meteo.com/v1/forecast",
                                  {"hourly": "precipitation", "forecast_days": 2, "timezone": "UTC"}, digits=4):
        payload, _ = _get_json("openmeteo_fine", url)
        rows = [r for cid, p in rain_cells.split_payload(payload, ids) for r in parsing.parse_openmeteo(cid, p, issue)]
        with db.connect() as c, c.cursor() as cur:
            cur.executemany(
                """INSERT INTO weather_forecast (point, issue_time, valid_time, model, precip_mm)
                   VALUES (%(point)s,%(issue_time)s,%(valid_time)s,%(model)s,%(precip_mm)s) ON CONFLICT DO NOTHING""",
                rows)
            c.commit()
        n += len(rows)
        time.sleep(1.0)
    log.info("openmeteo_fine: %d hourly values for %d points (issue %s)", n, len(pts), issue)
    return issue


def hii_geo() -> dt.datetime | None:
    """HII's public basin (22) and main-river (93) map files (owner 2026-10-02: basin data): weekly; assigns every gauge
    its basin22, main river and river system (basins.assign); fills a missing HII basin name, never overwrites one."""
    from floodwatch import basins
    b, _ = _get_json("hii_geo_basins", "https://www.thaiwater.net/json/boundary/basin.json")
    r, _ = _get_json("hii_geo_rivers", "https://www.thaiwater.net/json/river/river_main.json")
    with db.connect() as c:
        st = c.execute("SELECT code, lat, lon, basin FROM station WHERE code !~ '^TEST'").fetchall()
        rows = basins.assign(st, b.get("features") or [], r.get("features") or [])
        with c.cursor() as cur:
            cur.executemany("""UPDATE station SET basin22=%(basin22)s, river_main=%(river_main)s, river_system=%(river_system)s,
                               basin=COALESCE(basin, %(basin)s) WHERE code=%(code)s""", rows)
        db.set_state(c, "geo_rivers", r)  # river lines for the upstream rule and later views
        c.commit()
    log.info("hii_geo: %d gauges; %d with a main river", len(rows), sum(1 for x in rows if x["river_main"]))
    return None


CELL_BACKFILL_PER_RUN = 8  # a year per cell weighs ~26 Open-Meteo calls: 8 cells/h stays well inside the free quota


def openmeteo_prev_cells() -> dt.datetime | None:
    """Rain-forecast history for the cells (training data for star, D-052/D-064): a year for a few new cells each
    hour until all are done, then once a day the last 4 days for every cell."""
    from floodwatch import rain_cells
    today = dt.datetime.now(dt.timezone.utc).date()
    cells = _cells()
    with db.connect() as c:
        have = {r["point"] for r in c.execute(
            "SELECT DISTINCT point FROM rain_hindcast WHERE left(point, 2) = 'g_'").fetchall()}
        refreshed = db.get_state(c, "cells_prev_refreshed")
    new = {k: v for k, v in cells.items() if k not in have}
    jobs = []
    if new:
        todo = dict(sorted(new.items())[:CELL_BACKFILL_PER_RUN])
        jobs.append((todo, today - dt.timedelta(days=LOOKBACK_RAIN_DAYS)))
    if refreshed != today.isoformat():
        jobs.append(({k: v for k, v in cells.items() if k in have}, today - dt.timedelta(days=4)))
    newest = None
    for group, start in jobs:
        for ids, url in cell_requests(group, "https://previous-runs-api.open-meteo.com/v1/forecast",
                                      {"start_date": start.isoformat(), "end_date": today.isoformat(),
                                       "hourly": "precipitation_previous_day1,precipitation_previous_day2",
                                       "timezone": "UTC"}):
            payload, _ = _get_json("openmeteo_prev_cells", url)
            rows = [r for cid, p in rain_cells.split_payload(payload, ids) for r in parsing.parse_openmeteo_prev(cid, p)]
            with db.connect() as c, c.cursor() as cur:
                cur.executemany("""INSERT INTO rain_hindcast (point, valid_time, day1, day2)
                                   VALUES (%(point)s, %(valid_time)s, %(day1)s, %(day2)s)
                                   ON CONFLICT (point, valid_time) DO UPDATE SET day1=EXCLUDED.day1, day2=EXCLUDED.day2""", rows)
                c.commit()
            if rows:
                newest = max(filter(None, [newest, max(r["valid_time"] for r in rows)]))
            time.sleep(1.0)
    if refreshed != today.isoformat() and have:
        with db.connect() as c:
            db.set_state(c, "cells_prev_refreshed", today.isoformat())
            c.commit()
    log.info("openmeteo_prev_cells: %d new cells this run, %d of %d cells have history", min(len(new), CELL_BACKFILL_PER_RUN),
             len(have) + min(len(new), CELL_BACKFILL_PER_RUN), len(cells))
    return newest


def hii_fews_forecast() -> dt.datetime | None:
    """Archive each new issue of HII's official forecast files (one per station, overwritten daily)."""
    from email.utils import parsedate_to_datetime
    newest = None
    with db.connect() as c:
        for folder, fcode, code, unit in FEWS_FORECASTS:
            url = f"{FEWS}/{folder}/forecast/{fcode}.txt"
            r = fetch(url, retries=2)
            if r.status != 200 or not r.last_modified:
                log.warning("fews forecast %s: HTTP %s", fcode, r.status)
                continue
            issue = parsedate_to_datetime(r.last_modified).astimezone(dt.timezone.utc)
            if c.execute("SELECT 1 FROM external_forecast WHERE source='hii_fews' AND code=%s AND issue_time=%s LIMIT 1",
                         (code, issue)).fetchone():
                continue  # this issue is already archived
            archive.store("hii_fews_forecast", url, r.status, r.body, ext="txt")
            rows = parsing.parse_fews_forecast(r.body.decode("utf-8", "replace"), issue)
            with c.cursor() as cur:
                cur.executemany("""INSERT INTO external_forecast (source, code, issue_time, valid_time, value, unit)
                                   VALUES ('hii_fews', %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                                [(code, issue, x["valid_time"], x["value"], unit) for x in rows])
            c.commit()
            newest = max(filter(None, [newest, issue]))
    return newest


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


GISTDA_FLOOD = "https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/7days"
GISTDA_PAGE = 5000      # ~14 MB a page (polygons); the national 7-day layer had 111,387 cells on 2026-10-03
GISTDA_EVERY_H = 20     # the layer is rebuilt once a day (~18 UTC); a restart must not download ~300 MB again


def gistda_due(fetched_at: dt.datetime | None, now: dt.datetime) -> bool:
    return fetched_at is None or (now - fetched_at).total_seconds() >= GISTDA_EVERY_H * 3600


def gistda_flood(pause_s: float = 2.0) -> dt.datetime | None:
    """Satellite-flooded cells (GISTDA 7-day layer) for the pin panel's "ดาวเทียมเห็นน้ำท่วม" line (Q45, D-071).
    Checked hourly, downloaded at most every 20 h; the whole table is replaced in one transaction. Key in the API-Key
    header (KI-510). Not raw-archived: ~300 MB a day and every page echoes our key in `links` (KI-262)."""
    if not settings.gistda_api_key:
        return None
    with db.connect() as c:
        last = c.execute("SELECT max(fetched_at) AS t FROM sat_flood").fetchone()["t"]
        if last is None:
            st = c.execute("SELECT updated_at FROM collector_state WHERE key='gistda_flood_empty'").fetchone()
            last = st["updated_at"] if st else None
    if not gistda_due(last, dt.datetime.now(dt.timezone.utc)):
        return last
    rows, off, total = [], 0, None
    while total is None or off < total:
        r = fetch(f"{GISTDA_FLOOD}?limit={GISTDA_PAGE}&offset={off}", headers={"API-Key": settings.gistda_api_key}, retries=2)
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        page = json.loads(r.body)
        page.pop("links", None)  # KI-262
        total = int(page.get("numberMatched") or 0)
        rows += parsing.parse_gistda_flood(page)
        if not page.get("features"):
            break
        off += GISTDA_PAGE
        time.sleep(pause_s)
    with db.connect() as c, c.cursor() as cur:
        cur.execute("DELETE FROM sat_flood")
        cur.executemany("""INSERT INTO sat_flood (h3, lat, lon, area_m2, province, amphoe, tambon, img_from, img_to)
                           VALUES (%(h3)s,%(lat)s,%(lon)s,%(area_m2)s,%(province)s,%(amphoe)s,%(tambon)s,%(img_from)s,%(img_to)s)
                           ON CONFLICT (h3) DO NOTHING""", rows)
        # an empty layer is a true answer (nothing seen in 7 days): remember when we asked, so it is not re-asked hourly
        cur.execute("""INSERT INTO collector_state (key, value, updated_at) VALUES ('gistda_flood_empty', %s, now())
                       ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""", (json.dumps(not rows),))
        c.commit()
    log.info("gistda_flood: %d flooded cells (layer said %s)", len(rows), total)
    return dt.datetime.now(dt.timezone.utc)


def run(source: str) -> None:
    _run(source, {"hii_waterlevel": hii_waterlevel, "hii_stations": hii_stations, "hii_rain": hii_rain, "hii_history": hii_history, "hii_backfill": hii_backfill,
                  "openmeteo": openmeteo, "traffy": traffy, "bma_klong": bma_klong, "bma_dds": bma_dds,
                  "hii_fews_forecast": hii_fews_forecast, "openmeteo_prev": openmeteo_prev, "bma_history": bma_history,
                  "openmeteo_cells": openmeteo_cells, "openmeteo_prev_cells": openmeteo_prev_cells,
                  "openmeteo_fine": openmeteo_fine, "hii_geo": hii_geo, "gistda_flood": gistda_flood}[source])
