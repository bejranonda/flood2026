"""Step 3 of Q52 (owner 2026-10-04: "Continue to improve the model forecasting performance … not fake the result and error
or uncertainty to make it better"). Pre-declared input variants for the `star` ridge model, scored honestly:
  - star is trained only on hours before the backtest window and tested on the window (as forecast.evaluate);
  - the pipeline choice (best method + 10 % gate) is made on the first half of the window and scored on the second;
  - the winning variant is picked on gauge sample 1 and confirmed on a disjoint sample 2 (argv[2] = 1 or 2).
Variants: V0 today · V1 + distance from the 7-day and 30-day means · V2 + 1/3/72 h own changes · V3 + time of day
(sin/cos, Thai time, at issue and at target) · V4 recency weights (half-life 60 days) · V5 all.
Run: docker compose run --rm --no-deps -T -e PYTHONPATH=/app/src -v "$PWD/src:/app/src:ro" worker python - 200 1 < research/2026-10-04_star_variants.py"""
import collections as C, random, sys
import numpy as np
from floodwatch import db, forecast as F
N, SAMPLE = (int(sys.argv[1]) if len(sys.argv) > 1 else 200), (int(sys.argv[2]) if len(sys.argv) > 2 else 1)
rmse = lambda v: float(np.sqrt(np.mean(np.square(v))))
VARIANTS = {"V0": set(), "V1": {"long"}, "V2": {"lags"}, "V3": {"diurnal"}, "V4": {"recency"}, "V5": {"long", "lags", "diurnal", "recency"},
            "V12": {"long", "lags"}}  # V12 added after sample 1 (V1 and V2 each helped); judged on sample 2 only
if len(sys.argv) > 3:
    VARIANTS = {k: VARIANTS[k] for k in sys.argv[3].split(",")}

def feats(t, yf, eta, ybf, h, ex, opts):
    X = F.star_features(t, yf, eta, ybf, h, ex)
    cols = []
    if "long" in opts:
        cols += [yf - F.trailing_mean(yf, 24 * 7), yf - F.trailing_mean(yf, 24 * 30)]
    if "lags" in opts:
        cols += [F._lagdiff(yf, 1), F._lagdiff(yf, 3), F._lagdiff(yf, 72)]
    if "diurnal" in opts:
        a0, a1 = 2 * np.pi * ((t + 7) % 24) / 24, 2 * np.pi * ((t + 7 + h) % 24) / 24
        cols += [np.sin(a0), np.cos(a0), np.sin(a1), np.cos(a1)]
    return np.column_stack([X] + cols) if cols else X

def ridge_w(X, y, w):
    w = w / w.sum()
    mu = (X * w[:, None]).sum(0); sd = np.sqrt((((X - mu) ** 2) * w[:, None]).sum(0)) + 1e-9
    Z = (X - mu) / sd; ym = float((y * w).sum())
    b = np.linalg.solve(Z.T @ (Z * w[:, None]) * len(y) + F.STAR_RIDGE * np.eye(Z.shape[1]), Z.T @ (w * (y - ym)) * len(y))
    return lambda Xn: ((Xn - mu) / sd) @ b + ym

def star_errs(t, y, ex, errs, split, opts):
    eta = F.fit_tide(t[:split], y[:split])
    yf = F._ffill(y, F.OWN_FFILL_H); ybf = F.trailing_mean(yf, 25)
    out = {}
    for h in F.HORIZONS:
        X, tg = feats(t, yf, eta, ybf, h, ex, opts), F._star_target(y, h)
        ok = np.isfinite(X).all(1) & np.isfinite(tg); idx = np.arange(len(y))
        tr = ok & (idx < split - h)
        te = [i for i in range(split, len(y)) if ok[i] and i in errs[h]["persistence"]]
        if tr.sum() < F.STAR_MIN_TRAIN or len(te) < 0.5 * len(errs[h]["persistence"]):
            continue
        if "recency" in opts:
            f = ridge_w(X[tr], tg[tr], 0.5 ** ((split - idx[tr]) / (60 * 24)))
        else:
            f = F._ridge(X[tr], tg[tr])
        out[h] = {i: float(tg[i] - p) for i, p in zip(te, f(X[te]))}
    return out

tot = {v: {h: C.Counter() for h in F.HORIZONS} for v in VARIANTS}
ratios = {v: {h: [] for h in F.HORIZONS} for v in VARIANTS}
with db.connect() as c:
    codes = sorted(r["code"] for r in c.execute("SELECT DISTINCT code FROM forecast_run WHERE issue_time > now() - interval '3 hours'"))
    random.Random(23).shuffle(codes)
    sample = codes[(SAMPLE - 1) * N: SAMPLE * N]  # disjoint samples
    meta = {r["code"]: r for r in c.execute("SELECT code, lat, lon, in_focus FROM station WHERE code = ANY(%s)", (sample,)).fetchall()}
    cache, done = {}, 0
    for code in sample:
        m = meta.get(code)
        rows = c.execute("""SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                            AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (code, F.LOOKBACK_DAYS)).fetchall()
        if not m or len(rows) < 24 * 30:
            continue
        t, y = F.hourly_grid([r["obs_time"] for r in rows], [float(r["level_msl"]) for r in rows])
        exo = F.load_exo(c, code, m["lat"], m["lon"], cache, m["in_focus"])
        ex = F.align_exo(t, exo) if exo else None
        own, split = F._backtest_errors(t, y, None)
        if ex is None:
            continue
        done += 1
        for v, opts in VARIANTS.items():
            st = star_errs(t, y, ex, own, split, opts)
            for h in F.HORIZONS:
                errs = {**own[h], **({"star": st[h]} if h in st else {})}
                rws = F.common_rows(errs)
                if len(rws) < 60 or "star" not in errs:
                    continue
                e = {k: np.array([vv[i] for i in rws]) for k, vv in errs.items()}
                half = len(rws) // 2
                A = {k: x[:half] for k, x in e.items()}; B = {k: x[half:] for k, x in e.items()}
                cand = [k for k in e if k != "persistence"]
                best = min(cand, key=lambda x: rmse(A[x]))
                chosen = best if rmse(A[best]) < (1 - F.SKILL_GATE) * rmse(A["persistence"]) else "persistence"
                s = tot[v][h]; pB = rmse(B["persistence"])
                s["n"] += 1; s["star_all"] += rmse(e["star"]) / rmse(e["persistence"])
                ratios[v][h].append(rmse(B[chosen]) / pB if pB > 0 else 1.0)
                s["sumB"] += rmse(B[chosen]); s["sumP"] += pB
                s["model"] += chosen != "persistence"; s["star"] += chosen == "star"
                s["held"] += chosen != "persistence" and rmse(B[chosen]) < (1 - F.SKILL_GATE) * pB
                s["worse"] += chosen != "persistence" and rmse(B[chosen]) > pB
        if done % 25 == 0: print("…", done, flush=True)
print(f"sample {SAMPLE}: gauges with star inputs {done}")
for h in (6, 12, 24, 48, 72):
    print(f"\n=== +{h} h")
    for v in VARIANTS:
        s = tot[v][h]; n = s["n"] or 1
        print(f"{v} n {s['n']:4d} · star error / no-change (whole window) {s['star_all']/n:5.3f} · pipeline error vs no-change on B "
              f"{100*(s['sumB']/max(s['sumP'],1e-9)-1):+5.1f}% (per-gauge median {100*(np.median(ratios[v][h])-1):+5.1f}%, mean {100*(np.mean(ratios[v][h])-1):+5.1f}%) · served a model {s['model']:4d} (star {s['star']:4d}) · held ≥10 % on B {s['held']:4d} · worse on B {s['worse']:3d}")
