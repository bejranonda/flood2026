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


def test_alias_page_declares_itself_canonical_and_redirect_is_off_by_default():
    html = '<link rel="canonical" href="https://flood.autobahn.bot/"><meta property="og:url" content="https://flood.autobahn.bot/">'
    assert "flood.bejranonda.com" in api.page_for_host(html, "flood.bejranonda.com")
    assert api.page_for_host(html, "flood.autobahn.bot") == html
    assert api.legacy_redirect_target("flood.bejranonda.com", "/", "") is None  # REDIRECT_LEGACY_HOST unset


def test_legacy_redirect_when_enabled(monkeypatch):
    monkeypatch.setattr(api, "REDIRECT_LEGACY", True)
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

