# Measured rain as a forecast input (Q43) — result: no gain from daily totals; hourly archive kept for a re-test

**Date:** 2026-10-01 · **Owner request:** "Consider the factors in modeling and validate the results, think carefully."
**Script (re-runnable):** [2026-10-01_measured_rain.py](2026-10-01_measured_rain.py) · run 13:10–13:48 UTC on the production DB.

## Data (verified 2026-10-01, api-v3.thaiwater.net, honest UA)
- No public **hourly** rain history: HII's web app (`www.thaiwater.net` bundle, 90 endpoints listed) has `public/rain_24h` (now), `rain_today`, `rain_yesterday`, `rain_monthly`, `rain_yearly`, and per-gauge `provinces/rain{3,5,7,15}d_graph`.
- `provinces/rain3d_graph?station_id=<id>&start_date&end_date` gives **daily** totals per gauge (`station_id` = `station.id` in `rain_24h`), at most ~31 days per request ("limit date range"), back to at least 2024-10.
- **Label = the day the 24 h window ends.** Against our own hourly `rain_1h` (60 Bangkok gauges, 27–30 Sep), the best-matching window ends ~00:00–02:00 ICT on the labelled day (r = 0.64–0.66); 07–07 ending on the day r = 0.53; midnight-to-midnight of the label r = 0.29.
- **Values ≈ 7× the hourly sums** (median; exact within 0.5 mm only 19 %; BKK021 27 Sep: 274 mm vs 11.2 mm). Unexplained ⚠️ — either product may be wrong; only the information was used (ridge standardises inputs).

## Method
Production `evaluate` (last 45 days, rolling origin, no leakage) per gauge, three runs: **A** production `star` (upstream, dam release, forecast rain); **B** A + R1/R3/R7 (last complete daily total and 3/7-day sums, mean of ≤ 3 gauges within 10 km, QC 0–400 mm); **P** A + the same features from day-shuffled rain (placebo). Timing rule (leakage-safe under any plausible convention): the value labelled D is used from 08:00 ICT on D. Unit-checked. Event check: star RMSE on test hours after a day with ≥ 35 mm.

## Result
| | Bangkok (30 sampled, 28 compared) | Nationwide (24 sampled, 21 compared) |
|---|---|---|
| star RMSE change with rain, median at 6/12/24/48 h | +0.3 / +0.2 / −0.0 / +0.6 % | −0.1 / −0.5 / −1.2 / −0.9 % |
| gauges improved (rain vs placebo) | 10/12/14/12 of 28 vs 8/14/12/12 | 11/12/12/12 of 21 vs 8/10/8/11 |
| after a ≥ 35 mm day, RMSE 12 h / 24 h (persistence · star · star+rain) | 0.232·0.196·0.200 / 0.271·0.237·0.242 m | 0.273·0.259·0.259 / 0.403·0.365·0.373 m |

**Conclusion:** daily measured rain adds nothing beyond the current inputs (Bangkok: same as placebo; nationwide: −0.5 to −1.2 % median, 12/21 gauges, not significant; event hours slightly worse). Why: a daily total is usable only hours after the canals already responded — the gauge's own recent change carries it — and its quality is doubtful (7× scale, r ≈ 0.65). **Not shipped.**

## What would help, and what was done
- **Hourly rain of the last hours** is the input with a physical reason to help (rain that fell but has not reached the canals). HII does not serve its history, so only our own archive can: `retention` now keeps hourly `rain_obs` for 400 days at the 2,260 gauges within ~10 km of a water gauge (others 14 days). Re-test with this script's method once ≥ 75 days of hourly data exist (~mid-December 2026), using hourly accumulations (1/3/6 h, available ~1 h after the hour).
- `forecast.star_features` accepts `ex["extra"]` columns (inert unless supplied), so the re-test needs no model change.
