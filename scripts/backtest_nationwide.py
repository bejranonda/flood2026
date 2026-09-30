#!/usr/bin/env python3
"""Backtest report for v0.16 nationwide parity (D-064): does the production forecast beat persistence, per gauge?

Run on the server (read-only; nothing is written):
    docker compose run --rm --no-deps -v "$PWD/scripts:/scripts" worker python /scripts/backtest_nationwide.py [N]

1. Bangkok regression: the same 40 random HII focus gauges (seed 1) as the 2026-09-30 history-length check, full
   inputs (Chao Phraya upstream + Bangkok rain). Baseline that day: mean skill 12/24/48 h = 0.38/0.29/0.28,
   36/40 over the 10 % gate at 48 h.
2. Nationwide: up to N random gauges outside the focus area per region (default 8) with >= 300 days of history,
   each backtested twice with the production `evaluate`: own methods only (the 0/12 baseline of 2026-09-30) and
   with the new inputs — the gauge's 0.5° rain cell (rain_hindcast) and upstream gauges learned from its basin on
   data before the backtest window (forecast.upstream.learn), exactly as the forecaster does.
"""
import datetime as dt
import random
import sys

import numpy as np

from floodwatch import db, forecast as F
from floodwatch.forecast import upstream

H = (12, 24, 48)
GATE = F.SKILL_GATE


def series(c, code):
    rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                        AND level_msl IS NOT NULL AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""",
                     (code, F.LOOKBACK_DAYS)).fetchall()
    return F.hourly_grid([r["obs_time"] for r in rows], [r["level_msl"] for r in rows]), rows


def skills(ev):
    return {h: (ev[h]["skill_vs_persistence"], ev[h]["method"]) if h in ev else (None, None) for h in H}


def summary(label, res):
    for h in H:
        v = [r[h][0] for r in res if r[h][0] is not None]
        star = sum(1 for r in res if r[h][1] == "star")
        print(f"  {label:<22} {h:>2} h: n={len(v):>3}  mean skill {np.mean(v) if v else float('nan'):5.2f}  "
              f"over gate {sum(x > GATE for x in v):>3}/{len(v):<3}  star chosen {star}")


def bangkok(c):
    random.seed(1)
    st = c.execute("""SELECT s.code, s.lat, s.lon, s.agency FROM station s WHERE s.in_focus AND s.agency IS DISTINCT FROM 'BMA'
        AND (SELECT min(obs_time) FROM observation o WHERE o.code=s.code) < now()-interval '330 days'
        AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code AND o.obs_time>now()-interval '12 hours')""").fetchall()
    st = random.sample(st, min(40, len(st)))
    cache, res = {}, []
    for s in st:
        (t, y), _ = series(c, s["code"])
        if len(y) < 2000:
            continue
        exo = F.load_exo(c, s["code"], s["lat"], s["lon"], cache, True)
        res.append(skills(F.evaluate(t, y, F.align_exo(t, exo))))
    print(f"Bangkok regression ({len(res)} gauges, full inputs):")
    summary("focus, production", res)


def nationwide(c, per_region):
    from floodwatch import regions
    random.seed(7)
    st = c.execute("""SELECT s.code, s.lat, s.lon, s.basin, s.province FROM station s WHERE NOT s.in_focus
        AND s.code !~ '^TEST' AND s.agency IS DISTINCT FROM 'BMA' AND s.lat IS NOT NULL
        AND (SELECT min(obs_time) FROM observation o WHERE o.code=s.code) < now()-interval '300 days'
        AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code AND o.obs_time>now()-interval '12 hours')""").fetchall()
    by = {}
    for s in st:
        by.setdefault(regions.region_of(s["province"]), []).append(s)
    sample = [s for r in sorted(by, key=str) for s in random.sample(by[r], min(per_region, len(by[r])))]
    print(f"\nNationwide: {len(st)} gauges outside the focus area have >= 300 days; sampled {len(sample)} "
          f"({', '.join(f'{r}:{min(per_region, len(v))}' for r, v in sorted(by.items(), key=lambda kv: str(kv[0])))})")
    cutoff_h = int(dt.datetime.now(dt.timezone.utc).timestamp() // 3600) - F.EVAL_HOURS
    basin_series: dict = {}
    own, full, n_up, n_rain = [], [], 0, 0
    cache: dict = {"learned": {}}
    for s in sample:
        (t, y), _ = series(c, s["code"])
        if len(y) < 24 * 60:
            continue
        own.append(skills(F.evaluate(t, y, None)))
        if s["basin"] and s["basin"] not in basin_series:  # the basin's gauges with history, as the forecaster sees them
            codes = c.execute("""SELECT code, lat, lon FROM station WHERE basin=%s AND lat IS NOT NULL
                                 AND agency IS DISTINCT FROM 'BMA' AND code !~ '^TEST'""", (s["basin"],)).fetchall()
            ser = {k["code"]: series(c, k["code"])[0] for k in codes}
            basin_series[s["basin"]] = ({k: v for k, v in ser.items() if len(v[0])},
                                        {k["code"]: {"basin": s["basin"], "lat": k["lat"], "lon": k["lon"]} for k in codes})
        ser, meta = basin_series.get(s["basin"], ({}, {}))
        learned = upstream.learn(ser, meta, cutoff_h, {s["code"]}) if ser else {}
        cache["learned"] = learned
        exo = F.load_exo(c, s["code"], s["lat"], s["lon"], cache, False)
        n_up += bool(learned.get(s["code"]))
        n_rain += exo is not None
        full.append(skills(F.evaluate(t, y, F.align_exo(t, exo))) if exo else own[-1])
        for k in [k for k in cache if isinstance(k, tuple) and k[0] != "rain"]:
            cache.pop(k)  # upstream series of this gauge: not reused across basins
    print(f"  inputs found: rain history for {n_rain}/{len(own)}, learned upstream for {n_up}/{len(own)}")
    summary("own methods only", own)
    summary("rain + learned upstream", full)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print(f"backtest_nationwide {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC, gate {GATE:.0%}")
    with db.connect() as c:
        bangkok(c)
        nationwide(c, n)
