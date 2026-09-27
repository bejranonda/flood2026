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
    # 3. Slightly further station with forecast -> should be in stations_forecast
    st = [
        {"code": "STALE_NEAR", "lat": 13.722, "lon": 100.696, "status": "unknown", "stale": True, "river": "คลองประเวศ"},
        {"code": "LIVE_LOCAL", "lat": 13.725, "lon": 100.698, "status": "warning", "stale": False, "river": "คลองประเวศ", "trend12": "unknown"},
        {"code": "LIVE_FC", "lat": 13.750, "lon": 100.710, "status": "critical", "stale": False, "river": "คลองแสนแสบ", "trend12": "steady", "delta12_median": 0.02},
    ]
    out = point.assess(13.720, 100.695, st, 0, {}, None)
    fc_codes = [s["code"] for s in out["stations_forecast"]]
    near_codes = [s["code"] for s in out["stations_nearby"]]

    assert "LIVE_FC" in fc_codes
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
    assert "53" in out_heavy["forecast"]["desc"]
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
