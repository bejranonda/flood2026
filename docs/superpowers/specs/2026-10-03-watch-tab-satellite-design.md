# จับตา tab, satellite in the sheet and on the map, every gauge on the map — design

**Date:** 2026-10-03 · **Status:** approved in chat by the owner (Grillme rounds 1–3), awaiting spec review
**Decisions to record:** D-077 (จับตา tab and track records), D-078 (satellite sheet line and map toggle), D-079 (map shows every gauge with data; D-037 superseded)

## 1. Why

Owner, 2026-10-03: "I need another tab to have the list of potential risks according to the water level in next 24 or
48 hr … link to the stations or areas … inform as risk that come together with the confidential like percent or some
narrative", "We have now the satellite data. Can we apply the info from satellite for using in the app?", and (map)
"Do we still need 'แสดงสถานีที่ยังคาดการณ์ไม่ได้ (118)' in the map, should we integrate in the map".

Who and what for: anyone in Thailand who wants to know **where water may become a problem in the next 24–48 h**, as a
nationwide overview first (owner's choice), narrowed by ภาค/จังหวัด when wanted.

## 2. Evidence (live database, 2026-10-03 ~18:30 UTC; scripts in the session scratchpad, to be kept under `research/`)

| Check | Result |
|---|---|
| "Reaches the bank within 24 h" (`outlook24.bank_chance`, one archived run per gauge per 6 h, 26 Sep – 1 Oct, gauges below bank at issue) | `<5%` 4,803 runs → 0.4 % · `5–25%` 345 → 3.5 % · `25–50%` 128 → **11.7 %** · `>50%` 132 → **61.4 %**; 48 h: 0.6 / 3.6 / 14.0 / 61.3 % |
| Share of the 125 real bank-reaches (24 h) flagged | `>50%` alone 65 % · with `25–50%` 77 % · with `5–25%` 86 % |
| Upstream gauge (learned, lag 3–48 h, 394 pairs) rose ≥ 30 cm in 24 h → gauge rises ≥ 10 cm within lag + 6 h (since 1 Aug, every 6 h) | **69 %** of 10,153 (24 % without the signal) |
| 24 h forecast median rise ≥ 20 cm (archived runs) → observed rise ≥ 10 cm after 24 h | **72 %** of 393 (≥ 20 cm: 50 %) |
| Satellite (GISTDA, images 28 Sep – 2 Oct) ≥ 100 rai flooded within 5 km, outside กทม./ปริมณฑล | critical gauges 38 % · warning 35 % · watch 26 % · normal 8 %; no cell in Bangkok |
| Map checkbox "แสดงสถานีที่ยังคาดการณ์ไม่ได้" hides | 117 gauges: 65 in Bangkok (63 BMA), **3 critical + 3 warning**, 31 silent > 24 h |
| Forecast confidence today | ~960 of 1,040 rows "low" |

Conclusions: the model's bank-chance bands **rank** risk well but are about 3× too high in the middle, so the app shows
the measured track record, not the model's percent. All three forecast-based groups have a usable record (6–7 in 10).
The records rest on one week and one flood (forecast archive starts 2026-09-26): stated in the ⓘ and in KNOWLEDGE.

## 3. The tab "⚠️ จับตา"

- Fourth tab, after "〰️ แม่น้ำ". "เฝ้าระวัง" was rejected: it is already the yellow status (70–90 % of bank).
  Not "เตือนภัย": we are not the official warning authority.
- Top: the shared where-row `ภาค ▾ · จังหวัด ▾` (D-076). The tab **opens at ทั้งประเทศ** each time; a choice made
  here filters this tab only and does not change the list's or river tab's choice.
- One header line: `24–48 ชม. ข้างหน้า · อัปเดต HH:MM ⓘ`. ⓘ: not an official warning (follow ปภ./กรมชลประทาน/
  local announcements), sources, what "6 ใน 10" means.
- Six groups in this fixed order; an empty group is not drawn; nothing at all → `ไม่พบความเสี่ยงใน <area> ✓`.
- **A gauge appears once**, in the first group that applies (1 → 4). Area groups (5, 6) are about provinces.
- Stale gauges (`stale`) are not listed in 1–4; a group adds `· ข้อมูลเก่า n` when it left some out.
- BMA gauges keep their own yardstick (D-038): "critical" is the status the app already shows.

| # | Group | Rule (all from `/api/stations` fields unless noted) | Row (one line at 390 px) | Confidence |
|---|---|---|---|---|
| 1 | 🔴 ล้นตลิ่งแล้ว | `status == "critical"` | per province: `ปราจีนบุรี 6 ›`, tap expands its gauges (name · `เกินตลิ่ง N ซม.` · arrow of `change24`) | measured: no chip |
| 2 | 🟠 อาจถึงตลิ่ง | below bank and `bank_chance24` or `bank_chance48` in `>50%`/`25–50%` | `ชัยนาท · <name> · ต่ำกว่าตลิ่ง 12 ซม. · 24 ชม.` | chip per band |
| 3 | 🟠 น้ำเหนือกำลังมา | status watch or warning, and a learned upstream gauge (`upstream`, lag 3–48 h, fresh) rose ≥ 30 cm in its last 24 h | `<province> · <name> · น้ำจาก <upstream name> ราว N ชม.` | chip |
| 4 | 🟡 น้ำขึ้นเร็ว | `change24.level == "strong_rise"` | `<province> · <name> · +N ซม. ใน 24 ชม.` | chip |
| 5 | 🌧 ฝนหนักคาดการณ์ | forecast ≥ 35.1 mm in the next 24 h (`SUMMARY_RAIN_MIN_MM`) at a forecast point; province = the provinces of the gauges that point serves (as `point_regions`) | `<province> ราว N มม.` | chip only when its record has ≥ 30 cases |
| 6 | 🛰 ดาวเทียมเห็นน้ำท่วม | `sat_flood` per province; group header carries the image dates | `นครสวรรค์ 483,000 ไร่ ›` | observed: no chip |

Order inside a group: 1 by count, 2 by chance band then cm to bank, 3 by upstream rise, 4 by rise, 5 by mm, 6 by rai.
Long groups show the first 5 rows and `+ อีก N ›` (expands).

**Track-record chip** `6 ใน 10`: the same words as the existing ⓘ "ในอดีตเป็นแบบนี้ต่อ 7 ใน 10 ครั้ง". Its ⓘ:
`30 วันที่ผ่านมา เมื่อเราคาดแบบนี้ เกิดจริง 6 ใน 10 ครั้ง (N ครั้ง)`. Rounded to the nearest tenth; `< 1 ใน 10` below
0.05. Hidden when the record has fewer than 30 cases.

**Links:** a gauge row opens the existing station sheet; a province row in group 1 expands inline; a rain row opens
"📋 รายการ" filtered to that province; a satellite row opens "🗺️ แผนที่" with the satellite layer on, fitted to that
province's cells.

### Track records (`risk_record`)

Computed daily in the forecaster container (task `risk_record`, 24 h, after `forecast`), stored in `collector_state`
key `risk_record`: `{group: {band?: {"n", "hit"}}, "window_days": 30, "computed_at"}`. Definitions (same as §2):

- `bank_24` / `bank_48` per band: archived runs (one per gauge per 6 h, at least 24/48 h old), gauge below bank at issue
  → any reading ≥ bank within 24/48 h. Needs readings on ≥ a third of the hours.
- `upstream`: every 6 h, pairs (gauge, learned upstream, lag 3–48 h) where the upstream rose ≥ 30 cm in 24 h → gauge
  rises ≥ 10 cm within lag + 6 h.
- `fast_rise`: archived runs with 24 h median rise ≥ 20 cm → observed rise ≥ 10 cm at +24 h (± 30 min).
- `rain`: forecast points with day-1 hindcast ≥ 35.1 mm/24 h → a rain gauge within the point's cell measured ≥ 35.1 mm
  in that day. Shown only with n ≥ 30.

## 4. Satellite

- **Station sheet line** (any region; satellite is "seen only", D-071): when ≥ 100 rai were seen flooded within 5 km:
  `🛰 ดาวเทียมเห็นน้ำท่วมรอบสถานี ราว 14,000 ไร่ · ภาพ 28 ก.ย.–2 ต.ค. ⓘ`. ⓘ: GISTDA radar, 7-day composite, cannot see
  under buildings or in cities, never means "not flooded". Precomputed per gauge when a layer is downloaded
  (`collector_state` key `sat_near`: `{code: rai}` + image dates); the API reads that map.
- **Province totals** for group 6: precomputed at the same time (`sat_province`: `{province: rai}`).
- **Map toggle** `🛰 ดาวเทียม` (top-left, where the checkbox was), off by default; on when coming from group 6.
  `/api/satellite?bbox=w,s,e,n&z=<zoom>` returns observed cells (D-019: observed, never interpolated): at zoom < 11
  merged into a grid (0.02° below 9, 0.005° 9–10) with summed area; at ≥ 11 the cells; at most ~5,000 items per
  response, cached by bbox tile. Drawn on canvas below the stations and the Traffy cells, one colour with opacity from
  flooded share. Legend line while on: `▒ ดาวเทียมเห็นน้ำท่วม (ภาพ 28 ก.ย.–2 ต.ค.)`.

## 5. Map shows every gauge with data (supersedes D-037)

- The checkbox "แสดงสถานีที่ยังคาดการณ์ไม่ได้" goes. Every gauge with a reading in the last 24 h is drawn in its status
  colour. **No forecast** (`trend12` not rising/falling/steady) → **hollow ring** in the status colour; status unknown
  stays grey. Legend: `○ ยังไม่มีพยากรณ์` and a muted line `ไม่แสดง N สถานีที่ไม่ส่งข้อมูลเกิน 24 ชม.`
- Gauges silent > 24 h stay off the map (as in the list's closed group, D-036).
- The list chip "📈 เฉพาะที่คาดการณ์ได้" goes too (owner: remove).

## 6. API and code

- `src/floodwatch/risks.py` (new, pure): `build(stations, rain_points, sat_province, records, now) -> {"groups": [...],
  "generated"}`, plus `chance_band(path, bank, hours)` moved/reused from `forecast.outlook24` (24 and 48 h).
- `/api/stations` rows gain `bank_chance24`, `bank_chance48` (from the latest run's path) and `sat_near_rai`.
- `/api/risks` (cached 5 min, all of Thailand; the client filters by region/province like the list).
- `/api/satellite` as above. `/api/point` unchanged.
- Forecaster: task `risk_record`; GISTDA download also writes `sat_near` and `sat_province`.
- Web: tab button, `renderWatch()`, map ring markers, satellite toggle, sheet line; `?v=` bumped.
- Version **v0.21.0**.

## 7. Tests and validation

- Unit tests first (red, then green): every group rule and the dedupe order; chance band 24/48 h; record definitions on
  small synthetic series; satellite near/province aggregation and the grid merge; ring marker rule (wording tests in
  `test_wording.py`: tab name, chip format, no "เฝ้าระวัง" as the tab name, no "เตือนภัย").
- Live consistency check **C15** in `scripts/ux_consistency.py`: each gauge in groups 1–4 matches `/api/stations`
  (status, cm to bank, `change24`), counts per province add up, a gauge appears once; **C16**: the map draws every
  gauge with data < 24 h (none hidden for lack of a forecast).
- Visitor checks at 390 px (Playwright screenshots): four tabs fit on one line; every row is one line; tap targets open
  the right sheet / province / map; chip number equals its ⓘ; satellite layer response < 300 kB and drawn < 1 s.
- Docs: CHANGELOG, HANDOFF, README, KNOWLEDGE (track records, satellite vs gauges), KNOWN_ISSUES (map hid red gauges,
  model bands 3× too high in the middle), DECISIONS D-077–D-079, APPROACH (risk groups, records), GUIDELINES (risk
  wording), SOURCES (GISTDA use), UX_VALIDATION.

## 8. Not in scope

Push notifications or alerts; an "น้ำกำลังลด" group (owner did not choose it); the satellite province trend over time;
internal satellite-vs-bank QC; WeatherNext (Q44).
