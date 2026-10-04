# Changelog

All notable changes to BKK FloodWatch 2026. Versions follow `floodwatch.__version__`, which the UI shows (D-025).

## v0.25.0 — 2026-10-04
- **A better forecast, tested honestly (owner: "Continue to improve the model forecasting performance … not fake the result
  and error or uncertainty").** `star` now also reads how far the level sits from its 7- and 30-day means and its 1/3/72 h
  changes. Chosen on one sample of gauges and confirmed on another it never saw: the served error against "no change" went
  from −6.6/−5.5/−5.3 % to −8.3/−8.5/−9.4 % at 24/48/72 h, and 67/70/69 gauges (was 51/44/49) keep a ≥ 10 % gain; at
  72 h 21 gauges end up worse than "no change" (was 10) — stated, not hidden (D-092). Tried and not kept: averaging
  methods, a stricter selection rule, trend-dependent and shorter-window ranges (narrower but less honest). Google Flood
  Hub as an input gains ~1 point at 72 h only (Q55); WeatherNext awaits a BigQuery billing step (Q53). The served 24 h
  ranges hold as stated; at 72 h they are too confident in a falling river (KI-287, Q54). MODELS.md §5d, §9a.
- **The ticker (owner: "ควรจับตาพื้นที่กรุงเทพฯ … but no Bangkok gauge rising"; "use symbols … to see the separation";
  "simple, attractive and lovely Thai … only GLM").** "อาจถึงตลิ่ง" names only provinces where the water is rising (the
  จับตา tab shows น้ำยังขึ้น / ทรงตัวหรือลดลง pills for it too); new items for Bangkok, the Chao Phraya Dam release and
  the flow at Nakhon Sawan (with the change since yesterday) and counts against yesterday; the ticker is short items
  with a symbol and a ◆ divider, a list when tapped. GLM rewrites each item in the voice of the ✨ card; each item is
  checked against its own fact and falls back alone (9.3/11 items accepted in tests, 11/11 live) (D-094, KI-286).
- **✨ ให้ AI สรุปให้ฟังง่าย ๆ on station sheets and on the จับตา tab (owner request).** A station's summary says what
  its water is doing, the next 24–72 h and the rain measured nearby and forecast; the จับตา summary gives the overview
  for the tab's region/province with the most critical gauges first. Retelling shown for 9/9 regions and 11/13 test
  stations; new checks for every card: "กำลังจะถึงตลิ่ง" where the facts say "อาจถึง", a question to the reader;
  polite particles are dropped (D-095).
- **Robustness.** The collector's schema step gives up within 5 s when a lock is held (a research run took the site
  down ~12 min, KI-284); research uses read-only connections and AI calls that never touch the visitors' AI breaker
  (KI-285); a lean chip says "น่าจะเพิ่มขึ้น" (one verb with the solid chip).

## v0.24.0 — 2026-10-04
- **"? ไม่แน่ชัด" rows lean by the measured trend, with their own track record (owner: "Why many stations say ? ไม่แน่ชัด, even we
  can see the trend from graphs" → "Lean the rows by the trend").** 63 / 79 / 83 % of the 24 / 48 / 72 h rows were "?": the model
  ("no change" at 355 gauges, or a likely range across zero) cannot say *how much*. On those rows the measured direction held
  70–72 % (research/2026-10-04_unsure_rows.py); the lean rule (the trend groups' measured pace: 24 h, cut back when the last
  6 h stopped) held 75.5 / 75.4 / 76.4 % over 30 days (n 4,736 / 4,060 / 2,661; see the agreement rule below). A "?" row now reads "↗ น่าจะขึ้น" or
  "↘ น่าจะลดลง" in a dashed chip with "8 ใน 10"; the numbers stay the model's range, the band the chart draws; the ⓘ says
  where each part comes from. No measured pace (or the last 6 h disagree, e.g. pumped canals) → still "?". The stories say "น่าจะเพิ่มขึ้นตามแนวโน้มที่วัดได้ แต่ยังไม่แน่ชัดว่าเท่าไร" (D-091).
- **The past comes before the future (owner: "move 24 ชม. ที่ผ่านมา to locate before 24 hr prediction … the last and then the
  future").** In list cards, sheets and pin panels the measured line now leads the forecast rows.
- **A row leans only where the chart's dashed line goes the same way (owner, T.13 / BKK017: "I follow the dash trendline in
  chart … How we can calculate differently between description and chart?").** The first rule (measured pace alone) put
  "↘ น่าจะลดลง" beside a flat line and beside "0 ถึง +8 ซม." with a rising line. Now the model median must also move ≥ 3 cm
  that way: right 82.9 / 80.3 / 82.3 % at 24 / 48 / 72 h (was ~75 %), leaning 19–22 % of "?" rows; word, line and measured
  trend always agree (KI-282). Live check C20.
- Live check C2/C3 read a leaning chip as "not proven" (its range may cross zero by design).
- Ticker check: province names that are everyday words (เลย, แพร่, ตาก …) count as places only after จ./จังหวัด (two good
  retellings were rejected as "new place").
- **Google WeatherNext 3 integration verified (owner: "I try to integrate google weathernext 3 into this app... what I have to do next?"):** Linked dataset `weathernext_3` subscribed via BigQuery Analytics Hub; service-account key permissions updated (`chmod 644` for the container app user) and granted `BigQuery Admin` role in IAM. `scripts/owner_status.py` reports WNEXT ✅ (HTTP 200, 2 tables: `weathernext_3_0_0_0p1deg` and `weathernext_3_0_0_0p05deg`). Live query verified on Bangkok (17.3 MB billed; BigQuery GIS clustering confirmed). Documented in OWNER_ACTIONS, KNOWLEDGE, KNOWN_ISSUES (KI-283), GUIDELINES, APPROACH_AND_METHODS, and SOURCES (D-069, Q44).


## v0.23.0 — 2026-10-04
- **One running ticker for all of Thailand in the top bar (owner: "concentrate the all information of Thailand … into a
  single running scrolling text … periodically update, like every 30 minutes … let AI prepare it into simple, attractive
  and lovely Thai language").** `situation.py`: rules gather the facts (over the bank and still rising with provinces, over
  the bank in total, may reach the bank in 24–48 h, water from upstream, fast rise, the wettest gauge and forecast, the
  overview); the worker asks GLM every 30 min for a warm retelling (≤ 250 characters, calm, no "ด่วน", examples said as
  examples) and shows it only if it adds no number, place or verdict word (one retry), else the rule text. Live trials:
  9 of 9 accepted after the prompt fix; the first trials read "เร่งด่วน:" and implied 3 provinces held all 11 rising gauges
  (fixed: "เช่น" in the facts). `/api/situation`; tap the ticker for the full text, who wrote it and when; the text stands
  still for visitors who prefer reduced motion. It replaces the rain line and the urgent line (D-089).
- **Top bar = national overview (owner: "Do not need to focus only สถานีในภาคกลาง").** One line "ทั่วประเทศ · ● ล้นตลิ่ง N …"
  (words and counts, still the list's status filter), then the ticker; phone top area 277 px (was 382), desktop 163 px.
- **Forecast rows 24 / 48 / 72 h, no 12 h row (owner: "remove trend 12 hr … think about longer term").** 72 h: the network
  model wins at 372 gauges, medium confidence at 70 (48 h: 63); same rules as 48 h. Summary details count the trend groups.
- **จับตา readable at a glance (owner: "use color or symbol … a lot of text under subcategories").** Over-bank sub-groups as
  coloured pills ("⬆ น้ำยังขึ้น" red, "→ ทรงตัวหรือลดลง" grey) with province chips and count badges; a chip opens its stations.
- **AI summary review (owner: "review using AI in creating ให้ AI สรุปให้ฟังง่าย ๆ"):** 12 live pins → 10 retellings passed,
  2 timed out at 8 s; fixed what the check let through: "ข่าวดีคือ…" framing, mixed นะคะ/นะ voices, filler openings, "เริ่มสูง"
  read as "rising", "น้ำในสะพาน…" (prompt + check: tone, filler opening).
- **Dam releases beyond the Chao Phraya tested: no gain (owner: "consider การปล่อยน้ำเขื่อน more than เจ้าพระยา").** 50 large dams'
  daily releases (HII `dam_yearly_graph`) as inputs for 100 gauges in their sub-basins: error −0.5 / −0.9 / −0.9 % at
  24 / 48 / 72 h (median 0). Not adopted (D-090); rule curves found in the same data (research/2026-10-04_dam_release_backtest.md).
- **MODELS.md:** theory and formulas, which models win per horizon, eight hard-to-forecast gauges with real errors (D-088).
- Live checks C18 (24 h rise vs recent pace note), C19 (ticker); summary rain checks retired.

## v0.22.0 — 2026-10-04
- **AI Summary UX Overhaul ("✨ ให้ AI สรุปให้ฟังง่าย ๆ", D-068, KI-275):**
  - **Zero-wait two-stage rendering:** Tapping the button renders the deterministic rule narrative (`r.story`, ~40 ms) immediately; background GLM warm retelling replaces text seamlessly when verified. Visitors never face a blank 5–7s shimmer.
  - **Voice accessibility ("🔊 ฟังเสียง"):** Integrated native Web Speech API (`window.speechSynthesis`, `th-TH`, rate 1.0) in the summary header, allowing elderly, visually impaired, or on-the-move residents to listen to the explanation hands-free.
  - **Checker false positive fix (KI-275):** `_VERDICTS` regex replaced rigid `r"ไม่(?:ขึ้น)?ถึงตลิ่ง"` with hedged prefixes `(?:ยังไม่น่าจะ|น่าจะยังไม่|คงยังไม่|คงจะไม่|ยังขึ้นไม่|ยังไม่)ถึงตลิ่ง` and unhedged lookbehind. Natural safe hedging like `"ถ้าเป็นแบบเดิม น้ำน่าจะยังไม่ถึงตลิ่ง"` is accepted, while absolute guarantees (`"น้ำไม่ถึงตลิ่งแน่นอน"`) remain strictly rejected.
  - **Negative cache lockout reduction:** Reduced failure/timeout cache from 1800s (30m) to 120s (2m) so transient API timeouts don't lock residents out.
  - **Prompt and language refinement:** Instructed GLM to use warm, gentle, polite spoken Thai suitable for common people and the elderly, avoid repetitive `"และ"` chaining, preserve official waterway names, and raised `GIST_MAX = 420` chars. In templates: fixed `"น้ำขึ้นไม่เกิน 0 ซม."` → `"น้ำไม่เคยขึ้นเกินระดับนี้"`, and rain joins with `"ต่อไป"`.
- **Two-dimension status & top bar fold:**
  - `status.trend` on every station row ("น้ำยังขึ้น" vs "ทรงตัวหรือลดลง").
  - Top bar folding (collapsible header, rain line names the station/province).
  - Sheet rows and chart synchronized to one run snapshot (C15 race fix).
  - GISTDA layer removed and collector stopped (D-084).
  - 294 passing tests (`pytest -q`).
- **จับตา over-bank split** into "น้ำยังขึ้น" / "ทรงตัวหรือลดลง" (owner) with both labels per gauge ("วัดได้ ↗ · คาด ?"); the trend
  rule (`status.trend`, D-083): the 24 h forecast when sure (↗ ↘ or "→ ทรงตัว"), else the measured recent pace. Live: 132
  rising, 800 flat or falling, 108 without a trend; over the bank 8 rising, 43 flat.
- **River cards in two dimensions** (level counts + trend counts) for every river and "ลำน้ำอื่น" alike (owner: "Keep format …
  consistency"); the measured line adds "6 ชม. ล่าสุด: …" when the last 6 h differ (101 gauges read "เพิ่มขึ้น" over 24 h
  while their recent pace had stopped).
- **One map layer box** (owner chose "legend with checkboxes"): every status, rings, DWR posts and Traffy switchable with
  counts, remembered per browser, folded on phones (D-085).
- **Google Flood Hub collected and validated, not shown (D-087):** 103 virtual points in Thailand, every 6 h; 3 SEVERE (2
  where our gauges are over the bank, 1 without a gauge of ours), but NO_FLOODING at 7 places our gauges are over the bank;
  forecasts 9 days. The key only in the `X-Goog-Api-Key` header, worker only.
- **docs/MODELS.md** (D-088): how the app calculates, Thai summary, decisions record, data wish-list.

## v0.21.0 — 2026-10-03/04 (includes v0.20.6 and v0.20.7, interim deploys, not tagged)
- **New tab "⚠️ จับตา": the next 24–48 h risks (owner: "I need another tab to have the list of potential risks according to
  the water level in next 24 or 48 hr … link to the stations or areas … with the confidence").** Six groups, worst
  first, a gauge listed once (in its worst group): 🔴 ล้นตลิ่งแล้ว (per province, tap for the gauges), 🟠 อาจถึงตลิ่ง
  (bank-chance band ">50%" or "25–50%" within 24/48 h), 🟠 น้ำเหนือกำลังมา (a learned upstream gauge, travel time 3–48 h,
  rose ≥ 30 cm in 24 h; gauge at watch/warning), 🟡 น้ำขึ้นเร็ว (24 h forecast ≥ +20 cm), 🌧 ฝนหนักคาดการณ์ (≥ 35.1 mm in
  24 h per province), 🛰 ดาวเทียมเห็นน้ำท่วม (rai per province). Confidence is the measured track record as counts,
  "6 ใน 10" (owner kept counts over percent), from our own archived forecasts over 30 days, shown only with ≥ 30 cases
  (`risk_record`, daily in the forecaster): may reach the bank 6 in 10 (">50%") and 1 in 10 ("25–50%"; the model's
  own band says 25–50 %: ~3× too high, so never shown as a percent), upstream 6 in 10, fast rise 7 in 10. Opens
  nationwide each time with its own ภาค ▾ · จังหวัด ▾; "เฝ้าระวัง" (the yellow status) and "เตือนภัย" (official) were
  rejected as names. Rows: station name, one detail line; `/api/risks` builds the groups from the list's own rows.
- **Satellite in the station sheet and on the map (owner: "Can we apply the info from satellite?").** Sheet line when
  ≥ 100 rai were seen flooded within 5 km ("🛰 ดาวเทียมเห็นน้ำท่วมรอบสถานี (5 กม.) ราว 14,000 ไร่ ⓘ"); map toggle
  "🛰 ดาวเทียม" (off by default; on from the จับตา group) drawing observed cells merged into squares (`/api/satellite`,
  ≤ 5,000 squares, never interpolated); per-gauge and per-province totals computed once per download (`sat_summary`).
  Evidence: outside กทม./ปริมณฑล, 38 % of over-bank gauges have ≥ 100 rai flooded within 5 km vs 8 % of normal ones.
- **Map shows every gauge with data < 24 h (owner: "Do we still need 'แสดงสถานีที่ยังคาดการณ์ไม่ได้ (118)'?").** The
  switch hid 117 gauges, among them 3 over the bank and 3 near it, and 65 in Bangkok. Now a gauge without a tested
  forecast is a hollow ring in its status colour; gauges silent > 24 h stay off (the legend says how many). The list's
  "📈 เฉพาะที่คาดการณ์ได้" chip is gone too (owner: remove).
- **Satellite data lost and guarded (KI-269).** At 19:44 UTC GISTDA served an empty layer for over an hour before a
  rebuild; the "steady for an hour" rule took it as finished and replaced our 72,008 cells with nothing. Now an empty
  probe never counts and a download must hold ≥ 95 % of the announced cells. The cells return with GISTDA's next layer.
- **Tributaries join their river (owner: "คลองนางน้อย is under basin แม่น้ำตรัง").** HII's sub-basin id (stored per gauge
  now) groups a river and its tributaries: sub-basin 349 = the 8 แม่น้ำตรัง gauges plus คลองนางน้อย and คลองยวนปลา. A gauge
  without a river view of its own joins the view with the most gauges in its sub-basin, listed as "ลำน้ำสาขาในลุ่ม…"
  after the upstream→downstream chain (no confluence data, so not slotted into it); cards say "(รวมลำน้ำสาขา N)"; river
  tags follow. 170 of 426 "other" gauges placed; the rest stay under "ลำน้ำอื่นใน<จังหวัด>". Text no longer touches the
  province bar.
- **DWR early-warning level posts archived and shown as a trend-only layer (owner: "Get history, if possible, then
  archive first, and show as trend-only layer").** 455 posts of กรมทรัพยากรน้ำ (ews.dwr.go.th, Thai egress only); DWR
  serves ~11 h of history, so our 30-min archive (400 days) is the history. Kept apart from the gauges (`dwr_station`,
  `dwr_obs`): the level is depth on a local post, not m MSL, and 336 of 439 alarm levels are a default 4.00 m. Map: grey
  squares from zoom 9, popup with the measured 24 h change (same words and QC as the gauges), "กำลังเก็บข้อมูล" until
  24 h are archived, "ค่าค้าง" for stuck posts.
- **Forecast method "recent" and live check C15–C17:** see the forecaster item below; C16: the map draws every gauge
  with data < 24 h; C17: the จับตา tab agrees with the list's station data.

- **One forecaster: the rows and the chart come from the same model (owner: "Are the forecasting in text and in graph
  agree with each other, I found the difference" → "Why trend and model forecast in the chart are different? … I thought
  the trend were calculated by the model").** Proven at Kgt.19A: the rows came from a measured-trend override in the API
  (D-060, 2026-09-28: a 24 h straight line, +124 cm, continued and damped: "+48/+75/+91 ซม."), the chart from the model
  ("no change": flat), far outside the model's own 90 % band. The canal had jumped ~70 cm in 6 h and then levelled off.
  535 of 927 rows were override rows; 171 said ≥ 10 cm while the chart drew the model.
  - **The override is gone.** The rows are the model's own path (`change_summary` of the stored quantiles), the band
    the chart draws; the chart marks the model's 50 % range at 12/24/48 h for the live check.
  - **The trend became a method of the model, "recent" (แนวโน้มล่าสุด):** the smaller of the 24 h and the last-6 h
    pace, none when they disagree, damped like the others. It competes per gauge and horizon in the same 45-day
    rolling backtest with the same 10 % skill gate, and its bands come from its own backtest errors. Evidence for the
    rule (archived runs 26 Sep – 3 Oct, research/2026-10-03_verify_text_graph.py, ~6,000 cases per horizon): mean
    error 10.4 / 16.3 / 29.2 cm at 12 / 24 / 48 h vs 12.6 / 19.5 / 32.8 for the old override and 12.5 / 18.5 / 31.5
    for the served model; direction right 85–87 %. Cached backtests without "recent" are redone at once.
  - The QC's measured 24 h line also reports the last 6 h (`change6_cm`), shown nowhere yet.
  - v0.20.6 (interim, 15 min) kept the override at the recent pace and drew it as a second (orange) line; the owner's
    next question showed two forecasters on one chart is the problem itself.
  - Live check **C15**: every 12/24/48 h row prints the 50 % range the chart marks at that horizon.
- **River tab: every gauge of a picked province (owner: "You can show in river tab, even this province has only one
  station … is it the expectation from visitors?").** ชลบุรี showed "ทุกสาย (0)" and a pointer elsewhere; 13 provinces
  showed nothing and 426 of 840 non-BMA gauges never appeared in the tab (< 3 gauges per waterway). Now a section
  "〰️ ลำน้ำอื่นใน<จังหวัด>" lists them below the river views, grouped by waterway ("ไม่ระบุชื่อลำน้ำ" for 111 without a
  name), with the same bar, value and 24 h row; the picker counts them. River views keep the 3-gauge rule (1–2 gauges
  have no upstream/downstream). BMA canals stay in รายการ (D-074).
- **Thin provinces say so (owner: "Yes, one line").** With a province of ≤ 2 gauges picked, the shared where-row adds
  "จังหวัดนี้มีสถานีวัดระดับน้ำเพียง N แห่ง ⓘ". Checked first: we already carry all 808 gauges of HII's national feed
  (0 missing, 77 provinces); ภูเก็ต, ชลบุรี, หนองคาย and บึงกาฬ have one gauge there too — a gap of the network, not of
  the app. Other networks were tested (DWR EWS, RID Telerid, HII's BMA canal feed): see KNOWLEDGE and KNOWN_ISSUES.
- **"More stations → better forecasts?" (owner) answered with an ablation** (60 random gauges with learned upstream
  gauges, the same 45-day rolling backtest, research/2026-10-03_ablate_upstream.py): with their 2 upstream gauges the
  error is 7.6 / 5.4 / 4.2 % lower at 12 / 24 / 48 h than without (1 upstream: 4.3 / 2.2 / 1.8 %); skill over "no
  change" 22.8 vs 16.4 % at 12 h; 12 of 60 gauges gain > 15 %, 10–12 get slightly worse (the per-gauge backtest keeps
  them off). The second gauge adds as much as the first: no saturation at 2 (next: try 3–4). DWR posts can be tested as
  inputs once ~30 days are archived.

## v0.20.5 — 2026-10-03
- **Satellite cells follow GISTDA's new layer within about two hours (KI-268).** Found answering the owner's "Developing
  progress for satellite inputs?": GISTDA rebuilt its 7-day layer at ~15 UTC today (~18 UTC yesterday), cell by cell
  (23,650 → 30,700 → 88,200 cells while we watched), with a new Sentinel-1 pass of 2 Oct, while our 20-hour rule kept the
  morning copy (images 27–29 Sep) until ~02:30 UTC. Now a 1-cell probe every hour reads the rebuild stamp and count;
  the ~300 MB download runs only for a new stamp whose count stood still for an hour (never a half-built layer), and a
  copy older than 36 h is refreshed anyway. Confirmed the same evening: GISTDA rebuilt again at 17:24–17:27 UTC; the
  probes waited, then the steady layer came in at 17:49 UTC — 72,008 cells, images 28 Sep – 2 Oct (was 27–29 Sep).

## v0.20.4 — 2026-10-03
- **One "where" row for both tabs: ภาค ▾ · จังหวัด ▾ (owner: "Suggest, if the users like to see stations in their
  province?" → "Should we improve the dropdown menu under tab แม่น้ำ to have also province dropdown after select ภาค? …
  ภาค จังหวัด แม่น้ำ as dropdown menu. Is it good or bad? And how can we arrange it?" → chose "Shared where-row +
  river row"; D-076).** In the list, two pickers with counts ("ภาคเหนือ (173)", "น่าน (26)") replace the four rows of
  region chips; the province filters the status counts, list and map. The river tab shows the same row and its own
  "แม่น้ำ ▾ ⓘ" row below: the overview lists that province's rivers and counts its gauges; a river shows whole, with the
  province's gauges marked and scrolled to. Search hint "ค้นหา จังหวัด/อำเภอ/สถานี" (it always matched provinces).
- Validated at 390 px: the where row fits on one line in both tabs; Nan → 26 gauges in the list, overview แม่น้ำน่าน 9 ·
  น้ำมวบ 3 · น้ำยาว 3 · แม่น้ำน้ำว้า 3, 9 of 26 Nan-river gauges marked. Live checks C8/C9/C14 use the pickers.

## v0.20.3 — 2026-10-03
- **Usual region names (owner: "Users might expect กทม , กทมและปริมณฑล ภาคกลาง and other usual regions. The เหนือกทม
  and ปริมณฑล might sounds strange?"; D-075):** กทม. · **กทม. และปริมณฑล** (now includes Bangkok, 237 gauges) ·
  **ภาคกลาง** (was "เหนือ กทม.": the official central region without the Bangkok area) · ภาคเหนือ · ภาคอีสาน ·
  ภาคตะวันออก · ภาคตะวันตก · ภาคใต้ · **ทั่วประเทศ** (one word; "ทั้งประเทศ" gone). The same names in chips, list
  headings, the rain line and the river tab; saved choices keep working.
- **"ทุกสาย" in the river picker, the default (owner: "Can user select all rivers under river filter?"):** one row per
  river in the region — gauges over/near the bank and how many are forecast to rise or fall in 24 h, counted with the
  rows' own rules — most stressed first; tap a river to open it. Live check C14 compares each river's "↗ เพิ่มขึ้น N"
  with the rising rows in its own view. That check's first run (13:30–13:50 UTC) flagged 14 rivers — a bug in the
  check (it counted "↗" but not "⬆ เพิ่มขึ้นมาก") that showed a real gap: Hat Yai's คลองอู่ตะเภา had three
  "⬆ เพิ่มขึ้นมาก" rows while the overview said "↗ เพิ่มขึ้น 3". The overview now says strong rises apart, in the rows'
  red, and ranks rivers by them right after over-bank gauges.

## v0.20.2 — 2026-10-03
- **River tab picker is ภาค, shared with the list; no description line (owner: "Change filter from จังหวัด to ภาค?",
  "no long description อ่านจากบนลงล่าง.." → chose "ภาค synced + ⓘ"; D-074).** One line "ภาค ▾ · แม่น้ำ ▾ · ⓘ": the
  region is the same one as the list's region chip in both directions (pick ภาคเหนือ in the list → northern rivers;
  pick ภาคใต้ here → the list follows). The explanation (numbers vs the bank, top = upstream, ordering, tested
  forecasts only) moved behind the ⓘ; "↑ ต้นน้ำ / ↓ ปลายน้ำ" stay as small markers. A river tag on a station from
  another region switches to that station's region, so the river is in the picker.

## v0.20.1 — 2026-10-03
- **แม่น้ำ tab for people all over Thailand (owner, screenshot: "visitors can be people around Thailand — They might
  not found their river there … search their position by ภาค … add tag แม่น้ำ to each station … Is necessary to show
  ระยะห่างจากปลายน้ำ?" → chose all four, "one line: Province & river", upstream at the top; D-074, KI-267).**
  - Rivers with ≥ 3 gauges (was 8): ~62 waterways instead of 15. Natural waterways only — Bangkok-region canals are
    pumped and gated (no upstream), but outside the polders a "คลอง" is often a river (คลองอู่ตะเภา, คลองจันทบุรี) and
    is kept. Without an HII river line, gauges are ordered by bank height (said in "อ่านกราฟนี้").
  - One line of two pickers, "จังหวัด ▾ · แม่น้ำ ▾", instead of three rows of chips; picking a province shows its
    rivers and marks its gauges.
  - Upstream at the top: the water flows down the screen ("↑ ต้นน้ำ … ↓ ปลายน้ำ").
  - No "ราว N กม. จากปลายน้ำ" in the rows (one line shorter each).
  - A river tag on every gauge that has a view: "· 〰️ แม่น้ำน่าน" in the list, "〰️ ดูแม่น้ำน่านทั้งสาย ›" in the
    station sheet — it opens the river at that gauge.

## v0.20.0 — 2026-10-03
- **"〰️ แม่น้ำ" replaces the เจ้าพระยา tab, with forecasts (owner: "Should we adapt tab เจ้าพระยา? because we extended
  to nationwide already. Will users expect to see forecasting additionally under this tab too?" → chose "แม่น้ำ tab +
  forecast"; D-072).** 15 rivers with ≥ 8 gauges (เจ้าพระยา, น่าน, ยม, ชี, มูล, ปิง, วัง, ป่าสัก, ปัตตานี, แควน้อย,
  ท่าจีน, ตรัง, ตาปี, บางปะกง, เพชรบุรี) as chips; the region chip picks the default. Each gauge row adds the same
  "อีก 24 ชม." row as the list (tested forecasts only, D-060); stale gauges say "ไม่อัปเดต". On the Chao Phraya the
  rows show the flood wave moving down (rising Chai Nat → Ayutthaya, falling at Nakhon Sawan, 2026-10-03).
- **River km for every river (`rivers.py`):** HII's river lines joined into one network (bridging drawing gaps and
  reservoirs, e.g. Bhumibol and Sirikit), measured from the end where the banks are lowest — so the Pattani and the Tapi
  run north and the Mun east. Matches the hand-checked Chao Phraya km within 5 km; banks rise upstream for 73–100 % of
  gauge pairs. `/api/rivers`, `/api/profile?river=`.
- **Validation fixes (KI-266):** the BMA gauge ส.ปากคลองตลาด is no longer mixed into the HII/RID Chao Phraya chain
  (KI-217) and no longer mis-placed by latitude between the Bang Yo gates.
- **Nationwide descriptions, name kept (owner: "Keep old name, and adapt the description everywhere for nationwide";
  D-073):** page title "BKK FloodWatch — ระดับน้ำคลองและแม่น้ำทั่วไทย", meta/link-preview/structured-data texts,
  noscript, API docs, README, link-preview image and the GitHub description now say canals and rivers across
  Thailand (1,000+ gauges) and why the name says BKK ("started in Bangkok during the 2026 flood").

## v0.19.0 — 2026-10-03
- **"ดาวเทียมเห็นน้ำท่วม" in the pin panel (Q45: owner "yes"; D-071).** When GISTDA's satellite radar mapped flooding
  within 1 km of a pin in the last 7 days, the panel gets one factor line: "ดาวเทียมเห็นน้ำท่วมห่างราว 400 ม. · รวมราว
  286 ไร่ในรัศมี 1 กม. · ภาพ 27–29 ก.ย. (GISTDA)". Only what was seen: nothing is said when nothing was seen, never
  "ไม่ท่วม"; the ⓘ explains that radar cannot see water among buildings and trees. The AI story and its numbers tell
  it too ("ภาพดาวเทียมเมื่อไม่กี่วันก่อนเห็นน้ำท่วมห่างราว 400 ม.").
- **New daily collector `gistda_flood`:** GISTDA's national 7-day layer (111,387 flooded cells, 3,474 km² on
  2026-10-03), checked hourly, downloaded at most every 20 h, in the forecaster container (a download takes ~7 min and
  held the collector loop on the first try). Only centre, area and place are kept; no raw archive (size; the payload
  echoes our key, KI-262). `/api/point` gains `satellite`. Live check C13.

## v0.18.9 — 2026-10-02
- **Pins upstream of Bangkok use the river next to them (owner: "The point is next to station บางปะหัน LBI001, but
  showed no near station!!"; KI-263, D-070).** The Bangkok polder rules (a river gauge never judges the canals) were
  applied in every focus province up to Nakhon Sawan. Now they apply only where the nearest gauge is in กทม. or
  ปริมณฑล; at Bang Pahan the panel now says "ระดับน้ำในแม่น้ำล้นตลิ่ง/วิกฤต" from LBI001, 0.1 km away.
- **The top strip shows rain only when it is heavy (owner: "it used too much space again!! … specifically for Bangkok,
  for what?" → chose "Only when heavy"; KI-265).** No rain line unless the chosen region expects or measured heavy
  rain (TMD ≥ 35.1 mm), then one line. Everyday rain stays in the pin panel and station sheets.
- **New sources researched (D-069), research only, nothing new on the site:** Copernicus GFM satellite flood maps
  (keyless; blind on 61–71 % of Bangkok's land, 6 passes in 30 days; agrees with GISTDA on 89 % of cells); GloFAS
  for a 3–7 day outlook (no gain at any of 12 main-river gauges, even with perfect future discharge — stopped);
  Google WeatherNext 3 (terms read: its real-time rain is never shown or served; backtest script ready, waiting
  for the BigQuery subscription). [research](research/2026-10-02_satellite_flood.md),
  [GloFAS](research/2026-10-02_glofas_outlook.md).
- **Plumbing:** `.env` keys for GFM, WeatherNext (service account in `certs/`), EWDS; worker-only; `owner_status.py`
  checks each (GFM ✅, EWDS ✅, WNEXT waiting for the listing). `floodwatch.gcp`: Google service-account login with
  the standard library + openssl. GISTDA echoes our key in `links` (KI-262) — stripped in research code.

## v0.18.8 — 2026-10-02 (v0.18.0–v0.18.7 were live steps of the same work)
- **"? ไม่แน่ชัด" now says what is possible (owner: "we can't say just no trend in everytime, user expected to hear
  what can be possible even in the far station" → chose "possible change + bank risk").** The plain line, the story and
  the numbers give the size of the likely change and whether the wider (9 in 10) range could reach the bank from
  today's margin — Ko Kret: "น้ำน่าจะเปลี่ยนไม่มาก อาจลดลงราว 5 ซม. หรือเพิ่มขึ้นราว 10 ซม. แต่ถ้าน้ำขึ้นมาก อาจถึงตลิ่งได้"; a
  gauge 161 cm below its bank: "ถ้าเป็นแบบที่ผ่านมา น้ำยังไม่น่าจะถึงตลิ่ง". No direction is claimed where the backtest
  did not prove one (D-060); the numbers gain a "🏞️ ตลิ่ง" line. A close gauge among disagreeing ones is no longer
  called "ไกล" ("สถานีวัดน้ำรอบ ๆ ให้ผลต่างกัน …"); the checker now also rejects "ไม่ถึงตลิ่ง"-style certainty.

- **AI on request, one button (owner: "AI assistant generated only when requested, single point for that is enough?" →
  one "ask AI" button "to reduce unnecessary AI generated"; D-068, amends D-022).** Every pin panel shows a plain line
  under the headline (by template, no AI) and one button, "✨ ให้ AI สรุปให้ฟังง่าย ๆ". Nothing calls GLM until it is
  tapped. The card it opens tells the story the way a weather app's AI card does (owner: "they try to explain
  easily"): "แถวบ้านคุณไม่มีสถานีวัดน้ำใกล้ ๆ สถานีที่ใกล้ที่สุดอยู่ไกลราว 6 กม. ที่นั่นตอนนี้น้ำต่ำกว่าตลิ่งราว 31 ซม. …
  ส่วนวันข้างหน้ายังบอกไม่ได้ว่าจะขึ้นหรือลง คาดว่ามีฝนเล็กน้อย ช่วยสังเกตน้ำในคลองใกล้บ้านประกอบด้วยนะ". The numbers
  are folded under "ดูตัวเลข".
- **Rules write the story; GLM may only retell it.** A retelling is shown only if a checker finds no new number, no
  direction or strength the rules don't say, no past change told as the future, no verdict ("ได้ครับ", "ไม่ท่วม",
  "ปลอดภัย", "ปกติ"…), no dropped "cannot tell" and no far gauge called "แถวนี้"; otherwise the rule story is shown.
  GLM never sees the pin. `AI_EXPLAIN=0` switches it off; the site works without it.
- **Validated like a resident would read it** (`scripts/ai_explain_validate.py`, [research](research/2026-10-02_ai_explain.md)):
  198 answers at 33 places per run; whole-answer rewording passed 43 %, the final story retelling 91 % (median 4.0 s,
  none > 8 s). Reading the passing answers found a past rise retold as a future one (now rejected) and wording slips
  of my own (fixed). v0.18.0 called a gauge 6 km away "คลองแถวนี้" (KI-261, fixed).
- **GLM calls fixed (KI-260):** glm-5.3-flash always reasons; `reasoning_effort: "low"` cuts a call from 9–10 s to
  ~1–5 s, and a cut-off answer's reasoning text is never returned as the answer.
- Checker: C12 (plain line and story never call a far gauge "here"; the AI button opens a story with no verdict
  word); C4 no longer counts the same measured line under two different gauges as a repeat.

## v0.17.3 — 2026-10-02
- **"ห่าง 1.5 กม." like the station list (owner: "Distance > ห่าง 1.5 กม.").** The canal factor's gauge lines said a bare
  "1.5 กม.".
- **A canal without a forecast shows what was measured, not jargon.** "ยังไม่มีคาดการณ์ (ยังไม่ผ่านการทดสอบย้อนหลัง)" →
  "ยังไม่มีคาดการณ์ ⓘ" (the why in the ⓘ) + its measured line ("48 ชม. ที่ผ่านมา: ลดลง 11 ซม."), the same words as the
  gauge with a forecast below it. Guarded by `tests/test_wording.py`.

## v0.17.2 — 2026-10-02
- **"อีก 24 ชม." instead of "ใน 24 ชม." for every forecast (owner: '"ใน 24 ชม.", "ใน 48 ชม." are not clear. I cannot
  understand that it is about the future'; KI-259).** One rule across the app: row labels "อีก 12/24/48 ชม."
  (water rows in list, panel and sheet; the rain row; the summary), sentences "ในอีก N ชม." (headlines, peak time,
  bank chance, the AI summary), the past "N ชม. ที่ผ่านมา". `tests/test_wording.py` fails on any bare future "ใน N ชม.".

## v0.17.1 — 2026-10-02
- **Rain in the water rows' layout (owner: "Text for rainfall info are one in a long sentence … Compare to the water
  level info, it is easier"; KI-258).** One helper for the pin panel and the summary strip: a short bold state
  ("ฝนตกแล้ว" / "คาดว่าจะมีฝน" / "ไม่มีฝน", where it was measured behind its ⓘ), the forecast as a row like the water's
  "ใน 24 ชม. [ฝนเล็กน้อย] ราว 8 มม. ⓘ", then "24 ชม. ที่ผ่านมา: ฝนปานกลาง 11 มม." and "ชั่วโมงล่าสุด: 0.2 มม.".
  The summary reads "🌧️ ฝนสูงสุดใน<region> ⓘ" over the same rows.
- **The headline is one short clause and never repeats the rain rows' amounts (D-055).** Light rain is left to the rows;
  moderate rain stays as a warning ("…ลดลงต่อเนื่อง แต่คาดฝนปานกลาง อาจมีน้ำขังบนถนนช่วงฝนตก"); heavy rain that fell is
  said in words. New checker rule C11 (rows in panel and summary, no "มม." in the headline).

## v0.17.0 — 2026-10-02
- **Basin and river maps put to work (owner: "ข้อมูลลุ่มน้ำ watershed map, basin map เอาใช้ประโยชน์อะไรได้ไหม"; D-066).**
  HII's public `basin.json` (22 basins) and `river_main.json` (93 rivers) give every gauge its basin, its main river
  and its river system (weekly `hii_geo`; 215 gauges without a basin name got one).
- **"Water from upstream" line.** Station sheets and pin panels show the first upstream gauge's measured change and the
  learned travel time: "ต้นน้ำ: ท้ายเขื่อนนเรศวร · 48 ชม. ที่ผ่านมา: ลดลงมาก 58 ซม. · มักถึงที่นี่ในราว 5 ชม. ⓘ".
- **Upstream links stay within one river system** (no cross-river links such as โก-ลก ← สายบุรี). Tested on 39 gauges:
  neutral (1 link set changed). Basin-mean rain and an upstream-cells rain proxy were tested too: no significant gain,
  not adopted; rain from the wrong basin (placebo) clearly hurt. HydroBASINS sub-basins would allow a proper test,
  but their host challenges our server (owner download: OWNER_ACTIONS HYDROBASINS).
  [research/2026-10-02_basins.md](research/2026-10-02_basins.md)
- **High-canal headline follows the rows (C6).** "ระดับน้ำคลองค่อนข้างสูง แต่แนวโน้มยังทรงตัว" was said for every trend
  that was not falling; now steady → "ยังทรงตัว", rising → "และมีแนวโน้มสูงขึ้น", unclear → "ยังไม่เห็นทิศทางชัดเจน".
  Checker C10 now judges model directions the way the UI shows them. Live run: 488 sheets, 76 pins, 1,972 rows →
  0 findings on C1–C10.

## v0.16.8 — 2026-10-01
- **One way per panel (owner: "Continue all suggestions").** The canal factor's "▸ รายละเอียด" became an ⓘ like the
  rain factor's; the panel has no folded details left. The summary rain line uses the panel's words ("ราว N มม." for
  a forecast, no "ราว" for a measurement), no 4-square scale, and its gauge name behind an ⓘ.
- **Nearest gauges first once your location is known.** "📍 ใกล้คุณ": the 3 nearest fresh gauges within 15 km on top
  of the list, then "ทั้งหมดใน<region>" by severity as before (e.g. Chiang Mai: สะพานนวรัฐ P.1, P.103, MOU010).
- **Data that stopped upstream is said, not hidden (KI-257).** 2026-10-01 from 00:10 ICT all BMA canal readings were
  stuck (the relay kept answering; HII's copy and the direct BMA channel had nothing newer). The summary now says
  "⚠️ N สถานีไม่อัปเดตเกิน 3 ชม. (ล่าสุด …)" when most gauges of the region are stale, and `/api/health` lists
  `stale_sources` (newest reading too old although the fetch succeeds) for an uptime monitor.
- **A pin panel refreshes its gauges in the list, like a sheet does** (pin vs list differed by 1–2 cm at 12 blocks
  when new readings arrived between the two). Live consistency run: 488 sheets, 76 pins, 1,960 rows → **0 findings on
  C1–C10**.

## v0.16.7 — 2026-10-01
- **Shorter rain factor in the pin panel (owner: "Rainfall info in panel are not optimal, can we shorten?").**
  Four long lines became two (owner: "Or put unnecessary info in i symbol?"): the heavier of forecast and measured
  leads ("คาดฝนเล็กน้อย ราว 6 มม. ใน 24 ชม. ข้างหน้า" / "24 ชม. ที่ผ่านมา: ไม่มีฝน"; after a downpour
  "ฝนตกแล้ว: ฝนหนัก 88 มม. ใน 24 ชม. ที่ผ่านมา" / the forecast). The last hour shows only when it rained. Sources, gauge,
  distance, reading time and the forecast grid of that spot (~8 km square, Bangkok point or ~55 km cell) are behind
  an ⓘ, the same grey ⓘ as the trend rows. Consistency run on the live site: 488 sheets, 76 pins, 2,000 rows →
  0 findings on C1–C10 (C9 now reads the rain factor and its ⓘ against /api/point). The 4-square scale (a repeat of the word and the dot colour) and "0.0 มม." are gone. The headline and the
  region rain line use the same words ("ราว …", "24 ชม. ที่ผ่านมา").

## v0.16.6 — 2026-10-01
- **Nationwide forecasts now use their learned upstream gauges (fix).** The forecaster had learned upstream gauges
  once, when nationwide gauges had 4 days of history (none found), and every restart skipped relearning: no gauge
  ever used them. It now relearns at start when the result is empty or a day old, and drops the cached backtest of
  every gauge whose inputs changed. 326 nationwide gauges got upstream inputs.
- **Nationwide backtest after the backfill (owner: "Continue").** 51 gauges sampled across all regions: with area
  rain + learned upstream 27/19/19 beat "no change" by > 10 % at 12/24/48 h, versus 9/8/6 with their own history
  only; Bangkok unchanged (36/40 at 48 h). Outside Bangkok about a third of gauges earn a 48 h line; the rest show
  a range only.
- **Trend rows no longer flip direction because of the measured-trend fallback (KI-256).** TRD001 read ⬆ / ⬇ / ⬆ at
  12/24/48 h: the 24 h row followed the measured trend (D-060) against a rise the model proved at 12 and 48 h. Such a
  row now falls back to the model's own reading; 43 → 0 gauges. Rows of the model that differ by horizon (tides,
  rain arriving later) are left as they are (19 gauges).
- **Opening a sheet refreshes its list item.** The list is loaded every 5 min, a sheet fetches fresh data; when a
  forecast or QC update landed in between, the two differed (C1 at 6 gauges). The list now takes the sheet's row.
- **UI consistency checks C9 and C10** (rain and river lines agree with the API; one direction story per gauge).
  Final live run (2026-10-01 ~16:00 UTC): 488 sheets, 76 pins (9 national), 1,998 rows, 4 viewports → **0 findings
  on C1–C10**.

## v0.16.5 — 2026-10-01
- **Measured rain as a forecast input: tested, not adopted (Q43; owner: "Consider the factors in modeling and
  validate the results, think carefully").** HII serves no public hourly rain history, only daily totals per gauge
  (`provinces/rain3d_graph`, ≤ 31 days per request, labelled by the day the window ends, ~7× HII's own hourly sums).
  With a leakage-safe timing rule and a day-shuffled placebo, the production backtest on 28 Bangkok and 21 nationwide
  gauges showed no gain: Bangkok same as placebo; nationwide −0.5 to −1.2 % median RMSE at 12–48 h on 12 of 21 gauges
  (not significant); slightly worse in the hours after ≥ 35 mm days. Details:
  [research/2026-10-01_measured_rain.md](research/2026-10-01_measured_rain.md).
- **Hourly rain is kept for a re-test.** HII cannot give hourly rain again, so `rain_obs` now keeps 400 days for the
  2,260 rain gauges within ~10 km of a water gauge (others 14 days; ~4.6 GB a year at 211 B per row). The `star`
  model accepts extra known-at-issue inputs (`ex["extra"]`, inert unless supplied). Re-test ~mid-December 2026.

## v0.16.4 — 2026-10-01
- **Rain forecast for Bangkok and its neighbours at the model's own ~8 km grid (Q42, owner: "Continue as
  suggested").** Open-Meteo's grid here, measured 2026-10-01, is 0.0703° × ~0.0826° (~7.8 × 9 km). 111 grid points
  (the 3 × 3 cells around every gauge in the six Bangkok-region provinces), 50 per request, hourly, next 48 h. A pin
  in the region reads its own cell (e.g. ปากเกร็ด 5.7 mm, สีลม 2.1 mm in the next 24 h); the region line takes the
  wettest cell. First run: 111 points ranged 0.6–7.7 mm where the 5 old Bangkok points ranged 1.6–5.1 mm. The forecast
  *model* keeps its 9 proven rain points (changing them needs a new backtest). Open-Meteo use ≈ 4,500 calls a day.
- **Evidence that measured rain matters (owner: "Are the HII rain gauges useful?").** 2026-10-01 13:00 UTC: 4,461 of
  4,778 HII rain gauges reported within 3 h; of 14 gauges with ≥ 35 mm in 24 h, all 14 had been forecast < 10 mm a
  day ahead at our sampling point (e.g. 87.8 vs 3.4 mm at วัดพลวง จันทบุรี; 60.0 vs 0.9 mm at HII001 Bangkok).

## v0.16.3 — 2026-10-01
- **Measured rain, not only the forecast (owner: "There is no rain in panel anymore?", during a downpour; KI-254).**
  The pin panel showed only Open-Meteo's forecast ("คาดฝนเล็กน้อย") while it was raining hard. It now also shows the
  rain already measured by the nearest HII rain gauge (≤ 10 km, ≤ 3 h old): last 24 h in TMD words, last hour in mm,
  gauge name, distance and the time of the reading. Heavy measured rain (≥ 35 mm/24 h) raises the outlook to at least
  "moderate" with "ฝนตกหนักในพื้นที่ เฝ้าระวังน้ำขังบนถนน". Rain gauges are collected for every province (4,651 on
  2026-10-01, was ~185 in the focus area) every 15 min; kept 14 days (only the last 3 h are read).
- **Rain line for every region.** v0.16.0 showed "🌧️ ฝน กทม." for กทม./ปริมณฑล only; now each chip shows its wettest
  forecast point (next 24 h) and its wettest rain gauge (last 24 h), e.g. ทั่วประเทศ: 87.8 mm at วัดพลวง, จันทบุรี.
  `/api/rain` adds `by_region` and is shared for 60 s.
- **The river near a Bangkok pin gets its own line** (≤ 3 km, e.g. the Chao Phraya for riverside Nonthaburi): its
  distance to the bank and status, labelled as the river outside the walls — never canal evidence (D-059).

## v0.16.2 — 2026-10-01
- **The region follows your location once you allow GPS (owner answer to Q40: "Allow GPS"; D-065).** Tapping
  📍 สถานีใกล้ฉัน and allowing location switches the counts, list and map to your region (the region of the nearest
  gauge within 60 km), next to the point panel as before. On later visits with permission already granted, the
  region is set from your location silently. The app never asks for location when the page opens (only the 📍 button
  asks), and a region chip you tapped by hand wins until your next 📍 tap. Verified in a browser with emulated
  locations: Chiang Mai → ภาคเหนือ, Hat Yai → ใต้, no permission → กทม. without a prompt, hand-picked กทม. kept.

## v0.16.1 — 2026-10-01
- **Every region is visible, and the map shows every gauge (owner: "App shows only Bangkok stations"; KI-253).**
  Validated on the live site: on a 390 px phone only 3 of 9 region chips were on screen (ภาคเหนือ … ใต้ scrolled out
  of sight with no cue), and the map was filtered by the chip, so with the default กทม. a user who panned to Chiang Mai
  saw 0 gauges (phone and desktop). Now the chips wrap onto extra lines (all 9 visible at 390 px) and the map always
  shows every gauge in Thailand (796 with a tested forecast on 2026-10-01 05:00 UTC; canvas renderer for phones);
  the chip filters the counts and the list and moves the map view. `scripts/ux_consistency.py` C8 checks both.
- **A release reaches phones at once.** The owner's phone still ran v0.16.0 code after the fix: the page was cached
  5 min (`max-age=300`) and an open tab never reloads its code. The page is now `Cache-Control: no-cache`, and the app
  reloads itself once when `/api/stats` reports a newer version (never while a panel is open — then on close; never
  twice for one version). Verified in a browser with a faked newer version.
- **Headline and rows agree on "steady" (C6).** The pin headline said "ยังทรงตัว" where the gauge's row said
  "? ไม่แน่ชัด" (24 h "steady" with a likely −18…+2 cm; the rows say ทรงตัว only within ±5 cm, D-060). The headline
  now uses the same ±5 cm rule.
- **List and pin from the same snapshot (C1).** The list payload had its own 60 s cache on top of the 60 s rows cache
  (up to 2 min apart: 119 vs 118 cm at CHN001); it is now rebuilt whenever the rows refresh.

## v0.16.0 — 2026-09-30
- **Nationwide parity (owner: "the nation-wide should be the same as in Bangkok"; D-064).** Every HII-network gauge in
  Thailand (733 outside the Bangkok focus area: RID 297, HII 274, พพภ. 89, EGAT 73) now gets what a Bangkok gauge gets:
  a year of history (`hii_backfill` over the whole network, focus first, 12 gauges per 10 min; `hii_history` refills
  nationwide gauges in six daily slices), QC, the same forecast ladder and backtest gate, the same sheet and rows.
  Before, they only had the readings collected since 2026-09-26 and were never forecast, while their sheet promised
  "การคาดการณ์จะเริ่ม… (ราว 3 ต.ค.)" (KI-249).
- **`star` inputs outside Bangkok.** Rain from a 0.5° Open-Meteo cell per gauge (177 cells, 50 per request; forecast
  every 3 h, a year of previous-run rain for 8 new cells per hour) instead of Bangkok's rain; upstream gauges learned
  per basin (best *leading* 24 h change, lag 1–48 h, r ≥ 0.5, ≤ 250 km, before the backtest window; co-located gauges of
  another agency are never upstream). Bangkok gauges keep their proven inputs.
- **Forecaster container.** Forecasts run in their own service (`worker --role forecaster`); the backtest is cached per
  gauge for ~20 h (`forecast_model`). 965 gauges in 294–409 s; the 10-min collectors never wait.
- **Bounded storage.** Daily `retention`: HII-network readings > 400 days (re-fetchable; BMA never), rain-forecast issues
  > 3 days, forecast runs thinned after 2 days and dropped after 14.
- **UI parity.** Region chips for the whole country (กทม. · ปริมณฑล · เหนือ กทม. · ภาคเหนือ · อีสาน · ตะวันออก ·
  ตะวันตก · ใต้ · ทั้งประเทศ; default กทม.); status counts, list and map follow the chip; the "แสดงสถานีทั่วประเทศ"
  checkbox is gone. The water word comes from the agency's river name ("น้ำในแม่น้ำ…" at URTU07, not "น้ำในคลอง…").
  A gauge of another agency at the same place is linked, never merged (E.29A ↔ URTU07). Thai agency names
  (FOP = มูลนิธิอาสาเพื่อนพึ่ง (ภาฯ) ยามยาก สภากาชาดไทย). Pins outside Bangkok are judged from the river and stream
  gauges near them, without Bangkok's polder cautions. Place search finds places anywhere in Thailand.
- **Fixes found while deploying.** `/api/stations` hung ~13 min (nested memo on a non-reentrant lock, KI-250); a dead
  HII host (`tiwrm.hii.or.th`, connect timeouts) no longer stalls the collectors: 10 s connect timeout and a 10-min
  host cooldown (KI-251); two containers running `schema.sql` at start deadlocked (only the collector owns it now,
  KI-252); `/api/health` ignores flagged and future-stamped rows (KI-247; the 26 rows were flagged with the owner's OK).
- **Proof.** Bangkok 40-gauge regression unchanged (48 h: mean skill 0.29, 36/40 over the gate; baseline 0.28, 36/40).
  Nationwide backtest re-run pending the backfill (`scripts/backtest_nationwide.py`). `scripts/ux_consistency.py` now
  samples every region and checks national pins (C7): 488 sheets, 76 pins, 1,288 rows on the live site, 1 finding
  (two different gauges with the same status pill in one pin panel; not a regression). The phone map fits the chosen
  region when its tab is first shown.

## v0.15.3 — 2026-09-30
- **Site-level SEO and link previews (owner: "continue all as suggested").** `/robots.txt` (allow the page, keep
  `/api/docs`, `/api/openapi.json` and the DB-heavy `/api/point` out of indexes) and `/sitemap.xml` (one URL: every
  view is a `#fragment`); `og:image` (1200×630, real phone screenshots; `scripts/make_social_images.py`), `twitter:card`,
  `og:site_name`/`og:locale`, JSON-LD `WebApplication`, a `<noscript>` line, and a description that says 12–48 h
  (it said 12–72 h). The header/footer version now comes from the server (`__VERSION__`; the page showed a stale
  `v0.9.0` until the JS ran). No UI or forecast change.
- **HII readings stamped in the future are flagged (KI-247).** One fetch on 2026-09-30 delivered 28 `hii_load`
  gauges stamped 2026-10-01 16:00 UTC (~21 h ahead), so `/api/health` showed a negative data age. `parse_waterlevel_load`
  now flags such rows `future_time` (same 15-minute tolerance as BMA) so they are never a "latest" reading.
- GitHub: shorter repository description; `docs/img/social-preview.png` (1280×640) for the owner to upload as the
  repository social preview (GitHub has no API for it).

## v0.15.2 — 2026-09-30
- **Hotfix: database overload under load (KI-246).** From ~01:00 to 05:44 UTC (08:00–12:44 ICT) visitors saw
  "โหลดข้อมูลไม่สำเร็จ": ~10 API requests/s each ran the 2–3 s station query, 39 at once filled Postgres'
  40 connections, `/api/health` returned 500 and the worker restarted 452 times (collectors stalled). The station
  rows and the list/stats/street payloads are now computed once per minute and shared (single-flight lock).
  Load test after the fix (120 requests, 30 concurrent): 0 errors, median ~0.5 s, peak 11 DB connections.
- Docs (after the tag): README rewritten as a public front page (value line in Thai/English, live link, safety
  notice, screenshots with alt text, plain features, API with a live sample, FAQ); PLAN, docs index, GUIDELINES,
  ARCHITECTURE, KNOWN_ISSUES (KI-305 resolved), OWNER_ACTIONS (UPTIME) updated.

## v0.15.1 — 2026-09-29
- **GitHub issues reviewed against v0.15 (owner: keep the v0.15 concept):** #9 the desktop page now fits the screen
  exactly (was ~100 px taller than the window at 1366/1440/1920 px: a fixed `calc(100vh − 145px)`); #8 a card's
  hover/focus outline takes its urgency colour (red for ล้นตลิ่ง, was always blue); #6 each pin factor is one phrase
  ("น้ำในคลองล้นตลิ่ง", "ฝนเล็กน้อยใน 24 ชม. ข้างหน้า", "มีแจ้งน้ำท่วมบนถนน 5 เรื่อง"); #7 kept as is (owner).

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
