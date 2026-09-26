# Phase 1 — Data ingestion and our own archive

> **Status:** ⏳ starts right after G0. **Gate G1:** ≥ 7 days of continuous collection, backfill done, restore drill passed.

## Goal
Treat every external source as something that can disappear at any time. **Our database is the system of record.** Capture every reading from now on, and backfill everything that is currently available.

## Inputs
[ARCHITECTURE §3–§5, §8–§9](../ARCHITECTURE.md) · [SOURCES.md](../SOURCES.md) (G0-approved set) · [GUIDELINES §3, §5](../GUIDELINES.md) · scaffold: [collectors](../../src/floodwatch/collectors/README.md), [archive](../../src/floodwatch/archive/README.md), [db](../../src/floodwatch/db/README.md), [infra](../../infra/README.md)

## Tasks
### Day 1–2 (urgent, right after G0)
- [ ] `infra/docker-compose.yml`: Postgres + TimescaleDB + PostGIS, scheduler, bound to 127.0.0.1
- [ ] Raw archive writer (gzip + SHA-256 + metadata) with R2 replication
- [ ] Adapters: `hii_waterlevel` (10 min), `hii_rain` (10–15 min), `openmeteo_forecast` + `openmeteo_ensemble` (hourly, **every run**), `hii_graph_backfill`
- [ ] Start the **backfill**: HII `getGraphFirst` (30 days) for every inventory station, then `getGraph` further back

### Week 1
- [ ] Normalised schema: `observation`, `station` / `station_version` (effective-dated), `river_node` / `river_reach`, `polder`, `weather_forecast_run`, `tide_prediction`, `operation_event`, `source_health`
- [ ] Parsers with recorded fixtures; timezone handling ([KI-205](../KNOWN_ISSUES.md)); QC flags ([KI-206](../KNOWN_ISSUES.md))
- [ ] De-duplicate stations across agencies ([KI-204](../KNOWN_ISSUES.md))
- [ ] Datum conversion table + unit tests ([KI-201](../KNOWN_ISSUES.md))
- [ ] Adapters: `openmeteo_flood` (+1984 backfill), `rid_reports` (operation events), `traffy_public` (privacy-safe), `navy_tide` (once the URL is found), `bma_dds` (if accessible)
- [ ] Source health, degraded-mode flags, alerting on collector failure or stale data
- [ ] Internal read API: `/health`, latest observations (not public)

### Before G1
- [ ] Nightly `pg_dump` and weekly Parquet → R2; **restore drill** timed and documented
- [ ] Other backfills: data.go.th CSV, DWR/ONWR PDFs, RID yearbooks (as available)
- [ ] Phase 1 report: coverage per station, gaps, sizes, incidents → **stop for G1**

## Exit criteria (G1)
- ≥ 7 consecutive days of collection with less than 1 % missed cycles per P1 source (excluding source outages, which are logged).
- The backfill is complete as far as the sources allow, and its extent is documented.
- The restore from R2 has been tested, and its time recorded.
