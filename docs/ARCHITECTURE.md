# ARCHITECTURE.md — System Architecture

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-10-05 (v0.25.2)
> **Decisions:** [D-001](plan/DECISIONS.md) (VPS core + Cloudflare edge; keyless sources collected on the server), [D-002](plan/DECISIONS.md) (archive-first, strict phases)
> **Based on:** the brief's Phase 1 and Phase 4 ([docs/brief/first_prompt.md](brief/first_prompt.md))

---

## 1. Overview and current status

A **VPS core** runs the scheduled collectors, the immutable raw archive, PostgreSQL + TimescaleDB + PostGIS, the forecasting jobs and a FastAPI backend. **Cloudflare** sits in front: DNS, TLS, DDoS protection, edge caching of the public API, Pages for the static Thai web app, and R2 for off-site archive replicas and backups.

**Why not Cloudflare alone:** the core is scientific Python with long time series, heavy analytical queries and model training. That doesn't fit the Workers CPU limits or D1. **Why still put Cloudflare in front:** at the flood peak, traffic can jump by orders of magnitude, and 1–5 minute edge caching absorbs it.

| Component | Status (2026-09-26, verified) |
|---|---|
| **Main domain `flood.autobahn.bot`** ([D-017](plan/DECISIONS.md)) | Proxied CNAME → Cloudflare Tunnel `d62b426d…` → `cloudflared` → `http://app:3000`. ⚠️ The zone shows a bot challenge to non-browser clients ([KI-506](KNOWN_ISSUES.md)) |
| Alias `flood.bejranonda.com` | Same tunnel, full alias (no redirect until KI-506 is fixed) |
| Server | The single host `HZ-Agent` (Hetzner DE, 4 vCPU / 7.7 GB / ~13 GB free). **No other environment** ([D-013](plan/DECISIONS.md)). No inbound ports open |
| Application | **Live MVP**: collectors, raw archive, forecasts, FastAPI + Thai web app, all in `docker compose` (`db`, `worker`, **`forecaster`** (v0.16), `app`, `cloudflared`, `vpn`) |
| Nationwide parity (v0.16.0, [D-064](plan/DECISIONS.md)) | Every HII-network gauge (1,040 shown) gets history, QC, forecast and panels. **`worker`** (collector role) runs the collectors, QC, `retention` (daily) and owns `schema.sql`; **`forecaster`** (`worker --role forecaster`) runs `forecast` (30 min; ~965 gauges in 294–409 s, backtest cached per gauge ~20 h in `forecast_model`) and `upstream_learn` (daily, `collector_state.upstream_learned`). New collectors: `hii_geo` (weekly: HII basin/river map files → `station.basin22`, `river_main`, `river_system`, v0.17), `openmeteo_fine` (hourly, 111 points at the ~8 km grid around Bangkok-region gauges, v0.16.4), `openmeteo_cells` (3 h, 177 cells of 0.5°, 50 per request) and `openmeteo_prev_cells` (hourly, a year for 8 new cells per run, then 4 days daily). `hii_backfill` covers the whole network (12 gauges / 10 min); `hii_history` refills nationwide gauges in six rotating slices. `httpclient`: 10 s connect timeout + 10-min host cooldown (KI-251) |
| Request path (v0.15.2; v0.15.3 adds robots/sitemap and a server-filled `__VERSION__` in `index.html`) | `STATIONS_SQL` rows and the `/api/stations`, `/api/stats`, `/api/reports` payloads are shared for 60 s (`_station_rows`, `_memo`, single-flight lock; KI-246); Postgres `max_connections` = 40 |
| Scheduled tasks (`worker.TASKS`, v0.15) | every 10 min: `hii_waterlevel`, `traffy`, `bma_klong`, **`qc`** (dropouts, erratic and stuck gauges, measured 24/48 h trend → `collector_state` `erratic_gauges` / `observed24`; D-057, D-058), `bma_history` (BMA history from HII: backfill, then a daily 3-day refresh 20 gauges per run, D-054, KI-239), `hii_backfill`; 30 min: `hii_rain`, `forecast` (backtest incl. `star`, D-052); 1 h: `openmeteo`, `disk`; 3 h: `hii_fews_forecast` (HII official forecast archive, D-050), `bma_dds` (only with a Thai egress); 6 h: `hii_stations`, `hii_history`; 15 min: `ai_triage`; daily: `openmeteo_prev` (rain as forecast 1–2 days earlier) **Since v0.25.2 a task that does not run at start is due one interval after its last success (`worker.first_due`, KI-288); the collector's `schema.sql` step runs with a 5 s lock timeout (KI-284).** |
| Database | Plain PostgreSQL 16; TimescaleDB/PostGIS deferred ([D-013](plan/DECISIONS.md)) |
| Off-site backup (R2) | **Not yet** (owner: Q15/Q16) |
| Repo | **Public** GitHub `bejranonda/flood2026` ([D-028](plan/DECISIONS.md)); **MIT License** ([LICENSE](../LICENSE), [D-043](plan/DECISIONS.md)) |

### 1.1 Live API (FastAPI, `/api/docs`)
| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Per-source health, data age (latest `ok` reading ≤ 15 min ahead, KI-247), **version** |
| `GET /api/stations` | Every gauge by default since v0.16 (`scope=focus` still works); each row carries `region`, `water` (the water word), `in_focus` and `twin` (another agency's gauge ≤ 300 m) |
| `GET /api/stations?scope=focus\|all`, `GET /api/stations/{code}?days=` | **Every** station, with latest plausible level, status vs bank, trend, recovery, and `notes` explaining any hidden value or approximate/no location (D-024); history + forecast payload + 7-day feedback counts |
| `GET /api/near?lat=&lon=&n=` | Nearest gauges by distance (⚠️ not polder-aware) |
| `GET /api/stats` | Compact statistics: status and trend counts, reporting freshness (focus and whole HII network), metadata gaps, Bangkok 24 h rain ([APPROACH §3.4](APPROACH_AND_METHODS.md)) |
| `GET /api/profile` | Chao Phraya main-stem gauges north → south with freeboard (no interpolation, D-019) |
| `GET /api/reports?hours=`, `GET /api/rain` | Aggregated Traffy flood reports (counts per ~1 km cell); Open-Meteo rain totals |
| `POST /api/feedback`, `GET /api/feedback/summary` | Citizen feedback (private; rate-limited; instant rule-based `urgent` flag) and public counts ([D-020](plan/DECISIONS.md)) |
| `GET /api/geocode?q=` | Place search (ซอย, ถนน, ย่าน) in the Bangkok region via OSM Nominatim, ≤ 1 req/s across workers, 30/h per visitor, queries never logged ([D-032](plan/DECISIONS.md)) |
| `GET /api/point?lat=&lon=` | Point check for places without a gauge: area category, nearby gauges, citizen evidence, warnings ([D-021](plan/DECISIONS.md)) |
| `GET /api/summary` | One deterministic Thai situation sentence (template, not AI) |
| `GET /robots.txt`, `GET /sitemap.xml` | Crawler files (v0.15.3, KI-248): the page is allowed, `/api/docs`, `/api/openapi.json` and `/api/point` are kept out of indexes; one sitemap URL |

### 1.2 Optional Cloudflare Workers AI ([D-022](plan/DECISIONS.md))
The worker task `ai_triage` (every 15 min) sends new feedback notes to Workers AI (SEA-LION v4) over REST and stores `user_feedback.ai_label`. It has a budget and a circuit breaker (state in `collector_state.ai_usage`), and **only the worker holds AI credentials**. If AI is unavailable, nothing user-facing changes.

---

## 2. Data flow

```
  External feeds (keyless v1)                     VPS core (SG / TH)                                   Cloudflare edge            Users
 ┌──────────────────────────┐   every 10 min  ┌───────────────────────────────────────────────┐
 │ HII api-v3 + chart XHR    │───────────────►│ collectors/ (one adapter per source)           │
 │ Open-Meteo fcst/ens/flood │   hourly       │   fetch ─► archive raw ─► parse ─► QC flags    │
 │ RID pages/PDF, Traffy     │   daily/yearly │        │            │                          │
 │ BMA KlongMap via flood69  │                │        ▼            ▼                          │
 └──────────────────────────┘                │  ┌───────────┐  ┌─────────────────────────┐    │     ┌───────────────┐
        * see KNOWN_ISSUES                   │  │ Raw archive│  │ Postgres + Timescale    │    │     │ R2: raw replica│
                                             │  │ gzip+SHA256│─►│ + PostGIS (normalised)  │    │────►│ + DB backups   │
                                             │  └─────┬─────┘  └───────────┬─────────────┘    │     └───────────────┘
                                             │        └──── replicate ──────┼──────────────────│──►
                                             │                             ▼                  │
                                             │  forecast/ (every cycle; retrain weekly)       │
                                             │   L0–L5 ladder ─► forecast_run (versioned)     │
                                             │                             ▼                  │
                                             │  api/ FastAPI on 127.0.0.1:${PORT}             │
                                             └───────────────────┬───────────────────────────┘
                                                                 │ cloudflared tunnel (no open ports)
                                                                 ▼
                                             ┌──────────────────────────────────────┐        ┌──────────────┐
                                             │ CF: cache API 1–5 min + SWR; DDoS;    │───────►│ Thai mobile   │
                                             │ Pages: static web/ (Thai UI)         │        │ web users     │
                                             └──────────────────────────────────────┘        └──────────────┘
```
The browser only ever calls our API or edge (D-001), never a source directly.

---

## 3. Storage (two layers)

### 3.1 Layer 1 — immutable raw archive ([`src/floodwatch/archive/`](../src/floodwatch/archive/README.md))
- Every payload is stored **exactly as received**, gzip-compressed, with its fetch time (UTC), URL, HTTP status, SHA-256 and collector version. It is kept forever.
- Written to local disk **and** replicated to **Cloudflare R2**.
- **Rough size estimate** ⚠️: HII `waterlevel_load` is ~1.4 MB × 144 calls/day ≈ 200 MB/day raw, and much less gzipped (JSON typically compresses 5–10×). Plus `rain_24h` (several MB per call) and the other feeds. Plan for **tens of GB per year** and confirm in Phase 1.

### 3.2 Layer 2 — normalised database ([`src/floodwatch/db/`](../src/floodwatch/db/README.md))
PostgreSQL + **TimescaleDB** (hypertables, compression, continuous aggregates for hourly and daily data) + **PostGIS** (station points, polders, river reaches, chainage, spatial joins).

| Table | Key columns |
|---|---|
| `observation` | station_id, source, **obs_time (UTC)**, level_msl, bank_level_msl, discharge, quality_flag, raw_ref |
| `station`, `station_version` | geometry, datum, bank, ground, agency, regime, polder_id, **valid_from / valid_to** |
| `river_node`, `river_reach` | graph topology, chainage, reach length, fitted τ(Q) |
| `polder`, `pump`, `gate` | polygons, capacities, outlet node |
| `weather_forecast_run` | model, member, **issue_time**, **valid_time**, variable, value (areal aggregates per polder) |
| `tide_prediction` | station, time, height_llw, height_msl, method (navy / utide), fit window |
| `operation_event` | RID releases and diversions, BMA gates and pumps, warnings (time range, value, source) |
| `forecast_run`, `forecast_value` | model level (L0–L5), version, issue_time, lead, quantiles, conditions |
| `source_health` | per source: last success, last error, data age → degraded mode and alerts |
| `user_feedback` *(live)* | verdict, depth band, note (private), rounded lat/lon (opt-in), **snapshot of what was shown**, daily-salted client hash |
| `collector_state` *(live)* | small key/value bookkeeping: stations already backfilled (365 d), chart codes that failed in the last 24 h |

The live MVP schema ([schema.sql](../src/floodwatch/db/schema.sql)) is a simpler subset of this target: `station`, `station_version`, `observation`, `rain_obs`, `weather_forecast`, `crowd_report`, `forecast_run`, `source_health`, `user_feedback`, `collector_state`, plus `external_forecast` (HII official forecasts as issued, D-050) and `rain_hindcast` (rain as forecast 1–2 days earlier, training data for the `star` method, D-052).

Store UTC and display Asia/Bangkok. Station metadata is **versioned, never overwritten**.

---

## 4. Resilience and degraded mode
- **Circuit breaker per source.** A failing source never blocks the others.
- **Degraded mode:** the API serves the last verified value along with its age and a `degraded` reason. The UI greys it out and shows "ข้อมูลล่าสุดเมื่อ … (แหล่งข้อมูลขัดข้องชั่วคราว)".
- **Forecasts with stale inputs** are marked stale and fall back down the ladder (e.g. to L1) with wider intervals.
- **Edge `stale-while-revalidate`** keeps pages up even if the VPS is briefly unavailable.

---

## 5. Security
- Every service binds to **127.0.0.1**. Only `cloudflared` connects out to Cloudflare. **No inbound 80/443.**
- The firewall allows only SSH, **key-only** (no passwords, no root login).
- Secrets live in `.env` on the VPS (git-ignored) and Cloudflare secrets. Tokens have the least privilege needed ([KI-501](KNOWN_ISSUES.md)).
- `CORS_ORIGIN` is limited to the production domain.
- No citizen personal data in public responses ([KI-107](KNOWN_ISSUES.md)).

---

## 6. Deployment topology
| Node | Role | Notes |
|---|---|---|
| Production VPS (Singapore or Thailand; start at ~4 vCPU / 8–16 GB / 200 GB SSD) | Everything in the core | Docker Compose ([`infra/`](../infra/README.md)) |
| **Optional Thai collector node** | Only for sources that block non-Thai IPs (BMA) | Small, runs collectors only, pushes raw payloads to the core. Only after we've asked the agency ([KI-101](KNOWN_ISSUES.md)) |
| Cloudflare | Tunnel, cache, Pages, R2 | [`edge/`](../edge/README.md) |

**Redeploy target:** a fresh VPS restored from R2 backups in **under 1 hour**, following a tested runbook.

---

## 7. Repository layout
```
flood2026/
├── README.md · CLAUDE.md · .env.example · .gitignore
├── docs/                     maintained documentation (this file, SOURCES, KNOWLEDGE, …)
│   ├── brief/first_prompt.md   original project brief
│   └── plan/                   roadmap, phase checklists, decisions, open questions
├── research/                 research snapshots + VALIDATION report + validation/ script
├── src/floodwatch/
│   ├── collectors/           one adapter per source (Phase 1)
│   ├── archive/              immutable raw archive + R2 replication (Phase 1)
│   ├── db/                   schema, migrations, spatial and time-series helpers (Phase 1)
│   ├── forecast/             model ladder L0–L7, backtests (Phase 2)
│   └── api/                  FastAPI backend (Phase 1 internal / Phase 3 public)
├── web/                      Thai mobile-first frontend (Phase 3)
├── edge/                     Cloudflare cache rules, Pages, R2 notes (Phases 3–4)
├── infra/                    docker-compose, cloudflared template, backups, runbooks (Phases 1–4)
└── tests/                    datum, timezone, parser, QC and model tests
```

---

## 8. How to add a new source or station
1. **Research:** add a dated file in `research/` and validate its claims ([research/README.md](../research/README.md)).
2. **Register:** add a row to [SOURCES.md](SOURCES.md) with the probe result **from the VPS**, the datum, units, timezone convention, license and polling interval.
3. **Permission:** check the ToS or ask the agency. Record the outcome in SOURCES.md.
4. **Adapter:** create `src/floodwatch/collectors/<source>.py` following the adapter contract (fetch → archive raw → parse → QC → health).
5. **Fixtures:** save 2–3 archived raw payloads as test fixtures, and write parser tests, including for sentinel values and timezones.
6. **Stations:** insert or update `station` and `station_version` rows with geometry, datum, bank level (with its source), regime, polder and graph links.
7. **Backfill** whatever history the source exposes.
8. Update [KNOWN_ISSUES.md](KNOWN_ISSUES.md) with any quirks.

---

## 8b. Storage growth (v0.16.0, D-064; measured 2026-09-30)
- Before: DB 1.24 GB (`observation` 982 MB / 4.64 M rows, ~212 B per row with indexes; `forecast_run` 196 MB / 52 k rows since 2026-09-26); disk 75 GB, 13 GB free (83 %; the owner has more space).
- `rain_obs` (v0.16.5): hourly rain kept 400 days for the 2,260 gauges within ~10 km of a water gauge (not re-fetchable from HII), 14 days for the other ~2,200; ~211 B per row (name and position repeated on every row) → ~4.6 GB a year. Optimisation if needed: a `rain_gauge` table for the metadata (~half the size).
- Expected after the nationwide backfill: +~1.3 GB `observation` (733 gauges × ~8,700 hourly rows), then flat: `retention` deletes HII-network readings older than 400 days (never BMA), rain-forecast issues older than 3 days, and thins `forecast_run` (since v0.25.2 thinned runs are kept 31 days for the 30-day track records, KI-290; all runs 2 days, one per 6 h to 14 days: ~0.6 GB at 1,000 gauges). ⚠️ To re-measure one day after the backfill ends (`SELECT pg_size_pretty(pg_database_size('floodwatch'))`).

- `gfh_forecast` (v0.26.0): a year of Flood Hub daily forecasts (302 k rows at backfill, ~800 a day after) — a `star` input (D-097).

## 9. Backups and restore
- **Nightly:** `pg_dump` → R2. **Weekly:** Parquet export of the normalised tables → R2. **Continuous:** raw archive replication → R2.
- **Sizing (measured 2026-09-26):** the raw archive grows **3–5 MB/hour (~100 MB/day)** in steady state, ~45 MB after the first 4 hours (including the one-off backfill); the database directory is 724 MB. A year of raw archive is roughly 35–45 GB. R2 free tier: 10 GB-month, 1 M writes, 10 M reads, free egress; then $0.015/GB-month.
- **Blocked on the owner:** R2 is not enabled and there are no S3 credentials yet ([OWNER_ACTIONS](OWNER_ACTIONS.md), [KI-504](KNOWN_ISSUES.md)). Until then the archive and the database exist only on this disk.
- **Restore drill:** document it and **test it** (in Phase 1, then monthly). Record the time taken, with a target under 1 hour.
