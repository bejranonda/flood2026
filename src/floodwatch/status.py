"""One trend rule for the whole app: "น้ำยังขึ้น" / "ทรงตัวหรือลดลง" (owner 2026-10-04: "Forecast if sure direction: higher,
lower, stable. ไม่แน่ชัด can suggest with measured recent change as fallback … show two labels as summary"; D-083).

Computed once per station row (api._station_row) and read by every view (list, sheet, river cards, จับตา, top bar), so
the views cannot disagree. "Sure" follows the rows' own chips (app.js `directional` and `narrow`): a direction a real
model proved with a likely range that agrees, or "→ ทรงตัว" (likely range within ±5 cm). Otherwise the measured recent
change decides, with the model's "recent" rule (forecast.recent_rate): the smaller of the 24 h and 6 h pace, none when
they disagree, so a rise that stopped is not "rising".
"""
from __future__ import annotations

STEADY_M = 0.05     # "→ ทรงตัว" only when the likely range stays within ±5 cm (D-060, app.js STEADY_M)
RISE_CM_24H = 2.0   # a measured pace below 2 cm per 24 h is "steady" (qc.observed24's own steady band)


def _agrees(ch: dict) -> bool:
    lk = ch.get("likely")
    if not lk:
        return True
    return lk[1] < 0 if ch.get("dir") == "falling" else lk[0] > 0 if ch.get("dir") == "rising" else True


def forecast_label(ch: dict | None) -> str | None:
    """"up" | "down" | "steady" when the row is sure, "unsure" for "? ไม่แน่ชัด", None without a row."""
    if not ch:
        return None
    if ch.get("level") != "steady" and ch.get("method") not in (None, "persistence") and _agrees(ch):
        return "up" if ch.get("dir") == "rising" else "down" if ch.get("dir") == "falling" else "unsure"
    lk = ch.get("likely")
    if lk and not ch.get("wide") and max(abs(lk[0]), abs(lk[1])) <= STEADY_M:
        return "steady"
    return "unsure"


def measured_label(obs: dict | None) -> str | None:
    """"up" | "down" | "steady" from the measured recent pace, None without a measured line."""
    if not obs or obs.get("change_cm") is None:
        return None
    r24 = obs["change_cm"] / (obs.get("hours") or 24)  # cm/h
    r6 = obs.get("change6_cm")
    if r6 is not None:
        r6 /= 6.0
        rate = 0.0 if r6 == 0 or r24 == 0 or (r6 > 0) != (r24 > 0) else (min(abs(r24), abs(r6)) * (1 if r24 > 0 else -1))
    else:
        rate = r24
    return "up" if rate * 24 >= RISE_CM_24H else "down" if rate * 24 <= -RISE_CM_24H else "steady"


def trend(s: dict) -> dict | None:
    """{"group": "rising" | "flat_or_falling", "forecast", "measured", "basis": "forecast" | "measured"} or None."""
    if s.get("stale"):
        return None
    fc = forecast_label(s.get("change24") or s.get("change12"))
    me = measured_label(s.get("observed24"))
    if fc in ("up", "down", "steady"):
        return {"group": "rising" if fc == "up" else "flat_or_falling", "forecast": fc, "measured": me, "basis": "forecast"}
    if me is None:
        return None
    return {"group": "rising" if me == "up" else "flat_or_falling", "forecast": fc, "measured": me, "basis": "measured"}
