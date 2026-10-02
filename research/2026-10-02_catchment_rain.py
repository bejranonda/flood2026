#!/usr/bin/env python3
"""Rain over each gauge's true upstream catchment (HydroBASINS) as the forecast's rain input — does it beat the
gauge's own 0.5° cell? (OWNER_ACTIONS HYDROBASINS; owner 2026-10-02 downloaded `hybas_lake_as_lev01-12_v1c.zip`.)

HydroBASINS v1c (Lehner & Grill 2013; free for scientific, educational and commercial use with attribution): nested
sub-basins with `NEXT_DOWN` links. Level 8 here. A gauge's catchment = the sub-basin it lies in plus every sub-basin
whose chain of `NEXT_DOWN` reaches it.

Variants on the production backtest (`forecast.evaluate`, last 45 days; upstream gauges as learned in production):
  A  production rain: the gauge's own 0.5° Open-Meteo cell
  H  mean over our cells whose centre lies in the gauge's upstream catchment (always including its own cell)
  P  placebo: H's recipe with the catchment of another sampled gauge in a different basin (same kind of input,
     wrong place)

    docker compose run --rm --no-deps -v "$PWD/research:/research" -v "$PWD/data/basins:/basins:ro" worker \
        python /research/2026-10-02_catchment_rain.py [n]
Caveat (tech doc §2.3): in this lake version a sub-basin cut by a lake is split into left/right parts that share UP_AREA;
the right part drains into the left, so a gauge in a right part misses the left part's area (360 of 384 sub-basins
whose UP_AREA cannot be rebuilt from NEXT_DOWN are such sides or lakes).
"""
import datetime as dt
import importlib.util
import random
import struct
import sys
import zipfile
from collections import defaultdict

import numpy as np

from floodwatch import db, forecast as F, rain_cells

spec = importlib.util.spec_from_file_location("b", "/research/2026-10-02_basins.py")
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
ZIP = "/basins/raw/hybas_lake_as_lev01-12_v1c.zip"  # data/basins/raw on the host (scripts/prepare_basins.py)
LEVEL = "08"
BOX = (92.0, 5.0, 110.0, 24.0)  # lon/lat box for geometry (gauges and cells); the NEXT_DOWN graph uses every record
H = (12, 24, 48)


def read_dbf(d: bytes) -> list[dict]:
    n, hl, rl = struct.unpack("<IHH", d[4:12])
    fields, i = [], 32
    while d[i] != 0x0D:
        fields.append((d[i:i + 11].split(b"\0")[0].decode(), d[i + 16]))
        i += 32
    out, off = [], hl
    for _ in range(n):
        rec, p, row = d[off + 1:off + rl], 0, {}
        for name, ln in fields:
            row[name] = rec[p:p + ln].decode("latin-1").strip()
            p += ln
        out.append(row)
        off += rl
    return out


def read_shp(d: bytes, box) -> list:
    """Per record: list of rings (lon/lat arrays) when its bbox meets `box`, else None."""
    out, off = [], 100
    while off < len(d):
        _, clen = struct.unpack(">ii", d[off:off + 8])
        rec = d[off + 8:off + 8 + clen * 2]
        off += 8 + clen * 2
        if struct.unpack("<i", rec[:4])[0] != 5:
            out.append(None)
            continue
        x0, y0, x1, y1 = struct.unpack("<4d", rec[4:36])
        if x1 < box[0] or x0 > box[2] or y1 < box[1] or y0 > box[3]:
            out.append(None)
            continue
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = list(struct.unpack(f"<{nparts}i", rec[44:44 + 4 * nparts])) + [npts]
        pts = np.frombuffer(rec[44 + 4 * nparts:44 + 4 * nparts + 16 * npts], dtype="<f8").reshape(-1, 2)
        out.append([pts[a:b] for a, b in zip(parts, parts[1:])])
    return out


def _inside_ring(x: float, y: float, r: np.ndarray) -> bool:
    x1, y1 = r[:, 0], r[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    c = (y1 > y) != (y2 > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = (x2[c] - x1[c]) * (y - y1[c]) / (y2[c] - y1[c]) + x1[c]
    return np.count_nonzero(x < xi) % 2 == 1


def locate(lon: float, lat: float, geoms, ids) -> int | None:
    """HYBAS_ID of the sub-basin containing the point (even-odd over all rings: holes handled)."""
    for g, hid in zip(geoms, ids):
        if g is None:
            continue
        if sum(_inside_ring(lon, lat, r) for r in g if r[:, 0].min() <= lon <= r[:, 0].max()
               and r[:, 1].min() <= lat <= r[:, 1].max()) % 2 == 1:
            return hid
    return None


def main(n: int):
    z = zipfile.ZipFile(ZIP)
    rows = read_dbf(z.read(f"hybas_lake_as_lev{LEVEL}_v1c.dbf"))
    geoms = read_shp(z.read(f"hybas_lake_as_lev{LEVEL}_v1c.shp"), BOX)
    ids = [int(r["HYBAS_ID"]) for r in rows]
    area = {int(r["HYBAS_ID"]): float(r["SUB_AREA"]) for r in rows}
    ups = defaultdict(list)
    for r in rows:
        if int(r["NEXT_DOWN"]):
            ups[int(r["NEXT_DOWN"])].append(int(r["HYBAS_ID"]))

    def catchment(hid: int) -> set[int]:
        seen, todo = {hid}, [hid]
        while todo:
            for u in ups.get(todo.pop(), ()):
                if u not in seen:
                    seen.add(u)
                    todo.append(u)
        return seen

    with db.connect() as c:
        cells = {r["point"] for r in c.execute("SELECT DISTINCT point FROM rain_hindcast WHERE point LIKE 'g\\_%'").fetchall()}
        st = c.execute("""SELECT s.code, s.lat, s.lon, s.basin22 FROM station s WHERE s.lat IS NOT NULL AND NOT s.in_focus
            AND s.code !~ '^TEST' AND s.agency IS DISTINCT FROM 'BMA' AND s.basin22 IS NOT NULL
            AND (SELECT min(obs_time) FROM observation o WHERE o.code=s.code) < now()-interval '300 days'
            AND EXISTS (SELECT 1 FROM observation o WHERE o.code=s.code AND o.obs_time > now()-interval '12 hours')""").fetchall()
        learned = db.get_state(c, "upstream_learned") or {}
    cell_basin = {}
    for p in cells:
        _, la, lo = p.split("_")
        cell_basin[p] = locate(float(lo), float(la), geoms, ids)
    print(f"HydroBASINS lev{LEVEL}: {len(rows):,} sub-basins (Asia), median {np.median(list(area.values())):.0f} km²;"
          f" {len(cells)} rain cells, {sum(v is not None for v in cell_basin.values())} located", flush=True)
    random.seed(21)
    sample = random.sample(sorted(s["code"] for s in st), min(n, len(st)))
    meta = {s["code"]: s for s in st}
    catch = {}
    for code in sample:
        m = meta[code]
        hid = locate(m["lon"], m["lat"], geoms, ids)
        own = rain_cells.cell_of(m["lat"], m["lon"])[0]
        cs = catchment(hid) if hid else set()
        pts = sorted({own} | {p for p, b in cell_basin.items() if b in cs})
        catch[code] = (pts, sum(area[h] for h in cs))
    res, ser, rcache = [], {}, {}
    with db.connect() as c:
        def get(code):
            if code not in ser:
                ser[code] = B.series(c, code)
            return ser[code]
        for code in sample:
            m, (pts, km2) = meta[code], catch[code]
            t, y = get(code)
            if len(y) < 24 * 200:
                continue
            own = rain_cells.cell_of(m["lat"], m["lon"])[0]
            others = [k for k in sample if meta[k]["basin22"] != m["basin22"] and len(catch[k][0]) > 1]
            placebo = catch[random.Random(code).choice(others)][0] if others else [own]
            up = [get(u[0]) for u in learned.get(code, [])]
            up = [([dt.datetime.fromtimestamp(h * 3600, dt.timezone.utc) for h in tt], list(yy)) for tt, yy in up if len(tt)]
            out = {"code": code, "basin": m["basin22"], "cells": len(pts), "km2": km2}
            for name, p in (("A", [own]), ("H", pts), ("P", placebo)):
                rain = B.rain_of(c, p, rcache)
                out[name] = None if rain is None else B.skills(F.evaluate(t, y, F.align_exo(t, {"up": up, "q": None, "rain": rain})))
            res.append(out)
            print(code, m["basin22"], f"{km2:,.0f} km² {len(pts)} cells",
                  {k: (out[k] or {}).get(24) and round(out[k][24][0], 3) for k in "AHP"}, flush=True)
    print(f"\ncatchment rain {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC: {len(res)} gauges;"
          f" catchment cells median {np.median([r['cells'] for r in res]):.0f}, with > 1 cell: {sum(r['cells'] > 1 for r in res)}")
    multi = [r for r in res if r["cells"] > 1]
    for h in H:
        print(f"  {h} h (gauges whose catchment spans > 1 cell: {len(multi)}):")
        for k, label in (("A", "own cell (production)"), ("H", "upstream catchment"), ("P", "placebo catchment")):
            v = [r[k][h][0] for r in multi if r.get(k) and r[k][h]]
            print(f"    {label:<24} mean skill {np.mean(v):5.3f}  over gate {sum(x > F.SKILL_GATE for x in v):>3}/{len(v)}")
        for k in ("H", "P"):
            d = [r[k][h][1] / r["A"][h][1] - 1 for r in multi if r.get(k) and r.get("A") and r[k][h] and r["A"][h]
                 and r[k][h][1] and r["A"][h][1]]
            if d:
                print(f"    star RMSE {k} vs A: median {np.median(d) * 100:+.1f} %, better at {sum(x < 0 for x in d)}/{len(d)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
