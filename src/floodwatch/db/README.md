# `floodwatch.db` — normalised time-series database (PostgreSQL + TimescaleDB)

> **Status:** empty scaffold. Built in **Phase 1** ([plan](../../../docs/plan/phase-1-ingestion-archive.md)).

## Responsibility
This is layer 2 of the two-layer storage ([ARCHITECTURE.md §3](../../../docs/ARCHITECTURE.md)): the schema, migrations and data-access helpers.

## Planned tables (draft — finalised in Phase 1)
| Table | Purpose |
|---|---|
| `observation` (hypertable) | `station_id, source, obs_time (UTC), level_msl, bank_level_msl, discharge, quality_flag, raw_ref` |
| `station`, `station_version` | Station metadata **with history**: bank level, datum and location changes are versioned, never overwritten. Also holds upstream/downstream links and river chainage. |
| `weather_forecast_run` | **Every issued** NWP run (model, issue time, lead time, member), so backtests use forecasts exactly as issued. |
| `tide_prediction` | Navy table and own harmonic predictions (`height_llw`, `height_msl`, method). |
| `operation_event` | RID releases and diversions, BMA gate and pump notices, warnings, all stored as events. |
| `forecast_run`, `forecast_value` | **Our own** forecasts for every run, with the model version, so we can measure real skill over time. |

Use compression and continuous aggregates (hourly and daily) for fast charts. Store UTC; display Asia/Bangkok.

## Spatial side (PostGIS, D-008)
Station points, polder polygons and river reaches with chainage live in the same database via **PostGIS**. They support nearest-station and point-in-polygon lookups (the "controlling water body" for "ใกล้บ้านฉัน"), areal rain aggregation per polder, and interpolation along the chainage ([APPROACH §2](../../../docs/APPROACH_AND_METHODS.md)). Store WGS84 (EPSG:4326); compute distances and areas in UTM 47N (EPSG:32647).
