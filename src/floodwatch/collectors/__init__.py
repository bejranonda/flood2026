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
        data_time = fn()  # a collector returns its newest data time, or a count / None (only a datetime is a data time)
        db.record_health(source, True, data_time=data_time if isinstance(data_time, dt.datetime) else None)
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
        # river km of every gauge on rivers with >= 8 gauges, for the "แม่น้ำ" tab (2026-10-03; Ping ~6 s, all ~10 s)
        from floodwatch import rivers
        gauges = c.execute("""SELECT code, lat, lon, bank_msl, river, agency, province FROM station
                              WHERE lat IS NOT NULL AND code !~ '^TEST'""").fetchall()
        db.set_state(c, "river_km", rivers.river_km(r.get("features") or [], gauges))
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


DWR_EWS = "https://ews.dwr.go.th/ews/web-service/stn"


def dwr_ews() -> dt.datetime | None:
    """DWR early-warning posts (กรมทรัพยากรน้ำ): one POST for all 2,275 posts through the Thai egress (times out from
    Germany), ~45 s, 3 MB; archived raw (rain posts included), level posts stored apart (dwr_station, dwr_obs)."""
    if not settings.thai_egress_proxy:
        raise RuntimeError("skipped: THAI_EGRESS_PROXY not set (ews.dwr.go.th times out from outside Thailand)")
    r = fetch(DWR_EWS, via_thai_egress=True, method="POST", data={"action": "LoadStation"})
    sha, _ = archive.store("dwr_ews", r.url, r.status, r.body)
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status}")
    stations, obs = parsing.parse_dwr_stations(json.loads(r.body))
    with db.connect() as c, c.cursor() as cur:
        cur.executemany("""INSERT INTO dwr_station (code, name_th, lat, lon, province, amphoe, tambon, main_basin, sub_basin,
                               dept, alert_max, status) VALUES (%(code)s, %(name_th)s, %(lat)s, %(lon)s, %(province)s,
                               %(amphoe)s, %(tambon)s, %(main_basin)s, %(sub_basin)s, %(dept)s, %(alert_max)s, %(status)s)
                           ON CONFLICT (code) DO UPDATE SET name_th=EXCLUDED.name_th, lat=EXCLUDED.lat, lon=EXCLUDED.lon,
                               province=EXCLUDED.province, amphoe=EXCLUDED.amphoe, tambon=EXCLUDED.tambon,
                               alert_max=EXCLUDED.alert_max, status=EXCLUDED.status, updated_at=now()""", stations)
        cur.executemany("INSERT INTO dwr_obs (code, obs_time, level) VALUES (%(code)s, %(obs_time)s, %(level)s) ON CONFLICT DO NOTHING", obs)
        c.commit()
    log.info("dwr_ews: %d level posts, %d readings", len(stations), len(obs))
    return max((o["obs_time"] for o in obs), default=None)


GFH = "https://floodforecasting.googleapis.com/v1"


def _gfh(method: str, path: str, body: dict | None = None, params: list | None = None) -> dict:
    """One Flood Hub call. The key travels only in the X-Goog-Api-Key header (never in a URL, which is archived and
    logged); responses carry no key and are archived like every source."""
    url = f"{GFH}/{path}" + (("?" + urllib.parse.urlencode(params)) if params else "")
    r = fetch(url, method=method, data=json.dumps(body) if body is not None else None,
              headers={"X-Goog-Api-Key": settings.google_flood_api_key, "Content-Type": "application/json"}, retries=2)
    archive.store("google_floodhub", url, r.status, r.body)
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status}")
    return json.loads(r.body)


def _gfh_pages(path: str, key: str) -> list:
    out, tok = [], None
    while True:
        d = _gfh("POST", path, {"regionCode": "TH", "pageSize": 1000, **({"pageToken": tok} if tok else {})})
        out += d.get(key) or []
        tok = d.get("nextPageToken")
        if not tok:
            return out


def google_floodhub() -> dt.datetime | None:
    """Google Flood Hub for Thailand (D-087: collected and validated, not shown yet): virtual gauges, latest flood status
    (history kept), thresholds and the latest daily discharge forecast per gauge."""
    if not settings.google_flood_api_key:
        return None
    gauges = parsing.parse_gfh_gauges(_gfh_pages("gauges:searchGaugesByArea", "gauges"))
    status = parsing.parse_gfh_status(_gfh_pages("floodStatus:searchLatestFloodStatusByArea", "floodStatuses"))
    ids = [g["gauge_id"] for g in gauges if g["has_model"]]
    models, fcs = [], []
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for i in range(0, len(ids), 20):
        chunk = ids[i:i + 20]
        models += parsing.parse_gfh_models(_gfh("GET", "gaugeModels:batchGet", params=[("names", f"gaugeModels/{g}") for g in chunk]).get("gaugeModels"))
        fcs += parsing.parse_gfh_forecasts(_gfh("GET", "gauges:queryGaugeForecasts",
                                                params=[("gaugeIds", g) for g in chunk] + [("issuedTimeStart", since)]))
    th = {m["gauge_id"]: m for m in models}
    with db.connect() as c, c.cursor() as cur:
        cur.executemany("""INSERT INTO gfh_gauge (gauge_id, lat, lon, source, quality_verified, has_model, warning, danger, extreme, unit)
                           VALUES (%(gauge_id)s, %(lat)s, %(lon)s, %(source)s, %(quality_verified)s, %(has_model)s, %(warning)s,
                                   %(danger)s, %(extreme)s, %(unit)s)
                           ON CONFLICT (gauge_id) DO UPDATE SET lat=EXCLUDED.lat, lon=EXCLUDED.lon, quality_verified=EXCLUDED.quality_verified,
                               has_model=EXCLUDED.has_model, warning=COALESCE(EXCLUDED.warning, gfh_gauge.warning),
                               danger=COALESCE(EXCLUDED.danger, gfh_gauge.danger), extreme=COALESCE(EXCLUDED.extreme, gfh_gauge.extreme),
                               unit=COALESCE(EXCLUDED.unit, gfh_gauge.unit), updated_at=now()""",
                        [{**g, **{k: (th.get(g["gauge_id"]) or {}).get(k) for k in ("warning", "danger", "extreme", "unit")}} for g in gauges])
        cur.executemany("""INSERT INTO gfh_status (gauge_id, issued_time, severity, trend, range_start, range_end, inundation)
                           VALUES (%(gauge_id)s, %(issued_time)s, %(severity)s, %(trend)s, %(range_start)s, %(range_end)s, %(inundation)s)
                           ON CONFLICT DO NOTHING""", status)
        cur.executemany("""INSERT INTO gfh_forecast (gauge_id, issued_time, start_time, end_time, value)
                           VALUES (%(gauge_id)s, %(issued_time)s, %(start_time)s, %(end_time)s, %(value)s) ON CONFLICT DO NOTHING""", fcs)
        c.commit()
    log.info("google_floodhub: %d gauges, %d statuses (%d not NO_FLOODING), %d forecast steps", len(gauges), len(status),
             sum(1 for s in status if s["severity"] != "NO_FLOODING"), len(fcs))
    return max((s["issued_time"] for s in status), default=None)


def google_floodhub_backfill(days: int = 366) -> int:
    """Q55 (D-097), once: a year of Flood Hub daily forecasts per point (the API keeps it; equal to what we stored live,
    320/320), so `star` can be trained with it. Five points per call (a year is ~366 forecasts each); key in the header;
    responses archived like every call. Returns the steps stored."""
    if not settings.google_flood_api_key:
        return 0
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with db.connect() as c:
        ids = [r["gauge_id"] for r in c.execute("SELECT gauge_id FROM gfh_gauge WHERE has_model ORDER BY gauge_id").fetchall()]
    n = 0
    for i in range(0, len(ids), 5):
        chunk = ids[i:i + 5]
        fcs = parsing.parse_gfh_forecasts(_gfh("GET", "gauges:queryGaugeForecasts",
                                               params=[("gaugeIds", g) for g in chunk] + [("issuedTimeStart", since)]))
        with db.connect() as c, c.cursor() as cur:
            cur.executemany("""INSERT INTO gfh_forecast (gauge_id, issued_time, start_time, end_time, value)
                               VALUES (%(gauge_id)s, %(issued_time)s, %(start_time)s, %(end_time)s, %(value)s)
                               ON CONFLICT DO NOTHING""", fcs)
            c.commit()
        n += len(fcs)
    log.info("google_floodhub_backfill: %d forecast steps for %d points since %s", n, len(ids), since)
    return n


HII_ANALYST = "https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst"


def hii_dams() -> dt.datetime | None:
    """HII's large dams, daily (RID and EGAT records: storage, inflow, release, spill), for the impact page (D-099)."""
    payload, _ = _get_json("hii_dams", f"{HII_ANALYST}/dam")
    rows = parsing.parse_hii_dams(payload)
    meta = parsing.parse_hii_dam_meta(payload)
    with db.connect() as c, c.cursor() as cur:
        cur.executemany("""INSERT INTO dam (dam_id, agency, name_th, lat, lon, normal_mcm, max_mcm, sub_basin_id)
                           VALUES (%(dam_id)s, %(agency)s, %(name_th)s, %(lat)s, %(lon)s, %(normal_mcm)s, %(max_mcm)s, %(sub_basin_id)s)
                           ON CONFLICT (dam_id) DO UPDATE SET agency=EXCLUDED.agency, name_th=EXCLUDED.name_th, lat=EXCLUDED.lat,
                               lon=EXCLUDED.lon, normal_mcm=EXCLUDED.normal_mcm, max_mcm=EXCLUDED.max_mcm,
                               sub_basin_id=EXCLUDED.sub_basin_id, updated_at=now()""", meta)
        cur.executemany("""INSERT INTO dam_daily (dam_id, agency, name_th, dam_date, storage_mcm, storage_pct, inflow_mcm,
                               released_mcm, spilled_mcm, level_m)
                           VALUES (%(dam_id)s, %(agency)s, %(name_th)s, %(dam_date)s, %(storage_mcm)s, %(storage_pct)s,
                                   %(inflow_mcm)s, %(released_mcm)s, %(spilled_mcm)s, %(level_m)s)
                           ON CONFLICT (dam_id, dam_date) DO UPDATE SET storage_mcm=EXCLUDED.storage_mcm,
                               storage_pct=EXCLUDED.storage_pct, inflow_mcm=EXCLUDED.inflow_mcm, released_mcm=EXCLUDED.released_mcm,
                               spilled_mcm=EXCLUDED.spilled_mcm, level_m=EXCLUDED.level_m, fetched_at=now()""", rows)
        c.commit()
    log.info("hii_dams: %d dam-days", len(rows))
    try:
        hii_dam_history()  # the impact pilot's dam (Kaeng Krachan, RID record 13): history and rule curves
    except Exception:
        log.exception("hii_dam_history failed")
    days = [r["dam_date"] for r in rows]
    return dt.datetime.fromisoformat(max(days)).replace(tzinfo=dt.timezone.utc) if days else None


def dam_year_rows(dam_id: int, agency: str | None, name_th: str | None, released: dict, storage: dict,
                  inflow: dict | None = None) -> list[dict]:
    """One dam's year from HII's yearly graphs (release, storage, inflow), merged by Thai date into dam_daily rows."""
    days: dict[str, dict] = {}
    for key, part in (("released_mcm", released), ("storage_mcm", storage), ("inflow_mcm", inflow or {})):
        for day, value in part.get("series") or []:
            days.setdefault(day, {"released_mcm": None, "storage_mcm": None, "inflow_mcm": None})[key] = value
    return [{"dam_id": dam_id, "agency": agency, "name_th": name_th, "dam_date": day, **vals} for day, vals in sorted(days.items())]


def dam_history_todo(ids: list[int], complete: set, refreshed: dict, this_year: int, first_year: int, per_run: int,
                     case_dams: tuple, now: dt.datetime) -> list[tuple[int, int]]:
    """Which (dam, year) yearly graphs to fetch this run (D-100): current years not refreshed for 20 h first, then missing
    earlier years — at most `per_run` requests, so the hourly task never holds up the collectors. Case dams keep their
    own fuller history (hii_dam_history)."""
    stale = [(d, this_year) for d in ids if d not in case_dams
             and (refreshed.get(d) is None or now - refreshed[d] > dt.timedelta(hours=20))]
    past = [(d, y) for y in range(this_year - 1, first_year - 1, -1) for d in ids
            if d not in case_dams and (d, y) not in complete]
    return (stale + past)[:per_run]


def hii_dams_history(per_run: int = 10, first_year: int = 2018, pause_s: float = 1.0) -> int:
    """Every large dam's rule curve and daily releases (HII analyst/dam_yearly_graph, data_type=dam_released) for the
    national dams layer (D-100), a few requests an hour (dam_history_todo). Returns the dam-days written."""
    now = dt.datetime.now(dt.timezone.utc)
    this_year = dt.datetime.now(parsing.ICT).year
    case_dams = tuple(cfg["dam_ids"]["RID"] for cfg in __import__("floodwatch.impact", fromlist=["CASES"]).CASES.values())
    with db.connect() as c:
        meta = {r["dam_id"]: r for r in c.execute("SELECT dam_id, agency, name_th FROM dam").fetchall()}
        complete = {(r["dam_id"], r["y"]) for r in c.execute(
            """SELECT dam_id, extract(year FROM dam_date)::int AS y FROM dam_daily WHERE released_mcm IS NOT NULL
               AND inflow_mcm IS NOT NULL GROUP BY 1, 2 HAVING count(*) >= 300""").fetchall()}
        refreshed = {}
        for d in meta:
            st = db.get_state(c, f"dam_rule_curve_{d}") or {}
            if st.get("fetched"):
                refreshed[d] = dt.datetime.fromisoformat(st["fetched"])
    written = 0
    for dam_id, year in dam_history_todo(sorted(meta), complete, refreshed, this_year, first_year, per_run // 2 or 1, case_dams, now):
        payload, _ = _get_json("hii_dams", f"{HII_ANALYST}/dam_yearly_graph?data_type=dam_released&dam_id={dam_id}&year={year}")
        part = parsing.parse_hii_dam_year(payload)
        time.sleep(pause_s)
        # inflow too (D-102): a reservoir outlook — even persistence with an honest band — needs each dam's inflow history
        inflow = parsing.parse_hii_dam_year(_get_json("hii_dams", f"{HII_ANALYST}/dam_yearly_graph?data_type=dam_inflow&dam_id={dam_id}&year={year}")[0])
        m = meta[dam_id]
        rows = dam_year_rows(dam_id, m["agency"], m["name_th"] or part["name_th"], part, {"series": []}, inflow=inflow)
        with db.connect() as c, c.cursor() as cur:
            cur.executemany("""INSERT INTO dam_daily (dam_id, agency, name_th, dam_date, storage_mcm, released_mcm, inflow_mcm)
                               VALUES (%(dam_id)s, %(agency)s, %(name_th)s, %(dam_date)s, %(storage_mcm)s, %(released_mcm)s, %(inflow_mcm)s)
                               ON CONFLICT (dam_id, dam_date) DO UPDATE SET
                                   released_mcm = COALESCE(dam_daily.released_mcm, EXCLUDED.released_mcm),
                                   inflow_mcm = COALESCE(dam_daily.inflow_mcm, EXCLUDED.inflow_mcm)""", rows)
            if year == this_year and part["upper"]:
                db.set_state(c, f"dam_rule_curve_{dam_id}", {**{k: part[k] for k in ("upper", "lower", "normal", "upper_bound",
                                                                                       "lower_bound")}, "fetched": now.isoformat()})
            c.commit()
        written += len(rows)
        time.sleep(pause_s)
    log.info("hii_dams_history: %d dam-days", written)
    return written


def hii_dam_history(dam_id: int = 13, first_year: int = 2018, pause_s: float = 1.0) -> int:
    """A dam's daily release and storage since `first_year` and its rule curves (HII analyst/dam_yearly_graph), for the
    impact page (D-099): earlier years once (until ≥ 300 days are stored), the current year every run. Existing daily
    records win (COALESCE). Returns the rows written."""
    this_year = dt.datetime.now(parsing.ICT).year
    with db.connect() as c:
        have = {r["y"] for r in c.execute("""SELECT extract(year FROM dam_date)::int AS y FROM dam_daily WHERE dam_id=%s
                                             AND released_mcm IS NOT NULL AND inflow_mcm IS NOT NULL GROUP BY 1
                                             HAVING count(*) >= 300""", (dam_id,)).fetchall()}
        meta = c.execute("SELECT agency, name_th FROM dam_daily WHERE dam_id=%s ORDER BY dam_date DESC LIMIT 1", (dam_id,)).fetchone()
    agency, name = (meta["agency"], meta["name_th"]) if meta else (None, None)
    written, curves = 0, None
    for year in [y for y in range(first_year, this_year) if y not in have] + [this_year]:
        parts = {}
        for kind in ("dam_released", "dam_storage", "dam_inflow"):
            payload, _ = _get_json("hii_dams", f"{HII_ANALYST}/dam_yearly_graph?data_type={kind}&dam_id={dam_id}&year={year}")
            parts[kind] = parsing.parse_hii_dam_year(payload)
            time.sleep(pause_s)
        curves = curves or (parts["dam_released"] if parts["dam_released"]["upper"] else None)
        rows = dam_year_rows(dam_id, agency, name or parts["dam_released"]["name_th"], parts["dam_released"], parts["dam_storage"],
                             inflow=parts["dam_inflow"])
        with db.connect() as c, c.cursor() as cur:
            cur.executemany("""INSERT INTO dam_daily (dam_id, agency, name_th, dam_date, storage_mcm, released_mcm, inflow_mcm)
                               VALUES (%(dam_id)s, %(agency)s, %(name_th)s, %(dam_date)s, %(storage_mcm)s, %(released_mcm)s, %(inflow_mcm)s)
                               ON CONFLICT (dam_id, dam_date) DO UPDATE SET
                                   released_mcm = COALESCE(dam_daily.released_mcm, EXCLUDED.released_mcm),
                                   storage_mcm = COALESCE(dam_daily.storage_mcm, EXCLUDED.storage_mcm),
                                   inflow_mcm = COALESCE(dam_daily.inflow_mcm, EXCLUDED.inflow_mcm)""", rows)
            c.commit()
        written += len(rows)
    if curves:
        with db.connect() as c:
            db.set_state(c, f"dam_rule_curve_{dam_id}", {k: curves[k] for k in ("upper", "lower", "normal", "upper_bound", "lower_bound")})
            c.commit()
    log.info("hii_dam_history %s: %d dam-days", dam_id, written)
    return written


ONWR_TILES = "https://check-water-map-service-726396821992.asia-southeast3.run.app"
ONWR_LAYERS = {"flood-warn": "flood_warn", "flood-forecast-d1": "nextday01", "flood-forecast-d2": "nextday02",
               "flood-forecast-d3": "nextday03", "flood-area-poly": "FloodArea_Poly"}
ONWR_Z = 10


def onwr_layers(bbox: tuple, get=None) -> dict:
    """ONWR's flood layers inside bbox (lat0, lon0, lat1, lon1) at zoom 10 (SOURCES §2p; owner 2026-10-06: ONWR's layers
    on the impact map): per layer ONWR's own update time and the features {cls, tb, rai, rings [[lat, lon], …]} — the
    area warning (class_risk 1–3), its +1…+3-day forecasts and the observed flooded area per tambon. A tile with no
    features answers 404."""
    from floodwatch import mvt

    def _get(url):
        r = fetch(url)
        archive.store("onwr_tiles", url, r.status, r.body)
        return r
    get = get or _get
    out = {}
    for lid, lname in ONWR_LAYERS.items():
        r = get(f"{ONWR_TILES}/tiles/{lid}/tilejson.json")
        updated = None
        if r.status == 200:
            try:
                updated = json.loads(r.body).get("data_updated")
            except ValueError:
                updated = None
        feats = []
        for x, y in mvt.tiles_for_bbox(*bbox, ONWR_Z):
            t = get(f"{ONWR_TILES}/tiles/{lid}/{ONWR_Z}/{x}/{y}.pbf")
            if t.status != 200:
                continue
            lay = mvt.decode(t.body).get(lname) or {}
            for f in lay.get("features", []):
                p = f["properties"]
                rings = [[[round(c, 5) for c in mvt.to_latlon(px, py, ONWR_Z, x, y, lay["extent"])] for px, py in ring]
                         for ring in f["rings"]]
                feats.append({"cls": p.get("class_risk"), "tb": p.get("TB_IDN"), "rai": p.get("flood_area"), "rings": rings})
        out[lid] = {"updated": updated, "features": feats}
    return out


def onwr_flood() -> dt.datetime | None:
    """ONWR's flood layers over every impact case's river and gauges (padded 0.05°), every 3 h, as collector_state
    'onwr_flood_<case>'; the case state carries them to the impact map. Attributed "ที่มา: สทนช." on the page."""
    from floodwatch import impact
    newest = None
    now = dt.datetime.now(dt.timezone.utc)
    with db.connect() as c:
        for cid in impact.CASES:
            st = db.get_state(c, impact.state_key(cid)) or {}
            pts = [(p["lat"], p["lon"]) for p in st.get("points") or [] if p.get("lat") is not None] + \
                  [(v[0], v[1]) for part in st.get("river_line") or [] for v in part]
            if not pts:
                continue
            bbox = (min(p[0] for p in pts) - 0.05, min(p[1] for p in pts) - 0.05, max(p[0] for p in pts) + 0.05, max(p[1] for p in pts) + 0.05)
            layers = onwr_layers(bbox)
            db.set_state(c, f"onwr_flood_{cid.replace('-', '_')}", {"fetched": now.isoformat(), "bbox": bbox, "layers": layers})
            c.commit()
            for v in layers.values():
                if v.get("updated"):
                    t = dt.datetime.fromisoformat(v["updated"])
                    newest = t if newest is None or t > newest else newest
    return newest


HISTORY_YEARS = 3


def daily_means(obs: list[dict]) -> tuple[dict, dict]:
    """Parsed readings → ({Thai date: mean level of the 'ok' readings}, {Thai date: mean discharge})."""
    h, q = {}, {}
    for o in obs:
        d = (o["obs_time"] + dt.timedelta(hours=7)).date().isoformat()
        if o.get("level_msl") is not None and o.get("quality_flag") == "ok":
            h.setdefault(d, []).append(float(o["level_msl"]))
        if o.get("discharge") is not None:
            q.setdefault(d, []).append(float(o["discharge"]))
    mean = lambda acc: {d: round(sum(v) / len(v), 4) for d, v in acc.items()}
    return mean(h), mean(q)


def impact_history(per_run: int = 20, pause_s: float = 2.0) -> dt.datetime | None:
    """Three years of daily means for every impact case's river points (owner 2026-10-06: "best performance / less
    errors"; research/2026-10-06_e7d_down_3y*.log: on three wet seasons the gain model beat the served hybrid). HII's
    waterlevel_graph serves older months when start and end are both in the past; the database keeps 400 days, so the
    older years live as daily means in collector_state 'impact_daily_<case>' ({"data": {code: {"h", "q"}}, "months":
    {code: [YYYY-MM, …]}}). Oldest missing month first, ≤ per_run months a run, paced; months the database still holds
    (the last ~12) are left to it."""
    from floodwatch import impact
    today = dt.datetime.now(parsing.ICT).date()
    first = dt.date(today.year - HISTORY_YEARS, today.month, 1)
    stop = (today - dt.timedelta(days=330)).replace(day=1)  # the database covers the rest
    months = []
    m = first
    while m < stop:
        months.append(m)
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    done_any = 0
    with db.connect() as c:
        for cid, cfg in impact.CASES.items():
            key = f"impact_daily_{cid.replace('-', '_')}"
            st = db.get_state(c, key) or {"data": {}, "months": {}}
            codes = [p["code"] for p in cfg["points"]]
            stations = {r["code"]: dict(r) for r in c.execute(
                "SELECT code, hii_id, bank_msl, ground_msl FROM station WHERE code = ANY(%s) AND hii_id IS NOT NULL", (codes,)).fetchall()}
            todo = [(mo, code) for mo in months for code in codes if code in stations and mo.isoformat()[:7] not in st["months"].get(code, [])]
            for mo, code in todo[:max(0, per_run - done_any)]:
                s_ = stations[code]
                end = dt.date(mo.year + (mo.month == 12), mo.month % 12 + 1, 1) - dt.timedelta(days=1)
                url = (f"{HII}/waterlevel_graph?station_type=tele_waterlevel&station_id={s_['hii_id']}&start_date={mo.isoformat()}"
                       f"&end_date={urllib.parse.quote(end.isoformat() + ' 23:59')}")
                payload, sha = _get_json("hii_waterlevel_graph", url)
                h, q = daily_means(parsing.parse_waterlevel_graph(code, payload, s_["bank_msl"], s_["ground_msl"], sha))
                d = st["data"].setdefault(code, {"h": {}, "q": {}})
                d["h"].update(h)
                d["q"].update(q)
                st["months"].setdefault(code, []).append(mo.isoformat()[:7])
                done_any += 1
                time.sleep(pause_s)
            db.set_state(c, key, st)
            c.commit()
    log.info("impact_history: %d months fetched", done_any)
    return None


def run(source: str) -> None:
    _run(source, {"hii_waterlevel": hii_waterlevel, "hii_stations": hii_stations, "hii_rain": hii_rain, "hii_history": hii_history, "hii_backfill": hii_backfill,
                  "openmeteo": openmeteo, "traffy": traffy, "bma_klong": bma_klong, "bma_dds": bma_dds,
                  "hii_fews_forecast": hii_fews_forecast, "openmeteo_prev": openmeteo_prev, "bma_history": bma_history,
                  "openmeteo_cells": openmeteo_cells, "openmeteo_prev_cells": openmeteo_prev_cells,
                  "openmeteo_fine": openmeteo_fine, "hii_geo": hii_geo, "dwr_ews": dwr_ews, "google_floodhub": google_floodhub, "hii_dams": hii_dams,
     "hii_dams_history": hii_dams_history, "onwr_flood": onwr_flood, "impact_history": impact_history}[source])
