# Large-dam releases as a forecast input — backtest (2026-10-04)

Owner: "You can consider การปล่อยน้ำเขื่อน more than เจ้าพระยา, to improve the forecasting models in the other regions and basins."

**Data:** HII `analyst/dam` (50 large dams with `sub_basin_id`) and `analyst/dam_yearly_graph?data_type=dam_released&dam_id=…&year=…`
(daily release, million m³/day; the same call also returns `upper_rule_curve`, `lower_rule_curve`, bounds and average inflow).
All 50 dams had a release history for 2025–2026.

**Test** (`2026-10-04_dam_release_backtest.py`): up to 4 non-BMA gauges in the same HII sub-basin as each dam (100 gauges,
33 dams); the 45-day rolling backtest (`forecast.evaluate`) with the release (lagged one day: a day's release is reported the
next morning) and its 24 h / 72 h change as extra `star` inputs, against the same backtest without them.

| Horizon | Mean change in error | Median | > 5 % better | Worse |
|---|---|---|---|---|
| 24 h | −0.5 % (worse) | 0.0 % | 1 | 14 |
| 48 h | −0.9 % | 0.0 % | 1 | 20 |
| 72 h | −0.9 % | 0.0 % | 3 | 21 |

Best cases at 48 h: THA003 (Krasiao) 17.5 → 16.4 cm, N.22A (Khwae Noi Bamrung Daen) 43.3 → 41.2 cm, W.10B (Kiew Lom) 13.3 → 12.8 cm.

**Why no gain:** gauges just below a dam already measure its outflow and serve as learned upstream inputs; daily values with a
one-day reporting lag are coarse for 24–72 h; releases were mostly steady in the window; a shared sub-basin does not mean
"downstream of the dam". **Decision:** not adopted as an input (D-090). **Next:** dams above their upper rule curve as a
จับตา signal ("a release increase is likely"), and hourly or planned releases from RID/EGAT (MODELS §9 item 2).
