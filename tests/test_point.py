from floodwatch import point


def _st(code, lat, lon, status, river="คลองแสนแสบ", stale=False):
    return {"code": code, "lat": lat, "lon": lon, "status": status, "river": river, "stale": stale}


def test_area_index_is_a_category_with_spread_and_modest_confidence():
    st = [_st("A", 13.750, 100.500, "critical"), _st("B", 13.760, 100.510, "warning"),
          _st("C", 13.770, 100.520, "normal")]
    idx = point.area_index(13.752, 100.503, st)
    assert idx["category"] in ("warning", "critical") and idx["min"] == "normal" and idx["max"] == "critical"
    assert idx["confidence"] != "high" and idx["n"] == 3


def test_far_or_stale_gauges_give_no_answer():
    st = [_st("A", 14.5, 100.5, "critical"), _st("B", 13.75, 100.5, "critical", stale=True)]
    idx = point.area_index(13.75, 100.5, st)
    assert idx["category"] is None and idx["confidence"] == "none"
    out = point.assess(13.75, 100.5, st, 0, {}, None)
    assert "gauges_far_or_disagree" in out["warnings"] and "terrain_not_flat" in out["warnings"]


def test_disagreeing_neighbours_lower_confidence():
    st = [_st("A", 13.750, 100.500, "critical"), _st("B", 13.755, 100.505, "normal")]
    assert point.area_index(13.752, 100.502, st)["confidence"] == "very_low"


def test_water_body_label():
    assert point.water_body({"river": "แม่น้ำเจ้าพระยา"}) == "river"
    assert point.water_body({"river": "คลองลาดพร้าว"}) == "khlong" and point.water_body({"river": None}) == "khlong"


def test_single_distant_gauge_is_very_low_confidence():
    st = [_st("A", 13.854, 100.587, "critical")]
    assert point.area_index(13.82, 100.60, st)["confidence"] == "very_low"


def test_street_reports_override_a_calm_channel_picture():
    # 2026-09-26: 34 BMA gauges read "below bank" with >= 5 Traffy street-flood reports within 1 km (e.g. Saen Saep at
    # Bang Kapi: 35 cm below bank, 35 reports). The point check must not look calm when streets report flooding.
    near = [{"code": "A", "lat": 13.765, "lon": 100.645, "status": "normal", "stale": False, "river": "คลองแสนแสบ"},
            {"code": "B", "lat": 13.770, "lon": 100.650, "status": "normal", "stale": False, "river": "คลองแสนแสบ"}]
    calm = point.assess(13.766, 100.646, near, 0, {}, None)
    assert "street_flooding_despite_channels" not in calm["warnings"]
    wet = point.assess(13.766, 100.646, near, point.STREET_ALERT, {}, None)
    assert "street_flooding_despite_channels" in wet["warnings"]
    over = [{**s, "status": "critical"} for s in near]
    assert "street_flooding_despite_channels" not in point.assess(13.766, 100.646, over, 9, {}, None)["warnings"]


def test_categorized_stations_and_stale_filtering():
    # Stations around point:
    # 1. Nearby but stale -> must be excluded from active recommendations
    # 2. Nearby live BMA canal gauge without forecast -> should be in stations_nearby
    # 3. Slightly further station with forecast (within 3 km) -> should be in stations_forecast
    # 4. A forecast gauge 3.7 km away while closer gauges exist -> not used for the headline (KI-239: same band as the gate)
    st = [
        {"code": "STALE_NEAR", "lat": 13.722, "lon": 100.696, "status": "unknown", "stale": True, "river": "คลองประเวศ"},
        {"code": "LIVE_LOCAL", "lat": 13.725, "lon": 100.698, "status": "warning", "stale": False, "river": "คลองประเวศ", "trend12": "unknown"},
        {"code": "LIVE_FC", "lat": 13.735, "lon": 100.705, "status": "critical", "stale": False, "river": "คลองแสนแสบ", "trend12": "steady", "delta12_median": 0.02},
        {"code": "FAR_FC", "lat": 13.750, "lon": 100.710, "status": "normal", "stale": False, "river": "คลองแสนแสบ", "trend12": "falling", "delta12_median": -0.2},
    ]
    out = point.assess(13.720, 100.695, st, 0, {}, None)
    fc_codes = [s["code"] for s in out["stations_forecast"]]
    near_codes = [s["code"] for s in out["stations_nearby"]]

    assert "LIVE_FC" in fc_codes and "FAR_FC" not in fc_codes
    assert "LIVE_LOCAL" in near_codes
    assert "STALE_NEAR" not in fc_codes
    assert "STALE_NEAR" not in near_codes


def test_point_forecast_synthesis():
    # Scenario A: a close, usable khlong gauge in warning + heavy rain -> high, with the mm quoted
    st_heavy = [
        {"code": "BKK001", "lat": 13.87, "lon": 100.71, "status": "warning", "stale": False, "river": "คลองหกวา", "trend12": "steady", "delta12_median": 0.01}
    ]
    out_heavy = point.assess(13.87, 100.71, st_heavy, 0, {}, 53.0)
    assert out_heavy["forecast"]["risk"] == "high"
    assert "เสี่ยงน้ำท่วมขังเพิ่มขึ้น" in out_heavy["forecast"]["title"]
    # the amount lives in the rain factor now (owner 2026-09-27); the sentence keeps the warning
    assert "53" not in out_heavy["forecast"]["desc"] and "ฝนหนัก" in out_heavy["forecast"]["desc"]
    assert "gauges" in out_heavy["forecast"]["basis"] and "rain" in out_heavy["forecast"]["basis"]

    # Scenario B: a close, usable, calm gauge with light rain -> low, worded as a condition (never "ปกติ" without
    # any confidence check — D-042 also drops the old "ความเสี่ยงน้ำท่วมต่ำ" verdict phrasing)
    st_calm = [
        {"code": "BKK002", "lat": 13.87, "lon": 100.71, "status": "normal", "stale": False, "river": "คลองหกวา", "trend12": "steady", "delta12_median": 0.0}
    ]
    out_calm = point.assess(13.87, 100.71, st_calm, 0, {}, 2.0)
    assert out_calm["forecast"]["risk"] == "low"
    assert "ยังไม่มีสัญญาณน้ำเพิ่ม" in out_calm["forecast"]["title"]


def test_point_forecast_gated_by_confidence_d042():
    # A single gauge 5.6 km away is "very_low" confidence (area_index): the forecast must not carry a canal
    # verdict from it, even though the raw gauge itself reads "warning" (D-021/D-042; was a real bug in v0.6.0
    # where a far, disagreeing gauge still produced a "moderate / rising" banner).
    far = [{"code": "X1", "lat": 13.87, "lon": 100.60, "status": "warning", "stale": False,
            "river": "คลองสามเสน", "trend12": "rising", "delta12_median": 0.06}]
    out = point.assess(13.82, 100.60, far, 0, {}, 16.0)
    assert out["area"]["confidence"] == "very_low"
    assert "gauges" not in out["forecast"]["basis"]
    assert out["forecast"]["risk"] == "info"
    assert "ไม่มีสถานีวัดน้ำใกล้พอ" in out["forecast"]["title"]


def test_point_forecast_no_gauge_never_says_safe():
    # No gauge within RADIUS_KM at all: moderate rain must not be reported as "light" or the point as "calm".
    out = point.assess(14.30, 100.20, [], 0, {}, 18.0)
    assert out["area"]["confidence"] == "none"
    assert out["forecast"]["risk"] == "info"
    assert "ปกติ" not in out["forecast"]["title"] and "ต่ำ" not in out["forecast"]["title"]
    assert "ปานกลาง" in out["forecast"]["desc"]  # 18mm is TMD "moderate", not "light"/"none"


def test_point_forecast_unknown_rain_omits_a_number():
    out = point.assess(14.30, 100.20, [], 0, {}, None)
    assert "มม." not in out["forecast"]["desc"]
    assert out["forecast"]["basis"] == []


def test_point_forecast_heavy_rain_alone_is_moderate_without_a_gauge():
    out = point.assess(13.60, 100.95, [], 0, {}, 46.0)
    assert out["forecast"]["risk"] == "moderate"
    assert out["forecast"]["basis"] == ["rain"]


def test_point_forecast_needs_a_majority_of_agreeing_khlong_gauges():
    # One rising river gauge (tidal, ignored for canal risk) plus two steady khlong gauges close together
    # (medium confidence): the point-wide trend must be the khlong majority ("steady"), not "rising".
    st = [
        {"code": "R1", "lat": 13.821, "lon": 100.601, "status": "watch", "stale": False,
         "river": "แม่น้ำเจ้าพระยา", "trend12": "rising", "delta12_median": 0.10},
        {"code": "C1", "lat": 13.822, "lon": 100.599, "status": "watch", "stale": False,
         "river": "คลองสามเสน", "trend12": "steady", "delta12_median": 0.0},
        {"code": "C2", "lat": 13.819, "lon": 100.602, "status": "watch", "stale": False,
         "river": "คลองบางซื่อ", "trend12": "steady", "delta12_median": 0.0},
    ]
    out = point.assess(13.82, 100.60, st, 0, {}, 5.0)
    assert out["area"]["confidence"] == "medium"
    assert out["forecast"]["channel_trend"] == "steady"


def test_point_forecast_street_reports_alone_are_moderate_not_high():
    # Reports without a heavy-rain reading should not jump straight to "high" (D-042 keeps the >=20mm gate).
    below = point.assess(13.82, 100.60, [], point.STREET_ALERT, {}, 18.0)
    assert below["forecast"]["risk"] == "moderate"
    at_or_above = point.assess(13.82, 100.60, [], point.STREET_ALERT, {}, 20.0)
    assert at_or_above["forecast"]["risk"] == "high"


def test_rain_band_follows_tmd_categories_issue_1():
    # TMD "เกณฑ์อากาศ" (read 2026-09-27): เล็กน้อย 0.1–10.0 · ปานกลาง 10.1–35.0 · หนัก 35.1–90.0 · หนักมาก ≥ 90.1 mm.
    cases = {None: None, 0: "none", 0.05: "none", 0.1: "light", 10.0: "light", 10.1: "moderate", 35.0: "moderate",
             35.1: "heavy", 90.0: "heavy", 90.1: "very_heavy"}
    for mm, key in cases.items():
        got = point.rain_band(mm)
        assert (got[0] if got else None) == key, mm


def test_rain_text_never_uses_a_tilde_and_keeps_label_and_number_consistent():
    # Issue #1: "~27 มม." was read as "−27 มม." on a phone. The number must also not contradict the label
    # (35.1 mm is "ฝนหนัก"; printing "35" would read as "ปานกลาง").
    for mm in (0, 0.4, 10.1, 27.3, 35.1, 53.0, 90.1, 120):
        out = point.assess(14.30, 100.20, [], 0, {}, mm)
        assert "~" not in out["forecast"]["desc"] and "~" not in out["forecast"]["title"]
    # Owner 2026-09-27: the amount is already in the rain factor; the headline sentence keeps the word and the warning
    assert point._rain_phrase(35.1)[1] == "คาดฝนหนัก จุดที่ระบายช้าเสี่ยงน้ำขังบนถนน"
    assert point._rain_phrase(35.0)[1] == "คาดฝนปานกลาง อาจมีน้ำขังบนถนนช่วงฝนตก"
    for mm in (0.4, 27.3, 53.0, 120):
        assert "มม." not in point._rain_phrase(mm)[1]
    assert point.assess(14.30, 100.20, [], 0, {}, 27.3)["rain_band"] == "moderate"
    assert point.assess(14.30, 100.20, [], 0, {}, None)["rain_band"] is None


def test_outlook_lists_gauge_changes_only_when_a_canal_statement_is_allowed_d047():
    ch = {"dir": "rising", "level": "rise", "median": 0.1, "likely": [0.05, 0.15], "confidence": "low"}
    close = [{"code": "C1", "lat": 13.821, "lon": 100.601, "status": "watch", "stale": False, "river": "คลองสามเสน",
              "trend12": "rising", "delta12_median": 0.1, "change12": ch},
             {"code": "C2", "lat": 13.822, "lon": 100.599, "status": "watch", "stale": False, "river": "คลองบางซื่อ",
              "trend12": "rising", "delta12_median": 0.1, "change12": ch}]
    assert point.assess(13.82, 100.60, close, 0, {}, 5.0)["forecast"]["gauges"] == ["C1", "C2"]
    far = [{**close[0], "lat": 13.87}]  # one gauge 5.6 km away -> very_low -> no gauge lines in the banner (D-042)
    out = point.assess(13.82, 100.60, far, 0, {}, 5.0)
    assert out["area"]["confidence"] == "very_low" and out["forecast"]["gauges"] == []


def test_info_outlook_says_disagree_not_far_when_a_gauge_is_close():
    # 13.70, 100.50 on 2026-09-27: CPY015 (river) 0.8 km away, canals beyond -> very_low from disagreement, not distance.
    st = [{"code": "R", "lat": 13.7005, "lon": 100.5075, "status": "watch", "stale": False, "river": "แม่น้ำเจ้าพระยา"},
          {"code": "K1", "lat": 13.72, "lon": 100.51, "status": "critical", "stale": False, "river": "คลองดาวคะนอง"},
          {"code": "K2", "lat": 13.73, "lon": 100.49, "status": "normal", "stale": False, "river": "คลองบางไส้ไก่"}]
    out = point.assess(13.70, 100.50, st, 0, {}, 24.0)
    assert out["area"]["confidence"] == "very_low" and out["area"]["nearest_km"] <= point.NEAR_KM
    assert "ไม่ตรงกัน" in out["forecast"]["title"] and "ใกล้พอ" not in out["forecast"]["title"]


def test_nearest_canal_is_a_khlong_within_3_km_never_a_river_gauge():
    # 13.70,100.50 on 2026-09-27: CPY015 (Chao Phraya, tide) 0.8 km was shown as "คลองใกล้เคียงที่สุด" (review bug).
    ch = {"dir": "falling", "level": "strong_fall", "median": -0.5, "likely": [-0.7, -0.33], "confidence": "medium"}
    river = {"code": "CPY015", "lat": 13.7005, "lon": 100.5075, "status": "watch", "stale": False,
             "river": "แม่น้ำเจ้าพระยา", "trend12": "falling", "delta12_median": -0.5, "change12": ch}
    far_canal = {"code": "K9", "lat": 13.74, "lon": 100.50, "status": "normal", "stale": False, "river": "คลองดาวคะนอง",
                 "trend12": "steady", "delta12_median": 0.0, "change12": {**ch, "dir": "steady", "level": "steady"}}
    out = point.assess(13.70, 100.50, [river, far_canal], 0, {}, 5.0)
    assert out["forecast"]["nearest_canal"] is None  # river gauge excluded; the canal is 4.4 km away (> 3 km)
    # Close gauges that agree: the area statement lists them itself, so no separate "nearest canal" line.
    near_canal = {**far_canal, "code": "K1", "lat": 13.71}
    out = point.assess(13.70, 100.50, [river, near_canal], 0, {}, 5.0)
    assert out["forecast"]["gauges"] and out["forecast"]["nearest_canal"] is None
    # River normal, canal overflowing: the river is not canal evidence (KI-239), so the close canal speaks alone ("low").
    out = point.assess(13.70, 100.50, [{**river, "status": "normal"}, {**near_canal, "status": "critical"}], 0, {}, 5.0)
    assert out["area"]["category"] == "critical" and out["area"]["confidence"] == "low" and "K1" in out["forecast"]["gauges"]


def test_dense_city_is_judged_by_the_nearest_gauges_not_the_whole_8_km_d054():
    # 2026-09-27: with 310 gauges, 83 % of Bangkok pins were "ประเมินไม่ได้" because some gauge within 8 km always
    # disagreed. Two agreeing gauges within 1 km now decide; far ones are only counted.
    st = [_st("A", 13.7610, 100.6400, "normal"), _st("B", 13.7660, 100.6450, "normal"),
          _st("C", 13.8100, 100.6400, "critical"), _st("D", 13.7000, 100.6600, "warning")]
    idx = point.area_index(13.763, 100.642, st)
    assert idx["confidence"] == "medium" and idx["category"] == "normal"
    assert (idx["min"], idx["max"]) == ("normal", "normal") and (idx["min_all"], idx["max_all"]) == ("normal", "critical")
    assert idx["n"] == 4 and idx["n_close"] == 2


def test_nearest_canal_is_reported_with_distance_and_a_far_flag():
    st = [_st("R", 13.7005, 100.5075, "watch", river="แม่น้ำเจ้าพระยา"), _st("K", 13.74, 100.50, "normal")]
    out = point.assess(13.70, 100.50, st, 0, {}, 5.0)
    nc = out["nearest_canal"]
    assert nc["code"] == "K" and nc["far"] is True and nc["distance_km"] > point.NEAR_KM  # river gauge never counts
    st2 = st + [_st("K2", 13.705, 100.502, "critical")]
    nc2 = point.assess(13.70, 100.50, st2, 0, {}, 5.0)["nearest_canal"]
    assert (nc2["code"], nc2["distance_km"], nc2["far"], nc2["station"]["status"]) == ("K2", 0.6, False, "critical")


def test_nearest_canal_with_a_trend_is_given_when_the_nearest_has_none():
    # 13.764,100.679 on 2026-09-27: the nearest canal WL.SMK.01 (0.3 km) is relay-only (1.2 days) -> no trend; the
    # owner: "users cannot see the trend … if there is more than one, show both".
    ch = {"dir": "steady", "level": "steady", "likely": [-0.1, 0.1], "confidence": "low"}
    st = [_st("NEW", 13.7645, 100.6795, "critical"),
          {**_st("OLD", 13.772, 100.690, "normal"), "trend12": "steady", "change24": ch}]
    out = point.assess(13.764, 100.679, st, 0, {}, 5.0)
    assert out["nearest_canal"]["code"] == "NEW" and out["nearest_canal_trend"]["code"] == "OLD"
    st2 = [{**st[0], "trend12": "steady", "change24": ch}, st[1]]
    assert point.assess(13.764, 100.679, st2, 0, {}, 5.0)["nearest_canal_trend"] is None  # nearest already has one


def test_info_outlook_is_short_the_reason_lives_in_the_canal_factor():
    # Owner 2026-09-27: "สถานีใกล้เคียงวัดคนละแหล่งน้ำ … ดูแนวโน้มของแต่ละสถานีด้านล่าง" was too long and not needed.
    st = [{"code": "R", "lat": 13.7005, "lon": 100.5075, "status": "watch", "stale": False, "river": "แม่น้ำเจ้าพระยา"},
          {"code": "K1", "lat": 13.72, "lon": 100.51, "status": "critical", "stale": False, "river": "คลองดาวคะนอง"},
          {"code": "K2", "lat": 13.73, "lon": 100.49, "status": "normal", "stale": False, "river": "คลองบางไส้ไก่"}]
    f = point.assess(13.70, 100.50, st, 0, {}, 24.0)["forecast"]
    assert f["desc"] == point._rain_phrase(24.0)[1] and len(f["title"]) < 50


def test_river_gauges_never_decide_the_canal_factor():
    # KI-239: a Chao Phraya gauge 0.5 km away was the only "close" gauge and set the canal category alone
    st = [_st("R", 13.750, 100.500, "watch", river="แม่น้ำเจ้าพระยา"), _st("K", 13.790, 100.500, "normal")]
    idx = point.area_index(13.7505, 100.5005, st)
    assert idx["n"] == 1 and idx["category"] == "normal"


def test_a_lone_close_gauge_outvoted_nearby_is_not_trusted():
    # issue #3 / KI-239: one overflowing gauge at ~2.9 km, three calm ones at 3.1-4 km -> never "low" (usable) red
    lone = [_st("A", 13.776, 100.500, "critical")]
    calm = [_st(c, 13.750 + d, 100.500, "normal") for c, d in (("B", -0.028), ("C", -0.032), ("D", -0.036))]
    assert point.area_index(13.750, 100.500, lone + calm)["confidence"] == "very_low"
    assert point.area_index(13.750, 100.500, lone)["confidence"] == "low"  # alone, it may still speak (D-054)


def test_headline_trend_is_the_trend_the_rows_show():
    # pin 13.70,100.47 on 2026-09-28: headline "ยังทรงตัว" above rows "↘ ลดลง ราว −10 ซม." (the old trend12 label)
    measured = {"dir": "falling", "level": "fall", "basis": "measured_trend", "method": "persistence", "likely": [-0.1, -0.1]}
    assert point._station_trend({"trend12": "steady", "change12": measured}) == "falling"
    unsure = {"dir": "rising", "level": "rise", "method": "star", "likely": [-0.01, 0.14]}  # range crosses zero
    assert point._station_trend({"trend12": "rising", "change12": unsure}) == "steady"
    assert point._station_trend({"trend12": "rising"}) == "rising"  # no row: the old label still works


def test_a_high_but_falling_canal_is_not_called_steady():
    ch = {"dir": "falling", "level": "small_fall", "basis": "measured_trend", "method": "persistence", "likely": [-0.02, -0.02]}
    st = [{"code": "K", "lat": 13.74, "lon": 100.72, "status": "warning", "stale": False, "river": "คลองประเวศ",
           "trend12": "steady", "change24": ch, "change12": ch}]
    fc = point.assess(13.741, 100.721, st, 0, {}, 3.0)["forecast"]
    assert "ลดลง" in fc["title"] and "ทรงตัว" not in fc["title"] + fc["desc"]
