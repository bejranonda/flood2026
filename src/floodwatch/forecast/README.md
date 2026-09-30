# `floodwatch.forecast` — forecasting engine (model ladder L0–L7)

> **Status:** empty scaffold. Built in **Phase 2** ([plan](../../../docs/plan/phase-2-forecasting.md)). The method spec is [APPROACH_AND_METHODS.md](../../../docs/APPROACH_AND_METHODS.md).

## Build order (do not skip)
1. **Backtest harness** (rolling-origin) and metrics: RMSE, MAE, NSE, KGE, CRPS, coverage, POD/FAR/CSI.
2. **Baselines:** L0 persistence, L1 persistence + tide change, L2 climatology.
3. **L3 physical components:** harmonic tide (fitted with `utide` or from Navy tables), lag/Muskingum routing with lags estimated from data, rating curves, polder storage balance.
4. **L4** LightGBM quantile model on the residuals, then **L5** AR error correction + weather ensembles + conformal calibration (CQR/ACI).
5. Recovery-date distribution and depth-at-location products.

A model is served for a station and horizon only if it passes the acceptance gate: **skill vs persistence > 0.1 and 90 % interval coverage between 85 % and 95 %** on held-out events. Otherwise the app falls back to a lower level with wider intervals.

⚠️ Do **not** port the draft `BKKHydroEngine` ([research](../../../research/bangkok_flood_calculation_forecasting_engine.md)). Running it gives physically implausible output ([validation §C12](../../../research/VALIDATION_2026-09-26.md), KI-302 in [KNOWN_ISSUES.md](../../../docs/KNOWN_ISSUES.md)). Its equations are fine as a reference; its numbers are not.

**v0.16 (D-064):** every gauge runs the same ladder. `upstream.py` learns up to 2 upstream gauges per gauge outside the focus area (same basin, leading 24 h change, before the backtest window); `forecast_model` caches each gauge's backtest ~20 h; the `forecaster` container (`worker --role forecaster`) runs `run_all` every 30 min and `upstream_learn` daily. Report: `scripts/backtest_nationwide.py`.

