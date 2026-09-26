# Phase 3 — Web app (UI entirely in Thai)

> **Status:** ⏳ after G2. **Gate G3:** UX review by the owner (ideally also a few Thai residents).

## Goal
A mobile-first, calm and accessible Thai app that answers the two golden questions: **"น้ำแถวบ้านจะขึ้นหรือลง?"** and **"เมื่อไหร่จะกลับสู่ปกติ?"**. It must be honest about uncertainty and fast on weak connections.

## Inputs
[GUIDELINES §6](../GUIDELINES.md) · [KNOWLEDGE §6](../KNOWLEDGE.md) · [APPROACH §13–§15](../APPROACH_AND_METHODS.md) · scaffold: [web](../../web/README.md), [api](../../src/floodwatch/api/README.md)

## Tasks
- [ ] Choose the frontend framework ([OPEN_QUESTIONS](OPEN_QUESTIONS.md) Q9); set up Cloudflare Pages
- [ ] Public API endpoints (`/stations`, `/stations/{id}/observations`, `/stations/{id}/forecast`, `/near`, `/about/model-skill`), each with data age, attribution, a `degraded` flag, the model level and its conditions
- [ ] Map (MapLibre or Leaflet) of stations coloured ปกติ / เฝ้าระวัง / เตือนภัย / วิกฤต relative to the bank level
- [ ] "ใกล้บ้านฉัน": GPS or address → **controlling water body** (polder or river), then the trend with a range, the recovery date range and conditions, and a probabilistic depth category; optional floor height
- [ ] Station page: observed levels + bank line, forecast fan (12 h / 1 / 2 / 3 / 7 d), tide, upstream flow, rain
- [ ] Citizen mode (default) and expert mode
- [ ] "เกี่ยวกับแบบจำลอง" page: methods and skill per station and horizon, with limitations
- [ ] Attribution, disclaimer, official links; **re-verify every hotline** ([KNOWLEDGE §6.2](../KNOWLEDGE.md))
- [ ] Buddhist-era date option; Noto Sans Thai or Sarabun; accessibility checks; i18n-ready
- [ ] Optional: LINE or Web Push alerts for subscribed stations ([OPEN_QUESTIONS](OPEN_QUESTIONS.md) Q7)
- [ ] Owner UX review → **stop for G3**

## Exit criteria (G3)
The owner approves the UX. Every screen shows data age and attribution. There are no minute-precise countdowns. Stale data is visibly stale.
