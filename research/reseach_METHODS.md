# METHODS.md — Calculation & Forecasting Methods for Bangkok / Central Thailand Water Levels

> Research date: 26 Sep 2026. Companion to `SOURCES.md` (data sources).
> Audience: developers and AI coding agents implementing the forecasting engine.
> Principle: **hybrid = physics-informed structure + statistical/ML learning + calibrated uncertainty**, always benchmarked against simple baselines.
> Master Documentation: See [README.md](../README.md), [docs/APPROACH_AND_METHODS.md](../docs/APPROACH_AND_METHODS.md), and [docs/GUIDELINES.md](../docs/GUIDELINES.md). Note: Standardized file available at [research_METHODS.md](research_METHODS.md).

---

## 0. Summary for implementers

1. The study area has **three hydraulic regimes with different drivers**. Build one model family per regime, not one model for everything:
   - **A. Upstream river reach** (C.2 Nakhon Sawan → C.13 Chao Phraya Dam → C.3 → C.35 Ayutthaya → C.29A Bang Sai): driven by upstream flow and dam releases. Forecastable days ahead.
   - **B. Tidal lower Chao Phraya** (Bang Sai → Nonthaburi → Bangkok → Fort Phra Chunlachomklao): driven by **upstream discharge at Bang Sai + tide at the river mouth**.
   - **C. Bangkok khlongs / urban polders** (e.g. BKK008 Saen Saep): driven by **local rainfall, pumping/gates, and the outlet (river/tide) level**. Current (Sep 2026) flooding is mainly this regime.
   - **D. Inundation at a user's location**: derived from A–C plus ground elevation and observed flood extent.
2. Recommended engine per station: `forecast = physically-structured baseline (tide + routed flow + rain storage) + gradient-boosted residual model + error correction`, with **conformalized quantile intervals**.
3. Horizons: +12 h, +1 d, +2 d, +3 d, +7 d. Skill drops with horizon; for +7 d show a **category outlook** (up/stable/down, probability of exceeding bank), not a precise number.
4. "When will it return to normal?" = **recession analysis + forecast ensemble → probability distribution of the date** the level drops below the bank level and below the seasonal normal.
5. Every model must beat **persistence** and **persistence + tide** in backtesting before it is shown to users.

---

## 1. Evidence base (what the literature and operators do)

| Finding | Implication for us |
|---|---|
| At Bangkok Memorial Bridge (C.4, ~48 km from the mouth) hourly levels are governed mainly by **upstream discharge at Bang Sai (km 112) and tide at Fort Chula (km 1)**; tidal backwater raises flood stages. An ANN on these inputs forecast hourly levels. | Regime B model inputs = Bang Sai Q (lagged) + tide (observed and predicted). |
| For six key Chao Phraya stations, **XGBoost and Random Forest with rainfall input outperformed deep neural nets** for 1-day and 1-week water level prediction; inputs were past level, rainfall, reservoir outflow, and upstream discharge **with travel-time lags** (test R² 0.743–0.995). | Start with gradient boosting + physically chosen lagged features; add deep learning only if it wins in backtests. |
| Similar XGBoost/RF studies at C.2 and C.29 used 1990–2022 level, weather, dam outflow and upstream flow data. | Long history exists; backfill it. |
| Navy's harmonic tide model predicts the overall trend well but has high individual errors; ML models were compared against it. A 2026 study integrates **future tide** into ML for daily peak levels in tide-dominated reaches. | Use harmonic tide as a feature, and model the **non-tidal residual** with ML. |
| Integrated HEC-RAS model of the lower Chao Phraya used ANN for upstream boundary, **harmonic analysis for the tidal downstream boundary** and regression for lateral inflows, giving **~4 days** lead time (verified on Jun–Nov 2011). | Our component split mirrors proven operational practice. |
| DHI's post-2011 DSS (MIKE-based) forecasts levels and discharges at **28 locations up to 7 days** for the whole basin. | 7 days is the realistic upper bound for quantitative river forecasts. |
| In 2011, floodplain water moved **~120 km in about two weeks** from Chao Phraya Dam area toward Bangkok; what people most wanted was short-term direction of flood water (FRICS/JICA). | Overland flood propagation is far slower than in-channel waves; treat them separately. |
| Google's global LSTM model gives reliable extreme-flood predictions **up to 5 days** ahead, similar to or better than GloFAS nowcasts (Nearing et al., Nature 2024). | LSTM is a valid later upgrade, especially with ensemble weather input. |
| BMA's drainage system is designed for about **60 mm/h**; heavier bursts (80–100+ mm) cause street/khlong flooding. BMA monitors **55 flow stations and 270 pump stations**. | Rain intensity above ~60 mm/h is a key nonlinear feature for regime C. |

---

## 2. Architecture of the forecasting engine

```
               ┌──────────── inputs (archived, as-issued) ────────────┐
 observed WL/Q │  HII telemetry, RID C-stations, BMA khlongs           │
 rainfall obs  │  HII/BMA gauges, radar                                │
 rain forecast │  Open-Meteo ECMWF/GFS/ICON + ensembles, TMD WRF       │
 tide          │  Navy predictions + own harmonic fit                  │
 operations    │  RID planned releases, BMA gate/pump notices (events)  │
 upstream Q    │  GloFAS (Open-Meteo Flood API)                        │
               └───────────────────────────────────────────────────────┘
                                   │
          ┌────────────────────────┼─────────────────────────┐
          ▼                        ▼                         ▼
 [1] Physical baseline    [2] ML residual model      [3] Error correction
  - tide (harmonic)         - LightGBM quantile         - AR(1..p) on last
  - routing (lag/Muskingum)   per horizon, global         observed residuals
  - khlong storage balance    across stations           - blends out with
  - rating curves                                         horizon
          └────────────────────────┬─────────────────────────┘
                                   ▼
                [4] Ensemble over weather members → spread
                                   ▼
                [5] Conformal calibration (per station × horizon)
                                   ▼
        [6] Products: level fan chart, trend, P(exceed bank),
            recession date distribution, depth estimate at user point
```

Rules:
- Train on **forecast inputs as they were issued** (archived NWP runs), not on observed future rain. Training on observed rain ("perfect prognosis") overstates skill. Until enough archived forecasts exist, train with observed rain but **inflate intervals** and flag in METHODS.
- One **global model** across stations of the same regime (with station ID/static attributes as features) generalises better than hundreds of tiny models.
- Re-run on every data update (10 min); retrain weekly; recalibrate conformal intervals daily.

---

## 3. Core calculations

### 3.1 Derived quantities (shown in UI, also features)

| Quantity | Formula | Notes |
|---|---|---|
| Freeboard (ระยะห่างจากตลิ่ง) | `fb = H_bank − H` | m; negative = overtopping bank |
| % of bank | `p = (H − H_bed) / (H_bank − H_bed)` | HII's `storage_percent` if bed level unknown |
| Rate of change | `dH/dt` over 1, 3, 6, 24 h using a robust slope (Theil–Sen) on smoothed data | Tidal stations: compute on **tidally filtered** series (see 3.2) or on daily max |
| Trend class | stable if `|dH/dt| < k·σ_noise` ; rising/falling otherwise | `σ_noise` estimated per station from calm periods; typical k = 2 |
| Status class | ปกติ / เฝ้าระวัง / เตือนภัย / วิกฤต from freeboard thresholds | Prefer official thresholds (HII situation level, BMA warning levels, e.g. Pak Khlong Talat wall 3.0 / warning 2.8 m MSL) |
| Daily max/min | per local day | Tidal stations: users care about **daily high water** |

### 3.2 Tide (regime B and outlets of regime C)

**Harmonic model**

`η(t) = Z0 + Σ_k f_k(t)·H_k·cos(ω_k t + V_k(t) + u_k(t) − g_k)`

- Fit with `utide` (Python) on ≥ 1 year of hourly data (ideally 18.6-year nodal cycle handled via f,u corrections). Navy uses 112 constituents; 30–60 main constituents are usually enough for forecasting (M2, S2, K1, O1, N2, K2, P1, Q1, M4, MS4, MN4 and shallow-water terms, plus long-period Sa, Ssa for seasonal mean level).
- In the Gulf of Thailand diurnal constituents (K1, O1) are strong; spring–neap and diurnal inequality control the daily high water.
- Convert Navy LLW-referenced predictions to MSL per station.

**Non-tidal residual (surge + river + wind)**

`r(t) = H_obs(t) − η(t)`

- The residual is what the ML model predicts in regime B. It rises with Bang Sai discharge and with onshore/southerly wind setup.
- Low-pass filter (e.g. Godin filter or 25-h moving average) to get the **tidally averaged level**, which is the right signal for trend and recession.

### 3.3 Rating curves (stage ↔ discharge)

`Q = a · (H − H0)^b`

- Fit per station where both H and Q exist (RID C-stations, HII graph `discharge`). Use log-linear least squares with H0 grid search; refit when the residuals drift (channel change).
- Hysteresis (loop rating) appears in flood waves; add `dH/dt` term (Jones formula) if needed.
- Not valid in tidal reaches (backwater): there, use discharge from RID/BMA flow stations directly, or regime-B regression.

### 3.4 Travel time and routing (regime A → B)

**Step 1 – Estimate lags from data** (do not hard-code):

`lag* = argmax_τ corr(ΔQ_up(t−τ), ΔQ_down(t))` using differenced series during flood seasons; compute per reach and per flow class (waves travel faster at higher flows until the floodplain is engaged, then slower).

Indicative order of magnitude to sanity-check results (must be re-estimated): in-channel waves take roughly a day from Nakhon Sawan to Chao Phraya Dam and one to two more days to Bang Sai; overland/floodplain flooding travels much slower (≈ two weeks for 120 km in 2011).

**Step 2 – Flow balance at control points**

```
Q_C13(t)    ≈ Q_C2(t − τ1) + Q_SakaeKrang(t − τ2) − diversions_upstream_of_dam
Q_BangSai(t)≈ Release_C13(t − τ3) − Σ diversions(Noi, Tha Chin, Chai Nat–Pasak canals, retention areas)
              + Q_Pasak(Rama VI Dam)(t − τ4) + lateral inflow
```

RID publishes diversions and releases (e.g. 3 Oct 2024: east-bank canals 140 m³/s, west-bank 236 m³/s; Pasak Jolasid 350 m³/s; Bang Sai ~1,821 m³/s). Store these as time series of "operations".

**Step 3 – Muskingum routing (for smooth waves between gauges)**

```
S = K [x I + (1 − x) O]
O_{t+1} = C0·I_{t+1} + C1·I_t + C2·O_t
C0 = (Δt − 2Kx) / (2K(1−x) + Δt)
C1 = (Δt + 2Kx) / (2K(1−x) + Δt)
C2 = (2K(1−x) − Δt) / (2K(1−x) + Δt)
```

- Calibrate K (≈ travel time) and x (0–0.5) per reach on past floods (2011, 2017, 2021, 2022, 2024). Muskingum–Cunge if cross-section data are available.
- Dam releases are **controlled**: for future days use **RID's announced release plan** as the upstream boundary (scenario), not a statistical extrapolation. Show "based on RID plan of X m³/s".

**Step 4 – Stage at downstream stations**

- Non-tidal stations (C.3, C.35…): `H = rating⁻¹(Q_routed)` + ML residual.
- Tidal stations (Bangkok river): regime B model (3.5).

### 3.5 Regime B model — tidal Chao Phraya (Bangkok, Nonthaburi, Pathum Thani, Samut Prakan)

`H(t+h) = η(t+h) + f(Q_BangSai(t+h−τ), r(t), wind(t+h), rain_local, season) + ε`

- `η(t+h)` = predicted astronomical tide at the station (known in advance → strong predictor for all horizons).
- `f` = LightGBM (quantile loss) or a simple linear model as baseline: residual ≈ α + β·Q_BangSai^γ.
- Predict the **daily high water** separately (users worry about the peak): `Hmax_day = max over day`, with features daily-max tide + tidally averaged residual.
- High-tide warning periods (ONWR/Navy) and spring tides coinciding with high Bang Sai flow are the dangerous combination → add interaction feature `η_max_day × Q_BangSai`.

### 3.6 Regime C model — Bangkok khlongs and polders (rain-driven)

**Conceptual storage balance per drainage zone (polder):**

```
dS/dt = A · C · P(t) + Q_in(t) − Q_pump(t) − Q_gate(t)
H_khlong = g(S)                (stage–storage curve fitted from observations)
Q_gate  ≈ 0 when H_outlet (river/tide) > H_khlong  (gravity drainage blocked)
Q_pump ≤ Q_pump_max            (capacity-limited)
```

- `A` = zone area, `C` = runoff coefficient (0.7–0.9 urban), `P` = rain rate.
- Drainage design ≈ 60 mm/h: include features `max(0, P_1h − 60)` and `P_1h > 60` flags.
- Without published pump/gate logs, learn the net effect statistically: LightGBM with features
  - rain accumulations over 1, 3, 6, 12, 24, 72 h (observed, zone-averaged gauges + radar),
  - **forecast** rain accumulations for the horizon (ensemble mean + P90),
  - current level, `dH/dt`, level 6/12/24 h ago,
  - outlet level (Chao Phraya or downstream khlong) and predicted tide at outlet,
  - upstream inflow from outside Bangkok (e.g. Pathum Thani side via Khlong Hok Wa, Rangsit) for the eastern zone,
  - hour of day, days since event start, antecedent 7-day rain (soil/storage saturation).
- **Nowcasting 0–3 h**: radar extrapolation (optical flow, e.g. `pysteps`) gives better short-term rain than NWP; BMA publishes a 3-h rain forecast updated hourly.
- Khlong levels respond within **hours**; beyond 24–48 h skill depends almost entirely on rain forecast quality → present +2 d/+3 d as ranges conditioned on rain scenarios ("ถ้าฝนตกหนักอีก… / ถ้าฝนหยุด…").

### 3.7 ML model specification (all regimes)

**Primary: LightGBM, direct multi-horizon**

- Target: `ΔH_h = H(t+h) − H(t)` (change is easier to learn than level), for h ∈ {1…12 h hourly, 24, 48, 72, 168 h}. Either one model per horizon or horizon as a feature.
- Loss: quantile (τ = 0.05, 0.25, 0.5, 0.75, 0.95) → fan chart.
- Features: see 3.5/3.6 + static station attributes (bank level, distance to mouth, regime, zone), calendar (day of year sin/cos).
- Monotonic constraints where physics is clear (more upstream Q or rain ⇒ not lower level).
- Validation: time-based splits only (see §6); never shuffle.

**Secondary (upgrade path)**
- **LSTM / Temporal Fusion Transformer** (e.g. `neuralhydrology`, `neuralforecast`) trained globally across stations with hindcast + forecast weather sequences, as in Google's flood model (hindcast LSTM + forecast LSTM).
- **SARIMAX** as interpretable statistical baseline for single stations with exogenous tide and flow.

**Error correction (data assimilation light)**
`ε̂(t+h) = φ^h · ε(t)` where `ε(t) = H_obs(t) − H_model(t)`, φ fitted per station (AR(1)); larger lags AR(p) if useful. This removes persistent bias at short horizons and fades out automatically.

### 3.8 Weather uncertainty → ensemble

- Run the model once per ensemble member (ECMWF ENS / GFS ensemble via Open-Meteo) → distribution of H(t+h).
- Combine with model error: final samples = member forecast + resampled/conformal residual.
- For horizons > 3 days, rain-forecast uncertainty dominates; report probabilities (e.g. "โอกาสน้ำล้นตลิ่ง 30%").

### 3.9 Calibrated uncertainty (conformal prediction)

- **Conformalized Quantile Regression (CQR)**: fit quantile models, then widen/narrow intervals using a calibration set so that coverage holds (e.g. 90%). Implementation: `mapie.regression.ConformalizedQuantileRegressor` supports LightGBM.
- Hydrological series are **non-stationary** (managed releases, climate): use **Adaptive Conformal Inference** (Gibbs & Candès 2021) or a rolling calibration window (last N events), per station × horizon.
- Monitor realised coverage daily; if 90% intervals cover < 85% over the last 2 weeks, widen and alert.

### 3.10 "When will it return to normal?" (recession & recovery)

**Definitions (per station)**
- `H_bank`: bank level (HII `min_bank`).
- `H_normal(doy)`: seasonal normal = median level for that day-of-year over past years (exclude flood years or use median, not mean). Also "normal band" = P25–P75.
- Recovery milestones: (1) below bank, (2) below warning level, (3) back within normal band.

**Recession model**
- Tidally filtered level `H̄` (or discharge) during falling limbs typically follows an exponential decay:
  `H̄(t) − H_base = (H̄0 − H_base) · e^{−(t−t0)/k}`
  (equivalently `Q(t) = Q0 · e^{−t/k}` for discharge).
- Estimate `k` per station from historical recessions (master recession curve); allow `k` to depend on level (two-segment recession: fast channel drainage, slow floodplain/polder drainage).
- Polders (regime C): recession limited by pump capacity: `dS/dt ≈ −Q_pump_max + inflow` → nearly **linear** drawdown while pumps run at capacity → estimate `dH/dt` from recent falling periods.

**Output**
- Combine: forecast paths (ensemble/quantiles) for days 1–7 + recession extrapolation beyond → for each path, first date crossing each milestone → **distribution of recovery dates** (median + 80% range).
- Always conditional: "หากไม่มีฝนตกหนักเพิ่มเติม" (if no further heavy rain) and "ตามแผนการระบายน้ำของกรมชลประทาน". If new rain is forecast, show recovery as "not yet estimable".

### 3.11 Flood depth estimate at the user's location (regime D)

1. **Assign the controlling water body**, not simply the nearest station:
   - Inside BMA flood-protection walls/polders → the khlong station(s) of that drainage zone.
   - Outside dikes along the Chao Phraya/Noi/Pasak → nearest river station, interpolating the water surface along the river chainage between upstream and downstream stations (linear in distance, plus tide phase lag for tidal reach).
2. **Ground elevation** `z_g` from the best DEM (FABDEM preferred: ranked first against 65 LiDAR sites, reducing building/forest errors vs Copernicus DEM; typical RMSE ~1.2–1.5 m in flat/coastal areas). Convert DEM vertical datum (EGM2008) to Thai MSL (Ko Lak) with a local offset.
3. **Depth** `d = H_ws − z_g`, only if the point is hydraulically connected (HAND model: height above nearest drainage `< H_ws − H_channel`).
4. Because DEM error (≈ 1 m) is often larger than flood depth, report a **probability**: `P(d > 0) = Φ((H_ws − z_g)/σ)` with `σ² = σ_DEM² + σ_forecast²`, in categories (น้ำไม่น่าจะถึง / อาจท่วม / มีโอกาสสูงที่จะท่วม).
5. Cross-check with **GISTDA satellite flood extent** (observed) and **flood recurrence 2011–2023**; if satellite shows flooding, override "unlikely".
6. Let users enter their own floor/ground height ("บ้านสูงกว่าถนนกี่ ซม.") to personalise.

---

## 4. Horizon-by-horizon method matrix

| Horizon | Regime A (upstream river) | Regime B (tidal river) | Regime C (khlongs) | Expected quality |
|---|---|---|---|---|
| **+12 h** | Persistence + routing of already-observed upstream flow | Astronomical tide + current residual (AR) + Q_BangSai lag | Radar nowcast + NWP + storage/ML | High |
| **+1 d** | Routing of observed flow + RID release plan | Tide + routed Q + ML | NWP rain + ML | Good (C depends on rain forecast) |
| **+2 d** | Routing + planned releases | Tide + routed Q + ML | Ensemble rain, scenario ranges | Moderate |
| **+3 d** | Routing + releases + GloFAS | Tide + routed/planned Q | Ensemble, wide ranges | Moderate/low |
| **+7 d** | GloFAS ensemble + reservoir status + ENS rain | Tide (exact) + scenario Q | Category outlook only | Low → show probabilities / categories |

---

## 5. Model ladder (build in this order)

| Level | Model | Purpose |
|---|---|---|
| L0 | Persistence `H(t+h)=H(t)` | Mandatory baseline |
| L1 | Persistence + tide change `H(t)+η(t+h)−η(t)` (tidal stations) | Baseline for regime B |
| L2 | Climatology / seasonal normal | Baseline for +7 d |
| L3 | Physical components: harmonic tide, lag/Muskingum routing, rating curves, storage balance | Interpretable core |
| L4 | LightGBM quantile residual model (global per regime) | Main production model |
| L5 | + AR error correction + ensemble weather + conformal calibration | Production uncertainty |
| L6 | LSTM/TFT global model (optional) | Upgrade if it beats L5 in backtests |
| L7 | 1D hydrodynamic model (HEC-RAS unsteady) for Chao Phraya main stem | Long-term; needs cross-sections & structures |

Show users only the best model that has passed §6 acceptance for that station and horizon; otherwise fall back to lower levels and widen intervals.

---

## 6. Validation and acceptance

**Backtesting**: rolling-origin (walk-forward) — train up to T, forecast T+h, move T forward; include flood years 2011, 2017, 2021, 2022, 2024 and the 2026 event as held-out tests.

**Metrics (per station × horizon)**

| Metric | Formula / meaning |
|---|---|
| RMSE, MAE | Level error in m |
| NSE | `1 − Σ(o−s)² / Σ(o−ō)²` |
| KGE | `1 − √[(r−1)² + (α−1)² + (β−1)²]` (correlation, variability ratio, bias ratio) |
| Skill vs persistence | `1 − RMSE_model / RMSE_persistence` (must be > 0) |
| Peak error | Peak magnitude error (m) and **peak timing error** (h) per event |
| CRPS | Probabilistic accuracy of the full distribution |
| Interval coverage | Fraction of obs inside 50% / 90% intervals (target ≈ nominal) |
| Event detection | POD, FAR, CSI for "exceeds bank level" and "exceeds warning level" |

**Acceptance rule (proposal)**: skill vs persistence > 0.1 at that horizon **and** 90% interval coverage between 85–95% on held-out events; otherwise downgrade (§5).

Publish these metrics on the in-app "เกี่ยวกับแบบจำลอง" page.

---

## 7. Translating outputs into plain Thai for users

| Internal result | UI message (example) |
|---|---|
| median ΔH(+12 h) > +k·σ | "ระดับน้ำมีแนวโน้ม **เพิ่มขึ้น** ประมาณ X–Y ซม. ใน 12 ชม." |
| |ΔH| ≤ k·σ | "ระดับน้ำ **ทรงตัว**" |
| median ΔH < −k·σ | "ระดับน้ำมีแนวโน้ม **ลดลง**" |
| P(H > H_bank) | "โอกาสน้ำล้นตลิ่งภายใน 3 วัน: 30%" |
| Recovery date distribution | "คาดว่าน้ำจะลดต่ำกว่าตลิ่งประมาณ 2–5 ต.ค. (หากไม่มีฝนตกหนักเพิ่ม)" |
| Low confidence (horizon/model not accepted) | "ความเชื่อมั่นต่ำ — โปรดติดตามประกาศทางการ" |
| Daily high water (tidal) | "น้ำขึ้นสูงสุดวันนี้ประมาณ 18:40 น." |

Always show: last observed time, data source, and link to official warnings.

---

## 8. Pitfalls and how to handle them

| Pitfall | Mitigation |
|---|---|
| Managed operations (dam releases, gates, pumps) change the system abruptly | Treat announced operations as inputs/scenarios; event flags; fast recalibration (ACI) |
| Training on observed future rain inflates skill | Archive and train on as-issued forecasts; until then inflate intervals |
| Datum mix-ups (MSL vs gauge zero vs LLW vs EGM2008) | Single conversion table per station; unit tests with known bank levels |
| Sensor spikes, flatlines, clock errors | QC flags (§ SOURCES); robust features (medians); exclude flagged data from training |
| Station relocation / rating changes | Version station metadata; retrain after changes |
| Duplicate stations from multiple agencies | De-duplicate (SOURCES §3.1) |
| Floodplain flow ≠ channel flow (2011 lesson) | Use GISTDA extent + recession on floodplain; don't extrapolate channel lags to overland flow |
| Few extreme events in history | Global models across stations; monotonic constraints; physics baseline keeps extrapolation sane |
| DEM error larger than flood depth | Probabilistic depth; user-provided floor height; satellite override |
| Overconfidence harming users | Conformal coverage monitoring; conservative messaging; official links |

---

## 9. Suggested Python stack

| Task | Library |
|---|---|
| Data handling | `pandas`, `polars`, `xarray` |
| Tide harmonic analysis | `utide` |
| Filtering, recession fitting, rating curves | `scipy` (signal, optimize), `statsmodels` |
| Routing | own Muskingum implementation (few lines); `hec-ras` later |
| ML | `lightgbm`, `scikit-learn` |
| Deep learning (optional) | `neuralhydrology`, `neuralforecast`, `pytorch` |
| Conformal | `mapie` |
| Radar nowcast | `pysteps` |
| Geospatial (DEM, HAND, flood extent) | `rasterio`, `rioxarray`, `whitebox` / `pysheds`, `geopandas`, `shapely` |
| Probabilistic scores | `properscoring` (CRPS), `hydroeval` (NSE, KGE) |
| Experiment tracking | `mlflow` (model registry with version per forecast) |

---

## 10. Implementation checklist

1. Backfill history (HII graph API, DWR PDFs, data.go.th CSV, GloFAS 1984→).
2. Build station graph: regime, drainage zone, upstream/downstream links, chainage along river.
3. Fit tide models for all tidal stations; store predictions 1 year ahead.
4. Estimate lags and Muskingum parameters per reach; fit rating curves.
5. Implement L0–L3 baselines and the backtest harness (§6) **before** ML.
6. Train L4 LightGBM quantile models per regime; add AR correction and CQR.
7. Integrate ensemble weather; compute exceedance probabilities.
8. Implement recession/recovery estimator and depth-at-location module.
9. Run backtests on 2011/2017/2021/2022/2024/2026; publish metrics; apply acceptance rules.
10. Operate: 10-min forecast cycle, daily recalibration, weekly retraining, coverage monitoring alerts.

---

## 11. References

- Forecasting model of Chao Phraya river flood levels at Bangkok (ANN, C.4 Memorial Bridge; drivers: Bang Sai discharge + Fort Chula tide). ResearchGate 254879465.
- Machine Learning for Water Level Prediction in the Chao Phraya River Basin (XGBoost, RF, DNN; six stations; 1-day/1-week). Engineering Journal (Chulalongkorn), engj.org article 4646, 2025.
- Predicting Water Levels at Chao Phraya River Gauged Stations Using Machine Learning (C.2, C.29; 1990–2022). ResearchGate 380514152.
- Water levels forecast in Thailand: A case study of Chao Phraya river (ML vs Navy harmonic model). IEEE Xplore 7838716.
- Enhancing daily peak water level forecasts in tidal-dominated regions using machine learning and future tide integration (2026). ResearchGate 404815347.
- Chuanpongpanich, Tanaka, Kojiri, Arlai: Integrated Models in the Lower Part of Chao-Phraya River Basin for an Early Flood Warning System (HEC-RAS + ANN + harmonic + MLR; 4-day lead). DPRI Annuals No. 55.
- DHI: Protecting Thailand from floods — Chao Phraya DSS (28 locations, 7 days).
- Kuriki (FRICS/JICA): Flood Forecasting System of the Chao Phraya River Basin, 8th THAICID Symposium, 2013.
- Munrangsee: Flood modelling in the middle Chao Phraya River Basin using HEC-RAS (Chulalongkorn thesis, 2022).
- Nearing et al.: Global prediction of extreme floods in ungauged watersheds. Nature 627, 559–563 (2024).
- Romano et al. 2019 (Conformalized Quantile Regression); Gibbs & Candès 2021 (Adaptive Conformal Inference); MAPIE documentation.
- Weerts et al. 2011: Estimation of predictive hydrological uncertainty using quantile regression, HESS 15.
- Meadows, Jones, Reinke 2024: Vertical accuracy assessment of FABDEM, Copernicus DEM, NASADEM, AW3D30, SRTM in flood-prone environments.
- BMA drainage capacity (~60 mm/h) and monitoring network (55 flow stations, 270 pump stations): BMA statements reported by InfoQuest, ThaiPublica, Matichon (2025–2026).
