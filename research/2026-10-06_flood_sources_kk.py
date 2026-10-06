"""E-FLOOD, the second opinion (owner 2026-10-06: "satellite images might be unreliable, please validate before use … compare
with google or any global flood info or portal"): over the lowland below Kaeng Krachan (lon 99.45–100.10, lat 12.75–13.30),
GISTDA's 30-day flooded area (H3 cells; the Thai space agency, several satellites) against Copernicus GFM's Sentinel-1
floods of the same period (union of the passes 2026-09-06 … today), on land GFM could see; Google Flood Hub has no gauge in
this box (gfh_gauge, checked 2026-10-06), so it offers no inundation map here. The GISTDA key is read from the environment
and sent only in its header; responses echo it in `links` (KI-262), which are dropped before anything is kept.
Run (host): GISTDA_API_KEY=… PYTHONPATH=$PYLIB python3 research/2026-10-06_flood_sources_kk.py"""
import json, os, time, urllib.parse, urllib.request
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from rasterio.enums import Resampling

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"
W, S_, E, N = 99.45, 12.75, 100.10, 13.30
RES = 0.0002
NX, NY = int(round((E - W) / RES)), int(round((N - S_) / RES))
T = from_origin(W, N, RES, RES)
KM2 = (RES * 111.32) ** 2 * np.cos(np.radians(13.0))


def get(url, headers=None):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})}), timeout=120) as r:
                return json.loads(r.read())
        except Exception:
            if k == 3:
                raise
            time.sleep(5 * (k + 1))


key = os.environ["GISTDA_API_KEY"]
cells, off = [], 0
while True:
    d = get("https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/30days?" +
            urllib.parse.urlencode({"bbox": f"{W},{S_},{E},{N}", "limit": 1000, "offset": off}), {"API-Key": key})
    d.pop("links", None)
    cells += d.get("features") or []
    off += 1000
    if off >= d.get("numberMatched", 0) or not d.get("features"):
        break
gis = rasterize([(f["geometry"], 1) for f in cells if f.get("geometry")], out_shape=(NY, NX), transform=T, fill=0, dtype=np.uint8).astype(bool) if cells else np.zeros((NY, NX), bool)
dates = sorted({str((f.get("properties") or {}).get("_createdAt", ""))[:10] for f in cells})
print(f"GISTDA 30-day cells in the box: {len(cells)} · {gis.sum() * KM2:.1f} km² · built {dates[-3:] if dates else None}", flush=True)

url = f"https://stac.eodc.eu/api/v1/collections/GFM/items?bbox={W},{S_},{E},{N}&datetime=2026-09-06T00:00:00Z/2026-10-07T00:00:00Z&limit=100"
items = get(url).get("features", [])
gf = np.zeros((NY, NX), bool); gv = np.zeros((NY, NX), bool)
for it in items:
    a = it["assets"]
    arrs = {}
    for name in ("ensemble_flood_extent", "exclusion_mask", "reference_water_mask"):
        if name not in a:
            arrs[name] = None; continue
        with rasterio.open(a[name]["href"]) as r:
            b = transform_bounds("EPSG:4326", r.crs, W, S_, E, N)
            win = rasterio.windows.from_bounds(*b, r.transform).round_offsets().round_lengths().intersection(rasterio.windows.Window(0, 0, r.width, r.height))
            dst = np.full((NY, NX), 255, np.uint8)
            reproject(r.read(1, window=win), dst, src_transform=r.window_transform(win), src_crs=r.crs, src_nodata=255, dst_transform=T,
                      dst_crs="EPSG:4326", dst_nodata=255, resampling=Resampling.nearest)
            arrs[name] = dst
    fl = arrs["ensemble_flood_extent"]
    if fl is None or (fl != 255).mean() < 0.05:
        continue
    ex = arrs["exclusion_mask"] if arrs["exclusion_mask"] is not None else np.zeros_like(fl)
    rw = arrs["reference_water_mask"] if arrs["reference_water_mask"] is not None else np.zeros_like(fl)
    v = (fl != 255) & (ex != 1)
    gv |= v
    gf |= v & (fl == 1) & (rw != 1)
both_see = gv
out = {"gistda_km2": round(float(gis.sum() * KM2), 1), "gfm_km2": round(float(gf.sum() * KM2), 1),
       "gistda_where_gfm_could_see_km2": round(float((gis & both_see).sum() * KM2), 1),
       "share_of_gistda_flood_that_gfm_also_maps": round(float((gis & gf).sum() / max((gis & both_see).sum(), 1)), 3),
       "share_of_gfm_flood_that_gistda_also_maps": round(float((gis & gf).sum() / max(gf.sum(), 1)), 3),
       "google_flood_hub": "no gauge in the box (gfh_gauge 2026-10-06) — no inundation map here"}
print("SUMMARY_JSON", json.dumps(out))
