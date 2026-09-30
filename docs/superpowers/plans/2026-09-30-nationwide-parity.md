# Nationwide Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every HII-network gauge in Thailand gets Bangkok's history, forecast ladder, backtest gate and panels (v0.16.0).

**Architecture:** Collectors drop the `in_focus` filter (history, QC, forecast); a bounded 400-day retention keeps the DB flat. Nationwide gauges get `star` inputs from 0.5° Open-Meteo rain cells and learned upstream gauges in the same basin. Forecasts move to a `forecaster` compose service with a daily cached backtest. The UI extends region chips to the whole country; summary counts follow the chip.

**Tech Stack:** Python 3.12, psycopg 3, numpy, FastAPI, Postgres 16, vanilla JS + Leaflet, pytest, Playwright (Python).

**Spec:** `docs/superpowers/specs/2026-09-30-nationwide-parity-design.md`

## Global Constraints
- Levels in m MSL, times in UTC; never compare levels across agencies (KI-217); BMA judged by BMA thresholds (D-038).
- A forecast line only where the backtest beats persistence by > 10 % (SKILL_GATE = 0.10); otherwise a range (D-054/D-055).
- BMA history (`agency='BMA'`) is never deleted (KI-218). Retention for other gauges: 400 days.
- Polite polling: HII backfill 6 gauges / 10 min; Open-Meteo within its free quota (nationwide cells every 3 h).
- `RAIN_POINTS` and the Chao Phraya chainage rule stay unchanged for focus gauges.
- Default region chip stays กทม. (D-033). Bump `?v=` on changed static files. Check the UI at 390 px.
- Tests: `docker compose run --rm --no-deps worker pytest -q` must pass before deploy; health check after.

## Review Focus
1. A gauge whose rain cell has no hindcast yet → `star` must drop out quietly (own methods), never crash the run. Test in Task 4.
2. Learned upstream picking the target itself or a gauge that only correlates after the cutoff (leakage). Test in Task 3.
3. Retention deleting BMA rows or rows newer than 400 days. Test in Task 1.
4. A province not in the region table (e.g. สาธารณรัฐแห่งสหภาพเมียนมา) → shows under ทั้งประเทศ only, never crashes the chips. Test in Task 5.
5. `weather_forecast` global `max(issue_time)` no longer covers every point when cells refresh every 3 h → per-point latest issue. Test in Task 2.

---

### Task 1: History for every HII-network gauge + retention + KI-247 health
**Files:** Modify `src/floodwatch/collectors/__init__.py` (hii_backfill, hii_history), `src/floodwatch/qc.py:136`, `src/floodwatch/api/__init__.py` (health), `src/floodwatch/worker.py` (TASKS); Create `src/floodwatch/retention.py`; Test `tests/test_retention.py`, `tests/test_worker.py`.
**Produces:** `retention.run(conn) -> dict`, `retention.OBS_KEEP_DAYS = 400`, `retention.WF_KEEP_DAYS = 3`, `collectors.history_slice(codes: list[str], run_no: int, slices: int = 6) -> list[str]`.

- [ ] Test: `history_slice` returns disjoint slices covering all codes over 6 runs; `retention.SQL` statements exclude `agency='BMA'` and use 400 days (assert on SQL text + a fake connection capturing params).
- [ ] Implement: backfill/history select `WHERE code !~ '^TEST' AND hii_id IS NOT NULL AND agency IS DISTINCT FROM 'BMA'` (backfill) and focus-every-run + nationwide slice (history; slice index from `collector_state` key `hii_history_slice`). QC selects all gauges. Retention: batched `DELETE … WHERE ctid IN (SELECT ctid … LIMIT 50000)` loops for `observation` (non-BMA, older than 400 d) and `weather_forecast` (issue older than 3 d); daily task `retention`. Health: `max(obs_time) WHERE quality_flag='ok' AND obs_time <= now() + interval '15 minutes'`.
- [ ] Run tests; commit `feat: history and QC for every HII-network gauge; bounded retention (KI-247 health)`.

### Task 2: Rain cells (0.5°) for nationwide gauges
**Files:** Create `src/floodwatch/rain_cells.py`; Modify `collectors/__init__.py` (openmeteo, new `openmeteo_cells`, `openmeteo_prev_cells`), `worker.py`, `forecast/__init__.py` (load_exo, run_all rain query), `api/__init__.py` (point rain); Test `tests/test_rain_cells.py`.
**Produces:** `rain_cells.cell_of(lat, lon) -> tuple[str, float, float]` (id `g_16.5_101.5`, centre lat, lon); `rain_cells.rain_point_for(in_focus: bool, lat, lon) -> str`; `rain_cells.all_cells(stations) -> dict[str, tuple[float, float]]`; `parsing.parse_openmeteo` reused per list element.
- [ ] Tests: snapping (16.49,101.26 → g_16.5_101.5; 7.24,100.74 → g_7.0_100.5); focus gauge → nearest RAIN_POINTS key; per-point latest-issue SQL used (fake conn).
- [ ] Implement: `openmeteo_cells` every 3 h, batches of 50 coordinates per request, one issue timestamp per run; `openmeteo_prev_cells` hourly: 8 cells without hindcast per run (one request, a year), and once a day a 4-day refresh for all cells (batches of 50). Queries use the per-point latest issue: `issue_time=(SELECT max(issue_time) FROM weather_forecast WHERE point=…)` or `DISTINCT ON (point)`.
- [ ] Run tests; commit `feat: 0.5° rain cells for nationwide gauges (Open-Meteo, batched)`.

### Task 3: Learned upstream gauges
**Files:** Create `src/floodwatch/forecast/upstream.py`; Modify `forecast/__init__.py` (load_exo); Test `tests/test_upstream.py`.
**Produces:** `upstream.score(target: np.ndarray, cand: np.ndarray, max_lag: int = 48) -> tuple[int, float]` (best lag ≥ 1 h, r) on 24 h changes; `upstream.learn(series: dict[str, tuple[np.ndarray, np.ndarray]], meta: dict[str, dict], cutoff_h: int) -> dict[str, list[list]]`; `upstream.run_all() -> int` (stores `collector_state['upstream_learned']`).
- [ ] Tests: a candidate that leads the target by 12 h is found with lag ≈ 12 and r > 0.9; a series identical to the target (lag 0) is not chosen; a candidate that only matches after the cutoff is not chosen (leakage); other basin / > 250 km excluded; top 2 with r ≥ 0.5.
- [ ] Implement; `load_exo` uses chainage upstream when the gauge is on the chain, else the learned list. Weekly task `upstream_learn` in the forecaster.
- [ ] Run tests; commit `feat: learned upstream gauges in the same basin (star inputs nationwide)`.

### Task 4: Forecast every gauge; forecaster service; cached backtest
**Files:** Modify `forecast/__init__.py` (run_all, forecast_station accepts `ev`), `db/schema.sql` (+ `forecast_model`), `worker.py` (`--role`), `docker-compose.yml` (+ `forecaster`); Test `tests/test_forecast.py`, `tests/test_worker.py`.
**Produces:** `forecast_station(..., ev: dict | None = None)`; table `forecast_model(code text PK, trained_at timestamptz, history_hours int, payload jsonb)`; `worker.tasks_for(role: str) -> list[tuple[str, int]]` (roles `collector`, `forecaster`).
- [ ] Tests: `tasks_for("collector")` has no `forecast`/`upstream_learn`; `tasks_for("forecaster")` only those; a cached `ev` with string keys round-trips to int horizons and gives the same path as a fresh `evaluate`; missing rain cell → forecast still produced (own methods).
- [ ] Implement: run_all over every non-TEST gauge with data in 12 h; reuse `forecast_model` if trained < 20 h ago; else evaluate and upsert. Log the cycle time.
- [ ] Run tests; commit `feat: forecaster service; every gauge forecast with a daily cached backtest`.

### Task 5: API parity (regions, water word, twins, point/near nationwide)
**Files:** Create `src/floodwatch/regions.py`; Modify `api/__init__.py`, `point.py` (water_body); Test `tests/test_api.py`, `tests/test_point.py`.
**Produces:** `regions.region_of(province: str | None) -> str | None` (keys bkk, metro, up, north, northeast, east, west, south); `point.water_word(s) -> "แม่น้ำ" | "คลอง" | "ลำน้ำ"`; station row fields `region`, `water`, `twin` (`{code, name_th, agency}` or None).
- [ ] Tests: every province in the DB list (spec) maps; Myanmar → None; water word: แม่น้ำ/น้ำ/แคว → แม่น้ำ, คลอง/คู → คลอง, ลำ/ห้วย/เหมือง/ร่อง → ลำน้ำ, NULL + BMA → คลอง, CPY* → แม่น้ำ, BKK* → คลอง; twin: two agencies ≤ 300 m linked, same agency not linked.
- [ ] Implement: `/api/stations` default `scope=all`; point, near, stats use all rows; stats adds `by_region` status counts; point rain from the cell (non-focus) or RAIN_POINTS.
- [ ] Run tests; commit `feat: nationwide API parity (regions, water word, same-place twins)`.

### Task 6: UI parity
**Files:** Modify `web/app.js`, `web/index.html` (`?v=`), `web/style.css` if needed.
- [ ] REGIONS from `s.region` (chips กทม. · ปริมณฑล · เหนือ กทม. · ภาคเหนือ · อีสาน · ตะวันออก · ตะวันตก · ใต้ · ทั้งประเทศ; zero-count chips hidden); summary status chips count the chosen region client-side; map fits the region's gauges; remove "แสดงสถานีทั่วประเทศ" and `toggleNational`.
- [ ] Water word from `s.water` everywhere "น้ำในคลอง/แม่น้ำ" is built; pin factor heading uses the nearest gauge's word.
- [ ] New-gauge notice: "กำลังดึงข้อมูลย้อนหลังจาก สสน." while history < 7 d; "รอผลทดสอบย้อนหลัง" when no skill yet; no date promise.
- [ ] Twin line: "หน่วยงานอื่นวัดที่จุดเดียวกัน: <name> (<agency>) ›" opens that sheet.
- [ ] Load in the browser at 390/1440 px (URTU07, a southern gauge, a Bangkok gauge); commit `feat: UI parity for nationwide gauges`.

### Task 7: Proof, docs, release
**Files:** Create `scripts/backtest_nationwide.py`; Modify `scripts/ux_consistency.py`, docs (KNOWLEDGE, KNOWN_ISSUES KI-249/KI-250, APPROACH §19, DECISIONS D-064, ARCHITECTURE, SOURCES, GUIDELINES, PLAN, phase-5, OPEN_QUESTIONS, OWNER_ACTIONS, README, HANDOFF, CHANGELOG), `src/floodwatch/__init__.py` (0.16.0).
- [ ] Deploy (tests → build → up → health); watch backfill progress; run backtest report once enough gauges have a year (Bangkok 40-gauge regression + nationwide with/without inputs).
- [ ] Extend `ux_consistency.py` to sample nationwide gauges per region; run at 360/390/768/1440 px; fix findings.
- [ ] Docs sweep, version, CHANGELOG, tag, GitHub release; commit and push.
