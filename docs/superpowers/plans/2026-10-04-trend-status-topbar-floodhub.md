# Two-dimension status, จับตา split, map box, top bar, Flood Hub, MODELS.md — Implementation Plan

> Executed inline (owner: "continue all to finish"). Spec: `docs/superpowers/specs/2026-10-04-trend-status-topbar-floodhub-design.md`.
> Tests: `bash $SCRATCH/t.sh` (pytest in the worker image, source mounted). Every task: failing test first, then code, suite green, commit.

**Global constraints:** words already in the app (ทรงตัว, ล้นตลิ่ง, ใกล้ตลิ่ง/คลองเต็ม, เฝ้าระวัง, ยังรับน้ำได้, "อีก/ในอีก N ชม.");
groups "น้ำยังขึ้น" / "ทรงตัวหรือลดลง"; no official-warning words; secrets only in `.env`, the Flood Hub key only in
the `X-Goog-Api-Key` header; bump `?v=`; v0.22.0; HANDOFF updated early and at the end.

| # | Task | Tests (written first) | Files |
|---|---|---|---|
| 0 | HANDOFF checkpoint (in-progress state) | — | HANDOFF.md |
| 1 | Remove GISTDA everywhere, stop the collector | `test_worker` (no gistda task), `test_wording` (no satellite strings), `test_explain`/`test_point` satellite tests removed | collectors, worker, api, explain, point, risks, app.js, ux_consistency |
| 2 | Sheet rows and chart from one forecast run | `test_api`: station endpoint picks the run whose issue time = the snapshot's | api |
| 3 | `trend_group` rule (Python `status.py` + JS `trendGroup`) | `test_status` (forecast sure up/down/steady, unsure → measured, none); wording test that JS mirrors it | status.py, app.js |
| 4 | จับตา: over-bank split by trend group; satellite group gone | `test_risks` (split + order + unknown line) | risks.py, app.js |
| 5 | River cards with level + trend counts; ลำน้ำอื่น as cards | `test_wording` (card fn shared, both labels) | app.js, style.css |
| 6 | Map layer box (legend checkboxes, remembered, phone collapse) | `test_wording` (one box, no top-left box, categories) | app.js, style.css |
| 7 | Top bar: collapsible, rain line with place, urgent line, desktop disclaimer merge | `test_api` (rain by region carries the place), `test_wording` (strings, collapse state) | api, app.js, index.html, style.css |
| 8 | Flood Hub: env + compose, collector `google_floodhub`, tables, validation script | `test_parsing` (gauges/status/models/forecast), `test_worker` (daily task) | .env.example, docker-compose.yml, config, collectors, schema, research/ |
| 9 | docs/MODELS.md (Thai summary + English detail, ADR-style, data wish-list) | — | docs/MODELS.md, README, docs/README |
| 10 | Live checks (C13 out, C15 re-check, C17 split, C18 trend rule, C19 urgent line), deploy, visitor screenshots 390/1440, release v0.22.0, all docs | live run 0 findings | scripts/ux_consistency.py, docs/* |

Ruling: compact plan (task table, not full code per step) — the spec carries the exact rules and the owner asked to
finish without further stops; cost if wrong: less step detail for another executor.
