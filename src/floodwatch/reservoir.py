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
    """{dam_id: model} from the data file (empty when absent)."""
    if not MODELS_FILE.exists():
        return {}
    raw = json.loads(MODELS_FILE.read_text())
    return {int(m["dam_id"]): {**m, "name_th": name} for name, m in raw.items()}


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
    out, now = {}, dt.datetime.now(dt.timezone.utc)
    with db.connect() as c:
        for dam_id, m in models.items():
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
            if dam_id in models:
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

