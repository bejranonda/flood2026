"""Q52 experiment E-GFH: Google Flood Hub forecasts as a star input (owner 2026-10-04: "You can use the data mixing data
across various sources and models … Google flood hub is already there"). The Flood Hub API serves a year of daily issued
forecasts per gauge (probe 2026-10-04: 366 forecasts back to 2025-10-05), so the test is honest:
- our gauges within 10 km of a Flood Hub gauge (non-BMA, fresh) get that gauge (nearest), pre-declared;
- at each issue hour only the latest Flood Hub forecast issued at or before that hour is used;
- the input is the forecast's relative discharge change from the issue day to the target day: log((q_v + 1) / (q_0 + 1));
- star trained before the backtest window; method + 10 % gate chosen on the first half, scored on the second (q52_harness).
Caveat: if Google re-issued its archive with a newer model, past forecasts may be better than they were live.
The key travels only in the X-Goog-Api-Key header; responses are kept in memory, never archived, shown or served.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker python - < research/2026-10-04_floodhub_input.py"""
import datetime as dt, json, math, urllib.parse
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F
from floodwatch.collectors import GFH
from floodwatch.config import settings
from floodwatch.httpclient import fetch

MAX_KM = 10.0


def km(a, b):
    p = math.pi / 180
    h = math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def gfh_year(gid):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=366)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"{GFH}/gauges:queryGaugeForecasts?" + urllib.parse.urlencode([("gaugeIds", gid), ("issuedTimeStart", since)])
    r = fetch(url, headers={"X-Goog-Api-Key": settings.google_flood_api_key}, retries=2)
    if r.status != 200:
        return []
    out = []
    for f in (json.loads(r.body).get("forecasts") or {}).get(gid, {}).get("forecasts") or []:
        it = dt.datetime.fromisoformat(f["issuedTime"].replace("Z", "+00:00")).timestamp() / 3600
        days = {}
        for rg in f.get("forecastRanges") or []:
            if rg.get("value") is not None:
                d0 = dt.datetime.fromisoformat(rg["forecastStartTime"].replace("Z", "+00:00")).timestamp() / 3600
                days[int(d0 // 24)] = float(rg["value"])
        if days:
            out.append((it, days))
    return sorted(out)


def gfh_feature(t, fcs, h):
    """At each hour t[i]: the latest forecast issued <= t[i]; log((q(day of t+h) + 1) / (q(day of t) + 1))."""
    out = np.full(len(t), np.nan)
    issued = [x[0] for x in fcs]
    j = -1
    for i, ti in enumerate(t):
        while j + 1 < len(issued) and issued[j + 1] <= ti:
            j += 1
        if j < 0:
            continue
        days = fcs[j][1]
        d0, d1 = int(ti // 24), int((ti + h) // 24)
        if d0 in days and d1 in days:
            out[i] = math.log((days[d1] + 1) / (days[d0] + 1))
    return out


sc = H.Score()
with db.connect_readonly() as c:
    gg = [(r["gauge_id"], r["lat"], r["lon"]) for r in c.execute("SELECT gauge_id, lat, lon FROM gfh_gauge WHERE lat IS NOT NULL")]
    ours = c.execute("""SELECT DISTINCT s.code, s.lat, s.lon, s.in_focus FROM station s JOIN forecast_run f USING (code)
                        WHERE f.issue_time > now() - interval '3 hours' AND s.lat IS NOT NULL
                          AND s.agency IS DISTINCT FROM 'BMA'""").fetchall()
    pairs = []
    for s in ours:
        best = min(((km((s["lat"], s["lon"]), (g[1], g[2])), g[0]) for g in gg), default=None)
        if best and best[0] <= MAX_KM:
            pairs.append((s, best[1], best[0]))
    print(f"our gauges within {MAX_KM} km of a Flood Hub gauge: {len(pairs)} (Flood Hub gauges {len(gg)})", flush=True)
    year, cache, done = {}, {}, 0
    for s, gid, d in pairs:
        if gid not in year:
            year[gid] = gfh_year(gid)
        fcs = year[gid]
        if len(fcs) < 60:
            continue
        t, y = H.load_series(c, s["code"])
        if len(y) < 24 * 60:
            continue
        exo = F.load_exo(c, s["code"], s["lat"], s["lon"], cache, s["in_focus"])
        if not exo:
            continue
        ex = F.align_exo(t, exo)
        own, split = F._backtest_errors(t, y, None)
        feat = {h: gfh_feature(t, fcs, h) for h in F.HORIZONS}
        plus = lambda t_, yf, eta, ybf, h, ex_: np.column_stack([F.star_features(t_, yf, eta, ybf, h, ex_), feat[h]])
        sc.add("star (today, V12)", own, H.star_errs(t, y, ex, own, split))
        sc.add("star + Flood Hub", own, H.star_errs(t, y, ex, own, split, feats=plus))
        done += 1
        if done % 10 == 0:
            print("…", done, flush=True)
print(f"gauges scored: {done}")
print(sc.report(horizons=(12, 24, 48, 72)))
