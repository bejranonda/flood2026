# VALIDATION_2026-09-26.md — Claim-by-claim validation of all research files

> **Why:** the six research files came from assistant-assisted research (claude.ai and Gemini) and disagree with each other in places. Rather than trusting or discarding whole files, each **testable claim** was checked against live endpoints, observed data, or published sources.
> **When / where:** 2026-09-26 06:40–07:00 UTC, from a dev host in **Germany (Hetzner, not the production VPS)**, with the honest User-Agent `BKK-FloodWatch-research/0.1 (+https://flood.bejranonda.com)`.
> **Reproduce:** `python3 research/validation/validate_research_claims.py` ([script](validation/validate_research_claims.py)). It re-runs the endpoint probes and the tide check.
> **Caveat:** anything unreachable from Germany may still work from a Thai VPS. Those items are ⚠️, not ❌.

## Verdict legend
| Mark | Meaning |
|---|---|
| ✅ | Confirmed by a live call, observed data, or a published source cited here |
| ❌ | Refuted by evidence |
| ⚠️ | Not checkable yet (blocked from this host, needs a key, or no source found). **Treat as a hypothesis** |
| 💡 | Useful idea or design input (not a factual claim) → adopted |

## Summary

| File | Origin | ✅ | ❌ | ⚠️ | Verdict |
|---|---|---|---|---|---|
| [sources_survey.md](sources_survey.md) | assistant-assisted | most | 2 (Navy URL now 404; "no Traffy API" is outdated) | several | 🟢 reliable. Main input to [docs/SOURCES.md](../docs/SOURCES.md) |
| [methods_survey.md](methods_survey.md) | assistant-assisted | the tide-type statement | 0 found | literature not re-read | 🟢 reliable. Main input to [docs/APPROACH_AND_METHODS.md](../docs/APPROACH_AND_METHODS.md) |
| [keyless_access.md](keyless_access.md) | assistant-assisted | 5 | 0 | 3 | 🟢 reliable |
| [API_noKey-1.md](API_noKey-1.md) | Gemini (`utm_source=gemini`) | 4 | 4 | 3 | 🟠 mixed: the Open-Meteo parts are useful; the tide and HII parts are wrong |
| [bangkok_flood_intelligence_data_sources.md](bangkok_flood_intelligence_data_sources.md) | claude.ai / Gemini | 7 | 5 | 12 | 🟠 mixed: its source ideas are useful (Traffy, RID portals), its endpoints are wrong |
| [bangkok_flood_calculation_forecasting_engine.md](bangkok_flood_calculation_forecasting_engine.md) | claude.ai / Gemini | 7 (textbook physics) | 5 | 8 | 🟠 mixed: the equations are useful, the implementation and numbers are not |

---

## §A — `API_noKey-1.md`

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| A1 | Open-Meteo needs no key | ✅ | Forecast, ensemble, flood and elevation APIs all returned 200 without a key |
| A2 | Open-Meteo is free for non-commercial use up to about 10,000 calls a day | ⚠️ | Matches Open-Meteo's published terms as understood; **re-check the terms before launch** (KI-106) |
| A3 | `getBangkokRainForecast()` request pattern | ✅ | The same parameters returned 200 JSON with `utc_offset_seconds: 25200` |
| A4 | The JS tide formula (M2 0.62 m/125.4°, S2 0.28/172.1°, K1 0.44/210.8°, O1 0.35/185.3°, Z0 0.95) predicts Bangkok tides | ❌ | Against 30 days observed at HII **CPY015 (สะพานกรุงเทพ)**: correlation **−0.74** (inverted), RMSE 1.07 m. Cause: it counts hours from an arbitrary epoch **without the astronomical argument V₀+u or nodal factors f**. Interestingly, the K1/O1/S2 amplitudes are close to those fitted at CPY015 (0.45/0.36/0.27 m); M2 is too large (fitted 0.37 m) |
| A5 | "4 constituents suffice" | ⚠️ | A 4-constituent fit explains 92 % of the tidal variance at CPY015 in-sample, but it needs fitted phases and ≥1 year of data for operational use (P1/K2 and seasonal terms) |
| A6 | `bkk_stations_elevation.json` road elevations (e.g. Memorial Bridge 1.95 m, Udom Suk 0.85 m MSL) | ⚠️ unsourced | For comparison, the Open-Meteo elevation API (90 m DEM) gives **4 m and 7 m** at those points. Neither source is good enough at the centimetre scale (KI-202, KI-304) |
| A7 | Browser calls to Thai endpoints are always blocked by CORS | ❌ (partly) | `api-v3.thaiwater.net` **echoes the Origin** (`access-control-allow-origin: https://flood.bejranonda.com`, credentials true). `publicapi.traffy.in.th` and Open-Meteo send `*`. Only `tiwrm.hii.or.th` (the chart XHR) sends no CORS headers. We still keep browser → our API only, for other reasons (D-001) |
| A8 | Worker proxy target `https://api2.thaiwater.net/v1/analyst/water/telemetry` | ❌ | **The host does not resolve in DNS** |
| A9 | Station codes `C.29`, `C.22`, `BKK01`, `BKK02` | ❌ | HII `tele_station_oldcode` uses `BKK001…BKK021` and `C.2`, `C.13`, … `C.29`/`C.22` are not in `waterlevel_load` at all |
| A10 | Cloudflare Workers free tier ≈ 100k requests a day | ⚠️ | Consistent with Cloudflare's free plan as understood; not re-checked |
| A11 | TMD API with `uid`/`ukey`; DGA data.go.th keys | 🟡 | The TMD portal `data.tmd.go.th/api/index1.php` returns 200. Key flows not tested |

## §B — `bangkok_flood_intelligence_data_sources.md`

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| B1 | Five ingestion domains (upstream flow, urban canals, tide and surge, weather and radar, elevation) plus crowd validation | 💡 | Adopted as the structure of [docs/SOURCES.md](../docs/SOURCES.md) |
| B2 | HII `https://api-v3.thaiwater.net/v1/telemetry/station/river` with `x-api-key` | ❌ | **HTTP 404**. The working API is `/api/v1/thaiwater30/public/*` and needs no key |
| B3 | RID SWOC portals `water.rid.go.th/flood/`, `wmsc.rid.go.th` | ✅ reachable | Both return 200. Machine-readable data inside still has to be found (Phase 0) |
| B4 | DWR `ews.dwr.go.th` | ⚠️ | Timed out from Germany |
| B5 | BMA DDS `dds.bangkok.go.th/canal/`, `/pumping/`, `/flood_warning/`; `weather.bangkok.go.th/water/CanalList.aspx` `#GridView1`; `203.155.220.119/flood/` | ⚠️ | **All BMA hosts reset the connection or return 403 from Germany** (`www.bangkok.go.th` 403). The layout can't be verified from here. That BMA blocks foreign or datacenter IPs **is itself confirmed** (KI-101). Test from a Thai IP |
| B6 | Bang Sue tunnel 60 m³/s; Rama 9–Ramkhamhaeng tunnel 60 m³/s | ✅ | [MGR Online](https://mgronline.com/onlinesection/detail/9600000091782), [Spring News](https://www.springnews.co.th/keep-the-world/climate-change/852476). Rama 9–Ramkhamhaeng is 9.5 km and starts at the Phra Khanong pumping station |
| B7 | Phra Khanong complex 155 m³/s (another doc says 155–205) | ⚠️ | No source found in this run |
| B8 | 56 flood-prone arterial roads | ⚠️ | No source found |
| B9 | Navy tide stations (Fort Chula, Bangkok Port, Memorial Bridge) | 🟡 | Matches the careful survey. **`hydro.navy.mi.th` sits behind a Cloudflare bot challenge (403 "Just a moment…")**, and the 2026 PDF URL now returns 404 (KI-102) |
| B10 | Copernicus Marine `GLOBAL_ANALYSISFORECAST_PHY_001_024` for surge | ⚠️ | The product exists as the global physics forecast. Whether it's suitable for surge in the Bight of Bangkok is unverified |
| B11 | Radar Z = 200 R^1.6 | ✅ | Standard Marshall–Palmer relation. Fine as a default before calibration |
| B12 | TMD radar `weather.tmd.go.th/svpLoop.php` | ❌ | HTTP 404 |
| B13 | Open-Meteo request with `convective_precipitation`, `surface_pressure` | ✅ | 200 |
| B14 | Copernicus DEM `s3://copernicus-dem-30m/`, OSM Overpass | ⚠️ | Well-known public datasets; not re-checked |
| B15 | "GISTDA/BMA LiDAR 1 m, ±0.1 m for all 50 districts" | ⚠️ | No source and no evidence it's available. Ask GISTDA, BMA or RTSD |
| B16 | Traffy `https://open.traffy.in.th/api/v1/tickets?type=flooding` | ❌ URL / ✅ idea | The host doesn't resolve in DNS. **But** `https://publicapi.traffy.in.th/share/teamchadchart/search` works, returns JSON with `coords`, `description`, `photo_url`, `timestamp` and `state`, and sends CORS `*`. The latest item was a flood report from Lat Phrao at 06:51 UTC. **The idea is valid**, with privacy caveats (KI-107) |
| B17 | Longdo Traffic API, X/Twitter filtered stream | ⚠️ | Need a key or paid access; not tested |
| B18 | Canonical JSON payload (`current_status`, `recovery_forecast`, `limiting_factors`, …) | 💡 | Adopted as a design input for the Phase 3 API (with ranges instead of point ETAs) |
| B19 | Harvester fallback `c29_flow = 2450.0` when the API fails | ❌ | Silent fabrication; the brief forbids it. Also, `datetime.now().hour` indexes the Asia/Bangkok hourly array using **server-local** time, which is wrong on a server outside Thailand |
| B20 | Depth bands 0–5 / 10–15 / 20–30 / 50+ cm with landmarks | 💡 | Adopted as UX vocabulary ([GUIDELINES §6](../docs/GUIDELINES.md)) |
| B21 | Tidal damping γ ≈ 0.35 per 100 km, lag 0.058 h/km | ⚠️ | Plausible order of magnitude; **fit from paired river stations** (Phase 2) |

## §C — `bangkok_flood_calculation_forecasting_engine.md`

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| C1 | Three Waters plus the human control boundary | 💡 | Adopted ([KNOWLEDGE §1](../docs/KNOWLEDGE.md)) |
| C2 | 1-D Saint-Venant equations; kinematic celerity c = 5/3·v (wide channel, Manning) | ✅ | Textbook |
| C3 | c_k(Q) = c₀ (Q/Q_bf)^0.38, c₀ ≈ 0.95–1.25 m/s, and the travel-lag table built from it (Rama VII 15.5 h at 2,000 m³/s, …) | ⚠️ | No source for the exponent or c₀. **Estimate the lags from data**: HII already provides discharge at C.2, C.13, C.3, C.35 (§E) |
| C4 | "Gulf tide is mixed, predominantly semi-diurnal and diurnal" | ❌ (as worded) | Observed at CPY015: form factor F = (K1+O1)/(M2+S2) = **1.27**, which means mixed and mainly diurnal. Literature: "The Gulf of Thailand is dominated by diurnal tides, and the strongest tidal constituent is K1" ([Ocean Science 15, 321, 2019](https://os.copernicus.org/articles/15/321/2019/)) |
| C5 | Seasonal mean sea level +0.30–0.55 m in Oct–Nov | ⚠️ | A seasonal high is real; the magnitude is unverified. Fit Sa/Ssa from ≥1 year of data |
| C6 | Surge = inverse barometer + wind set-up | ✅ | Textbook form. Parameters (fetch 120 km, depth 20 m) ⚠️ |
| C7 | Polder continuity; gate orifice flow only when H_canal > H_river | ✅ | Textbook and matches BMA practice |
| C8 | Runoff coefficients (dense urban 0.85–0.92, suburban 0.65–0.75, parks 0.20–0.35) | ✅ | Standard textbook ranges |
| C9 | Drainage designed for about 60 mm/h | ⚠️ | Cited in the careful survey to news sources; not re-read here |
| C10 | T_dry = V / (Q_pump + Q_gravity − Q_rain) | 💡 structure / ❌ implementation | The idea is sound as a volume-balance **sanity check**. The implementation goes non-monotonic (see C12) |
| C11 | Impact classification by depth (vehicle and pedestrian effects) | 💡 | UX vocabulary. The vehicle claims ⚠️ |
| C12 | `BKKHydroEngine` is production-grade; README sample output | ❌ | Running the demo gives: river 2.16 m at +0 h (the README said 1.15), **3.40 m at +11 h (above the 3.0 m wall)**, khlong **−1.25 m** (unbounded pumping), street 4.9 cm at +2 h (the README said 29.0), and **ETA 05:22 on 29/09 at +2 h but 19:04 on 26/09 at +3 h** (earlier, even though deeper). Its tide constants correlate +0.12 with observations. The phase sign is `+phase`; it uses naive `datetime.now()` |
| C13 | Deployment targets: RMSE ≤ 0.08 m (12 h), ≤ 0.15 m (72 h) at C.22 | ⚠️ | Aspirational with no basis. Use the acceptance gate in [GUIDELINES §4](../docs/GUIDELINES.md) |
| C14 | Peak timing ≤ 45 min against Traffy | ⚠️ | Traffy timestamps are report times, not peak times. Report it as a metric, not a gate |
| C15 | Mass-balance closure < 3 % | ✅ | A good **unit test** for the storage model |
| C16 | BMA staff gauge offset ≈ −1.00 m | ⚠️ | Must be confirmed per station |

## §D — Careful files (`sources_survey.md`, `methods_survey.md`, `keyless_access.md`)

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| D1 | HII public JSON works with no key, only a User-Agent | ✅ | `waterlevel_load` 200 (805 stations, 1.4 MB); `rain_24h` 200 (several MB, slow; see KI-108) |
| D2 | Response paths `waterlevel_data.data[]`, `data[]`; fields `waterlevel_msl`, `station.min_bank`, `tele_station_oldcode`, `situation_level`, `storage_percent`, `waterlevel_datetime` | ✅ | All present. There are also `discharge`, `diff_wl_bank`, `river_name`, `station.ground_level`, `warning_level_m`, `critical_level_msl`, `qmax` |
| D3 | `waterlevel_datetime` is local time without a timezone | ✅ | `"2026-09-26 13:30"` returned at about 06:45 UTC → +07:00 |
| D4 | BKK008 = คลองแสนแสบ บางกะปิ | ✅ | Title on the HII chart page |
| D5 | The HII chart pages load data by XHR (capture in Phase 0) | ✅ **captured** | `GET https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}` returns **~30 days of 10-min data** as `[epoch_ms_UTC, level_msl, bank, ground, level_str]`. `POST …/getGraph` (form + CSRF `_token`) serves custom ranges. `…/queryStation` lists stations. No CORS headers |
| D6 | HII exchange standard only guarantees 7 days of history | ⚠️ | Not tested. The chart XHR already gives 30 days → the backfill starts sooner |
| D7 | Navy 2026 tide PDF at `www.hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf` | ❌ now | 301 → `hydro.navy.mi.th/…` → **404**. The site also shows a bot challenge. Find the new URL manually (Phase 0) |
| D8 | "No documented Traffy API" | ❌ outdated | See B16: an undocumented public endpoint works |
| D9 | 403 from HII seen in a sandbox says nothing about HII's own policy | ✅ | HII works from a German datacenter IP. **BMA** does block it (B5) |
| D10 | Gulf of Thailand diurnal constituents are strong | ✅ | F = 1.27 at CPY015; Ocean Science 2019 |
| D11 | C.13 bank level 17.21 vs 15.77 — verify | ✅ flagged correctly | HII `min_bank` gives a **third** value, **16.34** m MSL. Resolve with RID |
| D12 | Copernicus GFM API at `api.gfm.eodc.eu/v2` | ✅ | 200 (Swagger UI) |
| D13 | data.go.th Pak Khlong Talat dataset | ✅ | Page returns 200 |
| D14 | methods_survey literature (ANN at C.4, XGBoost/RF, HEC-RAS 4-day lead, DHI 28 locations, Nearing 2024, CQR, ACI, FABDEM ranking) | ⚠️ | Consistent and specific, but the papers weren't re-read in this run. Re-verify the citations when writing the "เกี่ยวกับแบบจำลอง" page |

## §E — Station metadata: the docs' claims vs HII live (2026-09-26 12:00–13:30 ICT)

| Station | Claimed in docs/research | HII live | Verdict |
|---|---|---|---|
| C.2 | Mueang Nakhon Sawan, 15.6722/100.1258, bank 26.20, warning 25.70 | ค่ายจิรประวัติ, 15.67059/100.10936, **min_bank 25.7**, WL 22.25, **Q 1,824 m³/s** | ⚠️ bank differs by 0.5 m; the location is ~1.7 km off |
| C.13 | 15.1583/100.1833, bank 17.21 (or 15.77) | ท้ายเขื่อนเจ้าพระยา, 15.16384/100.18792, **min_bank 16.34**, WL 14.40, **Q 1,912** | ⚠️ three different bank values |
| C.3 | bank 11.70 | บ้านบางพุทรา, **min_bank 13.2**, WL 10.72, **Q 1,946** | ⚠️ |
| C.35 | 14.3486/100.5603, bank 4.58 | บ้านป้อม, 14.3691/100.52873, **min_bank 4.35**, **WL 4.34 (at bank)**, Q 1,156 | ⚠️ ~4 km off; bank differs |
| C.36 / C.37 | bank 4.00 / 3.80 | min_bank 4.3 / 4.14; **C.36 WL 5.48 (above bank)**, Q 629 / 77 | ⚠️ |
| BKK008 | Saen Saep Bang Kapi, 13.7667/100.65, bank 1.20, warning 0.80 | Name ✅; chart API bank **0.88**; latest **1.18 m MSL (above bank)**; **missing from `waterlevel_load`** | ❌ bank value; the lat/lon still has to be found |
| BKK021 | "Khlong Lat Phrao (วัดลาดพร้าว)", 13.8055/100.5917, bank 1.10, warning 0.70 | **คลองลาดพร้าว วัดบางบัว**, **13.85402/100.58746**, **min_bank 2.2**, ground −0.33, **WL 2.82 (situation 5, ล้นตลิ่ง)** | ❌ name, location and bank |
| C.29/C.29A (Bang Sai), C.21, C.22 / C.4 (Memorial Bridge), Fort Chula | Listed as key stations | **Not in `waterlevel_load`**. RID reports use **C.29A** for Bang Sai ([iGreen](https://www.igreenstory.co/bangkok-risk-flood-oct-2022/)) | ⚠️ need another feed (RID) |
| — | — | Bangkok river stations actually in HII: **C.12 กรมชลประทานสามเสน** (bank 2.26), **CPY015 สะพานกรุงเทพ** (bank 2.16), **CPY014 สะพานนวลฉวี** (Nonthaburi, bank 2.5), **AIT001 อโศก (คลองแสนแสบ)** (bank 2.39) | 💡 candidate v1 stations |

The difference between `min_bank` and older DWR report values (up to 1.5 m) may reflect datum or benchmark updates, or the choice of left vs right bank. **Use HII's operational metadata, store where each value came from, and version it** ([ARCHITECTURE §3](../docs/ARCHITECTURE.md)).

## §F — New findings (not in any research file)
1. **HII agencies in `waterlevel_load`:** HII 330, RID 315, FOP 89, EGAT 71. There are **no stations under agency "BMA"**. The `BKKxxx` codes are HII's own stations, not BMA stations mirrored into HII as KNOWN_ISSUES claimed. BMA data has to come from BMA.
2. **Sentinel values:** HII chart data uses **`999999`** for missing or bad readings (51 of 727 rows at CPY015). The collector QC must flag these (KI-206).
3. **Stale stations:** some stations report old timestamps (e.g. BKC004, last reading 2026-09-24 17:40). The data age must be shown per station.
4. **Payload size and speed from outside Thailand:** `waterlevel_load` is 1.4 MB and takes about 9 s; `rain_24h` is several MB and needed more than 60 s. Use compression and generous timeouts, and **never** fetch these per user request.
5. **The current situation (evidence of an active event):** BKK021, BKK002 and BKK013 are above bank (situation 5). C.35 is at bank. C.36 is 1.2 m above bank. C.3 carries 1,946 m³/s.
6. **DEM reality check:** Open-Meteo elevation gives 4 m (Memorial Bridge) and 7 m (Udom Suk) for places that are about 0–2 m MSL in reality. This shows the building/DEM bias the careful survey warned about (KI-202).
