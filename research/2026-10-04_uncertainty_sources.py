"""Where does the "?" come from? (owner 2026-10-04: "we have to try to reduce the uncertainty of prediction instead").
Latest run per fresh gauge: served method per horizon, the best candidate's skill when persistence is served, history
length, star availability, and the 50 % band width. Read-only.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - < research/2026-10-04_uncertainty_sources.py"""
import collections as C, statistics as S
from floodwatch import db
with db.connect() as c:
    rows = c.execute("""SELECT DISTINCT ON (f.code) f.code, f.payload, s.agency FROM forecast_run f JOIN station s USING (code)
                        WHERE f.issue_time > now() - interval '3 hours' ORDER BY f.code, f.issue_time DESC""").fetchall()
print("gauges with a fresh run:", len(rows))
for h in ("24", "48", "72"):
    served, why, width, gap = C.Counter(), C.Counter(), C.defaultdict(list), C.Counter()
    for r in rows:
        p = r["payload"]; sk = (p.get("skill") or {}).get(h)
        hist = p.get("history_hours") or 0
        if not sk:
            served["no backtest"] += 1; why["history < backtest minimum" if hist < 24 * 14 else "no backtest (other)"] += 1; continue
        m = sk["method"]; served[m] += 1
        q = (p["path"][int(h) - 1] or {}).get("q")
        if q: width[m].append((q[3] - q[1]) * 100)
        if m == "persistence":
            rm = sk.get("rmse") or {}
            best = min((k for k in rm if k != "persistence"), key=lambda k: rm[k], default=None)
            s = 1 - rm[best] / rm["persistence"] if best and rm.get("persistence") else None
            why["no candidate" if s is None else "best is worse than no change" if s <= 0 else "best gains 0–5 %" if s <= 0.05 else "best gains 5–10 % (below gate)"] += 1
            if s is not None and 0 < s <= 0.10: gap[best] += 1
            if "star" not in rm: why["  · star not available"] += 1
    print(f"\n=== +{h} h · served: {dict(served)}")
    print("   why 'no change' is served:", dict(why))
    print("   near-miss candidates (gain 0–10 %):", dict(gap))
    print("   50 % band width median (cm):", {m: round(S.median(v)) for m, v in width.items() if v})
ag = C.Counter((r["agency"], (r["payload"].get("skill") or {}).get("24", {}).get("method", "none") == "persistence") for r in rows)
print("\nby agency (no-change at 24 h / all):", {a: f"{ag[(a, True)]}/{ag[(a, True)] + ag[(a, False)]}" for a in sorted({k[0] for k in ag})})
