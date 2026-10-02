# GloFAS for a 3–7 day outlook at main-river gauges: upper-bound test → no gain, stop

**Date:** 2026-10-02 · **Owner:** GloFAS "for longer outlook", shown only after a backtest (D-060 rule). Decision: D-069.
**Script:** [2026-10-02_glofas_outlook.py](2026-10-02_glofas_outlook.py) (worker container; Open-Meteo flood API, keyless, non-commercial). Two runs, 20:19 and 21:06 UTC.

## Method
- Open-Meteo serves GloFAS v4 reanalysis/consolidated + today's forecast, **not forecasts as issued** (its docs; a past date returns the same series for `seamless_v4` and `forecast_v4`). So the test is an **upper bound**: if even GloFAS's own best estimate of discharge — including its *future* change, which no forecast could know — does not help, archived forecasts (EWDS) cannot either.
- 12 gauges along the chain: C.2, C.13, C.3, C.7A, C.36, C.37, C.35, S.26 (with RID measured discharge), CPY012, CPY014, T.1, THA008. Daily mean level, 2025-09-25 → 2026-10-01 (371 days), chronological split: first 60 % train, test from 2026-05-07 (includes this flood).
- Target: level change over h = 3, 5, 7 days. Models (ridge): persistence · AR (own 1- and 3-day change) · AR + GloFAS now (log Q, 3-day change; knowable at t) · AR + GloFAS perfect (adds the true future change of log Q).
- Snapping (KI-509): run 1 = largest 14-day mean within ±0.1° (landed on window corners, downstream of confluences: C.35 at 3.4× measured); run 2 = the cell closest to the measured 14-day flow, else the nearest cell with ≥ half the largest flow. Weight kept ~650 Open-Meteo calls per run (see KI-264).

## Results (run 2; run 1 within ±0.01)
| Horizon | Median skill vs AR: GloFAS now | GloFAS perfect | AR vs persistence | Gauges where perfect beats AR by ≥ 10 % |
|---|---|---|---|---|
| 3 d | −2.3 % | −1.6 % | +13 % | 0 / 12 |
| 5 d | −2.9 % | −1.8 % | +4 % | 0 / 12 |
| 7 d | −4.5 % | −2.5 % | −2.4 % | 0 / 12 |

GloFAS daily discharge vs RID measured (371 days at C.2/C.13, 62–109 days elsewhere): r = 0.57 (C.2), 0.60 (C.13), ≤ 0.33 at the others; ratio GloFAS/measured from 0.06 to 3.4 depending on the cell. Tha Chin cells give ~22 m³/s.

## Verdict
- **No GloFAS input, no collector, no EWDS backtest** (the EWDS token works, 2026-10-02, but would only test forecasts that can do no better than this upper bound). Reason in one line: the lower Chao Phraya is run by dams, the Chao Phraya Dam (C.13) and diversions; a global 5 km daily model does not know them, and our gauges plus C.13's planned release already carry what it would add.
- A 3–7 day outlook is weak with any method here (at 7 d even AR loses to "no change"); the 48 h horizon stays (D-060).
- Revisit if RID publishes release plans further ahead, or for rivers without dams upstream (e.g. Mun/Chi backwater) where GloFAS might do better — a separate test.
