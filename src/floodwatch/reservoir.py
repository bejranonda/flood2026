"""7-day reservoir outlook for the impact tab's dams list (Q58, owner 2026-10-05: "continue testing" → impact tab first;
D-102). Per dam, a rain-driven inflow model fitted on 2018–2024 (ERA5 catchment rain + yesterday's inflow) is used only
for the horizons where it beat persistence by ≥ 10 % in the operational test with archived rain *forecasts*
(research/2026-10-05_q58_operational.log); elsewhere today's inflow is held. Bands are the tested residuals. Storage
follows the daily water balance with each dam's monthly loss term (the balance residual) and today's release held.
Models and their test results live in src/floodwatch/data/reservoir_models.json, written from the research log — evidence, not tuning.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

GATE_PCT = 10.0
MODELS_FILE = Path(__file__).resolve().parent / "data" / "reservoir_models.json"


def load_models() -> dict:
    """{dam_id: model} from the data file (empty when absent). The Q58 build stored its bands as quantiles of (predicted −
    observed); they are read as (observed − predicted), the convention every band here is added with (KI-309)."""
    if not MODELS_FILE.exists():
        return {}
    raw = json.loads(MODELS_FILE.read_text())
    flip = lambda b: {h: [round(-v[1], 3), round(-v[0], 3)] for h, v in (b or {}).items()}
    return {int(m["dam_id"]): {**m, "name_th": name, "band_model": flip(m.get("band_model")), "band_persist": flip(m.get("band_persist"))}
            for name, m in raw.items()}


def _passes(model: dict, h: int) -> bool:
    if not model.get("beta"):
        return False  # a persistence-only outlook (no tested model)
    g = model.get("op_gain") or {}
    key = "3" if h <= 3 else "7"
    v = g.get(key)
    return v is not None and float(v) >= GATE_PCT


MIN_INFLOW_DAYS = 200


def persistence_model(dam_id: int, name_th: str, inflow: dict) -> dict | None:
    """For a dam without a tested model: hold today's inflow, band = the dam's own 10–90 % inflow change after 1–7 days
    over its stored daily inflow (≥ MIN_INFLOW_DAYS); None with less history (no outlook rather than a made-up one)."""
    days = sorted(d for d, v in inflow.items() if v is not None)
    if len(days) < MIN_INFLOW_DAYS:
        return None
    idx = {d: i for i, d in enumerate(days)}
    vals = [float(inflow[d]) for d in days]
    if not any(vals):
        return None  # inflow only ever reported as 0 (ปากมูล): nothing to hold
    band, pairs = {}, 0
    for h in range(1, 8):
        ch = []
        for i, d in enumerate(days):
            nxt = (dt.date.fromisoformat(d) + dt.timedelta(days=h)).isoformat()
            j = idx.get(nxt)
            if j is not None:
                ch.append(vals[j] - vals[i])
        if len(ch) < MIN_INFLOW_DAYS - 10:
            return None
        ch.sort()
        q = lambda f: ch[min(len(ch) - 1, max(0, int(round(f * (len(ch) - 1)))))]
        band[str(h)] = [round(q(0.1), 3), round(q(0.9), 3)]
        pairs = max(pairs, len(ch))
    return {"dam_id": dam_id, "name_th": name_th, "beta": None, "method": "persistence", "op_gain": {"1": None, "3": None, "7": None},
            "bias": {}, "band_model": {}, "band_persist": band, "loss_by_month": {}, "test_days": pairs,
            "test_from": days[0], "test_to": days[-1], "points": [],
            "source": "the dam's own daily inflow (HII), persistence band — no tested model"}


def _model_step(beta: list, prev: float, rr: list) -> float:
    row = [1.0, prev, math.sqrt(max(prev, 0.0)), rr[0], rr[1], rr[2], rr[3], sum(rr[4:8])]
    return max(0.0, float(sum(b * x for b, x in zip(beta, row))))


def inflow_path(model: dict, inflow_today: float, rain_past7: list, rain_fc7: list, days: int = 7) -> list[dict]:
    """Daily inflow for days 1..days: the model (bias-corrected forecast rain, recursive) where it passed the gate at
    that horizon, else today's inflow; lo/hi from the tested residual band of the method used; never below zero."""
    beta, bias = model.get("beta"), {int(k): float(v) for k, v in (model.get("bias") or {}).items()}
    past = [float(x or 0.0) for x in rain_past7][-7:]
    fc = [float(x or 0.0) * bias.get(k + 1, 1.0) for k, x in enumerate(rain_fc7)]
    rain = past + fc  # index 6 = yesterday … index 7 = day 1
    out, prev = [], float(inflow_today)
    for k in range(1, days + 1):
        i = 6 + k  # position of day k in `rain`
        rr = [rain[i - j] for j in range(0, 8)]
        prev = _model_step(beta, prev, rr) if beta else float(inflow_today)
        use_model = _passes(model, k)
        mid = prev if use_model else float(inflow_today)
        band = (model.get("band_model") if use_model else model.get("band_persist")) or {}
        lo_b, hi_b = band.get(str(min(k, 7)), [0.0, 0.0])
        out.append({"h": k, "mid": round(mid, 3), "lo": round(max(0.0, mid + float(lo_b)), 3), "hi": round(max(0.0, mid + float(hi_b)), 3),
                    "method": "model" if use_model else "persistence"})
    return out


INFLOW7_FILE = Path(__file__).resolve().parent / "data" / "reservoir_inflow7.json"


def load_inflow7() -> dict:
    """E-7D-IN's served inflow models ({dam_id: model}); {} before a build exists."""
    if not INFLOW7_FILE.exists():
        return {}
    return {int(k): v for k, v in json.loads(INFLOW7_FILE.read_text(encoding="utf-8")).items()}


def compose_rain(era: dict, fc: dict, scale: dict, d0, models: list) -> tuple[list, list]:
    """Catchment rain as known at the end of day d0 (E-7D-IN): the 30 days to d0 — ERA5 up to d0−5 (it arrives ~5 days
    late), then the mean of the models' own values scaled to ERA5 (lead 0) — and days d0+1…d0+7, the mean of the models'
    forecasts scaled per lead. A model without a value or a scale on a day is left out; NaN when none has one."""
    def mean_at(day, lead):
        vals = []
        for m in models:
            v = (fc.get(m) or {}).get(day)
            sc = ((scale or {}).get(m) or {}).get(str(lead))
            if v is not None and sc is not None:
                vals.append(float(v) * float(sc))
        return sum(vals) / len(vals) if vals else float("nan")
    past = []
    for j in range(29, -1, -1):
        day = (d0 - dt.timedelta(days=j)).isoformat()
        if j >= 5 and era.get(day) is not None:
            past.append(float(era[day]))
        else:
            v = mean_at(day, 0)
            past.append(v if v == v else float(era.get(day) or 0.0))
    return past, [mean_at((d0 + dt.timedelta(days=k)).isoformat(), k) for k in range(1, 8)]


def features7(fam: str, inflow30: list, past30: list, fut7: list, h: int, d0) -> list[float]:
    """The tested feature rows of research/2026-10-05_e7d_inflow.py: inflow today and yesterday (√ or log1p), rain today,
    past 3, 7 and 30 days (wetness), forecast rain days 1…h and h−1…h, forecast × wetness, season; KF: today's anomaly to
    the 30-day mean inflow with the rain terms."""
    it, it1 = float(inflow30[-1]), float(inflow30[-2])
    wet = float(sum(past30[-30:]))
    Fh, Fl = float(sum(fut7[:h])), float(sum(fut7[max(0, h - 2):h]))
    if fam == "KF":
        vals = [float(x) for x in inflow30[-30:] if x is not None and x == x]
        return [it - (sum(vals) / len(vals) if vals else it), Fh, Fl, wet, Fh * wet / 100.0]
    doy = d0.timetuple().tm_yday
    base = [math.log1p(max(it, 0.0)), math.log1p(max(it1, 0.0))] if fam == "L" else [it, it1, math.sqrt(max(it, 0.0))]
    return base + [float(past30[-1]), float(sum(past30[-3:])), float(sum(past30[-7:])), wet, Fh, Fl, Fh * wet / 100.0,
                   math.sin(2 * math.pi * doy / 365.25), math.cos(2 * math.pi * doy / 365.25)]


def inflow_path7(m7: dict, inflow30: list, past30: list, fut7: list, d0, days: int = 7) -> list[dict]:
    """Days 1…7: the dam's E-7D-IN model at the horizons where it beat persistence by ≥ 10 % on the window's first half,
    today's inflow elsewhere (or where that day's forecast is missing); lo/hi = mid + the tested band of the method used —
    quantiles of (observed − predicted), so the range sits where the misses fell; never below zero."""
    fam = str(m7.get("family") or "D").split("_")[0]
    today = float(inflow30[-1])
    vals = [float(x) for x in inflow30[-30:] if x is not None and x == x]
    m30 = sum(vals) / len(vals) if vals else today
    rec = []  # the recursive family (the Q58 form): one step a day on the composed rain, inflow(d−1) → inflow(d)
    if fam == "R":
        beta = next((hz["params"]["beta"] for hz in (m7.get("horizons") or {}).values() if (hz.get("params") or {}).get("beta")), None)
        rain, prev = list(past30[-8:]) + list(fut7), today
        for k in range(1, days + 1):
            j = 7 + k
            prev = _model_step(beta, prev, [rain[j - i] for i in range(8)]) if beta and all(r == r for r in rain[j - 7:j + 1]) else float("nan")
            rec.append(prev)
    out = []
    for h in range(1, days + 1):
        hz = (m7.get("horizons") or {}).get(str(h)) or {}
        use = hz.get("use") not in (None, "persistence") and bool(hz.get("params")) and all(x == x for x in fut7[:h])
        mid = today
        x = ([rec[h - 1]] if fam == "R" else features7(fam, inflow30, past30, fut7, h, d0)) if use else []
        use = use and all(v == v for v in x)  # a missing inflow or rain input: persistence, never NaN
        if use and fam == "R":
            mid = max(0.0, x[0])
        elif use:
            p = hz["params"]
            z = sum((v - mu) / sd * w for v, mu, sd, w in zip(x, p["mu"], p["sd"], p["w"])) + p["ymean"]
            mid = max(0.0, math.expm1(z) if fam == "L" else (m30 + z) if fam == "KF" else z)
        lo_b, hi_b = (hz.get("band_model") if use else hz.get("band_persist")) or [0.0, 0.0]
        out.append({"h": h, "mid": round(mid, 3), "lo": round(max(0.0, mid + lo_b), 3), "hi": round(max(0.0, mid + hi_b), 3),
                    "method": "model" if use else "persistence"})
    return out


def rain_inputs7(points: list, models: list, d0, fetch=None) -> tuple[dict, dict]:
    """ERA5 (Open-Meteo archive, d0−40…d0) and each forecast model's daily rain (d0−7…d0+8) at the dam's catchment
    points, area-weighted over the points that have the day: ({date: mm}, {model: {date: mm}}) — compose_rain's inputs."""
    import urllib.request
    from floodwatch.config import settings

    def _fetch(url):
        req = urllib.request.Request(url, headers={"User-Agent": settings.user_agent})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    fetch = fetch or _fetch
    acc_e: dict = {}
    acc_f: dict = {m: {} for m in models}

    def add(acc, t, v, w):
        if v is not None:
            s = acc.setdefault(t, [0.0, 0.0])
            s[0] += float(v) * w
            s[1] += w
    for lat, lon, km2 in points:
        e = fetch(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat:.3f}&longitude={lon:.3f}"
                  f"&start_date={(d0 - dt.timedelta(days=40)).isoformat()}&end_date={d0.isoformat()}&daily=precipitation_sum"
                  f"&timezone=Asia%2FBangkok")["daily"]
        for t, v in zip(e["time"], e["precipitation_sum"]):
            add(acc_e, t, v, km2)
        f = fetch(f"https://api.open-meteo.com/v1/forecast?latitude={lat:.3f}&longitude={lon:.3f}&daily=precipitation_sum"
                  f"&past_days=7&forecast_days=9&timezone=Asia%2FBangkok&models={','.join(models)}")["daily"]
        for m in models:
            series = f.get(f"precipitation_sum_{m}") or (f.get("precipitation_sum") if len(models) == 1 else None) or []
            for t, v in zip(f["time"], series):
                add(acc_f[m], t, v, km2)
    mean = lambda acc: {t: round(s[0] / s[1], 3) for t, s in acc.items() if s[1] > 0}
    return mean(acc_e), {m: mean(a) for m, a in acc_f.items()}


def outlook7(m7: dict, dam: dict, inflow30: list, past30: list, fut7: list, curves7: dict | None, normal: float | None) -> dict | None:
    """The dam's 7-day outlook with its E-7D-IN model (D-104): inflow per horizon — the model where it beat persistence by
    ≥ 10 % on the choosing half, today's inflow elsewhere — with its tested band; storage with today's release held and the
    monthly loss term; the position against the upper rule curve per day; the test that justifies the method."""
    if dam.get("storage_mcm") is None or dam.get("inflow_mcm") is None or dam.get("released_mcm") is None:
        return None
    if float(dam["storage_mcm"]) <= 0:
        return None
    d0 = dt.date.fromisoformat(str(dam["dam_date"])[:10])
    inflow = inflow_path7(m7, inflow30, past30, fut7, d0)
    dates = [(d0 + dt.timedelta(days=k)).isoformat() for k in range(1, 8)]
    loss = m7.get("loss_by_month") or {}
    rel = float(dam["released_mcm"])
    s0 = float(dam["storage_mcm"])
    mid = storage_path(s0, [p["mid"] for p in inflow], rel, loss, dates)
    lo = storage_path(s0, [p["lo"] for p in inflow], rel, loss, dates)
    hi = storage_path(s0, [p["hi"] for p in inflow], rel, loss, dates)
    up = (curves7 or {}).get("upper") or [None] * 7
    days = [{"date": dates[k], "inflow": inflow[k]["mid"], "inflow_lo": inflow[k]["lo"], "inflow_hi": inflow[k]["hi"], "method": inflow[k]["method"],
             "storage": mid[k], "storage_lo": lo[k], "storage_hi": hi[k], "upper": up[k],
             "above_upper": (mid[k] > up[k]) if up[k] is not None else None,
             "above_normal": (mid[k] > normal) if normal else None} for k in range(7)]
    gains = {}
    for h in (1, 3, 7):
        hz = (m7.get("horizons") or {}).get(str(h)) or {}
        mt = hz.get("mae_test")
        gains[h] = round(100 * (1 - mt[0] / mt[1]), 1) if hz.get("use") not in (None, "persistence") and mt and mt[1] else None
    by_day = [p["method"] for p in inflow]
    model_days = [k + 1 for k, m in enumerate(by_day) if m == "model"]
    span = (f"{model_days[0]}–{model_days[-1]}" if len(model_days) > 1 else str(model_days[0])) if model_days else ""
    fin = [x for x in fut7 if x == x]
    n_models = len(m7.get("models") or [])
    words = (f"แบบจำลองจากฝนคาดการณ์ {n_models} แบบ (วันที่ {span})" + ("" if len(model_days) == 7 else " · คงค่าวันนี้ในวันอื่น")
             if model_days else "คงค่าวันนี้ (แบบจำลองไม่ผ่านเกณฑ์ที่ช่วงใดเลย)")
    return {"days": days, "release_assumed": rel, "methods": {"1-3": by_day[2], "4-7": by_day[6]}, "by_day": by_day,
            "test": {"model": bool(model_days), "gain_1d": gains[1], "gain_3d": gains[3], "gain_7d": gains[7], "days": m7.get("test_days"),
                     "from": m7.get("test_from"), "to": m7.get("test_to"), "family": m7.get("family"),
                     "source": "E-7D-IN, research/2026-10-05_e7d_inflow.log"},
            "rain7_mm": round(sum(fin), 1) if fin else None, "loss_month": loss.get(str(int(dates[0][5:7]))),
            "note": f"ปล่อยเท่าวันนี้ {rel:.2f} ล้าน ลบ.ม./วัน ตลอด 7 วัน · น้ำไหลเข้า: {words}"}


def storage_path(storage0: float, inflow: list, release: float, loss_by_month: dict, dates: list) -> list[float]:
    """S(d) = S(d−1) + I(d) − R + loss(month of d); loss is the balance residual's monthly median (negative = losses)."""
    out, s = [], float(storage0)
    for i_, d in zip(inflow, dates):
        s = max(0.0, s + float(i_) - float(release) + float((loss_by_month or {}).get(str(int(d[5:7])), 0.0)))
        out.append(round(s, 2))
    return out


def outlook(model: dict, dam: dict, rain14: dict, curves7: dict | None, normal: float | None) -> dict | None:
    """The dam's 7-day outlook: inflow (method per horizon, band), storage (mid and band, release held at today's),
    position against the upper rule curve per day, and the operational test result that justifies the method."""
    if dam.get("storage_mcm") is None or dam.get("inflow_mcm") is None or dam.get("released_mcm") is None:
        return None
    if float(dam["storage_mcm"]) <= 0:
        return None  # a reservoir reported empty is a missing value (KI-305), not a starting point
    d0 = str(dam["dam_date"])[:10]
    if model.get("beta"):
        if not rain14:
            return None
        dates_all, mm = rain14.get("dates") or [], rain14.get("mm") or []
        past = [m for d, m in zip(dates_all, mm) if d <= d0][-7:]
        fut = [m for d, m in zip(dates_all, mm) if d > d0][:7]
        if len(fut) < 7:
            return None
    else:
        past, fut = [0.0] * 7, [0.0] * 7  # a persistence outlook needs no rain
    inflow = inflow_path(model, float(dam["inflow_mcm"]), past, fut)
    dates = [(dt.date.fromisoformat(d0) + dt.timedelta(days=k)).isoformat() for k in range(1, 8)]
    loss = model.get("loss_by_month") or {}
    rel = float(dam["released_mcm"])
    mid = storage_path(float(dam["storage_mcm"]), [p["mid"] for p in inflow], rel, loss, dates)
    lo = storage_path(float(dam["storage_mcm"]), [p["lo"] for p in inflow], rel, loss, dates)
    hi = storage_path(float(dam["storage_mcm"]), [p["hi"] for p in inflow], rel, loss, dates)
    up = (curves7 or {}).get("upper") or [None] * 7
    days = [{"date": dates[k], "inflow": inflow[k]["mid"], "inflow_lo": inflow[k]["lo"], "inflow_hi": inflow[k]["hi"], "method": inflow[k]["method"],
             "storage": mid[k], "storage_lo": lo[k], "storage_hi": hi[k], "upper": up[k],
             "above_upper": (mid[k] > up[k]) if up[k] is not None else None,
             "above_normal": (mid[k] > normal) if normal else None} for k in range(7)]
    g = model.get("op_gain") or {}
    test = {"model": bool(model.get("beta")), "gain_1d": g.get("1"), "gain_3d": g.get("3"), "gain_7d": g.get("7"),
            "days": model.get("test_days"), "from": model.get("test_from"), "to": model.get("test_to")}
    if not model.get("beta"):
        return {"days": days, "release_assumed": rel, "methods": {"1-3": "persistence", "4-7": "persistence"}, "test": test,
                "rain7_mm": None, "loss_month": None,
                "note": f"ถ้าไหลเข้าและระบายเท่าวันนี้ ({float(dam['inflow_mcm']):.2f} และ {rel:.2f} ล้าน ลบ.ม./วัน) ตลอด 7 วัน"
                        f" · ช่วง = การเปลี่ยนของน้ำไหลเข้าเขื่อนนี้เองใน {model.get('test_days')} วันที่มีข้อมูล · ยังไม่มีแบบจำลองที่ผ่านการทดสอบ · ไม่มีพจน์การสูญเสีย"}
    return {"days": days, "release_assumed": rel, "methods": {"1-3": inflow[0]["method"], "4-7": inflow[6]["method"]},
            "test": test,
            "rain7_mm": round(sum(fut), 1), "loss_month": loss.get(str(int(dates[0][5:7]))),
            "note": f"ปล่อยเท่าวันนี้ {rel:.2f} ล้าน ลบ.ม./วัน ตลอด 7 วัน · น้ำไหลเข้า: " +
                    ("แบบจำลองจากฝนคาดการณ์" if inflow[0]["method"] == "model" else "คงค่าวันนี้") +
                    (" (วันที่ 1–3) และคงค่าวันนี้ (วันที่ 4–7)" if inflow[0]["method"] != inflow[6]["method"] and inflow[0]["method"] == "model"
                     else " (วันที่ 1–3) และแบบจำลอง (วันที่ 4–7)" if inflow[0]["method"] != inflow[6]["method"] else "")}


def run() -> dict:
    """Worker task (every 6 h): the 7-day outlook for every dam with a tested model, from the dam's latest daily record,
    its rule curves, Open-Meteo's past/next 7 days of catchment rain; stored as collector_state 'reservoir_outlook'."""
    import logging
    from floodwatch import db, impact
    log = logging.getLogger(__name__)
    models = load_models()
    m7s = load_inflow7()
    out, now = {}, dt.datetime.now(dt.timezone.utc)
    with db.connect() as c:
        for dam_id, m7 in m7s.items():  # E-7D-IN models first (D-104)
            try:
                row = c.execute("""SELECT dam_date::text AS dam_date, storage_mcm, inflow_mcm, released_mcm FROM dam_daily
                                   WHERE dam_id=%s AND storage_mcm IS NOT NULL AND inflow_mcm IS NOT NULL AND released_mcm IS NOT NULL
                                   ORDER BY dam_date DESC LIMIT 1""", (dam_id,)).fetchone()
                if not row:
                    continue
                d0 = dt.date.fromisoformat(row["dam_date"])
                hist = {r["d"]: float(r["v"]) for r in c.execute(
                    """SELECT dam_date::text AS d, inflow_mcm AS v FROM dam_daily WHERE dam_id=%s AND inflow_mcm IS NOT NULL
                       AND dam_date > %s::date - 30 AND dam_date <= %s::date""", (dam_id, d0, d0)).fetchall()}
                inflow30 = [hist.get((d0 - dt.timedelta(days=j)).isoformat(), float("nan")) for j in range(29, -1, -1)]
                era, fc = rain_inputs7(m7["points"], m7["models"], d0)
                past30, fut7 = compose_rain(era, fc, m7["scale"], d0, m7["models"])
                meta = c.execute("SELECT normal_mcm FROM dam WHERE dam_id=%s", (dam_id,)).fetchone() or {}
                curves = db.get_state(c, f"dam_rule_curve_{dam_id}")
                o = outlook7(m7, dict(row), inflow30, past30, fut7, impact.curves_ahead(curves, row["dam_date"]),
                             (curves or {}).get("normal") or meta.get("normal_mcm"))
                if o:
                    out[str(dam_id)] = {**o, "name_th": m7.get("name_th"), "dam_date": row["dam_date"]}
            except Exception:
                log.exception("7-day inflow outlook failed for dam %s", dam_id)
        for dam_id, m in models.items():
            if str(dam_id) in out:
                continue
            try:
                row = c.execute("""SELECT dam_date::text AS dam_date, storage_mcm, inflow_mcm, released_mcm FROM dam_daily
                                   WHERE dam_id=%s AND storage_mcm IS NOT NULL AND inflow_mcm IS NOT NULL AND released_mcm IS NOT NULL
                                   ORDER BY dam_date DESC LIMIT 1""", (dam_id,)).fetchone()
                if not row:
                    continue
                meta = c.execute("SELECT normal_mcm FROM dam WHERE dam_id=%s", (dam_id,)).fetchone() or {}
                curves = db.get_state(c, f"dam_rule_curve_{dam_id}")
                rain14 = impact.catchment_rain14(m["points"])
                o = outlook(m, dict(row), rain14, impact.curves_ahead(curves, row["dam_date"]), (curves or {}).get("normal") or meta.get("normal_mcm"))
                if o:
                    out[str(dam_id)] = {**o, "name_th": m.get("name_th"), "dam_date": row["dam_date"]}
            except Exception:
                log.exception("reservoir outlook failed for dam %s", dam_id)
        # every other dam with enough inflow history: a persistence projection with its own band (KI-303)
        for r0 in c.execute("SELECT dam_id, name_th FROM dam ORDER BY dam_id").fetchall():
            dam_id = r0["dam_id"]
            if dam_id in models or str(dam_id) in out:
                continue
            try:
                hist = {r["d"]: float(r["v"]) for r in c.execute(
                    "SELECT dam_date::text AS d, inflow_mcm AS v FROM dam_daily WHERE dam_id=%s AND inflow_mcm IS NOT NULL", (dam_id,)).fetchall()}
                m = persistence_model(dam_id, r0["name_th"], hist)
                if not m:
                    continue
                row = c.execute("""SELECT dam_date::text AS dam_date, storage_mcm, inflow_mcm, released_mcm FROM dam_daily
                                   WHERE dam_id=%s AND storage_mcm IS NOT NULL AND inflow_mcm IS NOT NULL AND released_mcm IS NOT NULL
                                   ORDER BY dam_date DESC LIMIT 1""", (dam_id,)).fetchone()
                if not row:
                    continue
                meta = c.execute("SELECT normal_mcm FROM dam WHERE dam_id=%s", (dam_id,)).fetchone() or {}
                curves = db.get_state(c, f"dam_rule_curve_{dam_id}")
                o = outlook(m, dict(row), None, impact.curves_ahead(curves, row["dam_date"]), (curves or {}).get("normal") or meta.get("normal_mcm"))
                if o:
                    out[str(dam_id)] = {**o, "name_th": r0["name_th"], "dam_date": row["dam_date"]}
            except Exception:
                log.exception("persistence outlook failed for dam %s", dam_id)
        db.set_state(c, "reservoir_outlook", {"built_at": now.isoformat(), "dams": out})
        c.commit()
    log.info("reservoir_outlook: %d dams", len(out))
    return out

