"""Spike 2026-10-03 for the จับตา tab (spec docs/superpowers/specs/2026-10-03-watch-tab-satellite-design.md §2).
Run: docker compose exec -T worker python - < research/2026-10-03_verify_up.py"""
import collections as C, datetime as dt, json
import numpy as np
from floodwatch import db
from floodwatch.api import _upstream
ups = _upstream()  # {gauge: [{code, lag_h}]}
pairs = [(g, u["code"], u["lag_h"]) for g, v in ups.items() for u in v if u.get("lag_h") and 3 <= u["lag_h"] <= 48]
print("pairs with lag 3-48 h:", len(pairs), "lags:", np.percentile([p[2] for p in pairs], [10, 50, 90]))
codes = {c for p in pairs for c in p[:2]}
t0 = dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc)
with db.connect() as c:
    rows = c.execute("""SELECT code, date_trunc('hour', obs_time) h, avg(level_msl) v FROM observation
        WHERE obs_time >= %s AND code = ANY(%s) AND level_msl IS NOT NULL AND quality_flag='ok' GROUP BY 1,2""", (t0, list(codes))).fetchall()
H = int((dt.datetime.now(dt.timezone.utc) - t0).total_seconds() // 3600) + 1
ser = {k: np.full(H, np.nan) for k in codes}
for r in rows:
    ser[r["code"]][int((r["h"] - t0).total_seconds() // 3600)] = r["v"]
for UP, DOWN in ((0.20, 0.05), (0.30, 0.10), (0.50, 0.10)):
    tab = C.Counter(); base = C.Counter()
    for g, u, lag in pairs:
        y, x = ser[g], ser[u]
        for i in range(24, H - lag - 6, 6):  # every 6 h
            if np.isnan(x[i]) or np.isnan(x[i-24]) or np.isnan(y[i]) or np.isnan(y[min(H-1, i+lag+6)]):
                continue
            fut = np.nanmax(y[i+1:i+lag+7]) - y[i]   # rise at the gauge before the travel time + 6 h
            sig = (x[i] - x[i-24]) >= UP
            (tab if sig else base)[fut >= DOWN] += 1
    n = tab[True] + tab[False]; nb = base[True] + base[False]
    print(f"upstream rose >= {UP*100:.0f} cm/24h -> gauge rises >= {DOWN*100:.0f} cm within lag+6h: "
          f"{tab[True]}/{n} = {100*tab[True]/max(1,n):.0f}%   (without the signal: {100*base[True]/max(1,nb):.0f}% of {nb})")
