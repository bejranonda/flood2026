# Phase 5 — Nationwide monitoring, then forecasts per flood type

> **Status:** 🟡 **v0.16.0 (2026-09-30): nationwide parity built (D-064)** — history, QC, forecasts and panels for every HII-network gauge. The national *layers* (dams, FFPI, DWR, GISTDA) below are still validated, not built. **Gate G5:** see the end.

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
### 5.1b Nationwide parity (v0.16.0, D-064) — done 2026-09-30
- [x] A year of history for every HII-network gauge (`hii_backfill`, `hii_history` slices); bounded retention (400 days, never BMA)
- [x] QC and forecasts for every gauge; forecaster container with a daily cached backtest
- [x] `star` inputs outside Bangkok: 0.5° rain cells, upstream gauges learned per basin
- [x] Region chips for the country; water word from the river name; twin gauges linked; national pin mode; place search Thailand-wide
- [x] Re-run `scripts/backtest_nationwide.py` after the backfill (2026-10-01 14:20 UTC): 27/19/19 of 51 over the gate at 12/24/48 h with the new inputs vs 9/8/6 without (APPROACH §19.8)
- [ ] Dam-controlled reaches (e.g. E.29/URTU07 above Ubol Ratana): release inputs, like C.13 for the Chao Phraya
### 5.2 National collectors behind a flag (lean, D-046)
- [ ] Freshness filter shared by all national collectors (KI-111)
- [ ] HII dams daily (large, medium with a fresh date, small-dam telemetry with spillway margin)
- [ ] HII FEWS: thresholds daily, FFPI every 6 h, tide daily
- [ ] GISTDA flood extent (7 days) daily, stored per H3 cell with pass dates (KI-510)
- [ ] DWR EWS hourly via the Thai egress (BE dates, status 9) — only once a reliable Thai egress exists or accepting gaps (A34)
- [x] Retention for high-volume series (v0.16: readings 400 d, rain issues 3 d, forecast runs 14 d); ⚠️ growth to re-measure after the backfill (ARCHITECTURE §8b)
- [ ] Not built: HII gates (dead feed), EGAT API (empty), GloFAS until the snapping rule is implemented (KI-509)
### 5.3 National view (only after D-046's conditions)
- [ ] Owner has sent the HII/DWR/RID notes; a reliable Thai egress exists
- [ ] Map: stations by tier, official-threshold status, reservoirs, FFPI tambons, GISTDA cells; region → basin → station/tambon
- [ ] Point check outside Bangkok: official-threshold gauges within reach, FFPI of the tambon, DWR status nearby, GISTDA cells within ~2 km (never "dry" in towns), rain (TMD words)
### 5.4 Forecasts per flood type (Phase 2 methods)
- [ ] Verify reference events from official reports (Hat Yai 2025, Mekong 2026, Northeast 2017/2019/2022) before using them as labels
- [ ] F1 regulated rivers: release scenarios once RID/EGAT rule curves are obtained; F5 Mekong: upstream-lag model; F3 flash floods: compare our rain thresholds with DWR/HII products first
- [ ] Model candidates from the Bangkok experiments ([research 2026-09-27 §8](../../research/2026-09-27_forecast_48h.md)): network STAR + rain first; SSN for values along dendritic rivers; k-NN analogues with GloFAS reanalysis; GTWR for regional rain-response; ST-GNN only as a benchmark on multi-year national data
- [ ] HII FEWS official forecasts exist for ~66 level and ~87 discharge stations nationally: extend the `hii_fews_forecast` archive and scoring (D-050) before using any of them

## Gate G5 (owner approves)
1. Every national statement in the UI carries a tier, a source and a time (GUIDELINES §6.18).
2. No verdict without an official threshold; statistical thresholds only with ≥ 5 years of history.
3. Backup and restore drill passed; disk growth measured below the free space for 12 months.
4. Agencies informed; the Thai egress has run for 7 days with gaps shown in `/api/health`.
5. A forecast for any flood type is shown only after its backtest beats persistence (§14).
