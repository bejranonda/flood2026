> **Research snapshot, 26 Sep 2026 (historical record, not maintained).** Trust level: 🟢 careful research. It uses a verification legend and cites sources, but **no endpoint has been tested from the production VPS yet**.
> The maintained source registry is [docs/SOURCES.md](../docs/SOURCES.md). Index of all research files: [research/README.md](README.md).

# SOURCES.md — Data Sources for the Bangkok / Central Thailand Water Level Forecasting App

> Research date: 26 Sep 2026 (during the ongoing Bangkok flood event)
> Purpose: reference for developers (human or AI agent) implementing data collectors, the raw archive and the forecasting pipeline.
> Master Documentation: See [README.md](../README.md), [docs/KNOWLEDGE.md](../docs/KNOWLEDGE.md), and [docs/KNOWN_ISSUES.md](../docs/KNOWN_ISSUES.md).

**Verification legend**

| Mark | Meaning |
|---|---|
| ✅ | Endpoint / format confirmed from documentation or working open-source code |
| 🟡 | Source confirmed to exist and publish the data; exact machine endpoint still to be captured (inspect browser network calls) |
| 🔴 | No public machine access found; requires registration, agreement, or scraping PDFs/images |
| 🔑 | Needs API key / registration |

All endpoints must be re-tested **from the production VPS** before building on them. Several Thai government hosts may throttle or block foreign/datacenter IPs. (During this research, `api-v3.thaiwater.net` returned HTTP 403 from our sandbox, which runs behind an egress proxy that only allows a whitelist of domains, so that result says nothing about HII's own access policy.)

---

## 1. Key findings (read first)

1. **HII ThaiWater (สสน.) is the backbone.** It aggregates telemetry from HII, RID, BMA, DWR and others, with bank levels (ระดับตลิ่ง) in m MSL. Its public JSON API (`api-v3.thaiwater.net/api/v1/thaiwater30/public/...`) is already used by open-source projects, so endpoints and field names are known (Section 3.1).
2. **Two different flood mechanisms are active right now, and they need different models.**
   - **Bangkok (esp. east side)**: rain-driven khlong flooding. On 25 Sep 2026 the Chao Phraya at Pak Khlong Talat was only ~0.88 m MSL against a 3.0 m wall, while eastern khlongs (Prawet Burirom, Saen Saep etc.) were at critical levels after up to 99 mm/24 h (Min Buri) and 154 mm/24 h (Khlong Sam Wa). BMA declared Nong Chok, Suan Luang and Khan Na Yao disaster zones; DDPM sent a Cell Broadcast on 26 Sep. → **Model = local rainfall + khlong levels + pumping/gate operations.**
   - **Ayutthaya / Pathum Thani / Nonthaburi and river-side Bangkok**: upstream flood wave. On 23 Sep, C.2 Nakhon Sawan carried 1,737 m³/s and C.13 Chao Phraya Dam 1,620 m³/s; RID announced raising dam release to ≤ 2,000 m³/s, with downstream levels rising 0.70–1.20 m outside dikes (Sena, Phak Hai, Bang Ban, Ayutthaya, Bang Pa-in, Bang Sai, Noi river). → **Model = upstream routing (C.2 → C.13 → C.3 → C.35 → Bang Sai → Bangkok) + tide.**
3. **BKK008 (user's example) = คลองแสนแสบ บางกะปิ** — a khlong station, i.e. exactly the rain-driven case above.
4. **Tide matters for everything below Bang Sai.** Royal Thai Navy publishes hourly harmonic predictions (112 constituents) for Chao Phraya stations; 2026 tables exist as PDF.
5. **HII's official exchange-standard API only guarantees 7 days of history** → start our own archive and backfill **immediately**.
6. **Zero-Key Architecture (V1):** The system operates keyless using Open-Meteo, client-side astronomical tide harmonics ($M_2, S_2, K_1, O_1$), local static hotspot elevation benchmarks, and public reverse-engineered endpoints. Detailed keyless recipes and free registration portals are in [API_noKey-1.md](API_noKey-1.md) (🟠 mixed validity, see [VALIDATION_2026-09-26.md](VALIDATION_2026-09-26.md)) and [keyless_access.md](keyless_access.md).

---

## 2. Source priority matrix

| Priority | Source | Data | Access | Status | Use in app |
|---|---|---|---|---|---|
| **P1** | HII ThaiWater public API | Water level (all agencies), bank level, rain 1h/24h, station metadata, history graph | JSON, no key | ✅ | Real-time map, station charts, model inputs |
| **P1** | Open-Meteo Forecast / Ensemble | Hourly rain forecast (ECMWF, GFS, ICON…), ensembles | JSON, no key (non-commercial) | ✅ | Rainfall forcing, uncertainty |
| **P1** | Open-Meteo Flood API (GloFAS v4) | Simulated daily river discharge 1984→present + forecast | JSON, no key | ✅ | Upstream discharge prior, long-range outlook |
| **P1** | Royal Thai Navy Hydrographic Dept | Hourly astronomical tide predictions 2026 | PDF | 🔴 (PDF parse) | Tide component for Bangkok stations |
| **P1** | RID (กรมชลประทาน) | C.2, C.13, C.3, C.35 levels & discharge; dam releases; daily basin situation PDF | Web/PDF; telemetry portal TBD | 🟡 | Upstream boundary for routing model |
| **P2** | BMA DDS (สำนักการระบายน้ำ) | Khlong/river levels, rain gauges, 3-h rain nowcast, radar | Web; data.go.th CSV | 🟡 | Bangkok khlong detail, nowcasting |
| **P2** | TMD (กรมอุตุฯ) | Obs (3-h, daily), forecasts, AWS; WRF NWP | TMD API 🔑; WIS2 | 🟡🔑 | Obs validation, Thai NWP forcing |
| **P2** | GISTDA API Gateway | Daily satellite flood extent, 2011–2023 flood recurrence | REST 🔑 | ✅🔑 | "Is my area flooded" layer, validation |
| **P3** | Traffy Fondue (BMA) | Citizen flood reports (500 m radius view, 6-h update) | No documented API | 🔴 | Ground-truth/validation (if permitted) |
| **P3** | Google Flood Hub | Riverine flood forecasts | Web; API by application | 🔴 | Cross-check only |
| **P3** | DEMs (FABDEM, Copernicus GLO-30, GEDTM30) | Ground elevation | GeoTIFF/COG | ✅ | Estimate depth at user location |
| **P3** | DWR / CCTV feeds | River cameras | Images | 🟡 | Visual confirmation (optional) |

---

## 3. Source details

### 3.1 HII ThaiWater — สถาบันสารสนเทศทรัพยากรน้ำ (องค์การมหาชน) ✅

**Human-facing pages (given by user)**
- Station warning map: `https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/warning`
- Station chart: `https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/chart/BKK008` (คลองแสนแสบ บางกะปิ), `.../BKK021`
- These pages render client-side; the data comes from JSON XHR calls. **Action:** open DevTools → Network on these pages and record the exact calls; they are expected to hit the same API family as below.
- Also: `https://www.thaiwater.net/water/wl` (national WL list with bank level, capacity, history), daily report `https://tiwrm.hii.or.th/v3/dailyreport`.

**Public JSON API (confirmed from working open-source code, `github.com/suralism/water-system`, file `src/thaiwater.ts`)**

| Purpose | Endpoint | Notes |
|---|---|---|
| Latest water level, all stations | `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load` | Response list at `waterlevel_data.data[]` |
| Latest rainfall, all stations | `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h` | Response list at `data[]` |
| Station history (graph) | `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_graph?station_type=tele_waterlevel&station_id={id}&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD%20HH:mm` | Points at `data.graph_data[]` |

**Key fields (water level)**

| Field | Meaning |
|---|---|
| `station.id` | Numeric internal ID (used by `waterlevel_graph`) |
| `station.tele_station_oldcode` | Human code, e.g. `BKK008`; RID stations prefixed `ridhydro_` |
| `station.tele_station_name.th/.en` | Name |
| `station.tele_station_lat/long` | Coordinates (filter out 0,0) |
| `station.min_bank` | **Bank level, m MSL** (ระดับตลิ่ง) — the red line on the chart |
| `waterlevel_msl` | Water level, m MSL (ม.รทก.) |
| `waterlevel_m` | Level relative to local gauge zero |
| `situation_level` | HII status class |
| `storage_percent` | % of channel capacity |
| `waterlevel_datetime` | Local time **without timezone** → treat as `+07:00` |
| `geocode.province_code / amphoe_name / tumbon_name`, `basin.basin_name`, `agency.*` | Location & owner agency |

Graph points: `datetime`, `value` (= level MSL), `waterlevel_m`/`value_out`, `discharge`, `situation_level`.
Rain: `rain_1h`, `rain_24h`, `rainfall_datetime`.

**Gotchas learned from the open-source implementation**
- In `end_date`, encode the space as `%20` (not `+`).
- Same physical station can appear several times (different agencies/IDs within ~100 m) → de-duplicate by ID, distance < 100 m + name/code match; prefer the record with bank level + latest timestamp.
- Map user-facing `oldcode` (BKK008) ↔ numeric `station.id` in a station table.
- Send a descriptive `User-Agent`; cache and use single-flight requests. The reference project polls every 5 min.

**Official exchange standard (for a formal data agreement later)**
- HII publishes a national water data exchange standard with REST APIs for rainfall, water level/discharge (`WaterLevel`, `Discharge` with `qualityFlag`, `qualityControlLevel`), reservoirs, water quality and station info, plus CSV/FTP formats: `https://standard.thaiwater.net/`
- The standard's API service guarantees **7 days of history** — another reason to archive ourselves.
- Contact: info_thaiwater@hii.or.th, 02-158-0901. **Recommended:** request official access/permission for public redistribution.

### 3.2 Royal Irrigation Department (RID) — กรมชลประทาน 🟡

**Why:** upstream boundary conditions and dam operations drive the river flood 2–5 days ahead.

**Key stations (Chao Phraya main stem, upstream → downstream)**

| Code | Location | Bank level (m MSL) | Channel capacity (m³/s) |
|---|---|---|---|
| C.2 | Mueang Nakhon Sawan | 26.20 | 3,590 |
| C.13 | Chao Phraya Dam, Sapphaya, Chai Nat | 17.21* | 2,840 |
| C.3 | Mueang Sing Buri | 11.70 | 2,340 |
| C.35 | Phra Nakhon Si Ayutthaya | 4.58 | 1,155 |
| C.36 / C.37 | Khlong Bang Luang / Khlong Bang Ban, Bang Ban | 4.00 / 3.80 | 404 / 134 |
| (Bang Sai) | Discharge "passing Bangkok" quoted by BMA | – | – |

*Values from DWR daily reports (2017–2019); C.13 also appears as 15.77 in one report (likely a different reference point) — **verify against current RID/HII station metadata.**

**Access**
- Most RID telemetry stations are already mirrored in HII ThaiWater (oldcode prefix `ridhydro_`) → **use HII first**.
- Daily Chao Phraya basin situation PDF (dam releases, gate operations, % capacity), e.g. `https://water.rid.go.th/flood/news/สถานการณ์ลุ่มน้ำเจ้าพระยา (4 ก.ย.69) .pdf` → parse daily (PDF → text/tables).
- RID press releases give dam release plans (e.g. 23 Sep 2026: C.13 release to ≤ 2,000 m³/s) → store as "planned boundary condition" events.
- 🟡 **To do:** locate RID hydrology telemetry web service (hourly C-station data, dam release time series) and large-reservoir data (Bhumibol, Sirikit, Khwae Noi, Pasak Jolasid).

### 3.3 BMA — Department of Drainage and Sewerage (สำนักการระบายน้ำ กทม.) 🟡

- Portal: `https://dds.bangkok.go.th/` — khlong and river levels, rain gauges, 3-hour rain nowcast (updated hourly).
- Radar: Nong Chok `https://weather.bangkok.go.th/Radar/RadarAnimation.aspx`, Nong Khaem `https://weather.bangkok.go.th/Radar/RadarAnimationNk.aspx`.
- Historical: daily max Chao Phraya level at Pak Khlong Talat (CSV, CC-BY) on data.go.th: `https://dev.data.go.th/en/dataset/wl-max-chaophraya-river`.
- Known thresholds (BMA public reports):

| Station | Flood wall (m MSL) | Warning level (m MSL) |
|---|---|---|
| ปากคลองตลาด (Pak Khlong Talat) | 3.0 | 2.8 |
| คลองบางเขนใหม่ | 3.5 | 3.3 |
| East-side gates (e.g. ปตร.คลองสอง สายใต้) | – | critical +1.80 (reported) |

- New (26 Sep 2026): BMA published a road-flooding status website for the public; link circulated in news as a claude.ai artifact URL (`https://claude.ai/artifact/N6umcENfSgoY6GMkhVKwZs`). Check whether it exposes reusable data.
- 🟡 **To do:** capture DDS JSON endpoints via DevTools; confirm which BMA khlong stations are already in HII (likely many BKKxxx codes).
- Hotline for users: 199 / 02-248-5115; Facebook "ศูนย์ป้องกันน้ำท่วม กรุงเทพมหานคร".

### 3.4 Tide — Hydrographic Department, Royal Thai Navy (กรมอุทกศาสตร์) 🔴 (PDF)

- 2026 tide tables (PDF): `https://www.hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf`
- Hourly heights predicted for Chao Phraya stations incl. Phra Chunlachomklao Fort (Samut Prakan), Bangkok Bar, Bangkok Port, Hydrographic Dept (Navy HQ, Bangkok); harmonic method, 112 constituents.
- ⚠️ Folder `LLW` → heights likely referenced to **Lowest Low Water**, not MSL. Determine per-station LLW→MSL offset (check the same site for an MSL version).
- Thai vertical datum: **Ko Lak 1915 MSL** (= ม.รทก.).
- **Plan:** parse PDF once per year into `tide_prediction(station, ts, height_llw, height_msl)`. Fallback: fit own harmonic model (`utide`) on archived HII river-mouth station data.
- Surge/ONWR high-tide warnings (น้ำทะเลหนุนสูง, e.g. 13–24 Oct 2024) → store as event flags.

### 3.5 Weather forecasts

**Open-Meteo** ✅ (no key, non-commercial free tier; commercial plan if needed)
- Forecast API: hourly precipitation from ECMWF IFS, GFS, ICON, etc. Use `past_days` to archive issued forecasts.
- Ensemble API: member-level precipitation for probabilistic forcing.
- **Global Flood API** (`https://open-meteo.com/en/docs/flood-api`): GloFAS v4 simulated river discharge, 5 km, **1984 → present**, forecasts 7 days default / up to 16 days, seasonal up to ~7 months; ensemble spread. ⚠️ At 5 km the nearest river may be wrong — nudge coordinates ±0.1° to snap onto the Chao Phraya/Pasak/Tha Chin channel and calibrate against C.2/C.13.

**Thai Meteorological Department (TMD)** 🟡🔑
- TMD API (registration): `https://data.tmd.go.th/api/index1.php` — 3-hourly & daily obs, daily/weekly forecasts, climate stats, AWS obs.
- WIS2: hourly SYNOP observations for Thailand (`urn:wmo:md:th-tmd:synop-hourly`).
- NWP: TMD runs WRF (2 km/48 h hourly short-range; 6 km/72 h; 18 km/10 days) — portal `https://hpc.tmd.go.th/`. 🟡 Machine access to gridded NWP output not confirmed.
- Warnings: heavy-rain warnings (e.g. 24–27 Sep 2026) → store as event flags.

### 3.6 Satellite flood extent — GISTDA ✅🔑

- API key: register at `https://api-gateway.gistda.or.th/v2`
- Daily flood extent by point:
  `https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.0/disasters/flood-extent-1day?lat={lat}&lon={lon}&api_key={KEY}`
- Flood recurrence 2011–2023 (point or GeoJSON geometry query) — good static "risk" layer.
- Public viewers: `https://disaster.gistda.or.th`, `http://flood.gistda.or.th/`
- License: Open Data Common (per opendata.gistda.or.th). Latency depends on satellite passes (Sentinel-1, COSMO-SkyMed…) → validation, not real-time.

### 3.7 Citizen reports — Traffy Fondue 🔴
- Has a flood feature showing reports within 500 m, updated every 6 h. No documented public API found → contact BMA/NECTEC for data access. Use only for validation, never as a sole source.

### 3.8 Elevation (for "near my house" depth estimate) ✅
- FABDEM / Copernicus GLO-30 (30 m); GEDTM30 v1.2 COG (OpenGeoHub) — see `github.com/gain9999/dtm` for a client-side COG streaming example that also includes a Thai water-level station explorer.
- ⚠️ Vertical error of global DEMs in flat, built-up Bangkok is often ≥ 1 m — show only as an estimate with uncertainty; prefer local survey/LiDAR if obtainable (BMA, RTSD).

### 3.9 Other (optional)
- Google Flood Hub — cross-check for riverine forecasts; API is by application.
- DWR river CCTV (e.g. `http://mekhala.dwr.go.th/cctv/cctv-basin.php?txtbasin=10`) — visual confirmation.
- DWR/ONWR daily situation PDFs (`dwr.go.th/uploads/file/statuswater/...`) — historical daily station tables back to ~2012, useful for backfilling C-stations.

---

## 4. Station set for v1

| Group | Stations | Role |
|---|---|---|
| Upstream boundary | C.2, C.13 (+ Pasak Jolasid release, Noi/Tha Chin diversions) | Routing inputs, 2–5 day lead |
| Mid-river | C.3, C.35, C.36, C.37, Bang Sai | Routing, Ayutthaya users |
| Bangkok river | Pak Khlong Talat, Khlong Bang Khen Mai, Bang Na (+ HII BKK river stations) | River level vs walls |
| Bangkok khlongs | BKK008 (Saen Saep, Bang Kapi), BKK021, Prawet Burirom, Lat Phrao, Prem Prachakorn, east-side gates | Rain-driven flooding |
| Tide | Phra Chunlachomklao Fort, Bangkok Bar | Downstream boundary |

**Action:** pull the full HII station list, filter provinces กรุงเทพฯ, นนทบุรี, ปทุมธานี, สมุทรปราการ, อยุธยา, อ่างทอง, สิงห์บุรี, ชัยนาท, นครสวรรค์, and store a curated `stations` table with upstream/downstream links.

---

## 5. Units, datums, time

| Item | Convention |
|---|---|
| Water level | m MSL (ม.รทก., Ko Lak 1915). Also keep `waterlevel_m` (gauge-zero) raw |
| Tide tables | LLW → convert to MSL per station (offset TBD) |
| Discharge | m³/s (ลบ.ม./วินาที) |
| Rain | mm |
| Time | Sources give local time without TZ → parse as Asia/Bangkok (+07:00), store UTC |
| Thai dates | Press/PDF use Buddhist Era (2569 = 2026) |

---

## 6. Collection schedule (proposal)

| Source | Interval | Notes |
|---|---|---|
| HII `waterlevel_load` | 10 min | All stations; archive raw JSON |
| HII `rain_24h` | 10 min | |
| HII `waterlevel_graph` | Daily per station + on-demand | Backfill: loop station × 30-day windows as far back as available |
| Open-Meteo forecast + ensemble | Hourly (per model run) | Store every issued run |
| Open-Meteo Flood API | Daily | Key river points; also backfill 1984→ |
| RID PDFs / press | 2× daily | Parse; store releases as events |
| BMA DDS | 10–15 min | After endpoints captured |
| GISTDA flood extent | Daily | Grid of points or AOI polygons |
| Navy tide tables | Yearly | Parse PDF |
| TMD obs | Hourly / 3-hourly | After registration |

All raw payloads → immutable archive (gzip + hash) → normalised TimescaleDB, as specified in the build prompt.

---

## 7. Open questions / next actions

1. Capture exact XHR endpoints on `tiwrm.hii.or.th` chart pages (BKK008, BKK021) and on `dds.bangkok.go.th`.
2. Test all endpoints from the Singapore/Thailand VPS (IP blocking, rate limits).
3. Determine how far back `waterlevel_graph` serves history; start backfill today.
4. Find RID hourly telemetry service and dam-release time series.
5. Get LLW→MSL offsets for Navy tide stations.
6. Register: TMD API, GISTDA API Gateway.
7. Email HII (info_thaiwater@hii.or.th) and BMA DDS for permission to redistribute and, ideally, an official feed.
8. Confirm C.13 bank level discrepancy (17.21 vs 15.77).

---

## 8. Legal / ethics

- Attribute every source in the UI (HII/สสน., RID, BMA, TMD, Navy, GISTDA, Open-Meteo/Copernicus GloFAS).
- Respect ToS/robots.txt; cache aggressively; no aggressive polling during peak events (their servers are under load too).
- Open-Meteo free tier is non-commercial — switch to a paid plan if the app is monetised.
- The app must link to official warnings (BMA, ปภ. 1784, HII, RID) and state that forecasts are estimates.
