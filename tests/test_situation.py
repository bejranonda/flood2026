"""The national situation ticker in the top bar (owner 2026-10-04: "concentrate the all information of Thailand got from
the app into a single running scrolling text … periodically update, like every 30 minutes … let AI prepare it into
simple, attractive and lovely Thai language"; D-089). Rules gather every fact; the AI may only retell them."""
from floodwatch import situation


def st(code, status, prov, group=None, stale=False):
    return {"code": code, "status": status, "province": prov, "stale": stale, "trend": {"group": group} if group else None}


STATIONS = [st("A", "critical", "พระนครศรีอยุธยา", "rising"), st("B", "critical", "พระนครศรีอยุธยา", "rising"),
            st("C", "critical", "ปราจีนบุรี", "flat_or_falling"), st("D", "warning", "นนทบุรี"), st("E", "normal", "ตรัง"),
            st("F", "critical", "ตาก", "rising", stale=True)]
RISKS = {"groups": [{"key": "may_reach", "items": [{"code": "X", "province": "นนทบุรี"}, {"code": "Y", "province": "นครปฐม"}]},
                    {"key": "upstream", "items": [{"code": "Z", "province": "สระแก้ว"}]}]}
RAIN = {"all": {"forecast_mm24": 52.0, "forecast_where": "น่าน",
                "measured": {"name_th": "บ้านโนนเขวา", "province": "ขอนแก่น", "rain_24h": 93.0}}}


def test_facts_count_fresh_gauges_and_name_the_places():
    f = situation.facts(STATIONS, RISKS, RAIN)
    assert f["over"] == {"n": 3, "rising": 2, "provinces": 2, "rising_top": [["พระนครศรีอยุธยา", 2]]}
    assert f["near"] == 1 and f["below"] == 1
    assert f["may_reach"] == {"n": 2, "top": ["นนทบุรี", "นครปฐม"]} and f["upstream"] == {"n": 1, "top": ["สระแก้ว"]}
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
    monkeypatch.setattr(situation, "_ai", lambda msgs: "ตอนนี้มีน้ำล้นตลิ่งและยังขึ้น 2 แห่งที่อยุธยา")
    out = situation.compose(f)
    assert out["ai"] is True and out["text"].startswith("ตอนนี้") and out["rule"] == situation.rule_text(f) and out["rejected"] == []
    monkeypatch.setattr(situation, "_ai", lambda msgs: "พื้นที่อื่นปลอดภัยทั้งหมด")
    out = situation.compose(f)
    assert out["ai"] is False and out["text"] == situation.rule_text(f) and len(out["rejected"]) == 2  # tried twice


def test_the_ticker_is_rewritten_every_30_min_in_the_collector_loop():
    from floodwatch import worker
    assert dict(worker.TASKS)["situation"] == 1800
