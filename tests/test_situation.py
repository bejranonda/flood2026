"""The national situation ticker in the top bar (owner 2026-10-04: "concentrate the all information of Thailand got from
the app into a single running scrolling text … periodically update, like every 30 minutes … let AI prepare it into
simple, attractive and lovely Thai language"; D-089). Rules gather every fact; the AI may only retell them."""
from floodwatch import situation


def st(code, status, prov, group=None, stale=False):
    return {"code": code, "status": status, "province": prov, "stale": stale, "trend": {"group": group} if group else None}


STATIONS = [st("A", "critical", "พระนครศรีอยุธยา", "rising"), st("B", "critical", "พระนครศรีอยุธยา", "rising"),
            st("C", "critical", "ปราจีนบุรี", "flat_or_falling"), st("D", "warning", "นนทบุรี"), st("E", "normal", "ตรัง"),
            st("F", "critical", "ตาก", "rising", stale=True)]
RISKS = {"groups": [{"key": "may_reach", "items": [{"code": "X", "province": "นนทบุรี", "sub": "rising"},
                                                   {"code": "Y", "province": "นครปฐม", "sub": "rising"}]},
                    {"key": "upstream", "items": [{"code": "Z", "province": "สระแก้ว"}]}]}
RAIN = {"all": {"forecast_mm24": 52.0, "forecast_where": "น่าน",
                "measured": {"name_th": "บ้านโนนเขวา", "province": "ขอนแก่น", "rain_24h": 93.0}}}


def test_facts_count_fresh_gauges_and_name_the_places():
    f = situation.facts(STATIONS, RISKS, RAIN)
    assert f["over"] == {"n": 3, "rising": 2, "provinces": 2, "rising_top": [["พระนครศรีอยุธยา", 2]]}
    assert f["near"] == 1 and f["below"] == 1
    assert f["may_reach"] == {"n": 2, "top": ["นนทบุรี", "นครปฐม"], "provinces": 2, "near_steady": 0}
    assert f["upstream"] == {"n": 1, "top": ["สระแก้ว"], "provinces": 1}
    assert f["rain_measured"] == {"mm": 93, "place": "บ้านโนนเขวา", "province": "ขอนแก่น"}
    assert f["rain_forecast"] == {"mm": 52, "province": "น่าน"}


def test_the_rule_ticker_leads_with_what_is_urgent():
    text = situation.rule_text(situation.facts(STATIONS, RISKS, RAIN))
    assert text.index("ล้นตลิ่งและน้ำยังขึ้น 2 สถานี") < text.index("อาจถึงตลิ่ง")
    assert "พระนครศรีอยุธยา" in text and "93 มม." in text and "ขอนแก่น" in text and "น่าน" in text


def test_an_ai_retelling_may_not_add_numbers_places_or_verdicts():
    f = situation.facts(STATIONS, RISKS, RAIN)
    ok = "ตอนนี้มีสถานีที่น้ำล้นตลิ่งและยังขึ้นอยู่ 2 แห่งที่อยุธยา ฝั่งนนทบุรีกับนครปฐมอาจถึงตลิ่งได้ในวันสองวันนี้ ฝนตกหนักสุด 93 มม. ที่ขอนแก่น"
    assert situation.check(ok, f) == []
    assert "new number" in situation.check(ok + " รวม 7 จังหวัด", f)
    assert "new place" in situation.check(ok + " ที่เชียงใหม่ด้วย", f)
    assert any(i.startswith("verdict") for i in situation.check(ok + " พื้นที่อื่นปลอดภัย", f))


def test_the_ticker_uses_the_ai_text_only_when_it_passes_and_otherwise_the_rules(monkeypatch):
    f = situation.facts(STATIONS, RISKS, RAIN)
    monkeypatch.setattr(situation, "_ai", lambda msgs: "1) ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา")
    out = situation.compose(f)
    rule = situation.items(f)
    # item by item: the AI's item 1 passed, every other fact keeps its rule wording (none is ever lost)
    assert out["ai"] is True and out["ai_items"] == 1 and len(out["items"]) == len(rule)
    assert out["items"][0] == {"icon": "🔴", "text": "ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา", "ai": True}
    assert out["items"][1] == {"icon": rule[1]["icon"], "text": rule[1]["text"], "ai": False}
    assert out["rule"] == situation.rule_text(f) and out["rejected"] == []
    monkeypatch.setattr(situation, "_ai", lambda msgs: "1) พื้นที่อื่นปลอดภัยทั้งหมด")
    out = situation.compose(f)
    assert out["ai"] is False and out["text"] == situation.rule_text(f)
    assert sum("verdict" in i for i in out["rejected"]) == 2  # tried twice
    assert [i["icon"] for i in out["items"]] == [i["icon"] for i in situation.items(f)]


def test_the_ticker_is_rewritten_every_30_min_in_the_collector_loop():
    from floodwatch import worker
    assert dict(worker.TASKS)["situation"] == 1800


def test_everyday_words_that_are_province_names_are_not_new_places():
    # 2026-10-04 14:59: two good retellings rejected as "new place" — เลย ("at all"), แพร่ ("spread"), ตาก ("to dry") are
    # also provinces; they count as places only after จ./จังหวัด
    f = situation.facts(STATIONS, RISKS, RAIN)
    ok = "ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา ฝนตกหนักสุด 93 มม. ที่ขอนแก่น ภาพรวมไม่เปลี่ยนมากเลย"
    assert situation.check(ok, f) == []
    assert "new place" in situation.check(ok + " ที่จังหวัดเลยด้วย", f)


MAY = {"groups": [{"key": "may_reach", "items": [
    {"code": "K1", "province": "กรุงเทพมหานคร", "sub": "flat_or_falling"}, {"code": "K2", "province": "กรุงเทพมหานคร", "sub": "flat_or_falling"},
    {"code": "S1", "province": "สมุทรปราการ", "sub": "rising"}, {"code": "S2", "province": "สมุทรปราการ", "sub": "rising"},
    {"code": "P1", "province": "เพชรบุรี", "sub": "rising"}]}]}


def test_may_reach_names_only_provinces_where_the_water_is_rising():
    # owner 2026-10-04: "ควรจับตาพื้นที่กรุงเทพฯ … ที่น้ำอาจถึงตลิ่งในอีก 24–48 ชม." while no Bangkok gauge was rising (all steady
    # just under the bank): steady near-bank gauges are counted apart and never name a province
    f = situation.facts(STATIONS, MAY, RAIN)
    assert f["may_reach"] == {"n": 3, "top": ["สมุทรปราการ", "เพชรบุรี"], "provinces": 2, "near_steady": 2}
    text = situation.rule_text(f)
    assert "อาจถึงตลิ่ง" in text and "สมุทรปราการ" in text and "กรุงเทพ" not in text.split("อาจถึงตลิ่ง")[1].split("·")[0]


BKK = [st("B1", "critical", "กรุงเทพมหานคร", "flat_or_falling"), st("B2", "critical", "กรุงเทพมหานคร", "flat_or_falling"),
       st("B3", "warning", "กรุงเทพมหานคร", "rising"), st("B4", "normal", "กรุงเทพมหานคร")]


def test_bangkok_gets_its_own_line_and_says_when_nothing_is_rising_toward_the_bank():
    f = situation.facts(STATIONS + BKK, MAY, RAIN)
    assert f["bkk"] == {"over": 2, "over_rising": 0, "may_reach_rising": 0, "near": 1}
    line = [p for p in situation.rule_text(f).split(" · ") if "กรุงเทพฯ" in p][0]
    assert "ล้นตลิ่ง 2 จุด" in line and "ทรงตัวหรือลดลง" in line and "ยังไม่มีจุดที่น้ำขึ้นจนอาจถึงตลิ่ง" in line
    assert "ใกล้ตลิ่ง/คลองเต็ม 1 จุด" in line  # the top bar's own words


def test_dam_release_and_the_flow_at_nakhon_sawan_with_their_24_h_change():
    # what the news leads with (Thai PBS 2026-10-03: the C.13 release, the flow at C.2); ours from RID discharge readings
    flows = {"C.13": {"q": 2500.0, "q24": 2510.0}, "C.2": {"q": 2101.0, "q24": 2290.0}}
    f = situation.facts(STATIONS, RISKS, RAIN, flows=flows)
    assert f["flows"] == [{"code": "C.2", "label": "น้ำเหนือที่นครสวรรค์", "q": 2101, "change": -189},
                          {"code": "C.13", "label": "เขื่อนเจ้าพระยาระบาย", "q": 2500, "change": -10}]
    text = situation.rule_text(f)
    assert "น้ำเหนือที่นครสวรรค์ 2,101 ลบ.ม./วินาที ลดลงจากเมื่อวาน 189" in text
    assert "เขื่อนเจ้าพระยาระบาย 2,500 ลบ.ม./วินาที ทรงตัว" in text


def test_counts_compare_with_yesterday_when_a_ticker_from_about_24_h_ago_exists():
    f = situation.facts(STATIONS, RISKS, RAIN, prev={"over": {"n": 1}})
    assert "ล้นตลิ่งรวม 3 สถานีใน 2 จังหวัด (เมื่อวาน 1)" in situation.rule_text(f)
    assert "เมื่อวาน" not in situation.rule_text(situation.facts(STATIONS, RISKS, RAIN))


def test_numbers_match_with_or_without_thousands_commas_and_no_new_conditions():
    flows = {"C.13": {"q": 2500.0, "q24": 2510.0}}
    f = situation.facts(STATIONS, RISKS, RAIN, flows=flows)
    assert situation.check("เขื่อนเจ้าพระยาระบายน้ำ 2500 ลบ.ม./วินาที ทรงตัว ส่วนฝนหนักสุด 93 มม. ที่ขอนแก่น", f) == []
    assert "speculation" in situation.check("ฝนหนักสุด 93 มม. ที่ขอนแก่น หากฝนตกต่อเนื่องน้ำอาจขึ้นเร็ว", f)


def test_previous_ticker_is_the_one_closest_to_24_h_ago():
    import datetime as dt
    now = dt.datetime(2026, 10, 5, 12, tzinfo=dt.timezone.utc)
    hist = [{"at": (now - dt.timedelta(hours=h)).isoformat(), "over": {"n": h}} for h in (1, 12, 23, 25, 40)]
    assert situation.yesterday(hist, now)["over"]["n"] == 23
    assert situation.yesterday([{"at": (now - dt.timedelta(hours=10)).isoformat(), "over": {"n": 3}}], now) is None


def test_a_province_that_is_also_a_word_is_a_place_in_our_own_text():
    # the rule text says "เช่น พิษณุโลก เลย" (the province Loei); the AI writing "จ.เลย" adds no new place
    risks_ = {"groups": [{"key": "fast_rise", "items": [{"code": "L", "province": "เลย"}]}]}
    f = situation.facts(STATIONS, risks_, RAIN)
    assert "new place" not in situation.check("น้ำขึ้นเร็วที่ จ.เลย ส่วนฝนหนักสุด 93 มม. ที่ขอนแก่น", f)


def test_the_ticker_is_a_list_of_short_items_each_with_its_own_symbol():
    # owner 2026-10-04: "very long text, try to use symbols or anything to see the separation of phrase"
    f = situation.facts(STATIONS, RISKS, RAIN, flows={"C.13": {"q": 2500.0, "q24": 2500.0}})
    items = situation.items(f)
    assert [i["topic"] for i in items][:2] == ["over_rising", "over"]
    assert all(i["icon"] and i["text"] and not i["text"][0] in "🔴🟠🌊🟡🌧☁🔵🏙🏞📊" for i in items)
    assert situation.rule_text(f) == " · ".join(f"{i['icon']} {i['text']}" for i in items)


def test_an_ai_answer_is_read_as_numbered_items_and_keeps_our_symbols():
    f = situation.facts(STATIONS, RISKS, RAIN)
    rule = situation.items(f)
    ai = "1) ตอนนี้น้ำล้นตลิ่งและยังขึ้น 2 สถานีที่พระนครศรีอยุธยา\n3) ขณะที่นนทบุรีกับนครปฐม น้ำยังขึ้นและอาจถึงตลิ่งในอีก 24–48 ชม.\nพูดเกินมาหนึ่งบรรทัด"
    got = situation.parse_items(ai, rule)
    assert [g["icon"] for g in got] == [rule[0]["icon"], rule[2]["icon"]] and got[1]["text"].startswith("ขณะที่")
    assert situation.check_items(got, rule) == []


def test_each_ai_item_may_only_use_the_numbers_and_places_of_its_own_fact():
    f = situation.facts(STATIONS, RISKS, RAIN)
    rule = situation.items(f)
    moved = situation.parse_items("1) น้ำล้นตลิ่งและยังขึ้น 2 สถานีที่ขอนแก่น", rule)  # Khon Kaen belongs to the rain item
    assert "new place" in situation.check_items(moved, rule)[0]
    assert situation.parse_items("ไม่มีเลขข้อเลย", rule) == []


def test_flows_are_two_items_one_per_place():
    flows = {"C.13": {"q": 2500.0, "q24": 2500.0}, "C.2": {"q": 2052.0, "q24": 2150.0}}
    rule = situation.items(situation.facts(STATIONS, RISKS, RAIN, flows=flows))
    topics = [i["topic"] for i in rule]
    assert "flow_C.2" in topics and "flow_C.13" in topics and topics.index("flow_C.2") < topics.index("flow_C.13")


def test_an_item_must_keep_the_trend_words_and_the_reassurance_of_its_fact():
    # Llama 3.3 (2026-10-04) dropped "ทรงตัวหรือลดลง … ยังไม่มีจุดที่น้ำขึ้นจนอาจถึงตลิ่ง" from the Bangkok item: more alarming
    f = situation.facts(STATIONS + BKK, MAY, RAIN)
    rule = situation.items(f)
    k = [i["topic"] for i in rule].index("bkk") + 1
    bad = situation.parse_items(f"{k}) ในกรุงเทพฯ มี 2 จุดที่น้ำล้นตลิ่ง และ 1 จุดที่ใกล้ตลิ่งหรือคลองเต็ม", rule)
    assert any("dropped" in x for x in situation.check_items(bad, rule))
    good = situation.parse_items(f"{k}) กรุงเทพฯ ล้นตลิ่ง 2 จุดแต่ทรงตัวหรือลดลง ยังไม่มีจุดที่น้ำขึ้นจนอาจถึงตลิ่ง และใกล้ตลิ่ง/คลองเต็ม 1 จุด", rule)
    assert situation.check_items(good, rule) == []


def test_a_flow_is_never_called_a_water_level():
    flows = {"C.2": {"q": 2052.0, "q24": 2150.0}}
    rule = situation.items(situation.facts(STATIONS, RISKS, RAIN, flows=flows))
    k = [i["topic"] for i in rule].index("flow_C.2") + 1
    got = situation.parse_items(f"{k}) ระดับน้ำเหนือที่นครสวรรค์อยู่ที่ 2,052 ลบ.ม./วินาที ลดลงจากเมื่อวาน 98", rule)
    assert any("level" in x for x in situation.check_items(got, rule))


def test_an_item_that_fails_falls_back_to_its_own_rule_wording_only(monkeypatch):
    f = situation.facts(STATIONS, RISKS, RAIN)
    rule = situation.items(f)
    k_rain = [i["topic"] for i in rule].index("rain") + 1
    monkeypatch.setattr(situation, "_ai", lambda msgs: f"1) ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา\n{k_rain}) ฝนหนักสุด 93 มม. ที่เชียงใหม่")
    out = situation.compose(f)
    assert out["items"][0]["ai"] is True and out["items"][k_rain - 1] == {**{k: rule[k_rain - 1][k] for k in ("icon", "text")}, "ai": False}
    assert any("new place" in x for x in out["rejected"])


def test_alarm_words_the_fact_does_not_say_are_rejected():
    # Llama 3.3 (2026-10-04) turned "ใกล้ตลิ่ง/คลองเต็ม" into "ใกล้จะล้น"
    f = situation.facts(STATIONS + BKK, MAY, RAIN)
    rule = situation.items(f)
    k = [i["topic"] for i in rule].index("bkk") + 1
    got = situation.parse_items(f"{k}) กรุงเทพฯ ล้นตลิ่ง 2 จุดแต่ทรงตัวหรือลดลง ยังไม่มีจุดที่น้ำขึ้นจนอาจถึงตลิ่ง อีก 1 จุดใกล้จะล้น", rule)
    assert any("alarm" in x for x in situation.check_items(got, rule))


def test_rising_said_in_other_words_counts_as_kept():
    f = situation.facts(STATIONS, MAY, RAIN)
    rule = situation.items(f)
    k = [i["topic"] for i in rule].index("may_reach") + 1
    got = situation.parse_items(f"{k}) สมุทรปราการและเพชรบุรีมีแนวโน้มน้ำสูงขึ้น อาจถึงตลิ่งใน 24–48 ชม. รวม 3 สถานี (ตัวอย่าง)", rule)
    assert situation.check_items(got, rule) == []


def test_examples_stay_examples():
    # 7 gauges in 4 provinces: the 3 named are examples
    f = situation.facts(STATIONS, {"groups": [{"key": "fast_rise", "items": [{"code": c, "province": p} for c, p in
                        (("a", "ตราด"), ("b", "ตราด"), ("c", "เลย"), ("d", "เลย"), ("e", "พิษณุโลก"), ("g", "พิษณุโลก"), ("h", "สตูล"))]}]}, RAIN)
    rule = situation.items(f)
    k = [i["topic"] for i in rule].index("fast_rise") + 1
    assert any("เช่น" in x for x in situation.check_items(situation.parse_items(f"{k}) จ.เลย พิษณุโลก และตราด น้ำขึ้นเร็ว", rule), rule))
    assert situation.check_items(situation.parse_items(f"{k}) น้ำขึ้นเร็ว 7 สถานี เช่น จ.เลย พิษณุโลก ตราด", rule), rule) == []


def test_unchanged_facts_keep_their_checked_wording_and_only_changed_items_go_to_the_ai(monkeypatch):
    # every 30 min most facts are the same: their accepted wording is reused (stable ticker, fewer GLM calls)
    f = situation.facts(STATIONS, RISKS, RAIN)
    rule = situation.items(f)
    calls = []

    def fake(msgs):
        calls.append(msgs[-1]["content"])
        return "1) ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา"

    monkeypatch.setattr(situation, "_ai", fake)
    first = situation.compose(f)
    assert first["cache"] == {rule[0]["text"]: "ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา"}
    again = situation.compose(f, cache=first["cache"])
    assert again["items"][0]["text"] == "ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา" and again["items"][0]["ai"] is True
    assert "1) " not in calls[-1] and "2) " in calls[-1]  # the second call asked only for the facts without wording
    monkeypatch.setattr(situation, "_ai", lambda msgs: (_ for _ in ()).throw(AssertionError("no call expected")))
    full = {i["text"]: i["text"] + " " for i in rule}  # every fact has wording already
    assert situation.compose(f, cache={k: v.strip() for k, v in full.items()})["ai_items"] == len(rule)


def test_the_summary_cards_tone_rules_apply_to_ticker_items():
    # GLM run 4 (2026-10-04): "…และน้ำยังขึ้นอยู่นะ", "สบายใจได้ว่าส่วนใหญ่…ทรงตัวหรือลดลงแล้ว" (a reassurance verdict)
    f = situation.facts(STATIONS, RISKS, RAIN)
    rule = situation.items(f)
    for bad in ("1) ที่พระนครศรีอยุธยามีน้ำล้นตลิ่ง 2 สถานี และน้ำยังขึ้นอยู่นะ",
                "2) ล้นตลิ่ง 3 สถานี สบายใจได้ว่าส่วนใหญ่ทรงตัวหรือลดลงแล้ว"):
        assert any("tone" in x for x in situation.check_items(situation.parse_items(bad, rule), rule)), bad
    ok = situation.parse_items("1) ที่พระนครศรีอยุธยามีน้ำล้นตลิ่ง 2 สถานี และน้ำยังกำลังขึ้นอยู่", rule)
    assert situation.check_items(ok, rule) == []
