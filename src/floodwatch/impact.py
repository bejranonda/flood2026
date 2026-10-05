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


def shift(x, k: int):
    """x moved k hours later, NaN where nothing came before (never wraps the end of the series into its start)."""
    x = np.asarray(x, float)
    if k <= 0:
        return x.copy()
    o = np.full(len(x), np.nan)
    o[k:] = x[:-k]
    return o


def lag_fit(up, down, max_lag: int = 72, min_pairs: int = 500) -> tuple[int, float] | None:
    """(hours, r): the lag at which `down`'s 24 h change best follows `up`'s, 0..max_lag, and that correlation — how
    strongly the point follows at all; None with too few pairs."""
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
    return best


def best_lag(up, down, max_lag: int = 72, min_pairs: int = 500) -> int | None:
    """Hours by which `down`'s 24 h change best follows `up`'s (correlation), 0..max_lag; None with too few pairs."""
    f = lag_fit(up, down, max_lag, min_pairs)
    return None if f is None else f[0]


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


# --- what we ask ONWR/RID for (owner 2026-10-05: "More requested data will come soon"), with a CSV template each -------
DATA_REQUEST = [
    {"key": "diversion_dam", "th": "เขื่อนทดน้ำเพชร: การเปิดประตู ระดับน้ำหน้า/ท้ายเขื่อน และปริมาณน้ำที่ผ่านลงแม่น้ำและเข้าคลองฝั่งซ้าย/ขวา (รายชั่วโมงหรือรายวัน)",
     "why": "ผลทดสอบย้อนหลังชี้ว่าระดับน้ำท้ายน้ำขึ้นกับการบริหารเขื่อนเพชร ไม่ใช่การระบายจากแก่งกระจานโดยตรง — ข้อมูลนี้สำคัญที่สุด"},
    {"key": "events", "th": "เหตุการณ์น้ำท่วมในอดีต (เช่น ส.ค. 2561): ปริมาณระบาย ระดับน้ำสูงสุดและเวลาที่แต่ละสถานี และพื้นที่ที่ท่วมจริง",
     "why": "ข้อมูล 1 ปีของเราไม่มีการระบายขนาดใหญ่ (ดูน้ำสูงสุดที่ B.18 ในผลทดสอบย้อนหลัง) จึงตรวจสอบกรณีน้ำมากไม่ได้"},
    {"key": "dam_release", "th": "เขื่อนแก่งกระจานรายชั่วโมง (หรือรายวัน) ย้อนหลัง 2–3 ปี: ระบายรวม แยกเครื่องกำเนิดไฟฟ้า/ทางระบายน้ำล้น/ประตูระบาย น้ำไหลเข้า ระดับและปริมาตรอ่าง",
     "why": "ข้อมูลรายวันผ่าน สสน. มีสองชุด (ชป. และ กฟผ.) ที่ไม่ตรงกัน และรายวันหยาบเกินไปสำหรับช่วง 24–72 ชม."},
    {"key": "release_plan", "th": "แผนการระบายล่วงหน้า 1–7 วัน และเวลาที่ประกาศ", "why": "ทำให้คาดผลกระทบล่วงหน้าได้จริง"},
    {"key": "station_reference", "th": "ระดับตลิ่งที่สำรวจแล้ว rating curve และปริมาณน้ำวิกฤต (ความจุลำน้ำ) ที่ท่ายาง บ้านลาด และตัวเมืองเพชรบุรี",
     "why": "ใช้ตรวจสอบตลิ่งและเส้นโค้งที่เราหาจากข้อมูลเอง และใช้เป็นเกณฑ์ล้นตลิ่ง"},
]
TEMPLATES = {
    "dam_release": ["datetime_ict", "release_total_m3s", "release_turbine_m3s", "release_spillway_m3s", "release_gate_m3s",
                    "inflow_m3s", "reservoir_level_m_msl", "storage_mcm", "note"],
    "release_plan": ["issued_at_ict", "valid_from_ict", "valid_to_ict", "planned_release_m3s", "note"],
    "diversion_dam": ["datetime_ict", "upstream_level_m_msl", "downstream_level_m_msl", "gate_opening_m", "flow_to_river_m3s",
                      "left_canal_m3s", "right_canal_m3s", "note"],
    "events": ["event_name", "station_code", "start_ict", "end_ict", "peak_release_m3s", "peak_time_ict", "peak_level_m_msl",
               "flooded_area", "note"],
    "station_reference": ["station_code", "bank_left_m_msl", "bank_right_m_msl", "critical_flow_m3s", "rating_curve",
                          "surveyed_date", "note"],
}


def template_csv(name: str) -> str | None:
    """A CSV template: the header row and one example row marked as an example (times in Thai time, levels in m MSL)."""
    cols = TEMPLATES.get(name)
    if not cols:
        return None
    example = {"datetime_ict": "2026-10-05 07:00", "issued_at_ict": "2026-10-05 09:00", "valid_from_ict": "2026-10-06 00:00",
               "valid_to_ict": "2026-10-08 00:00", "start_ict": "2018-08-10 00:00", "end_ict": "2018-08-20 00:00",
               "peak_time_ict": "2018-08-15 12:00", "station_code": "B.10", "event_name": "ตัวอย่าง: ส.ค. 2561",
               "surveyed_date": "2025-01-01", "note": "ตัวอย่าง — ลบแถวนี้"}
    return ",".join(cols) + "\n" + ",".join(example.get(c, "") for c in cols) + "\n"


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


def _last_at(x, idx: int, hours: int = 6) -> tuple[float | None, int | None]:
    """The latest value at or before hour `idx` within `hours`, and its hour; (None, None) when there is none."""
    for k in range(idx, max(-1, idx - hours), -1):
        if np.isfinite(x[k]):
            return float(x[k]), k
    return None, None


def _last(x, idx: int, hours: int = 6):
    return _last_at(x, idx, hours)[0]


METHODS = ("keep", "absolute", "anchored", "gain")
READY_GAIN = 0.10  # a method must beat "keep today's level" by 10 % at ท่ายาง and บ้านลาด before the what-if is shown


def replay(q18, q10, q16, hcity: dict, lags: dict, cut: int) -> dict:
    """Validation (D-099): from hour `cut` on (the last 40 %), B.18's measured flow stands in for the release; each method
    predicts the level at each point at its learned lag and is compared with what was measured and with simply keeping
    today's level. Ratings, lags and the pass-through gain come from the hours before `cut` only.
      absolute — mass balance + the point's rating curve;  anchored — today's level + rating(q + ΔQ) − rating(q), ΔQ the
      B.18 change on its way;  gain — today's level + g·ΔQ, g learned (cm per m³/s at B.18);  keep — today's level.
    `whatif_ready`: some method beats keep by READY_GAIN at B.10 and B.16 (all cases, and big changes when there are ≥ 30)."""
    n = len(q18)
    H = dict(lags["h"], **hcity)
    l10, l16 = lags["B.10"], lags["B.16"]
    qsrc = {"B.10": q10, "B.16": q16}
    for c in hcity:
        qsrc[c] = shift(q16, lags[c] - l16)
    lag = {c: lags[c] for c in qsrc}
    rating = {c: fit_rating(qsrc[c][:cut], H[c][:cut]) for c in qsrc}
    gain = {}
    for c in qsrc:  # level change per m³/s of B.18 change, fitted before `cut`
        t = np.arange(96, max(96, cut - lag[c]), 3)
        dq, dh = q18[t] - q18[t - lag[c]], H[c][t + lag[c]] - H[c][t]
        m = np.isfinite(dq) & np.isfinite(dh)
        gain[c] = float(np.sum(dq[m] * dh[m]) / np.sum(dq[m] ** 2)) if m.sum() > 50 and np.sum(dq[m] ** 2) > 0 else 0.0
    acc = {c: {k: {"n": 0, "err": dict.fromkeys(METHODS, 0.0)} for k in ("all", "big")} for c in qsrc}
    for t in range(max(cut, 96), n - max(lag.values()) - 1, 3):
        if not (np.isfinite(q18[t]) and np.isfinite(q10[t]) and np.isfinite(q16[t]) and np.isfinite(q18[t - l10])):
            continue
        D = diversion_now(q18[:t + 1], q10[:t + 1], l10) or 0.0
        p10 = max(0.0, q18[t] - D) + max(0.0, q10[t] - max(0.0, q18[t - l10] - D))
        up16 = q10[t - (l16 - l10)]
        if not np.isfinite(up16):
            continue
        p16 = max(0.0, p10 + q16[t] - up16)
        for c in qsrc:
            r, obs, hn, qn = rating[c], H[c][t + lag[c]], H[c][t], qsrc[c][t]
            dq = q18[t] - q18[t - lag[c]]
            if r is None or not all(np.isfinite(v) for v in (obs, hn, qn, dq)):
                continue
            pred = {"keep": hn, "absolute": level_at(r, p10 if c == "B.10" else p16),
                    "anchored": hn + level_at(r, max(0.0, qn + dq)) - level_at(r, qn), "gain": hn + gain[c] * dq}
            for k in ("all",) + (("big",) if abs(dq) >= 15 else ()):
                a = acc[c][k]
                a["n"] += 1
                for mth in METHODS:
                    a["err"][mth] += abs(pred[mth] - obs)
    points = {}
    for c, kinds in acc.items():
        points[c] = {"n": kinds["all"]["n"], "n_big": kinds["big"]["n"], "gain_cm_per_cms": round(100 * gain[c], 2),
                     "methods": {m: round(float(100 * kinds["all"]["err"][m] / max(1, kinds["all"]["n"])), 1) for m in METHODS},
                     "methods_big": {m: round(float(100 * kinds["big"]["err"][m] / kinds["big"]["n"]), 1) for m in METHODS}
                     if kinds["big"]["n"] else None}

    def beats(c: str) -> bool:
        p = points.get(c)
        if not p or not p["n"]:
            return False
        best = min(p["methods"][m] for m in METHODS if m != "keep")
        ok = best <= (1 - READY_GAIN) * p["methods"]["keep"]
        if p["methods_big"] and p["n_big"] >= 30:
            ok = ok and min(p["methods_big"][m] for m in METHODS if m != "keep") <= (1 - READY_GAIN) * p["methods_big"]["keep"]
        return ok

    return {"points": points, "whatif_ready": bool(beats("B.10") and beats("B.16"))}


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
    fits = {"B.10": lag_fit(q18, q10), "B.16": lag_fit(q18, q16)}
    fits.update({p["code"]: lag_fit(q18, H[p["code"]]) for p in cfg["points"] if p["role"] == "city"})
    lags = {"B.18": 0, "B.10": fits["B.10"][0] if fits["B.10"] else 32}
    lags["B.16"] = max(lags["B.10"], fits["B.16"][0] if fits["B.16"] else 43)
    for p in cfg["points"]:
        if p["role"] == "city":
            f = fits[p["code"]]
            lags[p["code"]] = max(lags["B.16"], f[0] if f else 48)
    idx = n - 1
    points = []
    for p in cfg["points"]:
        code, m = p["code"], meta.get(p["code"]) or {}
        if p["role"] == "city":
            rating = fit_rating(shift(Q[p["rating_from"]], lags[code] - lags[p["rating_from"]]), H[code])
        else:
            rating = fit_rating(Q[code], H[code])
        up = {"after_diversion": ("B.18", lags["B.10"]), "river": ("B.10", lags["B.16"] - lags["B.10"])}.get(p["role"])
        dam_lo, dam_hi = cfg["dam_to_first_h"]
        w = _window(lags[code])
        f = fits.get(code)
        h_now, h_k = _last_at(H[code], idx)
        points.append({**p, "name_th": m.get("name_th"), "agency": m.get("agency"), "bank": m.get("bank_msl"),
                       "lag_h": lags[code], "lag_r": round(f[1], 2) if f else None,
                       "window": [w[0] + dam_lo, w[1] + dam_hi], "rating": rating,
                       "q_now": _last(Q[code], idx), "h_now": h_now,
                       "h_time": (t0 + dt.timedelta(hours=h_k)).isoformat() if h_k is not None else None,
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
    for p in points:
        if p["code"] in lags_cut:
            p["lag_range"] = sorted([lags[p["code"]], lags_cut[p["code"]]])
    lags_cut["h"] = {"B.10": H["B.10"], "B.16": H["B.16"]}
    data_time = max((r[-1]["t"] for r in raw.values() if r), default=None)
    return {"case": case, "title": cfg["title"], "dam": {**(rid or {}), "egat": egat}, "dam_km": cfg["dam_km"],
            "dam_to_first_h": cfg["dam_to_first_h"], "points": points,
            "diversion_default": round(diversion_now(q18, q10, lags["B.10"]) or 0.0, 1),
            "validation": {"from": (t0 + dt.timedelta(hours=cut)).isoformat(), **replay(q18, q10, q16, city, lags_cut, cut)},
            "data_request": DATA_REQUEST,
            "data_time": data_time.isoformat() if data_time else None, "built_at": now.isoformat()}


def run() -> dict:
    """Worker task (hourly): rebuild the case state and store it in collector_state 'impact_kaeng_krachan'."""
    from floodwatch import db
    with db.connect() as c:
        state = build_state(c)
        db.set_state(c, "impact_kaeng_krachan", state)
        c.commit()
    return state
