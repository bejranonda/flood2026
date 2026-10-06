"""E-FLOOD-DEM — can a free DEM draw the flood of a release below Kaeng Krachan? (owner 2026-10-06: "Flood area generated
by DEM is firstly for experiment … I will ask for higher resolution DEM later"). Experiment only: nothing here reaches the
page (D-019 stands for the app until a DEM passes and the owner decides).

Method — height above nearest drainage (HAND): the DEM (default Copernicus GLO-30, 1″ ≈ 30 m, EGM2008; any DEM path can be
given, so a higher-resolution DEM drops in later) is conditioned (pits, depressions, flats filled; the mapped Phetchaburi
channel burned 5 m so flow follows the real river), D8 flow directions, and HAND = a cell's height above the channel cell it
drains to. A cell is "under water at stage s" when HAND ≤ s (s = metres above the channel's water surface).
Truth — Copernicus GFM's Sentinel-1 flood of August–September 2018 (Kaeng Krachan's largest releases since; flooded in ≥ 2
passes; permanent/seasonal reference water and the "cannot see" exclusion removed; research/2026-10-06_flood_satellite_kk.py).
Score — for s = 0.5 … 8 m, within 15 km of the river (the release's reach; rain floods far away are not the target), on the
pixels GFM saw: hits, misses, false alarms → CSI = hits / (hits + misses + false alarms), hit rate, false-alarm ratio.
A DEM "passes" only if a single stage reaches CSI ≥ 0.5 there (a common bar for flood-extent skill) — and even then the
stage of a planned release would still have to come from the river model, outside the flows the gauges have seen.
Run (host): PYTHONPATH=$PYLIB python3 research/2026-10-06_flood_dem_kk.py OUT_DIR [DEM.tif …]"""
import glob, json, sys
import numpy as np
import rasterio

if not hasattr(np, "in1d"):  # pysheds still calls np.in1d, removed in NumPy 2 (np.isin is its replacement)
    np.in1d = lambda a, b, **k: np.isin(np.ravel(a), b, **k)
from rasterio.merge import merge
from rasterio.features import rasterize
from rasterio.warp import reproject
from rasterio.enums import Resampling
from scipy import ndimage

OUT = sys.argv[1]
DEMS = sys.argv[2:] or sorted(glob.glob(f"{OUT}/dem/Copernicus_DSM_COG_10_*_DEM.tif"))
g = np.load(f"{OUT}/gfm_2018_mask.npz")
W, S_, E, N = [float(x) for x in g["bounds"]]
RES = float(g["res"])
NY, NX = g["count"].shape
truth = g["count"] >= 2
seen = (g["seen"] >= 1) & ~g["refwater"]
dst_t = rasterio.transform.from_origin(W, N, RES, RES)

# the DEM on the GFM grid (bilinear), then conditioned with the river burned in
srcs = [rasterio.open(p) for p in DEMS]
mosaic, mt = merge(srcs)
dem = np.full((NY, NX), np.nan, np.float32)
reproject(mosaic[0], dem, src_transform=mt, src_crs=srcs[0].crs, dst_transform=dst_t, dst_crs="EPSG:4326",
          resampling=Resampling.bilinear, src_nodata=srcs[0].nodata, dst_nodata=np.nan)
river = json.load(open(f"{OUT}/kk_river_line.json"))  # [[[lat, lon], …], …] from the case state
lines = [{"type": "LineString", "coordinates": [[lon, lat] for lat, lon in part]} for part in river if len(part) > 1]
chan = rasterize([(l, 1) for l in lines], out_shape=(NY, NX), transform=dst_t, fill=0, all_touched=True, dtype=np.uint8).astype(bool)
sea = ~np.isfinite(dem) | (dem <= 0.0)
dem_f = np.where(np.isfinite(dem), dem, 0.0).astype(np.float64)
burn = dem_f - 5.0 * chan

from pysheds.grid import Grid
from pysheds.view import Raster, ViewFinder
vf = ViewFinder(affine=dst_t, shape=(NY, NX), crs="EPSG:4326", nodata=np.nan)
grid = Grid(viewfinder=vf)
r = Raster(burn, viewfinder=vf)
cond = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(r)))
fdir = grid.flowdir(cond)
vf_mask = ViewFinder(affine=dst_t, shape=(NY, NX), crs="EPSG:4326", nodata=False)  # a boolean mask cannot carry NaN
hand = np.asarray(grid.compute_hand(fdir, Raster(dem_f, viewfinder=vf), Raster(chan, viewfinder=vf_mask)), dtype=np.float64)

# within 15 km of the river, on land GFM saw
dist_px = ndimage.distance_transform_edt(~chan)
near = dist_px * RES * 111.32 <= 15.0
dom = near & seen & ~sea & np.isfinite(hand)
t = truth & dom
res = []
for s in [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8]:
    pred = (hand <= s) & dom
    hits, misses, fa = int((pred & t).sum()), int((~pred & t).sum()), int((pred & ~t).sum())
    res.append({"stage_m": s, "csi": round(hits / max(hits + misses + fa, 1), 3), "hit_rate": round(hits / max(hits + misses, 1), 3),
                "false_alarm_ratio": round(fa / max(hits + fa, 1), 3), "pred_km2": round(float(pred.sum()) * (RES * 111.32) ** 2 * np.cos(np.radians(13)), 1)})
    print(res[-1], flush=True)
best = max(res, key=lambda x: x["csi"])
km2 = (RES * 111.32) ** 2 * np.cos(np.radians(13))
out = {"dems": [p.split("/")[-1] for p in DEMS], "domain_km2": round(float(dom.sum()) * km2, 1),
       "gfm_2018_flood_km2_in_domain": round(float(t.sum()) * km2, 1), "best": best, "pass": best["csi"] >= 0.5, "scores": res}
np.savez_compressed(f"{OUT}/hand_kk.npz", hand=hand.astype(np.float32), dom=dom, truth=t)
print("SUMMARY_JSON", json.dumps(out))
