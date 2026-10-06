"""E-7D-IN-LONG, the data (owner 2026-10-06: "Continue all you suggested … best performance / less errors at the end"):
the archived rain forecasts (Open-Meteo previous runs) reach back to 2024-01 at leads 1–7 (checked 2026-10-06 05:40 UTC:
best_match and GFS from 2024-01-19, ECMWF IFS 0.25° from 2024-02-04; ICON leads ≤ 6), not only the 92 days E-7D-IN used.
This fetches the 2025 wet season (May–Nov) for best_match, ECMWF and GFS at each RID dam's three catchment points (the
points of research/2026-10-05_e7d_inflow.py's cache), daily sums per lead (a day counts with ≥ 20 hourly values), area-
weighted. Paced: one request every 8 s after the first 20 dams at 20 s (a 214-day, 8-variable request bills ≈ 12 calls; ≤ 2,400 an hour, under the
free tier's 5,000 an hour and leaving the live site's ≈ 3,000 a day room within 10,000). Cache-only output, resumable.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" -v "$CACHE:/cache" worker \
       python - < research/2026-10-06_e7d_long_fetch.py"""
import json, os, time, urllib.request

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"
SRC, OUT = "/cache/e7d_in", "/cache/e7d_in_long"
os.makedirs(OUT, exist_ok=True)
MODELS = ["best_match", "ecmwf_ifs025", "gfs_seamless"]
LEADS = list(range(1, 8))
START, END = "2025-05-01", "2025-11-30"
PAUSE = 8.0


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(30 * (k + 1))


files = sorted(f for f in os.listdir(SRC) if f.startswith("dam_"))
print(f"dams in the 92-day cache: {len(files)}; fetching {START}…{END} for {MODELS}", flush=True)
calls = 0
for f in files:
    out_path = f"{OUT}/{f}"
    if os.path.exists(out_path):
        continue
    src = json.load(open(f"{SRC}/{f}"))
    pts = src["pts"]  # [[[lat, lon], area], …]
    days, fcp = None, {m: [] for m in MODELS}
    for (lat, lon), a in pts:
        for m in MODELS:
            hv = ",".join(["precipitation"] + [f"precipitation_previous_day{n}" for n in LEADS])
            h = get(f"https://previous-runs-api.open-meteo.com/v1/forecast?latitude={lat:.3f}&longitude={lon:.3f}&hourly={hv}"
                    f"&start_date={START}&end_date={END}&timezone=Asia%2FBangkok&models={m}")["hourly"]
            calls += 1
            dd = sorted({t[:10] for t in h["time"]})
            days = days or dd
            idx = {x: i for i, x in enumerate(days)}
            per = {}
            for n in [0] + LEADS:
                key = "precipitation" if n == 0 else f"precipitation_previous_day{n}"
                tot, cnt = [0.0] * len(days), [0] * len(days)
                for t, v in zip(h["time"], h.get(key) or []):
                    if v is not None and t[:10] in idx:
                        tot[idx[t[:10]]] += v; cnt[idx[t[:10]]] += 1
                per[str(n)] = [tot[i] if cnt[i] >= 20 else None for i in range(len(days))]
            fcp[m].append((a, per))
            time.sleep(PAUSE)
    fc = {}
    for m in MODELS:
        fc[m] = {}
        for n in [0] + LEADS:
            vals = []
            for i in range(len(days)):
                num = den = 0.0
                for a, per in fcp[m]:
                    if per[str(n)][i] is not None:
                        num += per[str(n)][i] * a; den += a
                vals.append(num / den if den > 0 else None)
            fc[m][str(n)] = vals
    json.dump({"days": days, "fc": fc}, open(out_path, "w"))
    print(f"{f}: {len(days)} days, {calls} requests so far", flush=True)
print("DONE", calls, "requests", flush=True)
