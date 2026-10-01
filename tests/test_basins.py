"""Basins and rivers from HII's public map files (owner 2026-10-02: "ข้อมูลลุ่มน้ำ … เอาใช้ประโยชน์อะไรได้ไหม")."""
from floodwatch import basins

SQUARE = {"type": "Feature", "properties": {"BASIN_T": "ปิง"},
          "geometry": {"type": "Polygon", "coordinates": [[[98.0, 17.0], [99.0, 17.0], [99.0, 18.0], [98.0, 18.0], [98.0, 17.0]]]}}
ISLANDS = {"type": "Feature", "properties": {"BASIN_T": "ภาคใต้ฝั่งตะวันตก"},
           "geometry": {"type": "MultiPolygon", "coordinates": [[[[98.0, 7.0], [98.2, 7.0], [98.2, 7.2], [98.0, 7.0]]],
                                                               [[[99.0, 8.0], [99.5, 8.0], [99.5, 8.5], [99.0, 8.5], [99.0, 8.0]]]]}}


def _river(name, *parts):
    return {"type": "Feature", "properties": {"STR_NAMT": name}, "geometry": {"type": "MultiLineString", "coordinates": list(parts)}}


# Ping and Nan meet the Chao Phraya; Kolok and Sai Buri reach the sea apart
RIVERS = [_river("แม่น้ำปิง", [[99.0, 17.0], [99.5, 16.0], [100.10, 15.70]]),
          _river("แม่น้ำน่าน", [[100.5, 17.0], [100.2, 16.2], [100.104, 15.703]]),  # mouth ~0.6 km from the confluence
          _river("แม่น้ำเจ้าพระยา", [[100.10, 15.70], [100.3, 14.5], [100.5, 13.6]]),
          _river("แม่น้ำโก-ลก", [[101.8, 5.8], [102.0, 6.2]]),
          _river("แม่น้ำสายบุรี", [[101.3, 6.0], [101.6, 6.7]])]


def test_a_gauge_gets_the_basin_it_lies_in():
    assert basins.basin_of(17.5, 98.5, [SQUARE, ISLANDS]) == "ปิง"
    assert basins.basin_of(8.2, 99.2, [SQUARE, ISLANDS]) == "ภาคใต้ฝั่งตะวันตก"  # second part of a MultiPolygon
    assert basins.basin_of(13.75, 100.5, [SQUARE, ISLANDS]) is None


def test_a_gauge_snaps_to_a_river_within_2_km_only():
    assert basins.river_of(16.0, 99.51, RIVERS) == "แม่น้ำปิง"  # ~1 km off the line
    assert basins.river_of(16.0, 99.7, RIVERS) is None  # ~20 km away: a small stream, not a main river


def test_rivers_that_touch_form_one_system_and_the_sea_separates_others():
    sys_ = basins.river_systems(RIVERS)
    assert sys_["แม่น้ำปิง"] == sys_["แม่น้ำน่าน"] == sys_["แม่น้ำเจ้าพระยา"]
    assert sys_["แม่น้ำโก-ลก"] != sys_["แม่น้ำสายบุรี"]


def test_an_upstream_candidate_must_share_the_river_system_when_both_are_on_main_rivers():
    sys_ = basins.river_systems(RIVERS)
    assert basins.connected("แม่น้ำปิง", "แม่น้ำเจ้าพระยา", sys_)
    assert not basins.connected("แม่น้ำสายบุรี", "แม่น้ำโก-ลก", sys_)
    assert basins.connected(None, "แม่น้ำโก-ลก", sys_)  # a small stream: no river data, the old rule applies


def test_assign_fills_missing_basins_in_hii_style_and_keeps_existing_ones():
    st = [{"code": "A", "lat": 17.5, "lon": 98.5, "basin": None}, {"code": "B", "lat": 17.5, "lon": 98.5, "basin": "ลุ่มน้ำปิง"},
          {"code": "C", "lat": 16.0, "lon": 99.51, "basin": None}]
    out = {u["code"]: u for u in basins.assign(st, [SQUARE], RIVERS)}
    assert out["A"]["basin"] == "ลุ่มน้ำปิง" and out["A"]["basin22"] == "ปิง"  # filled, HII's naming style
    assert out["B"]["basin"] == "ลุ่มน้ำปิง"  # kept
    assert out["C"]["river_main"] == "แม่น้ำปิง" and out["C"]["river_system"] == basins.river_systems(RIVERS)["แม่น้ำปิง"]
