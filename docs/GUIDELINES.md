# GUIDELINES.md — Engineering, Modelling, Data Ethics & UX Standards

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-26
> **Audience:** maintainers, contributors, AI agents (agents: also read [CLAUDE.md](../CLAUDE.md))

---

## 1. Core principles

1. **Hybrid forecasting.** Forecast = physically structured baseline + ML residual correction + calibrated uncertainty. Pure black-box ML extrapolates dangerously in record floods. Full 2-D hydrodynamics is too heavy for a 10-minute cycle ([APPROACH](APPROACH_AND_METHODS.md)).
2. **Beat the baselines or don't publish.** Every station × horizon must beat persistence (L0), or persistence + tide (L1) in tidal reaches, in walk-forward backtests (§4.3). Otherwise the app falls back to the baseline with wider intervals.
3. **Our archive is the system of record.** External sources are feeds and may disappear, change or throttle at any time. Every payload is archived raw before it is parsed ([ARCHITECTURE §3](ARCHITECTURE.md)).
4. **Keyless first, collected on the server** (D-001). v1 needs no gated API keys. "Zero-key" does **not** mean computing in the browser. **The browser only calls our API or edge**, never a government endpoint, even where CORS would allow it ([KI-105](KNOWN_ISSUES.md)). Code in the browser is for display only.
5. **Transparency on every screen.** Last observation time (Asia/Bangkok), data age, source attribution, forecast conditions, disclaimer, official links and hotlines.
6. **Space and time are first-class.** Every value carries **where** (station or geometry, datum, CRS) and **when** (observation time, issue time, valid time, all in UTC) ([APPROACH §2](APPROACH_AND_METHODS.md)).

---

## 2. Working process

### 2.1 Strict phase gates (D-002)
- Work phase by phase ([plan/PLAN.md](plan/PLAN.md)). At the end of each phase, deliver its report or result and **stop until the owner approves the gate** (G0–G4).
- **Exception built into the plan:** once G0 approves the sources, start the collectors and backfill immediately. Every flood day we don't capture is lost for good.

### 2.2 Evidence rule (D-003)
- Every number, endpoint, constant or station attribute in `docs/` carries **evidence**: a live call (with date and host), observed data, or a cited source. Otherwise it is marked **⚠️** and gets a Phase 0 or Phase 2 task.
- **Never invent** endpoints, field names, constants or data. When something fails, say so and propose alternatives.
- **Check owner statements too.** When the owner reports a state ("token has R2 permission", "stations are missing"), verify it with a call and report any discrepancy politely, with the evidence (the 2026-09-26 HANDOFF has an example table).
- **Sample outputs must be produced by running the code** in the same change. Never write expected-looking numbers by hand.
- AI-assisted research (claude.ai, Gemini, and so on) is welcome as **input**. It is validated claim by claim before use ([research/README.md](../research/README.md)).
- Silent fallbacks to made-up values (e.g. "default Bang Sai flow 2,450 m³/s") are forbidden. Missing data is shown as missing.

### 2.3 Documentation upkeep
| When you learn… | Update |
|---|---|
| A domain fact (hydrology, stations, datums) | [KNOWLEDGE.md](KNOWLEDGE.md) |
| A limitation, failure mode or workaround | [KNOWN_ISSUES.md](KNOWN_ISSUES.md) (new KI-ID and status) |
| A source was tested, changed or failed | [SOURCES.md](SOURCES.md) |
| A method or model changed | [APPROACH_AND_METHODS.md](APPROACH_AND_METHODS.md) |
| An architectural or product decision | [plan/DECISIONS.md](plan/DECISIONS.md) (new D-ID) |
| Something you need from the owner (a key, a dashboard change, a decision) | [OWNER_ACTIONS.md](OWNER_ACTIONS.md) first, then [plan/OPEN_QUESTIONS.md](plan/OPEN_QUESTIONS.md) for the history |
| Task progress | The relevant `plan/phase-*.md` checklist |

Update `Last updated` on each file you touch. Docs are written in English; Thai is used for UI strings and domain terms.

### 2.4 Owner dependencies (D-026)
- **Track them in [OWNER_ACTIONS.md](OWNER_ACTIONS.md) first** (why, exact steps, cost, how you'll verify), then mention them briefly in chat. Run `python3 scripts/owner_status.py` before asking.
- **Secrets only in `.env` on the server.** Ask the owner for the key *name* to be set; check the value works without printing it.
- **Check reachability with the client that matters** (curl for crawlers and monitors, a real browser for people). A single Python check once gave a false "fixed" (KI-506).
- **Interval timers need a startup run.** Anything on an interval must also run once at start, or frequent deploys starve it (KI-212).

---

## 3. Architecture and ingestion hygiene
- **Immutability first:** store every payload gzip-compressed with its SHA-256, fetch time, URL and HTTP status **before** parsing.
- **Circuit breaker:** retry with exponential backoff (1, 2, 4, 8 s, with a cap). Never crash the scheduler. After repeated failures, go to **degraded mode**: serve the last verified reading, its age, and a notice such as *"ข้อมูลล่าสุดเมื่อ 14:15 น. (แหล่งข้อมูลขัดข้องชั่วคราว)"*.
- **Single-flight:** at most one outgoing request per source per cycle. Nothing is fetched upstream on the user's request path.
- **QC flags, not deletion:** sentinel values (HII `999999`), range, rate of change, flatline, clock error, and neighbour consistency ([KI-206](KNOWN_ISSUES.md)).
- **Version metadata:** station bank level, datum, location and rating changes are versioned with effective dates, never overwritten.

---

## 4. Modelling and scientific rigour

### 4.1 No leakage
- Train on **as-issued** forecasts (the archived NWP runs), never on observed future rain. Until enough runs are archived, widen the intervals and disclose it ([KI-305](KNOWN_ISSUES.md)).
- Only time-ordered validation: **rolling-origin walk-forward** with an **embargo gap** of at least the forecast horizon between training and test, because autocorrelation leaks information. Never shuffle or use random K-fold.
- Spatial generalisation is tested with **leave-station-out** and, for polders, leave-zone-out splits.

### 4.2 Held-out events
2011 (mega-flood, overland flow), 2017, 2021 (release + high tide), 2022 (pluvial cloudbursts, tunnel drawdown), 2024, and the **2026 event** as live validation. Use this same list everywhere.

### 4.3 Acceptance gate (per station × horizon)
- **Skill vs persistence** = 1 − RMSE_model / RMSE_persistence **> 0.10**, **and**
- **90 % interval coverage between 85 % and 95 %** on held-out events and on the rolling 14-day window.
- **Reported, not gating:** NSE, KGE, CRPS, peak magnitude and timing error, and POD/FAR/CSI for bank and warning exceedance.
- **Unit tests, not gating:** mass-balance closure < 3 % for the storage model; monotonic constraints hold.
- If coverage drops below 85 %: widen automatically (ACI) and alert.

### 4.4 Uncertainty is mandatory
Always give quantiles or intervals, and let them widen with the horizon. Beyond about 3 days, show **probabilities or categories**, not precise levels.

---

## 5. Data-source etiquette and legal (D-004)
- **Owner decision D-014 (2026-09-26):** don't wait for agency replies. For geo-blocked **public** data, a Thai egress the owner controls (SSH SOCKS or a paid VPN) is allowed. Free public proxies and bot-challenge solving are not.
- **Thai egress limits (D-016):** the OpenVPN proxy (`THAI_EGRESS_PROXY`) is opt-in per request and only for **public pages** of sources that geo-block. **Never send credentials, tokens or personal data through it.** Always verify HTTPS certificates. Don't rotate relays or solve bot challenges to get past a block; if an IP class stays blocked, use an owner-controlled Thai host.
- **Identify honestly:** `User-Agent: BKK-FloodWatch/<version> (+https://flood.autobahn.bot; <contact>)`. **Never spoof a browser**, rotate proxies, or otherwise get around blocks, bot challenges or rate limits. If blocked, ask the agency or use the approved Thai collector node ([KI-101](KNOWN_ISSUES.md)).
- **Be polite:** poll no more often than the source updates (≥10 min for telemetry), cache aggressively, and back off under errors. Their servers are under flood load too.
- **Respect ToS and robots.txt.** Ask HII, BMA and BMA/NECTEC (Traffy) for permission before public redistribution.
- **Privacy:** don't store or republish citizen text or photos from third-party sources. Aggregate crowd reports spatially ([KI-107](KNOWN_ISSUES.md)).
- **Our own user feedback (D-020):**
  - collect the minimum: no names or contacts;
  - location only when the user opts in, rounded to ~100 m;
  - never store IPs, only `sha256(FEEDBACK_SALT + date + IP)` for rate limiting (`FEEDBACK_SALT` lives in `.env`, not the DB);
  - **never publish notes**; the public sees counts only;
  - feedback triggers human review and evaluation, **never an automatic change** to a forecast or status (KI-507);
  - every form says it is **not an emergency channel** and shows 1784 / 1555.
- **Be polite on failures too:** remember endpoints that fail deterministically (e.g. chart HTTP 500s) and retry them once a day, not on every run.
- **Licensing:** Open-Meteo and FABDEM are non-commercial; a paid plan is needed if the app is monetised ([KI-106](KNOWN_ISSUES.md)).
- **Attribution** on every screen.

---

## 6. Citizen UX and communication (D-005)
People using the app may be stressed, on the move, or protecting their home. Be immediate, calm and unambiguous.

```
┌────────────────────────────────────────────────────────────────────────┐
│  📍 คลองแสนแสบ บางกะปิ (BKK008)                                          │
│  ข้อมูลล่าสุด 14:30 น. (สสน.) · อัปเดตทุก 10 นาที                             │
├────────────────────────────────────────────────────────────────────────┤
│  สถานะ: ระดับน้ำสูงกว่าตลิ่ง ~30 ซม. (เตือนภัย)                               │
│                                                                        │
│  📈 12 ชม. ข้างหน้า: มีแนวโน้ม "เพิ่มขึ้น" ประมาณ 3–10 ซม.                      │
│     สูงสุดช่วง 16:00–18:00 น.  (ความเชื่อมั่น: ปานกลาง)                         │
│                                                                        │
│  ⏱️ คาดว่าจะลดต่ำกว่าตลิ่ง: ประมาณ 28–30 ก.ย.                                │
│     เงื่อนไข: หากไม่มีฝนตกหนักเพิ่ม และเครื่องสูบน้ำทำงานปกติ                          │
│                                                                        │
│  ⚠️ เป็นการคาดการณ์ โปรดติดตามประกาศทางการ · กทม. 1555 · ปภ. 1784             │
└────────────────────────────────────────────────────────────────────────┘
```
*(The numbers in the mockup are illustrative.)*

1. **Two golden questions above the fold:** "จะขึ้นหรือลง?" (the trend with a range) and "เมื่อไหร่จะกลับสู่ปกติ?" (a **date or time range**).
2. **No minute-precise countdowns.** Show ranges and a confidence level. If new heavy rain is forecast, say "ยังประเมินไม่ได้" instead of guessing.
3. **Always state the conditions** (rain, pumps, RID release plan).
4. **Citizen mode (default)** uses landmark depth bands and a probability category ([KNOWLEDGE §6](KNOWLEDGE.md)), plus action checklists. **Expert mode** shows m MSL, discharge, tide, quantile fans and model level.
5. **Stale data is shown as stale.** Grey the value out and show its age. Never present a stale reading as current.
6. Thai font (Noto Sans Thai or Sarabun), with an option for Buddhist-era dates. Must be fast on weak mobile connections, and accessible (contrast, doesn't rely on colour alone).
7. **Lead with centimetres to the bank** ("ต่ำกว่าตลิ่ง 35 ซม."), not m MSL. MSL stays visible as secondary detail.
8. **Mobile first** ([UX_VALIDATION](UX_VALIDATION.md)):
   - tabs instead of stacked map + list, and the detail as a bottom sheet;
   - tap targets ≥ 44 px, safe-area insets, search by district or khlong;
   - share and deep links (`#s=CODE`) for LINE;
   - check at 390 px width before each deploy.
9. **Compact statistics only:** status counts (tap to filter), rising/falling counts, 24 h rain, and data freshness. Anything more goes to `/api/health`.
10. **No invented surfaces:** never interpolate water levels across land, walls or polders (D-019). Don't draw lines across data gaps > 90 min. A reading older than 24 h shows status "unknown".
11. **"Nearest gauge" isn't "your home":** say so wherever distance-based results appear (Bangkok isn't flat; walls split areas).
12. **Point check (D-021):** show a category with its range and confidence, never a level or depth at the pin. The four warnings are always visible. No verdict at very low confidence. Put citizen reports next to the gauges.
13. **Charts need a rough time axis:** day markers with short Thai dates (owner feedback 2026-09-26); no fine ticks.
14. **Filter values, never stations (D-024):** keep every station visible and hide only the misleading value (wrong datum, implausible, stale), always with a note saying why. Approximate positions are dashed and give their radius.
15. **Version on screen (D-025):** the header badge and footer show the deployed version from the API.
16. **Urgent notes:** if a note matches emergency keywords, show 1669 / 1784 / 191 immediately, and say the site has no responders.

---

## 6b. AI usage (D-022, D-030)
- **The site must work identically without AI.** Only the worker calls AI, in the background, with error isolation and circuit breakers.
- **Provider options:** **GLM (`glm-5.3-flash`, D-030)** via Zhipu AI OpenAPI (`open.bigmodel.cn`) is supported and verified for Thai citizen note triage, alongside Cloudflare Workers AI.
- **AI never writes safety facts** (status, levels, times, advice). Those come strictly from deterministic templates and the forecast code.
- AI output must match a strict schema (`parse_label`) or it is discarded. AI may add urgency, never remove it.
- **No personal data to AI** beyond the note text the user chose to send; no locations, IPs, or hashes.
- **Instant fallback:** keyword-based deterministic rules (`triage_rules`) run without network dependencies and instantly trigger emergency hotlines (1669/1784/191) if needed.

## 6c. Releases (D-025)
Bump `floodwatch.__version__` and `pyproject.toml`, add a [CHANGELOG](../CHANGELOG.md) entry, tag `vX.Y.Z`, publish a GitHub release, and bump the `?v=` asset query. The UI reads the version from `/api/stats`.

## 7. Code and security standards

### 7.1 Security
- `.env`, `certs/` and `*.pem` are git-ignored. Commit only `.env.example` with placeholders.
- Services bind to **127.0.0.1**. Public traffic enters only through the Cloudflare Tunnel. No open 80/443.
- SSH: root login is key-only (`PermitRootLogin without-password`) and every login in practice uses a key; password authentication is still enabled globally, but no account except root has a usable password ([KI-214](KNOWN_ISSUES.md)). Recommended: `PasswordAuthentication no` and `fail2ban` (owner's call on this shared host).
- **Backups:** R2 off-site backups are kept disabled by owner choice ([D-029](plan/DECISIONS.md)); telemetry archive and database are kept locally on the server disk.
- **Publishing & License:** the repository is **public** (owner's action, 2026-09-26; [D-028](plan/DECISIONS.md)). All rights are reserved by default (no LICENSE file added, by owner choice, Q10). Everything committed is world-readable, including docs and commit messages, so **never write secrets, IP addresses, account ids, emails, or feedback content** into files or commit messages. Scan before any push if in doubt. Adding a license, rewriting history or force-pushing needs the owner's explicit approval.

### 7.2 Python (backend, collectors, models)
- Python ≥ 3.11. Type hints with built-in generics (`dict[str, float]`, `list[Reading]`, `X | None`).
- `ruff` for lint and format; `pytest`. Structured JSON logging via `logging`, with no `print` in services.
- Timezone-aware datetimes only (`datetime.now(tz=UTC)`), no naive `now()`.
- One adapter per source ([collectors/](../src/floodwatch/collectors/README.md)). Recorded fixtures in tests, never live calls.

### 7.3 Frontend
- Thai-first and i18n-ready. Minimal bundle; loads well on 3G/4G.
- Talks only to our API. CSS variables for design tokens.
- Escape every external string (`esc()`); no `innerHTML` with raw API text. Bump the `?v=` query on `app.js` / `style.css` in `index.html` when they change: `/static` files carry no Cache-Control, so browsers and the Cloudflare edge may cache them heuristically.
