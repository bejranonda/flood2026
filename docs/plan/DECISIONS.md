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
