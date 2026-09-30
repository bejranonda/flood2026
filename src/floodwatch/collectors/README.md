# `floodwatch.collectors` — one adapter per data source

> **Status:** empty scaffold. Built in **Phase 1** ([plan](../../../docs/plan/phase-1-ingestion-archive.md)), after the source set is approved at gate G0.

## Responsibility
Fetch data from **one** external source on a schedule and hand it to the archive and the normalised database. External sources are feeds only. Our own database is the system of record ([ARCHITECTURE.md](../../../docs/ARCHITECTURE.md)).

## Adapter contract
Every adapter goes through the same steps in the same order:

1. **Fetch.** Make one polite HTTP request. Use the configured `HTTP_USER_AGENT`, which has to identify the app and a contact. Don't spoof a browser ([GUIDELINES §5](../../../docs/GUIDELINES.md)). Retry with exponential backoff, and use single-flight so two runs never request the same thing at once.
2. **Archive raw.** Before parsing anything, write the payload exactly as received (gzip) to the raw archive, along with the fetch time (UTC), URL, HTTP status and SHA-256. See [`../archive/`](../archive/README.md).
3. **Parse.** Turn the payload into normalised rows (`station_id, source, obs_time (UTC), level_msl, bank_level_msl, discharge, quality_flag, raw_ref`). Treat source timestamps that have no timezone as `Asia/Bangkok` (+07:00).
4. **QC.** Flag spikes, flatlines, gaps and clock errors. Never delete a reading.
5. **Report health.** Record success or failure and data age, so the API can switch to degraded mode and alerts can fire.

A failing adapter must never crash the scheduler or stop the other adapters.

## Nationwide (v0.16, D-064)
`hii_backfill` covers every HII-network gauge (focus first, 12 per run); `hii_history` refills nationwide gauges in six rotating slices; `openmeteo_cells` (every 3 h) and `openmeteo_prev_cells` (hourly, a year for 8 new cells) fetch rain for the 0.5° cells of `floodwatch.rain_cells`, 50 cells per request. Old rows are removed by `floodwatch.retention` (never BMA).

## Planned adapters (after G0 confirms them in [SOURCES.md](../../../docs/SOURCES.md))
`hii_waterlevel`, `hii_rain`, `hii_graph_backfill`, `openmeteo_forecast`, `openmeteo_ensemble`, `openmeteo_flood`, `rid_reports`, `bma_dds`, `navy_tide_pdf`. The keyed adapters (`tmd`, `gistda`) come only once the keys exist.

**Never** build an adapter against an endpoint listed under *Refuted endpoints* in [SOURCES.md](../../../docs/SOURCES.md).
