"""7-day release scenarios for the impact tab (owner 2026-10-05; D-101).

The decision maker's question: "if we release this much over the next 7 days, what happens to the reservoir and to the
river below?" Plans are *found by search*, not fixed steps: every constant, ramped and front-loaded release path within
the feasible range is evaluated on the same effects, the best plan per effect is marked ("เหมาะกับ…"), and ★ marks the
optimal by a stated rule (least downstream impact among the plans that bring storage back under the upper rule curve
within 7 days). Reservoir side: a daily water balance (HII's inflow closes against its storage, research
2026-10-05_kk_inflow_model.log); inflow held at today's value with a band from persistence's own errors — a rain-driven
model lost to persistence at every horizon in the honest test, so it is not used. River side: impact.whatif per day with
whole-day travel times — unvalidated downstream (D-099), labelled as such.
"""
from __future__ import annotations

from floodwatch import impact

DAYS = 7
EFFECT_KEYS = ("city", "worst", "total", "dam", "curve", "water", "warning")
EFFECT_TH = {"city": "ปกป้องตัวเมือง", "worst": "ห่างตลิ่งมากสุด", "total": "ท่วมรวมน้อยสุด", "dam": "ความปลอดภัยเขื่อน",
             "curve": "กลับใต้เส้นควบคุมเร็ว", "water": "เก็บน้ำไว้ใช้", "warning": "เตือนล่วงหน้าได้"}
# inflow(t+h) − inflow(t), 10–90 % (research/2026-10-05_kk_inflow_model.log): the band around "hold today's inflow".
# PERSIST_BAND: 2025-2026, all days. HIGH_BAND: days with inflow ≥ HIGH_INFLOW (all years; floods move far more).
PERSIST_BAND = {1: (-0.84, 0.96), 2: (-1.18, 1.08), 3: (-1.27, 1.28), 4: (-1.41, 1.43), 5: (-1.65, 1.69), 6: (-1.36, 1.73), 7: (-1.32, 1.85)}
HIGH_INFLOW = 10.0
HIGH_BAND = {1: (-7.28, 6.07), 2: (-10.25, 7.31), 3: (-12.04, 6.33), 4: (-13.69, 7.51), 5: (-15.4, 8.05), 6: (-15.5, 7.57), 7: (-15.88, 5.41)}


def inflow_band(inflow_today: float, h: int) -> tuple[float, float]:
    """The 10–90 % change of inflow after h days around today's value, by regime."""
    band = HIGH_BAND if (HIGH_BAND and inflow_today >= HIGH_INFLOW) else PERSIST_BAND
    return band[min(max(h, 1), 7)]


def water_balance(storage0: float, inflow: list[float], release: list[float]) -> list[float]:
    """Storage after each day (ล้าน ลบ.ม.), never below zero. Losses are inside HII's inflow (the balance closes)."""
    out, s = [], float(storage0)
    for i, r in zip(inflow, release):
        s = max(0.0, s + float(i) - float(r))
        out.append(round(s, 3))
    return out


def candidate_plans(today: float, max_release: float, days: int = DAYS, step: float = 0.5, coarse: float = 2.0) -> list[dict]:
    """Every plan the search considers: hold; constants on a fine grid; linear ramps and front-loaded (k days at r1, then
    r2) on a coarse grid. All within 0..max_release."""
    plans = [{"kind": "hold", "release": [round(today, 2)] * days}]
    fine = [round(k * step, 2) for k in range(int(max_release / step) + 1)]
    crs = [round(k * coarse, 2) for k in range(int(max_release / coarse) + 1)]
    for r in fine:
        if abs(r - today) > 1e-9:
            plans.append({"kind": "constant", "release": [r] * days})
    for r0 in crs:
        for r1 in crs:
            if r1 != r0:
                plans.append({"kind": "ramp", "release": [round(r0 + (r1 - r0) * k / (days - 1), 2) for k in range(days)]})
                for k in (2, 3, 4):
                    plans.append({"kind": "front", "release": [r0] * k + [r1] * (days - k)})
    seen, out = set(), []
    for p in plans:
        key = tuple(p["release"])
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def effects(release: list[float], storage: list[float], upper: list[float], lower: list[float], normal: float,
            margins: dict, city: tuple, today: float | None = None, margin_req: dict | None = None) -> dict:
    """The numbers every plan is judged on. Margins: {code: [m to the gauge's own bank per day]}; negative = over it.
    `margin_req` {code: m}: the downstream model's own error per point — a plan is only as safe as its margin above it.
    `today`: today's release, so the first day's step counts as a change too (warning time)."""
    all_m = [m for ms in margins.values() for m in ms if m is not None]
    city_m = [m for c in city for m in margins.get(c, []) if m is not None]

    def req_at(c, d):  # one margin per point, or one per day (river7's hindcast error grows with the lead)
        v = (margin_req or {}).get(c, 0.0)
        if isinstance(v, (list, tuple)):
            return v[d] if d < len(v) and v[d] is not None else 0.0
        return v or 0.0
    req = [m - req_at(c, d) for c, ms in margins.items() for d, m in enumerate(ms) if m is not None]
    steps = [abs(release[d] - release[d - 1]) for d in range(1, len(release))] + ([abs(release[0] - today)] if today is not None else [])
    above = [d for d, (s, u) in enumerate(zip(storage, upper)) if s <= u]
    return {"city_margin_min": min(city_m) if city_m else None, "worst_margin_min": min(all_m) if all_m else None,
            "overtop_sum": round(sum(max(0.0, -m) for m in all_m), 3), "storage_peak": max(storage),
            "days_above_normal": sum(1 for s in storage if s > normal), "under_curve_day": (above[0] + 1) if above else None,
            "storage_end": storage[-1], "end_vs_lower": round(storage[-1] - lower[-1], 3),
            "ramp_max": round(max(steps, default=0.0), 3), "release_mean": round(sum(release) / len(release), 3),
            "margin_vs_req_min": round(min(req), 3) if req else None}


def _key(rows, fn):
    """The row that wins by `fn` (a tuple, smaller wins); stable, so the first of equals wins."""
    return min(rows, key=lambda r: fn(r["effects"]))["id"] if rows else None


# a goal has a "best" plan only when the plans differ on it by more than this (D-110: "ท่วมรวมน้อยสุด" was awarded while no
# plan overtopped anywhere): m for margins, ล้าน ลบ.ม. for storage, ล้าน ลบ.ม./วัน for the daily change
TOL = {"city": 0.05, "worst": 0.05, "dam": 1.0, "water": 1.0, "warning": 0.1}


def _spread(effects: list[dict], key: str) -> float:
    vals = [e[key] for e in effects if e.get(key) is not None]
    return (max(vals) - min(vals)) if len(vals) >= 2 else 0.0


def _differs(rows: list[dict], k: str) -> bool:
    e = [r["effects"] for r in rows]
    if len(e) < 2:
        return False
    if k == "total":
        return max(x["overtop_sum"] for x in e) > 0 and _spread(e, "overtop_sum") > 0.01
    if k == "dam":
        return _spread(e, "storage_peak") > TOL["dam"] or len({x["days_above_normal"] for x in e}) > 1
    if k == "curve":
        return len({99 if x["under_curve_day"] is None else x["under_curve_day"] for x in e}) > 1 or _spread(e, "storage_end") > TOL["water"]
    key = {"city": "city_margin_min", "worst": "worst_margin_min", "water": "storage_end", "warning": "ramp_max"}[k]
    return _spread(e, key) > TOL[k]


def best_for(rows: list[dict]) -> dict:
    """The best plan per goal, or None for a goal the plans do not differ on (D-110)."""
    none = lambda v, big: big if v is None else v
    keys = {"city": lambda e: (-none(e["city_margin_min"], -1e9),),
            "worst": lambda e: (-none(e["worst_margin_min"], -1e9),),
            "total": lambda e: (e["overtop_sum"], -none(e["worst_margin_min"], -1e9)),
            "dam": lambda e: (e["storage_peak"], e["days_above_normal"]),
            "curve": lambda e: (none(e["under_curve_day"], 99), e["storage_end"]),
            "water": lambda e: (-e["storage_end"],),
            "warning": lambda e: (e["ramp_max"], -none(e["worst_margin_min"], -1e9))}
    return {k: (_key(rows, fn) if _differs(rows, k) else None) for k, fn in keys.items()}


def feasible(rows: list[dict], storage0: float, upper_today: float | None, max_storage: float | None,
             lower_today: float | None = None) -> list[dict]:
    """The plans a decision maker may consider: C1 no gauge over its bank on any day; C2 storage never above the maximum
    storage (when known); C3 the reservoir does not end further from the rule curve than today — above the upper curve
    it must not end higher than today, below the lower curve it must not end lower."""
    out = []
    for r in rows:
        e = r["effects"]
        if e["overtop_sum"] > 0 or (e["worst_margin_min"] is not None and e["worst_margin_min"] < 0):
            continue
        if e.get("margin_vs_req_min") is not None and e["margin_vs_req_min"] < 0:  # inside the downstream model's own error
            continue
        if max_storage is not None and e["storage_peak"] > max_storage:
            continue
        if upper_today is not None and storage0 > upper_today and e["storage_end"] > storage0:
            continue
        if lower_today is not None and storage0 < lower_today and e["storage_end"] < storage0:
            continue
        out.append(r)
    return out


def optimal(rows: list[dict], storage0: float, upper_today: float | None, normal: float, max_storage: float | None = None,
            lower_today: float | None = None) -> dict:
    """The stated rule: among the feasible plans (no overtopping, within the maximum storage, the reservoir not left
    further from its curve), the fastest return toward the upper rule curve (earliest day under it, then the lowest
    storage on day 7), then the gentlest change of release. When no plan is feasible the rule says so and shows the plan
    that lowers the reservoir with the least overtopping — downstream is then the binding constraint."""
    e = lambda r: r["effects"]
    feas = feasible(rows, storage0, upper_today, max_storage, lower_today)
    if feas:
        win = min(feas, key=lambda r: (e(r)["under_curve_day"] if e(r)["under_curve_day"] is not None else 99,
                                       e(r)["storage_end"], e(r)["ramp_max"]))
        w = e(win)
        when = (f"กลับใต้เส้นควบคุมบนในวันที่ {w['under_curve_day']}" if w["under_curve_day"] is not None
                else f"ลดปริมาตรอ่างได้มากที่สุดโดยยังไม่ถึงเส้นควบคุมบนใน 7 วัน (เหลือ {w['storage_end']:.0f} ล้าน ลบ.ม.)")
        margin = f" (ห่างตลิ่งต่ำสุด {w['worst_margin_min']:.2f} ม. มากกว่าความคลาดเคลื่อนของแบบจำลองท้ายน้ำ)" if w["worst_margin_min"] is not None else ""
        return {"id": win["id"], "constraints_met": True,
                "reason": f"{when} โดยไม่มีจุดใดเกินตลิ่ง{margin} และเปลี่ยนอัตราระบายวันละไม่เกิน {w['ramp_max']:.1f} ล้าน ลบ.ม. (รวมก้าวแรกจากวันนี้)"
                          + (f"; ปริมาตรสูงสุด {w['storage_peak']:.0f} เทียบปริมาตรปกติ {normal:.0f} ล้าน ลบ.ม." if normal else ""),
                "rule": RULE}
    lowering = [r for r in rows if e(r)["storage_end"] <= storage0 and (max_storage is None or e(r)["storage_peak"] <= max_storage)] or rows
    win = min(lowering, key=lambda r: (e(r)["overtop_sum"], e(r)["storage_end"], e(r)["ramp_max"]))
    return {"id": win["id"], "constraints_met": False,
            "reason": "ไม่มีแผนใดลดปริมาตรอ่างได้โดยไม่มีจุดใดเกินตลิ่ง — ตลิ่งท้ายน้ำเป็นข้อจำกัดหลัก; แสดงแผนที่ลดอ่างโดยเกินตลิ่งน้อยที่สุดแทน"
                      f" (เกินตลิ่งรวม {e(win)['overtop_sum']:.2f} ม.·จุด·วัน) ⚠️ ระดับท้ายน้ำยังไม่ผ่านการทดสอบ",
            "rule": RULE}


RULE = ("แผนที่พาอ่างกลับสู่เส้นควบคุมเร็วที่สุด ในบรรดาแผนที่ทุกจุดห่างตลิ่งมากกว่าความคลาดเคลื่อนของแบบจำลองท้ายน้ำ "
        "ไม่เกินความจุสูงสุด และไม่ปล่อยให้อ่างสูงขึ้นอีก")


def daily_downstream(state: dict, release_path: list[float], diversion_cms: float | None = None) -> dict:
    """Per point, per day: the release that reaches it that day (whole-day travel time from its lag; before day 1 the
    release is today's). With `state["river7"]` (E-7D-DOWN) the level is that tested 7-day method's — below the dam its
    rating anchored on today's level, past the diversion today's level + the fitted gain — and the range is that day's
    90 % hindcast error; without it, impact.whatif's (local inflow and the diversion held at today's). Flows are the
    what-if's either way."""
    today = (state.get("dam") or {}).get("released_mcm")
    if today is None:
        today = release_path[0]
    out = {}
    cache = {}
    r7 = state.get("river7") or {}
    gains, errs = r7.get("gains_cm_per_cms") or {}, r7.get("errors") or {}
    for p in state["points"]:
        lag_days = int(round((p.get("lag_h") or 0) / 24.0))
        rows = []
        for d in range(len(release_path)):
            r = release_path[d - lag_days] if d - lag_days >= 0 else today
            key = round(float(r), 3)
            if key not in cache:
                cache[key] = {row["code"]: row for row in impact.whatif(state, key, diversion_cms)["rows"]}
            row = cache[key].get(p["code"]) or {}
            rec = {k: row.get(k) for k in ("flow_cms", "level", "margin_m", "overflow", "outside")}
            mid = impact.level7(p, r, today, d + 1, gains[p["code"]], r7.get("method") or "hybrid") if p["code"] in gains else None
            if mid is not None:
                e = errs.get(p["code"]) or {}
                band = ((e.get("p90_m") or [None] * 7)[min(d, 6)] or (e.get("mae_m") or [None] * 7)[min(d, 6)] or 0.0)
                bank = p.get("bank")
                rec.update({"level": [mid - band, mid, mid + band], "margin_m": (bank - mid) if bank is not None else None,
                            "overflow": None if bank is None else "yes" if mid >= bank else "possible" if mid + band >= bank else "no"})
            rows.append(rec)
        out[p["code"]] = rows
    return out


def _req_txt(c: str, m) -> str:
    if isinstance(m, (list, tuple)):
        vals = [x for x in m if x is not None]
        return f"{c} ≥ {min(vals):.2f}–{max(vals):.2f} ม." if vals else c
    return f"{c} ≥ {m:.2f} ม."


def compare(state: dict, inflow_today: float, upper: list[float], lower: list[float], normal: float,
            max_release: float, max_storage: float | None = None, custom: list[float] | None = None,
            diversion_cms: float | None = None, city: tuple = ("B.15", "PCH001"), inflow_path: list | None = None) -> dict:
    """The whole comparison: every candidate (and the custom plan) evaluated with today's inflow held (mid) and the
    persistence band (low/high storage), best plan per effect, the ★ optimal, and the plans worth showing."""
    dam = state.get("dam") or {}
    storage0 = float(dam.get("storage_mcm") or 0.0)
    today = float(dam.get("released_mcm") or 0.0)
    days = len(upper)
    tested = bool(inflow_path) and len(inflow_path) >= days and any(p.get("method") == "model" for p in inflow_path[:days])
    if tested:  # the dam's tested 7-day inflow (D-104): the model where it passed, today's inflow elsewhere, its own band
        inflow_mid = [max(0.0, float(p["mid"])) for p in inflow_path[:days]]
        inflow_lo = [max(0.0, float(p["lo"])) for p in inflow_path[:days]]
        inflow_hi = [max(0.0, float(p["hi"])) for p in inflow_path[:days]]
    else:
        inflow_mid = [max(0.0, inflow_today)] * days
        inflow_lo = [max(0.0, inflow_today + inflow_band(inflow_today, h)[0]) for h in range(1, days + 1)]
        inflow_hi = [max(0.0, inflow_today + inflow_band(inflow_today, h)[1]) for h in range(1, days + 1)]
    # the downstream model's own error: per point and day from river7's hindcast (E-7D-DOWN), else per point from the
    # replay's mean error of the mass-balance method (cm → m)
    r7 = state.get("river7") or {}
    r7e = r7.get("errors") or {}
    cm = lambda xs: [round(100 * x) if x is not None else None for x in (xs or [])]
    downstream = ({"method": "hybrid", "window": r7.get("window"), "test": r7.get("test"),
                   "mae_cm": {c: cm(e.get("mae_m")) for c, e in r7e.items()}, "keep_cm": {c: cm(e.get("keep_mae_m")) for c, e in r7e.items()},
                   "gains_cm_per_cms": r7.get("gains_cm_per_cms")} if r7e else {"method": "whatif"})
    if r7e:
        margin_req = {c: [round(x, 3) if x is not None else 0.0 for x in (e.get("mae_m") or [])] for c, e in r7e.items()}
    else:
        vp = ((state.get("validation") or {}).get("points") or {})
        margin_req = {c: (v.get("methods") or {}).get("absolute", 0.0) / 100.0 for c, v in vp.items()}
    plans = candidate_plans(today, max_release, days)
    if custom:
        plans.append({"kind": "custom", "release": [round(float(x), 2) for x in custom]})
    rows = []
    for i, p in enumerate(plans):
        storage = water_balance(storage0, inflow_mid, p["release"])
        down = daily_downstream(state, p["release"], diversion_cms)
        margins = {c: [r["margin_m"] for r in rs] for c, rs in down.items() if any(r["margin_m"] is not None for r in rs)}
        rows.append({"id": f"p{i}", "kind": p["kind"], "release": p["release"], "storage": storage,
                     "storage_low": water_balance(storage0, inflow_lo, p["release"]),
                     "storage_high": water_balance(storage0, inflow_hi, p["release"]),
                     "downstream": down, "effects": effects(p["release"], storage, upper, lower, normal, margins, city,
                                                            today=today, margin_req=margin_req)})
    feas = feasible(rows, storage0, upper[0], max_storage, lower[0])
    best = best_for(feas or rows)  # per-effect bests among the plans a decision maker may consider
    opt = optimal(rows, storage0, upper[0], normal, max_storage, lower[0])
    show_ids = [r["id"] for r in rows if r["kind"] in ("hold", "custom")] + [opt["id"]] + list(best.values())
    seen, show = set(), []
    for rid in show_ids:
        if rid and rid not in seen:
            seen.add(rid)
            r = next(x for x in rows if x["id"] == rid)
            show.append({**r, "best_for": [k for k in EFFECT_KEYS if best[k] == rid], "optimal": rid == opt["id"],
                         "feasible": any(f["id"] == rid for f in feas)})
    model_days = [k + 1 for k, p in enumerate((inflow_path or [])[:days]) if p.get("method") == "model"] if tested else []
    model_note = (f"แบบจำลองจากฝนคาดการณ์ (วันที่ {model_days[0]}–{model_days[-1]}) ที่ผ่านการทดสอบสองชุด" if len(model_days) > 1 else
                  f"แบบจำลองจากฝนคาดการณ์ (วันที่ {model_days[0]})" if model_days else "")
    if tested:
        model_note += (", วันอื่นคงค่าวันนี้" if len(model_days) < days else "") + " · ช่วง = ความคลาดเคลื่อนที่ทดสอบของแต่ละวิธี"
    return {"days": days, "inflow": {"mid": inflow_mid, "low": inflow_lo, "high": inflow_hi, "method": "model" if tested else "hold",
                                     "regime": "high" if (HIGH_BAND and inflow_today >= HIGH_INFLOW) else "normal",
                                     "note": model_note if tested else ("คงน้ำไหลเข้าวันนี้ ช่วง = ความคลาดเคลื่อนของวิธีนี้เองที่ 1–7 วัน" + (" (ช่วงน้ำไหลเข้ามาก กว้างกว่าปกติมาก)" if (HIGH_BAND and inflow_today >= HIGH_INFLOW) else " (ปี 2568–69)") + "; แบบจำลองจากฝนแพ้วิธีนี้ทุกช่วงในการทดสอบ 2026-10-05 จึงไม่ใช้")},
            "upper": upper, "lower": lower, "normal": normal, "max_storage": max_storage, "max_release": max_release,
            "candidates": len(rows), "feasible": len(feas), "best_for": best, "optimal": opt, "plans": show,
            "margin_req": margin_req, "downstream": downstream,
            "constraints": ["ทุกจุดห่างตลิ่ง (ของหน่วยงานผู้วัด) มากกว่าความคลาดเคลื่อนของแบบจำลองท้ายน้ำ: " +
                            ", ".join(_req_txt(c, m) for c, m in sorted(margin_req.items())) + (" (วันที่ 1–7)" if r7e else ""),
                            "ไม่เกินความจุสูงสุดของอ่าง",
                            "อ่างต้องไม่สูงขึ้นกว่าวันนี้เมื่ออยู่เหนือเส้นควบคุมบน (หรือไม่ต่ำลงเมื่ออยู่ใต้เส้นล่าง)"]}
