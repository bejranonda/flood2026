# GUIDELINES.md — Engineering, Modelling, Data Ethics & UX Standards

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-27
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
- **Site head is part of the product** (2026-09-30): every release keeps `index.html`'s title, description (same horizons as the app), canonical, `og:image`/`twitter:card`, JSON-LD and `<noscript>` line true; never hard-code a version in HTML (use `__VERSION__`); a new crawler-visible route goes through `robots.txt` (keep DB-heavy per-coordinate routes out); regenerate `web/og-image.jpg` and `docs/img/social-preview.png` with `scripts/make_social_images.py` after a visual change.
- **A reading stamped in the future is never "latest"** (KI-247): every adapter flags `future_time` beyond 15 minutes.
- **README is the public front page** (2026-09-30): lead with what the app does, the live link, the safety notice and screenshots; plain words, no decision IDs above the fold; facts current (sample outputs from a live call with its time); FAQ in Thai and English. History and decisions belong in CHANGELOG/DECISIONS, operations in HANDOFF.
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
- **Judge a series, not only a reading** (D-057, KI-237): `qc_level` sees one value; one- or two-reading dropouts and gauges that jump back and forth (pumps at the sensor) pass it. `floodwatch.qc` flags dropouts and hides erratic gauges; a filter that also removes real pump drawdowns is not acceptable (measure false positives on clean gauges first).
- **Per-request work must not scale with visitors** (KI-246): anything every visitor gets (station list, stats, street cells) is computed once per minute and shared; a heavy query on the request path needs a cache or a precomputed table. Load-test (≥ 30 concurrent) after touching `STATIONS_SQL`.
- **Never block the single worker loop** (KI-213, KI-239): a job that touches many stations spreads its work over runs (a few gauges per run), asks upstream nothing when it has nothing to do, and sets aside an item that keeps failing instead of retrying it first forever.
- **Version metadata:** station bank level, datum, location and rating changes are versioned with effective dates, never overwritten.

---

- **Adding a source adds stations to every query** (KI-219): check each collector's and the forecaster's station selection (filter by `agency`), and watch one full worker cycle in the logs after deploying.
- **Judge a gauge by the yardstick its owner uses** (D-038): BMA canals by BMA's warning/critical (drainage), rivers and HII/RID gauges by the bank. Always name the yardstick ("เกินเกณฑ์ กทม.", "ต่ำกว่าตลิ่ง").
- **Name what a gauge measures, not what the area is like** (D-036): never "ปกติ"/green for a channel below its bank; use "ต่ำกว่าตลิ่ง" (blue) and show street reports beside it. Hide gauges only when they say nothing about now (no data 24 h), and fold them away rather than deleting them from the page.
- **Always state the age of a secondary layer** (Traffy) when it is more than an hour old.
- **Measured facts and forecasts are different lines** (D-058): what the water did ("24 ชม. ที่ผ่านมา: ลดลง 5 ซม.") needs no model skill and is always shown; a forecast direction needs a model that beat "no change". Never let a "no change" model speak as if it had looked ("ยังไม่เห็นแนวโน้มลดลง…" at a falling gauge, KI-240).
- **Words match the rounded number** (D-056, D-058): classify on the value you print (e.g. −4.6 cm prints 5 → "ลดลง", not "เล็กน้อย"); a few cm matter in a flood, so do not round small steady changes away.
- **Prove consistency before a release** (D-062): `python3 scripts/ux_consistency.py` — list = sheet = pin panel, headline = rows, words = numbers, no overflow at 360/390/768/1440 px; C1–C3, C5, C6 must be 0.
- **Pin factors are one phrase each** (issue #6, D-063): "น้ำในคลองล้นตลิ่ง", not "ระดับน้ำในคลอง · ล้นตลิ่ง".
- **Desktop fits the screen** (issue #9): no fixed pixel offsets for heights; the page is one 100dvh column.
- **The headline speaks for what the panel shows** (D-062): same gauge, same horizon (24 h); never "ทรงตัว" above a falling row.
- **A row word never contradicts its numbers** (D-060): if the numbers would lean the other way (a "ลดลง" row with a range reaching +14 cm), keep the word and move the numbers into the ⓘ.
- **Panel text is short** (owner 2026-09-28): a headline, one line, the rest behind "รายละเอียด"/ⓘ; check at 390 px.
- **Resident first** (D-061): design for someone at home in a flooded or at-risk soi; operator statistics go behind a toggle.
- **A river gauge is never canal evidence** (KI-223, D-059), in the canal factor, the gate or the headline.
- **New stations must say they are new** (no empty chart without an explanation): the API gives `history_since`/`history_days`, the UI labels gauges with < 7 days of history.

- **Never let one slow host or task hold the collectors (KI-251, D-064).** Connect timeouts are short (10 s) and a host that refused a connection is skipped for 10 min; long work (forecasts, learning) runs in its own container. Only the collector runs `schema.sql` (KI-252).
- **Cached payloads may nest only through a re-entrant lock (KI-250).** After every deploy, time `/api/stations` at the origin (`curl http://127.0.0.1:3000/api/stations`), not only `/api/health`.
- **Every table that grows with gauges × time needs a retention** (`retention.py`): readings 400 days (never BMA), rain-forecast issues 3 days, forecast runs thinned after 2 days and dropped after 14.

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
- **Attribution** on every screen. Relayed data names both the owner and the relay (BMA via flood69, D-031).
- **Never mix levels across agencies** (KI-217): a BMA level and an HII level at the same place can differ by 0.3–0.6 m. Compare each gauge only with its own bank; combine agencies only as status ranks. Never use BMA `warning`/`critical` as a bank (KI-215).
- **What users type is private:** place-search queries are never logged, stored or sent anywhere except the geocoder (D-032). The same goes for error messages that might contain them.

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
12. **Point check (D-021, D-051):** show a category with its range and confidence, never a level or depth at the pin. The caveats (gauge ≠ street/home, walls and polders, distance) sit behind the panel's ⓘ since v0.7.0 (owner decision, D-051) — so the visible wording itself must never imply a level at the pin, and the canal factor says "ประเมินไม่ได้" (grey) when gauges are far or disagree. No verdict at very low confidence. Put citizen reports next to the gauges.
13. **Charts need a rough time axis:** day markers with short Thai dates (owner feedback 2026-09-26); no fine ticks.
14. **Filter values, never stations (D-024):** keep every station visible and hide only the misleading value (wrong datum, implausible, stale), always with a note saying why. Approximate positions are dashed and give their radius.
15. **Version on screen (D-025):** the header badge and footer show the deployed version from the API.
16. **Urgent notes:** if a note matches emergency keywords, show 1669 / 1784 / 191 immediately, and say the site has no responders.
17. **Numbers people can read (issue #1, KI-224):** no `~` in user-facing text (it reads as a minus on phones); write "ประมาณ"/"ราว". Every rain amount carries its TMD word (ฝนเล็กน้อย / ปานกลาง / หนัก / หนักมาก) and says whether it is past or forecast ("อีก 24 ชม." / "24 ชม. ที่ผ่านมา"). Unknown is "ไม่มีข้อมูล", never 0. The Python (`point.py RAIN_*`) and JS (`RAIN_TMD`) bands change together.
18. **National statements (D-044, APPROACH §19):** every statement outside the tested area shows its **tier** (วัดจริง · ประมาณจากแบบจำลอง · จากดาวเทียม) and source with its time; verdicts only against **official** thresholds (APPROACH §19.3); agencies' own products (HII FFPI, DWR status) are shown as theirs, not re-labelled; an empty satellite result is never "no flood"; virtual gauges are snapped and categorical only. Nothing national is public until D-046's conditions hold.
19. **Freshness before storage (KI-111):** a national collector drops rows older than 3 × its cadence and any epoch-0 date, and reports fresh/total in `/api/health`.
20. **Zero-crossing delta intervals (D-048):** Conformal intervals crossing zero under steady conditions must be phrased as `ทรงตัว (อาจแกว่งตัว -A ถึง +B ซม.)`, never contradictory words ("ลด 11 ถึงเพิ่ม 17 ซม.").
21. **Compact UI and progressive disclosure (D-049):**
    - Confidence indicator: Single color-coded `ⓘ` button (sky-blue for tide-calibrated models, slate-gray for baseline persistence) with desktop hover tooltip and touch-triggered non-blocking toast on mobile.
    - Technical surveying datum (`ม.รทก.`): Prioritize observation freshness on the main line; tuck raw surveying elevation into an interactive `[ม.รทก. ⓘ]` button.
    - Textual chart legends: Make collapsible (`<details class="chart-legend">`) to preserve vertical mobile viewport height.

22. **Horizons (D-050, D-052, D-055):** every method, including `star`, earns its place per gauge and horizon in the backtest; since v0.10.0 a 48 h line appears everywhere a forecast exists, but an unproven one shows only a range ("ยังบอกทิศทางไม่ได้ · ช่วงที่น่าจะเป็น …"), never a direction; a 12/24 h change is shown per gauge; a 48 h line only where the 48 h backtest gives "medium" confidence. When a high gauge shows no fall in 24 h, say "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า" — never "stable for 48 h". Outside forecasts (HII) are shown only after our scoring shows they beat "no change" and ours, labelled with their assumptions.
24. **One trend format (D-056):** every horizon, in every view, is a row `ใน N ชม. · chip · signed range · ⓘ`; a direction only where a real model beat "no change" at that horizon, otherwise "? ไม่แน่ชัด" + range. "When it drops" uses the same wording in panel and sheet (`dropText`). Status words must match the numbers next to them (no "ใกล้ตลิ่ง" when the bank is far). Say a thing once: a reason shown in a factor is not repeated in the headline text (KI-235). The same kind of item gets the same layout: every gauge in the canal factor is a block (label line → bold name · distance · status pill → its rows), KI-234.
23. **Logs are data too (D-032, KI-512):** access logs must not contain search text or coordinates; `RedactQuery` strips the query string of `/api/geocode`, `/api/point`, `/api/reverse`, `/api/near`. Any new endpoint that takes a place or a position is added to `PRIVATE_QUERY_PATHS`.

---

- **A release must reach open tabs (KI-253).** The page is `no-cache`; the app reloads itself once per new version (`maybeUpdate`), never while a panel is open. Bump `?v=` on static files as before.
- **The headline uses the rows' words (D-060, C6).** Server-side wording ("ทรงตัว") follows the same ±5 cm rule as the UI rows (`point.STEADY_M` = `app.js STEADY_M`).
- **Location (D-065):** never ask for GPS on page load; only the 📍 button asks. A choice the user made by hand (region chip) beats an automatic one.
- **Check a new data source against one you trust before modelling (Q43).** Same gauge, same period: units, scale and which hours a "day" covers. A daily total labelled D may cover hours of D+1 or end early on D; pick the timing rule that is safe under every plausible convention, and always run a placebo (shuffled input) next to the real one.
- **A fetch that succeeds is not fresh data (KI-257).** Health and the UI judge a source by its newest *reading*; when most of a region is stale, the summary says so in one line.
- **One rain vocabulary (v0.17.1, supersedes v0.16.7):** rain uses the water rows' layout everywhere (`rainRows`): a short bold state ("ฝนตกแล้ว" / "คาดว่าจะมีฝน" / "ไม่มีฝน"), the forecast as a row "อีก 24 ชม. [<TMD word chip>] ราว N มม. ⓘ", what fell as "24 ชม. ที่ผ่านมา: <TMD word> N มม."; sources, gauge, distance and reading time behind an ⓘ. The headline above the factors never repeats an amount (KI-258).
- **One way to say "when" (v0.17.2, owner: "ใน 24 ชม." was not understood as the future):** a forecast horizon is "อีก N ชม." in a row label and "ในอีก N ชม." in a sentence; the past is "N ชม. ที่ผ่านมา" (or "ล่าสุด"); never a bare "ใน N ชม." for the future. Guarded by `tests/test_wording.py`.
- **One direction story per gauge (KI-256).** A heuristic row (measured trend) never contradicts a direction the backtested model proved at another horizon; differing model horizons are allowed (tides, rain arriving later).
- **A filter never hides places the user can pan to (KI-253).** The map shows every gauge; region chips filter the list and counts and move the map. Every chip must be visible at 390 px without scrolling.
- **Nationwide parity (D-064):** one set of panels and rules for every gauge. Words come from data, never from guesses: the water word from the agency's river name (`water_word`), agency names in Thai (`AGENCY_TH`). Bangkok-only cautions (polders, drainage, BMA pumping) are said only where the nearest gauge is a Bangkok-area gauge (`pin_mode`). Never promise a date for a forecast; say what must happen first (history, backtest).

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
- **Publishing & License:** the repository is **public** (owner's action, 2026-09-26; [D-028](plan/DECISIONS.md)) and open source under the **MIT License** ([LICENSE](../LICENSE), [D-043](plan/DECISIONS.md)). Everything committed is world-readable, including docs and commit messages, so **never write secrets, IP addresses, account ids, emails, or feedback content** into files or commit messages. Scan before any push if in doubt. Rewriting history or force-pushing needs the owner's explicit approval.

### 7.2 Python (backend, collectors, models)
- Python ≥ 3.11. Type hints with built-in generics (`dict[str, float]`, `list[Reading]`, `X | None`).
- `ruff` for lint and format; `pytest`. Structured JSON logging via `logging`, with no `print` in services.
- Timezone-aware datetimes only (`datetime.now(tz=UTC)`), no naive `now()`.
- One adapter per source ([collectors/](../src/floodwatch/collectors/README.md)). Recorded fixtures in tests, never live calls.

### 7.3 Frontend
- Thai-first and i18n-ready. Minimal bundle; loads well on 3G/4G.
- Talks only to our API. CSS variables for design tokens.
- Escape every external string (`esc()`); no `innerHTML` with raw API text. Bump the `?v=` query on `app.js` / `style.css` and icon links in `index.html` when they change: `/static` files carry no Cache-Control, so browsers and the Cloudflare edge may cache them heuristically.
- **Favicon & Brand Icons (D-039, KI-221):**
  - Favicons display at **16×16 CSS pixels** in browser tabs. Never cram micro-details (sub-pixel dots, pulse rings, nested shells, ruler ticks, thin 1px borders) into the icon.
  - Fill the canvas (e.g. rounded squircle) so the icon occupies the full 14×14–16×16 area instead of a narrow shape with empty sides.
  - High contrast: Bold white wave (`#ffffff`) on vibrant blue (`#0284c7`) works against both dark tabs (`#202124`) and light tabs (`#dee1e6` / `#ffffff`).
  - iOS Touch Icons: Must use a solid canvas background (not transparent), because iOS renders transparent PNG backgrounds as solid black.
  - Generation: `scripts/generate_favicon.py` uses standard library only (math, struct, zlib) with 2×2 supersampling for subpixel smoothness and zero external runtime dependencies.

