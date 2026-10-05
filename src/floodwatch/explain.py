"""Plain words and resident questions over the pin panel (owner 2026-10-02: "ลองให้คนทั่วไปใช้ เขาไม่เข้าใจง่ายๆ … ให้ ai
แปลเป็นความเข้าใจง่ายๆ … be careful about UX"; then "AI สรุปดูไม่ได้ข้อมูลอะไรเท่าไหร่ แม้มีตัวเลขด้านล่างเยอะแยะ ควรเล่า
หรืออธิบายให้ดีกว่านี้ ว่าสถานีที่ใกล้เคียง แต่อยู่ไกล เป็นยังไง"; D-068).

- `plain(out)`: the panel's one line in everyday words, by template: which water it speaks about (here, or a gauge N km
  away), how full it is, and the 24 h row's word; then rain and street reports in words. No rain amounts (KI-258).
- `answer(q, out)`: rules decide every answer, as short labelled lines that tell the panel's own story with its numbers:
  the gauge and its distance, how full it is now, what it did, what the 24/48 h rows mean in words (a "? ไม่แน่ชัด" row
  is said as unclear, with its range as "half of past cases"), rain and street reports, and what to do. Advice gets
  firmer only on the panel's own warning signals.
- `gist(q, lines)`: GLM may add one short spoken-style sentence from those lines. `check` rejects it if it adds a
  number, a direction the lines do not say, a verdict ("ได้ครับ", "ไม่ท่วม", "ปลอดภัย", "ปกติ"…), drops a "cannot tell",
  calls a far gauge "แถวนี้", is not Thai or is long. Same lines → same gist (cached); a daily cap and ai.run's circuit
  breaker bound the cost; AI_EXPLAIN=0 switches it off. GLM sees only the question and the lines, never the pin (D-032).
Why rules carry the content: free AI answers gave "ได้ครับ" to "พาลูกไปโรงเรียนพรุ่งนี้เช้าได้ไหม"; AI rewordings of whole
answers passed the checker only 43 % of the time (too long, changed directions) at a median 4.5 s (validation
2026-10-02, 176 answers).
"""
from __future__ import annotations

import datetime as dt
import os
import re
import threading

from floodwatch import ai

QUESTIONS = {"simple": "สรุปให้ฟังง่าย ๆ", "home": "น้ำจะท่วมบ้านไหม", "car": "ควรย้ายรถไหม",
             "travel": "พรุ่งนี้เดินทางได้ไหม", "prepare": "ควรเตรียมอะไร", "numbers": "ตัวเลขหมายถึงอะไร"}
DAILY_CAP = 1500          # AI gists per process per day
CACHE_H = 6               # the key is the answer's lines, so new facts make a new key
GIST_MAX = 420            # characters: the story card is 3-4 short sentences (a weather app's AI card ~250)
STEADY_M = 0.05           # the rows' "ทรงตัว" band (D-060)
# the rows' own words (web/app.js CHANGE, OBS)
LEVEL_TH = {"strong_fall": "ลดลงมาก", "fall": "ลดลง", "small_fall": "ลดลงเล็กน้อย", "steady": "ทรงตัว",
            "small_rise": "เพิ่มขึ้นเล็กน้อย", "rise": "เพิ่มขึ้น", "strong_rise": "เพิ่มขึ้นมาก"}
OBS_TH = {"steady": "ทรงตัว", "small_fall": "ลดลงเล็กน้อย", "fall": "ลดลง", "strong_fall": "ลดลงมาก",
          "small_rise": "เพิ่มขึ้นเล็กน้อย", "rise": "เพิ่มขึ้น", "strong_rise": "เพิ่มขึ้นมาก", "mixed": "ขึ้นลงสลับกัน"}
STATE_TH = {"critical": "ล้นตลิ่งแล้ว", "warning": "ใกล้เต็มตลิ่ง", "watch": "น้ำเริ่มสูง", "normal": "ยังรับน้ำได้"}
RAIN_TH = [(0.1, "ไม่มีฝน"), (10.0, "ฝนเล็กน้อย"), (35.0, "ฝนปานกลาง"), (90.0, "ฝนหนัก"), (float("inf"), "ฝนหนักมาก")]

_cache: dict[tuple[str, str], tuple[str | None, float]] = {}
_lock = threading.Lock()
_count = {"day": "", "n": 0}


def _rain_word(mm: float | None) -> str | None:
    if mm is None:
        return None
    return next(w for i, (mx, w) in enumerate(RAIN_TH) if (mm < mx if i == 0 else mm <= mx))


def _signed(x: float) -> str:  # web/app.js signedCm: "−" (U+2212) for minus
    v = round(x * 100)
    return f"{'+' if v > 0 else '−' if v < 0 else ''}{abs(v)}"


def _row(ch: dict | None, unsure: bool) -> tuple[dict | None, bool]:
    """What the panel's row shows (web/app.js trendRow): kind "dir" (a model or measured direction), "steady" (±5 cm,
    never after a "?" at a shorter horizon, D-060), "unclear" ("? ไม่แน่ชัด"); plus the range as the row prints it."""
    if not ch:
        return None, unsure
    lk = ch.get("likely")
    agrees = not lk or (lk[1] < 0 if ch.get("dir") == "falling" else lk[0] > 0 if ch.get("dir") == "rising" else True)
    directional = ch.get("level") != "steady" and ch.get("method") not in (None, "persistence") and agrees
    narrow = bool(lk) and not ch.get("wide") and max(abs(lk[0]), abs(lk[1])) <= STEADY_M
    kind = "dir" if directional else "steady" if narrow and not unsure else "unclear"
    printed = ("ช่วงกว้างเกินไป" if ch.get("wide") or not lk else f"ราว {_signed(lk[0])} ซม." if _signed(lk[0]) == _signed(lk[1])
               else f"{_signed(lk[0])} ถึง {_signed(lk[1])} ซม.")
    word = LEVEL_TH.get(ch.get("level")) if kind == "dir" else "ทรงตัว" if kind == "steady" else None
    return ({"kind": kind, "word": word, "likely": lk, "wide": bool(ch.get("wide")), "printed": printed, "r90": ch.get("range90"),
             "lean": ch.get("lean") if kind == "unclear" else None, "lean_rec": ch.get("lean_rec")},
            unsure or kind == "unclear")


def _span(lk: list | None, wide: bool) -> str:
    """A likely range in words: "ลดลง 5 ซม. ถึงเพิ่มขึ้น 10 ซม."."""
    if wide or not lk:
        return "ช่วงที่กว้างมาก"
    lo, hi = round(lk[0] * 100), round(lk[1] * 100)
    if lo < 0 < hi:
        return f"ลดลง {-lo} ซม. ถึงเพิ่มขึ้น {hi} ซม."
    if hi <= 0:
        return f"ลดลง {-hi}–{-lo} ซม." if hi != lo else f"ลดลง {-lo} ซม."
    return f"เพิ่มขึ้น {lo}–{hi} ซม." if hi != lo else f"เพิ่มขึ้น {hi} ซม."


def _amount(lk: list | None) -> str | None:
    """The size of a directional range without its direction word: "4 ซม.", "3–6 ซม."."""
    if not lk:
        return None
    a, b = sorted((abs(round(lk[0] * 100)), abs(round(lk[1] * 100))))
    return f"{a} ซม." if a == b else f"{a}–{b} ซม."


def _km(x) -> str:  # as the app prints a distance (JS: 6.0 → "6")
    return f"{float(x):g}"


def _lead(out: dict) -> dict | None:
    """The gauge whose rows the panel shows (pointHTML: the nearest canal if it has a forecast, else the nearest one
    with a trend)."""
    near, trend = out.get("nearest_canal"), out.get("nearest_canal_trend")
    if near and near.get("station") and (near["station"].get("change24") or near["station"].get("change12")):
        return near
    return trend or near


def _signal(out: dict) -> str:
    """high: the panel's own warnings (risk high, over the bank, ≥ 3 street reports); watch: moderate risk, a street
    report, or near the bank; calm otherwise."""
    a, risk = out.get("area") or {}, (out.get("forecast") or {}).get("risk")
    n = int((out.get("evidence") or {}).get("traffy_flood_reports_1km_6h") or 0)
    if risk == "high" or n >= 3 or (a.get("category") == "critical" and a.get("confidence") in ("low", "medium")):
        return "high"
    if risk == "moderate" or n > 0 or a.get("category") == "warning":
        return "watch"
    return "calm"


def _facts(out: dict) -> dict:
    W, a, lead = out.get("word") or "คลอง", out.get("area") or {}, _lead(out)
    st = (lead or {}).get("station") or {}
    usable = a.get("confidence") in ("low", "medium")
    far = bool(lead) and (bool(lead.get("far")) or not usable)
    rows, unsure = {}, False
    for h in (24, 48, 72):  # the rows the app shows (owner 2026-10-04: no 12 h); "?" carries forward like trendRows
        rows[h], unsure = _row(st.get(f"change{h}"), unsure)
    if st.get("status_basis") == "bma_thresholds" and (st.get("over_bma_critical_m") or 0) > 0:
        level = f"เกินเกณฑ์ของ กทม. {abs(round(st['over_bma_critical_m'] * 100))} ซม."
    elif st.get("freeboard_m") is not None:
        c = round(st["freeboard_m"] * 100)
        level = "ระดับเท่าตลิ่ง" if c == 0 else f"สูงกว่าตลิ่ง {-c} ซม." if c < 0 else f"ต่ำกว่าตลิ่ง {c} ซม."
    else:
        level = None
    status = (a.get("category") if usable and not far else st.get("status")) if lead else None
    o = st.get("observed24") or {}
    obs = None
    if OBS_TH.get(o.get("level")):
        amount = "" if o["level"] in ("steady", "mixed") else f" {abs(o.get('change_cm') or 0)} ซม."
        obs = (o.get("hours") or 24, OBS_TH[o["level"]] + amount)
    m = out.get("rain_measured") or {}
    return {"W": W, "lead": lead, "name": st.get("name_th"), "km": _km(lead["distance_km"]) if lead and lead.get("distance_km") is not None else "?", "far": far,
            "dist_far": bool(lead and lead.get("far")),  # far by distance; "far" also covers disagreeing gauges around the pin
            "state": STATE_TH.get(status), "level": level, "obs": obs, "rows": rows,
            "fc_rain": _rain_word(out.get("rain_next24_mm")),
            "fell": _rain_word(float(m["rain_24h"])) if m.get("rain_24h") is not None else None,
            "street": int((out.get("evidence") or {}).get("traffy_flood_reports_1km_6h") or 0), "signal": _signal(out),
            "fb": round(st["freeboard_m"] * 100) if st.get("freeboard_m") is not None else None}


def _bank(f: dict) -> dict | None:
    """Could the water reach the bank within the forecast? From the rows' 90 % ranges (9 in 10 past cases) against the
    cm left to the bank now (owner 2026-10-02: say what is possible, even at a far gauge)."""
    fb = f["fb"]
    ups = [(h, round(r["r90"][1] * 100)) for h, r in f["rows"].items() if h in (24, 48) and r and r.get("r90")]
    if fb is None or fb <= 0 or not ups:
        return None
    h, up = max(ups, key=lambda x: x[1])
    when = "ใน 1–2 วัน" if h == 48 else "ในวันข้างหน้า"
    past_up = "น้ำไม่เคยขึ้นเกินระดับนี้" if up <= 0 else f"น้ำขึ้นไม่เกิน {up} ซม."
    line = f"🏞️ ตลิ่ง: เหลืออีกราว {fb} ซม. {when} 9 ใน 10 ครั้งที่ผ่านมา{past_up}"
    if up >= fb:
        return {"risk": "reach", "line": line + " จึงอาจถึงตลิ่งได้",
                "story": "แต่ถ้าน้ำขึ้นมาก อาจถึงตลิ่งได้", "plain": "แต่อาจถึงตลิ่งได้ถ้าน้ำขึ้นมาก"}  # the cm are in "now"
    if fb - up >= 10:
        return {"risk": "clear", "line": line, "story": "ถ้าเป็นแบบที่ผ่านมา น้ำยังไม่น่าจะถึงตลิ่ง", "plain": ""}
    return {"risk": "close", "line": line, "story": "ถ้าน้ำขึ้นมาก อาจเข้าใกล้ตลิ่ง", "plain": ""}


def _possible(r: dict) -> tuple[str, str]:
    """An unclear row ("? ไม่แน่ชัด") as what is possible (D-060): (story clause, plain clause). A row that leans by the
    measured pace (D-091) says the likely direction and that the amount is not certain, as the panel's chip does."""
    if r.get("lean"):
        w = "เพิ่มขึ้น" if r["lean"] == "up" else "ลดลง"
        return f"วันข้างหน้าน้ำน่าจะ{w}ตามแนวโน้มที่วัดได้ แต่ยังไม่แน่ชัดว่าเท่าไร", f"น้ำน่าจะ{w}แต่ยังไม่แน่ชัดว่าเท่าไร"
    lk = r["likely"]
    if r["wide"] or not lk:
        return "วันข้างหน้ายังไม่ชัดว่าน้ำจะขึ้นหรือลง", "ยังไม่ชัดว่าน้ำจะขึ้นหรือลง"
    lo, hi = round(lk[0] * 100), round(lk[1] * 100)
    if lo < 0 < hi:
        span = f"อาจลดลงราว {-lo} ซม. หรือเพิ่มขึ้นราว {hi} ซม."
        if max(-lo, hi) <= 10:
            return f"วันข้างหน้าน้ำน่าจะเปลี่ยนไม่มาก {span}", "น้ำน่าจะเปลี่ยนไม่มาก"
        return f"วันข้างหน้ายังไม่ชัดว่าน้ำจะขึ้นหรือลง {span}", "ยังไม่ชัดว่าน้ำจะขึ้นหรือลง"
    if lo >= 0:
        amt = f"{lo}–{hi}" if lo != hi else f"{hi}"
        return f"วันข้างหน้าน้ำอาจเพิ่มขึ้นราว {amt} ซม. แต่ยังไม่แน่ชัด", "น้ำอาจเพิ่มขึ้นแต่ยังไม่แน่ชัด"
    amt = f"{-hi}–{-lo}" if lo != hi else f"{-lo}"
    return f"วันข้างหน้าน้ำอาจลดลงราว {amt} ซม. แต่ยังไม่แน่ชัด", "น้ำอาจลดลงแต่ยังไม่แน่ชัด"


def _trend_clause(r: dict | None) -> str:
    if not r:
        return "ยังไม่มีคาดการณ์ว่าน้ำจะขึ้นหรือลง"
    if r["kind"] == "unclear":
        return _possible(r)[1]
    return f"อีก 24 ชม. น้ำน่าจะ{r['word']}"


def _rain_street(f: dict, short: bool = False) -> str | None:
    """Rain and street reports in words; `short` (the plain line, whose water clause already says "อีก 24 ชม.") drops
    the repeated horizon."""
    parts = []
    if f["fell"] in ("ฝนปานกลาง", "ฝนหนัก", "ฝนหนักมาก"):
        parts.append(f"24 ชม. ที่ผ่านมามี{f['fell']}")
    if f["fc_rain"]:
        ahead = "" if short else "อีก 24 ชม. "
        nxt = f"{ahead}ไม่น่าจะมีฝน" if f["fc_rain"] == "ไม่มีฝน" else f"{ahead}คาดว่ามี{f['fc_rain']}"
        if parts and short:  # "…มีฝนปานกลาง ต่อไปคาดว่ามีฝนเล็กน้อย", not "… และคาดว่า… และ…"
            parts[-1] += f" ต่อไป{nxt}"
        else:
            parts.append(nxt)
    if f["street"]:
        parts.append(f"มีคนแจ้งน้ำท่วมถนนใกล้ ๆ {f['street']} เรื่อง")
    return " และ".join(parts) if parts else None


def plain(out: dict) -> str:
    """One or two short sentences under the headline: the water (here, or a gauge N km away), then rain and reports."""
    f = _facts(out)
    r24 = f["rows"].get(24)
    if not f["lead"]:
        water = f"ไม่มีสถานีวัดน้ำใกล้จุดนี้พอ จึงยังบอกไม่ได้ว่าน้ำใน{f['W']}แถวนี้เป็นอย่างไร"
    elif f["far"]:
        now = f["level"] or f["state"]
        water = f"สถานีที่ใกล้ที่สุดอยู่ห่าง {f['km']} กม.{f' น้ำที่นั่น{now}' if now else ''} และ{_trend_clause(r24)}"
    else:
        joiner = "และ" if r24 and r24["kind"] != "unclear" else "แต่"
        water = f"{f['W']}แถวนี้{f['state'] or 'ยังบอกสถานะไม่ได้'} {joiner}{_trend_clause(r24)}"
    bank = _bank(f) if f["lead"] else None
    if bank and bank["plain"]:
        water += f" {bank['plain']}"
    rs = _rain_street(f, short=True)
    return water + (" " + rs if rs else "")


def _story(f: dict) -> list[str]:
    """The gauge lines shared by the answers: which gauge, now, what it did, the 24/48 h rows in words."""
    if not f["lead"]:
        return [f"📍 ไม่มีสถานีวัดน้ำในระยะ 8 กม. จึงบอกไม่ได้ว่าน้ำใน{f['W']}แถวนี้เป็นอย่างไร"]
    why = "ซึ่งไกล" if f["dist_far"] else "แต่สถานีรอบ ๆ ให้ผลต่างกัน"
    lines = [f"📍 สถานีที่ใกล้ที่สุด: {f['name']} ห่าง {f['km']} กม. {why} ใช้ดูภาพรวมเท่านั้น" if f["far"]
             else f"📍 ดูจากสถานี: {f['name']} ห่าง {f['km']} กม."]
    state = f" ({f['state']})" if f["state"] else ""
    now = f"น้ำที่นั่น{f['level']}{state}" if f["level"] else f"น้ำที่นั่น{f['state']}" if f["state"] else None
    if now:
        lines.append(f"🌊 ตอนนี้: {now}")
    if f["obs"]:
        lines.append(f"↕️ {f['obs'][0]} ชม. ที่ผ่านมา: {f['obs'][1]}")
    for h in (24, 48):
        r = f["rows"].get(h)
        if not r:
            continue
        if r["kind"] == "dir":
            amt = _amount(r["likely"]) if not r["wide"] else None
            lines.append(f"🔮 อีก {h} ชม.: น่าจะ{r['word']}{f' ราว {amt}' if amt else ''}")
        elif r["kind"] == "steady":
            lines.append(f"🔮 อีก {h} ชม.: น่าจะทรงตัว (เปลี่ยนไม่เกิน 5 ซม.)")
        elif r.get("lean"):
            rec = r.get("lean_rec") or {}
            said = f" (ในอดีตเป็นแบบนี้ราว {round(rec['hit'] * 10)} ใน 10 ครั้ง)" if (rec.get("n") or 0) >= 30 and rec.get("hit") is not None else ""
            w = "เพิ่มขึ้น" if r["lean"] == "up" else "ลดลง"
            lines.append(f"🔮 อีก {h} ชม.: น่าจะ{w}ตามแนวโน้มที่วัดได้{said} แต่ยังไม่แน่ชัดว่าเท่าไร (ระหว่าง{_span(r['likely'], r['wide'])})")
        else:
            # "? ไม่แน่ชัด": the direction is not proven. A range on both sides of zero is "up or down"; a one-sided one
            # (+1 to +64 cm) is only "not certain" (validation 2026-10-02: "ขึ้นหรือลง … เพิ่มขึ้น 1–64 ซม." read as nonsense)
            lk = r["likely"]
            both = r["wide"] or not lk or (lk[0] < 0 < lk[1])
            head = "ยังบอกไม่ได้ว่าจะขึ้นหรือลง" if both else "ยังบอกไม่ได้แน่ชัด"
            lines.append(f"🔮 อีก 24 ชม.: {head} ครึ่งหนึ่งของครั้งที่ผ่านมาอยู่ระหว่าง{_span(lk, r['wide'])}" if h == 24
                         else f"🔮 อีก 48 ชม.: ยังบอกไม่ได้ (ระหว่าง{_span(lk, r['wide'])})")
    bank = _bank(f)
    if bank:
        lines.append(bank["line"])
    return lines


def _todo(f: dict, q: str) -> str:
    if f["signal"] == "high":
        return {"car": "👉 ถ้าจอดในที่ต่ำ ควรย้ายไปที่สูงไว้ก่อน และติดตามประกาศของเขตหรืออำเภอ"}.get(
            q, "👉 ควรยกของสำคัญขึ้นที่สูงไว้ก่อน และติดตามประกาศของเขตหรืออำเภอ")
    if not f["lead"] or f["far"]:
        why = "สถานีรอบ ๆ ให้ผลต่างกัน" if f["lead"] and not f["dist_far"] else "สถานีอยู่ไกล"
        return f"👉 {why} ให้ดูน้ำใน{f['W']}หรือท่อระบายน้ำใกล้บ้านประกอบ และช่วยแตะ 'รายงานน้ำที่จุดของคุณ' ให้คนแถวนี้รู้"
    if q == "car":
        return "👉 ถ้าจอดในที่ต่ำ ให้ดูฝนและรายงานน้ำท่วมถนนอีกครั้งก่อนนอนและตอนเช้า"
    if f["signal"] == "watch":
        return "👉 ถ้าฝนตกหนักหรือมีคนแจ้งน้ำท่วมถนนเพิ่ม ให้เตรียมยกของขึ้นที่สูง"
    return "👉 ถ้าฝนตกหนักให้กลับมาดูอีกครั้ง"


def answer(q: str, out: dict) -> list[str]:
    """The rule answer to a resident question, as short labelled lines (shown as they are)."""
    f = _facts(out)
    rs = _rain_street(f)
    street = (f"🚧 ตอนนี้มีคนแจ้งน้ำท่วมถนนใกล้ ๆ {f['street']} เรื่อง" if f["street"]
              else "🚧 ตอนนี้ยังไม่มีใครแจ้งน้ำท่วมถนนในรัศมี 1 กม.")
    story = _story(f)
    if q == "simple":
        lines = story + [f"🌧️ {rs}" if rs else None, _todo(f, q)]
    elif q == "home":
        lines = [f"🏠 แอปบอกไม่ได้ว่าน้ำจะเข้าบ้านหรือไม่ เพราะวัดน้ำใน{f['W']} ไม่ได้วัดที่บ้านหรือบนถนน"] + story[:4] + [_todo(f, q)]
    elif q == "car":
        lines = ["🚗 แอปบอกไม่ได้ว่าต้องย้ายรถหรือไม่"] + story[:4] + [street, _todo(f, q)]
    elif q == "travel":
        fc = (f"🌧️ อีก 24 ชม. {'ไม่น่าจะมีฝน' if f['fc_rain'] == 'ไม่มีฝน' else 'คาดว่ามี' + f['fc_rain']}"
              if f["fc_rain"] else None)
        lines = ["🛣️ แอปไม่รู้สภาพถนนทุกเส้น", street, fc, "👉 ก่อนออกเดินทาง ให้ดูจุดสีม่วงบนแผนที่ (รายงานน้ำท่วมถนน) อีกครั้ง"]
    elif q == "prepare":
        lines = (["👉 ควรทำตอนนี้: เก็บเอกสารสำคัญ ยา และของมีค่าไว้ที่สูง ชาร์จโทรศัพท์ให้เต็ม เตรียมไฟฉาย",
                  "🚗 ย้ายรถไปที่สูง และติดตามประกาศของเขตหรืออำเภอ"] if f["signal"] == "high"
                 else ["🧳 เตรียมไว้ก่อนได้: เก็บเอกสารสำคัญและยาไว้ในที่สูง ชาร์จโทรศัพท์ให้เต็ม",
                       "🚗 รู้ไว้ว่าจะย้ายรถไปจอดที่ไหนถ้าน้ำขึ้น"])
    elif q == "numbers":
        r = f["rows"].get(24)
        where = f"ที่สถานี {f['name']}" if f["name"] else "ที่สถานีวัดน้ำ"
        if r:
            chip = r["word"] or "? ไม่แน่ชัด"
            meaning = (f"น่าจะ{r['word']} ราว {_amount(r['likely'])}" if r["kind"] == "dir" and r["likely"]
                       else f"อาจ{_span(r['likely'], r['wide'])}" if r["kind"] == "unclear" else "น่าจะเปลี่ยนไม่เกิน 5 ซม.")
            lines = [f"📏 'อีก 24 ชม. {chip} {r['printed']}' หมายถึง อีก 1 วัน น้ำ{where} {meaning} จากตอนนี้",
                     "📍 วัดที่สถานี ไม่ใช่ที่บ้าน: ค่าลบคือน้ำลด ค่าบวกคือน้ำขึ้น"]
        else:
            lines = [f"📏 ตัวเลขในแถว 'อีก 24 ชม.' คือระดับน้ำที่คาดว่าจะเปลี่ยนจากตอนนี้ วัด{where} ไม่ใช่ที่บ้าน"]
        lines += ["❔ '? ไม่แน่ชัด' แปลว่าข้อมูลยังไม่พอจะบอกทิศทาง ตัวเลขคือช่วงที่เกิดขึ้นครึ่งหนึ่งของครั้งที่ผ่านมา",
                  f"🏷️ ป้ายสี เช่น '{f['W']}ยังรับน้ำได้' หรือ 'เต็มลำน้ำ 93%' บอกว่าตอนนี้น้ำใกล้ตลิ่งแค่ไหน"]
    else:
        raise KeyError(q)
    return [line for line in lines if line]


# --- the story card: a few easy sentences, numbers stay in the lines (owner 2026-10-02: "I got complicated info …
# looks at second one to get feeling, they try to explain easily") -----------------------------------------------------
EASY_STATE = {"critical": "ล้นตลิ่งแล้ว", "warning": "ค่อนข้างสูง ใกล้เต็มตลิ่ง", "watch": "เริ่มสูง", "normal": "ยังรับน้ำได้อีก"}


def _easy_level(f: dict) -> str:
    st = f["lead"]["station"] if f["lead"] else {}
    if st.get("status_basis") == "bma_thresholds" and (st.get("over_bma_critical_m") or 0) > 0:
        return f"เกินเกณฑ์ของ กทม. ราว {abs(round(st['over_bma_critical_m'] * 100))} ซม."
    if st.get("freeboard_m") is None:
        return ""
    c = round(st["freeboard_m"] * 100)
    return "ระดับเท่าตลิ่ง" if c == 0 else f"สูงกว่าตลิ่งราว {-c} ซม." if c < 0 else f"ต่ำกว่าตลิ่งราว {c} ซม."


def _easy_water(f: dict) -> str:
    W, status = f["W"], f["lead"]["station"].get("status") if f["lead"] else None
    if not f["lead"]:
        return f"แถวนี้ยังไม่มีสถานีวัดน้ำในระยะ 8 กม. จึงยังบอกไม่ได้ว่าน้ำใน{W}เป็นอย่างไร"
    lvl = _easy_level(f)
    if f["far"]:
        now = f"น้ำที่นั่น{lvl}" if lvl else f"น้ำที่นั่น{EASY_STATE[status]}" if status in EASY_STATE else ""
        where = (f"สถานีวัดน้ำที่ใกล้ที่สุดอยู่ไกลราว {f['km']} กม." if f["dist_far"]
                 else f"สถานีวัดน้ำรอบ ๆ ให้ผลต่างกัน สถานีที่ใกล้ที่สุดอยู่ห่าง {f['km']} กม.")  # validation: "ไกลราว 1.3 กม."
        return f"{where}{' ตอนนี้' + now if now else ''}"
    state = {v: k for k, v in STATE_TH.items()}.get(f["state"])
    return f"น้ำใน{W}แถวนี้{EASY_STATE.get(state, 'ยังบอกสถานะไม่ได้')}{f' ({lvl})' if lvl else ''}"


def _easy_trend(f: dict) -> str:
    r, o = f["rows"].get(24), f["obs"]
    past = f"ช่วงที่ผ่านมาน้ำ{o[1].split(' ')[0]} " if o else ""
    if not f["lead"]:
        return ""
    if not r:
        return f"{past}ยังไม่มีคาดการณ์ว่าน้ำจะขึ้นหรือลง".strip()
    bank = _bank(f)
    if r["kind"] == "dir":
        text = f"{past}วันข้างหน้าน้ำมีแนวโน้ม{r['word']}"
    elif r["kind"] == "steady":
        text = f"{past}วันข้างหน้าน้ำน่าจะทรงตัว"
    else:
        text = f"{past}{_possible(r)[0]}"
    # the bank: always when it may be reached; otherwise only where the direction is not a proven fall
    if bank and (bank["risk"] == "reach" or (r["kind"] != "dir" or "เพิ่ม" in (r["word"] or ""))):
        text += f" {bank['story']}"
    return text


def _easy_rain(f: dict, after_trend: bool = False) -> str:
    """Rain and street reports; after a trend clause ("วันข้างหน้า…") the horizon is not repeated."""
    parts = []
    if f["fell"] in ("ฝนปานกลาง", "ฝนหนัก", "ฝนหนักมาก"):
        parts.append(f"เพิ่งมี{f['fell']}ไปแล้ว")
    if f["fc_rain"]:
        ahead = "" if after_trend else "อีกหนึ่งวันข้างหน้า"
        nxt = f"{ahead}ไม่น่าจะมีฝน" if f["fc_rain"] == "ไม่มีฝน" else f"{ahead}คาดว่ามี{f['fc_rain']}"
        if parts:
            parts[-1] += f" ต่อไป{nxt}"
        else:
            parts.append(nxt)
    if f["street"]:
        parts.append(f"มีคนแจ้งน้ำท่วมถนนใกล้ ๆ {f['street']} เรื่อง")
    return " และ".join(parts)


def narrative(q: str, out: dict) -> str:
    """The story card: 3-4 short everyday sentences, at most a couple of numbers; the numbers stay in `answer`."""
    f = _facts(out)
    todo = (f"ช่วยดูน้ำใน{f['W']}ใกล้บ้านประกอบด้วย" if (not f["lead"] or f["far"]) and f["signal"] != "high"
            else _todo(f, q).replace("👉 ", ""))
    street = (f"ตอนนี้มีคนแจ้งน้ำท่วมถนนใกล้ ๆ {f['street']} เรื่อง" if f["street"]
              else "ตอนนี้ยังไม่มีใครแจ้งน้ำท่วมถนนแถวนี้")
    if q == "simple":
        trend = _easy_trend(f)
        rain = _easy_rain(f, after_trend=bool(trend))
        parts = [_easy_water(f), f"{trend} และ{rain}" if trend and rain else trend or rain, todo]
    elif q == "home":
        parts = [f"แอปบอกไม่ได้ว่าน้ำจะเข้าบ้านไหม เพราะวัดน้ำใน{f['W']} ไม่ใช่ที่บ้าน", _easy_water(f), _easy_trend(f),
                 todo]
    elif q == "car":
        parts = ["แอปบอกไม่ได้ว่าต้องย้ายรถหรือไม่", _easy_water(f), street, todo]
    elif q == "travel":
        rain = f"อีกหนึ่งวันข้างหน้า{'ไม่น่าจะมีฝน' if f['fc_rain'] == 'ไม่มีฝน' else 'คาดว่ามี' + f['fc_rain']}" if f["fc_rain"] else ""
        parts = ["แอปไม่รู้สภาพถนนทุกเส้น", street, rain, "ก่อนออกเดินทางให้ดูจุดสีม่วงบนแผนที่อีกครั้ง"]
    elif q == "prepare":
        parts = [re.sub(r"^\W+\s*", "", line) for line in answer(q, out)]
    elif q == "numbers":
        parts = [f"ตัวเลขในแถว 'อีก 24 ชม.' คือระดับน้ำที่คาดว่าจะเปลี่ยนจากตอนนี้ วัดที่สถานี ไม่ใช่ที่บ้าน",
                 "ค่าลบคือน้ำลด ค่าบวกคือน้ำขึ้น", "ถ้าเห็น '? ไม่แน่ชัด' แปลว่าข้อมูลยังไม่พอจะบอกทิศทาง"]
    else:
        raise KeyError(q)
    return " ".join(p for p in parts if p)


# --- ✨ on a station sheet and on the ⚠️ จับตา tab (owner 2026-10-04) -------------------------------------------------
def _word_of(s: dict) -> str:
    r = s.get("river") or ""
    return "แม่น้ำ" if "แม่น้ำ" in r else "คลอง" if "คลอง" in r else "ลำน้ำ"


def station(s: dict, rain_measured: dict | None, rain_next24: float | None) -> tuple[list[str], str]:
    """The story and lines for one station sheet (owner 2026-10-04: "เพิ่ม ✨ … ที่จุด Stations … รวมข้อมูลน้ำฝนไปด้วย"):
    the station itself is the subject (never "แถวนี้"), the same rows as the sheet, the rain that fell nearby and the
    forecast. A stale station tells no "now" (D-024)."""
    name = s.get("name_th") or s["code"]
    head = " · ".join([f"📍 สถานีวัดน้ำ{name}"] + ([s["river"]] if s.get("river") else []) + ([f"จ.{s['province']}"] if s.get("province") else []))
    if s.get("stale"):
        hrs = max(1, round((s.get("age_min") or 0) / 60))
        return ([head, f"⏳ ข้อมูลล่าสุดเมื่อราว {hrs} ชม. ก่อน จึงไม่ใช้บอกสถานการณ์ตอนนี้"],
                f"ข้อมูลล่าสุดของสถานีวัดน้ำ{name}เก่าเกิน 3 ชม. จึงยังเล่าสถานการณ์ตอนนี้ไม่ได้ ลองกลับมาดูใหม่เมื่อข้อมูลอัปเดต")
    W = _word_of(s)
    out = {"word": W, "nearest_canal": {"station": s, "distance_km": 0.0, "far": False},
           "area": {"category": s.get("status"), "confidence": "medium"}, "rain_measured": rain_measured or {},
           "rain_next24_mm": rain_next24, "evidence": {"traffy_flood_reports_1km_6h": s.get("street_reports_6h") or 0},
           "forecast": {}}
    f = _facts(out)
    lines = [head] + [line.replace("น้ำที่นั่น", "น้ำที่สถานี") for line in _story(f)[1:]]
    m = rain_measured or {}
    if m.get("rain_24h") is not None:
        mm = float(m["rain_24h"])
        d = m.get("distance_km")
        where = (" ที่สถานีนี้" if d is not None and d < 0.5 else
                 f" ที่สถานีวัดฝน{m['name_th']} ห่าง {_km(d)} กม." if m.get("name_th") and d is not None else "")
        word = _rain_word(mm)
        lines.append("🌧️ 24 ชม. ที่ผ่านมา: ไม่มีฝน" if word == "ไม่มีฝน" else f"🌧️ 24 ชม. ที่ผ่านมา: {word} {round(mm)} มม.{where}")
    if rain_next24 is not None:
        w = _rain_word(rain_next24)
        lines.append("☁️ อีก 24 ชม.: ไม่น่าจะมีฝน" if w == "ไม่มีฝน" else f"☁️ อีก 24 ชม.: คาดว่ามี{w} ราว {round(rain_next24)} มม.")
    lvl = _easy_level(f)
    first = f"น้ำที่สถานีวัดน้ำ{name} {EASY_STATE.get(s.get('status'), 'ยังบอกสถานะไม่ได้')}" + (f" ({lvl})" if lvl else "")
    trend, rain = _easy_trend(f), _easy_rain(f, after_trend=True)
    todo = (f"ใครอยู่ริม{W}ใกล้สถานีนี้ ควรติดตามประกาศของอำเภอหรือเขตอย่างใกล้ชิด" if s.get("status") == "critical"
            else f"ถ้าฝนตกหนัก ใครอยู่ริม{W}ใกล้สถานีนี้ให้กลับมาดูอีกครั้ง" if s.get("status") == "warning" else "")
    parts = [first, f"{trend} และ{rain}" if trend and rain else trend or rain, todo]
    return lines, " ".join(p for p in parts if p)


def watch(out: dict, area: str) -> tuple[list[str], str]:
    """The ⚠️ จับตา tab in a few sentences (owner 2026-10-04: "อธิบายสถานการณ์ภาพรวม และเน้นจุดที่วิกฤติ"): the most
    critical gauges first (over the bank and still rising, the highest above the bank first), then what may reach the
    bank, upstream water, fast rises and heavy rain. `out` is risks.only(build(...)) for the tab's region/province."""
    g = {x["key"]: x["items"] for x in out.get("groups") or []}
    subs = {sub["sub"]: [gg for p in sub["provinces"] for gg in p["gauges"]] for sub in g.get("over_bank", [])}
    rising, flat = subs.get("rising", []), subs.get("flat_or_falling", [])
    n_over = sum(len(v) for v in subs.values())
    n_prov = len({gg.get("province") for v in subs.values() for gg in v})
    fb = lambda x: x["freeboard_m"] if x.get("freeboard_m") is not None else 0.0
    crit = sorted(rising, key=fb)[:3]
    may = g.get("may_reach", [])
    may_up = [i for i in may if i.get("sub") == "rising"]
    up, fast, rain = g.get("upstream", []), g.get("fast_rise", []), g.get("rain", [])
    nm = lambda x: f"{x['name_th']} ({x['province']})" if x.get("province") else x["name_th"]
    some = lambda xs, shown=3: "เช่น " if len(xs) > shown else ""  # an example stays an example; a full list is not one
    lines = []
    if n_over:
        split = (f"น้ำยังขึ้น {len(rising)} · ทรงตัวหรือลดลง {len(flat)}" if rising and flat
                 else "น้ำยังขึ้นทั้งหมด" if rising and not flat else "ทรงตัวหรือลดลงทั้งหมด" if flat else "")
        lines.append(f"🔴 ล้นตลิ่งแล้ว {n_over} สถานี ใน {n_prov} จังหวัด" + (f" · {split}" if split else ""))
    if crit:
        lines.append("❗ จุดที่ควรจับตาที่สุด (ล้นตลิ่งและน้ำยังขึ้น): "
                     + " · ".join(f"{nm(c)} สูงกว่าตลิ่ง {-round(fb(c) * 100)} ซม." for c in crit))
    if may_up:
        lines.append(f"🟠 น้ำยังขึ้นและอาจถึงตลิ่งใน 24–48 ชม. {len(may_up)} สถานี: "
                     + " · ".join(f"{nm(i)} ต่ำกว่าตลิ่ง {round(fb(i) * 100)} ซม." for i in may_up[:3]))
    if len(may) > len(may_up):
        lines.append(f"↔️ อีก {len(may) - len(may_up)} สถานีอยู่ใกล้ตลิ่งแต่ทรงตัวหรือลดลง")
    if up:
        lines.append(f"🌊 น้ำเหนือกำลังมา {len(up)} สถานี: {some(up)}"
                     + " · ".join(f"{nm(i)} ต้นน้ำขึ้น {i['up']['rise_cm']} ซม." for i in up[:3]))
    if fast:
        lines.append(f"🟡 คาดว่าน้ำขึ้นเร็ว (20 ซม. ขึ้นไปใน 24 ชม.) {len(fast)} สถานี: {some(fast)}" + " · ".join(nm(i) for i in fast[:3]))
    if rain:
        lines.append("🌧 ฝนหนักคาดการณ์ใน 24 ชม.: " + " · ".join(f"{r['province']} ราว {round(r['mm24'])} มม." for r in rain[:3]))
    if not lines:
        return [f"✅ ไม่พบจุดเสี่ยงใน{area}ในอีก 24–48 ชม. ข้างหน้า"], f"ตอนนี้ยังไม่พบจุดเสี่ยงใน{area}ในอีก 24–48 ชม. ข้างหน้า"
    trend_word = ("ทั้งหมดทรงตัวหรือลดลง" if flat and not rising else " ส่วนใหญ่ทรงตัวหรือลดลงแล้ว" if len(flat) > len(rising) else "")
    parts = [f"ตอนนี้{area}มีน้ำล้นตลิ่ง {n_over} สถานี" + (f" {trend_word.strip()}" if trend_word else "")
             if n_over else f"ตอนนี้{area}ยังไม่มีสถานีที่น้ำล้นตลิ่ง"]
    # each group closes its own sentence (live 2026-10-04: GLM merged an over-bank gauge into "…กำลังจะถึงตลิ่ง")
    if crit:
        more = f" และ {crit[1]['name_th']}" if len(crit) > 1 else ""
        parts.append(f"จุดที่ควรจับตาที่สุดคือ {nm(crit[0])}{more} ซึ่งน้ำล้นตลิ่งแล้วและยังขึ้นอยู่")
    if may_up:
        who = f"{some(may_up, 1)}{nm(may_up[0])}" if len(may_up) > 1 else f"คือ {nm(may_up[0])}"
        parts.append(f"ส่วนอีก {len(may_up)} สถานีที่ยังไม่ถึงตลิ่ง น้ำยังขึ้นและอาจถึงตลิ่งใน 1–2 วัน {who}")
    if up and not crit and not may_up:  # a long story makes GLM slip; upstream stays in the numbers (lines)
        parts.append(f"น้ำเหนือกำลังมาที่ {nm(up[0])}")
    if fast and not crit and not may_up:
        parts.append(f"น้ำอาจขึ้นเร็วที่ {nm(fast[0])}")
    if rain:
        parts.append(f"ส่วนฝนหนักคาดว่าจะตกแถว{rain[0]['province']}")
    return lines, " ".join(parts)


# --- the checker: an AI gist may only say what the lines say ---------------------------------------------------------
_NUM = re.compile(r"[0-9๐-๙]+(?:[.,][0-9๐-๙]+)?")
# directions as people write them ("น้ำจะขึ้น", "ลดลง"); "ขึ้นหรือลง"/"ขึ้นลงสลับ" is not a direction
_DIRS = {"fall": re.compile(r"ลดลง|น้ำลด|ต่ำลง|จะลด"), "rise": re.compile(r"สูงขึ้น|เพิ่มขึ้น|(?:น้ำ|จะ)\S{0,6}ขึ้น(?!หรือ|ลง)"),
         "flat": re.compile(r"ทรงตัว|คงที่")}
_STRONG = re.compile(r"(?:ขึ้น|ลง|ลด)\S{0,10}มาก")
_SURER = re.compile(r"(?:กำลังจะ|ใกล้จะ)ถึงตลิ่ง")
# verdicts; a polite particle after "ไม่ได้" / "รับน้ำได้" is not one ("ยังบอกไม่ได้ค่ะ", "ยังรับน้ำได้ค่ะ")
_VERDICTS = (r"(?<!ไม่)(?<!รับน้ำ)ได้(?:ครับ|ค่ะ)", r"ไปได้(?!หรือ|ไหม)", r"เดินทางได้(?!หรือ|ไหม)",
             r"ไม่ต้อง(?:ย้าย|กังวล|ห่วง|เตรียม|ทำอะไร|ระวัง)", "ไม่จำเป็น", "ไม่ท่วม",
             r"(?:ยังไม่น่าจะ|น่าจะยังไม่|คงยังไม่|คงจะไม่|ยังขึ้นไม่|ยังไม่)ถึงตลิ่ง",
             r"(?<!น่าจะ)(?<!น่าจะยัง)(?<!คง)(?<!คงจะ)(?<!คงยัง)(?<!ยังไม่น่าจะ)(?<!ยังขึ้น)(?<!ยัง)ไม่(?:ขึ้น)?ถึงตลิ่ง",
             r"จะท่วม(?!\S{0,8}(?:หรือ|ไหม))", "ท่วมแน่", "ปลอดภัย", "ปกติ", r"(?<!ไม่ได้)(?<!ไม่)แน่นอน", "รับรอง", "กังวล", "นาที")
_CANNOT = ("ไม่ได้", "ไม่รู้", "ไม่ทราบ", "ยังไม่มี", "ไม่สามารถ", "ไม่ชัด", "ไม่แน่ชัด", "ไม่มาก")


def _dirs(t: str) -> set[str]:
    return {k for k, rx in _DIRS.items() if rx.search(t)}


def check(text: str, rule: str) -> list[str]:
    """Problems with an AI gist against the rule lines ([] = may be shown)."""
    t = (text or "").strip()
    if not t:
        return ["empty"]
    future = "\n".join(line for line in rule.split("\n") if line.startswith(("🔮", "📏", "🏞️", "บทสรุป:")))  # forecast text
    past = "\n".join(line for line in rule.split("\n") if line.startswith("↕️"))
    said_past = "ที่ผ่านมา" in t
    issues = []
    if re.search(r"[A-Za-z]{3,}", t):
        issues.append("not Thai")
    if set(_NUM.findall(t)) - set(_NUM.findall(rule)):
        issues.append("new number")
    if _dirs(t) - _dirs(rule):
        issues.append("direction not in the answer")
    if not said_past and (_dirs(t) & _dirs(past)) - _dirs(future):  # validation 2026-10-02: "49 ซม. ที่ผ่านมา" → "จะขึ้นมาก"
        issues.append("past change told as future")
    if not said_past and _STRONG.search(t) and not _STRONG.search(future):
        issues.append("stronger than the forecast")
    if _SURER.search(t) and not _SURER.search(rule):  # "อาจถึงตลิ่ง" told as "กำลังจะถึงตลิ่ง" (live 2026-10-04)
        issues.append("stronger than the forecast")
    issues += [f"verdict '{m.group(0)}'" for v in _VERDICTS for m in [re.search(v, t)] if m and not re.search(v, rule)]
    if ("บอกไม่ได้" in rule or "ไม่รู้" in rule) and not any(c in t for c in _CANNOT):
        issues.append("dropped 'cannot tell'")
    if ("ไกล" in rule or "ไม่มีสถานีวัดน้ำ" in rule or "ให้ผลต่างกัน" in rule) and "ไกล" not in t and "ต่างกัน" not in t and re.search(
            r"แถวนี้\S{0,12}(?:ใกล้\S{0,4}เต็ม|ยังรับน้ำ|ล้นตลิ่ง|เริ่มสูง|ต่ำกว่าตลิ่ง|สูงกว่าตลิ่ง|ค่อนข้างสูง)", t):
        issues.append("far gauge called 'here'")  # a state told as "here" when the only gauge is far or missing
    if "ข่าวดี" in t or re.search(r"(?:ค่ะ|คะ|ครับ)(?=\s|$|[.!])", t):  # one neutral voice, never "good news" (2026-10-04)
        issues.append("tone")
    if re.match(r"\s*(?:เดี๋ยว|ขอ)?เล่าให้ฟัง", t):
        issues.append("filler opening")
    if re.search(r"(?:ไหม|มั้ย|หรือเปล่า|อยากให้\S*)\s*[?？]?\s*$", t):  # "…อยากให้ช่วยดูจุดไหนเพิ่มเติมไหม" (live 2026-10-04)
        issues.append("asks the reader")
    if len(t) > GIST_MAX:
        issues.append("too long")
    return issues


SYSTEM = ("คุณช่วยเล่าข้อมูลน้ำในแอปให้คนทั่วไปและผู้สูงอายุฟัง เป็นภาษาพูดที่อบอุ่น อ่อนโยน เข้าใจง่าย น่าฟัง 2–4 ประโยคสั้น ไม่เกิน 70 คำ "
          "เล่าตามบทสรุปที่ให้มาเป็นหลัก ใช้ตัวเลขน้อยที่สุด บอกสิ่งที่สำคัญที่สุดก่อน ใช้เฉพาะข้อมูลที่ให้ ห้ามเพิ่มตัวเลขหรือข้อมูลใหม่ ห้ามเปลี่ยนทิศทางของน้ำ "
          "ถ้าข้อมูลบอกว่าบอกไม่ได้ ไม่รู้ หรือสถานีอยู่ไกล ต้องบอกอย่างนุ่มนวล ถ้าสถานีอยู่ไกลห้ามเรียกว่าแถวนี้ "
          "ใช้ชื่อลำน้ำตามที่ระบุ ห้ามตัดทอนหรือแปลงชื่อสถานที่หรือลำน้ำเป็นคำอื่น "
          "เรียบเรียงภาษาพูดให้เชื่อมโยงลื่นไหลเป็นธรรมชาติ ไม่ใช้คำว่า 'และ' ซ้ำซ้อน "
          "ห้ามตอบว่าได้หรือไม่ได้แทนผู้ใช้ ห้ามใช้คำว่า ปกติ ปลอดภัย ไม่ท่วม ตอบเป็นภาษาไทยเท่านั้น ไม่ใส่อีโมจิ "
          "ไม่ต้องใส่ครับ ค่ะ หรือคะ เริ่มประโยคแรกด้วยสภาพน้ำเลย ไม่มีคำเกริ่นอย่าง เล่าให้ฟัง หรือ ข่าวดี "
          "คำว่า เริ่มสูง หมายถึงระดับน้ำค่อนข้างสูงเมื่อเทียบตลิ่ง ไม่ได้แปลว่ากำลังเพิ่มขึ้น "
          "เรียกจุดวัดว่า สถานีวัดน้ำ ตามด้วยชื่อ เช่น สถานีวัดน้ำสะพานนวรัฐ ห้ามพูดว่าน้ำในสะพาน "
          "ตอบเฉพาะข้อความ")


def _calls_today() -> int:
    today = dt.date.today().isoformat()
    if _count["day"] != today:
        _count.update(day=today, n=0)
    return _count["n"]


def prompt(q: str, lines: list[str], story: str | None = None) -> tuple[list[dict], str]:
    """The GLM messages for a retelling, and the rule text it is checked against (one place for app and validation)."""
    rule = "\n".join(([f"บทสรุป: {story}"] if story else []) + lines)
    return ([{"role": "system", "content": SYSTEM},
             {"role": "user", "content": f"คำถามของผู้ใช้: {QUESTIONS.get(q, q)}\nข้อมูล:\n{rule}"}], rule)


def tidy(text: str) -> str:
    """Drop sentence-final polite particles GLM adds despite the prompt (validation 2026-10-04: 13 of 18 rejections were
    only these): "นะคะ/นะครับ" -> "นะ", a lone "ครับ/ค่ะ/คะ" goes. Nothing else changes."""
    t = re.sub(r"นะ(?:คะ|ค่ะ|ครับ)(?=\s|$|[.!,])", "นะ", text)
    return re.sub(r"\s*(?:ครับ|ค่ะ|คะ)(?=\s|$|[.!,])", "", t).strip()


def gist(q: str, lines: list[str], story: str | None = None) -> str | None:
    """A warm retelling of the story (and the lines behind it) by GLM, or None (AI off, failed, capped or rejected)."""
    if os.environ.get("AI_EXPLAIN", "1") != "1":  # the owner's off switch (.env AI_EXPLAIN=0)
        return None
    messages, rule = prompt(q, lines, story)
    key = (q, rule)
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[1] < (CACHE_H * 3600 if hit[0] else 120):  # a failure is retried after 2 min (was 30 min)
            return hit[0]
        if _calls_today() >= DAILY_CAP:
            return None
        _count["n"] += 1
    good = None
    for _ in range(3):  # retries when an answer fails the check (live 2026-10-04: 1 in 3 national จับตา answers passed)
        try:
            text = ai.run(messages, max_tokens=400, timeout=15)  # GLM takes ~6-10 s; 8 s timed out (2026-10-04)
        except Exception:
            text = None
        if not text:
            break  # no answer (off, paused, timeout): do not wait twice
        text = tidy(text)
        if not check(text, rule):
            good = text
            break
    with _lock:
        _cache[key] = (good, now)
        if len(_cache) > 5000:
            for k in sorted(_cache, key=lambda k: _cache[k][1])[:1000]:
                _cache.pop(k, None)
    return good


# --- impact tab: the 7-day release scenarios (D-101) ------------------------------------------------------------------
def plan_words(plan: dict) -> str:
    """A release plan in words: constant, ramp, front-loaded or day by day (ล้าน ลบ.ม./วัน)."""
    r = plan["release"]
    kind = plan.get("kind")
    if kind in ("hold", "constant") or len(set(r)) == 1:
        return f"{r[0]:.1f} ล้าน ลบ.ม./วัน คงที่ 7 วัน" + (" (เท่าวันนี้)" if kind == "hold" else "")
    if kind == "ramp":
        return f"ทยอย{'เพิ่ม' if r[-1] > r[0] else 'ลด'}จาก {r[0]:.1f} เป็น {r[-1]:.1f} ล้าน ลบ.ม./วัน ใน 7 วัน"
    if kind == "front":
        k = next(i for i in range(1, len(r)) if r[i] != r[0])
        return f"{r[0]:.1f} ล้าน ลบ.ม./วัน {k} วันแรก แล้ว {r[k]:.1f}"
    return "รายวัน " + ", ".join(f"{x:.1f}" for x in r) + " ล้าน ลบ.ม./วัน"


def scenarios(cmp: dict) -> tuple[list[str], str]:
    """Lines and a plain story for the scenario comparison: today's reservoir, the ★ plan and the rule, what each other
    plan is best for, the constraints and the label. Numbers from the engine only; the AI may retell, never decide."""
    from floodwatch.scenarios import EFFECT_KEYS, EFFECT_TH
    dam = cmp.get("dam") or {}
    name = f"เขื่อน{dam.get('name_th') or ''}"
    rc = dam.get("rule_curve") or {}
    st0, up0, rel, inf = dam.get("storage_mcm"), rc.get("upper", (cmp.get("upper") or [None])[0]), dam.get("released_mcm"), dam.get("inflow_mcm")
    lines = [f"🏞️ {name} · ข้อมูลรายวัน {dam.get('dam_date') or ''}"]
    pos = ""
    if st0 is not None and up0 is not None:
        pos = (f"สูงกว่าเส้นควบคุมบน {st0 - up0:.0f} ล้าน ลบ.ม." if st0 > up0 else f"ต่ำกว่าเส้นควบคุมบน {up0 - st0:.0f} ล้าน ลบ.ม.")
        lines.append(f"ปริมาตรอ่าง {st0:.0f} ล้าน ลบ.ม." + (f" ({dam['storage_pct']:.0f} %)" if dam.get("storage_pct") is not None else "")
                     + f" · {pos} (เส้นบนวันนี้ {up0:.0f})")
    if rel is not None and inf is not None:
        hi = (cmp.get("inflow") or {}).get("high") or []
        lo = (cmp.get("inflow") or {}).get("low") or []
        band = f" ช่วงที่เป็นไปได้ใน 7 วัน {lo[-1]:.1f}–{hi[-1]:.1f}" if lo and hi else ""
        lines.append(f"วันนี้ระบาย {rel:.2f} และมีน้ำไหลเข้า {inf:.2f} ล้าน ลบ.ม./วัน (คิดว่าไหลเข้าเท่านี้ต่อไป{band})")
    rain = ((cmp.get("inputs") or {}).get("rain7") or {}).get("mm")
    if rain:
        lines.append(f"☁️ ฝนคาดการณ์ในลุ่มน้ำเหนือเขื่อน 7 วัน รวม {sum(rain):.0f} มม. (ดูประกอบ ไม่ได้ใช้คำนวณ)")
    plans = {p["id"]: p for p in cmp.get("plans") or []}
    opt = cmp.get("optimal") or {}
    star = plans.get(opt.get("id"))
    if star and opt.get("constraints_met"):
        lines.append(f"★ แผนที่เข้าเกณฑ์: {plan_words(star)} — {opt.get('reason', '')}")
    elif star:
        lines.append(f"⚠️ {opt.get('reason', '')} แผนที่ใกล้เคียงที่สุด: {plan_words(star)}")
    best = cmp.get("best_for") or {}
    for k in EFFECT_KEYS:
        p = plans.get(best.get(k))
        if p and p is not star:
            e = p["effects"]
            metric = {"city": f"ห่างตลิ่งในเมืองต่ำสุด {e['city_margin_min']:.2f} ม." if e.get("city_margin_min") is not None else "",
                      "worst": f"ห่างตลิ่งต่ำสุด {e['worst_margin_min']:.2f} ม." if e.get("worst_margin_min") is not None else "",
                      "total": f"เกินตลิ่งรวม {e['overtop_sum']:.2f}", "dam": f"ปริมาตรสูงสุด {e['storage_peak']:.0f}",
                      "curve": (f"ใต้เส้นควบคุมวันที่ {e['under_curve_day']}" if e.get("under_curve_day") else f"เหลือ {e['storage_end']:.0f} วันที่ 7"),
                      "water": f"เหลือ {e['storage_end']:.0f} ล้าน ลบ.ม. วันที่ 7", "warning": f"เปลี่ยนวันละไม่เกิน {e['ramp_max']:.1f}"}[k]
            lines.append(f"เหมาะกับ{EFFECT_TH[k]}: {plan_words(p)} ({metric})")
    ds = cmp.get("downstream") or {}
    mae = ds.get("mae_cm") or {}
    d1 = max((v[0] for v in mae.values() if v and v[0] is not None), default=None)
    d7 = max((v[-1] for v in mae.values() if v and v[-1] is not None), default=None)
    tested = ds.get("method") == "hybrid" and d1 is not None and d7 is not None
    if tested:  # E-7D-DOWN: the 7-day downstream method with its hindcast error per day
        lines.append(f"🟠 ระดับท้ายน้ำ 7 วัน ทดสอบย้อนหลังแล้ว: คลาดเคลื่อนเฉลี่ยสูงสุด ±{d1} ซม. ในวันที่ 1 ถึง ±{d7} ซม. ในวันที่ 7"
                     " — แผนต้องห่างตลิ่งมากกว่านี้ทุกวัน ใช้เปรียบเทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์")
    else:
        lines.append("🔴 ระดับท้ายน้ำจาก rating curve + เวลาเดินทาง ยังไม่ผ่านการทดสอบย้อนหลัง — ใช้เปรียบเทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์")
    first = f"ตอนนี้อ่าง{name}{pos and ' ' + pos} ระบายวันละ {rel:.1f} และมีน้ำเข้า {inf:.1f} ล้าน ลบ.ม." if rel is not None and inf is not None else f"ตอนนี้อ่าง{name} {pos}"
    if star and opt.get("constraints_met"):
        e = star["effects"]
        when = (f"กลับใต้เส้นควบคุมในวันที่ {e['under_curve_day']}" if e.get("under_curve_day")
                else f"ลดอ่างได้มากที่สุด (เหลือ {e['storage_end']:.0f} ล้าน ลบ.ม. ในวันที่ 7)")
        second = f"แผนที่เข้าเกณฑ์คือ {plan_words(star)}: {when} โดยทุกจุดยังห่างตลิ่งเกินความคลาดเคลื่อนของแบบจำลอง"
    elif star:
        second = f"{opt.get('reason', '')} แผนที่ใกล้เคียงที่สุดคือ{plan_words(star)}"
    else:
        second = "ยังไม่มีแผนให้เปรียบเทียบ"
    others = [EFFECT_TH[k] for k in EFFECT_KEYS if plans.get(best.get(k)) and plans.get(best.get(k)) is not star]
    third = ("แผนอื่นเหมาะกับ" + " ".join(dict.fromkeys(others)) + " ดูในแต่ละการ์ด" if others else "")
    tail = (f"ตัวเลขท้ายน้ำคลาดเคลื่อนได้ราว ±{d7} ซม. ในวันที่ 7 ใช้เทียบระหว่างแผน" if tested
            else "ตัวเลขท้ายน้ำยังไม่ผ่านการทดสอบ ใช้เทียบระหว่างแผนเท่านั้น")
    return lines, " ".join(x for x in (first, second, third, tail) if x)

