# PLAN.md — Roadmap, phase gates and status

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-26
> **Mode:** archive-first, **strict phase gates**. Each phase ends with a report and **stops until the owner approves** (D-002).
> **Brief:** [docs/brief/first_prompt.md](../brief/first_prompt.md) (the "Option 2" prompt plus the updated Phase 1 and Phase 4)

## Where we are

| Item | Status |
|---|---|
| Documentation reorganised and reconciled; research validated claim by claim | ✅ 2026-09-26 |
| Infrastructure: VPS + Cloudflare Tunnel for flood.bejranonda.com | ✅ live (owner-reported); app not deployed |
| **Phase 0 — source verification** | 🟡 **started**: first probes done from the dev host (Germany). **Still needed: the same tests from the production VPS, then the report** |
| Phases 1–4 | ⏳ not started |

## Phases and gates

| Phase | Goal | Key deliverables | Gate (owner approves) |
|---|---|---|---|
| **0** [Source verification](phase-0-source-verification.md) | Know exactly which sources work from the VPS, how, and under what terms | [SOURCES.md](../SOURCES.md) filled in the brief's format, with every row tested from the VPS; station inventory; recommended source set; permission emails sent | **G0:** approved source set → **collectors start immediately** |
| **1** [Ingestion and archive](phase-1-ingestion-archive.md) | Capture every reading from now on, and backfill everything available | Collectors, raw archive + R2, TimescaleDB/PostGIS schema, QC, backfill, source health, **tested restore** | **G1:** ≥ 7 days of continuous collection, backfill done, restore drill passed |
| **2** [Forecasting](phase-2-forecasting.md) | Honest, calibrated forecasts that beat the baselines | Backtest harness, L0–L2, L3 physics (tide fit, lags, rating curves, polders), L4/L5, recovery estimator, depth module, skill report | **G2:** acceptance gate passed per station × horizon (or a documented fallback) |
| **3** [Web app](phase-3-web-app.md) | A Thai, mobile-first public app answering the two golden questions | Public API, map, "ใกล้บ้านฉัน", station pages, model page, attribution, disclaimers | **G3:** UX review by the owner (and ideally a few Thai residents) |
| **4** [Deployment and ops](phase-4-deployment-ops.md) | Survive peak traffic and failures; redeploy in under 1 hour | Edge caching, monitoring and alerts, backups, runbooks, security hardening | **G4:** load test, redeploy drill, and alert test passed |

## Critical path and timing principles
1. **Phase 0 → G0 as fast as possible.** Every flood day not archived is lost for good, and it's the most valuable training and validation data we will ever get.
2. **Right after G0:** start the HII collectors and the backfill (`getGraphFirst` gives 30 days; go further back with `getGraph`), and archive **every** Open-Meteo run. This is why a minimal part of Phase 1 infrastructure (compose + DB + R2) is the first thing built after G0.
3. **Build the backtest harness and baselines L0–L2 before any ML** (Phase 2). A model that can't beat persistence isn't shown.
4. **No public UI before G2 and G3** (D-002). If the owner decides to publish an interim "observed levels only" page during the event, that's a new decision (D-xxx) with its own rules: observed data, age and attribution, no forecasts.

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Sources block the VPS (BMA already blocks non-Thai IPs) | Missing Bangkok khlong detail | Test from the VPS; ask BMA; a Thai collector node ([KI-101](../KNOWN_ISSUES.md)) |
| HII changes or removes its public endpoints | Core feed lost | Raw archive; request a formal agreement with HII; adapter isolation |
| Key stations missing (C.29A, Memorial Bridge, Fort Chula) | Weaker regime B | Find RID and Navy feeds; interim routing and our own tide fit ([KI-109](../KNOWN_ISSUES.md)) |
| Too little history for extremes | Poor ML skill | Backfill; GloFAS 1984→; global models; physical baseline |
| Overconfident public messages | Harm to users | Acceptance gate, conformal coverage, ranges, conditions, official links |
| Dev host mistaken for the VPS | Wrong conclusions, and the disk fills up | Run Phase 0 on the VPS ([KI-502](../KNOWN_ISSUES.md)) |
| Licensing (Open-Meteo, FABDEM non-commercial; HII redistribution) | Legal | Non-commercial operation; ask HII and BMA ([OPEN_QUESTIONS](OPEN_QUESTIONS.md)) |

## Related
[DECISIONS.md](DECISIONS.md) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) · [ARCHITECTURE](../ARCHITECTURE.md) · [GUIDELINES §2](../GUIDELINES.md)
