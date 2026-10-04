"""Q52 step 5: would a shorter error window make the likely ranges honest again? Live record (research/
2026-10-04_band_coverage_live.log): 72 h bands held 44 % (50 % band) and 80 % (90 % band), misses mostly BELOW the band —
the 45-day error window still carries the rising weeks while rivers recede. Rolling-origin test, no future: for each issue
hour i in the second half of the window, the band comes from the errors of issue hours j with j + h <= i (already known)
inside the last W days; coverage, width and the centre's error are judged on hour i. W = 10, 15, 30, 45 days.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker nice -n 19 python - 150 1 < research/2026-10-04_band_window.py"""
import collections as C, sys
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F

N, K = int(sys.argv[1]), int(sys.argv[2])
QS = [0.05, 0.25, 0.5, 0.75, 0.95]
WS = (10, 15, 30, 45)
acc = C.defaultdict(lambda: C.defaultdict(list))
with db.connect_readonly() as c:
    for code in H.sample_codes(c, N, K):
        t, y = H.load_series(c, code)
        if len(y) < 24 * 60:
            continue
        own, split = F._backtest_errors(t, y, None)
        for h in (24, 48, 72):
            for m in ("persistence",) + tuple(sorted(x for x in own[h] if x != "persistence")[:0]):
                e = own[h].get(m) or {}
                idx = np.array(sorted(e))
                if len(idx) < 240:
                    continue
                ev = np.array([e[i] for i in idx])
                test = idx[len(idx) // 2:]
                for W in WS:
                    cov50 = cov90 = n = 0
                    w50 = cen = 0.0
                    for i in test[::3]:  # every 3rd hour: enough cases, a third of the time
                        sel = (idx + h <= i) & (idx > i - W * 24)
                        if sel.sum() < 48:
                            continue
                        q = np.quantile(ev[sel], QS)
                        x = e[i]
                        n += 1
                        cov50 += q[1] <= x <= q[3]
                        cov90 += q[0] <= x <= q[4]
                        w50 += (q[3] - q[1]) * 100
                        cen += abs(x - q[2]) * 100
                    if n:
                        a = acc[(h, W)]
                        a["cov50"].append(cov50 / n); a["cov90"].append(cov90 / n)
                        a["w50"].append(w50 / n); a["cen"].append(cen / n)
for (h, W) in sorted(acc):
    a = acc[(h, W)]
    print(f"+{h} h, last {W:2d} days (n {len(a['cov50'])} gauges, 'no change' errors): 50 % band holds {100 * np.mean(a['cov50']):4.1f}% "
          f"(width {np.mean(a['w50']):5.1f} cm) · 90 % band holds {100 * np.mean(a['cov90']):4.1f}% · centre error {np.mean(a['cen']):5.1f} cm")
