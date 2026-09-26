# HANDOFF.md — State of the project and how to continue

> Updated **2026-09-26 ~18:00 UTC (01:00 ICT 27 Sep)** so any developer or AI harness (Claude Code, Codex, Gemini CLI, Cursor, …) can pick this up cold. **Release v0.3.2** ([CHANGELOG](CHANGELOG.md)) · **What the owner needs to do: [docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md)** (`python3 scripts/owner_status.py`) · Read this first, then [CLAUDE.md](CLAUDE.md) and [docs/plan/PLAN.md](docs/plan/PLAN.md). Several sessions work on this repo: **always `git pull --ff-only` and check `git log` before editing**. **The repository is public: never commit secrets, IPs, account ids, emails or feedback content (D-028).**

## 1. What is live right now
| Item | State |
|---|---|
| **Main domain** | **https://flood.autobahn.bot** (D-017), **the only domain now** (D-035). Bot Fight Mode is off (owner, 17:33 UTC): curl, Facebook and LINE user agents get HTTP 200. A flood-only page rule (security level and Browser Integrity Check off) is kept |
| Alias | `flood.bejranonda.com` **301s every path to flood.autobahn.bot** (D-034/D-035); only `/api/health` still answers there. Rollback: `REDIRECT_LEGACY_HOST=0` + `docker compose up -d app` |
| Site | **v0.3.2** (version in the header badge and footer). **Region chips (default กทม. this week, D-033), place search (D-032), collapsible footer.** Thai, **mobile-first**: summary strip (status chips that filter, rising/falling counts, Bangkok rain in the next 24 h, reporting freshness for focus + whole network), tabs (รายการ / แผนที่ / เจ้าพระยา), search, bottom-sheet station detail with a **24 h outlook**, recovery range, chart (gaps not bridged), **share + deep link `#s=CODE`**, and **citizen feedback**, **point check** (tap the map anywhere or use GPS: gauges around the pin, citizen reports, warnings; no invented level; shareable `#p=lat,lon`), chart day markers |
| API | `/api/health`, `/stations`, `/stations/{code}`, `/near`, `/stats`, `/profile` (river km), **`/point`**, **`/summary`** (template), `/reports`, `/rain`, `POST /feedback` (instant `urgent` flag), `/feedback/summary`; docs at `/api/docs` ([ARCHITECTURE §1.1](docs/ARCHITECTURE.md)) |
| Stations | **+199 BMA khlong gauges** via the flood69 relay (D-031, KI-217/218; history from 2026-09-26 16:30 UTC) → **310 in focus, 209 in Bangkok**. HII: **111 focus stations**, whole BMR + lower Chao Phraya (D-023). **Every station is shown** (D-024): 96 on the map (82 HII positions + **14 approximate OSM positions**, dashed, KI-207), **15 listed without a position**. Misleading values are hidden with a per-station note: GLF002 not MSL (KI-210); **> bank + 3 m flagged** (BKK003 stuck at 7.45 m, KI-211); > 24 h old → "unknown". Map toggle shows the whole HII network. `TEST*` excluded |
| History | **365-day backfill complete: 79 / 79 stations** (verified 15:20 UTC; it stalled at 34 until the worker began running a batch at every start, KI-212). Then `hii_history` refreshes 3 days every 6 h. **57 of 107 stations now serve a tide-based forecast** (44 of 95 before). DB 589 MB, 14 GB disk free |
| Server | Single host `HZ-Agent` (Hetzner DE, 4 vCPU / 7.7 GB, ~13 GB free). **No other environment** (D-013) |
| Stack | `docker compose` project `floodwatch`: `db` (postgres:16-alpine), `worker`, `app` (FastAPI :3000, 2 uvicorn workers), `cloudflared` (profile `public`), `vpn` (profile `vpn`) |
| Public path | Both hostnames → proxied CNAME → **tunnel `d62b426d…`** (the owner's new token, 2026-09-26 09:19 UTC) → `cloudflared --url http://app:3000`. No inbound ports |
| Thai egress | `vpn` container (VPN Gate relay 49.48.220.198) + proxy `http://vpn:8888`. **Flaky**: at 09:30 UTC the exit was up but `dds.bangkok.go.th` timed out ([KI-505](docs/KNOWN_ISSUES.md)) |
| AI (optional) | **GLM (`glm-5.3-flash`, D-030)** triages feedback notes in the worker (`ai_triage`), with Cloudflare Workers AI fallback. **The site never calls AI** and works unchanged without it. Live GLM triage verified ✅ (`local_drainage`, urgent=false). Token in `.env` |
| Repo | https://github.com/bejranonda/flood2026 — **PUBLIC** (owner action; verified 15:20 UTC). Full-history scan done: clean (D-028). **No LICENSE** by owner choice (all rights reserved, Q10). Git commit author updated to **`bejranonda <bwerapol@gmail.com>`** |

## 2f. Session 2026-09-26 16:05–16:50 UTC: new sources, BMA gauges, place search, UX round 3–4 (v0.3.0)
| Owner request / event | Result | Where |
|---|---|---|
| "Consider more sources": BMA KlongMap, BMA road flood, flood69 relay, BMA's road artifact | BMA unreachable (reset from DE; relay can't connect). **flood69 `/api/klongmap` relays BMA: 199 gauges** → integrated after the owner chose "use and show" (Q24). Road artifact: static, hand-made → **link only**. Its sensor host is a private VPN portal → **not used** | [SOURCES §2c](docs/SOURCES.md), [D-031](docs/plan/DECISIONS.md), [APPROACH §3.7](docs/APPROACH_AND_METHODS.md) |
| Datum check on co-located BMA/HII gauges | **Disagree by 0.3–0.6 m** → never mix levels across agencies | [KI-217](docs/KNOWN_ISSUES.md) |
| "Too much info in the footer" | Sources and methods collapse behind a tap | UX_VALIDATION #22 |
| UX check as a Bangkok resident (live, 390/1366 px) | Only 10/111 gauges were in Bangkok → **region chips**, default กทม. (Q26); BKK009 "0 cm below" under an overflow badge fixed (KI-216) | UX_VALIDATION #23–26 |
| A real user asked for data for their soi in Sai Mai (near Saphan Mai); search found nothing; "AI for search?" | **Place search via OSM Nominatim, not AI** (D-032): finds the soi first; the point check there shows BMA Khlong Song 1.8 km away, 30 cm over its bank | `/api/geocode`, [geocode.py](src/floodwatch/geocode.py) |
| Answers: audience = Bangkok residents; no Thai machine (Q17) | Recorded | [OPEN_QUESTIONS](docs/plan/OPEN_QUESTIONS.md) A22–A26 |
| Owner: "Bot Fight Mode is OFF now" | Q18 ✅ (curl/Facebook/LINE UAs → 200); **`/api/*` now redirects too**: only flood.autobahn.bot remains (D-035), `/api/health` still answers on the old host | [D-035](docs/plan/DECISIONS.md) |
| Owner: "historic graph and forecasting all lost?" | **Nothing lost.** My v0.3.0 bug (KI-219) stalled the worker ~1 h; BMA gauges are new (history since 16:25 UTC). Fixed + "🆕 new gauge" labels (v0.3.2) | [KI-219](docs/KNOWN_ISSUES.md), UX #32 |
| A parallel session restarted the app during testing → 5 s of 502 | Two sessions deploy the same containers; coordinate (only one deploys) | UX_VALIDATION #25 |

## 2e. Session 2026-09-26 15:50–16:05 UTC: git author, license, R2 disabled, GLM triage, GISTDA key
| Owner request / event | Result | Where |
|---|---|---|
| "update the git user to https://github.com/bejranonda when commit" | Git config updated locally and globally to `user.name=bejranonda`, `user.email=bwerapol@gmail.com`. Commits properly attributed on GitHub | `.git/config`, `~/.gitconfig` |
| "A license (Q10)... all rights are reserved. I won't add one for you." | Confirmed: no LICENSE file added. All rights reserved by copyright default. Q10 closed | [D-028](docs/plan/DECISIONS.md), [OPEN_QUESTIONS](docs/plan/OPEN_QUESTIONS.md) |
| "Enable R2 for off-site backups (Q15b/Q16)... > keep disable" | R2 off-site backups remain **disabled** by owner choice. Telemetry raw archive and database remain stored on the local VPS disk. Q15b/Q16 closed | [D-029](docs/plan/DECISIONS.md), [OPEN_QUESTIONS](docs/plan/OPEN_QUESTIONS.md) |
| "I will change from Cloudflare AI to GLM, is it possible. When good, please adapt .env to have GLM token" | **GLM integrated and live**: `src/floodwatch/ai.py`, `.env`, `.env.example`, `docker-compose.yml`. Configured with `glm-5.3-flash`. Live inference tested & verified in worker (`Parsed: {'category': 'local_drainage', 'urgent': False}`). Deterministic fallback intact | [D-030](docs/plan/DECISIONS.md), [APPROACH §3.6](docs/APPROACH_AND_METHODS.md) |
| "I have the key for Gistda, please adap the .env" | `GISTDA_API_KEY` and `GISTDA_API_ENDPOINT` added to `.env`, `.env.example`, `docker-compose.yml`, and `src/floodwatch/config.py`. Key configured by owner and verified in `scripts/owner_status.py` ✅ | `.env`, `docker-compose.yml`, [config.py](src/floodwatch/config.py) |
| Owner status (verified 16:02 UTC) | Q18 bot challenge open; RID coordinates open; GLM ✅; GISTDA ✅; License ✅; R2 🚫 (disabled by choice) | `python3 scripts/owner_status.py` |

## 2d. After the resume, 2026-09-26 15:20–15:45 UTC ("continue to finish"; v0.2.1)
| Finding | What I did | Where |
|---|---|---|
| **The owner made the repository public** | Scanned **every commit** (secret values compared without printing them): no credentials, `.env`, `.ovpn`, data or personal email ever committed; the only `.env` value in history is the internal `http://vpn:8888`. **The server IP is in 8 old commits** → removed from the current docs, history left alone (a rewrite needs the owner's go-ahead). No LICENSE was added (owner's call, Q10) | [D-028](docs/plan/DECISIONS.md), [KI-214](docs/KNOWN_ISSUES.md) |
| Public IP → checked the host | 15,754 failed SSH logins in 24 h (normal scanning). `passwordauthentication yes`, but root is key-only and no other account has a usable password; every login in 7 days used a key. **Not changed** (shared host, lockout risk); recorded with exact commands as an optional owner action. The guideline that claimed "SSH by key only" was corrected | [KI-214](docs/KNOWN_ISSUES.md), [OWNER_ACTIONS](docs/OWNER_ACTIONS.md) |
| **Traffy answered HTTP 502 for ~2.5 h** and each failing run held the worker loop 2+ min | Traffy: one attempt per run; repeatedly failing tasks back off ×2/×4/×6 (HII core capped at ×2). Test added | [KI-213](docs/KNOWN_ISSUES.md) |
| Backfill | **Completed 79/79** after the startup fix (was stuck at 34). Forecast methods re-measured: 57 tide-based, 45 persistence-only, 2 trend, 3 too short | [APPROACH §3.3](docs/APPROACH_AND_METHODS.md) |
| **Real users** | 10 feedback reports in ~4.5 h from 8 senders: 7 from a map pin, all with a location, 6 drainage notes (AI-labelled, none urgent), **0 used the station verdict buttons**. AI cost 41.7 of 3,000 neurons/day | [APPROACH §3.5](docs/APPROACH_AND_METHODS.md), [UX_VALIDATION](docs/UX_VALIDATION.md) |
| Owner status (unchanged since 11:20) | Q18 bot challenge still open (curl 403 `cf-mitigated`); R2 still not enabled; no `CF_AI_TOKEN`; no RID coordinates; no LICENSE | `python3 scripts/owner_status.py` |

## 2c. Session 2026-09-26 11:12–11:25 UTC: requests → results (v0.2.1)
| Owner request | Result | Where |
|---|---|---|
| "Keep/record what I need from you for later" | New **[docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md)**: prioritised items with why, exact steps, cost and verification, plus decisions that need only an answer. New **`scripts/owner_status.py`**: read-only, never prints a secret. OPEN_QUESTIONS cleaned (answered items moved) | [D-026](docs/plan/DECISIONS.md) |
| (verification) | **The owner had already acted**: old tunnel deleted ✅, tunnel rights on the API token ✅ (11:15 UTC). **R2 is not enabled** (API: "Please enable R2 through the Cloudflare Dashboard"). **The bot challenge is NOT fixed**: my first script run said "done" because Python's urllib passes while curl, Chrome and crawlers are challenged (TLS-fingerprint dependent). Script now uses curl + `cf-mitigated`. Cloudflare docs: **Bot Fight Mode can't be skipped by WAF rules**, so my earlier "Configuration Rule + WAF skip" advice was wrong for it → corrected | [KI-506](docs/KNOWN_ISSUES.md), [KI-504](docs/KNOWN_ISSUES.md) |
| (measured for Q11) | Raw archive **~3–5 MB/hour (~100 MB/day, 3–4 GB/month)**; DB dir 724 MB. R2 free tier 10 GB-month, free egress, $0.015/GB-month after → free ~2 months, then well under $1/month | [ARCHITECTURE §9](docs/ARCHITECTURE.md), [OWNER_ACTIONS](docs/OWNER_ACTIONS.md) |
| (found) | The alias page's `canonical`/`og:url` pointed crawlers **from the working alias to the challenged domain** → alias now self-canonical; redirect switch built (E2E-tested on a temporary server: `/`→301, `/api/stations?scope=all`→301 with query, `/api/health`→200, new host→200) but off. **Worker restarts starved the backfill** (stuck at 34/79) → a batch now runs at startup. **First real feedback** arrived (10:17 UTC: depth "knee", no note, no location) | [D-027](docs/plan/DECISIONS.md), [KI-212](docs/KNOWN_ISSUES.md) |
| "Release as next version, show it on the UI" | **v0.2.1** (patch): version in the header badge, footer, `/api/health`, `/api/stats`; [CHANGELOG](CHANGELOG.md); tag; GitHub release | [D-025](docs/plan/DECISIONS.md) |

## 2b. Session 2026-09-26 10:50–11:15 UTC: requests → results
| Owner request | Result | Where |
|---|---|---|
| "Include all stations on the map; filter misleading data but show the stations with a note" | `/api/stations` serves every focus station with `notes`. **14/29** unlocated gauges placed approximately (Nominatim 0/29; an Overpass name search matched an OSM town, canal, temple or RID office in the right province; ±2–5 km, dashed), 15 listed. GLF002 shown with values hidden. **New QC:** > bank + 3 m flagged (BKK003's 7.45 m "538 cm over bank" was a stuck sensor; 3,104 readings re-flagged; genuine max +1.90 m). Whole-country toggle | [D-024](docs/plan/DECISIONS.md), [KI-211](docs/KNOWN_ISSUES.md), [KI-207](docs/KNOWN_ISSUES.md) |
| "I can't click the station; the Traffy circle catches it" | Stations on a top map pane; Traffy cells smaller and non-interactive (a tap opens the point check) | `web/app.js` |
| "Release the next version; show the version in the UI" | **v0.2.0**: `__version__`, `/api/health` + `/api/stats`, header badge + footer, [CHANGELOG](CHANGELOG.md), git tag, GitHub release | [D-025](docs/plan/DECISIONS.md) |

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
| Found while working | TEST02 (11 days stale) ranked as the top "overflowing" gauge → fixed (KI-206/209). Rate limit broken by 2 uvicorn workers with separate salts → shared `FEEDBACK_SALT`. **Worker hung 15+ min** on a trickling HII response → total deadline per request (`httpclient.fetch`). **The single-threaded worker would have been blocked for hours** by a 104-station backfill with row-by-row inserts → batched `hii_backfill` + `COPY` bulk insert (measured: ~10 s per station-year, e.g. BKK021 52,545 rows; 16/69 id-bearing stations done at 09:54 UTC; that ETA was superseded, see §1 for the current one). **`outlook24` returned a numpy bool → every forecast save failed for ~10 min (09:42–09:53 UTC)** → cast to plain types, plus a test that JSON-serialises the payload; forecasts restored (95 stations in 31 s). A spurious "peak window" under persistence (CPY015) → peak shown only when a tide model is served. **Payoff of the backfill:** C.12 moved from persistence to the tide model at all horizons. Known-500 chart codes were retried 3× every 6 h → once a day | [KNOWN_ISSUES](docs/KNOWN_ISSUES.md) |

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
python3 scripts/owner_status.py                     # what the owner still needs to do (read-only, no secrets printed)
docker compose run --rm --no-deps worker pytest -q    # 33 tests passing at handoff
# feedback review (notes are private; never publish them)
docker compose exec db psql -U floodwatch -d floodwatch -c "SELECT created_at, code, verdict, depth, note FROM user_feedback ORDER BY id DESC LIMIT 50"
# backfill progress
docker compose exec db psql -U floodwatch -d floodwatch -c "SELECT jsonb_array_length(value) FROM collector_state WHERE key='hii_graph_backfilled'"
```
- **Secrets:** `.env` (git-ignored; backups `.env.backup-20260926`, `…b`, `…c`). New key this session: **`FEEDBACK_SALT`** (generated; keep it stable, because changing it resets the rate-limit identity). The `.ovpn` is git-ignored. **Never commit `.env`, `certs/`, `*.pem`, `infra/openvpn/*.ovpn`.**
- **Tunnel token change checklist:** after replacing `CLOUDFLARE_TUNNEL_TOKEN`, run `docker compose --profile public up -d --force-recreate cloudflared`, read the new `tunnelID` from its log, and **re-point every CNAME** (`flood.autobahn.bot`, `flood.bejranonda.com`) to `<new id>.cfargotunnel.com`. The API token has DNS edit on both zones ([KI-504](docs/KNOWN_ISSUES.md)).
- **Frontend cache:** Cloudflare serves `/static/*` with `max-age=14400`. **Bump `?v=` in `web/index.html`** when `app.js` or `style.css` change (currently `app.js?v=7`, `style.css?v=4`; v0.2.1 changed no static files).
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
| [scripts/owner_status.py](scripts/owner_status.py) | Read-only status of owner actions (curl for the challenge, Cloudflare GETs, `.env` key presence, one tiny AI call); never prints secrets |
| [scripts/build_chainage.py](scripts/build_chainage.py) | River km from HII's centreline → `src/floodwatch/data/chaophraya_chainage.json` |
| [web/](web/app.js) | Vanilla JS + Leaflet: summary, tabs, search, sheet, share, feedback, river profile. `esc()` on every external string |
| [infra/vpn/](infra/vpn/Dockerfile) | OpenVPN + tinyproxy sidecar with a watchdog |
| [tests/](tests/) | `test_parsing.py`, `test_forecast.py` (incl. outlook and the 45-day window), `test_api.py` (freshness, feedback validation, stale status) |

## 5. Next steps, in priority order
0. ~~Q18~~ **Done 17:33 UTC (D-035):** Bot Fight Mode off; everything is on flood.autobahn.bot. Still to do there: remove the old hostname's CNAME/tunnel route after a few weeks of redirects; test a real LINE share (previews should now work; not verified with the app itself). **BMA gauges (v0.3.0) follow-ups:** (a) store the **outside level at the 45 gates** (`wl_out01`, now only in the raw archive) as its own series → head across the gate → **polder-aware near-me** (step 3); (b) after ~7 days of history, compare *changes* at the 5 BMA/HII pairs (KI-217) and let the forecast ladder serve BMA gauges; (c) **density-adaptive point-check radius** (APPROACH §3.7), tested against user depth reports; (d) revisit the Bangkok default on **2026-10-03** (D-033); (e) watch `bma_klong` health: the relay is third-party (KI-218).
1. **Owner actions — see [docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md)** (run `python3 scripts/owner_status.py` first). In order: **Q18** bot challenge (then set `REDIRECT_LEGACY_HOST=1`) · **R2** enable + S3 token (then build the nightly `pg_dump` + archive replication and a **tested restore**, [ARCHITECTURE §9](docs/ARCHITECTURE.md)) · **Q21** Workers-AI-only token · **RID** gate coordinates · **Q10** license. Everything else is an answer only.
2. ~~Check the backfill finished~~ **Done (79/79, 57 stations on tide-based forecasts).** Next modelling step: look at *which* horizons and stations the tide model now wins, and re-check calibration (coverage of the 5–95 % band) on the last 45 days per station.
3. **Positions for the 15 unplaced stations**, and exact positions for the 14 approximate ones: RID's gate coordinates are the proper source ([KI-207](docs/KNOWN_ISSUES.md)). More QC rules: flatline and rate of change ([KI-211](docs/KNOWN_ISSUES.md)). Then **polder-aware "near me" / point check** (biggest UX gap, [UX_VALIDATION §3](docs/UX_VALIDATION.md)): polder polygons (BMA drainage zones) → choose the gauge in the same water body.
4. **1-D river interpolation (D-019):** chainage exists now (HII centreline). Next: a per-reach bias term + tide phase lag fitted on the year of history; leave-one-out on C.12 / CPY015 / CPY014. Ship only if RMSE < 0.10 m (today 0.20).
5. **Feedback use:** real reports exist now (10 in 4.5 h). Build the weekly script that compares depth reports at pins with the nearby gauges' status ([APPROACH §3.5](docs/APPROACH_AND_METHODS.md)) and a stronger prompt for the station verdict question (0 of 10 used it); a review page if the owner wants one (Q19).
6. **Coordinates / bank for the 34 / 28 stations** lacking them; **BMA / DWR** through a better Thai egress; the **Navy tide PDF** link; **GLF001** by asking HII/Navy directly.
7. **Forecast upgrades (Phase 2):** routing (C.2 → C.13 → C.35 lags), `utide` now that ~1 year exists, LightGBM, status calibration against official warning levels.
8. **Alerts** (Q7) and a service worker for offline use.

## 6. Rules that must survive a change of harness
- **Show every station; hide misleading values with a note** (D-024). **Releases:** bump the version, CHANGELOG, tag, GitHub release (D-025).
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
