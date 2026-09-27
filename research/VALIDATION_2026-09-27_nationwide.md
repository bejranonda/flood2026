# VALIDATION_2026-09-27_nationwide.md — claim-by-claim check of the nationwide research

> **Date:** 2026-09-27, 08:55–09:45 UTC · **Host:** the production server (Hetzner, Germany) with the honest UA
> `BKK-FloodWatch/0.6 (+https://flood.autobahn.bot) nationwide-source-probe`, **one request per endpoint**. DWR and RID
> were also tried through the Thai egress (`vpn` sidecar, VPN Gate relay; public pages only, D-014).
> **Re-run:** [validation/probe_nationwide_2026-09-27.py](validation/probe_nationwide_2026-09-27.py).
> **Files checked:** [Nationwide/Research_NATIONWIDE.md](Nationwide/Research_NATIONWIDE.md) (🟢 mostly reliable) and
> [Nationwide/Research_Thailand.md](Nationwide/Research_Thailand.md) (🔴 do not use as a source; ideas only).
> Legend: ✅ confirmed · ❌ refuted · ⚠️ unverified or partly true · 💡 method idea, not testable here · ⛔ against project rules.

## A. Endpoint probes (what actually answers, and how fresh it is)

"Fresh" = timestamp on 2026-09-26/27. HII timestamps are Thai local time without a zone (KI-205).

| Source | Endpoint | Result | Rows · fresh | Verdict |
|---|---|---|---|---|
| HII water level (in production) | `api-v3…/thaiwater30/public/waterlevel_load` | 200 | 805 stations nationwide (HII 330, RID 315, FOP 89, EGAT 71, SOURCES §2) | ✅ national WL already arrives; we filter to the focus area |
| HII dams | `…/thaiwater30/analyst/dam` | 200, 1.05 MB, 1.6 s | `dam_daily` **50 large, 50 fresh** (storage MCM/%, inflow, release, spill; `max_storage`, `normal_storage`); `dam_medium` **862, 448 fresh** (317 dated 1970-01-01, 71 from 2021); `dam_small_tele` **60, 52 fresh** (level, % storage, **spillway level**); `dam_hourly` 17, 13 fresh | ✅ usable after filtering stale rows. **No rule curves** in the payload |
| HII gates | `…/public/watergate_load` | 200, 3.6 MB | **2,315 rows, only 12 fresh** (5 provinces, all HII); most rows stopped in **July 2023**; `warning_level_m`/`critical_level_msl` empty on all rows | ❌ not usable nationally |
| HII BMA road-flood sensors | `…/public/flood_road` | 200 | **262 BMA sensors, 241 fresh**; value in cm on the road; 58 > 0 cm, 46 > 10 cm, max 56.8 cm (16:10 ICT) | ✅ **new for Bangkok** (APPROACH §3.7 called this feed unreachable) |
| HII BMA canal gauges | `…/public/canal_waterlevel` | 200 | **282 BMA gauges, 229 fresh, 47 stale since before 2026**; codes `WL.xxx.nn` = the flood69 relay's; **156 overlap our 199, +73 fresh gauges we lack**; 250 carry bank/warning/critical; WL.BBN.02 = 0.58 m at 16:15 ICT in both sources | ✅ **government channel for the same BMA data** (reduces KI-218) |
| HII BMA flow | `…/public/flow` | 200 | 55 rows, 47 fresh, all BMA canals | ✅ Bangkok only |
| HII 7-day rain forecast | `…/public/rain7day_forecast` | 200 | image references (WRF-ROMS JPGs), no gridded numbers | ⚠️ pictures only |
| HII storms | `…/public/storm_data` | 200 | empty today | ✅ endpoint works |
| HII FEWS flash flood | `fews2.hii.or.th/model-output/data_portal/flashflood/flashflood_report.txt` | 200 | **25 tambons** (only those at risk are listed), with FFPI, 1-day rain forecast, monitoring station | ✅ |
| HII FEWS thresholds | `…/metadata/hii_waterlevel.csv`, `…/metadata/rid_discharge.csv` | 200 | **66 HII stations** with lowest/alarm/warning/critical (m MSL; esan 26, cpy 20, sw 12, east 8); **87 RID discharge stations** with thresholds in m³/s (C.13: 2,176 / 2,448 / 2,720; C.2: 2,988 / 3,362 / 3,735) | ✅ official thresholds |
| HII FEWS tide | `…/tide_table/summary.txt` | 200 | **28 stations, Gulf and Andaman** (Navy HQ, Bangkok Harbour, **Fort Chula**, Bangkok Bar … Ranong, Krabi, Trang, Tarutao); daily max/min with times and 4-hourly values | ✅ (research said "9 Gulf stations" ❌) |
| DWR EWS | `POST ews.dwr.go.th/ews/web-service/stn action=LoadStation` | **timeout from Germany**; **200 via Thai egress**, 3.0 MB, 28 s | **2,275 stations** (1,819 rain, 455 water level); rain 12 h, level, **soil moisture**, `status` 0/1/2/3 = 1,470/14/4/4 and **`9` = 783** (meaning not documented; probably offline ⚠️); dates in Buddhist short form `27/09/69 15:45 น.` | ✅ Thai egress only |
| RID Telerid | `telerid.rid.go.th/restapi/main/station_list/` | timeout from Germany; **200 via Thai egress** | `count: 921` | ✅ list; readings not tested |
| EGAT | `api-egatwater.egat.co.th/api/dam` | 200, 8 s | 69 dams, mostly **empty fields** (`LEVEL_MAX`, `SPILL_*` = `{}`) | ⚠️ low value |
| GloFAS (Open-Meteo Flood) | `flood-api.open-meteo.com/v1/flood` | 200, keyless | **Naive point at Nong Khai (17.88, 102.74): 1–3 m³/s**; the cell at 17.925, 102.725 (≈ 5 km away): **≈ 9,000 m³/s** (the Mekong). Hat Yai point: 0.1–1.3 m³/s | ✅ works; **must be snapped to the channel** (KI-509) |
| Google Flood Forecasting API | `floodforecasting.googleapis.com/v1/gauges:searchGaugesByArea` | **403** "unregistered callers … use API Key" | — | 🔑 needs a key and pilot acceptance (owner action) |
| Copernicus GFM | `api.gfm.eodc.eu/v2/` | 200 (API landing page) | auth not tested | 🔑 |
| GDACS | `gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=FL&country=THA&fromdate=2026-08-01…` | **204** no events | — | ⚠️ too coarse for local use |
| GISTDA (key in `.env`) | old: `…/gi-service/v1.0/disasters/flood-extent-1day?api_key=`; documented: `…/api/2.0/resources/features/flood/{1day,3days,7days,30days}`, `/features/flood-freq`, header `API-Key` | old: **404 "Service not found"**; documented: **200** | 3 d 38,461 · 7 d 49,761 · 30 d 52,778 flooded H3 cells nationally (area, exposure, source passes); 1 d empty; Bangkok bbox 0 in 7 d | ✅ after using the documented API (owner sent the docs link); the old path was ours (KI-510) |
| MRC | `ffw-web.mrcmekong.org` (from Research_Thailand) | **no DNS** | — | ❌ |
| ThaiWater (old host) | `api2.thaiwater.net` (from Research_Thailand) | **no DNS** (re-checked; already refuted in SOURCES §3) | — | ❌ |
| thaiwater.net pages the owner named | `www.thaiwater.net/water/wl`, `/water`, `/water/gate` | 200, a JS single-page app | the data come from the `api-v3` endpoints above | ✅ same data as above |

Not tested (needs registration, or excluded by rule): TMD APIs and NWP (🔑), NASA IMERG / JAXA GSMaP / SWOT Hydrocron / DAHITI (🔑), HII token APIs `api.hii.or.th/v2/<token>` (⛔ tokens copied from a web bundle must not be used), DDPM and ONWR portals (⛔ Cloudflare challenge; not attempted).

## B. Research_NATIONWIDE.md — verdicts

| Claim | Verdict | Evidence |
|---|---|---|
| HII api-v3 exposes dams, gates, discharge, canals, flooded roads, 7-day rain, storms | ✅ endpoints answer; ❌ **gates are stale** (12 of 2,315 fresh); ⚠️ 7-day rain is images | §A |
| HII FEWS: FFPI per tambon, station thresholds, RID discharge thresholds, tide | ✅ | §A |
| "tide_table: 9 Gulf stations" | ❌ 28 stations incl. Andaman | §A |
| DWR EWS `LoadStation` with rain, level, soil moisture, status 0–3 | ✅ via Thai egress; status also takes `9` (783 stations) ⚠️ | §A |
| Telerid ~921 stations | ✅ `count: 921` | §A |
| EGAT `api/dam` static info | ✅ but mostly empty fields ⚠️ | §A |
| Google Flood API needs a key after acceptance | ✅ 403 message | §A |
| GloFAS via Open-Meteo without key | ✅, but a point query must be snapped (not mentioned in the research) | §A |
| GDACS public API | ✅ answers; no Thai flood events Aug–Sep 2026 ⚠️ | §A |
| Reservoirs are operated by upper/lower rule curves; model release by emulation | 💡 sound; **the curves are not in any feed we reached** → need RID/EGAT documents | §A dam payload |
| Flood-type taxonomy F1–F8, tiers A/B/C, one model per type, FFG for flash floods | 💡 adopted as the method frame (APPROACH §19) | — |
| "Always show which tier a forecast comes from" | 💡 adopted as a rule (GUIDELINES §6.18) | — |
| Hat Yai Nov 2025 (335 mm in a day, ~234 km²); Mekong Aug–Sep 2026 (Nong Khai 12.69 m vs 12.2 m) | ⚠️ not verified; confirm from official reports before using as test events | — |
| Regional flood seasons (South Gulf Oct–Jan; rest Jul–Oct) | ⚠️ consistent with general knowledge; not cited | — |

## C. Research_Thailand.md — verdicts

| Claim | Verdict | Evidence |
|---|---|---|
| Ingestion from `api2.thaiwater.net/v1/analyst/water/{telemetry,dam,watergate}` | ❌ host has no DNS; **already refuted** (SOURCES §3). CLAUDE.md forbids refuted endpoints | §A |
| "> 1,200 stations" | ❌ `waterlevel_load` has 805 | §A |
| "35 large dams and > 300 medium reservoirs" | ❌ HII: 50 large, 862 medium (448 fresh) | §A |
| DWR "> 800 rain stations"; thresholds 100 / 150 mm/24 h | ❌ 1,819 rain + 455 level stations; thresholds not in the payload ⚠️ | §A |
| C.13 discharge thresholds 2,000 / 2,500 m³/s | ❌ RID FEWS: 2,176 / 2,448 / 2,720 | §A |
| MRC `ffw-web.mrcmekong.org` | ❌ no DNS | §A |
| GISTDA SAR vectors every 24–48 h | ⚠️ partly: the 7-day extent cites passes on 21, 22, 23, 24 and 26 Sep (Sentinel-1, Radarsat-2); the 1-day layer was empty on 27 Sep | §A |
| Street depth `d(x,y) = H − HAND` from a 30–90 m DEM | ⛔ D-019/D-021: DEM error (1–2 m) exceeds flood depths; never a depth at a pin | APPROACH §2.9–2.10 |
| "Egress relay (SOCKS5 / Cloudflare Workers)" for Thai sources | ⛔ D-014/D-016: only the owner's egress, public pages, no evasion | GUIDELINES §5 |
| UA `NationalHydrologyBot/2.0` | ⛔ not the project's honest UA | GUIDELINES |
| `compute_basin_warning_index` with advice such as "อพยพ ตัดกระแสไฟฟ้า" | ⛔ the app must not issue evacuation instructions; link official channels (DDPM 1784) | D-005, GUIDELINES §6 |
| Sample JSON (C.2 at 25.85 m, 2,480 m³/s, forecasts) | ❌ invented numbers, no source | — |
| Kirpich tc = 0.0195 L^0.77 S^−0.385 | 💡 standard, but **units missing** (result in minutes, L in m) ⚠️ | — |
| SCS-CN, Muskingum-Cunge, Jones loop rating | 💡 textbook methods; usable later where data exist | — |
| 8-week plan to national HAND inundation | ⚠️ not realistic for this project | — |
| Domain `flood.bejranonda.com`; trailing YouTube placeholder link | ❌ outdated / generation artifact | D-035 |

## D. New findings that matter now

1. **Bangkok, via HII (government channel):** BMA's **262 road-flood sensors** and **282 canal gauges** (+73 fresh ones we lack). This reduces the dependence on the third-party political relay (KI-218) and gives the road-level measurement APPROACH §3.7 wanted for validation. *Validated, not built* (owner: validate first).
2. **Official thresholds** for 66 HII level stations and 87 RID discharge stations, and **Navy tide predictions for 28 stations** incl. Fort Chula (KI-109, KI-102).
3. **The gate feed is dead nationally** (12 of 2,315 fresh). Do not build on it.
4. **GloFAS virtual gauges must be snapped** to the channel cell, or a Mekong town reads 3 m³/s instead of ~9,000 (KI-509).
5. **GISTDA works with the documented API** (header `API-Key`, `/features/flood/…`): ~50,000 flooded cells nationally over 7 days with exposure. Our old path returned 404 while the status script showed ✅ (KI-510, fixed). In Bangkok the radar extent was empty while streets flooded, so an empty cell is not "dry".
6. **DWR and RID work only from a Thai IP**; the only Thai egress is a public VPN relay (KI-505). A national service needs a reliable Thai egress.
7. Freshness filtering is mandatory on every HII national feed (1970 placeholders, rows stale since 2019–2023).
