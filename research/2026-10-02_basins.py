#!/usr/bin/env python3
"""Do basin maps improve the nationwide forecast? (owner 2026-10-02: "ข้อมูลลุ่มน้ำ … เอาใช้ประโยชน์อะไรได้ไหม" →
items 3 "ฝนทั้งลุ่มน้ำต้นน้ำ" and 4 "ตัดลิงก์ต้นน้ำที่ผิด").

Run on the server (reads the DB and HII's two public map files; writes nothing):
    docker compose run --rm --no-deps -v "$PWD/research:/research" worker python /research/2026-10-02_basins.py [n]

Variants on the production backtest (`forecast.evaluate`, last 45 days) for n sampled gauges outside the focus area:
  A  production: upstream gauges learned within the HII basin name; rain = the gauge's 0.5° cell
  B  upstream learned within the 22-basin polygon AND the same river system (basins.river_systems), own-cell rain
  C  B + rain = mean of the cells of the gauge and of its upstream gauges (an upstream-catchment proxy)
  D  B + rain = mean over the cells of all gauges in its basin (basin-mean rain)
  P  B + basin-mean rain of a different, randomly chosen basin (placebo: same kind of input, wrong place)
Upstream gauges are learned on data before the backtest window (forecast.upstream.learn), as in production.
"""
import datetime as dt
import json
import random
import sys
from collections import defaultdict

import numpy as np

from floodwatch import basins, db, forecast as F, rain_cells
from floodwatch.forecast import upstream
from floodwatch.httpclient import fetch

H = (12, 24, 48)


def series(c, code):
    rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                        AND level_msl IS NOT NULL AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""",
                     (code, F.LOOKBACK_DAYS)).fetchall()
    return F.hourly_grid([r["obs_time"] for r in rows], [r["level_msl"] for r in rows])


def rain_of(c, points, cache):
    """{"hind": {hour: (day1, day2)}, "live": {hour: mm}} averaged over `points` (hours where any point has data)."""
    acc_h, acc_l = defaultdict(list), defaultdict(list)
    for pt in points:
        if pt not in cache:
            hind = {int(r["valid_time"].timestamp() // 3600): (r["day1"], r["day2"]) for r in c.execute(
                "SELECT valid_time, day1, day2 FROM rain_hindcast WHERE point=%s", (pt,)).fetchall()}
            live = {int(r["valid_time"].timestamp() // 3600): float(r["precip_mm"] or 0.0) for r in c.execute(
                """SELECT valid_time, precip_mm FROM weather_forecast WHERE point=%s
                   AND issue_time=(SELECT max(issue_time) FROM weather_forecast WHERE point=%s) AND valid_time > now()""",
                (pt, pt)).fetchall()}
            cache[pt] = (hind, live)
        hind, live = cache[pt]
        for k, v in hind.items():
            acc_h[k].append(v)
        for k, v in live.items():
            acc_l[k].append(v)
    if not acc_h:
        return None
    return {"hind": {k: (float(np.mean([a for a, _ in v])), float(np.mean([b for _, b in v]))) for k, v in acc_h.items()},
            "live": {k: float(np.mean(v)) for k, v in acc_l.items()}}


def skills(ev):
    return {h: (ev[h]["skill_vs_persistence"], ev[h]["rmse"].get("star"), ev[h]["method"]) if h in ev else None for h in H}


def main(n):
    B = json.loads(fetch("https://www.thaiwater.net/json/boundary/basin.json").body)["features"]
    R = json.loads(fetch("https://www.thaiwater.net/json/river/river_main.json").body)["features"]
    systems = basins.river_systems(R)
    with db.connect() as c:
        st = c.execute("""SELECT s.code, s.lat, s.lon, s.basin, s.in_focus FROM station s WHERE s.lat IS NOT NULL
            AND s.code !~ '^TEST' AND s.agency IS DISTINCT FROM 'BMA'
            AND (SELECT min(obs_time) FROM observation o WHERE o.code=s.code) < now()-interval '300 days'
            AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code AND o.obs_time > now()-interval '12 hours')""").fetchall()
    meta = {}
    for s in st:
        river = basins.river_of(s["lat"], s["lon"], R)
        meta[s["code"]] = {"lat": s["lat"], "lon": s["lon"], "hii": s["basin"], "b22": basins.basin_of(s["lat"], s["lon"], B),
                           "river": river, "in_focus": s["in_focus"]}
    random.seed(21)
    targets = random.sample([s["code"] for s in st if not s["in_focus"] and meta[s["code"]]["b22"]], n)
    cutoff_h = int(dt.datetime.now(dt.timezone.utc).timestamp() // 3600) - F.EVAL_HOURS
    basin_cells = defaultdict(set)
    for code, m in meta.items():
        if m["b22"]:
            basin_cells[m["b22"]].add(rain_cells.cell_of(m["lat"], m["lon"])[0])
    res, ser, rcache, changed = [], {}, {}, 0
    with db.connect() as c:
        def get(code):
            if code not in ser:
                ser[code] = series(c, code)
            return ser[code]
        for code in targets:
            m = meta[code]
            t, y = get(code)
            if len(y) < 24 * 200:
                continue
            # A: production candidates (same HII basin name); B: same 22-basin polygon and same river system
            cand_a = {k for k, v in meta.items() if k != code and v["hii"] and v["hii"] == m["hii"]}
            cand_b = {k for k, v in meta.items() if k != code and v["b22"] == m["b22"]
                      and basins.connected(v["river"], m["river"], systems)}
            ups = {}
            for name, cands in (("A", cand_a), ("B", cand_b)):
                sel = {k: get(k) for k in cands if len(get(k)[0])}
                sel[code] = (t, y)
                mm = {k: {"basin": "x", "lat": meta[k]["lat"], "lon": meta[k]["lon"]} for k in sel}
                ups[name] = [u[0] for u in upstream.learn(sel, mm, cutoff_h, {code}).get(code, [])]
            changed += set(ups["A"]) != set(ups["B"])
            own = rain_cells.cell_of(m["lat"], m["lon"])[0]
            others = [b for b in basin_cells if b != m["b22"]]
            variants = {
                "A": (ups["A"], [own]), "B": (ups["B"], [own]),
                "C": (ups["B"], sorted({own} | {rain_cells.cell_of(meta[u]["lat"], meta[u]["lon"])[0] for u in ups["B"]})),
                "D": (ups["B"], sorted(basin_cells[m["b22"]])),
                "P": (ups["B"], sorted(basin_cells[random.Random(hash(code) % 1000).choice(others)])),
            }
            out = {"code": code, "basin": m["b22"], "river": m["river"], "up_A": ups["A"], "up_B": ups["B"]}
            for name, (up, pts) in variants.items():
                rain = rain_of(c, pts, rcache)
                if rain is None:
                    out[name] = None
                    continue
                exo = {"up": [get(u) for u in up if len(get(u)[0])], "q": None, "rain": rain}
                exo["up"] = [([dt.datetime.fromtimestamp(h * 3600, dt.timezone.utc) for h in tt], list(yy)) for tt, yy in exo["up"]]
                out[name] = skills(F.evaluate(t, y, F.align_exo(t, exo)))
            res.append(out)
            print(code, m["b22"], m["river"], "A", ups["A"], "B", ups["B"],
                  {k: (out[k] or {}).get(24) and round(out[k][24][0], 3) for k in "ABCDP"}, flush=True)
    print(f"\nbasins {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC: {len(res)} gauges; upstream set changed A->B at {changed}")
    for h in H:
        print(f"  {h} h:")
        for k, label in (("A", "production"), ("B", "basin22 + river system"), ("C", "B + upstream-cells rain"),
                         ("D", "B + basin-mean rain"), ("P", "B + placebo basin rain")):
            v = [r[k][h][0] for r in res if r.get(k) and r[k][h]]
            print(f"    {label:<26} mean skill {np.mean(v):5.3f}  over gate {sum(x > F.SKILL_GATE for x in v):>3}/{len(v)}")
        for k, base in (("B", "A"), ("C", "B"), ("D", "B"), ("P", "B")):
            d = [r[k][h][1] / r[base][h][1] - 1 for r in res if r.get(k) and r.get(base) and r[k][h] and r[base][h]
                 and r[k][h][1] and r[base][h][1]]
            if d:
                print(f"    star RMSE {k} vs {base}: median {np.median(d) * 100:+.1f} %, better at {sum(x < 0 for x in d)}/{len(d)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
