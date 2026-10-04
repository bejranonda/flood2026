"""Which model writes the most natural Thai ticker? (owner 2026-10-04: "simple, attractive and lovely Thai … natural smooth
language … Test and validate the suggestion"). Same live facts and the item prompt (situation.prompt) for every model;
each answer is parsed (situation.parse_items) and checked per item (situation.check_items) on the first try.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-04_ticker_models.py"""
import json, os, statistics as S, time
import datetime as dt
import requests
from floodwatch import ai, db, situation

get = lambda p: requests.get(f"http://app:3000{p}", timeout=60).json()
with db.connect() as c:
    flows = situation.flows_now(c)
    hist = db.get_state(c, "situation_history") or []
f = situation.facts(get("/api/stations")["stations"], get("/api/risks"), get("/api/rain").get("by_region") or {},
                    flows=flows, prev=situation.yesterday(hist, dt.datetime.now(dt.timezone.utc)))
rule = situation.items(f)
print("FACTS (numbered as the model sees them):")
for k, i in enumerate(rule, 1):
    print(f"  {k}) {i['icon']} {i['text']}")
CONFIGS = [("glm", "glm-5.3-flash"), ("cloudflare", "@cf/aisingapore/gemma-sea-lion-v4-27b-it"),
           ("cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"), ("cloudflare", "@cf/google/gemma-3-12b-it")]
RUNS = 4
summary = {}
for prov, model in CONFIGS:
    os.environ["AI_PROVIDER"] = prov
    os.environ["GLM_MODEL" if prov == "glm" else "AI_MODEL"] = model
    res = []
    for r in range(RUNS):
        t0 = time.time()
        try:
            text = ai.run(situation.prompt(f), max_tokens=700, timeout=40)
        except Exception as e:
            text = None
        dt_s = time.time() - t0
        got = situation.parse_items(text, rule)
        issues = situation.check_items(got, rule)
        res.append({"ok": not issues, "issues": issues, "n": len(got), "len": [len(g["text"]) for g in got], "s": round(dt_s, 1),
                    "items": [f"{g['n']}) {g['text']}" for g in got], "raw": None if got else (text or "")[:300]})
    summary[model] = {"pass": sum(x["ok"] for x in res), "runs": RUNS, "items_avg": round(S.mean(x["n"] for x in res), 1),
                      "item_len_avg": round(S.mean([l for x in res for l in x["len"]] or [0])), "sec_avg": round(S.mean(x["s"] for x in res), 1)}
    print(f"\n##### {model}: {summary[model]}")
    for k, x in enumerate(res, 1):
        print(f"-- run {k}: {'PASS' if x['ok'] else 'FAIL ' + '; '.join(x['issues'])} ({x['s']} s)")
        for it in x["items"]:
            print("   ", it)
        if x["raw"] is not None:
            print("    raw:", x["raw"].replace(chr(10), " / "))
print("\nSUMMARY", json.dumps(summary, ensure_ascii=False))
