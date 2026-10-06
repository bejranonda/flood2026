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
    assert 4 <= len(lines) <= 7 and all(len(x) <= explain.ITEM_MAX for x in lines)
    text = "\n".join(lines)
    assert text.startswith("สถานการณ์:") and "แก่งกระจาน" in text and "725" in text
    assert any(x.startswith(("★ แผนตามเกณฑ์:", "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์")) for x in lines)
    assert any(x.startswith("ทางเลือก") for x in lines) and "ไม่ใช่ประกาศทางการ" in lines[-1]
    star = next(p for p in cmp["plans"] if p["optimal"])
    if star["outside_any"]:
        assert any(x.startswith("⚠ นอกช่วงข้อมูล") and "เคยวัดสูงสุด" in x for x in lines)
    assert "ปลอดภัย" not in text and "ควร" not in text
    # final review (D-110): units on every storage and plan label, a Thai date like the rest of the app
    assert lines[-1].startswith("ข้อมูล ชป. 6 ต.ค. 69 ·") and "2026-10-06" not in text
    for x in lines[1:3]:  # the ★ and today's plan: label (ล้าน ลบ.ม./วัน) → storage ล้าน ลบ.ม.
        assert "(ล้าน ลบ.ม./วัน) → อ่างวันที่ 7 " in x and " ล้าน ลบ.ม. ·" in x
    assert sum(x.startswith("⚠ นอกช่วงข้อมูล") for x in lines) <= 1


def test_the_brief_places_the_reservoir_against_todays_rule_curve_as_the_chips_do():
    # final review (D-110): the brief took curves7[0] (tomorrow) — "เหนือเส้นควบคุมบน 123" beside the chip's "+127"
    from floodwatch import explain
    cmp = _grid_cmp()
    cmp["dam"] = {**cmp["dam"], "rule_curve": {"upper": 598.0, "lower": 204.0}}
    cmp["upper"] = [602.0] * 7  # tomorrow's curve onward
    first = explain.brief(cmp)[0]
    assert "เหนือเส้นควบคุมบน 127 ล้าน ลบ.ม." in first and "123" not in first
    lines, story = explain.scenarios(cmp)  # the ✨ story already used today's curve: both agree
    assert "127" in story


def _p(pid, label, storage_end, worst, kind="constant", best=(), outside=(), optimal=False):
    return {"id": pid, "kind": kind, "label": label, "release": [10.0] * 7, "optimal": optimal, "best_for": list(best),
            "effects": {"storage_end": storage_end, "worst_margin_min": worst, "ramp_max": 0.0},
            "days": [{"worst_margin": worst, "worst_code": "B.10"}], "km_max": 0.0,
            "outside_any": bool(outside), "outside_detail": [{"code": c, "days": [1], "flow_max": f, "qmax": q} for c, f, q in outside]}


def _brief_cmp(plans, picks, best_for):
    return {"dam": {"name_th": "แก่งกระจาน", "dam_date": "2026-10-06", "storage_mcm": 725.0, "storage_pct": 102.1,
                    "released_mcm": 10.6, "inflow_mcm": 10.3, "rule_curve": {"upper": 598.0}},
            "upper": [598.0] * 7, "plans": plans, "picks": picks, "best_for": best_for,
            "optimal": {"id": "star", "constraints_met": True}, "downstream": {"method": "whatif"},
            "built_at": "2026-10-06T12:06:24+00:00"}


def test_the_briefs_second_alternative_is_the_pick_that_differs_most_from_the_star_and_from_today():
    # final review (D-110): the first pick in goal order could repeat today's plan; now the pick whose day-7 storage
    # differs most from the ★'s, preferring one that also differs from today's (> 1 ล้าน ลบ.ม. or > 0.05 m)
    from floodwatch import explain
    star, hold = _p("star", "21.5 คงที่", 639.0, 0.18, optimal=True), _p("hold", "10.6 วันนี้", 715.0, 2.11, kind="hold")
    near_today = _p("a", "10.8 คงที่", 716.0, 2.12, best=("warning",))     # furthest from the ★ but repeats today's plan
    kept = _p("b", "6→12 สองช่วง", 700.0, 1.85, best=("water",))           # differs from today's by 15 ล้าน ลบ.ม.
    close = _p("c", "20→18 ทยอย", 641.0, 0.30, best=("city",))
    cmp = _brief_cmp([star, hold, near_today, kept, close], ["c", "a", "b"], {"city": "c", "water": "b", "warning": "a"})
    alts = [x for x in explain.brief(cmp) if x.startswith("ทางเลือก (") and "วันนี้" not in x.split(":")[0]]
    assert len(alts) == 1 and alts[0].startswith("ทางเลือก (เก็บน้ำไว้ใช้): 6→12 สองช่วง (ล้าน ลบ.ม./วัน)")
    # no pick differs from today's: the one furthest from the ★ still stands
    also_today = _p("d", "10.6 คงที่", 715.5, 2.13, best=("city",))
    cmp = _brief_cmp([star, hold, near_today, also_today], ["d", "a"], {"city": "d", "warning": "a"})
    assert any(x.startswith("ทางเลือก (เตือนล่วงหน้าได้): 10.8 คงที่") for x in explain.brief(cmp))


def test_several_plans_outside_the_data_share_one_bullet_within_160_characters():
    # final review (D-110): one "⚠ นอกช่วงข้อมูล" bullet per plan pushed the brief past 7 bullets
    from floodwatch import explain
    five = [("B.18", 256, 143), ("B.10", 192, 86), ("B.16", 182, 73), ("B.15", 182, 73), ("PCH001", 182, 73)]
    star = _p("star", "21.5 คงที่", 639.0, 0.18, optimal=True, outside=five)
    hold = _p("hold", "10.6 วันนี้", 715.0, 2.11, kind="hold", outside=five[:1])
    alt = _p("b", "22→2 ทยอย", 705.0, 0.10, best=("dam",), outside=five)
    lines = explain.brief(_brief_cmp([star, hold, alt], ["b"], {"dam": "b"}))
    out = [x for x in lines if x.startswith("⚠ นอกช่วงข้อมูล")]
    assert len(lines) <= 7 and len(out) == 1 and all(len(x) <= explain.ITEM_MAX for x in lines)
    assert out[0].startswith("⚠ นอกช่วงข้อมูล: ★ 21.5 คงที่ (ล้าน ลบ.ม./วัน): B.18 256/143") and "เคยวัดสูงสุด" in out[0]
    assert "และอีก 2 สถานี · และ 10.6 วันนี้, 22→2 ทยอย" in out[0]  # the others by label when their gauges do not fit
    star["outside_detail"], hold["outside_detail"][0]["flow_max"] = star["outside_detail"][:2], 150
    short = explain.brief(_brief_cmp([star, hold], [], {}))  # it all fits: every plan's gauges, the unit once
    assert [x for x in short if x.startswith("⚠")] == [
        "⚠ นอกช่วงข้อมูล: ★ 21.5 คงที่ (ล้าน ลบ.ม./วัน): B.18 256/143, B.10 192/86 · 10.6 วันนี้: B.18 150/143 ลบ.ม./วิ (แผน/เคยวัดสูงสุด)"]


def test_the_simple_story_says_when_the_star_or_a_named_pick_runs_beyond_the_river_data():
    # final review (D-110): the ✨ story said nothing of the ★'s outside label the grid and the sheet show
    from floodwatch import explain
    cmp = _grid_cmp()
    star = next(p for p in cmp["plans"] if p["optimal"])
    star.update(outside_any=True, outside_detail=[{"code": "B.18", "days": [1, 2], "flow_max": 256.0, "qmax": 143.0}])
    lines, story = explain.scenarios(cmp)
    assert any(x.startswith("⚠ นอกช่วงข้อมูล (") and "B.18 256/143" in x for x in lines)
    assert "แผนนี้อยู่นอกช่วงข้อมูล" in story and "เคยวัด" in story and "ไม่ใช่ค่าพยากรณ์" in story
    assert "ดูในแต่ละการ์ด" not in story
    star.update(outside_any=False, outside_detail=[])
    lines, story = explain.scenarios(cmp)
    assert not any("นอกช่วงข้อมูล" in x for x in lines) and "นอกช่วงข้อมูล" not in story
    # a named pick outside: the story says some plan is, after naming the picks
    pick = {**star, "id": "pk", "optimal": False, "label": "22→2 ทยอย", "kind": "ramp", "release": [22.0, 19.0, 15.0, 12.0, 9.0, 5.0, 2.0],
            "outside_any": True, "outside_detail": [{"code": "B.10", "days": [1], "flow_max": 192.0, "qmax": 86.0}]}
    cmp["plans"].append(pick)
    cmp["best_for"] = {**{k: None for k in cmp["best_for"]}, "dam": "pk"}
    lines, story = explain.scenarios(cmp)
    assert any(x.startswith("⚠ นอกช่วงข้อมูล (22→2 ทยอย)") for x in lines)
    assert "บางแผนอยู่นอกช่วงข้อมูล" in story and story.index("ดูในตาราง") < story.index("บางแผนอยู่นอกช่วงข้อมูล")


def test_an_ai_line_may_not_drop_a_caveat_the_rule_line_carries():
    # final review (D-110): check_item only rejected additions; GLM's "แผนที่เลือกคือ …" for "★ แผนตามเกณฑ์: …" and a
    # data line without "ไม่ใช่ประกาศทางการ" passed
    from floodwatch import explain
    own = "★ แผนตามเกณฑ์: 14→8 ทยอย (ล้าน ลบ.ม./วัน) → อ่างวันที่ 7 720 ล้าน ลบ.ม."
    assert "dropped 'ตามเกณฑ์'" in explain.check_item("แผนที่เลือกคือ 14→8 ทยอย ทำให้อ่างวันที่ 7 เหลือ 720 ล้าน ลบ.ม.", own)
    assert explain.check_item("แผนตามเกณฑ์คือ 14→8 ทยอย ทำให้อ่างวันที่ 7 เหลือ 720 ล้าน ลบ.ม.", own) == []
    data = "ข้อมูล ชป. 6 ต.ค. 69 · ไม่ใช่ประกาศทางการ"
    assert "dropped 'ไม่ใช่ประกาศทางการ'" in explain.check_item("ข้อมูลจาก ชป. วันที่ 6 ต.ค. 69", data)
    story = ("บทสรุป: แผนที่เข้าเกณฑ์คือ 14→8 ทยอย แผนนี้อยู่นอกช่วงข้อมูล: บางวันน้ำมากกว่าที่สถานีเคยวัดได้ "
             "ใช้เทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์\n⚠ นอกช่วงข้อมูล (14→8 ทยอย): B.18 177/150 ลบ.ม./วิ (แผน/เคยวัดสูงสุด)")
    dropped = "แผนที่เข้าเกณฑ์คือ 14→8 ทยอย ใช้เทียบระหว่างแผน"
    assert explain.check(dropped, story) == []  # the public card's check lets it through …
    issues = explain.check_item(dropped, story)  # … the officials' check does not
    assert {"dropped 'นอกช่วงข้อมูล'", "dropped 'เคยวัด'", "dropped 'ไม่ใช่ค่าพยากรณ์'"} <= set(issues)
    kept = "แผนที่เข้าเกณฑ์คือ 14→8 ทยอย ซึ่งอยู่นอกช่วงข้อมูล บางวันน้ำมากกว่าที่สถานีเคยวัดได้ ใช้เทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์"
    assert explain.check_item(kept, story) == []


def test_brief_lines_that_carry_a_caveat_are_never_sent_to_the_ai(monkeypatch):
    # final review (D-110): the ⚠ outside line, the model's limit and the data line stay the rule's own words
    from floodwatch import ai, explain
    explain._cache.clear()
    monkeypatch.setenv("AI_EXPLAIN", "1")
    lines = explain.brief(_grid_cmp())
    sent = []

    def echo(messages, **k):  # GLM that returns each numbered line unchanged
        sent.append(messages[-1]["content"])
        return messages[-1]["content"]
    monkeypatch.setattr(ai, "run", echo)
    items = explain.brief_items(lines)
    assert len(items) == len(lines) and len(sent) == 1
    for line, item in zip(lines, items):
        if line.startswith(("⚠", "ข้อจำกัด:", "ข้อมูล")):
            assert item is None and line not in sent[0]
        else:
            assert item == line
    assert "ไม่ใช่ประกาศทางการ" not in sent[0] and "นอกช่วงข้อมูล" not in sent[0]


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


def test_an_ai_item_may_not_add_advice_or_an_alarm_word_official_forbids():
    # review round 1, D-110: _VERDICTS (the public ✨ card's words) only covers ปลอดภัย/ไม่ท่วม/แน่นอน; check_item must
    # reject the rest of OFFICIAL's own banned list itself, without widening _VERDICTS (that would change check()).
    from floodwatch import explain
    own = "★ แผนตามเกณฑ์: 14→8 ทยอย → อ่างวันที่ 7 720 · ห่างตลิ่งต่ำสุด 0.16 ม. (B.10)"
    issues = explain.check_item("ควรใช้แผน 14→8 ทยอย เพราะอ่างวันที่ 7 720 ห่างตลิ่งต่ำสุด 0.16 ม. (B.10)", own)
    assert issues and any("ควร" in i for i in issues)
    # "ตามเกณฑ์" stays (final review, D-110: a caveat may not be dropped)
    assert explain.check_item("แผนตามเกณฑ์ 14→8 ทยอย ทำให้อ่างวันที่ 7 720 ห่างตลิ่งต่ำสุด 0.16 ม. (B.10)", own) == []
    assert "advice or alarm" not in " ".join(explain.check("ควรติดตามข่าว", "บทสรุป: น้ำทรงตัว"))  # check() itself unchanged
