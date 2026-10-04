"""The national situation ticker in the top bar (owner 2026-10-04: "concentrate the all information of Thailand got from the
app into a single running scrolling text at notification in topbar … periodically update, like every 30 minutes …
Urgent message, critical areas and situations, the rain and water level situations … let AI prepare it into simple,
attractive and lovely Thai language which are easy to understand"; D-089).

Rules gather every fact from the app's own data (the station rows, the จับตา groups, the rain lines) and write a plain
ticker; the worker asks the AI (ai.run) every 30 min to retell it warmly; the retelling is shown only if `check` finds
no new number, no new place and no verdict word. The rule text is the fallback, so the ticker works without AI (D-022).
"""
from __future__ import annotations

import re
from collections import Counter

from floodwatch import regions

HEAVY_MM = 35.1  # the app's heavy-rain threshold (SUMMARY_RAIN_MIN_MM, KI-265)
TICKER_MAX = 300
SHORT = {"อยุธยา": "พระนครศรีอยุธยา", "กรุงเทพ": "กรุงเทพมหานคร", "กทม": "กรุงเทพมหานคร", "โคราช": "นครราชสีมา"}
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_VERDICTS = ("ปลอดภัย", "ไม่ท่วม", "ปกติ", "ไม่ต้องกังวล", "ไม่ต้องห่วง", "ท่วมแน่", "แน่นอน", "รับรอง", "ประกาศ", "อพยพ",
             "ด่วน")  # warm, never a siren (live trial 2026-10-04: "เร่งด่วน:", "ด่วน!")


def _top(items: list[str], k: int = 3) -> list[str]:
    return [p for p, _ in Counter(p for p in items if p).most_common(k)]


def facts(stations: list[dict], risks: dict, rain: dict) -> dict:
    """Counts and places for all of Thailand (fresh gauges only), from /api/stations, /api/risks and /api/rain."""
    fresh = [s for s in stations if not s.get("stale") and s.get("status") in ("critical", "warning", "watch", "normal")]
    over = [s for s in fresh if s["status"] == "critical"]
    rising = [s for s in over if (s.get("trend") or {}).get("group") == "rising"]
    grp = {g["key"]: g.get("items") or [] for g in (risks or {}).get("groups") or []}
    group = lambda k: {"n": len(grp.get(k, [])), "top": _top([i.get("province") for i in grp.get(k, [])])}
    r = (rain or {}).get("all") or {}
    m = r.get("measured") or {}
    mm = float(m["rain_24h"]) if m.get("rain_24h") is not None else None
    fc = r.get("forecast_mm24")
    return {
        "n": len(fresh),
        "over": {"n": len(over), "rising": len(rising), "provinces": len({s.get("province") for s in over}),
                 "rising_top": [[p, n] for p, n in Counter(s.get("province") for s in rising).most_common(3)]},
        "near": sum(1 for s in fresh if s["status"] == "warning"),
        "below": sum(1 for s in fresh if s["status"] == "normal"),
        "may_reach": group("may_reach"), "upstream": group("upstream"), "fast_rise": group("fast_rise"),
        "rain_measured": {"mm": round(mm), "place": m.get("name_th"), "province": m.get("province")} if mm and mm >= HEAVY_MM else None,
        "rain_forecast": {"mm": round(fc), "province": r.get("forecast_where")} if fc and fc >= HEAVY_MM else None,
    }


def rule_text(f: dict) -> str:
    """The plain ticker, urgent first. Every sentence is a fact from `facts`."""
    parts = []
    o = f["over"]
    if o["rising"]:
        where = " · ".join(f"{p} {n}" for p, n in o["rising_top"])
        # "เช่น" when the top provinces do not hold them all (2026-10-04: the AI read 3 provinces as all 11 gauges)
        some = "เช่น " if sum(n for _, n in o["rising_top"]) < o["rising"] else ""
        parts.append(f"🔴 ล้นตลิ่งและน้ำยังขึ้น {o['rising']} สถานี ({some}{where})")
    if o["n"]:
        rest = o["n"] - o["rising"]
        parts.append(f"ล้นตลิ่งรวม {o['n']} สถานีใน {o['provinces']} จังหวัด" + (f" ส่วนใหญ่ทรงตัวหรือลดลง ({rest} สถานี)" if rest > o["rising"] else ""))
    if f["may_reach"]["n"]:
        parts.append(f"🟠 อาจถึงตลิ่งในอีก 24–48 ชม. {f['may_reach']['n']} สถานี เช่น {' '.join(f['may_reach']['top'])}")
    if f["upstream"]["n"]:
        parts.append(f"🌊 น้ำเหนือกำลังมา {f['upstream']['n']} สถานี เช่น {' '.join(f['upstream']['top'])}")
    if f["fast_rise"]["n"]:
        parts.append(f"🟡 น้ำขึ้นเร็ว {f['fast_rise']['n']} สถานี เช่น {' '.join(f['fast_rise']['top'])}")
    if f["rain_measured"]:
        m = f["rain_measured"]
        parts.append(f"🌧️ ฝนมากสุด 24 ชม. ที่ผ่านมา {m['mm']} มม. ที่ {m['place']} จ.{m['province']}")
    if f["rain_forecast"]:
        parts.append(f"☁️ อีก 24 ชม. คาดฝนหนักแถว จ.{f['rain_forecast']['province']}")
    if f["n"]:
        parts.append(f"🔵 ยังรับน้ำได้ {f['below']} จาก {f['n']} สถานี")
    return " · ".join(parts)


AMBIGUOUS = {"เลย", "แพร่", "ตาก", "น่าน", "ตรัง", "ยะลา", "ระนอง", "เพชรบุรี"}  # also everyday words or inside other names


def _places(text: str) -> set[str]:
    """Provinces named in a text; names that are also everyday Thai words count only after จ./จังหวัด (2026-10-04: "…เลย"
    rejected a good retelling as a new place)."""
    found = {p for p in regions.PROVINCE_REGION if p not in AMBIGUOUS and p in text}
    found |= {p for p in AMBIGUOUS if re.search(rf"(?:จ\.\s?|จังหวัด){p}", text)}
    found |= {full for short, full in SHORT.items() if short in text}
    return found


def check(text: str, f: dict) -> list[str]:
    """Problems with an AI retelling ([] = may be shown)."""
    t = (text or "").strip()
    if not t:
        return ["empty"]
    rule = rule_text(f)
    issues = []
    if re.search(r"[A-Za-z]{3,}", t):
        issues.append("not Thai")
    if set(_NUM.findall(t)) - set(_NUM.findall(rule)):
        issues.append("new number")
    if _places(t) - _places(rule):
        issues.append("new place")
    issues += [f"verdict '{v}'" for v in _VERDICTS if v in t and v not in rule]
    if len(t) > TICKER_MAX:
        issues.append("too long")
    return issues


SYSTEM = ("คุณเขียนข่าวสั้นสถานการณ์น้ำทั่วประเทศไทยสำหรับแถบข้อความวิ่งในแอป ภาษาไทยที่อบอุ่น นุ่มนวล เป็นกันเอง อ่านลื่นไหล เข้าใจง่ายสำหรับทุกคน "
          "3–4 ประโยคสั้น ไม่เกิน 250 ตัวอักษร เลือกเฉพาะ 3–4 เรื่องที่สำคัญที่สุด เริ่มจากน้ำที่ล้นตลิ่งและยังขึ้น แล้วพื้นที่ที่ควรจับตา ฝน และภาพรวม "
          "เล่าอย่างใจเย็น ไม่ใช้คำว่า ด่วน หรือ เร่งด่วน ไม่ใช้เครื่องหมายตกใจ ถ้าข้อมูลบอกว่า เช่น ต้องบอกว่าเป็นตัวอย่าง ห้ามทำให้เข้าใจว่าเป็นทั้งหมด "
          "ใช้เฉพาะข้อมูลที่ให้ ห้ามเพิ่มตัวเลข จังหวัด หรือสถานที่ใหม่ ใช้ตัวเลขเท่าที่จำเป็น ห้ามใช้คำว่า ปลอดภัย ปกติ ไม่ท่วม แน่นอน อพยพ "
          "ห้ามบอกว่าเป็นประกาศทางการ ไม่ใส่ครับหรือค่ะ ไม่ใส่อีโมจิ ตอบเฉพาะข้อความ")


def prompt(f: dict) -> list[dict]:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"ข้อมูลจากแอป (ทั้งประเทศ):\n{rule_text(f).replace(' · ', chr(10))}"}]


def _ai(messages: list[dict]) -> str | None:
    from floodwatch import ai
    return ai.run(messages, max_tokens=500, timeout=25)


def compose(f: dict) -> dict:
    """{"text", "rule", "ai": bool, "rejected": [issues]}: the AI retelling when it passes `check`, else the rules."""
    rule = rule_text(f)
    rejected: list = []
    for _ in range(2):  # one retry: a slip (a new number or place) is rare and random (live trials 2026-10-04)
        try:
            text = _ai(prompt(f))
        except Exception:
            text = None
        issues = check(text, f) if text else ["no answer"]
        if not issues:
            return {"text": text.strip(), "rule": rule, "ai": True, "rejected": rejected}
        rejected += issues
    return {"text": rule, "rule": rule, "ai": False, "rejected": rejected}


def run(base: str = "http://app:3000") -> dict:
    """Worker task (every 30 min): read the app's own API, compose, store in collector_state 'situation'."""
    import datetime as dt
    import requests
    from floodwatch import db
    get = lambda p: requests.get(f"{base}{p}", timeout=60).json()
    f = facts(get("/api/stations")["stations"], get("/api/risks"), get("/api/rain").get("by_region") or {})
    out = {**compose(f), "facts": f, "at": dt.datetime.now(dt.timezone.utc).isoformat()}
    with db.connect() as c:
        db.set_state(c, "situation", out)
        c.commit()
    return out
