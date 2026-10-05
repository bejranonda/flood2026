# SOURCES.md — Data Source Registry (Phase 0 deliverable)

> **Project:** BKK FloodWatch 2026. Water-level monitoring and forecasting for Bangkok and the lower Chao Phraya.
> **Status:** 🟡 Live-probed from the production server in Germany (it is the only host, KI-502) and, for geo-blocked public pages, through the Thai egress: Bangkok sources 2026-09-26, **nationwide sources 2026-09-27 (§2d)**.
> **Last updated:** 2026-10-05 (v0.25.2; §2n)
> **Evidence:** [research/VALIDATION_2026-09-26.md](../research/VALIDATION_2026-09-26.md). Re-run with `python3 research/validation/validate_research_claims.py`.
> **Seeded from:** [sources_survey.md](../research/sources_survey.md), [keyless_access.md](../research/keyless_access.md), and the validated parts of [bangkok_flood_intelligence_data_sources.md](../research/bangkok_flood_intelligence_data_sources.md) and [API_noKey-1.md](../research/API_noKey-1.md).
> **Maintained by:** Phase 0 ([plan](plan/phase-0-source-verification.md)). Update this file whenever a source is tested, changes format, or fails.

## Legend
| Mark | Meaning |
|---|---|
| ✅ live | Called successfully on 2026-09-26 (dev host, Germany) |
| ✅ doc | Confirmed from documentation or working open-source code, not called yet |
| 🟡 | Source exists; the machine endpoint still has to be captured, or it only partly works |
| 🔴 | No machine access found (PDF, images, agreement needed, or blocked) |
| 🔑 | Needs an API key or registration |
| ❌ | Refuted: the endpoint doesn't exist or returns an error. Don't use it |

> **Rule:** a source is **"approved for Phase 1"** only after it has been called **from the production VPS** with our honest `User-Agent`, and the response has been archived as a test fixture ([GUIDELINES §5](GUIDELINES.md)). Results from Germany don't count for approval: BMA blocks non-Thai IPs, while HII accepts them.

---

## 1. Priority summary

| Priority | Source | Data | Access | Key | Status | Use in app |
|---|---|---|---|---|---|---|
| **P1** | HII ThaiWater public API (สสน.) | Latest WL (805 stations: HII, RID, FOP, EGAT), bank level, **discharge** for RID stations, rain, metadata | JSON | none | ✅ live | Real-time map, model inputs |
| **P1** | HII map feed `tiwrm…/json/telemetering/wl/warning` | ~110 stations: `lat`/`lng`, `bank`, `left_bank`/`right_bank`, `ground_level`, `wl_present`, `capacity` (% of bank), `raintoday`/`rain_yesterday`, local `date`/`time`, `wl_trend` | Keyless JSON GET | none | ✅ 200 (2026-09-26, 110 rows) | Coordinates, name and bank for stations missing them (D-023). ⚠️ Not all values are MSL (GLF002, KI-210) |
| P3 | OpenStreetMap (Overpass name search; Nominatim tried) | Approximate positions for 14 gauges no HII feed locates | One-off manual queries (honest UA, 1 req/s); results reviewed and committed as [station_coords_approx.json](../src/floodwatch/data/station_coords_approx.json) | none | ✅ 2026-09-26 (Nominatim: 0/29; Overpass: 14/29 plausible) | ODbL: "© OpenStreetMap contributors" (map tiles already credit OSM) |
| P2 | HII river centrelines `tiwrm…/resources/json/river/river_main.json` | 93 named rivers (MultiLineString, CRS84, ~100 m vertices); property `STR_NAMT` | Keyless GeoJSON (static asset of the warning map) | none | ✅ 200, 432 KB (2026-09-26) | River km for Chao Phraya gauges ([scripts/build_chainage.py](../scripts/build_chainage.py), D-019). Attribution: HII |
| **P1** | HII chart site (`tiwrm.hii.or.th`): `queryStation` (its `water1` has no timestamp and was frozen for GLF001, so not ingested), `getGraphFirst`, `POST /getGraph` (latest point only), map feed | **+162 stations not in `waterlevel_load`**; ~30 days of 10-min history per station (HTTP 500 for ~56 codes); coordinates only in the map feed (107 stations) | JSON | none | ✅ live / 🟡 partial | Backfill, charts, tide fitting, station coverage ([KI-207](KNOWN_ISSUES.md)) |
| **P1** | Open-Meteo Forecast + Ensemble | Hourly rain (ECMWF, GFS, ICON…), ensemble members | JSON | none (non-commercial) | ✅ live | Rain forcing, uncertainty |
| **P1** | Open-Meteo Flood API (GloFAS v4) | Daily discharge 1984→, forecast ≤16 d | JSON | none (non-commercial) | ✅ live | Upstream prior, backfill |
| **P1** | RID (กรมชลประทาน) | C-stations (partly in HII, **but not C.29A**), dam releases, diversions | Web/PDF | none | 🟡 portals reachable | Upstream boundary, Bang Sai |
| **P1** | Navy Hydrographic Dept. (กรมอุทกศาสตร์) | Hourly astronomical tide predictions | PDF | none | 🔴 **URL now 404 + bot challenge** | Tide component, fallback to own fit |
| **P2** | BMA DDS (สำนักการระบายน้ำ) | Khlong and river levels, rain gauges, 3 h nowcast, radar, flow and pump stations | Web / Relay / HII mirror | none | 🟢 **199 stations live via flood69 relay** (`bma_klong`); **30-day 10-min history via HII TIWRM** (`BKK*` series); direct `weather.bangkok.go.th` times out via VPN (subnet drop, KI-505) | Bangkok khlongs (live relay + HII telemetry mirror, D-031, D-053) |
| **P2** | Traffy Fondue public API | Citizen flood reports with coordinates, text, photos, state | JSON (undocumented) | none | ✅ live | Validation and "reported nearby" layer (privacy rules, KI-107) |
| **P2** | GISTDA API Gateway | Daily satellite flood extent, 2011–2023 recurrence | REST | 🔑 registered in `.env` | ✅ key configured | Flood extent layer, validation |
| **P2** | Copernicus GFM | Sentinel-1 flood masks | STAC (keyless) / REST (account) | none for the maps | ✅ live (§2k) | Research only (D-069); blind in Bangkok |
| **P3** | DEMs (FABDEM, Copernicus GLO-30, GEDTM30); Open-Meteo elevation | Ground elevation | COG / JSON | none | ✅ live (Open-Meteo) | **Probabilistic** depth only (KI-202) |
| **P3** | DWR EWS, DWR/ONWR PDFs, CCTV | Tributary telemetry, historical tables | Web/PDF | none | ✅ `ews.dwr.go.th` times out from Germany; **200 through the Thai egress**: 2,275 stations incl. soil moisture (§2d, 2026-09-27) | Backfill C-stations |
| **P3** | Google Flood Hub, NASA GPM IMERG | Forecast cross-check; satellite rain | Web / files | application / Earthdata | ⚠️ | Cross-check, upstream rain |

---

## 2. Registry (the brief's Phase 0 format)

"Probe" is the 2026-09-26 result from the dev host in Germany. The VPS column is still pending for every row.

| Source | Data type | Coverage | Access method | Endpoint(s) | Probe | Update interval | Latency / size | Auth | Datum & units | License / ToS | Reliability notes | VPS-tested |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HII `waterlevel_load` | Latest WL all stations | 805 stations nationwide (HII 330, RID 315, FOP 89, EGAT 71; **no BMA-agency rows**) | JSON | `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load` → `waterlevel_data.data[]` | ✅ 200 | 10 min (HII); RID rows hourly (12:00) | ~9 s, 1.4 MB | none | `waterlevel_msl` m MSL; `station.min_bank` bank m MSL; `discharge` m³/s; `waterlevel_datetime` **local, no TZ** | Not formally public. **Ask HII** (info_thaiwater@hii.or.th, 02-158-0901) | Some stations stale (e.g. BKC004 since 24 Sep); BKK008 absent although the chart API has it | not yet |
| HII `rain_24h` | Latest rain | National gauges | JSON | `GET …/thaiwater30/public/rain_24h` → `data[]` | ✅ 200 | 10 min | **>60 s, several MB** from Germany | none | `rain_1h`, `rain_24h` mm | as above | Needs compression and long timeouts; never fetch per user request | not yet |
| HII `waterlevel_graph` | Station history (API) | Per numeric `station.id` | JSON | `GET …/public/waterlevel_graph?station_type=tele_waterlevel&station_id={id}&start_date=…&end_date=…%20HH:mm` | ✅ 200 (2026-09-26) | hourly | ~2–5 s for a year | none | `value` m MSL, `discharge` | as above | **Serves at most 365 days**: C.12 (id 2599) from 2025-09-01 returned 8,777 points starting 2025-09-26; 2026-01-01 → 6,449; 2026-06-01 → 2,825 (≈ 75 % non-null). Used for the one-time 1-year backfill (D-018) | ✅ this host |
| **HII chart XHR** | 10-min WL history | Per `oldcode` (BKK001, BKK008, BKK020, BKK021, CPY015, …) | JSON behind the chart page | `GET https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}` → `[[epoch_ms_UTC, level_msl, bank, ground, bank], …]` (30 days = 4,310+ points); `GET …/json/telemetering/wl/warning` (live metadata) | ✅ 200 | 10 min | ~1.5 s, 180 KB | none | m MSL; epoch is **true UTC** | as above | **Provides 30-day 10-min history for key BMA canal reaches** (`BKK001` Lat Phrao, `BKK008` Saen Saep, `BKK005` Phasi Charoen, etc.). No geo-blocking | ✅ this host |
| RID C-stations via HII | WL + discharge | C.2 (1,824 m³/s), C.13 (1,912), C.3 (1,946), C.35 (1,156), C.36, C.37, S.26 Pasak (470) at 26 Sep 12:00 | via HII | `ridhydro_*` rows in `waterlevel_load` | ✅ 200 | hourly | – | none | m MSL, m³/s | – | **C.29A (Bang Sai), C.4/C.22 (Memorial Bridge), Fort Chula are not in HII** → need RID or Navy feeds | not yet |
| RID portals | Situation, releases, diversions | Chao Phraya basin | HTML / PDF | `https://water.rid.go.th/flood/`, `http://wmsc.rid.go.th/`; station list `http://water.rid.go.th/hyd/rainmean/st-list.htm` | ✅ 200 (pages) | daily | – | none | m³/s; Buddhist-era dates | – | Machine-readable data inside still to be found | not yet |
| BMA DDS (Direct) | Khlong/river WL, rain, flow and pump stations | Bangkok | Web pages / IIS | `https://dds.bangkok.go.th/`, `http://weather.bangkok.go.th/water/…`, `…/StationDetailFlow?id=` | 🔴 **connection reset from Germany**; via Thai VPN: **timed out** (BMA's server subnet blackholes relay) | 10–15 min | – | none | Datum per station TBD (KI-201) | ask BMA | Use HII TIWRM for history (`BKK*`) and `flood69` relay for live 199 `WL.*` stations | not yet |
| Navy tide tables | Hourly astronomical tide | Fort Phra Chulachomklao, Bangkok Bar, Bangkok Port, Navy HQ | PDF | old: `…/download/Water_lever69/LLW/TT2026.pdf` → **404**; site behind a Cloudflare challenge | 🔴 | yearly | – | none | **LLW (ม.ตลน.)**, offsets TBD | check | Find the new URL by hand; fall back to our own harmonic fit (APPROACH §5) | not yet |
| Open-Meteo Forecast | Hourly rain, wind, pressure | Point | JSON | `https://api.open-meteo.com/v1/forecast` | ✅ 200, CORS `*` | hourly | <0.2 s | none | mm, hPa, m/s | **Non-commercial free tier** (KI-106) | Store every issued run | not yet |
| Open-Meteo Ensemble | Member rain | Point | JSON | `https://ensemble-api.open-meteo.com/v1/ensemble` | ✅ 200 | per run | <0.2 s | none | mm | as above | – | not yet |
| Open-Meteo Flood (GloFAS v4) | Daily discharge | 5 km grid | JSON | `https://flood-api.open-meteo.com/v1/flood` | ✅ 200 | daily | <0.2 s | none | m³/s | as above | Snap onto the channel; calibrate against C.2/C.13 | not yet |
| Open-Meteo Elevation | Point elevation (90 m DEM) | Global | JSON | `https://api.open-meteo.com/v1/elevation` | ✅ 200 | static | <0.1 s | none | m (EGM2008) | as above | Gave 4 m and 7 m where the true value is about 0–2 m MSL. **Not for depth** | n/a |
| Traffy Fondue public | Citizen reports | Bangkok (+ other orgs) | JSON (undocumented) | `GET https://publicapi.traffy.in.th/share/teamchadchart/search?limit=…` → `results[]` (`coords` [lon, lat], `description`, `photo_url`, `timestamp` UTC, `state`) | ✅ 201, CORS `*` | near real time | <1 s | none | WGS84 | Citizen personal data: **aggregate only, don't republish photos or text**; ask BMA/NECTEC | Report time ≠ flood time | not yet |
| TMD API | Observations, forecasts | Thailand | REST | `https://data.tmd.go.th/api/…` (uid/ukey) | 🟡 portal 200 | 3 h / daily | – | 🔑 | mm, °C | TMD terms | Register now | not yet |
| GISTDA flood extent | 1/3/7/30-day extent, recurrence | Thailand | REST (OGC features) | `https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/7days?limit=&offset=&bbox=`, header `API-Key` (the older `gi-service/…flood-extent-1day?api_key=` path answers 404, KI-510) | ✅ key in `.env` | daily | days | 🔑 configured | – | Open Data Common | Use for validation | ✅ key verified |
| Copernicus GFM | Sentinel-1 flood masks | AOIs | REST | `https://api.gfm.eodc.eu/v2/` | ✅ 200 | per pass | days | free account | – | Copernicus open | – | not yet |
| data.go.th (BMA) | Daily max at Pak Khlong Talat | 1 station | CSV (CC-BY) | `https://dev.data.go.th/en/dataset/wl-max-chaophraya-river` | ✅ 200 (page) | daily | – | none | m MSL | CC-BY | Backfill | not yet |
| DEM files | Elevation | Global 30 m | COG | FABDEM, Copernicus GLO-30, GEDTM30 | ✅ doc | static | – | none | **EGM2008 → Ko Lak offset** | FABDEM is non-commercial | RMSE ≥ 1 m in Bangkok | n/a |

---

### 2b. Thai egress probe (Updated 2026-09-27 19:30 UTC, exit: the VPN Gate relay in Ayutthaya, TH, via [D-016](plan/DECISIONS.md))
| URL | From Germany | Via Thai egress | Notes |
|---|---|---|---|
| `https://ews.dwr.go.th/` | timeout | **200** | Successfully unblocked via VPN |
| `https://hydro.navy.mi.th/` | 403 bot challenge | **200** | Successfully unblocked via VPN |
| `…/download/Water_lever69/LLW/TT2026.pdf` | 404 | **404** | URL moved, not blocked |
| `https://dds.bangkok.go.th/` | connection reset | **timeout** (SYN dropped) | BMA's server subnet blackholes relay |
| `https://weather.bangkok.go.th/` (+ `flood/`) | connection reset | **timeout** (SYN dropped) | Port 80/443 dropped by BMA firewall (KI-505) |
| `https://tiwrm.hii.or.th/` | 200 | **200** | Free, unblocked, provides 30-d history (`BKK*`) |

### 2c. BMA Canal Gauges & Access Methodology (v0.3.0 + v0.9.0, D-031, D-053)
| Candidate / Channel | What we found | Verdict |
|---|---|---|
| **Direct BMA Portals** (`weather.bangkok.go.th`, `dds.bangkok.go.th`) | Blocked from foreign datacenters (reset/403) and drops TCP connections from VPN Gate relay IPs (ports 80 & 443 time out, tinyproxy 500). Furthermore, does not offer an open historical time-series API | 🔴 blocked & unsuitable for history |
| **`https://flood69.peoplesparty.or.th/api/klongmap`** (People's Party relay of BMA KlongMap) | **200**, 2.0 MB JSON, updated every 5 min. **199 unique BMA stations** (codes `WL.xxx.nn` like `WL.KTY.01` ส.คลองเตย, `WL.AJP.01` ค.อาจารย์พร, `WL.BKY.02` ค.บางเชือกหนัง, `WL.KLA.01` ค.ลาว ถ.พัฒนาการ, `WL.LPW.01` ปตร.คลองลาดพร้าว) with lat/lon, bank levels, BMA warning/critical thresholds. Snapshot only: history accumulates locally | ✅ **Primary live collector** (`bma_klong`, every 10 min) |
| **HII TIWRM 30-Day History API** (`https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}`) | **200**, keyless, unblocked globally. Provides **30 days of 10-minute resolution telemetering history** (4,310+ points) for key Bangkok canal reaches matching BMA stations (`BKK001` Lat Phrao ↔ `WL.SST.01`, `BKK008` Saen Saep ↔ `WL.SSB.06`, `BKK005` Phasi Charoen ↔ `WL.TWW.05`, `BKK009` Lam Pla Thio ↔ `WL.LPT.03`, `BKK020`, `BKK021`, etc.) | ✅ **Canonical historical telemetering** (v0.9.0, D-053) |
| BMA "roads to avoid" Claude artifact `claude.ai/artifact/N6umcENfSgoY6GMkhVKwZs` | A **static page**, data embedded, no fetch. 135 district-office reports (from an xlsx, 17:43 local) + 55 road sensors (20:40 local); positions **approximate, geocoded from street names**; depth in cm with impact notes ("รถเล็กผ่านไม่ได้"). Updated by hand, so it's a snapshot, not a feed | 🟡 link only (Q25); no scraping |
| `flood.larry-cctv.com` (road-sensor source named in that artifact) | Legacy TLS renegotiation + self-signed chain; the page **redirects to a Palo Alto GlobalProtect login** | 🔴 private system — **do not use** |

### 2d. Nationwide candidates (probed 2026-09-27 08:55–09:45 UTC; details and re-run script: [research/VALIDATION_2026-09-27_nationwide.md](../research/VALIDATION_2026-09-27_nationwide.md))
Freshness counts are rows with a timestamp on 2026-09-26/27. None of these is collected yet (owner: validate first, D-044).
| Source | Endpoint | Found | Verdict |
|---|---|---|---|
| HII dams | `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam` | 50 large dams (all fresh: storage MCM/%, inflow, release, spill, max/normal storage); 862 medium (448 fresh, 317 dated 1970-01-01); 60 small-dam telemetry (52 fresh, with spillway level). No rule curves here (they are in `dam_yearly_graph`, §2o) | ✅ national reservoir state; filter stale rows |
| HII BMA road sensors | `GET …/thaiwater30/public/flood_road` | **262 BMA road-flood sensors, 241 fresh**, depth on the road in **cm**, lat/lon, code `FL.xxx.nn` | ✅ Bangkok road-level measurement (never convert to m MSL) |
| HII BMA canals | `GET …/thaiwater30/public/canal_waterlevel` | 282 BMA canal gauges, 229 fresh; same `WL.xxx.nn` codes and values as the flood69 relay; +73 fresh gauges we lack; 250 with bank/warning/critical | ✅ government channel for BMA canals (KI-218) |
| HII gates | `GET …/thaiwater30/public/watergate_load` | 2,315 rows, **12 fresh**; most stopped July 2023; no thresholds | ❌ stale nationally |
| HII FEWS portal | `GET https://fews2.hii.or.th/model-output/data_portal/…` `flashflood/flashflood_report.txt`, `metadata/hii_waterlevel.csv`, `metadata/rid_discharge.csv`, `tide_table/summary.txt` | FFPI for at-risk tambons (25 today); thresholds for 66 HII level stations (m MSL) and 87 RID discharge stations (m³/s; C.13 2,176/2,448/2,720); Navy tide predictions for **28 stations** incl. Fort Chula | ✅ keyless flat files |
| DWR EWS | `POST https://ews.dwr.go.th/ews/web-service/stn` (`action=LoadStation`) | Timeout from Germany; **200 via the Thai egress** (28 s, 3 MB): 2,275 stations (1,819 rain, 455 level), rain 12 h, level, soil moisture, status 0–3 plus `9` on 783 stations; dates `27/09/69 15:45 น.` (Buddhist short year, ICT) | ✅ Thai egress only |
| RID Telerid | `GET https://telerid.rid.go.th/restapi/main/station_list/` | Timeout from Germany; 200 via Thai egress; `count: 921` | ✅ list only (readings untested) |
| EGAT | `GET https://api-egatwater.egat.co.th/api/dam` | 69 dams, static, most fields empty | ⚠️ low value |
| GloFAS | `GET https://flood-api.open-meteo.com/v1/flood` | Keyless; a naive point at Nong Khai gives 1–3 m³/s, the Mekong cell 5 km away ≈ 9,000 m³/s | ✅ **snap to the channel** (KI-509) |
| Google Flood Forecasting API | `floodforecasting.googleapis.com/v1/…` | 403 without an API key | 🔑 owner applies (OWNER_ACTIONS) |
| Copernicus GFM | `https://api.gfm.eodc.eu/v2/` | API reachable; account needed | 🔑 |
| GDACS | `gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=FL&country=THA…` | 204, no Thai flood events Aug–Sep 2026 | ⚠️ context only |
| GISTDA flood extent (key) | `GET https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/{1day,3days,7days,30days}` and `/features/flood-freq`, header `API-Key`, params `limit`/`offset`/`bbox` (docs: `disaster.gistda.or.th/services/open-api`) | 200. National flooded H3 cells (~0.12 km²): 3 d 38,461 · 7 d 49,761 · 30 d 52,778, with area, exposure and source passes (Sentinel-1, Radarsat-2, COSMO-SkyMed); 1 d empty (no pass); **Bangkok 0 in 7 d** (radar misses urban water) | ✅ satellite extent nationally; never "no flood" in cities (KI-510) |
| thaiwater.net pages (`/water/wl`, `/water`, `/water/gate`) | — | JS single-page app over the `api-v3` endpoints above | ✅ use the API, not the page |

### 2f. BMA canal history via HII (probed 2026-09-27 20:00 UTC, honest UA; D-054)
| Source | Endpoint | Found | Verdict |
|---|---|---|---|
| **HII canal graph (BMA gauges)** | `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_graph?station_type=canal&station_id={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` (`id` = `station.id` in `public/canal_waterlevel`, e.g. WL.SSB.07 = 77) | 200, keyless, from Germany; `graph_data[{datetime (Thai time), value, value_out}]` plus `min_bank`, `warning_level`, `critical_level`; 15-min; one year ≈ 29,000 points, 2.7 MB, ~18 s; 2024 fully present. Values **identical** to the relay (46 matching times, 0.0 m) | ✅ **collected** (`bma_history`: 1-year hourly backfill, then daily 3-day refresh). 162 of our 199 BMA gauges are in HII's canal feed; 37 are not (relay-only history) |
| HII chart XHR for BMA codes | `…/getGraphFirst/WL.SSB.07` | HTTP 500 | ❌ serves HII `BKK*` codes only |
| thaiwater.net app | `www.thaiwater.net/dist/js/app.chunk.js` | shows the canal graph call above and `tele_canal_station?province_code=` | reference only |

### 2e. Forecast and ONWR sources (probed 2026-09-27 16:45–17:15 UTC, honest UA; D-050)
| Source | Endpoint | Found | Verdict |
|---|---|---|---|
| **HII official forecast** | `GET https://fews2.hii.or.th/model-output/data_portal/hii_waterlevel/forecast/{CODE}.txt`, `…/rid_discharge/forecast/{CODE}.txt` (codes as in `metadata/*.csv`: CPY011, C13) | 200, keyless, from Germany; hourly `station,date,time,value`, Thai time, ~6 days before + 7 days after the issue; `Last-Modified` = issue time; overwritten each issue; C.13 release held constant | ✅ **archived** (`hii_fews_forecast` → `external_forecast`), not shown until scored (KI-112) |
| HII FEWS observed discharge | `…/rid_discharge/observe/{CODE}.txt` | referenced by the ONWR app; not needed (C.13 discharge arrives via `waterlevel_load`) | ⚠️ not used |
| ONWR National Thai Water | `https://nationalthaiwater.onwr.go.th/waterlevel`, `/dam` | React app over the same `api-v3.thaiwater.net/api/v1/thaiwater30` endpoints we already use (`waterlevel_load`, `analyst/dam`) | ✅ nothing new; use the API directly |
| ONWR public API | `https://ntw-admin.onwr.go.th/api/v1/public/disaster`, `/reportwater/events`, `/reportwater/events/option` | Timeout from Germany; 200 via the Thai egress. `disaster` empty on 2026-09-27; `reportwater/events`: 8 official event reports in 2026 (North/Northeast, none in Bangkok) | 🟡 low value for Bangkok; keep for the national phase |
| HII token API in the ONWR bundle | `api.hii.or.th/v2/<token>/isohyet/...` | token hard-coded in a public web bundle | ⛔ never use copied tokens |
| Open-Meteo historical forecast | `https://historical-forecast-api.open-meteo.com/v1/forecast?...&hourly=precipitation` | 200, keyless; a year of hourly rain at any point (stitched early forecast hours) | ✅ training data (upper-bound tests) |
| Open-Meteo previous runs | `https://previous-runs-api.open-meteo.com/v1/forecast?...&hourly=precipitation_previous_day1,precipitation_previous_day2` | 200, keyless; forecasts issued 1–2 days earlier, a year back | ✅ **collected daily** (`openmeteo_prev` → `rain_hindcast`, one year backfilled 2026-09-27); training data for `star` (D-052) |
| Nominatim reverse | `https://nominatim.openstreetmap.org/reverse?lat&lon&format=jsonv2&zoom=14&accept-language=th` | 0.15–0.23 s; แขวง/เขต in Bangkok, อำเภอ/จังหวัด elsewhere | ✅ district line (D-051), ≤ 1 req/s shared with search, rounded ~1 km, never logged |

### 2g. Nationwide history and rain cells (probed 2026-09-30 19:55–20:45 UTC, honest UA; D-064)
| Source | Endpoint | Result |
|---|---|---|
| HII year per gauge | `api-v3.thaiwater.net/.../waterlevel_graph?station_type=tele_waterlevel&station_id={hii_id}&start_date=…&end_date=…` | ✅ 200; URTU07 (3519): 8,537 hourly readings 2025-10-01 → 2026-09-30, 730 KB, one request; `min_bank` 237.389, `ground_level` 225.475 |
| Open-Meteo, several points | `api.open-meteo.com/v1/forecast?latitude=a,b,c&longitude=x,y,z&hourly=precipitation` | ✅ 200; a JSON **list** in coordinate order (a single point answers an object) |
| Open-Meteo previous runs, several points | `previous-runs-api.open-meteo.com/v1/forecast?latitude=a,b&longitude=x,y&hourly=precipitation_previous_day1,precipitation_previous_day2&start_date=2025-10-01&end_date=2026-09-29` | ✅ 200; list of 2, 8,736 hourly values each. ⚠️ Free-tier weighting of long ranges (a year ≈ 26 calls per location) is from Open-Meteo's terms, not measured; the collector stays at ≤ 8 new cells per hour |
| HII TIWRM chart host | `tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{code}` | ❌ connect timeout 2026-09-30 20:32–20:44 UTC (api-v3 fine at the same time) — transient outage, KI-251 |

### 2h. HII rain history (probed 2026-10-01 13:15–13:30 UTC, honest UA; Q43)
| Source | Endpoint | Result |
|---|---|---|
| HII web app endpoint list | `www.thaiwater.net/dist/js/app.chunk.js` (90 `thaiwater30/...` paths) | No public **hourly** rain history; rain endpoints: `public/rain_24h`, `rain_today`, `rain_yesterday`, `rain_monthly`, `rain_yearly`, `provinces/rain{3,5,7,15}d_graph` |
| HII daily rain per gauge | `api-v3.thaiwater.net/api/v1/thaiwater30/provinces/rain3d_graph?station_id={rain_24h station.id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | ✅ 200, `data: [{rainfall_datetime: "YYYY-MM-DD", rainfall_value}]`, ≤ ~31 days per request (else `RespCode 422 "limit date range"`), back to ≥ 2024-10. Label = day the 24 h window ends; values ~7× our hourly sums (median) ⚠️ unexplained ([research](../research/2026-10-01_measured_rain.md)) |

### 2i. Basin and river maps (probed 2026-10-02 22:20–22:45 UTC, honest UA; D-066)
| Source | Endpoint | Result |
|---|---|---|
| HII basin polygons | `www.thaiwater.net/json/boundary/basin.json` | ✅ 200, 22 features (`BASIN_CODE`, `BASIN_T`), 17 Polygon + 5 MultiPolygon, 119 KB |
| HII main rivers | `www.thaiwater.net/json/river/river_main.json` | ✅ 200, 93 MultiLineString (`STR_NAMT`), 432 KB |
| HII other boundaries | `json/boundary/{amphoe,tambon,thailand,region_tmd,bkk_amphoe,floodplain}.json` | ✅ 200 (931 amphoe, 7,791 tambon, 77 provinces, 6 TMD regions, 50 Bangkok districts, 10 retention areas) — not used yet |
| HydroBASINS / HydroRIVERS | `data.hydrosheds.org/file/hydrobasins/standard/hybas_as_lev01-12_v1c.zip` | ❌ 403 Cloudflare challenge ("Just a moment…") from the server — not bypassed; licence (product page): free for scientific, educational and commercial use, attribution Lehner & Grill (2013). Owner download: OWNER_ACTIONS HYDROBASINS |
| HydroBASINS v1c Asia, lake format (owner download 2026-10-02) | `data/basins/raw/hybas_lake_as_lev01-12_v1c.zip` (413 MB, not in git) | ✅ levels 1–12; level 8: 33,354 sub-basins (median 405 km²), `HYBAS_ID, NEXT_DOWN, NEXT_SINK, MAIN_BAS, DIST_SINK, DIST_MAIN, SUB_AREA, UP_AREA, PFAF_ID, SIDE, LAKE, ENDO, COAST, ORDER, SORT`. Lake format: lake-split sub-basins have L/R sides sharing `UP_AREA` (R drains into L, tech doc §2.3). Catchment rain tested: no gain ([research](../research/2026-10-02_catchment_rain.md)) |
| ONWR legal 22 main basins (owner download 2026-10-02) | DWR page `division.dwr.go.th/rdhd/index.php/th/services/12/2024-04-17-02-39-05/160-shapefiles` → Google Drive; stored `data/basins/raw/Shp_Basin_ONWR-*.zip` | ✅ `MainBasin_ONWR_Law_WGS84` (สทนช., 7 Jul 2021): 28 records (22 + island parts), UTM 47N, CP874, `MB_CODE, MBASIN_T, MBASIN_E, AREA_SQKM, Basin_T`; **no sub-basins; no licence stated ⚠️ (not redistributed)**. Same 22 basins as HII's `basin.json`: 98.5 % of gauges identical ([research](../research/2026-10-02_onwr_basins.md)) |

### 2j. AI provider for resident answers (probed 2026-10-02 11:15–13:30 UTC from the app container; D-068)
| Source | Endpoint | Result |
|---|---|---|
| GLM chat (Zhipu AI) | `open.bigmodel.cn/api/paas/v4/chat/completions`, model `glm-5.3-flash` (key in `.env`) | ✅ Thai answers. Always reasons: `thinking: {type: disabled}` → error 1210 ("该模型始终思考，不支持关闭思考；请使用 low、high 或 max"); `reasoning_effort: "low"` → 1.1 s, no `reasoning_content`; default → 8–10 s with ~850–1,400 reasoning chars. ~570 calls in three validation runs: median 3.1–4.5 s; the final run (198) median 3.1 s, p90 4.4 s, none > 8 s |
| GLM `glm-4-flash` | same endpoint | ❌ error 1211 "模型不存在" (model does not exist) — the D-030 default name is outdated |

### 2k. Satellite flood maps, GloFAS, WeatherNext, EWDS (probed 2026-10-02 19:50–21:10 UTC, honest UA; D-069)
| Source | Call | Result | Verdict |
|---|---|---|---|
| Copernicus GFM, keyless | `GET https://stac.eodc.eu/api/v1/collections/GFM/items?bbox=99.9,13.4,100.95,15.9&datetime=…&limit=100` (+ `next` links) | ✅ 200, no auth: 178 items in 30 days; assets are COGs at `data.eodc.eu/collections/GFM_LAYERS/…` (200, no auth): `ensemble_flood_extent`, `ensemble_likelihood`, `exclusion_mask` (missing on some items: 27 of 178 had 13 assets instead of 14), `reference_water_mask`, `advisory_flags`, 3 algorithm layers; 20 m, Equi7 `AS020M` tiles; values 0/1, 255 = no data. ⚠️ item bbox ≠ imaged strip (only 42 of 178 had data over the region) | ✅ research; CC BY 4.0 |
| Copernicus GFM, account | Swagger `https://api.gfm.eodc.eu/v2/swagger.json` (v24.01); `POST /v2/auth/login {"email","password"}` | 200 + token with the owner's login (owner_status GFM ✅); 400 with a wrong login; product endpoints 401 without | ✅ works; not needed (same products) |
| GISTDA flood, 7 days national (collector `gistda_flood`, 2026-10-03) | `GET …/features/flood/7days?limit=5000&offset=…`, header `API-Key` | ✅ 200, 111,387 cells in 23 pages of ~14 MB (≈ 7 min); `1day`/`3days` returned 0 cells that morning; every cell `_createdAt` = the daily rebuild (~18 UTC), one composite `file_name` list (images 27–29 Sep). `skipGeometry`/`properties=` → 0 features (not supported). **Rebuilt several times a day** (3 Oct: ~15 UTC and 17:24–17:27 UTC → 72,008 cells, images 28 Sep – 2 Oct): probe `limit=1` hourly, download a finished new build (KI-268) | ✅ live (D-071, v0.20.5) |
| GISTDA flood, 30 days in the region | `GET …/features/flood/30days?bbox=99.9,13.4,100.95,15.9&limit=1000&offset=…`, header `API-Key` | ✅ 200, 56,899 H3 cells, 1,440 km²; ⚠️ `links` echo the caller's key (KI-262) | ✅ research |
| GloFAS (Open-Meteo) | `GET https://flood-api.open-meteo.com/v1/flood?latitude=…&longitude=…&daily=river_discharge&start_date=2025-09-25&end_date=…` | ✅ 200; `consolidated_v4` empty for this period; `seamless_v4` = `forecast_v4` for past days (no forecasts as issued). C.2 point → 1.1 m³/s (side cell, KI-509). 49 points × 1 year in one request → **429** (KI-264) | ❌ no gain ([research](../research/2026-10-02_glofas_outlook.md)) |
| EWDS (CEMS GloFAS archive) | `GET https://ewds.climate.copernicus.eu/api/catalogue/v1/collections/cems-glofas-forecast` | ✅ 200, forecasts 2019-11-05 → 2026-10-01; reforecast 1999–2023. Token check `POST /api/profiles/v1/account/verification/pat` with `PRIVATE-TOKEN`: 401 without/with a dummy, **200 with the owner's token** | ✅ works; not needed (GloFAS upper bound failed) |
| WeatherNext 3 (Google DeepMind) | Docs: `developers.google.com/weathernext/guides/{access-forecast,models,bigquery}`; terms `storage.googleapis.com/weathernext-public/terms-of-use.pdf` (modified 2026-09-03) | Hourly init (15 d at 00/06/12/18 UTC, 48 h otherwise), 1 h steps, 64 members, 0.05° station / 0.1° grid; rain `total_precipitation_1hr` (m), also `imerg_tp_1hr`, `experimental_tp_1hr`; BigQuery `weathernext_3_0_0_0p1deg` / `_0p05deg` via Analytics Hub linked dataset `weathernext_3`. Subscribed & verified live 2026-10-04 (HTTP 200, 2 tables; sample query 17.3 MB scanned, KI-283) | ✅ connected (research only, D-069) |


### 2l. More stations and sub-basins (probed 2026-10-03 19:00–20:00 UTC; Thai egress for DWR/Telerid, public pages only, no credentials; D-081, D-082)
| Source | Request | Result | Use |
|---|---|---|---|
| HII `waterlevel_load` (again) | as §2 | 808 rows, 794 fresh; **all in our app**; `station.sub_basin_id` on every row (237 ids); `left_bank`/`right_bank` differ from `min_bank` by > 1 m at 254 rows (KI-272) | ✅ `sub_basin` stored (D-082) |
| DWR EWS stations | `POST https://ews.dwr.go.th/ews/web-service/stn` `action=LoadStation` | ✅ 200 via Thai egress, 45 s, 3 MB: 2,275 posts (1,819 rain, 455 level); `wl` m on a local post; `alert_max` mostly 4.00; `date` "04/10/69 01:15 น." (day/month/BE short year, ICT) | ✅ `dwr_ews` every 30 min, archived (D-081) |
| DWR EWS chart | `GET https://ews.dwr.go.th/ews/graph/wl_graph.php?FilterSTN={stn}` (from the site's `assets/js/utils.js`) | ✅ 200, ~23 s, JSON `[[epoch_ms, m], …]` 15-min, **~11 h only**, no date parameter; 5 of 30 sampled posts empty | ⚠️ not collected (too short, too slow) |
| RID Telerid | `GET https://telerid.rid.go.th/restapi/main/station_list/` | ✅ 921 stations (code, basin, sub-basin, province, point); `/restapi/main/` 401 "Authentication credentials were not provided" | ❌ readings need RID's permission (owner declined to ask, 2026-10-03) |
| HII BMA canals | `GET …/thaiwater30/public/canal_waterlevel` | 282 rows, newest 2026-09-28 (frozen, KI-273); 76 BMA gauges not in our app | ⚠️ re-check weekly |
| GISTDA 7-day layer | as §2k | 2026-10-03 19:44 UTC: `numberMatched` 0, no features for > 1 h (rebuild) | guarded (KI-269) |

### 2n. Flood Hub archive and WeatherNext query cost (probed 2026-10-04 20:00–20:30 UTC; D-094, D-096)
| Source | Call | Result | Use |
|---|---|---|---|
| Google Flood Hub | `gauges:queryGaugeForecasts?gaugeIds=…&issuedTimeStart=<365 d ago>` (key in header) | 366 daily forecasts per gauge back to 2025-10-05; 320/320 values identical to our live store (2–4 Oct) | honest backtest of Flood Hub as an input (Q55) |
| WeatherNext 3 | BigQuery, one literal point, one init | 11.8 MB processed; a joined list of 9 points 56 GB; archive at 2026-04-07 yes, 2025-10-04 no; 61 init times in one IN list refused, 3 pass (22 MB); then HTTP 403 "exceeded quota for free query bytes scanned" | backtest after the owner's billing step (Q53) |
| Google Flood Hub (backfill) | `queryGaugeForecasts`, 5 points per call, `issuedTimeStart` 366 days back (2026-10-05) | 302,408 daily steps for 103 points, 2025-10-04 → 2026-10-05 | `star` input (D-097) |
| RID discharge | `observation.discharge` | 290 gauges hourly; C.13 2,500 m³/s on 2026-10-04 = Thai PBS/Amarin | ticker flows (D-094) |

### 2m. Google Flood Hub and dam history (probed 2026-10-04 09:50–14:10 UTC, honest UA; D-087, D-090)
| Source | Request | Result | Use |
|---|---|---|---|
| Google Flood Forecasting API | `POST floodforecasting.googleapis.com/v1/gauges:searchGaugesByArea` `{regionCode:"TH"}`; `floodStatus:searchLatestFloodStatusByArea`; `GET gaugeModels:batchGet?names=gaugeModels/{id}`; `GET gauges:queryGaugeForecasts?gaugeIds=…&issuedTimeStart=…`; key in `X-Goog-Api-Key` | ✅ 200: 103 HYBAS virtual gauges (all `qualityVerified`, `hasModel`); statuses (severity NO_FLOODING / ABOVE_NORMAL / SEVERE, trend, forecast window, inundation map type); thresholds warning / danger / extreme (m³/s); daily discharge ~9 days | ✅ collector `google_floodhub`, validated, not shown (D-087) |
| HII large dams | `GET api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam` → `data.dam_daily` | ✅ 50 dams with storage, inflow, release, `dam.sub_basin_id` | reference |
| HII dam history | `GET …/analyst/dam_yearly_graph?data_type=dam_released&dam_id={id}&year={yyyy}` (from `www.thaiwater.net/dist/js/app.chunk.js`) | ✅ daily values (MCM/day) for the year, plus `upper_rule_curve`, `lower_rule_curve`, bounds, `average_inflow` — **rule curves exist** (SOURCES §2d said none) | tested as input: no gain (D-090) |

### 2o. Kaeng Krachan pilot: dam records, rule curves, river history (probed 2026-10-05 08:00–10:00 UTC; D-099)
Two probe requests to `dam_yearly_graph` went out without a User-Agent by mistake (an empty shell variable); every other request used the project UA from `config.py`.

| Source | Request | Result | Use |
|---|---|---|---|
| HII large dams (daily) | `GET …/thaiwater30/analyst/dam` → `data.dam_daily[]` | ✅ 50 dams; Kaeng Krachan twice: RID `dam.id` 13 (5 Oct: released 10.8 ล้าน ลบ.ม./วัน, storage 725.85 = 102.23 %, spill 0, `dam_level` 0 = not reported) and EGAT `dam.id` 57 (4 Oct: released 3.04, 58.64 %, level 99.36 m) — they disagree (KI-295) | `dam_daily` via `hii_dams` (6 h) |
| HII dam year | `GET …/analyst/dam_yearly_graph?data_type={dam_released\|dam_storage}&dam_id=13&year={yyyy}` | ✅ daily values for the year (Thai dates, `T00:00:00+07:00`); `upper_rule_curve` / `lower_rule_curve` (366 days listed as 2020, ล้าน ลบ.ม.; 5 Oct 593.37 / 203.80); `normal_bound` 710 (RID's percent = storage / 710: 725.85 / 710 = 102.23 %), `upper_bound` 900, `lower_bound` 65; 2018–2026 served; values equal `analyst/dam` (5 Oct: 10.8 and 725.849) | the pilot dam's history and rule curve (`hii_dam_history`, in `hii_dams`) |
| HII station history, 2018 | `GET …/public/waterlevel_graph?station_type=tele_waterlevel&station_id={id}&start_date=2018-08-01&end_date=2018-08-31%2023:59` for B.18 (1098952), B.10 (2671), B.16 (505029), B.15 (505030), PCH001 (758) | ⚠️ HTTP 200 with hourly timestamps but **no values** for every gauge | none — the 2018 release (24.36 ล้าน ลบ.ม./วัน on 21 Aug) needs RID's own records (Q56) |
| HII station history, 2024–25 | same, B.10, Oct 2024 and Jan 2025 | ✅ 635 and 611 hourly values with discharge | a longer replay is possible, but 2019–2025 never released more than 9.13 ล้าน ลบ.ม./วัน |

## 3. Refuted endpoints — do **not** use

| Endpoint / claim | From | Evidence (2026-09-26) |
|---|---|---|
| `https://api-v3.thaiwater.net/v1/telemetry/station/river` + `x-api-key`; fields `river_water_level_msl`, `tele_station_code` | bangkok_flood_intelligence_data_sources.md | **HTTP 404** |
| `https://api2.thaiwater.net/v1/analyst/water/telemetry`, codes `C.29`, `BKK01` | API_noKey-1.md | **The host does not resolve in DNS**; the codes don't match HII (`BKK001`…) |
| `https://open.traffy.in.th/api/v1/tickets?type=flooding` | bangkok_flood_intelligence_data_sources.md | **The host does not resolve in DNS**. Use `publicapi.traffy.in.th` (above) |
| `https://weather.tmd.go.th/svpLoop.php` | same | **HTTP 404** |
| `https://www.hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf` | sources_survey.md | 301 → **404** |
| `THAIWATER_API_KEY` for the public API | old `.env.example` | The public endpoints work without a key |
| `https://api2.thaiwater.net/v1/analyst/water/{telemetry,dam,watergate}` | research/Nationwide/Research_Thailand.md | **Still no DNS** (re-checked 2026-09-27) |
| `https://ffw-web.mrcmekong.org/` | research/Nationwide/Research_Thailand.md | **No DNS** (2026-09-27) |
| C.13 discharge thresholds "2,000 / 2,500 m³/s" | research/Nationwide/Research_Thailand.md | RID thresholds from HII FEWS are **2,176 / 2,448 / 2,720** (2026-09-27) |

Unverified (⚠️) rather than refuted, because they can only be tested from a Thai IP or with access: the BMA DDS paths (`/canal/`, `/pumping/`, `/flood_warning/`, `CanalList.aspx`, a BMA IP-only flood page), Longdo Traffic, the X/Twitter stream, the "GISTDA/BMA LiDAR 1 m" dataset, and Copernicus Marine surge suitability.

---

## 4. v1 station set (to confirm at G0)

| Group | Stations (HII code where known) | Role | Feed |
|---|---|---|---|
| Upstream boundary | C.2 ค่ายจิรประวัติ, C.13 ท้ายเขื่อนเจ้าพระยา (+ Pasak S.26 ท้ายเขื่อนพระรามหก) | Routing inputs, 2–5 day lead | HII ✅ |
| Mid-river | C.3 บ้านบางพุทรา, C.35 บ้านป้อม, C.36 บ้านบางหลวงโดด, C.37 บ้านบางบาล, **C.29A Bang Sai** | Routing; users in Ayutthaya | HII ✅ / **C.29A needs RID** |
| Bangkok river | CPY014 สะพานนวลฉวี (Nonthaburi), **C.12 กรมชลประทานสามเสน**, **CPY015 สะพานกรุงเทพ**, BKC003 ปตร.คลองลัดบางยอ 1; Pak Khlong Talat / Memorial Bridge (code ⚠️ C.4 vs C.22) | River level vs flood walls; tide | HII ✅ / Memorial Bridge needs RID or BMA |
| Bangkok khlongs | **BKK008 แสนแสบ บางกะปิ**, **AIT001 อโศก (แสนแสบ)**, **BKK021 คลองลาดพร้าว วัดบางบัว**, BKK001/BKK020 (คลองหกวา / ลาดพร้าว), BKK002 เปรมประชากร หลักหก, BKK003 มหาสวัสดิ์, BKK005 ภาษีเจริญ, BKK009 ลำปลาทิว ลาดกระบัง; plus BMA DDS stations once accessible | Rain-driven flooding | HII ✅ / BMA 🔴 |
| Tide | Fort Phra Chulachomklao, Bangkok Bar | Downstream boundary | Navy 🔴 → own fit on CPY015/BKC003 as interim |

**Action (Phase 0):** pull `waterlevel_load` and `queryStation`, filter to the provinces กรุงเทพฯ, นนทบุรี, ปทุมธานี, สมุทรปราการ, อยุธยา, อ่างทอง, สิงห์บุรี, ชัยนาท, นครสวรรค์ (the 26 Sep probe found 9, 2, 4, 4, 22, 4, 6, 5 and 13 stations respectively), and build the curated `station` table with chainage and upstream/downstream links ([APPROACH §2](APPROACH_AND_METHODS.md)).

---

## 5. Collection schedule (proposal, to confirm at G0)

| Source | Interval | Notes |
|---|---|---|
| HII `waterlevel_load` | 10 min | Archive raw JSON; ~1.4 MB per call → ~200 MB/day uncompressed, far less gzipped |
| HII `rain_24h` | 10–15 min | Large; use compression and a timeout ≥ 120 s |
| HII `waterlevel_graph` | Every 6 h (3 days) | **Done 2026-09-26:** a one-time 365-day backfill per focus station with a numeric id (D-018) |
| HII chart XHR `getGraphFirst` | Every 6 h per station | 30 days of 10-min data per call. **`POST /getGraph` returns only the latest point** (form has no date range; tested 2026-09-26), so it gives no extra history. Known-500 codes are retried once a day |
| Open-Meteo forecast + ensemble | Hourly | Store **every issued run** (issue time + valid time) |
| Open-Meteo Flood | Daily | Key river points; backfill 1984→ |
| RID pages and PDFs | 2× daily | Store as operation events |
| BMA DDS | 10–15 min | Only from a Thai IP and once permitted |
| Traffy public | 10–15 min | Store `ticket_id`, coordinates, time, state and a category flag only (no photos or text in the public UI) |
| GISTDA / GFM | Daily | Once keys or accounts exist |
| Navy tide | Yearly | Once the new PDF URL is found; else our own harmonic fit |
| TMD | Hourly / 3-hourly | Once registered |

## 6. Units, datums, time
| Item | Convention |
|---|---|
| Water level | m MSL (ม.รทก., Ko Lak 1915). Keep the raw value and any gauge-zero value too |
| Tide tables | LLW → MSL per station; **offset TBD** (KI-201) |
| DEM | EGM2008 → Ko Lak MSL with a local offset (KI-202) |
| Discharge | m³/s (ลบ.ม./วินาที) |
| Rain | mm |
| Time | HII `waterlevel_datetime` is local time without a timezone → parse as +07:00. The HII chart epoch is true UTC. Traffy `timestamp` is UTC. Open-Meteo returns what you request (`timezone=`). **Store UTC** (KI-205) |
| Thai dates | Press releases and PDFs use the Buddhist era (2569 = 2026) |
| Coordinates | WGS84 (EPSG:4326) for storage; UTM 47N (EPSG:32647) for distances and areas. Traffy gives `[lon, lat]` |

## 7. Access, keys, permissions, CORS
- **v1 needs no keys**: HII, Open-Meteo, Traffy public, RID pages, data.go.th ([D-001](plan/DECISIONS.md)).
- **Free registrations**: TMD (uid/ukey) and GISTDA. Register early, because approval can take days. Copernicus GFM and NASA Earthdata need free accounts.
- **Permission to redistribute**: email HII and BMA DDS, and ask BMA/NECTEC about Traffy data, before going public ([OPEN_QUESTIONS](plan/OPEN_QUESTIONS.md)).
- **CORS (probed):** HII `api-v3` echoes the requesting Origin; Traffy and Open-Meteo send `*`; the `tiwrm` chart XHR has no CORS. Browsers *could* call some sources directly, but **the browser only calls our API** ([D-001](plan/DECISIONS.md)): our archive is the system of record, and our caching protects HII under load.
- **Attribution**: every screen credits the sources it uses (HII/สสน., RID, BMA, TMD, Navy, GISTDA, Traffy Fondue, Open-Meteo/Copernicus GloFAS).
