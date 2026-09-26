# HANDOFF.md — State of the project and how to continue

> Updated 2026-09-26 ~09:00 UTC (16:00 ICT) so any developer or AI harness (Claude Code, Codex, Gemini CLI, Cursor, …) can pick this up cold. Read this first, then [CLAUDE.md](CLAUDE.md) (agent rules) and [docs/plan/PLAN.md](docs/plan/PLAN.md). Several sessions have worked on this repo: **always `git pull`/check `git log` before editing**.

## 1. What is live right now
| Item | State |
|---|---|
| Public site | **https://flood.bejranonda.com**: Thai MVP (map, station list, status vs bank, 12 h trend, recovery range, chart with forecast band, "สถานีใกล้ฉัน", citizen-report hotspots) |
| API | `https://flood.bejranonda.com/api/…` (`/health`, `/stations`, `/stations/{code}`, `/near`, `/reports`, `/rain`; docs at `/api/docs`) |
| Stations served | **104 focus stations** (was 69): Ayutthaya 32, Nakhon Sawan 16, Chai Nat 13, Bangkok 13, Sing Buri 10, Pathum Thani 8, Samut Prakan 5, Ang Thong 4, Nonthaburi 3. **34 have no coordinates** (list only, not on the map); **28 have no bank level** (status "unknown"). See [KI-207](docs/KNOWN_ISSUES.md) |
| Server | This single host (`HZ-Agent`, 178.104.238.220, Hetzner DE, 4 vCPU / 7.7 GB RAM, ~13 GB free disk). **No other environment exists** (owner, 2026-09-26) |
| Stack | `docker compose` project `floodwatch`: `db` (postgres:16-alpine), `worker`, `app` (FastAPI :3000), `cloudflared` (profile `public`), `vpn` (profile `vpn`) |
| Public path | Cloudflare Tunnel: `flood.bejranonda.com` CNAME → `<tunnel id>.cfargotunnel.com` (proxied) → `cloudflared` → `http://app:3000`. **No inbound ports are open** (80/443 closed; only 127.0.0.1:3000 locally). The old Caddy origin is retired |
| Thai egress | `vpn` container = OpenVPN client (VPN Gate relay `49.48.220.198`, Thailand) + HTTP proxy on `http://vpn:8888`, used only by collectors that ask for it (`THAI_EGRESS_PROXY`). Volunteer relay: **flaky and untrusted** ([KI-505](docs/KNOWN_ISSUES.md)) |
| Repo | https://github.com/bejranonda/flood2026 (**private**, D-011) |

## 2. Owner statements checked against evidence (2026-09-26, 08:20–08:50 UTC)
| Owner statement | Verdict | Evidence |
|---|---|---|
| "Many stations are missing, e.g. …/chart/BKK021" | ✅ **True in general; the example was already served.** BKK021 was in the DB and public API (critical, 2.82 m vs bank 2.20). The real gap: the HII chart site lists **162 stations** in our provinces that `waterlevel_load` doesn't (BKK004/007/011/012, ATG\*, MOU\*, …) | `queryStation?prov=<Thai name>` per province vs our DB. **Fix shipped:** `hii_stations` collector added **34** of them (+1 with coordinates) → 104 focus stations. **56 candidates remain unavailable** (chart endpoint returns HTTP 500 or only `999999`) — including **GLF001 ป้อมพระจุลจอมเกล้า (Fort Chula tide gauge, latest 0.03)** and **CPY013 บางไทร (Bang Sai, latest 1.46)** |
| VPN: OpenVPN file added at `infra/openvpn/…` | ✅ **Works, with caveats** | In an isolated container the exit IP is **49.48.220.198, Phra Nakhon Si Ayutthaya, TH (3BB)**. From that IP: `ews.dwr.go.th` 200 (timed out from DE), `hydro.navy.mi.th` 200 (bot wall from DE), `dds.bangkok.go.th` reachable, **`weather.bangkok.go.th` still 403 (IIS "Access is denied", even with a browser UA → IP-class block, not evaded)**. The tunnel needed one restart to carry traffic → watchdog added |
| "Tunnel running now in docker" | ✅ **True** | CNAME → tunnel, public URL 200, ports 80/443 closed, `cloudflared` container up |
| "Token has now Tunnel and R2 permission" | ❌ **Not effective for the token in `.env`** | `/user/tokens/verify` = active, but tunnel get-by-id → *Not authorized* (list returns empty), **R2 list → HTTP 403**. Either a different token was edited, or `.env` holds the old value. Also: R2 needs **S3 API credentials** (`R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY`), which are separate from the API token |
| (found while checking) `CLOUDFLARE_ACCOUNT_ID` in `.env` | ⚠️ **Was wrong** (belonged to another account). The zone and the tunnel token belong to account `6914a3…1a45` → **fixed in `.env`** (backup `.env.backup-20260926b`) |

## 3. Operate
```bash
cd /root/flood2026
git pull --ff-only                                     # other sessions push here
docker compose --profile public --profile vpn up -d --build   # db, worker, app, cloudflared, vpn
docker compose ps
docker compose logs -f worker                          # collectors + forecasts
docker compose logs vpn --tail 20                      # Thai egress
curl -s localhost:3000/api/health | python3 -m json.tool
docker compose run --rm --no-deps worker pytest -q    # 10 tests passing at handoff
python3 research/validation/validate_research_claims.py   # re-run source probes (result depends on host country)
```
- **Secrets:** `.env` (git-ignored; backups `.env.backup-20260926`, `…b`). The `.ovpn` file is git-ignored too. **Never commit `.env`, `certs/`, `*.pem`, `infra/openvpn/*.ovpn`.**
- **Data:** `data/pg` (Postgres) and `data/raw_archive` (immutable gzip payloads + `.meta.json`, dedup by SHA-256), both git-ignored. **Neither is backed up off-site yet.**
- **Worker schedule** ([worker.py](src/floodwatch/worker.py)): HII latest 10 min; Traffy 10 min; HII rain 30 min; Open-Meteo hourly; **`hii_stations` and `hii_history` every 6 h**; forecasts 30 min; disk check hourly (alert below 2 GB free); `bma_dds` every 3 h **only if `THAI_EGRESS_PROXY` is set**.
- **VPN swap:** replace the file in `infra/openvpn/` (one `.ovpn`), then `docker compose --profile vpn up -d --build vpn`. Check `docker compose exec vpn curl -s https://ipinfo.io/ip`.

## 4. Code map
| Path | What |
|---|---|
| [src/floodwatch/collectors/parsing.py](src/floodwatch/collectors/parsing.py) | Pure parsers + QC (timezone, `999999` sentinel, `0/0` bank-ground placeholders, range, map-feed coordinates). Tested |
| [src/floodwatch/collectors/\_\_init\_\_.py](src/floodwatch/collectors/__init__.py) | Collectors: HII `waterlevel_load`, `rain_24h`, `waterlevel_graph` (RID + HII history by numeric id), chart XHR `getGraphFirst` (BKK/CPY/BKC/AIT, BKK008 and every chart-only station), **`hii_stations`** (chart station lists + map feed), Open-Meteo, Traffy (privacy-safe), BMA (via Thai egress) |
| [src/floodwatch/archive/](src/floodwatch/archive/__init__.py) | Raw archive writer (write-once, SHA-256) |
| [src/floodwatch/db/](src/floodwatch/db/__init__.py) | Schema ([schema.sql](src/floodwatch/db/schema.sql)) + helpers. Plain Postgres (D-013) |
| [src/floodwatch/forecast/](src/floodwatch/forecast/__init__.py) | MVP forecasts: persistence / persistence + fitted tide / + damped trend; per-station rolling backtest; served only if skill > 10 % vs persistence; split-conformal quantiles; recovery range; status |
| [src/floodwatch/api/](src/floodwatch/api/__init__.py) · [web/](web/index.html) | FastAPI + Thai frontend (vanilla JS, Leaflet with SRI, SVG chart) |
| [infra/vpn/](infra/vpn/Dockerfile) | OpenVPN + tinyproxy sidecar with a watchdog. [infra/Caddyfile](infra/Caddyfile) is legacy (not running) |
| [docker-compose.yml](docker-compose.yml), [Dockerfile](Dockerfile) | Deployment |

## 5. Next steps, in priority order
1. **Off-site backup (R2)** — blocked on the owner: create an R2 bucket, **S3 API token** (Access Key ID + Secret) and put `R2_*` in `.env`; also fix the API token's R2 permission (see §2). Then implement replication of `data/raw_archive` and a nightly `pg_dump` ([ARCHITECTURE §9](docs/ARCHITECTURE.md)). Until then everything lives on one disk.
2. **Chart-only stations that answer HTTP 500** (GLF001 Fort Chula, CPY013 Bang Sai, BKK004, BKC001, FROC01, …): try the chart page's `POST /getGraph` (form + CSRF `_token`; see `getGraph` in the page source) and the `water1` field returned by `queryStation` (latest value only, no timestamp). **Highest value: GLF001 (tide gauge) and CPY013 (Bang Sai).** Closes [KI-109](docs/KNOWN_ISSUES.md).
3. **Coordinates and bank levels for the 34 / 28 stations lacking them** (HII map feed `json/telemetering/wl/warning` covers only 107 stations). Sources to try: `waterlevel_graph` metadata (`min_bank`, `ground_level` in its response), RID station list `water.rid.go.th/hyd/…`, OSM/name geocoding as a last resort (flag it as approximate).
4. **BMA / DWR through the Thai egress:** `dds.bangkok.go.th` and `ews.dwr.go.th` open from the relay; `weather.bangkok.go.th` is 403 even from it. Explore DWR EWS and the DDS pages (now possible via `http://vpn:8888`), write parsers with fixtures, and find a Thai IP that BMA accepts (owner-controlled host, or another relay).
5. **Navy tide:** `TT2026.pdf` is 404 even from a Thai IP → the URL moved. The Navy home page is reachable through the proxy; find the current link. Until then tide = our own fits (add GLF001 history when available).
6. **Forecast upgrades (Phase 2):** longer history (loop `waterlevel_graph` back), `utide` with ≥ 1 year, upstream routing (C.2 → C.13 → C.35 lags), rain-driven khlong model, LightGBM L4/L5, polder polygons for "near me" (currently nearest by distance only), calibrate the status thresholds ([APPROACH §3.3](docs/APPROACH_AND_METHODS.md)).
7. **Disk:** ~13 GB free, shared with other projects. Watch `/api/health` → `disk`. Estimated archive growth 30–80 MB/day (measure it).
8. **Owner questions still open:** license and going public (Q10), notifications (Q7), Buddhist-era dates (Q8) — [OPEN_QUESTIONS](docs/plan/OPEN_QUESTIONS.md).

## 6. Rules that must survive a change of harness
Evidence rule (no invented endpoints or numbers; **owner statements are also checked and discrepancies reported**), honest User-Agent, attribution, ranges instead of countdowns, stale data shown as stale, no secrets in git, and the Thai egress limits in [GUIDELINES §5](docs/GUIDELINES.md) (public pages only, no credentials through the relay, no bot-challenge solving). See [CLAUDE.md](CLAUDE.md). Decisions: [docs/plan/DECISIONS.md](docs/plan/DECISIONS.md) (D-012–D-016 cover the MVP choices).
