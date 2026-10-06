# Impact tab: release plans as a comparison grid, honest labels, river coverage and AI help — design

**Date:** 2026-10-06 · **Status:** owner answers in one Grillme round (2026-10-06 ~13:00–13:45 UTC); awaiting spec review
**Decisions to record:** D-110 (this redesign, the owner's "label only" exception to GUIDELINES §6c-6, ONWR layers off by
default, river km + villages as the flood-coverage proxy, four AI helps) · **Issues to record:** KI-318 (ONWR tiles not
clipped to the case), KI-319 (★ and other plans outside the river data, unflagged)
**Release:** v0.34.0

## 0. Why (the owner's request and what the live tab showed)

Owner, with two screenshots of `/impact` (desktop plan sheet and phone case view): improve the impact tab's design so it
is smart and consistent with the other tabs (it is "massive with text"); validate the flood areas ("some are far away
from river, is it correct?"); ONWR's goals — release scenarios for the next 6–7 days, each turned into water level and
flood coverage; users are government, authorities and engineers who control releases; AI may assist.

Evidence gathered before any question (2026-10-06 12:45–13:05 UTC, live state and API, read-only):

| Finding | Evidence |
|---|---|
| The hexagons are **ONWR's land warning** (`flood-warn`, on by default), not a result of any plan | `collector_state.onwr_flood_kaeng_krachan`, fetched 12:03 UTC |
| **Not clipped:** whole zoom-10 tiles are kept — 118 of 134 warning cells, 148 of 226 +1-day cells lie outside the case box; 111 warning cells sit around Ratchaburi town (Mae Klong), 30–42 km from the Phetchaburi River; +1-day cells up to 56 km | same, distance to the river line per cell |
| Inside Phetchaburi: 4 warning cells at the city next to the river, 19 cells 6–15 km east in the coastal lowland (Hat Chao Samran); ONWR's observed-flood layer has nothing in Phetchaburi (3 polygons, all near Ratchaburi); our five gauges 1.7–5.0 m below their banks | same; `/api/impact/case/kaeng-krachan` |
| KNOWLEDGE §28 counts ONWR's +1-day cells as "over the case area" — most were outside it | as above |
| **The ★ plan is outside the river data:** 21.5 ล้าน ลบ.ม./วัน for 7 days (≈ 249 m³/s) puts 256 / 192 / 182 m³/s through B.18 / B.10 / B.16; the ratings were fitted on ≤ 143 / 86 / 73 m³/s. `daily_downstream` marks those days `outside: true` (B.18 7 days, B.10 6, B.16/B.15/PCH001 5) but the ★ rule and the page ignore it; two of the other four shown plans are outside too | `/api/impact/case/kaeng-krachan/scenarios`, 13:05 UTC |
| The downstream gains were learned while เขื่อนเพชร's canals absorbed release changes (KNOWLEDGE §25, §27; D-099); the only comparable release, Aug 2018 (up to 24.36 on 21 Aug), overflowed the spillway and the province warned five riverside districts (news reports); HII has no river levels for 2018 | KNOWLEDGE §25, §28; [ThaiPBS](https://www.thaipbs.or.th/news/content/273780), [Khaosod](https://www.khaosod.co.th/special-stories/news_1415217) |
| Text: the plan sheet opens with a **309-character paragraph** (GUIDELINES §6c-9: none over 160); the tab check measures the case view only (first screen 972 characters) | `scratchpad walk.py` at 390 / 1366 px |
| "เหมาะกับ ท่วมรวมน้อยสุด / ไม่มีจุดใดล้นหนัก" shown on 9.5 although no plan overtops anywhere | scenarios JSON: `overtop_sum` 0 for all plans |
| Desktop: opening the case leaves the map on Bangkok; ONWR's box sits over Bangkok; two layer boxes on the map | 1366 px screenshot |
| OpenStreetMap near the river: Nominatim (zoom 14) returns a **village and อำเภอ for 3/3 points**, a ตำบล-level name for 1/3; Overpass returns **no admin_level 8 (ตำบล) boundary** (levels 2, 4, 6 only; two of three queries 504) | live calls 13:30 UTC, project User-Agent |
| River length per gauge reach (pieces nearest each gauge within 10 km, D-105): B.18 62.4, B.10 45.8, B.15 21.0, B.16 11.4, PCH001 8.2 km (149 km of the 297 km line) | case state `river_reaches` |

## 1. Owner decisions (Grillme, 2026-10-06)

| Question | Answer |
|---|---|
| Plans above the tested range (★ 21.5 ≈ 249 m³/s vs 143 at B.18) | **Label only:** keep today's ★ rule and every number; add a visible "นอกช่วงข้อมูล" label (recommended was "show, river unjudged"). Recorded as an owner exception to GUIDELINES §6c-6 for this tab |
| Has ONWR seen the tab? | **Not yet** — this redesign prepares the first ONWR demo |
| Where will ONWR first see it? | **Their own desktops**, self-serve, without the owner beside them |
| ONWR's layers | **Off by default, inside the app's one layer box** as a group "สทนช. · ไม่ขึ้นกับแผนระบาย"; clipped to the case |
| Flood coverage until ONWR maps / a LiDAR DEM | **River km + places**: km of river near or over its bank per plan and day, and the places along those stretches — as OSM has no ตำบล here: **villages + อำเภอ** (owner confirmed) |
| AI help | **All four:** executive brief (plain bullets, copy), compare two plans, type a plan in Thai, keep today's ✨ |
| First-screen layout | **B — comparison grid** (one row per plan, a 7-day colour strip) |
| Which plans | **Picks + release ladder** (★, today, the engine's best-per-goal plans, a collapsed ladder of constant releases, own plans) |
| Brief style | **Plain bullets** |
| Sections 1–4 of the design | approved as presented |

## 2. Fixes (ship in the same release)

1. **ONWR features clipped to the case box.** `collectors.onwr_layers(bbox)` keeps a feature only when its first ring
   intersects the box (any vertex inside, or the box's centre inside the ring); the API filters a stored copy the same way
   when serving (`impact.clip_onwr(onwr, bbox)`), so the fix shows before the next 3-hourly fetch. KI-318; KNOWLEDGE §28
   corrected.
2. **ONWR layers off by default, in the app's one layer box.** `impact.js` no longer adds its own Leaflet control; it
   appends a group block to the app's existing box (`details.legend.layers`, built by `app.js`) titled
   "สทนช. · ไม่ขึ้นกับแผนระบาย": rows in the box's markup (checkbox, swatch by class, label, count with ONWR's update time),
   present only while a case is open, every item unchecked on open, removed on leaving the case or logging out. The
   box's own change handler ignores rows without `data-layer`, so **`app.js` is unchanged**; `impact.js` listens to its
   own rows. The group's ⓘ says "พื้นที่ของ สทนช. ไม่ใช่ผลของแผนระบาย · ที่มา: สทนช.".
3. **Outside-the-data label.** The engine already sets `outside` per gauge and day (`flow > rating.qmax`, for the city
   gauges the flow of their `rating_from` gauge). `scenarios.compare` now carries it to the plan: `outside_detail`
   (per gauge: days, the plan's highest flow, the rating's `qmax`) and `outside_any`. The ★ rule is unchanged (owner).
   The label appears on the ★ row, every plan row, the plan sheet and the brief: "⚠ นอกช่วงข้อมูล" + ⓘ
   "B.18 256 ลบ.ม./วิ (เคยวัดสูงสุด 143) วันที่ 1–7 · … · แบบจำลองท้ายน้ำเรียนจากช่วงที่เขื่อนเพชรรับการเปลี่ยนแปลงไว้;
   ปี 2561 ระบายสูงสุด 24.4 ล้าน ลบ.ม./วัน ไม่มีข้อมูลระดับแม่น้ำปีนั้น". KI-319.
4. **A "best for" only where plans differ.** `best_for` awards an effect only when the feasible plans' values differ by
   more than a tolerance (margins 0.05 m, storage 1 ล้าน ลบ.ม., ramp 0.1, overtopping > 0 in some plan, under-curve day
   differs); otherwise the effect has no best and no badge. "ไม่มีจุดใดล้นหนัก" is renamed **"ห่างตลิ่งมากสุด"** (what
   it measures) in `scenarios.EFFECT_TH` and `impact.js`.
5. **The map follows the case on desktop.** Opening a case fits the map to its river and gauges (as a dam row pans the map);
   phones keep their tab.

## 3. Case view: the comparison grid (desktop first, also 390 px)

```
เขื่อนแก่งกระจาน → แม่น้ำเพชรบุรี
[● อ่าง 725 102%] [+127 เหนือเส้นบน] [ระบาย 10.6] [เข้า 10.3]      chips as today (tap → dam sheet)
ล้าน ลบ.ม.(/วัน) · ชป. 6 ต.ค. · ⓘ

แผนระบาย 7 วัน   วันที่ [1] 2 3 4 5 6 7   อ่าง  ห่างตลิ่ง  กม.
★ 21.5 คงที่ ⚠       ▒ ▒ ▒ ▒ ▒ ▒ ▒       639   0.18      0   ›
  10.6 วันนี้         ■ ■ ■ ■ ■ ■ ■       715   2.11      0   ›
  9.5 คงที่ 🌊        ■ ■ ■ ■ ■ ■ ■       723   2.13      0   ›
  22→2 ทยอย 🏞️ ⚠     ▒ ▒ ▒ ▒ ■ ■ ■       705   0.10      0   ›
  6→12 สองช่วง 💧 ⚠   ■ ■ ■ ▒ ▒ ▒ ▒       723   1.85      0   ›
▸ ระบายคงที่ทุกระดับ (0–24)
■ รับน้ำได้ ■ ใกล้ตลิ่ง ■ เกินตลิ่ง ▒ นอกช่วงข้อมูล ⓘ
★ ตามเกณฑ์: ลดอ่างได้มากสุด ทุกจุดห่างตลิ่งเกินความคลาดเคลื่อน ⓘ
[➕ ลองแผนเอง] [✨ AI ▾]
แม่น้ำตอนนี้: B.18 2.11 → B.10 5.05 → B.16 3.02 → เมือง 2.13 (strip as today)
▸ ℹ️ วิธีการ ข้อมูล และข้อจำกัด (as today)
```

- **Rows (one table, `<table>` for screen readers):** ★ first, then today's plan, then the engine's picks (one best plan
  per goal, merged; a goal icon per goal with `title`/`aria-label` naming it: 🏙️ ปกป้องตัวเมือง · 🌊 ห่างตลิ่งมากสุด ·
  📏 ท่วมรวมน้อยสุด · 🏞️ ความปลอดภัยเขื่อน · 📉 กลับใต้เส้นควบคุมเร็ว · 💧 เก็บน้ำไว้ใช้ · ⏱ เตือนล่วงหน้าได้), then the
  user's own plans (kept for the session, newest first, at most 3). Labels are short: "21.5 คงที่", "10.6 วันนี้",
  "22→2 ทยอย", "6→12 สองช่วง", "กำหนดเอง"; the full words live in the sheet.
- **Ladder:** constant releases every 2.0 ล้าน ลบ.ม./วัน from 0 to the cap (0…24, 13 rows), collapsed under
  "▸ ระบายคงที่ทุกระดับ (0–24)", same columns. Its hatching shows where our river data end.
- **Day cells (computed once on the server, `plan.days[d]`):** for each gauge with a margin that day: `over` if
  margin < 0, `near` if margin < that day's tested error (`margin_req[code][d]`), else `ok`; the cell is the worst gauge
  (`over` > `near` > `ok`; `none` when no gauge has a margin). `outside` = any gauge outside the data that day →
  hatched over the colour. Colours are the app's (`--critical`, `--warning`, `--normal`, `--unknown`); colour is never
  the only signal (the hatch, ⚠ and the cell's `title` "วันที่ 3: ใกล้ตลิ่งที่ B.16 (0.20 ม., คลาดเคลื่อน ±0.26)").
- **Columns:** อ่าง = storage on day 7 (ล้าน ลบ.ม.); ห่างตลิ่ง = the lowest margin over gauges and days (m, red when
  < 0); กม. = the most km at risk on any day (§4).
- **Interaction, desktop:** a row click selects the row (highlight) and colours the river on the map for that plan and the
  selected day (default: its worst day); `›` (or Enter) opens the plan sheet; a click on a day number in the header selects
  that day for the map and highlights the column. The map legend says the plan and day in one line. **Phone:** a row tap
  opens the sheet (as today); the day header still selects the day; the km column moves under the plan label if the row
  does not fit 390 px.
- **Text budget:** no paragraph over 160 characters in the case view, the plan sheets, the custom-plan sheet and the brief;
  the ★ "why" is one short line plus ⓘ (the full rule and reason). The ℹ️ sheets (replay, river table, matrix, method, data
  request) are the on-demand method prose (GUIDELINES §6c-9): measured and reported by the check, not trimmed in this
  release (refined during planning, 2026-10-06).
- **Unchanged:** the national dams list, the login, the chips, the river strip, the ℹ️ collapsible and its sheets
  (replay, river table, matrix, method, data request).

## 4. Plan sheet and flood coverage

**Sheet (the app's `#sheet`; floating on desktop, bottom sheet on phones):**
1. Title: the plan in words + ★ / ⚠ badges; one subtitle line ≤ 100 characters ("★ ตามเกณฑ์" or the goals it is best
   for) + ⓘ with the full reason.
2. Day chips 1–7 (as today) → the map day.
3. Reservoir: the existing chart, then a compact table วัน · ระบาย · อ่าง (ช่วง) · เทียบเส้นบน.
4. River: **a grid of 5 gauges × 7 days**, each cell coloured by its status with the margin in m (two decimals), hatched
   where that gauge is outside the data; header "ห่างตลิ่ง (ม.) · ตลิ่งของหน่วยงานผู้วัด". Replaces today's wide table's
   last column and the hidden per-gauge table.
5. Coverage line: "แม่น้ำใกล้/เกินตลิ่ง วันที่ 3–7 ราว 11 กม. (B.16) · หมู่บ้านริมแม่น้ำช่วงนี้: บ้าน…, บ้าน… (อ.บ้านลาด)"
   or "ไม่มีช่วงใดใกล้ตลิ่งใน 7 วัน".
6. Outside line (when any): "⚠ นอกช่วงข้อมูล: B.18 256 ลบ.ม./วิ (เคยวัดสูงสุด 143) วันที่ 1–7 · …" + ⓘ (§2.3).
7. Buttons: ✨ เทียบกับแผน ★ (on the ★ sheet: เทียบกับวันนี้); 🗺️ ดูบนแผนที่ (phones).
8. The units and assumptions list moves behind one ⓘ.

**Flood coverage proxy (river only; D-019 and D-105 stand — no water drawn on land):**
- **km at risk:** `impact.river_reaches` already assigns each piece of the river line to its nearest gauge within 10 km;
  the case state gains `reach_km` {code: km} (haversine along each piece). For plan p and day d,
  `km = Σ reach_km[code]` over gauges whose status that day is `near` or `over`; the plan's `km_max` and the days it
  holds. The ⓘ says it is coarse: one gauge speaks for its whole stretch; stretches more than 10 km from every gauge are
  never counted.
- **Villages:** `research/2026-10-06_kk_reach_places.py` samples the river line every ~1 km inside the reaches
  (~150 points), calls Nominatim reverse (zoom 14, Thai, project User-Agent, one call per 1.5 s, results kept), takes
  `village` (else `hamlet`, `municipality`) and `county` (อำเภอ), groups them per reach code in river order, removes
  duplicates and writes `src/floodwatch/data/kk_reach_places.json` (+ a `.log` with the counts). It is rerun by hand when
  the river line or the gauges change; nothing calls Nominatim at request time. Credit on the sheet and map:
  "หมู่บ้าน: © OpenStreetMap contributors". If fewer than 80 % of samples return a village, the file keeps อำเภอ only
  for that reach and the log says so.
- **Map:** an at-risk stretch's tooltip lists its villages (at most 6, "และอีก N").

## 5. AI help (GLM only, on tap only, never deciding; D-022, D-068)

| Place | Feature | Rules first | GLM | Fallback |
|---|---|---|---|---|
| Case view `✨ AI ▾` | **สรุปให้ฟังง่าย ๆ** | today's `explain.scenarios` | retells (today's gist) | rule story |
| same menu | **สรุปเสนอผู้บริหาร** | `explain.brief(cmp)` → 5–7 bullets: สถานการณ์ตอนนี้ · ★ ตามเกณฑ์ (plan, อ่างวันที่ 7, ห่างตลิ่งต่ำสุด, กม.) · two alternatives (today's + the best-differing pick) · ⚠ นอกช่วงข้อมูล · ข้อจำกัดท้ายน้ำ · ข้อมูล ณ | may tidy each bullet; checked one by one (no new number, place, verdict or alarm word; ≤ 160 chars) | that bullet's rule text |
| Plan sheet | **✨ เทียบกับแผน ★** (★ sheet: กับวันนี้) | `explain.compare(cmp, a, b)` → difference lines: อ่างวันที่ 7, ห่างตลิ่งต่ำสุด, กม., เปลี่ยนต่อวัน, นอกช่วงข้อมูล | retells under the same check | rule lines |
| ลองแผนเอง sheet | **พิมพ์แผนเป็นภาษาไทย** | `impact_plan_parse.parse(text, today, cap)`: numbers + day counts ("ระบาย 15 สามวันแล้วลดเหลือ 10", "คงเดิม", "ทยอยลดจาก 20 เป็น 8") | only when the rules cannot read it: JSON `{"release": [7 numbers]}` | "อ่านแผนนี้ไม่ได้ กรอกตัวเลขเอง" |

- Endpoints (login required): `GET /api/impact/case/{id}/explain?q=simple|brief` (+ `part=gist`),
  `GET /api/impact/case/{id}/explain?q=compare&a=<7 numbers>&b=<7 numbers>` (the two plans by their release values, so
  an hourly rebuild between loading the grid and tapping ✨ cannot swap plans), `POST /api/impact/case/{id}/parse` with
  `{"text": ≤ 200 chars}` → `{"release": [7], "by": "rules"|"ai"}` or 422. The typed text is never logged or stored
  (POST body; not in the access log); 30 parses per 15 min per client (the login limiter's keying).
- The brief has a copy button (`navigator.clipboard.writeText`, with a select-all fallback); its last line names the data
  time and "ไม่ใช่ประกาศทางการ".
- A parsed plan only fills the seven boxes; nothing is computed until "คำนวณ". Values are clipped to 0…cap and must be 7.
- `AI_EXPLAIN=0`: the menu gives the rule texts; the parser runs rules only.

## 6. Data contract changes (`scenarios.compare`)

Added to every plan in `plans` (and the ladder): `roles` ⊆ {star, today, pick, custom, ladder} (a list: a pick may also be a rung),
`label` (short), `days` [7 × {status, outside, km, codes}], `km_max`, `km_days`, `outside_any`, `outside_detail`
[{code, days, flow_max, qmax}]. Top level: `ladder` [plan ids], `picks` [plan ids], `reach_km`, `places`
{code: [{village, amphoe}]}, `best_for` (suppressed per §2.4). `release=` now takes up to three custom plans separated
by `;` (7 numbers each, 0…200), so the session's own plans stay rows after a reload of the comparison. Unchanged:
`optimal`, `margin_req`, `downstream`. Payload: measured in a test, target < 150 kB (today 34 kB for 5 plans; ladder
rungs drop the per-gauge level arrays and keep margins, flows and flags).

## 7. Tests and validation

- **Unit (written first):** ONWR clipping (feature inside / outside / crossing the box); `clip_onwr` on a stored copy;
  `outside_detail` from downstream rows; the day-cell rule (over/near/ok/none, hatched, worst gauge); km per day from
  `reach_km`; ladder rungs (0…cap step 2, present even when equal to a pick); `best_for` suppression with tolerances and
  the renamed effect; `explain.brief` / `explain.compare` (every number in the text exists in the comparison); the rule
  parser on 12 Thai phrasings and its refusals; API: login required, 422 on bad input, parse never logged.
- **Browser (`scripts/impact_tab_check.py`, 390 and 1366 px):** grid rows and their day cells; hatched cells for the ★;
  the ladder toggles; a day-header click changes the map legend's day; a row click colours the river (desktop); ONWR group
  in the app's box, unchecked on open, removed on leaving the case; the map fits the case on desktop; **no paragraph over
  160 characters in the view, the plan and custom sheets and the brief** (ℹ️ sheets reported only); ✨ menu (both items),
  compare in a sheet, a parsed plan fills the boxes;
  logout clears everything. Public page: `scripts/ux_consistency.py` (C1–C20) as the release's regression check (`app.js`
  and `index.html` unchanged; the impact assets load only on `/impact`).
- **As a first-time ONWR engineer on a desktop:** answer "what happens if we release 15 for 7 days?" in ≤ 3 actions with no
  paragraph to read; screenshots reviewed at 390 and 1366 px.
- **Suite:** `docker compose build worker` → `pytest -q` (with the research mount) → deploy → `/api/health` → the checks
  above against production.

## 8. Docs and release

D-110 (this design and the owner's answers, incl. the §6c-6 exception), KI-318, KI-319; KNOWLEDGE §28 corrected + reach
lengths, OSM coverage, 2018 news; GUIDELINES §6c-11 (a flag the engine computes must reach the decision and the screen;
clip tiled layers to the area; another agency's layer off by default where it can be misread; measure sheets too; an owner
exception to a rule is written into the rule); APPROACH §19.27; MODELS §11 (outside-the-data note); SOURCES (Nominatim
village coverage, Overpass without ตำบล, ONWR clipping); ARCHITECTURE (endpoints, data file, the ONWR group in the app's
layer box); README;
UX_VALIDATION; `docs/plan/impact-kaeng-krachan.md`; CHANGELOG; HANDOFF §3x. v0.34.0: `__version__`, CHANGELOG, tag,
GitHub release; validation after the release.

## 9. Not in scope

A land flood area (D-105: waits for ONWR's maps by release level or a LiDAR DEM — OWNER_ACTIONS FLOODMAP, DEM); a new
river model or a change to the ★ rule; more cases than Kaeng Krachan; the national dams list; ตำบล names (OSM has no
boundaries here; an official ADM3 dataset would need a licence check first).

## 10. Risks

- **The ★ stays outside the data by the owner's choice.** The label must be impossible to miss: ⚠ on the row, hatched
  cells, the sheet's outside line and the brief's bullet. If ONWR reads the ★ as advice anyway, revisit D-110.
- Village names are points near the river, not the people at risk; the wording says "ริมแม่น้ำช่วงนี้", never "น้ำท่วม".
- The km figure is coarse (B.18 speaks for 62 km); the ⓘ says so.
- The ONWR group lives inside a box `app.js` builds: if `app.js` ever renames `.legend.layers`, the group must fail
  visibly — the browser check asserts the group is inside the box; `app.js` itself does not change in this release.
