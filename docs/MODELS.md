# MODELS.md — How BKK FloodWatch calculates, forecasts and decides

> Owner, 2026-10-04: "We would like to understand how we can calculate, how to setup the model, which parameters are
> applied. What have we tried already, good or bad results, and why we go this way … like Architecture Decision Report.
> What kind of data do we need more in the future." This document answers that for developers, reviewers and agencies.
> It describes **v0.26.0** (code in `src/floodwatch/`); §5d records the honest-improvement work of 2026-10-04 (Q52). Numbers come from running code or the cited research files;
> decisions link to [plan/DECISIONS.md](plan/DECISIONS.md) (D-IDs) and pitfalls to [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## สรุปภาษาไทย (หนึ่งหน้า)

**แอปตอบอะไร** — น้ำในคลอง/แม่น้ำใกล้ฉัน *ตอนนี้* อยู่ห่างตลิ่งเท่าไร และ *ในอีก 12–48 ชม.* น่าจะขึ้นหรือลง พร้อมบอกว่ามั่นใจแค่ไหน
แอปวัดน้ำ **ที่สถานีวัด** ไม่ได้วัดที่บ้านหรือบนถนน

**ข้อมูลที่ใช้** — ระดับน้ำจากสถานีของ สสน. กรมชลประทาน กฟผ. มูลนิธิ และ กทม. (กว่า 1,000 สถานี ทุก 10 นาที) · ระดับตลิ่งของแต่ละสถานี ·
ฝนคาดการณ์ (Open-Meteo) และฝนที่วัดได้ (สสน.) · การปล่อยน้ำเขื่อนเจ้าพระยา · รายงานน้ำท่วมถนน (Traffy) · เสาวัดน้ำ กรมทรัพยากรน้ำ (แสดงเฉพาะแนวโน้ม)

**สถานะตอนนี้** — เทียบระดับน้ำกับตลิ่ง: ล้นตลิ่ง (เกินตลิ่ง) · ใกล้ตลิ่ง (≥ 90 % ของความลึกตลิ่ง) · เฝ้าระวัง (70–90 %) · ยังรับน้ำได้ ·
คลอง กทม. ใช้เกณฑ์ของสำนักการระบายน้ำ กทม. เอง

**การคาดการณ์** — ทุกสถานีมี "บันได" วิธีคาดการณ์หลายแบบ (ค่าคงที่, น้ำขึ้นน้ำลง, แนวโน้ม, แนวโน้มล่าสุด, และแบบจำลอง star ที่ใช้ฝน +
น้ำจากต้นน้ำ + เขื่อน) แต่ละสถานีและแต่ละช่วงเวลา **ทดสอบย้อนหลัง 45 วัน** แล้วใช้วิธีที่แม่นที่สุด แต่ต้องแม่นกว่า "ถือว่าน้ำคงที่"
อย่างน้อย 10 % ไม่เช่นนั้นใช้ "ค่าคงที่" ช่วงที่บอก (เช่น "−3 ถึง +11 ซม.") มาจากความคลาดเคลื่อนจริงในการทดสอบย้อนหลัง

**แนวโน้ม "น้ำยังขึ้น / ทรงตัวหรือลดลง"** — ใช้การคาดการณ์ 24 ชม. เมื่อมั่นใจ (ขึ้น ลง หรือทรงตัว ±5 ซม.)
ถ้า "ไม่แน่ชัด" ใช้การเปลี่ยนแปลงที่วัดได้ล่าสุด (24 ชม. แต่ถ้า 6 ชม. ล่าสุดหยุดหรือกลับทิศ ถือว่าหยุด)

**แท็บจับตา** — รวมสิ่งที่ควรรู้ล่วงหน้า 24–48 ชม. ตัวเลข "6 ใน 10" คือ **สถิติจริงของแอปเอง** 30 วันที่ผ่านมา ว่าเมื่อแอปคาดแบบนี้ เกิดจริงกี่ครั้ง

**ปรับปรุงแบบจำลอง (4 ต.ค. 2569, ทดสอบแบบไม่โกง: เลือกวิธีจากครึ่งแรก วัดผลครึ่งหลัง ยืนยันกับสถานีอีกชุดที่ไม่เคยเห็น)** —
แบบจำลอง star อ่านค่าเพิ่ม: ระดับน้ำเทียบค่าเฉลี่ย 7 และ 30 วัน และการเปลี่ยนแปลง 1/3/72 ชม. ความคลาดเคลื่อนลดลงจาก "ถือว่าคงที่"
−5.3…−6.6 % เป็น −8.3…−9.4 % ที่ 24–72 ชม. (สถานีชุดที่สอง) · สิ่งที่ลองแล้วได้น้อยหรือไม่ได้: เฉลี่ยหลายวิธี (+0.4–0.9 จุด),
ช่วงคาดการณ์ตามแนวโน้ม (แคบลงแต่พลาดบ่อยขึ้น = ไม่ซื่อตรง จึงไม่ใช้), ใช้ Google Flood Hub เป็นข้อมูลเข้า (+0.9 จุดที่ 72 ชม. เท่านั้น)
· ตรวจย้อนหลัง 30 วัน: ช่วงที่แอปบอกที่ 24 ชม. ถูกตามที่บอก (50 % ถูก 51 %) แต่ที่ 72 ชม. มั่นใจเกินไป (ถูก 44 %) และมักพลาดด้านต่ำ (น้ำลดมากกว่าที่คาด)

**สิ่งที่ลองแล้วไม่ใช้** — ภาพดาวเทียม GISTDA (คลาดเคลื่อน อาจทำให้เข้าใจผิด) · GloFAS (ไม่ช่วยในเจ้าพระยาตอนล่าง) · ฝนรายวันที่วัดได้ใส่ในแบบจำลอง (ไม่แม่นขึ้น) ·
แบบจำลองไฮดรอลิกร่างแรก (ให้ผลไม่สมจริง)

**ข้อมูลที่อยากได้เพิ่ม** — สถานีวัดน้ำของกรมชลประทาน (Telerid) · ฝนรายชั่วโมงย้อนหลัง · แผนการปล่อยน้ำเขื่อนและการเปิดประตูระบายน้ำ ·
ระดับถนน/บ้าน (DEM ละเอียด) · ระดับตลิ่งที่ตรวจสอบแล้ว · ข้อมูลน้ำท่วมจริงย้อนหลัง

---

## 1. What the app answers, and what it does not

- **Question:** for a canal or river near me, how far is the water from the bank **now**, and will it rise or fall in
  the **next 12–48 h** — with a range and how sure we are (D-005: ranges, probabilities, conditions; never countdowns).
- **Not answered:** water depth at a house or street (gauges measure channels, D-021); interpolated flood maps over land
  (D-019); official warnings (we are not the authority; every page says so).
- **Space and time are explicit** (D-008): every value belongs to a gauge, a time and a datum (m MSL, Ko Lak); times are
  stored in UTC; each source's timezone convention is handled at parsing (KI-201, KI-205).

## 2. Data flow

```
sources ──► collectors (worker, every 10 min … weekly) ──► PostgreSQL (observation, station, weather_forecast, …)
                                                              │
               forecaster container (every 30 min) ◄──────────┘──► forecast_run (paths), forecast_model (backtests)
                                                              │
                     API (FastAPI, 60 s snapshot) ──► list · map · sheets · river tab · จับตา · pin check
```

| Source | What | Cadence | Notes |
|---|---|---|---|
| HII `waterlevel_load` (+ chart API) | 808 + 32 gauges: level m MSL, bank, discharge, sub-basin | 10 min | RID rows hourly; all of HII's feed is ingested (2026-10-03) |
| HII `waterlevel_graph` / BMA canal graph | 1-year hourly history per gauge | backfill + daily | trains the models (D-018, D-054) |
| BMA canals via flood69 relay | 200 canal gauges, BMA warning/critical levels | 10 min | own datum; never mixed with HII/RID (KI-217) |
| Open-Meteo | rain forecast per 0.5° cell / ~8 km point, previous runs as hindcast | 1–3 h | model input and rain words |
| HII `rain_24h` | measured rain, all provinces | 15 min | shown; hourly archive near water gauges (Q43) |
| RID C.13 discharge | Chao Phraya Dam release | hourly | input for gauges below the dam |
| Traffy Fondue | street-flood reports (location only) | 10 min | shown beside gauges, never merged (D-036) |
| DWR EWS | 455 village level posts | 30 min | trend-only layer, own tables (D-081) |
| Google Flood Hub | 103 virtual river points: status, thresholds, 9-day discharge | 6 h | collected and validated, not shown (D-087) |

## 3. Quality control (before anything is computed)

`floodwatch/qc.py`, every 10 min over the last 49 h:
- **Dropouts:** a fall and return within 10 cm (`BACK_M`) over ≤ 2 readings (`MAX_DROPOUT_RUN`) of 30-min spacing → flagged
  `dropout`, never deleted (KI-237).
- **Erratic gauges:** ≥ 3 steps of ≥ 30 cm (`STEP_M`, `ERRATIC_STEPS`) in 24 h → level, trend and forecast hidden, the
  gauge stays with a note (pumps at the sensor or a faulty sensor; D-057).
- **Stuck loggers:** one exact value in ≥ 90 % of ≥ 50 readings in 24 h (`STUCK_SHARE`) → hidden with a note (KI-241).
- **Datum suspects** (values not in m MSL) are listed in `config.DATUM_SUSPECT` and never shown or forecast (KI-210).
- **Measured change (`observed24`):** straight-line fit over 24 h (48 h when 24 h shows no clear trend); words follow
  the rounded centimetres (< 2 steady · 2–4 small · 5–19 plain · ≥ 20 strong; "mixed" when the fit is poor and the
  wiggle ≥ 5 cm); plus `change6_cm`, the fitted change over the last 6 h (v0.20.7).

## 4. Status now: the level against the bank

`forecast.classify_status` (HII/RID/EGAT/FOP gauges): over the bank → **ล้นตลิ่ง**; with a ground level known,
≥ 90 % of the bank depth → **ใกล้ตลิ่ง**, 70–90 % → **เฝ้าระวัง**, else **ยังรับน้ำได้**; without a ground level,
< 30 cm below the bank → ใกล้ตลิ่ง. The bank is HII's `min_bank` (KNOWLEDGE §3.2; KI-272 notes 254 gauges whose
left/right bank fields disagree). **BMA canals** use BMA's own drainage levels (D-038): over the bank → ล้นตลิ่ง, over
BMA critical → คลองเต็ม, over BMA warning → คลองเริ่มเต็ม. No data for 24 h → **ไม่ทราบ**; > 3 h → "ข้อมูลเก่า".

## 5. The forecast ladder (one forecaster per gauge, D-080)

Code: `floodwatch/forecast/__init__.py` (`evaluate`, `_backtest_errors`, `forecast_station`, `run_all`), version `star-0.4`
(`STAR_INPUTS = 2`, stamped on every cached backtest; one from older inputs is redone).

| Method | Formula (change over h hours from now, level y₀) | When it can win |
|---|---|---|
| `persistence` | 0 ("no change") | the baseline every method must beat |
| `tide` | η(t₀+h) − η(t₀), harmonic tide fitted by least squares on K1, O1, M2, S2, M4, MS4 | tidal lower reaches |
| `trend` / `tide_trend` | (tide +) s₂₄·h·e^(−h/48), s₂₄ = 24 h slope of the 25 h trailing mean | slow, steady drains and rises |
| `recent` | (tide +) r·h·e^(−h/48), r = smaller of the 24 h and 6 h fitted pace, 0 if they disagree | a rise or fall still going; stops when the last 6 h stop (Kgt.19A, D-080) |
| `star` | ridge regression (λ = 1) per gauge and horizon on: tide change, own 1/3/6/24/72 h change, deviation from the 25 h, 7-day and 30-day trailing means, each upstream gauge's 24/48 h change, C.13 dam release (+24/48 h change), rain forecast over the horizon (day-1 near, day-2 far), the nearest Flood Hub point's forecast discharge change over the horizon (≤ 10 km, non-BMA) | rain, upstream water and dam releases (D-052); the 7/30-day means and 1/3/72 h changes since v0.25.0 (D-092); Flood Hub since v0.26.0 (D-097) |

- **Horizons:** 1, 3, 6, 12, 24, 48, 72 h (rows show 24/48/72 h). **History:** up to 370 days hourly (`LOOKBACK_DAYS`); a
  gauge needs ≥ 7 days (`MIN_HOURS`); `star` needs ≥ 30 days of complete training rows (`STAR_MIN_TRAIN`); since the 30-day mean joined (v0.25.0) that means
  about 90 days of history before a gauge can use `star`.
- **Backtest (rolling origin):** the last 45 days (`EVAL_HOURS`, or the last 40 % of a short record); the tide is fitted
  only on data before the window, `star` trained only on targets ending before it (no leakage). All methods are
  compared on the same rows by RMSE.
- **Gate:** the best method is served only if its skill over persistence `1 − RMSE/RMSE_persistence` is **> 0.10**
  (`SKILL_GATE`); otherwise persistence. Chosen per gauge **and** per horizon.
- **Bands:** the 5/25/50/75/95 % empirical quantiles of the chosen method's backtest errors are added to its live
  prediction (a split-conformal style band); 90 % coverage in the backtest is stored (`coverage90_backtest`). Since v0.26.0
  the 90 % band (5–95 %) is widened by a daily factor per horizon and kind from our own last 5 days of outcomes, never below 1
  (`risks.band90_factors` → `forecast.widen90`, D-098); the printed 50 % range is not changed.
- **Cached backtests** (`forecast_model`) are reused ~20 h or until history grows 20 %; a backtest stored before a new
  ladder method existed is redone (`model_is_fresh`).
- **Upstream gauges** (`forecast/upstream.py`): per gauge, up to 4 (`K`, was 2 until v0.25.0, D-093) gauges in the same basin
  and river system within 250 km (MAX_KM) whose 24 h change leads this gauge's by 1–48 h with correlation ≥ 0.5 over
  ≥ 90 days of hourly pairs (was 180);
  relearned daily. On the Chao Phraya chain, gauges up the river by river km are used.

**What the rows say** (`api.change_summary`): the median change and the 50 % range ("−3 ถึง +11 ซม."); direction
"steady" unless the median moves more than max(2 cm, half the 50 % range); "strong" at ≥ 20 cm; confidence
**ปานกลาง** only when a real model beats persistence by ≥ 30 % and its 90 % band held (≥ 0.85) — there is no "high";
a 50 % range wider than 75 cm prints "ช่วงกว้างเกินไป". A row is shown as a direction only when a real model proved it
and its whole likely range agrees; otherwise "→ ทรงตัว" (range within ±5 cm) or "? ไม่แน่ชัด". The chart draws the same
path (D-080: one forecaster; check C15).

**Results so far:**
- Nationwide backtest (v0.16.6, 51 sample gauges): 27 / 19 / 19 beat persistence at 12 / 24 / 48 h (own history alone
  9 / 8 / 6); `star` serves 48 h at ~35 gauges.
- First pass with `recent` (2026-10-03, 638 gauges retrained): served at 12 h by star 265, persistence 294, recent 72,
  tide methods 6.
- Continuing a measured trend (archived runs 26 Sep – 3 Oct, ~6,000 cases per horizon): 24 h straight line 12.6 / 19.5 /
  32.8 cm mean error at 12/24/48 h; the served model 12.5 / 18.5 / 31.5; the `recent` rule 10.4 / 16.3 / 29.2.

### 5a. Theory and formulas

Notation: y(t) the hourly level (m MSL) at a gauge, t₀ the latest hour, h the horizon in hours, ŷ(t₀+h) the median
forecast, ε the forecast error y − ŷ.

- **Harmonic tide** (`fit_tide`): η(t) = a₀ + Σₖ [aₖ cos(ωₖ t) + bₖ sin(ωₖ t)] for the constituents K1, O1, M2, S2, M4, MS4
  (speeds 15.04, 13.94, 28.98, 30.00, 57.97, 58.98 °/h), least squares on history before the backtest window. Methods add
  the tide *change* η(t₀+h) − η(t₀), never a tide level.
- **Damped trend** (`trend`, `tide_trend`): ŷ = y₀ + Δη + s·h·e^(−h/48), with s = (ȳ(t₀) − ȳ(t₀−24))/24 the slope of the
  25 h trailing mean ȳ. The e^(−h/48) damping says "trends fade": at 24 h a trend is continued at 61 %, at 72 h at 22 %.
- **Recent pace** (`recent`): r = sign(s₂₄)·min(|s₂₄|, |s₆|) when the straight-line slopes over the last 24 h and the
  last 6 h have the same sign, else r = 0; ŷ = y₀ + Δη + r·h·e^(−h/48). A rise that stopped (s₆ ≈ 0) is not continued.
- **Network model** (`star`, "space-time AR + rain"): Δy(t, h) = y(t+h) − y(t) is regressed on
  x(t) = [Δη(t, h), y(t) − y(t−6), y(t) − y(t−24), y(t) − ȳ(t), {u_j(t) − u_j(t−24), u_j(t) − u_j(t−48)} for each
  upstream gauge j, Q(t), Q(t) − Q(t−24), Q(t) − Q(t−48) for the C.13 dam release, R_near(t, h) + R_far(t, h)]
  where R is the forecast rain summed over the horizon (day-1 forecasts for the first 24 h, day-2 beyond, from the
  hindcast archive in training). Ridge regression: β = argmin ‖Xβ − Δy‖² + λ‖β‖², λ = 1, inputs standardised; one model
  per gauge and horizon, trained only on rows before the backtest window.
- **Error bands** (split-conformal style): for the chosen method, the empirical quantiles q₀.₀₅ … q₀.₉₅ of the backtest
  errors ε at that horizon are added to the live median: [ŷ + q₀.₂₅, ŷ + q₀.₇₅] is the 50 % range the rows print,
  [ŷ + q₀.₀₅, ŷ + q₀.₉₅] the 90 % band the chart shades. Between backtested horizons the quantiles are interpolated.
- **Skill**: skill = 1 − RMSE_method / RMSE_persistence on the same backtest rows; served if > 0.10.
- **Bank chance**: over horizons 1…H, if max ŷ ≥ bank → ">50%", else if max (ŷ + q₀.₇₅) ≥ bank → "25–50%", else if
  max (ŷ + q₀.₉₅) ≥ bank → "5–25%", else "<5%".
- **Measured change** (`qc.observed24`): ordinary least squares over the last 24 h (≥ 6 readings spanning ≥ 20 h):
  change = slope × 24 h; R² < 0.5 with a residual wiggle ≥ 5 cm → "ขึ้นลงสลับกัน".
- **Upstream learning**: for candidate gauges u in the same basin within 250 km, the lag L ∈ [1, 48] h maximising the
  correlation of 24 h changes corr(Δ₂₄y(t), Δ₂₄u(t−L)) over ≥ 180 days; keep up to 2 with corr ≥ 0.5 and L > 0.

### 5b. Which models are applied (backtests of 2026-10-04, gauges with a model)

| Horizon | star | recent | tide / tide_trend / trend | persistence (nothing beat it by 10 %) | medium confidence |
|---|---|---|---|---|---|
| 12 h | 408 | 92 | 18 | 457 | 218 |
| 24 h | 311 | 81 | 39 | 563 | 112 |
| 48 h | 332 | 40 | 36 | 557 | 63 |
| 72 h | 372 | 14 | 30 | 549 | 70 |

The rows show 24 / 48 / 72 h (owner 2026-10-04: no 12 h row). The network model carries the long horizons: rain and
upstream water take a day or more to arrive, which a gauge's own history cannot know.

### 5c. Hard cases (real gauges, backtest RMSE in cm, 2026-10-04)

| Gauge | Where | 24 h: served (RMSE vs no change) | 72 h | Why it is hard |
|---|---|---|---|---|
| CPY015 สะพานกรุงเทพ | Chao Phraya, Bangkok | star 12.7 vs 22.3 | star 23.0 vs 55.3 | tide (±1 m) on top of the river flood; the dam release (C.13) and upstream gauges make it one of the best-forecast gauges |
| N.67 | Nan, Nakhon Sawan | star 15.8 vs 34.0 | star 66.9 vs 91.5 | big flood wave from Sirikit and the Nan; upstream gauges ~1 day ahead help at 24 h, less at 72 h |
| C.67 สะพานหัวเวียง | Chao Phraya, Sena (Ayutthaya) | star 11.1 vs 19.3 | star 39.4 vs 54.9 | 2.7 m over its listed bank: the forecast is good, the bank value is in question (KI-272) |
| Kgt.19A บ้านท่าบุญมี | Khlong Tha Bun Mi, Chon Buri | no change 20.6 (star 21.6) | no change 38.2 | jumps of ~70 cm in 6 h then a plateau (gate or local inflow): no input explains them, so no method beats "no change"; it caused the text-vs-chart case (KI-270) |
| STU003 มะนัง | Khlong La-ngu, Satun | star 76.1 vs 85.6 | no change 102.7 | flash floods of 1–1.5 m within hours after heavy rain; daily rain cannot time them — hourly rain is the missing input |
| WL.SSB.08 | Khlong Saen Saep, Bangkok (BMA) | no change 25.1 | star 24.8 vs 28.8 | pumped and gated polder canal; hidden when erratic (KI-237); levels follow pump operations, not hydrology |
| P.1 สะพานนวรัฐ | Ping, Chiang Mai | no change 23.6 (star 21.6) | no change 28.8 | star is better but by less than 10 %, so the gate keeps "no change": the app would rather say "? ไม่แน่ชัด" than claim skill it does not have |
| X.44 บ้านหาดใหญ่ใน | Khlong U-Taphao, Hat Yai | star 20.8 vs 24.9 | no change 28.9 | rain-driven, fast; star helps a day ahead, not three |

### 5d. Improving the forecast honestly (Q52, 2026-10-04)

> Owner: "Continue to improve the model forecasting performance that is our goal, not fake the result and error or
> uncertainty to make it better." Every change below was judged the same way, and kept only if it held.

**Protocol** (`research/q52_harness.py`): the gauge's own methods come from the rolling backtest; a `star` variant is
trained only on hours before the 45-day window; the served method (best + the 10 % gate) is chosen on the window's
**first half** and scored on the **second**; a variant is picked on gauge sample 1 and confirmed on a **disjoint**
sample 2. We report the served error against "no change" (summed and per-gauge mean), how many gauges keep a ≥ 10 % gain
on the unseen half, and how many end up **worse** than "no change" (the cost of serving a model).

| Experiment | Result on the unseen half | Decision |
|---|---|---|
| Where the "?" comes from (`_uncertainty_sources.py`) | 528/520/512 of 961 gauges serve "no change" at 24/48/72 h; the best model gains 5–10 % at ~200 of them (just under the gate), 0–5 % at ~210; `star` is the near-miss at ~280 | aim at `star` |
| Average the methods (`_combine.py`) | −5.9 → −6.8 % at 24 h, −5.4 → −5.6 % at 72 h | not shipped (too small) |
| `star` inputs V1–V5 (`_star_variants.py`, picked on sample 1) | V1 (7/30-day means) best at 24–72 h, V2 (1/3/72 h changes) at 6 h; time of day and recency weights did not help | V12 = V1 + V2 |
| V12 confirmed on sample 2 | served error vs "no change" 24/48/72 h: −6.6/−5.5/−5.3 → **−8.3/−8.5/−9.4 %**; gauges keeping ≥ 10 %: 51/44/49 → **67/70/69**; worse than "no change": 12/15/10 → 12/20/21 | **shipped v0.25.0 (D-092)** |
| Stricter selection (gain on both halves of the choosing period) | removes few failures (72 h: 21 → 17) and loses more gain (−9.4 → −5.5 %) | gate stays 10 % |
| More upstream gauges (K 2→4, history 180→90 days, `_upstream_k.py`) | picked on sample 1 (24 h −8.0 → −9.5 %); confirmed on sample 2: 12/24/48/72 h −14.8/−6.6/−7.5/−6.9 → −15.9/**−9.1**/−8.6/−8.0 %, gauges keeping ≥ 10 % 53/44/43/36 → 55/47/44/38, worse 13/11/12/15 → 13/12/13/14 | **shipped v0.25.0 (D-093)** |
| Google Flood Hub forecasts as an input (`_floodhub_input.py`, 75 river gauges ≤ 10 km from a Flood Hub point) | 12/24 h no gain; 48 h −11.2 → −11.4 % (worse 7 → 4); 72 h −8.3 → −9.2 %. Archive verified "as issued" (320/320 values equal to what we stored live) | **shipped v0.26.0 (D-097)** after the owner's yes |
| WeatherNext 3 rain (`_weathernext_*.py`) | archive ≥ 180 days (April 2026 on); one literal point costs ~12 MB per run, a join of points scans the whole 56 GB partition; the month's free BigQuery quota ran out before the 60-day test | blocked: owner step (billing or 1 Nov), then backtest (D-069, Q44, Q53) |
| Bands by measured trend (`_bands_by_trend.py`) | narrower (90 % band 72 → 64 cm at 24 h) but held less often (78 → 75 %) | **rejected** (narrower but less honest) |
| Shorter error window for bands (`_band_window.py`) | 10/15/30 days widen bands and lower coverage vs 45 days | 45 days stays |
| Rebound forecasts after a steep measured fall (`_rebound_check.py`) | archive: came true 65 % (48 cases, mean error 72 cm); after v0.25.0 four gauges forecast +35…+70 cm while falling; interim 2026-10-05 (8 h): all four kept falling | watching (KI-292); a guard only after the honest test |
| Served bands vs reality, 30 days (`_band_coverage_live.py`) | 50 % band held 51 / 48 / 44 % and 90 % band 88 / 86 / 80 % at 24 / 48 / 72 h; misses mostly **below** the band (water fell more than forecast: 32 / 36 / 42 % below vs 17 / 16 / 14 % above) | owner's yes (Q54) → daily 90 % band factor shipped v0.26.0 (D-098, `_band_calibration*.log`); the 50 % band stays (refitting overshot it) |

**What it means for a visitor.** More gauges carry a real forecast where `star` learned the slow return of a river to its
usual level (V1); the 24 h ranges hold as stated; at 72 h the ranges are too confident in a falling river, so we say so
instead of hiding it.

## 6. Derived signals

- **Bank chance** (`forecast.bank_chance`): the max over horizons of the 50/75/95 % quantiles against the bank →
  ">50%", "25–50%", "5–25%", "<5%". It ranks well but is ~3× too high in the middle (25–50 % came true 12 %), so the app
  shows the **measured record**, never this band as a percent (D-077).
- **Trend group** (`status.trend`, D-083): the 24 h row when sure (proven ↗/↘, or "→ ทรงตัว"), else the measured recent
  pace (`recent` rule; ≥ +2 cm per 24 h = up) → **น้ำยังขึ้น** / **ทรงตัวหรือลดลง**; None when stale. Two labels shown
  ("วัดได้ ↗ · คาด ?"). One field on every station row, read by every view.
- **Lean of an unsure row** (`status.lean`, D-091): a "? ไม่แน่ชัด" row (no proven direction, range wider than ±5 cm)
  takes the measured pace's direction (the trend-group rule) **only when the model median — the chart's dashed line — also
  moves ≥ 3 cm that way**, shown as "↗ น่าจะขึ้น / ↘ น่าจะลดลง" with its 30-day record (83 / 80 / 82 % at 24/48/72 h); the
  numbers stay the model's range. The amount stays uncertain (30–50 cm errors).
- **จับตา groups** (`risks.build`, D-077): over the bank (split by trend group) → may reach the bank (band ≥ "25–50%" in
  24 or 48 h) → water from upstream (learned upstream gauge, lag 3–48 h, fitted 24 h rise ≥ 30 cm, gauge at
  watch/warning) → fast rise (24 h median ≥ +20 cm); heavy rain per province (≥ 35.1 mm in 24 h). A gauge appears once.
- **Track records** (`risks.compute_records`, daily): over 30 days of our own archived forecasts (one run per gauge per
  6 h; readings hourly), how often each forecast-based group came true; shown as "N ใน 10" with ≥ 30 cases. Live
  2026-10-03: may reach the bank 6 in 10 (">50%") and 1 in 10 ("25–50%"), water from upstream 6 in 10, fast rise 7 in 10.
- **Pin check** (`point.assess`): nearest gauges within 8 km weighted by distance and agreement → a category and
  warnings; polder rules only in กทม./ปริมณฑล (D-070); never a level at the pin (D-021).
- **Rivers** (`rivers.py`): km along HII's river line (pieces joined ≤ 1.5 km, gaps bridged ≤ 100 km, mouth = the end
  from which banks rise most consistently); rivers with ≥ 3 gauges get a view; tributaries join by HII sub-basin (D-082).

## 7. Decisions record (what we tried, the result, why)

| Topic | Tried | Result | Decision |
|---|---|---|---|
| Hydraulic engine | Draft `BKKHydroEngine` from research | physically implausible output (VALIDATION_2026-09-26 §C12) | not ported; data-driven ladder instead (KI-302) |
| Model choice | one global model vs per-gauge backtest | per-gauge winners differ by place and horizon | ladder + 45-day backtest + 10 % gate (APPROACH §4) |
| Network model | upstream + rain + dam in a ridge regression (`star`) | wins 48 h at ~35 gauges | served where it wins (D-052) |
| Measured daily rain as input | HII daily rain per catchment | no skill gain | not adopted; hourly archive kept, re-test mid-Dec 2026 (Q43, D-067) |
| Official HII forecast | scored against readings | useful in places, not better than ours overall | cross-check only (D-050) |
| Trend in the rows | override beside the model (D-060) | text and chart disagreed (Kgt.19A, 535 rows) | removed; `recent` method in the ladder (D-080) |
| GloFAS | upper bound with perfect future discharge | 0 of 12 main-river gauges gain ≥ 10 % | rejected (D-069) |
| Satellite radar (GFM, GISTDA) | flooded cells near pins/gauges | blind in cities; GISTDA cells could mislead; layer emptied before rebuilds | removed from the app (D-084); a future source gets its own design |
| WeatherNext 3 | 64-member rain ensemble | subscribed (KI-283); archive ≥ 180 days; a literal point is ~12 MB per run but a joined point list scans 56 GB; free BigQuery quota used up before the 60-day test (2026-10-04) | backtest after the owner's billing step (D-069, Q44, Q53) |
| `star` inputs (Q52) | 7/30-day means, 1/3/72 h changes, time of day, recency weights | V12 (means + changes) −8.3…−9.4 % vs −5.3…−6.6 % on unseen gauges | shipped v0.25.0 (D-092) |
| Averaging methods, stricter selection | forecast combination; gain on both halves | +0.4–0.9 points; stricter loses more than it saves | not shipped |
| Flood Hub as a `star` input | the forecast's relative discharge change | +0.9 points at 72 h, none at 12–24 h (75 gauges) | candidate (Q55) |
| Bands | by measured trend; shorter windows | narrower but less honest; wider and less honest | rejected; 72 h overconfidence → Q54 |

| Google Flood Hub | 103 virtual points | agrees when it flags (2 of 3 SEVERE over our over-bank gauges), misses 7 over-bank places; 31 points beyond our gauges; 9-day horizon | collected and validated before any display (D-087) |
| More stations | ablation: 2 / 1 / 0 upstream gauges | 2 upstream gauges cut error 7.6 / 5.4 / 4.2 % (12/24/48 h); no saturation | try 3–4 (Q47); DWR as inputs after ~30 days (Q46) |
| DWR village posts | quality check | local datum, default 4.00 m alarms, ~11 h history | archive + trend-only layer (D-081) |
| AI plain summary ("✨ ให้ AI สรุป") | free-form LLM vs deterministic rule narrative + background GLM retelling | free-form LLM invented safe/normal verdicts; rule narrative + checked retelling gives 91 % pass and 0 safety errors | deterministic rule story rendered at 0s (<50 ms); GLM polishes tone asynchronously; checked for safety; 🔊 voice readout added (D-068, KI-275) |

## 8. Limits we state

- Gauges measure channels; streets flood from rain the drains cannot take (Bangkok polders, KNOWLEDGE §4).
- Forecast skill is modest: most rows are "low" confidence; 48 h is shown only where tested.
- Track records rest on weeks, not seasons (archive since 2026-09-26).
- Banks come from HII metadata and are not all verified (KI-272, Q48).
- Gates, dams and pumps are operated by people; their plans are not in any feed we reached.

## 9. Data that would make the app more useful and more accurate (ranked)

| # | Data | Why it matters | Expected gain | Who has it |
|---|---|---|---|---|
| 1 | **Verified bank levels** per gauge | a wrong bank makes a false "ล้นตลิ่ง" or hides one | correctness of every status | RID, HII (Q48) |
| 2 | **Dam and gate operation plans** (releases, gate openings for 1–3 days) | the lower Chao Phraya is decided by operations, not rain | large at 24–72 h below dams | RID, EGAT, BMA |
| 3 | **More upstream gauges with history** (RID Telerid 921 stations; 3–4 learned per gauge) | ablation: each upstream gauge adds skill, no saturation at 2 | 5–10 % error at 12–24 h where added | RID (login), our network (Q47) |
| 4 | **Hourly rain history** (gauges or radar) | event-scale rain drives canals and flash floods; daily rain gave no gain | possibly large for fast-reacting gauges | HII (hourly), TMD radar |
| 5 | **Street/house elevation (fine DEM) and drainage** | to say what a channel level means for a street | changes what we can answer (depth risk) | BMA, GISTDA, LDD |
| 6 | **Observed flooded areas with dates** (field reports, validated satellite) | to verify statuses and records against what flooded | trust and calibration | DDPM, a future satellite source |
| 7 | **Tide predictions for the Gulf** (Navy tables) | lower reaches in the high-tide season | small–moderate at 1–12 h | Royal Thai Navy |
| 8 | **Longer-range river outlook** (Flood Hub after validation, 3–9 days) | days of lead time where we stop at 48 h | lead time, not precision | Google Flood Hub (D-087) |

### 9a. Data review for nationwide forecasting (2026-10-04; owner: "which data can we obtain … more data coverage … other variables or sources")

**What we have now** (fresh gauges in the forecast, 2026-10-04): HII 336, RID 291 (290 with discharge), BMA 183, FOP 86,
EGAT 65; DWR village posts 455 (archive since 3 Oct, trend only); rain: Open-Meteo forecasts with day-1/day-2 hindcasts
(0.5° cells nationwide, ~8 km points around Bangkok), HII rain gauges (measured); Google Flood Hub 103 points (status +
daily forecasts, a year of archive available); WeatherNext 3 (research only).

| Candidate | Evidence so far | Next step |
|---|---|---|
| Discharge at RID gauges (290) as upstream inputs | levels are used; discharge is used only at C.13 | test like `_upstream_k.py` with discharge changes |
| More learned upstream gauges | confirmed on sample 2: +1.1–2.5 points at 12–72 h | shipped (D-093) |
| Flood Hub forecasts as inputs | +0.9 points at 72 h, none at 12–24 h | owner choice (Q55) |
| WeatherNext rain | archive ≥ 180 days; cheap query form found | owner billing step, then the 60-day rain test (Q53) |
| DWR posts as upstream inputs (thin provinces) | ~1 day of archive now | after 30–60 days (Q46) |
| Hourly rain (own archive) | daily rain gave nothing | re-test mid-Dec 2026 (Q43) |
| Soil moisture / antecedent rain (e.g. Open-Meteo soil moisture, ERA5-Land) | not tested | candidate variable for rain-fed rivers |
| Reservoir storage % (RID dams) | dam releases beyond C.13 gave no gain (D-090) | as a regional context line, not an input |
| Gulf tide tables (Navy) | our harmonic fit covers lower reaches | small gain expected |
| Gate and pump operations | not in any feed we reached | ask BMA/RID (unchanged) |

### 9b. Reservoir inflow nationwide (owner 2026-10-05: "not only the water level … inflow, reservoir and much more")
Daily inflow for every RID dam (HII) against ERA5 catchment rain (HydroBASINS lev08 upstream basins), fit 2018–2024,
tested 2025–2026, recursive to 7 days with observed rain (an upper bound): the rain + yesterday's-inflow model beats
persistence by ≥ 10 % at 7 days for 16 of 35 dams (the large and northern/western reservoirs), is level for 13, and worse
for 6 (แก่งกระจาน, ทับเสลา, ลำพระเพลิง, บางลาง, ปราณบุรี, ป่าสักชลสิทธิ์). HII's day-of-year average beats persistence at
7 days for the big dams too. Before any outlook is shown: (1) the same test with archived rain *forecasts* (Open-Meteo's
historical-forecast or previous-runs APIs) for the operational skill; (2) a loss term where the balance leaks (−1.8 to
−2.8 ล้าน ลบ.ม./วัน at the biggest reservoirs); (3) the gate per dam, as for gauges (Q58). KI-301, research/2026-10-05_dam_inflow_nationwide.log.

## 10. How to reproduce

- Tests: `docker compose run --rm --no-deps worker pytest -q` (≈ 290 tests).
- Nationwide backtest: `scripts/backtest_nationwide.py`. Track records: `risks.compute_records` (forecaster, daily).
- Evidence scripts: `research/2026-10-03_verify_bank.py`, `_verify_up.py`, `_verify_rise.py`, `_verify_text_graph.py`,
  `_ablate_upstream.py`, `research/2026-10-04_floodhub_validate.py`.
- Live UI consistency: `python3 scripts/ux_consistency.py out.json 6` (checks C1–C20).
- Q52 experiments (honest protocol): `research/q52_harness.py`, `2026-10-04_{combine,star_variants,star_selection,upstream_k,
  floodhub_input,bands_by_trend,band_window,band_coverage_live,uncertainty_sources,weathernext_probe*,weathernext_rain_v2}.py`
  with their `.log` files. Open the database read-only (`db.connect_readonly()`), never redeploy during a run (KI-284), and
  call AI with `account=False` (KI-285).
- Impact pilot (D-099): `research/2026-10-05_impact_anchored_replay.py` (absolute, anchored and gain what-ifs against keeping
  today's level) and `research/2026-10-05_impact_release_vs_b18.py` (does B.18 carry the dam's reported release), with logs;
  the live replay is `impact.replay` inside the hourly `impact` task.

## 11. Impact what-if for a dam release (pilot Kaeng Krachan, `/impact`, D-099)

**Question (ONWR/RID engineers).** If Kaeng Krachan releases X ล้าน ลบ.ม./วัน and เขื่อนเพชร diverts D m³/s, when and how
high does the water get at B.18 (เขาลูกช้าง), B.10 (ตลาดท่ายาง), B.16 (สะพานบ้านลาด), B.15 (ข้างจวนผู้ว่าฯ) and PCH001
(เมืองเพชรบุรี), and does it reach each agency's own bank? 1 ล้าน ลบ.ม./วัน = 11.574 m³/s.

**Model (built, behind the gate).**
- Flow down the river, a steady release held ≥ 1 day: B.18 = R + (B.18 now − release now); B.10 = max(0, B.18 − D) + local,
  local = max(0, B.10 now − max(0, B.18 then − D now)); B.16 = B.10 + (B.16 now − B.10 then). Short pulses arrive lower
  (attenuation not modelled).
- Level: a rating curve h = h₀ + a·Qᵇ per gauge with flow (least squares in log space over a grid of h₀ below the lowest
  level); the city gauges (no flow) against B.16's flow at the learned lag. Range = the 10–90 % residuals; "outside the
  data" when a flow exceeds the highest the year carried (the curve is extrapolated).
- When: the lag of the best correlation of 24 h changes (0–72 h), window ±20 % (at least ±3 h), plus 2–8 h dam → B.18
  (assumed; a year of daily data shows a same-day response).
- Diversion default: the median of B.18 (lag earlier) − B.10 over the last 72 h (63 m³/s on 2026-10-05).

**Ratings fitted on the year (2026-10-05).**
| Gauge | h₀ (m) | a | b | RMSE (cm) | Q seen (m³/s) |
|---|---|---|---|---|---|
| B.18 | 23.13 | 0.061 | 0.78 | 3.4 | 2–143 |
| B.10 | 5.28 | 0.184 | 0.70 | 2.2 | 2–86 |
| B.16 | 1.54 | 0.627 | 0.47 | 1.1 | 5–73 |
| B.15 (B.16's flow) | −0.47 | 0.326 | 0.56 | 28.6 | 5–73 |
| PCH001 (B.16's flow) | −0.83 | 0.371 | 0.57 | 9.8 | 5–73 |

**Validation (replay, honest protocol).** Ratings, lags and the pass-through gain are fitted on the first 60 % of 370 days
and judged every 3 h on the last 40 %, B.18's measured flow standing in for the release. Four predictions at each
point's lag: *keep* today's level; *absolute* (the model above); *anchored* (today's level + rating(q + ΔQ) − rating(q),
ΔQ the B.18 change on its way); *gain* (today's level + g·ΔQ, g fitted). Mean level error, cm, 2026-10-05:
| Gauge | keep | absolute | anchored | gain | n |
|---|---|---|---|---|---|
| B.10 | 12.5 | 39.4 | 24.9 | **12.0** | 951 |
| B.16 | **13.6** | 48.1 | 113.6 | 13.7 | 791 |
| B.15 | **34.1** | 51.7 | 85.2 | 44.8 | 740 |
| PCH001 | **16.7** | 46.9 | 83.6 | 21.6 | 775 |
On big changes (|ΔQ| ≥ 15 m³/s) keep wins too (B.10 25.9 vs gain 28.6). **Gate:** a method must beat keep by ≥ 10 % at
B.10 and B.16 (and on big changes when there are ≥ 30) — not met, so `/whatif` answers 409 and the table stays off. The
replay is rebuilt hourly.

**Why it fails here.** In the year, flow changes at B.18 (≤ 143 m³/s) barely reached the river below เขื่อนเพชร: the
learned pass-through is 1.64 cm (B.10) and 0.26 cm (B.16) per m³/s at B.18, travel-time correlation r 0.29–0.46. Most
likely the diversion dam absorbs them (~63 m³/s to the canals; ⚠️ unverified), so the levels follow the diversion, local
rain and the tide in the city. The steep ratings (B.10 ≈ 4–5 cm per m³/s) turn small flow errors into large level
errors. A flood-size release must pass the diversion dam, but the only one since 2018 (24.36 ล้าน ลบ.ม./วัน on
21 Aug 2018) has no public river record.

**Dam context (shown, not modelled).** RID's daily record against HII's rule curve (5 Oct: storage 725.9, upper curve
593.4, lower 203.8 ล้าน ลบ.ม.) and against its own history (2019–2025 never released more than 9.13 ล้าน ลบ.ม./วัน; the
release since 2 Oct is the largest since 2018). B.18 carries RID's release: a year of daily data, r 0.93, +12.6 m³/s
median, same-day response (EGAT's record does not match, KI-295).

**What would make it credible (asked on the page, Q56):** เขื่อนเพชร gate settings and canal flows; RID's hourly river
records for Aug–Sep 2018; hourly releases and the rule curve in use; release plans; surveyed banks and channel capacity.

**National dams at risk (D-100).** For each of HII's 50 daily dam records (39 physical dams): the storage on the reported
date against HII's upper and lower rule curve for that day of the year (looked up by MM-DD) → *above* / *between* /
*below* (a fact from the agencies' own curve, never turned into a warning); the "largest release since …" note uses the
same rule as the case (complete years only, a gap suppresses it). Records of one dam (RID, EGAT) stay side by side,
never merged (KI-217); the dam's colour comes from its first record with a position. Sorted above, below, between,
unknown, then by storage %. 2026-10-05: 13 above (ป่าสักชลสิทธิ์ 109.8 %, 957 vs upper curve 465 ล้าน ลบ.ม., releasing
43.2 ล้าน ลบ.ม./วัน ≈ 500 m³/s; หนองปลาไหล 105.0 %; แก่งกระจาน 102.2 %), 23 between, 3 without a curve (KI-299).

### 11b. 7-day release scenarios (D-101, `scenarios.py`)
**Reservoir.** Daily water balance S(d) = S(d−1) + I − R(d), inflow I held at today's value; the band = persistence's own
10–90 % change after h days (all days: ±0.8 at 1 d → −1.3/+1.9 at 7 d; days with inflow ≥ 10: −7/+6 → −16/+5 ล้าน
ลบ.ม./วัน). HII's inflow closes the balance (median gap −0.15). A rain-driven model lost to persistence (KI-301).
**River.** `impact.whatif` per day; each gauge sees the release of day d − round(lag/24) (B.18 same day, B.10 one day,
B.16/B.15/PCH001 two days); local inflow and the diversion held at today's. Unvalidated downstream (D-099) — labelled.
**Plans.** Hold; constants 0..cap step 0.5; ramps r0→r1 and front-loaded (k = 2, 3, 4 days at r1 then r2) on a 2.0 grid;
cap = the highest daily release in HII's record (24.36). 2026-10-05: 676 plans, 0.3 s.
**Effects.** city margin min (B.15, PCH001); worst margin min; overtopping sum (m·point·day); storage peak and days above
normal (710); first day under the upper curve; day-7 storage (and vs the lower curve); largest day-to-day change of
release including the step from today.
**Constraints.** margin_i(d) ≥ MAE_i (the replay's mean error of the mass-balance method at gauge i: B.10 0.39, B.16
0.48, B.15 0.52, PCH001 0.47 m); S(d) ≤ maximum storage (900); when today's storage is above the upper curve, S(7) ≤
S(0) (below the lower curve: S(7) ≥ S(0)).
**★ rule.** Among feasible plans: the earliest day under the upper curve, then the lowest S(7), then the gentlest change.
None feasible → say so; show the lowering plan with the least overtopping. 2026-10-05 19:00 UTC: 108 feasible, ★ = 17.0
constant (S(7) 679, worst margin 0.55 m, step 6.2); "hold" best for the city and warning time; 10.5 best for the worst
point, total and water kept (the smallest release that still lowers the reservoir).

