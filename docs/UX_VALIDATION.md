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
| 16 | "What if someone writes that they're trapped?" | Keyword rules flag emergency notes instantly, and the page shows **1669 / 1784 / 191** with "this site has no responders" |

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
- Screenshots: `chrome --headless=new --no-sandbox --window-size=390,844 --virtual-time-budget=8000 --screenshot=m.png http://localhost:3000/` (add `#s=BKK021` for the sheet).
- Walk each persona's question in §1. Can it be answered in ≤ 10 s on the phone screenshot without scrolling past the first screen?
