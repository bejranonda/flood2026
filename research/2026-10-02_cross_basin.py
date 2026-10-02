#!/usr/bin/env python3
"""Can a gauge learn upstream gauges from the basin that flows into its own? (owner 2026-10-02: "validate and check,
whether the basin data is useful", after downloading ONWR's legal 22 main basins.)

Production learns upstream gauges only within the gauge's own basin (forecast.upstream.learn). The 22 basins are
nested, though: the Ping, Wang, Yom, Nan, Sakae Krang and Pasak basins drain into the Chao Phraya basin, the Chi into
the Mun. So a gauge just below a confluence (C.2 Nakhon Sawan) cannot learn from the gauges on the rivers that feed it.

  A  production: candidates in the same basin (and the same river system when both are on main rivers)
  X  candidates in the same basin OR on the same main-river system (both gauges on main rivers), anywhere ≤ 250 km
  Y  like X, but only from basins that drain INTO the gauge's basin (FEEDS: Wang→Ping, Yom→Nan, Ping/Nan/Sakae Krang/
     Pasak→Chao Phraya, Chao Phraya→Tha Chin, Chi→Mun, Mun/Mekong North→Mekong Northeast), so never from downstream

Learned on data before the backtest window, as in production; scored with the production backtest (`forecast.evaluate`,
last 45 days) with the gauge's own-cell rain. Only gauges whose learned set changes are compared.

    docker compose run --rm --no-deps -v "$PWD/research:/research" worker python /research/2026-10-02_cross_basin.py
"""
import datetime as dt
import importlib.util
from collections import Counter

import numpy as np

from floodwatch import db, forecast as F, rain_cells
from floodwatch.forecast import upstream

spec = importlib.util.spec_from_file_location("b", "/research/2026-10-02_basins.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
H = (12, 24, 48)
# basin → the basins that drain into it directly (hydrography of the 22 legal basins; Tha Chin branches off the Chao Phraya)
FEEDS = {"ปิง": {"วัง"}, "น่าน": {"ยม"}, "เจ้าพระยา": {"ปิง", "น่าน", "สะแกกรัง", "ป่าสัก"}, "ท่าจีน": {"เจ้าพระยา"},
         "มูล": {"ชี"}, "โขงตะวันออกเฉียงเหนือ": {"มูล", "โขงเหนือ"}}


def feeders(b: str) -> set[str]:
    out, todo = set(), [b]
    while todo:
        for f in FEEDS.get(todo.pop(), ()):
            if f not in out:
                out.add(f)
                todo.append(f)
    return out


def main():
    with db.connect() as c:
        st = c.execute("""SELECT code, lat, lon, basin22, river_system, in_focus FROM station WHERE lat IS NOT NULL
            AND code !~ '^TEST' AND agency IS DISTINCT FROM 'BMA' AND basin22 IS NOT NULL""").fetchall()
    meta = {s["code"]: s for s in st}
    multi = Counter()  # river systems that span more than one basin: the only place X can differ
    for sysid in {s["river_system"] for s in st if s["river_system"] is not None}:
        multi[sysid] = len({s["basin22"] for s in st if s["river_system"] == sysid})
    targets = sorted(s["code"] for s in st if not s["in_focus"] and s["river_system"] is not None and multi[s["river_system"]] > 1)
    cutoff_h = int(dt.datetime.now(dt.timezone.utc).timestamp() // 3600) - F.EVAL_HOURS
    ser, rcache, res = {}, {}, []
    print(f"{len(targets)} target gauges on main rivers whose system spans several basins", flush=True)
    with db.connect() as c:
        def get(code):
            if code not in ser:
                ser[code] = B.series(c, code)
            return ser[code]
        for code in targets:
            m = meta[code]
            t, y = get(code)
            if len(y) < 24 * 200:
                continue
            ups = {}
            up_basins = feeders(m["basin22"])
            for name in ("A", "X", "Y"):
                cands = {k for k, v in meta.items() if k != code and (v["basin22"] == m["basin22"] or (
                    name != "A" and v["river_system"] is not None and v["river_system"] == m["river_system"]
                    and (name == "X" or v["basin22"] in up_basins)))}
                sel = {k: get(k) for k in cands if len(get(k)[0])}
                sel[code] = (t, y)
                mm = {k: {"basin": "x", "lat": meta[k]["lat"], "lon": meta[k]["lon"], "system": meta[k]["river_system"]} for k in sel}
                ups[name] = upstream.learn(sel, mm, cutoff_h, {code}).get(code, [])
            if {u[0] for u in ups["A"]} == {u[0] for u in ups["X"]} == {u[0] for u in ups["Y"]}:
                continue
            rain = B.rain_of(c, [rain_cells.cell_of(m["lat"], m["lon"])[0]], rcache)
            out = {"code": code, "basin": m["basin22"], "A": ups["A"], "X": ups["X"], "Y": ups["Y"]}
            for name in ("A", "X", "Y"):
                up = [get(u[0]) for u in ups[name]]
                exo = {"up": [([dt.datetime.fromtimestamp(h * 3600, dt.timezone.utc) for h in tt], list(yy)) for tt, yy in up],
                       "q": None, "rain": rain}
                out["ev" + name] = B.skills(F.evaluate(t, y, F.align_exo(t, exo)))
            res.append(out)
            fmt = lambda us: ", ".join(f"{u[0]}({meta[u[0]]['basin22']},{u[1]}h,r{u[2]})" for u in us) or "-"
            sk = lambda k: (out["ev" + k][24] or [None])[0]
            print(f"{code} [{m['basin22']}] A: {fmt(ups['A'])} | X: {fmt(ups['X'])} | Y: {fmt(ups['Y'])} | 24h skill "
                  f"A {sk('A')} X {sk('X')} Y {sk('Y')}", flush=True)
    print(f"\ncross-basin {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC: {len(res)} gauges changed their upstream set")
    for k in ("X", "Y"):
        sub = [r for r in res if {u[0] for u in r["A"]} != {u[0] for u in r[k]}]
        print(f" {k} vs A ({len(sub)} gauges whose set differs):")
        for h in H:
            pairs = [(r["evA"][h], r["ev" + k][h]) for r in sub if r["evA"][h] and r["ev" + k][h]]
            if not pairs:
                continue
            d = [x[1] / a[1] - 1 for a, x in pairs if a[1] and x[1]]
            print(f"  {h} h: over gate A {sum(a[0] > F.SKILL_GATE for a, _ in pairs)}/{len(pairs)} -> {k} {sum(x[0] > F.SKILL_GATE for _, x in pairs)}"
                  f"; mean skill {np.mean([a[0] for a, _ in pairs]):.3f} -> {np.mean([x[0] for _, x in pairs]):.3f}"
                  f"; star RMSE median {np.median(d) * 100:+.1f} %, better at {sum(v < 0 for v in d)}/{len(d)}")


if __name__ == "__main__":
    main()
