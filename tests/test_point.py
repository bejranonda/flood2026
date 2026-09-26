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
