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
