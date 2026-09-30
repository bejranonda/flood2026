# Nationwide parity: the same history, forecast and panels as Bangkok (v0.16.0)

- **Date:** 2026-09-30 · **Status:** design approved by the owner (grill session 19:48–20:30 UTC) · **Decision:** D-064 (to be written with the implementation)
- **Owner answers:** nationwide "should be the same as in Bangkok, consider the consistency"; "I have more free space in server, you can consider to do full forecast"; inputs = rain + learned upstream; UI = full parity, กทม. default; go public and send the agency notes in parallel; keep the name BKK FloodWatch with a "ทั่วประเทศ" line.

## 1. Problem (evidence, 2026-09-30, production DB and live site flood.autobahn.bot)

| Measured | Focus (Bangkok + lower Chao Phraya) | Nationwide (`in_focus = false`) |
|---|---|---|
| Gauges | 311 | 733 (719 reported in the last 24 h): RID 297, HII 274, FOP 89, EGAT 73; all have `hii_id` |
| History source | `hii_waterlevel` + `hii_backfill` (365 d) + `hii_history` (3 d / 6 h) | `hii_waterlevel` only: both history collectors filter `WHERE in_focus` |
| Oldest reading | 2025-09-25 | URTU07 (น้ำพอง บ้านผานกเค้า (E.29), เลย, EGAT): 2026-09-26 07:00 UTC, 104 hourly rows |
| Forecast | yes | never (`forecast.run_all` filters `WHERE s.in_focus`) |

- HII serves the year: `waterlevel_graph?station_type=tele_waterlevel&station_id=3519` returned 8,537 hourly readings 2025-10-01 → 2026-09-30, 730 KB, one request (HTTP 200, called from the worker container 2026-09-30 ~19:55 UTC).
- **History length matters only up to a full year.** Backtest (production `evaluate`, same last-45-day window) on 40 random HII focus gauges: mean skill vs persistence at 12/24/48 h = 0.29/0.22/0.20 with 60 d history, 0.24/0.25/0.20 (90 d), 0.31/0.22/0.20 (180 d), **0.38/0.29/0.28 (365 d)**; gauges with 48 h skill > 10 %: 28, 30, 29, **36 of 40**. `star` chosen 37 → 95 times.
- **History alone does not help nationwide.** A year fetched for 12 nationwide gauges (URTU07, E.29A, RAJ002, B.3A, PIN008, FOP057, PATO01, K.11A, MOU172, M.192, FOP019, N.54): own methods only (no tide inland → persistence vs trend) → **0 / 12 beat persistence** at 12/24/48 h. Bangkok's skill comes from `star` inputs (Chao Phraya chainage upstream gauges, Bangkok `RAIN_POINTS`), which nationwide gauges lack (Loei would get Bangkok's rain).
- Compute: `forecast_station` takes 1.3–1.5 s per gauge (C.35, BKK013, CPY012; `evaluate` ≈ 0.4–0.7 s of it). The 30-min run for 277 gauges takes ~4.5 min inside the single worker loop, blocking the 10-min collectors. Host: 4 CPUs, ~2 GB RAM available, disk 83 % (13 GB free; owner says more space is available).
- Storage: `observation` 982 MB for 4.64 M rows (~212 B/row). A year for 733 gauges ≈ 6.3 M rows ≈ +1.3 GB.
- UI defects seen on URTU07 (390 px and 1440 px screenshots): "น้ำในคลองต่ำกว่าตลิ่ง 983 ซม." (a river, not a canal); "การคาดการณ์จะเริ่มเมื่อมีข้อมูลครบ 7 วัน (ราว 3 ต.ค.)" is false for every nationwide gauge; header "ข้อมูลล่าสุด 1 ต.ค. 23:00" in the future (KI-247 rows; 26 rows flagged `future_time` with owner approval 2026-09-30 ~20:25 UTC, `/api/health` still reads them); nationwide gauges only behind the map checkbox; E.29A (RID, bank 238.5) and URTU07 (EGAT, bank 237.39) measure the same place.

## 2. Goal and success criteria
Every HII-network gauge in Thailand gets what a Bangkok gauge gets: a year of history, the same forecast ladder and backtest gate (48 h line only where it beats persistence by > 10 %, a range otherwise), the same panels, rows, chips and texts, reachable from region chips. Success:
1. ≥ 95 % of the 719 fresh nationwide gauges have ≥ 300 days of history within 48 h of deploy.
2. Nationwide backtest reported (with vs without the new inputs, vs the 0/12 baseline); no gauge shows a line without passing the gate.
3. Bangkok 48 h skill does not drop (same 40-gauge check: mean ≥ 0.27, ≥ 35/40 over the gate).
4. Collectors never wait for forecasts; each gauge gets a fresh forecast every 30 min; forecast cycle < 25 min.
5. `ux_consistency.py` passes C1–C6 on Bangkok **and** nationwide gauges at 360/390/768/1440 px.

## 3. Design

### 3.1 History (bounded full year)
- `hii_backfill` and `hii_history` cover every gauge with `hii_id` and agency ≠ BMA (drop `in_focus`). Backfill pace unchanged (6 gauges / 10 min → ~20 h for 733).
- `hii_history` refreshes focus gauges every run (as today) and **rotates nationwide gauges in six slices** (one slice per 6 h run, so each nationwide gauge is refilled daily); a run stays ≤ ~5 min.
- **Retention:** a daily `retention` task deletes `observation` rows older than **400 days** for HII-network gauges only. BMA (`agency='BMA'`, relay history, not re-fetchable, KI-218) is never deleted. Deletes in batches (≤ 50,000 rows per statement) to keep locks short.

### 3.2 Rain per gauge
- `RAIN_POINTS` (Bangkok, 9 points) unchanged.
- Nationwide gauges snap to a 0.5° cell (177 cells today): point id `g_<lat>_<lon>` (cell centre, 2 decimals). Cells are derived from station coordinates, not hard-coded.
- `openmeteo` fetches the cells hourly with batched multi-location requests; `openmeteo_prev` backfills a year per cell, spread across runs (a few cells per run), then 3 days daily. ⚠️ Batch size and the free-quota weighting of long ranges must be verified live before use (evidence rule); if the quota does not fit, nationwide cells refresh every 3 h.
- Rows go into the existing `weather_forecast` and `rain_hindcast` tables. `load_exo` picks the gauge's own cell (Bangkok gauges keep the nearest `RAIN_POINTS`).

### 3.3 Learned upstream gauges
- Only for gauges without Chao Phraya chainage (Bangkok's `upstream_of` rule is unchanged).
- Candidates: same `basin`, ≤ 250 km, ≥ 180 days overlap. Score = max over lag 1–48 h of the correlation between the candidate's 24 h change at t − lag and the target's 24 h change at t, **on data before the backtest window only** (no leakage). Keep the top 2 with r ≥ 0.5.
- Recomputed weekly; stored in `collector_state` key `upstream_learned` as `{code: [[up_code, lag_h, r], …]}`.
- Features are changes, so datum offsets between agencies cancel; levels are never compared across agencies (KI-217 holds).

### 3.4 Compute
- New compose service `forecaster` (same image, `python -m floodwatch.worker --only forecast`); the collector worker no longer runs `forecast`.
- `evaluate` results cached per gauge per day in a new table `forecast_model (code PK, trained_at, payload jsonb)`; the 30-min run builds the live path from the cached choice and bands (star coefficients refit live as today, or cached if the cycle exceeds 25 min). Bangkok and nationwide share one code path.
- Streams one gauge at a time (RAM); uses 2 processes only if the measured cycle exceeds 25 min.

### 3.5 UI (full parity, กทม. default, D-033 kept)
- Region chips: กทม. · ปริมณฑล · เหนือ กทม. · ภาคเหนือ · อีสาน · ตะวันออก · ตะวันตก · ใต้ · ทั้งประเทศ; province → region table in the API (one source of truth). Summary counts, list, map, "ใกล้ฉัน" and pin panel follow the chip. Checkbox "แสดงสถานีทั่วประเทศ" removed. `/api/stations` default scope becomes all (the list filters by region).
- Water-body word: "แม่น้ำ" for river gauges, "คลอง" for canal gauges (BMA `WL.*`, HII canal gauges), "ลำน้ำ" when unknown; the rule reads agency/type fields, never guesses from names.
- New-gauge notice tells the truth: "กำลังดึงข้อมูลย้อนหลัง" while backfilling; "รอผลทดสอบย้อนหลัง" before the first backtest; no date promise.
- Same place, two agencies (≤ 300 m, different agency): each keeps its own bank; the sheet shows one line "หน่วยงานอื่นวัดที่จุดเดียวกัน: <name> (<agency>)" linking to the other sheet. Never merged.
- Header and `/api/health` ignore readings stamped > 15 min in the future (KI-247).
- Name stays BKK FloodWatch; meta description, JSON-LD and README say it covers HII/RID/EGAT/FOP gauges nationwide, Bangkok in depth.

### 3.6 Errors and degradation
- Open-Meteo down or over quota: gauges without fresh rain fall back to their own methods (as `star` does today when an input is missing); health recorded per source.
- Backfill failures retry on the next run; a gauge with < 7 days shows measured data only.
- Forecaster down: the site shows the last forecast with its issue time (as today); `/api/health` reports forecaster staleness.

## 4. Testing and proof
- Unit tests: retention never deletes BMA rows and respects 400 days; cell snapping; learned-upstream uses only pre-window data (a leakage test with a synthetic leading series); region mapping for all 77 provinces; water-body word; KI-247 header/health filter; forecaster task split (collector worker has no `forecast`).
- Backtest report: nationwide skill with/without the new inputs vs the 0/12 baseline; Bangkok 40-gauge check vs §1 numbers. Written to APPROACH §19 with date and host.
- `scripts/ux_consistency.py` extended to sample nationwide gauges per region; screenshots at 360/390/768/1440 px: URTU07 (เลย), one southern gauge, one Bangkok gauge.
- Full test suite in the container, health check before and after deploy.

## 5. Out of scope (recorded as open)
Dam release scenarios beyond C.13 (e.g. Ubol Ratana below E.29), DWR/FFPI/GISTDA national layers (phase 5.2), Traffy outside Bangkok, per-station server-rendered pages for SEO.
