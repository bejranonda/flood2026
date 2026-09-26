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


def test_level_far_above_bank_is_flagged_not_deleted():
    # BKK003 sat at a 7.45 m ceiling with a 2.07 m bank (+5.4 m); genuine flood maxima were <= +1.9 m.
    assert parsing.qc_level(7.45, 2.07, -3.1) == (7.45, "out_of_range")
    assert parsing.qc_level(4.0, 2.07, -3.1) == (4.0, "ok")


def test_bma_klongmap_bank_is_lower_bank_not_critical_and_missing_dropped():
    # Shape as served by the flood69 relay of BMA KlongMap (2026-09-26); values from WL.BPM.03 and a gate.
    payload = {"waterStation": [
        {"water_station_info": None},  # layout-only entries carry no station
        {"water_station_info": {"water_code": "WL.BPM.03", "water_shortname": "ค.บางพรม ถ.กาญจนาฯ", "latitude": 13.76264,
                                "longitude": 100.39624, "left_bank": 1.91, "right_bank": 2.0, "bed_bank": -2.0,
                                "warning": 0.6, "critical": 0.7, "river_name": "คลองบางพรม"},
         "water_level_last": {"site_timestamp": "/Date(1790438700000)/", "wl_in": 1.1, "wl_out01": -99}},
        {"water_station_info": {"water_code": "WL.OFF.01", "latitude": 13.7, "longitude": 100.5, "left_bank": 1.0},
         "water_level_last": {"site_timestamp": "/Date(1790438700000)/", "wl_in": -99}},
    ]}
    stations, obs = parsing.parse_bma_klongmap(payload, "sha")
    s = {x["code"]: x for x in stations}
    assert s["WL.BPM.03"]["bank_msl"] == 1.91 and s["WL.BPM.03"]["critical_msl"] is None  # KI-215
    assert s["WL.BPM.03"]["agency"] == "BMA" and "WL.OFF.01" in s  # the station is kept even without a reading
    assert [(o["code"], o["level_msl"], o["quality_flag"]) for o in obs] == [("WL.BPM.03", 1.1, "ok")]
    assert obs[0]["obs_time"].isoformat() == "2026-09-26T16:05:00+00:00"


def test_geocode_parse_name_area_and_dedup():
    from floodwatch import geocode
    rows = [{"display_name": "ซอยลาดพร้าว 71, แขวงจรเข้บัว, เขตลาดพร้าว, กรุงเทพมหานคร, 10230, ประเทศไทย",
             "lat": "13.8123", "lon": "100.6061"},
            {"display_name": "ซอยลาดพร้าว 71, แขวงจรเข้บัว", "lat": "13.81231", "lon": "100.60611"},
            {"display_name": "", "lat": "1", "lon": "2"}, {"display_name": "x"}]
    assert geocode.parse(rows) == [{"name": "ซอยลาดพร้าว 71", "area": "แขวงจรเข้บัว, เขตลาดพร้าว, กรุงเทพมหานคร",
                                    "lat": 13.8123, "lon": 100.6061}]


def test_geocode_variants_and_rank():
    from floodwatch import geocode
    assert geocode.variants("ลาดพร้าว 71") == ["ลาดพร้าว 71", "ซอยลาดพร้าว 71"]
    assert geocode.variants("ซ.ลาดพร้าว 71") == ["ซอยลาดพร้าว 71"]
    assert geocode.variants("พหล 24") == ["พหลโยธิน 24", "ซอยพหลโยธิน 24"]
    assert geocode.variants("สะพานใหม่") == ["สะพานใหม่"]
    hits = [{"name": "ถนนจรัญสนิทวงศ์"}, {"name": "ซอยลาดพร้าว 71"}]
    assert geocode.rank(geocode.variants("ลาดพร้าว 71"), hits)[0]["name"] == "ซอยลาดพร้าว 71"


def test_bma_reading_far_in_the_future_is_flagged():
    import datetime as dt
    ms = int((dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)).timestamp() * 1000)
    payload = {"waterStation": [{"water_station_info": {"water_code": "WL.X.01", "latitude": 13.7, "longitude": 100.5,
                                                        "left_bank": 1.0}, "water_level_last": {"site_timestamp": f"/Date({ms})/", "wl_in": 0.5}}]}
    _, obs = parsing.parse_bma_klongmap(payload, "sha")
    assert obs[0]["quality_flag"] == "future_time"
