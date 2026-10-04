# Two-dimension status, จับตา sub-groups, map layer box, top bar, Flood Hub, models doc — design

**Date:** 2026-10-04 · **Status:** owner answers in Grillme rounds 1–2 (2026-10-04 ~09:45–10:00 UTC); awaiting spec review
**Decisions to record:** D-083 (trend group rule), D-084 (GISTDA removed), D-085 (map layer box), D-086 (top bar),
D-087 (Flood Hub collected and validated), D-088 (MODELS.md)

## 1. Trend group: "น้ำยังขึ้น" / "ทรงตัวหรือลดลง" (one rule for the whole app)

Owner: "Forecast if sure direction: higher, lower, stable. ไม่แน่ชัด can suggest with measured recent change as fallback.
In the description, we can show two labels as summary (if possible)."

- `trend_group(station) -> "rising" | "flat_or_falling" | None` in `floodwatch/status.py` (pure, Python) and the same
  rule in `app.js` (`trendGroup(s)`), tested to agree on the live station list.
- **Forecast first:** the 24 h row (`change24`, else `change12`) when it is *sure*: a direction the model proved
  (`directional` in app.js: rising/falling with a real model and a likely range that agrees) or the narrow
  "→ ทรงตัว" (likely range within ±5 cm). Rising → `rising`; falling or steady → `flat_or_falling`.
- **Measured fallback** when the row is "? ไม่แน่ชัด" or missing: the recent measured pace (`observed24` with
  `change6_cm`, the model's own `recent` rule: the smaller of the 24 h and 6 h pace, none when they disagree). ≥ +2 cm
  over 24 h → `rising`; otherwise `flat_or_falling`. Neither available (stale, no data) → `None` (not counted).
- **Two labels** where both exist, in summaries and sheets: `วัดได้ ↗ · คาด ?` (measured, then forecast), using the
  app's arrows; the group is decided by the rule above.
- **Level dimension** stays the app's four statuses and colours (ล้นตลิ่ง · ใกล้ตลิ่ง/คลองเต็ม · เฝ้าระวัง ·
  ยังรับน้ำได้; ไม่ทราบ) — no new words.

## 2. จับตา

- 🔴 ล้นตลิ่งแล้ว splits into two sub-groups: **"น้ำยังขึ้น"** (first) and **"ทรงตัวหรือลดลง"**, each with its count
  and the province rows (tap → gauges with `เกินตลิ่ง N ซม. · วัดได้ ↗ · คาด ?`). Gauges whose trend is unknown
  (`None`: stale or no readings for a trend) go to a third line "ไม่ทราบแนวโน้ม", shown only when it has gauges.
- Keep 🟠 อาจถึงตลิ่ง, 🟠 น้ำเหนือกำลังมา, 🟡 น้ำขึ้นเร็ว, 🌧 ฝนหนักคาดการณ์ (owner: "It is nice").
- 🛰 group removed (GISTDA gone; a future source replaces it).

## 3. River tab summaries (main rivers and ลำน้ำอื่น alike)

- One card format for every waterway: name · `N สถานี` · level counts (ล้นตลิ่ง N · ใกล้ตลิ่ง N …) · trend counts
  (`น้ำยังขึ้น N · ทรงตัวหรือลดลง N`). "ลำน้ำอื่นใน<จังหวัด>" becomes cards like the rivers (tap → its gauges),
  no longer full rows.

## 4. GISTDA removed (owner: "Hide everywhere and stop the collector")

- Remove: pin factor line (`explain._sat_line`), AI story sentence, station-sheet line, map toggle, จับตา group,
  `/api/point` `satellite`, `/api/satellite`, `sat_near_rai`, `sat_summary`; collector `gistda_flood` removed from
  FORECASTER_TASKS. Table `sat_flood` kept (empty) for a future source; code and tests deleted, not commented out.
- Docs: D-071/D-078 marked superseded; live checks C13 removed.

## 5. Map layer box (owner chose "One box: legend with checkboxes")

- The legend is the switch: ☑ per status (with count), "○ = ยังไม่มีพยากรณ์" (toggles ring gauges), ☐ DWR posts,
  ☑ Traffy. One box bottom-right; on phones collapsed to "ชั้นข้อมูล ▾". Choices remembered (localStorage). The
  top-left box and the "ไม่มีพิกัด" line go. Hidden categories never change counts elsewhere.

## 6. Top bar (owner chose all four)

- **Collapsible:** one line `🔴 53 · 🟠 75 · 🟡 133 · 🔵 694 · ⚪ 85 ▾`; open = today's chips and lines. Desktop starts
  collapsed, phones open; remembered.
- **Rain line names the place:** `🌧️ ฝนมากสุด 24 ชม. ที่ผ่านมา: 93 มม. ที่ <อำเภอ> <จังหวัด>` (from `/api/rain`
  `by_region[*].measured`), forecast part likewise `คาดสูงสุด … ที่ <จังหวัด>`.
- **One urgent line** only when gauges are over the bank *and* "น้ำยังขึ้น": `🔴 ล้นตลิ่งและน้ำยังขึ้น 12 สถานี
  (อยุธยา 5 · ปราจีนบุรี 3 …) ›` → opens จับตา. Follows the where-row; nothing when none.
- **Shorter disclaimer** on desktop (≥ 900 px): merged into the header line.

## 7. Google Flood Hub (owner: "Validate first, then a 3–7 day outlook")

- `.env`/`.env.example`/compose: `GOOGLE_FLOOD_API_KEY` passed to worker/forecaster only; key in the
  `X-Goog-Api-Key` header, never in a URL, never archived in clear (the archive stores responses, not requests).
- Collector `google_floodhub` daily (forecaster): gauges, latest statuses, gauge models (thresholds), the latest
  forecast per gauge → tables `gfh_gauge`, `gfh_status` (history kept), `gfh_forecast`.
- Validation script now and after 1–2 weeks: each Google point vs our gauges within 15 km on the same river/basin:
  SEVERE/ABOVE_NORMAL vs our over-bank/near-bank; Google's forecast trend vs our measured trend afterwards.
- Nothing shown until validated (D-087 revisit). Terms of use checked and recorded in SOURCES.

## 8. docs/MODELS.md (English + Thai summary)

- Thai one-page summary; concept (what we answer, gauges vs bank, horizons), data flow, every method in the ladder
  (persistence, tide, trend, tide_trend, recent, star) with parameters and the backtest gate, quantiles and
  conformal bands, bank chance, track records, risk groups, trend groups, upstream learning, rivers/sub-basins, QC;
  ADR-style "tried → result → why" for each choice (links to D-IDs and research files); limits; data wish-list
  (what more data would raise usefulness or skill, ranked).

## 9. Also

- Sheet rows and chart from one forecast run (the C15 race: rows from the 60 s snapshot, chart from the newest run).
- Tests first for every rule (trend_group both languages, จับตา split, river card counts, urgent line, top-bar
  wording, GISTDA gone, Flood Hub parsing); live checks: C13 removed, C15 re-check after reload, C17 split, new C18
  (trend group = rule on every list row), C19 (top bar urgent line = จับตา count).
- Visitor checks at 390 and 1440 px; release v0.22.0; docs.
