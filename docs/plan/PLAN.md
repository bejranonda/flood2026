# PLAN.md — Roadmap, phase gates and status

> **Project:** BKK FloodWatch 2026
> **Mode (since 2026-09-26, D-012):** all workstreams run **in parallel**. An interim public MVP is live at **https://flood.autobahn.bot** (main domain since D-017; `flood.bejranonda.com` is an alias). Gates G0–G4 are now quality reviews, not blockers. Current state and next steps: [HANDOFF.md](../../HANDOFF.md).
> **Brief:** [docs/brief/first_prompt.md](../brief/first_prompt.md) (the "Option 2" prompt plus the updated Phase 1 and Phase 4)

## Where we are

| Item | Status |
|---|---|
| Documentation reorganised and reconciled; research validated claim by claim | ✅ 2026-09-26 |
| Infrastructure: single server + Cloudflare Tunnel; main domain **flood.autobahn.bot** (D-017) | ✅ live; bot challenges off (D-035); request path shares the station list for 60 s after the 2026-09-30 overload (KI-246) |
| Code hosting: [github.com/bejranonda/flood2026](https://github.com/bejranonda/flood2026) | ✅ published 2026-09-26 (private first, D-011); **public** (owner action, D-028); **MIT License** ([LICENSE](../../LICENSE), [D-043](DECISIONS.md)) |
| **MVP live** (collectors, raw archive, Postgres, baseline forecasts, API, Thai web) | ✅ 2026-09-26, https://flood.autobahn.bot (D-012, D-013, D-017) |
| Phase 0 — sources | 🟡 HII, Open-Meteo and Traffy in production; BMA needs a Thai egress (D-014); RID C.29A and the Navy tide are still open |
| Phase 1 — ingestion | 🟡 running: **1,040 gauges nationwide (v0.16), ~310 in the focus area** (HII, RID, all 199 BMA canals every 5 min); 1-year hourly backfill (D-018, D-054); QC for dropouts, erratic and stuck gauges (D-057, KI-241); as-issued forecasts archived (KI-305 resolved). Missing: off-site backup (D-029, KI-511) |
| Phase 2 — forecasting | 🟡 per gauge and horizon backtest with the 10 % gate; `star` (rain + upstream + dam + **7/30-day means and 1/3/72 h changes**, D-092) and **up to 4 learned upstream gauges** (D-093) shipped v0.25.0 under an honest protocol (chosen on the first half, scored on the second, confirmed on a disjoint sample — MODELS §5d): 24 h error vs "no change" on unseen gauges −6.6 → −8.3…−9.1 %. Served ranges: 24 h hold as stated, 72 h too confident (KI-287, Q54); rebound forecasts after steep falls watched (KI-292). Next: Flood Hub input (Q55), WeatherNext backtest (Q53), RID discharge as upstream inputs, L3–L5 |
| Phase 3 — web | 🟡 **v0.33.0 live**; the v0.15 concept is the owner-approved baseline (D-063). One story per view, proven on every gauge by `scripts/ux_consistency.py` (C1–C20; 0 findings after v0.25.0, 1 intermittent after v0.25.2, KI-291); ⚠️ จับตา tab with trend pills (D-077, D-094); national ticker as items with symbols, GLM checked per item (D-094); ✨ AI summary on pins, station sheets and the จับตา tab (D-068, D-095); 24/48/72 h rows (D-086) |
| Impact tab — `/impact` ([plan](impact-kaeng-krachan.md)) | 🟡 **v0.27.0–v0.33.0**, pilot Kaeng Krachan for ONWR/RID engineers (password, D-099/D-100): the national dams list (D-103); 7-day release plans that keep each day's tested margin (D-101, D-104); 32 dams on tested 7-day inflow models (D-106); a flood view per plan — the river by its gauges plus ONWR's dated layers, no water drawn on land (D-105). Planning models have their own test (GUIDELINES §4.5, D-107). Waiting on: flood maps by release level, a LiDAR DEM, the diversion data (OWNER_ACTIONS FLOODMAP, DEM) |
| Phase 5 — nationwide ([phase-5](phase-5-nationwide.md)) | 🟡 **v0.16.0: nationwide parity (D-064)** — every HII-network gauge gets a year of history (backfill ~10 h from 2026-09-30 20:25 UTC), QC, the same forecast gate (rain cells + learned upstream) and panels; region chips for the country (default กทม.). Still open: nationwide backtest re-run after the backfill, dams/FFPI/DWR/GISTDA layers, agency notes (Q3) |
| Phase 4 — ops | 🟡 Cloudflare Tunnel live (no inbound ports); Thai VPN sidecar (D-016) **intermittent since 2026-10-04 (KI-289, owner)**; schema step with a lock timeout and research on read-only connections after a 12-min outage (KI-284, D-096); tasks due from their last success (KI-288); **no external uptime alert yet** (OWNER_ACTIONS "UPTIME"); backups off by owner choice (D-029) |

## Phases and gates

| Phase | Goal | Key deliverables | Gate (a quality review since D-012) |
|---|---|---|---|
| **0** [Source verification](phase-0-source-verification.md) | Know exactly which sources work from the VPS, how, and under what terms | [SOURCES.md](../SOURCES.md) filled in the brief's format, with every row tested from the VPS; station inventory; recommended source set; permission emails sent | **G0:** approved source set → **collectors start immediately** |
| **1** [Ingestion and archive](phase-1-ingestion-archive.md) | Capture every reading from now on, and backfill everything available | Collectors, raw archive + R2, TimescaleDB/PostGIS schema, QC, backfill, source health, **tested restore** | **G1:** ≥ 7 days of continuous collection, backfill done, restore drill passed |
| **2** [Forecasting](phase-2-forecasting.md) | Honest, calibrated forecasts that beat the baselines | Backtest harness, L0–L2, L3 physics (tide fit, lags, rating curves, polders), L4/L5, recovery estimator, depth module, skill report | **G2:** acceptance gate passed per station × horizon (or a documented fallback) |
| **3** [Web app](phase-3-web-app.md) | A Thai, mobile-first public app answering the two golden questions | Public API, map, "ใกล้บ้านฉัน", station pages, model page, attribution, disclaimers | **G3:** UX review by the owner (and ideally a few Thai residents) |
| **5** [Nationwide](phase-5-nationwide.md) | An honest national view, then forecasts per flood type | Bangkok via HII (D-045), backup, lean national collectors behind a flag, national view with tiers, per-type forecasts | **G5:** tiers on every statement, official thresholds only, backup drill, agencies informed, per-type backtests |
| **4** [Deployment and ops](phase-4-deployment-ops.md) | Survive peak traffic and failures; redeploy in under 1 hour | Edge caching, monitoring and alerts, backups, runbooks, security hardening | **G4:** load test, redeploy drill, and alert test passed |

## Critical path and timing principles
1. **Phase 0 → G0 as fast as possible.** Every flood day not archived is lost for good, and it's the most valuable training and validation data we will ever get.
2. **Right after G0:** start the HII collectors and the backfill (`waterlevel_graph` gives up to 365 days, done 2026-09-26; `getGraphFirst` gives 30 days of 10-min data; `POST /getGraph` gives only the latest point), and archive **every** Open-Meteo run. This is why a minimal part of Phase 1 infrastructure (compose + DB + R2) is the first thing built after G0.
3. **Build the backtest harness and baselines L0–L2 before any ML** (Phase 2). A model that can't beat persistence isn't shown.
4. ~~No public UI before G2 and G3 (D-002).~~ **Superseded by D-012 (2026-09-26):** the MVP went public the same day with D-002's safeguards kept — forecasts only where the backtest beats persistence, stale data shown as stale, a disclaimer and official hotlines on every screen.

## Risks
| Risk | Impact | Mitigation |
|---|---|---|
| Sources block the VPS (BMA already blocks non-Thai IPs) | Missing Bangkok khlong detail | Test from the VPS; ask BMA; a Thai collector node ([KI-101](../KNOWN_ISSUES.md)) |
| HII changes or removes its public endpoints | Core feed lost | Raw archive; request a formal agreement with HII; adapter isolation |
| Key stations missing (C.29A, Memorial Bridge, Fort Chula) | Weaker regime B | Find RID and Navy feeds; interim routing and our own tide fit ([KI-109](../KNOWN_ISSUES.md)) |
| Too little history for extremes | Poor ML skill | Backfill; GloFAS 1984→; global models; physical baseline |
| Overconfident public messages | Harm to users | Acceptance gate, conformal coverage, ranges, conditions, official links |
| Single server's disk fills up (13 GB free, 83 % on 2026-09-30; +~1.3 GB for the nationwide year, then flat by retention; owner has more space) and **no backup exists** | Collection stops; history lost | Disk alert below 2 GB; local nightly dump before national collection (D-046, [KI-511](../KNOWN_ISSUES.md)); R2 declined (D-029) |
| Main domain behind a bot challenge | Slow first load; LINE previews and API users blocked | Owner relaxes the zone setting (Q18); old domain kept as alias ([KI-506](../KNOWN_ISSUES.md)) |
| Feedback abuse or misreading | Misleading counts | Private notes, rate limit, human review only ([KI-507](../KNOWN_ISSUES.md), D-020) |
| Licensing (Open-Meteo, FABDEM non-commercial; HII redistribution) | Legal | Non-commercial operation; ask HII and BMA ([OPEN_QUESTIONS](OPEN_QUESTIONS.md)) |

## Related
[DECISIONS.md](DECISIONS.md) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) · [ARCHITECTURE](../ARCHITECTURE.md) · [GUIDELINES §2](../GUIDELINES.md)
