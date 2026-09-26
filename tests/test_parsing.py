import datetime as dt

from floodwatch.collectors import parsing


def test_local_time_is_ict():
    t = parsing.parse_local("2026-09-26 13:30")
    assert t == dt.datetime(2026, 9, 26, 6, 30, tzinfo=dt.timezone.utc)


def test_sentinel_flagged_not_stored():
    assert parsing.qc_level(999999.0, 2.0, -1.0) == (None, "sentinel")
    assert parsing.qc_level(1.2, 2.0, -1.0) == (1.2, "ok")
    assert parsing.qc_level(None, 2.0, -1.0) == (None, "missing")


def test_waterlevel_load_row():
    payload = {"waterlevel_data": {"data": [{
        "waterlevel_datetime": "2026-09-26 13:30", "waterlevel_msl": "2.82", "discharge": None, "situation_level": 5,
        "agency": {"agency_shortname": {"en": "HII"}}, "geocode": {"province_name": {"th": "กรุงเทพมหานคร"}},
        "station": {"id": 1, "tele_station_oldcode": "BKK021", "tele_station_name": {"th": "คลองลาดพร้าว วัดบางบัว"},
                    "tele_station_lat": 13.85402, "tele_station_long": 100.58746, "min_bank": 2.2, "ground_level": -0.33}}]}}
    st, obs = parsing.parse_waterlevel_load(payload, "sha")
    assert st[0]["code"] == "BKK021" and st[0]["in_focus"] and st[0]["bank_msl"] == 2.2
    assert obs[0]["level_msl"] == 2.82 and obs[0]["obs_time"].hour == 6


def test_chart_rows_epoch_utc_and_sentinel():
    rows = [[1790404800000, 2.82, 2.2, -0.33, "2.82"], [1790405400000, 999999, 2.2, -0.33, "999999"]]
    obs, bank, ground = parsing.parse_chart("BKK021", rows, "sha")
    assert bank == 2.2 and ground == -0.33
    assert obs[0]["obs_time"].tzinfo is not None and obs[1]["quality_flag"] == "sentinel"


def test_traffy_drops_text_and_photos():
    payload = {"results": [{"ticket_id": "X", "coords": ["100.6", "13.8"], "timestamp": "2026-09-26 06:51:50.9+00",
                            "description": "น้ำท่วมเข้าบ้าน", "photo_url": "http://x", "problem_type_abdul": [""],
                            "state": "รอรับเรื่อง"}]}
    r = parsing.parse_traffy(payload)[0]
    assert r["is_flood"] and r["lat"] == 13.8 and "description" not in r and "photo_url" not in r


def test_chart_zero_bank_ground_are_unknown_not_zero():
    obs, bank, ground = parsing.parse_chart("ATG011", [[1790410200000, 17.203, 0, 0, "17.203"]], "sha")
    assert bank is None and ground is None and obs[0]["level_msl"] == 17.203


def test_map_feed_gives_coordinates_and_skips_missing():
    rows = [{"code": "BKK001 ", "name": "x", "lat": "13.92", "lng": "100.63", "bank": "2.563", "ground_level": "-1.9",
             "province_name": "กรุงเทพมหานคร", "amphoe_name": "สายไหม", "basin": "b"},
            {"code": "ZZZ", "lat": None, "lng": None}]
    out = parsing.parse_map_feed(rows)
    assert len(out) == 1 and out[0]["code"] == "BKK001" and out[0]["lat"] == 13.92 and out[0]["bank_msl"] == 2.563
