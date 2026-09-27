"""Proof for D-052 before release: does adding the network space-time AR + rain model ("star") to the production
backtest improve the chosen forecast, across 3 separate 45-day windows? Uses the production code
(forecast.evaluate, forecast.load_exo); each window truncates all series at its end, so nothing after it is used.
Run: docker compose run --rm --no-deps -v $PWD/research/validation:/exp worker python /exp/validate_star_2026-09-27.py
Compares, on the same rows, the best of the gauge's own methods (persistence/tide/tide_trend/trend) with the best
including star, per horizon. Results: research/2026-09-27_forecast_48h.md §9."""
import datetime as dt
import statistics as st
import numpy as np
from floodwatch import db, forecast

WINDOW_ENDS_DAYS_AGO = (0, 45, 90)
HS = (12, 24, 48)

def cut(series, end):
    ts, vs = series
    k = sum(1 for x in ts if x <= end)
    return ts[:k], vs[:k]

with db.connect() as c:
    stations = c.execute("""SELECT s.code, s.lat, s.lon, s.name_th FROM station s WHERE s.in_focus AND s.lat IS NOT NULL
                            AND (SELECT count(*) FROM observation o WHERE o.code=s.code AND o.quality_flag='ok') > 24*100""").fetchall()
    cache = {}
    exos = {s["code"]: forecast.load_exo(c, s["code"], s["lat"], s["lon"], cache) for s in stations}
    series = {s["code"]: forecast_series for s in stations for forecast_series in [
        (lambda rows: ([r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows]))(c.execute(
            "SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok' AND level_msl IS NOT NULL "
            "AND obs_time > now() - interval '370 days' ORDER BY obs_time", (s["code"],)).fetchall())]}
now = dt.datetime.now(dt.timezone.utc)
summary = {}
detail = {}
for ago in WINDOW_ENDS_DAYS_AGO:
    end = now - dt.timedelta(days=ago)
    for s in stations:
        code, ex = s["code"], exos[s["code"]]
        if ex is None:
            continue
        ts, vs = cut(series[code], end)
        if len(ts) < 24 * 60:
            continue
        exo = {"up": [cut(u, end) for u in ex["up"]], "q": cut(ex["q"], end) if ex["q"] else None,
               "rain": {"hind": ex["rain"]["hind"], "live": {}}}
        t, y = forecast.hourly_grid(ts, vs)
        ev = forecast.evaluate(t, y, forecast.align_exo(t, exo))
        for h in HS:
            e = ev.get(h)
            if not e or "star" not in e["rmse"]:
                continue
            own = min(v for m, v in e["rmse"].items() if m != "star")
            best = min(e["rmse"].values())
            summary.setdefault((ago, h), []).append((code, own, best, e["rmse"]["persistence"], e["method"]))
            detail[(ago, h, code)] = (e["rmse"]["star"], own, min(e["rmse"], key=lambda m: e["rmse"][m] if m != "star" else 9e9))
print("window end | horizon | gauges | star chosen | median own->best RMSE (cm) | median gain | gauges improved >10% | 48h-skill>=0.3 own->best")
for (ago, h), rows in sorted(summary.items()):
    own = [r[1] for r in rows]; best = [r[2] for r in rows]; per = [r[3] for r in rows]
    gains = [1 - b / o for _, o, b, _, _ in rows if o > 0]
    sk_own = sum(1 for o, p in zip(own, per) if p > 0 and 1 - o / p >= 0.3)
    sk_best = sum(1 for b, p in zip(best, per) if p > 0 and 1 - b / p >= 0.3)
    print(f"-{ago:>2}d | +{h:>2}h | {len(rows):>3} | {sum(r[4] == 'star' for r in rows):>3} | "
          f"{st.median(own)*100:5.1f} -> {st.median(best)*100:5.1f} | {st.median(gains)*100:4.1f}% | "
          f"{sum(g > 0.10 for g in gains):>3} | {sk_own:>3} -> {sk_best:>3}")
top = sorted(summary.get((0, 48), []), key=lambda r: -(1 - r[2] / r[1]))[:8]
print("largest 48 h gains, latest window:", [(c, round(o * 100, 1), round(b * 100, 1)) for c, o, b, _, _ in top])

# Out of sample: choose on the older window, score on the next newer one. Where star was chosen on the older window,
# is it still better than the gauge's own best method on the newer window, and by how much?
print("chosen on window -> scored on window | horizon | star chosen before | still better after | median gain after (star vs own)")
for older, newer in ((90, 45), (45, 0)):
    for h in HS:
        picked = [code for (a, hh, code), _ in detail.items() if a == older and hh == h
                  and [r for r in summary[(older, h)] if r[0] == code][0][4] == "star"]
        after = [detail[(newer, h, c)] for c in picked if (newer, h, c) in detail]
        if not after:
            continue
        better = sum(1 for sr, own, _ in after if sr < own)
        gains = [1 - sr / own for sr, own, _ in after if own > 0]
        print(f"-{older}d -> -{newer}d | +{h}h | {len(after)} | {better} ({100*better/len(after):.0f}%) | {st.median(gains)*100:.1f}%")
