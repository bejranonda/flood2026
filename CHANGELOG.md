# Changelog

All notable changes to BKK FloodWatch 2026. Versions follow `floodwatch.__version__`, which the UI shows (D-025).

## v0.15.0 — 2026-09-28
- **Proven consistent (owner: "prove the consistency of panel and text", "validate the UI in many possibilities"):**
  `scripts/ux_consistency.py` opens all 310 station sheets, 67 pins and 4 viewports (360/390/768/1440 px) and checks
  list = sheet = pin panel, words vs numbers, horizon order, headline vs rows, duplicates and overflow. Final run:
  1,261 rows, 0 issues (2 accepted: two different gauges with the same status). Fixed on the way (KI-244, D-062):
  the pin headline spoke for 12 h and for a 3-gauge majority while the panel shows the nearest gauge's 24/48 h rows;
  "ค่อนข้างสูง แต่แนวโน้มยังทรงตัว" above falling rows; "ยังทรงตัว" with no trend at all; a list 24 h row "→ ทรงตัว"
  where the sheet said "?"; model chips with a range crossing zero ("↗ เพิ่มขึ้น −1 ถึง +14"); the gauge pill
  repeating the factor word; the same measured line twice in the pin panel.
- **Numbers back on measured-trend rows (owner):** "↘ ลดลง ราว −7 ซม." = the measured trend continued and damped
  (slope·h·e^(−h/48)), so word and number agree; past odds stay in the ⓘ.
- **Shorter panels (owner):** "ควรทำอะไรตอนนี้" removed; "วิธีคาดการณ์" collapsed; "(เมื่อวาน N)" kept on one line;
  the recovery line keeps its early end ("29 ก.ย. ราว 02–05 น. หรือนานกว่า 3 วัน" instead of "หลัง 72 ชม.").
- Tests: 103 passing (+2).

## v0.14.0 — 2026-09-28
- **Trend rows follow what the chart shows (owner, D-060, KI-242):** where no model sees a direction, the 12/24/48 h
  rows follow the measured trend ("↘ ลดลง · ตามแนวโน้มที่วัดได้"; odds and past range in the ⓘ, e.g. "ในอดีตเป็นแบบนี้ต่อ
  6 ใน 10 ครั้ง"). Slow falls count: 48 h is used when 24 h shows no trend, and whole-cm steps no longer read as
  "ขึ้นลงสลับกัน" (WL.LBK.03). "→ ทรงตัว" only when the likely range stays within ±5 cm, and never after a "?".
- **Stuck gauges hidden (KI-241):** one exact value in ≥ 90 % of 24 h (six BMA gauges at 1.00 m / 0.40 m) → note
  "ค่าค้าง", no level, status or forecast.
- **Resident first (D-061):** "ควรทำอะไรตอนนี้" (3 bullets per risk level, from DDPM advice, collapsed); the pin
  panel shows the nearest canal's measured trend under the headline; GPS shows the district; operator lines behind
  "รายละเอียดข้อมูล"; the map opens on Bangkok; the Chao Phraya tab starts in Bangkok; "(เมื่อวาน N)" after the bank
  distance.
- Tests: 101 passing (+5).

## v0.13.0 — 2026-09-28
- **What the water did in the last 24 h, in finer words (owner, D-058, KI-240):** sheet, point panel and list cards
  show "24 ชม. ที่ผ่านมา: ลดลง 5 ซม." from a straight-line fit of the measured levels (every 10 min, dropouts removed):
  < 2 cm ทรงตัว · 2-4 cm เล็กน้อย · 5-19 cm ลดลง/เพิ่มขึ้น · ≥ 20 cm มาก, and "ขึ้นลงสลับกัน" for tide or pumps.
  It replaces "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า", which the "no change" model showed at 26 gauges that had
  clearly fallen (e.g. WL.CKS.01 −91 cm; BKK021 −5 cm). Live: 272 gauges get a line.
- **Review of v0.9.0 → v0.11.2 fixed (KI-239, D-059):** the "when it drops" line states its conditions again
  ("หากไม่มีฝนตกหนักเพิ่ม", "ความเชื่อมั่นต่ำ"; D-005); river gauges no longer decide the canal factor; a lone gauge
  within 3 km is not trusted when a gauge within 5 km disagrees by 2+ ranks (issue #3); the headline trend uses the
  same distance band as the gate; the daily BMA history refresh runs 20 gauges per run and asks HII nothing when idle;
  a gauge failing 3 backfill runs is set aside; sheet drag resets on `touchcancel`; a 12 h-only gauge shows its row;
  a string payload from HII gives a clear error. Bangkok pins with a usable canal statement: 55 % → 50 %.
- Zig-zag rows (KI-238) re-measured after v0.12.0: 3 of 221 gauges, none with opposite directions on screen; left open.
- Tests: 96 passing (+7).

## v0.12.0 — 2026-09-28
- **Erratic (pump-affected) gauges are hidden, dropouts removed (owner, D-057, KI-237):** a new worker task `qc`
  (every 10 min) flags single- or two-reading dropouts (e.g. -2.00 m at WL.LPT.03, WL.KPM.05) as `dropout`, and marks
  a gauge erratic after 3 or more steps of ≥ 0.30 m within 30 min in 24 h (WL.SSB.08 jumping ±0.8 m, pump cycling at
  WL.BNJ.02). Erratic gauges keep their dot and measured chart; level, status, trend and forecast are hidden with a
  note, and they are left out of the point check. 11 of 307 focus gauges on 2026-09-28. Tests: 89 passing (+6).
- Station sheet of an erratic gauge leads with "ไม่แสดงระดับน้ำ (ขึ้นลงผิดปกติ)" and the reason instead of "no forecast
  data"; the generic unknown label is now "ไม่ทราบสถานะ" (it said "no bank" also for old data). One-off clean-up of
  45 days: 2,006 dropout readings at 54 gauges flagged (the history the forecast trains on).
- Code review of v0.9.0 → v0.11.2 and the per-horizon zig-zag logged as open issues (KI-238, KI-239).

## v0.11.2 — 2026-09-27
- **Shorter "can't summarise" outlook (owner review, KI-235):** the headline is now "สถานีรอบจุดไม่ตรงกัน ยังสรุป
  ระดับคลองไม่ได้" (or "ไม่มีสถานีวัดน้ำใกล้พอ …") and the text under it is only the rain condition. The long reason
  ("สถานีใกล้เคียงวัดคนละแหล่งน้ำ … ดูแนวโน้มของแต่ละสถานีด้านล่าง") is gone — the canal factor already says
  "คลองรอบจุดต่างกันมาก". Tests: 83 passing (+1).

## v0.11.1 — 2026-09-27
- **Canal factor readable at a glance (owner review, KI-234):** each gauge is its own block with the same structure —
  a small label on its own line ("คลองใกล้สุด" / "คาดการณ์จากคลองใกล้เคียง"), then the **bold name** · distance ·
  status pill, then that gauge's 24/48 h rows or "ยังไม่มีคาดการณ์"; a divider separates the two gauges. Before, one
  name was bold and the other not, and the labels ran into long lines.

## v0.11.0 — 2026-09-27
- **One trend format everywhere (D-056, KI-233):** list, point panel and station sheet use the same aligned rows —
  "ใน 24 ชม. · [→ ทรงตัว] · −7 ถึง +7 ซม. · ⓘ". A direction is shown only where a real model beat "no change" at that
  horizon; otherwise "? ไม่แน่ชัด" with the likely range (same rule for 12, 24 and 48 h).
- **Compact canal factor:** one gauge with its rows and one "when it drops" line; details behind "รายละเอียด"; a
  borrowed forecast is labelled "คาดการณ์จากคลองใกล้เคียง".
- **Station sheet:** the trend block comes first (rows, when it drops, peak time, chance of reaching the bank);
  emojis and the duplicate trend headline removed; BMA source and datum moved into ⓘ.
- **Words match numbers:** bank gauges in watch/warning while the bank is > 30 cm away now say "น้ำเต็มลำน้ำ 91 %"
  instead of "ใกล้ตลิ่ง" (CPY015 was "near bank" 158 cm below it). Kicker "คาดการณ์ข้างหน้า"; depth reports "N ราย".

## v0.10.2 — 2026-09-27
- **The canal factor always shows a trend when one exists** (owner: "users cannot see the trend … show both"): when the
  nearest canal has no forecast (37 BMA gauges HII does not serve, history since 26 Sep), the panel adds **the nearest
  canal that has one** (`nearest_canal_trend` in `/api/point`). Each canal line says **when the water may drop** ("คาดว่า
  จะต่ำกว่าตลิ่ง: 30 ก.ย. – 2 ต.ค.", or "ยังไม่เห็นแนวโน้มลดลง…").
- **Plain words** for the canal summary: "คลองรอบจุดต่างกันมาก — คลองใกล้จุด 3 แห่งมีตั้งแต่ “ยังรับน้ำได้” ถึง
  “ล้นตลิ่ง” จึงสรุปรวมไม่ได้ ดูทีละคลองด้านล่าง"; the "ทั้งรัศมี 8 กม." block is gone.
- Tests: 82 passing (+1).

## v0.10.1 — 2026-09-27
- **Fixed a contradiction found on the live site:** a "steady" chip next to a one-sided range read "→ ทรงตัว … เพิ่มขึ้น
  1–22 ซม." (WL.SSB.06). Steady ranges are now always worded neutrally: "อาจแกว่งตัว +1 ถึง +22 ซม.".

## v0.10.0 — 2026-09-27
- **BMA canal gauges get a year of history (D-054).** HII serves BMA's own `WL.*` gauges through
  `waterlevel_graph?station_type=canal` back to 2024, identical to the relay (0.0 m difference). New collector
  `bma_history`: one-year hourly backfill for all 199 gauges, then a daily 3-day refresh. BMA gauges now enter the
  forecast backtest: on a dry run `star` beat "no change" at 12 h on 46 of 85, with real skill (≥ 30 %) on 17; at 24/48 h
  almost none — BMA pumps and gates drive the canals.
- **Canal factor judged from the nearest gauges (D-054, KI-229):** "ประเมินไม่ได้" fell from 83 % to 39 % of Bangkok
  pins. The panel leads with the nearest canal gauge (distance, agency, status, 24 h and 48 h change; a note when it is
  more than 3 km away) and folds the other stations into one line.
- **48 h everywhere, honestly (D-055):** where the backtest isn't convincing, a dashed "? 48 ชม." chip with "ยังบอก
  ทิศทางไม่ได้ · ช่วงที่น่าจะเป็น −10 ถึง +31 ซม." (a range, never a direction). Station lists show the 24 h change.
- **Shorter outlook sentence:** the rain amount now appears once, in the rain factor ("…และคาดฝนปานกลาง อาจมีน้ำขัง
  บนถนนช่วงฝนตก"). Recovery windows show dates (≥ 24 h) or whole hours, never minutes (KI-231).
- **Issues #4 and #5:** the mobile sheet can be pulled down to close (✕ kept); panel headings and factor details share
  one text style.
- **Corrections to v0.9.0 docs:** the `BKK*` gauges are HII's own, and most already had a year of history; "BMA
  local datum" is unverified; public IP addresses removed from the maintained docs (D-028).
- Faster forecast runs: `trailing_mean` vectorised (tested identical to the old loop).
- Tests: 81 passing (+6).

## v0.9.0 — 2026-09-27
- **BMA canal telemetry historical access via HII TIWRM (D-053, KI-103):**
  - **30-Day Historical Canal Telemetry:** Discovered and verified direct access to 30 days of 10-minute resolution water level telemetering from HII's public TIWRM service (`GET https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{station_code}`). Unlike BMA DDS's private/geo-blocked endpoints, HII provides open international access with zero authentication.
  - **Comprehensive Bangkok Canal Gauge Coverage:** Expanded `EXTRA_STATIONS` in `config.py` to include all verified BKK canal gauges (`BKK001` through `BKK021`, plus `CPY015` Krungthep Bridge and `AIT001` Asoke). All 18 active endpoints return full ~4,310 time-series observations in UTC, backfilling historical canal trends across Khlong Saen Saep, Khlong Lat Phrao, Khlong Thawi Watthana, Khlong Phasi Charoen, Khlong Maha Sawat, and Khlong Lam Pla Thio.
  - **BMA (`WL.*`) vs HII (`BKK*`) Cross-Referencing:** Documented station taxonomy, dual-channel ingestion, and spatial proximity pairings (e.g. BMA `WL.SSB.06` ↔ HII `BKK008` Bang Kapi, `WL.SST.01` ↔ `BKK001` Lat Phrao Khlong 2) in `docs/KNOWLEDGE.md` §11 and `docs/SOURCES.md`.
  - **Explicit Datum Distinction:** Preserved clear distinction between BMA's local municipal datum (`ม. (หมุด กทม.)`, where mean sea level is ~+1.50 m) and HII's national Mean Sea Level / Ko Lak 1915 datum (`ม.รทก.`), preventing dangerous false-critical water level alarms.
  - **VPN Probe Diagnostic (KI-505):** Egress through Thai residential proxy (the VPN Gate relay in Ayutthaya) successfully connects to DWR (`ews.dwr.go.th`) and Royal Thai Navy Hydrographic Dept (`hydro.navy.mi.th`), but confirmed that BMA's perimeter firewall subnet actively drops TCP SYN packets from this VPN range.
- UI: Bumped version indicator to `v0.9.0` in header badge and footer; updated data source descriptions in index.html and docs.
- Tests: 75 passing.

## v0.8.0 — 2026-09-27
- **New forecast method `star` (D-052): forecast rain + upstream water + Chao Phraya Dam release.** Each gauge now also
  tries a regression on its own tide/trend, the 2 nearest upstream Chao Phraya gauges, the C.13 release and the forecast
  rain over the horizon. It is used only where it beats the gauge's own methods on the same backtest rows and "no
  change" by the skill gate. Validation on 3 separate 45-day windows and out of sample (choose on one window, score on
  the next): the gain held at 87–100 % of gauges; gauges with a 48 h forecast ≥ 30 % better than "no change" went from
  8 to 35. Largest gains on the upper river (Ayutthaya 48 h error 27 → 17 cm).
- **Rain history for training:** new collector `openmeteo_prev` (daily) stores rain as it was forecast 1–2 days earlier
  (Open-Meteo previous runs) in `rain_hindcast`; one year backfilled for the 9 rain points.
- **Fixed before release:** gaps in a gauge's own record made the live forecast silently fall back (Ayutthaya);
  own levels are now carried over gaps ≤ 6 h when building inputs.
- UI: method names in Thai in the station sheet ("ฝนคาดการณ์ + น้ำจากต้นน้ำ" for the new method); confidence tooltip
  and footer explain what the models use. The 48 h line (D-050) now appears wherever the new method earns it.
- Q29 answered: no database backup for now (risk accepted, KI-511).
- Tests: 75 passing (+8).

## v0.7.0 — 2026-09-27
- **Point panel redesigned (issue #3, D-051):** one panel instead of three boxes — "แนวโน้ม 12–24 ชม. ข้างหน้า" with a
  single ⓘ for sources and caveats (owner: "everything into ⓘ"), a larger headline, and "ปัจจัยที่ใช้คาดการณ์": canal,
  rain and street reports, each with a coloured dot **and** a word. The canal dot follows the confidence gate (grey
  "ประเมินไม่ได้" when gauges are far or disagree, never red from one overflowing gauge). District line under the
  coordinates (`/api/reverse`, e.g. "คลองจั่น, บางกะปิ, กรุงเทพมหานคร"), filled in after the panel shows.
- **Report form behind a button (issue #2):** "รายงานน้ำที่จุดของคุณ" opens the form in a popup. Baseline for
  comparison: 57 reports in the 24 h before release.
- **48-hour line only where proven (D-050):** station sheets show +48 h only at gauges whose 48 h backtest is "medium"
  (7 of 102 today, tidal river/estuary). High gauges with no forecast fall say "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า".
- **HII's official 7-day forecast archived, not shown yet (D-050, KI-112):** new collector `hii_fews_forecast` (every
  3 h; CPY011, CPY014, PAS008, C.13, C.2, C.3, C.7A, C.35) → table `external_forecast`; `scripts/score_hii_forecast.py`
  compares HII, "no change" and ours on the same issue times.
- **Research (research/2026-09-27_forecast_48h.md):** measured what limits 48 h forecasts and what fixes it — upstream
  flow and dam release (Ayutthaya 48 h error 26.8 → 18.6 cm), forecast rain (canal 42.9 → 36.5 cm), network vs
  proximity space-time AR, k-NN analogues; SSN/GTWR/ST-GNN assessed and kept for the national phase.
- **Fixed:** "nearest canal" could be a river gauge (KI-227); tapping ⓘ in a list opened the station (KI-228); access
  logs kept place-search text and point coordinates, against D-032 (KI-512); rain words "ไม่มีฝน"/"ฝนเล็กน้อย" below
  4.5:1 contrast.
- Tests: 67 passing (+6). Checked at 390 px at three probe points; popup, ⓘ toggle and list-ⓘ verified by driving
  headless Chrome.

## v0.6.5 — 2026-09-27
- **Compact UI: single ⓘ confidence indicator, collapsible legends, and datum tooltips (D-049, owner feedback):**
  - **Single ⓘ confidence symbol:** Replaced multi-dot meter with a single circular `ⓘ` button (sky-blue `.conf-medium` for tide-validated models, slate-gray `.conf-low` for baseline statistical models). Eliminates mobile line wrap. Includes desktop hover tooltips and touch-triggered non-blocking toast notifications (`showToast`).
  - **Collapsible chart legend:** Folded dense 3-line textual SVG chart definitions (`เส้นทึบ = ...`) into a sleek `<details class="chart-legend"><summary>ℹ️ สัญลักษณ์กราฟ</summary>...` collapse, reclaiming 3–4 lines of vertical screen height.
  - **Observation time prioritized & MSL datum tucked:** Main line keeps the actionable observation timestamp (`ข้อมูล 27 ก.ย. 18:40 (15 นาทีที่แล้ว)`), tucking raw technical surveying datum into an adjacent `[ม.รทก. ⓘ]` button.
  - **Compact point forecast banner:** Relocated forecast basis to a top-row button (`อ้างอิงข้อมูล ⓘ`) and integrated canal distance warnings into an inline label tooltip `ⓘ`.
  - **Methodology legend in footer:** Added confidence indicator color key to the "ที่มาข้อมูลและวิธีคาดการณ์" popup.
  - Cache-busters bumped: `style.css?v=19`, `app.js?v=28`.

## v0.6.4 — 2026-09-27
- **Human-centered forecast phrasing and confidence indicators (D-048, owner feedback):**
  - **Zero-crossing interval clarity:** Replaced confusing literal delta intervals like "น่าจะลด 11 ถึงเพิ่ม 17 ซม." with intuitive citizen wording: `ทรงตัว (อาจแกว่งตัว -11 ถึง +17 ซม.)`.
  - **Friendly UX confidence indicators:** Replaced harsh negative wording "มั่นใจต่ำ" with progressive dot scale badges: `●○○ คาดการณ์เบื้องต้น` (for persistence/statistical baseline) and `●●○ คาดการณ์ปานกลาง` (for tested harmonic tide models) with explanatory tooltips on the 45-day backtest.
  - **Visible canal outlook at point check:** When area confidence is low/none due to mixed gauge statuses across 8 km, the forecast banner now explicitly displays the nearest canal station (`คลองใกล้เคียงที่สุด (ชื่อสถานี ห่าง X.X กม.)`) with its rise/fall forecast and distance disclaimer `*(ระดับน้ำที่สถานีคลอง ไม่ใช่ระดับน้ำที่จุดนี้หรือบนถนน)*` (D-021).
  - **Stacked alert deduplication:** Suppressed duplicate top urgent road alert banner when the forecast banner is already in high-risk alert mode, removing redundant warning boxes.
  - Cache-busters bumped: `style.css?v=17`, `app.js?v=26`.

## v0.6.3 — 2026-09-27
- **Forecast banner now says how much, and how sure (D-047, owner feedback):** "จะเพิ่มหรือลด เมื่อไหร่ เท่าไหร่ และ
  มั่นใจแค่ไหน" — the plain trend arrow gained a coloured chip (5 steps: ลดลงมาก/ลดลง/ทรงตัว/เพิ่มขึ้น/เพิ่มขึ้นมาก) with
  a likely range in cm at +12 h and +24 h, taken from each gauge's own conformal forecast band, plus an honest
  confidence label ("มั่นใจปานกลาง" only when a real model beats persistence and its 90% band held in the 45-day
  backtest — otherwise "มั่นใจต่ำ"; there is no "มั่นใจสูง", a gauge is not the ground at the user's pin, D-021).
  A tidal peak window is shown only when it is ≥ 3 h out (a "peak" 1–2 h away is just "still falling"). Bands wider
  than 1.5 m hide the numbers instead of printing a meaningless range. New `forecast.change_summary()`, `/api/*`
  fields `change12`/`change24`/`peak_h` per station, and `forecast.gauges` on `/api/point` (only the gauges the
  point outlook actually used, so the banner never cites one it didn't rely on).
- **Removed the rain-legend paragraph** (owner: "is it too much?") from the point card and summary strip. Rain now
  shows as a short coloured pill (TMD word + a 4-step mini scale) instead of a full sentence explaining the bands.
- **`/api/point` outlook wording fixed:** when a gauge sits close by but the confidence gate still withholds a
  verdict, the banner now says the nearby gauges *disagree* (different water body/polder) rather than claiming
  none is "close enough" — the old wording was misleading when a gauge was in fact under a kilometre away.
- Tests: 61 passing (+5). Checked at 390 px on a throwaway preview container; production untouched until deploy.

## v0.6.2 — 2026-09-27
- **Fixed issue #1 "ฝน -27 มม. แปลว่าอะไร"** (KI-224): the point card showed `ฝน 24 ชม.: ~27 มม.`. On a phone the
  `~` read as a minus sign, the amount had no meaning attached, and "24 ชม." did not say it is a forecast.
  - Rain is now worded with the **Thai Meteorological Department's rain-amount categories** (ฝนเล็กน้อย 0.1–10.0 ·
    ฝนปานกลาง 10.1–35.0 · ฝนหนัก 35.1–90.0 · ฝนหนักมาก ≥ 90.1 mm, from tmd.go.th "เกณฑ์อากาศ", read 2026-09-27):
    `ฝน 24 ชม. ข้างหน้า: ฝนปานกลาง (ประมาณ 27 มม.)`, with a one-line legend and the note that a short burst can
    flood streets even when the day's total is small. The same words appear in the forecast banner.
  - Every user-facing `~` replaced by "ประมาณ"/"ราว" (also river km, the profile legend next to "ติดลบ = ต่ำกว่าตลิ่ง",
    and the feedback location note). When rain is unknown the card says "ไม่มีข้อมูล" instead of "~0 มม.".
  - A number is printed with one decimal when rounding would cross a TMD boundary (35.1 mm is "ฝนหนัก").
  - `/api/point` adds `rain_band`. Tests: 56 passing (+2). Checked at 390 px on a preview container of the branch.
- **Nationwide research validated, not built** (D-044–D-046, APPROACH §19, phase 5): 22 national and international
  endpoints probed live ([research/VALIDATION_2026-09-27_nationwide.md](research/VALIDATION_2026-09-27_nationwide.md),
  re-run script in `research/validation/`). Findings: HII serves BMA's 262 road sensors and 282 canal gauges (+73 we
  lack); official thresholds for 66 level and 87 RID discharge stations; Navy tide for 28 stations; DWR (2,275) and RID
  (921) only via a Thai IP; the HII gate feed is dead (12 of 2,315 fresh); GloFAS points must be snapped (Nong Khai 3
  vs ~9,000 m³/s). `Research_Thailand.md` kept with a 🔴 banner (refuted host, invented numbers, rule-breaking methods).
- **GISTDA works again** (KI-510): our endpoint path and key placement were outdated; with the documented API
  (`/api/2.0/resources/features/flood/7days`, header `API-Key`) the key returns ~50,000 flooded cells nationally.
  `config.py` default and `.env.example` updated.
- **`scripts/owner_status.py` tests services, not the presence of keys:** GISTDA makes one real request (key never
  printed); new rows for the Google Flood API key and a reliable Thai egress.
- Docs: SOURCES §2d, KNOWLEDGE §9, KNOWN_ISSUES KI-110/111/404/509/510/511, GUIDELINES §6.17–19, OWNER_ACTIONS,
  OPEN_QUESTIONS A27–A37 and Q28–Q31, PLAN + phase-5.

## v0.6.1 — 2026-09-27
- **Fixed: the D-041 forecast banner could give a canal verdict without a usable gauge** (D-042, KI-223). Found in
  a routine review: at `confidence=none` (0 gauges) the banner said "สถานการณ์ปกติ … ความเสี่ยงน้ำท่วมต่ำ" from no
  data; at `confidence=very_low` it stated "moderate/rising" while the overview card above it correctly showed no
  verdict — a contradiction on one sheet. A single tidal river gauge's routine swing could also read as the whole
  point "rising".
  - The canal/river gauge layer of the outlook is now used **only when `area.confidence ∈ {low, medium}`** — the
    same gate the overview card already applies (D-021).
  - Trend now needs a **strict majority** of same-water-body forecast gauges, computed separately for khlong
    (drives "canal" wording) and river (tidal; labelled, never used alone).
  - Rainfall (Open-Meteo 24h) is usable everywhere and worded by band (light/moderate/heavy/very heavy), as a
    *condition*, never folded into a "risk is low" verdict; unknown rain no longer prints "~0 มม.".
  - When neither a usable gauge nor strong local evidence (heavy rain, street reports) exists, the outlook returns
    `risk: "info"` (ℹ️, new `.risk-info` style) — stating plainly that gauges are too far or in another basin to
    judge the point, never dressed up as "low risk" or "ปกติ".
  - A new `basis` field (`rain`/`reports`/`gauges`) is shown as a one-line footnote so a checked "low" doesn't look
    identical to an unassessable "info".
  - Evidence for the distance/confidence bands themselves: a 264-gauge snapshot shows status agreement between
    nearby same-agency gauges falling from ~80% at ≤1 km to ~50% by 5–8 km; no polder polygons exist yet, so this
    distance/agreement proxy (unchanged) remains the basis for "confidence", pending real basin boundaries.
  - `src/floodwatch/point.py`, `tests/test_point.py` (+6 tests, 54 total), `web/app.js`/`web/style.css`
    (`app.js?v=23`, `style.css?v=14`).

## v0.6.0 — 2026-09-26
- **Point check redesigned for Bangkok resident clarity** (D-040, UX round 6):
  - **Collapsed static disclaimers:** Educational disclaimers ("นี่ไม่ใช่ระดับน้ำที่จุดนี้...", terrain variation, polders/gates) are collapsed into an expandable `<details class="point-disclaimer">` ("ℹ️ ข้อจำกัดของข้อมูล (สถานีคลอง ≠ ระดับถนนหรือในบ้าน)"), freeing up >40% vertical space on mobile and desktop.
  - **Prominent dynamic alerts:** When street flood reports conflict with calm canal readings (`street_flooding_despite_channels`), an urgent warning banner is displayed at the very top.
  - **Categorized station list in point sheet:**
    - 📈 **สถานีที่มีการคาดการณ์ (12–72 ชม.)**: Shows the nearest 2–3 stations with active ML forecasts (HII/RID gauges with trend and delta12), providing users with forward-looking hydrological trends.
    - 📍 **สถานีคลอง/แม่น้ำใกล้จุดนี้**: Shows the closest 2–3 active real-time gauges (BMA canal gauges with BMA threshold or bank margins), keeping duplicates out.
  - **Stale gauge suppression:** Gauges with no data for > 24 hours (such as `WL.JKK.01`) are automatically excluded from the point check recommendations, eliminating dead clutter.
  - **Traffy flood hotspot visibility:** Increased fill opacity from 0.14 to 0.30–0.55 and added a distinct 1px purple stroke (`#6a1b9a`), making citizen-validated street flood reports immediately visible over map tiles.
  - API `/api/point` now returns `stations_forecast` and `stations_nearby` alongside the backward-compatible `stations` list.
  - **Streamlined area overview & street flood guidance:** Replaced wordy, defensive area paragraphs ("ข้อมูลรอบจุดนี้น้อยหรือขัดกัน...") and removed misleading generic BMA homepage links ("ประกาศเตือน กทม. ↗") in favor of direct map-guided Traffy status: `🚗 น้ำท่วมบนถนน (1 กม.): มีแจ้ง N จุด (ดูจุดสีม่วงบนแผนที่)`.
  - **Point Forecast Outlook & Trend Synthesis (USP, D-041):** Clicking any coordinate now generates a forward-looking 12–24h hydrological and street risk forecast banner (`🔮 คาดการณ์แนวโน้ม 12–24 ชม. ข้างหน้า`), synthesizing nearby ML channel trends, 24h precipitation, current canal capacity, and citizen street reports into a clear, actionable summary (e.g. `⚠️ เสี่ยงน้ำท่วมขังเพิ่มขึ้นจากฝนตกหนัก`, `📈 ระดับน้ำคลองมีแนวโน้มสูงขึ้นใน 12 ชม.`, or `✅ สถานการณ์ปกติ / แนวโน้มทรงตัว`).
  - **Ultra-compact 1-line footer & vertical map reclamation:** Compressed the previously multi-line footer into an ultra-compact ~28px flex bar with upward popover details for methodology/sources. Reclaimed 45–50px of vertical viewport height on desktop and mobile for the map and station cards, eliminating wasted bottom whitespace.
  - Cache-busters bumped to `style.css?v=13` and `app.js?v=22`. All 48 tests pass.

## v0.5.1 — 2026-09-26
- **Favicon & brand icon modernized for browser tab recognizability** (D-039, KI-221):
  - Solved browser tab visibility failure: the previous dark navy tile (`#0d3b66` to `#061c33`) had zero edge contrast against dark-mode browser tabs (`#202124` / `#1e1e1e`), and 6 micro-details (triple drop, sub-pixel beacon, 1px border, 3 side gauge ticks) collapsed into an unreadable blur at standard 16×16 CSS pixels.
  - Implemented **"Flood Droplet & Wave"** design: iconic water droplet silhouette, dual rising flood waves (vivid cyan `#38bdf8` and crisp pure white `#ffffff`), glowing amber telemetry beacon (`#fbbf24`), and luminous sky-blue rim (`#7dd3fc`) with soft drop-shadow. Guarantees razor-sharp contrast across dark mode tabs (`#202124`), light mode tabs (`#dee1e6`), and pure white titlebars (`#ffffff`).
  - Rewrote `scripts/generate_favicon.py`: self-contained 2×2 supersampled pure-Python rasterizer (zero external runtime dependencies; builds valid `favicon.svg`, multi-resolution `favicon.ico` [16×16 and 32×32], `apple-touch-icon.png` [180×180 on deep oceanic squircle to prevent solid-black iOS home screen backgrounds], and `icon-192.png`).
  - Bumped icon cache-busters in `web/index.html` to `?v=2`. All 12 API/asset tests pass.

## v0.5.0 — 2026-09-26
- **BMA canal gauges are judged by BMA's own drainage levels** (D-038): ล้นตลิ่ง (over bank) / **คลองเต็ม** (over BMA critical) / คลองเริ่มเต็ม (over BMA warning) / คลองยังรับน้ำได้. Near flooded streets 60 % of BMA gauges were over BMA critical but only 18 % over the bank. BMA `warning`/`critical` stored (`warning_msl` column); `status_basis`, `over_bma_critical_m`, `bma_critical_msl` in the station API; BMA's critical level drawn on the chart; explanation "canal can't take street water well".
- Summary chips: "ใกล้ตลิ่ง/คลองเต็ม", "ยังรับน้ำได้". HII/RID gauges unchanged (bank). `app.js?v=18`. 46 tests.
- The owner's hypothesis (gate in/out mixing) was tested and not supported: only the canal side is stored; 39 of 49 cases were plain canal gauges.

## v0.4.1 — 2026-09-26
- **Map: forecastable gauges only by default** (81), switch "แสดงสถานีที่ยังคาดการณ์ไม่ได้ (N)" to show all (D-037). The list and point check are unchanged.
- **Observed trend for every gauge:** `change_m` / `change_hours` in `/api/stations` (readings 1–3 h apart); cards and details of gauges without a forecast show "สูงขึ้น/ลดลง N ซม. ใน N ชม.ที่ผ่านมา" or "ทรงตัว".
- Fix: the map options sat under the legend and below the fold at 390 px; moved to the top left. `app.js?v=16`. 44 tests.

## v0.4.0 — 2026-09-26
Canals and streets are shown as separate facts (D-036), after the owner saw "flood69 gauges below bank" next to Traffy street floods.
- **"ปกติ" → "ต่ำกว่าตลิ่ง" (blue)** everywhere: a canal below its bank says nothing about the street. Headline "น้ำในคลองต่ำกว่าตลิ่ง N ซม.".
- **Street reports beside each gauge:** `street_reports_6h` in `/api/stations` (Traffy flood reports within 1 km, 6 h); card line, detail explanation (rain beyond the drains, canals pumped low), and a point-check warning `street_flooding_despite_channels`.
- **Filtering:** gauges without data for 24 h folded away in the list and hidden on the map (checkbox); optional "📈 เฉพาะที่คาดการณ์ได้" chip.
- **Traffy:** overloaded (HTTP 502 since 15:11 UTC); requests cut to 40 tickets; the street layer's age is shown when > 60 min (KI-220).
- `app.js?v=14`, `style.css?v=8`. 43 tests.

## v0.3.2 — 2026-09-26
- **Only flood.autobahn.bot remains** (D-035): the owner turned Bot Fight Mode off, so `flood.bejranonda.com` now 301s every path, `/api/*` included (only `/api/health` still answers there for old monitors). curl, Facebook and LINE user agents get HTTP 200 on the main domain; an old `#s=` link lands on the station (tested in a browser). Q18 and KI-506 closed.
- **Fix (KI-219):** since v0.3.0 the HII history job also asked HII's chart endpoint for the 199 BMA gauges (HTTP 500 ×3 each), stalling the single worker loop for ~1 h (no BMA readings or forecast refresh 16:33–17:46 UTC). BMA stations are now excluded; a regression test guards it. No data was deleted.
- **New gauges say they are new** (owner: "the historic graph and forecasting all lost?"): `/api/stations` returns `history_since` / `history_days`; cards of gauges with < 7 days of history show "🆕 สถานีใหม่ เริ่มเก็บข้อมูล …", and the detail sheet explains the short chart and when a forecast starts (~3 Oct for BMA). HII gauges keep their year of history. `app.js?v=12`.

## v0.3.1 — 2026-09-26
- **Everything moves to https://flood.autobahn.bot** (owner request, D-034): pages and static files on `flood.bejranonda.com` answer 301 to the main domain (path, query and `#` fragment kept). `/api/*` stays on the alias because non-browser clients can't pass the main domain's bot challenge.
- ⚠️ Visitors from old links now meet that challenge; the fix is owner-side (Q18, OWNER_ACTIONS priority 1, new scoped option D).

## v0.3.0 — 2026-09-26
Bangkok release: from 10 to 209 Bangkok gauges, and a way to find your soi. Audience: Bangkok residents (owner, Q27).

### Data
- **BMA khlong gauges (199)** via the People's Party relay of BMA's KlongMap, every 10 min, raw payload archived (D-031). Bank = lower bank; BMA `warning`/`critical` not used (KI-215); never compared with HII levels (KI-217); relay risk KI-218. History starts 2026-09-26 16:30 UTC.

### Web and API
- **Place search** `/api/geocode` (OSM Nominatim, Bangkok region, ≤ 1 req/s, queries never logged; ซ./ถ./พหล expanded, "name + number" also tried as ซอย) → opens the point check (D-032). No AI needed.
- **Region chips** (ทั้งหมด / กทม. / ปริมณฑล / เหนือ กทม.), **Bangkok by default this week** (D-033), remembered per device; a search looks everywhere.
- BMA gauges credited on the card and the detail sheet; unit "ม. (หมุด กทม.)".
- The footer's sources and methods collapse behind a tap.
- Link to BMA's "roads to avoid" page in the point card.
- `app.js?v=10`, `style.css?v=7`.

### Fixes
- "ต่ำกว่าตลิ่ง 0 ซม." under an overflow badge → "ระดับเท่าตลิ่ง" (KI-216).

### Research
- BMA KlongMap and road pages unreachable from this host; the BMA road artifact is a static snapshot; its sensor host is a private VPN portal (SOURCES §2c, APPROACH §3.7).

## v0.2.1 — 2026-09-26
Patch release: an owner tracker, a safer alias, and a worker fix. **Live at https://flood.autobahn.bot** (alias https://flood.bejranonda.com).

### Owner tracker (D-026)
- New [docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md): everything needed from the owner, with why, exact steps, cost and how it is verified.
  - R2 is not enabled, and the measured archive growth is ~100 MB/day, so the free tier lasts about two months.
  - The bot-challenge fix is corrected: Bot Fight Mode can't be skipped by WAF rules.
- New `scripts/owner_status.py`: a read-only status check that never prints a secret. It checks the challenge with curl, the Cloudflare API, `.env` keys and one tiny AI call.
- The OPEN_QUESTIONS list is cleaned up (answered items moved).

### Web and API
- **The alias page declares itself canonical** (D-027). Before, `flood.bejranonda.com` told crawlers to use the challenged main domain.
- A tested **`REDIRECT_LEGACY_HOST=1`** switch (301 to the main domain, `/api/health` excluded) is off until the bot challenge is relaxed.
- Version 0.2.1 in the header badge, the footer, `/api/health` and `/api/stats`.

### Fixes
- The worker runs a backfill batch at startup. Frequent deploys had stalled the backfill at 34 of 79 stations (KI-212). **After the fix it completed: 79 of 79.**
- **Traffy outage handling (KI-213):** Traffy answered HTTP 502 for ~2.5 h and each failing run held the single worker loop for over 2 minutes. Traffy now makes one attempt per run, and repeatedly failing tasks back off (×2, ×4, ×6; core HII tasks capped at ×2).
- **Result of the full-year history:** 57 of 107 stations now serve a tide-based forecast (44 of 95 before).

### Public repository (D-028)
- The owner made the repository **public**. A full-history scan found no credentials, data or personal email (KI-214). The server IP was removed from the current docs (it remains in 8 old commits; low risk behind the tunnel).
- Docs corrected: SSH is key-only for root, but password authentication is still enabled globally (KI-214). No LICENSE yet (Q10, all rights reserved).
- KI-506 and KI-504 corrected and updated (the tunnel rights are fixed, the old tunnel is deleted, R2 is not enabled).

### Known limits
- Q18 (bot challenge), R2 (Q15b/Q16), the RID gate coordinates, and the license are open on the owner side. See OWNER_ACTIONS.
- **Tests:** 33 passing.

## v0.2.0 — 2026-09-26
**Live at https://flood.autobahn.bot** (alias https://flood.bejranonda.com).

### Citizen-facing
- **Mobile-first UI:**
  - tabs (list / map / Chao Phraya), bottom-sheet station detail, search by district or khlong;
  - share and deep links (`#s=CODE`, `#p=lat,lon`);
  - freeboard in cm first, a map legend, the version badge.
- **Compact statistics strip:** status counts (tap to filter), rising/falling counts, Bangkok 24 h rain, and reporting freshness for the focus area and the whole HII network.
- **24 h outlook:** peak time window (only when a tide model is served) and the chance of reaching the bank as a category.
- **Point check** for places without a gauge: gauges around the pin as an area category (never a level), citizen reports within ~1 km, rain, always-on warnings. No verdict at very low confidence (D-021).
- **Citizen feedback:** verdict, depth band, note and opt-in location. Private; rate-limited; instant hotline box for urgent notes (D-020).
- **Chao Phraya profile** ordered by river km from the mouth (HII centreline).
- **Charts:** day markers, no lines across data gaps.
- **Every station is shown** (111 in focus, 96 placed: 82 from HII, 14 approximate from OSM; 15 unplaced and listed). Misleading values are hidden, always with a note, and there's a whole-country toggle (D-024).

### Data and models
- **Coverage:** the whole Bangkok Metropolitan Region (Samut Sakhon and Nakhon Pathom added). BKK008 placed from HII's map feed (D-023).
- **History:** a one-year hourly backfill from `waterlevel_graph`, batched with `COPY` (D-018). Tides are fitted on up to a year; the backtest covers the last 45 days. C.12 moved from persistence to the tide model.
- **QC:**
  - level > bank + 3 m is flagged (BKK003 stuck at 7.45 m; KI-211);
  - GLF002 values are not MSL (KI-210);
  - `TEST*` gauges are excluded;
  - readings older than 24 h show status "unknown".
- **Optional Cloudflare Workers AI** (SEA-LION v4) triages feedback notes in the worker only, with a budget and a circuit breaker. The site never depends on it (D-022).

### Operations
- **Domain:** main domain flood.autobahn.bot, served by the new tunnel (D-017).
- **Worker robustness:** a total per-request deadline (after a 15-minute hang), known-failing endpoints retried once a day, and the backfill no longer blocks the collectors.
- **Tests:** 29 passing.

### Known limits
- **Domain:** the `autobahn.bot` bot challenge blocks non-browser clients (KI-506).
- **Backups:** no off-site backup yet (KI-504).
- **Near me:** not polder-aware.
- **Unplaced stations:** 15 gauges still without a position (KI-207).

## v0.1.0 — 2026-09-26
The first live MVP:
- collectors (HII, Open-Meteo, Traffy), raw archive, Postgres;
- baseline forecasts (persistence / tide / trend) with conformal bands;
- FastAPI and the Thai map/list;
- Cloudflare Tunnel, and a Thai VPN egress sidecar.
