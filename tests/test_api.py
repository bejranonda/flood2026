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
