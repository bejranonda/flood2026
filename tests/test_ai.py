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
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("GLM_API_KEY", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "glm")
    assert ai._credentials() is None and ai.run([{"role": "user", "content": "x"}]) is None
    monkeypatch.setenv("AI_PROVIDER", "cloudflare")
    assert ai._credentials() is None and ai.run([{"role": "user", "content": "x"}]) is None


def test_glm_credentials_when_set(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "glm")
    monkeypatch.setenv("GLM_API_KEY", "test-key-123")
    monkeypatch.setenv("GLM_MODEL", "glm-4-flash")
    cred = ai._credentials()
    assert cred is not None
    assert cred["provider"] == "glm"
    assert cred["api_key"] == "test-key-123"
    assert cred["model"] == "glm-4-flash"



def test_summary_is_deterministic_template():
    stats = {"focus": {"total": 100, "status": {"critical": 14, "warning": 19, "watch": 28, "normal": 11, "unknown": 28},
                       "trend12": {"rising": 26, "falling": 0}}, "rain_bkk_next24_mm_max": 53.8}
    t = ai.summary_text(stats)
    assert "ล้นตลิ่ง 14" in t and "ใกล้ตลิ่งหรือคลองเต็ม 19" in t and "54 มม." in t and t == ai.summary_text(stats)


def test_glm_asks_for_low_reasoning_so_answers_come_in_seconds():
    # glm-5.3-flash always thinks (API 1210: thinking cannot be disabled); default effort took 9-10 s per call and
    # truncated answers at 500 tokens; reasoning_effort "low" answered in ~1-4 s (probe 2026-10-02)
    p = ai._glm_payload("glm-5.3-flash", [{"role": "user", "content": "x"}], 60)
    assert p["reasoning_effort"] == "low" and p["model"] == "glm-5.3-flash" and p["max_tokens"] >= 60


def test_glm_never_passes_reasoning_off_as_the_answer():
    # a cut-off answer has empty content and only reasoning_content ("The user wants me to ...")
    cut = {"choices": [{"message": {"content": "", "reasoning_content": "The user wants me to explain..."}}]}
    assert ai._glm_text(cut) is None
    assert ai._glm_text({"choices": [{"message": {"content": " ระดับน้ำลดลง "}}]}) == "ระดับน้ำลดลง"
    assert ai._glm_text({"error": {"code": "1211"}}) is None
