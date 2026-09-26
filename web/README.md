# `web/` — Thai, mobile-first web app

> **Status:** empty scaffold. Built in **Phase 3** ([plan](../docs/plan/phase-3-web-app.md)). The framework is still an open question ([OPEN_QUESTIONS.md](../docs/plan/OPEN_QUESTIONS.md)).

## Scope
- The UI is **entirely in Thai**, with an i18n-ready structure so English can be added later. Use a Thai font (Noto Sans Thai or Sarabun).
- Station map coloured by status (ปกติ / เฝ้าระวัง / เตือนภัย / วิกฤต relative to ระดับตลิ่ง).
- "ใกล้บ้านฉัน": the controlling station(s), the trend for the next 12 hours, and a **recovery date range with its conditions**.
- Station page: observed levels, the bank-level line, a forecast fan chart (12 h / 1 / 2 / 3 / 7 d), tide, upstream flow and rain.
- Citizen mode is the default; expert mode is a toggle.
- Every screen shows the last-updated time, source attribution, the disclaimer, official links and hotlines.

## Rules
Talk only to our own API. It is served as a static build on Cloudflare Pages, and it has to load fast on weak mobile connections. The UX rules are in [GUIDELINES §6](../docs/GUIDELINES.md).
