# Satellite flood maps: Copernicus GFM vs GISTDA vs our gauges (research only)

**Date:** 2026-10-02 · **Owner:** "Research and consider how can we apply this info to improve our app?" (GloFAS/GFM); asked what satellite maps should do first → **"Research only for now"**. Decision: D-069.
**Script:** [2026-10-02_satellite_flood.py](2026-10-02_satellite_flood.py) (throwaway `python:3.12` container with rasterio + h3; run 20:19–20:33 UTC). Region: lon 99.9–100.95, lat 13.4–15.9 (Bangkok region + lower Chao Phraya to Nakhon Sawan); period 2026-09-02 → 2026-10-02 (GISTDA keeps 30 days).

## 1. Access (verified 2026-10-02)
| | GFM (Copernicus, Sentinel-1) | GISTDA (Thai space agency) |
|---|---|---|
| Access | **Keyless** STAC: `stac.eodc.eu/api/v1/collections/GFM/items?bbox=…&datetime=…` → per pass and tile, Cloud-Optimized GeoTIFFs at `data.eodc.eu` (HTTP 200, no auth). Account API `api.gfm.eodc.eu/v2` (Swagger v24.01): `POST /auth/login {email,password}` → token valid 5 h → AOIs, product lists, alerts (401 without) | Key in `API-Key` header (KI-510); `/features/flood/{1day,3days,7days,30days}`, `bbox`, `limit`/`offset` |
| Product | 20 m rasters: ensemble flood extent (3 algorithms: DLR, TU Wien, LIST), likelihood, **exclusion mask**, reference water (permanent/seasonal), advisory flags. Values 0/1, 255 = no data | H3 cells (resolution 9, ~0.12 km²) with flooded area, tambon/amphoe/province, population, buildings, roads, rice area, and the satellite files used |
| Licence | CC BY 4.0 (product user manual v20251201) | GISTDA terms (key holder) |
| Latency | median **7.3 h** after the pass (max 11.3 h) | daily composites |
| ⚠️ | A STAC item's bbox is wider than the imaged strip: 178 items listed for the region, only **42** had data over it (the rest are all 255 there) | **Echoes the caller's API key** in every response's `links` URLs (KI-262) |

## 2. How often the radar looks, and where it is blind
Sentinel-1 (S1C, S1D) imaged the region on **6 days in 30** (09-03, 09-07, 09-15, 09-19, 09-27, 10-01): gaps of 4–8 days. A flood that rises and falls within a week can be missed entirely.

GFM's exclusion mask marks pixels where radar cannot see flooding (urban areas, dense vegetation, shadows; manual §4.2). Share of land hidden in at least half of the passes, and share ever mapped flooded:

| Place (circle) | Hidden | Ever flooded (30 d) |
|---|---|---|
| Bangkok core (10 km around 13.75, 100.53) | **71 %** | **0.0 %** |
| Pak Kret / Ko Kret (3 km) | 65 % | 0.0 % |
| Nonthaburi city (4 km) | 61 % | 0.0 % |
| Ayutthaya island (2.5 km) | 57 % | 1.2 % |
| Pathum Thani town (4 km) | 55 % | 4.2 % |
| Sam Khok rice fields (4 km) | 29 % | 9.4 % |
| Bang Ban rice fields (5 km) | 23 % | **32.4 %** |

Over the whole region GFM mapped **3,153 km²** flooded at least once (outside reference water).

## 3. GFM and GISTDA agree where both can see
GISTDA's 30-day layer: 56,899 H3 cells, 1,440 km² flooded area; its file list names Sentinel-1C/1D, Radarsat-2 (`rd2`) and COSMO-SkyMed (`cg2`, `cm4`). ⚠️ Every cell carries the same composite file list, so the satellite behind a single cell cannot be told.
- Of GISTDA's flooded cells that GFM could see, **89 %** also had GFM flood (≥ 3 pixels).
- Of GFM's flooded cells, **66 %** are in GISTDA's layer (GFM maps more: 20 m pixels, every pass).
→ Two independent processing chains largely agree in the open country; GISTDA adds other satellites (more passes) and Thai admin areas and exposure, GFM adds per-pass timing, likelihood and an explicit "cannot see" mask.

## 4. Satellite vs our gauges (1,512 gauge-pass pairs, 280 non-BMA gauges with a bank)
Flood within 1 km of the gauge (≥ 2 % of visible land, outside reference water) vs the gauge's level at the pass (±3 h):

| Gauge at pass time | Satellite saw flood nearby | Dry |
|---|---|---|
| Over the bank | 27 (**38 %**) | 44 |
| 0–0.5 m below the bank | 12 (9.5 %) | 114 |
| More than 0.5 m below | 57 (4.3 %) | 1,258 |

Over-bank gauges have flood nearby nine times more often than low gauges, but the satellite misses most over-bank moments (short peaks between passes, blind pixels, overflow onto ground that is already reference water).

## 5. What this means for the app
- **Bangkok, Nonthaburi, Pak Kret:** satellite maps are mostly blind and showed **no** flood in the core during an active flood, while Traffy had **1,040** flood reports within the same 10 km on 7 days of the period (our `crowd_report`, queried 2026-10-02). A line "ดาวเทียมไม่เห็นน้ำท่วม" there would mislead (D-019 spirit). Not useful for the app's main audience.
- **Rice belt and the river provinces (Ayutthaya, Pathum Thani north, Ang Thong, Sing Buri, Chai Nat):** an honest, observed fact a gauge cannot give: "ดาวเทียมเห็นน้ำท่วมห่าง ~N ม. เมื่อ X วันก่อน (GISTDA/GFM)". Only "seen" may be said, never "not flooded", and only where the mask says the radar can see.
- **Order:** GISTDA first (key works, Thai, more satellites, admin areas); GFM second (keyless, per pass, the exclusion mask tells us where to stay silent). The GFM account adds nothing the keyless catalogue lacks for this use (the API lists the same products per AOI).
- **Validation:** too sparse (6 days in 30) and too blind in Bangkok to score our 48 h forecasts; usable as a seasonal check of over-bank calls in the river provinces.
- Owner chose research only; a UI line would need its own decision (D-069 lists the rules).
