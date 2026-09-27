# Phase 5 — Nationwide monitoring, then forecasts per flood type

> **Status:** 🔎 validated, **not built** (owner, 2026-09-27: "review and validate first"; work stays on branch `research/nationwide-scope`). **Gate G5:** see the end.

## Goal
Give residents in any province, and local officials and volunteers, an honest national view: measured levels against **official** thresholds, reservoir state, the agencies' flash-flood products and satellite-observed flooding, each labelled with its tier and time. Forecasts come later, one flood type at a time, only after a backtest (D-044).

## Inputs
[APPROACH §19](../APPROACH_AND_METHODS.md) · [SOURCES §2d](../SOURCES.md) · [VALIDATION_2026-09-27_nationwide](../../research/VALIDATION_2026-09-27_nationwide.md) · [D-044, D-045, D-046](DECISIONS.md) · [KI-110, KI-111, KI-509, KI-510, KI-511](../KNOWN_ISSUES.md)

## Tasks (in order)
### 5.0 Bangkok first (D-045)
- [ ] Compare HII `canal_waterlevel` warning/critical with the relay's for the 156 shared BMA gauges; then HII as primary, relay as fallback; add the 73 missing gauges
- [ ] BMA road sensors (`flood_road`, 262, cm on the road): own table, never m MSL; map layer; point-check evidence; tests
- [ ] Navy tide predictions (HII FEWS, 28 stations) and RID discharge thresholds (C.2, C.13) in the river station sheets
### 5.1 Safety net (D-046)
- [ ] Nightly local `pg_dump -Fc` (keep 3) + one tested restore into a throwaway container (KI-511; owner question Q29)
### 5.2 National collectors behind a flag (lean, D-046)
- [ ] Freshness filter shared by all national collectors (KI-111)
- [ ] HII dams daily (large, medium with a fresh date, small-dam telemetry with spillway margin)
- [ ] HII FEWS: thresholds daily, FFPI every 6 h, tide daily
- [ ] GISTDA flood extent (7 days) daily, stored per H3 cell with pass dates (KI-510)
- [ ] DWR EWS hourly via the Thai egress (BE dates, status 9) — only once a reliable Thai egress exists or accepting gaps (A34)
- [ ] 90-day retention for high-volume series; growth measured and written to ARCHITECTURE §9
- [ ] Not built: HII gates (dead feed), EGAT API (empty), GloFAS until the snapping rule is implemented (KI-509)
### 5.3 National view (only after D-046's conditions)
- [ ] Owner has sent the HII/DWR/RID notes; a reliable Thai egress exists
- [ ] Map: stations by tier, official-threshold status, reservoirs, FFPI tambons, GISTDA cells; region → basin → station/tambon
- [ ] Point check outside Bangkok: official-threshold gauges within reach, FFPI of the tambon, DWR status nearby, GISTDA cells within ~2 km (never "dry" in towns), rain (TMD words)
### 5.4 Forecasts per flood type (Phase 2 methods)
- [ ] Verify reference events from official reports (Hat Yai 2025, Mekong 2026, Northeast 2017/2019/2022) before using them as labels
- [ ] F1 regulated rivers: release scenarios once RID/EGAT rule curves are obtained; F5 Mekong: upstream-lag model; F3 flash floods: compare our rain thresholds with DWR/HII products first

## Gate G5 (owner approves)
1. Every national statement in the UI carries a tier, a source and a time (GUIDELINES §6.18).
2. No verdict without an official threshold; statistical thresholds only with ≥ 5 years of history.
3. Backup and restore drill passed; disk growth measured below the free space for 12 months.
4. Agencies informed; the Thai egress has run for 7 days with gaps shown in `/api/health`.
5. A forecast for any flood type is shown only after its backtest beats persistence (§14).
