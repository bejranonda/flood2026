"""KI-292: `star` forecast a rise right after a steep measured fall (SKG007: +0.55 m forecast, −0.30 m measured). Honest
test of damping: when the 24 h trend at the issue hour opposes star's forecast change and is steep (≥ 10 cm), shrink the
forecast toward persistence. Variants on sample 1 (120 non-BMA gauges), confirmed on the disjoint sample 2; the served
method + 10 % gate chosen on the first half, scored on the second (q52_harness). Report gauges made worse.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src:/research -v "$PWD/src:/app/src:ro" \
     -v "$PWD/research:/research:ro" worker python - < research/2026-10-05_star_damping.py"""
import numpy as np
import q52_harness as H
from floodwatch import db, forecast as F

STEEP_M = 0.10
VARIANTS = {"half when opposing": lambda tr, pred: pred * 0.5,
            "fade by trend (0.5 m → 0)": lambda tr, pred: pred * max(0.0, 1 - abs(tr) / 0.5),
            "zero when opposing": lambda tr, pred: 0.0}


def damped(star_errs, t, y, rule):
    """Errors of the damped forecast: pred_star = target − err; damp when the 24 h trend opposes and is steep."""
    out = {}
    for h, errs in star_errs.items():
        tg = F._star_target(y, h)
        o = {}
        for i, e in errs.items():
            pred = tg[i] - e
            tr = y[i] - y[i - 24] if i >= 24 and np.isfinite(y[i - 24]) else 0.0
            if abs(tr) >= STEEP_M and np.sign(tr) != np.sign(pred) and pred != 0:
                pred = rule(tr, pred)
            o[i] = float(tg[i] - pred)
        out[h] = o
    return out


with db.connect_readonly() as c:
    for k in (1, 2):
        sc = H.Score()
        codes = H.sample_codes(c, 120, k, where="s.agency IS DISTINCT FROM 'BMA' AND s.lat IS NOT NULL")
        meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus, agency FROM station WHERE code = ANY(%s)", (codes,)).fetchall()}
        cache, done = {}, 0
        for code in codes:
            s = meta.get(code)
            if not s:
                continue
            t, y = H.load_series(c, code)
            if len(y) < 24 * 60:
                continue
            exo = F.load_exo(c, code, s["lat"], s["lon"], cache, s["in_focus"], s["agency"])
            if not exo:
                continue
            ex = F.align_exo(t, exo)
            own, split = F._backtest_errors(t, y, None)
            star = H.star_errs(t, y, ex, own, split)
            sc.add("star (today)", own, star)
            for name, rule in VARIANTS.items():
                sc.add(f"star, {name}", own, damped(star, t, y, rule))
            done += 1
            if done % 20 == 0:
                print("…", done, flush=True)
        print(f"\n=== sample {k}: {done} gauges")
        print(sc.report(horizons=(12, 24, 48, 72)))
