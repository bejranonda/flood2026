"""Mapbox Vector Tiles, read without dependencies (spec 2.1), for ONWR's flood layers on the impact map (owner 2026-10-06).

Tile.layers (3) → Layer: name (1), features (2), keys (3), values (4), extent (5), version (15); Feature: id (1), tags
(2, packed key/value indexes), type (3; 3 = polygon), geometry (4, packed commands); Value: string (1), float (2),
double (3), int (4), uint (5), sint (6), bool (7). Geometry commands: MoveTo 1, LineTo 2, ClosePath 7, zigzag deltas.
"""
from __future__ import annotations

import math
import struct


def _varint(buf, i: int) -> tuple[int, int]:
    shift = result = 0
    while True:
        b = buf[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, i
        shift += 7


def _fields(buf):
    """(field number, wire type, value) of one message; length-delimited values as memoryview slices."""
    i, n = 0, len(buf)
    while i < n:
        key, i = _varint(buf, i)
        num, wire = key >> 3, key & 7
        if wire == 0:
            v, i = _varint(buf, i)
        elif wire == 1:
            v, i = buf[i:i + 8], i + 8
        elif wire == 2:
            ln, i = _varint(buf, i)
            v, i = buf[i:i + ln], i + ln
        elif wire == 5:
            v, i = buf[i:i + 4], i + 4
        else:
            raise ValueError(f"wire type {wire}")
        yield num, wire, v


def _packed(buf) -> list[int]:
    out, i = [], 0
    while i < len(buf):
        v, i = _varint(buf, i)
        out.append(v)
    return out


def _value(buf):
    for num, _wire, v in _fields(buf):
        if num == 1:
            return bytes(v).decode("utf-8", "replace")
        if num == 2:
            return struct.unpack("<f", bytes(v))[0]
        if num == 3:
            return struct.unpack("<d", bytes(v))[0]
        if num == 4:
            return v - (1 << 64) if v >= 1 << 63 else v
        if num == 5:
            return v
        if num == 6:
            return (v >> 1) ^ -(v & 1)
        if num == 7:
            return bool(v)
    return None


def _rings(cmds: list[int]) -> list[list[tuple[int, int]]]:
    rings, cur, x, y, i = [], [], 0, 0, 0
    while i < len(cmds):
        cmd, count = cmds[i] & 7, cmds[i] >> 3
        i += 1
        if cmd == 7:  # ClosePath: back to the ring's first vertex
            if cur:
                rings.append(cur + [cur[0]])
                cur = []
            continue
        for _ in range(count):
            dx, dy = cmds[i], cmds[i + 1]
            i += 2
            x += (dx >> 1) ^ -(dx & 1)
            y += (dy >> 1) ^ -(dy & 1)
            if cmd == 1:
                if cur:
                    rings.append(cur)
                cur = [(x, y)]
            else:
                cur.append((x, y))
    if cur:
        rings.append(cur)
    return rings


def decode(data: bytes) -> dict:
    """{layer name: {"extent", "features": [{"id", "type", "properties", "rings"}]}} in tile coordinates; {} for an
    empty or broken tile."""
    out: dict = {}
    try:
        for num, _wire, v in _fields(memoryview(data)):
            if num != 3:
                continue
            name, keys, vals, feats, extent = None, [], [], [], 4096
            for n2, _w2, v2 in _fields(v):
                if n2 == 1:
                    name = bytes(v2).decode("utf-8", "replace")
                elif n2 == 2:
                    feats.append(v2)
                elif n2 == 3:
                    keys.append(bytes(v2).decode("utf-8", "replace"))
                elif n2 == 4:
                    vals.append(_value(v2))
                elif n2 == 5:
                    extent = v2
            features = []
            for fb in feats:
                f = {"id": None, "type": 0, "properties": {}, "rings": []}
                for n3, _w3, v3 in _fields(fb):
                    if n3 == 1:
                        f["id"] = v3
                    elif n3 == 2:
                        tags = _packed(v3)
                        f["properties"] = {keys[tags[k]]: vals[tags[k + 1]] for k in range(0, len(tags) - 1, 2)}
                    elif n3 == 3:
                        f["type"] = v3
                    elif n3 == 4:
                        f["rings"] = _rings(_packed(v3))
                features.append(f)
            out[name] = {"extent": extent, "features": features}
    except (IndexError, ValueError, struct.error):
        return {}
    return out


def to_latlon(px: float, py: float, z: int, x: int, y: int, extent: int = 4096) -> tuple[float, float]:
    """A tile coordinate of tile z/x/y as (lat, lon), Web Mercator."""
    n = 2 ** z
    lon = (x + px / extent) / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + py / extent) / n))))
    return lat, lon


def tiles_for_bbox(lat0: float, lon0: float, lat1: float, lon1: float, z: int) -> list[tuple[int, int]]:
    """Every tile (x, y) at zoom z that touches the box (south-west lat0/lon0, north-east lat1/lon1)."""
    def xy(lat, lon):
        n = 2 ** z
        return int((lon + 180) / 360 * n), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    x0, y1 = xy(lat0, lon0)
    x1, y0 = xy(lat1, lon1)
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def ring_overlaps_bbox(ring, lat0: float, lon0: float, lat1: float, lon1: float) -> bool:
    """A ring of [lat, lon] whose own bounding box overlaps the box (lat0, lon0, lat1, lon1). ONWR's cells are ≈ 1.1 km
    hexagons, so boxes overlapping is shapes overlapping to within a cell (KI-318)."""
    if not ring:
        return False
    lats = [p[0] for p in ring]
    lons = [p[1] for p in ring]
    return min(lats) <= lat1 and max(lats) >= lat0 and min(lons) <= lon1 and max(lons) >= lon0
