"""DWR early-warning level posts (กรมทรัพยากรน้ำ, ews.dwr.go.th; owner 2026-10-03: "Get history, if possible, then
archive first, and show as trend-only layer"). Their level is the depth on a local staff post (0-9 m), not m MSL, and
336 of 439 alarm levels were the default 4.00 m, so they are kept apart from the gauges: no bank, no status, no
forecast, only the measured change (the same qc rules as our gauges)."""
import datetime as dt

from floodwatch import dwr
from floodwatch.collectors import parsing

ROW = {"stn": "STN0027", "name": "บ้านแม่ตื่น", "stn_type": "wl", "tambon": "แม่ตื่น", "amphoe": "อมก๋อย",
       "province": "เชียงใหม่", "dept": "สทน. 1", "main_basin": "ปิง", "sub_basin": "แม่ตื่น", "latitude": "17.51",
       "longitude": "98.31", "status": "9", "wl": "2.12", "alert_max": "4.00", "date": "04/10/69 01:15 น."}


def test_dwr_rows_parse_buddhist_short_year_thai_time_and_keep_level_posts_only():
    rain = {**ROW, "stn": "STN0001", "stn_type": "RF", "wl": "N/A"}
    blank = {**ROW, "stn": "STN0002", "wl": "N/A"}
    st, obs = parsing.parse_dwr_stations([ROW, rain, blank, {**ROW, "stn": "STN0003", "stn_type": "wl "}])
    assert [s["code"] for s in st] == ["STN0027", "STN0002", "STN0003"]  # level posts, even without a value now
    assert st[0]["lat"] == 17.51 and st[0]["province"] == "เชียงใหม่" and st[0]["alert_max"] == 4.0
    assert obs[0] == {"code": "STN0027", "obs_time": dt.datetime(2026, 10, 3, 18, 15, tzinfo=dt.timezone.utc), "level": 2.12}
    assert len(obs) == 2


def test_a_post_shows_only_its_measured_change_and_says_when_it_is_stuck():
    now = dt.datetime(2026, 10, 4, 12, tzinfo=dt.timezone.utc)
    rising = [(now - dt.timedelta(minutes=30 * k), 2.0 + 0.004 * (48 - k)) for k in range(49)]
    s = dwr.summary(rising, now)
    assert s["trend"]["level"] == "rise" and s["trend"]["change_cm"] == 19 and s["note"] is None
    flat = [(now - dt.timedelta(minutes=30 * k), 1.0) for k in range(49)]
    assert dwr.summary(flat, now)["note"] == "stuck" and dwr.summary(flat, now)["trend"] is None
    young = rising[:10]  # 5 h archived: no 24 h change yet
    assert dwr.summary(young, now)["trend"] is None and dwr.summary(young, now)["note"] == "collecting"
    assert dwr.summary([], now) is None


def test_the_layer_lists_posts_with_a_reading_in_the_last_24_h_only():
    now = dt.datetime(2026, 10, 4, 12, tzinfo=dt.timezone.utc)
    st = [{"code": "A", "name_th": "a", "lat": 17.5, "lon": 98.3, "province": "เชียงใหม่", "amphoe": "x", "tambon": "y"},
          {"code": "B", "name_th": "b", "lat": 17.6, "lon": 98.4, "province": "เชียงใหม่", "amphoe": "x", "tambon": "y"},
          {"code": "C", "name_th": "c", "lat": None, "lon": None, "province": "ตาก", "amphoe": "x", "tambon": "y"}]
    rows = [{"code": "A", "obs_time": now - dt.timedelta(hours=1), "level": 1.0},
            {"code": "B", "obs_time": now - dt.timedelta(hours=30), "level": 1.0},
            {"code": "C", "obs_time": now - dt.timedelta(hours=1), "level": 1.0}]
    out = dwr.items(st, rows, now)
    assert [i["code"] for i in out] == ["A"] and out[0]["note"] == "collecting" and out[0]["province"] == "เชียงใหม่"
