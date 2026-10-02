"""Optional Cloudflare Workers AI helpers (D-022). The app never depends on them.

Design rules:
- **Off the request path.** Only the worker calls AI, in the background; no page or API response waits for it.
- **Deterministic fallback first.** Keyword rules run instantly and always; AI only refines their labels.
- **Budget and breaker.** A daily neuron budget (default 3,000 of the 10,000 free per day) and a circuit breaker
  (1 h pause after 3 consecutive failures, or until 00:00 UTC after "daily allocation used", error 3036).
- **AI never writes safety facts.** Situation text is a template (see summary_text); evidence in D-022.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re

import requests

from floodwatch import db

log = logging.getLogger(__name__)
CATEGORIES = ("gauge_mismatch", "local_drainage", "emergency", "info", "spam")
URGENT_WORDS = ("ช่วยด้วย", "ติดอยู่", "ติดค้าง", "จมน้ำ", "ไฟดูด", "ไฟรั่ว", "หมดสติ", "บาดเจ็บ", "ผู้ป่วยติดเตียง",
                "เด็กหาย", "คนหาย", "อพยพไม่ได้", "ออกจากบ้านไม่ได้", "sos", "help")
SPAM_PATTERNS = (r"https?://", r"\bline\s*[:@]", r"@\w{3,}", r"ขาย", r"โปรโมชั่น", r"สมัครสมาชิก")
MODEL = os.environ.get("AI_MODEL", "@cf/aisingapore/gemma-sea-lion-v4-27b-it")
BUDGET = float(os.environ.get("AI_DAILY_NEURON_BUDGET", "3000"))
TRIAGE_PROMPT = ("Classify a Thai citizen's flood feedback note for a volunteer flood-information website. Reply ONLY "
                 "with JSON {\"category\": one of [gauge_mismatch, local_drainage, emergency, info, spam], "
                 "\"urgent\": true|false}. gauge_mismatch = the site's river/khlong level looks wrong; "
                 "local_drainage = street/soi/pipe flooding; emergency = someone may be in danger now; "
                 "urgent=true only if someone may be in danger now.")


def triage_rules(note: str | None) -> dict:
    """Instant, dependency-free label. Errs towards 'urgent' (a false alarm only shows hotlines)."""
    t = (note or "").lower()
    if any(w in t for w in URGENT_WORDS):
        return {"category": "emergency", "urgent": True, "by": "rules"}
    if any(re.search(p, t) for p in SPAM_PATTERNS):
        return {"category": "spam", "urgent": False, "by": "rules"}
    return {"category": "info", "urgent": False, "by": "rules"}


def parse_label(text: str) -> dict | None:
    """Accept only a JSON object with a known category and a boolean `urgent` (models wrap it in ``` fences)."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except ValueError:
        return None
    if d.get("category") not in CATEGORIES or not isinstance(d.get("urgent"), bool):
        return None
    return {"category": d["category"], "urgent": d["urgent"]}


def _provider() -> str:
    p = os.environ.get("AI_PROVIDER", "").strip().lower()
    if p in ("glm", "zhipu"):
        return "glm"
    if p == "cloudflare":
        return "cloudflare"
    if os.environ.get("GLM_API_KEY", "").strip():
        return "glm"
    return "cloudflare"


def _credentials() -> dict | None:
    if os.environ.get("AI_ENABLED", "1") != "1":
        return None
    p = _provider()
    if p == "glm":
        key = os.environ.get("GLM_API_KEY", "").strip()
        if not key:
            return None
        return {
            "provider": "glm",
            "api_key": key,
            "model": os.environ.get("GLM_MODEL", "glm-5.3-flash").strip() or "glm-5.3-flash",
            "endpoint": os.environ.get("GLM_ENDPOINT", "https://open.bigmodel.cn/api/paas/v4/chat/completions").strip(),
        }
    acct = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    tok = os.environ.get("CF_AI_TOKEN", "").strip()
    if not acct or not tok:
        return None
    return {
        "provider": "cloudflare",
        "account_id": acct,
        "token": tok,
        "model": os.environ.get("AI_MODEL", MODEL),
    }


def _state(c) -> dict:
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    st = db.get_state(c, "ai_usage") or {}
    if st.get("day") != today:
        st = {"day": today, "neurons": 0.0, "calls": 0, "failures": 0, "paused_until": st.get("paused_until")}
    return st


def available() -> bool:
    cred = _credentials()
    if cred is None:
        return False
    with db.connect() as c:
        st = _state(c)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    if st.get("paused_until") and st["paused_until"] > now:
        return False
    if cred["provider"] == "cloudflare" and st["neurons"] >= BUDGET:
        return False
    return True


def _glm_payload(model: str, messages: list[dict], max_tokens: int) -> dict:
    """glm-5.3-flash always reasons (API 1210: it cannot be switched off); "low" effort answers in ~1-4 s instead of
    9-10 s and leaves the token budget to the answer (probe 2026-10-02)."""
    return {"model": model, "messages": messages, "max_tokens": max(max_tokens, 500), "temperature": 0.1,
            "reasoning_effort": "low"}


def _glm_text(d: dict) -> str | None:
    """The answer only. A cut-off answer has empty content and only `reasoning_content` ("The user wants me to …"):
    that is not an answer and is never returned as one."""
    try:
        text = (d["choices"][0]["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
    return text or None


def run(messages: list[dict], max_tokens: int = 60, timeout: float = 25) -> str | None:
    """One AI triage call (GLM or Cloudflare Workers AI) with error handling. Returns None on any problem; never raises."""
    cred = _credentials()
    if cred is None or not available():
        return None
    ok, text, neurons, err = False, None, 0.0, ""
    try:
        if cred["provider"] == "glm":
            r = requests.post(
                cred["endpoint"],
                headers={"Authorization": f"Bearer {cred['api_key']}", "Content-Type": "application/json"},
                timeout=timeout,
                json=_glm_payload(cred["model"], messages, max_tokens),
            )
            d = r.json()
            text = _glm_text(d) if r.ok else None
            if text is not None:
                ok = True
            else:
                err = (json.dumps(d.get("error")) if "error" in d else "no answer (empty content)")[:200]
        else:
            acct, tok, model = cred["account_id"], cred["token"], cred["model"]
            r = requests.post(
                f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}",
                headers={"Authorization": f"Bearer {tok}"},
                timeout=20,
                json={"messages": messages, "max_tokens": max_tokens, "temperature": 0.1},
            )
            d = r.json()
            if r.ok and d.get("success"):
                res = d["result"]
                text = res.get("response") or res["choices"][0]["message"]["content"]
                neurons = float((res.get("usage") or {}).get("neurons") or 0)
                ok = True
            else:
                err = json.dumps(d.get("errors"))[:200]
    except Exception as e:  # network, JSON, schema
        err = f"{type(e).__name__}: {e}"[:200]
    with db.connect() as c:
        st = _state(c)
        st["calls"] += 1
        st["neurons"] += neurons
        if ok:
            st["failures"] = 0
        else:
            st["failures"] += 1
            now = dt.datetime.now(dt.timezone.utc)
            if "3036" in err:  # daily free allocation used: wait for the 00:00 UTC reset
                st["paused_until"] = (now + dt.timedelta(days=1)).replace(hour=0, minute=5, second=0).isoformat()
            elif st["failures"] >= 3:
                st["paused_until"] = (now + dt.timedelta(hours=1)).isoformat()
            log.warning("ai triage failed (%s)", err)
        db.set_state(c, "ai_usage", st)
        c.commit()
    return text


def triage_pending(limit: int = 20) -> int:
    """Refine rule labels of new feedback notes with AI (background task). Returns how many were labelled."""
    cred = _credentials()
    model_tag = cred["model"] if cred else MODEL
    with db.connect() as c:
        rows = c.execute("""SELECT id, note FROM user_feedback WHERE note IS NOT NULL AND ai_label IS NULL
                            ORDER BY id LIMIT %s""", (limit,)).fetchall()
    n = 0
    for r in rows:
        text = run([{"role": "system", "content": TRIAGE_PROMPT}, {"role": "user", "content": r["note"]}])
        if text is None:
            break  # unavailable, over budget or paused: rules labels stay; try again next run
        label = parse_label(text)
        rules = triage_rules(r["note"])
        if label is None:
            label = {"category": "unparsed", "urgent": rules["urgent"]}
        label["urgent"] = label["urgent"] or rules["urgent"]  # AI may add urgency, never remove it
        label.update(by=model_tag, at=dt.datetime.now(dt.timezone.utc).isoformat())
        with db.connect() as c:
            c.execute("UPDATE user_feedback SET ai_label=%s WHERE id=%s", (db.Jsonb(label), r["id"]))
            c.commit()
        n += 1
    return n


def summary_text(stats: dict) -> str:
    """Deterministic Thai situation sentence from /api/stats. Deliberately NOT AI-written (D-022)."""
    f = stats["focus"]
    s = f["status"]
    parts = [f"จาก {f['total']} สถานีที่ติดตาม ล้นตลิ่ง {s['critical']} · ใกล้ตลิ่งหรือคลองเต็ม {s['warning']} · เฝ้าระวัง {s['watch']}"
             f" · ยังรับน้ำได้ {s['normal']} · ไม่ทราบ {s['unknown']} สถานี"]
    t = f["trend12"]
    parts.append(f"ในอีก 12 ชม. มีแนวโน้มเพิ่มขึ้น {t['rising']} สถานี ลดลง {t['falling']} สถานี")
    rain = stats.get("rain_bkk_next24_mm_max")
    if rain is not None:
        parts.append(f"คาดฝนในกรุงเทพฯ ในอีก 24 ชม. สูงสุดราว {round(rain)} มม. (Open-Meteo)")
    return " · ".join(parts)
