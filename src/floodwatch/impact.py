"""Impact analysis for engineers — pilot: Kaeng Krachan Dam on the Phetchaburi River (owner 2026-10-05; D-099;
docs/plan/impact-kaeng-krachan.md).

"If the dam releases X ล้าน ลบ.ม./วัน and เขื่อนเพชร diverts D m³/s, when and how high does the water get downstream, and
does it overflow?" Method (pilot): flow passed down the river by mass balance with today's local inflow, flow → level by
each gauge's own rating curve (h = h₀ + a·Qᵇ fitted on a year of hourly pairs), arrival from learned travel times, the
bank of each gauge's own agency (never mixed, KI-217), and a flag when a flow is beyond anything the year carried.
"""
from __future__ import annotations

import math

import numpy as np

SECONDS_PER_DAY = 86400.0


def mcm_to_cms(mcm_per_day: float) -> float:
    """ล้าน ลบ.ม./วัน → m³/s (1 = 11.574)."""
    return float(mcm_per_day) * 1e6 / SECONDS_PER_DAY


def cms_to_mcm(cms: float) -> float:
    return float(cms) * SECONDS_PER_DAY / 1e6


def fit_rating(q, h) -> dict | None:
    """h = h₀ + a·Qᵇ by least squares in log space over a grid of h₀ below the lowest level; the 10-90 % residuals give the
    level range, qmin/qmax the flows the fit has seen."""
    q, h = np.asarray(q, float), np.asarray(h, float)
    ok = np.isfinite(q) & np.isfinite(h) & (q > 0.5)
    q, h = q[ok], h[ok]
    if len(q) < 100:
        return None
    lq = np.log(q)
    best = None
    for h0 in h.min() - np.geomspace(0.01, 8.0, 160):
        y = np.log(h - h0)
        b, la = np.polyfit(lq, y, 1)
        pred = h0 + math.exp(la) * q ** b
        sse = float(np.sum((h - pred) ** 2))
        if best is None or sse < best[0]:
            best = (sse, h0, math.exp(la), b, pred)
    _, h0, a, b, pred = best
    res = h - pred
    return {"h0": float(h0), "a": float(a), "b": float(b), "rmse": float(np.sqrt(np.mean(res ** 2))),
            "res": [float(np.quantile(res, 0.1)), float(np.quantile(res, 0.9))],
            "qmin": float(q.min()), "qmax": float(q.max()), "n": int(len(q))}


def level_at(r: dict, q: float) -> float:
    return r["h0"] + r["a"] * max(float(q), 0.0) ** r["b"]


def best_lag(up, down, max_lag: int = 72, min_pairs: int = 500) -> int | None:
    """Hours by which `down`'s 24 h change best follows `up`'s (correlation), 0..max_lag; None with too few pairs."""
    def d24(x):
        x = np.asarray(x, float)
        o = np.full(len(x), np.nan)
        o[24:] = x[24:] - x[:-24]
        return o
    a, b = d24(up), d24(down)
    best = None
    for lag in range(max_lag + 1):
        x, y = (a[:len(a) - lag], b[lag:]) if lag else (a, b)
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < min_pairs or np.std(x[m]) == 0 or np.std(y[m]) == 0:
            continue
        r = float(np.corrcoef(x[m], y[m])[0, 1])
        if best is None or r > best[1]:
            best = (lag, r)
    return None if best is None else best[0]


def diversion_now(q18, q10, lag: int, hours: int = 72) -> float | None:
    """Today's diversion at เขื่อนเพชร estimated from the data: the median of B.18's flow `lag` hours earlier minus B.10's
    flow over the last `hours` hours (≥ 0)."""
    q18, q10 = np.asarray(q18, float), np.asarray(q10, float)
    n = len(q10)
    idx = np.arange(max(lag, n - hours), n)
    d = q18[idx - lag] - q10[idx]
    d = d[np.isfinite(d)]
    return None if len(d) < 6 else max(0.0, float(np.median(d)))


ASSUMPTIONS = (
    "สมมติว่าระบายในอัตรานี้ต่อเนื่องอย่างน้อย 1 วัน (การระบายสั้น ๆ ถึงท้ายน้ำต่ำกว่านี้)",
    "น้ำท่าระหว่างทาง (local inflow) ใช้ค่าวันนี้คงที่",
    "ระดับน้ำจาก rating curve ของแต่ละสถานีที่หาจากข้อมูลของเราเอง 1 ปี; เกินช่วงที่เคยเห็นคือการต่อเส้นโค้งออกไป",
)


def whatif(state: dict, release_mcm: float, diversion_cms: float | None = None) -> dict:
    """The what-if table: each point's flow, level range (m MSL of its own agency), margin to its own bank, overflow flag
    ("yes": the expected level reaches the bank; "possible": only the upper end does), arrival window and whether the flow is
    outside what the year carried."""
    R = mcm_to_cms(release_mcm)
    d_now = float(state.get("diversion_default") or 0.0)
    D = d_now if diversion_cms is None else max(0.0, float(diversion_cms))
    dam = state.get("dam") or {}
    rows, flows = [], {}
    prev = None
    for p in state["points"]:
        role = p["role"]
        if role == "below_dam":
            r_now = mcm_to_cms(dam["released_mcm"]) if dam.get("released_mcm") is not None else (p.get("q_now") or 0.0)
            flow = R + max(0.0, (p.get("q_now") or 0.0) - r_now)
        elif role == "after_diversion":
            reached = max(0.0, (p.get("q_up_lagged") or 0.0) - d_now)
            flow = max(0.0, prev - D) + max(0.0, (p.get("q_now") or 0.0) - reached)
        elif role == "river":
            flow = max(0.0, prev + (p.get("q_now") or 0.0) - (p.get("q_up_lagged") or 0.0))
        else:  # city: no flow of its own; its rating maps the flow of `rating_from` to its level
            flow = None
        if flow is not None:
            flows[p["code"]] = flow
            prev = flow
        q_for = flow if flow is not None else flows.get(p.get("rating_from"))
        r = p.get("rating")
        level = outside = margin = overflow = None
        if r and q_for is not None:
            mid = level_at(r, q_for)
            level = [mid + r["res"][0], mid, mid + r["res"][1]]
            outside = bool(q_for > r["qmax"])
            if p.get("bank") is not None:
                margin = p["bank"] - mid
                overflow = "yes" if mid >= p["bank"] else "possible" if level[2] >= p["bank"] else "no"
        rows.append({"code": p["code"], "name_th": p.get("name_th"), "agency": p.get("agency"), "role": role,
                     "flow_cms": None if flow is None else round(flow, 1), "level": level, "bank": p.get("bank"),
                     "margin_m": margin, "overflow": overflow, "outside": outside, "arrival_h": p.get("window"),
                     "h_now": p.get("h_now"), "q_now": p.get("q_now")})
    return {"release_mcm": float(release_mcm), "release_cms": R, "diversion_cms": D, "diversion_default": diversion_cms is None,
            "dam": dam, "rows": rows, "assumptions": list(ASSUMPTIONS)}


# --- the Kaeng Krachan case: state from the database (rebuilt hourly by the worker) -------------------------------------
CASES = {
    "kaeng-krachan": {
        "title": "เขื่อนแก่งกระจาน → แม่น้ำเพชรบุรี", "dam_ids": {"RID": 13, "EGAT": 57},
        # no hourly dam data: from the dam to B.18 (~21 km) a few hours, an assumption stated on the page
        "dam_to_first_h": [2, 8], "dam_km": 21,
        "points": [{"code": "B.18", "role": "below_dam"}, {"code": "B.10", "role": "after_diversion"},
                   {"code": "B.16", "role": "river"}, {"code": "B.15", "role": "city", "rating_from": "B.16"},
                   {"code": "PCH001", "role": "city", "rating_from": "B.16"}],
    },
}
HOURLY_SQL = """SELECT date_trunc('hour', obs_time) AS t, avg(level_msl) AS h, avg(discharge) AS q FROM observation
                WHERE code=%s AND quality_flag='ok' AND obs_time > now() - interval '370 days' GROUP BY 1 ORDER BY 1"""


def _window(lag: int) -> list[int]:
    return [max(0, int(round(lag * 0.8))) if lag > 15 else max(0, lag - 3), int(round(lag * 1.2)) if lag > 15 else lag + 3]


def _last(x, idx: int, hours: int = 6):
    for k in range(idx, max(-1, idx - hours), -1):
        if np.isfinite(x[k]):
            return float(x[k])
    return None


def replay(q18, q10, q16, hcity: dict, lags: dict, cut: int) -> dict:
    """Validation (D-099): from hour `cut` on (the last 40 % of the year), B.18's measured flow is the "release" and the
    model's levels at the learned lags are compared with what was measured — against simply keeping today's level. Rating
    curves and lags are fitted on the hours before `cut` only (passed in `lags`/fitted here), so the replay is out of sample."""
    n = len(q18)
    l10, l16 = lags["B.10"], lags["B.16"]
    r10 = fit_rating(q10[:cut], lags["h"]["B.10"][:cut])
    r16 = fit_rating(q16[:cut], lags["h"]["B.16"][:cut])
    rc = {c: fit_rating(np.roll(q16, lags[c] - l16)[:cut], h[:cut]) for c, h in hcity.items()}
    acc: dict = {}

    def add(code, pred_mid, res, obs, now_level, big):
        if pred_mid is None or not np.isfinite(obs) or not np.isfinite(now_level):
            return
        a = acc.setdefault(code, {"n": 0, "model": 0.0, "keep": 0.0, "inside": 0, "n_big": 0, "model_big": 0.0, "keep_big": 0.0})
        a["n"] += 1
        a["model"] += abs(pred_mid - obs)
        a["keep"] += abs(now_level - obs)
        a["inside"] += (pred_mid + res[0]) <= obs <= (pred_mid + res[1])
        if big:
            a["n_big"] += 1
            a["model_big"] += abs(pred_mid - obs)
            a["keep_big"] += abs(now_level - obs)

    for t in range(max(cut, 96), n - max(list(lags[c] for c in hcity) + [l16]) - 1, 3):
        if not (np.isfinite(q18[t]) and np.isfinite(q10[t]) and np.isfinite(q16[t]) and np.isfinite(q18[t - l10])):
            continue
        D = diversion_now(q18[:t + 1], q10[:t + 1], l10) or 0.0
        local10 = max(0.0, q10[t] - max(0.0, q18[t - l10] - D))
        p10 = max(0.0, q18[t] - D) + local10
        up16 = q10[t - (l16 - l10)] if t - (l16 - l10) >= 0 else np.nan
        if not np.isfinite(up16):
            continue
        p16 = max(0.0, p10 + q16[t] - up16)
        big = np.isfinite(q18[t - 24]) and abs(q18[t] - q18[t - 24]) >= 15
        if r10:
            add("B.10", level_at(r10, p10), r10["res"], lags["h"]["B.10"][t + l10], lags["h"]["B.10"][t], big)
        if r16:
            add("B.16", level_at(r16, p16), r16["res"], lags["h"]["B.16"][t + l16], lags["h"]["B.16"][t], big)
        for c, h in hcity.items():
            if rc.get(c):
                add(c, level_at(rc[c], p16), rc[c]["res"], h[t + lags[c]], h[t], big)
    out = {}
    for c, a in acc.items():
        n_ = max(1, a["n"])
        out[c] = {"n": a["n"], "mae_cm": round(100 * a["model"] / n_, 1), "keep_mae_cm": round(100 * a["keep"] / n_, 1),
                  "inside_pct": round(100 * a["inside"] / n_), "n_big": a["n_big"],
                  "mae_big_cm": round(100 * a["model_big"] / a["n_big"], 1) if a["n_big"] else None,
                  "keep_big_cm": round(100 * a["keep_big"] / a["n_big"], 1) if a["n_big"] else None}
    return out


def build_state(c, case: str = "kaeng-krachan", now=None) -> dict:
    """Everything the page needs, from our database: ratings and lags fitted on the year, today's values, the dam's latest
    records, today's diversion and the replay (validation)."""
    import datetime as dt
    cfg = CASES[case]
    now = now or dt.datetime.now(dt.timezone.utc)
    codes = [p["code"] for p in cfg["points"]]
    raw = {code: c.execute(HOURLY_SQL, (code,)).fetchall() for code in codes}
    t0 = min(r[0]["t"] for r in raw.values() if r)
    n = int((now.replace(minute=0, second=0, microsecond=0) - t0).total_seconds() // 3600) + 1
    H, Q = {}, {}
    for code, rows in raw.items():
        h, q = np.full(n, np.nan), np.full(n, np.nan)
        for r in rows:
            k = int((r["t"] - t0).total_seconds() // 3600)
            if 0 <= k < n:
                h[k] = r["h"] if r["h"] is not None else np.nan
                q[k] = r["q"] if r["q"] is not None else np.nan
        H[code], Q[code] = h, q
    meta = {r["code"]: r for r in c.execute("SELECT code, name_th, agency, bank_msl FROM station WHERE code = ANY(%s)", (codes,)).fetchall()}
    q18, q10, q16 = Q["B.18"], Q["B.10"], Q["B.16"]
    lags = {"B.18": 0, "B.10": best_lag(q18, q10) or 32}
    lags["B.16"] = max(lags["B.10"], best_lag(q18, q16) or 43)
    for p in cfg["points"]:
        if p["role"] == "city":
            lags[p["code"]] = max(lags["B.16"], best_lag(q18, H[p["code"]]) or 48)
    idx = n - 1
    points = []
    for p in cfg["points"]:
        code, m = p["code"], meta.get(p["code"]) or {}
        if p["role"] == "city":
            shift = lags[code] - lags[p["rating_from"]]
            rating = fit_rating(np.roll(Q[p["rating_from"]], shift)[:n], H[code])
        else:
            rating = fit_rating(Q[code], H[code])
        up = {"after_diversion": ("B.18", lags["B.10"]), "river": ("B.10", lags["B.16"] - lags["B.10"])}.get(p["role"])
        dam_lo, dam_hi = cfg["dam_to_first_h"]
        w = _window(lags[code])
        points.append({**p, "name_th": m.get("name_th"), "agency": m.get("agency"), "bank": m.get("bank_msl"),
                       "lag_h": lags[code], "window": [w[0] + dam_lo, w[1] + dam_hi], "rating": rating,
                       "q_now": _last(Q[code], idx), "h_now": _last(H[code], idx),
                       "q_up_lagged": _last(Q[up[0]], idx - up[1]) if up else None})
    dams = {r["dam_id"]: dict(r) for r in c.execute(
        """SELECT DISTINCT ON (dam_id) dam_id, agency, name_th, dam_date::text AS dam_date, storage_mcm, storage_pct, inflow_mcm,
                  released_mcm, spilled_mcm, level_m FROM dam_daily WHERE dam_id = ANY(%s) ORDER BY dam_id, dam_date DESC""",
        (list(cfg["dam_ids"].values()),)).fetchall()}
    rid, egat = dams.get(cfg["dam_ids"]["RID"]), dams.get(cfg["dam_ids"]["EGAT"])
    cut = int(n * 0.6)
    lags_cut = {"B.10": best_lag(q18[:cut], q10[:cut]) or lags["B.10"]}
    lags_cut["B.16"] = max(lags_cut["B.10"], best_lag(q18[:cut], q16[:cut]) or lags["B.16"])
    city = {p["code"]: H[p["code"]] for p in cfg["points"] if p["role"] == "city"}
    for code in city:
        lags_cut[code] = max(lags_cut["B.16"], best_lag(q18[:cut], H[code][:cut]) or lags[code])
    lags_cut["h"] = {"B.10": H["B.10"], "B.16": H["B.16"]}
    data_time = max((r[-1]["t"] for r in raw.values() if r), default=None)
    return {"case": case, "title": cfg["title"], "dam": {**(rid or {}), "egat": egat}, "dam_km": cfg["dam_km"],
            "dam_to_first_h": cfg["dam_to_first_h"], "points": points,
            "diversion_default": round(diversion_now(q18, q10, lags["B.10"]) or 0.0, 1),
            "validation": {"from": (t0 + dt.timedelta(hours=cut)).isoformat(), "points": replay(q18, q10, q16, city, lags_cut, cut)},
            "data_time": data_time.isoformat() if data_time else None, "built_at": now.isoformat()}


def run() -> dict:
    """Worker task (hourly): rebuild the case state and store it in collector_state 'impact_kaeng_krachan'."""
    from floodwatch import db
    with db.connect() as c:
        state = build_state(c)
        db.set_state(c, "impact_kaeng_krachan", state)
        c.commit()
    return state
