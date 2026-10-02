# Rain over the true upstream catchment (HydroBASINS) — result: no gain; not adopted

**Date:** 2026-10-02 · **Owner:** downloaded HydroBASINS (OWNER_ACTIONS HYDROBASINS) and asked to "validate and check, whether the basin data is useful".
**Script (re-runnable):** [2026-10-02_catchment_rain.py](2026-10-02_catchment_rain.py) · runs 10:26–10:29 UTC (60 sampled gauges) and 10:30–10:59 UTC (all 682 eligible gauges) on the production DB.

## Data (inspected 2026-10-02)
- `hybas_lake_as_lev01-12_v1c.zip` (413 MB): HydroBASINS v1c, Asia, customized format with lakes, levels 1–12; licence (product page): free for scientific, educational and commercial use with attribution (Lehner & Grill 2013). Level 8 used: 33,354 sub-basins in Asia, median 405 km².
- Topology: `NEXT_DOWN`. In the lake format a sub-basin whose outlet is covered by a lake is split into left/right parts that share `UP_AREA`, and the right part drains into the left (tech doc §2.3). Check: for 2,581 level-8 sub-basins touching Thailand (plus upstream), `UP_AREA` rebuilt from `NEXT_DOWN` matches within 1 % except 384, of which 360 are such split sides or lakes; 24 (~1 %) unexplained ⚠️.
- Rain: our 177 Open-Meteo 0.5° cells with a year of hindcast; 165 cell centres lie in a level-8 sub-basin (the others are at sea).

## Method
A gauge's catchment = its sub-basin plus every sub-basin whose `NEXT_DOWN` chain reaches it. Production backtest (`forecast.evaluate`, last 45 days, rolling origin; upstream gauges as learned in production) with three rain inputs: **A** the gauge's own cell (production), **H** the mean over our cells whose centre lies in the catchment (own cell always included), **P** placebo: H's recipe with another sampled gauge's catchment in a different basin. Only gauges whose catchment spans > 1 cell can differ.

## Result
| | 60 sampled (29 with > 1 cell) | **All 682 eligible (296 with > 1 cell)** |
|---|---|---|
| over the gate 12 / 24 / 48 h — A own cell | 18 / 15 / 13 | **181 / 155 / 137** |
| — H upstream catchment | 18 / 15 / 13 | **175 / 150 / 138** |
| — P placebo catchment | 18 / 15 / 11 | **169 / 139 / 106** |
| star RMSE H vs A, median (better at) 12 / 24 / 48 h | −0.3 / −0.6 / −1.5 % (17, 17, 20 of 29) | **−0.0 / −0.1 / −0.0 % (142/284, 157/283, 142/283)** |
| star RMSE P vs A, median | +1.1 / +1.6 / +2.4 % | **+0.5 / +1.5 / +2.5 %** |

The hint in the first sample (48 h better at 20 of 29) **did not replicate** on all gauges: catchment rain is a coin flip against the own cell and costs 5–6 gauges their gate at 12/24 h. The placebo is clearly worse at every horizon (48 h: 106 vs 137 gauges over the gate), so *where* the rain falls matters — but the own cell plus the learned upstream gauges (which see the catchment's rain once it reaches the river) already carry it. Large catchments behave the same (e.g. P.15 Ping, 45,540 km², 17 cells: 24 h skill 0.293 own → 0.284 catchment → 0.245 placebo).

**Conclusion: not adopted.** Same verdict as the 22-basin-mean and upstream-cells proxies ([2026-10-02_basins.md](2026-10-02_basins.md)). What could still help is finer rain over the hours before the river responds (Q43 re-test with our own hourly gauge archive, ~mid-December 2026), not a better catchment outline.

## Files
Both downloads are kept on the server in `data/basins/raw/` (git-ignored). `scripts/prepare_basins.py` makes small, reusable files next to them: `onwr_basins_22.geojson` (13 MB) and `hydrobasins_lev08_th.geojson` (8 MB; 2,581 sub-basins touching Thailand, everything upstream of them and their path to the sea), plus `README.md` and `SHA256SUMS`.
