# HANDOFF.md — State of the project and how to continue

> Written 2026-09-26 (ICT afternoon) so any developer or AI harness (Claude Code, Codex, Gemini CLI, Cursor, …) can pick this up cold. Read this first, then [CLAUDE.md](CLAUDE.md) (agent rules) and [docs/plan/PLAN.md](docs/plan/PLAN.md).

## 1. What is live right now
| Item | State |
|---|---|
| Public site | **https://flood.bejranonda.com**: Thai MVP (map, station list, status vs bank, 12 h trend, recovery range, chart with forecast band, "สถานีใกล้ฉัน") |
| API | `https://flood.bejranonda.com/api/…` (`/health`, `/stations`, `/stations/{code}`, `/near`, `/reports`, `/rain`, docs at `/api/docs`) |
| Server | This single host (`HZ-Agent`, 178.104.238.220, Hetzner DE, 4 vCPU / 7.7 GB RAM, ~13 GB free disk). **No other environment exists** (owner, 2026-09-26) |
| Stack | `docker compose` project `floodwatch` in `/root/flood2026`: `db` (postgres:16-alpine), `worker`, `app` (FastAPI :3000 on 127.0.0.1), `caddy` (profile `origin`, host network, :80/:443, **Cloudflare IPs only**) |
| Public path | Cloudflare proxy (A record → 178.104.238.220) → Caddy (self-signed origin cert in `certs/`) → app. Direct IP access is refused |
| Repo | https://github.com/bejranonda/flood2026 (**private**) |

## 2. Operate
```bash
cd /root/flood2026
docker compose --profile origin up -d --build     # start/update everything (db, worker, app, caddy)
docker compose ps
docker compose logs -f worker                     # collectors + forecasts
curl -s localhost:3000/api/health | python3 -m json.tool
docker compose run --rm --no-deps worker pytest -q   # tests (8 passing at handoff)
infra/update-cloudflare-ips.sh                    # refresh the Cloudflare allowlist in Caddy
```
- Secrets: `.env` (git-ignored; backup `.env.backup-20260926`). `POSTGRES_PASSWORD` was generated for the DB. **Never commit `.env` or `certs/`.**
- Data: `data/pg` (Postgres) and `data/raw_archive` (immutable gzip payloads + `.meta.json`, dedup by SHA-256). Both git-ignored.
- Worker schedule ([worker.py](src/floodwatch/worker.py)): HII latest every 10 min, Traffy every 10 min, HII rain every 30 min, Open-Meteo hourly, HII history every 6 h, forecasts every 30 min, disk check hourly (alerts below 2 GB free).

## 3. Code map
| Path | What |
|---|---|
| [src/floodwatch/collectors/parsing.py](src/floodwatch/collectors/parsing.py) | Pure parsers + QC (timezone, `999999` sentinel, range). Tested |
| [src/floodwatch/collectors/\_\_init\_\_.py](src/floodwatch/collectors/__init__.py) | Collectors: HII `waterlevel_load`, `rain_24h`, `waterlevel_graph` (RID + HII history by numeric id), chart XHR `getGraphFirst` (BKK/CPY/BKC/AIT + BKK008), Open-Meteo, Traffy (privacy-safe), BMA (only with a Thai egress proxy) |
| [src/floodwatch/archive/](src/floodwatch/archive/__init__.py) | Raw archive writer (write-once, SHA-256) |
| [src/floodwatch/db/](src/floodwatch/db/__init__.py) | Schema ([schema.sql](src/floodwatch/db/schema.sql)) + helpers. Plain Postgres (D-013) |
| [src/floodwatch/forecast/](src/floodwatch/forecast/__init__.py) | MVP forecasts: persistence / persistence + fitted tide / + damped trend; per-station rolling backtest; served only if skill > 10 % vs persistence; split-conformal quantiles; recovery range; status |
| [src/floodwatch/api/](src/floodwatch/api/__init__.py) | FastAPI + static web |
| [web/](web/index.html) | Thai frontend (vanilla JS + Leaflet with SRI, SVG chart) |
| [docker-compose.yml](docker-compose.yml), [Dockerfile](Dockerfile), [infra/Caddyfile](infra/Caddyfile) | Deployment |

## 4. Known gaps — next steps in priority order
1. **Cloudflare Tunnel (KI-501):** the API token in `.env` can read tunnels but **cannot create them** (403). To switch to the tunnel (no open ports): add *Account → Cloudflare Tunnel: Edit* to the token, create a tunnel with ingress `flood.bejranonda.com → http://app:3000`, replace the A record with a CNAME to `<id>.cfargotunnel.com`, put the token in `CLOUDFLARE_TUNNEL_TOKEN`, run `docker compose --profile public up -d cloudflared`, and stop `caddy`. (The old 33-character `CLOUDFLARE_TUNNEL_TOKEN` value is not a valid tunnel token.)
2. **Off-site backup (R2):** no R2 credentials yet → the raw archive and DB exist **only on this disk**. Add `R2_*` to `.env` and implement replication plus a nightly `pg_dump` (ARCHITECTURE §9).
3. **BMA DDS (KI-101/103):** blocked from this German IP. Set `THAI_EGRESS_PROXY=socks5h://127.0.0.1:1080` after opening an SSH SOCKS tunnel to **any Thai host you control** (`ssh -N -D 1080 user@thai-host`) or a paid VPN with a Thai exit. The `bma_dds` collector then archives raw pages; a parser is still to be written once the format is visible. Don't use free public proxies (tampering and abuse risk).
4. **Bang Sai C.29A, Memorial Bridge, Fort Chula tide (KI-109):** not in HII. Find RID feeds; tide stays on our own fits until then.
5. **Forecast upgrades (Phase 2):** longer history (loop `waterlevel_graph` further back), `utide` with ≥ 1 year, upstream routing features (C.2 → C.13 → C.35 lags), rain-driven khlong model, LightGBM L4/L5, polder polygons for "near me" (it's currently nearest by distance only).
6. **Disk:** ~13 GB free, shared with other projects. The archive grows by roughly 30–80 MB/day (estimate) → watch `/api/health` → `disk`.
7. **Owner questions still open:** license and making the repo public (Q10), permissions (Q3 — the owner says don't wait; keep attribution and polite polling), notifications (Q7).

## 5. Rules that must survive a change of harness
Evidence rule (no invented endpoints or numbers), honest User-Agent, attribution, ranges instead of countdowns, stale data shown as stale, and no secrets in git. See [CLAUDE.md](CLAUDE.md) and [docs/GUIDELINES.md](docs/GUIDELINES.md). Decisions: [docs/plan/DECISIONS.md](docs/plan/DECISIONS.md) (D-012–D-014 cover today's MVP choices).
