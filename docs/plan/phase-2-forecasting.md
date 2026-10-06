# Phase 2 — Forecasting (scientifically grounded, spatio-temporal)

> **Status:** ⏳ after G1 (baseline work can start earlier on backfilled data). **Gate G2:** acceptance gate per station × horizon ([GUIDELINES §4.3](../GUIDELINES.md)).

## Goal
Probabilistic forecasts at +12 h / 1 / 2 / 3 / 7 d, and an estimate of when levels return to normal, that **beat the baselines** and have **calibrated intervals**. They must be explicit in space (network, polders) and time (lags, periodicities, issue vs valid time).

## Inputs
[APPROACH_AND_METHODS](../APPROACH_AND_METHODS.md) (esp. §2 spatio-temporal) · [forecast scaffold](../../src/floodwatch/forecast/README.md) · [KNOWN_ISSUES §3](../KNOWN_ISSUES.md)

## Tasks
### Spatial and temporal foundations (APPROACH §2)
- [ ] River graph: nodes, reaches, **chainage along the centreline**, confluences and diversions
- [ ] Polder / drainage-zone polygons with pumps and gates (sources: BMA, OSM, literature) — mark unknowns
- [ ] Areal rain aggregation per polder (gauges, and NWP grids area-weighted); resampling rules implemented
- [ ] **Lag estimation** per reach and flow class from HII discharge (C.2 → C.13 → C.3 → C.35), later Bang Sai
- [ ] Spatio-temporal QC (neighbour and travel-time consistency)

### Harness and baselines
- [ ] Rolling-origin backtest with an **embargo**; leave-station-out splits; metrics (RMSE, MAE, NSE, KGE, CRPS, coverage, POD/FAR/CSI, peak timing)
- [ ] L0 persistence, L1 persistence + tide, L2 climatology (the "normal band")

### Physical layer (L3)
- [ ] Harmonic tide per tidal station with `utide` (interim 30-day fits → ≥ 1 year); discharge-dependent damping; Navy tables if found
- [ ] Rating curves for non-tidal stations
- [ ] Muskingum per reach; RID release plans as scenario boundaries
- [ ] Polder storage model with pump limits and minimum levels; mass-balance unit test

### Statistical layer (L4–L5)
- [ ] LightGBM quantile models (global per regime) with graph-lagged, neighbour, areal-rain, tide and calendar features; monotonic constraints
- [ ] AR error correction; ensemble weather runs; CQR + ACI per station × lead
- [ ] Training on **as-issued** NWP only once enough runs are archived; until then, widened intervals and disclosure ([KI-305](../KNOWN_ISSUES.md))

### Products
- [ ] Recovery-date distribution (milestones: below bank / below warning / within the normal band), with conditions
- [ ] Depth-at-location module (controlling water body, DEM → MSL, HAND, probability categories, satellite and crowd overrides)
- [ ] Skill report per station × lead × regime, with maps → **stop for G2**

## Progress (2026-10-04, v0.25.0–v0.25.2)
- [x] **Honest improvement harness** (`research/q52_harness.py`): `star` trained before the 45-day window; method + gate chosen on the first half, scored on the second; variants confirmed on a disjoint gauge sample (MODELS §5d).
- [x] `star` V12 inputs (7/30-day means, 1/3/72 h changes) — D-092; up to 4 learned upstream gauges after 90 days — D-093.
- [x] Rejected with evidence: averaging methods, a stricter selection rule, trend-dependent and shorter-window bands.
- [x] Served-band check against reality (30 days): 24 h on target; 72 h overconfident (KI-287 → Q54).
- [ ] Flood Hub forecasts as an input (+0.9 points at 72 h; Q55) · WeatherNext rain backtest (blocked by BigQuery quota; Q53) · RID discharge as upstream inputs · rebound-forecast guard if KI-292 confirms.

## Exit criteria (G2)
- For every station and horizon shown: skill vs persistence > 0.1 **and** 90 % coverage of 85–95 % on held-out data ([GUIDELINES §4.2](../GUIDELINES.md): later in time, a disjoint sample, the newest season). Otherwise it's served at a lower level with wider intervals, documented.
- Forecasts are stored per run with the model version.
