# APPROACH_AND_METHODS.md — Forecasting Approach, Calculations & Models

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-26
> **Role:** this is the brief's `docs/METHODS.md`. It explains every method and cites what it relies on.
> **Built from:** [research/methods_survey.md](../research/methods_survey.md) 🟢, plus the validated parts of [bangkok_flood_calculation_forecasting_engine.md](../research/bangkok_flood_calculation_forecasting_engine.md) 🟠 (the equations only; see [validation §C](../research/VALIDATION_2026-09-26.md)).
> **Companion docs:** [KNOWLEDGE](KNOWLEDGE.md) · [KNOWN_ISSUES](KNOWN_ISSUES.md) · [GUIDELINES §4](GUIDELINES.md)
> **Principle:** forecast = physically structured baseline + ML residual + calibrated uncertainty, **always benchmarked against simple baselines**, and **explicit in space and time**.

---

## 0. Summary for implementers
1. There are **four regimes with different drivers**, so there's one model family per regime (§1).
2. **Model in space and time explicitly** (§2): a station network graph, polder zones, scale-aware aggregation, flow-dependent lags, tidal and seasonal periodicities, and issue time vs valid time.
3. The engine per station: physical baseline (tide + routed flow + polder storage) + LightGBM quantile residual + AR error correction, with **conformal intervals** (§5–§11).
4. Horizons: +12 h, +1 d, +2 d, +3 d, +7 d. For +7 d, give categories or probabilities only (§3).
5. "When does it return to normal?" is answered with a **distribution of dates**, with its conditions (§12). There's no minute countdown (D-005).
6. Nothing is served unless it beats persistence (and persistence + tide) at that station and horizon ([GUIDELINES §4.3](GUIDELINES.md)).

---

## 1. Hydraulic regimes

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ REGIME A — upstream river: C.2 → C.13 → C.3 → C.35 (+S.26 Pasak) → C.29A      │
│ Drivers: dam releases, tributary inflow, routing. Lead time: days             │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ Q at Bang Sai
┌───────────────────────────────────▼──────────────────────────────────────────┐
│ REGIME B — tidal lower Chao Phraya: Bang Sai → Nonthaburi → Bangkok → mouth   │
│ Drivers: Q_BangSai (lagged) + tide at the mouth (+ surge). Lead time: hours–days │
└───────────────┬───────────────────────────────────────┬──────────────────────┘
                │ outlet level blocks gravity drainage    │ overtopping outside walls
┌───────────────▼───────────────────────┐ ┌─────────────▼────────────────────────┐
│ REGIME C — khlongs / polders            │ │ REGIME D — at the user's location     │
│ Drivers: local rain, pumps, gates,      │ │ Derived from A–C + ground elevation   │
│ outlet level. Responds within hours     │ │ + observed flood extent (probabilistic)│
└─────────────────────────────────────────┘ └───────────────────────────────────────┘
```
The current (Sep 2026) situation shows both A/B (Ayutthaya above bank) and C (east Bangkok khlongs above bank) at once ([KNOWLEDGE §5](KNOWLEDGE.md)).

---

## 2. Spatio-temporal framework

Every quantity in this system is a field **H(x, t)**. It is observed at scattered points and times, driven by inputs at other points and times, and needed at the user's location and at future times. This section defines how space and time are represented, matched and validated.

### 2.1 Spatial representation
| Object | Representation | Stored as |
|---|---|---|
| Stations | Points (WGS84) with datum, bank and ground level, agency, **regime**, **polder or zone ID** | `station`, `station_version` (effective-dated) |
| River network | **Directed graph**: nodes = stations, confluences (Pasak at Ayutthaya), diversions, gates; edges = reaches with **chainage (km from the mouth)**, length and fitted travel-time function τ(Q) | `river_node`, `river_reach` |
| Polders / drainage zones | Polygons with khlongs, pumps (capacity), gates (outlet and to which river node), area and imperviousness | `polder`, `pump`, `gate` |
| Rain fields | Gauge points, radar grids, NWP grids (per model and resolution) | Raw + areal aggregates per polder or catchment |
| Terrain | DEM rasters (EGM2008 → Ko Lak), HAND raster, flood-extent rasters | COGs + derived tables |
| Users | A point → resolved to its **controlling water body** (§13) | Not stored (privacy) |

- **CRS:** store WGS84 (EPSG:4326). Compute distances and areas in UTM 47N (EPSG:32647). Chainage is measured **along the river centreline**, not in straight lines.
- **PostGIS** alongside TimescaleDB handles nearest-station queries, point-in-polygon lookup, areal rain aggregation and chainage ([ARCHITECTURE §3](ARCHITECTURE.md)).
- **Walls and gates break spatial continuity.** Never interpolate a water surface across a flood wall or between polders. Inside a polder the khlong stations govern; outside the walls the river water surface governs.

### 2.2 Temporal representation
| Axis | Meaning | Rule |
|---|---|---|
| `obs_time` | When a value was measured | UTC; from local time without a timezone → +07:00 ([KI-205](KNOWN_ISSUES.md)) |
| `fetch_time` | When we got it | Detects source latency and staleness |
| `issue_time` | When a forecast (NWP or ours) was issued | **Every run is stored.** Training uses only inputs with `issue_time ≤ t` |
| `valid_time` / lead | The time a forecast refers to; lead = valid − issue | Skill is always reported per lead time |

**Native resolutions and resampling**

| Source | Native Δt | Resample to | Rule |
|---|---|---|---|
| HII telemetry | 10 min (RID rows hourly) | 10 min / 1 h | Level: instantaneous (no averaging across tidal peaks); daily **max/min** for tidal stations |
| Rain gauges | 10 min / 1 h / 24 h | 1 h | Accumulations; never interpolate rain in time |
| NWP (Open-Meteo) | 1 h per run | 1 h | Keep member and run; accumulate over windows |
| GloFAS | Daily | Daily | Daily mean discharge |
| Navy / own tide | 1 h (or exact harmonic) | Any | Evaluate the harmonic at the exact time |
| Traffy | Irregular | Counts per hour and per cell | Report time ≠ flood time |

Gaps: short gaps (≤ 30 min) can be interpolated for features, with a flag. Longer gaps stay missing. Never fill a target with invented values.

### 2.3 Scale matching (points vs grids vs polygons)
| Need | Method |
|---|---|
| Rain over a polder from gauges | Thiessen or IDW areal mean (radar-merged when available); report gauge density |
| Rain over a polder from NWP | Area-weighted average of grid cells overlapping the polygon. Note that 9–25 km cells are coarser than most polders → treat as regional forcing, and let ML learn the local bias |
| Upstream discharge prior (GloFAS 5 km) | Snap to the right channel cell; bias-correct against C.2/C.13 observations |
| Water surface between river stations | Linear in chainage between neighbours plus a tide phase lag (§8), only **outside** the walls |
| Terrain at the user's point | DEM with σ ≥ 1 m → probabilistic depth only (§13) |

### 2.4 Temporal structure the models must respect
- **Travel-time lags**, estimated from data rather than hard-coded: lag* = argmax_τ corr(ΔQ_up(t−τ), ΔQ_down(t)), per reach and **per flow class**. Waves speed up with discharge until the floodplain engages, then slow down (§7).
- **Tidal periodicities:** diurnal and semi-diurnal (dominant K1, O1, M2, S2), **spring–neap ≈ 14.8 d**, monthly, **seasonal Sa/Ssa**, and the **18.61-year nodal cycle** (handled by nodal corrections f, u) (§5).
- **Rain:** a diurnal convective cycle, monsoon seasonality, and **antecedent storage** (7-day and 30-day rain and levels act as memory).
- **Recession timescales:** fast channel drainage vs slow floodplain and polder drainage (§12).
- **Non-stationarity:** managed operations (sudden), channel and rating changes, and **land subsidence** that drifts benchmarks over years ([KI-303](KNOWN_ISSUES.md), [KNOWLEDGE §2](KNOWLEDGE.md)). Use rolling recalibration and effective-dated metadata.

### 2.5 Space–time propagation (what moves where, and how fast)
| Process | Space–time form | Handled by |
|---|---|---|
| River flood wave (A → B) | Travels down the reach graph with celerity c(Q) and attenuation | Lags + Muskingum per reach (§7) |
| Tide into the estuary (B) | Travels upstream from the mouth with phase lag τ_t(x) and amplitude damping that increases with Q | Per-station harmonic fits; damping regressed on Q_BangSai (§5, §8) |
| Rain cells (C) | Move across the city in 0–3 h | Radar nowcast extrapolation (optical flow, `pysteps`) (§9) |
| Floodplain / overland water | Much slower than channel waves (≈ two weeks for 120 km in 2011) | Satellite extent + recession; never extrapolate channel lags onto land |

### 2.6 Spatio-temporal features for ML
- **Graph-lagged upstream features:** Q and H at upstream nodes at t − τ̂(Q), plus trends.
- **Neighbour features:** levels at adjacent stations on the same reach or polder; the outlet (river) level for khlongs.
- **Windowed areal rain:** observed 1/3/6/12/24/72 h per polder, forecast accumulations per lead (ensemble mean + P90).
- **Tide:** η(t+h) predicted exactly at the station, daily η_max.
- **Calendar harmonics:** sin/cos of day-of-year and hour-of-day.
- **Static spatial attributes:** chainage, regime, polder pump capacity per area, bank level, imperviousness.
- **Upgrade path (L6):** a spatio-temporal graph neural network or a global LSTM across stations, only if it beats L5.

### 2.7 Spatio-temporal QC
- **Neighbour consistency:** flag a station whose change disagrees with both upstream and downstream neighbours after lag alignment.
- **Travel-time consistency:** an upstream rise should appear downstream within the lag window.
- **Tidal consistency:** at tidal stations, residual spikes at exactly the tidal period suggest a clock or datum problem.

### 2.8 Validation in space and time
- **Time:** rolling-origin walk-forward with an **embargo ≥ horizon**; report per lead time and per event.
- **Space:** **leave-station-out** (and leave-polder-out) to test generalisation to stations without history, which is what "near my house" relies on.
- Report skill **per regime, per station, per lead time**, and map it. Skill naturally varies in space.

---

## 3. Horizons and the model ladder

### 3.1 Horizon × regime matrix
| Horizon | Regime A (upstream river) | Regime B (tidal river) | Regime C (khlongs) | Expected quality |
|---|---|---|---|---|
| **+12 h** | Persistence + routing of already observed flow | Exact tide + current residual (AR) + lagged Q_BangSai | Radar nowcast + NWP + storage/ML | High |
| **+1 d** | Routing + RID release plan | Tide + routed Q + ML | NWP rain + ML | Good (C depends on the rain forecast) |
| **+2 d** | Routing + planned releases | Tide + routed Q + ML | Ensemble rain, scenario ranges | Moderate |
| **+3 d** | Routing + releases + GloFAS | Tide + routed or planned Q | Ensemble, wide ranges | Moderate/low |
| **+7 d** | GloFAS ensemble + reservoirs + ensemble rain | Tide (exact) + scenario Q | **Category outlook only** | Low → probabilities |

### 3.2 Model ladder (build in this order; serve the best one that passes the gate)
| Level | Model | Purpose |
|---|---|---|
| L0 | Persistence H(t+h) = H(t) | Mandatory baseline |
| L1 | Persistence + tide change H(t) + η(t+h) − η(t) | Baseline for tidal stations |
| L2 | Climatology (day-of-year median, P25–P75 band) | Baseline for +7 d; defines "normal" |
| L3 | Physical components: harmonic tide, lags + Muskingum, rating curves, polder storage | Interpretable core |
| L4 | LightGBM quantile model on L3 residuals (global per regime) | Main production model |
| L5 | L4 + AR error correction + weather ensemble + CQR/ACI | Production with uncertainty |
| L6 | Global LSTM / TFT / spatio-temporal GNN | Only if it beats L5 in backtests |
| L7 | 1-D hydrodynamic model (HEC-RAS unsteady) of the main stem | Long term; needs cross-sections |

---

## 4. Derived quantities (shown in the UI and used as features)
| Quantity | Formula | Notes |
|---|---|---|
| Freeboard (ระยะห่างจากตลิ่ง) | fb = H_bank − H | Negative = above bank. HII also gives `diff_wl_bank` |
| % of bank | (H − H_bed)/(H_bank − H_bed) | HII `storage_percent` when the bed level is unknown |
| Rate of change | Robust slope (Theil–Sen) over 1/3/6/24 h | For tidal stations, compute it on the **tidally filtered** series (§5) or on the daily max |
| Trend class | Stable if \|dH/dt\| < k·σ_noise (k ≈ 2), otherwise rising or falling | σ_noise estimated per station from calm periods |
| Status | ปกติ / เฝ้าระวัง / เตือนภัย / วิกฤต | Official thresholds first (HII `situation_level`, BMA warning levels) |
| Daily high water | Max per local day | What residents at tidal stations care about |

---

## 5. Tide (regime B and khlong outlets)

**Harmonic model** (the full form; the phase needs the astronomical argument):

η(t) = Z₀ + Σₖ fₖ(t) · Hₖ · cos( ωₖ·t + Vₖ(t₀) + uₖ(t) − gₖ )

where Hₖ and gₖ are the amplitude and Greenwich phase lag, Vₖ is the equilibrium argument at the reference time, and fₖ, uₖ are the nodal corrections (18.61-year cycle).

- **Leaving out V + u makes the timing arbitrary.** That's why the draft constants failed (correlation −0.74) ([KI-301](KNOWN_ISSUES.md)). Always use a tidal library (`utide`) to fit and predict. Never hand-roll the phase.
- **Evidence (2026-09-26):** a 30-day fit at HII CPY015 (สะพานกรุงเทพ) gives K1 0.45, O1 0.36, M2 0.37, S2 0.27 m (F = 1.27, mixed and mainly diurnal), explaining 92 % of the tidal variance in-sample ([validation](../research/VALIDATION_2026-09-26.md)).
- **Record length (Rayleigh criterion):** ≥ 15 days separates M2/S2 and K1/O1. **≥ 6 months separates K1/P1 and S2/K2. ≥ 1 year gives Sa/Ssa.** Use 30-day fits only as an interim fallback; switch to ≥ 1 year of archived data or the Navy tables.
- **River–tide interaction:** tidal amplitude at upstream stations is **damped by river discharge**. Fit the constants per station and regress the amplitude damping on Q_BangSai (non-stationary tidal analysis).
- **Navy tables** are LLW-referenced → convert to MSL with the per-station offset ([KI-201](KNOWN_ISSUES.md)).
- **Non-tidal residual** r(t) = H_obs(t) − η(t), low-pass filtered (Godin filter or 25 h mean). This is the signal for trend, recession and the ML target in regime B.
- **Surge (optional feature):** inverse barometer (≈ 1 cm per hPa) + wind set-up ∝ U² along the Gulf axis. Its parameters must be fitted, not assumed.

## 6. Rating curves (stage ↔ discharge)
Q = a·(H − H₀)^b, fitted per station where both H and Q exist (the RID C-stations via HII). Use log-linear least squares with a grid search over H₀, and refit when the residuals drift. Add a dH/dt (Jones) term for loop ratings. **Not valid in tidal reaches** (backwater). There, use measured Q or the regime B regression.

## 7. Routing (regime A → B)
1. **Lags from data** (§2.4), per reach and flow class. HII already gives discharge at C.2, C.13, C.3 and C.35 → estimate C.2→C.13→C.3→C.35 now. Bang Sai (C.29A) needs a RID feed ([KI-109](KNOWN_ISSUES.md)).
2. **Flow balance at control points:**
   Q_C13(t) ≈ Q_C2(t − τ₁) + Q_SakaeKrang(t − τ₂) − diversions
   Q_BangSai(t) ≈ Release_C13(t − τ₃) − Σ diversions + Q_Pasak/S.26(t − τ₄) + lateral
3. **Muskingum** between gauges: O_{t+1} = C₀I_{t+1} + C₁I_t + C₂O_t, with C₀ = (Δt − 2Kx)/(2K(1−x) + Δt), C₁ = (Δt + 2Kx)/(2K(1−x) + Δt), C₂ = (2K(1−x) − Δt)/(2K(1−x) + Δt). Calibrate K and x per reach on past floods.
4. **Celerity law** c(Q) = c₀(Q/Q_bf)^m is a **hypothesis**. The drafts' m = 0.38 and c₀ ≈ 1 m/s have no source; fit them if the lag data supports a power law.
5. **Controlled releases:** for future days, use **RID's announced release plan** as a scenario boundary ("ตามแผนการระบายน้ำ X ลบ.ม./วินาที"), not a statistical extrapolation.

## 8. Regime B — tidal Chao Phraya
H(t+h) = η(t+h) + f( Q_BangSai(t+h−τ̂), r(t), wind, local rain, season ) + ε
- η is known exactly ahead → a strong predictor at every horizon. f = LightGBM quantile (baseline: α + β·Q^γ).
- Predict the **daily high water** separately: daily-max tide + tidally averaged residual; interaction η_max × Q_BangSai (spring tides + high flow is the dangerous combination).
- Along the reach, the water surface is interpolated in chainage with a tide phase lag between stations (§2.3), **outside the walls only**.

## 9. Regime C — khlongs and polders (rain-driven)
**Storage balance per polder** (textbook form; the draft's structure was correct):

A_s(H) · dH/dt = C·A·P(t) + Q_in(t) − Q_pump(t) − Q_gate(t)
- Q_gate = C_d·B·Y·√(2g(H_khlong − H_outlet)) if H_khlong > H_outlet, otherwise 0 (gates closed)
- 0 ≤ Q_pump ≤ Q_pump,max, and pumps stop at a **minimum operating level**. The draft engine had no such floor and drained to −1.25 m ([KI-302](KNOWN_ISSUES.md)).
- Mass-balance closure < 3 % as a **unit test**.

Pump and gate logs aren't published, so the net effect is learned statistically. LightGBM features:
- polder rain windows (§2.6), including max(0, P_1h − 60) and a P_1h > 60 flag (drainage ~60 mm/h)
- forecast rain (ensemble mean + P90)
- current H, dH/dt, H 6/12/24 h ago
- outlet level + predicted tide
- inflow from outside Bangkok (e.g. Khlong Hok Wa, Rangsit for the east)
- hour of day, days since the event started, antecedent 7-day rain

**Nowcasting (0–3 h):** radar extrapolation (`pysteps`) beats NWP. Beyond 24–48 h, skill depends on the rain forecast → show +2/+3 d as **scenario ranges** ("ถ้าฝนตกหนักอีก… / ถ้าฝนหยุด…").

## 10. ML specification
- **LightGBM, direct multi-horizon.** Target ΔH_h = H(t+h) − H(t), or the residual of L3, for h ∈ {1…12 h, 24, 48, 72, 168 h}. Horizon either as a feature or as separate models.
- **Quantile loss** at τ ∈ {0.05, 0.25, 0.5, 0.75, 0.95}: L_τ(y, ŷ) = max(τ(y − ŷ), (1 − τ)(ŷ − y)).
- **One global model per regime** across stations, with static spatial attributes (§2.6). This generalises better than hundreds of tiny models.
- **Monotonic constraints:** ∂H/∂Q_upstream ≥ 0, ∂H/∂P ≥ 0.
- **AR error correction:** ε̂(t+h) = φ^h·(H_obs(t) − H_model(t)), with φ fitted per station. It fades out with the horizon.
- Secondary: SARIMAX (interpretable single station); L6 upgrades (§3.2).

## 11. Uncertainty: ensembles and conformal calibration
- **Weather ensemble:** run the model once per member (ECMWF ENS, GFS ensemble) → distribution of H(t+h), plus model error (resampled or conformal residuals). For > 3 d, report probabilities ("โอกาสน้ำล้นตลิ่ง 30%").
- **CQR:** non-conformity Eᵢ = max(q̂_lo(xᵢ) − yᵢ, yᵢ − q̂_hi(xᵢ)). Calibrated interval [q̂_lo − Q₁₋α(E), q̂_hi + Q₁₋α(E)], per station × lead time (`mapie`).
- **ACI** (adaptive conformal inference) or a rolling calibration window for non-stationarity. If coverage on the 90 % band falls below 85 % over 14 days: widen and alert.

## 12. "When will it return to normal?" (recovery)
**Milestones per station:** (1) below bank (`min_bank`), (2) below warning, (3) back within the **normal band** (L2: day-of-year P25–P75, with flood years excluded or using the median).

**Recession:** the tidally filtered H̄(t) − H_base = (H̄₀ − H_base)·e^{−(t−t₀)/k}, with k per station from historical recessions (two segments: fast channel, slow floodplain). **Polders:** roughly **linear** drawdown while pumps run at capacity, so dH/dt comes from recent falling periods.

**Output:** for each ensemble or quantile path over days 1–7, plus recession beyond → the first crossing of each milestone → **a distribution of recovery dates** (median + 80 % range). It is always conditional ("หากไม่มีฝนตกหนักเพิ่มเติม", "ตามแผนการระบายน้ำของกรมชลประทาน"). If heavy rain is forecast, show "ยังประเมินไม่ได้".

**Volume-balance check (from the drafts):** T_dry ≈ V_ponded / (Q_pump,allocated + Q_gravity − Q_rain). This is used as a **consistency check and a feature**, output as a range. It is never shown as a countdown (D-005).

## 13. Depth at the user's location (regime D)
1. **Controlling water body** (spatial rule, §2.1): inside a polder → that polder's khlong station(s). Outside the walls → the river water surface interpolated along the chainage with a tide lag.
2. **Ground elevation** z_g from the best DEM (FABDEM preferred), converted EGM2008 → Ko Lak MSL. σ_DEM ≥ 1 m in Bangkok ([KI-202](KNOWN_ISSUES.md)).
3. **Connectivity:** depth only if the point is hydraulically connected (HAND below H_ws − H_channel).
4. **Probability, not a number:** P(d > 0) = Φ((H_ws − z_g)/σ), σ² = σ_DEM² + σ_forecast² → categories (น้ำไม่น่าจะถึง / อาจท่วม / มีโอกาสสูงที่จะท่วม).
5. **Observed overrides:** satellite extent (GISTDA or GFM) and **aggregated Traffy reports** nearby raise the category ([KI-107](KNOWN_ISSUES.md)).
6. **Personalise:** the user can enter "บ้านสูงกว่าถนนกี่ ซม.".

## 14. Validation metrics (per station × lead time × regime)
| Metric | Meaning |
|---|---|
| RMSE, MAE | Level error (m) |
| NSE | 1 − Σ(o−s)²/Σ(o−ō)² |
| KGE | 1 − √((r−1)² + (α−1)² + (β−1)²) |
| Skill vs persistence | 1 − RMSE_model/RMSE_persistence (**gate: > 0.1**) |
| Peak error | Peak magnitude (m) and timing (h) per event |
| CRPS | Accuracy of the full distribution |
| Interval coverage | Fraction of observations inside the 50 % and 90 % intervals (**gate: 85–95 % for the 90 % band**) |
| POD / FAR / CSI | For "exceeds bank" and "exceeds warning" |

Results are published on the in-app "เกี่ยวกับแบบจำลอง" page, and mapped (§2.8).

## 15. Plain-Thai translation
| Internal result | UI message |
|---|---|
| Median ΔH(+12 h) > +kσ | "ระดับน้ำมีแนวโน้ม **เพิ่มขึ้น** ประมาณ X–Y ซม. ใน 12 ชม." |
| \|ΔH\| ≤ kσ | "ระดับน้ำ **ทรงตัว**" |
| Median ΔH < −kσ | "ระดับน้ำมีแนวโน้ม **ลดลง**" |
| P(H > H_bank) | "โอกาสน้ำล้นตลิ่งภายใน 3 วัน: 30%" |
| Recovery distribution | "คาดว่าน้ำจะลดต่ำกว่าตลิ่งประมาณ 2–5 ต.ค. (หากไม่มีฝนตกหนักเพิ่ม)" |
| Model not accepted or low confidence | "ความเชื่อมั่นต่ำ — โปรดติดตามประกาศทางการ" |
| Daily high water (tidal) | "น้ำขึ้นสูงสุดวันนี้ประมาณ 18:00–19:00 น." |
| Stale input | "ข้อมูลล่าสุดเมื่อ … (แหล่งข้อมูลขัดข้องชั่วคราว)" |

## 16. Pitfalls
| Pitfall | Mitigation |
|---|---|
| Managed operations change the system abruptly | Operation events as inputs and scenarios; ACI ([KI-303](KNOWN_ISSUES.md)) |
| Perfect-prognosis training | Archive as-issued runs; widen intervals until then ([KI-305](KNOWN_ISSUES.md)) |
| Datum mix-ups | One conversion table per station; unit tests ([KI-201](KNOWN_ISSUES.md)) |
| Interpolating across walls or polders | The controlling-water-body rule (§2.1, §13) |
| Scale mismatch (grid vs point vs polygon) | Explicit aggregation (§2.3) ([KI-306](KNOWN_ISSUES.md)) |
| Sensor spikes, sentinels, stale data | QC flags ([KI-206](KNOWN_ISSUES.md)); exclude flagged data from training |
| Station relocation, rating change, subsidence | Effective-dated metadata; retrain after changes |
| Floodplain flow ≠ channel flow | Satellite extent + recession; don't reuse channel lags |
| Few extreme events | Global models; monotonic constraints; physical baseline |
| DEM error > flood depth | Probabilistic depth; user floor height; observed overrides |
| Overconfidence | Coverage monitoring; conservative wording; official links |
| Hand-copied constants (tide, celerity) | Fit from data; the evidence rule ([GUIDELINES §2.2](GUIDELINES.md)) |

## 17. Software stack
| Task | Library |
|---|---|
| Data | `pandas`, `polars`, `xarray` |
| Spatial | **PostGIS**, `geopandas`, `shapely`, `pyproj`, `rasterio`, `rioxarray`, `pysheds` / `whitebox` (HAND) |
| Tide | `utide` |
| Filtering, recession, rating curves | `scipy`, `statsmodels` |
| Routing | Own Muskingum (a few lines); HEC-RAS later |
| ML | `lightgbm`, `scikit-learn`; optional `neuralhydrology`, `neuralforecast`, `torch`, `torch-geometric-temporal` |
| Conformal | `mapie` |
| Radar nowcast | `pysteps` |
| Scores | `properscoring` (CRPS), `hydroeval` (NSE, KGE) |
| Tracking | `mlflow` (model version on every forecast) |

## 18. References
From [methods_survey §11](../research/methods_survey.md). The citations are to be re-read and confirmed before the model page is published ([validation D14](../research/VALIDATION_2026-09-26.md)):
- ANN forecast of Chao Phraya levels at Bangkok (C.4 Memorial Bridge; drivers Bang Sai Q + Fort Chula tide). ResearchGate 254879465.
- Machine Learning for Water Level Prediction in the Chao Phraya River Basin (XGBoost, RF, DNN). Engineering Journal (Chulalongkorn), 2025.
- Predicting Water Levels at Chao Phraya River Gauged Stations Using ML (C.2, C.29; 1990–2022). ResearchGate 380514152.
- Water levels forecast in Thailand: Chao Phraya (ML vs Navy harmonic model). IEEE Xplore 7838716.
- Daily peak water level forecasts in tidal-dominated regions with future-tide integration (2026). ResearchGate 404815347.
- Chuanpongpanich et al.: Integrated models in the lower Chao Phraya for early flood warning (HEC-RAS + ANN + harmonic; 4-day lead). DPRI Annuals 55.
- DHI Chao Phraya DSS (28 locations, 7 days). Kuriki (FRICS/JICA) 2013. Munrangsee 2022 (HEC-RAS thesis).
- Nearing et al. (2024), Nature 627, 559–563 — global flood prediction with LSTM.
- Romano et al. (2019) CQR; Gibbs & Candès (2021) ACI; Weerts et al. (2011) HESS 15 — quantile regression uncertainty.
- Meadows, Jones, Reinke (2024) — vertical accuracy of FABDEM and other DEMs in flood-prone areas.
- **Tide type:** "Tidal resonance in the Gulf of Thailand", Ocean Science 15, 321 (2019) — the Gulf is diurnal-dominated, with K1 strongest. ✅ checked 2026-09-26.
- Pawlowicz, Beardsley, Lentz (2002) T_TIDE, and Codiga (2011) UTide — harmonic analysis with nodal corrections.
