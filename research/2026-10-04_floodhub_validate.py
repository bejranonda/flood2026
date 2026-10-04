"""Google Flood Hub vs our gauges (D-087). Run: docker compose exec -T worker python - < research/2026-10-04_floodhub_validate.py
For each Flood Hub virtual gauge: our gauges within 15 km (no BMA), their worst status and trend group now; and how
Google's latest severity lines up. Re-run after 1-2 weeks of `gfh_status` history before showing anything."""
import collections as C, json, math, urllib.request
from floodwatch import db
with db.connect() as c:
    gg = c.execute("""SELECT g.gauge_id, g.lat, g.lon, g.warning, g.danger, s.severity, s.trend, s.issued_time
                      FROM gfh_gauge g JOIN LATERAL (SELECT * FROM gfh_status WHERE gauge_id=g.gauge_id ORDER BY issued_time DESC LIMIT 1) s ON true""").fetchall()
    fc = c.execute("""SELECT gauge_id, max(start_time) - min(start_time) AS span, count(DISTINCT issued_time) AS issues FROM gfh_forecast GROUP BY 1""").fetchall()
st = json.load(urllib.request.urlopen("http://app:3000/api/stations"))["stations"]
RANK = {"critical": 3, "warning": 2, "watch": 1, "normal": 0}
km = lambda a, b, c, d: 111.2 * math.hypot(a - c, (b - d) * math.cos(math.radians(a)))
tab, near_n = C.Counter(), []
for g in gg:
    near = [s for s in st if s["lat"] and s["agency"] != "BMA" and not s["stale"] and s["status"] in RANK and km(g["lat"], g["lon"], s["lat"], s["lon"]) <= 15]
    near_n.append(len(near))
    worst = max((RANK[s["status"]] for s in near), default=None)
    word = {None: "no gauge ≤15 km", 3: "over bank", 2: "near bank", 1: "watch", 0: "below"}[worst]
    tab[(g["severity"], word)] += 1
    if g["severity"] != "NO_FLOODING":
        print(g["gauge_id"], g["severity"], g["trend"], round(g["lat"], 3), round(g["lon"], 3), "→ ours:",
              [(s["code"], s["status"], (s.get("trend") or {}).get("group"), round(km(g["lat"], g["lon"], s["lat"], s["lon"]), 1)) for s in near][:5])
print("Google severity × our worst gauge within 15 km:")
for k, v in sorted(tab.items()): print("  ", k, v)
print("Flood Hub points with ≥ 1 of our gauges within 15 km:", sum(1 for n in near_n if n), "of", len(near_n))
print("forecast span per gauge (days):", C.Counter(round(r["span"].total_seconds() / 86400) for r in fc).most_common(3))
