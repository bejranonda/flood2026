# UX_VALIDATION.md — Would a Bangkok resident find this useful?

> Heuristic review, 2026-09-26, written from the point of view of people living in Bangkok during the 2026 flood. It checks the live site against their needs. **It is not a user study.** The personas are assumptions to be replaced by real feedback (the in-app form, [APPROACH §3.5](APPROACH_AND_METHODS.md)) and by talks with residents. Screens were checked at 390×844 (phone) and 1366×800 (desktop) with headless Chrome.

## 1. Who uses it, and what they need to know in 10 seconds
| # | Persona (assumed) | Their question | What they need on screen |
|---|---|---|---|
| P1 | **Riverside resident** outside the flood wall (Bang Krachao, Nonthaburi, Pak Kret, communities along the Chao Phraya) | "Will the river come over the bank tonight, and when is high water?" | Freeboard in **cm** at the nearest river gauge, **time window of the next peak**, and the chance of reaching the bank |
| P2 | **Inner-city resident** inside a polder (Lat Phrao, Bang Khen, Don Mueang, Nong Chok) | "Will my soi flood when it rains? When will it drain?" | Khlong gauges in *my* area, **rain forecast**, citizen reports nearby, drainage time as a range |
| P3 | **Commuter / parent** | "Is it getting worse or better today?" | One-screen summary: how many gauges are overflowing, rising vs falling |
| P4 | **Elderly relative, or low digital literacy** (often helped by family via LINE) | "Is it dangerous? Whom do I call?" | Big, plain words; colours with labels; hotline one tap away; a link family can share |
| P5 | **Someone already flooded** | "When will the water go down?" | Recovery as a date/time range with conditions; "not estimable" when rain is coming |
| P6 | **Volunteer / community leader** | "Which areas are worst? Can I trust this?" | Ranking by severity, data freshness, a map, and a way to report what they see |

## 2. Findings on the previous MVP (before 2026-09-26 10:00 UTC) and what changed
| # | Finding (as a resident) | Severity | Done now |
|---|---|---|---|
| 1 | "ม.รทก." (m MSL) means nothing to most people; the number that matters is **how far below or above the bank** | High | Each list item and the detail headline lead with **"ต่ำกว่าตลิ่ง 35 ซม." / "สูงกว่าตลิ่ง 61 ซม."**; the MSL value is secondary |
| 2 | No overview: I had to scroll 100 gauges to know if things are bad | High | **Summary strip** (§3.4 of APPROACH): tappable status chips with counts, rising/falling counts, Bangkok rain in the next 24 h, and data freshness |
| 3 | On a phone the map took half the screen and the list was far below; the detail opened at the top of a long page | High | **Tabs** (รายการ / แผนที่ / เจ้าพระยา); the detail is a **bottom sheet**; tap targets ≥ 44 px; the header height is measured for sticky tabs; safe-area insets |
| 4 | I can't find my area | High | **Search** by district, khlong, station name or code |
| 5 | I want to send this to my family on LINE | High | **Share** button (native share sheet, or copy link) with a **deep link** `#s=CODE` that opens the station |
| 6 | "When is high tide?" matters more than a 72 h chart for riverside people | High | **24 h outlook**: next peak as a ±1 h window with a 50 % range, and the **chance of reaching the bank** as a category (< 5 % … > 50 %) |
| 7 | An 11-day-old test gauge was the first "overflowing" item | High | Readings > 24 h old → **"unknown"**; `TEST*` gauges removed (KI-206, KI-209) |
| 8 | The chart drew straight lines across data outages, which looked like real measurements | Medium | Gaps > 90 min are **not bridged**, and the legend says so |
| 9 | I can't tell the site it's wrong for my street | High | **Feedback form** in every station detail, plus a location-only depth report in "near me". Privacy notice, and "not an emergency channel" with hotlines |
| 10 | "Nearest station" can be misleading: Bangkok isn't flat, and walls separate areas | High | Explicit note under "near me" and in the footer. **Polder-aware near me is still to do** (Phase 2) |
| 11 | The long disclaimer pushed content down | Medium | Collapsed into one line that keeps "not official" and the **1784 / 1555** hotlines visible |
| 12 | Colours without a key | Medium | Map legend; chips show colour and label together |
| 13 | Riverside residents want to see the whole river | Medium | **"เจ้าพระยา" tab**: every main-stem gauge from Nakhon Sawan to the gulf with freeboard bars. Gauges only; no interpolation between them ([APPROACH §2.9](APPROACH_AND_METHODS.md)) |

### Round 2 (2026-09-26 ~10:30 UTC, owner feedback)
| # | Finding | Done |
|---|---|---|
| 14 | "I want to check **my** spot, and there's no station there" | **Point check** (D-021): tap the map anywhere, or "สถานีใกล้ฉัน" → an area category with range and confidence, nearby river/khlong gauges, citizen reports within ~1 km, rain, and 4 warnings. No verdict at very low confidence. Shareable `#p=lat,lon`. Report water at the pin |
| 15 | "I can't read even a rough time from the chart" (owner) | **Day markers with short dates** (e.g. "24 ก.ย.") on the chart; "ตอนนี้" moved to the top; no fine ticks |
| 17 | "BKK008 Saen Saep isn't on the map" (owner) | Coordinates from HII's map feed for every station lacking them (D-023); BKK008 now shows as ล้นตลิ่ง. Samut Sakhon and Nakhon Pathom added (whole BMR) |
| 18 | "I can't tap the station, the Traffy circle catches it" (owner) | Stations on a top map layer; Traffy cells smaller and non-interactive (a tap opens the point check, which lists the counts) |
| 19 | "Show all stations; hide bad data with a note" (owner) | Every station listed and, where possible, placed; dashed markers = approximate position; notes for hidden values; whole-country toggle; version shown (D-024, D-025) |
| 20 | "I shared the link on LINE and no preview appeared" (expected, not yet reported) | The main domain challenges crawlers (KI-506). Until Q18 is fixed, share **flood.bejranonda.com**: its page declares itself canonical (v0.2.1, D-027). ⚠️ Not tested with LINE or Facebook themselves |
| 21 | Real usage (owner asked what users actually do) | 10 reports in ~4.5 h from 8 senders: **7 from map pins, 10/10 with a location, 6 street-drainage notes, 0 used the station verdict buttons** ([APPROACH §3.5](APPROACH_AND_METHODS.md)). The pin flow works and is used; the "does this match?" question is ignored, so it needs a stronger prompt or a rethink |
| 16 | "What if someone writes that they're trapped?" | Keyword rules flag emergency notes instantly, and the page shows **1669 / 1784 / 191** with "this site has no responders" |

### Round 3 (2026-09-26 ~16:20 UTC, live site at 390 px and 1366 px, headless Chromium)
| # | Finding (as a Bangkok resident) | Done |
|---|---|---|
| 22 | "The footer about sources and methods is too long" (owner) | One short line stays (status is vs the station's bank, **not your street**); sources and methods open on tap (`<details>`) |
| 23 | "The first 7 cards are Ayutthaya, Nakhon Pathom, Samut Prakan: where is **Bangkok**?" Only **10 of 111** gauges are in Bangkok; 74 are upstream | **Region chips**: ทั้งหมด 111 · กทม. 10 · ปริมณฑล 27 · เหนือ กทม. 74, one scrollable row, choice remembered on the device. Default stays "all" until Q26 |
| 24 | BKK009 showed a red "ล้นตลิ่ง" badge with "ต่ำกว่าตลิ่ง 0 ซม." | Fixed: "ระดับเท่าตลิ่ง" (KI-216) |
| 25 | A 502 page appeared for a few seconds during a redeploy by a parallel session | Known: a single app container restarts in ~5 s. Not fixed (zero-downtime deploys need two app containers) |
| 26 | Bangkok has too few gauges for a "my soi" answer (P2) | Needs the BMA khlong network ([SOURCES §2c](SOURCES.md), Q24) |

### Round 4 (2026-09-26 ~16:45 UTC): a real request and the owner's answers (audience: Bangkok residents)
| # | Finding | Done |
|---|---|---|
| 27 | A real user asked for data for their soi in Sai Mai (near Saphan Mai), where water was rising. Searching "สะพานใหม่" found nothing | **Place search**: typing shows "🔎 ค้นหาสถานที่ …"; Enter or tap asks OSM; a soi name without "ซอย" (e.g. "ลาดพร้าว 71") → the soi first; the point check opens there. A search looks in every region |
| 28 | At that soi the nearest gauge was HII BKK001, ~3.5 km | With BMA gauges: **Khlong Song at Phahonyothin, 1.8 km, 30 cm over its bank**, which matches the report. The area card still says "no verdict" (21 gauges within 8 km disagree): radius to tune (APPROACH §3.7) |
| 29 | Bangkok first (owner: "Bangkok as default this week") | The list opens on กทม. (209 gauges) |
| 30 | "Which data is this?" on BMA gauges | Card: "ข้อมูล กทม."; detail: BMA via flood69 credited, unit "ม. (หมุด กทม.)", "compare only with this gauge's bank" |
| 31 | Commuters: "which roads to avoid?" | Link to BMA's road page in the point card (a snapshot, not a feed) |
| 32 | Owner: "the historic graph and forecasting all lost, what happened? Should we separate old and new info?" | Nothing was lost: the Bangkok list now opens on BMA gauges that only started today, and a worker stall (KI-219) made their charts even shorter. **Separated in the display, not the storage:** gauges with < 7 days of history are labelled "🆕 สถานีใหม่" with the start date and the expected forecast date |

### Round 5 (2026-09-26 ~18:20 UTC): owner: "filter unpredictable stations"; "Traffy shows floods, flood69 stations show below bank: conflict?"
| # | Finding | Done (v0.4.0, D-036) |
|---|---|---|
| 33 | Green "ปกติ" on a canal while the streets around it flood reads as "all fine here" (34 BMA gauges with ≥ 5 street reports within 1 km) | "ต่ำกว่าตลิ่ง" in blue; headline "น้ำในคลองต่ำกว่าตลิ่ง 35 ซม."; card line "🚗 ถนนรอบ ๆ มีรายงานน้ำท่วม N เรื่อง"; detail explains canal vs street; point check warns and says to trust street reports |
| 34 | 42 gauges with no data for > 24 h mixed into the list and map | Folded into "สถานีที่ไม่มีข้อมูลล่าสุด (N)" at the end (13 in Bangkok); hidden on the map unless "แสดงสถานีที่ไม่มีข้อมูล" is ticked; still reachable via the "ไม่ทราบ" chip and search |
| 35 | "Show only what can be predicted" | Chip "📈 เฉพาะที่คาดการณ์ได้" (Bangkok: 10 of 196 live gauges). Off by default, otherwise Bangkok residents lose the canal network |
| 36 | Street data silently 3 h old (Traffy outage) | Age shown on cards, in the detail and the map legend when > 60 min |
| 38 | Owner: "users like to see the trend; separate the non-predictable from the map, with an option" | Map default = 81 forecastable gauges; switch shows 214 more (D-037). Observed 1–3 h change on every gauge without a forecast |
| 39 | Map switches were under the legend and below the fold on a phone (found by the test) | Moved to the top left; verified at 390 and 1366 px |
| 40 | Owner: "flood69 gauges show below bank but the area is flooded; maybe gate/pump mixing hides the real level" | Tested: no mixing (canal side only); 39 of 49 cases were plain canal gauges. BMA's own critical level matched flooded streets far better than the bank → **BMA gauges now read ล้นตลิ่ง / คลองเต็ม / คลองเริ่มเต็ม / คลองยังรับน้ำได้** with "เกินเกณฑ์ กทม. N ซม." and an explanation (D-038). Not hidden |
| 37 | Redundant text in a new gauge's sheet | Trend line hidden when the 🆕 box explains it |
| 41 | Owner: "favicon not easy to recognize on browser, too much detail" (screenshot of 16px tab) | Redesigned with bold "Bold Wave Tile" (D-039): full 14×14 area, bold white wave crest (🌊) on electric cyan water + royal blue, zero micro-dots or rings. Razor-sharp on dark and light tabs |

### Round 6 (2026-09-26 ~19:15 UTC): Point check streamlining, categorized stations & Traffy hotspots (v0.6.0, D-040)
| # | Finding | Done (v0.6.0, D-040) |
|---|---|---|
| 42 | Wall of static text in point sheet ("⚠️ นี่ไม่ใช่ระดับน้ำที่จุดนี้...") pushing data below the fold | Static educational cautions collapsed into `<details class="point-disclaimer">` ("ℹ️ ข้อจำกัดของข้อมูล (สถานีคลอง ≠ ระดับถนนหรือในบ้าน)"); freed up >40% vertical viewport height |
| 43 | Street flooding warning buried under generic cautions | Dynamic warning `street_flooding_despite_channels` separated into a prominent red/orange alert banner at the top |
| 44 | Point check flooded with newly ingested BMA gauges lacking predictive models or stale (e.g. `WL.JKK.01` 2 days old) | Stale stations suppressed; point check categorizes stations into **📈 สถานีที่มีการคาดการณ์ (12–72 ชม.)** (HII/RID with ML forecast) and **📍 สถานีคลอง/แม่น้ำใกล้จุดนี้** (active local gauges) |
| 45 | Traffy flood hotspot circles barely visible on map (`fillOpacity: 0.14`, `weight: 0`) | Opacity boosted to 0.30–0.55 with 1px `#6a1b9a` stroke: crowd-verified street flooding clusters now pop out distinctly on OpenStreetMap tiles |
| 46 | Dead private artifact link in point card | Linked to official BMA drainage department (`dds.bangkok.go.th`) alongside curated route guidance |

### Round 7 (2026-09-27 ~08:00 UTC): D-041 outlook gave a verdict without evidence (v0.6.1, D-042)
Live `/api/point` probes on 4 real coordinates (KI-223), before and after the fix:
| Point | Area confidence | Before (v0.6.0) | After (v0.6.1) |
|---|---|---|---|
| 14.30, 100.20 (0 gauges in 8 km) | `none` | ✅ "สถานการณ์ปกติ … ความเสี่ยงน้ำท่วมต่ำ" (18 mm called "light") | ℹ️ "ไม่มีสถานีวัดน้ำใกล้พอ …" + rain condition, no verdict |
| 13.82, 100.60 (1 gauge, 5.6 km) | `very_low` | 🌧️ "moderate / rising" — **contradicted the overview card**, which already showed no verdict at this confidence | Consistent with the card: no canal claim; rain/reports still shown |
| 13.75, 100.50 (1 gauge at 0 km, tidal noise) | `low` | 🌧️ "rising" from one river gauge's routine tide swing | Trend now needs a same-water-body majority; a lone river gauge no longer drives risk |
| 13.60, 100.95 (0 gauges, heavy rain) | `none` | 🌧️ "moderate" (rain only — this one was already reasonable) | Same outcome, now with an explicit `basis: ["rain"]` footnote |
| — | — | — | See [D-042](plan/DECISIONS.md) for the distance/agreement evidence behind the confidence bands, and [KI-223](KNOWN_ISSUES.md) for the bug detail. |

### Round 8 (2026-09-27 ~09:40 UTC): issue #1 "ฝน -27 มม. แปลว่าอะไร" (branch, KI-224)
| # | Finding | Done (branch `research/nationwide-scope`) |
|---|---|---|
| 47 | Owner's phone screenshot: `ฝน 24 ชม.: ~27 มม. (Open-Meteo)` read as "−27 mm", with no sense of little vs a lot, and no hint that it is a forecast | `ฝน 24 ชม. ข้างหน้า: ฝนปานกลาง (ประมาณ 27 มม.)` + a 2-line TMD legend ("ฝนหนักช่วงสั้นทำถนนท่วมได้แม้ยอดรวมไม่มาก"); all user-facing `~` removed; unknown → "ไม่มีข้อมูล". Checked at 390 px on a throwaway preview of the branch (same pin, Bang Kapi) |

### Round 9 (2026-09-27 ~17:30 UTC): issues #2 and #3, v0.6.5 review bugs (v0.7.0, D-051)
| # | Finding | Done |
|---|---|---|
| 48 | Issue #3 (kcskrittapas): 3 stacked boxes, small headline, emojis, disclaimers in the way, no district name | One panel: kicker + ⓘ, 21 px headline, "ปัจจัยที่ใช้คาดการณ์" with dot + word per factor, district line from `/api/reverse`, caveats behind ⓘ (owner). Checked at 390 px at 13.776,100.64 · 13.70,100.50 · 14.30,100.20 |
| 49 | Wireframe coloured the mixed-canal factor red | Grey "ประเมินไม่ได้" when gauges are far or disagree (owner: follow the gate) |
| 50 | Issue #2: report form long in the panel | Full-width button → `<dialog>` popup; opened/closed via CDP-driven headless Chrome; baseline 57 reports/24 h to compare |
| 51 | Review: river gauge shown as "nearest canal"; ⓘ in a list opened the station | Server-side canal-only rule (≤ 3 km); capture-phase click handler; both verified |
| 52 | Rain words "ไม่มีฝน"/"ฝนเล็กน้อย" 2.5:1 contrast | grey-500 / cyan-700 (≥ 4.5:1) |

### Round 10 (2026-09-28 ~03:00–04:00 ICT): owner's panel review, issues #4/#5, a Bangkok resident's check (v0.10.0)
Persona: a resident of Lat Phrao / Chatuchak on a phone at night during the flood, asking "is the water near me going up or down, will my street flood tonight, when will it drop?"
| # | Finding | Done |
|---|---|---|
| 53 | "ระดับน้ำในคลอง · ประเมินไม่ได้" almost everywhere (83 % of a 64-point grid) although forecasts exist | Nearest-gauge gate (D-054): 39 %; the canal factor leads with the nearest canal, its state and 24/48 h change |
| 54 | The outlook sentence repeated the rain amount shown in the rain factor | Sentence keeps the TMD word + warning only (D-055) |
| 55 | "สถานีรอบจุดให้ผลต่างกัน … (41 สถานีใน 8 กม.)" was long and came first | Folded into "สถานีอื่นรอบจุด (N แห่งใน 8 กม.)"; nearest canal first, "ห่างเกิน 3 กม." note when far |
| 56 | Nearest canal is usually a BMA gauge — it had no trend at all | 1-year BMA history from HII (D-054); honest result: skill mainly at 12 h |
| 57 | Wanted a 48 h line in the panel, lists and station sheet; lists showed only 12 h | 48 h everywhere, unproven = dashed "? 48 ชม." + range only; lists show 24 h (D-055) |
| 58 | Recovery window "30 ก.ย. 01:12 – 2 ต.ค. 05:12" read as exact | Dates only for windows ≥ 24 h, whole hours otherwise (KI-231) |
| 59 | Station sheet said "steady" three times | Median note dropped when the 12 h chip exists |
| 60 | Area word "เตือนภัย (ใกล้ตลิ่ง)" next to a BMA gauge saying "คลองเต็ม" | Area uses the combined chip words ("ใกล้ตลิ่ง/คลองเต็ม") |
| 61 | Issue #5: kicker vs factor heading and the three detail lines had different styles | One heading style; every factor "title · word" + one grey detail style |
| 63 | Owner: nearest canal (relay-only BMA gauge) showed no trend; the summary block was not understood | Second line "คลองใกล้ที่มีคาดการณ์"; "when it may drop" on each line; plain one-sentence summary (v0.10.2, KI-232) |
| 62 | Issue #4: drag signifier did nothing on mobile | Real grip; pull down from the top (sheet at scroll 0) closes, > 90 px; ✕ kept. Verified with CDP touch events: short pull snaps back, long pull closes, scrolled content and mid-sheet pulls never close |

### Round 11 (2026-09-27 ~20:50–21:20 UTC): one trend format, compact canal factor, text read-through (v0.11.0, D-056)
| # | Finding | Done |
|---|---|---|
| 64 | 24 h vs 48 h rows had different grammar and chip content | Aligned rows `ใน N ชม. · chip · range · ⓘ` in list, panel and sheet |
| 65 | 24 h showed "→ ทรงตัว" from the "no change" model; 48 h withheld a direction | One rule: direction only where a real model won the backtest at that horizon, else "? ไม่แน่ชัด" |
| 66 | Canal factor long (two gauges, far notes, counts) | One gauge + rows + drop line; details folded; label for a borrowed forecast |
| 67 | Sheet: emojis, duplicate trend headline, notes above the trend | Trend block first; emojis removed; BMA margin line under the headline; source/datum in ⓘ |
| 68 | "ใกล้ตลิ่ง" 158 cm below the bank (CPY015) | "น้ำเต็มลำน้ำ 91 %" |
| 71 | Owner: the "can't summarise" text repeated the reason at length | Short headline + rain condition only; the reason stays in the canal factor (v0.11.2, KI-235) |
| 70 | Owner: one gauge name bold and one not; labels ran into long lines (v0.11.0) | One block per gauge: label line, bold name · distance · pill, then rows; divider between gauges (v0.11.1, KI-234) |
| 69 | Kicker "12–24 ชม." above 24/48 h rows; "ท่วมถึงเข่า … 2" | "คาดการณ์ข้างหน้า"; "2 ราย" |

### Round 12 (2026-09-28 17:30–18:30 UTC): resident at home, live site on phone and desktop (v0.14.0, D-060, D-061)
Real walk with `scripts/ux_walk.py` (Playwright, Android phone 390×844 with GPS at Bang Khen, and 1440×900): home → "สถานีใกล้ฉัน" → search "ลาดพร้าว" → map + tap → Chao Phraya tab → station sheet. List in 1.6–1.8 s, no console errors; phone 0.5–0.7 MB, desktop 1.6–1.9 MB (map tiles).
| # | Finding (as a resident) | Done |
|---|---|---|
| 64 | Six gauges stuck at 1.00 m / 0.40 m showed statuses ("ถึงตลิ่ง 25–50 %") | Hidden with "ค่าค้าง" (KI-241) |
| 65 | Rows "? / ? / → ทรงตัว" under a chart that clearly falls (owner screenshots KPM.04, LBK.03, PWT.03) | Rows follow the measured trend; ±5 cm "ทรงตัว"; 48 h for slow falls (D-060, KI-242) |
| 66 | The pin panel said "ล้นตลิ่ง" but hid the good news (falling 13 cm/day) far below | One line under the headline: "คลองใกล้สุด 24 ชม. ที่ผ่านมา: ลดลง 14 ซม." |
| 67 | No "what should I do" | "ควรทำอะไรตอนนี้" collapsed, 3 bullets by risk level, DDPM advice (D-061) |
| 68 | GPS panel showed "13.854, 100.588" | District name ("อนุสาวรีย์, บางเขน") |
| 69 | ~40 % of the first phone screen was header, banner, chips and operator lines | Operator lines behind "รายละเอียดข้อมูล" (small gain: list starts ~50 px higher) |
| 70 | Map opened at Ayutthaya scale; Bangkok a corner | Opens on Bangkok when the region is กทม. |
| 71 | Chao Phraya tab started at Nakhon Sawan with a long legend | Bangkok first; one-line legend, the rest behind "อ่านกราฟนี้" |
| — | Not done: tapping a crowded area hits a station instead of a point check; the header + disclaimer still take ~25 % of the first screen; no real residents interviewed yet | Next round |

### Round 13 (2026-09-28 18:30–20:10 UTC): consistency proof across views and viewports (v0.15.0, D-062)
Owner: "keep number to show"; "วิธีคาดการณ์ … collapsed"; "we do not need ควรทำอะไรตอนนี้"; "prove the consistency of panel and text"; "validate the UI in many possibilities". `scripts/ux_consistency.py`: 310 sheets, 67 pins (8×8 Bangkok grid + riverside, Ayutthaya side, outside the network), 405 panel blocks, 1,261 rows, viewports 360/390/768/1440 px.
| # | Finding | Done |
|---|---|---|
| 72 | Measured rows had no numbers; restoring the past range made "ลดลง −7 ถึง +14" | "ราว −7 ซม." = trend continued, damped |
| 73 | Headline "ทรงตัว"/"12 ชม. เพิ่มขึ้น" above falling 24/48 h rows (7 pins) | Headline = canal-factor gauge at 24 h; falling wording for high canals |
| 74 | List "→ ทรงตัว" vs sheet "? ไม่แน่ชัด" (VLGE20) | Every view walks 12→24→48 h |
| 75 | Model chip against its range (3 rows) | Direction only when the range agrees |
| 76 | Pill repeated the factor word; measured line twice; action guide and method line too long | Removed / collapsed |
| 77 | BKK008 recovery "หลัง 72 ชม." while 1 cm over the bank and falling | Window keeps its early end |
Final run: 0 issues in C1–C3, C5, C6; 2 accepted (two gauges, same status).

## 3. Still missing (prioritised)
1. **Polder-aware "near me"**: pick the gauge in the user's water body, not the nearest one (APPROACH §13). This matters most for P2.
2. **The main domain loads behind a Cloudflare challenge** ([KI-506](KNOWN_ISSUES.md)). LINE previews fail and slow phones wait. Owner action.
3. **Alerts** (LINE OA or Web Push) for a saved station: Q7.
4. **Khlong / rain view for P2**: rain-gauge totals near the user, and drainage-time ranges for khlong gauges (Phase 2).
5. **Offline / low-bandwidth**: a service worker that caches the last snapshot. Today the page itself is ≈ 42 KB uncompressed (HTML + JS + CSS), plus Leaflet, map tiles and a web font.
6. **Accessibility pass**: contrast of the "watch" colour (darkened to `#b58900`), and screen-reader labels on the chart and chips (partly done).
7. **Buddhist-era dates** (Q8). The UI uses the `th-TH` locale, which already shows day and month; years are not displayed.
8. **Real users**: 5–10 short interviews (riverside, polder, elderly) and a look at feedback counts after one week.

## 4. How to re-run this check
- Consistency proof (all sheets, pins, 4 viewports): `python3 scripts/ux_consistency.py [out.json]`.
- Real walk (phone + desktop, GPS, search, map tap, river tab, sheet): `python3 scripts/ux_walk.py <out_dir>` (needs Python Playwright; Chromium runs with `--no-sandbox` as root).
- Screenshots: `chrome --headless=new --no-sandbox --window-size=390,844 --virtual-time-budget=8000 --screenshot=m.png http://localhost:3000/` (add `#s=BKK021` for the sheet).
- Walk each persona's question in §1. Can it be answered in ≤ 10 s on the phone screenshot without scrolling past the first screen?
