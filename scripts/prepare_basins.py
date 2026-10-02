#!/usr/bin/env python3
"""Tidy the basin maps the owner downloads into small, reusable files (owner 2026-10-02: "you can also reorganize the
shape files for better").

Input (owner downloads, not in git: no redistribution licence stated for ONWR; HydroBASINS is 413 MB):
    data/basins/raw/Shp_Basin_ONWR-*.zip           ONWR legal 22 main basins (DWR page, SOURCES §2i), UTM 47N, CP874
    data/basins/raw/hybas_lake_as_lev01-12_v1c.zip HydroBASINS v1c Asia with lakes (Lehner & Grill 2013)
Output (data/basins/, git-ignored like all runtime data):
    onwr_basins_22.geojson         22 basins (island parts merged), lon/lat, UTF-8: code, name_th, name_en, area_km2
    hydrobasins_lev08_th.geojson   level-8 sub-basins touching Thailand plus everything upstream of them (Mekong,
                                   Salween), with HYBAS_ID, NEXT_DOWN, NEXT_SINK, MAIN_BAS, SUB_AREA, UP_AREA, PFAF_ID
    README.md, SHA256SUMS

    python3 scripts/prepare_basins.py [level=08]
Pure Python + numpy. Readers as in research/2026-10-02_onwr_basins.py and research/2026-10-02_catchment_rain.py.
"""
import datetime as dt
import glob
import hashlib
import json
import math
import pathlib
import struct
import sys
import zipfile

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "basins"
RAW = OUT / "raw"
TH_BOX = (97.3, 5.6, 105.7, 20.5)  # Thailand's extent (ONWR file bbox, rounded out)

A, F, K0, LON0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(99.0)
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)
E1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))


def utm47_to_lonlat(x: float, y: float) -> tuple[float, float]:
    """UTM zone 47N → WGS84 (Snyder 1987); sub-metre within Thailand."""
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


def read_dbf(d: bytes, encoding: str) -> list[dict]:
    n, hl, rl = struct.unpack("<IHH", d[4:12])
    fields, i = [], 32
    while d[i] != 0x0D:
        fields.append((d[i:i + 11].split(b"\0")[0].decode(), d[i + 16]))
        i += 32
    out, off = [], hl
    for _ in range(n):
        rec, p, row = d[off + 1:off + rl], 0, {}
        for name, ln in fields:
            row[name] = rec[p:p + ln].decode(encoding).strip()
            p += ln
        out.append(row)
        off += rl
    return out


def read_shp(d: bytes, keep=None) -> list:
    """Per record: a list of rings (N×2 arrays), or None (null shape, or `keep(bbox)` is False)."""
    out, off = [], 100
    while off < len(d):
        _, clen = struct.unpack(">ii", d[off:off + 8])
        rec = d[off + 8:off + 8 + clen * 2]
        off += 8 + clen * 2
        if struct.unpack("<i", rec[:4])[0] != 5 or (keep and not keep(struct.unpack("<4d", rec[4:36]))):
            out.append(None)
            continue
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])) + [npts]
        pts = np.frombuffer(rec[44 + 4 * nparts:44 + 4 * nparts + 16 * npts], dtype="<f8").reshape(-1, 2)
        out.append([pts[a:b] for a, b in zip(parts, parts[1:])])
    return out


def _area2(ring) -> float:
    x, y = ring[:, 0], ring[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def to_multipolygon(rings: list, nd: int) -> list:
    """Shapefile rings (outer clockwise, holes counter-clockwise) → GeoJSON MultiPolygon coordinates."""
    polys = []
    for r in rings:
        coords = [[round(float(x), nd), round(float(y), nd)] for x, y in r]
        if _area2(r) < 0 or not polys:
            polys.append([coords[::-1]])  # GeoJSON (RFC 7946): outer rings counter-clockwise
        else:
            polys[-1].append(coords[::-1])
    return polys


def write_geojson(path: pathlib.Path, features: list[dict]) -> None:
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False,
                               separators=(",", ":")), encoding="utf-8")


def onwr(zpath: pathlib.Path) -> int:
    z = zipfile.ZipFile(zpath)
    base = next(n[:-4] for n in z.namelist() if n.endswith("MainBasin_ONWR_Law_WGS84.shp"))
    rows = read_dbf(z.read(base + ".dbf"), "cp874")
    shapes = read_shp(z.read(base + ".shp"))
    merged: dict[str, dict] = {}
    for r, rings in zip(rows, shapes):
        code = r["MB_CODE"].split("-")[0]  # "10-is" (islands) belongs to basin 10
        f = merged.setdefault(code, {"code": code, "name_th": r["MBASIN_T"].replace(" (เกาะ)", ""),
                                     "name_en": r["MBASIN_E"].replace(" (Island)", ""), "area_km2": 0.0, "polys": []})
        f["area_km2"] += float(r["AREA_SQKM"])
        if rings:
            ll = [np.array([utm47_to_lonlat(x, y) for x, y in ring]) for ring in rings]
            f["polys"] += to_multipolygon(ll, 5)
    feats = [{"type": "Feature", "properties": {k: (round(v, 1) if k == "area_km2" else v) for k, v in f.items() if k != "polys"},
              "geometry": {"type": "MultiPolygon", "coordinates": f["polys"]}} for f in sorted(merged.values(), key=lambda f: f["code"])]
    write_geojson(OUT / "onwr_basins_22.geojson", feats)
    return len(feats)


def hydrobasins(zpath: pathlib.Path, level: str) -> int:
    z = zipfile.ZipFile(zpath)
    stem = f"hybas_lake_as_lev{level}_v1c"
    rows = read_dbf(z.read(stem + ".dbf"), "latin-1")
    ids = [int(r["HYBAS_ID"]) for r in rows]
    meets = lambda b: not (b[2] < TH_BOX[0] or b[0] > TH_BOX[2] or b[3] < TH_BOX[1] or b[1] > TH_BOX[3])
    shapes = read_shp(z.read(stem + ".shp"))
    # keep: sub-basins touching Thailand, the ones they drain to, and everything upstream of them
    ups: dict[int, list[int]] = {}
    down = {int(r["HYBAS_ID"]): int(r["NEXT_DOWN"]) for r in rows}
    for h, d in down.items():
        ups.setdefault(d, []).append(h)
    seeds = {h for h, g in zip(ids, shapes) if g and meets((min(r[:, 0].min() for r in g), min(r[:, 1].min() for r in g),
                                                            max(r[:, 0].max() for r in g), max(r[:, 1].max() for r in g)))}
    keep, todo = set(seeds), list(seeds)
    while todo:
        for u in ups.get(todo.pop(), ()):
            if u not in keep:
                keep.add(u)
                todo.append(u)
    for h in list(seeds):  # downstream to the sea, so every chain inside the file ends
        while down.get(h) and down[h] not in keep:
            keep.add(down[h])
            h = down[h]
    props = ("HYBAS_ID", "NEXT_DOWN", "NEXT_SINK", "MAIN_BAS", "SUB_AREA", "UP_AREA", "PFAF_ID")
    feats = []
    for r, g in zip(rows, shapes):
        if int(r["HYBAS_ID"]) in keep and g:
            p = {k: (float(r[k]) if k in ("SUB_AREA", "UP_AREA") else int(r[k])) for k in props}
            feats.append({"type": "Feature", "properties": p, "geometry": {"type": "MultiPolygon", "coordinates": to_multipolygon(g, 4)}})
    write_geojson(OUT / f"hydrobasins_lev{level}_th.geojson", feats)
    return len(feats)


def main(level: str = "08"):
    RAW.mkdir(parents=True, exist_ok=True)
    onwr_zip = sorted(glob.glob(str(RAW / "Shp_Basin_ONWR*.zip")))
    hyb_zip = RAW / "hybas_lake_as_lev01-12_v1c.zip"
    n_onwr = onwr(pathlib.Path(onwr_zip[-1])) if onwr_zip else 0
    n_hyb = hydrobasins(hyb_zip, level) if hyb_zip.exists() else 0
    sums = []
    for f in sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in ("SHA256SUMS", "README.md")):
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        sums.append(f"{h.hexdigest()}  {f.relative_to(OUT)}")
    (OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    (OUT / "README.md").write_text(f"""# Basin maps (prepared {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by scripts/prepare_basins.py)

Not in git. Sources, tests and verdicts: docs/SOURCES.md §2i, research/2026-10-02_onwr_basins.md,
research/2026-10-02_catchment_rain.md.

| File | What | Source / licence |
|---|---|---|
| raw/Shp_Basin_ONWR-*.zip | ONWR legal 22 main basins, UTM 47N, CP874 | DWR page (division.dwr.go.th/rdhd, "Shapefiles ขอบเขตลุ่มน้ำหลัก"), สทนช. 2021; no licence stated — do not redistribute |
| raw/hybas_lake_as_lev01-12_v1c.zip | HydroBASINS v1c Asia with lakes, levels 1–12 | hydrosheds.org; free incl. commercial use with attribution (Lehner & Grill 2013) |
| onwr_basins_22.geojson | {n_onwr} basins (island parts merged), lon/lat, UTF-8; code, name_th, name_en, area_km2 | derived from the ONWR file |
| hydrobasins_lev{level}_th.geojson | {n_hyb} level-{level} sub-basins touching Thailand + all upstream (Mekong, Salween) + their path to the sea | derived from HydroBASINS |
""")
    print(f"onwr_basins_22.geojson: {n_onwr} basins; hydrobasins_lev{level}_th.geojson: {n_hyb} sub-basins; README.md, SHA256SUMS")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "08")
