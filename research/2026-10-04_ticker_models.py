"""Which model writes the most natural Thai ticker? (owner 2026-10-04: "simple, attractive and lovely Thai … natural smooth
language … Test and validate the suggestion"). Same live facts and the item prompt (situation.prompt) for every model;
each answer is parsed (situation.parse_items) and checked per item (situation.check_items) on the first try.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-04_ticker_models.py"""
import json, os, statistics as S, time
import datetime as dt
import requests
from floodwatch import ai, db, situation

get = lambda p: requests.get(f"http://app:3000{p}", timeout=60).json()
with db.connect_readonly() as c:
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
CONFIGS = [c for c in CONFIGS if "gemma-3" not in c[1]]  # not available on this account (error 5018, run 1)
import sys
if len(sys.argv) > 1 and sys.argv[1] == "glm":  # run 4: the owner keeps GLM only ("You can use only GLM")
    CONFIGS, RUNS = [("glm", "glm-5.3-flash")], 6
for prov, model in CONFIGS:
    res = []
    for r in range(RUNS):
        t0 = time.time()
        try:  # account=False: research never touches the visitors' AI budget or breaker (run 1 paused it for an hour)
            text = ai.run(situation.prompt(f), max_tokens=1600, timeout=60, provider=prov, model=model, account=False)
        except Exception as e:
            text = None
        dt_s = time.time() - t0
        got = situation.parse_items(text, rule)
        per = [(g, situation.check_item(g, rule)) for g in got]  # item by item, as compose() decides
        issues = [x for _, iss in per for x in iss]
        res.append({"ok": not issues, "issues": issues, "n": len(got), "acc": sum(1 for _, iss in per if not iss),
                    "len": [len(g["text"]) for g in got], "s": round(dt_s, 1),
                    "items": [f"{'✓' if not iss else '✗'} {g['n']}) {g['text']}" for g, iss in per], "raw": None if got else (text or "")[:300]})
    summary[model] = {"items_accepted_avg": round(S.mean(x["acc"] for x in res), 1), "of": len(rule), "runs": RUNS,
                      "item_len_avg": round(S.mean([l for x in res for l in x["len"]] or [0])), "sec_avg": round(S.mean(x["s"] for x in res), 1)}
    print(f"\n##### {model}: {summary[model]}")
    for k, x in enumerate(res, 1):
        print(f"-- run {k}: {x['acc']}/{len(rule)} items accepted ({x['s']} s){'' if x['ok'] else ' — ' + '; '.join(x['issues'])}")
        for it in x["items"]:
            print("   ", it)
        if x["raw"] is not None:
            print("    raw:", x["raw"].replace(chr(10), " / "))
print("\nSUMMARY", json.dumps(summary, ensure_ascii=False))
