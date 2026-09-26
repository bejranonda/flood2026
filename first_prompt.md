# Water level forecasting for Bangkok flood 2026
Now Bangkok is under flood, I like to build a we app to call the data of water level from many stations in Bangkok, and together the weather forecaste
- show water level in real-time
- show trend for next 12 hr , 1, 2 , 3 day, week
- forcasting by calculation using tools ans models with weather forcast, based scientific modern research and statistic
## UI
Make the UI in in Thai.
## Area
Thailand
Focus on Bangkok and central of Thailand.
## Users
Users will be Thai people who monitoring and affected by flood.
They would like to know the status,
- water will go up or lower around their house in comming future.
- when will flood recover or return to normal state
## Storage
Consider about data, the sources might not be always accessible later, please consider to store the data also in our own database.
## Deployment
We have cloudflare account and the VPS here.
During a flood event, government sites often slow down, change their internal APIs, or go offline under load, so your own archive becomes the most reliable source you have. It's also what makes the forecasting possible at all, since the models need long, clean history.

On deployment, I'd recommend a hybrid: a VPS runs the backend, with Cloudflare in front of it.

**Why not Cloudflare alone.** The core of this app is Python with scientific libraries (pandas, statsmodels, LightGBM, possibly PyTorch), a time-series database, scheduled collectors, and periodic model retraining. Cloudflare Workers are built for short, lightweight request handling. They have CPU-time limits, limited support for Python packages, and D1 (their SQLite database) isn't a good fit for years of high-frequency time series with heavy analytical queries. You could force it, but you'd spend your effort working around the platform instead of on the forecasting.

**Why a VPS for the core.** It can run the full Python stack, TimescaleDB, cron-style collectors, and training jobs without limits, and costs are predictable (roughly 4 vCPU and 8–16 GB RAM is plenty to start). Choose a region close to Thailand, such as Singapore or a Thai provider. That keeps latency to the Thai sources low. It also avoids a real risk: some Thai government sites throttle or block foreign or datacenter IP ranges. Have the agent test access from the VPS in Phase 0.

**Why still put Cloudflare in front.** When the flood peaks, traffic can jump from hundreds to hundreds of thousands of users in hours, and a single VPS won't survive that uncached. Cloudflare fixes this cheaply. Its CDN caches public pages and API responses for 1–5 minutes, which absorbs almost all the load, and it adds DDoS protection. Cloudflare Pages can host the static frontend. R2 (object storage with no egress fees) works well as an off-site archive and backup of raw data, so your history survives even if the VPS dies.

Here are the updated sections to replace Phase 1 and Phase 4 in the prompt:

````markdown
# Phase 1 — Data ingestion and own data archive
Assume every external source may become unavailable, change its format, or remove history at any
time. Our own database is the system of record; external sources are only feeds into it.

- Scheduled collectors (every 10–15 min for water level, hourly for weather/forecasts), one adapter
  per source, with retry, backoff, and alerting on failure
- Two-layer storage:
  1. Raw archive (immutable): store every fetched payload exactly as received (JSON/HTML/CSV),
     gzip-compressed, with fetch timestamp, source URL, HTTP status and content hash. Keep it
     forever. Write to local disk AND replicate to object storage (Cloudflare R2 or S3-compatible)
  2. Normalised database: PostgreSQL + TimescaleDB with one schema: station_id, source, timestamp
     (UTC stored, Asia/Bangkok displayed), level_msl, bank_level_msl, discharge, quality_flag,
     raw_ref (link back to the raw payload). Use compression and continuous aggregates
     (hourly/daily) for fast charts
- Also store weather and rainfall forecasts as issued (every forecast run, not just the latest),
  so forecasts can be backtested exactly as they would have performed in real time
- Store our own forecasts too (every run, with model version) to measure real skill over time
- Store station metadata with history (bank level, datum, location changes are versioned, not
  overwritten)
- Backfill: as early as possible, download all historical data each source currently exposes
  (especially past flood years), because it may disappear later
- Handle datum differences explicitly (MSL / ม.รทก. vs local gauge zero); document every conversion
- QC: spike detection, flatlines, gaps, clock errors; flag, don't silently delete
- The app must keep working in "degraded mode" when a source is down: show last known value,
  its age, and a clear notice (e.g. "ข้อมูลล่าสุดเมื่อ ... แหล่งข้อมูลขัดข้องชั่วคราว")
- Backups: nightly database dump to off-site object storage; weekly Parquet exports of the
  normalised data; document and test the restore procedure
- Check each source's license/ToS regarding storing and redistributing data, and attribute sources
  in the UI

# Phase 4 — Deployment: VPS core + Cloudflare edge
Architecture:
- VPS (Singapore or Thailand region, start ~4 vCPU / 8–16 GB RAM / 200 GB SSD):
  Docker Compose with PostgreSQL + TimescaleDB, collectors (scheduler), forecasting jobs,
  FastAPI backend. First verify from this VPS that all Thai sources are reachable (some may
  block foreign or datacenter IPs); if blocked, propose a Thai-hosted collector node
- Cloudflare in front:
  - DNS + proxy, TLS, DDoS protection
  - CDN caching of public API responses and pages (short TTL, 1–5 min, with stale-while-revalidate)
    so flood-peak traffic doesn't hit the VPS
  - Cloudflare Pages for the static/SSG frontend
  - R2 for the raw data archive replica and database backups
- Only the Cloudflare edge may reach the VPS web port (firewall / Cloudflare Tunnel); SSH by key only
- Monitoring: uptime checks, collector failure and stale-data alerts, disk usage, forecast skill drift
- Infrastructure documented so the whole stack can be redeployed on a new VPS from backups in
  under one hour; README with setup, data flow diagram, and how to add a new station or source
````

One more practical point: start the collectors and the historical backfill as soon as Phase 0 confirms the sources, even before the UI exists. Every day of the current flood you capture is valuable training and validation data, and it can't be recovered later if a source drops it.

## Sources
Review and deep research how to extract all possible surces.
Please find the all possible sources of data.
Here below are the additional sources, review how can we get the data.
## water level
Station map : https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/warning
Exmaple stations in Bangkok, you can see the redline, ระดับตลิ่ง (ม.รทก.) :
- https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/chart/BKK008
- https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/chart/BKK021

## Frank Suggestion
You can comment and blame me, tell me honestly, and suggest me frankly.
You can also suggestto improve my command and instruction here.
## Grillme
Ask me till you can see the clear and precise picture for improvement.
Do not continue if the all info is not clear or enough.


# Potential prompts
## Option 1
Act as a Principal Full-Stack Engineer and Disaster Informatics UX Specialist. 

Build a responsive, mobile-first Web Application titled "BKK FloodWatch: เช็กระดับน้ำแถวบ้านและระยะเวลาคืนสู่ปกติ" designed specifically for Bangkok residents experiencing or monitoring urban and riverine flooding.

### 1. Primary User Personas & Core Jobs-to-be-Done
- Target User: Bangkok residents stressed about water reaching their home, parking, or commuting route.
- Critical Need 1: "น้ำแถวบ้านฉันจะขึ้นหรือจะลงในอีก 12 ชม. / 1-3 วัน?" (Trend & Delta)
- Critical Need 2: "น้ำจะแห้ง/กลับสู่ภาวะปกติเมื่อไหร่?" (ETA to Normal / Road Clear)

### 2. Information Architecture & UX Layout (Mobile-First)

#### Header & Geo-Selector (Sticky Top)
- Large search bar: Search by District (เขต), Sub-district (แขวง), Landmark, or click "📍 ใช้ตำแหน่งปัจจุบัน (GPS)".
- Fast Quick-Picks: 10 flood-prone hotspots (e.g., บางนา-ลาซาล, อุดมสุข, รัชดาภิเษก-แยกลาดพร้าว, รามคำแหง, แจ้งวัฒนะ, พระราม 4, ปากเกร็ด, ทาวน์อินทาวน์).

#### Hero Status Card (Answers the 2 Golden Questions instantly)
Display a high-contrast status card for the selected location:
1. Current State:
   - Status Badge: [ปลอดภัย / เฝ้าระวัง / น้ำท่วมขังบนผิวถนน / วิกฤติน้ำเอ่อล้น]
   - Water Depth Estimate on Street: in centimeters (e.g., "ท่วมผิวจราจร ~15-20 ซม. (ระดับฟุตบาท รถเล็กเริ่มสัญจรลำบาก)")
2. Trend Indicator (Next 12 Hours):
   - Dynamic direction icon (Arrow Up / Steady / Arrow Down)
   - Plain Thai explanation: e.g., "📈 แนวโน้ม: น้ำจะขึ้นสูงสุดอีก 8 ซม. เวลา 14:30 น. จากอิทธิพลน้ำทะเลหนุนสูง"
3. Recovery Forecast (Time-to-Dry / เข้าสู่ภาวะปกติ):
   - ETA Countdown Clock: e.g., "⏱️ คาดการณ์น้ำลดกลับสู่สภาวะปกติ: อีก 3 ชั่วโมง 45 นาที (ประมาณ 18:30 น.)"
   - Confidence Factor & Conditions: "คำนวณจากกำลังสูบของสถานีอุโมงค์พระโขนง (สมมติฐาน: ไม่มีฝนตกหนักเพิ่ม)"

#### Micro-Timeline View ("ชั่วโมงต่อชั่วโมง & 3 วันข้างหน้า")
- Interactive horizontal slider/tab switcher: [+6 ชม. | +12 ชม. | 24 ชม. | 3 วัน | 7 วัน]
- Step-by-step visual cards showing:
  - 14:00 (ฝนเริ่มซา)
  - 15:30 (น้ำทะเลหนุนพีคสุด - จุดเสี่ยงสูงสุด)
  - 17:00 (อุโมงค์ระบายน้ำเร่งระบาย - น้ำเริ่มลดระดับ)
  - 19:30 (ถนนสายหลักแห้ง รถยนต์วิ่งได้ปกติ)

#### Dual View Toggle: "ประชาชน (Citizen Mode)" vs "วิศวกรรม/ละเอียด (Expert Mode)"
- Citizen Mode (Default): Simple metrics, centimeter depths relative to car wheels/curbs, plain text guidance, action checklists ("ย้ายของขึ้นที่สูง", "เลี่ยงเส้นทาง").
- Expert Mode: Hydrological curves, water elevation in m MSL (รทก.), Bang Sai (C.29) discharge in m³/s, astronomical tide harmonics, BMA pumping station status (m³/s flow), and rainfall hyetograph.

#### Live Map & Canal Network
- Clean Leaflet map centered on Bangkok with:
  - Color-coded flood risk overlay on roads/sub-districts.
  - Chao Phraya key river telemetry stations (C.29 Bang Sai, Memorial Bridge C.22, Bangkok Port, Chulachomklao).
  - Main BMA Drainage Canals (Khlong Saen Saep, Khlong Lat Phrao, Prem Prachakon) and Giant Pumping Stations.

### 3. Hydrological & Forecasting Calculation Logic (Client-Side Simulation Engine)
Implement a robust computational engine combining:
1. Fluvial Upstream Lag: Bang Sai (C.29) flow translated to Bangkok reaches with an 8-14 hour hydrograph propagation delay.
2. Astronomical Tidal Surge: Semi-diurnal high/low tide cycle of the Gulf of Thailand (Fort Chulachomklao benchmark) backwater effect.
3. Urban Runoff & Soil Infiltration: Inflow hydrograph driven by real-time Open-Meteo rainfall forecast for Bangkok (using Rational Method / Unit Hydrograph for high imperviousness $C = 0.85$).
4. Drainage & Pumping Capacity: Water evacuation rate modeled on BMA drainage tunnel capacities (e.g., Rama IX tunnel, Phra Khanong complex at nominal $60\text{ m}^3/\text{s}$).
5. Time-to-Dry Equation:
   $$\Delta T_{\text{dry}} = \frac{V_{\text{ponding}}}{Q_{\text{pump}} + Q_{\text{gravity}} - Q_{\text{residual\_rain}}}$$
   Translate $\Delta T_{\text{dry}}$ directly into human-readable completion timestamps.

### 4. Technical Stack & Deliverables
- Single-page application using modern HTML5, Tailwind CSS, Vanilla JS / Vue 3 / React (standalone in single file if possible or standard Vite structure).
- Mapping: Leaflet.js with CartoDB Positron / OpenStreetMap tiles (light, high readability).
- Charts: Chart.js with responsive dual-axis support.
- Weather: Connect to live Open-Meteo API (`https://api.open-meteo.com/v1/forecast`) for Bangkok precipitation, wind, and pressure; provide seamless offline fallback values.
- Language: Primary UI in clear, natural Thai language. Technical toggles in English/Thai.
- Design Aesthetic: Clean, urgent yet calming (GovTech/Utility aesthetic), responsive across mobile and desktop.

## Option 2
### Role
You are a senior hydroinformatics engineer and full-stack developer. You combine operational
flood forecasting (river routing, tidal hydraulics, rainfall–runoff) with modern statistical/ML
forecasting and production web development. Work carefully, verify every data source by actually
calling it, and never invent API endpoints or data.

### Context
Bangkok and the central plain of Thailand are currently flooding (2026). Build a web app that
aggregates real-time water levels from many stations, combines them with weather forecasts and
upstream conditions, and forecasts water levels so affected Thai residents can answer two questions:
1. Will the water around my house rise or fall in the coming hours/days?
2. When will the flood recede and return to normal?

Users: Thai residents, many on mobile phones, many non-technical, some under stress.
The entire UI must be in Thai.

### Geographic scope
- Primary: Bangkok (Chao Phraya main stem, major khlongs, BMA drainage network)
- Secondary: Central region / lower Chao Phraya basin (Nakhon Sawan → Chai Nat → Ayutthaya →
  Pathum Thani → Nonthaburi → Bangkok → Samut Prakan), including Pasak, Tha Chin, Noi, Lop Buri rivers.

### Phase 0 — Data source research and verification (do this FIRST, deliver a report before coding)
Research and test every available source. For each one, produce a row in `docs/SOURCES.md`:
| Source | Data type | Stations/coverage | Access method (API / JSON behind web page / CSV / scrape) |
| Endpoint(s) tested | Update interval | Latency | Auth/key needed | Datum & units | License/ToS | Reliability notes |

###### Given sources (analyse how the pages load their data)
- HII ThaiWater station map: https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/warning
- Station charts (note the red line = ระดับตลิ่ง bank level, in ม.รทก. = metres above MSL):
  - https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/chart/BKK008
  - https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/chart/BKK021
Inspect the network requests these pages make (XHR/fetch) to find the underlying JSON APIs.
Extract: station ID, name (Thai/English), lat/lon, current level, bank level (ระดับตลิ่ง),
ground level, warning thresholds, history, timestamp. Check whether HII's public API
(e.g. api-v3.thaiwater.net and the ThaiWater data catalog) exposes the same data more cleanly.

###### Additional sources to investigate (verify each; drop what doesn't work)
Water level / discharge / hydraulic structures
- HII / ONWR ThaiWater (thaiwater.net, national water data warehouse)
- Royal Irrigation Department (RID): hydrology stations (esp. C.2 Nakhon Sawan, C.13 Chao Phraya
  Dam discharge and levels, C.29A, C.35, Pasak stations), reservoir data, regional hydro sites
- EGAT / RID: Bhumibol, Sirikit, Pasak Jolasid dam storage and release
- BMA Department of Drainage and Sewerage: canal and river levels, Pak Khlong Talat station,
  pumping stations, flood-prone points, rain gauges
Tide (critical: lower Chao Phraya is tide-dominated)
- Hydrographic Department, Royal Thai Navy: tide predictions for Fort Phra Chulachomklao / Bangkok Bar
- Build a harmonic tide model from station history (e.g. `utide`) as a fallback
Weather / rainfall
- Thai Meteorological Department (TMD) open data API and radar
- BMA rain radar (weather.bangkok.go.th)
- Open-Meteo: deterministic + ensemble forecasts (ECMWF IFS, GFS, ICON), and the Open-Meteo
  Flood API (GloFAS river discharge)
- NASA GPM IMERG near-real-time rainfall (upstream basin rainfall)
Flood extent / remote sensing
- GISTDA flood maps (Sentinel-1 / satellite flood extent)
- Copernicus Emergency Management Service / GloFAS
Elevation (to relate water level to a user's house)
- Best available DEM: FABDEM, Copernicus GLO-30, MERIT DEM; note vertical accuracy limits in flat Bangkok
Citizen reports (optional, if accessible and permitted)
- BMA Traffy Fondue flood reports

Also search for any other official Thai or international source I haven't listed.
Respect robots.txt, ToS and rate limits; cache aggressively; identify the app with a User-Agent.
STOP after Phase 0 and show me the report plus a recommended source set before continuing.

### Phase 1 — Data ingestion
- Scheduled collectors (every 10–15 min for water level, hourly for weather/forecasts)
- Normalise to one schema: station_id, source, timestamp (UTC stored, Asia/Bangkok displayed),
  level_msl, bank_level_msl, discharge, quality_flag
- Handle datum differences explicitly (MSL / ม.รทก. vs local gauge zero); document every conversion
- QC: spike detection, flatlines, gaps, clock errors; flag, don't silently delete
- Store in PostgreSQL + TimescaleDB (or equivalent); keep raw payloads for reprocessing
- Station metadata table incl. upstream/downstream relationships and river network topology

### Phase 2 — Forecasting (scientifically grounded, explain every method in docs/METHODS.md)
Horizons: +12 h, +1 d, +2 d, +3 d, +7 d. Always output probabilistic forecasts (median + 50%/90%
intervals), with uncertainty growing with horizon. Be honest: beyond ~3 days skill relies on
upstream flow and ensemble rainfall and must be shown as low-confidence.

Use a hybrid approach and benchmark each component:
1. Baselines: persistence, persistence + tide, climatology (must be beaten to be shown)
2. Physically informed components:
   - Tidal component via harmonic analysis
   - Upstream flood-wave routing (lagged/Muskingum-style) from C.2 / C.13 discharge to Bangkok,
     with empirically estimated travel times
   - Rainfall-driven local component for khlongs (BMA rain + forecast rain, drainage/pump capacity)
3. Statistical/ML components trained on station history (use the flood years 2011, 2017, 2021,
   2022, 2024 and the current event where available):
   - SARIMAX with exogenous inputs (tide, upstream flow, rainfall)
   - Gradient boosting (LightGBM) with lagged features, quantile loss
   - Optionally a deep model (LSTM / Temporal Fusion Transformer) only if it beats the above
4. Ensemble / blending weighted by recent skill; calibrate intervals with conformal prediction
5. Recession / "back to normal" estimate: fit recession curves on the falling limb and upstream
   release trends; output estimated date range when level drops below bank level and below
   normal seasonal level, with probability
6. Validation: rolling-origin backtesting; report RMSE, MAE, NSE, KGE, interval coverage and
   threshold-hit/miss (bank-level exceedance) per station and horizon; show skill in the app's
   "about the model" page
7. Re-run forecasts automatically after each data update; flag stale inputs

### Phase 3 — Web app (UI entirely in Thai)
Mobile-first, fast on weak connections, accessible, calm tone.
- Map (MapLibre/Leaflet) of all stations, coloured by status:
  ปกติ / เฝ้าระวัง / เตือนภัย / วิกฤต (relative to ระดับตลิ่ง)
- "ใกล้บ้านฉัน" feature: user shares GPS or types an address → nearest relevant stations →
  plain-language answer:
  "ระดับน้ำคาดว่าจะ เพิ่มขึ้น / ทรงตัว / ลดลง ในอีก 12 ชม." and
  "คาดว่าน้ำจะลดลงสู่ระดับปกติประมาณ วันที่ ... (ความเชื่อมั่น ...)"
  Optionally compare forecast level (ม.รทก.) with the DEM ground elevation at their point,
  clearly labelled as an estimate with its uncertainty
- Station page: real-time chart with bank level red line, history, forecast fan chart for
  12 h / 1 / 2 / 3 / 7 days, tide overlay, upstream flow, rainfall
- Trend summary with arrows and simple words; numbers in metres; Thai date/time, option for พ.ศ.
- Last-updated timestamp and data-source attribution on every screen
- Clear disclaimer: forecasts are estimates, follow official warnings (BMA, ปภ. 1784, HII, RID);
  links to official channels and emergency numbers
- Thai font (e.g. Noto Sans Thai / Sarabun); i18n-ready structure so English can be added later
- Optional: LINE notification / Web Push when a subscribed station is forecast to exceed bank level

### Phase 4 — Deployment and operations
- Suggested stack: Python (FastAPI, pandas, statsmodels, LightGBM) backend; Next.js or SvelteKit
  frontend; Docker Compose; justify alternatives if better
- CDN caching for public pages to survive traffic spikes during the flood
- Monitoring: collector failures, stale data, forecast skill drift
- README with setup, data flow diagram, and how to add a new station or source

### Working rules
- Work phase by phase; show results and wait for my confirmation between phases
- If a source fails or blocks access, say so and propose alternatives; never fabricate data
- Cite the papers/methods you rely on in docs/METHODS.md
- Keep the code modular: one adapter per data source