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
  - The web app never calls AI.
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
- **Context:** BMA stations (`WL.*` series, e.g. `WL.KTY.01`, `WL.AJP.01`, `WL.BKY.02`, `WL.KLA.01`, `WL.LPW.01`) are geo-blocked from non-Thai datacenters. A probe using our project's Thai residential VPN egress the VPN Gate relay in Ayutthaya) verified that BMA's perimeter subnet (BMA server subnet) drops all incoming TCP SYN packets on ports 80/443 (tinyproxy 500), while other Thai agencies (`ews.dwr.go.th`, `hydro.navy.mi.th`) connect normally (HTTP 200). Furthermore, BMA's own dashboard does not host multi-week historical time series.
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
  3. **Canal factor compacted:** one gauge line (name, distance, status pill), its rows and one "when it drops" line; a relay-only nearest canal gets a single line and "คาดการณ์จากคลองใกล้เคียง:" introduces the gauge that carries the trend; the why/where details sit behind "รายละเอียด".
  4. **Sheet order:** status → BMA margin line → freshness (+ source/datum in ⓘ) → trend block (rows, when it drops, peak, chance of reaching the bank) → street note → chart → notes → method → feedback; no emojis in the sheet text.
  5. **Say what is measured:** bank-based watch/warning with the bank still > 30 cm away read "น้ำเต็มลำน้ำ N %" (share of channel depth), not "ใกล้ตลิ่ง".
  6. Kicker "คาดการณ์ข้างหน้า" (rows carry their own horizons); user depth reports counted as "N ราย".
