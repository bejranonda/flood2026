"""River km for every main river (owner 2026-10-03: "Should we adapt tab เจ้าพระยา? because we extended to nationwide
already" → chose "แม่น้ำ tab + forecast"). The downstream end is where the banks are lowest: Thai rivers flow south,
east (Mun) or north (Pattani), so latitude cannot decide."""
from floodwatch import rivers


def _feat(name, parts):
    return {"properties": {"STR_NAMT": name}, "geometry": {"type": "MultiLineString", "coordinates": parts}}


LINE = [[100.0, 13.0 + i * 0.01] for i in range(201)]  # 13.0 -> 15.0 N, ~222 km


def test_km_runs_from_the_end_with_the_lowest_banks_south():
    g = [{"code": "A", "lat": 13.10, "lon": 100.0, "bank_msl": 2.0}, {"code": "B", "lat": 14.00, "lon": 100.0, "bank_msl": 9.0},
         {"code": "C", "lat": 14.90, "lon": 100.0, "bank_msl": 20.0}]
    out = rivers.chainage(_feat("แม่น้ำX", [LINE]), g)
    assert out["mouth"] == [100.0, 13.0]
    assert abs(out["stations"]["A"]["km"] - 11.1) < 0.5 and abs(out["stations"]["C"]["km"] - 211.3) < 1
    assert out["stations"]["A"]["km"] < out["stations"]["B"]["km"] < out["stations"]["C"]["km"]


def test_a_river_flowing_north_gets_its_mouth_in_the_north():
    g = [{"code": "A", "lat": 13.10, "lon": 100.0, "bank_msl": 30.0}, {"code": "B", "lat": 14.00, "lon": 100.0, "bank_msl": 12.0},
         {"code": "C", "lat": 14.90, "lon": 100.0, "bank_msl": 3.0}]
    out = rivers.chainage(_feat("แม่น้ำปัตตานี", [LINE]), g)
    assert out["mouth"] == [100.0, 15.0] and out["stations"]["C"]["km"] < out["stations"]["A"]["km"]
    assert out["agree"] == 1.0  # banks fall monotonically towards the chosen mouth


def test_pieces_of_a_river_are_joined_and_far_gauges_are_left_out():
    a, b = LINE[:101], [[100.0005, 14.0 + i * 0.01] for i in range(101)]  # second piece starts ~50 m from the first's end
    g = [{"code": "A", "lat": 13.10, "lon": 100.0, "bank_msl": 2.0}, {"code": "C", "lat": 14.90, "lon": 100.0, "bank_msl": 20.0},
         {"code": "FAR", "lat": 14.0, "lon": 100.2, "bank_msl": 9.0}]  # ~22 km off the river
    out = rivers.chainage(_feat("แม่น้ำX", [a, b]), g)
    assert abs(out["stations"]["C"]["km"] - 211.3) < 1.5
    assert "FAR" not in out["stations"]


def test_order_keeps_gauges_without_a_place_out_of_the_profile():
    st = [{"code": "A", "river": "แม่น้ำX"}, {"code": "B", "river": "แม่น้ำX"}, {"code": "Z", "river": "แม่น้ำX"}]
    km = {"A": {"km": 10.0, "up": 10.0}, "B": {"km": 50.0, "up": 50.0}}
    assert [s["code"] for s in rivers.order(st, km)] == ["B", "A"]  # upstream first (owner 2026-10-03: upstream at the top)


def test_pieces_with_a_gap_of_a_few_km_are_still_joined():
    # 2026-10-03 validation: the Ping's and Nan's upper pieces are > 1.5 km apart, so Chiang Mai (P.1) and Nan city had no km
    a, b = LINE[:101], [[100.0, 14.03 + i * 0.01] for i in range(98)]  # ~3.3 km gap
    g = [{"code": "A", "lat": 13.10, "lon": 100.0, "bank_msl": 2.0}, {"code": "C", "lat": 14.90, "lon": 100.0, "bank_msl": 20.0}]
    out = rivers.chainage(_feat("แม่น้ำX", [a, b]), g)
    assert "C" in out["stations"] and 205 < out["stations"]["C"]["km"] < 220


def test_profile_keeps_one_river_without_bma_gauges_and_carries_their_km():
    # 2026-10-03 validation: BMA's WL.PKG.01 sat in the HII/RID Chao Phraya chain (levels differ 0.3-0.6 m, KI-217)
    # and, without a river km, was placed by latitude between the Bang Yo gates
    rows = [{"code": "C.12", "river": "แม่น้ำเจ้าพระยา", "agency": "RID"}, {"code": "WL.PKG.01", "river": "แม่น้ำเจ้าพระยา", "agency": "BMA"},
            {"code": "CPY015", "river": "แม่น้ำเจ้าพระยา", "agency": "HII"}, {"code": "P.1", "river": "แม่น้ำปิง", "agency": "RID"}]
    km = {"C.12": {"km": 57.4, "up": 57.4}, "CPY015": {"km": 42.0, "up": 42.0}, "WL.PKG.01": {"km": 45.0, "up": 45.0}}
    out = rivers.profile(rows, "แม่น้ำเจ้าพระยา", km)
    assert [s["code"] for s in out] == ["C.12", "CPY015"] and out[0]["chainage_km"] == 57.4



# --- v0.20.1 (owner 2026-10-03: "They might not found their river there (not all are there)") ------------------------
def _g(code, lat, bank, river, province="น่าน", agency="RID"):
    return {"code": code, "lat": lat, "lon": 100.0, "bank_msl": bank, "river": river, "province": province, "agency": agency}


def test_rivers_with_three_gauges_get_a_view_and_without_a_line_are_ordered_by_bank():
    st = [_g("A", 18.0, 300.0, "น้ำแม่ลาว"), _g("B", 18.5, 420.0, "น้ำแม่ลาว"), _g("C", 18.2, 350.0, "น้ำแม่ลาว"),
          _g("X", 18.0, 10.0, "น้ำสองสาย"), _g("Y", 18.1, 12.0, "น้ำสองสาย")]  # two gauges: no river view
    out = rivers.river_km([], st)
    assert set(out) == {"น้ำแม่ลาว"} and out["น้ำแม่ลาว"]["mouth"] is None
    km = out["น้ำแม่ลาว"]["stations"]
    assert [c for c, _ in sorted(km.items(), key=lambda x: -x[1]["up"])] == ["B", "C", "A"] and km["A"]["km"] is None


def test_polder_canals_get_no_river_view_but_natural_khlongs_do():
    # Bangkok-region canals are pumped and gated (no upstream); in the south "คลอง" names natural rivers (Hat Yai)
    polder = [_g(f"K{i}", 13.9, 1.0 + i, "คลองหกวา", province="ปทุมธานี") for i in range(3)]
    south = [_g(f"U{i}", 6.9 + i / 10, 5.0 + 3 * i, "คลองอู่ตะเภา", province="สงขลา") for i in range(3)]
    out = rivers.river_km([], polder + south)
    assert "คลองอู่ตะเภา" in out and "คลองหกวา" not in out


def test_a_khlong_whose_provinces_are_unknown_gets_no_river_view():
    # 2026-10-03 live: the collector's query lacked `province`, so คลองหกวา (Pathum Thani polder) got a view
    unknown = [{**_g(f"K{i}", 13.9, 1.0 + i, "คลองหกวา"), "province": None} for i in range(3)]
    assert rivers.river_km([], unknown) == {}


# --- v0.21.0 (owner 2026-10-03: "The canals which are under the same basin of river, they should be located in the same
# as that river, not separated into ลำน้ำอื่น, for example คลองนางน้อย is under basin แม่น้ำตรัง") ---------------------------
def _r(code, river, sub, agency="HII"):
    return {"code": code, "river": river, "sub_basin": sub, "agency": agency}


def test_a_gauge_without_its_own_view_joins_the_river_of_its_sub_basin():
    # HII sub-basin 349 holds the 8 แม่น้ำตรัง gauges and TNG003 คลองนางน้อย, TNG005 คลองยวนปลา (live 2026-10-03)
    rows = [_r(f"T{i}", "แม่น้ำตรัง", 349) for i in range(8)] + [_r("L1", "คลองท่าเลา", 349), _r("L2", "คลองท่าเลา", 349),
            _r("L3", "คลองท่าเลา", 349), _r("TNG003", "คลองนางน้อย", 349), _r("TNG005", "คลองยวนปลา", 349),
            _r("X", "ห้วยไกล", 999), _r("N", "คลองไม่มีลุ่ม", None), _r("B", "คลองบางกอกน้อย", 349, agency="BMA")]
    views = {"แม่น้ำตรัง": {f"T{i}" for i in range(8)}, "คลองท่าเลา": {"L1", "L2", "L3"}}
    trib = rivers.tributaries(rows, views)
    assert trib == {"แม่น้ำตรัง": ["TNG003", "TNG005"]}  # the bigger view of the sub-basin; no BMA; none without a sub-basin
