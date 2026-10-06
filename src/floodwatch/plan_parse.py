"""Type a plan in Thai (owner 2026-10-06; D-110): seven daily releases (ล้าน ลบ.ม./วัน) from text such as
"ระบาย 15 สามวันแล้วลดเหลือ 10". Rules first; GLM only when the rules cannot read it, and its answer is only 7 numbers that
fill the boxes for the engineer to check — nothing is computed until they press คำนวณ (D-022: AI never decides). Values
above MAX are refused, never clipped; a value above MAX or a per-second unit never reaches the AI either (it could "fix" it
into a plausible plan). The rules refuse rather than guess: a number they cannot place, a third step, a direction word the
numbers contradict, or "ลดลง 5" (by 5 or to 5?) all return None (final review, D-110). The text is never logged or stored."""
from __future__ import annotations

import json
import os
import re

DAYS = 7
MAX = 200.0  # the custom plan's own bound (the API accepts 0–200)
TH_NUM = {"หนึ่ง": 1, "สอง": 2, "สาม": 3, "สี่": 4, "ห้า": 5, "หก": 6, "เจ็ด": 7}
_TH_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
NUM = r"\d+(?:\.\d+)?"
N = "(" + NUM + ")"
UNIT = r"(?:ล้าน\s*(?:ลบ\.?\s*ม\.?)?\s*(?:/\s*วัน)?\s*)?"
CHANGE = re.compile(r"เพิ่ม|ลด|ขึ้น|ลง|แล้ว|ทีละ|ค่อย|จากนั้น|ต่อด้วย")  # words that say the release changes over the week
UP, DOWN = re.compile(r"เพิ่ม|ขึ้น"), re.compile(r"ลด|(?<!แป)ลง")  # "เปลี่ยนแปลง" (change) is not "ลง"
AMOUNT = r"(?![\d.])(?!\s*วัน)"  # a whole number that is not a day count ("แล้ว 10 วัน" is ten days, not 10)
RAMP = re.compile(r"ทยอย\S*\s*(?:จาก\s*)?" + N + r"\s*" + UNIT + r"(?:เป็น|ถึง|ไป|→|-)\s*" + N + AMOUNT + r"(.*)$")
# the first amount may not run on into a digit or a dot: "15 วันแรก" is not "1" for "5 วัน" (final review, D-110)
TWO = re.compile(r"(?P<a>" + NUM + r")(?![\d.])\s*" + UNIT + r"(?P<n>\d)\s*วัน(?:แรก)?\s*(?:แล้ว|จากนั้น|ต่อด้วย)?\s*(?:ค่อย)?\s*"
                 r"(?P<chg>(?:ลด|เพิ่ม)?\s*(?:ลง|ขึ้น)?)\s*(?P<to>เหลือ|เป็น|ไป)?\s*(?P<b>" + NUM + r")" + AMOUNT)
# the boxes are ล้าน ลบ.ม./วัน: "20 ลบ.ม./วินาที" is 1.7 ล้าน ลบ.ม./วัน, not 20 — refused, never converted or guessed
PER_SECOND = re.compile(r"วินาที|(?:(?<![ก-๙])|(?<=ต่อ))วิ(?![ก-๙])|(?<![a-z])(?:cms|cumecs?)(?![a-z])"
                        r"|m\s*(?:3|³|\^\s*3)\s*/\s*s|/\s*s(?:ec(?:ond)?)?(?![a-z])", re.I)


def _norm(text: str) -> str:
    t = (text or "").translate(_TH_DIGITS).replace(",", " ")
    for word, n in TH_NUM.items():
        t = re.sub(word + r"(?=\s*วัน)", str(n), t)
    return re.sub(r"\s+", " ", t).strip()


def _blocked(text: str) -> bool:
    """Text nobody may read into a plan: a per-second unit, or a value above MAX — as typed, and with a comma before three
    digits read as a thousands separator ("1,000" is one thousand, never "1" and "0"). The price: a comma list with
    three-digit items ("10,150,150,…") is refused too; such a plan is typed into the boxes."""
    raw = (text or "").translate(_TH_DIGITS)
    if PER_SECOND.search(raw):
        return True
    joined = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", raw)
    return any(float(x) > MAX for s in (_norm(text), joined) for x in re.findall(NUM, s))


def _direction_ok(t: str, a: float, b: float) -> bool:
    """A direction word must agree with the numbers: เพิ่ม/ขึ้น only when b > a, ลด/ลง only when b < a."""
    up, down = UP.search(t), DOWN.search(t)
    return not (up and down) and not (up and b <= a) and not (down and b >= a)


def _ok(vals) -> list[float] | None:
    if vals is None or len(vals) != DAYS or any(v is None or not (0 <= v <= MAX) for v in vals):
        return None
    return [round(float(v), 2) for v in vals]


def parse_rules(text: str, today: float) -> list[float] | None:
    """Day by day (7 numbers), a ramp ("ทยอย… จาก A เป็น B"), two steps ("A N วัน(แรก) แล้ว… B"), a constant (one number),
    or today's release ("คงเดิม", "เท่าวันนี้"); else None."""
    t = _norm(text)
    if not t or _blocked(text):
        return None
    m = RAMP.search(t)
    if m:
        a, b, rest = float(m.group(1)), float(m.group(2)), m.group(3)
        d = re.match(r"\s*(?:ล้าน\S*\s*)?(?:ภายใน|ใน)\s*(\d)\s*วัน", rest)
        n = int(d.group(1)) if d else DAYS
        rest = rest[d.end():] if d else rest
        # a duration we cannot honour, another clause with a number (before or after), or a contradicting direction
        if not 2 <= n <= DAYS or re.search(r"\d", rest) or re.search(r"\d", t[:m.start()]) or not _direction_ok(t, a, b):
            return None
        return _ok([a + (b - a) * min(k, n - 1) / (n - 1) for k in range(DAYS)])  # over n days, then hold b
    m = TWO.search(t)
    if m:
        a, n, b = float(m.group("a")), int(m.group("n")), float(m.group("b"))
        if re.search(r"\d", t[:m.start()] + t[m.end():]):  # a third step ("… แล้ว 10 2 วัน แล้ว 5") or a number we cannot place
            return None
        if m.group("chg").strip() and not m.group("to"):  # "แล้วลดลง 5": down by 5 or down to 5? (final review, D-110)
            return None
        if not _direction_ok(t, a, b):  # "แล้วเพิ่มขึ้น 5" after 10
            return None
        if 1 <= n < DAYS:
            return _ok([a] * n + [b] * (DAYS - n))
    nums = [float(x) for x in re.findall(N, re.sub(r"\d+\s*วัน", " ", t))]
    counts = [int(x) for x in re.findall(r"(\d+)\s*วัน", t)]
    if len(nums) == DAYS:  # day by day; a direction word must agree with the first and last day too
        return _ok(nums) if _direction_ok(t, nums[0], nums[-1]) else None
    # one number for the whole week only: "ระบาย 15 สามวัน" says nothing about days 4–7, so it is not 15 for 7 days
    whole_week = all(c == DAYS for c in counts)
    if len(nums) == 1 and not CHANGE.search(t) and whole_week:  # "เริ่ม 12 แล้วค่อย ๆ เพิ่ม…" is not a constant 12: leave it to the AI
        return _ok([nums[0]] * DAYS)
    if not nums and whole_week and re.search(r"คงเดิม|เท่าเดิม|เท่าวันนี้", t):
        return _ok([round(today, 2)] * DAYS)
    return None


SYSTEM = ("แปลงแผนการระบายน้ำจากเขื่อนที่ผู้ใช้พิมพ์ เป็นปริมาณระบายรายวัน 7 วัน หน่วยล้าน ลบ.ม./วัน "
          "ตอบเป็น JSON เท่านั้น รูปแบบ {\"release\": [ตัวเลข 7 ตัว]} ถ้าอ่านไม่ได้หรือไม่แน่ใจ ตอบ {\"release\": null} ห้ามอธิบาย")


def parse_ai(text: str, today: float) -> list[float] | None:
    """GLM reads what the rules could not; only a JSON list of 7 numbers within 0–MAX is accepted. Text with a value above
    MAX or a per-second unit is never sent."""
    if os.environ.get("AI_EXPLAIN", "1") != "1" or _blocked(text):
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
    """(release, "rules" | "ai") or None. A value above MAX or a per-second unit is refused here, before the rules and
    the AI (final review, D-110: "ระบาย 250" must never become an AI's 25)."""
    if _blocked(text):
        return None
    vals = parse_rules(text, today)
    if vals:
        return vals, "rules"
    vals = parse_ai(text, today)
    return (vals, "ai") if vals else None
