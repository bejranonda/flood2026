# docs/ — Documentation index

> Maintained documentation for BKK FloodWatch 2026. When `research/` and `docs/` disagree, **docs/ wins**.

## Reading order
1. [../README.md](../README.md): what the app does, screenshots, API, FAQ (public front page) · [../HANDOFF.md](../HANDOFF.md): live state and operations
2. [brief/first_prompt.md](brief/first_prompt.md): the original brief (the owner's words)
3. [plan/PLAN.md](plan/PLAN.md): roadmap, phase gates, where we are
4. [KNOWLEDGE.md](KNOWLEDGE.md): the hydrology and domain facts you need
5. [ARCHITECTURE.md](ARCHITECTURE.md): how the system fits together
6. [SOURCES.md](SOURCES.md): every data source, how to call it, and its test status
7. [APPROACH_AND_METHODS.md](APPROACH_AND_METHODS.md): the calculations and models, including the spatio-temporal framework
8. [GUIDELINES.md](GUIDELINES.md): rules for engineering, modelling, data ethics and UX
9. [KNOWN_ISSUES.md](KNOWN_ISSUES.md): limitations and workarounds (KI-IDs)
10. [UX_VALIDATION.md](UX_VALIDATION.md): resident personas, UX findings and what's still missing
11. [OWNER_ACTIONS.md](OWNER_ACTIONS.md): what the project needs from the owner, with steps and status

## Map
| File | Purpose | Update when… |
|---|---|---|
| [plan/PLAN.md](plan/PLAN.md) | Roadmap, gates G0–G4, risks | A phase starts or ends |
| [plan/phase-0 … phase-5](plan/) | Task checklists and exit criteria per phase (phase 5 = nationwide, validated 2026-09-27) | Tasks progress |
| [plan/DECISIONS.md](plan/DECISIONS.md) | Decision log (D-001…) | A decision is made or superseded |
| [plan/impact-kaeng-krachan.md](plan/impact-kaeng-krachan.md) | `/impact` pilot for ONWR/RID engineers: design, replay result, data needs (D-099) | The pilot or its data change |
| [plan/OPEN_QUESTIONS.md](plan/OPEN_QUESTIONS.md) | Questions for the owner | Asked or answered |
| [SOURCES.md](SOURCES.md) | Source registry (the brief's Phase 0 format) | A source is tested, changes or fails |
| [KNOWLEDGE.md](KNOWLEDGE.md) | Domain knowledge, stations, datums, contacts | A fact is learned or corrected |
| [MODELS.md](MODELS.md) | How the app calculates: formulas, parameters, model choices, hard cases, decisions, data wish-list (Thai summary); §12 how the models improved release by release, measured as issued | A model, threshold or rule changes |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | Pitfalls with status | Something breaks or is worked around |
| [APPROACH_AND_METHODS.md](APPROACH_AND_METHODS.md) | Methods (= the brief's `docs/METHODS.md`) | A method changes |
| [GUIDELINES.md](GUIDELINES.md) | Standards | A standard changes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, live API, storage, security, repo layout | The architecture changes |
| [UX_VALIDATION.md](UX_VALIDATION.md) | Personas, UX review findings, gaps | The UI changes, or user feedback arrives |
| [OWNER_ACTIONS.md](OWNER_ACTIONS.md) | Everything needed from the owner, with steps, cost and verification | You need something from the owner, or they did it |

## Evidence markers used across the docs
| Mark | Meaning |
|---|---|
| ✅ | Confirmed: live call, observed data, or cited source |
| 🟡 | From careful research or documentation; not re-checked yet |
| ⚠️ | Unverified or indicative. Don't hard-code it; there's a task to verify it |
| 🔴 | Blocked or unavailable |
| 🔑 | Needs a key or registration |
| ❌ | Refuted |

Research validity (🟢 reliable / 🟠 mixed) is explained in [../research/README.md](../research/README.md).

## Checks and assets
| Path | What |
|---|---|
| [../scripts/ux_consistency.py](../scripts/ux_consistency.py) | UI consistency proof: every Bangkok-area sheet plus a sample per region, a pin grid, national pins (C7) and 4 viewports (run before a release, D-062, D-064) |
| [../scripts/backtest_nationwide.py](../scripts/backtest_nationwide.py) | Backtest report: Bangkok 40-gauge regression and nationwide gauges with/without rain cells and learned upstream (D-064) |
| [superpowers/specs/](superpowers/specs/) · [superpowers/plans/](superpowers/plans/) | Design specs and implementation plans agreed with the owner (v0.16 nationwide parity) |
| [../scripts/ux_walk.py](../scripts/ux_walk.py) | Real-user walk on a phone and a desktop (screenshots, timings, console errors) |
| [../scripts/owner_status.py](../scripts/owner_status.py) | What is still open for the owner |
| [img/](img/) | README screenshots (WebP; retake with `ux_walk.py` when the UI changes) and `social-preview.png` (GitHub social preview; rebuild with `scripts/make_social_images.py`) |
