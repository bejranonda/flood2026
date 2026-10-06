"""E-HIST — how accurate were the forecasts each model generation actually issued? (owner 2026-10-06: "In models.MD we
expect to see how good the models were developed here along many release and history: for example, how good can we
improve the accuracy, how better the models, what we benefit more")

Read-only (`db.connect_readonly()`, D-096). `forecast_run` keeps every issued forecast for 14 days (thinned after 2), with
the forecaster's version: mvp-0.1 (v0.1, 2026-09-26), star-0.2 (v0.8.0, 09-27: rain + upstream + dam release),
star-0.3 (v0.20.7, 10-03: one forecaster, the measured trend as a model method), star-0.4 (v0.25.0, 10-04: 7/30-day means,
1/3/72 h changes and up to 4 learned upstream gauges, D-092/D-093). star-0.4's runs from 2026-10-05 07:00 UTC are scored
apart as "star-0.4+cal": v0.26.0 (tagged 06:56 UTC) added the daily 90 % band calibration (D-098) and Flood Hub as an
input (D-097) without changing the version.
For every run and each horizon h in (6, 12, 24, 48, 72): the issued median (path q[2]), "no change" (level_now), the
50 % and 90 % ranges (q[1]..q[3], q[0]..q[4]), and the gauge's mean ok reading in the hour nearest to issue + h (±30 min;
runs were issued at any minute of the 30-min cycle).
Per generation: MAE of the median and of "no change" on the same runs; the share of runs a model (not "no change")
served; where a model served, its error against "no change" on those runs; how often the ranges held.
Caveat: each generation ran in a different week (the flood peak, then the recession), so compare the ratios against
"no change" rather than raw errors, and the "same gauges" table (gauges every generation forecast) over the "all" one.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker nice python - \
       < research/2026-10-06_model_history.py"""
import collections as C
import datetime as dt
import json

import numpy as np

from floodwatch import db

HS = (6, 12, 24, 48, 72)
CAL = dt.datetime(2026, 10, 5, 7, 0, tzinfo=dt.UTC)  # v0.26.0 (D-097, D-098)


def generation(r) -> str:
    return "star-0.4+cal" if r["version"] == "star-0.4" and r["issue_time"] >= CAL else r["version"]


with db.connect_readonly() as c, c.cursor() as cur:
    cur.execute("SET statement_timeout = '180s'")
    cur.execute("""SELECT code, issue_time, version, (payload->>'level_now')::float AS now,
                          jsonb_path_query_first(payload, '$.path[*] ? (@.h == 6)')  AS p6,
                          jsonb_path_query_first(payload, '$.path[*] ? (@.h == 12)') AS p12,
                          jsonb_path_query_first(payload, '$.path[*] ? (@.h == 24)') AS p24,
                          jsonb_path_query_first(payload, '$.path[*] ? (@.h == 48)') AS p48,
                          jsonb_path_query_first(payload, '$.path[*] ? (@.h == 72)') AS p72
                   FROM forecast_run""")
    runs = cur.fetchall()
    codes = sorted({r["code"] for r in runs})
    t0 = min(r["issue_time"] for r in runs)
    cur.execute("""SELECT code, date_trunc('hour', obs_time + interval '30 minutes') AS t, avg(level_msl) AS lv
                   FROM observation WHERE obs_time >= %s AND quality_flag = 'ok' AND level_msl IS NOT NULL
                     AND code = ANY(%s) GROUP BY 1, 2""", (t0, codes))
    obs = {(r["code"], r["t"]): r["lv"] for r in cur.fetchall()}

print(f"runs: {len(runs)}; gauges {len(codes)}; observations (hourly) {len(obs)}; from {t0:%Y-%m-%d %H:%M} UTC")
gauges = C.defaultdict(set)
for r in runs:
    gauges[generation(r)].add(r["code"])
order = sorted(gauges, key=lambda v: min(r["issue_time"] for r in runs if generation(r) == v))
common = set.intersection(*(gauges[v] for v in order))
print("generations:", ", ".join(f"{v} ({len(gauges[v])} gauges)" for v in order), f"; forecast by all: {len(common)}")

rows = C.defaultdict(list)  # (version, h, "all"|"same") -> [(err_model, err_none, served_model, in50, in90)]
for r in runs:
    if r["now"] is None:
        continue
    for h in HS:
        p = r[f"p{h}"]
        if not p or not p.get("q") or len(p["q"]) != 5:
            continue
        vt = r["issue_time"] + dt.timedelta(hours=h, minutes=30)
        o = obs.get((r["code"], vt.replace(minute=0, second=0, microsecond=0)))
        if o is None:
            continue
        q = p["q"]
        rec = (abs(q[2] - o), abs(r["now"] - o), p.get("method") not in (None, "persistence"),
               q[1] <= o <= q[3], q[0] <= o <= q[4])
        rows[(generation(r), h, "all")].append(rec)
        if r["code"] in common:
            rows[(generation(r), h, "same")].append(rec)

out = {}
for scope in ("same", "all"):
    print(f"\n=== {'gauges every generation forecast' if scope == 'same' else 'all gauges'} — issued median vs what happened")
    print(f"{'generation':12s} {'h':>3s} {'n':>6s} {'MAE cm':>7s} {'no-change':>9s} {'vs no-change':>12s} "
          f"{'model served':>12s} {'where served':>12s} {'50% held':>8s} {'90% held':>8s}")
    for v in order:
        for h in HS:
            x = rows.get((v, h, scope))
            if not x or len(x) < 30:
                continue
            a = np.array(x, dtype=float)
            mae, none = a[:, 0].mean() * 100, a[:, 1].mean() * 100
            sv = a[:, 2] > 0
            wsv = (a[sv, 0].mean() / a[sv, 1].mean() - 1) * 100 if sv.sum() >= 30 and a[sv, 1].mean() > 0 else float("nan")
            res = {"n": len(a), "mae_cm": round(mae, 1), "no_change_cm": round(none, 1),
                   "vs_no_change_pct": round((mae / none - 1) * 100, 1), "model_served_pct": round(sv.mean() * 100, 1),
                   "where_served_pct": None if np.isnan(wsv) else round(wsv, 1),
                   "held50_pct": round(a[:, 3].mean() * 100, 1), "held90_pct": round(a[:, 4].mean() * 100, 1)}
            out[f"{scope}|{v}|{h}"] = res
            ws = "–" if res["where_served_pct"] is None else f"{res['where_served_pct']:+.1f} %"
            print(f"{v:12s} {h:3d} {res['n']:6d} {res['mae_cm']:7.1f} {res['no_change_cm']:9.1f} "
                  f"{res['vs_no_change_pct']:+11.1f} % {res['model_served_pct']:11.1f} % {ws:>12s} "
                  f"{res['held50_pct']:7.1f} % {res['held90_pct']:7.1f} %")
print("SUMMARY_JSON", json.dumps(out))
