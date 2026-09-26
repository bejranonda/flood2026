# ARCHITECTURE.md — System Architecture

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-26
> **Decisions:** [D-001](plan/DECISIONS.md) (VPS core + Cloudflare edge; keyless sources collected on the server), [D-002](plan/DECISIONS.md) (archive-first, strict phases)
> **Based on:** the brief's Phase 1 and Phase 4 ([docs/brief/first_prompt.md](brief/first_prompt.md))

---

## 1. Overview and current status

A **VPS core** runs the scheduled collectors, the immutable raw archive, PostgreSQL + TimescaleDB + PostGIS, the forecasting jobs and a FastAPI backend. **Cloudflare** sits in front: DNS, TLS, DDoS protection, edge caching of the public API, Pages for the static Thai web app, and R2 for off-site archive replicas and backups.

**Why not Cloudflare alone:** the core is scientific Python with long time series, heavy analytical queries and model training. That doesn't fit the Workers CPU limits or D1. **Why still put Cloudflare in front:** at the flood peak, traffic can jump by orders of magnitude, and 1–5 minute edge caching absorbs it.

| Component | Status (2026-09-26) |
|---|---|
| Domain `flood.bejranonda.com` via Cloudflare Tunnel | **Live** (owner-reported). Its configuration isn't in this repo yet |
| Production VPS | **Live** (owner-reported). Region and specs to confirm ([OPEN_QUESTIONS](plan/OPEN_QUESTIONS.md)) |
| Application code | **None yet**. Scaffold only ([§7](#7-repository-layout)). Hosted in the private GitHub repo `bejranonda/flood2026` ([D-011](plan/DECISIONS.md)) |
| Dev host of this repo | Germany, 4 vCPU / 7 GB / ~11 GB free. **Not the VPS**, and blocked by BMA ([KI-502](KNOWN_ISSUES.md)) |

---

## 2. Data flow

```
  External feeds (keyless v1)                     VPS core (SG / TH)                                   Cloudflare edge            Users
 ┌──────────────────────────┐   every 10 min  ┌───────────────────────────────────────────────┐
 │ HII api-v3 + chart XHR    │───────────────►│ collectors/ (one adapter per source)           │
 │ Open-Meteo fcst/ens/flood │   hourly       │   fetch ─► archive raw ─► parse ─► QC flags    │
 │ RID pages/PDF, Traffy     │   daily/yearly │        │            │                          │
 │ BMA DDS* (Thai IP), Navy* │                │        ▼            ▼                          │
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

## 9. Backups and restore
- **Nightly:** `pg_dump` → R2. **Weekly:** Parquet export of the normalised tables → R2. **Continuous:** raw archive replication → R2.
- **Restore drill:** document it and **test it** (in Phase 1, then monthly). Record the time taken, with a target under 1 hour.
