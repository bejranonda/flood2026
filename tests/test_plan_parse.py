"""Type a plan in Thai (owner 2026-10-06; D-110): rules first, GLM only when they cannot read it; 7 numbers that only fill
the boxes. Values above 200 are refused, never clipped."""
import pytest

from floodwatch import ai, plan_parse as pp

CASES = [
    ("ระบาย 15 สามวันแล้วลดเหลือ 10", [15, 15, 15, 10, 10, 10, 10]),
    ("15 ล้าน ลบ.ม./วัน 3 วันแรก แล้วเพิ่มเป็น 20", [15, 15, 15, 20, 20, 20, 20]),
    ("คงเดิม", [10.63] * 7),
    ("ระบายเท่าวันนี้", [10.63] * 7),
    ("ทยอยลดจาก 20 เป็น 8", [20, 18, 16, 14, 12, 10, 8]),
    ("ทยอยเพิ่ม 10 ถึง 16", [10, 11, 12, 13, 14, 15, 16]),
    ("12", [12] * 7),
    ("ระบาย 18 ทุกวัน", [18] * 7),
    ("10 12 14 16 18 20 22", [10, 12, 14, 16, 18, 20, 22]),
    ("๑๕ สองวันแรก แล้วเหลือ ๘", [15, 15, 8, 8, 8, 8, 8]),
    ("21.5 คงที่ 7 วัน", [21.5] * 7),
    ("10,12,14,16,18,20,22", [10, 12, 14, 16, 18, 20, 22]),
    ("ทยอยลดจาก 20 เป็น 8 ใน 3 วัน", [20, 14, 8, 8, 8, 8, 8]),
    ("ทยอยเพิ่มจาก 10 เป็น 16 ภายใน 4 วัน", [10, 12, 14, 16, 16, 16, 16]),
    ("ทยอยลดจาก 20 เป็น 8 ภายใน 3 วันถัดไป", [20, 14, 8, 8, 8, 8, 8]),
    # a change word with its target word still reads (final review, D-110: only "by or to?" is refused)
    ("ระบาย 15 3 วัน แล้วลดลงเหลือ 5", [15, 15, 15, 5, 5, 5, 5]),
    ("ระบาย 15 3 วัน แล้วเพิ่มขึ้นเป็น 20", [15, 15, 15, 20, 20, 20, 20]),
    ("ระบาย 15 ล้าน 3 วัน แล้ว 10 ล้าน ลบ.ม./วัน", [15, 15, 15, 10, 10, 10, 10]),
    ("ระบาย 12.5 2 วันแรก แล้ว 8", [12.5, 12.5, 8, 8, 8, 8, 8]),
]


@pytest.mark.parametrize("text,want", CASES)
def test_the_rules_read_common_thai_phrasings(text, want):
    assert pp.parse_rules(text, today=10.63) == [float(x) for x in want]


@pytest.mark.parametrize("text", ["ระบายเยอะ ๆ", "300", "10 12 14", "", "   ", "ทยอยลดจาก 20 เป็น 15 แล้วเหลือ 8", "ขึ้นเป็น 15", "ลงเหลือ 8"])
def test_the_rules_refuse_what_they_cannot_read_and_values_above_200(text):
    assert pp.parse_rules(text, today=10.63) is None


# final review (D-110): each of these was read silently as a wrong plan (e.g. "ระบาย 15 วันแรก แล้ว 10" → 1, 1, 1, 1, 1,
# 10, 10; "ทยอยลดจาก 8 เป็น 20" → a rising ramp; "ระบาย 20 ลบ.ม./วินาที" → 20 ล้าน ลบ.ม./วัน for 7 days); now refused
MISREADS = [
    "ระบาย 15 วันแรก แล้ว 10", "ระบาย 12 วันแรก แล้ว 8",                              # the amount split into "1" + "5 วัน"
    "ระบาย 15 3 วัน แล้ว 10 2 วัน แล้ว 5", "ระบาย 10 สองวัน 12 สามวัน 14 สองวัน",     # a third step dropped
    "ระบาย 10 2 วัน แล้วเพิ่มขึ้น 5", "ทยอยลดจาก 8 เป็น 20",                          # the direction word contradicts
    "ระบาย 15 3 วัน แล้วลดลง 5",                                                     # down by 5 or down to 5?
    "ระบาย 20 ลบ.ม./วินาที", "ระบาย 143 cms",                                       # per second, not per day
    "ระบาย 250",
    # the same holes, other spellings
    "ระบาย 15 3 วัน แล้วลด 5", "ระบาย 10 2 วัน แล้วเพิ่มเป็น 5", "ทยอยเพิ่มจาก 20 เป็น 10", "ทยอยลด 10 12 14 16 18 20 22",
    "ระบาย 20 ลบ.ม./วิ", "ระบาย 20 ลบ.ม.ต่อวิ", "ระบาย 20 m3/s", "ระบาย 20 m³/s", "143cms", "ระบาย 1,000",
    "ระบาย 25 2 วัน แล้วทยอยลดจาก 20 เป็น 8", "ระบาย 20 แล้วลดเหลือ 15 3 วัน แล้ว 10",  # a number the rule cannot place
    "ระบาย 15 สามวัน", "คงเดิม 3 วัน", "ระบาย 15 3 วันแรก แล้ว 10 วัน",                 # says nothing about the other days
]


@pytest.mark.parametrize("text", MISREADS)
def test_the_rules_refuse_phrasings_they_used_to_misread(text):
    assert pp.parse_rules(text, today=10.63) is None


@pytest.mark.parametrize("text", ["ระบาย 250", "ระบาย 20 ลบ.ม./วินาที", "ระบาย 143 cms", "ระบาย 1,000"])
def test_values_above_200_and_per_second_units_never_reach_the_ai(monkeypatch, text):
    # final review (D-110): the AI could turn "250" into 25 or 20 m³/s into 20 ล้าน ลบ.ม./วัน — it is never asked
    monkeypatch.setenv("AI_EXPLAIN", "1")
    monkeypatch.setattr(ai, "run", lambda *a, **k: pytest.fail("AI called for a refused text"))
    assert pp.parse(text, today=10.63) is None
    assert pp.parse_ai(text, today=10.63) is None


def test_a_word_that_merely_contains_the_per_second_letters_is_not_a_unit():
    assert not pp._blocked("ระบาย 15 ตามวิธีเดิม") and not pp._blocked("10,12,14,16,18,20,22")
    assert pp.parse_rules("ระบาย 15 ตามวิธีเดิม", today=10.63) == [15.0] * 7


def test_ai_reads_the_rest_and_its_answer_is_only_seven_valid_numbers(monkeypatch):
    monkeypatch.setenv("AI_EXPLAIN", "1")
    monkeypatch.setattr(ai, "run", lambda *a, **k: 'แผน: {"release": [12, 12, 14, 14, 16, 16, 16]}')
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่มทีละสองทุกสองวัน", today=10.63) == ([12.0, 12.0, 14.0, 14.0, 16.0, 16.0, 16.0], "ai")
    monkeypatch.setattr(ai, "run", lambda *a, **k: '{"release": [12, 12, 14]}')
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่ม", today=10.63) is None
    monkeypatch.setattr(ai, "run", lambda *a, **k: '{"release": [500, 12, 14, 14, 16, 16, 16]}')
    assert pp.parse("เริ่ม 500 แล้วค่อย ๆ ลด", today=10.63) is None
    monkeypatch.setattr(ai, "run", lambda *a, **k: "ขอโทษ อ่านไม่ได้")
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่ม", today=10.63) is None
    assert pp.parse("ระบาย 15 สามวันแล้วลดเหลือ 10", today=10.63)[1] == "rules"


def test_without_ai_only_the_rules_read(monkeypatch):
    monkeypatch.setenv("AI_EXPLAIN", "0")
    monkeypatch.setattr(ai, "run", lambda *a, **k: pytest.fail("AI called while off"))
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่ม", today=10.63) is None
