"""Plain words and resident questions over the pin panel (owner 2026-10-02: "ลองให้คนทั่วไปใช้ เขาไม่เข้าใจง่ายๆ … ให้ ai
แปลเป็นความเข้าใจง่ายๆ … be careful about UX"; chose: template summary + AI question chips, rules decide and AI only
rewords; D-068). Then (screenshot at Ko Kret): "AI สรุปดูไม่ได้ข้อมูลอะไรเท่าไหร่ แม้มีตัวเลขด้านล่างเยอะแยะ ควรเล่าหรืออธิบาย
ให้ดีกว่านี้ ว่าสถานีที่ใกล้เคียง แต่อยู่ไกล เป็นยังไง ผมเห็นแล้วว่าน้ำสูงขึ้นหรือเปล่า" — so rule answers carry the story
with its numbers, and AI may add one short checked sentence."""
from floodwatch import explain


def _ch(dir_, level, lo, hi, method="star", basis=None):
    return {"dir": dir_, "level": level, "likely": [lo, hi], "wide": False, "method": method, "basis": basis, "confidence": "low"}


def _out(category="normal", confidence="medium", ch24=None, ch12=None, ch48=None, status="normal", rain=5.0, measured=None,
         reports=0, risk="low", word="คลอง", near=True, far=False, km=2.4, freeboard=0.44, obs=("fall", -14, 48),
         title="ระดับน้ำคลองมีแนวโน้มลดลง", basis=None, over_bma=None, name="ค.แสนแสบ-สนข.บางกะปิ"):
    st = {"code": "G1", "name_th": name, "status": status, "change12": ch12, "change24": ch24, "change48": ch48,
          "freeboard_m": freeboard, "status_basis": basis, "over_bma_critical_m": over_bma,
          "observed24": {"level": obs[0], "change_cm": obs[1], "hours": obs[2]} if obs else None}
    lead = {"code": "G1", "distance_km": km, "far": far, "station": st} if near else None
    return {"word": word, "mode": "bangkok" if word == "คลอง" else "national",
            "area": {"category": category if near else None, "confidence": confidence if near else "none",
                     "n_close": 3 if near and not far else 0, "nearest_km": km if near else None},
            "nearest_canal": None, "nearest_canal_trend": lead, "rain_next24_mm": rain, "rain_measured": measured,
            "evidence": {"traffy_flood_reports_1km_6h": reports}, "forecast": {"risk": risk, "title": title, "desc": "x"}}


FALLING = _ch("falling", "small_fall", -0.04, -0.04, basis="measured_trend")
UNCLEAR24 = {**_ch("steady", "steady", -0.05, 0.10, method="persistence"), "range90": [-0.13, 0.44]}
UNCLEAR48 = {**_ch("steady", "steady", -0.06, 0.22, method="persistence"), "range90": [-0.20, 0.61]}
# the owner's pin at Ko Kret, 2026-10-02 19:40 ICT: the only gauge 6 km away, 33 cm below its bank, rows "? ไม่แน่ชัด"
KO_KRET = dict(category="warning", confidence="very_low", status="warning", far=True, km=6.0, freeboard=0.33,
               ch24=UNCLEAR24, ch48=UNCLEAR48, obs=("mixed", -1, 24), name="คลองอ้อมนนท์ บางใหญ่ (ถนนบางกรวย-ไทรน้อย)",
               title="ไม่มีสถานีวัดน้ำใกล้พอ ยังสรุประดับคลองไม่ได้", risk="info")


def text(lines):
    return " ".join(lines)


def test_a_far_gauge_is_never_described_as_here():
    # v0.18.0 said "คลองแถวนี้น้ำใกล้เต็มตลิ่ง" under the headline "ไม่มีสถานีวัดน้ำใกล้พอ ยังสรุประดับคลองไม่ได้"
    p = explain.plain(_out(**KO_KRET))
    assert "แถวนี้น้ำ" not in p and "ห่าง 6 กม." in p and "ต่ำกว่าตลิ่ง 33 ซม." in p
    assert "เปลี่ยนไม่มาก" in p and "ทรงตัว" not in p  # an unclear row: what is possible, no direction (owner 2026-10-02)


def test_plain_line_for_a_close_gauge_says_the_rows_word_without_rain_amounts():
    p = explain.plain(_out(ch12=FALLING, ch24=FALLING, rain=7.8, reports=2))
    assert "คลองแถวนี้ยังรับน้ำได้" in p and "อีก 24 ชม. น้ำน่าจะลดลงเล็กน้อย" in p
    assert "มม." not in p and " · " not in p


def test_plain_line_without_any_gauge_says_so():
    p = explain.plain(_out(near=False, title="ไม่มีสถานีวัดน้ำใกล้พอ ยังสรุประดับคลองไม่ได้"))
    assert "บอกไม่ได้" in p and "ปกติ" not in p and "ยังรับน้ำได้" not in p


def test_a_longer_horizon_is_never_surer_than_a_shorter_one():
    # the rows' rule (D-060, trendRow): the chain starts at 24 h since the 12 h row is gone (owner 2026-10-04: "remove
    # trend 12 hr"), so a hidden 12 h "?" no longer colours the 24 h words; a proven direction still shows
    unclear = _ch("falling", "fall", -0.19, 0.18, method="persistence")
    steady = _ch("steady", "steady", -0.01, 0.01, method="persistence")
    assert "น้ำน่าจะทรงตัว" in explain.plain(_out(ch12=unclear, ch24=steady))
    assert "น้ำน่าจะทรงตัว" in explain.plain(_out(ch12=steady, ch24=steady))
    assert "น้ำน่าจะลดลงเล็กน้อย" in explain.plain(_out(ch12=unclear, ch24=FALLING))


def test_the_simple_answer_tells_the_story_with_its_numbers():
    lines = explain.answer("simple", _out(**KO_KRET))
    t = text(lines)
    assert "คลองอ้อมนนท์ บางใหญ่" in t and "ห่าง 6 กม." in t and "ไกล" in t  # which gauge, how far
    assert "ต่ำกว่าตลิ่ง 33 ซม." in t  # how full now
    assert "24 ชม. ที่ผ่านมา" in t and "ขึ้นลงสลับกัน" in t  # what it did
    assert "อีก 24 ชม." in t and "ลดลง 5 ซม." in t and "เพิ่มขึ้น 10 ซม." in t  # what the range means
    assert "อีก 48 ชม." in t and "เพิ่มขึ้น 22 ซม." in t
    assert "ครึ่งหนึ่ง" in t  # the rows' range is the middle half of past cases: said honestly
    assert "ฝนเล็กน้อย" in t and "รายงานน้ำที่จุดของคุณ" in t  # rain, and what the resident can do
    assert 4 <= len(lines) <= 8 and all(len(l) < 160 for l in lines)  # + the bank line


def test_a_proven_direction_is_said_with_its_amount():
    t = text(explain.answer("simple", _out(ch12=FALLING, ch24=FALLING, ch48=_ch("falling", "fall", -0.05, -0.05, basis="measured_trend"))))
    assert "อีก 24 ชม.: น่าจะลดลงเล็กน้อย ราว 4 ซม." in t and "อีก 48 ชม.: น่าจะลดลง ราว 5 ซม." in t
    assert "ครึ่งหนึ่ง" not in t


def test_a_bma_gauge_over_its_bma_level_is_said_that_way():
    t = text(explain.answer("simple", _out(basis="bma_thresholds", over_bma=0.12, status="warning", category="warning")))
    assert "เกินเกณฑ์ของ กทม. 12 ซม." in t


def test_outside_bangkok_the_word_is_the_local_water():
    p = explain.plain(_out(ch12=FALLING, ch24=FALLING, word="แม่น้ำ"))
    assert "แม่น้ำแถวนี้" in p and "คลอง" not in p


def test_safety_questions_say_what_the_app_cannot_tell_and_never_give_a_verdict():
    for q in ("home", "car", "travel"):
        t = text(explain.answer(q, _out(ch12=FALLING, ch24=FALLING)))
        assert "ไม่ได้" in t or "ไม่รู้" in t, q
        for bad in ("ปลอดภัย", "ไม่ท่วม", "ได้ครับ", "ไปได้", "ปกติ", "ไม่ต้อง"):
            assert bad not in t, (q, bad)


def test_advice_gets_firmer_only_on_the_panels_own_warning_signals():
    calm = text(explain.answer("car", _out(ch12=FALLING, ch24=FALLING)))
    high = text(explain.answer("car", _out(category="critical", status="critical", risk="high", reports=4)))
    assert "ควรย้ายไปที่สูงไว้ก่อน" in high and "ควรย้ายไปที่สูงไว้ก่อน" not in calm
    assert "ควรทำตอนนี้" in text(explain.answer("prepare", _out(risk="high", reports=4)))
    assert "เตรียมไว้ก่อนได้" in text(explain.answer("prepare", _out()))


def test_the_numbers_answer_explains_this_panels_own_row():
    t = text(explain.answer("numbers", _out(**KO_KRET)))
    assert "−5 ถึง +10 ซม." in t and "ลดลง 5 ซม." in t and "เพิ่มขึ้น 10 ซม." in t and "ไม่ใช่ที่บ้าน" in t


def test_every_question_has_a_rule_answer_in_every_situation():
    for q in explain.QUESTIONS:
        for o in (_out(), _out(near=False), _out(**KO_KRET), _out(ch12=FALLING, ch24=FALLING, measured={"rain_24h": 60.0}),
                  _out(word="แม่น้ำ", reports=5, risk="high"), _out(freeboard=None, obs=None)):
            lines = explain.answer(q, o)
            assert lines and all(l and "None" not in l for l in lines), (q, lines)


def test_the_checker_rejects_what_the_probe_produced():
    rule = text(explain.answer("travel", _out(ch12=FALLING, ch24=FALLING)))
    # the real probe answer at Phaya Thai, 2026-10-02
    assert explain.check("ได้ครับ ข้อมูลระบุว่าแนวโน้มน้ำอีก 24 ชม. ทรงตัว และไม่มีรายงานน้ำท่วมถนนบริเวณใกล้เคียง", rule)
    assert explain.check("น้ำจะเพิ่มขึ้น 15 ซม.", rule)  # a new number and a direction the rule does not say
    assert explain.check("The water is falling.", rule)
    assert explain.check("ก" * 200, rule)  # a gist is short


def test_the_v018_ko_kret_ai_text_is_rejected_and_a_faithful_one_passes():
    # the AI text on the owner's screenshot called a gauge 6 km away "แถวนี้" and dropped the rule's "cannot tell"
    rule = text(explain.answer("simple", _out(**KO_KRET)))
    assert explain.check("สรุปง่าย ๆ นะคะ: น้ำในคลองแถวนี้ตอนนี้ใกล้จะเต็มตลิ่งแล้ว ถ้าฝนตกหนักขึ้น ควรกลับมาดูข้อมูลอีกครั้งนะคะ", rule)
    ok = "สถานีที่ใกล้ที่สุดอยู่ไกลถึง 6 กม. น้ำที่นั่นยังต่ำกว่าตลิ่ง 33 ซม. และยังบอกไม่ได้ว่าจะขึ้นหรือลง"
    assert explain.check(ok, rule) == []


def test_without_ai_there_is_no_gist(monkeypatch):
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: None)
    explain._cache.clear()
    assert explain.gist("home", explain.answer("home", _out())) is None


def test_a_gist_that_fails_the_check_is_never_shown(monkeypatch):
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: "ไม่ต้องกังวลครับ บ้านคุณไม่ท่วมแน่นอน")
    explain._cache.clear()
    assert explain.gist("home", explain.answer("home", _out())) is None


def test_a_good_gist_is_shown_and_cached(monkeypatch):
    lines = explain.answer("simple", _out(**KO_KRET))
    good = "สถานีที่ใกล้ที่สุดอยู่ไกลถึง 6 กม. น้ำที่นั่นยังต่ำกว่าตลิ่ง 33 ซม. และยังบอกไม่ได้ว่าจะขึ้นหรือลง"
    calls = []
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: calls.append(1) or good)
    explain._cache.clear()
    assert explain.gist("simple", lines) == good and explain.gist("simple", lines) == good
    assert len(calls) == 1  # same facts → same gist, one call


def test_the_daily_cap_and_the_off_switch(monkeypatch):
    lines = explain.answer("simple", _out(**KO_KRET))
    good = "สถานีที่ใกล้ที่สุดอยู่ไกลถึง 6 กม. และยังบอกไม่ได้ว่าน้ำจะขึ้นหรือลง"
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: good)
    explain._cache.clear()
    monkeypatch.setenv("AI_EXPLAIN", "1")
    assert explain.gist("simple", lines) == good
    explain._cache.clear()
    monkeypatch.setenv("AI_EXPLAIN", "0")
    assert explain.gist("simple", lines) is None
    explain._cache.clear()
    monkeypatch.setenv("AI_EXPLAIN", "1")
    monkeypatch.setattr(explain, "_calls_today", lambda: explain.DAILY_CAP)
    assert explain.gist("simple", lines) is None


LAM_NAM_KAM = ["📍 ดูจากสถานี: ลำน้ำก่ำ ห่าง 1 กม.", "🌊 ตอนนี้: น้ำที่นั่นต่ำกว่าตลิ่ง 545 ซม. (ยังรับน้ำได้)",
               "↕️ 24 ชม. ที่ผ่านมา: เพิ่มขึ้นมาก 49 ซม.", "🔮 อีก 24 ชม.: น่าจะเพิ่มขึ้นเล็กน้อย ราว 3 ซม.",
               "🌧️ อีก 24 ชม. คาดว่ามีฝนเล็กน้อย", "👉 ถ้าฝนตกหนักหรือมีคนแจ้งน้ำท่วมถนนเพิ่ม ให้เตรียมยกของขึ้นที่สูง"]


def test_a_past_change_told_as_the_future_is_rejected():
    # validation 2026-10-02: the past line "เพิ่มขึ้นมาก 49 ซม." became "…นี้น้ำจะขึ้นค่อนข้างมาก" (a strong future rise)
    rule = "\n".join(LAM_NAM_KAM)
    bad = "ตอนนี้น้ำที่ลำน้ำก่ำยังต่ำกว่าตลิ่งอยู่ แต่ช่วงหนึ่งวันสองวันนี้น้ำจะขึ้นค่อนข้างมาก ฝนคาดว่าจะตกเล็กน้อย"
    assert explain.check(bad, rule)
    ok = "ลำน้ำก่ำยังต่ำกว่าตลิ่งมาก 24 ชม. ที่ผ่านมาน้ำเพิ่มขึ้นมาก และอีก 24 ชม. น่าจะเพิ่มขึ้นเล็กน้อย"  # one neutral voice: no ค่ะ/ครับ (2026-10-04)
    assert explain.check(ok, rule) == []


def test_polite_particles_are_not_verdicts():
    # validation 2026-10-02: these were blocked as "ได้ค่ะ"/"แน่นอน" verdicts though they say nothing of the kind
    rule = text(explain.answer("simple", _out(**KO_KRET)))
    for t in ("น้ำที่นั่นยังต่ำกว่าตลิ่ง 33 ซม. แต่ยังบอกไม่ได้ค่ะว่าจะขึ้นหรือลง",
              "สถานีอยู่ไกล 6 กม. ยังบอกไม่ได้แน่นอนว่าจะขึ้นหรือลง"):
        assert not [i for i in explain.check(t, rule) if i.startswith("verdict")], t
    assert [i for i in explain.check("ได้ค่ะ ไปได้เลย", rule) if i.startswith("verdict")]


def test_the_numbers_answer_may_repeat_its_own_strong_word():
    # validation 2026-10-02: "น่าจะลดลงมากราว 75–112 เซนติเมตร" was blocked though the 📏 line says exactly that
    rule = "\n".join(explain.answer("numbers", _out(ch24=_ch("falling", "strong_fall", -1.12, -0.75), ch12=_ch("falling", "strong_fall", -0.6, -0.4))))
    assert "ลดลงมาก" in rule
    assert explain.check("อีกหนึ่งวัน น้ำที่สถานีน่าจะลดลงมากราว 75–112 ซม. วัดที่สถานี ไม่ใช่ที่บ้าน", rule) == []


def test_an_unclear_row_with_a_one_sided_range_is_not_called_up_or_down():
    # validation 2026-10-02, คลองกลาง: "? ไม่แน่ชัด" with +1 to +64 cm was told "ยังบอกไม่ได้ว่าจะขึ้นหรือลง … เพิ่มขึ้น 1–64 ซม."
    up = _ch("rising", "rise", 0.01, 0.64, method="persistence")
    t = text(explain.answer("simple", _out(ch12=up, ch24=up)))
    assert "อีก 24 ชม.: ยังบอกไม่ได้แน่ชัด" in t and "เพิ่มขึ้น 1–64 ซม." in t and "จะขึ้นหรือลง" not in t


def test_the_plain_line_says_the_horizon_once():
    p = explain.plain(_out(ch12=FALLING, ch24=FALLING, rain=5.0))
    assert p.count("อีก 24 ชม.") == 1 and "ฝนเล็กน้อย" in p


def test_honest_refusals_are_not_flagged():
    # validation 2026-10-02: blocked as "dropped cannot tell" / "verdict จะท่วม" though they say exactly that
    rule = text(explain.answer("travel", _out(ch12=FALLING, ch24=FALLING)))
    assert explain.check("แอปไม่สามารถบอกได้ว่าเดินทางได้หรือไม่ ก่อนออกเดินทางลองดูจุดสีม่วงบนแผนที่อีกครั้ง", rule) == []
    rule = text(explain.answer("home", _out(ch12=FALLING, ch24=FALLING)))
    assert explain.check("ส่วนจะท่วมบ้านหรือไม่ แอปบอกไม่ได้เพราะวัดที่คลอง", rule) == []
    assert explain.check("บ้านคุณจะท่วมแน่", rule)


def test_rain_that_fell_and_rain_ahead_read_as_one_short_story():
    p = explain.plain(_out(ch12=FALLING, ch24=FALLING, measured={"rain_24h": 11.0}, rain=7.8, reports=2))
    assert "24 ชม. ที่ผ่านมามีฝนปานกลาง ต่อไปคาดว่ามีฝนเล็กน้อย" in p and p.count(" และ") <= 2


# --- the story card (owner 2026-10-02, v0.18.3 screenshot vs a weather app's AI card: "I got complicated info …
# looks at second one to get feeling, they try to explain easily") ----------------------------------------------------

def test_the_story_is_a_few_easy_sentences_with_at_most_a_couple_of_numbers():
    s = explain.narrative("simple", _out(**KO_KRET))
    assert "ไกล" in s and "6 กม." in s and "ต่ำกว่าตลิ่ง" in s and "เปลี่ยนไม่มาก" in s and "ฝนเล็กน้อย" in s
    assert "ครึ่งหนึ่ง" not in s and "ถึงเพิ่มขึ้น" not in s and "−" not in s  # no ranges, no signed numbers
    assert len(s) <= 320 and len(set(explain._NUM.findall(s))) <= 5
    assert "ดูน้ำใน" in s  # what to do


def test_the_story_says_up_or_down_plainly_when_the_rows_do():
    s = explain.narrative("simple", _out(ch12=FALLING, ch24=FALLING, reports=2, rain=7.8))
    assert "แนวโน้มลดลง" in s and "แจ้งน้ำท่วมถนน" in s and "แถวนี้" in s


def test_every_question_has_a_story_and_the_numbers_stay_in_the_lines():
    for q in explain.QUESTIONS:
        for o in (_out(), _out(near=False), _out(**KO_KRET), _out(word="แม่น้ำ", reports=5, risk="high")):
            s = explain.narrative(q, o)
            assert s and len(s) <= 320 and "ครึ่งหนึ่งของครั้ง" not in s, (q, s)
            assert explain.check(s, s + "\n" + "\n".join(explain.answer(q, o))) == [], (q, s)  # the rule passes its own check


def test_a_good_ai_story_is_used_and_a_bad_one_falls_back(monkeypatch):
    out = _out(**KO_KRET)
    story, lines = explain.narrative("simple", out), explain.answer("simple", out)
    good = "แถวนี้ยังไม่มีสถานีวัดน้ำใกล้ ๆ สถานีที่ใกล้ที่สุดอยู่ไกลราว 6 กม. น้ำที่นั่นยังต่ำกว่าตลิ่ง และยังบอกไม่ได้ว่าจะขึ้นหรือลง"
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: good)
    explain._cache.clear()
    assert explain.gist("simple", lines, story) == good
    monkeypatch.setattr(explain.ai, "run", lambda *a, **k: "น้ำแถวนี้ไม่ท่วมแน่นอน ไม่ต้องกังวล")
    explain._cache.clear()
    assert explain.gist("simple", lines, story) is None


def test_the_story_says_the_horizon_once_and_no_gauge_is_not_far():
    s = explain.narrative("simple", _out(ch12=FALLING, ch24=FALLING, rain=7.8))
    assert s.count("ข้างหน้า") == 1 and "และคาดว่ามีฝนเล็กน้อย" in s
    rule = explain.narrative("simple", _out(near=False)) + "\n" + "\n".join(explain.answer("simple", _out(near=False)))
    assert explain.check("แถวนี้ยังไม่มีสถานีวัดน้ำในระยะ 8 กม. จึงยังบอกไม่ได้ว่าน้ำในคลองเป็นอย่างไร", rule) == []



# --- unclear rows say what is possible (owner 2026-10-02: "we can't say just no trend in everytime, user expected to
# hear what can be possible even in the far station" → chose: possible change + bank risk, no direction claimed) -----

def test_an_unclear_row_says_the_size_of_the_change_and_the_bank_risk():
    s = explain.narrative("simple", _out(**KO_KRET))
    assert "น่าจะเปลี่ยนไม่มาก" in s and "อาจลดลงราว 5 ซม. หรือเพิ่มขึ้นราว 10 ซม." in s
    assert "อาจถึงตลิ่งได้" in s and "33 ซม." in s  # 90 % range reaches +61 cm, the bank is 33 cm away
    assert "บอกไม่ได้ว่าจะขึ้นหรือลง" not in s and "น่าจะลดลง" not in s and "น่าจะเพิ่มขึ้น" not in s  # no direction claimed
    p = explain.plain(_out(**KO_KRET))
    assert "เปลี่ยนไม่มาก" in p and "อาจถึงตลิ่งได้" in p
    lines = text(explain.answer("simple", _out(**KO_KRET)))
    assert "🏞️ ตลิ่ง: เหลืออีกราว 33 ซม." in lines and "61 ซม." in lines and "9 ใน 10" in lines


def test_a_wide_unclear_row_far_below_the_bank_is_said_that_way():
    wide = {**_ch("steady", "steady", -0.19, 0.18, method="persistence"), "range90": [-0.35, 0.40]}
    s = explain.narrative("simple", _out(ch12=wide, ch24=wide, freeboard=1.61, far=True, confidence="very_low", km=7.3))
    assert "ยังไม่ชัดว่าน้ำจะขึ้นหรือลง" in s and "อาจลดลงราว 19 ซม. หรือเพิ่มขึ้นราว 18 ซม." in s
    assert "ยังไม่น่าจะถึงตลิ่ง" in s and "อาจถึงตลิ่งได้" not in s


def test_a_one_sided_unclear_row_says_it_may_rise_but_is_not_certain():
    up = {**_ch("rising", "rise", 0.01, 0.64, method="persistence"), "range90": [-0.1, 0.9]}
    s = explain.narrative("simple", _out(ch12=up, ch24=up, freeboard=0.5))
    assert "อาจเพิ่มขึ้นราว 1–64 ซม. แต่ยังไม่แน่ชัด" in s and "อาจถึงตลิ่งได้" in s


def test_a_proven_fall_far_from_the_bank_needs_no_bank_sentence():
    s = explain.narrative("simple", _out(ch12=FALLING, ch24={**FALLING, "range90": [-0.2, 0.05]}))
    assert "มีแนวโน้มลดลงเล็กน้อย" in s and "ตลิ่งได้" not in s


def test_ai_may_retell_the_possible_change_without_inventing_a_direction():
    out = _out(**KO_KRET)
    _, rule = explain.prompt("simple", explain.answer("simple", out), explain.narrative("simple", out))
    ok = "สถานีที่ใกล้ที่สุดอยู่ไกลราว 6 กม. น้ำที่นั่นน่าจะเปลี่ยนไม่มาก แต่ถ้าน้ำขึ้นมาก อาจถึงตลิ่งได้ เพราะเหลืออีกราว 33 ซม."
    assert explain.check(ok, rule) == []


def test_a_close_gauge_among_disagreeing_ones_is_not_called_far():
    # validation 2026-10-02: "สถานีวัดน้ำที่ใกล้ที่สุดอยู่ไกลราว 1.3 กม." — the area gauges disagreed, the gauge was not far
    o = _out(confidence="very_low", far=False, km=1.3, ch12=FALLING, ch24=FALLING)
    s = explain.narrative("simple", o)
    assert "ไกลราว 1.3" not in s and "ให้ผลต่างกัน" in s and "1.3 กม." in s
    assert "ซึ่งไกล" not in explain.answer("simple", o)[0] and "ให้ผลต่างกัน" in explain.answer("simple", o)[0]


def test_bank_certainty_and_harmless_phrases():
    rule = "\n".join(explain.prompt("simple", explain.answer("simple", _out(**KO_KRET)), explain.narrative("simple", _out(**KO_KRET)))[1:])
    assert [i for i in explain.check("วันข้างหน้าน่าจะเปลี่ยนไม่มาก ไม่ขึ้นถึงตลิ่ง", rule) if i.startswith("verdict")]
    prep = "\n".join(explain.answer("prepare", _out()))
    assert not [i for i in explain.check("เก็บเอกสารสำคัญและยาไว้ในที่สูง จะได้ไม่ต้องตกใจทีหลัง", prep) if i.startswith("verdict")]
    trav = "\n".join(explain.answer("travel", _out()))
    assert not [i for i in explain.check("แอปไม่รู้สภาพถนนทุกเส้น จะเดินทางได้ไหมให้ดูจุดสีม่วงบนแผนที่อีกครั้ง", trav) if i.startswith("verdict")]


def test_hedged_bank_phrasing_is_accepted_when_rule_allows():
    safe_rule = "บทสรุป: ถ้าเป็นแบบที่ผ่านมา น้ำยังไม่น่าจะถึงตลิ่ง และคาดว่ามีฝนเล็กน้อย\n🏞️ ตลิ่ง: เหลืออีกราว 58 ซม."
    assert not [i for i in explain.check("ถ้าเป็นแบบเดิม น้ำน่าจะยังไม่ถึงตลิ่ง", safe_rule) if i.startswith("verdict")]
    assert not [i for i in explain.check("น้ำยังไม่น่าจะถึงตลิ่ง", safe_rule) if i.startswith("verdict")]
    assert [i for i in explain.check("น้ำไม่ถึงตลิ่งแน่นอน", safe_rule) if i.startswith("verdict")]
    assert [i for i in explain.check("น้ำไม่ขึ้นถึงตลิ่ง", safe_rule) if i.startswith("verdict")]


# --- satellite (Q45 yes, D-071): told as seen, in the past, with its distance; silent when nothing was seen ----------
SAT = {"nearest_m": 300, "cells": 4, "area_rai": 120, "img_from": "2026-09-27", "img_to": "2026-09-29", "source": "GISTDA"}




def test_retellings_open_with_the_water_in_one_neutral_voice_without_good_news_framing():
    # live sample of 12 pins (2026-10-04): "ข่าวดีคือ …", "เดี๋ยวเล่าให้ฟังนะคะ" openings and mixed นะคะ / นะ voices passed
    rule = "บทสรุป: น้ำยังต่ำกว่าตลิ่ง ช่วงที่ผ่านมาน้ำลดลง\n🔮 อีก 24 ชม.: ลดลง"
    assert "tone" in " ".join(explain.check("ข่าวดีคือ น้ำยังต่ำกว่าตลิ่ง ช่วงที่ผ่านมาน้ำลดลง", rule))
    assert "tone" in " ".join(explain.check("น้ำยังต่ำกว่าตลิ่ง ช่วงที่ผ่านมาน้ำลดลงนะคะ", rule))
    assert "filler" in " ".join(explain.check("เดี๋ยวเล่าให้ฟังนะ น้ำยังต่ำกว่าตลิ่ง ช่วงที่ผ่านมาน้ำลดลง", rule))
    assert explain.check("น้ำยังต่ำกว่าตลิ่ง ช่วงที่ผ่านมาน้ำลดลงนะ", rule) == []
    assert "เริ่มสูง หมายถึง" in explain.SYSTEM and "สถานีวัดน้ำ" in explain.SYSTEM


def test_a_leaning_row_is_told_as_a_likely_direction_without_an_amount():
    # owner 2026-10-04: "Lean the rows by the trend": the panel shows "↗ น่าจะเพิ่มขึ้น"; the words say the same, from the
    # measured trend, and still say the amount is not certain
    lean = {**_ch("steady", "steady", -0.05, 0.12, method="persistence"), "lean": "up", "lean_rec": {"n": 120, "hit": 0.64}}
    out = _out(ch24=lean, obs=("rise", 8, 24))
    p = explain.plain(out)
    assert "น่าจะเพิ่มขึ้น" in p and "ไม่แน่ชัด" in p
    lines = " ".join(explain.answer("simple", out))
    assert "น่าจะเพิ่มขึ้นตามแนวโน้มที่วัดได้" in lines and "6 ใน 10" in lines
