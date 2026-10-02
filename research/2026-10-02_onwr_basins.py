#!/usr/bin/env python3
"""ONWR's legal 22 main basins vs HII's basin.json: do our gauges land in the same basin? (owner 2026-10-02: downloaded
"Shp_Basin_ONWR" from the DWR page https://division.dwr.go.th/rdhd/index.php/th/services/12/2024-04-17-02-39-05/160-shapefiles)

Run on the server (reads the unzipped shapefile and the DB; writes nothing):
    (unzip data/basins/raw/Shp_Basin_ONWR-*.zip into a scratch dir <d> first; the run used the 2026-10-02 download)
    docker compose run --rm --no-deps -v "$PWD/research:/research" -v "<d>:/onwr" worker \
        python /research/2026-10-02_onwr_basins.py /onwr/Shp_Basin_ONWR/MainBasin_ONWR_Law_WGS84
A tidy lon/lat GeoJSON of the same file: data/basins/onwr_basins_22.geojson (scripts/prepare_basins.py).

Pure Python + numpy: a minimal shapefile reader (Polygon, type 5), a UTM 47N inverse (Snyder 1987), CP874 attributes.
"""
import json
import math
import struct
import sys
from collections import Counter

import numpy as np

from floodwatch import basins, db
from floodwatch.httpclient import fetch

A, F, K0, LON0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(99.0)
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)
E1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))


def utm47_to_lonlat(x: float, y: float) -> tuple[float, float]:
    x -= 500000.0
    mu = y / K0 / (A * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256))
    p = (mu + (3 * E1 / 2 - 27 * E1 ** 3 / 32) * math.sin(2 * mu) + (21 * E1 ** 2 / 16 - 55 * E1 ** 4 / 32) * math.sin(4 * mu)
         + 151 * E1 ** 3 / 96 * math.sin(6 * mu) + 1097 * E1 ** 4 / 512 * math.sin(8 * mu))
    s, c, t = math.sin(p), math.cos(p), math.tan(p)
    C, T = EP2 * c * c, t * t
    N = A / math.sqrt(1 - E2 * s * s)
    R = A * (1 - E2) / (1 - E2 * s * s) ** 1.5
    D = x / (N * K0)
    lat = p - N * t / R * (D ** 2 / 2 - (5 + 3 * T + 10 * C - 4 * C * C - 9 * EP2) * D ** 4 / 24
                           + (61 + 90 * T + 298 * C + 45 * T * T - 252 * EP2 - 3 * C * C) * D ** 6 / 720)
    lon = LON0 + (D - (1 + 2 * T + C) * D ** 3 / 6 + (5 - 2 * C + 28 * T - 3 * C * C + 8 * EP2 + 24 * T * T) * D ** 5 / 120) / c
    return math.degrees(lon), math.degrees(lat)


def read_dbf(path: str) -> list[dict]:
    d = open(path, "rb").read()
    n, hl, rl = struct.unpack("<IHH", d[4:12])
    fields, i = [], 32
    while d[i] != 0x0D:
        fields.append((d[i:i + 11].split(b"\0")[0].decode(), d[i + 16]))
        i += 32
    out, off = [], hl
    for _ in range(n):
        rec, p, row = d[off + 1:off + rl], 0, {}
        for name, ln in fields:
            row[name] = rec[p:p + ln].decode("cp874").strip()
            p += ln
        out.append(row)
        off += rl
    return out


def _signed_area(ring) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1])) / 2


def read_shp(path: str) -> list[list]:
    """Per record: a list of polygons [outer, *holes] in lon/lat (shapefile outer rings are clockwise)."""
    d = open(path, "rb").read()
    out, off = [], 100
    while off < len(d):
        _, clen = struct.unpack(">ii", d[off:off + 8])
        rec = d[off + 8:off + 8 + clen * 2]
        off += 8 + clen * 2
        if struct.unpack("<i", rec[:4])[0] != 5:
            out.append([])
            continue
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])) + [npts]
        pts = np.frombuffer(rec[44 + 4 * nparts:44 + 4 * nparts + 16 * npts], dtype="<f8").reshape(-1, 2)
        polys = []
        for a, b in zip(parts, parts[1:]):
            ring = [utm47_to_lonlat(x, y) for x, y in pts[a:b]]
            if _signed_area(ring) < 0 or not polys:  # clockwise: a new outer ring
                polys.append([ring])
            else:
                polys[-1].append(ring)
        out.append(polys)
    return out


def area_km2(polys) -> float:
    tot = 0.0
    for poly in polys:
        for k, ring in enumerate(poly):
            lat0 = ring[0][1]
            xy = [(lon * 111.32 * math.cos(math.radians(lat0)), lat * 110.57) for lon, lat in ring]
            tot += abs(_signed_area(xy)) * (1 if k == 0 else -1)
    return tot


def inside(lon: np.ndarray, lat: np.ndarray, ring) -> np.ndarray:
    r = np.asarray(ring)
    x1, y1 = r[:, 0], r[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    res = np.zeros(len(lon), bool)
    for k in range(len(lon)):
        c = (y1 > lat[k]) != (y2 > lat[k])
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = (x2[c] - x1[c]) * (lat[k] - y1[c]) / (y2[c] - y1[c]) + x1[c]
        res[k] = np.count_nonzero(lon[k] < xi) % 2 == 1
    return res


def assign(lon, lat, features: list[tuple[str, list]]) -> list:
    out = [None] * len(lon)
    for name, polys in features:
        for poly in polys:
            r = np.asarray(poly[0])
            box = (lon >= r[:, 0].min()) & (lon <= r[:, 0].max()) & (lat >= r[:, 1].min()) & (lat <= r[:, 1].max())
            idx = np.nonzero(box)[0]
            if not len(idx):
                continue
            hit = inside(lon[idx], lat[idx], poly[0])
            for hole in poly[1:]:
                hit &= ~inside(lon[idx], lat[idx], hole)
            for k in idx[hit]:
                out[k] = out[k] or name
    return out


def boundary_km(lon: float, lat: float, polys) -> float:
    f = {"geometry": {"type": "MultiLineString", "coordinates": [ring for poly in polys for ring in poly]}}
    return basins._dist_km(lat, lon, f)


def main(base: str):
    rows, shapes = read_dbf(base + ".dbf"), read_shp(base + ".shp")
    onwr = {}
    for r, polys in zip(rows, shapes):  # "10-is" (islands) joins basin "10"
        onwr.setdefault(r["MBASIN_T"].replace(" (เกาะ)", ""), []).extend(polys)
    hii = json.loads(fetch("https://www.thaiwater.net/json/boundary/basin.json").body)["features"]
    hii_f = [(f["properties"]["BASIN_T"], basins._polygons(f["geometry"])) for f in hii]
    print(f"ONWR: {len(rows)} records -> {len(onwr)} basins, {sum(len(r) for p in shapes for poly in p for r in poly):,} vertices;"
          f" HII: {len(hii)} basins, {sum(len(r) for _, p in hii_f for poly in p for r in poly):,} vertices")
    hn = {n for n, _ in hii_f}
    print("names only in ONWR:", sorted(set(onwr) - hn), "| only in HII:", sorted(hn - set(onwr)))
    print("area km2 (ONWR file field vs HII polygon):")
    field = Counter()
    for r in rows:
        field[r["MBASIN_T"].replace(" (เกาะ)", "")] += float(r["AREA_SQKM"])
    hii_area = {n: area_km2(p) for n, p in hii_f}
    for n in sorted(onwr, key=lambda k: -field[k]):
        print(f"  {n:<28} ONWR {field[n]:>9,.0f}  (computed {area_km2(onwr[n]):>9,.0f})  HII {hii_area.get(n, float('nan')):>9,.0f}")

    with db.connect() as c:
        st = c.execute("""SELECT code, lat, lon, agency, in_focus, basin22 FROM station
                          WHERE lat IS NOT NULL AND code !~ '^TEST'""").fetchall()
    lon = np.array([s["lon"] for s in st])
    lat = np.array([s["lat"] for s in st])
    a_o = assign(lon, lat, list(onwr.items()))
    a_h = assign(lon, lat, hii_f)
    same = sum(1 for x, y in zip(a_o, a_h) if x == y and x)
    print(f"\n{len(st)} gauges: same basin {same}; ONWR only {sum(1 for x, y in zip(a_o, a_h) if x and not y)};"
          f" HII only {sum(1 for x, y in zip(a_o, a_h) if y and not x)}; neither {sum(1 for x, y in zip(a_o, a_h) if not x and not y)};"
          f" different {sum(1 for x, y in zip(a_o, a_h) if x and y and x != y)}")
    for s, x, y in zip(st, a_o, a_h):
        if x != y:
            km = boundary_km(s["lon"], s["lat"], onwr[x] if x else onwr[y] if y in onwr else [])
            print(f"  {s['code']:<10} {s['agency'] or '':<5} focus={s['in_focus']!s:<5} ONWR {x or '-':<24} HII {y or '-':<24}"
                  f" ONWR boundary {km:5.1f} km")


if __name__ == "__main__":
    main(sys.argv[1])
