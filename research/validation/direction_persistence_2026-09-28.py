"""Does a measured steady trend continue? (owner 2026-09-28: "a few cm lower in a flood is significant")

For every focus gauge, every hour t of the last 45 days: fit a straight line to the hourly levels of the 24 h before
t (the same rule as qc.observed24): past change and R². Outcome: level change over the next 12 h and 24 h (3 h mean
at both ends, so a single reading cannot decide). Reports, per past-change bucket, how often the level kept moving
the same way, and the typical size of the future change. Run inside the worker image:
  docker compose run --rm --no-deps -e PYTHONPATH=/app/src -v "$PWD/src:/app/src" -v "$PWD/research:/app/research" \
      worker python research/validation/direction_persistence_2026-09-28.py
"""
import collections

import numpy as np

from floodwatch import db
from floodwatch.forecast import hourly_grid

DAYS = 45
with db.connect() as c:
    rows = c.execute(
        """SELECT o.code, o.obs_time, o.level_msl, s.river, s.agency FROM observation o JOIN station s USING (code)
           WHERE s.in_focus AND o.quality_flag='ok' AND o.level_msl IS NOT NULL
             AND o.obs_time > now() - make_interval(days => %s) ORDER BY o.code, o.obs_time""", (DAYS,)).fetchall()
    erratic = set((db.get_state(c, "erratic_gauges") or {}).keys())
ser, meta = collections.defaultdict(lambda: ([], [])), {}
for r in rows:
    ser[r["code"]][0].append(r["obs_time"]); ser[r["code"]][1].append(float(r["level_msl"]))
    meta[r["code"]] = ("river" if (r["river"] or "").startswith("แม่น้ำ") else "khlong", r["agency"])

xs = np.arange(25, dtype=float)
xc = xs - xs.mean()
sxx = (xc ** 2).sum()


def mean3(y, i):
    w = y[max(0, i - 1):i + 2]
    w = w[np.isfinite(w)]
    return w.mean() if len(w) else np.nan


buckets = collections.defaultdict(list)  # (kind, bucket) -> [(fut12, fut24)]
for code, (t, v) in ser.items():
    if code in erratic or code.startswith("TEST"):
        continue
    _, y = hourly_grid(t, v)
    n = len(y)
    for i in range(24, n - 25, 1):
        w = y[i - 24:i + 1]
        if not np.isfinite(w).all():
            continue
        b = (xc * (w - w.mean())).sum() / sxx
        res = w - (w.mean() + b * xc)
        ss = ((w - w.mean()) ** 2).sum()
        r2 = 1 - (res ** 2).sum() / ss if ss > 0 else 1.0
        past = b * 24
        now, f12, f24 = mean3(y, i), mean3(y, i + 12), mean3(y, i + 24)
        if not (np.isfinite(now) and np.isfinite(f12) and np.isfinite(f24)):
            continue
        cm = round(past * 100)
        steady = r2 >= 0.5
        if abs(cm) < 2:
            bk = "flat <2"
        elif not steady:
            bk = "mixed"
        else:
            size = "2-4" if abs(cm) < 5 else "5-19" if abs(cm) < 20 else ">=20"
            bk = ("fall " if cm < 0 else "rise ") + size
        buckets[(meta[code][0], bk)].append((f12 - now, f24 - now, past))

order = ["fall >=20", "fall 5-19", "fall 2-4", "flat <2", "rise 2-4", "rise 5-19", "rise >=20", "mixed"]
print(f"{'kind':7} {'past 24 h':10} {'n':>7}  {'same dir 12h':>12} {'same dir 24h':>12}  "
      f"{'next 12h cm (25/50/75%)':>24}  {'next 24h cm (25/50/75%)':>24}  {'|next24| < 2 cm':>15}")
for kind in ("khlong", "river"):
    for bk in order:
        a = np.array(buckets.get((kind, bk), []))
        if len(a) < 50:
            continue
        sgn = -1 if bk.startswith("fall") else 1 if bk.startswith("rise") else 0
        same12 = np.mean(np.sign(a[:, 0]) == sgn) if sgn else float("nan")
        same24 = np.mean(np.sign(a[:, 1]) == sgn) if sgn else float("nan")
        q12 = np.percentile(a[:, 0] * 100, [25, 50, 75]).round(0)
        q24 = np.percentile(a[:, 1] * 100, [25, 50, 75]).round(0)
        flat = np.mean(np.abs(a[:, 1]) < 0.02)
        print(f"{kind:7} {bk:10} {len(a):7}  {same12:12.0%} {same24:12.0%}  {str(q12):>24}  {str(q24):>24}  {flat:15.0%}")
