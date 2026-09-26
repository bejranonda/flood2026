# `floodwatch.forecast` — forecasting engine (model ladder L0–L7)

> **Status:** empty scaffold. Built in **Phase 2** ([plan](../../../docs/plan/phase-2-forecasting.md)). The method spec is [APPROACH_AND_METHODS.md](../../../docs/APPROACH_AND_METHODS.md).

## Build order (do not skip)
1. **Backtest harness** (rolling-origin) and metrics: RMSE, MAE, NSE, KGE, CRPS, coverage, POD/FAR/CSI.
2. **Baselines:** L0 persistence, L1 persistence + tide change, L2 climatology.
3. **L3 physical components:** harmonic tide (fitted with `utide` or from Navy tables), lag/Muskingum routing with lags estimated from data, rating curves, polder storage balance.
4. **L4** LightGBM quantile model on the residuals, then **L5** AR error correction + weather ensembles + conformal calibration (CQR/ACI).
5. Recovery-date distribution and depth-at-location products.

A model is served for a station and horizon only if it passes the acceptance gate: **skill vs persistence > 0.1 and 90 % interval coverage between 85 % and 95 %** on held-out events. Otherwise the app falls back to a lower level with wider intervals.

⚠️ Do **not** port the draft `BKKHydroEngine` from [`research/unverified/`](../../../research/unverified/README.md). Its outputs are physically implausible (KI-302 in [KNOWN_ISSUES.md](../../../docs/KNOWN_ISSUES.md)).
