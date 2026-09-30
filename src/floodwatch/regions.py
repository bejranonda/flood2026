"""Province -> region for the region chips (D-064): one table, in the API, used by the list, counts and map.

The six official regions (National Research Council of Thailand, 1977: north 9, northeast 20, central 22,
east 7, west 5, south 14 = 77 provinces), with central split the way the app already worked: Bangkok (bkk),
its five neighbours (metro), and the rest of the central plain (up, "เหนือ กทม.").
"""
from __future__ import annotations

REGION_TH = {"bkk": "กทม.", "metro": "ปริมณฑล", "up": "เหนือ กทม.", "north": "ภาคเหนือ", "northeast": "อีสาน",
             "east": "ตะวันออก", "west": "ตะวันตก", "south": "ใต้"}

_REGIONS = {
    "bkk": "กรุงเทพมหานคร",
    "metro": "นนทบุรี ปทุมธานี สมุทรปราการ สมุทรสาคร นครปฐม",
    "up": "กำแพงเพชร ชัยนาท นครนายก นครสวรรค์ พระนครศรีอยุธยา พิจิตร พิษณุโลก เพชรบูรณ์ ลพบุรี สมุทรสงคราม สิงห์บุรี "
          "สุโขทัย สุพรรณบุรี สระบุรี อ่างทอง อุทัยธานี",
    "north": "เชียงราย เชียงใหม่ น่าน พะเยา แพร่ แม่ฮ่องสอน ลำปาง ลำพูน อุตรดิตถ์",
    "northeast": "กาฬสินธุ์ ขอนแก่น ชัยภูมิ นครพนม นครราชสีมา บึงกาฬ บุรีรัมย์ มหาสารคาม มุกดาหาร ยโสธร ร้อยเอ็ด เลย "
                 "ศรีสะเกษ สกลนคร สุรินทร์ หนองคาย หนองบัวลำภู อำนาจเจริญ อุดรธานี อุบลราชธานี",
    "east": "จันทบุรี ฉะเชิงเทรา ชลบุรี ตราด ปราจีนบุรี ระยอง สระแก้ว",
    "west": "กาญจนบุรี ตาก ประจวบคีรีขันธ์ เพชรบุรี ราชบุรี",
    "south": "กระบี่ ชุมพร ตรัง นครศรีธรรมราช นราธิวาส ปัตตานี พังงา พัทลุง ภูเก็ต ยะลา ระนอง สงขลา สตูล สุราษฎร์ธานี",
}
PROVINCE_REGION = {p: r for r, ps in _REGIONS.items() for p in ps.split()}


def region_of(province: str | None) -> str | None:
    """Region key, or None (no province, or a gauge abroad such as the three in Myanmar): shown under ทั้งประเทศ only."""
    return PROVINCE_REGION.get((province or "").strip())
