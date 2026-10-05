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
- **Date:** 2026-09-26 · **Status:** accepted, **superseded by D-028** (the owner made it public) (owner asked to publish to https://github.com/bejranonda; visibility was not specified)
- **Context:** the owner asked to publish the repo with `gh`. The history was scanned first: no keys, tokens or secret files were ever committed (`.env`, `certs/` and `*.pem` are git-ignored). Making a repository public can't be undone once it's been indexed and cloned, and two things are still open: the license and permission from HII, BMA and Traffy for redistribution ([OPEN_QUESTIONS](OPEN_QUESTIONS.md) Q3, Q10).
- **Decision:** create `bejranonda/flood2026` as **private** and push `main`. Going public is a one-line change once Q10 is answered: `gh repo edit bejranonda/flood2026 --visibility public --accept-visibility-change-consequences`.
- **Consequences:** collaborators can be added right away; a public launch needs a LICENSE file and a final secrets scan first.

### D-012 — Build all phases in parallel; ship an interim public MVP now
- **Date:** 2026-09-26 · **Status:** accepted (owner: "We need everything now, make all in parallel"). **Supersedes D-002** (strict phase gates) and answers Q13.
- **Decision:** collectors, archive, database, baseline forecasts, API and the Thai web app were built together and published at https://flood.bejranonda.com the same day. Safeguards carried over from D-002/D-005: forecasts only where the backtest beats persistence by > 10 %, intervals taken from real backtest errors, stale data shown as stale, a disclaimer, and official hotlines on every screen.
- **Consequences:** the phase checklists become parallel workstreams; gates G0–G4 become quality reviews rather than blockers.

### D-013 — Single server; plain PostgreSQL for the MVP
- **Date:** 2026-09-26 · **Status:** accepted (owner: "we have only single server here")
- **Decision:** everything runs on the one host (Hetzner, Germany; the IP is deliberately not written in the docs) with `docker compose`. The DB is **postgres:16-alpine** (already on disk; ~11–13 GB free). TimescaleDB and PostGIS are deferred until disk and volume require them. Spatial work (nearest station) is done in Python for now.
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
- **Evidence:** exit: a VPN Gate relay in Ayutthaya (TH, 3BB); DWR EWS and the Navy home page open from it; BMA `weather.` still 403 ([KI-101](../KNOWN_ISSUES.md)).

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

### D-021 — Point check: evidence card instead of an interpolated level
- **Date:** 2026-09-26 · **Status:** accepted (owner: "If I am user, I would like to check the area which has no station by his own pinpoint … propose like interpolation with note and warning?")
- **Decision:**
  - Tapping the map, or "สถานีใกล้ฉัน", opens a point card (`/api/point`) with an **IDW area category of gauge *status*** (not a level), its min–max range, a confidence level that is never "high", nearby gauges labelled river/khlong, Traffy and user reports within ~1 km, the 24 h rain forecast, and **always-on warnings**.
  - At very low confidence **no area verdict** is shown.
  - Pins are shareable (`#p=lat,lon`), and reports from a pin are stored with `loc_source = pin`.
- **Why:** it keeps D-019 (no water surface over land) while answering the user's question with what we actually know. Method: [APPROACH §2.10](../APPROACH_AND_METHODS.md).

### D-022 — Cloudflare Workers AI only for background triage; never for safety facts; the site never depends on it
- **Date:** 2026-09-26 · **Status:** accepted (owner: "Cloudflare has AI, how can we apply it? If the Cloudflare quota is full, the app must continue working as normal.")
- **Decision:**
  - SEA-LION v4 (Thai-capable) labels feedback notes in a worker task (every 15 min, ≤ 20 notes, budget 3,000 neurons/day, circuit breaker).
  - Instant urgency detection and the situation summary are **deterministic** (keyword rules, template).
  - The web app never calls AI. *(Amended by D-068, 2026-10-02: the app may ask GLM for one short sentence from rule-decided lines, shown only after a strict check.)*
  - Tested models paraphrased warning levels incorrectly, so AI must not write status text.
- **Evidence and future uses:** [APPROACH §3.6](../APPROACH_AND_METHODS.md). **Security:** prefer a dedicated token with only Workers AI rights (`CF_AI_TOKEN`, Q21); until then the worker falls back to the general API token (worker container only).

### D-023 — Focus = the whole Bangkok Metropolitan Region + lower Chao Phraya; map-feed coordinates for every station
- **Date:** 2026-09-26 · **Status:** accepted (owner: "Consider integrating this station in the map … BKK008 … Any other missing stations?")
- **Findings (HII map feed `json/telemetering/wl/warning`, 110 rows, 2026-09-26 ~10:35 UTC):**
  - BKK008 was in our data but **had no coordinates**. The map feed has them (13.7613, 100.6160). Map-feed coordinates were only applied to newly added chart-only stations.
  - **8 gauges within 60 km of central Bangkok were outside our focus.** All are in **Samut Sakhon and Nakhon Pathom**, the two Bangkok Metropolitan Region (BMR) provinces we didn't cover: BKK006, VLGE20, BKK019, THA008, THA009, THA007, MKG005, and GLF002 (Tha Chin mouth).
- **Decision:**
  - `FOCUS_PROVINCES` += สมุทรสาคร, นครปฐม, plus an Open-Meteo point for them.
  - `hii_stations` now fills coordinates, and missing name, amphoe and bank, for **any** station lacking coordinates, versioned in `station_version`.
  - **GLF002 is excluded** because its values are not m MSL ([KI-210](../KNOWN_ISSUES.md)).
- **Result:** 110 focus stations (81 on the map). BKK008 is on the map as ล้นตลิ่ง (1.18 m vs bank 0.88 m), matching HII's own page (104.72 % of capacity).
- **Owner follow-up ("find coordinates from the map inside the warning page"):** that page's map loads only the same 110-station feed, plus boundary and river layers. **It has no coordinates for the 29 remaining stations** (KI-207). Its river layer did provide the Chao Phraya centreline, now used for river km ([APPROACH §2.9](../APPROACH_AND_METHODS.md)).

### D-024 — Show every station; filter misleading *values*, never stations, and say why
- **Date:** 2026-09-26 · **Status:** accepted (owner: "You can include all stations to the map. If some parts of data are not good, filter out the misleading data, but show the stations with note.")
- **Decision:**
  - `/api/stations` serves **every** focus station, including those without a recent reading. Each station has `notes`: `datum_suspect`, `suspect_values_hidden`, `no_recent_data`, `stale`, `no_bank`, `approx_location`, `no_location`. The UI shows them in the list, tooltip and detail.
  - **GLF002** is shown with its non-MSL values hidden (KI-210).
  - **Plausibility rule:** a level more than **3 m above the station's bank** is flagged `out_of_range`, using the *stored* bank on every insert. It is kept in the DB, hidden in the UI, and the last plausible value is shown instead (KI-211).
  - **14 of the 29 stations** with no position in any HII feed get **approximate OSM positions** (±2–5 km, dashed markers, `coord_source=osm_approx`, cited per station in [station_coords_approx.json](../../src/floodwatch/data/station_coords_approx.json)). The 15 others that couldn't be matched are listed, and the map shows how many are unplaced.
  - A map toggle shows **the whole HII network** (840 stations) as small markers.
- **Also:** station markers are on their own top layer; Traffy cells are non-interactive (the owner couldn't tap stations under them).

### D-025 — Versioned releases, version shown in the UI
- **Date:** 2026-09-26 · **Status:** accepted (owner: "release as next version, show version on UI too")
- **Decision:**
  - The single source is `floodwatch.__version__` (plus `pyproject.toml`). `/api/health` and `/api/stats` return it, and the UI shows it in the header badge and footer.
  - Each release gets a [CHANGELOG.md](../../CHANGELOG.md) entry, a `vX.Y.Z` git tag and a GitHub release (private repo).
  - `v0.1.0` (by another session) = `b78869c`; **`v0.2.0`** = this release.

### D-026 — One owner-action tracker with a read-only status script
- **Date:** 2026-09-26 · **Status:** accepted (owner: "Keep/record what I need from you for later")
- **Decision:**
  - [OWNER_ACTIONS.md](../OWNER_ACTIONS.md) is the single place for anything needed from the owner, with why, exact steps, cost and how it is verified.
  - [scripts/owner_status.py](../../scripts/owner_status.py) checks it read-only (curl for the challenge, Cloudflare API GETs, `.env` key presence, one tiny AI call) and **never prints a secret**.
  - Agents run it before asking, because the owner may already have acted. On 2026-09-26 the owner had already deleted the old tunnel and fixed tunnel rights.
- **Lesson recorded:** never test reachability with one client. A Python urllib check reported the bot challenge as "fixed" while curl, browsers and crawlers were still challenged.

### D-027 — Host-aware canonical now; legacy-domain redirect built but off until Q18
- **Date:** 2026-09-26 · **Status:** accepted
- **Context:** the alias `flood.bejranonda.com` works for every client, while the main domain challenges non-browsers (KI-506). The page's `canonical` and `og:url` pointed crawlers from the alias to the challenged domain.
- **Decision:**
  - The alias page declares **itself** canonical, so the shareable link works today.
  - `REDIRECT_LEGACY_HOST=1` (301 to the main domain, keeping path and query; `/api/health` excluded) is implemented and tested (temporary server, four cases) but **off**. It must be enabled only after Q18, or crawlers and API users would be redirected into the challenge.
- **Also (v0.2.1):** the worker runs a `hii_backfill` batch at startup ([KI-212](../KNOWN_ISSUES.md)).

### D-028 — The repository is public: scan, keep the docs safe, do not add a license unasked
- **Date:** 2026-09-26 · **Status:** accepted. The owner changed the visibility to public (seen at 15:20 UTC, `gh repo view` → `PUBLIC`, 0 stars, 0 forks); this supersedes D-011.
- **Done on discovery:** a full-history scan (every commit, secret values compared without printing them) found no credentials, data or personal email. Findings and residual risks are in [KI-214](../KNOWN_ISSUES.md), including the server IP that remains in 8 old commits.
- **Rules from now on:**
  - nothing secret, no IPs, account ids, emails or feedback content in files or commit messages ([GUIDELINES §7.1](../GUIDELINES.md));
  - **no LICENSE is added without the owner's choice** (Q10: all rights reserved until then);
  - history is never rewritten or force-pushed without the owner's go-ahead.
- **Also:** the SSH and password findings are recorded as an optional owner action, not changed by an agent (KI-214).

### D-029 — R2 off-site backups kept disabled by owner choice
- **Date:** 2026-09-26 · **Status:** accepted (owner: "keep disable")
- **Decision:**
  - Cloudflare R2 off-site backups remain **disabled**.
  - All raw telemetry archives (`data/raw_archive`) and PostgreSQL database files (`data/pg`) remain stored on the local server disk.
  - No Cloudflare R2 bucket or S3 tokens are required.
  - Nightly snapshots/backups will be retained locally on the VPS disk.

### D-030 — Support GLM (Zhipu AI) for background feedback triage
- **Date:** 2026-09-26 · **Status:** accepted (owner: "I will change from Cloudflare AI to GLM, is it possible. When good, please adapt .env to have GLM token, I will fill in later.")
- **Decision:**
  - FloodWatch supports **GLM** (`glm-4-flash` via Zhipu AI OpenAPI `open.bigmodel.cn`) as the primary AI provider for background citizen feedback triage, replacing or complementing Cloudflare Workers AI.
  - GLM configuration (`AI_PROVIDER=glm`, `GLM_API_KEY`, `GLM_MODEL=glm-4-flash`) is integrated into `.env`, `.env.example`, `docker-compose.yml`, and `src/floodwatch/ai.py`.
  - When `GLM_API_KEY` is empty, the system gracefully falls back to deterministic rule-based triage without error.
  - Once the owner populates `GLM_API_KEY` in `.env`, the worker automatically begins classifying feedback notes with `glm-4-flash`.

### D-031 — Use and show BMA khlong gauges via the People's Party relay
- **Date:** 2026-09-26 · **Status:** accepted (owner, Q24: "a" = use it and show it, crediting BMA and the relay; Q27: the audience is **Bangkok residents**; Q17: no Thai machine is available)
- **Why:** only 10 of 111 gauges were in Bangkok; BMA's own site is unreachable from this host (SOURCES §2c); the relay serves BMA's KlongMap (199 gauges, 147 of them ≥ 3 km from any HII gauge) every 5 min.
- **Decision:** collector `bma_klong` (10 min, one attempt, raw payload archived, ≥ 50 stations or the run fails and the last good data stays). Stations `agency=BMA`, codes `WL.xxx.nn`, `in_focus`. **Bank = lower of left/right bank; BMA `warning`/`critical` never used (KI-215). Levels never compared with HII levels (KI-217): each gauge is judged only against its own bank.** The UI credits BMA and the relay on every BMA detail and labels the unit "ม. (หมุด กทม.)".
- **Risks accepted:** a third-party, political relay without a stated licence may change or vanish (then BMA gauges go "unknown" after 24 h; HII is unaffected). A courtesy note to the relay and BMA is in [OWNER_ACTIONS](../OWNER_ACTIONS.md).

### D-032 — Place search through OpenStreetMap Nominatim, not AI
- **Date:** 2026-09-26 · **Status:** accepted (a real user asked for data for their soi near สะพานใหม่ and search found nothing; the owner asked whether to put AI in the search bar)
- **Decision:** `/api/geocode` asks Nominatim (Bangkok region box, `accept-language=th`) **only when the user presses search**, ≤ 1 request/s across workers (Postgres advisory lock), 30 searches/h per visitor, in-memory cache. Thai abbreviations (ซ., ถ., พหล) are expanded, and "name + number" is also tried as "ซอย…" with exact name matches ranked first. The chosen place opens the point check. **Queries are never logged or stored** (people type their own street).
- **Why not AI:** Nominatim found all three places in the request exactly (tested 16:26 UTC); an LLM would add cost, latency and invented coordinates. AI could later rewrite messy free text into a query, never produce coordinates.

### D-033 — Bangkok is the default list region (this week)
- **Date:** 2026-09-26 · **Status:** accepted, **revisit 2026-10-03** (owner, Q26: "Bangkok as default this week")
- **Decision:** the list opens on "กทม."; a tapped region is remembered on the device. A search always looks in every region.

### D-034 — Everything moves to flood.autobahn.bot (pages redirect; the API stays reachable on the alias)
- **Date:** 2026-09-26 · **Status:** accepted (owner: "move all to flood.autobahn.bot"), supersedes the "off until Q18" part of D-027
- **Decision:** `REDIRECT_LEGACY_HOST=1` in production: pages and static files on `flood.bejranonda.com` answer **301 → `flood.autobahn.bot`** (path and query kept; browsers keep `#s=` / `#p=` fragments). **`/api/*` is not redirected**: scripts, monitors and other non-browser clients cannot pass the main domain's bot challenge (KI-506).
- **Consequence, verified 16:58 UTC:** a browser following an old link reaches Cloudflare's "Performing security verification / Verify you are human" page on the main domain (headless Chromium; real phones usually pass without a click, not verified here). Link previews (LINE, Facebook) of either domain now depend on the challenge. **Fix is owner-side only (Q18):** turn Bot Fight Mode off for the zone, or Pro + skip rule. Our API token cannot read or change zone security settings (checked: `bot_management`, `security_level`, rulesets → unauthorised).
- **Token check after the owner added Zone Settings / Firewall Services / Page Rules edit (17:00 UTC):** security level medium, Browser Integrity Check on, no firewall/access/UA rules; Bot Fight Mode and rulesets still unreadable. A flood-only page rule (security level essentially off, Browser Integrity Check off; OWNER_ACTIONS option D) was applied at 17:11 UTC on the owner's explicit go-ahead: **no effect on the challenge** → Bot Fight Mode (or a WAF custom rule) remains the cause; option A is the owner's. Target state (owner): **only flood.autobahn.bot** — once the challenge is gone, `/api/*` is redirected too.
- **Rollback:** set `REDIRECT_LEGACY_HOST=0` in `.env` and `docker compose up -d app` (seconds). Browsers may cache the 301.

### D-035 — Q18 done: the bot challenge is off, so the API moves too; flood.autobahn.bot is the only domain
- **Date:** 2026-09-26 · **Status:** accepted (owner turned **Bot Fight Mode off** at ~17:30 UTC; supersedes the API exception in D-034)
- **Evidence (17:33 UTC):** `curl`, `facebookexternalhit` and a LINE user agent get **HTTP 200**, no `cf-mitigated`, on `/` and `/api/health` of `flood.autobahn.bot`. The flood-only page rule (D-034, security level and BIC off) stays.
- **Decision:** every path on `flood.bejranonda.com` answers **301 → flood.autobahn.bot**, `/api/*` included; only `/api/health` stays answering on the old host so an old uptime monitor keeps working. A browser following an old link with a `#s=` fragment lands on the station on the new domain (tested).
- **Left for later:** the old hostname's CNAME and tunnel route can be removed once redirects have run for a few weeks (keep them until then: shared links live in chats).

### D-036 — Channels and streets are separate facts: relabel "normal", show street reports beside gauges, fold away dead gauges
- **Date:** 2026-09-26 · **Status:** accepted (owner: "many areas are under flood from Traffy, but the new flood69 stations show water below bank. It is conflict. Should we filter or separate?" and "filter the stations which cannot be predicted")
- **Evidence (18:10 UTC):** of 188 fresh BMA gauges, **34 read "normal" with ≥ 5 Traffy flood reports within 1 km** (12 h window), e.g. Saen Saep at Bang Kapi district office: 35 cm below bank, 35 street reports. Not a data conflict: a khlong gauge measures the canal against its bank; streets flood when rain exceeds the drains while BMA keeps canals pumped low (KNOWLEDGE §4.2–4.3).
- **Decision:**
  1. Status `normal` is shown as **"ต่ำกว่าตลิ่ง" (below bank) in blue**, never "ปกติ" (normal) in green: it describes the channel, not the neighbourhood. Headline: "น้ำในคลองต่ำกว่าตลิ่ง 35 ซม.".
  2. **Street layer beside every gauge:** `street_reports_6h` (Traffy flood reports within 1 km, 6 h) in `/api/stations`; cards show "🚗 ถนนรอบ ๆ มีรายงานน้ำท่วม N เรื่อง" at ≥ 3; the detail explains canal vs street; the point check adds `street_flooding_despite_channels` when ≥ 3 reports meet a calm channel picture, and tells users to trust street reports first. **Neither source is filtered out.**
  3. **Freshness of the street layer is always stated** when Traffy is > 60 min old ("ข้อมูล Traffy ล่าสุด 3 ชม.ที่แล้ว").
  4. **Filtering:** gauges with no data for 24 h are folded into a closed "ไม่มีข้อมูลล่าสุด (N)" group at the end of the list and hidden on the map (checkbox to show). A **"📈 เฉพาะที่คาดการณ์ได้" chip** (off by default) hides gauges without a tested forecast. Not on by default: it would hide 186 of 209 Bangkok gauges, the reason residents come (Q27).
- **Not done:** merging Traffy into gauge status (reports lag, cluster where people are, and describe streets), or hiding BMA gauges that disagree with reports.

### D-037 — The map shows forecastable gauges by default; every gauge shows a trend
> **Superseded 2026-10-03 by D-079:** the map shows every gauge with data < 24 h (the switch hid red gauges); a ring marks "no forecast".
- **Date:** 2026-09-26 · **Status:** accepted (owner: "users like to see the trend; separate the non-predictable from the map, but with an option to show"), refines D-036 item 4
- **Decision:** the map shows only gauges with a tested forecast and fresh data (81 at 18:30 UTC); a switch at the top left, "แสดงสถานีที่ยังคาดการณ์ไม่ได้ (214)", shows the rest. The **list and the point check still use every gauge.** Gauges without a forecast show an **observed trend** from our own readings (`change_m` over 1–3 h: "↗️ สูงขึ้น 12 ซม. ใน 2 ชม.ที่ผ่านมา"), labelled as past, not a prediction; available ~1 h after a gauge starts reporting (170 BMA gauges at 18:30 UTC).
- **Trade-off stated to the owner:** the default Bangkok map is sparse (most Bangkok gauges are BMA, forecastable from ~3 Oct); the list stays the Bangkok view.

### D-038 — BMA canal gauges are judged by BMA's own drainage levels
- **Date:** 2026-09-26 · **Status:** accepted (owner chose "BMA's own levels" over hiding below-bank BMA gauges; owner's hypothesis: "flood69 mixes water levels in front of and behind gates, pump-controlled, so we cannot see the real level")
- **Evidence (18:40 UTC, 199 BMA gauges, Traffy reports 3–6 h old):**
  - We never mix the two sides of a gate: only `wl_in` (canal side) is stored. Of 49 gauges "below bank" with ≥ 5 street-flood reports within 1 km, **39 are plain canal gauges**, 8 gates, 2 other. At 38 of 42 gates the canal is held below the river (median 0.64 m): the system is pump-managed, but that is not what hid the floods.
  - Near flooded streets 18 % of gauges were over the bank but **60 % over BMA "critical"** (median +0.18 m); near quiet streets 5 % and 38 % (median −0.26 m). BMA's levels separate wet from quiet far better than the bank. Still a weak signal (one evening, reports lag, 38 % of quiet areas also over critical).
- **Decision:** BMA gauges: over bank → **ล้นตลิ่ง** (red); over BMA critical → **คลองเต็ม** (orange); over BMA warning → **คลองเริ่มเต็ม** (amber); otherwise **คลองยังรับน้ำได้** (blue). The margin shown is "เกินเกณฑ์ กทม. N ซม."; the bank distance and BMA's critical level are the second line; the detail explains "the canal can't take street water well"; the chart draws BMA's critical level. `status_basis` in the API says which yardstick applies. HII/RID gauges keep bank-based status. Summary chips use combined words ("ใกล้ตลิ่ง/คลองเต็ม", "ยังรับน้ำได้").
- **Result:** of 42 BMA gauges with ≥ 3 street reports, 14 still read "ยังรับน้ำได้" (before: most). Not hidden: the street reports next to them stay visible (D-036).
- **Supersedes** the KI-215 rule "never use BMA critical": it is still never a bank, but now it is the drainage yardstick.

### D-039 — Favicon redesigned for browser tab recognizability (Flood Droplet & Wave)
- **Date:** 2026-09-26 · **Status:** accepted (owner prompt: "review favicon, it is not easy to recognize on web browswer, make it simple modern and easy to recognize from web browswer"; owner explicitly selected Option 2: Flood Droplet & Wave).
- **Root-cause evidence:**
  1. The original favicon used a dark navy background gradient (`#0d3b66` to `#061c33`) inside a rounded square tile. In modern browsers with dark mode tabs (Chrome `#202124`, macOS `#1e1e1e`), the dark base had near-zero edge contrast, making the icon virtually invisible.
  2. The SVG crammed 6 micro-elements into a 64×64 viewBox (1px border, 3-layer nested droplet, 1.8px center white beacon dot, 1.5px specular highlight, and 3 thin ruler gauge lines). At standard 16×16 CSS tab resolution, these collapsed into a murky, illegible pixel smear.
  3. iOS home screen risk: Apple touch icons render transparent backgrounds as solid black squares unless backed by a solid squircle canvas.
- **Decision:**
  1. Adopted **"Flood Droplet & Wave"** design: iconic water droplet silhouette (hydro telemetry motif), dual rising flood waves (vivid cyan `#38bdf8` and crisp pure white `#ffffff`), and an amber telemetry warning beacon (`#fbbf24`) with white core.
  2. Contrast guarantee: Luminous sky-blue outer rim (`#7dd3fc`) with soft SVG drop shadow (`tabShadow`) ensures clear silhouette separation on dark tabs (`#202124`), light tabs (`#dee1e6`), and pure white titlebars (`#ffffff`).
  3. Asset generator `scripts/generate_favicon.py` rewritten in pure Python with 2×2 supersampling for subpixel antialiasing and zero external runtime dependencies (runs in Docker container without PIL).
  4. Generates `web/favicon.svg`, dual-resolution `web/favicon.ico` (16×16 and 32×32), `web/apple-touch-icon.png` (180×180 on deep oceanic squircle to avoid iOS black background), and `web/icon-192.png` (192×192 PWA). Cache buster bumped to `?v=2` in `web/index.html`.

### D-040 — Point check redesign: collapsible disclaimers, categorized predictable vs local gauges, and enhanced Traffy layer
- **Date:** 2026-09-26 · **Status:** accepted (owner prompt: "when select point on map, it shows a lot of text in sidebar, collapse which is extended by users; order showing stations, predictable first or categorize; decrease transparency of Traffy hotspots")
- **Evidence & Problems Identified:**
  1. The static yellow disclaimer box ("⚠️ นี่ไม่ใช่ระดับน้ำที่จุดนี้...") consumed 35–40% of the viewport on both mobile and desktop, repeating 4 generic educational cautions every time a user clicked any point, pushing actionable data far below the fold.
  2. After ingesting 199 BMA stations, sorting strictly by distance resulted in the top 5 stations being newly added BMA gauges with no forecast models (`trend12: unknown`), high banks ("ต่ำกว่าตลิ่ง 60 ซม."), or stale data (e.g. `WL.JKK.01` with no data for 2 days). Stations with predictive models (HII/RID gauges) were completely pushed out.
  3. Traffy flood hotspots on the map were rendered at `fillOpacity: 0.14` with zero stroke (`weight: 0`), rendering them almost invisible against standard OpenStreetMap tiles.
- **Decision:**
  1. **Collapsible static disclaimers:** Educational disclaimers are folded into `<details class="point-disclaimer">` with summary "ℹ️ ข้อจำกัดของข้อมูล (สถานีคลอง ≠ ระดับถนนหรือในบ้าน)".
  2. **Prominent dynamic warnings:** If street flood reports are detected (`street_flooding_despite_channels`), an urgent alert banner is displayed immediately at the top of the card.
  3. **Categorized station list:** Stations returned by `/api/point` are split into:
     - `stations_forecast`: Top 2–3 closest stations with active ML forecasts / trend12.
     - `stations_nearby`: Top 2–3 closest active local canal/river gauges (deduplicated against forecast).
  4. **Stale gauge suppression:** Gauges with no data > 24 hours are excluded from the point check list.
  5. **Enhanced Traffy hotspots:** Changed circle styling to `weight: 1, opacity: 0.5, fillColor: "#7b1fa2", fillOpacity: 0.30–0.55` with subtle purple outline, giving instant visual clarity on street flood clusters.
  6. **Ultra-compact 1-line footer & viewport expansion:** Transformed the previously 3-line footer (which consumed ~20% of desktop viewport) into an ultra-compact ~28px flex bar with popover details for methodology/sources. Expanded desktop and mobile map and station card viewport height by 45–50px.

### D-041 — Point forecast outlook synthesis & future trend warning (Core USP)
- **Date:** 2026-09-26 · **Status:** accepted (owner prompt: "when click coordinate, users might expect short summary of forecasting future trend and warning of the clicked point, this might be our USP")
- **Evidence & Need:**
  1. Previously, clicking a point returned raw status of nearby stations and rainfall, but lacked an synthesized outlook of what will happen at this point over the next 12–24 hours.
  2. BKK FloodWatch's unique advantage over raw government telemetry (ThaiWater / BMA DDS) is forward-looking ML hydrological forecasting and rain integration.
- **Decision:**
  1. Implement `point_forecast()` in `src/floodwatch/point.py` that synthesizes:
     - Canal trend (`rising`, `steady`, `falling`) from nearest forecast models.
     - Open-Meteo 24h precipitation forecast.
     - Area channel stress (`normal`, `watch`, `warning`, `critical`).
     - Real-time citizen street reports (Traffy Fondue).
  2. Output a structured forecast outlook (`risk`: high/moderate/low, `channel_trend`, `title`, `desc`).
  3. Render a prominent `.forecast-banner` at the top of the point sheet (`🔮 คาดการณ์แนวโน้ม 12–24 ชม. ข้างหน้า`), immediately informing the user of upcoming flood risk.

### D-042 — Gate the point forecast by confidence; never a canal verdict without a usable gauge
- **Date:** 2026-09-27 · **Status:** accepted (owner asked for a review; "use the only available data for giving verdicts, e.g. rainfall, adjust the words"; "water is diverse by basin, not distance — how far is the criteria?")
- **Bug found (D-041 shipped without a confidence check):** live probes on 2026-09-27 ~07:47 UTC showed the banner
  giving a calm verdict from **zero gauges** (`14.30,100.20`: `confidence=none` → "สถานการณ์ปกติ … ความเสี่ยงน้ำท่วมต่ำ"
  with 18 mm called "light"), and a **contradiction on one sheet**: at `13.82,100.60` the overview card correctly
  withheld a verdict at `confidence=very_low` (per D-021, `web/app.js` canalSummary), while the banner above it stated
  "moderate / rising" from the same far, disagreeing gauge. A single tidal river gauge's routine swing (`delta12 ≥
  0.04 m`) could also read as "rising" for the whole point.
- **Evidence for the distance criterion:** a snapshot of 264 fresh gauges (`/api/stations`, 2026-09-27) shows status
  agreement between same-agency gauge pairs falls from 80–86% at 0–1 km to ~46–66% at 2–5 km to ~50% at 5–8 km
  (vs. a ~31–45% random baseline at 8–15 km); ≥2-level disagreement is already ~21% by 1–2 km. Grouping by matching
  river name (a crude basin proxy) gave no improvement over plain distance. **No polder polygons exist in this repo**
  (APPROACH §2 lists them as a future data layer), so a true basin-aware boundary is not buildable yet — the
  existing distance/agreement bands in `area_index()` (`confidence`: medium ≤3 km + agreeing, low ≤5 km + agreeing,
  else very_low/none) remain the best available proxy and are reused rather than duplicated (KI: see KNOWN_ISSUES).
- **Decision — three evidence layers, each worded for what it is:**
  1. **Canal/river gauge trend** is only used when `area.confidence ∈ {low, medium}` (i.e. `area_index()` already
     judged the nearby gauges close enough and in agreement). At `very_low`/`none`, the outlook carries **no canal
     claim at all** — consistent with the overview card and D-021.
  2. Trend requires a **strict majority** of same-water-body forecast gauges (`_majority_trend`), computed
     separately for khlong (drives "canal" wording) and river (tidal; only labelled, never drives risk alone) —
     not "any one gauge ≥ 0.04 m".
  3. **Rainfall is usable everywhere** (it needs no nearby gauge), worded by 24h band (light/moderate/heavy/very
     heavy — since 2026-09-27 the TMD categories, cited in KI-224) as a *condition*, never folded into a "risk is low"
     verdict. `rain_next24_mm = None` omits the rain sentence entirely (no more "~0 มม.").
  4. **Street reports** (Traffy, ≥`STREET_ALERT` in 1 km/6 h) are usable everywhere and can raise risk on their own.
  5. When neither a usable gauge nor strong local evidence exists, the outlook returns **`risk: "info"`** (ℹ️, new
     `.risk-info` style) stating plainly that gauges are too far or in another basin to judge the point — never
     `"low"`/`"ปกติ"`.
  6. A new `"basis"` field (`["rain","reports","gauges"]`) lets the UI show a one-line footnote of which evidence
     the outlook actually used (`web/app.js` `fcBasis`), so "info" doesn't look identical to a checked "low".
- **Where:** `src/floodwatch/point.py` (`point_forecast`, `_majority_trend`, `_station_trend`, `_rain_phrase`),
  `tests/test_point.py` (6 new cases), `web/app.js`/`web/style.css` (`risk-info`, `fc-basis`), cache-busters bumped.
- **Follow-up (unchanged from HANDOFF §5):** polder/drainage-zone polygons are the real fix for "near me"; until
  then this distance/agreement proxy is what confidence is built on, for both the overview card and this outlook.

### D-043 — Open source release under the MIT License
- **Date:** 2026-09-27 · **Status:** accepted (owner prompt: "Upate the license in github to open source, you can recomend the optimal choice"; owner confirmed the recommended MIT License).
- **Context:** The repository was made public on 2026-09-26 without a LICENSE file (D-028, Q10: all rights reserved by copyright default). With public visibility, an active REST API for AI agents and civic tech, and live flood monitoring, an open source license allows disaster response organizations, researchers, civic tech volunteers, and government agencies (HII, BMA, GISTDA) to adopt and reuse the codebase.
- **License Options Evaluated:**
  1. **MIT License (Selected):** Most permissive, widely recognized, zero friction for civic integration, academic research, and public disaster mitigation. Allows anybody to use, modify, and distribute with simple copyright attribution.
  2. **Apache-2.0:** Permissive with explicit contributor patent grants, trademark terms, and corporate/institutional protections.
  3. **GNU AGPLv3:** Strong copyleft requiring anyone running modified network/cloud services of the pipeline to open-source all changes.
- **Decision:** Released under the **MIT License**. Created `LICENSE` file in repo root, added `license = { text = "MIT" }` to `pyproject.toml`, added MIT badge to `README.md`, updated documentation and status checks (closing Q10 and KI-503). Third-party data sources retain their respective terms per `docs/SOURCES.md`.



### D-044 — National scope: monitor first, forecast later
- **Date:** 2026-09-27 · **Status:** accepted (owner answers to the national grill; research validated in [VALIDATION_2026-09-27_nationwide.md](../../research/VALIDATION_2026-09-27_nationwide.md))
- **Context:** the owner asked how to extend the forecast to all of Thailand. National **water levels already arrive** (`waterlevel_load`, 805 stations); official thresholds (66 HII level, 87 RID discharge stations), reservoir state (50 large, 448 fresh medium), HII flash-flood potential and DWR's 2,275 village stations are reachable. **Forecasting** outside Bangkok needs a different model per flood type (no tide inland, reservoir control, flash floods, backwater), and each needs its own backtest; none exists.
- **Decision:**
  1. **Monitor first:** a national view of *measured* levels against *official* thresholds, reservoirs, and the agencies' own flash-flood products, with the data tier shown on every statement (APPROACH §19.2). Forecasts only per flood type after a backtest passes (§14).
  2. **Audience:** residents in any province, and local officials and volunteers (อบต., อสม., rescue). Thai, mobile-first.
  3. **Frame:** flood types F1–F8 and data tiers A/B/C from Research_NATIONWIDE (💡); thresholds only from the priority list in APPROACH §19.3, never invented.
  4. **Rejected:** street depth from HAND (D-019/D-021), `api2.thaiwater.net` (no DNS), the HII gate feed (12 of 2,315 rows fresh), egress relays other than the owner's Thai egress, generated evacuation instructions.
- **Consequence:** nothing national is shown to the public before D-046's conditions are met.

### D-045 — Bangkok first: use HII's copy of BMA data; build order
- **Date:** 2026-09-27 · **Status:** accepted as the plan; **validated, not built** (owner: "review and validate first")
- **Evidence (2026-09-27):** HII `public/canal_waterlevel` serves **282 BMA canal gauges** (229 fresh) with the same `WL.xxx.nn` codes and identical values as the flood69 relay (WL.BBN.02 = 0.58 m at 09:15 UTC in both), **+73 fresh gauges** we lack, and bank/warning/critical on 250; HII `public/flood_road` serves **262 BMA road-flood sensors** (241 fresh, depth in cm); HII FEWS has Navy tide predictions for 28 stations (Fort Chula included) and RID discharge thresholds (C.13: 2,176/2,448/2,720 m³/s).
- **Decision (order):**
  1. BMA canals from HII as **primary**, the relay as fallback (reduces KI-218). Check before switching that HII's warning/critical equal the relay's for the 156 shared gauges (D-038 yardstick).
  2. BMA **road sensors** as a map layer **and** as point-check evidence (a measured depth on the road, stored in cm and never mixed with m MSL; D-019/D-021 hold because nothing is interpolated).
  3. Navy tide predictions and RID discharge thresholds in the river station sheets.
  4. Then the national collectors (D-046).

### D-046 — National data: lean storage, local backup first, agencies told before anything is public
- **Date:** 2026-09-27 · **Status:** accepted (owner answers)
- **Evidence:** disk 60 of 75 GB used (12 GB free, shared host); DB 706 MB growing ~74,000 rows/day; **no backup of any kind** (KI-511). DWR and RID answer only from a Thai IP (KI-110) and the only Thai egress is a public VPN relay (KI-505). The national endpoints are public but undocumented.
- **Decision:**
  1. **Local nightly `pg_dump -Fc`** (keep 3) and one tested restore **before** any national collector runs. R2 stays off (D-029). **Amended 2026-09-27 (owner, Q29): "no backup for now"** — the risk (KI-511) is accepted; re-ask before national collectors or when feedback volume grows.
  2. **Lean national series:** dams and thresholds daily, FFPI every 6 h, DWR hourly via the Thai egress, 90-day retention for high-volume series, a freshness filter on every feed (KI-111).
  3. **Collect quietly, ask before public:** national collectors may poll gently (behind a flag, not shown) once built; before national data is shown publicly the owner sends short notes to HII, DWR and RID (drafts in OWNER_ACTIONS) and a reliable Thai egress exists.
  4. The work stays on branch `research/nationwide-scope` until the owner reviews it (owner answer 2026-09-27).

### D-047 — Forecast banner shows how much, and how sure
- **Date:** 2026-09-27 · **Status:** accepted (owner prompt: "the rain legend was too much text; forecast banner didn't say how much the water would rise/fall, when, or how confident")
- **Decision:**
  1. `forecast.change_summary()` outputs direction (`rising`, `steady`, `falling`), 5-step intensity level, numerical likely range (50% conformal band), 90% error band, and an honest confidence label (`medium` only when a model beats persistence by 30% and calibrated; otherwise `low`).
  2. Station card, sheet, and point banner show a coloured chip with the range and confidence.
  3. Tidal peak window shown only when ≥ 3 hours out.
  4. Rain legend sentence replaced with a concise coloured TMD-word pill with a 4-step mini scale.

### D-048 — Human-centered forecast phrasing, progressive confidence indicators, and point outlook visibility
- **Date:** 2026-09-27 · **Status:** accepted (owner feedback on v0.6.3: "in 12h will decrease 11 to increase 17 cm is not understandable"; "can we modify 'มั่นใจต่ำ' with symbol or sign to be UX friendly?"; "in click point, visitor wants to know if water will rise or fall, when and how much before 'คลองรอบจุด'")
- **Evidence & UX Problems:**
  1. Literal conformal delta intervals like `[-0.11, +0.17]` printed as "น่าจะลด 11 ถึงเพิ่ม 17 ซม." read as a bizarre contradiction to citizens, especially alongside a "ทรงตัว" badge.
  2. "มั่นใจต่ำ" sounded like a severe system defect, undermining user trust in reliable baseline telemetry.
  3. When area confidence was `very_low` (due to wide gauge status spreads across 8 km), the banner omitted all canal gauges, withholding rise/fall information that users explicitly sought.
  4. Multiple stacked warning boxes (urgent street alert + high risk forecast banner + overview card) caused cognitive warning fatigue.
- **Decision:**
  1. **Zero-crossing phrasing:** When delta spans across zero under steady conditions, format as `ทรงตัว (อาจแกว่งตัว -A ถึง +B ซม.)` (e.g. `[→ ทรงตัว] ใน 12 ชม. อาจแกว่งตัว -11 ถึง +17 ซม.`).
  2. **Progressive confidence scale:** Replace "มั่นใจต่ำ" with dot indicators and friendly phrasing: `●○○ คาดการณ์เบื้องต้น` and `●●○ คาดการณ์ปานกลาง`, with an explanatory tooltip on the 45-day backtest.
  3. **Point outlook nearest canal visibility:** When area-wide confidence is low/none, the forecast banner explicitly displays the nearest forecast canal gauge (`คลองใกล้เคียงที่สุด (ชื่อสถานี ห่าง X.X กม.)`) with its rise/fall forecast and disclaimer `*(ระดับน้ำที่สถานีคลอง ไม่ใช่ระดับน้ำที่จุดนี้หรือบนถนน)*` (D-021).
  4. **Alert deduplication:** Suppress the top urgent road banner when the forecast banner is already in high-risk alert mode.

### D-049 — Compact UI: single ⓘ confidence indicator, collapsible legends, and progressive technical detail
- **Date:** 2026-09-27 · **Status:** accepted (owner feedback on v0.6.4: "can we show only a single symbol with a color or sign, and put the description in tooltip to reduce text length? Can we put descriptions and legends into tooltips or collapse to save space?")
- **Evidence & UX Problems:**
  1. Three-dot meter and text labels wrapped awkwardly on 390px mobile viewports.
  2. Technical surveying datum (`ระดับน้ำ 1.06 ม.รทก. · ตลิ่ง 0.88 ม.รทก.`) was displayed before observation freshness, cluttering the top of the station sheet for ordinary citizens.
  3. The SVG chart's dense 3-line textual legend (`เส้นทึบ = ...`) pushed actionable user feedback and survey tools down.
  4. The point check forecast banner suffered from vertical bloat due to standalone disclaimer and basis lines.
- **Decision:**
  1. **Single ⓘ confidence symbol with color:** Replaced multi-dot meter with a single circular `ⓘ` button (sky-blue for medium/tide, slate-gray for low/baseline). Full explanation in `title` for desktop hover, plus touch-triggered non-blocking toast (`showToast`) for mobile tap.
  2. **Collapsible chart legend:** Folded chart line definitions into `<details class="chart-legend"><summary>ℹ️ สัญลักษณ์กราฟ</summary>...` saving 3–4 lines of vertical space by default.
  3. **Elevation datum tucked into tooltip button:** Kept freshness prominent on the main line (`ข้อมูล 27 ก.ย. 18:40 (15 นาทีที่แล้ว)`), tucking raw surveying numbers into an adjacent `[ม.รทก. ⓘ]` button.
  4. **Compact forecast banner:** Moved forecast basis to a header button `อ้างอิงข้อมูล ⓘ`, and integrated canal disclaimer into a label tooltip `ⓘ`.
  5. **Footer methodology legend:** Added the confidence color key directly to the "ที่มาข้อมูลและวิธีคาดการณ์" popup.


### D-050 — 48-hour forecasts only where proven; archive and score HII's official forecast; next model = network STAR + rain
- **Date:** 2026-09-27 · **Status:** accepted (owner grill: "12+24 h, 48 h only if skilled"; "no sign of falling yet"; "prove the forecast from HII"; "research how to improve 48 h"; "should the model include forecast rain?"; "review STAR / SSN / k-NN / GTWR / ST-GNN")
- **Evidence:** [research/2026-09-27_forecast_48h.md](../../research/2026-09-27_forecast_48h.md). Production backtest: only 7 of 102 gauges beat "no change" by ≥ 30 % at 48 h (all tidal river/estuary); median 90 % band 80 cm at 48 h. HII publishes an official hourly 7-day forecast for CPY011, CPY014, PAS008 and RID discharges (C.13 flat at 1,950 m³/s = constant-release assumption). Experiments: upstream + dam release cut Ayutthaya's 48 h error 26.8 → 18.6 cm; forecast rain (issued 1–2 days early) cut Lat Phrao canal 42.9 → 36.5 cm and Samsen 22.3 → 18.1 cm; network neighbours beat proximity neighbours and k-NN analogues everywhere.
- **Decision:**
  1. **Horizons:** 12 h and 24 h as now; a **48 h line only at gauges whose 48 h backtest gives "medium" confidence** (`change48` in the API).
  2. **No-fall wording:** at watch/warning/critical gauges whose 24 h forecast is not falling, say "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า". Never "stable for 48 h".
  3. **HII forecast:** collector `hii_fews_forecast` archives every issue (table `external_forecast`); `scripts/score_hii_forecast.py` compares HII, "no change" and ours on the same issue times. **Not shown** until it beats both at a station and lead; then labelled as HII's, with the dam-release assumption.
  4. **Next model (not built yet):** per-gauge network space-time AR (own tide/trend + upstream gauges + C.13 release) **plus archived rain forecasts**, behind the existing skill gate, validated on ≥ 3 windows with rolling origin and event scores. SSN only for along-river values later; k-NN and GTWR (as recency weighting) revisited with more history; ST-GNN not now.

### D-051 — One point panel (issue #3) and a report button (issue #2); all caveats behind one ⓘ
- **Date:** 2026-09-27 · **Status:** accepted (owner: "keep the information from the current version"; "everything into ⓘ"; "dots follow the confidence gate"; "reverse geocode if it doesn't slow the click"; "button → popup sheet")
- **Decision:**
  1. The point sheet shows one panel: kicker "แนวโน้ม 12–24 ชม. ข้างหน้า" + ⓘ, a large headline, then "ปัจจัยที่ใช้คาดการณ์" — canal, rain, street reports — each with a **coloured dot and a word**. The separate street banner, overview card and disclaimer box are merged in; decorative emojis removed.
  2. **Canal dot follows the gate (D-042):** grey "ประเมินไม่ได้" when gauges are far or disagree (never red from one overflowing gauge among calm ones); otherwise the area category colour. Rain = TMD colour; street = red ≥ 3 reports/1 km/6 h, amber 1–2, grey 0.
  3. **Caveats behind ⓘ (amends D-021 / GUIDELINES §6.12):** sources, "gauge ≠ your street/home", walls and polders, distance notes live in the ⓘ box of the panel. The panel wording itself never states a level at the pin, and the canal factor says "ประเมินไม่ได้" when it cannot judge.
  4. **Nearest canal (fixes the D-048 fallback):** only a *canal* gauge within 3 km, chosen server-side (`forecast.nearest_canal`), never a river gauge.
  5. **District line** under the coordinates from `/api/reverse` (Nominatim via our server, rounded to ~1 km, cached, never logged); filled in after the panel renders, so it never delays the answer.
  6. **Report form** opens from one full-width button in a popup. Baseline before the change: 57 reports in 24 h (56 with a depth); compare after release.

### D-052 — Network space-time AR + rain ("star") as a production forecast method
- **Date:** 2026-09-27 · **Status:** accepted (owner: "Q32: continue")
- **Evidence:** [research §9](../../research/2026-09-27_forecast_48h.md#9-built-and-proven-network-star--rain-in-production-d-052-v080). Three 45-day windows with production code; out of sample (choose on one window, score on the next) `star` kept its gain at 87–100 % of gauges, median 9.5–25 %. Gauges with 48 h skill ≥ 0.3: 8 → 35 in the latest window.
- **Decision:**
  1. `star` joins persistence / tide / tide_trend / trend in `forecast.evaluate`, compared on the same rows, chosen per gauge and horizon only where it wins and passes the skill gate (GUIDELINES §2). No new display rules: the existing confidence gate (D-047) and 48 h rule (D-050) decide what is shown.
  2. Inputs: own tide/trend, 2 upstream Chao Phraya gauges (river km), C.13 release downstream of the dam, forecast rain at the nearest rain point. Training rain = Open-Meteo previous runs (table `rain_hindcast`, collector `openmeteo_prev`, daily); live rain = the latest `weather_forecast` run.
  3. If today's inputs are incomplete, the path falls back to the gauge's best own method with that method's error band (`q_all` in the payload).
  4. Forecast payload version `star-0.2`.
- **Next:** interval coverage checked out of sample; canal gains depend on rain alone — BMA pump/gate data would be the next input; the same scripts are the starting point for the national phase (research §8).

### D-053 — BMA Canal Historical Telemetry Access via HII TIWRM and Dual Ingestion Architecture
- **Date:** 2026-09-27 · **Status:** accepted (v0.9.0 release) · **Corrected by [D-054](#d-054--bma-canal-history-from-hii-and-a-nearest-gauge-canal-gate) (review 2026-09-27):** the `BKK*` gauges are HII's own gauges, and all but BKK007/BKK008 already had ~1 year of hourly history (the code change added BKK007); the real history for BMA's `WL.*` gauges comes from HII `waterlevel_graph?station_type=canal` (D-054). "BMA local datum" is unverified: we only know BMA and HII differ 0.3–0.6 m (KI-217); the "ม. (หมุด กทม.)" label was never implemented.
- **Context:** BMA stations (`WL.*` series, e.g. `WL.KTY.01`, `WL.AJP.01`, `WL.BKY.02`, `WL.KLA.01`, `WL.LPW.01`) are geo-blocked from non-Thai datacenters. A probe using our project's Thai residential VPN egress the VPN Gate relay in Ayutthaya) verified that BMA's perimeter subnet drops all incoming TCP SYN packets on ports 80/443 (tinyproxy 500), while other Thai agencies (`ews.dwr.go.th`, `hydro.navy.mi.th`) connect normally (HTTP 200). Furthermore, BMA's own dashboard does not host multi-week historical time series.
- **Decision:**
  1. **Dual Ingestion Architecture:**
     - **Live monitoring:** Continue polling `flood69.peoplesparty.or.th/api/klongmap` (`bma_klong`) every 5 min for 199 BMA stations (`WL.*`), accumulating history in PostgreSQL.
     - **30-day historical telemetering:** Ingest HII ThaiWater canal telemetry stations (`BKK*` series) via `https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}`. This provides 30 days of 10-minute resolution history (4,310+ points per station) without authentication or geo-blocking.
  2. **Station Coverage:** Add all verified `BKK*` canal gauges (`BKK001`, `BKK002`, `BKK003`, `BKK005`, `BKK006`, `BKK007`, `BKK008`, `BKK009`, `BKK013`, `BKK015`, `BKK017`, `BKK018`, `BKK019`, `BKK020`, `BKK021`) to `EXTRA_STATIONS` in `config.py` with automatic coordinate and name backfilling from HII map feeds.
  3. **Datum Separation (KI-217):** Keep BMA local datum and HII MSL / Ko Lak datum explicitly labelled in UI and API; do not average raw elevations across the two networks.


### D-054 — BMA canal history from HII, and a nearest-gauge canal gate
- **Date:** 2026-09-27 · **Status:** accepted (owner grill: "1 year, hourly"; "nearest gauges first")
- **Evidence:** HII `waterlevel_graph?station_type=canal&station_id=…` (found in thaiwater.net's app) serves BMA's `WL.*` gauges at 15 min back to at least 2024-01; values identical to the relay (WL.SSB.07: 46 matching times, difference 0.0 m, 2026-09-27). BMA gauges had ~28 h of our own history, so all 199 fell back to "no change". Over a grid of 64 Bangkok points the old gate (all gauges within 8 km must agree) gave "ประเมินไม่ได้" at **53 (83 %)**; the nearest gauge is typically 1.9 km away.
- **Decision:**
  1. Collector `bma_history`: one year hourly for every BMA gauge (5 per run until done, progress saved per gauge), then a daily 3-day refresh that fills relay gaps. Same BMA values and datum as the relay; never mixed with HII m MSL.
  2. **Canal gate from the nearest gauges:** agreement is judged among up to 3 gauges within 3 km; the 8 km circle is only counted and ranged (`min_all`/`max_all`). Result on the same 64 points: "ประเมินไม่ได้" 53 → 25 (the rest are places where the nearest gauges really disagree).
  3. *(Amended v0.10.2: when the nearest canal has no forecast, the nearest canal with one is shown too, and each line says when the water may drop; the summary is one plain sentence — KI-232.)* The panel leads the canal factor with **the nearest canal gauge** (name, distance, agency, status, 24 h and 48 h change), notes "ห่างเกิน 3 กม. …" when it is far, and folds the other stations into one line. Area words use the combined short labels (ใกล้ตลิ่ง/คลองเต็ม) because an area mixes HII (bank) and BMA (drainage-level) gauges.

### D-055 — 48 h line everywhere, honestly labelled; lists show 24 h; shorter rain sentence
- **Date:** 2026-09-27 · **Status:** accepted (owner: "add a longer 48 h trend"; "show 24 h instead of 12 h in lists"; "shorten the redundant rain sentence") · **Amends D-050 §1**
- **Decision:**
  1. `change48` is given wherever a forecast exists, with `proven` = the 48 h backtest gives "medium". Proven: direction chip + likely range, as for 12/24 h. **Unproven: a dashed grey "? 48 ชม." chip, "ยังบอกทิศทางไม่ได้ · ช่วงที่น่าจะเป็น A ถึง B ซม."** — a range, never a direction (e.g. BKK008: −10 to +31 cm).
  2. The "too wide to show" rule tests the likely (50 %) range, which is what is printed (> 0.75 m), instead of the 90 % band (> 1.5 m). BKK005-type bands stay hidden; BKK008's 48 h range is shown.
  3. Station lists show the 24 h change (12 h only where 24 h is missing).
  4. The outlook sentence no longer repeats the rain amount (it is in the rain factor): "มีรายงานน้ำรอระบายในพื้นที่ และคาดฝนปานกลาง อาจมีน้ำขังบนถนนช่วงฝนตก".
  5. Recovery times are windows without false precision: dates only when the window is ≥ 24 h, whole hours otherwise (was "30 ก.ย. 01:12 – 2 ต.ค. 05:12").

### D-056 — One trend format and one direction rule in every view
- **Date:** 2026-09-27 · **Status:** accepted (owner: "why do 24 h and 48 h have different formats?"; "the panel and station formats are confusing and inconsistent"; "compact the canal factor"; grill: aligned rows, same rule for all horizons, trend first in the sheet) · **Amends D-047, D-055**
- **Evidence (audit at 390 px, 2026-09-27):** 12/24 h put the direction in the chip and the horizon in the text, 48 h the reverse; 24 h showed a direction even for the "no change" model while 48 h withheld it; horizons differed per view; status was a pill, coloured text or a headline; the sheet kept emojis and a duplicate "ทรงตัว" headline; two note boxes pushed the trend below the fold; CPY015 read "ใกล้ตลิ่ง" while 158 cm below its bank.
- **Decision:**
  1. **Aligned rows everywhere** (list: 24 h; panel: 24 + 48 h; sheet: 12 + 24 + 48 h): `ใน N ชม. · chip · signed range · ⓘ`.
  2. **A direction only where a real model beat "no change" at that horizon** (method ≠ persistence, i.e. the backtest's own gate); otherwise a dashed grey "? ไม่แน่ชัด" with the range. The ⓘ colour shows medium vs low confidence. The `proven` flag of D-055 is no longer used by the UI.
  3. *(Refined v0.11.1: every gauge is a block — label line, bold name · distance · pill, then its rows — KI-234.)* **Canal factor compacted:** one gauge line (name, distance, status pill), its rows and one "when it drops" line; a relay-only nearest canal gets a single line and "คาดการณ์จากคลองใกล้เคียง:" introduces the gauge that carries the trend; the why/where details sit behind "รายละเอียด".
  4. **Sheet order:** status → BMA margin line → freshness (+ source/datum in ⓘ) → trend block (rows, when it drops, peak, chance of reaching the bank) → street note → chart → notes → method → feedback; no emojis in the sheet text.
  5. **Say what is measured:** bank-based watch/warning with the bank still > 30 cm away read "น้ำเต็มลำน้ำ N %" (share of channel depth), not "ใกล้ตลิ่ง".
  6. *(v0.11.2: the can't-summarise outlook is one short headline + the rain condition, KI-235.)* Kicker "คาดการณ์ข้างหน้า" (rows carry their own horizons); user depth reports counted as "N ราย".

### D-057 — Hide erratic (pump-affected) gauges; drop single-reading dropouts
- **Date:** 2026-09-28 · **Status:** accepted (owner, on WL.SSB.08: "you can filter out this kind of stations, the water levels might be effected by pumping. It's not easy to predict.") · **Applies D-024**
- **Evidence:** KI-237 (41 gauges with reversing spikes in 7 days, all stored `ok`; four patterns; a plain Hampel filter both missed the oscillating gauges and removed real readings).
- **Decision:**
  1. **Dropouts** (≥ 0.30 m away from the level before for one or two readings, then back within 10 cm, all within 30 min) are flagged `dropout` and hidden everywhere; the gauge stays fully visible. This keeps real warnings such as WL.LPT.03 (critical) on screen.
  2. **Erratic gauges** (≥ 3 other steps of ≥ 0.30 m within 30 min in the last 24 h) keep their dot and chart of measured values; level, status, trend and forecast are hidden with the note `erratic` ("ระดับน้ำขึ้นลงเร็วผิดปกติ … อาจมีการสูบน้ำใกล้จุดวัด หรือเครื่องวัดขัดข้อง"), and they are not used in the point check. The 24 h window keeps a gauge hidden through calm spells between pump runs; it returns by itself after 24 calm hours.
  3. Thresholds live in `floodwatch.qc`; revisit when a gauge is wrongly hidden or a pump gauge slips through.

### D-058 — Say what the water did in the last 24 h, in finer words
- **Date:** 2026-09-28 · **Status:** accepted (owner: "a few cm lower in a flood is significant"; "replace it with finer words for small changes") · **Amends D-056** (the "no fall" sentence)
- **Evidence:** KI-240 (48 of 48 clearly falling gauges showed no fall; the no-fall sentence at 26 falling gauges).
- **Decision:**
  1. A measured line "24 ชม. ที่ผ่านมา: <word> N ซม." under the trend rows in the sheet and the point panel (and in place of the 1-3 h change where a gauge has no forecast). It is a measurement, so it needs no model skill; forecast rows keep the D-056 rule unchanged.
  2. Words by the rounded cm, so words match numbers: < 2 ทรงตัว (เปลี่ยนไม่ถึง 2 ซม.) · 2-4 ลดลง/เพิ่มขึ้นเล็กน้อย · 5-19 ลดลง/เพิ่มขึ้น · ≥ 20 ลดลง/เพิ่มขึ้นมาก; a direction only when a straight line explains ≥ 50 % of the 24 h (R²), otherwise "ขึ้นลงสลับกัน" (unless the ups and downs stay within 5 cm).
  3. "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า" is retired. Never a flooded area or a depth at a pin from these centimetres (D-019, D-021).

### D-059 — River gauges never judge canals; a lone close gauge is checked; one distance band
- **Date:** 2026-09-28 · **Status:** accepted (owner: "review till no problem"; follows issue #3 "never red from one overflowing gauge among calm ones", KI-223, KI-239) · **Amends D-054**
- **Evidence:** KI-239 (review) and the pin-grid comparison (426 Bangkok pins, live stations 2026-09-28): usable statements 55 % → 50 %, 9 red single-gauge statements removed where a gauge within 5 km disagreed by 2+ ranks.
- **Decision:**
  1. `area_index` skips river gauges: the river outside the walls is never evidence about canal drainage.
  2. One gauge within 3 km still gives "low" confidence (D-054) unless a gauge between 3 and 5 km (`CHECK_KM`) differs from it by 2 or more ranks; then "very_low" (no canal verdict).
  3. The headline trend uses gauges from the same band as the gate (3 km when a canal gauge is that close, otherwise 5 km), never gauges from other polders further away.

### D-060 — Trend rows follow the measured trend; "ทรงตัว" only within ±5 cm
> **Override superseded 2026-10-03 by D-080:** rows no longer follow the measured trend beside the model; the recent-pace rule is the model method "recent". The measured 24 h line stays.
- **Date:** 2026-09-28 · **Status:** accepted (owner: "a few cm lower in a flood is significant"; "the trend in chart shows lowering slowly in 48 hr, but we said ทรงตัว"; chose "Always follow the measured trend" over an odds chip or a ≥ 70 % gate) · **Amends D-056, D-058**
- **Evidence:** KI-242; continuation backtest (canals 53–64 %, rivers 70–96 %).
- **Decision:**
  1. Where no model beat "no change" with a direction (persistence, or a model saying steady), the 12/24/48 h rows take the direction and size word of the measured trend (`qc.observed`: 24 h, else 48 h). The row shows "ตามแนวโน้มที่วัดได้" instead of numbers; the ⓘ gives how often such a trend continued at this gauge and the past range (`forecast.continuation`). A model that sees a direction keeps its word.
  2. A measured trend needs ≥ 2 cm; it is "mixed" only when the ups and downs are ≥ 5 cm or larger than half the change (whole-cm steps are not noise).
  3. "→ ทรงตัว" only when the likely range stays within ±5 cm; otherwise "? ไม่แน่ชัด"; a longer horizon is never shown surer than a shorter one.
- **Known cost:** in canals such rows are right about 5–6 times in 10; the ⓘ says so.

### D-061 — Resident at home first; a short action guide
- **Date:** 2026-09-28 · **Status:** accepted (owner answers, UX round 12: main user "resident at home"; advice "full action guide", "I draft and ship directly", "collapsed button, 3 bullets"; "collapse operator lines"; "hide stuck gauges"; "do not describe in panel too long")
- **Decision:** "ควรทำอะไรตอนนี้" under the pin outlook, collapsed, 3 bullets per risk level (high / moderate / low), drawn from DDPM (ปภ.) public advice (move belongings and cars up, cut the power, keep supplies and documents at hand, follow official notices, 1784/1555), with "ทำตามประกาศของเจ้าหน้าที่ก่อนเสมอ". Operator lines behind "รายละเอียดข้อมูล"; the map opens on Bangkok; the Chao Phraya tab starts in Bangkok; the GPS panel names the district; every new panel text fits one or two lines at 390 px.

### D-062 — One story per view: the headline, the rows and the list say the same thing
- **Date:** 2026-09-28 · **Status:** accepted (owner: "prove the consistency of panel and text"; "keep number to show"; "we do not need ควรทำอะไรตอนนี้ … too much text"; "วิธีคาดการณ์ … should be in collapsed info") · **Amends D-060, D-061**
- **Evidence:** KI-244 and the consistency proof (`scripts/ux_consistency.py`).
- **Decision:**
  1. The pin headline speaks for the gauge the canal factor shows with rows, and for 24 h (the horizon the panel shows); "ทรงตัว" only when that row is steady.
  2. A model gives a direction only when its whole likely range agrees; otherwise the measured trend (D-060) or the ±5 cm rule applies. The same rule runs in the API and the UI.
  3. Measured-trend rows show "ราว N ซม." = the measured trend continued and damped (slope·h·e^(−h/48)); the past odds stay in the ⓘ.
  4. Every view evaluates 12 → 24 → 48 h even when it prints fewer rows.
  5. D-061's action guide is withdrawn (too much text in the panel); the method line is collapsed.
  6. Before a release, run `scripts/ux_consistency.py`; C1–C3, C5, C6 must be 0.

### D-063 — v0.15 is the baseline; old issues are judged against it
- **Date:** 2026-09-29 · **Status:** accepted (owner: "This version is already good and keep this concept"; "review git issues, but do not need to follow, because the issues could be outdated")
- **Decision:** the v0.15 concept (D-058, D-060, D-062) stays. GitHub #6 (one-phrase factor headers) adopted — it shortens the panel without changing the concept; #7 (a one-line canal factor with the rows under รายละเอียด) not adopted, the owner keeps the rows and numbers visible; #8 (hover colour) and #9 (page fits the screen) fixed as bugs.

### D-064 — Nationwide parity: every gauge gets Bangkok's history, forecast gate and panels
- **Date:** 2026-09-30 · **Status:** accepted (owner grill 19:48–20:30 UTC: "should be the same as in Bangkok, consider the consistency"; "I have more free space in server, you can consider to do full forecast"; inputs "rain + learned upstream"; UI "full parity, กทม. default"; "go public, send notes in parallel"; name "keep BKK FloodWatch, add a ทั่วประเทศ line"). Spec: [2026-09-30-nationwide-parity-design.md](../superpowers/specs/2026-09-30-nationwide-parity-design.md)
- **Evidence (2026-09-30, production DB and live site):** the 733 gauges outside the focus area had only readings since 2026-09-26 (history collectors and the forecast filtered `in_focus`); HII serves each a year in one request (URTU07: 8,537 hourly readings, 730 KB). Backtest on 40 Bangkok gauges: history length matters only at a full year (48 h mean skill 0.20 with 60–180 days, 0.28 with 365; 36/40 over the gate). A year of their own history alone gave **0 of 12** nationwide gauges any skill: Bangkok's skill comes from `star`'s upstream and rain inputs.
- **Decision:**
  1. A year of history for every HII-network gauge, bounded by a 400-day retention (BMA never deleted, KI-218).
  2. The same forecast ladder and gate everywhere (line only where the backtest beats persistence by > 10 %; range otherwise). `star` inputs outside the focus area: 0.5° rain cells and upstream gauges learned per basin (leading change, before the backtest window). Focus gauges keep their proven inputs.
  3. Forecasts in their own container with a daily cached backtest; collectors never wait.
  4. UI parity: region chips for the country (default กทม., D-033); counts and list follow the chip, the map shows every gauge and the chip moves its view (amended v0.16.1, KI-253); water word from the agency's river name; another agency's gauge at the same place linked, never merged (KI-217); pins outside Bangkok judged from the river/stream gauges near them (the D-059 polder rule applies where the nearest gauge is a Bangkok-area gauge).
- **Supersedes:** D-044's "forecast later" (the per-gauge backtest gate replaces the per-flood-type gate for showing a line) and D-046 §3's "public only after the agency notes" (the notes stay an open owner action, Q3). D-046's lean-storage principle stands (bounded retention).
- **Outcome (2026-10-01 14:20 UTC, after the backfill):** with rain cells + learned upstream, 27/19/19 of 51 sampled nationwide gauges beat persistence by > 10 % at 12/24/48 h (own methods alone: 9/8/6); Bangkok unchanged (36/40 at 48 h). APPROACH §19.8.
- **Not done (open):** dam release scenarios beyond C.13 (e.g. Ubol Ratana below E.29), DWR/FFPI/GISTDA national layers, Traffy outside Bangkok, a status label for rivers other than "ใกล้ตลิ่ง/คลองเต็ม".

### D-065 — The default region follows the user's location when GPS is allowed (amends D-033)
- **Date:** 2026-10-01 · **Status:** accepted (owner answer to Q40: "Allow GPS")
- **Decision:** กทม. stays the default for anyone who has not allowed location. Once the user allows GPS (📍 สถานีใกล้ฉัน), the region chip becomes the region of the nearest gauge within 60 km, and is remembered. With permission already granted, later visits apply it silently. A chip tapped by hand wins until the next 📍 tap.
- **Rulings (Claude, owner may override):** no location prompt on page load (browsers discourage it and a refused prompt usually sticks); the region comes from the nearest gauge, not a province lookup (no reverse geocoding call, works offline from the loaded list).

### D-066 — Basin and river maps: upstream links within one river system; "water from upstream" line
- **Date:** 2026-10-02 · **Status:** accepted (owner: "ข้อมูลลุ่มน้ำ … เอาใช้ประโยชน์อะไรได้ไหม" → chose items 1+2, 3, 4)
- **Evidence:** [research/2026-10-02_basins.md](../../research/2026-10-02_basins.md) — HII's public `basin.json` (22) and `river_main.json` (93 rivers, 40 systems); backtest on 39 gauges: river-system rule neutral (links changed at 1/39), basin-mean rain no gain, upstream-cells rain small and not significant, placebo clearly worse.
- **Decision:** (1) every gauge gets its 22-basin polygon, main river and river system (weekly `hii_geo`), filling missing basin names; (2) learned upstream gauges must share the basin polygon and, when both are on main rivers, the river system; (3) station sheet and pin panel show the first upstream gauge's measured 24 h change and the learned travel time ("มักถึงที่นี่ในราว N ชม.") with an ⓘ — a measurement, never a forecast. Not adopted: basin-mean rain; upstream-cells rain until HydroBASINS sub-catchments can be tested (owner download, behind a bot challenge).
- **Not for:** Bangkok polders (drainage follows canals, gates and pumps, not basin maps) and never to paint flooded areas (D-019).

### D-067 — Basin data validated; no further basin-based forecast inputs (amends D-066)
- **Date:** 2026-10-02 · **Status:** accepted (owner: "validate and check, whether the basin data is useful"; downloaded ONWR's 22 basins and HydroBASINS)
- **Evidence:** [research/2026-10-02_onwr_basins.md](../../research/2026-10-02_onwr_basins.md) — ONWR's legal 22 basins = HII's `basin.json` (1,011 of 1,026 gauges identical, the rest on boundary lines or a spelling); cross-basin upstream links: open rule worse (48 h gate 5 → 3 of 10, RMSE +4.4 %), hydrologically directed rule finds no qualifying link. [research/2026-10-02_catchment_rain.md](../../research/2026-10-02_catchment_rain.md) — HydroBASINS catchment rain on 296 gauges: no gain (RMSE ±0.0 %, gate 181/155/137 → 175/150/138), placebo clearly worse.
- **Decision:** keep D-066 as is: HII's map for basins, upstream links within one basin and river system, own-cell rain. ONWR and HydroBASINS files stay on the server for research (`data/basins/`, `scripts/prepare_basins.py`), not in git (ONWR: no licence stated; HydroBASINS: 413 MB).
- **Revisit:** with hourly measured rain (Q43, ~mid-December 2026), or if a gauge network gains gauges right below confluences (the directed rule would then have links to find).

### D-068 — AI on request only: one button, rules tell the story, GLM may retell it after a check (amends D-022; amended v0.22.0)
> **Amended 2026-10-04 by D-089:** one scheduled AI text exists — the national ticker (worker, every 30 min, checked); per-place AI stays on request.
- **Date:** 2026-10-02 · **Status:** accepted (owner: "ลองให้คนทั่วไปใช้ เขาไม่เข้าใจง่ายๆ … อยากให้มีฟังก์ชันการแปลความ เช่น ให้ ai แปลเป็นความเข้าใจง่ายๆ … think more than just translation … be careful about UX … You can use GLM"; "validate and test also the AI assistance, think about the users who are common people"; on v0.18.0: "AI สรุปดูไม่ได้ข้อมูลอะไรเท่าไหร่ … ควรเล่าหรืออธิบายให้ดีกว่านี้ ว่าสถานีที่ใกล้เคียง แต่อยู่ไกล เป็นยังไง"; on v0.18.3 with a weather app's AI card: "I got complicated info … they try to explain easily"; then "AI assistant generated only when requested, single point for that is enough?" → chose one "ask AI" button "to reduce unnecessary AI generated"; on v0.22.0: "review using AI in create ให้ AI สรุปให้ฟังง่าย ๆ , what will you suggest to improve? Test and validate till get the optimal UX ... Try to let AI prepare it into simple, attractive and lovely Thai language which are easy to understand. I need the natural smooth language ... Validate and check the expectation as you are visitors also")
- **Evidence:** [research/2026-10-02_ai_explain.md](../../research/2026-10-02_ai_explain.md). Free AI answers gave a go-verdict ("พาลูกไปโรงเรียนพรุ่งนี้เช้าได้ไหม" → "ได้ครับ …") and called a canal "ปกติ" where the panel cannot judge; rewording whole rule answers passed a strict check 43 % of the time; retelling a rule-written story passes 91 % (198 answers, 33 places) at a median 4.0 s. glm-5.3-flash always reasons (API 1210): 9–10 s by default, `reasoning_effort: "low"` ~1–5 s.
- **Decision:**
  - Under every pin headline, a **plain line** by template (`explain.plain`): which water it speaks about — "แถวนี้" only when the panel's gauges are close and agree, else "สถานีที่ใกล้ที่สุดอยู่ห่าง N กม. น้ำที่นั่น…" — how full it is, the 24 h row's word, rain and street reports in words. No AI.
  - **One button, "✨ ให้ AI สรุปให้ฟังง่าย ๆ"** — the only place AI runs; nothing calls GLM until it is tapped.
  - **Zero-wait two-stage rendering (amended v0.22.0):** Tapping the button renders the deterministic rule story (`explain.narrative`, <50 ms) immediately so visitors never wait on a blank shimmer. Concurrently, GLM retells the story in the background (`&part=gist`) and the UI smoothly swaps in the warm retelling once checked.
  - **Voice accessibility ("🔊 ฟังเสียง", added v0.22.0):** Web Speech API (`window.speechSynthesis`, `th-TH`, rate 1.0) allows elderly or vision-impaired users to listen to the explanation hands-free.
  - **Hedged bank phrasing accepted (amended v0.22.0, KI-275):** `explain.check` allows natural Thai hedging when the rule permits it (`ยังไม่น่าจะถึงตลิ่ง`, `น่าจะยังไม่ถึงตลิ่ง`, `คงยังไม่ถึงตลิ่ง`, `ยังขึ้นไม่ถึงตลิ่ง`), while still rejecting absolute guarantees (`น้ำไม่ถึงตลิ่งแน่นอน`).
  - `explain.check` rejects a retelling with a new number, a direction the rules don't say, a past change told as the future, a stronger word than the forecast, an absolute verdict (ได้ครับ, ไปได้, ไม่ท่วม, ปลอดภัย, ปกติ, ไม่ต้อง…; a polite particle after "ไม่ได้"/"รับน้ำได้" is not one), a dropped "cannot tell", a far or missing gauge's state told as "แถวนี้", English, or > 420 characters (`GIST_MAX = 420` in v0.22.0).
  - GLM gets only the rule story and lines — never the pin, a place name or a search (D-032). `/api/explain` queries are redacted from logs and kept out of robots. The API also answers the other rule questions (home, car, travel, prepare, numbers); the page does not offer them now (owner: one entry point).
  - Bounds: 8 s server timeout, 7 s client wait, cache per (question, rule text) 6 h; failures/rejections cached for only **120 s** (reduced from 30 min in v0.22.0 so transient timeouts don't lock residents out), daily cap 1,500 per app process, ai.run's circuit breaker; `AI_EXPLAIN=0` switches GLM off. The site works fully without it.
- **Unchanged from D-022:** AI never writes a status, a level, a forecast or a warning; the worker's feedback triage stays as it is.

### D-069 — New sources (GFM, GISTDA, GloFAS, WeatherNext): research verdicts; WeatherNext rain never shown or served
- **Date:** 2026-10-02 · **Status:** accepted (owner: "Research and consider how can we apply this info to improve our app?"; chose: satellite maps "Research only for now", GFM "Use the login now", WeatherNext "Backtest first, internal", GloFAS "for longer outlook" only after a backtest, scope "Research + plumbing")
- **Evidence:** [satellite](../../research/2026-10-02_satellite_flood.md) · [GloFAS](../../research/2026-10-02_glofas_outlook.md) · WeatherNext terms PDF (last modified 2026-09-03), read 2026-10-02.
- **Decision:**
  - **Satellite flood maps (GFM + GISTDA): research only, no UI now.** In Bangkok, Nonthaburi and Pak Kret the radar is blind on 61–71 % of land and mapped no flood in the core while Traffy had 1,040 reports; it imaged the region on 6 days in 30. Where it can see (rice belt, river provinces) GFM and GISTDA agree (89 % of GISTDA's cells). If a UI line is ever added: GISTDA first, observed "seen" only ("ดาวเทียมเห็นน้ำท่วม … เมื่อ X วันก่อน"), never "not flooded", silent where GFM's exclusion mask says the radar cannot see. GFM is keyless (STAC); the account works (owner_status GFM ✅) but adds nothing for this use.
  - **GloFAS: no input, no collector, no EWDS backtest.** Upper bound with perfect future discharge: 0 of 12 main-river gauges gain ≥ 10 % at 3/5/7 days; median −1.6 % to −2.5 % vs our own-trend model. The dams and diversions decide the lower Chao Phraya.
  - **WeatherNext: backtest only, past data only (≥ 1 h old = CC BY 4.0).** Its real-time rain (now and future) is **never** shown on the site or served by our API (the terms count recolouring, cropping or re-timing as the raw data; sharing is limited to known recipients). Any forecast that would use it as an input needs a new decision first: Google's "experimental … not approved for real world use" notice on the site and the Japan/South Korea/Indonesia clause. Access only from the worker (`floodwatch.gcp`, stdlib + openssl, read-only service account in git-ignored `certs/`).
  - New `.env` keys (empty in git): `GFM_EMAIL`, `GFM_PASSWORD`, `GOOGLE_APPLICATION_CREDENTIALS`, `WEATHERNEXT_PROJECT`, `WEATHERNEXT_DATASET`, `EWDS_API_KEY` — worker only, never the web app; `owner_status.py` checks each with one request and prints no value.
- **Revisit:** satellite UI if users outside Bangkok ask what the fields look like; WeatherNext after its backtest (owner step WNEXT: subscribe to the listing).

### D-102 — The impact tab reads like the app (chips, one ★ card, rows, sheets); a 7-day reservoir outlook on the dams list, model gated per dam and horizon
- **Date:** 2026-10-05 · **Status:** accepted (owner's answers 2026-10-05: "just click and see the evaluation and can easily choose … not read so long"; Q58 "continue testing", home = impact tab dams list; stop rule = two-sample gate; cadence back-to-back)
- **Context:** the first scenario page was a report (paragraphs, tables, notes on the panel); the other tabs onboard with chips, one-line items and a sheet. Q58 asked whether rain can forecast reservoir inflow nationwide; the honest tests said yes for the big dams with observed rain (MODELS §9b) and needed the operational check with archived rain *forecasts*.
- **Evidence:** UI — `scripts/impact_tab_check.py` on the redesigned case view: first screen 768 characters, no paragraph over 160 characters, 4 chips, 1 ★ card, 2 rows, 5 river nodes; a chip opens the dam sheet, a node opens the station's own sheet, the custom plan appears as a row, ℹ️ opens the replay; both 390 px and 1366 px. Outlook — research/2026-10-05_q58_operational.log: 17 dams, 43 scored days, 17 Aug–28 Sep 2026 (Open-Meteo previous runs, leads 1–7, bias per lead learned on the first half of the 92-day archive), model vs persistence: at 3 days ≥ 10 % better for 15 dams (ภูมิพล +35 %, สิริกิติ์ +32, รัชชประภา +31, ลำปาว +34, น้ำอูน +39, ขุนด่านปราการชล +36, ศรีนครินทร์ +21, วชิราลงกรณ +24, สิรินธร +31, อุบลรัตน์ +19, ห้วยหลวง +26, แม่งัดฯ +26, แควน้อยฯ +21, ลำนางรอง +11, กิ่วคอหมา +11), not for แก่งกระจาน (+7) and แม่กวงฯ (−20); at 7 days ≥ 10 % for 11 (สิริกิติ์ +49, น้ำอูน +52, ห้วยหลวง +47, ขุนด่านฯ +38, แควน้อยฯ +31, ลำปาว +31, รัชชประภา +29, วชิราลงกรณ +27, แก่งกระจาน +26, ลำนางรอง +22, สิรินธร +20, ศรีนครินทร์ +16) but not ภูมิพล (−12), กิ่วคอหมา (−8), แม่กวงฯ (0), อุบลรัตน์ (+8), แม่งัดฯ (+10); the monthly loss term lowers the 7-day storage error for 13 of 17 dams (e.g. สิรินธร 33.8 → 27.4, อุบลรัตน์ 38.9 → 35.3 ล้าน ลบ.ม.).
- **Decision:** (1) **UI grammar:** the case view = number chips (tap → dam sheet) · one ★ card (plan, three icon lines, one "why") · one-line plan rows with "เหมาะกับ…" badges · ➕ กำหนดเอง and ✨ · a river strip (margin to the bank in the app's colours, tap → the station's sheet) · one ℹ️ collapsible whose buttons open sheets (replay, river table, matrix, method, data request); ⓘ badges toast their text (the app's `.conf-badge`); the disabled what-if card is removed (the custom plan does the same). (2) **Reservoir outlook** (`reservoir.py`, `src/floodwatch/data/reservoir_models.json` written from the research log): per dam the inflow model is used for days 1–3 only if its 3-day gain ≥ 10 % and for days 4–7 only if its 7-day gain ≥ 10 %, else today's inflow is held; bands = the tested residuals of the method used; storage = balance with the monthly loss term and today's release; rain = Open-Meteo past/next 7 days at the catchment points with the per-lead bias; recomputed every 6 h; shown on the dams list (one line + ⓘ with the test result) and in the popup (7-day table). Not public. (3) The Kaeng Krachan scenarios keep holding today's inflow (its model fails at 3 days).
- **Consequences:** engineers see numbers first and read only on demand; the outlook states per horizon which method produced it and how it tested. The scored window is 43 wet-season days (17 Aug–28 Sep 2026) — short; the gate is re-run when a longer archive exists (previous runs grow daily).
- **Revisit:** monthly, re-run `research/2026-10-05_q58_operational.py` as the forecast archive grows; a public reservoir layer only after the owner decides (Q58 said impact tab first).

### D-101 — 7-day release scenarios for Kaeng Krachan: plans found by search, judged on seven effects, ★ by a stated rule; inflow held (the rain model failed its test)
- **Date:** 2026-10-05 · **Status:** accepted (owner's answers 2026-10-05; impact work stays "only for แก่งกระจาน and surrounding")
- **Context:** owner: "Releasing water from dam in next 7 days as scenarios, what will happen … calculate each scenario into water level and flood coverage … offer the scenarios … suggest which scenarios best for what … the optimal scenario and why … you can use AI to assist." Grill answers: show everything, clearly labelled; optimal by a stated rule; scenarios by calculation ("do not need to fix as % or steps, but experiment to find each scenario and validate first"); effects = city first, worst point, least overall, dam · curve · water · warning; cards + sheet; ✨ explains on tap; inflow "rain-driven"; DEM screening "build it, show only if it validates" — later "A and C", GISTDA not reliable enough for validation, so the DEM layer waits; ONWR data (dam releases by outlet 2–3 years, เขื่อนเพชร gates and canal flows, flood-coverage Shapefiles by release level) requested, nothing received yet.
- **Evidence:** research/2026-10-05_kk_inflow_model.log — HII's daily inflow closes the water balance (Δstorage − (inflow − release): median −0.15, IQR −0.57..+0.22 ล้าน ลบ.ม./วัน, 3,199 days); a rain-driven inflow model (ERA5 catchment rain from HydroBASINS lev08 upstream basins, 1,988 km², + yesterday's inflow; fit 2018–2024, test 2025–2026) **lost to holding today's inflow at every horizon** (MAE 0.99 vs 0.80 at 1 day, 3.11 vs 1.57 at 7 days; worse on 72–85 % of days) even with observed rain, and again on a 2024 test; persistence band 10–90 %: ±0.8 (1 d) to −1.3/+1.9 (7 d) ล้าน ลบ.ม./วัน on all days, −7/+6 to −16/+5 on days with inflow ≥ 10. Live 2026-10-05 19:00 UTC: storage 725.9 (132 above the upper curve), 676 candidate plans, 108 meet the constraints; ★ = 17.0 ล้าน ลบ.ม./วัน constant → 679 on day 7 with every gauge ≥ 0.55 m from its bank. A first rule (least impact among plans returning under the curve) chose a 25.0 plan that overtopped B.10 by 1.4 m; a second (no overtopping) chose 19.0 with an 8 cm margin inside the model's 39 cm error — both rejected (KI-302).
- **Decision:** `scenarios.py`: (1) candidate plans by search — hold, every constant on a 0.5 grid, ramps and front-loaded (k days at r1 then r2) on a 2.0 grid, 0..cap, cap = the highest daily release in HII's history (24.36, ⚠️ until ONWR's outlet capacity); (2) reservoir: daily water balance, inflow held at today's with the regime band; (3) river: `impact.whatif` per day with whole-day travel times (unvalidated, labelled 🔴); (4) seven effects per plan; (5) **constraints**: every gauge's margin to its own bank ≥ the replay's mean error of the downstream model at that point (B.10 0.39, B.16 0.48, B.15 0.52, PCH001 0.47 m), storage ≤ the maximum storage, the reservoir not left further from its curve than today; (6) **★ rule**: among feasible plans the fastest return toward the upper curve (earliest day under it, then the lowest day-7 storage), then the gentlest change of release (the first day's step from today counts); when nothing is feasible the page says so and shows the lowering plan with the least overtopping; (7) "เหมาะกับ…" = the best feasible plan per effect; (8) ✨: `explain.scenarios` writes lines and a story from the numbers, GLM may retell them (D-068), never decide. UI: cards like the station list, the app's bottom sheet (7-day table, SVG chart, per-point margins), an effects matrix, a custom day-by-day plan, the rain forecast over the catchment as context only.
- **Consequences:** decision makers get a comparison whose numbers carry their own uncertainty — the reservoir side tested, the river side labelled; the 8 cm case shows why the model error must be a constraint, not a footnote. Flood coverage remains "overtopping per reach" until ONWR's Shapefiles; no DEM layer. More cases wait (owner: Kaeng Krachan only).
- **Revisit:** when ONWR's data arrive — เขื่อนเพชร canal flows change the river side (D-099 gate), hourly releases and outlet capacities change the search range; the nationwide inflow test (research/2026-10-05_dam_inflow_nationwide.log) decides whether reservoir outlooks go national.

### D-100 — `/impact` becomes the main app plus a "💧 ผลกระทบ" tab: national dams at risk, a case picker, Kaeng Krachan on the map
- **Date:** 2026-10-05 · **Status:** accepted (owner's answers 2026-10-05)
- **Context:** owner: "In impact page we need similar map and functions to main page but add the risk and impacts as additional tab or menu, possible, please suggest?" Offered: the main app + a tab (recommended), a standalone page with its own map, or a login menu on the public page. Owner chose **"Main app + ผลกระทบ tab"** with **"Kaeng Krachan case"**, **"National dams at risk"** and **"Case picker for more dams"**.
- **Evidence:** HII `analyst/dam` carries `dam_lat`, `dam_long`, `normal_storage`, `max_storage` for all 50 records (39 physical dams; 11 dams have both a RID and an EGAT record); `dam_yearly_graph` returns the same rule curve for both ids of a dam (ภูมิพล 43 / 1: 366 days, normal 13,462) and none for ห้วยกุ่ม, ปากมูล, ท่าทุ่งนา (EGAT). 2026-10-05: 13 dams above their upper rule curve, 23 between, 3 without a curve. HII's main-river lines include แม่น้ำเพชรบุรี (359 points).
- **Decision:** (1) `/impact` serves `index.html` with one more tab, its view, `impact.css` / `impact.js` (content-hashed `?v=`), noindex, and a CSP for the main app (scripts from us and unpkg only, no inline script; inline styles allowed because `app.js` builds some; OSM tiles; data only from us); `/` is unchanged. (2) `app.js` gets two hooks only: `window.FW_TABS` (an extra tab's view and `show`) and the `fw:map` event once the map exists; its `?v=` goes to 119. (3) The tab: login inside it; "🏞️ เขื่อนทั่วประเทศ": one card and one ◆ per physical dam, coloured by its position against HII's rule curve on the reported date (above / between / below — a fact, not a warning), RID and EGAT side by side, the "largest release since …" note; cases as chips (Kaeng Krachan, pilot), each with its board and the river, dam and gauges on the map. (4) Data: a `dam` table (coordinates, storage bounds) from `hii_dams`; `hii_dams_history` (hourly, ≤ 10 requests) refreshes every dam's current-year releases and rule curve daily and back-fills from 2018; the `impact` task builds `impact_dams` hourly; endpoints `/api/impact/cases`, `/dams`, `/case/{id}` (login).
- **Consequences:** engineers get the whole app plus the risk view; the public page is unchanged apart from `app.js` `?v=`. The `/impact` CSP allows inline styles (weaker than the standalone page's; scripts stay strict). A new case needs its river gauges, ratings and replay before it gets a what-if (the gate, D-099).
- **Revisit:** more cases (ป่าสักชลสิทธิ์ stood the furthest above its curve on 5 Oct) when the owner asks; ONWR's risk layers stay with Q57.

### D-099 — `/impact`: a password page for partner engineers (pilot Kaeng Krachan); the what-if stays off until it beats "keep today's level"
- **Date:** 2026-10-05 · **Status:** accepted (owner's answers 2026-10-05)
- **Context:** owner: "Make extra tab to make case for flood impact analysis, the pilot is แก่งกระจาน … might need a password to open for authorize only … Test & Validate as view from onwr … More requested data will come soon." Answers: audience **ONWR/RID engineers**; **one shared password in the app**; a **separate page `/impact`**; first answer **a what-if release table**; model **rating curves + travel times**; input **ล้าน ลบ.ม./วัน with m³/s shown**; the diversion at เขื่อนเพชร **an input, default from recent data**; a short pilot password "for now" (its value only in `.env`). After the replay below, the owner chose **"Board + validation + data request now"**.
- **Evidence:** research/2026-10-05_impact_anchored_replay.log and the live replay (ratings, travel times and gains fitted on the first 60 % of the year, judged on the last 40 %, every 3 h): level error at B.10 / B.16 on 2026-10-05 — keep today's level 12.5 / 13.6 cm; mass balance + rating curve 39.4 / 48.1; anchored 24.9 / 113.6; learned pass-through gain 12.0 / 13.7 (big changes 28.6 vs 25.9 at B.10). Travel-time correlation r 0.29–0.46. research/2026-10-05_impact_release_vs_b18.log: B.18 carries RID's reported release (366 days, r 0.93, +12.6 m³/s median, same-day response). HII serves the dam's daily history and rule curves (`analyst/dam_yearly_graph`) back to 2018, but no river levels for 2018 — the only year since with a big release (24.36 ล้าน ลบ.ม./วัน, 21 Aug 2018; 2019–2025 ≤ 9.13).
- **Decision:** (1) `/impact` and `/api/impact/*`: one shared password (`IMPACT_PASSWORD`, `.env` only, app only), constant-time check, a signed cookie (HttpOnly, Secure, SameSite=Strict, Path=/api/impact, 12 h) whose HMAC binds a fingerprint of the password, 5 failed tries per 15 min per client and app worker; noindex, robots, a strict CSP and `X-Frame-Options: DENY` on the page. (2) The board: the dam's daily RID record against HII's rule curve and its own yearly history, EGAT's record and the open doubts as questions; the river now (margin to each agency's own bank, flow, travel time with r, when measured); the replay; the data request with CSV templates; the method and the check that B.18 carries the release. (3) **The what-if table is gated:** `/whatif` answers 409 and the page keeps the table off until a method beats keeping today's level by ≥ 10 % at B.10 and B.16 (and on big changes when there are ≥ 30); the state and the replay are rebuilt hourly (worker task `impact`). (4) Dam data: `hii_dams` (6 h) stores HII's national daily records (`dam_daily`) and the pilot dam's yearly history and rule curves.
- **Consequences:** no unvalidated number reaches a release decision; the first ONWR meeting gets the evidence and a precise data request instead of a table that would be quoted. The pilot password is short — acceptable while the page shows public data only; a long passphrase before partner data (OWNER_ACTIONS IMPACT, KI-293). Partner data never go in git (GUIDELINES §7.1).
- **Revisit:** when ONWR/RID data arrive — เขื่อนเพชร gates and canal flows first, then the 2018 river records, hourly releases, release plans and surveyed banks: add them to the replay; the gate decides.

### D-098 — The 90 % band is widened daily so it holds as stated; the printed 50 % range stays
- **Date:** 2026-10-05 · **Status:** accepted (owner: "Yes" to Q54, widen the 48/72 h ranges so they hold as stated)
- **Evidence:** research/2026-10-05_band_calibration.log — a fixed factor learned in the flood peak over-widened later (50 % bands would hold 64–68 %); research/2026-10-05_band_calibration_rolling.log — a daily factor from the last 5 days (outcomes already known, never below 1) brought the 90 % band closer to 90 % in all six horizon × kind cases (72 h "no change" 76 → 94 %, 48 h model 88 → 91 %), but overshot the 50 % band (48 h "no change" 41 → 63 %).
- **Decision:** `risks.band90_factors` (daily, in the track records) → `forecast.widen90` scales q0/q4 around the median per horizon and kind (piecewise linear from 1.0 at 0 h); q1–q3 unchanged. First factors (2026-10-05): ×1.15/1.20/1.40 (model), ×1.00/1.25/1.55 ("no change") at 24/48/72 h. Affects the "5–25 %" bank-chance band and the "9 ใน 10 … ไม่เกิน X ซม." lines; the printed ranges do not change.

### D-097 — Google Flood Hub forecasts feed `star` near a Flood Hub point (STAR_INPUTS 3)
- **Date:** 2026-10-05 · **Status:** accepted (owner: "Yes" to Q55)
- **Evidence:** research/2026-10-04_floodhub_input.log (75 river gauges ≤ 10 km from a point, honest protocol): 72 h −8.3 → −9.2 %, 48 h −11.2 → −11.4 % (worse 7 → 4), no gain at 12–24 h; the API's year of archive equals what we stored live (320/320).
- **Decision:** input = log((q(target day)+1)/(q(issue day)+1)) from the latest forecast issued at or before the hour (`gfh_matrix`, `gfh_change`, vectorised), for non-BMA gauges within 10 km (`nearest_gfh`); `google_floodhub_backfill()` stored a year once (302,408 steps, 103 points); the 6-hourly collector keeps it current. Without a fresh forecast the input is missing and the live `star` falls back to the gauge's own methods. Display of Flood Hub itself is still Q49.

### D-096 — Research never touches live state: read-only connections, a schema lock timeout, AI calls without accounting
- **Date:** 2026-10-04 · **Status:** accepted (after KI-284 and KI-285)
- **Decision:** research scripts open the database with `db.connect_readonly()` (autocommit, read-only); the collector's `init_schema` runs with `lock_timeout = 5s` and retries; research calls `ai.run(..., account=False)` (no daily budget, no breaker); BigQuery research uses one literal point per query, literal init times in small batches and a running byte cap (KI-283 correction). Never redeploy during a research run without these.

### D-095 — ✨ ให้ AI สรุปให้ฟังง่าย ๆ on station sheets (with rain) and on the ⚠️ จับตา tab
- **Date:** 2026-10-04 · **Status:** accepted (owner: "เพิ่ม ✨ … ที่จุด Stations เพื่อสรุปให้ฟังแบบง่ายๆ รวมข้อมูลน้ำฝนไปด้วย" and "… ที่ tab ⚠️ จับตา เพื่ออธิบายสถานการณ์ภาพรวม และเน้นจุดที่วิกฤติ"; "The current version of app is already good")
- **Decision:** the pin's pattern (D-068): rules write the story and the lines (`explain.station`, `explain.watch`); GLM may retell them only after `explain.check`, cached 6 h by content, on request only (`/api/explain_station`, `/api/explain_watch`). Station: the station is the subject, the sheet's own rows, rain measured nearby and forecast; stale data tells no "now"; no button where the level is hidden (D-024). จับตา: `risks.only()` = the tab's filter; over the bank and still rising first (highest above the bank), then rising toward the bank, fast rise, heavy rain; each group closes its own sentence.
- **Checks added for every card:** "กำลังจะ/ใกล้จะถึงตลิ่ง" when the facts say "อาจถึง" (stronger than the forecast), a closing question to the reader; polite particles are dropped (not a reason to reject); 3 tries, 15 s each.
- **Validation:** research/2026-10-04_ai_summaries_validate_run2.log — retelling shown 9/9 จับตา regions and 11/13 stations, 1.2–1.3 tries; what is left is rightly rejected or a timeout.

### D-094 — The national ticker: items with symbols, rising-only "อาจถึงตลิ่ง", Bangkok, dam and river flows; GLM item by item
- **Date:** 2026-10-04 · **Status:** accepted (owner: "ควรจับตาพื้นที่กรุงเทพฯ … แต่ไม่พบสถานีในกรุงเทพฯ ที่น้ำขึ้นจนถึงตลิ่ง"; "very long text, try to use symbols … to see the separation of phrase"; "simple, attractive and lovely Thai … natural smooth language"; "You can use only GLM … as at current ✨ ให้ AI สรุปให้ฟังง่าย ๆ")
- **Decision:** may-reach gauges carry their trend group (tab pills like over the bank); the ticker names provinces only for gauges whose water is rising; new facts: a Bangkok line, the C.2 (Nakhon Sawan) and C.13 (dam release) discharge with their 24 h change (RID; C.13 2,500 m³/s matched Thai PBS/Amarin 2026-10-03/04), counts against yesterday from a 30 h history; "เช่น" only for a partial list. The ticker is a list of items with a topic symbol and a divider (a list when opened). GLM (only) rewrites every item in the voice of the ✨ card; each item is checked against its own fact (numbers, places, trend words and "เช่น" kept, no alarm or tone slip, a flow never a level); a failed item keeps the rule wording; accepted wording is cached by fact.
- **Evidence:** research/2026-10-04_ticker_models_run{1..4}*.log — GLM 6.8/11 items accepted with the first prompt → 9.3/11 with the ✨ voice; live run 11/11. Llama 3.3 (11/11) and SEA-LION (10.2/11) were tested on Workers AI; not used (owner: GLM only).

### D-093 — Up to 4 learned upstream gauges after 90 days of history (was 2 after 180)
- **Date:** 2026-10-04 · **Status:** accepted (Q47 "3–4 upstream gauges"; owner: "Continue to improve the model forecasting performance")
- **Evidence:** research/2026-10-04_upstream_k_s{1,2}.log, honest protocol (MODELS §5d): K4/90 d picked on sample 1, confirmed on sample 2 (148 gauges outside the focus area): served error vs "no change" at 12/24/48/72 h −14.8/−6.6/−7.5/−6.9 → −15.9/−9.1/−8.6/−8.0 %; gauges keeping ≥ 10 % 53/44/43/36 → 55/47/44/38; worse 13/11/12/15 → 13/12/13/14. Upstream gauges used: 114 → 176 in the sample.
- **Decision:** `upstream.K = 4`, `MIN_PAIRS = 90 days`; relearned daily; gauges whose inputs change are backtested again at once.

### D-092 — `star` reads the 7/30-day means and the 1/3/72 h changes (STAR_INPUTS 2)
- **Date:** 2026-10-04 · **Status:** accepted (owner: "Continue to improve the model forecasting performance … not fake the result and error or uncertainty")
- **Evidence:** honest protocol (MODELS §5d): V12 picked on sample 1, confirmed on disjoint sample 2 — served error vs "no change" at 24/48/72 h −6.6/−5.5/−5.3 → −8.3/−8.5/−9.4 %; gauges keeping ≥ 10 % 51/44/49 → 67/70/69; worse than "no change" 12/15/10 → 12/20/21 (stated cost). Stricter selection removed few failures and lost more gain; averaging methods +0.4–0.9 points only; time of day and recency weights did not help.
- **Decision:** added to `star_features`; cached backtests carry `star_inputs` and are redone when it changes; `star` needs ~90 days of history (30-day mean). Deployed 2026-10-04 16:49 UTC; the next run redid 944 backtests in 1,454 s.

### D-091 — A "? ไม่แน่ชัด" row leans by the measured trend; the numbers stay the model's
- **Date:** 2026-10-04 · **Status:** accepted (owner: "Why many stations say ? ไม่แน่ชัด, even we can see the trend from graphs. Could we think about average trend in long term" → chose "Lean the rows by the trend" over my recommended "measured trend + one forecast line"; window "24 h as now", and "move 24 ชม. ที่ผ่านมา … before 24 hr prediction")
- **Evidence:** research/2026-10-04_unsure_rows.py — on "?" rows with a real change, direction right: measured 24 h trend 70 / 71 / 72 %, 3-day trend 67 / 66 / 63 %, model median 69 / 61 / 57 % at 24 / 48 / 72 h; amount errors 30–50 cm either way. Daily lean record (strict sign, 30 days): 75.5 / 75.4 / 76.4 %.
- **Decision:** `status.lean` (forecast label "unsure" + measured label up/down, the trend groups' rule) on each 24/48/72 h row, `lean_rec` from `risk_record.lean`; UI dashed chip "↗ น่าจะขึ้น / ↘ น่าจะลดลง" + "N ใน 10" (≥ 30 cases); the numbers remain the model's 50 % range (= chart band); stories say it the same way. The measured line precedes the rows everywhere.
- **Trade-off stated to the owner:** the word can lean one way while the range (and a tide peak line) leans the other (HDA009: "↘ น่าจะลดลง", −5 to +15 cm); the ⓘ names both sources (Q51).
- **Amended the same day (owner, T.13 and BKK017: "I follow the dash trendline in chart … How we can calculate differently between description and chart?"):** BKK017 read "↘ น่าจะลดลง" beside "0 ถึง +8 ซม." and a rising line. A row now leans **only where the chart's dashed line (the model median) visibly moves ≥ 3 cm the same way** (`status.LEAN_MEDIAN_M`). Backtest (research/2026-10-04_lean_agreement.py): measured pace alone leaned 58–62 % of "?" rows, right 75–76 %; with the line ≥ 1 / 2 / 3 / 5 cm the same way: right 81.6 / 82.8 / 82.9 / 83.7 % at 24 h (80.3 % / 82.3 % at 48 / 72 h for 3 cm), leaning 19–22 % of "?" rows at 3 cm. The word, the line and the measured trend now always agree; live check C20. Q51 resolved.
- **Considered and declined the same day (owner: "Do nothing, current version is okay, we have to try to reduce the uncertainty of prediction instead"):** (a) words that read today's line (rising lines at "no change" gauges were right 45–61 %, 13–18 % against a measured fall — research/2026-10-04_line_words.py); (b) a line that continues the measured trend (τ 24 h) at "no change" gauges: error −4–5 %, direction 61–66 → 74–77 %, band holds 41–54 → 46–60 % (research/2026-10-04_line_candidates.py, _line_pace_detail.py). Kept for the uncertainty work (Q52).

### D-090 — Large-dam releases are not a forecast input (tested); rule curves noted for a future จับตา signal
- **Date:** 2026-10-04 · **Status:** accepted (owner: "consider การปล่อยน้ำเขื่อน more than เจ้าพระยา, to improve the forecasting models in the other regions")
- **Evidence:** research/2026-10-04_dam_release_backtest.md — 50 dams, 100 gauges in their HII sub-basins, release lagged 1 day as `star` input: error −0.5 / −0.9 / −0.9 % at 24 / 48 / 72 h, median 0, > 5 % better at 1–3 gauges.
- **Decision:** not adopted. Kept: the C.13 Chao Phraya Dam release (D-052). **Next:** a "dam above its upper rule curve" signal (same HII call), hourly or planned releases from RID/EGAT.

### D-089 — One national ticker in the top bar: rules gather the facts, AI retells them every 30 min after a check
- **Date:** 2026-10-04 · **Status:** accepted (owner: "concentrate the all information of Thailand got from the app into a single running scrolling text … periodically update, like every 30 minutes … let AI prepare it into simple, attractive and lovely Thai"; "Do not need to focus only สถานีในภาคกลาง, but provide only the overview of the nation")
- **Decision:** `situation.facts/rule_text/check/compose`, worker task `situation` (1800 s): the AI text is shown only with no new number, no new province (short forms mapped), no verdict word (incl. "ด่วน"), ≤ 300 characters; one retry; else the rule text. `/api/situation` {text, ai, at}. The top bar shows national counts (words; still the list's status filter) and the ticker; the rain line and the urgent line are folded into it. Amends D-068 (the ticker is the one scheduled AI text; per-place AI stays on request) and D-086.

### D-088 — docs/MODELS.md is the model and calculation reference (Thai summary + English detail)
- **Date:** 2026-10-04 · **Status:** accepted (owner: "We would like to understand how we can calculate … like Architecture Decision Report … What kind of data do we need more")
- **Decision:** one document: concept, data flow, QC, status, ladder with parameters and formulas, which models win, hard cases, derived signals, decisions record, limits, ranked data wish-list. Updated with every model change.

### D-087 — Google Flood Hub: collected and validated before anything is shown
- **Date:** 2026-10-04 · **Status:** accepted (owner: "Validate first, then a 3–7 day outlook")
- **Evidence:** 103 HYBAS virtual gauges in Thailand, all quality-verified; snapshot 08:24 UTC: 3 SEVERE (2 with our over-bank gauges within 15 km, 1 without any gauge of ours), 2 ABOVE_NORMAL (near bank / watch), NO_FLOODING at 7 places with our gauges over the bank; 31 points beyond 15 km of any gauge of ours; daily discharge 9 days ahead; thresholds per point.
- **Decision:** collector `google_floodhub` (worker, 6 h): `gfh_gauge`, `gfh_status` (history kept), `gfh_forecast`; key only in the `X-Goog-Api-Key` header, worker only. Revisit after 1–2 weeks of history (Q49): a "Google คาด 3–9 วัน" line where it agrees with our gauges.

### D-086 — The top bar folds; rows 24 / 48 / 72 h (no 12 h)
- **Date:** 2026-10-04 · **Status:** accepted (owner: collapsible top bar on all screens; "remove trend 12 hr … think about longer term like 24, 48, 72 hr")
- **Decision:** the fold keeps national counts and the ticker visible; details and freshness inside. Forecast rows 24/48/72 h in sheets and pins, 24 h in list cards; `change72` with the 48 h rules (direction only where proven; 72 h: star wins at 372 gauges, medium confidence 70). `change12` stays in the API for compatibility.

### D-085 — One map layer box: the legend lines are switches
- **Date:** 2026-10-04 · **Status:** accepted (owner: "Let the all stations can be show and hide in the list box. Try to simplify the categories" → "One box: legend with checkboxes")
- **Decision:** five statuses, "ยังไม่มีพยากรณ์" rings, DWR posts and Traffy as checkboxes with counts in one box (bottom right), remembered in the browser, folded on phones; the top-left box and the "ไม่มีพิกัด" line removed; hidden categories never change counts elsewhere.

### D-084 — GISTDA satellite cells removed from every display; collector stopped (supersedes D-071, D-078)
- **Date:** 2026-10-04 · **Status:** accepted (owner: "The satellite cell-info for flood showed in App is not so correct, and might mislead, please consider to remove from display" → "Hide everywhere and stop the collector"; "we will find the new info from this later to replace GISTDA")
- **Decision:** pin line, AI sentence, sheet line, map toggle, `/api/satellite`, จับตา group, `sat_summary` and the `gistda_flood` collector removed; `sat_flood` kept empty for a future source, which gets its own validation first.

### D-083 — One trend rule for the whole app: "น้ำยังขึ้น" / "ทรงตัวหรือลดลง"
- **Date:** 2026-10-04 · **Status:** accepted (owner: "Forecast if sure direction: higher, lower, stable. ไม่แน่ชัด can suggest with measured recent change as fallback … show two labels as summary"; names "น้ำยังขึ้น / ทรงตัวหรือลดลง"; status in two dimensions: level × trend)
- **Decision:** `status.trend` on every station row (computed once in the API, read by every view): the 24 h row when sure (proven ↗/↘, or "→ ทรงตัว" within ±5 cm), else the measured recent pace (the `recent` rule; ≥ +2 cm per 24 h = up); None when stale. Two labels "วัดได้ ↗ · คาด ?". Used by จับตา (over-bank split, coloured pills and province chips), river cards (level + trend counts, rivers and ลำน้ำอื่น alike), the ticker and the summary details. The measured line says "6 ชม. ล่าสุด: …" when the last 6 h differ from the 24 h word (C18).

### D-082 — Tributaries join their river by HII sub-basin; the river tab lists every gauge of a picked province
- **Date:** 2026-10-03 · **Status:** accepted (owner: "You can show in river tab, even this province has only one station … is it the expectation from visitors?" → chose a "ลำน้ำอื่น" section; then "The canals which are under the same basin of river, they should be located in the same as that river … คลองนางน้อย is under basin แม่น้ำตรัง")
- **Evidence (2026-10-03):** 13 provinces showed nothing in the river tab; 426 of 840 non-BMA gauges were in no view. HII's `waterlevel_load` gives every gauge a `station.sub_basin_id` (237 sub-basins, 808 gauges, none missing); sub-basin 349 holds the 8 แม่น้ำตรัง gauges, TNG003 คลองนางน้อย and TNG005 คลองยวนปลา. `river_main` (HII's river map) only names gauges on a main river's line, so it cannot place tributaries.
- **Decision:** `station.sub_basin` stored from the feed; `rivers.tributaries`: a gauge without a view of its own (not BMA) joins the view with the most gauges in its sub-basin (7 sub-basins hold two views: the larger wins). `/api/rivers` `tributaries`, `/api/profile` `tributaries`; the river view lists them after the chain as "ลำน้ำสาขาในลุ่ม…" with their waterway name (no confluence data → never slotted into the upstream order); cards count them ("รวมลำน้ำสาขา N"); river tags follow. Gauges still outside every view are listed under "ลำน้ำอื่นใน<จังหวัด>" (grouped by waterway, no province bar) when a province is picked. Thin provinces (≤ 2 gauges) say so in the shared where-row. 170 of 426 gauges placed by sub-basin.

### D-081 — DWR early-warning posts: archive, then a trend-only layer, kept apart from the gauges
- **Date:** 2026-10-03 · **Status:** accepted (owner: "Many province has only one or few water level stations, do we miss some info … validate and test the data quality and history before integrate" → "Get history, if possible, then archive first, and show as trend-only layer"; declined a Telerid request to RID)
- **Evidence:** HII's feed is fully ingested (808/808). DWR EWS `LoadStation` via the Thai egress: 455 level posts, 362 fresh; level = depth on a local post (0–9 m), not m MSL; 336 of 439 `alert_max` = 4.00 m (a default); DWR's `status` disagrees with level vs alarm, and status "9" posts still move (STN2201: 81 cm in 11 h). History: `graph/wl_graph.php` gives only ~11 h (15-min), ~23 s per post. Sample of 30: 25 with data, 3 flat, 9 moved ≥ 5 cm. RID Telerid: readings need a login (HTTP 401). HII's BMA canal feed: frozen since 2026-09-28.
- **Decision:** collector `dwr_ews` every 30 min in the forecaster container (one 45 s call), raw archived; `dwr_station`/`dwr_obs` apart from `station` (never in statuses, forecasts, river views, จับตา, pins; never compared with HII/RID/BMA levels, KI-217); 400-day retention. `/api/dwr`: posts with a reading < 24 h, each with the measured 24 h change (`qc.observed24`), "stuck" (one value ≥ 90 % of ≥ 24 readings) or "collecting". Map: grey squares from zoom 9 (circles are gauges), popup with the change only and an ⓘ on why.
- **Revisit:** after 2–4 weeks of archive (Q46): gaps, stuck rate, rain response; whether DWR posts help as upstream inputs (needs ~30 days).

### D-080 — One forecaster: the rows and the chart come from the same model; the trend is the model method "recent" (supersedes D-060's override)
- **Date:** 2026-10-03 · **Status:** accepted (owner: "Are the forecasting in text and in graph agree with each other, I found the difference" → "Why trend and model forecast in the chart are different? … I thought the trend were calculated by the model. Please validate and find the problems, solve all")
- **Evidence:** Kgt.19A rows "+48/+75/+91 ซม." came from the API's measured-trend override (D-060: a 24 h straight line through a 70 cm jump that had levelled off), the chart from the model (persistence, flat), far outside its own 90 % band; 535 of 927 rows were override rows, 171 said ≥ 10 cm while the chart drew the model. Backtest on the archived runs 26 Sep – 3 Oct (~6,000 cases per horizon, research/2026-10-03_verify_text_graph.py): the old override 12.6 / 19.5 / 32.8 cm mean error at 12 / 24 / 48 h, the served model 12.5 / 18.5 / 31.5, "the smaller of the 24 h and last-6 h pace, none when they disagree" 10.4 / 16.3 / 29.2 (direction right 85–87 %). Picked from 5 variants on one week ⚠️.
- **Decision:** `follow_measured`/`reconcile_rows` removed; the rows are `change_summary` of the model's stored quantiles, which the chart draws (hidden markers at 12/24/48 h for check C15). The rule became `forecast.recent_rate`, method `recent` (แนวโน้มล่าสุด) in the ladder: it competes per gauge and horizon in the 45-day rolling backtest with the 10 % skill gate, bands from its own errors; cached backtests without it are redone (`model_is_fresh`). The measured 24 h line stays as a fact ("24 ชม. ที่ผ่านมา: …").
- **Trade-off stated to the owner:** where "recent" does not win the backtest, a gauge whose chart falls slowly may read "ทรงตัว"/"? ไม่แน่ชัด" again (the D-060 complaint); the measured line under it says what happened. One forecaster per chart is the rule.

### D-079 — The map shows every gauge with data in the last 24 h; a ring marks "no forecast" (supersedes D-037)
- **Date:** 2026-10-03 · **Status:** accepted (owner: "Do we still need 'แสดงสถานีที่ยังคาดการณ์ไม่ได้ (118)' in the map, should we integrate in the map … suggest frankly" → "Hollow ring, no checkbox"; list chip: "Remove it")
- **Evidence:** the switch hid 117 gauges: 3 critical + 3 warning, 65 in Bangkok (63 BMA), 36 fresh without a forecast, 31 silent > 24 h. Hiding a red gauge breaks D-024.
- **Decision:** draw every gauge whose latest reading is < 24 h old, in its status colour; no tested forecast (`trend12` not rising/falling/steady) → white-filled ring in the status colour; legend "ยังไม่มีพยากรณ์" and "ไม่แสดง N สถานีที่ไม่ส่งข้อมูลเกิน 24 ชม."; the top-left control holds the 🛰 and DWR toggles. The list's "📈 เฉพาะที่คาดการณ์ได้" chip is removed. Live check C16.

### D-078 — Satellite in the station sheet, on the map (toggle) and per province
> **Superseded 2026-10-04 by D-084:** removed (cells could mislead; owner).
- **Date:** 2026-10-03 · **Status:** accepted (owner: "We have now the satellite data. Can we apply the info from satellite?" → sheet line + map layer; layer "Toggle, off by default")
- **Evidence:** GISTDA cells (images 28 Sep – 2 Oct) vs gauges: ≥ 100 rai flooded within 5 km for 38 % of over-bank, 35 % warning, 26 % watch, 8 % normal gauges outside กทม./ปริมณฑล; no cell in Bangkok. Gauges at "watch" inside ~14,000 rai (Yom at Sukhothai, Nan at Nakhon Sawan) and gauges without a bank (PRC001, ATG021) sit in flooded areas.
- **Decision:** at each download `sat_summary` = rai within 5 km per gauge (only ≥ 100) and per province; sheet line "🛰 ดาวเทียมเห็นน้ำท่วมรอบสถานี (5 กม.) ราว N ไร่ ⓘ" (dates and limits in the ⓘ; seen only, D-071); map toggle drawing `/api/satellite` squares (0.02° / 0.005° / 0.002° by zoom, coarsened to ≤ 5,000), off by default, on from the จับตา group; จับตา group per province. A download replaces our copy only when complete (KI-269).

### D-077 — The "⚠️ จับตา" tab: six risk groups with measured track records
- **Date:** 2026-10-03 · **Status:** accepted (owner: "I need another tab to have the list of potential risks according to the water level in next 24 or 48 hr … link to the stations or areas … confidence like percent or some narrative"; Grillme: name "จับตา" (เฝ้าระวัง = the yellow status, เตือนภัย = official), track record kept as counts ("6 ใน 10", owner asked percent vs counts: counts), nationwide overview with the where-row starting ทั่วประเทศ, groups by risk, threshold ≥ 1 in 10, groups: + น้ำเหนือ, ดาวเทียม, ฝนหนัก; not "น้ำกำลังลด")
- **Evidence (archived runs, research/2026-10-03_verify_*.py):** bank reached within 24 h, gauges below bank at issue: band <5 % → 0.4 % (4,803 runs), 5–25 % → 3.5 % (345), 25–50 % → 11.7 % (128), >50 % → 61.4 % (132); the top two bands catch 77 % of real bank-reaches. Upstream ≥ 30 cm/24 h → gauge +10 cm within lag + 6 h: 69 % (24 % without). 24 h forecast ≥ +20 cm → +10 cm observed: 72 %.
- **Decision:** `risks.build` (pure) from the list's station rows: over_bank (critical, per province) → may_reach (`bank_chance24/48` in ">50%", "25-50%") → upstream (watch/warning gauge, learned upstream lag 3–48 h, fresh, `observed24.change_cm` ≥ 30) → fast_rise (`change24.level` strong_rise); a gauge once, stale ones counted not listed; rain (≥ 35.1 mm/24 h per province, the provinces of the gauges each point serves) and satellite (rai per province). `risk_record` daily in the forecaster (30 days, DB-side path reduction, hourly readings): chips "N ใน 10" only with n ≥ 30; rain record not built yet (too little `rain_obs` history). `/api/risks` (5 min). UI: own where-row starting ทั่วประเทศ, header "24–48 ชม. ข้างหน้า · อัปเดต … ⓘ" (not an official warning), first 5 rows + "+ อีก N", station rows two lines (name; one detail line), links to sheets / province list / satellite map. Live check C17.
- **Caveat:** records rest on one week and one flood (archive since 2026-09-26) and refresh daily.

### D-076 — One "where" row (ภาค · จังหวัด) shared by the list and the river tab; river row below
- **Date:** 2026-10-03 · **Status:** accepted (owner asked whether ภาค + จังหวัด + แม่น้ำ as dropdowns is good or bad and how to arrange them; chose my "Shared where-row + river row")
- **My assessment recorded:** good — cascading ภาค → จังหวัด is the familiar Thai form pattern, a province narrows 62 rivers to 1–5, and defaults (region from the list, ทุกจังหวัด, ทุกสาย) mean no pick is required; bad only on one line (three pickers ≈ 110 px each at 390 px, river names cut), hence two rows.
- **Decision:** `whereRow()` (`.pick-region`, `.pick-prov`, counts in the options) in both tabs, one state (`region`, `prov`, both remembered; a region change clears the province); `inRegion` = region ∧ province, so counts, list, map fit and river lists follow; the list's region chips are gone (the "เฉพาะที่คาดการณ์ได้" toggle stays). River tab: the overview filters rivers to the province and counts its gauges; a river view stays whole (upstream water is the point), province gauges marked (`.here`) and scrolled to; a river tag from another place resets the province.

### D-075 — Usual region names; "กทม. และปริมณฑล" includes Bangkok; "ทุกสาย" river overview
- **Date:** 2026-10-03 · **Status:** accepted (owner: "Users might expect กทม , กทมและปริมณฑล ภาคกลาง and other usual regions …", "Can user select all rivers under river filter?", "You can suggest, and validate the suggestions and UX")
- **Decision:** labels กทม. / กทม. และปริมณฑล / ภาคกลาง / ภาคเหนือ / ภาคอีสาน / ภาคตะวันออก / ภาคตะวันตก / ภาคใต้ / ทั่วประเทศ; keys unchanged (bkk, metro, up, …). "metro" includes Bangkok everywhere (`regions.chips_of`; JS `REGION_TEST`): chips, counts, map fit, rain-by-region, river regions. "ภาคกลาง" = NRCT 1977 central minus the Bangkok area (which has its own two chips). River picker gains "ทุกสาย (N)" as the default: per river, over/near-bank counts and 24 h rising/falling counts from the list's station data with `directional()` (D-060), sorted by stress.
- **Validated:** chips at 390 px wrap to 4 rows (was 3) — the cost of clearer names; option offered to the owner: a one-line "ภาค ▾" picker for the list too.

### D-074 — River views for every natural waterway with ≥ 3 gauges; pickers, upstream on top, river tags (amends D-072)
- **Date:** 2026-10-03 · **Status:** accepted (owner's four points, all agreed by me except "tag instead" → tag *and* view; owner: "Yes all four, but one line : Province & river", "Upstream at the top")
- **Evidence (2026-10-03):** 826 non-BMA gauges with coordinates; waterways with ≥ 8 gauges held 240 (29 %); ≥ 3 gauges on natural waterways: 49 named rivers (367 gauges, 30 with an HII line) plus natural "คลอง" outside กทม./ปริมณฑล. 218 waterways have a single gauge (no chain to show).
- **Decision:** `rivers.MIN_GAUGES = 3`; `rivers.has_view`: natural waterway names (point.water_body), or a "คลอง" whose gauges are mostly outside กทม./ปริมณฑล; no HII line → order by bank height (`up`), no km. UI: two native pickers on one line (province filters rivers; province gauges marked), upstream first, no km text, river tag on list rows and sheets that opens the river at that gauge. The region chip still picks the default river when no province is chosen.
- **Amended v0.20.2 (owner: "Change filter from จังหวัด to ภาค?", "no long description" → chose "ภาค synced + ⓘ"):** the picker is the app's one region (`setRegion`, shared with the list chips, summary and map); `/api/rivers` gives each river's `regions`; the explanation is one ⓘ. I recommended this over province: the list already works by ภาค, so the river tab opens on the user's region with no extra tap, and a region holds 5–17 rivers (a province picker meant 65 options and choosing again); the station tag still lands on the exact gauge.
- **My view recorded:** a tag alone would lose the only place the flood wave along a river is visible (2026-10-03: rising Chai Nat → Ayutthaya, falling at Nakhon Sawan), so the tag leads into the view rather than replacing it.

### D-073 — The name stays "BKK FloodWatch"; every description says nationwide
- **Date:** 2026-10-03 · **Status:** accepted (owner: "Think about rebrand from BKK flood watch to nationwide, please suggest and validate" → I recommended ริมตลิ่ง · Rim Taling; owner: "But it sounds not international?" → "Keep old name, and adapt the description everywhere for nationwide, please suggest and validate")
- **Validated names (2026-10-03, web search):** taken or confusable — เช็คน้ำ (GISTDA's app), checknam.com, Water Watch (CIPAT), ThaiWater (HII, official), Tuammai/ท่วมไหม, NamWatch (a Bangkok volunteer flood map with HII + Traffy), "Flood Watch Thailand" (GitHub project), "Taling" (Korean learning startup); free — ริมตลิ่ง. Freeboard: a technical term and a dashboard tool.
- **Decision:** keep the name (recognition, links, the honest User-Agent agencies will see). One wording everywhere: title "BKK FloodWatch — ระดับน้ำคลองและแม่น้ำทั่วไทย" (45 chars); meta description 153 chars; English "Water levels of canals and rivers across Thailand: 1,000+ gauges (HII, RID, EGAT, BMA) compared with the bank, with backtested 12–48 hour forecasts. Started in Bangkok during the 2026 flood." Counts in static text are rounded ("กว่า 1,000"), never exact.

### D-072 — "แม่น้ำ" tab: every river with ≥ 8 gauges, ordered by river km, with the 24 h forecast row
- **Date:** 2026-10-03 · **Status:** accepted (owner chose "แม่น้ำ tab + forecast")
- **Decision:** river chips (Chao Phraya first, then by gauges; the region chip picks the default for north/northeast/east/west/south); rows from the downstream end up; each fresh gauge with a forecast gets the list's "อีก 24 ชม." row (`trendRows`, D-060); stale or unknown gauges say "ไม่อัปเดต" (D-024); BMA gauges stay in the list and map, never in an HII/RID chain (KI-217). River km by `rivers.chainage` (weekly with the river map, `collector_state.river_km`), ±10 km, never used to interpolate water between gauges (D-019).

### D-071 — Satellite flooding near a pin: "seen" only, from GISTDA, in the pin panel (Q45)
> **Superseded 2026-10-04 by D-084:** GISTDA cells removed from every display; collector stopped.
- **Date:** 2026-10-03 · **Status:** accepted (owner: "Q45 : yes")
- **Decision:** a factor line "ดาวเทียมเห็นน้ำท่วม<บริเวณจุดนี้|ห่างราว N ม.>" with the flooded area within 1 km (rai) and the image dates, when GISTDA's 7-day layer has flooded cells within 1 km of the pin (images ≤ 10 days old). Nothing when none: never "not flooded" (radar is blind among buildings; research/2026-10-02_satellite_flood.md). Does not change the headline or status (gauges judge channels; this is water on the ground, like street reports). Told in the AI story and its lines too.
- **Rulings (Claude):** GISTDA only (Thai, more satellites; GFM stays research); 1 km radius (as street reports); the 7-day layer's composite image dates (cells carry no own date; the 1/3-day layers were empty on 2026-10-03); a bulk download (no user location is sent to GISTDA), kept as centre + area + place in `sat_flood`; runs in the forecaster container (~7 min per download). *Amended v0.20.5 (KI-268):* not "every 20 h" but when an hourly probe shows a new, finished layer (or our copy is > 36 h old).

### D-070 — Polder rules only in กทม. + ปริมณฑล; the top strip shows rain only when heavy (amends D-059, D-064)
- **Date:** 2026-10-02 · **Status:** accepted (owner: "The point is next to station บางปะหัน LBI001, but showed no near station!!"; "Review the topbar of UI, it used too much space again!! and it showed specifically for Bangkok, for what?" → chose "Only when heavy")
- **Decision:** (1) A pin uses the Bangkok polder rules (a river gauge never judges the canals) only when its nearest gauge is in กทม. or ปริมณฑล (`point.POLDER_REGIONS`); upstream focus provinces (Ayutthaya to Nakhon Sawan) are judged like the rest of the country: the nearest river or stream gauge is the local evidence (KI-263). (2) The summary strip shows no rain unless the chosen region expects or measured heavy rain (TMD ≥ 35.1 mm), then one line (KI-265).
