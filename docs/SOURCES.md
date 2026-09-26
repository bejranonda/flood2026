# SOURCES.md — Data Source Registry (Phase 0 deliverable)

> **Project:** BKK FloodWatch 2026. Water-level monitoring and forecasting for Bangkok and the lower Chao Phraya.
> **Status:** 🟡 **Desk research plus a first live probe (2026-09-26, from a dev host in Germany).** Testing from the **production VPS** (Phase 0) has not started.
> **Last updated:** 2026-09-26
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
| **P1** | HII chart site (`tiwrm.hii.or.th`): `queryStation` (its `water1` has no timestamp and was frozen for GLF001, so not ingested), `getGraphFirst`, `POST /getGraph` (latest point only), map feed | **+162 stations not in `waterlevel_load`**; ~30 days of 10-min history per station (HTTP 500 for ~56 codes); coordinates only in the map feed (107 stations) | JSON | none | ✅ live / 🟡 partial | Backfill, charts, tide fitting, station coverage ([KI-207](KNOWN_ISSUES.md)) |
| **P1** | Open-Meteo Forecast + Ensemble | Hourly rain (ECMWF, GFS, ICON…), ensemble members | JSON | none (non-commercial) | ✅ live | Rain forcing, uncertainty |
| **P1** | Open-Meteo Flood API (GloFAS v4) | Daily discharge 1984→, forecast ≤16 d | JSON | none (non-commercial) | ✅ live | Upstream prior, backfill |
| **P1** | RID (กรมชลประทาน) | C-stations (partly in HII, **but not C.29A**), dam releases, diversions | Web/PDF | none | 🟡 portals reachable | Upstream boundary, Bang Sai |
| **P1** | Navy Hydrographic Dept. (กรมอุทกศาสตร์) | Hourly astronomical tide predictions | PDF | none | 🔴 **URL now 404 + bot challenge** | Tide component, fallback to own fit |
| **P2** | BMA DDS (สำนักการระบายน้ำ) | Khlong and river levels, rain gauges, 3 h nowcast, radar, flow and pump stations | Web pages | none | 🟡 `dds.` opens via the Thai VPN egress; **`weather.bangkok.go.th` returns 403 even from Thailand (IP class)** | Bangkok khlongs (**not mirrored in HII**) |
| **P2** | Traffy Fondue public API | Citizen flood reports with coordinates, text, photos, state | JSON (undocumented) | none | ✅ live | Validation and "reported nearby" layer (privacy rules, KI-107) |
| **P2** | TMD (กรมอุตุนิยมวิทยา) | Observations, forecasts, AWS | REST | 🔑 free | 🟡 portal reachable | Observation validation |
| **P2** | GISTDA API Gateway | Daily satellite flood extent, 2011–2023 recurrence | REST | 🔑 free | 🟡 portal reachable | Flood extent layer, validation |
| **P2** | Copernicus GFM | Sentinel-1 flood masks | REST | free account | ✅ live (Swagger) | Fallback for GISTDA |
| **P3** | DEMs (FABDEM, Copernicus GLO-30, GEDTM30); Open-Meteo elevation | Ground elevation | COG / JSON | none | ✅ live (Open-Meteo) | **Probabilistic** depth only (KI-202) |
| **P3** | DWR EWS, DWR/ONWR PDFs, CCTV | Tributary telemetry, historical tables | Web/PDF | none | 🟡 `ews.dwr.go.th` timed out from Germany; **200 through the Thai egress** (content not yet explored) | Backfill C-stations |
| **P3** | Google Flood Hub, NASA GPM IMERG | Forecast cross-check; satellite rain | Web / files | application / Earthdata | ⚠️ | Cross-check, upstream rain |

---

## 2. Registry (the brief's Phase 0 format)

"Probe" is the 2026-09-26 result from the dev host in Germany. The VPS column is still pending for every row.

| Source | Data type | Coverage | Access method | Endpoint(s) | Probe | Update interval | Latency / size | Auth | Datum & units | License / ToS | Reliability notes | VPS-tested |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HII `waterlevel_load` | Latest WL all stations | 805 stations nationwide (HII 330, RID 315, FOP 89, EGAT 71; **no BMA-agency rows**) | JSON | `GET https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load` → `waterlevel_data.data[]` | ✅ 200 | 10 min (HII); RID rows hourly (12:00) | ~9 s, 1.4 MB | none | `waterlevel_msl` m MSL; `station.min_bank` bank m MSL; `discharge` m³/s; `waterlevel_datetime` **local, no TZ** | Not formally public. **Ask HII** (info_thaiwater@hii.or.th, 02-158-0901) | Some stations stale (e.g. BKC004 since 24 Sep); BKK008 absent although the chart API has it | not yet |
| HII `rain_24h` | Latest rain | National gauges | JSON | `GET …/thaiwater30/public/rain_24h` → `data[]` | ✅ 200 | 10 min | **>60 s, several MB** from Germany | none | `rain_1h`, `rain_24h` mm | as above | Needs compression and long timeouts; never fetch per user request | not yet |
| HII `waterlevel_graph` | Station history (API) | Per numeric `station.id` | JSON | `GET …/public/waterlevel_graph?station_type=tele_waterlevel&station_id={id}&start_date=…&end_date=…%20HH:mm` | ✅ 200 (2026-09-26) | hourly | ~2–5 s for a year | none | `value` m MSL, `discharge` | as above | **Serves at most 365 days**: C.12 (id 2599) from 2025-09-01 returned 8,777 points starting 2025-09-26; 2026-01-01 → 6,449; 2026-06-01 → 2,825 (≈ 75 % non-null). Used for the one-time 1-year backfill (D-018) | ✅ this host |
| **HII chart XHR** | 10-min WL history | Per `oldcode` (BKK008, CPY015, …) | JSON behind the chart page | `GET https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}` → `[[epoch_ms_UTC, level_msl, bank, ground, "level"], …]` (~30 days); `POST …/getGraph` (form + CSRF `_token`) for ranges; `…/queryStation` | ✅ 200 | 10 min | ~2 s, 170 KB | none | m MSL; epoch is **true UTC** | as above | **`999999` = missing sentinel** (KI-206). No CORS headers | not yet |
| RID C-stations via HII | WL + discharge | C.2 (1,824 m³/s), C.13 (1,912), C.3 (1,946), C.35 (1,156), C.36, C.37, S.26 Pasak (470) at 26 Sep 12:00 | via HII | `ridhydro_*` rows in `waterlevel_load` | ✅ 200 | hourly | – | none | m MSL, m³/s | – | **C.29A (Bang Sai), C.4/C.22 (Memorial Bridge), Fort Chula are not in HII** → need RID or Navy feeds | not yet |
| RID portals | Situation, releases, diversions | Chao Phraya basin | HTML / PDF | `https://water.rid.go.th/flood/`, `http://wmsc.rid.go.th/`; station list `http://water.rid.go.th/hyd/rainmean/st-list.htm` | ✅ 200 (pages) | daily | – | none | m³/s; Buddhist-era dates | – | Machine-readable data inside still to be found | not yet |
| BMA DDS | Khlong/river WL, rain, flow and pump stations | Bangkok | Web pages | `https://dds.bangkok.go.th/`, `http://weather.bangkok.go.th/water/…`, `…/StationDetailFlow?id=` | 🔴 **connection reset from Germany**; `www.bangkok.go.th` 403 | 10–15 min | – | none | Datum per station TBD (KI-201) | ask BMA | Must be tested from a Thai IP; capture the XHR calls there | not yet |
| Navy tide tables | Hourly astronomical tide | Fort Phra Chulachomklao, Bangkok Bar, Bangkok Port, Navy HQ | PDF | old: `…/download/Water_lever69/LLW/TT2026.pdf` → **404**; site behind a Cloudflare challenge | 🔴 | yearly | – | none | **LLW (ม.ตลน.)**, offsets TBD | check | Find the new URL by hand; fall back to our own harmonic fit (APPROACH §5) | not yet |
| Open-Meteo Forecast | Hourly rain, wind, pressure | Point | JSON | `https://api.open-meteo.com/v1/forecast` | ✅ 200, CORS `*` | hourly | <0.2 s | none | mm, hPa, m/s | **Non-commercial free tier** (KI-106) | Store every issued run | not yet |
| Open-Meteo Ensemble | Member rain | Point | JSON | `https://ensemble-api.open-meteo.com/v1/ensemble` | ✅ 200 | per run | <0.2 s | none | mm | as above | – | not yet |
| Open-Meteo Flood (GloFAS v4) | Daily discharge | 5 km grid | JSON | `https://flood-api.open-meteo.com/v1/flood` | ✅ 200 | daily | <0.2 s | none | m³/s | as above | Snap onto the channel; calibrate against C.2/C.13 | not yet |
| Open-Meteo Elevation | Point elevation (90 m DEM) | Global | JSON | `https://api.open-meteo.com/v1/elevation` | ✅ 200 | static | <0.1 s | none | m (EGM2008) | as above | Gave 4 m and 7 m where the true value is about 0–2 m MSL. **Not for depth** | n/a |
| Traffy Fondue public | Citizen reports | Bangkok (+ other orgs) | JSON (undocumented) | `GET https://publicapi.traffy.in.th/share/teamchadchart/search?limit=…` → `results[]` (`coords` [lon, lat], `description`, `photo_url`, `timestamp` UTC, `state`) | ✅ 201, CORS `*` | near real time | <1 s | none | WGS84 | Citizen personal data: **aggregate only, don't republish photos or text**; ask BMA/NECTEC | Report time ≠ flood time | not yet |
| TMD API | Observations, forecasts | Thailand | REST | `https://data.tmd.go.th/api/…` (uid/ukey) | 🟡 portal 200 | 3 h / daily | – | 🔑 | mm, °C | TMD terms | Register now | not yet |
| GISTDA flood extent | Daily extent, recurrence | Thailand | REST | `https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.0/disasters/flood-extent-1day?lat=&lon=&api_key=` | 🟡 portal 200 | daily | days | 🔑 | – | Open Data Common | Use for validation | not yet |
| Copernicus GFM | Sentinel-1 flood masks | AOIs | REST | `https://api.gfm.eodc.eu/v2/` | ✅ 200 | per pass | days | free account | – | Copernicus open | – | not yet |
| data.go.th (BMA) | Daily max at Pak Khlong Talat | 1 station | CSV (CC-BY) | `https://dev.data.go.th/en/dataset/wl-max-chaophraya-river` | ✅ 200 (page) | daily | – | none | m MSL | CC-BY | Backfill | not yet |
| DEM files | Elevation | Global 30 m | COG | FABDEM, Copernicus GLO-30, GEDTM30 | ✅ doc | static | – | none | **EGM2008 → Ko Lak offset** | FABDEM is non-commercial | RMSE ≥ 1 m in Bangkok | n/a |

---

### 2b. Thai egress probe (2026-09-26 08:30 UTC, exit 49.48.220.198, Ayutthaya TH, via [D-016](plan/DECISIONS.md))
| URL | From Germany | Via Thai egress |
|---|---|---|
| `https://ews.dwr.go.th/` | timeout | **200** (348 B, to explore) |
| `https://hydro.navy.mi.th/` | 403 bot challenge | **200** |
| `…/download/Water_lever69/LLW/TT2026.pdf` | 404 | **404** (URL moved, not blocked) |
| `https://dds.bangkok.go.th/` | connection reset | **redirect → 200** (news page) |
| `https://weather.bangkok.go.th/` (+ `StationDetailFlow`) | reset / 403 | **403 IIS "Access is denied"**; a browser UA doesn't change it → IP-class block |
| `https://tiwrm.hii.or.th/` | 200 | 200 |

## 3. Refuted endpoints — do **not** use

| Endpoint / claim | From | Evidence (2026-09-26) |
|---|---|---|
| `https://api-v3.thaiwater.net/v1/telemetry/station/river` + `x-api-key`; fields `river_water_level_msl`, `tele_station_code` | bangkok_flood_intelligence_data_sources.md | **HTTP 404** |
| `https://api2.thaiwater.net/v1/analyst/water/telemetry`, codes `C.29`, `BKK01` | API_noKey-1.md | **The host does not resolve in DNS**; the codes don't match HII (`BKK001`…) |
| `https://open.traffy.in.th/api/v1/tickets?type=flooding` | bangkok_flood_intelligence_data_sources.md | **The host does not resolve in DNS**. Use `publicapi.traffy.in.th` (above) |
| `https://weather.tmd.go.th/svpLoop.php` | same | **HTTP 404** |
| `https://www.hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf` | sources_survey.md | 301 → **404** |
| `THAIWATER_API_KEY` for the public API | old `.env.example` | The public endpoints work without a key |

Unverified (⚠️) rather than refuted, because they can only be tested from a Thai IP or with access: the BMA DDS paths (`/canal/`, `/pumping/`, `/flood_warning/`, `CanalList.aspx`, `203.155.220.119/flood/`), `ews.dwr.go.th`, Longdo Traffic, the X/Twitter stream, the "GISTDA/BMA LiDAR 1 m" dataset, and Copernicus Marine surge suitability.

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
