import math
import datetime as dt

import pytest
from pydantic import ValidationError

from floodwatch import api


def test_freshness_buckets_are_cumulative():
    now = dt.datetime.now(dt.timezone.utc)
    ts = [now - dt.timedelta(minutes=10), now - dt.timedelta(hours=2), now - dt.timedelta(hours=5),
          now - dt.timedelta(days=3), None]
    f = api._freshness(ts)
    assert f == {"total": 5, "h1": 1, "h3": 2, "h24": 3, "older": 1, "never": 1}


def test_feedback_input_is_whitelisted_and_bounded():
    ok = api.FeedbackIn(code="BKK021", verdict="higher", depth="knee", note="น้ำเอ่อจากท่อ", lat=13.85, lon=100.58)
    assert ok.verdict == "higher"
    with pytest.raises(ValidationError):
        api.FeedbackIn(verdict="terrible")
    with pytest.raises(ValidationError):
        api.FeedbackIn(depth="knee", note="x" * 281)
    with pytest.raises(ValidationError):
        api.FeedbackIn(depth="knee", lat=51.5, lon=0.1)  # outside Thailand


def test_old_reading_is_not_reported_as_current_status():
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=11)
    row = {"code": "X", "name_th": "x", "name_en": None, "lat": None, "lon": None, "bank_msl": 2.0, "ground_msl": -1.0,
           "agency": None, "province": None, "amphoe": None, "river": None, "level_msl": 6.6, "discharge": None,
           "situation_level": None, "obs_time": old, "trend12": None, "delta12": None, "recovery": None,
           "forecast_time": None}
    r = api._station_row(row)
    assert r["status"] == "unknown" and r["stale"]
    r = api._station_row({**row, "obs_time": dt.datetime.now(dt.timezone.utc)})
    assert r["status"] == "critical" and not r["stale"]


def test_chainage_data_is_packaged_and_ordered():
    ch = api.CHAINAGE
    assert ch and ch["CPY015"]["chainage_km"] < ch["C.12"]["chainage_km"] < ch["CPY014"]["chainage_km"] < ch["C.13"]["chainage_km"]


def test_misleading_values_are_filtered_but_the_station_is_kept():
    now = dt.datetime.now(dt.timezone.utc)
    base = {"code": "GLF002", "name_th": "x", "name_en": None, "lat": 13.5, "lon": 100.3, "bank_msl": None,
            "ground_msl": None, "agency": None, "province": None, "amphoe": None, "river": None, "level_msl": 6.8,
            "discharge": None, "situation_level": None, "obs_time": now, "trend12": "rising", "delta12": 0.2,
            "recovery": None, "forecast_time": None, "coord_source": None, "coord_precision_km": None}
    r = api._station_row(base)
    assert r["level_msl"] is None and r["trend12"] is None and "datum_suspect" in r["notes"] and r["status"] == "unknown"
    r = api._station_row({**base, "code": "ATG151", "coord_source": "osm_approx", "coord_precision_km": 5, "bank_msl": 3.0})
    assert r["level_msl"] == 6.8 and "approx_location" in r["notes"]
    assert "no_location" in api._station_row({**base, "code": "X", "lat": None})["notes"]


def test_erratic_gauge_keeps_its_dot_but_not_its_level_status_or_trend():
    now = dt.datetime.now(dt.timezone.utc)
    row = {"code": "WL.SSB.08", "name_th": "x", "name_en": None, "lat": 13.78, "lon": 100.67, "bank_msl": 0.7,
           "ground_msl": None, "critical_msl": 0.45, "warning_msl": 0.3, "agency": "BMA", "province": None,
           "amphoe": None, "river": "คลองแสนแสบ", "level_msl": -0.4, "discharge": None, "situation_level": None,
           "obs_time": now, "trend12": "rising", "delta12": 0.19, "recovery": None, "forecast_time": now,
           "fc_now": -0.4, "q12": [-0.5, -0.3, -0.2, -0.1, 0.1], "coord_source": None, "coord_precision_km": None}
    assert api._station_row(row)["status"] == "normal"
    obs = {"change_cm": -5, "r2": 0.83, "level": "fall"}
    assert api._station_row({**row, "observed24": obs})["observed24"] == obs  # measured 24 h change passes through
    r = api._station_row({**row, "erratic": {"steps": 24}, "observed24": obs})
    assert r["observed24"] is None
    assert r["lat"] == 13.78 and "erratic" in r["notes"] and r["status"] == "unknown"
    assert r["level_msl"] is None and r["freeboard_m"] is None and r["trend12"] is None and r["change12"] is None


def test_alias_page_declares_itself_canonical_and_redirect_is_off_by_default(monkeypatch):
    monkeypatch.setattr(api, "REDIRECT_LEGACY", False)  # the default when REDIRECT_LEGACY_HOST is unset (production sets 1, D-034)
    html = '<link rel="canonical" href="https://flood.autobahn.bot/"><meta property="og:url" content="https://flood.autobahn.bot/">'
    assert "flood.bejranonda.com" in api.page_for_host(html, "flood.bejranonda.com")
    assert api.page_for_host(html, "flood.autobahn.bot") == html
    assert api.legacy_redirect_target("flood.bejranonda.com", "/", "") is None  # switch off


def test_legacy_redirect_when_enabled(monkeypatch):
    monkeypatch.setattr(api, "REDIRECT_LEGACY", True)
    assert api.legacy_redirect_target("flood.bejranonda.com", "/", "") == "https://flood.autobahn.bot/"
    assert api.legacy_redirect_target("flood.bejranonda.com", "/static/app.js", "v=10") == "https://flood.autobahn.bot/static/app.js?v=10"
    assert api.legacy_redirect_target("flood.bejranonda.com", "/api/stations", "scope=all") == "https://flood.autobahn.bot/api/stations?scope=all"
    assert api.legacy_redirect_target("flood.bejranonda.com", "/api/health", "") is None
    assert api.legacy_redirect_target("flood.autobahn.bot", "/", "") is None


def test_favicon_and_apple_touch_icon_endpoints():
    r_ico = api.favicon()
    assert r_ico.status_code == 200
    assert "image" in r_ico.media_type
    r_apple = api.apple_touch_icon()
    assert r_apple.status_code == 200
    assert r_apple.media_type == "image/png"
    assert (api.WEB_DIR / "favicon.svg").exists()
    assert (api.WEB_DIR / "favicon.ico").exists()
    assert (api.WEB_DIR / "apple-touch-icon.png").exists()



def test_station_row_reports_history_start_for_new_gauges():
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    row = {"code": "WL.KSG.01", "name_th": "x", "name_en": None, "lat": 13.9, "lon": 100.6, "bank_msl": 1.25,
           "ground_msl": None, "agency": "BMA", "province": "กรุงเทพมหานคร", "amphoe": None, "river": "คลองสอง",
           "coord_source": None, "coord_precision_km": None, "obs_time": now, "level_msl": 1.55, "discharge": None,
           "situation_level": None, "trend12": None, "delta12": None, "recovery": None, "forecast_time": None,
           "raw_time": now, "raw_flag": "ok", "first_time": now - dt.timedelta(hours=36)}
    r = api._station_row(row)
    assert r["history_days"] == 1.5 and r["history_since"].startswith(str((now - dt.timedelta(hours=36)).date()))
    assert api._station_row({**row, "first_time": None})["history_days"] is None


def test_street_counts_within_one_km_only():
    items = [{"lat": 13.7650, "lon": 100.6450}, {"lat": None, "lon": None}]
    reports = [(13.7651, 100.6451), (13.7700, 100.6450), (13.7800, 100.6450), (13.9, 100.9)]  # 0.01, 0.55, 1.67 km, far
    api.street_counts(items, reports)
    assert items[0]["street_reports_6h"] == 2 and items[1]["street_reports_6h"] is None


def test_observed_change_is_from_readings_and_needs_both_ends():
    import datetime as dt
    t = dt.datetime(2026, 9, 26, 18, 0, tzinfo=dt.timezone.utc)
    r = {"level_msl": 1.55, "prev_level": 1.43, "obs_time": t, "prev_time": t - dt.timedelta(hours=2)}
    assert api._observed_change(r) == {"change_m": 0.12, "change_hours": 2.0}
    assert api._observed_change({**r, "prev_level": None}) == {"change_m": None, "change_hours": None}


def test_bma_status_uses_bma_drainage_levels_then_bank():
    # WL.SSB.07-like: 35 cm below bank but above BMA critical -> "canal full" (warning), not "normal" (D-038)
    assert api.bma_status(0.40, 0.75, 0.10, 0.22) == ("warning", 0.18)
    assert api.bma_status(0.15, 0.75, 0.10, 0.22) == ("watch", -0.07)
    assert api.bma_status(0.05, 0.75, 0.10, 0.22) == ("normal", -0.17)
    assert api.bma_status(0.80, 0.75, 0.10, 0.22)[0] == "critical"
    assert api.bma_status(0.30, 0.75, None, None) == ("normal", None)  # no BMA levels: bank only
    assert api.bma_status(None, 0.75, 0.1, 0.2) == ("unknown", None)


def test_access_log_never_records_search_text_or_coordinates_d032():
    import logging
    from floodwatch import api
    f = api.RedactQuery()
    def rec(path):
        r = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                              ("1.2.3.4:5", "GET", path, "1.1", 200), None)
        f.filter(r)
        return r.getMessage()
    assert "ซอย" not in rec("/api/geocode?q=%E0%B8%8B%E0%B8%AD%E0%B8%A2") and "?q=" not in rec("/api/geocode?q=soi")
    assert "13.7" not in rec("/api/point?lat=13.766&lon=100.646")
    assert "13.7" not in rec("/api/reverse?lat=13.77&lon=100.64") and "100.6" not in rec("/api/near?lat=13.7&lon=100.6")
    assert "scope=focus" in rec("/api/stations?scope=focus")  # other endpoints unchanged


def test_reverse_label_from_nominatim_address():
    from floodwatch import geocode
    bkk = {"quarter": "แขวงคลองจั่น", "suburb": "เขตบางกะปิ", "city": "กรุงเทพมหานคร"}
    assert geocode.reverse_label(bkk) == "คลองจั่น, บางกะปิ, กรุงเทพมหานคร"  # the wireframe of issue #3
    rural = {"village": "ตำบลบางปลาม้า", "county": "อำเภอบางปลาม้า", "province": "จังหวัดสุพรรณบุรี"}
    assert geocode.reverse_label(rural) == "บางปลาม้า, บางปลาม้า, สุพรรณบุรี"
    assert geocode.reverse_label({}) is None
    assert geocode.reverse_key(13.7764, 100.6412) == geocode.reverse_key(13.7801, 100.6449)  # same ~1 km cell


def test_change48_is_always_given_and_flagged_proven_only_at_medium_confidence():
    q48 = [0.55, 0.9, 1.01, 1.31, 2.25]  # BKK008-like: persistence, likely -10..+31 cm, 90 % -45..+125 cm
    row = {"fc_now": 1.0, "q12": None, "q24": None, "q48": q48, "sk48": {"method": "persistence"}, "outlook24": None}
    c = api._change_fields(row, "critical")["change48"]
    assert c is not None and c["proven"] is False and c["likely"] == [-0.1, 0.31]
    row["sk48"] = {"method": "star", "skill_vs_persistence": 0.4, "coverage90_backtest": 0.9}
    row["q48"] = [0.9, 0.95, 1.0, 1.05, 1.1]
    assert api._change_fields(row, "critical")["change48"]["proven"] is True


def test_rows_come_from_the_model_only_never_from_a_trend_beside_it():
    # owner 2026-10-03 (Kgt.19A): "Why trend and model forecast in the chart are different? … I thought the trend were
    # calculated by the model". The D-060 override (rows from the measured trend while the chart drew the model) is
    # gone: the recent pace is a method of the model (forecast.recent_rate) and competes in its backtest.
    row = {"fc_now": 16.6, "q12": [16.58, 16.59, 16.6, 16.61, 16.62], "q24": [16.57, 16.59, 16.6, 16.61, 16.63],
           "q48": [16.55, 16.58, 16.6, 16.62, 16.65], "sk12": {"method": "persistence"}, "sk24": {"method": "persistence"},
           "sk48": {"method": "persistence"}, "outlook24": None,
           "observed24": {"change_cm": 124, "r2": 0.88, "level": "strong_rise", "hours": 24, "change6_cm": 1.0}}
    out = api._change_fields(row, "normal")
    for h in (12, 24, 48):
        assert out[f"change{h}"].get("basis") != "measured_trend" and out[f"change{h}"]["median"] == 0.0
    assert not hasattr(api, "follow_measured")


def test_station_rows_are_computed_once_per_ttl_and_shared(monkeypatch):
    # KI-246: ~10 requests/s each ran STATIONS_SQL; 39 at once exhausted Postgres (max_connections 40)
    calls = []

    class C:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, p):
            calls.append(p); return type("R", (), {"fetchall": lambda _s: [{"code": "X"}]})()

    monkeypatch.setattr(api.db, "connect", lambda: C())
    monkeypatch.setattr(api, "_rows_cache", {})
    for _ in range(50):
        assert api._station_rows(False) == [{"code": "X"}]
    api._station_rows(True)
    assert len(calls) == 2  # one query per scope, not 51


def _req(host):
    from starlette.requests import Request
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [(b"host", host.encode())], "query_string": b""})


def test_robots_and_sitemap_point_at_the_host_and_keep_heavy_routes_out():
    r = api.robots(_req("flood.autobahn.bot")).body.decode()
    assert "Sitemap: https://flood.autobahn.bot/sitemap.xml" in r and "Disallow: /api/point" in r and "Allow: /" in r
    assert "Disallow: /api/stations" not in r  # the page itself needs its data
    x = api.sitemap(_req("flood.autobahn.bot"))
    assert x.media_type == "application/xml" and "<loc>https://flood.autobahn.bot/</loc>" in x.body.decode()


def test_home_page_carries_the_running_version_and_share_tags():
    html = api.index(_req("flood.autobahn.bot")).body.decode()
    assert f"v{api.__version__}" in html and "__VERSION__" not in html
    for tag in ('og:image" content="https://flood.autobahn.bot/static/og-image.jpg', "twitter:card", "application/ld+json", '<link rel="canonical"'):
        assert tag in html
    assert (api.WEB_DIR / "og-image.jpg").exists()


def test_a_memoised_payload_may_use_another_memoised_value(monkeypatch):
    # v0.16 deploy, 2026-09-30 20:47 UTC: _stations_data (inside _memo) called _twins() (also _memo) and waited forever
    # on the same non-reentrant lock; /api/stations hung for every visitor.
    import threading
    api._memo_cache.clear()
    done = []
    t = threading.Thread(target=lambda: done.append(api._memo(("outer",), lambda: api._memo(("inner",), lambda: 1) + 1)),
                         daemon=True)
    t.start(); t.join(2)
    assert done == [2]


def test_home_page_is_revalidated_so_a_release_reaches_phones_at_once():
    # 2026-10-01: the owner's phone still ran v0.16.0 code after the v0.16.1 fix (page cached 5 min + an open tab)
    assert api.index(_req("flood.autobahn.bot")).headers["cache-control"] == "no-cache"


def test_the_list_is_rebuilt_from_the_same_rows_snapshot_as_the_pin_panel(monkeypatch):
    # 2026-10-01 C1: the list payload had its own 60 s memo on top of the 60 s rows cache, so a list could be up to
    # 2 min older than a pin panel built from fresh rows (119 vs 118 cm at CHN001).
    built = []
    monkeypatch.setattr(api, "_stations_data", lambda scope: built.append(scope) or {"n": len(built)})
    monkeypatch.setattr(api, "_station_rows", lambda all_: [])
    monkeypatch.setattr(api, "_memo_cache", {})
    monkeypatch.setattr(api, "_rows_cache", {True: (100.0, [])})
    api.stations("all"); api.stations("all")
    assert built == ["all"]  # same snapshot: built once
    api._rows_cache[True] = (200.0, [])  # the rows were refreshed (what the pin panel now uses)
    api.stations("all")
    assert built == ["all", "all"]  # the list follows at once


def test_rain_summary_per_region_takes_the_wettest_point_forecast_and_measured():
    pts = [{"point": "bkk_central", "mm24": 5.0}, {"point": "bkk_north", "mm24": 7.0}, {"point": "g_19.0_99.0", "mm24": 30.0}]
    obs = [{"code": "HII001", "name_th": "อาคาร", "province": "กรุงเทพมหานคร", "rain_24h": 60.0, "rain_1h": 0.5},
           {"code": "X", "name_th": "เชียงใหม่", "province": "เชียงใหม่", "rain_24h": 12.0, "rain_1h": 1.0}]
    regions_of_cells = {"g_19.0_99.0": "north"}
    out = api.rain_by_region(pts, obs, regions_of_cells)
    assert out["bkk"]["forecast_mm24"] == 7.0 and out["bkk"]["measured"]["code"] == "HII001"
    assert out["north"]["forecast_mm24"] == 30.0 and out["north"]["measured"]["rain_24h"] == 12.0
    assert out["all"]["forecast_mm24"] == 30.0 and out["all"]["measured"]["rain_24h"] == 60.0


def test_health_lists_sources_whose_data_stopped_although_the_fetch_succeeds():
    # 2026-10-01: the BMA relay answered every 10 min but its readings stopped at 17:10 UTC; health said "ok"
    now = dt.datetime(2026, 10, 1, 21, 30, tzinfo=dt.timezone.utc)
    rows = [{"source": "bma_klong", "last_data_time": now - dt.timedelta(hours=4, minutes=20)},
            {"source": "hii_waterlevel", "last_data_time": now - dt.timedelta(minutes=20)},
            {"source": "traffy", "last_data_time": None}]
    assert api.stale_sources(rows, now) == ["bma_klong"]


def test_each_gauge_names_its_upstream_gauges_with_the_learned_travel_time():
    # owner 2026-10-02 (basin data, item 1): "water from upstream is coming" — from learned links, never a forecast
    learned = {"NAN012": [["N.27A", 5, 0.81], ["N.5A", 9, 0.6]]}
    m = api.upstream_map(learned, {"C.2": 200.0, "C.13": 275.3, "C.7A": 150.0})
    assert m["NAN012"] == [{"code": "N.27A", "lag_h": 5}, {"code": "N.5A", "lag_h": 9}]
    assert m["C.7A"] == [{"code": "C.2", "lag_h": None}]  # Chao Phraya chain: upstream known, travel time not learned


def test_explain_queries_are_private_like_the_point_check():
    # /api/explain carries the pin (D-032): its query string never reaches the access log, robots stay out
    import logging
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0, '%s - "%s %s HTTP/%s" %d',
                            ("1.2.3.4", "GET", "/api/explain?lat=13.75&lon=100.66&q=home", "1.1", 200), None)
    api.RedactQuery().filter(rec)
    assert "13.75" not in rec.args[2] and rec.args[2].startswith("/api/explain")
    assert "Disallow: /api/explain" in api.robots(_req("flood.autobahn.bot")).body.decode()


def test_explain_rejects_unknown_questions():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        api.explain_point(13.75, 100.66, "weather")


def test_station_row_carries_the_24_and_48_h_bank_chances():
    # v0.21.0 (D-077): the จับตา tab lists gauges that may reach the bank, from the stored forecast's bands
    now = dt.datetime.now(dt.timezone.utc)
    row = {"code": "X1", "name_th": "x", "name_en": None, "lat": 15.0, "lon": 100.0, "bank_msl": 2.0, "ground_msl": None,
           "agency": "RID", "province": "ชัยนาท", "amphoe": None, "river": None, "level_msl": 1.0, "discharge": None,
           "situation_level": None, "obs_time": now, "trend12": None, "delta12": None, "recovery": None,
           "forecast_time": None, "coord_source": None, "coord_precision_km": None,
           "outlook24": {"bank_chance": "25-50%"}, "outlook48": {"bank_chance": ">50%"}}
    r = api._station_row(row)
    assert r["bank_chance24"] == "25-50%" and r["bank_chance48"] == ">50%"
    assert api._station_row({**row, "obs_time": now - dt.timedelta(days=3)})["bank_chance24"] is None  # unknown: none
