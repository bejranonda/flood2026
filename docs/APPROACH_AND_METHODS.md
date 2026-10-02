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

- **Plausibility ceiling (live, D-024, KI-211):** level > bank + 3 m → `out_of_range`, using the stored bank on every insert. It caught BKK003's stuck 7.45 m (+5.4 m) and spikes at BKK006 / CPY012, while the largest genuine value in 30 days was +1.90 m (C.67). Flagged values stay in the DB and are hidden in the UI, and the station shows the last plausible value with a note.
- **Show stations, filter values:** every station stays visible; the reason for each hidden value is a per-station `notes` code (D-024).
- **Canal gate at a pin (live, D-054 + D-059):** river gauges are skipped; the nearest ≤ 3 canal gauges within 3 km decide; a lone one is overruled (very_low) when a gauge within 5 km differs by 2+ ranks; the headline trend uses the same band.
- **Numbers on measured-trend rows (live, D-062):** the measured rate continued and damped, slope·h·e^(−h/48) (the same damping as the `tide_trend` method), shown as "ราว N ซม."; the size word follows the rounded number (1–4 เล็กน้อย, 5–19, ≥ 20 มาก). It is a conditional statement ("if the trend continues"), labelled so in the ⓘ with the past odds.
- **Pin headline (live, D-062):** the outlook trend comes from the gauge the canal factor shows (nearest canal with rows) at 24 h, not a majority of three gauges at 12 h.
- **Trend continuation (live, D-060):** `forecast.continuation` counts, per gauge over the backtest window, how often a steady measured 24 h trend (≥ 2 cm; R² ≥ 0.5 or small wiggle) kept its direction 12/24/48 h later (3 h means at both ends), with the 5–95 % of those changes. It is shown in the ⓘ of rows that follow the measured trend. 45-day result: canals 53–64 %, rivers 70–96 %.
- **Stuck gauges (live, KI-241):** one exact value in ≥ 90 % of ≥ 50 readings in 24 h → hidden like an erratic gauge.
- **Measured 24 h change (live, D-058, KI-240; 48 h fallback and noise rule D-060):** `qc.observed24` fits a straight line to the last 24 h of each gauge (dropouts removed, ≥ 20 h of readings); change = slope × 24 h, words by the rounded cm (< 2 / 2-4 / 5-19 / ≥ 20), "mixed" when R² < 0.5 and the residual wiggle ≥ 5 cm (tidal and pumped gauges).
- **Dropouts and erratic gauges (live, D-057, KI-237):** `floodwatch.qc` runs every 10 min over the last 24 h. A reading ≥ 0.30 m away from the level before for one or two readings, then back within 10 cm, is flagged `dropout`. Three or more remaining steps of ≥ 0.30 m within 30 min mark the gauge erratic (pumps next to the sensor or a faulty sensor): its level, status, trend and forecast are hidden with the note `erratic`.
### 2.8 Validation in space and time
- **Time:** rolling-origin walk-forward with an **embargo ≥ horizon**; report per lead time and per event.
- **Space:** **leave-station-out** (and leave-polder-out) to test generalisation to stations without history, which is what "near my house" relies on.
- Report skill **per regime, per station, per lead time**, and map it. Skill naturally varies in space.

---

### 2.9 Is spatio-temporal interpolation useful for users? (assessment 2026-09-26)
The owner asked this, noting that **Bangkok is not flat**. Short answer: **2-D interpolation of water levels over the city: no, it would mislead. 1-D interpolation along the Chao Phraya outside the walls: yes, later, once validated. Temporal interpolation: only for short gaps inside models, never in what users see.**

Evidence (live DB, 2026-09-26 ~09:30 UTC):
- **Sparse, channel-bound gauges.** Bangkok plus Nonthaburi, Samut Prakan and Pathum Thani have **20 gauges with coordinates**. Median nearest-neighbour spacing is **7.7 km** (max 17.1 km). Street-scale flooding varies over tens of metres.
- **Protection heights differ by metres.** Bank levels of metro gauges range from **0.43 m (BKK017) to 4.56 m MSL (CAN001)**. Water levels on either side of a gate differ too (BKC003 bank 1.51 vs BKC004 0.91 on the same Bang Yo cut). An interpolated surface would cross walls, gates and polder boundaries, which §2.1 forbids.
- **"Ground level" at a river gauge is the channel bed**, not land: CPY015 −15.7 m, C.12 −14.5 m. HII `ground_level` therefore can't be used to build a land surface ([KI-208](KNOWN_ISSUES.md)).
- **1-D along the river works, but isn't good enough yet.** Leave-one-out at C.12 Samsen, predicting it from CPY014 (Nonthaburi, 17.9 km upstream) and CPY015 (Krung Thep Bridge, 9.9 km downstream) by linear interpolation in straight-line distance:

  | Method | RMSE (m) | Bias (m) |
  |---|---|---|
  | Linear interpolation | **0.175** | +0.145 |
  | Nearest gauge | 0.38–0.46 | – |
  | Spread of C.12 itself (SD) | 0.42 | – |

  54 matched hours over 30 days; C.12 reports sparsely. So the along-river position carries information, but the bias (tide phase and non-linear slope) must be modelled before this is shown to riverside residents.
- **Update ~10:45 UTC, with true river distance:**
  - HII's map page has a river centreline layer (`resources/json/river/river_main.json`). [scripts/build_chainage.py](../scripts/build_chainage.py) turns it into river km from the mouth for each gauge ([data file](../src/floodwatch/data/chaophraya_chainage.json)):
    - the Chao Phraya pieces are joined as a graph and measured as the shortest path from the mouth;
    - mouth → Nakhon Sawan is 376 km, against the commonly cited ~372 km;
    - uncertainty is up to ~10 km near branch points; the order of C.2 and CPY001 depends on how pieces link.
  - River km: CPY015 42.0 · C.12 57.4 · CPY014 84.1.
  - Leave-one-out at C.12 with **river-km weights**, on 125 matched hours (after the backfill):

    | Method | RMSE (m) | Bias (m) |
    |---|---|---|
    | Linear in river km | **0.200** | **+0.171** |
    | Straight-line weights | 0.190 | – |
    | Nearest gauge | 0.45–0.52 | – |

  - **True distance doesn't remove the bias.** C.12 sits ~17 cm above a straight line between its neighbours: a non-linear water surface, or gauge datum offsets (KI-201). The next step is a per-reach bias term (or tide-phase-aware model) fitted on the year of history, still gated at RMSE < 0.10 m. River km is used now only to order and label the "เจ้าพระยา" profile.

| Interpolation | Useful to users? | Decision |
|---|---|---|
| 2-D water surface over land (IDW, kriging) | **No, harmful.** It crosses walls and polders, ignores terrain, and gives false "safe" or "flooded" signals | Not built. "Near me" says the nearest gauge may not represent the user's home |
| 1-D along the Chao Phraya, outside the walls | **Yes**, for riverside communities (piers, communities outside the flood wall) | **Now:** the "เจ้าพระยา" profile shows gauges only, north → south, with freeboard (`/api/profile`), and nothing between gauges. **Phase 2:** chainage from a river centreline (OSM, ODbL) + tide phase lag (§8), validated leave-one-out, shown only if RMSE < 0.10 m |
| Along a khlong inside one polder | Maybe. Gauges are sparse and pumps and gates dominate | Phase 2, per polder, only where ≥ 2 gauges share a reach |
| Rain (gauges → areal mean per polder) | Yes, as model **forcing** (§2.3); little direct value to users | Phase 2 (IDW or Thiessen + radar). Users get the Open-Meteo 24 h total in the summary strip |
| Temporal gap filling | Inside models only (tide-aware, ≤ 1 h gaps) | **Now:** charts don't bridge gaps > 90 min, and readings older than 24 h show as "unknown" instead of their last status |
| Depth at the user's point | Yes, the real need, but only as probabilistic categories | §13. Validated against user depth reports (§3.5) and Traffy (§2.3) |

What helps a Bangkok resident most is not interpolation. It is **choosing the gauge in the same water body** (polder-aware "near me", §13) and **reporting ground truth back** (§3.5).

### 2.10 Point check: a place with no gauge (`/api/point`, D-021)
> **Update 2026-09-27 (D-054):** the area's confidence is now judged from **up to 3 gauges within 3 km** (the 8 km circle is only counted and ranged); the old all-8-km rule made 83 % of Bangkok pins "ประเมินไม่ได้" once BMA's 199 gauges joined (KI-229) — now 39 %. The panel leads with the nearest canal gauge and its 24/48 h change; since v0.11 every horizon uses one row format and a direction appears only where a real model beat "no change" at that horizon (D-056); if the nearest canal has no forecast, the nearest canal with one is shown as a second, identically formatted block (KI-232, KI-234). When no canal statement is possible the outlook headline says so in one short line and the text gives only the rain condition (KI-235).
The owner asked what a user should see when they pin a place that has no station. Following §2.9, **we don't interpolate a water level to the pin**. The pin gets an evidence card instead.

1. **Area category, not a level.** An inverse-distance-weighted (power 2, min distance 0.3 km) mean of the **status rank** (normal 0 · watch 1 · warning 2 · critical 3) of fresh gauges within **8 km**.
   - This interpolates a *normalised state*: each gauge relative to its own bank. That transfers between places far better than an absolute level, because banks differ by metres.
   - It is shown with the **minimum and maximum** status of those gauges, so disagreement is visible.
2. **Confidence, never "high".**

   | Confidence | Condition |
   |---|---|
   | medium | ≥ 2 gauges within 3 km that agree within one class |
   | low | nearest ≤ 5 km, agreement within one class, and (≥ 2 gauges or nearest ≤ 3 km) |
   | very low | otherwise; the UI then **shows no area verdict**, only the range and the gauges |
   | none | no fresh gauge within 8 km: "ประเมินไม่ได้" |

   Example, pin at 13.82, 100.60: only BKK021, 4 km away → very low, no verdict.
3. **Gauges nearby, categorized (D-040):** ≤ 15 km, separated into two clear groups:
   - **📈 Stations with tested forecasts (12–72 h):** HII/RID gauges with ML forecasts, showing forward-looking trend and delta12.
   - **📍 Nearest local canal/river gauges:** Active, fresh gauges (e.g. BMA canal sensors) showing real-time water level vs BMA threshold or bank.
   - Gauges with no data for > 24 hours are suppressed so inactive stations (e.g. `WL.JKK.01`) do not crowd out actionable data.
4. **Citizen evidence at the pin:** Traffy flood reports within ~1 km in 6 h, and our users' depth reports within ~1 km in 24 h. On the ground these beat any interpolation.
5. **Rain:** the Open-Meteo total for the next 24 h at the nearest of 8 forecast points, labelled as coarse.
6. **Warnings & Disclaimers (D-040):**
   - **Dynamic alerts:** when street flood reports conflict with calm canals (`street_flooding_despite_channels`), an urgent prominent alert banner appears at the very top.
   - **Static disclaimers:** general educational disclaimers (canal ≠ street, Bangkok terrain variation, polders/gates) are collapsed into an expandable `<details>` accordion ("ℹ️ ข้อจำกัดของข้อมูล (สถานีคลอง ≠ ระดับถนนหรือในบ้าน)"), keeping >40% vertical space open for actionable data.
6d. **Two yardsticks (D-038):** HII/RID status = level vs bank (§4). BMA status = level vs BMA warning/critical (drainage capacity), with over-bank still critical. The point check's area index mixes only status ranks, so the two combine without mixing levels (KI-217).
6c. **Observed trend ≠ forecast (D-037):** `change_m` is the difference between the latest reading and the earliest reading 1–3 h before it; it is labelled "ที่ผ่านมา" (past) and never extrapolated. The ladder's `trend12` remains the only forward-looking trend.
6b. **Street reports beat a calm channel picture (D-036):** when ≥ 3 Traffy flood reports lie within ~1 km in 6 h and the area category is normal/watch (or none), the warning `street_flooding_despite_channels` is shown and users are told to trust street reports first. The category itself is not changed: gauges and reports measure different things and are shown side by side.
7. **Report from the pin:** the feedback form attaches the pin's location with `loc_source = pin` (vs `gps`), so pin reports can be weighted lower. A pin can be placed anywhere.
8. **Point Forecast Outlook & Trend Synthesis (USP: D-041, gated by confidence per D-042):** Clicking any coordinate synthesizes a 12–24h outlook (`/api/point` field `forecast`, `point_forecast()`) from **only the evidence that actually reaches that point**:
   - **Canal/river gauge trend** — used *only* when the point's own `area.confidence` is `low` or `medium` (the same gate §2.10.2 already applies to the overview card). At `very_low`/`none` the outlook carries no canal claim at all — it must not contradict the card above it. Trend requires a **strict majority** of same-water-body forecast gauges (khlong drives "canal" wording; a lone tidal river gauge is labelled, never used alone).
   - **24h precipitation** (Open-Meteo) — usable everywhere (needs no nearby gauge), worded by the **TMD rain-amount categories** (ฝนเล็กน้อย 0.1–10.0 · ปานกลาง 10.1–35.0 · หนัก 35.1–90.0 · หนักมาก ≥ 90.1 mm; tmd.go.th "เกณฑ์อากาศ", read 2026-09-27; the page gives amounts without a period, and we apply them to the 24 h forecast total ⚠️) as a *condition*, never folded into a "risk is low" verdict. Unknown rain omits the sentence.
   - **Crowdsourced street reports** (Traffy, ≥3 within 1 km / 6 h) — usable everywhere, can raise risk on their own.
   - Output: `risk` (`high`/`moderate`/`low`/`info`), `channel_trend`, `basis` (which of `rain`/`reports`/`gauges` were actually used), `title`, `desc`, rendered as `.forecast-banner`. `risk: "info"` (ℹ️) means only rain/reports were usable — it is stated plainly, never dressed up as "low risk" or "ปกติ".
   - **Distance-vs-agreement evidence for the confidence bands** (2026-09-27 snapshot, 264 fresh gauges): same-agency status agreement falls from 80–86% at 0–1 km to ~46–66% at 2–5 km to ~50% at 5–8 km (~31–45% baseline at 8–15 km); grouping by matching river name (a crude basin proxy) gave no improvement over plain distance. No polder polygons exist yet in this repo, so the existing distance/agreement bands remain the best available proxy for basin membership (D-042, KI-223).
9. **Human-centered forecast phrasing and confidence scaling (D-047, D-048):**
   - **Zero-crossing interval clarity:** Conformal quantile deltas (50% likely band) crossing zero are worded intuitively as `ทรงตัว (อาจแกว่งตัว -A ถึง +B ซม.)`, eliminating paradoxical mathematical translations ("ลด 11 ถึงเพิ่ม 17 ซม.").
   - **Progressive confidence scale:** Replaces harsh negative labels ("มั่นใจต่ำ") with a progressive dot scale: `●○○ คาดการณ์เบื้องต้น` (persistence baseline / 45-day empirical error band) and `●●○ คาดการณ์ปานกลาง` (harmonic tide model beating persistence by ≥30% with calibrated 90% coverage), with informative tooltips detailing backtest methodology.
   - **Nearest canal gauge visibility:** When area-wide status spread triggers `area.confidence = very_low`, the point outlook still surfaces the closest forecast station (`คลองใกล้เคียงที่สุด (ชื่อสถานี ห่าง X.X กม.)`) with its 12h change and an explicit distance disclaimer `*(ระดับน้ำที่สถานีคลอง ไม่ใช่ระดับน้ำที่จุดนี้หรือบนถนน)*` (D-021).
   - **Alert deduplication:** Top urgent road alerts are suppressed when the forecast banner is active in high-risk alert mode to eliminate duplicate warning fatigue.

**Not done, and why:** a depth at the pin needs ground elevation. Available DEMs (Copernicus GLO-30/90, FABDEM) have errors ≥ 1–2 m in Bangkok, larger than flood depths (KI-202), and GLO is a surface model (buildings). Planned (§13): polder polygons → the controlling gauge; FABDEM + σ → a probability category; calibrated against user depth reports.

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

### 3.3 What the live MVP implements (2026-09-26, [forecast/](../src/floodwatch/forecast/__init__.py))
- Candidates per station: **L0 persistence**, **L1 persistence + tide** (harmonic K1, O1, M2, S2, M4, MS4 fitted by least squares on the station's own 25 h-detrended data; only when ≥ 15 days of hourly data exist), and **L1 + damped 24 h trend** (trend only, for non-tidal stations).
- **History:** up to **one year** of hourly data per station (api-v3 `waterlevel_graph` serves ≤ 365 days, verified 2026-09-26; backfilled once in batches of 6 stations every 10 min and **once more at every worker start**, so frequent deploys can't starve it (KI-212); then refreshed with 3 days every 6 h) plus ~30 days of 10-min chart data for BKK/CPY/BKC/AIT and chart-only stations. The forecast reads up to 370 days.
- **Rolling-origin backtest** on the **last 45 days** (or the last 40 % of a shorter record), horizons 1, 3, 6, 12, 24, 48, 72 h. The tide used in the backtest is fitted only on data before that window (no leakage), so a long record gives the tide model a fair test while the error quantiles reflect the current flood regime. **First evidence (2026-09-26 ~10:00 UTC):** after its 1-year backfill (6,866 hourly values), C.12 Samsen serves the **tide** model at every horizon 1–72 h; with 30 days it was on persistence. **Network-wide, after the backfill completed (15:20 UTC, latest forecast of each of 107 stations):** **57 serve a tide or tide+trend method at one or more horizons** (mean history 6,805 h ≈ 9 months), against **44 of 95** at 09:54 UTC before it; **45 stay on persistence** (mean 5,454 h; the tide adds nothing at those horizons, as expected upstream of the tidal reach); 2 use trend only (no tide fit); 3 have too little history for a backtest (mean 41 h, new stations). The best candidate is served **only if its skill vs persistence is > 0.10**, otherwise persistence.
- **Intervals:** split-conformal, as empirical 5/25/50/75/95 % quantiles of the chosen method's backtest errors, interpolated between horizons. There are no intervals when the backtest has fewer than 30 errors.
- **Trend (12 h):** "steady" if the median change is within max(2 cm, half the 50 % band).
- **Recovery:** first crossing below bank of the q25/q50/q75 paths (≤ 72 h), otherwise extrapolation of the 24 h recession rate (low confidence). "Not estimable" when ≥ 30 mm of rain is forecast for the next 24 h at the nearest Open-Meteo point, or when the water isn't falling.
- **Status:** ≥ bank → วิกฤต; ≥ 90 % of ground→bank range → เตือนภัย; ≥ 70 % → เฝ้าระวัง; otherwise ปกติ (⚠️ heuristic, to be calibrated against official warning levels).
- **Coverage (2026-09-26 11:10 UTC; v0.2.0):** 111 focus stations, 96 on the map (14 at approximate OSM positions), 15 listed only. Earlier count at 10:40: 110 focus stations (Samut Sakhon and Nakhon Pathom added, D-023; `TEST*` and GLF002 excluded). **26 have no bank level** (status "unknown", no recovery) and **29 have no coordinates** (not on the map, excluded from "near me"): [KI-207](KNOWN_ISSUES.md). Stations that only the chart site serves have about 30 days of 10-min data, so the tide fit (needs ≥ 15 days) is available; a station with less data stays on persistence without intervals.
- **Tide reference gap:** the Fort Chula gauge (GLF001) and Bang Sai (CPY013) exist in the HII chart list but no history is retrievable. `getGraphFirst` and `POST /getGraph` (with CSRF token) both answer HTTP 500, and `queryStation`'s `water1` stayed at 0.03 m for ≥ 35 min at a tide gauge, i.e. frozen (2026-09-26, KI-207). Until then regime B relies on each station's own tide fit; getting GLF001 history is the highest-value data task ([HANDOFF §5](../HANDOFF.md)).
- **24 h outlook** (`outlook24`): the hour at which the median path peaks, shown as a ±1 h window with the 50 % range, **only when a tide model is served** and the median varies by > 5 cm. Under persistence the median just drifts with the per-horizon error bias; CPY015 showed a spurious "peak" at +24 h before this rule. Also a **chance of reaching the bank** category: < 5 %, 5–25 %, 25–50 % or > 50 %, from the maximum over 1–24 h of the per-horizon conformal quantiles. ⚠️ This is a *lower bound* on "reaches the bank at some time in 24 h" (marginal quantiles, not a joint path probability), so it is shown only as a category (D-005).
- **Status after 24 h without data** is "unknown"; the last value is shown, marked stale.
- Not yet implemented: routing (L3), polder storage, ML (L4/L5), ensembles, and polder-aware "near me" (nearest by distance only).

### 3.4 Network statistics shown to users (`/api/stats`)
A compact strip at the top of the page answers "how bad is it, and can I trust the data?":
- **Status chips** (ล้นตลิ่ง / ใกล้ตลิ่ง / เฝ้าระวัง / ปกติ / ไม่ทราบ), each with a count. Tapping one filters the list.
- **Trend counts** (rising / falling over 12 h) and the **maximum Open-Meteo rain total for the next 24 h** over the Bangkok points.
- **Reporting freshness** for the focus gauges (100 after removing `TEST*`) (within 1 h / 3 h / 24 h) with a 3-colour bar; the **whole HII network** is behind a "ทั้งประเทศ" toggle. Example at 09:17 UTC: focus 79 / 95 / 98 of 104; network 434 / 783 / 823 of 840, with 17 older than 24 h or never reporting. Also the metadata gaps (no coordinates / no bank level).

Why these and not more: status and trend answer the citizen's question; freshness tells them whether to trust it. Per-agency or per-basin breakdowns belong in `/api/health`, not on a phone screen.

### 3.5 Citizen feedback loop (`POST /api/feedback`)
- **What users can send**, all optional but at least one of:
  - a **verdict** on what we show at a station (ตรง / น้ำจริงสูงกว่า / ต่ำกว่า / ไม่แน่ใจ);
  - the **water depth where they are** (none / ankle ≤ 20 cm / knee ~50 cm / waist ~1 m / above);
  - a **note** (≤ 280 characters);
  - an **opt-in location**, rounded to 3 decimals (~100 m).

  The "near me" box also offers a location-only depth report.
- **What the server adds:** a **snapshot of what the site showed at that moment** (level, status, freeboard, trend, recovery, forecast issue time), so every report can be scored against the forecast that was actually displayed.
- **Privacy and abuse** ([GUIDELINES §5](GUIDELINES.md)):
  - no names or contacts;
  - the IP is never stored, only `sha256(FEEDBACK_SALT + date + IP)` for rate limiting (10 per hour), so senders can't be linked across days;
  - a honeypot field catches bots;
  - notes are **never published**; the public sees counts only (`/api/feedback/summary`, and 7-day counts in the station detail).
- **How it feeds the system.** Feedback is an **input to people and to evaluation, never an automatic model change**, because a flood site attracts both honest error and manipulation.
  1. **Verification:** the "higher/lower" share per station and lead time is tracked with the §14 metrics. A station with ≥ 3 disagreements outnumbering "matches" in 7 days gets `review: true` and a "ทีมงานกำลังตรวจสอบ" note.
  2. **Data quality:** reports that disagree with a gauge are usually a stuck sensor, a datum or bank-level error, or a gauge in a different water body. They trigger checks, not edits.
  3. **Depth ground truth:** depth reports plus location become labels for §13 (DEM, HAND and polder calibration), weighted with Traffy.
  4. **Model features (Phase 2+):** only aggregated, de-duplicated and outlier-screened counts, and only if they improve the backtest.
- **First evidence of use (2026-09-26 10:17–14:56 UTC, ~4.5 h after launch):** **10 reports from 8 distinct senders** (daily-salted hashes).
  - Depth: 7 "ankle", 3 "knee". **7 came from a map pin** and 10 of 10 carried a location.
  - **6 had a note**, and the AI triage labelled all 6 *street-level drainage* (none "gauge mismatch", none urgent; the rule-based emergency check flagged none).
  - **0 of 10 used the station verdict buttons** (matches / higher / lower).
  - **Reading:** people report the water *at their own spot*, not whether the gauge is right. That supports the point check ([§2.10](#210-point-check-a-place-with-no-gauge-apipoint-d-021)) as the main feedback path. Sample size is tiny; the verdict question stays but needs a stronger prompt if it is to feed §14 (open item in [UX_VALIDATION](UX_VALIDATION.md)).
  - **Cost:** 41.7 neurons in 11 AI calls that day, out of a 3,000 budget, with no failures.

### 3.6 AI Feedback Triage: GLM and Cloudflare Workers AI (D-022, D-030)
**Tested and verified 2026-09-26**:

1. **GLM (Zhipu AI `glm-5.3-flash`, D-030)** — *Primary configured provider*:
   - REST endpoint: `https://open.bigmodel.cn/api/paas/v4/chat/completions` (OpenAI-compatible).
   - High speed, cost-effective, fluent Thai comprehension for informal citizen notes.
   - Tested live inside the worker container: reasoning tokens are parsed and structured classification succeeds (`{"category": "local_drainage", "urgent": false}`).
   - Avoids Cloudflare zone token scoping issues (`CF_AI_TOKEN`) and neuron quota limits.

2. **Cloudflare Workers AI (SEA-LION v4 27B, D-022)** — *Optional alternative*:
   - `@cf/aisingapore/gemma-sea-lion-v4-27b-it` via Cloudflare REST API.
   - Measured cost ~4.8 neurons per note. Free quota 10,000 neurons/day.
   - Fallback if `AI_PROVIDER=cloudflare`.

**Critical safety constraints:**
- **Summaries of the flood situation drift on safety terms** when generated by LLMs (e.g. SEA-LION transposed warning ↔ watch; Llama 3.3 claimed "nationwide"). Therefore, **AI is restricted strictly to background triage of user notes**. Situation summaries (`/api/summary`) are deterministic templates.
- **Instant emergency detection is rule-based:** regex/keyword matching triggers emergency hotline displays (1669 / 1784 / 191) immediately without network roundtrips. AI may *add* urgency, never remove it.

| Use | Status | Why |
|---|---|---|
| **Triage of feedback notes** (category + urgent) | ✅ live, worker task every 15 min | Low stakes, verifiable schema; helps operators filter emergencies, drainage, and spam (Q19) |
| Instant "urgent" response to the reporter | ✅ **keyword rules, not AI** | Must work without network latency or quota. AI may *add* urgency later, never remove it |
| Situation summary text | ✅ **template** (`/api/summary`) | Safety facts must be exact; prevents LLM drift on warning thresholds |
| Satellite flood extent validation | ✅ **GISTDA / GFM** | Observed satellite masks override pure model outputs |
| Traffy text → flood/drainage labels | 💡 later | Public text; selectively label uncertain reports |
| Voice reports (Whisper, Thai) for elderly users | 💡 later | Accessibility; transcripts go through the same privacy rules |
| Chatbot / Q&A | ❌ not planned | Hallucination risk on life-safety questions |

**If AI is unconfigured or fails, the site is completely unaffected:**
- AI runs only in the background worker; no public page or API request calls or waits for it.
- Circuit breaker: 3 consecutive failures pause AI for 1 hour.
- Deterministic rule labels remain active for all feedback reports.

### 3.7 Bangkok Canal Ingestion Architecture (v0.3.0 + v0.9.0, D-031, D-053)
**Dual-channel access for BMA canal telemetry:**
1. **Live snapshots across Bangkok (199 stations, codes `WL.*`):**
   - Ingested every 5 min via the People's Party relay (`bma_klong`, `https://flood69.peoplesparty.or.th/api/klongmap`).
   - Covers 199 stations (e.g. `WL.KTY.01` ส.คลองเตย, `WL.AJP.01` ค.อาจารย์พร, `WL.BKY.02` ค.บางเชือกหนัง, `WL.KLA.01` ค.ลาว ถ.พัฒนาการ, `WL.LPW.01` ปตร.คลองลาดพร้าว) with BMA warning/critical thresholds and gates (45) with inside/outside head levels.
   - History builds up locally from our own polling (since 2026-09-26).
2. **30-day 10-minute historical telemetering (key canal reaches, codes `BKK*`):**
   - HII ThaiWater telemetering operates parallel stations along primary Bangkok canals and serves **30 full days of 10-minute observations** (4,310+ points) via `GET https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}` without authentication or geo-blocking.
   - Cross-referenced pairs: `BKK001` (Khlong Lat Phrao) ↔ `WL.SST.01` (60 m distance), `BKK020` ↔ `WL.ANX.01`, `BKK021` ↔ `WL.BBU.01`, `BKK008` (Khlong Saen Saep) ↔ `WL.SSB.06` (80 m distance), `BKK005` (Khlong Phasi Charoen) ↔ `WL.TWW.05`, `BKK009` (Khlong Lam Pla Thio) ↔ `WL.LPT.03`.
   - Ingested automatically into `observation` through `hii_history` (`EXTRA_STATIONS`).
3. **Data integrity and datum rules:**
   - **Never mix BMA and HII levels directly (KI-217):** BMA gauges are referenced to local zero/datum, while HII stations are referenced to Mean Sea Level (m MSL / Ko Lak datum). Status ranks (normal/watch/warning/critical) can be combined in spatial index calculations, but raw numeric levels are kept separate.

**Road water levels (the BMA "roads to avoid" page), assessed, not integrated:**
- *Would it help?* In principle, yes, a lot. Street depth is the quantity residents care about and the one no gauge measures: it would validate the point check (which today only has Traffy counts and our users' depth reports) and could train a rain → street-ponding model per district.
- *In practice, not from this page:* it is a static page updated by hand (135 district reports from a spreadsheet + 55 sensor readings), positions are geocoded from street names (approximate), and there is no feed or licence. The sensors' own host is a private VPN portal (SOURCES §2c), which we must not touch. Scraping hand-made snapshots gives irregular, unrepeatable data: bad for training, fine for humans.
- *Decision:* **a link in the point card**, nothing more. If BMA ever publishes the road-sensor feed (55 points, depth in cm), it becomes the best validation set for §2.10: collect it like any gauge, but as depth above road, never converted to m MSL.

**Place search (D-032):** OSM Nominatim, not AI. The point check's 8 km radius was set when Bangkok had 10 gauges; with ~200 it mixes too many (at that Sai Mai pin: 21 gauges from normal to critical → very low confidence, no verdict). **Next:** a density-adaptive radius (e.g. the 5 nearest fresh gauges within 3 km when available), tested against user depth reports before shipping.

### 3.8 Web & Brand Asset Pipeline: Browser Tab Recognizability (v0.5.1, D-039)
- **16×16 CSS pixel scale rule:** Favicons in desktop and mobile tabs render primarily at 16×16 pixels. Any feature thinner than 3–4 px in a 64×64 viewBox becomes sub-pixel anti-aliasing noise at 16×16. Multi-nested droplet outlines, thin gauge ticks, and 1.8 px beacon dots collapse into an illegible smear.
- **Canvas area utilisation:** Narrow symbols (e.g. slender teardrops) waste 40–50 % of the available width on transparent margins, rendering only ~8 px wide. A rounded squircle tile (`rx=16` in 64×64) utilizes the full 14×14–16×16 pixel footprint.
- **High-contrast dual-tone wave:** Exactly one dominant motif—a bold white wave crest (`#ffffff`) over electric cyan water (`#38bdf8`) on vibrant royal blue (`#0284c7` to `#0369a1`). Delivers > 5:1 contrast against both dark-mode tabs (`#202124` / `#1e1e1e`) and light-mode tabs (`#dee1e6` / `#ffffff`).
- **Zero-dependency pure-Python rasterizer (`scripts/generate_favicon.py`):** Uses mathematical boundary evaluation with 2×2 supersampling (4 subpixel samples per pixel) and zlib PNG/ICO struct packing. Requires no third-party imaging libraries (PIL, Cairo), guaranteeing reproducible asset builds inside minimal Docker containers. Outputs:
  1. `web/favicon.svg`: Modern vector icon (803 bytes).
  2. `web/favicon.ico`: Dual-resolution Windows/browser icon (16×16 and 32×32, 793 bytes).
  3. `web/apple-touch-icon.png`: 180×180 high-res icon on deep oceanic squircle canvas (avoids solid-black iOS home screen backgrounds).
  4. `web/icon-192.png`: 192×192 PWA / Android home screen icon.

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
| Median ΔH(+12 h) > +kσ | "ระดับน้ำมีแนวโน้ม **เพิ่มขึ้น** X–Y ซม. ใน 12 ชม." |
| \|ΔH\| ≤ kσ (steady) | "[→ ทรงตัว] ใน 12 ชม. อาจแกว่งตัว -A ถึง +B ซม. <span class='conf-badge'>ⓘ</span>" (D-048) |
| Median ΔH < −kσ | "ระดับน้ำมีแนวโน้ม **ลดลง** X–Y ซม. ใน 12 ชม." |
| Conformal confidence (medium) | `ⓘ` สีฟ้า = "คาดการณ์ปานกลาง (ทดสอบแบบจำลองย้อนหลัง 45 วัน แม่นกว่าค่าคงที่)" (D-049) |
| Conformal confidence (low) | `ⓘ` สีเทา = "คาดการณ์เบื้องต้น (อิงสถิติหรือความคงที่ 45 วัน)" (D-049) |
| P(H > H_bank) | "โอกาสน้ำล้นตลิ่งภายใน 3 วัน: 30%" |
| Recovery distribution | "คาดว่าน้ำจะลดต่ำกว่าตลิ่งประมาณ 2–5 ต.ค. (หากไม่มีฝนตกหนักเพิ่ม)" |
| Daily high water (tidal) | "สูงสุดราว 18:00–20:00 น." |
| Stale input | "ข้อมูลล่าสุดเมื่อ … (⚠️ ข้อมูลเก่า แหล่งข้อมูลอาจขัดข้องชั่วคราว)" |
| Elevation datum | Fresh timestamp prominent; surveying datum tucked into `[ม.รทก. ⓘ]` (D-049) |


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

## 19. National scope: monitor first, forecast later (D-044, 2026-09-27; forecast gate per gauge since D-064, §19.8)
The owner asked how the app could cover all of Thailand. The research ([Research_NATIONWIDE.md](../research/Nationwide/Research_NATIONWIDE.md) 🟢, [Research_Thailand.md](../research/Nationwide/Research_Thailand.md) 🔴) was checked live in [VALIDATION_2026-09-27_nationwide.md](../research/VALIDATION_2026-09-27_nationwide.md). Nothing here is built yet: the owner asked for validation first.

**Decision (D-044):** first a national **monitoring** view (measured levels against *official* thresholds, reservoirs, flash-flood products of the agencies, satellite extent when available); forecasts only per flood type and only where a backtest passes (§14, GUIDELINES §2). Audience: residents in any province, and local officials and volunteers (อบต., อสม., rescue).

### 19.1 What changes outside Bangkok
| Bangkok today | Elsewhere | Consequence |
|---|---|---|
| Tide dominates the lower river (§5, §8) | Inland stations have **no tide**; coasts and river mouths do (28 Navy tide stations, Gulf and Andaman, SOURCES §2d) | Tide features only for coastal/tidal types (F6 below) |
| Flow from upstream and pumps | **Reservoirs control many rivers** (50 large dams, 448 fresh medium reservoirs) | Show storage and release; a release *forecast* needs rule curves, which **no feed carries** (RID/EGAT documents needed) |
| Every HII gauge has a bank level | Many stations **lack an official flood level** | Priority list in §19.3; never invent one |
| Gauges every ~8 km in the metro | Sparse; many valleys have none | Tiers (§19.2), virtual gauges (§19.5) and **GISTDA satellite extent** (§19.4b), categories only |
| Sources reachable from Germany | **DWR and RID answer only from a Thai IP** | A reliable Thai egress before any public national launch (D-046, KI-110) |

### 19.2 Flood types and data tiers (adopted from the research as the frame, 💡)
- **Types:** F1 regulated large river · F2 unregulated medium river · F3 flash flood in steep catchments · F4 slow flat-basin flood with backwater (Mun/Chi) · F5 Mekong mainstream · F6 coastal/tidal/lagoon · F7 urban pluvial · F8 reservoir spill. Each station, reach or tambon gets one or more tags; the tag chooses the message and, later, the model family.
- **Tiers:** A = long telemetry + official thresholds; B = telemetry without history or thresholds; C = no gauge (virtual gauge, satellite, FFPI only). **The UI always says which tier a statement comes from** (วัดจริง · ประมาณจากแบบจำลอง · จากดาวเทียม), GUIDELINES §6.18.

### 19.3 Thresholds, in order of preference (never invented)
1. **Official:** HII station `min_bank` / `warning_level_m` / `critical_level_msl`; HII FEWS `hii_waterlevel.csv` (66 stations, m MSL); **RID discharge thresholds** `rid_discharge.csv` (87 stations, m³/s); BMA's own warning/critical for BMA canals (D-038); DWR EWS station status (their classification, shown as theirs).
2. **Statistical**, only with ≥ 5 years of history: percentiles or return levels of annual maxima → worded "สูงกว่าปกติมาก (สูงสุดในรอบราว X ปี)", **never** "ล้นตลิ่ง".
3. **Virtual gauges:** GloFAS return-period discharges → category only.
4. None → show the level and its trend, without a verdict (as D-021/D-042 do for the point check).

### 19.4 Reservoirs and flash floods: use the agencies' products first
- **Reservoirs:** storage % against `normal_storage`, inflow and release trends, a spill flag when `dam_spilled > 0`; small-dam telemetry gives **level vs spillway** (a measured overflow margin, F8). No release forecast until rule curves are obtained; a rule-curve emulator (research §4.2) is a later Phase-2 item.
- **Flash floods:** show HII's **FFPI per tambon** and **DWR EWS status** as published, attributed and dated; our own Flash Flood Guidance (research §4.3) comes later and must be verified against DWR/DDPM events first.

### 19.4b Satellite flood extent (GISTDA) — observed water where no gauge exists
GISTDA's documented API (KI-510) returns flooded **H3 cells (~0.12 km²)** for 1/3/7/30 days, nationally (7 days on 2026-09-27: 49,761 cells), each with flooded area, exposure (population, buildings, road length, hospitals) and the satellite passes used (Sentinel-1, Radarsat-2, COSMO-SkyMed). Use: an **observed** tier-C layer ("จากดาวเทียม", with the pass dates), and for point checks outside cities ("ดาวเทียมพบน้ำท่วมในรัศมี … ช่วง 7 วัน"). **Never** read an empty result as "dry" in built-up areas: the Bangkok bbox had 0 cells in 7 days while streets flooded (radar misses water between buildings ⚠️). The recurrence layer (`flood-freq`) gives "flooded N times" polygons for context.

### 19.5 Virtual gauges (GloFAS) must be snapped
A point query returns the 5 km cell under the point, which may be a side cell: at Nong Khai the naive point gave **1–3 m³/s** and the cell ≈ 5 km away **≈ 9,000 m³/s** (the Mekong, 2026-09-27, KI-509). Rule: snap to the cell with the largest long-term discharge within ~5 km of the reach, store the chosen cell, compare only with that cell's own climatology (median/max), and show a category, never a level or a depth.

### 19.6 Rejected, and why
- **Street depth from HAND** (`d = H − HAND`, Research_Thailand §2.4): DEM error of 1–2 m exceeds flood depths; against D-019/D-021.
- **`api2.thaiwater.net`**: no DNS (SOURCES §3). **HII gates** (`watergate_load`): 12 of 2,315 rows fresh.
- **Egress relays** to reach blocked sources other than the owner's Thai egress for public pages (D-014/D-016); **token APIs** with tokens copied from web bundles.
- **Evacuation instructions** generated by our code: link official channels instead (D-005).

### 19.7 Order of work (D-045, D-046)
1. **Bangkok, via HII's government channel:** BMA canals from `canal_waterlevel` as primary (relay as fallback, +73 gauges), BMA **road sensors** as a map layer and as point-check evidence (measured cm on the road, not an interpolation), Navy tide predictions, RID discharge thresholds at C.2/C.13. Validated 2026-09-27, not built.
2. **Local nightly backup** before national data grows (none exists today, KI-511).
3. **National collectors behind a flag**, lean: dams daily, FEWS thresholds daily, FFPI every 6 h, tide daily, DWR hourly via the Thai egress; 90-day retention for high-volume series; freshness filters on every HII national feed (KI-111).
4. **National map** only after HII/DWR/RID have been informed (D-046) and a reliable Thai egress exists.
5. **Forecasts per flood type**, each with its own backtest on verified events. Candidate models by flood type, from the Bangkok experiments of 2026-09-27 (network STAR + rain, SSN, k-NN analogues, GTWR, ST-GNN): [research note §8](../research/2026-09-27_forecast_48h.md#8-keep-for-the-nationwide-phase-owner-2026-09-27-the-other-methods-might-be-useful-outside-bangkok).

### 19.8 Nationwide parity (v0.16.0, D-064, 2026-09-30)
The owner asked for the same experience everywhere. What changed, and the evidence for each choice:
- **History:** a year per gauge from HII `waterlevel_graph` (one request each; URTU07 8,537 hourly readings), bounded by a 400-day retention (BMA never deleted). Measured need (40 Bangkok gauges, same 45-day test window): 48 h mean skill 0.20 / 0.20 / 0.20 with 60 / 90 / 180 days of history, **0.28 with 365 days** (36/40 over the gate): a full wet season is what `star` learns from.
- **Why history alone is not enough:** a year of own history for 12 nationwide gauges gave **0/12** any skill over persistence (no tide inland; trend never wins). Inputs are what matter:
  - **Rain per gauge:** the gauge's 0.5° Open-Meteo cell (`rain_cells.cell_of`; halves round up), forecast and a year of previous-run rain, exactly like the Bangkok rain points. Focus gauges keep `RAIN_POINTS`. A place (pin) uses a Bangkok rain point within 0.5°, else its cell.
  - **Upstream gauges learned per basin** (`forecast/upstream.py`): candidates in the same HII basin within 250 km; score = best correlation of the candidate's 24 h change `lag` hours earlier with the gauge's 24 h change, lag 0–48 h, on hours **before the backtest window only**; kept when the best lag is ≥ 1 h (it *leads*) and r ≥ 0.5, top 2. A co-located gauge of another agency peaks at lag 0 and is never "upstream" (24 h changes autocorrelate strongly at lag 1, so "lag ≥ 1 with the best r" alone would pick it). Changes, not levels, so datum offsets cancel (KI-217). Relearned daily.
  - The backtest decides per gauge and horizon, as in Bangkok (§14, SKILL_GATE 10 %).
- **Pins outside Bangkok** (`point.pin_mode`): where the nearest gauge is a Bangkok-area gauge, the polder rule holds (a river gauge never judges canals, D-059); elsewhere every waterway gauge is local evidence, the Bangkok-only cautions (polders, uneven Bangkok ground) are not said, and the sentences name the river ("แม่น้ำ"/"ลำน้ำ") instead of "คลอง".
- **Water word** (`point.water_word`): from the agency's river name — แม่น้ำ/แคว/น้ำ → แม่น้ำ; คลอง/คู → คลอง; ลำ/ห้วย/เหมือง/ร่อง → ลำน้ำ; บึง → บึง; no name: BMA and Bangkok-area gauges "คลอง" (gates), CPY* "แม่น้ำ", elsewhere "ลำน้ำ". Never guessed from the station name.
- **Results (`scripts/backtest_nationwide.py`, 2026-10-01 14:20 UTC, after the backfill — 808/808 gauges — and with 160/177 rain cells and learned upstream for 326 gauges):** Bangkok regression unchanged (40 gauges: mean skill 0.38/0.28/0.29 at 12/24/48 h; 36/40 over the gate at 48 h). Nationwide (51 gauges sampled across all regions out of 675 with ≥ 300 days; rain history for 47, learned upstream for 25): own methods only 9/8/6 of 51 over the gate at 12/24/48 h (mean 0.06/0.03/0.03); **with rain cells + learned upstream 27/19/19 of 51** (mean 0.18/0.09/0.07; `star` chosen 24/16/16). The inputs triple the gauges with a proven 48 h line, but outside Bangkok only ~37 % earn one (Bangkok ~90 %); the rest show a range only. (The 2026-09-30 preliminary run had 20 gauges and no rain history.)

### 19.9 Measured rain and the river near a pin (v0.16.3, KI-254)
- **Measured rain** (`point.measured_rain`): the nearest HII rain gauge within 10 km with a reading ≤ 3 h old; last 24 h in the TMD bands used for the forecast (§ rain words), last hour in mm, with the reading's time. ≥ 35 mm/24 h (TMD "heavy") raises the outlook to at least "moderate" ("ฝนตกหนักในพื้นที่ เฝ้าระวังน้ำขังบนถนน"); 10–35 mm is mentioned in the text. A measurement is a fact about the past 24 h; the forecast line stays forward-looking.
- **River near a Bangkok pin:** the nearest fresh river gauge within 3 km is its own line (distance to bank, status), never mixed into the canal verdict (D-059).

### 19.10 Fine rain for the Bangkok region, and what the rain gauges tell us (v0.16.4, Q42)
- **Fine grid** (`rain_cells.fine_of`, `fine_points`): a lattice anchored on Open-Meteo's own grid near Bangkok (0.0703° lat × 0.08265° lon, measured 2026-10-01), the 3 × 3 cells around every gauge in the six Bangkok-region provinces (111 points). Used for pins (`rain_point_at` prefers the fine point when it has a fresh forecast) and the region rain line. Not used by the forecast model yet: its skill was proven on `RAIN_POINTS`; moving it needs a year of fine-point previous-run rain and a new backtest.
- **Measured vs forecast rain (one day, 2026-10-01):** among 151 HII rain gauges with a day-ahead forecast for the same 24 h at our sampling point, all 78 that measured ≥ 10 mm had been forecast < 10 mm; all 14 with ≥ 35 mm had been forecast "light" (87.8 vs 3.4 mm, 60.0 vs 0.9 mm, …). Convective downpours are missed in place and amount by the forecast at this sampling, so measured rain is the better signal for "now". ⚠️ One day of evidence at coarse sampling points; not a verification study.
- **Measured rain as a `star` input (Q43, tested 2026-10-01): daily totals do not help.** Leakage-safe daily features (last complete day, 3- and 7-day sums; mean of ≤ 3 gauges within 10 km; usable from 08:00 ICT on the labelled day) vs a day-shuffled placebo, production backtest: Bangkok no gain (same as placebo), nationwide −0.5 to −1.2 % median RMSE (12/21 gauges, not significant), slightly worse after ≥ 35 mm days. A daily total arrives after the canals already responded. **Hourly** accumulations of the last hours remain the candidate; our own archive (kept 400 days near water gauges) allows a re-test ~mid-December 2026. Full write-up: [research/2026-10-01_measured_rain.md](../research/2026-10-01_measured_rain.md). Rain gauges are single instruments: a QC against neighbours before they drive anything automatic.

### 19.11 Basins and rivers (v0.17.0, D-066)
- `basins.basin_of` (point in the 22 HII basin polygons), `basins.river_of` (≤ 2 km from one of 93 main river lines), `basins.river_systems` (rivers whose line ends lie ≤ 1 km from another river join one system). Learned upstream gauges (§19.8) must share the basin polygon and, when both are on main rivers, the system. Experiment (39 gauges): neutral (1/39 changed), so adopted for physical soundness; basin-mean rain and an upstream-cells rain proxy did not beat the current own-cell rain (placebo: wrong-place rain clearly worse). Write-up: [research/2026-10-02_basins.md](../research/2026-10-02_basins.md).
- **Upstream line:** the first upstream gauge's measured 24 h change (`observed24`, the list's words) and its learned lag ("มักถึงที่นี่ในราว N ชม."); the Chao Phraya chain shows the gauge without a lag.

### 19.12 Validating basin data, and rain in the water rows' layout (v0.17.1–v0.17.2, D-067)
- **Validate a new map against the one in use before using it:** ONWR's legal 22 basins vs HII's `basin.json`, point in polygon for every gauge (1,011 of 1,026 identical; differences on boundary lines ≤ 0.1 km and a spelling). Same scheme → no new information.
- **Test a physical idea with a control:** cross-basin upstream links were tried open (any basin on the river system: worse, wrong-direction links such as Mun ← Mekong backwater) and directed by the basin hierarchy (only feeder basins: no qualifying link). HydroBASINS catchment rain vs own cell vs a placebo catchment on all 296 gauges whose catchment spans > 1 cell: a 29-gauge hint did not replicate, the placebo was clearly worse. Lesson kept: run the full set before believing a small-sample hint.
- **Rain uses the water rows' layout** (`rainRows`): forecast as a row "อีก 24 ชม. [chip] ราว N มม. ⓘ", what fell as "24 ชม. ที่ผ่านมา: …"; the headline never repeats an amount (KI-258). **Horizon words:** "อีก N ชม." in rows, "ในอีก N ชม." in sentences, "N ชม. ที่ผ่านมา" for the past (KI-259, `tests/test_wording.py`).

### 19.13 Plain words and the AI helper (v0.18.0–v0.18.6, D-068)
- **Rules tell the story, AI retells one sentence.** `explain.plain` (under the headline) and `explain.answer` (six fixed questions) are templates over the same data as the panel: the lead gauge as the panel picks it, its distance ("ไกล" when far or when the area gauges disagree — never "แถวนี้"), how full now (cm below the bank, or over the BMA level), the observed 24/48 h change (`observed24`), the 24/48 h rows by the app's own rule (`trendRow`: direction / ±5 cm steady / unclear, D-060) with the range in words ("half of past cases" for an unclear row), rain and street reports, the app's limits, and advice that gets firmer only on the panel's own warning signals.
- **Story first, numbers folded, AI on request (v0.18.4–v0.18.6).** The owner compared v0.18.3's labelled lines with a weather app's AI card ("they try to explain easily"): the answer now leads with `explain.narrative` (3–4 everyday sentences, at most a couple of numbers), the lines go under "ดูตัวเลข", and GLM runs only behind one button. Retelling a rule story passes the checker 91 % of the time (198 answers, median 4.0 s).
- **Unclear rows say what is possible (v0.18.7).** `_possible`: a range on both sides of zero within ±10 cm → "น่าจะเปลี่ยนไม่มาก อาจลดลงราว a ซม. หรือเพิ่มขึ้นราว b ซม."; wider → "ยังไม่ชัดว่าน้ำจะขึ้นหรือลง" + the same span; one-sided → "อาจเพิ่มขึ้น/ลดลงราว … แต่ยังไม่แน่ชัด". `_bank`: the highest upper end of the 24/48 h 90 % ranges (`range90`, ~9 in 10 past cases) against the cm left to the bank → "อาจถึงตลิ่งได้" (≥ margin), "อาจเข้าใกล้ตลิ่ง" (< 10 cm short), "ยังไม่น่าจะถึงตลิ่ง" (≥ 10 cm short). Ko Kret 2026-10-02: 50 % −5…+10 cm, 90 % up to +61 cm, 33 cm left → "น่าจะเปลี่ยนไม่มาก … แต่ถ้าน้ำขึ้นมาก อาจถึงตลิ่งได้".
- **The AI sentence must be checkable.** One short sentence (≤ 220 chars) from the lines, with checks for numbers, directions, tense (a past change told as the future), strength, verdict words, "cannot tell", far-vs-here, language. Measured on the same 198 real answers: whole-answer rewording 43 % pass; one-sentence retelling 61 % with the first checker, 83 % with the final one on the same answers, 86 % on 198 fresh answers (median 3.1 s).
- **Validate like a resident would read it.** `scripts/ai_explain_validate.py` samples real places (half Bangkok, half elsewhere) × six questions; read the passing answers, not only the pass rate.

### 19.14 Satellite maps, GloFAS and WeatherNext: what they can and cannot do here (2026-10-02, D-069, D-070)
- **Satellite (GFM + GISTDA), research only.** Sentinel-1 radar imaged the lower Chao Phraya on 6 days in 30 (median 7.3 h to publication) and is blind on 61–71 % of land in Bangkok, Nonthaburi and Pak Kret (GFM exclusion mask); it mapped no flood in central Bangkok during the event, while open rice land showed 9–32 %. GFM and GISTDA agree on 89 % of GISTDA's cells where GFM could see. Near gauges, flood was seen at 38 % of over-bank moments vs 4 % of low ones. → Never "no flood here" from a satellite; a future line may say "seen", where the radar can see, GISTDA first ([research](../research/2026-10-02_satellite_flood.md)).
- **GloFAS 3–7 day outlook: rejected.** Upper bound (GloFAS's own discharge including its true future change) adds nothing over the gauges' own trend at 12 main-river gauges (median −1.6 % to −2.5 %); daily GloFAS vs RID measured discharge r ≤ 0.6. Snapping (§19.5): with a discharge gauge, choose the cell closest to measured flow, else the nearest cell with ≥ half the largest flow ([research](../research/2026-10-02_glofas_outlook.md)).
- **WeatherNext 3: backtest only.** Compare its daily rain (64-member mean and p90, issued 00 UTC the day before) with Open-Meteo's previous-day forecast against HII gauges within 10 km of the 9 rain points (`research/2026-10-02_weathernext_rain.py`, dry run first, ≤ 50 GB). A gain would still need a decision about Google's terms before any public use.
- **Pin modes (D-070):** polder rules only where the nearest gauge is in กทม./ปริมณฑล; upstream focus provinces use the national rule (the nearest river or stream gauge is local evidence).

## 20. Forecasting 48 h ahead and outside forecasts (D-050, 2026-09-27)
Full evidence and re-runnable scripts: [research/2026-09-27_forecast_48h.md](../research/2026-09-27_forecast_48h.md).
- **What is shown:** 12 h and 24 h change per gauge (§4, `change_summary`); a **48 h line only where the 48 h backtest gives "medium"** (7 of 102 gauges on 2026-09-27, all tidal river/estuary). At high gauges with no forecast fall: "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า". Never "stable for 48 h".
- **Why the model stops at ~24 h:** it uses only each gauge's own past (tide + trend). Two inputs are missing, and both were measured to help (single 45-day window, honest split):
  - **Upstream flow and dam release** (network space-time AR): Ayutthaya 48 h RMSE 26.8 → 18.6 cm; little gain on the tidal reach.
  - **Forecast rain** (Open-Meteo `previous_runs`, forecasts issued 1–2 days earlier): canal BKK021 42.9 → 36.5 cm, Samsen 22.3 → 18.1 cm; biggest gains before heavy rain.
- **Neighbourhoods:** neighbours along the river network beat neighbours by distance and k-NN analogues everywhere; distance neighbours can hurt (they mix canals and basins). SSN, GTWR and ST-GNN assessed and kept for later (research note §4, §8), with notes on where they may fit nationally.
- **Outside forecast (HII FEWS):** archived per issue in `external_forecast` and scored by `scripts/score_hii_forecast.py` against "no change" and ours on the same issue times; shown only if it wins, with its assumption (C.13 release held constant).
- **Built (v0.8.0, D-052):** per-gauge network STAR + rain is the method `star` in `forecast.evaluate`, chosen only where it wins on the same rows and passes the skill gate. Validated on 3 windows and out of sample (choose on one window, score on the next): the gain held at 87–100 % of gauges; 48 h skill ≥ 0.3 at 35 gauges (was 8). Details: [research §9](../research/2026-09-27_forecast_48h.md). Still to do: out-of-sample interval coverage and event scores ("reaches the bank within 48 h").
- **v0.10.0 (D-054, D-055):** BMA canal gauges now carry a year of history (HII canal graph), so they enter the same backtest. Dry run on 85 BMA gauges (2026-09-27): `star` wins at 12 h on 46, with skill ≥ 0.3 on 17; at 24/48 h almost none reach 0.3 — canal levels are driven by pumps and gates no model sees. A 48 h line is now shown everywhere a forecast exists; unproven ones show only a range.

## 21. Discoverability: how the site is found and previewed (v0.15.3, KI-248, 2026-09-30)
- **What is indexable.** The app is one page; every view is a `#fragment` (`#s=CODE`, `#p=lat,lon`), which search engines fold into the home URL. So the sitemap has one URL and the head carries the story: title, a description with the same horizons as the app (12–48 h), canonical, JSON-LD `WebApplication` (only facts true today: name, URL, free, MIT, repository; no rating or price), and a `<noscript>` line for crawlers and readers without JavaScript. Per-station pages would need server-side rendering; not built ⚠️ (would only pay off if station names are searched).
- **What crawlers must not reach.** `robots.txt` keeps `/api/docs`, `/api/openapi.json` and `/api/point` out (the point check is one heavy call per coordinate; KI-246 showed what traffic does to the pool). Data endpoints the page needs stay open so a rendering crawler sees the list.
- **Link previews.** `og:image` is a 1200×630 JPEG (~100 KB, under LINE/Facebook size limits) made from the real phone screenshots; GitHub's social preview is the 1280×640 PNG of the same design. Both come from `scripts/make_social_images.py` (Chromium renders the Thai text; Pillow would need a shaping engine). Preview cards are cached by the platforms: re-scrape after a change.
- **Not measured.** No ranking, click or share data exists; the owner has no analytics (D-032 forbids logging place searches). Judge the work by what is checkable: 200s for the files, valid JSON-LD, the image rendering in a chat app.
