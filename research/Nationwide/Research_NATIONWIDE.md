> **Validity: 🟢 mostly reliable** (checked 2026-09-27, [VALIDATION_2026-09-27_nationwide.md](../VALIDATION_2026-09-27_nationwide.md)).
> Kept as written. Corrections: the HII gate feed is **stale** (12 of 2,315 rows fresh); the tide table has **28**
> stations (Gulf and Andaman), not 9; GloFAS points must be **snapped** to the channel; the HII dam feed has **no rule
> curves**; event figures (Hat Yai 2025, Mekong 2026) are unverified. Adopted parts live in `docs/` (APPROACH §19,
> SOURCES §2d, D-044). When this file and `docs/` disagree, `docs/` wins.

# NATIONWIDE.md — Scaling the Flood & Water Level Forecast to All of Thailand

> Research date: 27 Sep 2026. Extends `SOURCES.md` (data) and `METHODS.md` (Bangkok/central methods).
> Audience: developers and AI coding agents. Everything marked 🟡 must be re-verified from the production server before use.

**Verification legend:** ✅ confirmed from official docs · 🟡 documented by working open-source code or third-party docs, verify · 🔑 needs (free) registration · 🔴 no machine access / browser only · ⛔ do not use without permission

---

## 0. Executive summary

1. Outside Bangkok the problem changes: **fewer gauges, shorter records, missing flood thresholds, strong reservoir control, flash floods in mountains, slow floods in the flat Northeast, Mekong backwater, and tidal/lagoon effects in the South.** One model cannot cover all of this.
2. Use a **flood-type taxonomy (F1–F8)** and route each station/location to the right model family (§2). Most of the code is shared; the physics module and features differ.
3. Use **one global (national) ML model per flood type**, trained across all stations with catchment attributes, so data-poor stations borrow strength from data-rich ones. This is the approach behind Google's global flood model, which forecasts extreme floods in ungauged basins up to 5 days ahead with reliability similar to GloFAS nowcasts.
4. Where a station has **no flood level**, derive thresholds from station metadata, statistics (return periods), GloFAS/Google thresholds, or observed impacts (§4.7) — and communicate "unusually high" rather than "above bank".
5. Where there is **no station at all**, use **virtual gauges** (GloFAS discharge, Google Flood Hub hybas gauges), satellite flood extent (GISTDA, Copernicus GFM) and satellite altimetry (SWOT, DAHITI).
6. Thai government data are richer than they look: HII's ThaiWater API also exposes **dams, water gates, discharge, canals, flooded roads, 7-day rain forecast, storms**; HII's FEWS portal exposes **flash-flood potential per tambon and station thresholds**; RID, DWR and EGAT have their own telemetry endpoints (§5).
7. Roll out region by region, in time for each region's flood season (§8): the South floods mainly **Oct–Jan** (northeast monsoon), the rest mainly **Jul–Oct**.

---

## 1. Hydrological regions and what drives floods

| Region | Main rivers / systems | Dominant flood types | Key controls & features |
|---|---|---|---|
| **North** | Ping, Wang, Yom, Nan; Kok, Ing, Sai (Mekong tributaries, transboundary with Myanmar/Laos) | Flash floods, mudflows, fast river floods in valleys (Chiang Rai, Chiang Mai, Nan, Phrae) | Steep catchments, hours of lead time; Bhumibol (Ping) & Sirikit (Nan) regulate; **Yom is largely unregulated** |
| **Northeast** | Mun, Chi, Songkhram, Loei; Mekong mainstream | Slow, long-duration floods in flat basins; Mekong riverbank floods; backwater | Ubol Ratana, Lam Pao, Sirindhorn, Pak Mun; Mun/Songkhram outflow limited by **Mekong level** |
| **Central** | Chao Phraya, Pasak, Sakae Krang, Tha Chin, Noi, Lop Buri | Regulated river floods, floodplain/retention flooding, urban pluvial | Chao Phraya Dam, Pasak Jolasid, diversions; tide in lower reach (see METHODS.md) |
| **West** | Mae Klong, Khwae Noi, Khwae Yai, Phetchaburi | Mostly regulated; local flash floods | Srinagarind, Vajiralongkorn dams |
| **East** | Bang Pakong, Prachin Buri, Chanthaburi, Trat, short coastal rivers | River + coastal floods, tidal lower reaches | Tidal Bang Pakong; heavy SW-monsoon rain on Chanthaburi coast |
| **South** | Tapi, Pak Phanang, Pattani, Sai Buri, Kolok, U-Taphao→Songkhla Lake, Andaman rivers | Extreme rain events, flash floods from mountains, urban floods, lagoon/tidal backwater | NE monsoon (Oct–Jan) on Gulf side; SW monsoon on Andaman side; Bang Lang dam (Pattani) |

**Recent reference events (use for validation/backtesting):**
- **Hat Yai, Nov 2025**: 335 mm fell on 21 Nov alone and more than 630 mm over three days. Hat Yai is a basin collecting water from three mountain ranges with **one main drainage route, the U-Taphao canal, to Songkhla Lake**, and the canal has been narrowed by urban development. Satellite analysis estimated ~234 km² flooded in Songkhla province (19–25 Nov). → Needs flash-flood + urban + lagoon-boundary modelling.
- **Mekong, Aug–Sep 2026**: DDPM warned four Mekong provinces (Nong Khai, Bueng Kan, Nakhon Phanom, Mukdahan) of rises of about 2.0–4.8 m, with Nong Khai forecast to exceed its critical level on 2–4 Sep 2026. Earlier, the MRC reported Nong Khai at 12.69 m against a **flood threshold of 12.2 m**, driven by upstream rain and releases from Lao dams (Nam Ou, Nam Khan). → Needs Mekong routing with upstream (Chiang Saen/Luang Prabang/Vientiane) and dam operations.
- Also: Central 2011; Northeast 2017 (Sakon Nakhon), 2019 (Ubon, Mun), 2022 (Mun/Chi); North 2024 (Chiang Rai/Mae Sai, Chiang Mai) — verify dates/impacts from official reports before using as labels.

---

## 2. Flood-type taxonomy → model family

Assign every station, reach and grid cell one or more types. The model router uses these tags.

| Type | Description | Typical lead time | Primary model | Key inputs |
|---|---|---|---|---|
| **F1 Regulated large river** | Downstream of big dams/barrages | 1–7 d | Reservoir balance + release model + routing + ML residual | Dam storage, inflow, release plans, rule curves, upstream Q |
| **F2 Unregulated medium river** | e.g. Yom, many NE/South rivers | 0.5–5 d | Rain–runoff ML (global LSTM/LightGBM) + routing | Basin rain obs + forecast, soil moisture, upstream stations |
| **F3 Flash flood (small steep catchments)** | North & South mountains, Western range | 0–12 h | Flash-flood guidance / rainfall-threshold model + nowcast | Radar/satellite rain, NWP, soil moisture, catchment threshold runoff |
| **F4 Slow flat-basin flood** | Mun, Chi, lower Songkhram, Bang Pakong plains | days–weeks | Storage/routing with long recession + ML; backwater term | Upstream Q, Mekong/downstream level, basin storage |
| **F5 Mekong mainstream** | Chiang Saen → Khong Chiam | 1–5 d | Upstream-lag routing + ML; MRC forecasts as feature | Upstream Mekong stations, Lao/China dam releases, basin rain |
| **F6 Coastal / tidal / lagoon** | River mouths, Songkhla Lake, Bang Pakong, Tha Chin, Mae Klong, Pak Phanang | hours–days | Harmonic tide + residual ML; lake level as boundary | Tide predictions, storm surge, lake level, river Q |
| **F7 Urban pluvial** | Bangkok, Hat Yai, Chiang Mai, Khon Kaen, Nakhon Ratchasima… | 0–24 h | Storage balance + ML (as METHODS.md §3.6) | Rain intensity vs drainage capacity, outlet level, pumps |
| **F8 Reservoir spill / small-dam risk** | Medium & small reservoirs spilling into villages | 0–3 d | Reservoir water balance with spillway; overflow probability | Storage %, inflow forecast, spillway level |

---

## 3. Data-availability tiers (per location)

| Tier | What exists | Method |
|---|---|---|
| **A** | Long telemetry (≥ 5 yr), discharge or rating curve, official thresholds | Full METHODS.md pipeline (station-specific calibration + global model) |
| **B** | Telemetry with short history and/or no thresholds | Global model (transfer learning via catchment attributes) + derived thresholds (§4.7) + wide intervals |
| **C** | No gauge (ungauged) | Virtual gauges (GloFAS, Google hybas), satellite extent & altimetry, flash-flood potential per tambon; categorical outlook only |

Rule: **the app must always show which tier a forecast comes from** ("วัดจริง", "ประมาณจากแบบจำลอง", "ประมาณจากดาวเทียม").

---

## 4. Methods (what changes outside Bangkok)

### 4.1 One national model, many stations (global / regional learning)

- Train **one LightGBM (quantile) model per flood type** (F1–F8) across all stations of that type; later a global **LSTM** (hindcast + forecast sequences) as Google does, whose model is trained on thousands of gauges.
- Static features per station (Caravan-style catchment attributes), computed once from open GIS layers:
  catchment area, mean/max slope, elevation, stream order, land cover fractions (forest, rice, urban), soil/clay fraction, % catchment upstream of a reservoir, reservoir storage upstream relative to mean annual flow, distance to sea/Mekong, climate indices (mean annual rain, seasonality).
- Dynamic features: basin-averaged rain (observed + NWP + ensemble), antecedent rain 3/7/30 d, soil moisture (SMAP / ERA5-Land / DWR EWS soil sensors), upstream station levels/flows with lags, dam releases, tide/lake/Mekong levels where relevant, day-of-year.
- Target: change in level (or normalised level, e.g. `(H − H_p50)/(H_p99 − H_p50)`) so stations with different datums and ranges can share one model.
- Delineate catchments for each station by snapping to **MERIT Hydro / HydroRIVERS** networks.

### 4.2 Reservoir-controlled rivers (F1, F8)

Most Thai reservoirs are operated with an **upper and lower rule curve**: the upper curve is the standard level not to be exceeded each month (flood control), and the lower curve protects supply. Model reservoirs explicitly:

**Water balance (daily or hourly):**
```
S(t+1) = S(t) + [I(t) − R(t) − Spill(t) − E(t) − Div(t)] · Δt
```
- `I` inflow forecast: from F2 rain–runoff model of the upstream catchment (or reported `dam_inflow`).
- `R` release, in order of preference:
  1. **Announced plan** (RID/EGAT press releases, RID daily reports) → use as scenario.
  2. **Rule-curve policy emulation**:
     `if S > URC(doy): R = min(R_max_downstream, R_normal + (S − URC)/τ)`; `if S < LRC(doy): R = R_min`; else `R = demand`.
     `R_max_downstream` = safe capacity at the downstream control station (e.g. Bhumibol operation studies constrained flow at P.17 to 1,815 m³/s).
  3. **ML release model** trained on history (storage, inflow, neighbour dam release, downstream discharge, month) — studied for Sirikit comparing seven ML algorithms from linear regression to RNNs.
- `Spill` when `S > S_spillway`: use spillway rating `Q = C·L·(H − H_crest)^1.5`.
- **Outputs**: storage trajectory with uncertainty, **P(spill within N days)**, release forecast feeding downstream routing (METHODS.md §3.4).
- Small/medium reservoirs (thousands) often lack release data → use storage % trend + rain forecast → **overflow-risk category** (F8).

### 4.3 Flash floods (F3)

Lead times are hours; precision in level is impossible, so forecast **probability of flash flooding per small catchment / tambon**.

- **Flash Flood Guidance (FFG) concept** (US NWS method used in WMO FFGS): continuous soil-water accounting per small basin; compute the rain depth over 1/3/6 h that would produce bankfull flow (the "guidance"); **flash-flood threat = forecast/observed rain − FFG**. MRC's FFGS works on exactly this basis for small stream basins.
- **Rainfall-threshold model** (simpler, calibrate from history): intensity–duration thresholds `I = a·D^−b` per region, adjusted by antecedent rain/soil moisture; label past events from DWR EWS warnings, DDPM reports, news.
- **Inputs**: radar (TMD, HII, BMA), satellite rain (GSMaP, IMERG Early), NWP (TMD WRF 3 km hourly for 72 h; ECMWF/ICON via Open-Meteo), soil moisture (DWR EWS sensors, SMAP, ERA5-Land).
- **Use existing Thai products as features/baselines**: HII's tambon-level **flash-flood potential (FFPI)** with 1-day rain forecast, HII 24 h/48 h flash-flood risk areas, DWR EWS station status (watch/prepare/critical).
- **Nowcast 0–3 h**: radar extrapolation (`pysteps`).
- **Communication**: "เสี่ยงน้ำป่าไหลหลาก" levels per tambon with time window; never a precise depth.

### 4.4 Slow flat-basin floods & backwater (F4)

- Long travel times and **floodplain storage** dominate (Mun/Chi can stay high for weeks). Use Muskingum with large K or a **linear-reservoir cascade (Nash)**; calibrate on 2017/2019/2022 events.
- **Backwater at confluences**: the level at the lower Mun (e.g. Ubon) depends on Mekong level at Khong Chiam; include downstream level as a feature and an interaction term with local discharge.
- Recession is slow → "back to normal" estimates (METHODS.md §3.10) are especially valuable here; use two-segment recession (channel + floodplain drainage).

### 4.5 Mekong mainstream (F5)

- Stations: Chiang Saen, Chiang Khan, Nong Khai, Nakhon Phanom, Mukdahan, Khong Chiam (+ Lao/Cambodian stations upstream/downstream from MRC).
- Drivers: upstream flow from China (Jinghong dam releases), Lao tributaries and dams, basin rain. Example: a 1.2 m rise below Jinghong over two days (≈ +1,090 m³/s) was used by ONWR to forecast rises of 0.8–1.2 m at Chiang Khan and Nong Khai days later.
- Model: lagged-upstream ML (LightGBM) + MRC forecasts as a feature/benchmark; thresholds from MRC alarm/flood levels.

### 4.6 Coastal, tidal and lagoon boundaries (F6)

- Gulf-side stations: harmonic tides (METHODS.md §3.2), HII tide table (9 Gulf stations) and Navy tables; storm surge from HII's surge model stations.
- Andaman side and stations without tables: global tide models (FES2014/TPXO) at the river mouth, bias-corrected with any local gauge.
- **Songkhla Lake**: lake level is the downstream boundary for U-Taphao/Hat Yai; include lake level (gauge or satellite altimetry) as a feature.
- Tidal influence is **not** relevant for most inland stations → the router simply omits tide features (type ≠ F6).

### 4.7 Stations without a flood level (thresholds)

Priority order:
1. **Official metadata**: HII FEWS `hii_waterlevel.csv` (alarm/warning/critical thresholds), RID `rid_discharge.csv`, ThaiWater fields `min_bank`, `warning_level_m`, `critical_level_msl`, DWR EWS status thresholds, MRC alarm/flood levels.
2. **Statistical**: from ≥ 5 years of annual maxima fit GEV/Gumbel; **bankfull ≈ 1.5–2-year return level**; also percentiles (P90/P95/P99 of the daily-max series by season).
3. **Model thresholds at virtual points**: GloFAS return-period discharges (2/5/20-yr); Google gauge models include warning/danger thresholds.
4. **Impact-based calibration**: find the level at which flooding was observed (GISTDA/GFM extent overlapping settlements, DDPM reports, flooded-road reports from ThaiWater `flood_road`, Traffy/news) → set "impact level".

UI when only statistical thresholds exist: "สูงกว่าปกติมาก (สูงสุดในรอบ ~X ปี)" instead of "ล้นตลิ่ง".

### 4.8 Ungauged places (tier C)

- **Virtual gauges**: GloFAS discharge (Open-Meteo Flood API, ~5 km) and Google Flood Hub virtual (hybas) gauges → convert to **return-period category** (normal / 2-yr / 5-yr / 20-yr).
- **Satellite water levels**: SWOT river reaches and lakes via NASA's Hydrocron API (GeoJSON/CSV time series by reach/node ID); DAHITI altimetry for large rivers/reservoirs. Sparse in time → use for validation and slow systems (F4, lakes).
- **Satellite flood extent**: GISTDA (Thai, daily/7-day) and Copernicus GFM (every Sentinel-1 overpass). Use to confirm and to override "unlikely" messages.
- **Flash-flood potential**: HII FFPI per tambon covers places with no gauge.

### 4.9 Inundation / "is my home at risk" nationally

Same logic as METHODS.md §3.11, but:
- Controlling water body = nearest **hydraulically connected** reach (HAND on MERIT Hydro/FABDEM), not nearest station.
- For tier C: show **flood-recurrence** (GISTDA 2011–2023), current observed extent (GISTDA/GFM), and the virtual-gauge category.
- Always probabilistic; DEM error (~1–1.5 m) dominates in flat areas.

### 4.10 Verification at national scale

- Backtest per flood type and region (§1 events); metrics as METHODS.md §6.
- For categorical products (flash flood, spill risk, return-period category): **POD, FAR, CSI, Brier score, reliability diagrams**.
- Publish a national skill map (which stations/types have accepted models).

---

## 5. Data sources — Thai government

> Many endpoints below were documented by an open-source toolkit (`github.com/gain9999/thaiwater`, `skills/*.md`) that calls them without keys. Treat them as 🟡: verify, respect rate limits, cache, and ask the agency for official access before public launch.

### 5.1 HII / ThaiWater (สสน.) — backbone 🟡
Base: `https://api-v3.thaiwater.net/api/v1/thaiwater30/`

| Data | Endpoint(s) | Notes |
|---|---|---|
| Water level (all / by basin) | `public/waterlevel_load`, `?basin_code=`, `public/waterlevel?province_code=` | Fields include `warning_level_m`, `critical_level_msl`, `situation_level` 1–4 |
| History | `public/waterlevel_graph?station_type=tele_waterlevel&station_id=&start_date=&end_date=`, `public/waterlevel_graph_year?...&year=` | Yearly graph helps backfill |
| Canals | `public/canal_waterlevel` | |
| **Dams / reservoirs** | `analyst/dam`, `analyst/dam?dam_date=YYYY-MM-DD&dam_size=large|small`, `analyst/dam_yearly_graph?data_type=dam_storage&dam_id=&year=`, `analyst/dam_small_tele_graph` | Storage (MCM, %), inflow, release, level, spill — corresponds to thaiwater.net/water (dam page) |
| **Water gates** | `public/watergate_load`, `public/watergate_graph?station_id=&start_date=&end_date=` | Upstream/downstream level, pump on, gate open/height — thaiwater.net/water/gate |
| Discharge | `public/flow`, `public/flow_graph` | |
| Rain | `public/rain_24h`, `rain_today`, `rain_yesterday`, `rain_monthly`, `rain_yearly`, `public/rain7day_forecast` | |
| Flooded roads | `public/flood_road` | Impact data for threshold calibration |
| Storms | `public/storm_data` | |
| Station lookup | `frontend/shared/station_all?province_code=`, `watergate_station`, `tele_canal_station` | |
| National summary | `public/thaiwater_main`, `public/thailand` | |

Basin codes (examples): 1 Ping, 2 Wang, 3 Yom, 4 Nan, 5 Mun, 6 Chi, 7 Mekong, 10 Chao Phraya, 12 Pasak, 13 Tha Chin, 14 Mae Klong.

**HII FEWS data portal (flat files, no auth) 🟡** — `https://fews2.hii.or.th/model-output/data_portal/`
- `flashflood/flashflood_report.txt` — every tambon with **FFPI**, 1-day rain forecast, monitoring station, basin
- `flashflood/storm.txt` — active storms
- `metadata/hii_waterlevel.csv` — **station thresholds (alarm/warning/critical)**
- `metadata/rid_discharge.csv` — RID discharge station thresholds
- `tide_table/summary.txt` — daily tide predictions, 9 Gulf stations
- `drought/drought_dri_report.txt`, `radar/latest/png/rain24hrs.png`

**HII token APIs (flash-flood 24 h/48 h risk areas, storm surge stations, isohyets, GSMaP images)** 🟡⛔ — `api.hii.or.th/v2/<token>/warning/flashflood-24h|48h`, `api.hii.or.th/tiservice/v1/ws/<token>/...`. Tokens are embedded in the public web bundle; **do not hard-code them** — request your own token from HII (info_thaiwater@hii.or.th).

### 5.2 RID — Royal Irrigation Department (กรมชลประทาน) 🟡
| System | Access | Content |
|---|---|---|
| Telerid telemetry `https://telerid.rid.go.th/restapi/main/station_list/`, `.../get_basin_tree/` | Station list public; readings partly auth | ~921 stations (WL, rain), basin tree |
| Reservoir app `https://app.rid.go.th/reservoir/` | Public web | Storage by region/reservoir |
| Smart Water Operations Center `https://wmsc.rid.go.th/` | Portal | Links to subsystems |
| Flood reports `https://water.rid.go.th/flood/` (daily/weekly PDFs, upper/lower Chao Phraya plans) | Public | Releases, diversions, situation |

### 5.3 DWR — Department of Water Resources, Early Warning System (กรมทรัพยากรน้ำ) 🟡
- `POST https://ews.dwr.go.th/ews/web-service/stn` with `action=LoadStation` → all EWS stations (village-level flash-flood/landslide warning network) with rain 12 h, level, **soil moisture**, and status 0–3 (normal/watch/prepare/critical).
- 24 h graphs: `.../ews/graph/rain_graph.php?FilterSTN=`, `wl_graph.php`, `soil_graph.php` (value −9.99 = no data).
- Most valuable national source for **F3 flash floods** in mountainous villages.

### 5.4 EGAT — hydro dams (กฟผ.) 🟡
- `https://api-egatwater.egat.co.th/api/dam` → static info for EGAT dams (storage max/normal/min, coordinates, basin).
- Real-time storage/inflow/release: situation pages `water.egat.co.th/situation/situation_vol.php`, `inflowDaily.php`, `store_release.php` (data embedded in chart XML); live dashboard uses WebSocket.

### 5.5 TMD — Thai Meteorological Department 🔑
- Obs/forecast API: register at `https://data.tmd.go.th/api/registerPre.php` (WeatherToday, Weather3Hours, monthly rain, station list…).
- **NWP API** (register at `https://data.tmd.go.th/nwpapi/register`, OAuth bearer): 9 km / 10 days / 3-hourly and **3 km / 72 h / hourly** point forecasts → best Thai-specific rain forecast for F3/F7.
- Warnings pages (heavy rain, storms) → event flags.

### 5.6 GISTDA 🔑
- API gateway `https://api-gateway.gistda.or.th` (free key): daily flood extent by point, flood recurrence 2011–2023, **7-day flood WMS** (`.../resources/maps/flood/7days/wms`).
- Dashboards: `disaster.gistda.or.th/flood`, `flood.gistda.or.th`.

### 5.7 DDPM, ONWR, others 🔴
- DDPM (`disaster.go.th`, `api.disaster.go.th`) and ONWR national water portal (`ntw.onwr.go.th`) are behind Cloudflare browser challenges → **do not scrape around protections**; use their open data on `data.go.th`, official announcements, or request access. ONWR's National Water Command Center announcements (e.g. Mekong forecasts) are valuable event inputs.
- Navy Hydrographic Dept tide tables (PDF), Marine Dept (river mouths) as needed.

---

## 6. Data sources — international

### 6.1 Forecasts and warnings

| Source | What | Access | Use |
|---|---|---|---|
| **Google Flood Hub / Flood Forecasting API** | AI riverine forecasts, flood status, inundation maps, significant events; API also has flash-flood search | API key via Google Cloud **after acceptance** to the pilot/waiting list | Benchmark + virtual gauges for ungauged rivers |
| **GloFAS (Copernicus CEMS)** | Global discharge forecasts & return-period thresholds | Via Open-Meteo Flood API (no key) ✅; full products via CEMS/EWDS (free account) | Upstream Q, ungauged categories, thresholds |
| **Copernicus GFM** | Sentinel-1 flood extent every overpass, 3 algorithms | Viewer (free registration), API `api.gfm.eodc.eu/v2`, portal with downloads & alerts | Observed flood extent nationwide |
| **GDACS (UN + EC JRC)** | Global flood/cyclone alerts with GeoJSON polygons | Public REST API, no auth (`gdacs.org/gdacsapi/api`); flood polygons CC BY 4.0 | Event context, international alert level |
| **MRC (Mekong River Commission)** | Mekong water level, rain, forecasts, flash-flood bulletins | Data portal: free account for download, **license not open** | F5 Mekong inputs/benchmark (ask MRC for permission) |
| **WMO FFGS (MRCFFGS, SeAFFGS)** | Flash-flood guidance & threat | For national met/hydro services (TMD), not public | Ask TMD for products; replicate method (§4.3) |
| **SERVIR-SEA + ASEAN AHA Centre** | Regional flash-flood warning based on a rainstorm tracker | Partner access | Benchmark / collaboration |
| **ECMWF open data** (IFS/AIFS) | Global NWP incl. ensembles | Free, CC BY, no key (or via Open-Meteo) | Rain forcing 0–15 d |
| **ReliefWeb API, AHA Centre ADInet** | Situation reports, disaster records | Free | Event labels for validation |

### 6.2 Satellite interpretation (rain, extent, levels, soil)

| Product | Content | Access |
|---|---|---|
| **NASA GPM IMERG** (Early/Late/Final) | 30-min satellite rainfall | Free NASA Earthdata login |
| **JAXA GSMaP NRT** | Hourly satellite rainfall | Free registration |
| **Sentinel-1 SAR** | Raw radar images (cloud-penetrating) for own flood mapping | Copernicus Data Space (free account) |
| **NASA LANCE MODIS/VIIRS NRT flood** | Daily optical flood maps (cloud-limited) | Free Earthdata login |
| **SWOT (Hydrocron API)** | River reach/node & lake water-surface elevation time series (since late 2022) | NASA PO.DAAC API |
| **DAHITI** | Satellite-altimetry water levels for rivers/reservoirs | Free account + API |
| **SMAP / ERA5-Land** | Soil moisture (antecedent conditions) | Earthdata / Copernicus CDS (free) |
| **JRC Global Surface Water** | Historical water occurrence 1984→ | Free |
| **Sentinel Asia (JAXA), UNOSAT** | Emergency satellite maps on activation | Public products |

### 6.3 Static geodata

MERIT Hydro (flow direction, HAND), HydroBASINS/HydroRIVERS, FABDEM/Copernicus DEM, ESA WorldCover (land cover), SoilGrids, GHSL/WorldPop (exposure), Caravan (catchment attributes methodology).

---

## 7. System design changes for national scale

- **Station registry**: unify HII, RID, DWR, EGAT, BMA, MRC stations → canonical station ID, agency IDs, lat/lon, datum, thresholds (with source), flood-type tags F1–F8, data tier A/B/C, snapped river reach ID (HydroRIVERS/MERIT) and upstream catchment polygon.
- **River network graph**: reaches + stations + dams + gates + confluences; used for upstream feature extraction, routing and "which station controls my house".
- **Collectors**: one adapter per agency; national polling every 10–15 min (telemetry), hourly (reservoirs, EWS), daily (PDF reports, satellite). Raw archive + TimescaleDB as in SOURCES.md.
- **Compute**: LightGBM national models retrain weekly (CPU is enough); inference every 10–60 min; satellite processing (optional own Sentinel-1) is the only heavy job — start with GISTDA/GFM products instead.
- **Model router**: `station → (type, tier) → model family + threshold set + message template`.
- **UI**: national map → region → basin → station/tambon; each forecast shows type, tier and confidence.

---

## 8. Rollout plan

| Phase | Area | Why / timing | Main new components |
|---|---|---|---|
| 1 | Chao Phraya basin (current app) | Active now | METHODS.md pipeline |
| 2 | **South (Gulf side)** — Songkhla/U-Taphao, Nakhon Si Thammarat, Pattani, Narathiwat, Surat Thani | Flood season Oct–Jan; Hat Yai 2025 showed extreme risk | F3 + F7 + F6 (lagoon), DWR EWS, TMD NWP 3 km |
| 3 | Northeast + Mekong | Aug–Oct floods; long-duration | F4 + F5, MRC/ONWR, backwater |
| 4 | North | Jul–Oct flash floods | F3 flash-flood guidance, radar/GSMaP nowcasts, transboundary rivers |
| 5 | East & West | Regulated + coastal | F1 + F6 |

At each phase: backfill history → derive thresholds → backtest on reference events → accept per §4.10 → launch.

---

## 9. Legal, ethics and etiquette

- Attribute every source; follow licenses (GDACS/GFM CC BY 4.0 with credit; MRC not open → permission).
- Do not bypass Cloudflare or login protections; do not hard-code tokens copied from other sites' bundles — request your own.
- Poll gently, especially during disasters when agency servers are overloaded; serve users from your cache/CDN.
- Always link to official warnings (DDPM 1784, TMD, ONWR, RID, local authorities) and state that forecasts are estimates.

---

## 10. References (selection)

- Nearing et al. (2024) Global prediction of extreme floods in ungauged watersheds, Nature 627.
- Google Flood Forecasting API docs & Flood Hub help (API FAQ; gauges verified/lower confidence; 7-day hydrologic forecasts).
- Copernicus CEMS GloFAS & GFM technical documentation; GFM data access (api.gfm.eodc.eu).
- GDACS API documentation; IFRC Monty GDACS mapping.
- MRC Data Portal; MRC FFGS description (AMS 2013); WMO FFGS regional projects; SeAFFGS launch (WMO/VNMHA).
- SERVIR-SEA flash-flood warning with ASEAN AHA Centre (2024).
- Wannasin et al.: Machine learning for real-time reservoir operation simulation, Sirikit reservoir.
- Rule-curve operation of Bhumibol/Sirikit (JIRCAS JARQ; Kasemsup & Supriyasilp HEC-ResSim; Kyaw, Rittima et al.).
- NASA PO.DAAC Hydrocron (SWOT) announcement and docs; DAHITI API docs.
- Open-source Thai data toolkit: github.com/gain9999/thaiwater (skills: thaiwater, wmsc_rid, ews, egat, tmd, gistda, ddpm, onwr).
- News/official statements used for event context: Thairath, Khaosod English, The Nation/ANN (Hat Yai Nov 2025); Thairath (Mekong Aug–Sep 2026); MRC press release via ScandAsia; ThaiPBS World (ONWR Mekong forecasts).
