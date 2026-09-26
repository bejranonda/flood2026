# Changelog

All notable changes to BKK FloodWatch 2026. Versions follow `floodwatch.__version__`, which the UI shows (D-025).

## v0.3.0 — 2026-09-26
Bangkok release: from 10 to 209 Bangkok gauges, and a way to find your soi. Audience: Bangkok residents (owner, Q27).

### Data
- **BMA khlong gauges (199)** via the People's Party relay of BMA's KlongMap, every 10 min, raw payload archived (D-031). Bank = lower bank; BMA `warning`/`critical` not used (KI-215); never compared with HII levels (KI-217); relay risk KI-218. History starts 2026-09-26 16:30 UTC.

### Web and API
- **Place search** `/api/geocode` (OSM Nominatim, Bangkok region, ≤ 1 req/s, queries never logged; ซ./ถ./พหล expanded, "name + number" also tried as ซอย) → opens the point check (D-032). No AI needed.
- **Region chips** (ทั้งหมด / กทม. / ปริมณฑล / เหนือ กทม.), **Bangkok by default this week** (D-033), remembered per device; a search looks everywhere.
- BMA gauges credited on the card and the detail sheet; unit "ม. (หมุด กทม.)".
- The footer's sources and methods collapse behind a tap.
- Link to BMA's "roads to avoid" page in the point card.
- `app.js?v=10`, `style.css?v=7`.

### Fixes
- "ต่ำกว่าตลิ่ง 0 ซม." under an overflow badge → "ระดับเท่าตลิ่ง" (KI-216).

### Research
- BMA KlongMap and road pages unreachable from this host; the BMA road artifact is a static snapshot; its sensor host is a private VPN portal (SOURCES §2c, APPROACH §3.7).

## v0.2.1 — 2026-09-26
Patch release: an owner tracker, a safer alias, and a worker fix. **Live at https://flood.autobahn.bot** (alias https://flood.bejranonda.com).

### Owner tracker (D-026)
- New [docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md): everything needed from the owner, with why, exact steps, cost and how it is verified.
  - R2 is not enabled, and the measured archive growth is ~100 MB/day, so the free tier lasts about two months.
  - The bot-challenge fix is corrected: Bot Fight Mode can't be skipped by WAF rules.
- New `scripts/owner_status.py`: a read-only status check that never prints a secret. It checks the challenge with curl, the Cloudflare API, `.env` keys and one tiny AI call.
- The OPEN_QUESTIONS list is cleaned up (answered items moved).

### Web and API
- **The alias page declares itself canonical** (D-027). Before, `flood.bejranonda.com` told crawlers to use the challenged main domain.
- A tested **`REDIRECT_LEGACY_HOST=1`** switch (301 to the main domain, `/api/health` excluded) is off until the bot challenge is relaxed.
- Version 0.2.1 in the header badge, the footer, `/api/health` and `/api/stats`.

### Fixes
- The worker runs a backfill batch at startup. Frequent deploys had stalled the backfill at 34 of 79 stations (KI-212). **After the fix it completed: 79 of 79.**
- **Traffy outage handling (KI-213):** Traffy answered HTTP 502 for ~2.5 h and each failing run held the single worker loop for over 2 minutes. Traffy now makes one attempt per run, and repeatedly failing tasks back off (×2, ×4, ×6; core HII tasks capped at ×2).
- **Result of the full-year history:** 57 of 107 stations now serve a tide-based forecast (44 of 95 before).

### Public repository (D-028)
- The owner made the repository **public**. A full-history scan found no credentials, data or personal email (KI-214). The server IP was removed from the current docs (it remains in 8 old commits; low risk behind the tunnel).
- Docs corrected: SSH is key-only for root, but password authentication is still enabled globally (KI-214). No LICENSE yet (Q10, all rights reserved).
- KI-506 and KI-504 corrected and updated (the tunnel rights are fixed, the old tunnel is deleted, R2 is not enabled).

### Known limits
- Q18 (bot challenge), R2 (Q15b/Q16), the RID gate coordinates, and the license are open on the owner side. See OWNER_ACTIONS.
- **Tests:** 33 passing.

## v0.2.0 — 2026-09-26
**Live at https://flood.autobahn.bot** (alias https://flood.bejranonda.com).

### Citizen-facing
- **Mobile-first UI:**
  - tabs (list / map / Chao Phraya), bottom-sheet station detail, search by district or khlong;
  - share and deep links (`#s=CODE`, `#p=lat,lon`);
  - freeboard in cm first, a map legend, the version badge.
- **Compact statistics strip:** status counts (tap to filter), rising/falling counts, Bangkok 24 h rain, and reporting freshness for the focus area and the whole HII network.
- **24 h outlook:** peak time window (only when a tide model is served) and the chance of reaching the bank as a category.
- **Point check** for places without a gauge: gauges around the pin as an area category (never a level), citizen reports within ~1 km, rain, always-on warnings. No verdict at very low confidence (D-021).
- **Citizen feedback:** verdict, depth band, note and opt-in location. Private; rate-limited; instant hotline box for urgent notes (D-020).
- **Chao Phraya profile** ordered by river km from the mouth (HII centreline).
- **Charts:** day markers, no lines across data gaps.
- **Every station is shown** (111 in focus, 96 placed: 82 from HII, 14 approximate from OSM; 15 unplaced and listed). Misleading values are hidden, always with a note, and there's a whole-country toggle (D-024).

### Data and models
- **Coverage:** the whole Bangkok Metropolitan Region (Samut Sakhon and Nakhon Pathom added). BKK008 placed from HII's map feed (D-023).
- **History:** a one-year hourly backfill from `waterlevel_graph`, batched with `COPY` (D-018). Tides are fitted on up to a year; the backtest covers the last 45 days. C.12 moved from persistence to the tide model.
- **QC:**
  - level > bank + 3 m is flagged (BKK003 stuck at 7.45 m; KI-211);
  - GLF002 values are not MSL (KI-210);
  - `TEST*` gauges are excluded;
  - readings older than 24 h show status "unknown".
- **Optional Cloudflare Workers AI** (SEA-LION v4) triages feedback notes in the worker only, with a budget and a circuit breaker. The site never depends on it (D-022).

### Operations
- **Domain:** main domain flood.autobahn.bot, served by the new tunnel (D-017).
- **Worker robustness:** a total per-request deadline (after a 15-minute hang), known-failing endpoints retried once a day, and the backfill no longer blocks the collectors.
- **Tests:** 29 passing.

### Known limits
- **Domain:** the `autobahn.bot` bot challenge blocks non-browser clients (KI-506).
- **Backups:** no off-site backup yet (KI-504).
- **Near me:** not polder-aware.
- **Unplaced stations:** 15 gauges still without a position (KI-207).

## v0.1.0 — 2026-09-26
The first live MVP:
- collectors (HII, Open-Meteo, Traffy), raw archive, Postgres;
- baseline forecasts (persistence / tide / trend) with conformal bands;
- FastAPI and the Thai map/list;
- Cloudflare Tunnel, and a Thai VPN egress sidecar.
