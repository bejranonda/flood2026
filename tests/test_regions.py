"""Task 5 (v0.16, D-064): nationwide parity in the API — regions, the water-body word, same-place twins."""
from floodwatch import api, point, regions

# every province with a gauge on 2026-09-30 (production DB)
PROVINCES = """กระบี่ กรุงเทพมหานคร กาญจนบุรี กาฬสินธุ์ กำแพงเพชร ขอนแก่น จันทบุรี ฉะเชิงเทรา ชลบุรี ชัยนาท ชัยภูมิ ชุมพร ตรัง ตราด ตาก
นครนายก นครปฐม นครพนม นครราชสีมา นครศรีธรรมราช นครสวรรค์ นนทบุรี นราธิวาส น่าน บึงกาฬ บุรีรัมย์ ปทุมธานี ประจวบคีรีขันธ์ ปราจีนบุรี
ปัตตานี พระนครศรีอยุธยา พะเยา พังงา พัทลุง พิจิตร พิษณุโลก ภูเก็ต มหาสารคาม มุกดาหาร ยะลา ยโสธร ระนอง ระยอง ราชบุรี ร้อยเอ็ด ลพบุรี
ลำปาง ลำพูน ศรีสะเกษ สกลนคร สงขลา สตูล สมุทรปราการ สมุทรสงคราม สมุทรสาคร สระบุรี สระแก้ว สิงห์บุรี สุพรรณบุรี สุราษฎร์ธานี สุรินทร์
สุโขทัย หนองคาย หนองบัวลำภู อุดรธานี อุตรดิตถ์ อุทัยธานี อุบลราชธานี อ่างทอง เชียงราย เชียงใหม่ เพชรบุรี เพชรบูรณ์ เลย แพร่ แม่ฮ่องสอน""".split()


def test_every_province_with_a_gauge_has_a_region_and_all_77_are_listed():
    assert all(regions.region_of(p) for p in PROVINCES)
    assert len(regions.PROVINCE_REGION) == 77
    assert regions.region_of("กรุงเทพมหานคร") == "bkk" and regions.region_of("นนทบุรี") == "metro"
    assert regions.region_of("พระนครศรีอยุธยา") == "up" and regions.region_of("เลย") == "northeast"
    assert regions.region_of("เชียงใหม่") == "north" and regions.region_of("สงขลา") == "south"
    assert regions.region_of("ชลบุรี") == "east" and regions.region_of("กาญจนบุรี") == "west"


def test_gauges_abroad_or_without_a_province_have_no_region():
    assert regions.region_of("สาธารณรัฐแห่งสหภาพเมียนมา") is None and regions.region_of(None) is None


def test_water_word_from_the_river_name_never_guessed():
    w = point.water_word
    assert w({"code": "URTU07", "river": "น้ำพอง"}) == "แม่น้ำ"
    assert w({"code": "C.2", "river": "แม่น้ำเจ้าพระยา"}) == "แม่น้ำ" and w({"code": "X", "river": "แควน้อย"}) == "แม่น้ำ"
    assert w({"code": "X", "river": "คลองแสนแสบ"}) == "คลอง" and w({"code": "X", "river": "คูเมือง"}) == "คลอง"
    assert w({"code": "X", "river": "ห้วยหลวง"}) == "ลำน้ำ" and w({"code": "X", "river": "ลำตะคอง"}) == "ลำน้ำ"
    assert w({"code": "WL.X.01", "agency": "BMA", "river": None}) == "คลอง"
    assert w({"code": "ATG011", "in_focus": True, "river": None}) == "คลอง"  # Bangkok gates: unchanged
    assert w({"code": "CPY012", "in_focus": True, "river": None}) == "แม่น้ำ"
    assert w({"code": "FOP019", "in_focus": False, "river": None}) == "ลำน้ำ"


def test_natural_waterways_are_rivers_for_the_pin_logic():
    assert point.water_body({"code": "URTU07", "river": "น้ำพอง"}) == "river"
    assert point.water_body({"code": "X", "river": "ห้วยหลวง"}) == "river"
    assert point.water_body({"code": "X", "river": "คลองลาดพร้าว"}) == "khlong"


def _row(code, agency, lat, lon, name="x"):
    return {"code": code, "agency": agency, "lat": lat, "lon": lon, "name_th": name}


def test_two_agencies_at_the_same_place_are_linked_never_merged():
    rows = [_row("URTU07", "EGAT", 16.4870, 101.2630, "น้ำพอง บ้านผานกเค้า (E.29)"), _row("E.29A", "RID", 16.4885, 101.2640),
            _row("K", "RID", 16.4880, 101.2635), _row("FAR", "HII", 16.6, 101.3), _row("NOPOS", "HII", None, None)]
    t = api.find_twins(rows)
    assert t["URTU07"]["code"] in ("E.29A", "K") and t["URTU07"]["agency"] == "RID"
    assert t["E.29A"]["code"] == "URTU07"
    assert "FAR" not in t and "NOPOS" not in t  # > 300 m, or no position


def test_station_list_is_nationwide_by_default():
    import inspect
    assert 'Query("all"' in inspect.getsource(api.stations)
    for fn in (api.point_check, api.near):
        assert "_station_rows(True)" in inspect.getsource(fn)


def test_place_search_prefers_bangkok_but_finds_thai_places_anywhere():
    from floodwatch import geocode
    assert geocode.SEARCH_PARAMS["countrycodes"] == "th" and geocode.SEARCH_PARAMS["bounded"] == 0
    assert geocode.SEARCH_PARAMS["viewbox"] == geocode.VIEWBOX  # Bangkok ranks first when names repeat
