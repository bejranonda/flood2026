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
]


@pytest.mark.parametrize("text,want", CASES)
def test_the_rules_read_common_thai_phrasings(text, want):
    assert pp.parse_rules(text, today=10.63) == [float(x) for x in want]


@pytest.mark.parametrize("text", ["ระบายเยอะ ๆ", "300", "10 12 14", "", "   "])
def test_the_rules_refuse_what_they_cannot_read_and_values_above_200(text):
    assert pp.parse_rules(text, today=10.63) is None


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
