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

### D-012 — Build all phases in parallel; ship an interim public MVP now
- **Date:** 2026-09-26 · **Status:** accepted (owner: "We need everything now, make all in parallel"). **Supersedes D-002** (strict phase gates) and answers Q13.
- **Decision:** collectors, archive, database, baseline forecasts, API and the Thai web app were built together and published at https://flood.bejranonda.com the same day. Safeguards carried over from D-002/D-005: forecasts only where the backtest beats persistence by > 10 %, intervals taken from real backtest errors, stale data shown as stale, a disclaimer, and official hotlines on every screen.
- **Consequences:** the phase checklists become parallel workstreams; gates G0–G4 become quality reviews rather than blockers.

### D-013 — Single server; plain PostgreSQL for the MVP
- **Date:** 2026-09-26 · **Status:** accepted (owner: "we have only single server here")
- **Decision:** everything runs on the one host (Hetzner DE, 178.104.238.220) with `docker compose`. The DB is **postgres:16-alpine** (already on disk; ~11–13 GB free). TimescaleDB and PostGIS are deferred until disk and volume require them. Spatial work (nearest station) is done in Python for now.
- **Consequences:** no off-site copy until R2 is configured (HANDOFF §4.2). BMA is unreachable from this IP (see D-014).

### D-014 — Don't wait for agencies; public data only, optional Thai egress (refines D-004)
- **Date:** 2026-09-26 · **Status:** accepted (owner: "We cannot expect the response from government, please find the solutions and alternatives ourselves? proxy, VPN?")
- **Decision:** use publicly served data now, with attribution and polite polling, without waiting for permission replies. For sources that geo-block non-Thai IPs (BMA), a **Thai egress** is allowed: an SSH SOCKS tunnel to a Thai host the owner controls, or a paid VPN with a Thai exit, set as `THAI_EGRESS_PROXY`. **Still not allowed:** free or open public proxies (tampering and abuse risk), solving bot challenges (Navy site), spoofing identity, or going beyond public pages.
- **Consequences:** the BMA collector is ready but inactive until a Thai egress exists. Navy tide stays on our own harmonic fits.

### D-015 — Sync the station list from the HII chart site, not only `waterlevel_load`
- **Date:** 2026-09-26 · **Status:** accepted (owner: "Many stations are missing")
- **Context:** `waterlevel_load` has 805 stations, but the HII chart site lists **162 more stations** in our provinces (BKK004/007/011/012, ATG\*, MOU\*, …). Verified by calling `queryStation?prov=<Thai province name>` for 18 provinces and diffing against the database.
- **Decision:** the `hii_stations` collector (every 6 h) lists the chart stations per focus province, fetches each one's 30-day chart series, and adds it as a focus station. Coordinates and bank/ground come from the HII map feed (`json/telemetering/wl/warning`, 107 stations) when present. Chart `bank=0, ground=0` is treated as **unknown**, not zero.
- **Result:** focus stations 69 → 104. **56 candidates stay unavailable** (chart endpoint answers HTTP 500, or only `999999`), including Fort Chula (GLF001) and Bang Sai (CPY013): tracked in [KI-207](../KNOWN_ISSUES.md) and [HANDOFF §5](../../HANDOFF.md).

### D-016 — Thai egress = OpenVPN sidecar in an isolated network namespace (refines D-014)
- **Date:** 2026-09-26 · **Status:** accepted (owner added a VPN Gate config: "I have added openvpn from vpngate.net")
- **Decision:** the `vpn` compose service (profile `vpn`) runs the owner's OpenVPN client plus a small HTTP proxy in **one** container. Only requests that explicitly use `THAI_EGRESS_PROXY=http://vpn:8888` leave through it. **Host routing and SSH are untouched.** A watchdog restarts the tunnel when it stops carrying traffic.
- **Limits (public relay = untrusted and flaky):** public pages only; **never send credentials, tokens or personal data through it**; HTTPS is always verified; used only for sources that geo-block (BMA/DWR/Navy); no bot-challenge solving; if a site still blocks the relay's IP class (as `weather.bangkok.go.th` does), don't rotate through relays to evade it: get an owner-controlled Thai host instead.
- **Evidence:** exit IP 49.48.220.198 (Ayutthaya, TH, 3BB); DWR EWS and the Navy home page open from it; BMA `weather.` still 403 ([KI-101](../KNOWN_ISSUES.md)).

### D-017 — Main domain `flood.autobahn.bot`; `flood.bejranonda.com` stays as an alias
- **Date:** 2026-09-26 · **Status:** accepted (owner: "Change the main domain to https://flood.autobahn.bot/"; the owner also replaced the tunnel token)
- **Decision:** `flood.autobahn.bot` is the canonical URL: `rel=canonical`, Open Graph URL, User-Agent `BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)`, `CORS_ORIGIN`, and the docs. Both hostnames are proxied CNAMEs to tunnel `d62b426d…`; `cloudflared` sends any hostname to `app:3000`. **No redirect from the old domain yet**, because the `autobahn.bot` zone shows a bot challenge to non-browser clients ([KI-506](../KNOWN_ISSUES.md)). Add a 301 once the owner relaxes it for this host.
- **Evidence:** CNAME created and re-pointed via the API on 2026-09-26. The old domain returns 200; the new domain returns 403 "Just a moment…" to curl and headless Chrome, as does every proxied host in the zone.

### D-018 — One year of history; backtest on the recent 45 days
- **Date:** 2026-09-26 · **Status:** accepted
- **Context:** api-v3 `waterlevel_graph` serves **up to 365 days** of hourly data (C.12: a request from 2025-09-01 returned 8,777 points starting 2025-09-26). With only 30 days, the backtest's tide fit (on the first 60 %) had < 15 days, so 43 stations with a tide fit were still served persistence.
- **Decision:** each focus station is backfilled **once** with 365 days (`collector_state.hii_graph_backfilled`) by the `hii_backfill` task: 6 stations every 10 min, bulk-inserted with `COPY`, so the single worker loop is never blocked for long. Then `hii_history` refreshes 3 days every 6 h. Forecasts read up to 370 days. The tide is fitted on everything before the backtest window. **The backtest and conformal errors use only the last 45 days**, so the intervals reflect the current regime rather than the dry season.
- **Consequences:** better tide constants (closer to the ≥ 1-year `utide` target), a one-time load of about 100 requests on HII, and a larger archive (one-off).

### D-019 — No 2-D interpolation of water levels for users; 1-D along the river only after validation
- **Date:** 2026-09-26 · **Status:** accepted (owner asked whether spatio-temporal interpolation is useful, noting that Bangkok is not flat)
- **Decision:** don't interpolate water surfaces across land, walls or polders. Show gauges as they are (map, list, and the north→south Chao Phraya profile). Along-river interpolation (chainage + tide lag) goes to Phase 2 and is shown only if leave-one-out RMSE < 0.10 m. Today's test at C.12 gives 0.175 m, against 0.38–0.46 m for the nearest gauge. Temporal: never bridge gaps > 90 min in charts; show "unknown" after 24 h without data. Evidence and reasoning: [APPROACH §2.9](../APPROACH_AND_METHODS.md).

### D-020 — Citizen feedback: collected privately, used for review and evaluation, never auto-applied
- **Date:** 2026-09-26 · **Status:** accepted (owner: "Give the chance to get feedback from users … will be fed into the system to improve the model or calculation or data")
- **Decision:**
  - `POST /api/feedback` collects a verdict on what was shown, the water depth where the user is, a short note, and an opt-in location rounded to ~100 m. The server stores a snapshot of what was displayed.
  - Privacy: no names or contacts; the IP is never stored (a salted daily hash for rate limiting); notes are never published; the public sees counts only.
  - Feedback drives **verification metrics, data-quality review and future depth-model labels** ([APPROACH §3.5](../APPROACH_AND_METHODS.md)). It **never automatically changes a forecast or a status** ([KI-507](../KNOWN_ISSUES.md)).
