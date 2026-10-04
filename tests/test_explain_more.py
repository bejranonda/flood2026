"""✨ ให้ AI สรุปให้ฟังง่าย ๆ on a station sheet and on the ⚠️ จับตา tab (owner 2026-10-04: "เพิ่ม ✨ … ที่จุด Stations เพื่อสรุปให้ฟัง
แบบง่ายๆ รวมข้อมูลน้ำฝนไปด้วยก็ดีนะ" and "… ที่ tab ⚠️ จับตา เพื่ออธิบายสถานการณ์ภาพรวม และเน้นจุดที่วิกฤติ"). Rules write the story and
the lines; GLM may only retell them (explain.gist, explain.check), as on the pin."""
from floodwatch import explain, risks

ROW_DOWN = {"dir": "falling", "level": "fall", "likely": [-0.12, -0.04], "wide": False, "method": "star", "confidence": "low",
            "median": -0.08}


def station(**k):
    s = {"code": "T.13", "name_th": "บ้านบางการ้อง", "river": "แม่น้ำท่าจีน", "province": "สุพรรณบุรี", "status": "critical",
         "freeboard_m": -0.94, "observed24": {"level": "small_fall", "change_cm": -3, "hours": 24}, "change24": ROW_DOWN,
         "change48": None, "change72": None, "stale": False, "street_reports_6h": 0}
    return {**s, **k}


def test_a_station_summary_is_about_that_station_and_carries_its_rain():
    lines, story = explain.station(station(), {"rain_24h": 42.0, "name_th": "บ้านดอนตาล", "distance_km": 3.2}, 12.0)
    assert lines[0].startswith("📍 สถานีวัดน้ำบ้านบางการ้อง") and "แม่น้ำท่าจีน" in lines[0]
    assert any(l.startswith("🌧️") and "42 มม." in l and "บ้านดอนตาล" in l for l in lines)
    assert any(l.startswith("☁️") and "12 มม." in l for l in lines)
    assert "บ้านบางการ้อง" in story and "ล้นตลิ่ง" in story and "ฝน" in story
    assert "แถวนี้" not in story + " ".join(lines) and "ห่าง 0" not in " ".join(lines)
    assert any(l.startswith("🔮 อีก 24 ชม.") for l in lines)  # the same rows as the sheet


def test_a_stale_station_says_its_data_is_old_and_tells_no_now():
    lines, story = explain.station(station(stale=True, age_min=400), None, None)
    assert "ข้อมูลล่าสุด" in story and "ล้นตลิ่ง" not in story


G = lambda code, prov, fb, **k: {"code": code, "name_th": f"สถานี{code}", "province": prov, "region": "up", "freeboard_m": fb, **k}
WATCH = {"groups": [
    {"key": "over_bank", "items": [
        {"sub": "rising", "provinces": [{"province": "พระนครศรีอยุธยา", "region": "up",
                                          "gauges": [G("A1", "พระนครศรีอยุธยา", -1.20), G("A2", "พระนครศรีอยุธยา", -0.30)]}]},
        {"sub": "flat_or_falling", "provinces": [{"province": "นครปฐม", "region": "up", "gauges": [G("B1", "นครปฐม", -0.50)]}]}]},
    {"key": "may_reach", "items": [G("M1", "สมุทรปราการ", 0.20, sub="rising", band=">50%", hours=24),
                                   G("M2", "กรุงเทพมหานคร", 0.06, sub="flat_or_falling", band="25-50%", hours=48)]},
    {"key": "fast_rise", "items": [G("F1", "พิษณุโลก", 0.9, rise_cm=25, region="north")]},
    {"key": "rain", "items": [{"province": "นราธิวาส", "region": "south", "mm24": 52.0}]}], "records": {}}


def test_the_watch_summary_leads_with_the_most_critical_gauges():
    lines, story = explain.watch(WATCH, "ทั่วประเทศ")
    assert story.index("สถานีA1") < story.index("สถานีM1")  # over the bank and rising, the highest first
    assert "สถานีB1" not in story  # steady over-bank gauges are counted, not named
    assert any(l.startswith("🔴") and "3 สถานี" in l for l in lines)
    assert any("สถานีA1" in l and "120 ซม." in l for l in lines)
    assert any(l.startswith("🟠") and "สถานีM1" in l for l in lines) and not any("สถานีM2" in l for l in lines)
    assert any(l.startswith("🌧") and "นราธิวาส" in l for l in lines)


def test_the_watch_summary_follows_the_tabs_filters():
    north = risks.only(WATCH, region="north", prov="")
    lines, story = explain.watch(north, "ภาคเหนือ")
    assert "สถานีF1" in story and "สถานีA1" not in story and "ภาคเหนือ" in story
    lines, story = explain.watch(risks.only(WATCH, region="all", prov="ตรัง"), "ตรัง")
    assert "ไม่พบ" in story


def test_watch_wording_says_examples_only_when_there_are_more_and_all_when_none_rise():
    one = {"groups": [{"key": "over_bank", "items": [{"sub": "flat_or_falling", "provinces": [
        {"province": "กรุงเทพมหานคร", "region": "bkk", "gauges": [G("B1", "กรุงเทพมหานคร", -0.2), G("B2", "กรุงเทพมหานคร", -0.1)]}]}]},
        {"key": "may_reach", "items": [G("M1", "กรุงเทพมหานคร", 0.32, sub="rising", band=">50%", hours=24)]}], "records": {}}
    lines, story = explain.watch(one, "กทม.")
    assert "ทรงตัวหรือลดลงทั้งหมด" in " ".join(lines) and "น้ำยังขึ้น 0" not in " ".join(lines)
    assert "เช่น" not in story and "ทั้งหมดทรงตัวหรือลดลง" in story
    assert "สถานีM1 (กรุงเทพมหานคร) " in story or story.endswith("สถานีM1 (กรุงเทพมหานคร)")


def test_station_rain_reads_naturally_when_dry_or_at_the_same_spot():
    lines, story = explain.station(station(), {"rain_24h": 0.0, "name_th": "บ้านบางการ้อง", "distance_km": 0.0}, 0.0)
    rain = [l for l in lines if l.startswith("🌧️")][0]
    assert rain == "🌧️ 24 ชม. ที่ผ่านมา: ไม่มีฝน" and "ห่าง 0" not in " ".join(lines)
    near = explain.station(station(), {"rain_24h": 12.0, "name_th": "บ้านบางการ้อง", "distance_km": 0.2}, None)[0]
    assert any(l == "🌧️ 24 ชม. ที่ผ่านมา: ฝนปานกลาง 12 มม. ที่สถานีนี้" for l in near)
    assert lines[0] == "📍 สถานีวัดน้ำบ้านบางการ้อง · แม่น้ำท่าจีน · จ.สุพรรณบุรี"
    assert "บ้านบางการ้อง ล้นตลิ่ง" in story


def test_a_gist_that_fails_the_check_is_asked_once_more(monkeypatch):
    answers = iter(["ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่งครับ", "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง"])
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: next(answers))
    explain._cache.clear()
    assert explain.gist("simple", ["✅ ไม่มีจุดที่น้ำล้นตลิ่ง"], "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง") == "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง"
