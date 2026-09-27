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

from floodwatch import db

log = logging.getLogger(__name__)
VERSION = "mvp-0.1"
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
    out = np.full(len(y), np.nan)
    for i in range(len(y)):
        lo, hi = (i - w // 2, i + w // 2 + 1) if centered else (i - w + 1, i + 1)
        seg = y[max(0, lo):min(len(y), hi)]
        seg = seg[np.isfinite(seg)]
        if len(seg) >= w // 2:
            out[i] = seg.mean()
    return out


def _predict(method: str, y0: float, tide: float, h: int, slope: float) -> float:
    """tide = eta(t0+h) - eta(t0) (0 when no tide model)."""
    if method == "persistence":
        return y0
    if method == "tide":
        return y0 + tide
    return y0 + tide + (0.0 if not np.isfinite(slope) else slope * h * math.exp(-h / 48.0))


def _slope(ybar: np.ndarray, i: int) -> float:
    if i < 24 or not (np.isfinite(ybar[i]) and np.isfinite(ybar[i - 24])):
        return float("nan")
    return (ybar[i] - ybar[i - 24]) / 24.0


def evaluate(t: np.ndarray, y: np.ndarray) -> dict:
    """Rolling-origin backtest on the last EVAL_HOURS (or the last 40 % of a short record). The tide used in the
    backtest is fitted only on data before the window (no leakage). Returns per-horizon choice, skill, residuals."""
    n = len(y)
    split = max(int(n * 0.6), n - EVAL_HOURS)
    eta = fit_tide(t[:split], y[:split])
    methods = ["persistence"] + (["tide", "tide_trend"] if eta else ["trend"])
    ybar = trailing_mean(y, 25)
    etag = eta(t) if eta else np.zeros(n)
    errs = {h: {m: [] for m in methods} for h in HORIZONS}
    for i in range(split, n):
        if not np.isfinite(y[i]):
            continue
        sl = _slope(ybar, i)
        for h in HORIZONS:
            j = i + h
            if j >= n or not np.isfinite(y[j]):
                continue
            for m in methods:
                tide = 0.0 if m == "trend" else etag[j] - etag[i]
                p = _predict("tide_trend" if m == "trend" else m, y[i], tide, h, sl)
                errs[h][m].append(y[j] - p)
    result = {}
    for h in HORIZONS:
        e = {m: np.array(v) for m, v in errs[h].items()}
        if len(e["persistence"]) < 30:
            continue
        rmse = {m: float(np.sqrt(np.mean(v ** 2))) for m, v in e.items() if len(v)}
        best = min(rmse, key=rmse.get)
        skill = 1 - rmse[best] / rmse["persistence"] if rmse["persistence"] > 0 else 0.0
        chosen = best if (best == "persistence" or skill > SKILL_GATE) else "persistence"
        res = e[chosen]
        result[h] = {"method": chosen, "rmse": rmse, "skill_vs_persistence": round(skill, 3) if chosen != "persistence" else 0.0,
                     "n": int(len(res)), "q": [float(np.quantile(res, q)) for q in QUANTILES],
                     "coverage90_backtest": float(np.mean((res >= np.quantile(res, 0.05)) & (res <= np.quantile(res, 0.95))))}
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


def forecast_station(code: str, times: list[dt.datetime], values: list[float], bank: float | None,
                     rain_next24: float | None) -> dict | None:
    t, y = hourly_grid(times, values)
    if len(y) == 0:
        return None
    last = int(np.max(np.where(np.isfinite(y))[0]))
    t, y = t[: last + 1], y[: last + 1]
    y0, t0 = float(y[-1]), float(t[-1])
    issue = dt.datetime.fromtimestamp(t0 * 3600, tz=dt.timezone.utc)
    enough = np.isfinite(y).sum() >= MIN_HOURS
    ev = evaluate(t, y) if enough else {}
    eta = fit_tide(t, y) if enough else None
    ybar = trailing_mean(y, 25)
    sl = _slope(ybar, len(y) - 1)
    fut = eta(t0 + np.arange(0, 73, dtype=float)) if eta else np.zeros(73)
    path = []
    for hh in range(1, 73):
        hb = next((h for h in HORIZONS if h >= hh), 72)
        e = ev.get(hb)
        method = e["method"] if e else "persistence"
        m = "tide_trend" if method == "trend" else method
        p = _predict(m, y0, 0.0 if method == "trend" else float(fut[hh] - fut[0]), hh, sl)
        if e:
            lo_h = max([h for h in HORIZONS if h <= hh and h in ev], default=hb)
            w = 0.0 if hb == lo_h else (hh - lo_h) / (hb - lo_h)
            q = [(1 - w) * a + w * b for a, b in zip(ev[lo_h]["q"], e["q"])]
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
        top = lambda k: max(p["q"][k] for p in qs)
        out["bank_chance"] = (">50%" if top(2) >= bank else "25-50%" if top(3) >= bank
                              else "5-25%" if top(4) >= bank else "<5%")
    return out


WIDE_BAND_M = 1.5          # a 90 % band wider than this says nothing useful to a resident; hide the numbers (D-024)
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
    wide = (q[4] - q[0]) > WIDE_BAND_M
    return {"dir": direction, "level": level, "median": round(med, 2),
            "likely": None if wide else [round(d[1], 2), round(d[3], 2)],
            "range90": None if wide else [round(d[0], 2), round(d[4], 2)],
            "wide": wide, "confidence": "medium" if (good_model and calibrated and not wide) else "low",
            "method": sk.get("method"), "skill": sk.get("skill_vs_persistence"),
            "coverage90": None if sk.get("coverage90_backtest") is None else round(sk["coverage90_backtest"], 2)}


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


def run_all() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    with db.connect() as c:
        stations = c.execute(
            """SELECT s.code, s.bank_msl, s.lat, s.lon FROM station s
               WHERE s.in_focus AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code
                     AND o.obs_time > now() - interval '12 hours' AND o.level_msl IS NOT NULL)""").fetchall()
        rain = {r["point"]: r["mm"] for r in c.execute(
            """SELECT point, sum(precip_mm) AS mm FROM weather_forecast
               WHERE issue_time=(SELECT max(issue_time) FROM weather_forecast)
                 AND valid_time BETWEEN now() AND now() + interval '24 hours' GROUP BY point""").fetchall()}
    from floodwatch.config import RAIN_POINTS
    n = 0
    from floodwatch.config import DATUM_SUSPECT
    for s in stations:
        if s["code"] in DATUM_SUSPECT:  # values not in m MSL (KI-210): never forecast or show them
            continue
        with db.connect() as c:
            rows = c.execute(
                """SELECT obs_time, level_msl FROM observation WHERE code=%s AND quality_flag='ok'
                   AND obs_time > now() - make_interval(days => %s) ORDER BY obs_time""", (s["code"], LOOKBACK_DAYS)).fetchall()
        rain24 = None
        if s["lat"] is not None and rain:
            pt = min(RAIN_POINTS, key=lambda k: (RAIN_POINTS[k][0] - s["lat"]) ** 2 + (RAIN_POINTS[k][1] - s["lon"]) ** 2)
            rain24 = rain.get(pt)
        try:
            fc = forecast_station(s["code"], [r["obs_time"] for r in rows], [r["level_msl"] for r in rows],
                                  s["bank_msl"], rain24)
        except Exception:
            log.exception("forecast %s failed", s["code"])
            continue
        if fc:
            db.save_forecast(s["code"], now.replace(second=0, microsecond=0), VERSION, fc)
            n += 1
    log.info("forecast: %d stations", n)
    return n
