"""Point check: what can honestly be said about a place that has no gauge (APPROACH §2.10, D-021).

No water surface is interpolated over land (D-019): Bangkok is not flat, and walls, gates and polders separate
water bodies. Instead, the gauges around the point are summarised as an *area category* (how stressed the
drainage and river system is nearby), with the spread between gauges, a confidence level that falls with
distance and disagreement, and nearby citizen evidence. Pure functions only; the API supplies the rows.
"""
from __future__ import annotations

import math

RANK = {"normal": 0, "watch": 1, "warning": 2, "critical": 3}
LEVELS = ["normal", "watch", "warning", "critical"]
RADIUS_KM = 8.0        # beyond this a gauge says too little about the point
NEAR_KM = 3.0
LIST_KM = 15.0
STREET_ALERT = 3      # street-flood reports within ~1 km in 6 h that override a calm channel picture


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    p = math.pi / 180
    h = (math.sin((b_lat - a_lat) * p / 2) ** 2
         + math.cos(a_lat * p) * math.cos(b_lat * p) * math.sin((b_lon - a_lon) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(h))


def water_body(s: dict) -> str:
    """River gauges describe the river outside the walls; khlong gauges describe drainage inside polders."""
    river = s.get("river") or ""
    return "river" if river.startswith("แม่น้ำ") else "khlong"


def area_index(lat: float, lon: float, stations: list[dict]) -> dict:
    """Inverse-distance-weighted status rank of fresh gauges within RADIUS_KM, reported as a category.

    Interpolates a *normalised state* (status relative to each gauge's own bank), never an absolute level, and
    returns the min/max around it so a user sees when neighbours disagree."""
    near = []
    for s in stations:
        if s.get("lat") is None or s.get("lon") is None or s.get("stale") or s.get("status") not in RANK:
            continue
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if d <= RADIUS_KM:
            near.append((d, s))
    if not near:
        return {"category": None, "confidence": "none", "n": 0}
    weights = [1.0 / max(d, 0.3) ** 2 for d, _ in near]
    score = sum(w * RANK[s["status"]] for w, (_, s) in zip(weights, near)) / sum(weights)
    ranks = [RANK[s["status"]] for _, s in near]
    spread = max(ranks) - min(ranks)
    n_close = sum(d <= NEAR_KM for d, _ in near)
    nearest = min(d for d, _ in near)
    if n_close >= 2 and spread <= 1:
        confidence = "medium"  # never "high": gauges measure channels, not the ground at the point
    elif nearest <= 5.0 and spread <= 1 and (len(near) >= 2 or nearest <= NEAR_KM):
        confidence = "low"  # a single gauge > 3 km away may sit in another polder -> very_low
    else:
        confidence = "very_low"
    return {"category": LEVELS[min(3, int(round(score)))], "score": round(score, 2), "confidence": confidence,
            "n": len(near), "nearest_km": round(nearest, 1), "min": LEVELS[min(ranks)], "max": LEVELS[max(ranks)]}


def assess(lat: float, lon: float, stations: list[dict], reports_1km: int, feedback_depths: dict[str, int],
           rain_next24_mm: float | None) -> dict:
    listed = []
    for s in stations:
        if s.get("lat") is None or s.get("lon") is None:
            continue
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if d <= LIST_KM:
            listed.append({**s, "distance_km": round(d, 1), "water_body": water_body(s)})
    listed.sort(key=lambda s: s["distance_km"])
    idx = area_index(lat, lon, stations)
    warnings = ["no_gauge_at_point", "terrain_not_flat", "walls_and_polders"]
    if idx["confidence"] in ("very_low", "none"):
        warnings.append("gauges_far_or_disagree")
    if listed and listed[0]["distance_km"] > NEAR_KM:
        warnings.append("nearest_gauge_far")
    if reports_1km >= STREET_ALERT and idx.get("category") in ("normal", "watch", None):
        warnings.append("street_flooding_despite_channels")  # canals low, streets flooded: rain vs drains (D-036)

    # Filter active stations: exclude stale or unknown stations so dead gauges do not clutter the sheet
    active = [s for s in listed if not s.get("stale") and s.get("status") not in (None, "unknown")]
    candidates = active if active else listed

    # Predictable stations: stations with tested forecast / trend12
    stations_forecast = [s for s in candidates if s.get("trend12") in ("rising", "falling", "steady") or s.get("delta12_median") is not None][:3]
    fc_codes = {s["code"] for s in stations_forecast}

    # Nearby local stations (avoiding duplicate cards that already appear in forecast)
    stations_nearby = [s for s in candidates if s["code"] not in fc_codes][:3]

    combined = stations_forecast + stations_nearby

    fc_outlook = point_forecast(idx, stations_forecast, stations_nearby, rain_next24_mm, reports_1km)

    return {"lat": round(lat, 3), "lon": round(lon, 3), "area": idx,
            "forecast": fc_outlook,
            "stations": combined,
            "stations_forecast": stations_forecast,
            "stations_nearby": stations_nearby,
            "evidence": {"traffy_flood_reports_1km_6h": reports_1km, "user_depth_reports_1km_24h": feedback_depths},
            "rain_next24_mm": rain_next24_mm, "warnings": warnings}


def point_forecast(area: dict, stations_forecast: list[dict], stations_nearby: list[dict],
                   rain_24h_mm: float | None, reports_1km: int) -> dict:
    """Synthesize a forward-looking 12-24h forecast outlook for the clicked point (USP: D-041)."""
    cat = area.get("category")
    rain = rain_24h_mm or 0.0

    # Hydrological channel trend from nearest forecastable gauges
    trends = [s.get("trend12") for s in stations_forecast if s.get("trend12") in ("rising", "falling", "steady")]
    deltas = [s.get("delta12_median") for s in stations_forecast if s.get("delta12_median") is not None]

    if "rising" in trends or any(d >= 0.04 for d in deltas):
        channel_trend = "rising"
    elif "falling" in trends or any(d <= -0.04 for d in deltas):
        channel_trend = "falling"
    elif trends or deltas:
        channel_trend = "steady"
    else:
        channel_trend = "unknown"

    rain_round = round(rain)

    # 1. High risk conditions
    if reports_1km >= STREET_ALERT and rain >= 20:
        return {
            "risk": "high",
            "channel_trend": channel_trend,
            "title": "เฝ้าระวังน้ำท่วมขังบนถนนต่อเนื่อง",
            "desc": f"มีรายงานน้ำรอระบายในพื้นที่ และมีฝนตกต่อเนื่อง ~{rain_round} มม. ใน 24 ชม."
        }
    if cat in ("critical", "warning") and rain >= 30:
        return {
            "risk": "high",
            "channel_trend": channel_trend,
            "title": "เสี่ยงน้ำท่วมขังเพิ่มขึ้นจากฝนตกหนัก",
            "desc": f"คลองรอบจุดอยู่ในระดับสูง (ใกล้เต็ม) รองรับฝนตกหนัก ~{rain_round} มม. ได้จำกัด ระวังน้ำรอระบายบนถนน"
        }
    if cat == "critical":
        return {
            "risk": "high",
            "channel_trend": channel_trend,
            "title": "ระดับน้ำในคลองล้นตลิ่ง/วิกฤต",
            "desc": "คลองสายหลักรอบจุดนี้ล้นตลิ่ง เฝ้าระวังน้ำเอ่อล้นพื้นที่ลุ่มต่ำริมตลิ่ง"
        }

    # 2. Moderate risk conditions
    if channel_trend == "rising" and cat in ("warning", "watch"):
        rain_str = f" และมีฝน ~{rain_round} มม." if rain >= 15 else ""
        return {
            "risk": "moderate",
            "channel_trend": channel_trend,
            "title": "ระดับน้ำคลองมีแนวโน้มเพิ่มสูงขึ้นใน 12 ชม.",
            "desc": f"สถานีคาดการณ์รอบจุดมีแนวโน้มสูงขึ้น{rain_str} โปรดติดตามสถานการณ์ใกล้ชิด"
        }
    if rain >= 35:
        return {
            "risk": "moderate",
            "channel_trend": channel_trend,
            "title": "เฝ้าระวังน้ำรอระบายจากฝนตกหนัก",
            "desc": f"คาดการณ์ฝนสะสม ~{rain_round} มม. อาจมีน้ำท่วมขังชั่วคราวบนผิวถนนช่วงฝนตก"
        }
    if cat in ("warning", "watch"):
        rain_str = f" มีฝนคาดการณ์ ~{rain_round} มม." if rain >= 15 else " หากไม่มีฝนตกหนักเพิ่มระดับน้ำจะค่อยๆ ทรงตัว"
        return {
            "risk": "moderate",
            "channel_trend": channel_trend,
            "title": "ระดับน้ำคลองค่อนข้างสูง แต่แนวโน้มยังทรงตัว",
            "desc": f"คลองยังระบายน้ำได้ต่อเนื่อง{rain_str}"
        }
    if channel_trend == "rising":
        return {
            "risk": "moderate",
            "channel_trend": channel_trend,
            "title": "ระดับน้ำคลองมีแนวโน้มสูงขึ้นเล็กน้อย",
            "desc": "ระดับน้ำใน 12 ชม. มีแนวโน้มเพิ่มขึ้น แต่ยังอยู่ในเกณฑ์ที่คลองรับน้ำได้"
        }

    # 3. Low risk conditions
    if channel_trend == "falling":
        rain_str = f" ฝนน้อย (~{rain_round} มม.)" if rain < 15 else ""
        return {
            "risk": "low",
            "channel_trend": channel_trend,
            "title": "ระดับน้ำคลองมีแนวโน้มลดลง",
            "desc": f"ระดับน้ำในคลองมีแนวโน้มลดลงต่อเนื่อง{rain_str} ความเสี่ยงน้ำล้นต่ำ"
        }

    # Default calm / steady
    return {
        "risk": "low",
        "channel_trend": channel_trend,
        "title": "สถานการณ์ปกติ / แนวโน้มทรงตัว",
        "desc": f"คลองรอบจุดยังรับน้ำได้ดี คาดการณ์ฝนเบาบาง (~{rain_round} มม.) ความเสี่ยงน้ำท่วมต่ำ"
    }
