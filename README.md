# BKK FloodWatch 2026 🌊
### Water-level monitoring and forecasting for Bangkok and the lower Chao Phraya
> **ระบบติดตามและคาดการณ์ระดับน้ำ กรุงเทพมหานครและลุ่มเจ้าพระยาตอนล่าง (พ.ศ. 2569)**

[![Status: MVP live](https://img.shields.io/badge/status-MVP%20live%20(beta)-brightgreen.svg)](https://flood.autobahn.bot)
[![Infra: single server + Cloudflare](https://img.shields.io/badge/infra-single%20server%20%2B%20Cloudflare-orange.svg)](HANDOFF.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](docs/GUIDELINES.md)
[![Domain: Hydrology & Flood Forecasting](https://img.shields.io/badge/domain-hydrology%20%26%20flood%20forecast-0077b6.svg)](docs/APPROACH_AND_METHODS.md)
[![Coverage: Bangkok & Chao Phraya](https://img.shields.io/badge/coverage-Bangkok%20%26%20Chao%20Phraya-023e8a.svg)](docs/KNOWLEDGE.md)
[![Repo: bejranonda/flood2026](https://img.shields.io/badge/github-bejranonda%2Fflood2026-181717.svg?logo=github)](https://github.com/bejranonda/flood2026)

> [!IMPORTANT]
> **Current status (2026-09-26): v0.5.0 live at https://flood.autobahn.bot** ([CHANGELOG](CHANGELOG.md)). **flood.autobahn.bot is the only domain**: `flood.bejranonda.com` redirects everything there (D-035); the bot challenge is off, so link previews and API clients work.
> **What the project needs from its owner:** [docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md) (gate coordinates, a courtesy note to the BMA relay, decisions). Status: `python3 scripts/owner_status.py`.
>
> It collects:
> - HII telemetry (805 stations in the main feed plus chart-only stations → **111 in focus** across the whole Bangkok Metropolitan Region and the lower Chao Phraya; **every station is on the map or listed**, and misleading values are hidden with a note, with up to **one year** of hourly history);
> - **BMA khlong gauges (199, Bangkok)** via the People's Party relay of BMA's KlongMap (D-031);
> - Open-Meteo rain forecasts;
> - Traffy reports;
> - **citizen feedback** from the site itself.
>
> It keeps a raw archive and a Postgres database, serves backtested baseline forecasts with uncertainty bands and a 24 h outlook, and shows a **mobile-first Thai UI**: summary statistics, list (region chips, Bangkok first), **place search** (ซอย/ถนน/ย่าน via OpenStreetMap), map, the Chao Phraya profile, share links, and a **point check** (tap anywhere: gauges around the pin, citizen reports and warnings; no invented water level). **Cloudflare Workers AI** triages feedback notes in the background, and the site works the same without it. Runs on a single server with `docker compose`, published through a **Cloudflare Tunnel** (no inbound ports), with an optional **Thai VPN egress** for geo-blocked public pages ([D-012–D-016](docs/plan/DECISIONS.md)). **Continue from [HANDOFF.md](HANDOFF.md)** (live state, operations, prioritised next steps).

---

## Why
Bangkok and the central plain are flooding right now. HII shows several Bangkok khlongs (BKK008 Saen Saep, BKK021 Lat Phrao) **above bank**, and Ayutthaya stations at or above bank, with **~1,900 m³/s** passing C.13 and C.3 (26 Sep 2026). Official portals publish fragmented data: river discharge, canal levels relative to bank, tide tables in PDFs. Residents need two plain answers.

## The two golden questions
| # | Citizen question | What we compute | What we show |
|---|---|---|---|
| 1 | **"น้ำแถวบ้านจะขึ้นหรือลง ใน 12 ชม. – 3 วัน?"** | Quantile forecasts of H(t+h) at the **controlling** station (polder khlong or river), h = 12 h … 7 d | A trend arrow with a **range** in cm, the peak time window, a confidence level, and depth as a probability category |
| 2 | **"เมื่อไหร่น้ำจะกลับสู่ปกติ?"** | A distribution of the dates when the level falls below bank → below warning → back within the seasonal normal band | A **date or time range with its conditions** ("หากไม่มีฝนตกหนักเพิ่ม…"), never a minute countdown |

Methods: [docs/APPROACH_AND_METHODS.md](docs/APPROACH_AND_METHODS.md).

## The Three Waters (น้ำสามน้ำ)
**น้ำเหนือ** (upstream flood wave: C.2 → C.13 → C.35 → Bang Sai) + **น้ำหนุน** (Gulf tide, mixed and mainly diurnal, plus surge) + **น้ำฝน** (convective rain above the ~60 mm/h drainage capacity), all modulated by **human control**: giant tunnels, gates, pumps, dam releases. East Bangkok needs a rain + polder model; the riverside needs routing + tide. See [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md).

## Architecture (short)
A **single-server core** (collectors → immutable raw archive → Postgres → forecasts → FastAPI) behind a **Cloudflare Tunnel** (no inbound ports; R2 backups pending). TimescaleDB/PostGIS come later. v1 uses **keyless** sources collected on the server. The browser only talks to our API. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Roadmap
| Phase | Goal | Gate | Status |
|---|---|---|---|
| 0 | [Verify every source](docs/plan/phase-0-source-verification.md) | G0: approved source set | 🟡 HII, Open-Meteo, Traffy in production; BMA/Navy open |
| 1 | [Collectors + our own archive + backfill](docs/plan/phase-1-ingestion-archive.md) | G1: 7 days collected, restore tested | 🟡 running; 1-year backfill; no R2 yet |
| 2 | [Forecasting (spatio-temporal, calibrated)](docs/plan/phase-2-forecasting.md) | G2: beats persistence, coverage 85–95 % | 🟡 L0/L1 + trend, conformal bands, 24 h outlook |
| 3 | [Thai web app](docs/plan/phase-3-web-app.md) | G3: UX review | 🟡 live, mobile-first, feedback ([UX_VALIDATION](docs/UX_VALIDATION.md)) |
| 4 | [Deployment and ops hardening](docs/plan/phase-4-deployment-ops.md) | G4: load and redeploy drills | 🟡 tunnel live; backups and alerts next |

All workstreams run in parallel during the flood ([D-012](docs/plan/DECISIONS.md)); the gates are quality reviews.

## Data sources (v1, keyless)
| Source | Status (probe 2026-09-26) | Use |
|---|---|---|
| HII ThaiWater public API + chart site | ✅ live (805 stations + **162 chart-only candidates**, 34 added; **up to 365 days** of hourly history via `waterlevel_graph`; ~54 chart codes return HTTP 500, incl. Fort Chula and Bang Sai; all workarounds tested) | Levels, bank, discharge (RID stations), rain |
| Open-Meteo forecast / ensemble / flood (GloFAS) | ✅ live | Rain forcing, upstream prior |
| RID portals | 🟡 reachable; Bang Sai (C.29A) feed still to find | Upstream boundary, releases |
| Navy tide tables | 🔴 URL moved + bot challenge → our own harmonic fit as the interim | Tide |
| BMA KlongMap via flood69 relay | ✅ live since v0.3.0: 199 Bangkok gauges, 5-min copies; BMA direct is unreachable from here | Bangkok khlongs, gates (inside/outside) |
| BMA DDS / DWR EWS | 🟡 `weather.bangkok.go.th` unreachable (reset / relay can't connect) | — |
| OSM Nominatim | ✅ place search only, on demand | Find a soi, open the point check |
| Traffy Fondue public API | 🟡 overloaded since 2026-09-26 15:11 UTC (HTTP 502); requests cut to 40 tickets, age shown in the UI | Street flooding beside each gauge (D-036), point check |

Full registry, including endpoints that were tested and **refuted**: [docs/SOURCES.md](docs/SOURCES.md).

## Repository layout
```
docs/        maintained docs: PLAN, SOURCES, KNOWLEDGE, KNOWN_ISSUES, GUIDELINES, APPROACH_AND_METHODS, ARCHITECTURE
  brief/     the original project brief (first_prompt.md)
  plan/      roadmap, phase checklists, DECISIONS, OPEN_QUESTIONS
research/    research snapshots (claude.ai / Gemini), VALIDATION report, validation/ script
src/floodwatch/{collectors,archive,db,forecast,api}/   Python backend (MVP)
web/                                                   Thai frontend (vanilla JS + Leaflet)
infra/ (vpn/ sidecar, legacy Caddyfile)  scripts/ (build_chainage.py, owner_status.py)  tests/  docker-compose.yml  Dockerfile  HANDOFF.md
```

## Documentation
| Doc | What's inside |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | Releases (v0.1.0, v0.2.0, v0.2.1) |
| [docs/OWNER_ACTIONS.md](docs/OWNER_ACTIONS.md) | **What the owner needs to do** (with steps and cost), and how to check it |
| [docs/README.md](docs/README.md) | Index, reading order, evidence markers |
| [docs/plan/PLAN.md](docs/plan/PLAN.md) | Roadmap, gates, risks · [DECISIONS](docs/plan/DECISIONS.md) · [OPEN_QUESTIONS](docs/plan/OPEN_QUESTIONS.md) |
| [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md) | Three Waters, datums, stations (HII live metadata), polders, the 2026 event, contacts |
| [docs/SOURCES.md](docs/SOURCES.md) | Source registry with probe results; refuted endpoints |
| [docs/APPROACH_AND_METHODS.md](docs/APPROACH_AND_METHODS.md) | Spatio-temporal framework (incl. **§2.9 is interpolation useful?**, **§2.10 point check**), model ladder L0–L7, statistics (§3.4), **feedback loop (§3.5)**, **Workers AI (§3.6)**, tide, routing, polders, conformal, recovery, depth |
| [docs/GUIDELINES.md](docs/GUIDELINES.md) | Phase gates, evidence rule, data ethics, UX, code and security |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | KI-101…KI-508 and KI-210…212 with status |
| [docs/UX_VALIDATION.md](docs/UX_VALIDATION.md) | Resident personas, UX findings, what changed, what's still missing |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Data flow, storage, security, deployment, adding a source |
| [research/README.md](research/README.md) | Research validity index · [VALIDATION report](research/VALIDATION_2026-09-26.md) |

## Repository and license
Hosted at [github.com/bejranonda/flood2026](https://github.com/bejranonda/flood2026) — **public** (the owner changed visibility on 2026-09-26; the full history was scanned clean, see [D-028](docs/plan/DECISIONS.md)). **All rights reserved by owner choice** (no LICENSE file added, Q10): you may read and fork on GitHub, but reuse needs the owner's permission. Data from third parties keeps its own terms ([docs/SOURCES.md](docs/SOURCES.md)).

## Configuration
Copy [`.env.example`](.env.example) to `.env` on the VPS and fill it in. `.env`, `certs/`, `*.pem` and `infra/openvpn/*.ovpn` are git-ignored; never commit secrets. v1 needs **no data API keys** to run basic monitoring. Cloudflare (tunnel token) is required for publishing. **R2 off-site backups are kept disabled by owner choice** ([D-029](docs/plan/DECISIONS.md)); data and archive stay on the local VPS disk. **AI feedback note triage supports GLM** (`glm-5.3-flash`, [D-030](docs/plan/DECISIONS.md)) and Cloudflare Workers AI. **GISTDA API key** is configured in `.env` for satellite flood extent.

## Run it
```bash
cp .env.example .env    # then set POSTGRES_PASSWORD (and the Cloudflare values if publishing)
docker compose --profile public --profile vpn up -d --build   # db, worker, app, Cloudflare Tunnel, Thai VPN egress
docker compose run --rm --no-deps worker pytest -q
```
Operations and next steps: [HANDOFF.md](HANDOFF.md).

## Reproduce the source validation
```bash
pip install numpy   # only dependency
python3 research/validation/validate_research_claims.py
```
Results depend on the host's country (this host is in Germany; BMA blocks it) ([KI-101](docs/KNOWN_ISSUES.md)).

## Search & AI discovery index

| Category | Keywords (EN / TH) |
|---|---|
| **Core Domain** | Bangkok flood monitoring, Chao Phraya flood forecasting, water-level prediction, urban flood risk, early warning system, ระบบติดตามน้ำท่วม, พยากรณ์ระดับน้ำ, คาดการณ์น้ำท่วม กรุงเทพมหานคร |
| **Geographic Coverage** | Bangkok (BMA), lower Chao Phraya river basin, Ayutthaya, Nonthaburi, Pathum Thani, Khlong Saen Saep (คลองแสนแสบ), Khlong Lat Phrao (คลองลาดพร้าว), Gulf of Thailand |
| **Key Hydrological Stations** | C.2 (Nakhon Sawan), C.13 (Chao Phraya Dam), C.35 (Ayutthaya), C.29A (Bang Sai / บางไทร), Fort Chula (ป้อมพระจุลฯ), BKK008, BKK021 |
| **Hydrological Phenomena** | The Three Waters (น้ำสามน้ำ): น้ำเหนือ (upstream river discharge), น้ำหนุน (Gulf tidal surge & harmonic tide), น้ำฝน (urban convective precipitation & polder drainage) |
| **Data Providers** | HII (สสน. / ThaiWater), Royal Irrigation Department (RID / กรมชลประทาน), BMA Department of Drainage and Sewerage (สำนักการระบายน้ำ กทม.), Royal Thai Navy Hydrographic Dept (กรมอุทกศาสตร์ กองทัพเรือ), Open-Meteo GloFAS |
| **Architecture & Modeling** | Spatio-temporal graph modeling, lag routing, quantile regression, conformal prediction calibration, TimescaleDB, PostGIS, FastAPI, Cloudflare Tunnel & Pages |

## Safety notice and official contacts
This project **doesn't replace official warnings**. Always follow BMA, DDPM, RID and HII announcements.
- กรุงเทพมหานคร **1555** · ศูนย์ป้องกันน้ำท่วม กทม. **02-248-5115**
- ปภ. (DDPM) **1784** · กรมชลประทาน (RID) **1460** (to re-verify before launch)
- สสน. (HII): [thaiwater.net](https://www.thaiwater.net)

Data attribution: HII/สสน., RID/กรมชลประทาน, BMA/กทม., Navy Hydrographic Dept., TMD, GISTDA, Traffy Fondue, Open-Meteo / Copernicus GloFAS, as used.
