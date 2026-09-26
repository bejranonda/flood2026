# DECISIONS.md — Decision log (ADR-lite)

> Append new decisions; never rewrite old ones. To change one, add a new decision that **supersedes** it.
> Format: context → decision → consequences. Dates are ICT.

---

### D-001 — VPS core + Cloudflare edge; "zero-key" means keyless sources collected on the server
- **Date:** 2026-09-26 · **Status:** accepted
- **Context:** the brief recommends a VPS core with Cloudflare in front and our own archive. A later commit pushed a "Zero-Key client-side" v1 (browser-side tide maths, a Worker proxying government sites). Probes showed HII sends permissive CORS headers ([KI-105](../KNOWN_ISSUES.md)), so CORS doesn't force the choice.
- **Decision:** a VPS core (collectors, raw archive, Postgres + TimescaleDB + PostGIS, forecasts, FastAPI) behind a Cloudflare Tunnel, CDN, Pages and R2. v1 uses only **keyless** sources, **collected on the server**. **The browser only calls our API or edge.** Code in the browser is for display only.
- **Consequences:** the archive is the system of record; caching protects sources under load; degraded mode is possible. The Worker is only a cache for our own API, never a scraper.

### D-002 — Archive-first, strict phase gates
- **Date:** 2026-09-26 · **Status:** accepted (owner)
- **Decision:** follow the brief exactly: Phase 0 report → **stop for approval** → Phase 1 → … with gates G0–G4 ([PLAN](PLAN.md)). No public UI before Phase 3. As soon as G0 passes, the collectors and backfill start immediately.
- **Consequences:** slower to a public page, but safer. Any interim public page during the current event needs a new decision.

### D-003 — Validate research claim by claim; the evidence rule
- **Date:** 2026-09-26 · **Status:** accepted (owner). This refines the owner's first choice of "quarantine unverified files".
- **Context:** the research came from claude.ai and Gemini sessions. Some files mixed useful content with refuted endpoints and constants. The owner asked for everything to be reviewed, proven and validated, since "not all are unverified" and some content "might be really useful".
- **Decision:** keep all research files in `research/` with validity banners. Validate every testable claim (live call, observed data, or cited source) in [VALIDATION_2026-09-26.md](../../research/VALIDATION_2026-09-26.md), using a re-runnable [script](../../research/validation/validate_research_claims.py). Only ✅/💡 items go into `docs/`; everything else is ⚠️ with a task. Sample outputs must come from running code ([GUIDELINES §2.2](../GUIDELINES.md)).
- **Consequences:** several useful items were saved (the working Traffy public API, tunnel capacities, the equations, the payload design), and several refuted (made-up HII endpoints, the tide constants, the engine output).

### D-004 — Honest identification; no evasion
- **Date:** 2026-09-26 · **Status:** accepted
- **Decision:** a descriptive `User-Agent` with a contact. No browser spoofing, proxy rotation, or bypassing of bot challenges or blocks. If blocked: ask the agency, or use an approved Thai collector node ([GUIDELINES §5](../GUIDELINES.md)).
- **Supersedes:** the "header spoofing" advice in the old KNOWN_ISSUES.

### D-005 — Ranges and probabilities, not minute-precise countdowns
- **Date:** 2026-09-26 · **Status:** accepted
- **Context:** DEM error (≥ 1 m) is much larger than street flood depth, and rain forecasts dominate after 24–48 h. The old UX showed "อีก 3 ชั่วโมง 45 นาที".
- **Decision:** recovery is shown as a **date or time range with conditions**; depth at a location as a **probability category**; +7 d as categories. "ยังประเมินไม่ได้" when heavy rain is forecast.

### D-006 — Scaffold code folders now, with READMEs only
- **Date:** 2026-09-26 · **Status:** accepted (owner)
- **Decision:** create `src/floodwatch/{collectors,archive,db,forecast,api}`, `web/`, `edge/`, `infra/`, `tests/`, each with a README (purpose, contract, phase). No code until the relevant phase.

### D-007 — Documentation in English, UI in Thai
- **Date:** 2026-09-26 · **Status:** accepted
- **Decision:** developer docs are in English, with Thai domain terms where useful. All user-facing strings are Thai; i18n-ready.

### D-008 — Model explicitly in space and time
- **Date:** 2026-09-26 · **Status:** accepted (owner request)
- **Decision:** a station network graph with chainage, polder polygons, scale-aware aggregation, flow-dependent lags, tidal and seasonal periodicities, issue time vs valid time, effective-dated metadata, and space- plus time-aware validation ([APPROACH §2](../APPROACH_AND_METHODS.md)). Add **PostGIS** to the database.

### D-009 — HII metadata is the operational reference for station attributes
- **Date:** 2026-09-26 · **Status:** accepted
- **Context:** bank levels differ between sources by up to 1.5 m (C.13: 17.21 / 15.77 / 16.34) ([KI-203](../KNOWN_ISSUES.md)).
- **Decision:** use HII `min_bank` and `ground_level` operationally; store every alternative value with its source; version it; confirm key stations with RID.

### D-010 — Tide constants are fitted, never copied
- **Date:** 2026-09-26 · **Status:** accepted
- **Context:** two hand-copied constant sets failed against observations (correlation −0.74 and +0.12) ([KI-301](../KNOWN_ISSUES.md)).
- **Decision:** use the Navy tables (converted to MSL) or our own `utide` fits on archived HII tidal stations (interim 30-day fits, then ≥ 1 year). Every tide prediction records its method and fit window.

### D-011 — Publish to GitHub as a private repository first
- **Date:** 2026-09-26 · **Status:** accepted (owner asked to publish to https://github.com/bejranonda; visibility was not specified)
- **Context:** the owner asked to publish the repo with `gh`. The history was scanned first: no keys, tokens or secret files were ever committed (`.env`, `certs/` and `*.pem` are git-ignored). Making a repository public can't be undone once it's been indexed and cloned, and two things are still open: the license and permission from HII, BMA and Traffy for redistribution ([OPEN_QUESTIONS](OPEN_QUESTIONS.md) Q3, Q10).
- **Decision:** create `bejranonda/flood2026` as **private** and push `main`. Going public is a one-line change once Q10 is answered: `gh repo edit bejranonda/flood2026 --visibility public --accept-visibility-change-consequences`.
- **Consequences:** collaborators can be added right away; a public launch needs a LICENSE file and a final secrets scan first.
