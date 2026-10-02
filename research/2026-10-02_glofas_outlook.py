#!/usr/bin/env python3
"""GloFAS (Open-Meteo flood API, keyless, non-commercial) for a 3-7 day outlook at main-river gauges: upper-bound test.
Owner 2026-10-02: GloFAS "for longer outlook", only after a backtest (D-060 rule). Report: 2026-10-02_glofas_outlook.md.

Open-Meteo serves GloFAS reanalysis/consolidated + today's forecast, not forecasts as issued, so this is an UPPER BOUND:
  1. snap each gauge to the GloFAS channel cell (KI-509): the largest mean discharge within +-0.075 deg;
  2. realism: GloFAS daily discharge vs measured discharge (RID C.* gauges);
  3. backtest of daily level change y = L(t+h) - L(t), h = 3/5/7 d, chronological split (first 60 % train):
     persistence | AR (own changes) | AR + GloFAS now (known at t) | AR + GloFAS future change (perfect, not knowable).
If even the perfect variant does not beat AR, GloFAS cannot help a 3-7 day outlook here and we stop.

    docker compose run --rm --no-deps -v "$PWD/research:/r:ro" worker python /r/2026-10-02_glofas_outlook.py > out.json
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time

import numpy as np
import psycopg
import requests

UA = "BKK-FloodWatch/0.18 (+https://flood.autobahn.bot; research)"
API = "https://flood-api.open-meteo.com/v1/flood"
# 12 gauges, chosen along the chain (8 with measured discharge). Open-Meteo weights a request by locations x 2-week
# chunks and shares the free daily allowance with our production rain collectors: keep this run ~650 weighted calls.
GAUGES = ["C.2", "C.13", "C.3", "C.7A", "C.36", "C.37", "C.35", "S.26", "CPY012", "CPY014", "T.1", "THA008"]
H = (3, 5, 7)
START, END = "2025-09-25", (dt.date.today() - dt.timedelta(days=1)).isoformat()


def glofas(lats, lons, start=START) -> list[dict]:
    time.sleep(10)  # stay far below the per-minute limit (HTTP 429 seen 2026-10-02 with 49 points x 1 year)
    r = requests.get(API, params={"latitude": ",".join(f"{x:.4f}" for x in lats), "longitude": ",".join(f"{x:.4f}" for x in lons),
                                  "daily": "river_discharge", "start_date": start, "end_date": END}, headers={"User-Agent": UA},
                     timeout=120)
    r.raise_for_status()
    d = r.json()
    return d if isinstance(d, list) else [d]


def snap(lat, lon, measured_14d=None):
    """Snap to the GloFAS channel cell (KI-509) on the 0.05-deg grid within +-0.1 deg (25 cells, last 14 days, weight 25):
    with measured discharge, the cell whose 14-day mean is closest (log ratio) to the measured mean; without it, the
    NEAREST cell carrying >= half of the largest mean (plain "largest mean" lands on the window corner, downstream of
    confluences: run 1, C.35 at 3.4x measured). Then one year for that cell only (weight ~28)."""
    off = np.arange(-0.1, 0.1001, 0.05)
    pts = [(lat + a, lon + b) for a in off for b in off]
    res = glofas([p[0] for p in pts], [p[1] for p in pts], start=(dt.date.today() - dt.timedelta(days=14)).isoformat())
    cells = [(float(np.nanmean([np.nan if v is None else v for v in d["daily"]["river_discharge"]])), d["latitude"], d["longitude"])
             for d in res]
    cells = [c for c in cells if np.isfinite(c[0]) and c[0] > 0]
    if measured_14d:
        m, cla, clo = min(cells, key=lambda c: abs(np.log(c[0] / measured_14d)))
    else:
        top = max(c[0] for c in cells)
        m, cla, clo = min((c for c in cells if c[0] >= top / 2), key=lambda c: np.hypot(c[1] - lat, c[2] - lon))
    d = glofas([cla], [clo])[0]
    q = np.array([np.nan if v is None else v for v in d["daily"]["river_discharge"]], float)
    return float(np.nanmean(q)), d["latitude"], d["longitude"], d["daily"]["time"], q


def fit_mae(Xtr, ytr, Xte, yte, lam=1e-3):
    Xtr1, Xte1 = np.c_[np.ones(len(Xtr)), Xtr], np.c_[np.ones(len(Xte)), Xte]
    w = np.linalg.solve(Xtr1.T @ Xtr1 + lam * np.eye(Xtr1.shape[1]), Xtr1.T @ ytr)
    return float(np.mean(np.abs(Xte1 @ w - yte)))


def main():
    out = {"period": [START, END], "gauges": {}}
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        for code in GAUGES:
            st = con.execute("SELECT lat, lon, bank_msl FROM station WHERE code=%s", (code,)).fetchone()
            if not st:
                continue
            rows = con.execute("""SELECT (obs_time AT TIME ZONE 'Asia/Bangkok')::date d, avg(level_msl), avg(discharge)
                                  FROM observation WHERE code=%s AND quality_flag='ok' AND obs_time >= %s
                                  GROUP BY 1 ORDER BY 1""", (code, START)).fetchall()
            recent = [qo for d, lv, qo in rows if qo is not None and d >= dt.date.today() - dt.timedelta(days=14)]
            m, gla, glo, days, q = snap(st[0], st[1], float(np.mean(recent)) if len(recent) >= 7 else None)
            day_i = {dt.date.fromisoformat(t): i for i, t in enumerate(days)}
            L = np.full(len(days), np.nan)
            Qobs = np.full(len(days), np.nan)
            for d, lv, qo in rows:
                if d in day_i:
                    L[day_i[d]] = lv
                    Qobs[day_i[d]] = np.nan if qo is None else qo
            g = {"cell": [gla, glo], "snap_km": round(float(np.hypot(gla - st[0], (glo - st[1]) * np.cos(np.radians(st[0])))) * 111, 1),
                 "glofas_mean_m3s": round(float(m), 1), "days_level": int(np.isfinite(L).sum())}
            ok = np.isfinite(Qobs) & np.isfinite(q)
            if ok.sum() > 60:
                g["vs_measured"] = {"n": int(ok.sum()), "r": round(float(np.corrcoef(q[ok], Qobs[ok])[0, 1]), 3),
                                    "glofas_over_measured_median": round(float(np.median(q[ok] / np.maximum(Qobs[ok], 1))), 2),
                                    "measured_mean_m3s": round(float(np.mean(Qobs[ok])), 1)}
            lq = np.log(np.maximum(q, 1))
            res = {}
            for h in H:
                idx = [t for t in range(3, len(days) - h)
                       if np.isfinite(L[[t, t - 1, t - 3, t + h]]).all() and np.isfinite(lq[[t, t - 3, t + h]]).all()]
                if len(idx) < 120:
                    continue
                t = np.array(idx)
                y = L[t + h] - L[t]
                ar = np.c_[L[t] - L[t - 1], L[t] - L[t - 3]]
                now = np.c_[ar, lq[t], lq[t] - lq[t - 3]]
                fut = np.c_[now, lq[t + h] - lq[t]]
                cut = int(len(t) * 0.6)
                tr, te = slice(0, cut), slice(cut, None)
                res[f"{h}d"] = {"n_test": len(t) - cut, "test_from": days[t[cut]],
                                "persist": round(float(np.mean(np.abs(y[te]))), 3),
                                "ar": round(fit_mae(ar[tr], y[tr], ar[te], y[te]), 3),
                                "ar_glofas_now": round(fit_mae(now[tr], y[tr], now[te], y[te]), 3),
                                "ar_glofas_perfect": round(fit_mae(fut[tr], y[tr], fut[te], y[te]), 3)}
            g["mae_m"] = res
            out["gauges"][code] = g
            print(code, json.dumps(g)[:300], file=sys.stderr, flush=True)
    # summary: median skill vs AR (positive = better than AR)
    for h in H:
        k = f"{h}d"
        gs = [g["mae_m"][k] for g in out["gauges"].values() if k in g.get("mae_m", {})]
        if gs:
            out[f"summary_{k}"] = {"gauges": len(gs),
                                   "median_skill_now_vs_ar": round(float(np.median([1 - x["ar_glofas_now"] / x["ar"] for x in gs])), 3),
                                   "median_skill_perfect_vs_ar": round(float(np.median([1 - x["ar_glofas_perfect"] / x["ar"] for x in gs])), 3),
                                   "median_skill_ar_vs_persist": round(float(np.median([1 - x["ar"] / x["persist"] for x in gs])), 3),
                                   "perfect_better_by_10pct": sum(1 - x["ar_glofas_perfect"] / x["ar"] >= 0.10 for x in gs),
                                   "now_better_by_10pct": sum(1 - x["ar_glofas_now"] / x["ar"] >= 0.10 for x in gs)}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
