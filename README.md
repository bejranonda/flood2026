# BKK FloodWatch 2026 🌊
### Water-level monitoring and forecasting for Bangkok and the lower Chao Phraya
> **ระบบติดตามและคาดการณ์ระดับน้ำ กรุงเทพมหานครและลุ่มเจ้าพระยาตอนล่าง (พ.ศ. 2569)**

[![Status: Phase 0](https://img.shields.io/badge/status-Phase%200%20%E2%80%94%20source%20verification-yellow.svg)](docs/plan/PLAN.md)
[![Infra: Cloudflare Tunnel live](https://img.shields.io/badge/infra-Cloudflare%20Tunnel%20live%2C%20app%20not%20deployed-orange.svg)](docs/ARCHITECTURE.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](docs/GUIDELINES.md)

> [!IMPORTANT]
> **Current status (2026-09-26):** documentation and plan only; **no runnable code yet**. The VPS and the Cloudflare Tunnel for `flood.bejranonda.com` are live, but the application isn't deployed. Phase 0 (source verification) has started: the first live probes are in [research/VALIDATION_2026-09-26.md](research/VALIDATION_2026-09-26.md). **Next:** repeat the probes from the production VPS and deliver the Phase 0 report ([plan](docs/plan/phase-0-source-verification.md)).

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
A **VPS core** (collectors → immutable raw archive → Postgres + TimescaleDB + PostGIS → forecasts → FastAPI on 127.0.0.1) behind **Cloudflare** (Tunnel, edge cache, Pages, R2 backups). v1 uses **keyless** sources collected on the server. The browser only talks to our API. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Roadmap
| Phase | Goal | Gate | Status |
|---|---|---|---|
| 0 | [Verify every source from the VPS](docs/plan/phase-0-source-verification.md) | G0: approved source set | 🟡 in progress |
| 1 | [Collectors + our own archive + backfill](docs/plan/phase-1-ingestion-archive.md) | G1: 7 days collected, restore tested | ⏳ |
| 2 | [Forecasting (spatio-temporal, calibrated)](docs/plan/phase-2-forecasting.md) | G2: beats persistence, coverage 85–95 % | ⏳ |
| 3 | [Thai web app](docs/plan/phase-3-web-app.md) | G3: UX review | ⏳ |
| 4 | [Deployment and ops hardening](docs/plan/phase-4-deployment-ops.md) | G4: load and redeploy drills | ⏳ |

Strict gates: each phase stops for the owner's approval ([D-002](docs/plan/DECISIONS.md)). The collectors start the moment G0 passes.

## Data sources (v1, keyless)
| Source | Status (probe 2026-09-26) | Use |
|---|---|---|
| HII ThaiWater public API + chart XHR | ✅ live (805 stations; 30-day history per station) | Levels, bank, discharge (RID stations), rain |
| Open-Meteo forecast / ensemble / flood (GloFAS) | ✅ live | Rain forcing, upstream prior |
| RID portals | 🟡 reachable; Bang Sai (C.29A) feed still to find | Upstream boundary, releases |
| Navy tide tables | 🔴 URL moved + bot challenge → our own harmonic fit as the interim | Tide |
| BMA DDS | 🔴 blocked from non-Thai IPs; test from the VPS | Bangkok khlongs |
| Traffy Fondue public API | ✅ live (privacy rules apply) | Validation, "reported nearby" |

Full registry, including endpoints that were tested and **refuted**: [docs/SOURCES.md](docs/SOURCES.md).

## Repository layout
```
docs/        maintained docs: PLAN, SOURCES, KNOWLEDGE, KNOWN_ISSUES, GUIDELINES, APPROACH_AND_METHODS, ARCHITECTURE
  brief/     the original project brief (first_prompt.md)
  plan/      roadmap, phase checklists, DECISIONS, OPEN_QUESTIONS
research/    research snapshots (claude.ai / Gemini), VALIDATION report, validation/ script
src/floodwatch/{collectors,archive,db,forecast,api}/   scaffold (READMEs only)
web/  edge/  infra/  tests/                            scaffold (READMEs only)
```

## Documentation
| Doc | What's inside |
|---|---|
| [docs/README.md](docs/README.md) | Index, reading order, evidence markers |
| [docs/plan/PLAN.md](docs/plan/PLAN.md) | Roadmap, gates, risks · [DECISIONS](docs/plan/DECISIONS.md) · [OPEN_QUESTIONS](docs/plan/OPEN_QUESTIONS.md) |
| [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md) | Three Waters, datums, stations (HII live metadata), polders, the 2026 event, contacts |
| [docs/SOURCES.md](docs/SOURCES.md) | Source registry with probe results; refuted endpoints |
| [docs/APPROACH_AND_METHODS.md](docs/APPROACH_AND_METHODS.md) | Spatio-temporal framework, model ladder L0–L7, tide, routing, polders, conformal, recovery, depth |
| [docs/GUIDELINES.md](docs/GUIDELINES.md) | Phase gates, evidence rule, data ethics, UX, code and security |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | KI-101…KI-502 with status |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Data flow, storage, security, deployment, adding a source |
| [research/README.md](research/README.md) | Research validity index · [VALIDATION report](research/VALIDATION_2026-09-26.md) |

## Configuration
Copy [`.env.example`](.env.example) to `.env` on the VPS and fill it in. `.env`, `certs/` and `*.pem` are git-ignored; never commit secrets. v1 needs **no data API keys**. Only Cloudflare and R2 credentials are required; TMD and GISTDA keys are optional.

## Reproduce the source validation
```bash
pip install numpy   # only dependency
python3 research/validation/validate_research_claims.py
```
Results depend on the host's country. Run it on the production VPS for Phase 0 ([KI-101](docs/KNOWN_ISSUES.md)).

## Safety notice and official contacts
This project **doesn't replace official warnings**. Always follow BMA, DDPM, RID and HII announcements.
- กรุงเทพมหานคร **1555** · ศูนย์ป้องกันน้ำท่วม กทม. **02-248-5115**
- ปภ. (DDPM) **1784** · กรมชลประทาน (RID) **1460** (to re-verify before launch)
- สสน. (HII): [thaiwater.net](https://www.thaiwater.net)

Data attribution: HII/สสน., RID/กรมชลประทาน, BMA/กทม., Navy Hydrographic Dept., TMD, GISTDA, Traffy Fondue, Open-Meteo / Copernicus GloFAS, as used.
