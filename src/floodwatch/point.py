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
    return {"lat": round(lat, 3), "lon": round(lon, 3), "area": idx, "stations": listed[:5],
            "evidence": {"traffy_flood_reports_1km_6h": reports_1km, "user_depth_reports_1km_24h": feedback_depths},
            "rain_next24_mm": rain_next24_mm, "warnings": warnings}
