"""Q52 step 4: likely ranges (bands) that depend on the measured trend at issue time — honest test (owner 2026-10-04: "not
fake the result and error or uncertainty to make it better"). Today a gauge's 50/90 % band is one set of error quantiles
from its 45-day backtest, whatever the water is doing. Here the quantiles are learned on the first half of the window,
per regime (measured pace up / down / flat, forecast.recent_rate, >= 2 cm a day) when a regime has >= 30 cases, else
global; they are judged on the second half: coverage (a 50 % band should hold ~50 %, a 90 % band ~90 %) and width.
Methods: persistence ("no change", served at ~520 gauges) and the gauge's best own method.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker nice -n 19 python - 200 1 < research/2026-10-04_bands_by_trend.py"""
import collections as C, sys
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F

N, K = int(sys.argv[1]), int(sys.argv[2])
QS = [0.05, 0.25, 0.5, 0.75, 0.95]
acc = C.defaultdict(lambda: C.defaultdict(list))


def regime(y, i):
    r = F.recent_rate(y, i) * 24
    return "up" if r >= 0.02 else "down" if r <= -0.02 else "flat"


with db.connect_readonly() as c:
    for code in H.sample_codes(c, N, K):
        t, y = H.load_series(c, code)
        if len(y) < 24 * 60:
            continue
        own, split = F._backtest_errors(t, y, None)
        for h in (24, 48, 72):
            rows = F.common_rows(own[h])
            if len(rows) < 120:
                continue
            half = len(rows) // 2
            A, B = rows[:half], rows[half:]
            best = min((m for m in own[h] if m != "persistence"),
                       key=lambda m: H.rmse(np.array([own[h][m][i] for i in A])), default=None)
            for m in ("persistence", best):
                if m is None:
                    continue
                eA = np.array([own[h][m][i] for i in A]); eB = np.array([own[h][m][i] for i in B])
                rA = [regime(y, i) for i in A]; rB = [regime(y, i) for i in B]
                g = np.quantile(eA, QS)
                per = {r: np.quantile(eA[[x == r for x in rA]], QS) for r in ("up", "down", "flat") if sum(x == r for x in rA) >= 30}
                for name, qfun in (("global", lambda r: g), ("by trend", lambda r: per.get(r, g))):
                    qq = np.array([qfun(r) for r in rB])
                    key = (h, "persistence" if m == "persistence" else "best own")
                    acc[key][name + " cov50"].append(np.mean((eB >= qq[:, 1]) & (eB <= qq[:, 3])))
                    acc[key][name + " cov90"].append(np.mean((eB >= qq[:, 0]) & (eB <= qq[:, 4])))
                    acc[key][name + " w50"].append(np.mean(qq[:, 3] - qq[:, 1]) * 100)
                    acc[key][name + " w90"].append(np.mean(qq[:, 4] - qq[:, 0]) * 100)
                    acc[key][name + " mae"].append(np.mean(np.abs(eB - qq[:, 2])) * 100)
for key in sorted(acc):
    a = acc[key]
    n = len(a["global cov50"])
    print(f"\n+{key[0]} h, {key[1]} (n {n} gauges, second half)")
    for name in ("global", "by trend"):
        print(f"  {name:9s} 50 % band holds {100 * np.mean(a[name + ' cov50']):4.1f}% (width {np.mean(a[name + ' w50']):5.1f} cm) · "
              f"90 % band holds {100 * np.mean(a[name + ' cov90']):4.1f}% (width {np.mean(a[name + ' w90']):5.1f} cm) · "
              f"error of the centre {np.mean(a[name + ' mae']):5.1f} cm")
