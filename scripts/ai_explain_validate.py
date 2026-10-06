#!/usr/bin/env python3
"""Validate the resident questions (D-068) on real places: for each pin and question, the plain line, the rule lines,
GLM's short sentence (gist), the checker's verdict, the time taken. Run inside the app container (same GLM settings and code as production):

    docker compose run --rm --no-deps -v "$PWD/scripts:/s:ro" app python /s/ai_explain_validate.py [n_pins=30] > out.json

Pins: gauges' positions moved ~1 km (a place, not a gauge), half in the Bangkok area, half elsewhere, plus the
owner's pins of 2026-10-02. Prints one JSON object (per-answer rows + summary) for review. Calls GLM directly with
explain.SYSTEM and explain.check, without the cache, so every gist is a fresh sample.
"""
import json
import random
import statistics
import sys
import time
import urllib.request

from floodwatch import ai, explain

BASE = "http://app:3000"  # the live app service
OWNER_PINS = [(13.7688, 100.5374), (13.7551, 100.6679), (13.9130, 100.4980)]


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.load(r)


def main(n: int):
    st = [s for s in get("/api/stations")["stations"] if s.get("lat") and not s.get("stale")]
    rnd = random.Random(2)
    bkk = [s for s in st if s.get("in_focus")]
    other = [s for s in st if not s.get("in_focus")]
    pick = rnd.sample(bkk, min(n // 2, len(bkk))) + rnd.sample(other, min(n - n // 2, len(other)))
    pins = OWNER_PINS + [(round(s["lat"] + rnd.uniform(-0.009, 0.009), 4), round(s["lon"] + rnd.uniform(-0.009, 0.009), 4))
                         for s in pick]
    rows = []
    for la, lo in pins:
        out = get(f"/api/point?lat={la}&lon={lo}")
        for q in explain.RESIDENT_Q:
            lines, story = explain.answer(q, out), explain.narrative(q, out)
            messages, rule = explain.prompt(q, lines, story)  # exactly what the app sends
            t0 = time.time()
            text = ai.run(messages, max_tokens=400, timeout=20)
            sec = round(time.time() - t0, 1)
            issues = explain.check(text or "", rule) if text else ["no answer"]
            rows.append({"pin": [la, lo], "mode": out.get("mode"), "title": out["forecast"].get("title"),
                         "plain": out["forecast"].get("plain"), "q": q, "story": story, "lines": lines, "ai": text, "sec": sec, "issues": issues})
            print(f"{la},{lo} {q:<8} {sec:>5}s {'OK' if not issues else issues}", file=sys.stderr, flush=True)
    secs = [r["sec"] for r in rows if r["ai"]]
    summ = {"pins": len(pins), "answers": len(rows), "ai_answered": len(secs),
            "passed_check": sum(1 for r in rows if not r["issues"]),
            "median_s": statistics.median(secs) if secs else None,
            "p90_s": sorted(secs)[int(0.9 * len(secs))] if secs else None,
            "within_8s": sum(1 for s in secs if s <= 8),
            "issues": {}, "pass_by_q": {}}
    for r in rows:
        for i in r["issues"]:
            k = i.split(" '")[0]
            summ["issues"][k] = summ["issues"].get(k, 0) + 1
        d = summ["pass_by_q"].setdefault(r["q"], [0, 0])
        d[0] += not r["issues"]
        d[1] += 1
    print(json.dumps({"summary": summ, "rows": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
