"""The river below Kaeng Krachan, two more years (owner 2026-10-06: "Continue all you suggested … less errors"): HII's
waterlevel_graph serves older years when start and end are both in the past (checked 2026-10-06: B.18, B.16, B.15 from
2023-09-30). Hourly level and discharge for the five case points, 2023-09-30 … 2025-09-29, month by month (PCH001 posts
every 10 min and a year times out), paced 2 s, cached as raw JSON. Run: docker compose run --rm --no-deps -T -e
PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$CACHE:/cache" worker python - < research/2026-10-06_kk_river_history.py"""
import datetime as dt, json, os, time, urllib.request
from floodwatch import db
from floodwatch.config import settings

HII = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public"
OUT = "/cache/kk_river"
os.makedirs(OUT, exist_ok=True)
with db.connect_readonly() as c:
    rows = [dict(r) for r in c.execute("SELECT code, hii_id FROM station WHERE code = ANY(%s)", (["B.18", "B.10", "B.16", "B.15", "PCH001"],)).fetchall()]
print("stations:", rows, flush=True)
start = dt.date(2023, 9, 30)
for r in rows:
    if not r["hii_id"]:
        print(r["code"], "has no HII id", flush=True); continue
    path = f"{OUT}/{r['code']}.json"
    have = json.load(open(path)) if os.path.exists(path) else {}
    a = start
    while a < dt.date(2025, 9, 30):
        b = min(dt.date(a.year + (a.month == 12), a.month % 12 + 1, 1) - dt.timedelta(days=1), dt.date(2025, 9, 29))
        key = a.isoformat()
        if key not in have:
            url = (f"{HII}/waterlevel_graph?station_type=tele_waterlevel&station_id={r['hii_id']}&start_date={a.isoformat()}"
                   f"&end_date={b.isoformat()}%2023:59")
            for k in range(4):
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": settings.user_agent}), timeout=120) as resp:
                        g = (json.loads(resp.read()).get("data") or {}).get("graph_data") or []
                    have[key] = [[x.get("datetime"), x.get("value"), x.get("discharge")] for x in g]
                    break
                except Exception as e:
                    if k == 3:
                        print(r["code"], key, "failed", type(e).__name__, flush=True)
                    time.sleep(10 * (k + 1))
            json.dump(have, open(path, "w"))
            time.sleep(2.0)
        a = b + dt.timedelta(days=1)
    n = sum(len(v) for v in have.values())
    print(r["code"], "months", len(have), "points", n, flush=True)
print("DONE", flush=True)
