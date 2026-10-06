# MODELS.md — How BKK FloodWatch calculates, forecasts and decides

> Owner, 2026-10-04: "We would like to understand how we can calculate, how to setup the model, which parameters are
> applied. What have we tried already, good or bad results, and why we go this way … like Architecture Decision Report.
> What kind of data do we need more in the future." This document answers that for developers, reviewers and agencies.
> It describes **v0.33.0** (code in `src/floodwatch/`). **§12 shows how the models improved release by release** — what each change
> gained when it was tested, and what each model generation actually delivered, scored against what the water did. §5d records the honest-improvement work of 2026-10-04 (Q52), §5e–5i the experiments of 2026-10-05, §9b–9d the reservoirs and the national dams list, §11c the river below the dam for 7-day release plans. Numbers come from running code or the cited research files;
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

**เขื่อน (แท็บ 💧 ผลกระทบ สำหรับเจ้าหน้าที่)** — 38 เขื่อนใหญ่ จัดกลุ่มตามเส้นควบคุม (rule curve) ของ สสน. · % = ปริมาตร ÷ ปริมาตรที่ระดับเก็บกักปกติ
ของหน่วยงานนั้น (นิยามเดียวทั้งรายการ — ชป. รายงานแบบนี้; % ที่ กฟผ. รายงานเป็น 0 หรือนิยามต่างกัน จึงไม่ใช้) · แนวโน้ม 7 วัน: 32 เขื่อนใช้แบบจำลองฝน
ที่ผ่านการทดสอบกับ *ฝนคาดการณ์จริง* (เฉพาะช่วงวันที่ผ่านเกณฑ์) — แบบจำลองเดิมป้อนด้วยค่าเฉลี่ยฝนคาดการณ์ 4 แบบ และวันที่ 3–7 ที่เคยคงค่าวันนี้
ใช้แบบจำลองคงค่าแบบหน่วง + ฝน ECMWF ซึ่งเลือกจากฤดูฝน 2568 ทั้งฤดู และดีกว่าเดิมทุกช่วงวันในปี 2569 โดยไม่มีเขื่อนใดแย่ลง (§9d) ที่เหลือแสดง "ถ้าไหลเข้าและระบายเท่าวันนี้" (*) พร้อมช่วงจากข้อมูลของเขื่อนเอง ·
ค่า 0 ที่แปลว่า "ไม่ได้รายงาน" ไม่แสดงเป็น 0 และไม่ใช้เป็นจุดเริ่มคาดการณ์ · กฟผ. กับ ชป. แยกกันเสมอ (§9c)

**แผนระบาย 7 วัน (แก่งกระจาน)** — ระดับท้ายน้ำแต่ละวันของแต่ละแผน: ใต้เขื่อน (B.18) ตาม rating curve เทียบระดับวันนี้ จุดอื่น =
ระดับวันนี้ + การตอบสนองต่อการระบายที่เรียนรู้ (ไม่ติดลบ) · ทดสอบย้อนหลัง 7 วันแล้ว คลาดเคลื่อน ~10 ซม. วันแรก ถึง ~40 ซม. วันที่ 7 และแผนต้องห่างตลิ่ง
มากกว่าค่านั้นทุกวัน (เดิมใช้สูตรที่คลาดเคลื่อน ~1 ม.) · ลองฝนในพื้นที่ท้ายเขื่อน ความชื้น น้ำขึ้นน้ำลง และแบบจำลองหลายแบบแล้ว ไม่ช่วย จึงไม่ใช้ (§11c)

**แผนที่น้ำท่วมของแต่ละแผนระบาย** — แสดงแม่น้ำเป็นช่วงตามสถานีที่ใกล้ที่สุด สีตามระยะห่างตลิ่งของวันที่เลือก (ไม่ใช่พื้นที่น้ำท่วม) และชั้นข้อมูลของ สทนช.
(พื้นที่เตือน คาดการณ์ +1…+3 วัน น้ำท่วมที่พบ) · ภาพดาวเทียม (GFM, GISTDA) ตรวจแล้วไม่น่าเชื่อถือพอบริเวณนี้ (มองไม่เห็น 39–58 % ของพื้นที่ ไม่สอดคล้องกันระหว่างรอบ)
จึงไม่แสดง · แผนที่จาก DEM 30 ม. เป็นการทดลอง ยังให้คะแนนไม่ได้เพราะ 3 ปีที่ผ่านมาแม่น้ำไม่เคยล้นตลิ่งที่สถานีใดเลย (§11d)

**ปรับปรุงแบบจำลอง (4 ต.ค. 2569, ทดสอบแบบไม่โกง: เลือกวิธีจากครึ่งแรก วัดผลครึ่งหลัง ยืนยันกับสถานีอีกชุดที่ไม่เคยเห็น)** —
แบบจำลอง star อ่านค่าเพิ่ม: ระดับน้ำเทียบค่าเฉลี่ย 7 และ 30 วัน และการเปลี่ยนแปลง 1/3/72 ชม. ความคลาดเคลื่อนลดลงจาก "ถือว่าคงที่"
−5.3…−6.6 % เป็น −8.3…−9.4 % ที่ 24–72 ชม. (สถานีชุดที่สอง) · สิ่งที่ลองแล้วได้น้อยหรือไม่ได้: เฉลี่ยหลายวิธี (+0.4–0.9 จุด),
ช่วงคาดการณ์ตามแนวโน้ม (แคบลงแต่พลาดบ่อยขึ้น = ไม่ซื่อตรง จึงไม่ใช้), ใช้ Google Flood Hub เป็นข้อมูลเข้า (+0.9 จุดที่ 72 ชม. เท่านั้น)
· ตรวจย้อนหลัง 30 วัน: ช่วงที่แอปบอกที่ 24 ชม. ถูกตามที่บอก (50 % ถูก 51 %) แต่ที่ 72 ชม. มั่นใจเกินไป (ถูก 44 %) และมักพลาดด้านต่ำ (น้ำลดมากกว่าที่คาด)

**แบบจำลองดีขึ้นแค่ไหนในแต่ละรุ่น (§12)** — ตรวจ 2 แบบ: ผลทดสอบตอนปล่อยรุ่น (เลือกจากช่วงหนึ่ง วัดผลกับข้อมูลที่ไม่เคยเห็น)
และผลจริงของการคาดการณ์ที่แอปออกไปแล้ว เทียบกับระดับน้ำที่เกิดจริง 91,429 รอบ ตั้งแต่ 26 ก.ย. 2569 ·
**ดีขึ้น:** จาก ~300 สถานีรอบ กทม. (v0.1) เป็น ~1,000 สถานีทั่วประเทศ (v0.16) · การคาดการณ์ 24 ชม. ที่ใช้แบบจำลองจริง
(ไม่ใช่ "ถือว่าน้ำคงที่") เพิ่มจาก 38 % เป็น 56 % · คาด 6–12 ชม. แม่นกว่า "ถือว่าน้ำคงที่" 11–21 % ทุกรุ่นตั้งแต่มี star ·
ตอนปล่อย v0.25 ความคลาดเคลื่อน 24–72 ชม. ลดจาก −5.3…−6.6 % เป็น −8.3…−9.4 % (สถานีชุดที่ไม่เคยเห็น) ·
**ยังไม่ดีขึ้น:** ผลจริงที่ 24 ชม. แม่นกว่า "ถือว่าน้ำคงที่" เพียง 2–7 % และที่ 48–72 ชม. แทบไม่ต่าง · ช่วง 90 % ถูกจริง 80–89 %
(รุ่นล่าสุด 81–83 %) น้อยกว่าที่บอก · สถานีชุดแรก 266 แห่ง (ส่วนใหญ่ใน กทม.) รุ่นล่าสุดยังพอ ๆ กับ "ถือว่าน้ำคงที่" ใน 1.5 วันที่วัดได้ ต้องตรวจต่อ ·
**แผนระบาย 7 วัน:** น้ำไหลเข้าเขื่อนแม่นกว่า "ถือว่าคงที่" 24–32 % ที่วันที่ 3–7 (ฤดูฝน 2569) · 32 เขื่อนมีแบบจำลองที่ผ่านการทดสอบ (เดิม 16) ·
ระดับท้ายน้ำคลาดเคลื่อน ~10 ซม. วันแรก ถึง ~40 ซม. วันที่ 7 (สูตรเดิมคลาด ~1 ม.)

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
on the unseen half, and how many end up **worse** than "no change" (the cost of serving a model). Since 2026-10-06 (D-107)
a gauge counts as worse only **beyond chance** — its error rises by more than 3 % and a moving-block bootstrap (blocks of the
horizon) puts the rise above zero at 95 % one-sided (`floodwatch.model_gate.made_worse`); the harness prints both counts.

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
| Reservoir outlook (Q58, D-102) | a rain model per dam fed with archived rain *forecasts*, bias per lead, monthly loss term | beats persistence by ≥ 10 %: 15 of 17 dams at 3 d, 11 of 17 at 7 d; the loss term helps 13 of 17 | served per dam and per horizon where it passed; persistence elsewhere (§9b) |
| 7-day inflow (E-7D-IN, D-104) | 31 candidates × six rain sources on 35 RID dams; four ways to choose | per-dam picking overfits (+38 % in sample 2); single families add 1–3 dams worse; the served model fed the 4-model rain mean is better at every lead in both samples, none worse | the 4-model rain mean for the served model (§9d); horizon 7 days |
| 7-day river below the dam (E-7D-DOWN, D-104) | 15 candidates incl. rain, wetness, tide phase, analogs | the absolute chain ~1 m off; anchored at B.18 and a non-negative gain elsewhere beat keep by 5–15 % at days 3–7; rain terms ≈ 0 | served with a margin per point and day (§11c) |
| Dams without a tested model (D-103) | a projection "if today's inflow and release hold" with the dam's own band | no skill claimed; marked * and "ถ้าเท่าวันนี้" | shown; 36 of 38 dams have a 7-day trend (§9c) |
| EGAT's daily % (D-103, KI-305) | as the dams list's badge | 0 for 11 of 15 dams; the other four −44 … +26 points from storage ÷ normal | not used; storage ÷ the agency's own normal storage for every record (§9c) |
| Night of 2026-10-05 (two-sample gate) | dam release input (E-DAM), damping (E-DAMP), upstream flow (E-UQ), two years of history (E-2Y), discharge forecasts (E-Q) | E-DAM no gain; E-DAMP, E-UQ and E-2Y fail the gate; E-Q passes both samples | E-Q is a new parameter (where to show it is the owner's call); the others not shipped (§5e–5i) |
| 7-day inflow on a whole wet season (E-7D-IN-LONG, D-106) | the same candidates chosen on the 2025 wet season, scored on 2026 | only 'served + KF_ec on days 3–7 where persistence was served' passes, with no lead or dam worse | shipped: 32 dams on tested models (§9d) |
| A flood view per release plan (D-105) | river reaches by nearest gauge; ONWR's layers; satellite past floods; a DEM (HAND) flood area | reaches and ONWR's layers built; GFM blind on 39–58 % and inconsistent, GISTDA/GFM agree 73 %/13 %; DEM unscorable (no observed release flood) | reaches + ONWR shown; satellites and DEM not shown (§11d) |
| River on three wet seasons (2026-10-06) | the gain method and rain terms with two more wet seasons | gain beats the hybrid in both month samples, loses the live Jul–Sep 2026 window at days 5–7 | served model unchanged; history kept for the next season (§11c) |
| "Made worse" (D-107) | counting every unit whose error rose at all | one noisy dam could veto a change for all 35 (E-7D-IN-LONG logs gave counts, no sizes) | worse = rise > 3 % and a block-bootstrap lower bound > 0; sizes reported |
| Planning-model test (D-107) | the public 72 h gate (10 % skill, categories beyond 3 days, walk-forward only) for the 7-day tab | the river model beats "keep today" by 4–7 % at days 1–3 yet is the only what-if answer; margins needed month-by-month scoring | own test: two samples + the newest season, never worse than keep, physical sign, per-day margins (GUIDELINES §4.5) |
| Research quota (D-108) | hand-paced Open-Meteo research under a written ≲ 1,000 a day | ≈ 4,800 weighted calls on 2026-10-06; live feeds unharmed (errors 503, never 429) | a shared counter in code: 3,000 a day, 1,000 an hour, 10 s apart |
| As-issued record (E-HIST, §12) | every stored forecast run scored per model generation | see §12a | re-run as the record grows; backtest gains must show up as issued |
| AI plain summary ("✨ ให้ AI สรุป") | free-form LLM vs deterministic rule narrative + background GLM retelling | free-form LLM invented safe/normal verdicts; rule narrative + checked retelling gives 91 % pass and 0 safety errors | deterministic rule story rendered at 0s (<50 ms); GLM polishes tone asynchronously; checked for safety; 🔊 voice readout added (D-068, KI-275) |

## 8. Limits we state

- Gauges measure channels; streets flood from rain the drains cannot take (Bangkok polders, KNOWLEDGE §4).
- Forecast skill is modest: most rows are "low" confidence; 48 h is shown only where tested.
- Track records rest on weeks, not seasons (archive since 2026-09-26).
- As issued, gains beyond 24 h are about zero, and the ranges hold less often than they say (90 % ranges 80–89 %; §12b, KI-287).
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

### 5e. Experiment E-DAM (2026-10-05): a dam's daily release as a `star` input — no gain
106 gauges lie on a main river within 150 km below a RID dam with a release history (dams placed on HII's river lines with
`rivers.chainage`: ภูมิพล → 13 gauges on the Ping, วชิราลงกรณ 11, สิริกิติ์ 10, แก่งกระจาน 10, ป่าสักฯ 9 …). Input: the
previous Thai day's release (what is known that morning) as log changes over 1 and 3 days and against the 30-day mean.
Honest protocol (q52_harness), 104 gauges scored: error vs "no change" 12 h −18.5 → −17.2 %, 24 h −4.5 → −3.7 %, 48 h
−3.0 → −3.4 %, 72 h −3.7 → −3.5 %; within 60 km the same picture. Verdict: not adopted — a daily release known a day
late adds nothing the gauge's own and upstream levels do not carry. Hourly releases (ONWR item 1) would be the real test.
research/2026-10-05_dam_release_input.log. (The first run served the variant at 0 gauges: the time axis had been read as
seconds instead of hours and every feature was NaN — a never-served variant is a bug signal, GUIDELINES §6c-8.)

### 5f. Experiment E-DAMP (2026-10-05): damping `star` against a steep opposing 24 h trend — rejected
KI-292's case (SKG007: +0.55 m forecast after a steep fall, −0.30 m measured) asked whether `star` should be shrunk when
the measured 24 h trend (≥ 10 cm) opposes its forecast. Three variants (half, fade to zero over 0.5 m of trend, zero),
honest protocol on two disjoint samples (116 and 118 gauges): all worse at every horizon on both samples — 12 h −19.3 →
−18.5 / −17.1 / −14.0 %, 24 h −10.7 → −10.3 / −9.2 / −8.8 %, 48 h −10.6 → −9.2 / −7.4 / −6.9 %, 72 h −8.6 → −7.9 / −5.2 /
−4.4 % (sample 1; sample 2 alike), with 1–3 fewer gauges made worse. Verdict: rebounds are usually right; the 90 % band
covers the wrong ones. Not adopted. research/2026-10-05_star_damping.log.

### 5g. Experiment E-UQ (2026-10-05): upstream *flow* change as a `star` input — rejected
For gauges whose learned upstream gauges measure discharge (49 and 68 in two samples of 200): log-flow changes over 24
and 48 h next to the upstream level changes. Sample 1: 12 h −24.9 → −23.1 %, 24 h −12.5 → −14.7 %, 48 h −10.1 → −9.3 %,
72 h −10.8 → −9.3 %; sample 2 worse at every horizon (24 h −18.1 → −15.8 %, 72 h −12.7 → −8.1 %). Fails the two-sample
gate (owner 2026-10-05). The level already carries the routing signal. research/2026-10-05_upstream_flow_input.log.

### 5h. Experiment E-Q (2026-10-05): discharge forecasts for RID gauges — a new parameter that beats persistence
The same ladder on log(1 + Q) for RID gauges with discharge (two disjoint samples, 97 and 94 gauges; production inputs):
served error vs "no change" 12 h −11.3 / −13.1 %, 24 h −7.8 / −5.4 %, 48 h −7.1 / −7.2 %, 72 h −7.8 / −7.4 %; about half
the gauges get a model (persistence's own 24 h error is ≈ 35 % of the flow). Consistent on both samples at every horizon
→ a flow forecast is credible as a product parameter; where to show it is the owner's call (impact tab, RID sheets).
research/2026-10-05_discharge_forecast.log.

### 5i. Experiment E-2Y (2026-10-05): two years of training history for `star` — rejected (72 h hint)
HII serves a second year per gauge (2024-09 … 2025-10) for ~80 % of sampled gauges; same inputs in both arms (upstream
levels for two years, ERA5 hourly rain, no Flood Hub), the training rows cut to the last 400 days in the baseline arm.
Two disjoint samples of 46 gauges: 24 h −9.0 → −8.3 % and −18.3 → −17.9 %, 48 h −8.5 → −7.6 % and −16.5 → −15.2 %
(worse on both), 72 h −8.5 → −8.8 % and −10.4 → −13.4 % (better on both, 21 → 28 gauges served in sample 2) with more
gauges made worse. Fails the two-sample gate. **The 72 h-only variant (2026-10-06)** is answered by the same log —
it equals the two-year arm at 72 h: sample 1 −8.8 vs −8.5 % (3 vs 4 gauges worse), sample 2 −13.4 vs −10.4 % (**4 vs 2**
worse) → fails on gauges made worse; not shipped. research/2026-10-05_two_years_history.log.

### 9b. Reservoir inflow nationwide (owner 2026-10-05: "not only the water level … inflow, reservoir and much more")
Daily inflow for every RID dam (HII) against ERA5 catchment rain (HydroBASINS lev08 upstream basins), fit 2018–2024,
tested 2025–2026, recursive to 7 days with observed rain (an upper bound): the rain + yesterday's-inflow model beats
persistence by ≥ 10 % at 7 days for 16 of 35 dams (the large and northern/western reservoirs), is level for 13, and worse
for 6 (แก่งกระจาน, ทับเสลา, ลำพระเพลิง, บางลาง, ปราณบุรี, ป่าสักชลสิทธิ์). HII's day-of-year average beats persistence at
7 days for the big dams too. **Operational test (research/2026-10-05_q58_operational.log):** Open-Meteo's previous-runs archive gives 92 days of
lead-1…7 rain forecasts (2026-07-06…10-06); leads 3–7 run 35–50 % too wet, so a multiplicative bias per lead is learned on
the first half and the second half is scored (43 days with inflow, 17 Aug–28 Sep 2026). With *forecast* rain the model beats persistence by ≥ 10 % at 3 days for
15 of 17 dams and at 7 days for 11; it fails at 3 days for แก่งกระจาน and แม่กวงอุดมธารา and at 7 days for ภูมิพล, กิ่วคอหมา,
แม่กวงฯ, อุบลรัตน์. The monthly loss term (balance residual) improves the 7-day storage outlook for 13 of 17 dams. Built as
the dams-list outlook (D-102): the model only at the horizons where it passed, persistence with its band elsewhere.
Window: 43 wet-season days — re-test as the archive grows. The dams list and the dams without a tested model: §9c. KI-301, research/2026-10-05_dam_inflow_nationwide.log.

### 9c. The national dams list (D-102, D-103): one % definition, reporting zeros, twin records, the 7-day trend
Evidence: HII `analyst/dam` daily records in our database, checked 2026-10-05 ~21:30 UTC; code `impact.clean_record`,
`impact.twin_names`, `impact.dams_layer`, `reservoir.persistence_model`, `reservoir.outlook`.

**The badge's %.** `pct_normal` = storage ÷ the agency's own normal storage, for every record. RID reports exactly this
(reported − computed −0.12 … +0.16 points over 35 dams). EGAT's reported % is 0 for 11 of its 15 dams (10 with water in
them, e.g. ห้วยกุ่ม 18.31 of 20.23 ล้าน ลบ.ม.; ปากมูล reports 0 for everything) and differs by −44 … +26 points for the
other four (แก่งกระจาน 58.64 vs 102.3, อุบลรัตน์ 81.26 vs 55.0, วชิราลงกรณ 84.59 vs 99.0, รัชชประภา 77.76 vs 74.2), so the
list does not use it; the Kaeng Krachan case still shows it as reported, with the question to both agencies (KI-295).
One definition ranks each group (highest first; records without data last).

**Zeros that mean "not reported" (KI-305).** Storage 0 → missing; storage, inflow and release all 0 → "ไม่มีข้อมูล" and no
outlook; a reported 0 % with water in the dam → missing. A persistence band needs an inflow history that is not all zeros.

**Twin records.** An EGAT dam within 2 km of an RID dam whose normal storage agrees within 1 % is the same reservoir:
all 11 such pairs lie 0.0–1.2 km apart with normal storages equal to within 0.01 %. It is listed under the RID name
with both records apart (KI-217). Only แม่งัด ↔ แม่งัดสมบูรณ์ชล needed this (the other pairs share a name): 39 → 38 dams.

**The 7-day trend.** Storage path S(t+h) = S(t) + Σ(k=1..h) [I(k) − R(today)] − L(month) (the loss term only for modelled
dams); the release is held at today's value (the pilot dam's scenarios, §11b, vary it).

| Dams | Inflow I(k) | Band | Shown as |
|---|---|---|---|
| 16 RID dams with a rain model (§9b, §9d) | the model at the horizons where it beat persistence by ≥ 10 % with forecast rain — fed with the mean of four forecast models since v0.32 — today's inflow at the others | the tested error per horizon (model or persistence) | "อีก 7 วัน ↘ 93 %" |
| others with ≥ 200 days of daily inflow, not all zero | today's inflow (persistence) | 10–90 % of the dam's own inflow change after h days | "… %*", sheet "ถ้าเท่าวันนี้" |

Coverage 2026-10-05: 36 of 38 dams (ปากมูล: no data; แม่มอก: one day of inflow history, back-filled hourly). The row's
arrow compares the two percentages shown, rounded as displayed (36 rows checked in a browser: none disagree).
Tests: `test_one_percent_definition_ranks_the_list_and_egat_zeros_are_missing_not_empty`,
`test_an_egat_dam_at_an_rid_dam_with_the_same_normal_storage_is_one_dam_under_the_rid_name`,
`test_no_outlook_from_a_record_of_zeros`, `test_dams_without_a_tested_model_get_a_persistence_outlook_from_their_own_inflow`,
`test_a_persistence_outlook_needs_no_rain_and_says_it_is_a_projection`.

### 9d. Reservoir inflow 1–7 days: 31 candidates, one change kept (E-7D-IN, D-104)
Owner 2026-10-05: "Try validating many possibilities, models, theories, inputs, parameters for 7-day forecast … If the
other rain model is not better, you can limit to 6 days". Every candidate sees only what is known at issue day t: inflow up
to t, past rain = ERA5 to t−5 and the forecast system's own lead-0 rain after (ERA5 arrives ~5 days late), rain for
t+1…t+7 = the archived forecasts (Open-Meteo previous runs) at their real lead, scaled per model and lead to ERA5's total
on the first half of the window. 35 RID dams, issue days in the 92-day archive (first half chooses, second half scores,
43 days), two disjoint samples (alternate dams). research/2026-10-05_e7d_inflow*.{py,log}.

**Candidates** (×6 rain sources: best_match, ECMWF IFS 0.25°, GFS, ICON — leads ≤ 6 — and the 3- and 4-model means):
persistence · climatology (day of year) · damped persistence (to the 30-day mean; to climatology) · direct ridge per
horizon (inflow, rain past 1/3/7 days, 30-day wetness, forecast rain 1…h and h−1…h, forecast × wetness, season) · the same in
log space · damped persistence + rain · the Q58 recursive model · analogs (20 nearest days, change after h) · an HBV-style
soil bucket with linear-reservoir routing (calibrated per dam, its state corrected at t) · blends.

**Choosing** (error vs persistence on the scored half, sample 1 | sample 2, dams made worse in brackets):

| | 3 d | 7 d | verdict |
|---|---|---|---|
| served now (Q58 model where it passed, best_match rain) | −23.5 (0) \| −18.1 (0) | −17.2 (0) \| −20.5 (0) | baseline |
| per dam, best of all on the first half | −31.2 (0) \| **+37.5** (5) | −24.2 (0) \| −20.4 (3) | overfits — fail |
| one candidate per horizon picked on the other sample | −24.9 (3) \| −18.7 (2) | −12.5 (3) \| −14.1 (4) | fail (+16.6 % at 4 d) |
| served + a family where persistence is served (best: direct ridge, 3-model rain) | −24.4 (0) \| −19.9 (2) | −23.2 (0) \| −20.2 (1) | dams worse — fail |
| **served model, rain = mean of four models** | **−28.0 (0) \| −22.4 (0)** | **−18.5 (0) \| −23.4 (0)** | **passes** |

The 4-model rain mean is better at every lead 1–7 in both samples (e.g. 2 d −25.4/−18.0 vs −21.3/−12.1 %) and makes no dam
worse; ICON's archive stops at lead 6, so day 7 is the mean of the other three — the horizon stays 7 days. Built for the
16 dams with a served horizon (research/2026-10-05_e7d_inflow_build.log; `src/floodwatch/data/reservoir_inflow7.json`):
the same model form refitted on 2018–2024, the served horizons unchanged, per-model and per-lead rain scales, bands from
the scored half as quantiles of (observed − predicted), and the monthly loss term. Kaeng Krachan stays on persistence for
days 1–3 (its served choice) and runs the model on days 4–7: day-7 MAE 5.58 vs 6.19 (best_match rain) and 8.37
(persistence) ล้าน ลบ.ม./วัน; the direct ridge would roughly halve its 3–7-day error (3.9 vs 5.6 at 3 d) but only a per-dam
pick chooses it, and that rule fails across dams — not shipped (re-test when the archive holds a season more).
**Bands (KI-309):** the Q58 build stored quantiles of (predicted − observed) and the outlook added them as (observed −
predicted) — Bhumibol's 7-day band showed the range below the line where the misses lay above it; the Q58 bands are now
read the right way round and every new band is stored as (observed − predicted). Production (`reservoir.run`, every 6 h):
`rain_inputs7` (ERA5 + one multi-model forecast call per catchment point), `compose_rain`, `inflow_path7`, `outlook7`;
the KK release plans take the dam's path when it is for the same day and a model is used (`scenarios.compare(inflow_path=…)`).
Live 2026-10-05 22:38 UTC: 16 dams on the 4-model rain; KK inflow 10.3 → 7.9 (6.4–20.8) ล้าน ลบ.ม./วัน on day 7.

**A whole wet season to choose on (E-7D-IN-LONG, 2026-10-06; D-106).** The archived forecasts reach back to 2024 at every
lead, so the choice moved from 42 days to the 2025 wet season (~200 issue days per dam; rain scales learned there) and
the score to the unseen 2026 window (research/2026-10-06_e7d_inflow_long*.{py,log}). Error vs persistence on 2026,
sample 1 | sample 2 (dams worse than persistence):

| | 1 d | 3 d | 5 d | 7 d |
|---|---|---|---|---|
| served model form | −15.0 (0) \| −10.5 (1) | −23.4 (0) \| −20.3 (0) | −22.3 (0) \| −28.1 (0) | −18.8 (1) \| −25.6 (0) |
| per dam, best of all on 2025 | −15.0 \| −9.7 | −29.8 (0) \| −17.8 (2) | −33.6 (3) \| −28.0 (3) | −27.8 (2) \| −24.6 (4) |
| one blend for all (picked on the other sample) | −14.5 \| −14.4 | −28.0 (0) \| −23.3 (**1**) | −33.9 \| −24.7 | — |
| **served + KF_ec where persistence is served, days 3–7** | as served | **−24.8 (0) \| −23.8 (0)** | **−32.0 (0) \| −31.0 (0)** | **−27.0 (1) \| −28.2 (0)** |

Every new family or per-dam choice lowered the summed error but left one or more dams worse than persistence in a sample
(the owner's rule says no); damped persistence + ECMWF forecast rain (KF_ec) where persistence was served passes at days 3
and 7 in both samples and, kept to days 3–7, makes no lead worse and no extra dam worse at any lead (at day 2 it left four
more dams worse in sample 2, so days 1–2 stay as served). 85 dam-horizons on 20 dams; the file now holds 32 dams (16 new,
e.g. แม่มอก, which had no outlook). Kaeng Krachan: KF_ec on day 3 (2026: 3.72 vs 4.57 for persistence), its served model on
days 4–7 — its direct ridge still wins only under per-dam picking, which fails across dams. Live 2026-10-06: 37 of 38 dams
with a trend, 32 of them modelled (5 still "if today holds"; ปากมูล has no data).

## 10. How to reproduce

- Tests: `docker compose build worker`, then `docker compose run --rm --no-deps -v "$PWD/research:/app/research:ro" worker pytest -q`
  (460 tests on 2026-10-06; the research mount lets the guard on Open-Meteo research run).
- Model history (§12): `research/2026-10-06_model_history.py` scores every stored forecast run (`forecast_run`, 14 days) per
  model generation against what happened, read-only; its `.log` holds the tables.
- Judging a change: `floodwatch.model_gate.made_worse` (D-107). Research that calls Open-Meteo goes through
  `floodwatch.research_quota.get_json` with `-v "$PWD/data/research:/data/research"` (3,000 weighted calls a day, D-108).
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
- Reservoirs (D-101, D-102): `research/2026-10-05_kk_inflow_model.py` (Kaeng Krachan: rain model vs persistence, bands,
  water balance), `2026-10-05_dam_inflow_nationwide.py` (35 RID dams, observed rain), `2026-10-05_q58_operational.py`
  (17 dams, archived rain *forecasts*, loss term; writes the BUILD_JSON behind `src/floodwatch/data/reservoir_models.json`).
- Q52 night of 2026-10-05 (two-sample gate): `2026-10-05_dam_release_input.py` (E-DAM), `2026-10-05_star_damping.py`
  (E-DAMP), `2026-10-05_discharge_forecast.py` (E-Q), `2026-10-05_upstream_flow_input.py` (E-UQ),
  `2026-10-05_two_years_history.py` (E-2Y), each with its `.log`.
- 7 days for release plans (D-104): `research/2026-10-05_e7d_inflow.py` (35 dams, 31 candidates; cache outside the repo),
  `_e7d_inflow_strategies.py` and `_e7d_inflow_narrow.py` (the choice, offline from its log), `_e7d_inflow_build.py R_E4`
  (writes the BUILD_JSON behind `src/floodwatch/data/reservoir_inflow7.json`), `_e7d_down.py` (the river below Kaeng Krachan).
- 2026-10-06: `research/2026-10-06_kk_river_history.py` (older HII years), `_e7d_down_3y.py` / `_e7d_down_3y_fc.py` (+ `_gate.log`),
  `_flood_satellite_kk.py` (GFM 2018 and now), `_flood_sources_kk.py` (GISTDA vs GFM; the key only from the environment),
  `_flood_dem_kk.py` (HAND on any DEM), `_e7d_long_fetch.py` + `_e7d_inflow_long.py` (the inflow choice on a whole wet season).
- The impact tab in a browser: `IMPACT_PW="$(sed -n 's/^IMPACT_PASSWORD=//p' .env)" python3 scripts/impact_tab_check.py` — it
  measures the dams list (row height, groups) and checks that a row and a ◆ open the same dam sheet.

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

### 11c. Seven days below the dam for a release plan (E-7D-DOWN, D-104)
Owner 2026-10-05: "plan reservoir discharge release for 7 days in advance together with future rain and other parameters,
so we need the good prediction for the impact tab for this forecast time period … 7-day prediction is first for impact
analysis for reservoir management only". Until then plans were judged with `impact.whatif` per day — the absolute
mass-balance + rating chain with today's local inflows and diversion held — and one margin per point from the replay,
which scores the chain at the point's own lag (~1–2 days), not at days 3–7.

**Test** (research/2026-10-05_e7d_down.{py,log}). Every issue day of the year of hourly data (2025-09-30…2026-10-05, 328
days); the actual releases of days d+1…d+7 stand in for the plan (the release is the decision, so knowing it is fair);
target = each point's daily mean level on d+k. 15 candidates: keep · mean reversion · the production chain (absolute) ·
the chain anchored on today's level · a gain (today + g·ΔQ, cm per m³/s of release change reaching the point) · 14-input
ridges per point and lead (release change, anomaly, yesterday's change, rain today/3/30 days, forecast rain, forecast ×
wetness, season, spring–neap tide phase) with and without the release terms · the anchored chain corrected by a ridge ·
analogs · a blend · the gain + γ·forecast rain (γ ≥ 0) · + rain × wetness · + mean reversion · a hybrid per point. Two
disjoint samples (odd vs even months; each scored with every fit — ratings, lags, gains — made on the other, training days
whose 7-day target reaches into the scored months dropped; observed rain, an upper bound for rain terms) and an operational
check (fits before 2026-07-06, archived 4-model forecast rain, scored 17 Aug–28 Sep).

| Summed MAE over the 5 points | day 1 | day 3 | day 5 | day 7 |
|---|---|---|---|---|
| production chain vs keep (sample 2) | 381 vs 30 cm | 383 vs 58 | 392 vs 73 | 395 vs 78 |
| hybrid vs keep, picked on 1 → scored on 2 | −1 % | −5 % | −9 % | −13 % |
| hybrid vs keep, picked on 2 → scored on 1 | −2 % | −6 % | −8 % | −14 % |
| hybrid vs keep, operational (forecast rain) | −5 % | −9 % | −15 % | −13 % |
| hybrid vs the production chain, operational | −73 % | −52 % | −45 % | −38 % |

- The **absolute chain is ~1 m off** downstream (85–100 cm MAE at B.10, B.16 and PCH001 on every day; KI-306): plans were
  judged on it. Anchored on today's level, the chain is the best method **right below the dam** (B.18 9 cm at day 7 vs
  20–47 cm for keep), and past the diversion the **gain** is (B.10, B.16, PCH001); both samples agree per point.
- **Rain on the land between the dam and the city did not help:** the non-negative rain coefficient fits to ≈ 0 (the gain
  + rain equals the gain), and the 14-input ridges are worse than keep (2–4× worse operationally) — one mostly dry year
  does not teach them the wet season. Mean reversion is worse operationally (+8 to +15 %); analogs ≈ keep. Future rain
  enters the plan through the reservoir's inflow (§9d), not the river's level.
- **Physics over fit:** fitted on the dry months alone, B.10's gain came out *negative* (−0.27…−0.77 cm per m³/s: small
  releases, most of the water diverted at เขื่อนเพชร, releases raised when the river was low). A negative gain would tell a
  planner that releasing more lowers the river; gains are clipped at 0 and each month is scored with gains from the other
  months.

**Served (D-104, `impact.river7`, `impact.level7`, hourly):** level(c, k) = today's level + Δrating(release reaching B.18
on day k) at B.18; = today's level + g(c, k) · ΔQ(c, k) elsewhere (g ≥ 0, fitted on the year; ΔQ in m³/s of release change
that has reached c by day k, whole-day travel times). Margin a plan must keep = that point's MAE on that day; the range
shown = the 90 % error. Live hindcast 2026-07-01…09-28 (each month scored with gains from the other months), MAE day 1→7:
B.18 8→11 cm (keep 10→28), B.10 12→41 (12→42), B.16 12→38 (12→39), B.15 8→29 (= keep; gain ≈ 0), PCH001 10→34 (10→37);
gains on day 7: B.10 0.63, B.16 0.55, B.15 0.17, PCH001 1.01 cm per m³/s. 2026-10-05 22:40 UTC: 228 of 676 plans feasible,
★ = 21.5 constant, bound by B.18 (0.14 m from its bank against its 0.11 m day-7 error). Tests:
`test_river7_learns_how_each_point_follows_a_release_change_and_scores_it_per_day`, `test_river7_never_lets_more_release_lower_a_point_downstream`,
`test_plans_use_the_river7_levels_once_the_release_reaches_each_point`, `test_a_plan_keeps_the_river_models_margin_for_each_day`,
`test_the_plan_says_which_downstream_model_it_used_and_the_story_states_its_tested_error`.

**Three wet seasons (2026-10-06; owner: "Continue all you suggested … best performance / less errors").** HII serves
older hourly years when start and end are both in the past (B.18, B.10, B.16, B.15 from 2023-09-30; PCH001 10-min), so
the test was rerun on 2023-09-30 … 2026-10-05 (1,103 days; research/2026-10-06_e7d_down_3y*.{py,log}). Month samples
with observed rain: the **gain at every point (B.18 too)** beats the served hybrid at days 3 and 7 in both samples
(s1 78.5 vs 79.8 cm summed at day 3, 96.7 vs 99.0 at day 7; s2 65.6 vs 66.6 and 96.3 vs 97.2) with no more points worse;
with archived *forecast* rain over the three wet seasons (500 issue days): the same (s1 103.7 vs 105.2, 131.1 vs 133.3;
s2 85.8 vs 87.0, 128.1 vs 128.4). The rain terms come alive with two more wet seasons (γ > 0; best at day 3, −3 to −6 %)
but leave a fourth point worse at day 7 in one sample — a near-miss. On the **live window** (Jul–Sep 2026, each month
scored with the other months, the same three-year history), however, the hybrid stays better at days 5–7 (summed 153.5
vs 159.0 cm at day 7; B.18 11 vs 14 cm): a change ships only when it holds everywhere, so **the served model stays the
one-year hybrid**. `impact_history` keeps three years of daily means (`impact_daily_<case>`) and `river7(history=…,
method="gain")` is tested, so the next wet season decides without new code.

### 11d. A flood view for each release plan (owner 2026-10-06, D-105)
Owner: "can we show flood area in the map for each of reservoir discharge release scenario?"; chose all four options —
river reaches + ONWR's layers, a DEM flood area as research first ("firstly for experiment … I will ask for higher
resolution DEM later"), past floods as analogues ("satellite images might be unreliable, please validate before use …
compare with google or any global flood info"), and ONWR's flood maps when they arrive.
- **Shown:** for the plan and day picked in its sheet, the Phetchaburi in pieces by nearest gauge (≤ 10 km), coloured red
  over the bank, orange inside that day's model error, blue otherwise (`impact.river_reaches`, `colorReaches`) — the
  legend says it is no flood area (D-019); ONWR's area warning, +1…+3-day forecast and observed flooded area over the case
  (`collectors.onwr_flood`, 3-hourly; `floodwatch.mvt` reads the vector tiles and matches the reference decoder on a live
  tile), with ONWR's update times, credited "ที่มา: สทนช." and said not to be results of the plan. 2026-10-06: warning 36
  cells, +1 day 226 (176 at class 3), +2 days 174 (161 at class 3), observed 3 polygons.
- **The record:** in 2023-09 … 2026-10 none of the five gauges went over its bank (closest: B.16 1.9 m below on
  2024-10-11, B.15 1.87 m below on 2026-09-29) — no recent release-driven flood exists to calibrate a flood map against.
  The one in reach is August 2018 (Kaeng Krachan up to 24.36 ล้าน ลบ.ม./วัน on 21 Aug).
- **Satellites (not shown):** Copernicus GFM (archive from 2015) over the lowland below the dam: 39–58 % of it hidden from
  the radar in every pass (towns, orchards — where damage is); 2018 flood outside permanent water 0–6.5 km² a pass (6.2 on
  21 Aug), consecutive passes keep < 35 % of each other's flood; 2026: 53 km² on one track and ~4 km² on others days
  apart. GISTDA's 30-day flood (18.1 km²) vs GFM (95.6 km²): 73 % of GISTDA's flood also in GFM, only 13 % of GFM's in
  GISTDA. Google Flood Hub has no gauge in the box. Past-flood analogues therefore fail validation here and are not shown.
- **DEM experiment (not shown):** height above nearest drainage from Copernicus GLO-30 (30 m, the river burned in) scored
  against GFM's 2018 flood within 15 km of the river: that flood is 0.2 km² on land the radar saw, so CSI is 0.012 at
  every stage (HAND maps 18–49 km² for 0.5–8 m) — unscorable rather than proven wrong. Needed before any land flood area:
  an observed extent of a release flood (ONWR/RID flood-coverage maps by release level, data request #5, or imagery of a
  future event) and the higher-resolution DEM the owner will request; the script takes any DEM path.
research/2026-10-06_flood_satellite_kk.{py,log}, _flood_sources_kk, _flood_dem_kk.

## 12. How the models improved, release by release

> Owner, 2026-10-06: "In models.MD we expect to see how good the models were developed here along many release and
> history: for example, how good can we improve the accuracy, how better the models, what we benefit more."

Two kinds of evidence, both from running code:
- **When a change shipped** — the test that decided it: chosen on one period or sample, scored on another it never saw
  (§5d, §9d, §11c). Old and new are compared on the same days, so this measures the change itself.
- **As issued** — what each model generation actually forecast, scored against what the water then did
  (`research/2026-10-06_model_history.py`: all 91,429 forecast runs stored since 2026-09-26 12:27 UTC at 1,022 gauges;
  the gauge's mean reading within ±30 min of each valid time; read-only). This is what people saw, but each generation
  ran in a different week, so on its own it cannot rank them.

"vs no change" = the forecast's mean absolute miss against assuming the water stays where it is (persistence): −10 % means
the typical miss is 10 % smaller.

### 12a. The public forecast: what each release changed, and what its test showed

| Release (date) | What changed | Measured when it shipped | What people got |
|---|---|---|---|
| v0.1.0 (2026-09-26) | a ladder per gauge ("no change", tide, trend) chosen by a 45-day backtest; a model only where it beats "no change" by ≥ 10 % (D-012) | the gate itself, per gauge and horizon | forecasts with ranges for ~300 Bangkok-area gauges; "no change" where no model won |
| v0.8.0 (09-27) | `star`: forecast rain + upstream gauges + the Chao Phraya Dam release (D-052) | gauges with a 48 h forecast ≥ 30 % better than "no change": 8 → 35; Ayutthaya 48 h error 27 → 17 cm; the gain held at 87–100 % of gauges on three separate 45-day windows | water coming from upstream seen up to two days ahead |
| v0.10.0 (09-27) | BMA's 199 canal gauges get a year of history (D-054) | `star` beat "no change" at 12 h on 46 of 85 BMA gauges (≥ 30 % on 17); "ประเมินไม่ได้" fell from 83 % to 39 % of Bangkok pins | canal forecasts and a judged canal factor in Bangkok |
| v0.16.0 (09-30) | nationwide parity: 733 more gauges get history, QC, the ladder and the gate; rain cells and learned upstream gauges outside Bangkok (D-064) | the same gate per gauge | forecasts for ~1,000 gauges (294 → 1,021 in the record) |
| v0.20.7 (10-03) | one forecaster per gauge: the measured trend became a model method that must win its place (D-080) | — | the words, the chart and the tabs agree (KI-270) |
| v0.25.0 (10-04) | `star` reads 7/30-day means and 1/3/72 h changes (D-092); up to 4 learned upstream gauges (D-093) | on unseen gauges, error vs "no change" at 24/48/72 h: −6.6/−5.5/−5.3 → **−8.3/−8.5/−9.4 %**; gauges keeping a ≥ 10 % gain 51/44/49 → 67/70/69; at 72 h 21 gauges worse than "no change" (was 10) | more gauges with a real forecast; slow returns to the usual level learned |
| v0.26.0 (10-05) | Flood Hub as an input near its points (D-097); the 90 % range widened daily until 9 in 10 recent outcomes fall inside (D-098) | 79 gauges: 72 h −8.3 → −9.2 %, 48 h −11.2 → −11.4 %; factors ×1.15/1.20/1.40 at 24/48/72 h | ranges meant to hold as stated (12b: not yet) |

### 12b. The public forecast as issued (2026-09-26 → 2026-10-06)

All gauges: the issued median's error vs "no change" (forecasts scored at 24 h in brackets); the share of 24 h forecasts a
model served (not "no change"); how often the issued 90 % and 50 % ranges held at 24 h (they should hold 90 % and 50 %).

| Generation (releases; when it ran) | Gauges | 6 h | 12 h | 24 h | 48 h | 72 h | Model served | 90 % held | 50 % held |
|---|---|---|---|---|---|---|---|---|---|
| mvp-0.1 (v0.1–v0.7; 09-26 12:27 → 09-27 12:10, the flood peak) | 294 | −10.8 % | −4.8 % | −5.6 % (600) | −7.5 % | −9.6 % | 46 % | 87.5 % | 47.8 % |
| star-0.2 (v0.8.0–v0.20.6; 09-27 → 10-03) | 1,021 | −11.3 % | −10.7 % | −6.6 % (10,962) | −2.8 % | +0.4 % | 38 % | 88.2 % | 51.5 % |
| star-0.3 (v0.20.7–v0.24; 10-03 22:24 → 10-04 16:04) | 987 | −20.5 % | −19.6 % | −5.7 % (24,373) | +2.1 % | – | 44 % | 87.7 % | 48.2 % |
| star-0.4 (v0.25.0; 10-04 16:49 → 10-05 07:00) | 990 | −15.4 % | −14.5 % | −3.5 % (16,938) | – | – | 56 % | 81.0 % | 39.2 % |
| star-0.4, calibrated ranges (v0.26.0–v0.33.0; 10-05 07:00 → 10-06 07:39) | 998 | −14.1 % | −13.0 % | −1.6 % (1,103) | – | – | 54 % | 82.5 % | 37.1 % |

"–": too recent to score, or fewer than 30 forecasts. Where a model was served, its own forecasts against "no change" on the
same runs, at 6/12/24/48/72 h: star-0.2 −20.5/−22.2/−17.9/−13.6/−8.7 %; star-0.3 −32.5/−32.2/−15.7/−5.1 %; star-0.4
−24.6/−23.5/−10.9 %; calibrated −23.2/−23.6/−8.2 %. On the 266 gauges every generation forecast (mostly the first
Bangkok-area set), at 6/12/24 h: mvp-0.1 −18.4/+1.4/−7.9 %; star-0.2 −6.5/−2.3/−6.4 %; star-0.3 −5.4/−1.9/−3.4 %;
star-0.4 +2.8/−0.2/+0.3 %; calibrated +0.7/−1.1/+2.2 %.

**How to read it.** Each generation ran in a different week: mvp-0.1 on the flood peak around Bangkok ("no change" missed
by 32–81 cm), star-0.2 over six days as rivers began to fall nationwide, star-0.3 for 18 hours, star-0.4 for a day and a
half of recession. Raw errors are not comparable, and even the ratios move with the weather; the fair old-vs-new comparison is the
test in 12a.

**What improved.**
- **Reach:** ~300 → ~1,000 gauges with forecasts and ranges (v0.16.0).
- **More real forecasts:** at 24 h the share served by a model rose from 38 % (star-0.2) to 56 % (star-0.4) — fewer "?" rows.
- **Where a model speaks, it helps:** its 6–12 h misses are 20–33 % smaller than "no change" on the forecasts it served,
  24 h 8–18 %.
- **Nationwide, 6–12 h forecasts** have been 11–21 % better than "no change" in every generation since `star`.

**What did not, yet.**
- **Beyond a day the issued gain is small:** 24 h −1.6 to −6.6 %; 48–72 h about zero since `star` (star-0.2 −2.8 % and
  +0.4 %, star-0.3 +2.1 % at 48 h) — only the flood-peak day gave −7.5/−9.6 % (mvp-0.1).
- **The ranges hold less often than they say:** the 90 % range held 80–89 % (star-0.4: 81–83 % at 24 h), the 50 % range
  37–55 % (star-0.4: 37–39 % at 24 h). The daily calibration (v0.26.0) has not closed the gap: the stored ranges are the
  calibrated ones (`forecast.widen90`), and at 24 h only one issue hour can be scored so far (82.5 % of 1,103). KI-287 is
  open again.
- **On the 266 gauges every generation forecast,** the latest model is level with "no change" in its two days (−1.1 to
  +2.8 % at 6–24 h), where star-0.2 and star-0.3 gained 2–7 % in their weeks. Whether that is the recession's flat canals or
  a loss from the v0.25.0 inputs on these gauges needs a same-days backtest of the old and new `star` on them (HANDOFF next
  steps).

Re-run `research/2026-10-06_model_history.py` after each model change and weekly: a backtest gain in 12a has to show up
here as issued.

### 12c. Planning models for the impact tab (1–7 days)

| Release (date) | Model | Measured when it shipped | What planners got |
|---|---|---|---|
| v0.27.0 (10-05) | a what-if chain for Kaeng Krachan, gated against "keep today's level" (D-099) | the gate stayed closed until a model beat keeping today's level | no number on screen before it was tested |
| v0.29.0 (10-05) | 7-day release plans; inflow held at today's value with a regime band (D-101) | a rain-driven inflow model lost to persistence at every horizon: shown as context, not used | plans that say which side is tested |
| v0.30.0 (10-05) | a rain model per dam on archived rain *forecasts*, with a monthly loss term (Q58, D-102) | beats persistence by ≥ 10 %: 15 of 17 dams at 3 days, 11 of 17 at 7 days | 7-day storage trends on the dams list |
| v0.32.0 (10-05) | the served inflow model fed with the mean of four rain forecasts; the river below the dam as B.18's rating anchored on today's level plus a non-negative release effect, with a margin per day (D-104) | inflow vs persistence (two dam samples): 3 days −23.5/−18.1 → **−28.0/−22.4 %**, 7 days −17.2/−20.5 → **−18.5/−23.4 %**; river: the old chain was ~1 m off, the new one beats "keep today" by 5–15 % at days 3–7, error ~10 cm on day 1 to ~40 cm on day 7 | plans checked against each day's tested error instead of one number |
| v0.33.0 (10-06) | damped persistence + ECMWF rain on days 3–7 where persistence was served, chosen on the whole 2025 wet season (D-106); the river re-tested on three wet seasons | 2026 wet season, two samples: 3 days −23.4/−20.3 → **−24.8/−23.8 %**, 5 days −22.3/−28.1 → **−32.0/−31.0 %**, 7 days −18.8/−25.6 → **−27.0/−28.2 %**, no dam made worse than before; the river's alternative lost the live season, so it stays | 32 dams on tested 7-day models (was 16); Kaeng Krachan's plans on a model from day 3 |

Each row's numbers come from its own test (different periods and samples): compare within a row, not down the column.

### 12d. What it adds up to
- **Residents:** forecasts with ranges at ~1,000 gauges instead of ~300; more of them answer "up or down?" with a tested
  model (24 h: 38 % → 56 % of forecasts); 6–12 h misses 11–20 % smaller than "no change" nationwide. Still to earn:
  ranges that hold as stated, and real gains beyond 24 h.
- **Planners (ONWR, RID):** a 7-day plan carries each day's tested error (~10 cm on day 1 to ~40 cm on day 7) instead of a
  chain ~1 m off; 32 dams have tested 7-day inflow models, with misses 24–32 % smaller than persistence at days 3–7 in
  the 2026 wet season.
- **Trust:** every change is judged on data it never saw, units made worse are reported with their size (D-107), and the
  as-issued record (12b) checks that a backtest gain reaches people.
