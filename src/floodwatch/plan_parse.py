"""Type a plan in Thai (owner 2026-10-06; D-110): seven daily releases (ล้าน ลบ.ม./วัน) from text such as
"ระบาย 15 สามวันแล้วลดเหลือ 10". Rules first; GLM only when the rules cannot read it, and its answer is only 7 numbers that
fill the boxes for the engineer to check — nothing is computed until they press คำนวณ (D-022: AI never decides). Values
above MAX are refused, never clipped. The text is never logged or stored."""
from __future__ import annotations

import json
import os
import re

DAYS = 7
MAX = 200.0  # the custom plan's own bound (the API accepts 0–200)
TH_NUM = {"หนึ่ง": 1, "สอง": 2, "สาม": 3, "สี่": 4, "ห้า": 5, "หก": 6, "เจ็ด": 7}
_TH_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
N = r"(\d+(?:\.\d+)?)"
UNIT = r"(?:ล้าน\s*(?:ลบ\.?\s*ม\.?)?\s*(?:/\s*วัน)?\s*)?"
CHANGE = re.compile(r"เพิ่ม|ลด|แล้ว|ทีละ|ค่อย|จากนั้น|ต่อด้วย")  # words that say the release changes over the week


def _norm(text: str) -> str:
    t = (text or "").translate(_TH_DIGITS).replace(",", " ")
    for word, n in TH_NUM.items():
        t = re.sub(word + r"(?=\s*วัน)", str(n), t)
    return re.sub(r"\s+", " ", t).strip()


def _ok(vals) -> list[float] | None:
    if vals is None or len(vals) != DAYS or any(v is None or not (0 <= v <= MAX) for v in vals):
        return None
    return [round(float(v), 2) for v in vals]


def parse_rules(text: str, today: float) -> list[float] | None:
    """Day by day (7 numbers), a ramp ("ทยอย… จาก A เป็น B"), two steps ("A N วัน(แรก) แล้ว… B"), a constant (one number),
    or today's release ("คงเดิม", "เท่าวันนี้"); else None."""
    t = _norm(text)
    if not t:
        return None
    m = re.search(r"ทยอย\S*\s*(?:จาก\s*)?" + N + r"\s*" + UNIT + r"(?:เป็น|ถึง|ไป|→|-)\s*" + N, t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return _ok([a + (b - a) * k / (DAYS - 1) for k in range(DAYS)])
    m = re.search(N + r"\s*" + UNIT + r"(\d)\s*วัน(?:แรก)?\s*(?:แล้ว|จากนั้น|ต่อด้วย)?\s*(?:ค่อย)?\s*(?:ลด|เพิ่ม)?\s*(?:ลง|ขึ้น)?\s*"
                  r"(?:เหลือ|เป็น|ไป)?\s*" + N, t)
    if m:
        a, n, b = float(m.group(1)), int(m.group(2)), float(m.group(3))
        if 1 <= n < DAYS:
            return _ok([a] * n + [b] * (DAYS - n))
    nums = [float(x) for x in re.findall(N, re.sub(r"\d+\s*วัน", " ", t))]
    if len(nums) == DAYS:
        return _ok(nums)
    if len(nums) == 1 and not CHANGE.search(t):  # "เริ่ม 12 แล้วค่อย ๆ เพิ่ม…" is not a constant 12: leave it to the AI
        return _ok([nums[0]] * DAYS)
    if not nums and re.search(r"คงเดิม|เท่าเดิม|เท่าวันนี้", t):
        return _ok([round(today, 2)] * DAYS)
    return None


SYSTEM = ("แปลงแผนการระบายน้ำจากเขื่อนที่ผู้ใช้พิมพ์ เป็นปริมาณระบายรายวัน 7 วัน หน่วยล้าน ลบ.ม./วัน "
          "ตอบเป็น JSON เท่านั้น รูปแบบ {\"release\": [ตัวเลข 7 ตัว]} ถ้าอ่านไม่ได้หรือไม่แน่ใจ ตอบ {\"release\": null} ห้ามอธิบาย")


def parse_ai(text: str, today: float) -> list[float] | None:
    """GLM reads what the rules could not; only a JSON list of 7 numbers within 0–MAX is accepted."""
    if os.environ.get("AI_EXPLAIN", "1") != "1":
        return None
    from floodwatch import ai
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"วันนี้ระบาย {today:.2f} ล้าน ลบ.ม./วัน\nแผน: {(text or '')[:200]}"}]
    try:
        out = ai.run(messages, max_tokens=120, timeout=15)
    except Exception:
        return None
    m = re.search(r"\{.*\}", out or "", re.S)
    if not m:
        return None
    try:
        vals = json.loads(m.group(0)).get("release")
        return _ok([float(v) for v in vals]) if isinstance(vals, list) else None
    except (ValueError, TypeError, AttributeError):
        return None


def parse(text: str, today: float) -> tuple[list[float], str] | None:
    """(release, "rules" | "ai") or None."""
    vals = parse_rules(text, today)
    if vals:
        return vals, "rules"
    vals = parse_ai(text, today)
    return (vals, "ai") if vals else None
