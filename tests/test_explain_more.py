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
    answers = iter(["ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง ปลอดภัยดี", "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง"])
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: next(answers))
    explain._cache.clear()
    assert explain.gist("simple", ["✅ ไม่มีจุดที่น้ำล้นตลิ่ง"], "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง") == "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง"


def test_the_watch_story_keeps_over_the_bank_and_may_reach_apart():
    # live 2026-10-04: GLM merged an over-bank gauge into "…อีกไม่กี่สถานีที่น้ำกำลังจะถึงตลิ่ง"; the rule story now closes
    # each group's sentence, and "กำลังจะ/ใกล้จะถึงตลิ่ง" is stronger than "อาจถึง" (the check rejects it)
    lines, story = explain.watch(WATCH, "ทั่วประเทศ")
    assert "สถานีA1 (พระนครศรีอยุธยา) และ สถานีA2 ซึ่งน้ำล้นตลิ่งแล้วและยังขึ้นอยู่" in story
    assert "ส่วนอีก 1 สถานีที่ยังไม่ถึงตลิ่ง" in story
    rule = "\n".join(["บทสรุป: " + story] + lines)
    assert "stronger than the forecast" in explain.check("สถานีM1 น้ำกำลังจะถึงตลิ่งในหนึ่งถึงสองวัน", rule)
    assert "stronger than the forecast" not in explain.check("สถานีM1 น้ำยังขึ้นและอาจถึงตลิ่งในหนึ่งถึงสองวัน", rule)


def test_a_retelling_never_ends_by_asking_the_reader_something():
    # live 2026-10-04: "… อยากให้ช่วยดูจุดไหนเพิ่มเติมไหม" (a chatbot question on a summary card)
    rule = "บทสรุป: ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง\n✅ ไม่พบจุดเสี่ยง"
    assert "asks the reader" in explain.check("ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง อยากให้ช่วยดูจุดไหนเพิ่มเติมไหม", rule)
    assert explain.check("ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง", rule) == []


def test_the_watch_story_leaves_upstream_to_the_numbers_when_more_critical_things_exist():
    with_up = {**WATCH, "groups": WATCH["groups"] + [{"key": "upstream", "items": [
        G("U1", "อุตรดิตถ์", 0.5, up={"name_th": "ต้นน้ำ", "rise_cm": 120, "lag_h": 7}, region="north")]}]}
    lines, story = explain.watch(with_up, "ทั่วประเทศ")
    assert "สถานีU1" not in story and any("สถานีU1" in l for l in lines)


def test_polite_particles_are_dropped_not_rejected(monkeypatch):
    # validation 2026-10-04: 13 of 18 rejections were only "ครับ/ค่ะ" (WL.LPG.03 failed three times on them alone)
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่งค่ะ ติดตามข่าวกันต่อไปนะคะ")
    explain._cache.clear()
    assert explain.gist("simple", ["✅ ไม่มีจุดที่น้ำล้นตลิ่ง"], "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง") == "ตอนนี้ยังไม่มีจุดที่น้ำล้นตลิ่ง ติดตามข่าวกันต่อไปนะ"
    assert explain.tidy("ได้คะแนนดี") == "ได้คะแนนดี"  # a word that starts with คะ is not a particle


def _grid_cmp():
    from test_scenarios import _r7_state
    from floodwatch import scenarios as sc
    st = _r7_state()
    st["dam"].update({"name_th": "แก่งกระจาน", "dam_date": "2026-10-06", "storage_mcm": 725.0, "storage_pct": 102.1, "inflow_mcm": 10.3})
    st["reach_km"] = {"B.18": 62.4, "B.10": 45.8, "B.16": 11.4, "B.15": 21.0}
    cmp = sc.compare(st, inflow_today=10.3, upper=[593.0] * 7, lower=[204.0] * 7, normal=710.0, max_release=24.0, customs=[[20.0] * 7])
    cmp.update({"dam": st["dam"], "built_at": "2026-10-06T12:06:24+00:00"})
    return cmp


def test_the_brief_is_short_bullets_with_the_engines_numbers_and_the_outside_label():
    from floodwatch import explain
    cmp = _grid_cmp()
    lines = explain.brief(cmp)
    assert 4 <= len(lines) <= 8 and all(len(x) <= explain.ITEM_MAX for x in lines)
    text = "\n".join(lines)
    assert text.startswith("สถานการณ์:") and "แก่งกระจาน" in text and "725" in text
    assert any(x.startswith(("★ แผนตามเกณฑ์:", "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์")) for x in lines)
    assert any(x.startswith("ทางเลือก") for x in lines) and "ไม่ใช่ประกาศทางการ" in lines[-1]
    star = next(p for p in cmp["plans"] if p["optimal"])
    if star["outside_any"]:
        assert any(x.startswith("⚠ นอกช่วงข้อมูล") and "เคยวัดสูงสุด" in x for x in lines)
    assert "ปลอดภัย" not in text and "ควร" not in text


def test_two_plans_are_compared_by_their_differences_without_a_verdict():
    from floodwatch import explain
    cmp = _grid_cmp()
    star = next(p for p in cmp["plans"] if p["optimal"])
    hold = next(p for p in cmp["plans"] if p["kind"] == "hold")
    lines, story = explain.compare_lines(cmp, hold, star)
    assert lines[0] == f"{hold['label']} เทียบกับ {star['label']}" and any(x.startswith("อ่างวันที่ 7:") for x in lines)
    assert not set(explain._NUM.findall(story)) - set(explain._NUM.findall("\n".join(lines)))  # the story adds no number
    assert "ดีกว่า" not in story and "ปลอดภัย" not in story


def test_ai_items_replace_only_the_lines_they_retell_faithfully(monkeypatch):
    from floodwatch import ai, explain
    explain._cache.clear()
    monkeypatch.setenv("AI_EXPLAIN", "1")
    lines = ["สถานการณ์: อ่างเขื่อนแก่งกระจาน 725 ล้าน ลบ.ม. (102 %)", "ข้อมูล ชป. 2026-10-06 · ไม่ใช่ประกาศทางการ"]
    monkeypatch.setattr(ai, "run", lambda *a, **k: "1) ขณะนี้อ่างเขื่อนแก่งกระจานมีน้ำ 725 ล้าน ลบ.ม. หรือ 102 %\n2) ข้อมูล ชป. 2026-10-07 ปลอดภัย")
    got = explain.retell_items(lines)
    assert got[0] and "725" in got[0] and got[1] is None  # item 2 added a date and a verdict: the rule line stays
    monkeypatch.setenv("AI_EXPLAIN", "0")
    explain._cache.clear()
    assert explain.retell_items(lines) == [None, None]


def test_station_codes_in_the_rule_line_do_not_make_an_ai_line_foreign():
    from floodwatch import explain
    own = "ห่างตลิ่งต่ำสุด 1.73 ม. (PCH001)"
    assert explain.check_item("จุดที่ห่างตลิ่งน้อยที่สุดคือ PCH001 ที่ 1.73 ม.", own) == []
    assert "not Thai" in explain.check_item("lowest margin at PCH001 1.73", own)
