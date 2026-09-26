# HANDOFF.md — State of the project and how to continue

> Updated **2026-09-26 ~10:50 UTC (17:50 ICT)** so any developer or AI harness (Claude Code, Codex, Gemini CLI, Cursor, …) can pick this up cold. Read this first, then [CLAUDE.md](CLAUDE.md) (agent rules) and [docs/plan/PLAN.md](docs/plan/PLAN.md). Several sessions work on this repo: **always `git pull --ff-only` and check `git log` before editing**.

## 1. What is live right now
| Item | State |
|---|---|
| **Main domain** | **https://flood.autobahn.bot** (D-017). ⚠️ The `autobahn.bot` zone shows a Cloudflare "Just a moment…" challenge to non-browser clients (curl, headless Chrome, link previews): [KI-506](docs/KNOWN_ISSUES.md), owner action Q18 |
| Alias | **https://flood.bejranonda.com**: same tunnel, full alias, **no redirect** until KI-506 is fixed |
| Site | Thai, **mobile-first**: summary strip (status chips that filter, rising/falling counts, Bangkok rain in the next 24 h, reporting freshness for focus + whole network), tabs (รายการ / แผนที่ / เจ้าพระยา), search, bottom-sheet station detail with a **24 h outlook**, recovery range, chart (gaps not bridged), **share + deep link `#s=CODE`**, and **citizen feedback**, **point check** (tap the map anywhere or use GPS: gauges around the pin, citizen reports, warnings; no invented level; shareable `#p=lat,lon`), chart day markers |
| API | `/api/health`, `/stations`, `/stations/{code}`, `/near`, `/stats`, `/profile` (river km), **`/point`**, **`/summary`** (template), `/reports`, `/rain`, `POST /feedback` (instant `urgent` flag), `/feedback/summary`; docs at `/api/docs` ([ARCHITECTURE §1.1](docs/ARCHITECTURE.md)) |
| Stations | **110 focus stations**, the whole Bangkok Metropolitan Region (Samut Sakhon and Nakhon Pathom added) + the lower Chao Phraya (D-023). 81 on the map (BKK008 fixed); **29 without coordinates** (Ayutthaya gate pairs etc., KI-207); 26 without a bank level. `TEST*` (KI-209) and **GLF002 (not MSL, KI-210)** excluded. Readings older than 24 h show status "unknown" |
| History | **One-time 365-day backfill** from `waterlevel_graph` (D-018) by `hii_backfill`: 6 stations every 10 min. **28 / 79 done at 10:41 UTC → complete ~12:10 UTC.** Progress: `collector_state.hii_graph_backfilled`. Then `hii_history` refreshes 3 days every 6 h. DB 267 MB |
| Server | Single host `HZ-Agent` (Hetzner DE, 4 vCPU / 7.7 GB, ~13 GB free). **No other environment** (D-013) |
| Stack | `docker compose` project `floodwatch`: `db` (postgres:16-alpine), `worker`, `app` (FastAPI :3000, 2 uvicorn workers), `cloudflared` (profile `public`), `vpn` (profile `vpn`) |
| Public path | Both hostnames → proxied CNAME → **tunnel `d62b426d…`** (the owner's new token, 2026-09-26 09:19 UTC) → `cloudflared --url http://app:3000`. No inbound ports |
| Thai egress | `vpn` container (VPN Gate relay 49.48.220.198) + proxy `http://vpn:8888`. **Flaky**: at 09:30 UTC the exit was up but `dds.bangkok.go.th` timed out ([KI-505](docs/KNOWN_ISSUES.md)) |
| AI (optional) | Cloudflare Workers AI (SEA-LION v4) triages feedback notes in the worker (`ai_triage`, every 15 min; 3,000-neuron daily budget; circuit breaker). **The site never calls AI** and works unchanged without it (D-022). Credentials are in the worker only; the general token is a fallback until `CF_AI_TOKEN` exists (Q21) |
| Repo | https://github.com/bejranonda/flood2026 (**private**, D-011) |

## 2a. Session 2026-09-26 10:20–10:50 UTC: requests → results
| Owner request | Result | Where |
|---|---|---|
| "Check an area with no station by my own pinpoint; interpolation with notes and warnings?" | **Point check** (D-021):<br>• an IDW **area category of gauge status**, not a level, with min–max range and confidence (never "high"; **no verdict at very low**);<br>• nearby gauges labelled river/khlong;<br>• Traffy + user reports within ~1 km;<br>• 24 h rain;<br>• 4 warnings always shown;<br>• report water at the pin (`loc_source=pin`);<br>• shareable `#p=`.<br>Example: pin 13.82, 100.60 → only BKK021 at 4 km → very low, no verdict | [APPROACH §2.10](docs/APPROACH_AND_METHODS.md), [KI-307](docs/KNOWN_ISSUES.md) |
| "Cloudflare AI: how to use it? If the quota is full the app must keep working" | Tested Workers AI with the existing token. SEA-LION v4 gives fluent Thai; triage correct on 3/3 test notes (~0.6 s, ~4.8 neurons each). **Summaries drifted on safety terms** (warning ↔ watch, "nationwide"), so **AI does triage only**; summary and urgency are deterministic. Worker-only, budget 3,000/day, breaker. **Verified:** budget 0 or an invalid token → site unaffected (200) | [APPROACH §3.6](docs/APPROACH_AND_METHODS.md), [D-022](docs/plan/DECISIONS.md), [KI-508](docs/KNOWN_ISSUES.md) |
| "Users can't read rough time from the graph" (screenshot) | **Day markers with short Thai dates** on every chart; "ตอนนี้" moved to the top | `web/app.js` `dayTicks` |
| "Integrate BKK008 in the map; any other missing stations?" | BKK008 had **no coordinates**. The map feed has them, and now fills every station lacking them. **8 gauges within 60 km were outside our focus**, all in Samut Sakhon / Nakhon Pathom → both provinces added (**whole BMR**, 100 → 110 stations). **GLF002** (Tha Chin mouth) excluded: median 5.5 m, max 7.4 m, spikes −28.6 m → not MSL | [D-023](docs/plan/DECISIONS.md), [KI-210](docs/KNOWN_ISSUES.md) |
| "Find coordinates from the map in the warning page" | That map loads **only the same 110-station feed** (+ boundary and river layers) → **no coordinates for the 29 remaining** stations. **But** its river layer gave the **Chao Phraya centreline** → river km per gauge (mouth → Nakhon Sawan 376 km vs ~372 cited). Profile ordered by river km. LOO at C.12 with river km: RMSE 0.200 m, bias +0.171 → interpolation still gated | [scripts/build_chainage.py](scripts/build_chainage.py), [APPROACH §2.9](docs/APPROACH_AND_METHODS.md) |
| Found while working | An urgent note ("ติดอยู่… ช่วยด้วย") now shows **1669 / 1784 / 191** instantly (keyword rules, no network) | [GUIDELINES §6](docs/GUIDELINES.md) |

## 2. Session 2026-09-26 09:00–09:45 UTC: requests → results
| Owner request | Result | Evidence / where |
|---|---|---|
| "Continue the HANDOFF tasks" | **GLF001 / CPY013:** both remaining routes tested and **failed**. `POST /getGraph` (+CSRF) → HTTP 500, and it only returns the latest point even for working stations. `queryStation.water1` frozen (GLF001 0.03 m at 08:30 and 09:04). **Found instead:** `waterlevel_graph` serves **365 days** → 1-year backfill; the tide is fitted on up to a year; the backtest uses the last 45 days (D-018) | [KI-207](docs/KNOWN_ISSUES.md), [SOURCES](docs/SOURCES.md) |
| "Is spatio-temporal interpolation useful? Bangkok is not flat" | **2-D over land: no, it misleads.** Metro banks range 0.43–4.56 m; walls and gates split areas; gauges are 7.7 km apart; `ground_level` is the channel bed. **1-D along the Chao Phraya: promising but not ready.** Leave-one-out at C.12: RMSE 0.175 m vs 0.38–0.46 m for nearest-gauge, with +0.15 m bias. Shipped the gauge-only river profile; interpolation waits for chainage + tide lag, shown only if RMSE < 0.10 m (D-019) | [APPROACH §2.9](docs/APPROACH_AND_METHODS.md) |
| "Compact statistics" | `/api/stats` + a summary strip. Status chips double as filters; freshness shows as 3 numbers + a bar; the whole-network line is behind a toggle. At 09:17 UTC: focus 79 / 95 / 98 of 104 within 1 / 3 / 24 h; network 434 / 783 / 823 of 840 | [APPROACH §3.4](docs/APPROACH_AND_METHODS.md) |
| "Consider mobile users" | Tabs, bottom sheet, ≥ 44 px targets, search, share/deep link, collapsed disclaimer with hotlines, safe-area insets. Checked at 390×844 and 1366×800 | [UX_VALIDATION](docs/UX_VALIDATION.md) |
| "Validate as a Bangkok resident" | 6 personas, 13 findings (12 fixed, 1 partly: "near me" has a caveat but is not polder-aware yet), 8 open items. Biggest remaining gap: **polder-aware "near me"** | [UX_VALIDATION](docs/UX_VALIDATION.md) |
| "User feedback feeds the system" | `POST /api/feedback`: verdict / depth band / note / opt-in location (~100 m), with a server-side snapshot of what was shown. IP never stored (daily-salted hash, `FEEDBACK_SALT` in `.env`); 10 per hour; honeypot. Public sees counts only. Used for review, evaluation and depth labels; **never auto-applied** (D-020) | [APPROACH §3.5](docs/APPROACH_AND_METHODS.md), [KI-507](docs/KNOWN_ISSUES.md) |
| "Change the main domain to flood.autobahn.bot" + new tunnel token | CNAME created via API. `cloudflared` recreated with the new token (tunnel `d62b426d…`). **Both CNAMEs re-pointed** after the old domain briefly returned 530. Canonical, OG, UA and docs updated. **Blocked:** zone-wide bot challenge (KI-506) | [D-017](docs/plan/DECISIONS.md) |
| Found while working | TEST02 (11 days stale) ranked as the top "overflowing" gauge → fixed (KI-206/209). Rate limit broken by 2 uvicorn workers with separate salts → shared `FEEDBACK_SALT`. **Worker hung 15+ min** on a trickling HII response → total deadline per request (`httpclient.fetch`). **The single-threaded worker would have been blocked for hours** by a 104-station backfill with row-by-row inserts → batched `hii_backfill` + `COPY` bulk insert (measured: ~10 s per station-year, e.g. BKK021 52,545 rows; 16/69 id-bearing stations done at 09:54 UTC, the rest by ~11:30 UTC). **`outlook24` returned a numpy bool → every forecast save failed for ~10 min (09:42–09:53 UTC)** → cast to plain types, plus a test that JSON-serialises the payload; forecasts restored (95 stations in 31 s). A spurious "peak window" under persistence (CPY015) → peak shown only when a tide model is served. **Payoff of the backfill:** C.12 moved from persistence to the tide model at all horizons. Known-500 chart codes were retried 3× every 6 h → once a day | [KNOWN_ISSUES](docs/KNOWN_ISSUES.md) |

Earlier owner statements (tunnel, VPN, token rights, missing stations) and their verification are in git history (`git show b78869c:HANDOFF.md`).

## 3. Operate
```bash
cd /root/flood2026
git pull --ff-only                                     # other sessions push here
docker compose --profile public --profile vpn up -d --build   # db, worker, app, cloudflared, vpn
docker compose ps
docker compose logs -f worker                          # collectors + forecasts
curl -s localhost:3000/api/health | python3 -m json.tool
curl -s localhost:3000/api/stats  | python3 -m json.tool
docker compose run --rm --no-deps worker pytest -q    # 27 tests passing at handoff
# feedback review (notes are private; never publish them)
docker compose exec db psql -U floodwatch -d floodwatch -c "SELECT created_at, code, verdict, depth, note FROM user_feedback ORDER BY id DESC LIMIT 50"
# backfill progress
docker compose exec db psql -U floodwatch -d floodwatch -c "SELECT jsonb_array_length(value) FROM collector_state WHERE key='hii_graph_backfilled'"
```
- **Secrets:** `.env` (git-ignored; backups `.env.backup-20260926`, `…b`, `…c`). New key this session: **`FEEDBACK_SALT`** (generated; keep it stable, because changing it resets the rate-limit identity). The `.ovpn` is git-ignored. **Never commit `.env`, `certs/`, `*.pem`, `infra/openvpn/*.ovpn`.**
- **Tunnel token change checklist:** after replacing `CLOUDFLARE_TUNNEL_TOKEN`, run `docker compose --profile public up -d --force-recreate cloudflared`, read the new `tunnelID` from its log, and **re-point every CNAME** (`flood.autobahn.bot`, `flood.bejranonda.com`) to `<new id>.cfargotunnel.com`. The API token has DNS edit on both zones ([KI-504](docs/KNOWN_ISSUES.md)).
- **Frontend cache:** Cloudflare serves `/static/*` with `max-age=14400`. **Bump `?v=` in `web/index.html`** when `app.js` or `style.css` change (currently `app.js?v=5`, `style.css?v=3`).
- **AI:** `collector_state.ai_usage` shows today's calls, neurons, failures and `paused_until`. To reset the breaker, run `UPDATE collector_state SET value = value || '{"failures":0,"paused_until":null}'::jsonb WHERE key='ai_usage'`. To disable, set `AI_ENABLED=0` in `.env` and recreate the worker.
- **River km:** regenerate with `python3 scripts/build_chainage.py stations.csv > src/floodwatch/data/chaophraya_chainage.json`.
- **Worker schedule** ([worker.py](src/floodwatch/worker.py)): HII latest 10 min; Traffy 10 min; **`hii_backfill` 10 min (6 stations; a no-op when done)**; HII rain 30 min; Open-Meteo hourly; `hii_stations` and `hii_history` every 6 h; forecasts 30 min; disk check hourly; `bma_dds` every 3 h if `THAI_EGRESS_PROXY` is set.
- **Data:** `data/pg` and `data/raw_archive` (git-ignored), **not backed up off-site yet**.

## 4. Code map
| Path | What |
|---|---|
| [src/floodwatch/collectors/parsing.py](src/floodwatch/collectors/parsing.py) | Pure parsers + QC. Tested |
| [src/floodwatch/collectors/\_\_init\_\_.py](src/floodwatch/collectors/__init__.py) | Collectors; `hii_backfill` (1-year history, 6 stations per run), `hii_history` (3-day refresh + 10-min chart), `hii_stations` (skips `TEST*`, retries known-500 codes daily) |
| [src/floodwatch/httpclient.py](src/floodwatch/httpclient.py) | Honest UA, retries, **total deadline per request**, optional Thai egress |
| [src/floodwatch/db/](src/floodwatch/db/__init__.py) | Schema incl. **`user_feedback`**, **`collector_state`**; `get_state`/`set_state`; `insert_observations` (COPY for ≥ 500 rows) |
| [src/floodwatch/forecast/](src/floodwatch/forecast/__init__.py) | L0 / L1 tide / trend; 45-day backtest (`EVAL_HOURS`), 370-day lookback; conformal quantiles; **`outlook24`**; recovery; status |
| [src/floodwatch/api/](src/floodwatch/api/__init__.py) | FastAPI: stations, stats, profile (river km), **point**, **summary**, feedback (+ instant urgent flag); stale → unknown after 24 h |
| [src/floodwatch/point.py](src/floodwatch/point.py) | Point check: IDW status category, confidence, warnings. Pure, tested |
| [src/floodwatch/ai.py](src/floodwatch/ai.py) | Keyword triage, Workers AI client (budget, breaker, strict schema), template summary. Tested |
| [scripts/build_chainage.py](scripts/build_chainage.py) | River km from HII's centreline → `src/floodwatch/data/chaophraya_chainage.json` |
| [web/](web/app.js) | Vanilla JS + Leaflet: summary, tabs, search, sheet, share, feedback, river profile. `esc()` on every external string |
| [infra/vpn/](infra/vpn/Dockerfile) | OpenVPN + tinyproxy sidecar with a watchdog |
| [tests/](tests/) | `test_parsing.py`, `test_forecast.py` (incl. outlook and the 45-day window), `test_api.py` (freshness, feedback validation, stale status) |

## 5. Next steps, in priority order
1. **Owner actions:** Q21 (a Workers-AI-only token), Q22 (Traffy / voice AI?), Q18 (relax the `autobahn.bot` challenge for `flood.` → then add a 301 from the old domain), Q15/Q16 (API token rights + **R2 S3 credentials** → off-site backups), Q19 (who reads feedback), Q20 (delete the old tunnel `ecd8a7b9…` if unused).
2. **Check the backfill finished** (69 stations with a numeric id; expected ~11:30 UTC 2026-09-26), then the next forecast run. Record in APPROACH §3.3 how many stations now serve `tide`/`tide_trend` (before: 43 tide-fitted stations were still on persistence). Watch disk (`/api/health` → `disk`) and DB size after the ~5M-row load.
3. **Coordinates for the 29 stations** (mostly Ayutthaya gate pairs `ATG*`): geocode gate names via OSM, flag as approximate. Then **polder-aware "near me" / point check** (biggest UX gap, [UX_VALIDATION §3](docs/UX_VALIDATION.md)): polder polygons (BMA drainage zones) → choose the gauge in the same water body.
4. **1-D river interpolation (D-019):** chainage exists now (HII centreline). Next: a per-reach bias term + tide phase lag fitted on the year of history; leave-one-out on C.12 / CPY015 / CPY014. Ship only if RMSE < 0.10 m (today 0.20).
5. **Feedback use:** a weekly script comparing `verdict` with the displayed snapshot and later observations; a small review page if the owner wants one (Q19).
6. **Coordinates / bank for the 34 / 28 stations** lacking them; **BMA / DWR** through a better Thai egress; the **Navy tide PDF** link; **GLF001** by asking HII/Navy directly.
7. **Forecast upgrades (Phase 2):** routing (C.2 → C.13 → C.35 lags), `utide` now that ~1 year exists, LightGBM, status calibration against official warning levels.
8. **Alerts** (Q7) and a service worker for offline use.

## 6. Rules that must survive a change of harness
- The **evidence rule**: no invented endpoints or numbers; owner statements are checked too.
- An **honest User-Agent**: `BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)`.
- **Attribution**, and **ranges instead of countdowns**.
- **Stale data is shown as stale**; after 24 h the status is "unknown".
- **No interpolated water surfaces over land** (D-019).
- **Feedback stays private and is never auto-applied** (D-020).
- **Point checks show categories and warnings, never a level at the pin** (D-021).
- **AI runs in the worker only, never writes safety facts, and the site must work without it** (D-022).
- **No secrets in git.**
- The **Thai egress limits** in [GUIDELINES §5](docs/GUIDELINES.md).

See [CLAUDE.md](CLAUDE.md) and [DECISIONS](docs/plan/DECISIONS.md) (D-012 … D-020).
