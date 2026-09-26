# Phase 3 — Web app (UI entirely in Thai)

> **Status:** 🟡 MVP live at https://flood.autobahn.bot (parallel mode, D-012). Mobile-first redesign and feedback shipped 2026-09-26; heuristic review in [UX_VALIDATION](../UX_VALIDATION.md). **Gate G3:** UX review by the owner (ideally also a few Thai residents).

## Goal
A mobile-first, calm and accessible Thai app that answers the two golden questions: **"น้ำแถวบ้านจะขึ้นหรือลง?"** and **"เมื่อไหร่จะกลับสู่ปกติ?"**. It must be honest about uncertainty and fast on weak connections.

## Inputs
[GUIDELINES §6](../GUIDELINES.md) · [KNOWLEDGE §6](../KNOWLEDGE.md) · [APPROACH §13–§15](../APPROACH_AND_METHODS.md) · scaffold: [web](../../web/README.md), [api](../../src/floodwatch/api/README.md)

## Tasks
- [x] Frontend: plain HTML/CSS/JS served by FastAPI behind the tunnel (≈ 42 KB, no build step). A framework and Pages remain optional (Q9)
- [x] Public API: `/api/stations`, `/api/stations/{code}` (history + forecast + feedback counts), `/api/near`, `/api/stats`, `/api/profile`, `/api/reports`, `/api/rain`, `/api/feedback`, `/api/health` ([ARCHITECTURE §1.1](../ARCHITECTURE.md))
- [ ] `/about/model-skill` and a `degraded` flag per response
- [x] Leaflet map coloured by status vs bank, with a legend and Traffy report cells
- [x] **Summary strip:** status chips (tap to filter), rising/falling counts, Bangkok 24 h rain, reporting freshness (focus + whole network)
- [x] **Mobile:** tabs, bottom-sheet detail, ≥ 44 px targets, search, share + deep link `#s=CODE`
- [x] **Chao Phraya profile** tab (gauges only, north → south, D-019)
- [x] **Citizen feedback** in the station detail and "near me" (D-020)
- [x] **Point check** for places with no gauge: tap the map or use GPS (D-021); shareable `#p=` links
- [x] Chart day markers (rough time axis)
- [x] Optional Workers AI triage of notes (D-022); site independent of AI
- [~] "ใกล้บ้านฉัน": nearest gauges by distance with a caveat (done); **still to do:** GPS or address → **controlling water body** (polder or river), then the trend with a range, the recovery date range and conditions, and a probabilistic depth category; optional floor height
- [~] Station detail: observed levels + bank line + forecast fan (72 h), 24 h outlook (peak window, chance of reaching the bank), recovery range (done); upstream flow and rain panels still to do
- [ ] Citizen mode (default) and expert mode
- [ ] "เกี่ยวกับแบบจำลอง" page: methods and skill per station and horizon, with limitations
- [ ] Attribution, disclaimer, official links; **re-verify every hotline** ([KNOWLEDGE §6.2](../KNOWLEDGE.md))
- [ ] Buddhist-era date option; Noto Sans Thai or Sarabun; accessibility checks; i18n-ready
- [ ] Optional: LINE or Web Push alerts for subscribed stations ([OPEN_QUESTIONS](OPEN_QUESTIONS.md) Q7)
- [ ] Owner UX review → **stop for G3**

## Exit criteria (G3)
The owner approves the UX. Every screen shows data age and attribution. There are no minute-precise countdowns. Stale data is visibly stale.
