# `floodwatch.archive` — immutable raw payload archive

> **Status:** empty scaffold. Built in **Phase 1** ([plan](../../../docs/plan/phase-1-ingestion-archive.md)).

## Responsibility
This is layer 1 of the two-layer storage ([ARCHITECTURE.md §3](../../../docs/ARCHITECTURE.md)). It stores every fetched payload **exactly as received** and keeps it forever. When a parser is fixed or a source changes its schema, we reprocess from here instead of losing history.

## Contract
- **Write once.** Nothing is overwritten or deleted.
- **Path:** `{TELEMETRY_ARCHIVE_PATH}/{source}/{YYYY}/{MM}/{DD}/{fetch_ts_utc}_{sha256[:12]}.{ext}.gz`
- **Sidecar metadata** for each object (or a manifest row): source, URL, HTTP status, fetch time (UTC), SHA-256, byte size, collector version.
- **Replication:** copy to Cloudflare R2 (`R2_*` settings in [`.env.example`](../../../.env.example)) so the history survives if the VPS dies.
- **Dedup:** an identical SHA-256 from the same source within one collection cycle may be stored as a reference instead of a second copy.
