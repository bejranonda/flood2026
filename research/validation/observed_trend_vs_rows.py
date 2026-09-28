"""Proof for the owner's question (2026-09-28): gauges whose recent observations fall (or rise) steadily while the UI
says "? ไม่แน่ชัด" / "ทรงตัว" / "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า". Reads the live API only."""
import json, math, sys, urllib.request, datetime as dt

BASE = "https://flood.autobahn.bot"
get = lambda p: json.load(urllib.request.urlopen(BASE + p, timeout=60))
st = get("/api/stations")
st = st["stations"] if isinstance(st, dict) else st
print("stations", len(st))

def fit(pts, hours):
    """Least-squares slope (m/h) and R² over the last `hours` of (datetime, level)."""
    if not pts: return None
    end = pts[-1][0]
    w = [(((t - end).total_seconds() / 3600), v) for t, v in pts if (end - t).total_seconds() <= hours * 3600]
    if len(w) < max(6, hours // 3) or (w[-1][0] - w[0][0]) < hours * 0.7: return None
    n = len(w); mx = sum(x for x, _ in w) / n; my = sum(y for _, y in w) / n
    sxx = sum((x - mx) ** 2 for x, _ in w); sxy = sum((x - mx) * (y - my) for x, y in w)
    if sxx == 0: return None
    b = sxy / sxx; ss = sum((y - my) ** 2 for _, y in w); res = sum((y - (my + b * (x - mx))) ** 2 for x, y in w)
    return b, (1 - res / ss) if ss > 0 else 0.0

rows = []
cand = [s for s in st if s.get("change24") and s.get("level_msl") is not None and "erratic" not in (s.get("notes") or [])]
for s in cand:
    d = get(f"/api/stations/{s['code']}?days=3")
    pts = [(dt.datetime.fromisoformat(t), v) for t, v, _ in d["observations"] if v is not None]
    f24, f48 = fit(pts, 24), fit(pts, 48)
    fc = d.get("forecast") or {}
    sk = {h: (fc.get("skill") or {}).get(h) or {} for h in ("12", "24")}
    rows.append({"code": s["code"], "agency": s.get("agency"), "status": s["status"],
                 "s24": f24, "s48": f48, "c12": s.get("change12"), "c24": s.get("change24"),
                 "rec": (s.get("recovery") or {}).get("state"),
                 "rmse24": sk["24"].get("rmse"), "rmse12": sk["12"].get("rmse")})

def ui24(r):
    c = r["c24"]; return c["level"] if c["method"] != "persistence" else "?"
# a clear observed trend: 24 h linear change >= 5 cm with R² >= 0.7 (and the 48 h fit agrees in sign)
clear = [r for r in rows if r["s24"] and abs(r["s24"][0] * 24) >= 0.05 and r["s24"][1] >= 0.7
         and (r["s48"] is None or r["s48"][0] * r["s24"][0] > 0)]
print(f"gauges with 24 h rows: {len(rows)} | clear observed trend over 24 h (>=5 cm, R²>=0.7): {len(clear)}")
fall = [r for r in clear if r["s24"][0] < 0]; rise = [r for r in clear if r["s24"][0] > 0]
for name, grp, want in (("FALLING", fall, "fall"), ("RISING", rise, "rise")):
    miss = [r for r in grp if not ui24(r).endswith(want)]
    print(f"\n{name}: {len(grp)} gauges; the 24 h row does NOT say {want}: {len(miss)}")
    why = {}
    for r in miss:
        k = "no model beat 'no change' (persistence -> ?)" if r["c24"]["method"] == "persistence" else f"model {r['c24']['method']} says {r['c24']['level']}"
        why[k] = why.get(k, 0) + 1
    for k, v in why.items(): print("   ", v, k)
    for r in sorted(miss, key=lambda r: r["s24"][0])[:40]:
        rm = r["rmse24"] or {}; tt = rm.get("tide_trend", rm.get("trend")); p = rm.get("persistence")
        print(f"   {r['code']:10} {str(r['agency'])[:4]:4} {r['status']:8} obs24 {r['s24'][0]*24*100:+5.0f} cm (R² {r['s24'][1]:.2f})"
              f" obs48 {'' if not r['s48'] else f'{r['s48'][0]*48*100:+5.0f}'} | row24 {ui24(r):12} med {r['c24']['median']*100:+4.0f}"
              f" | rmse24 persist {p if p is None else round(p,3)} trend {tt if tt is None else round(tt,3)} | recovery {r['rec']}")
# the sentence "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า": shown when change24.dir != falling and status watch+
nofall = [r for r in rows if r["c24"]["dir"] != "falling" and r["status"] in ("watch", "warning", "critical")]
nofall_p = [r for r in nofall if r["c24"]["method"] == "persistence"]
nofall_obs = [r for r in nofall if r in fall]
print(f"\n'ยังไม่เห็นแนวโน้มลดลง…' shown at {len(nofall)} gauges; from the no-change model: {len(nofall_p)};"
      f" while the gauge has fallen clearly for 24 h: {len(nofall_obs)}")
json.dump([{**r, "s24": r["s24"], "s48": r["s48"]} for r in rows], open(sys.argv[1], "w"), default=str)
