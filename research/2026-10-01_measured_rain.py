#!/usr/bin/env python3
"""Does measured daily rain (HII rain gauges) improve the production `star` forecast? (Q43, owner 2026-10-01:
"Consider the factors in modeling and validate the results, think carefully.")

Run on the server (reads the DB, fetches daily rain from HII politely and caches it; writes nothing to the DB):
    docker compose run --rm --no-deps -v "$PWD/research:/research" -v "$PWD/data/rain_daily_cache:/cache" \
        worker python /research/2026-10-01_measured_rain.py [n_per_group]

Data (verified 2026-10-01): HII `provinces/rain3d_graph?station_id&start_date&end_date` gives DAILY totals per rain
gauge (local date), at most ~31 days per request, back to at least 2024. No public hourly history exists.

Features, aligned to the forecast's hourly grid (UTC) and known at issue time (no leakage):
  HII labels a daily total by the day its 24 h window ENDS (fit 2026-10-01 on 60 Bangkok gauges x 4 days against our
  own hourly readings: best window ends ~00:00-02:00 ICT on the labelled day, r = 0.64-0.66; 07-07 r = 0.53; midnight to
  midnight of the label r = 0.29). Values are ~7x the hourly sums (median): unexplained, so only their information is
  used (ridge standardises inputs). Leakage-safe rule: the value labelled D is used from 08:00 ICT on D (later than
  any plausible window end, 07:00 for the 07-07 convention, plus 1 h);
  R1 = rain of the last complete day, R3 / R7 = sums of the last 3 / 7 complete days;
  each = mean over the up to 3 nearest rain gauges within 10 km (QC: 0 <= mm <= 400); NaN when none reported.
Training and backtest use the same rule, and the live forecast would too.

Comparisons per gauge (same production `evaluate`, same last-45-day window):
  A  production star inputs (upstream, dam release, forecast rain);
  B  A + R1, R3, R7;
  P  A + the same features from day-shuffled rain (placebo: any "gain" here is overfitting, not information).
Event check: RMSE of star A vs B vs persistence on test hours within 24 h after a complete day with >= 35 mm.
"""
import datetime as dt
import json
import math
import os
import random
import sys
import time

import numpy as np

from floodwatch import db, forecast as F
from floodwatch.httpclient import fetch

H = (6, 12, 24, 48)
LAT_H = 1          # hours after a local day ends before its total may be used
NEAR_KM, K = 10.0, 3
HEAVY = 35.0
CACHE = "/cache"
ICT = dt.timedelta(hours=7)
START, END = dt.date(2025, 9, 1), dt.date(2026, 10, 1)


def km(a, b):
    p = math.pi / 180
    h = math.sin((b[0] - a[0]) * p / 2) ** 2 + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def rain_gauges():
    d = json.loads(fetch("https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h").body)
    out = []
    for r in d.get("data") or []:
        s = r.get("station") or {}
        try:
            out.append({"id": s["id"], "lat": float(s["tele_station_lat"]), "lon": float(s["tele_station_long"])})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def daily(gid):
    path = f"{CACHE}/{gid}.json"
    if os.path.exists(path):
        return json.load(open(path))
    out, s = {}, START
    while s <= END:
        e = min(s + dt.timedelta(days=29), END)
        url = (f"https://api-v3.thaiwater.net/api/v1/thaiwater30/provinces/rain3d_graph?station_id={gid}"
               f"&start_date={s}&end_date={e}")
        try:
            j = json.loads(fetch(url, retries=2).body)
            for p in j.get("data") if isinstance(j.get("data"), list) else []:
                v = p.get("rainfall_value")
                if v is not None and 0 <= float(v) <= 400:
                    out[p["rainfall_datetime"][:10]] = float(v)
        except Exception as ex:
            print("  fetch failed", gid, s, ex)
        s = e + dt.timedelta(days=1)
        time.sleep(0.6)
    json.dump(out, open(path, "w"))
    return out


def features(t, series_list, shuffle_seed=None):
    """R1, R3, R7 on the hourly grid t (unix hours), from daily series {YYYY-MM-DD: mm} of nearby gauges."""
    days = sorted({d for s in series_list for d in s})
    if shuffle_seed is not None:  # placebo: same values, wrong days
        perm = days[:]
        random.Random(shuffle_seed).shuffle(perm)
        series_list = [{perm[days.index(d)]: v for d, v in s.items()} for s in series_list]
    mean = {}
    for d in days:
        v = [s[d] for s in series_list if d in s]
        if v:
            mean[d] = sum(v) / len(v)
    out = np.full((3, len(t)), np.nan)
    for i, h in enumerate(t.astype(int)):
        # the latest label D with D 07:00 ICT + LAT_H <= this hour (see the module docstring)
        now_utc = dt.datetime.fromtimestamp(h * 3600, dt.timezone.utc)
        last = (now_utc + ICT - dt.timedelta(hours=7 + LAT_H)).date()
        vals = [mean.get((last - dt.timedelta(days=k)).isoformat()) for k in range(7)]
        if vals[0] is None:
            continue
        out[0, i] = vals[0]
        if all(v is not None for v in vals[:3]):
            out[1, i] = sum(vals[:3])
        if all(v is not None for v in vals):
            out[2, i] = sum(vals)
    return list(out), out[0]


def star_errors(t, y, ex, h):
    """Production star split (as forecast.evaluate): train before the window, test on it; per-row errors."""
    n = len(y)
    split = max(int(n * 0.6), n - F.EVAL_HOURS)
    eta = F.fit_tide(t[:split], y[:split])
    yf = F._ffill(y, F.OWN_FFILL_H)
    X, tg = F.star_features(t, yf, eta, F.trailing_mean(yf, 25), h, ex), F._star_target(y, h)
    ok = np.isfinite(X).all(1) & np.isfinite(tg)
    idx = np.arange(n)
    tr, te = ok & (idx < split - h), ok & (idx >= split)
    if tr.sum() < F.STAR_MIN_TRAIN or te.sum() < 100:
        return None
    pred = F._ridge(X[tr], tg[tr])(X[te])
    return idx[te], tg[te] - pred, tg[te]  # star error, and persistence error (= target change)


def run(group, stations, n):
    random.seed(11)
    stations = random.sample(stations, min(n, len(stations)))
    gauges = rain_gauges()
    res, cache = [], {}
    for s in stations:
        near = sorted((km((s["lat"], s["lon"]), (g["lat"], g["lon"])), g["id"]) for g in gauges)
        near = [gid for d, gid in near[:K] if d <= NEAR_KM]
        if not near:
            continue
        with db.connect() as c:
            rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                                AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""",
                             (s["code"], F.LOOKBACK_DAYS)).fetchall()
            exo = F.load_exo(c, s["code"], s["lat"], s["lon"], cache, s["in_focus"])
        t, y = F.hourly_grid([r["obs_time"] for r in rows], [r["level_msl"] for r in rows])
        if len(y) < 24 * 200 or not exo:
            continue
        ex = F.align_exo(t, exo)
        series = [daily(g) for g in near]
        extra, r1 = features(t, series)
        placebo, _ = features(t, series, shuffle_seed=5)
        out = {"code": s["code"], "n_gauges": len(near)}
        for name, e in (("A", ex), ("B", {**ex, "extra": extra}), ("P", {**ex, "extra": placebo})):
            ev = F.evaluate(t, y, e)
            out[name] = {h: (ev[h]["skill_vs_persistence"], ev[h]["method"], ev[h]["rmse"].get("star"),
                             ev[h]["rmse"].get("persistence")) for h in H if h in ev}
        # event check: hours within 24 h after a complete day with >= HEAVY mm
        ev_out = {}
        for h in (12, 24):
            a, b = star_errors(t, y, ex, h), star_errors(t, y, {**ex, "extra": extra}, h)
            if not a or not b:
                continue
            common = np.intersect1d(a[0], b[0])
            wet = common[np.nan_to_num(r1[common]) >= HEAVY]
            if len(wet) < 12:
                continue
            ea = dict(zip(a[0], a[1])); eb = dict(zip(b[0], b[1])); ep = dict(zip(a[0], a[2]))
            rm = lambda d: float(np.sqrt(np.mean([d[i] ** 2 for i in wet])))
            ev_out[h] = {"n": int(len(wet)), "star": rm(ea), "star_rain": rm(eb), "persistence": rm(ep)}
        out["event"] = ev_out
        res.append(out)
        print(group, s["code"], {k: out[k].get(24) for k in "ABP"}, out["event"].get(24), flush=True)
    return res


def summary(group, res):
    print(f"\n== {group}: {len(res)} gauges")
    for h in H:
        for k, label in (("A", "production star"), ("B", "+ measured rain"), ("P", "+ placebo rain")):
            v = [r[k][h][0] for r in res if h in r[k]]
            print(f"  {h:>2} h {label:<17} mean skill {np.mean(v):5.3f}  over gate {sum(x > F.SKILL_GATE for x in v):>3}/{len(v)}")
        d = [r["B"][h][2] / r["A"][h][2] - 1 for r in res if h in r["A"] and h in r["B"] and r["A"][h][2] and r["B"][h][2]]
        dp = [r["P"][h][2] / r["A"][h][2] - 1 for r in res if h in r["A"] and h in r["P"] and r["A"][h][2] and r["P"][h][2]]
        if d:
            print(f"        star RMSE change with rain: median {np.median(d) * 100:+.1f} %, better at {sum(x < 0 for x in d)}/{len(d)}"
                  f" | placebo median {np.median(dp) * 100:+.1f} %, better at {sum(x < 0 for x in dp)}/{len(dp)}")
    for h in (12, 24):
        e = [r["event"][h] for r in res if h in r["event"]]
        if e:
            print(f"  after a >= {HEAVY:.0f} mm day, {h} h ahead ({len(e)} gauges, {sum(x['n'] for x in e)} hours): "
                  f"RMSE persistence {np.mean([x['persistence'] for x in e]):.3f} | star {np.mean([x['star'] for x in e]):.3f}"
                  f" | star + rain {np.mean([x['star_rain'] for x in e]):.3f} m; better at {sum(x['star_rain'] < x['star'] for x in e)}/{len(e)}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    os.makedirs(CACHE, exist_ok=True)
    with db.connect() as c:
        st = c.execute("""SELECT s.code, s.lat, s.lon, s.in_focus, s.agency FROM station s WHERE s.lat IS NOT NULL
            AND s.code !~ '^TEST' AND (SELECT min(obs_time) FROM observation o WHERE o.code=s.code) < now()-interval '300 days'
            AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code AND o.obs_time > now()-interval '12 hours')""").fetchall()
    out = {}
    for group, sel in (("bangkok", [s for s in st if s["in_focus"]]), ("nationwide", [s for s in st if not s["in_focus"]])):
        out[group] = run(group, sel, n)
    print(f"\nmeasured_rain {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC, LAT_H={LAT_H}, K={K}, {NEAR_KM} km")
    for group, res in out.items():
        summary(group, res)
    json.dump(out, open(f"{CACHE}/result.json", "w"), default=str)
