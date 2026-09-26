# PLAN.md — Roadmap, phase gates and status

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-26
> **Mode (since 2026-09-26, D-012):** all workstreams run **in parallel**. An interim public MVP is live at **https://flood.autobahn.bot** (main domain since D-017; `flood.bejranonda.com` is an alias). Gates G0–G4 are now quality reviews, not blockers. Current state and next steps: [HANDOFF.md](../../HANDOFF.md).
> **Brief:** [docs/brief/first_prompt.md](../brief/first_prompt.md) (the "Option 2" prompt plus the updated Phase 1 and Phase 4)

## Where we are

| Item | Status |
|---|---|
| Documentation reorganised and reconciled; research validated claim by claim | ✅ 2026-09-26 |
| Infrastructure: single server + Cloudflare Tunnel; main domain **flood.autobahn.bot** (D-017) | ✅ live; ⚠️ the new domain shows a bot challenge to non-browsers (KI-506, Q18) |
| Code hosting: [github.com/bejranonda/flood2026](https://github.com/bejranonda/flood2026) | ✅ published 2026-09-26 (private first, D-011); **public** by the owner's action, history scanned ([D-028](DECISIONS.md)); no LICENSE yet |
| **MVP live** (collectors, raw archive, Postgres, baseline forecasts, API, Thai web) | ✅ 2026-09-26, https://flood.autobahn.bot (D-012, D-013, D-017) |
| Phase 0 — sources | 🟡 HII, Open-Meteo and Traffy in production; BMA needs a Thai egress (D-014); RID C.29A and the Navy tide are still open |
| Phase 1 — ingestion | 🟡 running; **110 focus stations**, whole BMR (D-015, D-023, KI-209/210); **1-year hourly backfill** from `waterlevel_graph` (D-018); missing: R2 off-site backup (blocked on R2 S3 credentials) and ~54 stations the chart endpoint won't serve (incl. GLF001, CPY013; all workarounds tested, KI-207) |
| Phase 2 — forecasting | 🟡 L0/L1 + damped trend; tide fitted on up to a year, backtest on the last 45 days (D-018); 24 h outlook (peak window, chance of reaching the bank); interpolation assessed (D-019). L3–L5 and polder-aware depth are next |
| Phase 3 — web | 🟡 MVP live, **mobile-first redesign** (tabs, bottom sheet, search, share/deep links, summary statistics, Chao Phraya profile) and **citizen feedback** (D-020), **point check** for places with no gauge (D-021), optional **Workers AI** triage (D-022), **every station shown with notes** (D-024). **Released v0.2.0** ([CHANGELOG](../../CHANGELOG.md), D-025). Reviewed in [UX_VALIDATION](../UX_VALIDATION.md). Next: polder-aware "near me", alerts (Q7), model page |
| Phase 4 — ops | 🟡 **Cloudflare Tunnel live** (no inbound ports); Thai VPN sidecar (D-016); monitoring alerts and R2 backups are next (KI-504, KI-505) |

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
2. **Right after G0:** start the HII collectors and the backfill (`waterlevel_graph` gives up to 365 days, done 2026-09-26; `getGraphFirst` gives 30 days of 10-min data; `POST /getGraph` gives only the latest point), and archive **every** Open-Meteo run. This is why a minimal part of Phase 1 infrastructure (compose + DB + R2) is the first thing built after G0.
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
| Single server's disk fills up (~13 GB free, shared) | Collection stops | Disk alert below 2 GB; R2 replication once credentials exist ([KI-502](../KNOWN_ISSUES.md), [KI-504](../KNOWN_ISSUES.md)) |
| Main domain behind a bot challenge | Slow first load; LINE previews and API users blocked | Owner relaxes the zone setting (Q18); old domain kept as alias ([KI-506](../KNOWN_ISSUES.md)) |
| Feedback abuse or misreading | Misleading counts | Private notes, rate limit, human review only ([KI-507](../KNOWN_ISSUES.md), D-020) |
| Licensing (Open-Meteo, FABDEM non-commercial; HII redistribution) | Legal | Non-commercial operation; ask HII and BMA ([OPEN_QUESTIONS](OPEN_QUESTIONS.md)) |

## Related
[DECISIONS.md](DECISIONS.md) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) · [ARCHITECTURE](../ARCHITECTURE.md) · [GUIDELINES §2](../GUIDELINES.md)
