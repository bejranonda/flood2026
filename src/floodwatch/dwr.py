"""DWR early-warning level posts (กรมทรัพยากรน้ำ, D-078 to be): a trend-only layer (owner 2026-10-03: "Get history, if
possible, then archive first, and show as trend-only layer"). Kept apart from `station`: the level is the depth on a
local staff post (not m MSL, so never compared with HII/RID/BMA, KI-217), alarm levels are mostly a default 4.00 m,
and DWR serves only ~11 h of history, so our 30-min archive is the history. Shown: the measured change only."""
from __future__ import annotations

import datetime as dt

from floodwatch import qc

STUCK_MIN = 24  # 12 h of 30-min readings (qc.STUCK_MIN_READINGS counts 10-min gauge readings)


def summary(readings: list[tuple[dt.datetime, float]], now: dt.datetime) -> dict | None:
    """{"level", "obs_time", "age_min", "trend": qc.observed24 or None, "note": None | "stuck" | "collecting"}."""
    if not readings:
        return None
    rs = sorted(readings)
    t_last, v_last = rs[-1]
    xs = [(t.timestamp(), v) for t, v in rs if t > t_last - dt.timedelta(hours=24)]
    flat = None
    if len(xs) >= STUCK_MIN:
        counts: dict[float, int] = {}
        for _, v in xs:
            counts[v] = counts.get(v, 0) + 1
        top, n = max(counts.items(), key=lambda kv: kv[1])
        flat = top if n / len(xs) >= qc.STUCK_SHARE else None
    trend = None if flat is not None else qc.observed24(xs, 24)
    note = "stuck" if flat is not None else ("collecting" if trend is None else None)
    return {"level": v_last, "obs_time": t_last.isoformat(), "age_min": round((now - t_last).total_seconds() / 60, 1),
            "trend": trend, "note": note}


def items(stations: list[dict], rows: list[dict], now: dt.datetime) -> list[dict]:
    """The map layer: placed posts with a reading in the last 24 h, each with its summary."""
    by: dict[str, list] = {}
    for r in rows:
        by.setdefault(r["code"], []).append((r["obs_time"], float(r["level"])))
    out = []
    for s in stations:
        if s.get("lat") is None or s.get("lon") is None:
            continue
        sm = summary(by.get(s["code"], []), now)
        if not sm or sm["age_min"] > 24 * 60:
            continue
        out.append({"code": s["code"], "name_th": s.get("name_th"), "lat": s["lat"], "lon": s["lon"],
                    "province": s.get("province"), "amphoe": s.get("amphoe"), "tambon": s.get("tambon"), **sm})
    return out
