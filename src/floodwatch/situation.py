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
BKK = "กรุงเทพมหานคร"
# what the news leads with (Thai PBS 2026-10-03: the Chao Phraya Dam release and the flow at Nakhon Sawan), from RID
# discharge readings (m³/s); upstream first, then the dam
FLOWS = (("C.2", "น้ำเหนือที่นครสวรรค์"), ("C.13", "เขื่อนเจ้าพระยาระบาย"))
FLOW_STEADY = 50  # m³/s: a 24 h change smaller than this reads "ทรงตัว"
SHORT = {"อยุธยา": "พระนครศรีอยุธยา", "กรุงเทพ": "กรุงเทพมหานคร", "กทม": "กรุงเทพมหานคร", "โคราช": "นครราชสีมา"}
_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_VERDICTS = ("ปลอดภัย", "ไม่ท่วม", "ปกติ", "ไม่ต้องกังวล", "ไม่ต้องห่วง", "ท่วมแน่", "แน่นอน", "รับรอง", "ประกาศ", "อพยพ",
             "ด่วน")  # warm, never a siren (live trial 2026-10-04: "เร่งด่วน:", "ด่วน!")


def _top(items: list[str], k: int = 3) -> list[str]:
    return [p for p, _ in Counter(p for p in items if p).most_common(k)]


def facts(stations: list[dict], risks: dict, rain: dict, flows: dict | None = None, prev: dict | None = None) -> dict:
    """Counts and places for all of Thailand (fresh gauges only), from /api/stations, /api/risks and /api/rain;
    `flows` {code: {q, q24}} from RID discharge readings; `prev` the stored facts of about 24 h ago (yesterday())."""
    fresh = [s for s in stations if not s.get("stale") and s.get("status") in ("critical", "warning", "watch", "normal")]
    over = [s for s in fresh if s["status"] == "critical"]
    rising_of = lambda xs: [s for s in xs if (s.get("trend") or {}).get("group") == "rising"]
    rising = rising_of(over)
    grp = {g["key"]: g.get("items") or [] for g in (risks or {}).get("groups") or []}
    group = lambda k: {"n": len(grp.get(k, [])), "top": _top([i.get("province") for i in grp.get(k, [])])}
    # may reach the bank: only gauges whose water is rising name a province (owner 2026-10-04: Bangkok was named while
    # its gauges sat steady just under the bank); the steady ones are only counted
    may = grp.get("may_reach", [])
    may_up = [i for i in may if i.get("sub") == "rising"]
    bkk = [s for s in fresh if s.get("province") == BKK]
    bkk_over = [s for s in bkk if s["status"] == "critical"]
    r = (rain or {}).get("all") or {}
    m = r.get("measured") or {}
    mm = float(m["rain_24h"]) if m.get("rain_24h") is not None else None
    fc = r.get("forecast_mm24")
    flow = []
    for code, label in FLOWS:
        v = (flows or {}).get(code) or {}
        if v.get("q") is not None:
            flow.append({"code": code, "label": label, "q": round(v["q"]),
                         "change": None if v.get("q24") is None else round(v["q"] - v["q24"])})
    prev_over = ((prev or {}).get("over") or {}).get("n")
    return {
        "n": len(fresh),
        "over": {"n": len(over), "rising": len(rising), "provinces": len({s.get("province") for s in over}),
                 "rising_top": [[p, n] for p, n in Counter(s.get("province") for s in rising).most_common(3)],
                 **({"prev_n": prev_over} if prev_over is not None else {})},
        "near": sum(1 for s in fresh if s["status"] == "warning"),
        "below": sum(1 for s in fresh if s["status"] == "normal"),
        "may_reach": {"n": len(may_up), "top": _top([i.get("province") for i in may_up]), "near_steady": len(may) - len(may_up)},
        "upstream": group("upstream"), "fast_rise": group("fast_rise"),
        "bkk": {"over": len(bkk_over), "over_rising": len(rising_of(bkk_over)),
                "may_reach_rising": sum(1 for i in may_up if i.get("province") == BKK),
                "near": sum(1 for s in bkk if s["status"] == "warning")} if bkk else None,
        "flows": flow,
        "rain_measured": {"mm": round(mm), "place": m.get("name_th"), "province": m.get("province")} if mm and mm >= HEAVY_MM else None,
        "rain_forecast": {"mm": round(fc), "province": r.get("forecast_where")} if fc and fc >= HEAVY_MM else None,
    }


def _flow_text(x: dict) -> str:
    ch = x.get("change")
    how = "" if ch is None else " ทรงตัว" if abs(ch) < FLOW_STEADY else f" {'เพิ่มขึ้น' if ch > 0 else 'ลดลง'}จากเมื่อวาน {abs(ch):,}"
    return f"{x['label']} {x['q']:,} ลบ.ม./วินาที{how}"


def _bkk_text(b: dict) -> str:
    """Bangkok in one line (the question every Bangkok reader asks first)."""
    bits = []
    if b["over"]:
        bits.append(f"ล้นตลิ่ง {b['over']} จุด" + (f" น้ำยังขึ้น {b['over_rising']} จุด" if b["over_rising"] else " ทรงตัวหรือลดลง"))
    bits.append(f"อาจถึงตลิ่งใน 24–48 ชม. {b['may_reach_rising']} จุด" if b["may_reach_rising"]
                else "ยังไม่มีจุดที่น้ำขึ้นจนอาจถึงตลิ่ง")
    if b["near"]:
        bits.append(f"ใกล้ตลิ่ง/คลองเต็ม {b['near']} จุด")  # the top bar's own words
    return "กรุงเทพฯ " + " ".join(bits)


def items(f: dict) -> list[dict]:
    """The ticker as short items, urgent first, each with its own symbol (owner 2026-10-04: "very long text, try to use
    symbols or anything to see the separation of phrase"). Every item is one fact from `facts`."""
    out = []
    add = lambda topic, icon, text: out.append({"topic": topic, "icon": icon, "text": text})
    o = f["over"]
    if o["rising"]:
        where = " · ".join(f"{p} {n}" for p, n in o["rising_top"])
        # "เช่น" when the top provinces do not hold them all (2026-10-04: the AI read 3 provinces as all 11 gauges)
        some = "เช่น " if sum(n for _, n in o["rising_top"]) < o["rising"] else ""
        add("over_rising", "🔴", f"ล้นตลิ่งและน้ำยังขึ้น {o['rising']} สถานี ({some}{where})")
    if o["n"]:
        rest = o["n"] - o["rising"]
        yday = f" (เมื่อวาน {o['prev_n']})" if o.get("prev_n") is not None else ""
        add("over", "📊", f"ล้นตลิ่งรวม {o['n']} สถานีใน {o['provinces']} จังหวัด{yday}"
            + (f" ส่วนใหญ่ทรงตัวหรือลดลง ({rest} สถานี)" if rest > o["rising"] else ""))
    if f["may_reach"]["n"]:
        add("may_reach", "🟠", f"น้ำยังขึ้นและอาจถึงตลิ่งในอีก 24–48 ชม. {f['may_reach']['n']} สถานี เช่น {' '.join(f['may_reach']['top'])}")
    if f.get("bkk"):
        add("bkk", "🏙️", _bkk_text(f["bkk"]))
    if f.get("flows"):
        add("flows", "🏞️", " · ".join(_flow_text(x) for x in f["flows"]))
    if f["upstream"]["n"]:
        add("upstream", "🌊", f"น้ำเหนือกำลังมา {f['upstream']['n']} สถานี เช่น {' '.join(f['upstream']['top'])}")
    if f["fast_rise"]["n"]:
        add("fast_rise", "🟡", f"น้ำขึ้นเร็ว {f['fast_rise']['n']} สถานี เช่น {' '.join(f['fast_rise']['top'])}")
    if f["rain_measured"]:
        m = f["rain_measured"]
        add("rain", "🌧️", f"ฝนมากสุด 24 ชม. ที่ผ่านมา {m['mm']} มม. ที่ {m['place']} จ.{m['province']}")
    if f["rain_forecast"]:
        add("rain_forecast", "☁️", f"อีก 24 ชม. คาดฝนหนักแถว จ.{f['rain_forecast']['province']}")
    if f["n"]:
        add("overview", "🔵", f"ยังรับน้ำได้ {f['below']} จาก {f['n']} สถานี")
    return out


def rule_text(f: dict) -> str:
    """The plain ticker: the items in one line (the fallback when AI is off or its answer fails the check)."""
    return " · ".join(f"{i['icon']} {i['text']}" for i in items(f))


AMBIGUOUS = {"เลย", "แพร่", "ตาก", "น่าน", "ตรัง", "ยะลา", "ระนอง", "เพชรบุรี"}  # also everyday words or inside other names


def _places(text: str, ours: bool = False) -> set[str]:
    """Provinces named in a text; in the AI's text, names that are also everyday Thai words count only after จ./จังหวัด
    (2026-10-04: "…เลย" rejected a good retelling as a new place); in our own rule text every name is a province."""
    found = {p for p in regions.PROVINCE_REGION if (ours or p not in AMBIGUOUS) and p in text}
    found |= {p for p in AMBIGUOUS if re.search(rf"(?:จ\.\s?|จังหวัด){p}", text)}
    found |= {full for short, full in SHORT.items() if short in text}
    return found


def _nums(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUM.findall(text)}  # "2,500" and "2500" are the same number


CONDITIONALS = ("หาก", "ถ้า")  # "หากฝนหนักต่อเนื่อง น้ำอาจขึ้นเร็วขึ้น" (live 2026-10-04): a guess the facts do not make


def yesterday(history: list[dict], now) -> dict | None:
    """The stored facts closest to 24 h before `now` (20–28 h back), or None."""
    import datetime as dt
    best = None
    for h in history or []:
        try:
            age = (now - dt.datetime.fromisoformat(h["at"])).total_seconds() / 3600
        except (KeyError, TypeError, ValueError):
            continue
        if 20 <= age <= 28 and (best is None or abs(age - 24) < abs(best[0] - 24)):
            best = (age, h)
    return best[1] if best else None


def check(text: str, f: dict) -> list[str]:
    """Problems with an AI retelling ([] = may be shown)."""
    t = (text or "").strip()
    if not t:
        return ["empty"]
    rule = rule_text(f)
    issues = []
    if re.search(r"[A-Za-z]{3,}", t):
        issues.append("not Thai")
    if _nums(t) - _nums(rule):
        issues.append("new number")
    if any(w in t and w not in rule for w in CONDITIONALS):
        issues.append("speculation")
    if _places(t) - _places(rule, ours=True):
        issues.append("new place")
    issues += [f"verdict '{v}'" for v in _VERDICTS if v in t and v not in rule]
    if len(t) > TICKER_MAX:
        issues.append("too long")
    return issues


SYSTEM = ("คุณเป็นผู้ประกาศข่าวสถานการณ์น้ำของแอปติดตามระดับน้ำ เรียบเรียงข้อมูลที่ให้เป็นข่าววิ่งสั้น ๆ "
          "ด้วยภาษาไทยที่เป็นธรรมชาติ ลื่นไหล อบอุ่น ใจเย็น เหมือนเพื่อนที่รู้เรื่องน้ำเล่าให้ฟัง ไม่ใช่ภาษาราชการหรือภาษารายงาน\n"
          "กติกา:\n"
          "- เลือก 4–5 ข้อที่คนอยากรู้ที่สุด เรียงตามเลขข้อเดิม (ข้อแรก ๆ สำคัญกว่า) ข้อที่ไม่เลือกให้ข้ามไป\n"
          "- เขียนข้อละหนึ่งประโยคสั้น อ่านจบในครั้งเดียว ขึ้นต้นด้วยเลขข้อเดิม เช่น 1) …\n"
          "- ใช้ได้เฉพาะตัวเลข จังหวัด และสถานที่ที่อยู่ในข้อนั้นเท่านั้น ห้ามย้ายข้อมูลข้ามข้อ ห้ามเพิ่มเหตุผลหรือคำคาดเดา\n"
          "- ถ้าข้อมูลมีคำว่า เช่น ต้องบอกว่าเป็นตัวอย่าง ห้ามทำให้เข้าใจว่าเป็นทั้งหมด\n"
          "- ไม่ใช้คำว่า หาก ถ้า ด่วน เร่งด่วน ปลอดภัย ปกติ ไม่ท่วม แน่นอน อพยพ ไม่ใช้เครื่องหมายตกใจ ไม่ใส่อีโมจิ "
          "ไม่ลงท้ายด้วยครับหรือค่ะ ไม่บอกว่าเป็นประกาศทางการ\n"
          "- ตอบเฉพาะรายการข้อ")
ITEM_MAX = 110  # characters in one AI item: one breath on a phone


def prompt(f: dict) -> list[dict]:
    lines = "\n".join(f"{k}) {i['text']}" for k, i in enumerate(items(f), 1))
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"ข้อมูลจากแอป (ทั่วประเทศ):\n{lines}"}]


def _ai(messages: list[dict]) -> str | None:
    from floodwatch import ai
    return ai.run(messages, max_tokens=700, timeout=25)


def parse_items(text: str | None, rule: list[dict]) -> list[dict]:
    """The AI's numbered lines ("3) …") as items with our symbol for that fact; lines without a known number are dropped."""
    out, seen = [], set()
    for line in (text or "").splitlines():
        m = re.match(r"\s*(\d+)\s*[).:]\s*(.+)", line)
        if not m:
            continue
        k = int(m.group(1))
        if 1 <= k <= len(rule) and k not in seen:
            seen.add(k)
            out.append({"n": k, "topic": rule[k - 1]["topic"], "icon": rule[k - 1]["icon"], "text": m.group(2).strip()})
    return out


def check_items(got: list[dict], rule: list[dict]) -> list[str]:
    """Problems with the AI items ([] = may be shown): each item may only use the numbers and places of its own fact,
    plus the checks on the whole text (not Thai, verdicts, conditions)."""
    if not got:
        return ["no items"]
    issues = []
    for g in got:
        own = rule[g["n"] - 1]["text"]
        if _nums(g["text"]) - _nums(own):
            issues.append(f"new number in item {g['n']}")
        if _places(g["text"]) - _places(own, ours=True):
            issues.append(f"new place in item {g['n']}")
        if len(g["text"]) > ITEM_MAX:
            issues.append(f"item {g['n']} too long")
    whole = " ".join(g["text"] for g in got)
    if re.search(r"[A-Za-z]{3,}", whole):
        issues.append("not Thai")
    rule_all = " ".join(i["text"] for i in rule)
    issues += [f"verdict '{v}'" for v in _VERDICTS if v in whole and v not in rule_all]
    if any(w in whole and w not in rule_all for w in CONDITIONALS):
        issues.append("speculation")
    return issues


def compose(f: dict) -> dict:
    """{"items", "text", "rule", "ai": bool, "rejected"}: the AI items when they pass `check_items`, else the rule items."""
    rule = items(f)
    rejected: list = []
    for _ in range(2):  # one retry: a slip (a new number or place) is rare and random (live trials 2026-10-04)
        try:
            got = parse_items(_ai(prompt(f)), rule)
        except Exception:
            got = []
        issues = check_items(got, rule)
        if not issues:
            shown = [{"icon": g["icon"], "text": g["text"]} for g in got]
            return {"items": shown, "text": " · ".join(f"{i['icon']} {i['text']}" for i in shown), "rule": rule_text(f),
                    "ai": True, "rejected": rejected}
        rejected += issues
    shown = [{"icon": i["icon"], "text": i["text"]} for i in rule]
    return {"items": shown, "text": rule_text(f), "rule": rule_text(f), "ai": False, "rejected": rejected}


FLOWS_SQL = """WITH latest AS (
    SELECT DISTINCT ON (code) code, obs_time, discharge FROM observation
     WHERE code = ANY(%(codes)s) AND discharge IS NOT NULL AND obs_time > now() - interval '6 hours'
     ORDER BY code, obs_time DESC)
SELECT l.code, l.discharge AS q,
       (SELECT o.discharge FROM observation o WHERE o.code = l.code AND o.discharge IS NOT NULL
           AND o.obs_time BETWEEN l.obs_time - interval '26 hours' AND l.obs_time - interval '22 hours'
         ORDER BY abs(extract(epoch FROM o.obs_time - (l.obs_time - interval '24 hours'))) LIMIT 1) AS q24
  FROM latest l"""
HISTORY_H = 30


def flows_now(c) -> dict:
    """{code: {q, q24}}: the latest discharge (last 6 h) and the one about 24 h before it, for FLOWS."""
    return {r["code"]: {"q": float(r["q"]), "q24": None if r["q24"] is None else float(r["q24"])}
            for r in c.execute(FLOWS_SQL, {"codes": [k for k, _ in FLOWS]}).fetchall()}


def run(base: str = "http://app:3000") -> dict:
    """Worker task (every 30 min): read the app's own API and the RID flows, compose, store in collector_state
    'situation'; keep the last 30 h of counts ('situation_history') so the next day can say "(เมื่อวาน N)"."""
    import datetime as dt
    import requests
    from floodwatch import db
    get = lambda p: requests.get(f"{base}{p}", timeout=60).json()
    now = dt.datetime.now(dt.timezone.utc)
    with db.connect() as c:
        flows = flows_now(c)
        hist = db.get_state(c, "situation_history") or []
    f = facts(get("/api/stations")["stations"], get("/api/risks"), get("/api/rain").get("by_region") or {},
              flows=flows, prev=yesterday(hist, now))
    out = {**compose(f), "facts": f, "at": now.isoformat()}
    keep = [h for h in hist if (now - dt.datetime.fromisoformat(h["at"])).total_seconds() < HISTORY_H * 3600]
    keep.append({"at": now.isoformat(), "over": {"n": f["over"]["n"], "rising": f["over"]["rising"]},
                 "may_reach": {"n": f["may_reach"]["n"]}, "near": f["near"]})
    with db.connect() as c:
        db.set_state(c, "situation", out)
        db.set_state(c, "situation_history", keep)
        c.commit()
    return out
