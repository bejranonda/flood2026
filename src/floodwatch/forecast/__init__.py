"""MVP forecasting: L0 persistence, L1 persistence + fitted tide, L1T + damped trend (APPROACH §3.2).

For each station the three candidates are backtested (rolling origin) on its own recent history; the best
candidate per horizon is served only if it beats persistence by > 10 % RMSE, otherwise persistence is served.
Intervals are split-conformal: empirical quantiles of the chosen method's backtest errors. Tide constants are
fitted from the station's data (D-010), never copied.
"""
from __future__ import annotations

import datetime as dt
import logging
import math

import numpy as np

from floodwatch import db, rain_cells

log = logging.getLogger(__name__)
VERSION = "star-0.3"  # v0.20.7: "recent" pace joins the ladder (one forecaster; the API override is gone)  # D-052: network space-time AR + rain competes in the backtest
HORIZONS = [1, 3, 6, 12, 24, 48, 72]
TIDE_SPEEDS = {"K1": 15.0410686, "O1": 13.9430356, "M2": 28.9841042, "S2": 30.0, "M4": 57.9682084,
               "MS4": 58.9841042}
QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
MIN_HOURS = 7 * 24
SKILL_GATE = 0.10
EVAL_HOURS = 45 * 24  # backtest the recent regime only; older history (up to a year) serves the tide fit
LOOKBACK_DAYS = 370


def hourly_grid(times: list[dt.datetime], values: list[float]) -> tuple[np.ndarray, np.ndarray]:
    """Regular hourly grid (absolute hours since epoch) holding the last valid value in each hour."""
    hrs = np.array([t.timestamp() / 3600.0 for t in times])
    vals = np.array(values, float)
    ok = np.isfinite(vals)
    hrs, vals = hrs[ok], vals[ok]
    if len(hrs) == 0:
        return np.array([]), np.array([])
    h0, h1 = math.floor(hrs.min()), math.floor(hrs.max())
    grid = np.arange(h0, h1 + 1, dtype=float)
    y = np.full(len(grid), np.nan)
    idx = (np.floor(hrs) - h0).astype(int)
    order = np.argsort(hrs)
    y[idx[order]] = vals[order]  # later values overwrite earlier ones within the hour
    return grid, y


def _design(t: np.ndarray) -> np.ndarray:
    cols = [np.ones_like(t)]
    for s in TIDE_SPEEDS.values():
        w = np.radians(s * t)
        cols += [np.cos(w), np.sin(w)]
    return np.column_stack(cols)


def fit_tide(t: np.ndarray, y: np.ndarray):
    """Least-squares harmonic fit on a 25 h-detrended series; returns eta(t) (tidal part only) or None."""
    ok = np.isfinite(y)
    if ok.sum() < 15 * 24:  # Rayleigh: >= ~15 days to separate M2/S2 and K1/O1
        return None
    base = trailing_mean(y, 25, centered=True)
    r = y - base
    m = ok & np.isfinite(r)
    coef, *_ = np.linalg.lstsq(_design(t[m]), r[m], rcond=None)
    return lambda tt: _design(np.asarray(tt, float))[:, 1:] @ coef[1:]


def trailing_mean(y: np.ndarray, w: int, centered: bool = False) -> np.ndarray:
    """Mean of the finite values in a window of w hours (trailing, or centred), NaN when fewer than w // 2 are finite.
    Vectorised with cumulative sums: it runs several times per gauge per forecast cycle (~500 gauges)."""
    n = len(y)
    ok = np.isfinite(y)
    cs = np.concatenate([[0.0], np.cumsum(np.where(ok, y, 0.0))])
    cn = np.concatenate([[0], np.cumsum(ok)])
    i = np.arange(n)
    lo, hi = (i - w // 2, i + w // 2 + 1) if centered else (i - w + 1, i + 1)
    lo, hi = np.clip(lo, 0, n), np.clip(hi, 0, n)
    cnt = cn[hi] - cn[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (cs[hi] - cs[lo]) / cnt
    out[cnt < w // 2] = np.nan
    return out


def _predict(method: str, y0: float, tide: float, h: int, slope: float) -> float:
    """tide = eta(t0+h) - eta(t0) (0 when no tide model)."""
    if method == "persistence":
        return y0
    if method == "tide":
        return y0 + tide
    return y0 + tide + (0.0 if not np.isfinite(slope) else slope * h * math.exp(-h / 48.0))


def _fit_rate(y: np.ndarray, i: int, w: int, min_n: int) -> float:
    """Straight-line pace (m/h) over the w hours ending at i; nan with fewer than min_n readings."""
    seg = y[max(0, i - w):i + 1]
    k = np.where(np.isfinite(seg))[0]
    if len(k) < min_n or k[-1] - k[0] < min_n - 1:
        return float("nan")
    x, v = k.astype(float), seg[k]
    xm = x.mean()
    return float(((x - xm) * (v - v.mean())).sum() / ((x - xm) ** 2).sum())


def recent_rate(y: np.ndarray, i: int) -> float:
    """The "recent" method's pace (m/h): the smaller of the 24 h and the last-6 h pace, 0 when they disagree (a rise
    that stopped or turned is not continued). Owner 2026-10-03 (Kgt.19A: "+75 ซม." after a 70 cm jump had levelled
    off; "I thought the trend were calculated by the model"). Backtest of the rule: research/2026-10-03_verify_text_graph.py."""
    r24, r6 = _fit_rate(y, i, 24, 12), _fit_rate(y, i, 6, 4)
    if not (np.isfinite(r24) and np.isfinite(r6)) or r24 == 0 or r6 == 0 or (r24 > 0) != (r6 > 0):
        return 0.0
    return float(math.copysign(min(abs(r24), abs(r6)), r24))


def _slope(ybar: np.ndarray, i: int) -> float:
    if i < 24 or not (np.isfinite(ybar[i]) and np.isfinite(ybar[i - 24])):
        return float("nan")
    return (ybar[i] - ybar[i - 24]) / 24.0


# --- Network space-time AR + rain ("star", D-052) -------------------------------------------------------------------
# Each gauge: change over h hours ~ own tide change + own recent trend + upstream gauges' recent change (Chao Phraya
# chain, by river km) + C.13 dam release + forecast rain over the next h hours at the nearest rain point. One ridge
# regression per gauge and horizon; it competes in the same backtest as the other methods (research 2026-09-27).
STAR_MIN_TRAIN = 30 * 24
OWN_FFILL_H = 6  # own-level gaps bridged when building features (never in the target); same in training and live
STAR_RIDGE = 1.0
FUTURE_H = 72


def rain_arrays(t: np.ndarray, hind: dict, live: dict) -> tuple[np.ndarray, np.ndarray]:
    """Hourly rain aligned to the grid `t` plus FUTURE_H hours after it: (r1, r2) = forecast issued ~1 / ~2 days
    before each hour (Open-Meteo previous runs) for the past; for the future both are the latest run (`live`).
    Keys are hour indices (unix hours). Missing hours stay NaN, so rows without rain data drop out of the fit."""
    n = len(t)
    hours = np.concatenate([t, t[-1] + np.arange(1, FUTURE_H + 1)]) if n else np.arange(0)
    r1 = np.full(len(hours), np.nan); r2 = np.full(len(hours), np.nan)
    for i, h in enumerate(hours.astype(int)):
        if i >= n and h in live:
            r1[i] = r2[i] = live[h]
        elif h in hind:
            r1[i], r2[i] = hind[h]
    return r1, r2


def _ffill(x: np.ndarray, limit: int) -> np.ndarray:
    """Carry the last finite value over gaps of at most `limit` hours."""
    out, last, since = x.copy(), np.nan, limit + 1
    for i in range(len(out)):
        if np.isfinite(out[i]):
            last, since = out[i], 0
        else:
            since += 1
            if since <= limit and np.isfinite(last):
                out[i] = last
    return out


def _on_grid(t: np.ndarray, times, vals, ffill: int = 3) -> np.ndarray:
    tt, yy = hourly_grid(times, vals)
    m = {int(a): b for a, b in zip(tt, yy) if np.isfinite(b)}
    # carry the last value a few hours: upstream gauges report at slightly different times than the target
    return _ffill(np.array([m.get(int(a), np.nan) for a in t]), ffill)


def align_exo(t: np.ndarray, exo: dict | None) -> dict | None:
    """Raw inputs {up: [(times, vals)], q: (times, vals) | None, rain: {hind, live}} -> arrays on the grid `t`."""
    if not exo:
        return None
    rain = exo.get("rain") or {}
    r1, r2 = rain_arrays(t, rain.get("hind") or {}, rain.get("live") or {})
    return {"up": [_on_grid(t, *u) for u in exo.get("up") or []],
            "q": None if not exo.get("q") else _on_grid(t, *exo["q"]), "r1": r1, "r2": r2}


def _lagdiff(x: np.ndarray, k: int) -> np.ndarray:
    o = np.full(len(x), np.nan)
    o[k:] = x[k:] - x[:-k]
    return o


def star_features(t: np.ndarray, y: np.ndarray, eta, ybar: np.ndarray, h: int, ex: dict) -> np.ndarray:
    """Feature rows for predicting y[i+h] - y[i] from what is known at hour i (levels up to i; rain as forecast)."""
    n = len(y)
    cols = [(eta(t + h) - eta(t)) if eta else np.zeros(n), _lagdiff(y, 6), _lagdiff(y, 24), y - ybar]
    for u in ex.get("up") or []:
        cols += [_lagdiff(u, 24), _lagdiff(u, 48)]
    if ex.get("q") is not None:
        q = ex["q"]
        cols += [q, _lagdiff(q, 24), _lagdiff(q, 48)]
    c1 = np.concatenate([[0.0], np.cumsum(ex["r1"])])  # NaN propagates: rows without rain data are dropped
    c2 = np.concatenate([[0.0], np.cumsum(ex["r2"])])
    i = np.arange(n)
    near = c1[i + 1 + min(h, 24)] - c1[i + 1]
    far = (c2[i + 1 + h] - c2[i + 1 + 24]) if h > 24 else np.zeros(n)
    cols.append(near + far)
    # extra inputs known at hour i (e.g. measured daily rain of complete days, Q43); already aligned to `t`
    cols += [np.asarray(x, float) for x in ex.get("extra") or []]
    return np.column_stack(cols)


def _ridge(X: np.ndarray, y: np.ndarray):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    w = np.linalg.solve(Z.T @ Z + STAR_RIDGE * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    ym = y.mean()
    return lambda Xn: ((Xn - mu) / sd) @ w + ym


def _star_target(y: np.ndarray, h: int) -> np.ndarray:
    tg = np.full(len(y), np.nan)
    tg[:-h] = y[h:] - y[:-h]
    return tg


CONT_MIN_CM = 0.02   # a "steady trend" (same rule as qc.observed24): >= 2 cm over the last 24 h ...
CONT_MIN_R2 = 0.5    # ... along a straight line
CONT_HORIZONS = (12, 24, 48)


def _mean3(y: np.ndarray, i: int) -> float:
    w = y[max(0, i - 1):i + 2]
    w = w[np.isfinite(w)]
    return float(w.mean()) if len(w) else float("nan")


def continuation(y: np.ndarray, start: int) -> dict:
    """How often a steady measured 24 h trend kept its direction at this gauge (owner 2026-09-28: a few cm matter;
    D-060). For every hour i >= start with a steady trend in the 24 h before it, the change over the next h hours (3 h
    means at both ends). Returns {h: {"fall"|"rise": {"n", "hit", "q"}}}: q = 5/25/50/75/95 % of that change."""
    xc = np.arange(25, dtype=float) - 12.0
    sxx = float((xc ** 2).sum())
    acc: dict = {h: {"fall": [], "rise": []} for h in CONT_HORIZONS}
    for i in range(max(start, 24), len(y)):
        w = y[i - 24:i + 1]
        if not np.isfinite(w).all():
            continue
        b = float((xc * (w - w.mean())).sum() / sxx)
        ss = float(((w - w.mean()) ** 2).sum())
        r2 = 1 - float(((w - (w.mean() + b * xc)) ** 2).sum()) / ss if ss > 0 else 1.0
        wiggle = math.sqrt(float(((w - (w.mean() + b * xc)) ** 2).mean()))
        if abs(b * 24) < CONT_MIN_CM or (r2 < CONT_MIN_R2 and (wiggle >= 0.05 or wiggle > abs(b * 24) / 2)):
            continue  # same trend rule as qc.observed24
        now = _mean3(y, i)
        for h in CONT_HORIZONS:
            if i + h + 1 < len(y):
                f = _mean3(y, i + h)
                if np.isfinite(now) and np.isfinite(f):
                    acc[h]["fall" if b < 0 else "rise"].append(f - now)
    out: dict = {}
    for h, d in acc.items():
        for k, v in d.items():
            if v:
                a = np.array(v)
                hit = float(np.mean(a < 0) if k == "fall" else np.mean(a > 0))
                out.setdefault(h, {})[k] = {"n": int(len(a)), "hit": round(hit, 3),
                                            "q": [round(float(np.quantile(a, q)), 3) for q in QUANTILES]}
    return out


def evaluate(t: np.ndarray, y: np.ndarray, ex: dict | None = None) -> dict:
    """Rolling-origin backtest on the last EVAL_HOURS (or the last 40 % of a short record). The tide used in the
    backtest is fitted only on data before the window (no leakage). Returns per-horizon choice, skill, residuals."""
    n = len(y)
    split = max(int(n * 0.6), n - EVAL_HOURS)
    eta = fit_tide(t[:split], y[:split])
    methods = ["persistence"] + (["tide", "tide_trend"] if eta else ["trend"]) + ["recent"]
    ybar = trailing_mean(y, 25)
    etag = eta(t) if eta else np.zeros(n)
    errs = {h: {m: {} for m in methods} for h in HORIZONS}  # row index -> error, so methods compare on the same rows
    for i in range(split, n):
        if not np.isfinite(y[i]):
            continue
        sl = _slope(ybar, i)
        rr = recent_rate(y, i)
        for h in HORIZONS:
            j = i + h
            if j >= n or not np.isfinite(y[j]):
                continue
            for m in methods:
                tide = 0.0 if m == "trend" else etag[j] - etag[i]
                p = _predict("tide_trend" if m in ("trend", "recent") else m, y[i], tide, h, rr if m == "recent" else sl)
                errs[h][m][i] = y[j] - p
    if ex:  # star: trained only on targets that end before the window, tested on the window (no leakage)
        yf = _ffill(y, OWN_FFILL_H)
        ybf = trailing_mean(yf, 25)
        for h in HORIZONS:
            X, tg = star_features(t, yf, eta, ybf, h, ex), _star_target(y, h)
            ok = np.isfinite(X).all(1) & np.isfinite(tg)
            idx = np.arange(n)
            tr = ok & (idx < split - h)
            te = [i for i in range(split, n) if ok[i] and i in errs[h]["persistence"]]
            if tr.sum() < STAR_MIN_TRAIN or len(te) < 0.5 * len(errs[h]["persistence"]):
                continue  # not enough inputs over the window: compare only the gauge's own methods
            pred = _ridge(X[tr], tg[tr])(X[te])
            errs[h]["star"] = {i: float(tg[i] - p) for i, p in zip(te, pred)}
    result = {}
    cont = continuation(y, split)
    for h in HORIZONS:
        rows = set(errs[h]["persistence"])
        for m in errs[h]:
            rows &= set(errs[h][m])  # with star present: only rows every method could forecast
        rows = sorted(rows)
        if len(rows) < 30:
            continue
        e = {m: np.array([v[i] for i in rows]) for m, v in errs[h].items()}
        rmse = {m: float(np.sqrt(np.mean(v ** 2))) for m, v in e.items() if len(v)}
        best = min(rmse, key=rmse.get)
        skill = 1 - rmse[best] / rmse["persistence"] if rmse["persistence"] > 0 else 0.0
        chosen = best if (best == "persistence" or skill > SKILL_GATE) else "persistence"
        res = e[chosen]
        result[h] = {"method": chosen, "rmse": rmse, "skill_vs_persistence": round(skill, 3) if chosen != "persistence" else 0.0,
                     "n": int(len(res)), "q": [float(np.quantile(res, q)) for q in QUANTILES],
                     "coverage90_backtest": float(np.mean((res >= np.quantile(res, 0.05)) & (res <= np.quantile(res, 0.95)))),
                     # every method's error quantiles, so the live path can fall back with the right band
                     "q_all": {m: [float(np.quantile(v, q)) for q in QUANTILES] for m, v in e.items() if len(v)},
                     "cont": cont.get(h)}  # D-060: does a steady measured trend keep its direction here?
    return result


def classify_status(level: float | None, bank: float | None, ground: float | None) -> tuple[str, float | None]:
    """Status relative to bank (heuristic thresholds, ⚠️ to calibrate against official levels; KNOWLEDGE §6)."""
    if level is None or bank is None:
        return "unknown", None
    if ground is not None and bank > ground:
        pct = (level - ground) / (bank - ground) * 100.0
    else:
        pct = None
    if level >= bank:
        return "critical", pct
    if pct is None:
        return ("warning" if bank - level < 0.3 else "normal"), pct
    if pct >= 90:
        return "warning", pct
    if pct >= 70:
        return "watch", pct
    return "normal", pct


MODEL_MAX_AGE_H = 20      # the backtest (evaluate) is redone about daily ...
MODEL_MAX_GROWTH = 1.2    # ... or at once when the history grew by 20 % (a backfill arrived)


def ev_from_json(skill: dict) -> dict:
    """A stored backtest (payload["skill"], horizons as strings in jsonb) back to evaluate()'s int-keyed form."""
    return {int(h): v for h, v in (skill or {}).items()}


def model_is_fresh(row: dict | None, n_rows: int, now: dt.datetime) -> bool:
    """True when a cached backtest (forecast_model row) may be reused for a gauge with `n_rows` readings."""
    if not row or row.get("trained_at") is None:
        return False
    sk = row.get("payload")
    if isinstance(sk, dict) and sk and not any("recent" in (v or {}).get("rmse", {}) for v in sk.values()):
        return False  # stored before the "recent" method joined the ladder (v0.20.7): backtest again
    return (now - row["trained_at"]).total_seconds() < MODEL_MAX_AGE_H * 3600 and n_rows <= row["n_rows"] * MODEL_MAX_GROWTH


def forecast_station(code: str, times: list[dt.datetime], values: list[float], bank: float | None,
                     rain_next24: float | None, exo: dict | None = None, ev: dict | None = None) -> dict | None:
    """The 72 h path for one gauge. `ev`: a cached backtest (forecast_model, D-064); None runs evaluate() here."""
    t, y = hourly_grid(times, values)
    if len(y) == 0:
        return None
    last = int(np.max(np.where(np.isfinite(y))[0]))
    t, y = t[: last + 1], y[: last + 1]
    y0, t0 = float(y[-1]), float(t[-1])
    issue = dt.datetime.fromtimestamp(t0 * 3600, tz=dt.timezone.utc)
    enough = np.isfinite(y).sum() >= MIN_HOURS
    ex = align_exo(t, exo) if enough else None
    ev = (ev if ev is not None else evaluate(t, y, ex)) if enough else {}
    eta = fit_tide(t, y) if enough else None
    ybar = trailing_mean(y, 25)
    sl = _slope(ybar, len(y) - 1)
    rr = recent_rate(y, len(y) - 1)
    fut = eta(t0 + np.arange(0, 73, dtype=float)) if eta else np.zeros(73)

    yf = _ffill(y, OWN_FFILL_H) if ex else y
    ybf = trailing_mean(yf, 25) if ex else ybar

    def star_now(hh: int) -> float | None:
        """Live star forecast for hh hours: fit on all complete rows, apply to the latest hour (today's inputs)."""
        X, tg = star_features(t, yf, eta, ybf, hh, ex), _star_target(y, hh)
        ok = np.isfinite(X).all(1) & np.isfinite(tg)
        if ok.sum() < STAR_MIN_TRAIN or not np.isfinite(X[-1]).all():
            return None  # e.g. an upstream gauge has not reported yet
        return float(y0 + _ridge(X[ok], tg[ok])(X[-1:])[0])

    path = []
    for hh in range(1, 73):
        hb = next((h for h in HORIZONS if h >= hh), 72)
        e = ev.get(hb)
        method = e["method"] if e else "persistence"
        p = star_now(hh) if method == "star" else None
        if method == "star" and p is None:  # fall back to the best of the gauge's own methods for this horizon
            own = {m: r for m, r in e["rmse"].items() if m != "star"}
            method = min(own, key=own.get)
        if p is None:
            m = "tide_trend" if method in ("trend", "recent") else method
            p = _predict(m, y0, 0.0 if method == "trend" else float(fut[hh] - fut[0]), hh, rr if method == "recent" else sl)
        if e:
            lo_h = max([h for h in HORIZONS if h <= hh and h in ev], default=hb)
            w = 0.0 if hb == lo_h else (hh - lo_h) / (hb - lo_h)
            qa = ev[lo_h].get("q_all", {}).get(method, ev[lo_h]["q"])
            qb = e.get("q_all", {}).get(method, e["q"])
            q = [(1 - w) * a + w * b for a, b in zip(qa, qb)]
            path.append({"h": hh, "method": method, "q": [round(p + qi, 3) for qi in q]})
        else:
            path.append({"h": hh, "method": method, "q": None, "p": round(p, 3)})
    med12 = path[11]["q"][2] if path[11]["q"] else None
    trend = "unknown"
    if med12 is not None:
        half50 = (path[11]["q"][3] - path[11]["q"][1]) / 2
        d = med12 - y0
        trend = "steady" if abs(d) <= max(0.02, half50) else ("rising" if d > 0 else "falling")
    return {"version": VERSION, "issue_time": issue.isoformat(), "level_now": y0, "trend12": trend,
            "delta12_median": None if med12 is None else round(med12 - y0, 3), "path": path,
            "skill": {str(h): v for h, v in ev.items()}, "history_hours": int(np.isfinite(y).sum()),
            "tide_fitted": eta is not None, "outlook24": outlook24(path, bank),
            "outlook48": {"bank_chance": bank_chance(path, bank, 48)},
            "recovery": recovery(y, ybar, y0, bank, path, rain_next24)}


def outlook24(path: list[dict], bank: float | None) -> dict | None:
    """Next-24 h summary for citizens: when the median path peaks, and a coarse chance of reaching the bank.
    The chance band comes from the per-horizon conformal quantiles (max over horizons), so it is a lower bound
    on "reaches the bank at some time in 24 h" and is reported as a category, never a precise number (D-005)."""
    qs = [p for p in path[:24] if p.get("q")]
    if not qs:
        return None
    meds = [p["q"][2] for p in qs]
    peak = max(qs, key=lambda p: p["q"][2])
    # A peak window is only meaningful when a tide model drives the path; under persistence the median just
    # drifts with the per-horizon error bias (seen at CPY015: a spurious "peak" at +24 h).
    tidal = any(p["method"] in ("tide", "tide_trend") for p in qs)
    out = {"peak_h": int(peak["h"]), "peak_q": [float(v) for v in peak["q"]],
           "varies": bool(tidal and max(meds) - min(meds) > 0.05)}
    if bank is not None:
        out["bank_chance"] = bank_chance(path, bank, 24)
    return out


def bank_chance(path: list[dict], bank: float | None, hours: int) -> str | None:
    """Coarse chance that the level reaches the bank within `hours` (max over horizons of the 50/75/95 % quantiles).
    It ranks gauges well but is ~3x too high in the middle bands (25-50 % came true 12 % of the time, 2026-10-03,
    research/2026-10-03_verify_bank.py), so the UI shows the measured track record (risks.compute_records), never
    this band as a percent (D-077)."""
    qs = [p for p in path[:hours] if p.get("q")]
    if bank is None or not qs:
        return None
    top = lambda k: max(p["q"][k] for p in qs)
    return ">50%" if top(2) >= bank else "25-50%" if top(3) >= bank else "5-25%" if top(4) >= bank else "<5%"


WIDE_LIKELY_M = 0.75       # a likely (50 %) range wider than this says nothing useful to a resident; hide the numbers
                           # (D-024). The 50 % range is what the UI prints, so it is what we test (was the 90 % band > 1.5 m)
STRONG_CHANGE_M = 0.20     # colour steps for citizens (D-047): |median change| >= 20 cm is "มาก"
MEDIUM_SKILL = 0.30        # skill over "no change" needed before we call a forecast "ปานกลาง" (never "สูง")


def change_summary(q: list[float] | None, level_now: float | None, skill: dict | None) -> dict | None:
    """Rise or fall, by how much, and how sure — for one gauge at one horizon (D-047).

    `q` are the forecast quantiles (5/25/50/75/95 %) of the level at the horizon, `skill` is that horizon's backtest
    (method, skill_vs_persistence, coverage90_backtest). Everything is a *change at this gauge*, never a level at a
    user's pin (D-021). Direction uses the same rule as `trend12`: steady unless the median moves by more than
    max(2 cm, half the 50 % band). Confidence is "medium" only when a real model beats "no change" by ≥ 30 % and its
    90 % band held in the backtest; otherwise "low". There is no "high" (gauges are not the ground at the pin)."""
    if not q or level_now is None or len(q) != 5 or any(v is None for v in q):
        return None
    d = [v - level_now for v in q]
    med, half50 = d[2], (d[3] - d[1]) / 2
    direction = "steady" if abs(med) <= max(0.02, half50) else ("rising" if med > 0 else "falling")
    if direction == "steady":
        level = "steady"
    elif direction == "rising":
        level = "strong_rise" if med >= STRONG_CHANGE_M else "rise"
    else:
        level = "strong_fall" if med <= -STRONG_CHANGE_M else "fall"
    sk = skill or {}
    good_model = sk.get("method") not in (None, "persistence") and (sk.get("skill_vs_persistence") or 0) >= MEDIUM_SKILL
    calibrated = (sk.get("coverage90_backtest") or 0) >= 0.85
    wide = (q[3] - q[1]) > WIDE_LIKELY_M
    return {"dir": direction, "level": level, "median": round(med, 2),
            "likely": None if wide else [round(d[1], 2), round(d[3], 2)],
            "range90": None if wide else [round(d[0], 2), round(d[4], 2)],
            "wide": wide, "confidence": "medium" if (good_model and calibrated and not wide) else "low",
            "method": sk.get("method"), "skill": sk.get("skill_vs_persistence"),
            "coverage90": None if sk.get("coverage90_backtest") is None else round(sk["coverage90_backtest"], 2)}


def score_external(pairs: list[tuple[int, float, float, float]]) -> dict:
    """Skill of an outside forecast (e.g. HII's official one, D-050) per lead time, against "no change".
    `pairs` = (lead_h, forecast value, observed value at the valid time, observed value at the issue time)."""
    by: dict[int, list] = {}
    for lead, f, o, o0 in pairs:
        by.setdefault(int(lead), []).append((f, o, o0))
    out = {}
    for lead, rows in sorted(by.items()):
        mae = sum(abs(f - o) for f, o, _ in rows) / len(rows)
        mae_p = sum(abs(o0 - o) for _, o, o0 in rows) / len(rows)
        out[lead] = {"n": len(rows), "mae": mae, "mae_persistence": mae_p,
                     "skill": (1 - mae / mae_p) if mae_p > 0 else None}
    return out


def recovery(y, ybar, y0, bank, path, rain_next24) -> dict:
    """Milestone 1 (below bank) as a range with conditions (APPROACH §12, D-005)."""
    if bank is None:
        return {"state": "unknown"}
    if y0 < bank:
        return {"state": "below_bank"}
    if rain_next24 is not None and rain_next24 >= 30:
        return {"state": "not_estimable", "reason": "heavy_rain_forecast", "rain_next24_mm": round(rain_next24, 1)}
    def first(k):
        for p in path:
            if p["q"] and p["q"][k] < bank:
                return p["h"]
        return None
    early, mid, late = first(1), first(2), first(3)
    if mid is not None:
        return {"state": "forecast", "hours_min": early or mid, "hours_mid": mid, "hours_max": late,
                "basis": "forecast_path"}
    sl = _slope(ybar, len(y) - 1)
    if np.isfinite(sl) and sl < -0.002 and np.isfinite(ybar[-1]):
        hrs = (ybar[-1] - bank) / -sl
        if hrs > 0:
            return {"state": "extrapolated", "hours_min": round(hrs * 0.7), "hours_mid": round(hrs),
                    "hours_max": round(hrs * 1.5), "basis": "recent_recession_rate_24h"}
    return {"state": "not_estimable", "reason": "not_falling"}


DAM_CODE, DAM_KM = "C.13", 275.3  # Chao Phraya Dam (Chai Nat): its release drives every gauge downstream


def _chainage() -> dict[str, float]:
    import json
    from importlib import resources
    d = json.loads(resources.files("floodwatch").joinpath("data/chaophraya_chainage.json").read_text())["stations"]
    return {k: v["chainage_km"] for k, v in d.items()}


def upstream_of(code: str, chain: dict[str, float], k: int = 2, min_km: float = 5.0, max_km: float = 150.0) -> list[str]:
    """The k nearest gauges further up the Chao Phraya (by river km), skipping co-located ones and the dam gauge,
    whose release enters as discharge instead. Empty for gauges off the main stem (canals: rain only)."""
    if code not in chain:
        return []
    own = chain[code]
    ups = sorted((c for c, km in chain.items() if c != DAM_CODE and min_km <= km - own <= max_km), key=lambda c: chain[c] - own)
    return ups[:k]


def upstream_codes(code: str, chain: dict[str, float], in_focus: bool, learned: dict) -> list[str]:
    """Upstream gauges for star: the Chao Phraya rule for gauges on the chain; learned gauges (same basin, leading
    change, forecast.upstream) for gauges outside the focus area; none for focus canals (rain only, as proven)."""
    if code in chain or in_focus:
        return upstream_of(code, chain)
    return [u[0] for u in learned.get(code, [])]


def load_exo(c, code: str, lat: float | None, lon: float | None, cache: dict, in_focus: bool = True) -> dict | None:
    """Raw inputs for the star model from the database (cached across stations within one run). Rain: the Bangkok
    rain point for focus gauges, the gauge's 0.5° cell elsewhere (D-064)."""
    from floodwatch import rain_cells
    if lat is None:
        return None
    chain = cache.setdefault("chain", _chainage())

    def level(cd, col="level_msl"):
        key = (cd, col)
        if key not in cache:
            rows = c.execute(f"""SELECT obs_time, {col} AS v FROM observation WHERE code=%s AND quality_flag='ok'
                                AND {col} IS NOT NULL AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""",
                             (cd, LOOKBACK_DAYS)).fetchall()
            cache[key] = ([r["obs_time"] for r in rows], [float(r["v"]) for r in rows])
        return cache[key]

    pt = rain_cells.rain_point_for(in_focus, lat, lon)
    if ("rain", pt) not in cache:
        hind = {int(r["valid_time"].timestamp() // 3600): (r["day1"], r["day2"]) for r in c.execute(
            "SELECT valid_time, day1, day2 FROM rain_hindcast WHERE point=%s", (pt,)).fetchall()}
        live = {int(r["valid_time"].timestamp() // 3600): float(r["precip_mm"] or 0.0) for r in c.execute(
            """SELECT valid_time, precip_mm FROM weather_forecast WHERE point=%s
               AND issue_time=(SELECT max(issue_time) FROM weather_forecast WHERE point=%s) AND valid_time > now()""",
            (pt, pt)).fetchall()}
        cache[("rain", pt)] = {"hind": hind, "live": live}
    if not cache[("rain", pt)]["hind"]:
        return None  # no rain history yet: the star model cannot be trained
    if "learned" not in cache:
        cache["learned"] = db.get_state(c, "upstream_learned") or {}
    ups = [level(u) for u in upstream_codes(code, chain, in_focus, cache["learned"])]
    q = level(DAM_CODE, "discharge") if code in chain and chain[code] < DAM_KM else None
    return {"up": [u for u in ups if u[0]], "q": q if q and q[0] else None, "rain": cache[("rain", pt)]}


def run_all() -> int:
    """Forecast every gauge with data in the last 12 h (Bangkok and nationwide, one code path, D-064). The backtest
    is reused from forecast_model for about a day (model_is_fresh); gauges are grouped by basin so the input cache
    (upstream series, rain) stays small: it is cleared whenever the basin changes."""
    import time as _time
    from psycopg.types.json import Jsonb
    t_start = _time.monotonic()
    now = dt.datetime.now(dt.timezone.utc)
    with db.connect() as c:
        stations = c.execute(
            """SELECT s.code, s.bank_msl, s.lat, s.lon, s.in_focus, s.basin FROM station s
               WHERE s.code !~ '^TEST' AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code
                     AND o.obs_time > now() - interval '12 hours' AND o.level_msl IS NOT NULL)
               ORDER BY s.basin NULLS FIRST, s.code""").fetchall()
        rain = {r["point"]: r["mm"] for r in c.execute(
            f"""SELECT w.point, sum(w.precip_mm) AS mm FROM weather_forecast w
               JOIN ({rain_cells.LATEST_ISSUE}) l ON l.point=w.point AND l.t=w.issue_time
               WHERE w.valid_time BETWEEN now() AND now() + interval '24 hours' GROUP BY w.point""").fetchall()}
        models = {r["code"]: r for r in c.execute("SELECT code, trained_at, n_rows, payload FROM forecast_model").fetchall()}
        erratic = db.get_state(c, "erratic_gauges") or {}
    n = retrained = 0
    from floodwatch.config import DATUM_SUSPECT
    cache: dict = {}
    basin = object()
    for s in stations:
        if s["code"] in DATUM_SUSPECT:  # values not in m MSL (KI-210): never forecast or show them
            continue
        if s["code"] in erratic:  # pumps at the sensor or a faulty sensor (KI-237): the level is not predictable
            continue
        if s["basin"] != basin:  # upstream gauges share the basin: keep only what the next basin can use
            basin = s["basin"]
            cache = {k: v for k, v in cache.items() if k in ("chain", "learned")}
        with db.connect() as c:
            rows = c.execute(
                """SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                   AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (s["code"], LOOKBACK_DAYS)).fetchall()
        try:
            with db.connect() as c:
                exo = load_exo(c, s["code"], s["lat"], s["lon"], cache, s["in_focus"])
        except Exception:
            log.exception("star inputs for %s failed; own methods only", s["code"])
            exo = None
        rain24 = None
        if s["lat"] is not None and rain:
            rain24 = rain.get(rain_cells.rain_point_for(s["in_focus"], s["lat"], s["lon"]))
        model = models.get(s["code"])
        fresh = model_is_fresh(model, len(rows), now)
        try:
            fc = forecast_station(s["code"], [r["obs_time"] for r in rows], [r["level_msl"] for r in rows],
                                  s["bank_msl"], rain24, exo, ev=ev_from_json(model["payload"]) if fresh else None)
        except Exception:
            log.exception("forecast %s failed", s["code"])
            continue
        if fc:
            db.save_forecast(s["code"], now.replace(second=0, microsecond=0), VERSION, fc)
            n += 1
            if not fresh:
                retrained += 1
                with db.connect() as c:
                    c.execute("""INSERT INTO forecast_model (code, trained_at, n_rows, payload) VALUES (%s, %s, %s, %s)
                                 ON CONFLICT (code) DO UPDATE SET trained_at=EXCLUDED.trained_at, n_rows=EXCLUDED.n_rows,
                                 payload=EXCLUDED.payload""", (s["code"], now, len(rows), Jsonb(fc["skill"])))
                    c.commit()
    log.info("forecast: %d stations (%d backtests redone) in %.0f s", n, retrained, _time.monotonic() - t_start)
    return n
