"""Basins and main rivers from HII's public map files (owner 2026-10-02: "ข้อมูลลุ่มน้ำ … เอาใช้ประโยชน์อะไรได้ไหม").

`https://www.thaiwater.net/json/boundary/basin.json`: the 22 main basins (17 Polygon, 5 MultiPolygon, `BASIN_T`).
`https://www.thaiwater.net/json/river/river_main.json`: 93 main rivers (MultiLineString, `STR_NAMT`). Verified 2026-10-02.

- `basin_of`: the basin a gauge lies in — one consistent scheme for every gauge (HII's station feed names 25 basins
  and leaves 230 gauges without one).
- `river_of`: the main river a gauge sits on (≤ 2 km from its line), else None (a small stream).
- `river_systems`: rivers whose lines touch (≤ 1 km) form one system (Ping + Nan + Chao Phraya); rivers that reach the
  sea apart stay apart (Kolok, Sai Buri). Learned upstream gauges must share the system when both are on main rivers.
Geometry is planar on a local equirectangular projection: fine at these distances.
"""
from __future__ import annotations

import math

RIVER_KM = 2.0
TOUCH_KM = 1.0


def _xy(lat0: float):
    k = math.cos(math.radians(lat0))
    return lambda lon, lat: (lon * 111.32 * k, lat * 110.57)


def _in_ring(x: float, y: float, ring) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _polygons(geom) -> list:
    return [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"] if geom["type"] == "MultiPolygon" else []


def basin_of(lat: float, lon: float, features: list[dict]) -> str | None:
    for f in features:
        for poly in _polygons(f.get("geometry") or {}):
            if poly and _in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, hole) for hole in poly[1:]):
                return f["properties"].get("BASIN_T")
    return None


def _lines(geom) -> list:
    return [geom["coordinates"]] if geom["type"] == "LineString" else geom["coordinates"] if geom["type"] == "MultiLineString" else []


def _seg_km(p, a, b) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _dist_km(lat: float, lon: float, f: dict) -> float:
    xy = _xy(lat)
    p = xy(lon, lat)
    best = math.inf
    for line in _lines(f.get("geometry") or {}):
        pts = [xy(x, y) for x, y in line]
        for a, b in zip(pts, pts[1:] or pts):
            best = min(best, _seg_km(p, a, b))
    return best


def river_of(lat: float, lon: float, rivers: list[dict], max_km: float = RIVER_KM) -> str | None:
    best = min(((_dist_km(lat, lon, f), f["properties"].get("STR_NAMT")) for f in rivers), default=(math.inf, None))
    return best[1] if best[0] <= max_km else None


def river_systems(rivers: list[dict], touch_km: float = TOUCH_KM) -> dict[str, int]:
    """{river name: system id}; two rivers are one system when an end of one lies within touch_km of the other."""
    names = sorted({f["properties"].get("STR_NAMT") for f in rivers if f["properties"].get("STR_NAMT")})
    parent = {n: n for n in names}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    ends = {}
    for f in rivers:
        n = f["properties"].get("STR_NAMT")
        if n:
            ends.setdefault(n, []).extend(p for line in _lines(f["geometry"]) if line for p in (line[0], line[-1]))
    for f in rivers:
        b = f["properties"].get("STR_NAMT")
        for a, pts in ends.items():
            if a == b or not b or find(a) == find(b):
                continue
            if any(_dist_km(lat, lon, f) <= touch_km for lon, lat in pts):
                parent[find(a)] = find(b)
    roots = {n: find(n) for n in names}
    ids = {r: i for i, r in enumerate(sorted(set(roots.values())))}
    return {n: ids[r] for n, r in roots.items()}


def connected(river_a: str | None, river_b: str | None, systems: dict[str, int]) -> bool:
    """Same river system, or unknown for either (a small stream: the basin rule alone applies)."""
    if not river_a or not river_b or river_a not in systems or river_b not in systems:
        return True
    return systems[river_a] == systems[river_b]


def assign(stations: list[dict], basin_features: list[dict], rivers: list[dict]) -> list[dict]:
    """Per gauge: basin22 (the 22-basin scheme, every gauge), basin (HII's name kept; filled as "ลุ่มน้ำ<name>" when
    missing), river_main (≤ 2 km) and river_system (touching rivers joined)."""
    systems = river_systems(rivers)
    out = []
    for s in stations:
        if s.get("lat") is None or s.get("lon") is None:
            continue
        b22 = basin_of(s["lat"], s["lon"], basin_features)
        river = river_of(s["lat"], s["lon"], rivers)
        out.append({"code": s["code"], "basin22": b22, "basin": s.get("basin") or (f"ลุ่มน้ำ{b22}" if b22 else None),
                    "river_main": river, "river_system": systems.get(river) if river else None})
    return out

