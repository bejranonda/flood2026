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


# Bangkok and its neighbours at the model's own grid (Q42, v0.16.4): Open-Meteo's grid near Bangkok, measured
# 2026-10-01, is 0.0703° (lat) x ~0.0826° (lon), ~7.8 x 9 km. One point per grid cell within FINE_KM (12 km) of a gauge in
# the six Bangkok-region provinces. Used for what people see (pin panel, region rain line); the forecast model keeps
# RAIN_POINTS, on which its skill was proven.
FINE_LAT0, FINE_DLAT = 13.3919, 0.0703
FINE_LON0, FINE_DLON = 100.3306, 0.08265
FINE_KM = 12.0  # the 3 x 3 grid cells around each gauge (diagonal ~11.9 km), so pins between gauges are covered
FINE_PROVINCES = ("กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "นครปฐม")


def fine_of(lat: float, lon: float) -> tuple[str, float, float]:
    i = math.floor((lat - FINE_LAT0) / FINE_DLAT + 0.5)
    j = math.floor((lon - FINE_LON0) / FINE_DLON + 0.5)
    flat, flon = round(FINE_LAT0 + i * FINE_DLAT, 4), round(FINE_LON0 + j * FINE_DLON, 4)
    return f"f_{flat:.4f}_{flon:.4f}", flat, flon


def fine_points(stations) -> dict[str, tuple[float, float]]:
    """Fine grid points within FINE_KM of any gauge in the Bangkok region: {point id: (lat, lon)}."""
    out = {}
    for s in stations:
        if s.get("province") not in FINE_PROVINCES or s.get("lat") is None or s.get("lon") is None:
            continue
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                pid, flat, flon = fine_of(s["lat"] + di * FINE_DLAT, s["lon"] + dj * FINE_DLON)
                if math.hypot((flat - s["lat"]) * 111.0, (flon - s["lon"]) * 111.0 * math.cos(math.radians(s["lat"]))) <= FINE_KM:
                    out[pid] = (flat, flon)
    return out


def rain_point_at(lat: float, lon: float, fine: set[str] | None = None) -> str:
    """The rain series for a place (point check): its fine grid point when that has data (Bangkok region), else a
    Bangkok point nearby, else the place's 0.5° cell."""
    if fine:
        pid = fine_of(lat, lon)[0]
        if pid in fine:
            return pid
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
