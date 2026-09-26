from floodwatch import ai


def test_rules_flag_emergencies_and_spam_without_any_network():
    assert ai.triage_rules("น้ำเข้าบ้าน ยายติดอยู่ชั้นล่าง ช่วยด้วย")["urgent"] is True
    assert ai.triage_rules("ขายครีม line @abc")["category"] == "spam"
    assert ai.triage_rules("ท่อตันหน้าซอย")["urgent"] is False
    assert ai.triage_rules(None)["category"] == "info"


def test_parse_label_accepts_only_known_schema():
    assert ai.parse_label('```json\n{"category": "emergency", "urgent": true}\n```') == {"category": "emergency", "urgent": True}
    assert ai.parse_label('{"category": "flood", "urgent": true}') is None
    assert ai.parse_label('{"category": "info", "urgent": "no"}') is None
    assert ai.parse_label("sorry, I cannot") is None


def test_ai_is_unavailable_without_credentials(monkeypatch):
    monkeypatch.delenv("CF_AI_TOKEN", raising=False)
    assert ai._credentials() is None and ai.run([{"role": "user", "content": "x"}]) is None


def test_summary_is_deterministic_template():
    stats = {"focus": {"total": 100, "status": {"critical": 14, "warning": 19, "watch": 28, "normal": 11, "unknown": 28},
                       "trend12": {"rising": 26, "falling": 0}}, "rain_bkk_next24_mm_max": 53.8}
    t = ai.summary_text(stats)
    assert "ล้นตลิ่ง 14" in t and "ใกล้ตลิ่ง 19" in t and "54 มม." in t and t == ai.summary_text(stats)
