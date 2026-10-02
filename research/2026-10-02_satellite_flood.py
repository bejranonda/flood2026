#!/usr/bin/env python3
"""Satellite flood maps for the lower Chao Phraya: Copernicus GFM (Sentinel-1, keyless STAC) vs GISTDA (key), and both vs
our gauges. Research only (owner, 2026-10-02: "Research only for now"); report: 2026-10-02_satellite_flood.md.

Runs in a throwaway python:3.12 container on the compose network (rasterio needs system libraries the app image lacks):

    docker run --rm --network floodwatch_default -v "$PWD/research:/r" -v <pylib>:/pylib \
      -e PYTHONPATH=/pylib -e DATABASE_URL=... -e GISTDA_API_KEY=... python:3.12 python /r/2026-10-02_satellite_flood.py

(pylib = `pip install --target <pylib> rasterio h3 pyproj numpy psycopg[binary]`). Prints one JSON summary; never prints
the GISTDA key (GISTDA echoes it inside `links`, KI-262, so those are dropped on arrival).
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request

import h3
import numpy as np
import psycopg
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds

UA = "BKK-FloodWatch/0.18 (+https://flood.autobahn.bot; research)"
W, S_, E, N = 99.9, 13.4, 100.95, 15.9          # focus region: Bangkok region + lower Chao Phraya to Nakhon Sawan
RES = 0.0004                                      # ~44 m analysis grid (GFM is 20 m)
START = dt.datetime(2026, 9, 2, tzinfo=dt.timezone.utc)
END = dt.datetime(2026, 10, 3, tzinfo=dt.timezone.utc)
GAUGE_R_KM = 1.0                                  # flood looked for within this radius of a gauge
PLACES = {  # named circles (lat, lon, radius km) to measure where the radar is blind
    "Bangkok core": (13.75, 100.53, 10), "Nonthaburi city": (13.86, 100.51, 4), "Pathum Thani town": (14.02, 100.53, 4),
    "Sam Khok rice (Pathum Thani)": (14.07, 100.47, 4), "Ayutthaya island": (14.355, 100.565, 2.5),
    "Bang Ban rice (Ayutthaya)": (14.40, 100.47, 5), "Pak Kret / Ko Kret": (13.91, 100.50, 3),
}


def get(url: str, headers: dict | None = None, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def stac_items() -> list[dict]:
    url = ("https://stac.eodc.eu/api/v1/collections/GFM/items?" + urllib.parse.urlencode(
        {"bbox": f"{W},{S_},{E},{N}", "datetime": f"{START:%Y-%m-%dT%H:%M:%SZ}/{END:%Y-%m-%dT%H:%M:%SZ}", "limit": 100}))
    out = []
    while url:
        d = get(url)
        out += d["features"]
        url = next((l["href"] for l in d.get("links", []) if l["rel"] == "next"), None)
    return out


def gistda_cells(key: str, period: str = "30days") -> list[dict]:
    base = f"https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/{period}"
    out, off = [], 0
    while True:
        d = get(f"{base}?{urllib.parse.urlencode({'bbox': f'{W},{S_},{E},{N}', 'limit': 1000, 'offset': off})}", {"API-Key": key})
        d.pop("links", None)  # KI-262: GISTDA echoes the caller's key in these URLs
        out += [f["properties"] for f in d["features"]]
        off += 1000
        if off >= d.get("numberMatched", 0) or not d["features"]:
            return out


def main() -> None:
    nx, ny = round((E - W) / RES), round((N - S_) / RES)
    dst_tf = from_origin(W, N, RES, RES)
    lon_c = W + (np.arange(nx) + 0.5) * RES
    lat_c = N - (np.arange(ny) + 0.5) * RES
    n_obs = np.zeros((ny, nx), np.uint16)
    n_flood = np.zeros((ny, nx), np.uint16)
    n_excl = np.zeros((ny, nx), np.uint16)
    refw = np.zeros((ny, nx), np.uint8)       # 1/2 = permanent/seasonal reference water

    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        gauges = con.execute("""SELECT code, lat, lon, bank_msl, agency FROM station
                                WHERE lat BETWEEN %s AND %s AND lon BETWEEN %s AND %s AND bank_msl IS NOT NULL
                                  AND code NOT LIKE 'BKK%%'""", (S_, N, W, E)).fetchall()
    gauge_px = {}
    for code, la, lo, bank, ag in gauges:
        iy, ix = int((N - la) / RES), int((lo - W) / RES)
        r = int(GAUGE_R_KM / 111 / RES)
        yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
        disk = (yy ** 2 + xx ** 2) <= r * r
        gauge_px[code] = (iy, ix, r, disk, bank)

    items = stac_items()
    passes, per_gauge = [], []
    for it in sorted(items, key=lambda f: f["properties"]["datetime"]):
        p = it["properties"]
        t = dt.datetime.fromisoformat(p["datetime"].replace("Z", "+00:00"))
        lat_h = (dt.datetime.fromisoformat(p["processing:datetime"].replace("Z", "+00:00")) - t).total_seconds() / 3600
        arrs = {}
        for a in ("ensemble_flood_extent", "exclusion_mask", "reference_water_mask"):
            if a not in it["assets"]:  # some passes ship without an exclusion mask: treat as "nothing excluded"
                arrs[a] = np.full((ny, nx), 255, np.uint8)
                continue
            with rasterio.open(it["assets"][a]["href"]) as r:
                b = transform_bounds("EPSG:4326", r.crs, W, S_, E, N)
                win = rasterio.windows.from_bounds(*b, r.transform).round_offsets().round_lengths()
                win = win.intersection(rasterio.windows.Window(0, 0, r.width, r.height))
                src = r.read(1, window=win)
                dst = np.full((ny, nx), 255, np.uint8)
                reproject(src, dst, src_transform=r.window_transform(win), src_crs=r.crs, src_nodata=255,
                          dst_transform=dst_tf, dst_crs="EPSG:4326", dst_nodata=255, resampling=Resampling.nearest)
                arrs[a] = dst
        fl, ex, rw = arrs["ensemble_flood_extent"], arrs["exclusion_mask"], arrs["reference_water_mask"]
        seen = fl != 255
        if not seen.any():
            continue
        n_obs += seen
        n_flood += fl == 1
        n_excl += ex == 1
        refw = np.maximum(refw, np.where(rw == 255, 0, rw))
        passes.append({"time": p["datetime"], "tile": p.get("Equi7Tile"), "latency_h": round(lat_h, 1),
                       "flood_km2": round(float((fl == 1).sum()) * (RES * 111) ** 2 * np.cos(np.radians(14.5)), 1)})
        for code, (iy, ix, r, disk, bank) in gauge_px.items():
            sl = (slice(max(iy - r, 0), iy + r + 1), slice(max(ix - r, 0), ix + r + 1))
            sub_fl, sub_rw, sub_ex = fl[sl], rw[sl], ex[sl]
            d = disk[: sub_fl.shape[0], : sub_fl.shape[1]]
            land = d & (sub_fl != 255) & ~np.isin(sub_rw, (1, 2))
            if land.sum() < 50:
                continue
            per_gauge.append({"code": code, "time": p["datetime"], "land_px": int(land.sum()),
                              "flood_px": int((land & (sub_fl == 1)).sum()), "excl_px": int((d & (sub_ex == 1)).sum())})
        print(p["datetime"], p.get("Equi7Tile"), f"{lat_h:.1f} h", file=sys.stderr, flush=True)

    # gauge level at pass time (nearest observation within 3 h) -> margin to bank
    with psycopg.connect(os.environ["DATABASE_URL"]) as con:
        for g in per_gauge:
            row = con.execute("""SELECT level_msl FROM observation WHERE code=%s AND quality_flag='ok' AND level_msl IS NOT NULL
                                 AND obs_time BETWEEN %s::timestamptz - interval '3 hours' AND %s::timestamptz + interval '3 hours'
                                 ORDER BY abs(extract(epoch FROM obs_time - %s::timestamptz)) LIMIT 1""",
                              (g["code"], g["time"], g["time"], g["time"])).fetchone()
            g["margin_m"] = None if not row else round(row[0] - gauge_px[g["code"]][4], 2)

    ever_flood = (n_flood > 0) & (refw == 0)
    observed = (n_obs > 0)
    # blindness by place: share of pixels the exclusion mask hid in at least half of the passes that saw them
    places = {}
    for name, (la, lo, rk) in PLACES.items():
        yy, xx = np.ogrid[:ny, :nx]
        cy, cx, rr = (N - la) / RES, (lo - W) / RES, rk / 111 / RES
        m = ((yy - cy) ** 2 + (xx - cx) ** 2 <= rr * rr) & observed & (refw == 0)
        blind = m & (n_excl * 2 >= n_obs)
        places[name] = {"land_px": int(m.sum()), "blind_share": round(float(blind.sum()) / max(int(m.sum()), 1), 3),
                        "ever_flooded_share": round(float((m & ever_flood).sum()) / max(int(m.sum()), 1), 3),
                        "passes_median": int(np.median(n_obs[m])) if m.any() else 0}

    # GISTDA 30 days vs GFM 30 days, on GISTDA's own H3 cells (resolution 9, ~0.1 km2)
    gis = gistda_cells(os.environ["GISTDA_API_KEY"])
    gis_cells = {c["h3_address"]: c for c in gis}
    sats = collections.Counter(fn.strip()[:3] for c in gis for fn in (c.get("file_name") or "").split(","))
    fy, fx = np.nonzero(ever_flood)
    gfm_cells = collections.Counter(h3.latlng_to_cell(float(lat_c[y]), float(lon_c[x]), 9) for y, x in zip(fy, fx))
    oy, ox = np.nonzero(observed & (n_excl * 2 < n_obs) & (refw == 0))
    seen_cells = {h3.latlng_to_cell(float(lat_c[y]), float(lon_c[x]), 9) for y, x in zip(oy[::4], ox[::4])}
    gis_seen = [c for c in gis_cells if c in seen_cells]
    both = [c for c in gis_seen if gfm_cells.get(c, 0) >= 3]       # >= 3 GFM pixels (~0.006 km2) in the cell
    gfm_big = {c for c, n in gfm_cells.items() if n >= 3}

    # gauges: over bank (margin > 0) vs GFM flood within 1 km
    tab = collections.Counter()
    for g in per_gauge:
        if g["margin_m"] is None:
            continue
        over = "over_bank" if g["margin_m"] > 0 else ("within_0.5m" if g["margin_m"] > -0.5 else "below_0.5m")
        sat = "sat_flood" if g["flood_px"] / g["land_px"] >= 0.02 else "sat_dry"
        tab[f"{over}|{sat}"] += 1

    lat_hours = [p["latency_h"] for p in passes]
    days = sorted({p["time"][:10] for p in passes})
    out = {
        "region": [W, S_, E, N], "period": [f"{START:%Y-%m-%d}", f"{END:%Y-%m-%d}"],
        "gfm": {"items": len(passes), "pass_days": len(days), "days": days,
                "latency_h_median": statistics.median(lat_hours) if lat_hours else None,
                "latency_h_max": max(lat_hours) if lat_hours else None,
                "ever_flooded_km2": round(float(ever_flood.sum()) * (RES * 111) ** 2 * np.cos(np.radians(14.5)), 1)},
        "places": places,
        "gistda": {"cells_30d": len(gis_cells), "area_km2": round(sum(c.get("f_area") or 0 for c in gis) / 1e6, 1),
                   "satellite_files": dict(sats.most_common())},
        "agreement": {"gistda_cells_gfm_could_see": len(gis_seen), "of_those_gfm_flooded": len(both),
                      "share": round(len(both) / max(len(gis_seen), 1), 3),
                      "gfm_flood_cells": len(gfm_big), "gfm_cells_in_gistda": len(gfm_big & set(gis_cells)),
                      "gfm_share_in_gistda": round(len(gfm_big & set(gis_cells)) / max(len(gfm_big), 1), 3)},
        "gauges": {"n_gauges": len(gauge_px), "pairs": sum(tab.values()), "table": dict(sorted(tab.items()))},
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
