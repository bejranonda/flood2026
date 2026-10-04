"""Validate the two new ✨ summaries (owner 2026-10-04: "Test and validate the suggestion … Validate the outcome, also the
consistency to the current app"). For every จับตา region and a spread of stations (over the bank, near it, below it, BMA,
stale), the rule story and lines come from the live API; GLM retells them through the same loop as explain.gist
(up to 3 tries, explain.check) but with account=False (research never touches the visitors' AI budget or breaker).
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-04_ai_summaries_validate.py"""
import collections as C, time
import requests
from floodwatch import ai, explain

API = "http://app:3000"
get = lambda p: requests.get(API + p, timeout=60).json()


def retell(d):
    msgs, rule = explain.prompt("simple", d["lines"], d["story"])
    tries, issues = 0, []
    for _ in range(3):
        tries += 1
        t = ai.run(msgs, max_tokens=400, timeout=15, account=False)
        if not t:
            issues.append("no answer")
            break
        t = explain.tidy(t)  # as explain.gist (run 2)
        iss = explain.check(t, rule)
        if not iss:
            return t.strip(), tries, issues
        issues += iss
    return None, tries, issues


stations = get("/api/stations")["stations"]
pick, seen = [], set()
want = [("critical", "rising"), ("critical", "flat_or_falling"), ("warning", None), ("watch", None), ("normal", None)]
for status, grp in want:
    for agency in ("RID", "HII", "BMA"):
        for s in stations:
            if s["status"] == status and s.get("agency") == agency and not s["stale"] and s["code"] not in seen and \
                    (grp is None or (s.get("trend") or {}).get("group") == grp):
                pick.append(s["code"]); seen.add(s["code"]); break
stale = next((s["code"] for s in stations if s["stale"] and s["status"] != "unknown"), None)
pick = pick[:12] + ([stale] if stale else [])
cases = [("watch " + r, f"/api/explain_watch?region={r}&prov=&q=simple") for r in
         ("all", "bkk", "metro", "up", "north", "northeast", "east", "west", "south")]
cases += [("station " + c, f"/api/explain_station?code={c}&q=simple") for c in pick]
tot, why = C.Counter(), C.Counter()
for name, path in cases:
    d = get(path)
    t0 = time.time()
    text, tries, issues = retell(d)
    kind = name.split()[0]
    tot[kind + "_n"] += 1
    tot[kind + "_ok"] += text is not None
    tot[kind + "_tries"] += tries
    why.update(i for i in issues)
    print(f"\n=== {name} ({tries} tr, {time.time() - t0:.1f} s) {'PASS' if text else 'FAIL'} {issues}")
    print("STORY:", d["story"])
    print("GIST: ", text)
for k in ("watch", "station"):
    print(f"\n{k}: retelling shown {tot[k + '_ok']}/{tot[k + '_n']}, tries per summary {tot[k + '_tries'] / max(1, tot[k + '_n']):.1f}")
print("rejections:", dict(why))
