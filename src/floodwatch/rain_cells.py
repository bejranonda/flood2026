"""Rain inputs per gauge (D-064).

Focus gauges (Bangkok + lower Chao Phraya) keep the nine `RAIN_POINTS` their backtests were proven on. Every other
gauge reads rain from a 0.5° cell (~55 km, catchment scale; 177 cells for the HII network on 2026-09-30), so a gauge
in Loei no longer gets Bangkok's rain. Open-Meteo serves many cells in one request (comma-separated coordinates,
checked 2026-09-30 for the forecast and previous-runs APIs).
"""
from __future__ import annotations

import math

from floodwatch.config import RAIN_POINTS

CELL_DEG = 0.5
NEAR_POINT_DEG = 0.5  # a place this close to a Bangkok rain point uses it (point check)
BATCH = 50

# Latest issue per point: cells refresh every 3 h, Bangkok points hourly, so a global max(issue_time) would lose
# the cells between their refreshes. Join as `JOIN (LATEST_ISSUE) l ON l.point=w.point AND l.t=w.issue_time`.
LATEST_ISSUE = "SELECT point, max(issue_time) AS t FROM weather_forecast GROUP BY point"


def _snap(x: float) -> float:
    return math.floor(x / CELL_DEG + 0.5) * CELL_DEG


def cell_of(lat: float, lon: float) -> tuple[str, float, float]:
    clat, clon = _snap(lat), _snap(lon)
    return f"g_{clat:.1f}_{clon:.1f}", clat, clon


def _nearest_point(lat: float, lon: float) -> tuple[str, float]:
    k = min(RAIN_POINTS, key=lambda p: (RAIN_POINTS[p][0] - lat) ** 2 + (RAIN_POINTS[p][1] - lon) ** 2)
    return k, math.hypot(RAIN_POINTS[k][0] - lat, RAIN_POINTS[k][1] - lon)


def rain_point_for(in_focus: bool, lat: float | None, lon: float | None) -> str | None:
    """The rain series a gauge's forecast uses."""
    if lat is None or lon is None:
        return None
    return _nearest_point(lat, lon)[0] if in_focus else cell_of(lat, lon)[0]


def rain_point_at(lat: float, lon: float) -> str:
    """The rain series for a place (point check): a Bangkok point nearby, else the place's cell."""
    k, d = _nearest_point(lat, lon)
    return k if d <= NEAR_POINT_DEG else cell_of(lat, lon)[0]


def all_cells(stations) -> dict[str, tuple[float, float]]:
    """Cells needed by the gauges outside the focus area: {cell id: (lat, lon)}."""
    out = {}
    for s in stations:
        if not s["in_focus"] and s["lat"] is not None and s["lon"] is not None:
            cid, clat, clon = cell_of(s["lat"], s["lon"])
            out[cid] = (clat, clon)
    return out


def batches(items: list, n: int = BATCH) -> list[list]:
    return [items[i:i + n] for i in range(0, len(items), n)]


def split_payload(payload, ids: list[str]) -> list[tuple[str, dict]]:
    """Open-Meteo answers a list for several coordinates and one object for a single coordinate."""
    return list(zip(ids, payload if isinstance(payload, list) else [payload]))
