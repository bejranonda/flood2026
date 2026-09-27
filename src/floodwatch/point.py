"""Point check: what can honestly be said about a place that has no gauge (APPROACH §2.10, D-021).

No water surface is interpolated over land (D-019): Bangkok is not flat, and walls, gates and polders separate
water bodies. Instead, the gauges around the point are summarised as an *area category* (how stressed the
drainage and river system is nearby), with the spread between gauges, a confidence level that falls with
distance and disagreement, and nearby citizen evidence. Pure functions only; the API supplies the rows.
"""
from __future__ import annotations

import math
from collections import Counter

RANK = {"normal": 0, "watch": 1, "warning": 2, "critical": 3}
LEVELS = ["normal", "watch", "warning", "critical"]
RADIUS_KM = 8.0        # beyond this a gauge says too little about the point
NEAR_KM = 3.0
LIST_KM = 15.0
STREET_ALERT = 3      # street-flood reports within ~1 km in 6 h that override a calm channel picture

# Rain-amount categories of the Thai Meteorological Department (TMD "เกณฑ์อากาศ" page, tmd.go.th/info/เกณฑ์อากาศ,
# read 2026-09-27): เล็กน้อย 0.1–10.0 mm · ปานกลาง 10.1–35.0 · หนัก 35.1–90.0 · หนักมาก ≥ 90.1. They are national
# words for an amount; street flooding also depends on short bursts and local drains (issue #1, KI-224). The same
# bands are mirrored in web/app.js RAIN_TMD — change both together.
RAIN_LIGHT_MAX_MM = 10.0
RAIN_MODERATE_MAX_MM = 35.0
RAIN_HEAVY_MAX_MM = 90.0

# A trend needs a strict majority of same-water-body forecast gauges to be reported (D-042): any single tidal
# river gauge or lone khlong reading is not enough to call a point "rising" (KI: false "rising" on tidal noise).
TREND_DELTA_M = 0.04


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
    near.sort(key=lambda x: x[0])
    # Judge from the nearest gauges (D-054): up to 3 within NEAR_KM. The whole 8 km circle almost always holds some
    # overflowing and some calm canal in Bangkok (83 % of pins were "can't assess" on 2026-09-27), while gauges
    # within ~1-2 km agree 71-86 % of the time (D-042 distance analysis). Far gauges are only counted and ranged.
    close = [x for x in near if x[0] <= NEAR_KM][:3]
    basis = close or near
    weights = [1.0 / max(d, 0.3) ** 2 for d, _ in basis]
    score = sum(w * RANK[s["status"]] for w, (_, s) in zip(weights, basis)) / sum(weights)
    ranks = [RANK[s["status"]] for _, s in basis]
    all_ranks = [RANK[s["status"]] for _, s in near]
    spread = max(ranks) - min(ranks)
    nearest = near[0][0]
    if len(close) >= 2 and spread <= 1:
        confidence = "medium"  # never "high": gauges measure channels, not the ground at the point
    elif close and spread <= 1:
        confidence = "low"  # one gauge within 3 km
    elif not close and nearest <= 5.0 and len(near) >= 2 and spread <= 1:
        confidence = "low"
    else:
        confidence = "very_low"  # close gauges disagree, or the nearest is far (another polder?)
    return {"category": LEVELS[min(3, int(round(score)))], "score": round(score, 2), "confidence": confidence,
            "n": len(near), "n_close": len(close), "nearest_km": round(nearest, 1), "min": LEVELS[min(ranks)],
            "max": LEVELS[max(ranks)], "min_all": LEVELS[min(all_ranks)], "max_all": LEVELS[max(all_ranks)]}


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

    # The canal line the panel leads with (D-054): the nearest fresh canal gauge, never a river gauge (KI-227).
    nc = next((s for s in candidates if s.get("water_body") == "khlong" and not s.get("stale")
               and s.get("status") not in (None, "unknown")), None)
    nearest_canal = None if nc is None else {"code": nc["code"], "distance_km": nc["distance_km"],
                                             "far": nc["distance_km"] > NEAR_KM, "station": nc}
    return {"lat": round(lat, 3), "lon": round(lon, 3), "area": idx, "nearest_canal": nearest_canal,
            "forecast": fc_outlook,
            "stations": combined,
            "stations_forecast": stations_forecast,
            "stations_nearby": stations_nearby,
            "evidence": {"traffy_flood_reports_1km_6h": reports_1km, "user_depth_reports_1km_24h": feedback_depths},
            "rain_next24_mm": rain_next24_mm, "rain_band": (rain_band(rain_next24_mm) or (None,))[0],
            "warnings": warnings}


def _station_trend(s: dict) -> str | None:
    """One gauge's own 12h direction, from its tested trend label or its forecast delta."""
    t = s.get("trend12")
    if t in ("rising", "falling", "steady"):
        return t
    d = s.get("delta12_median")
    if d is None:
        return None
    if d >= TREND_DELTA_M:
        return "rising"
    if d <= -TREND_DELTA_M:
        return "falling"
    return "steady"


def _majority_trend(stations: list[dict]) -> str | None:
    """A strict majority of same-water-body gauges must agree, or the trend is reported as unclear (D-042):
    one tidal river gauge's routine swing, or a single outlier, must not read as a point-wide "rising"."""
    votes = [t for t in (_station_trend(s) for s in stations) if t]
    if not votes:
        return None
    counts = Counter(votes)
    top, n = counts.most_common(1)[0]
    return top if n > len(votes) / 2 else "mixed"


def rain_band(rain_mm: float | None) -> tuple[str, str] | None:
    """(key, Thai TMD label) for a rainfall amount; None when the amount is unknown."""
    if rain_mm is None:
        return None
    if rain_mm < 0.1:
        return "none", "ไม่มีฝน"
    if rain_mm <= RAIN_LIGHT_MAX_MM:
        return "light", "ฝนเล็กน้อย"
    if rain_mm <= RAIN_MODERATE_MAX_MM:
        return "moderate", "ฝนปานกลาง"
    if rain_mm <= RAIN_HEAVY_MAX_MM:
        return "heavy", "ฝนหนัก"
    return "very_heavy", "ฝนหนักมาก"


def _rain_phrase(rain_mm: float) -> tuple[str, str]:
    """(band key, sentence) for a forecast 24h rainfall total. Never invoked when rain is unknown."""
    key, label = rain_band(rain_mm)
    if key == "none":
        return key, "ไม่คาดว่าจะมีฝนใน 24 ชม. ข้างหน้า"
    # No amount here: the panel's rain factor shows it (owner 2026-09-27); this sentence keeps the word + warning.
    tail = {"light": "", "moderate": " อาจมีน้ำขังบนถนนช่วงฝนตก", "heavy": " จุดที่ระบายช้าเสี่ยงน้ำขังบนถนน",
            "very_heavy": " เสี่ยงน้ำขังบนถนนหลายจุด"}[key]
    return key, f"คาด{label}{tail}"


def point_forecast(area: dict, stations_forecast: list[dict], stations_nearby: list[dict],
                   rain_24h_mm: float | None, reports_1km: int) -> dict:
    """The outlook (below) plus the gauges whose own forecast change the banner may show (D-047). Gauges are listed
    only when the area confidence allows a canal statement at all (D-042); each keeps its name and distance, so the
    change is read as "at that gauge", never as a level at the pin (D-021)."""
    out = _outlook(area, stations_forecast, stations_nearby, rain_24h_mm, reports_1km)
    usable = area.get("confidence") in ("low", "medium")
    out["gauges"] = [s["code"] for s in stations_forecast if s.get("change12")] if usable else []
    # When the area gate gives no canal statement, the panel may still show the trend at the nearest *canal* gauge,
    # named with its distance (D-048). Never a river gauge (its tide swing is not canal drainage, KI-223) and never
    # beyond NEAR_KM, where a gauge says little about the pin (D-042 distance analysis).
    canal = next((s for s in stations_forecast if s.get("water_body") == "khlong" and s.get("change12")
                  and s.get("distance_km", 99) <= NEAR_KM), None)
    out["nearest_canal"] = None if out["gauges"] or canal is None else canal["code"]
    return out


def _outlook(area: dict, stations_forecast: list[dict], stations_nearby: list[dict],
             rain_24h_mm: float | None, reports_1km: int) -> dict:
    """Synthesize a forward-looking 12-24h outlook for the clicked point from whatever evidence actually reaches
    it (USP: D-041, gated per D-042): canal/river gauges only when they are close enough and agree (area
    confidence low/medium — see area_index); rainfall and street reports are usable everywhere and are worded
    as conditions, never as a verdict about a channel that has no gauge near this point."""
    cat = area.get("category")
    gauge_usable = area.get("confidence") in ("low", "medium")
    basis = []

    band = rain_sentence = None
    if rain_24h_mm is not None:
        band, rain_sentence = _rain_phrase(rain_24h_mm)
        basis.append("rain")

    channel_trend = "unknown"
    khlong_trend = None
    if gauge_usable:
        khlong = [s for s in stations_forecast if s.get("water_body") == "khlong"]
        khlong_trend = _majority_trend(khlong)
        river_trend = _majority_trend([s for s in stations_forecast if s.get("water_body") == "river"])
        channel_trend = khlong_trend or (f"river_{river_trend}" if river_trend else "unknown")
        if khlong_trend or river_trend:
            basis.append("gauges")

    if reports_1km >= STREET_ALERT:
        basis.append("reports")

    # 1. High risk: strong, local evidence of water on the street or a channel already over its bank
    if reports_1km >= STREET_ALERT and rain_24h_mm is not None and rain_24h_mm >= 20:
        return {"risk": "high", "channel_trend": channel_trend, "basis": basis,
                "title": "เฝ้าระวังน้ำท่วมขังบนถนนต่อเนื่อง",
                "desc": f"มีรายงานน้ำรอระบายในพื้นที่ และ{rain_sentence}"}
    if gauge_usable and cat in ("critical", "warning") and band in ("heavy", "very_heavy"):
        return {"risk": "high", "channel_trend": channel_trend, "basis": basis,
                "title": "เสี่ยงน้ำท่วมขังเพิ่มขึ้นจากฝนตกหนัก",
                "desc": "คลองรอบจุดอยู่ในระดับสูง (ใกล้เต็ม) รองรับฝนหนักที่คาดไว้ได้จำกัด ระวังน้ำรอระบายบนถนน"}
    if gauge_usable and cat == "critical":
        return {"risk": "high", "channel_trend": channel_trend, "basis": basis,
                "title": "ระดับน้ำในคลองล้นตลิ่ง/วิกฤต",
                "desc": "คลองสายหลักรอบจุดนี้ล้นตลิ่ง เฝ้าระวังน้ำเอ่อล้นพื้นที่ลุ่มต่ำริมตลิ่ง"}

    # 2. Moderate risk: heavy rain anywhere, a rising khlong nearby, or repeated street reports alone
    if reports_1km >= STREET_ALERT:
        return {"risk": "moderate", "channel_trend": channel_trend, "basis": basis,
                "title": "มีรายงานน้ำรอระบายบนถนนใกล้จุดนี้",
                "desc": "ผู้ใช้งานแจ้งน้ำขังบนถนนในระยะ 1 กม. ช่วง 6 ชม.ที่ผ่านมา โปรดระวังการเดินทาง"}
    if band in ("heavy", "very_heavy"):
        return {"risk": "moderate", "channel_trend": channel_trend, "basis": basis,
                "title": "เฝ้าระวังน้ำรอระบายจากฝนตกหนัก",
                "desc": rain_sentence}
    if gauge_usable and khlong_trend == "rising" and cat in ("warning", "watch"):
        extra = f" {rain_sentence}" if band == "moderate" else ""
        return {"risk": "moderate", "channel_trend": channel_trend, "basis": basis,
                "title": "ระดับน้ำคลองมีแนวโน้มเพิ่มสูงขึ้นใน 12 ชม.",
                "desc": f"สถานีคาดการณ์รอบจุดมีแนวโน้มสูงขึ้น{extra} โปรดติดตามสถานการณ์ใกล้ชิด"}
    if gauge_usable and cat in ("warning", "watch"):
        extra = f" {rain_sentence}" if band == "moderate" else " หากไม่มีฝนตกหนักเพิ่ม ระดับน้ำจะค่อยๆ ทรงตัว"
        return {"risk": "moderate", "channel_trend": channel_trend, "basis": basis,
                "title": "ระดับน้ำคลองค่อนข้างสูง แต่แนวโน้มยังทรงตัว",
                "desc": f"คลองยังระบายน้ำได้ต่อเนื่อง{extra}"}
    if gauge_usable and khlong_trend == "rising":
        return {"risk": "moderate", "channel_trend": channel_trend, "basis": basis,
                "title": "ระดับน้ำคลองมีแนวโน้มสูงขึ้นเล็กน้อย",
                "desc": "ระดับน้ำใน 12 ชม. มีแนวโน้มเพิ่มขึ้น แต่ยังอยู่ในเกณฑ์ที่คลองรับน้ำได้"}

    # 3. Low risk: only said when a nearby gauge is actually close enough to say it
    if gauge_usable and khlong_trend == "falling":
        extra = f" {rain_sentence}" if band else ""
        return {"risk": "low", "channel_trend": channel_trend, "basis": basis,
                "title": "ระดับน้ำคลองมีแนวโน้มลดลง",
                "desc": f"ระดับน้ำในคลองใกล้จุดนี้มีแนวโน้มลดลงต่อเนื่อง{extra}"}
    if gauge_usable:
        extra = f" {rain_sentence}" if band else ""
        return {"risk": "low", "channel_trend": channel_trend, "basis": basis,
                "title": "สถานีใกล้เคียงยังไม่มีสัญญาณน้ำเพิ่มผิดปกติ",
                "desc": f"คลอง/แม่น้ำใกล้จุดนี้ยังทรงตัว{extra}"}

    # 4. No usable gauge and no strong local evidence: say so, worded from rain alone, never a "safe" verdict.
    # Say *why*: gauges close by that disagree (e.g. a river gauge 0.8 km away and canals beyond it) are not "far".
    near = area.get("nearest_km")
    if near is not None and near <= NEAR_KM:
        title = "สถานีรอบจุดนี้ให้ข้อมูลไม่ตรงกัน จึงยังสรุประดับคลองที่จุดนี้ไม่ได้"
        why = "สถานีใกล้เคียงวัดคนละแหล่งน้ำ (แม่น้ำ/คลอง) หรือคนละพื้นที่ปิดล้อม ดูแนวโน้มของแต่ละสถานีด้านล่าง"
    else:
        title = "ไม่มีสถานีวัดน้ำใกล้พอที่จะประเมินคลองที่จุดนี้"
        why = "สถานีวัดน้ำใกล้เคียงอยู่ไกลหรือคนละลุ่มน้ำ จึงบอกระดับคลองที่จุดนี้ไม่ได้"
    if rain_sentence:
        return {"risk": "info", "channel_trend": "unknown", "basis": basis, "title": title,
                "desc": f"{rain_sentence} {why}"}
    return {"risk": "info", "channel_trend": "unknown", "basis": basis,
            "title": "ไม่มีข้อมูลพอที่จะประเมินจุดนี้",
            "desc": "ไม่มีสถานีวัดน้ำหรือข้อมูลฝนใกล้พอที่จะประเมิน โปรดตรวจสอบประกาศของหน่วยงานในพื้นที่"}
