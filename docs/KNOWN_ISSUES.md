# KNOWN_ISSUES.md — Limitations, pitfalls and workarounds

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-26
> **Audience:** developers, operators, AI agents
> **Status values:** 🔴 Open · 🟡 Workaround defined · 🟢 Resolved · ℹ️ Inherent (permanent constraint; design around it)
> Evidence for items marked "probe" is in [research/VALIDATION_2026-09-26.md](../research/VALIDATION_2026-09-26.md).

| ID | Title | Area | Status |
|---|---|---|---|
| KI-101 | Geo/datacenter IP blocking (BMA yes, HII no; VPN partly helps) | Data access | 🟡 |
| KI-102 | Navy tide tables: PDF moved (404) and bot challenge | Data access | 🔴 |
| KI-103 | BMA DDS has no API and isn't mirrored in HII | Data access | 🔴 |
| KI-104 | Short history retention at sources | Data access | 🟡 |
| KI-105 | CORS: actual behaviour differs from earlier claims | Data access | 🟢 |
| KI-106 | Open-Meteo free tier is non-commercial | Data access | ℹ️ |
| KI-107 | Traffy data contains personal data; report time ≠ flood time | Data access | 🟡 |
| KI-108 | Large, slow HII payloads | Data access | 🟡 |
| KI-109 | Key stations missing from HII (C.29A, Memorial Bridge, Fort Chula) | Data access | 🔴 |
| KI-207 | Chart-only stations: missing from the main feed, HTTP 500, no coordinates or bank | Data access | 🟡 |
| KI-201 | Datum mixing (MSL / LLW / gauge zero / EGM2008); LLW offsets unknown | Data quality | 🔴 |
| KI-202 | DEM vertical error ≫ flood depth | Data quality | ℹ️ |
| KI-203 | Station code and metadata ambiguity | Data quality | 🔴 |
| KI-204 | Duplicate stations across agencies | Data quality | 🟡 |
| KI-205 | Mixed timestamp conventions | Data quality | 🟡 |
| KI-206 | Sentinel values, stale stations, spikes | Data quality | 🟡 |
| KI-208 | HII `ground_level` at river gauges is the channel bed, not land | Data quality | ℹ️ |
| KI-209 | HII test gauges (`TEST*`) appear in station lists | Data quality | 🟢 |
| KI-210 | GLF002 (Tha Chin mouth) values are not m MSL | Data quality | 🔴 (excluded) |
| KI-301 | Placeholder tide constants (inverted phase) | Modelling | 🟢 (don't use; fit our own) |
| KI-302 | Draft `BKKHydroEngine` gives implausible output | Modelling | 🟢 (don't port) |
| KI-303 | Managed operations make the system non-stationary | Modelling | ℹ️ |
| KI-304 | Unsourced street-elevation benchmarks | Modelling | 🔴 |
| KI-305 | No archive of as-issued forecasts yet (perfect-prognosis risk) | Modelling | 🔴 |
| KI-306 | Spatial and temporal scale mismatch between data sources | Modelling | ℹ️ |
| KI-401 | Research files of mixed validity | Docs integrity | 🟢 |
| KI-402 | Config contradictions (`.env.example` vs guidelines) | Docs integrity | 🟢 |
| KI-403 | Old README: fake quick start, sample output, missing files | Docs integrity | 🟢 |
| KI-501 | Cloudflare token scopes and tunnel config | Infrastructure | 🟡 |
| KI-502 | Single server; this host is production | Infrastructure | 🟢 |
| KI-503 | No license; repository is private | Infrastructure | 🟡 |
| KI-504 | Tunnel live; API token lacks Tunnel/R2 rights; no off-site backup | Infrastructure | 🟡 |
| KI-505 | Public VPN relay is untrusted and flaky | Infrastructure | 🟡 |
| KI-506 | `autobahn.bot` zone challenges non-browser clients (new main domain) | Infrastructure | 🟡 |
| KI-507 | User feedback can be wrong or manipulated | Data quality | 🟡 |
| KI-307 | Point check is not a depth or level at the pin | Modelling | ℹ️ |
| KI-508 | Workers AI quota, outages and wording drift | Infrastructure | 🟢 (mitigated) |

---

## 1. Data access

### KI-101 — Geo/datacenter IP blocking · 🟡
**Probe (2026-09-26, from Germany):** HII `api-v3` and `tiwrm` work. **All BMA hosts** (`dds.bangkok.go.th`, `weather.bangkok.go.th`) reset the connection, and `www.bangkok.go.th` returns 403. `ews.dwr.go.th` timed out. The earlier claim that HII returns 403 to foreign datacenters is **not** supported. That 403 came from a sandbox with restricted egress.
**Update 2026-09-26 (D-016):** a Thai VPN egress was tested. Exit 49.48.220.198 (Ayutthaya, TH). **Opens from it:** `ews.dwr.go.th` (timed out from DE), `hydro.navy.mi.th` (bot wall from DE), `dds.bangkok.go.th`. **Still blocked:** `weather.bangkok.go.th` returns an IIS 403 even with a browser User-Agent → an IP-class block on that relay. It's not being evaded; get an owner-controlled Thai host instead.
**Workaround:**
- Run the collectors from the production VPS in Singapore or Thailand, and **re-test everything there** (Phase 0).
- If BMA still blocks the VPS, use a **small collector node on a Thai IP**, as the brief suggests, and **ask BMA for access**.
- **Do not** spoof browser User-Agents or rotate proxies to get around blocks ([GUIDELINES §5](GUIDELINES.md)).

### KI-102 — Navy tide tables · 🔴
**Symptom:** `www.hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf` redirects to `hydro.navy.mi.th/…`, which returns **404**. The site is behind a Cloudflare bot challenge, so scripts can't fetch it. The tables are referenced to **LLW**, not MSL.
**Workaround:**
- Find the current PDF by hand in a browser and archive it once a year. Parse it with `pdfplumber` into `tide_prediction` (LLW and MSL).
- **Interim / fallback:** fit our own harmonic model on HII tidal stations. A 4-constituent fit on 30 days at CPY015 already explains 92 % of the tidal variance. Use `utide` with ≥1 year of data for production ([APPROACH §5](APPROACH_AND_METHODS.md)).

### KI-103 — BMA DDS has no API and isn't mirrored in HII · 🔴
**Symptom:** the older claim that "many BMA stations are aggregated by HII under agency bma" is **wrong**. HII `waterlevel_load` has no BMA-agency rows. The `BKKxxx` codes are HII's own stations. The BMA portals are legacy web pages, blocked from outside Thailand.
**Workaround:**
- Use HII's Bangkok stations first (BKK008, BKK021, AIT001, BKK001–BKK020, C.12, CPY014, CPY015).
- From a Thai IP, capture the DDS XHR calls and pages (`StationDetailFlow?id=`, canal lists).
- Scrape politely: one call per cycle, with a circuit breaker (after 3 failures, switch to degraded mode).
- Ask BMA for an official feed.

### KI-104 — Short history retention at sources · 🟡
The HII exchange standard only guarantees **7 days** 🟡. The chart XHR `getGraphFirst` returns **~30 days** ✅.
**Workaround:** **start the raw archive and the backfill right after G0.** Loop `getGraph` ranges back as far as allowed. Add GloFAS 1984→, data.go.th CSV, DWR/ONWR PDFs and RID yearbooks.

### KI-105 — CORS · 🟢 (corrected)
Earlier docs said Thai endpoints never allow browser calls. **Probe:**
- HII `api-v3` **echoes the Origin** (with credentials allowed).
- Traffy and Open-Meteo send `*`.
- Only the `tiwrm` chart XHR has no CORS headers.

The design is unchanged: **the browser only calls our API** (D-001). The reasons are the archive, caching that protects HII, degraded mode and consistent data, not CORS.

### KI-106 — Open-Meteo free tier is non-commercial · ℹ️
Free and keyless for **non-commercial** use (about 10k calls a day ⚠️; re-check the terms). If the app is ever monetised, switch to a paid plan. FABDEM is also non-commercial.

### KI-107 — Traffy data: privacy and meaning · 🟡
`publicapi.traffy.in.th` returns citizens' free text, photos and exact coordinates. **Rules:**
- Store only ticket ID, coordinates, time, state and a flood flag.
- **Never republish photos or text.**
- Aggregate spatially (e.g. counts per 500 m cell).
- Ask BMA/NECTEC before public use.

The report timestamp is **when someone reported**, not when the water peaked, so use it for validation only.

### KI-108 — Large, slow HII payloads · 🟡
`waterlevel_load` is ~1.4 MB and takes ~9 s; `rain_24h` is several MB and took >60 s (from Germany). **Workaround:** `Accept-Encoding: gzip`, timeouts ≥120 s, one call per cycle, and **never** on the user request path.

### KI-109 — Key stations missing from HII · 🔴
C.29A (Bang Sai), Memorial Bridge / Pak Khlong Talat (C.4 or C.22 ⚠️) and Fort Phra Chulachomklao are **not** in `waterlevel_load`. **Update 2026-09-26:** the HII chart station lists do contain **CPY013 บางไทร** and **GLF001 ป้อมพระจุลจอมเกล้า** (Fort Chula), but their chart data answers HTTP 500 ([KI-207](#ki-207--chart-only-stations--)).
**Workaround:** find RID and Navy feeds in Phase 0. In the meantime, estimate Bang Sai from C.35 + S.26 with routing, and use CPY015 / C.12 as the Bangkok river references.

---

### KI-207 — Chart-only stations · 🟡
**Found 2026-09-26 (owner report "many stations are missing").** The HII chart site (`tiwrm.hii.or.th`) serves stations that `waterlevel_load` doesn't: **162 candidates** in 18 nearby provinces at first count (Bangkok: BKK004, BKK007, BKK011, BKK012, …; Ayutthaya, Chai Nat, Nakhon Sawan: many `ATG*`, `MOU*`, …).
- **Fixed (D-015):** the `hii_stations` collector added **34** of them, so the focus set went **69 → 104**, and to **100** after the 4 `TEST*` gauges were removed (KI-209). At 09:40 UTC: 30 without coordinates, 26 without a bank level.
- **Still open:**
  - **56 candidates return HTTP 500** from `getGraphFirst` (stable across retries) or contain only `999999`. They include **GLF001 ป้อมพระจุลจอมเกล้า (Fort Chula tide gauge, latest 0.03)**, **CPY013 บางไทร (Bang Sai, latest 1.46)**, BKK004, BKC001 and FROC01. **Workarounds tested 2026-09-26 ~09:05 UTC, both fail:**
    - The chart page's `POST /getGraph` (form `province_name`, `station` + CSRF `_token` + session cookie) returns only the *latest* point for working stations (BKK021 → `[1790413200000, 2.811, 2.2, -0.33, …]`) and **HTTP 500 for GLF001 and CPY013**.
    - `queryStation`'s `water1` has no timestamp, and for GLF001 it read **0.03 m at 08:30 and at 09:04 UTC**. A tide gauge doesn't stay flat for 35 minutes, so the value is frozen; not ingested.
    - **Remaining routes:** Navy/HII direct contact (Q17), or the RID/Navy Fort Chula series if published elsewhere.
  - Known-500 codes are now retried **once a day** instead of three times on every 6 h run (`collector_state.hii_chart_unavailable`).
  - **34 focus stations had no coordinates** (the map feed covers only ~110 stations). **2026-09-26 (D-023):** the map feed now also fills existing stations, which fixed BKK008. **29 remain** (all absent from the feed): ATG011 ATG021 ATG031 ATG032 ATG042 ATG051 ATG052 ATG081 ATG082 ATG091 ATG092 ATG101 ATG111 ATG112 ATG122 ATG151 ATG152 ATG161 ATG162 ATG171 ATG181 ATG182 BKC006 FROC02 HDA001 HDA002 HDA003 TBW014 TCP013. Most are Ayutthaya gate pairs (upstream/downstream, e.g. ATG081/082 at ปตร.พระธรรมราชา), so geocoding the gate name (OSM) is the likely fix, flagged as approximate.
  - **28 focus stations have no bank level** → status "unknown", no recovery estimate.
  - Chart placeholders `bank=0, ground=0` mean *unknown* (now treated as such).
- **Not the cause:** BKK021 was already served (the owner's example page); it is critical (2.82 m vs bank 2.20).

## 2. Data quality and datums

### KI-201 — Datum mixing; LLW offsets unknown · 🔴
Sources mix MSL (Ko Lak), LLW (Navy), gauge zero (`waterlevel_m`, BMA) and EGM2008 (DEMs). The LLW→MSL offsets that used to be in these docs (−1.55 / −1.35 / −1.25 m) **had no source** and were removed.
**Workaround:**
- Keep one conversion table per station, with source and effective date.
- Use HII `min_bank` / `ground_level` as MSL anchors.
- Unit-test every conversion ([tests/](../tests/README.md)).
- Consider **land subsidence** when comparing across years.

### KI-202 — DEM vertical error ≫ flood depth · ℹ️
Global DEMs have ≥1 m RMSE in flat, built-up Bangkok 🟡, while street floods are 10–50 cm. **Probe:** Open-Meteo elevation returned 4 m (Memorial Bridge) and 7 m (Udom Suk), far above the true ~0–2 m MSL. The DEMs are on **EGM2008**, not ellipsoidal heights.
**Workaround:**
- Report depth as **P(d > 0) = Φ((H_ws − z_g)/σ)** in categories.
- Use HAND (height above nearest drainage) and the controlling water body.
- Let the satellite flood extent override.
- Let users enter their floor or ground height.
- Ask GISTDA, BMA or RTSD for survey or LiDAR data.

### KI-203 — Station code and metadata ambiguity · 🔴
- Memorial Bridge is **C.4** in the literature but **C.22** in the older docs.
- RID uses **C.29A** for Bang Sai.
- The C.13 bank level appears as 17.21, 15.77 and (HII) **16.34**.
- The older docs had BKK021 as "วัดลาดพร้าว", bank 1.10. HII says **วัดบางบัว, bank 2.20**.
- The older docs had BKK008's bank at 1.20. HII says **0.88**.

**Workaround:** HII metadata is the operational reference. Store where each value came from, version it, and confirm with RID.

### KI-204 — Duplicate stations across agencies · 🟡
The same physical site can appear under several agencies or IDs within ~100 m. **Workaround:** de-duplicate by distance < 100 m plus a name/code match. Prefer the record that has a bank level and the latest timestamp ([sources_survey §3.1](../research/sources_survey.md)).

### KI-205 — Mixed timestamp conventions · 🟡
| Source | Convention |
|---|---|
| HII `waterlevel_datetime` | Local time **without TZ** → treat as +07:00 |
| HII chart epoch | True UTC |
| Traffy `timestamp` | UTC |
| Open-Meteo | Whatever `timezone=` you request |

Store UTC and display Asia/Bangkok. Never use naive `datetime.now()`.

### KI-206 — Sentinel values, stale stations, spikes · 🟡
- HII chart data uses **`999999`** for missing or bad values (51 of 727 rows at CPY015).
- Some stations are stale for days (e.g. BKC004).
- Spikes and flatlines occur.

**Workaround:** QC flags (sentinel, range, rate of change, flatline, neighbour-consistency check) and per-station data age in every API response. Flag readings; never delete them.
- **Done 2026-09-26:** a reading older than **24 h** is shown with status **"unknown"** (value kept, marked stale), so it no longer counts as "ล้นตลิ่ง". Seen: TEST02 at +4.6 m above its bank with an 11-day-old reading was ranked first.

### KI-208 — HII `ground_level` at river gauges is the channel bed · ℹ️
`ground_level` is the **bed of the channel**, not the land around the gauge. Examples: CPY015 −15.70, C.12 −14.52, CPY014 −13.31 m MSL. It is correct for the status percentage (depth relative to bank depth). It **must not** be used as terrain or to interpolate a land surface ([APPROACH §2.9](APPROACH_AND_METHODS.md)).

### KI-210 — GLF002 (Tha Chin mouth) values are not m MSL · 🔴 (excluded)
`getGraphFirst/GLF002` serves 4,410 values over 30 days with a **median of 5.53 m, a maximum of 7.40 m and spikes to −28.59 m**. The map feed's latest was 6.816. At a river mouth, MSL values should be around 0–2 m (CPY015 over the same period: −0.94 to 1.58, median 0.44). So the series is on another datum (LLW or gauge zero, KI-201), with bad spikes. **Excluded** via `DATUM_SUSPECT` in `config.py`: not collected, not shown. It would be a valuable tide reference for the western side once HII confirms its datum offset. Same gauge family as GLF001 (Fort Chula, HTTP 500).

### KI-209 — HII test gauges in station lists · 🟢
`queryStation` lists test gauges (`TEST02` and three more `TEST*` codes in Bangkok). **Fixed:** `hii_stations` skips `TEST*`, the API filters them out, and the 4 existing rows were set to `in_focus=false`.

---

## 3. Modelling

### KI-301 — Placeholder tide constants · 🟢 (don't use)
Two draft constant sets were validated against 30 days observed at CPY015:
- **Draft A** (the old docs' JS): correlation **−0.74** (inverted).
- **Draft B** (the engine): **+0.12**.
- A simple fit to the data: **+0.96**.

Root cause: the phases were used without the astronomical argument **V₀+u** and nodal factor **f**. **Resolution:** fit our own constants (`utide`) or use the Navy tables. Never hard-code constants copied from a document.

### KI-302 — Draft `BKKHydroEngine` · 🟢 (don't port)
Running it gives:
- river 3.40 m (above the 3.0 m wall)
- khlong −1.25 m (unbounded pumping)
- an ETA that goes **earlier** as the water gets deeper
- output that doesn't match the "sample" the old README published

Its equations are a useful reference; its implementation and parameters are not ([validation §C](../research/VALIDATION_2026-09-26.md)).

### KI-303 — Managed operations make the system non-stationary · ℹ️
Dam releases, diversions, gate closures and pump outages change the system abruptly. **Workaround:**
- Store announced operations as events and scenario inputs ("ตามแผนการระบายน้ำของกรมชลประทาน X ลบ.ม./วินาที").
- Add event flags as ML features.
- AR error fading.
- Adaptive conformal calibration ([APPROACH §11](APPROACH_AND_METHODS.md)).

### KI-304 — Unsourced street-elevation benchmarks · 🔴
The `bkk_stations_elevation.json` values in [API_noKey-1.md](../research/API_noKey-1.md) and the "hotspot road elevation" table in the old KNOWLEDGE.md have **no source**. They were removed from the docs. Replace them with survey data or DEM-with-uncertainty in Phase 2/3.

### KI-305 — No archive of as-issued forecasts yet · 🔴
Training on observed future rain ("perfect prognosis") overstates skill. **Workaround:** archive **every** Open-Meteo run from day one of Phase 1. Until enough runs exist, train on observed rain but **widen the intervals** and state this on the model page.

### KI-306 — Spatial and temporal scale mismatch · ℹ️
| Source | Scale |
|---|---|
| Gauges | Points, 10-min |
| NWP | 9–25 km grids, hourly |
| GloFAS | 5 km, daily |
| DEMs | 30–90 m |
| Traffy | Points, irregular |
| Navy tide | A few stations, hourly |

Naive nearest-point joins create bias. **Workaround:** explicit aggregation and downscaling rules per variable, polder-level rainfall aggregation, and resampling rules ([APPROACH §2](APPROACH_AND_METHODS.md)).

---

## 4. Documentation integrity

### KI-401 — Research files of mixed validity · 🟢
Three research files (Gemini / claude.ai) mixed useful ideas with refuted endpoints and constants. **Resolved (2026-09-26):** every file was validated claim by claim ([VALIDATION](../research/VALIDATION_2026-09-26.md)), given validity banners, and only ✅/💡 items went into `docs/` (D-003).

### KI-402 — Config contradictions · 🟢
The old `.env.example` used SQLite and `HOST=0.0.0.0`, while GUIDELINES said TimescaleDB and 127.0.0.1. **Resolved:** `.env.example` is aligned with [ARCHITECTURE](ARCHITECTURE.md). If your local `.env` was copied from the old template, check `HOST`, `DATABASE_URL`, `CORS_ORIGIN` and the TMD keys.

### KI-403 — Old README problems · 🟢
The old README had:
- a quick start that ran `python3 file.md`
- a sample output that the code never produced
- a `docker compose` command with no compose file
- a license badge with no LICENSE file
- a "Live Deployment" badge with no app deployed

**Resolved:** the README was rewritten with an honest status.

---

## 5. Infrastructure

### KI-501 — Cloudflare token scopes and tunnel config · 🟡
The API token needs: Account → Cloudflare Tunnel: Edit, Workers/Pages: Edit; Zone → DNS: Edit, Cache Purge: Purge. The VPS never exposes 80/443. `cloudflared` routes `flood.bejranonda.com` to `http://127.0.0.1:${PORT}`. The live tunnel's configuration **isn't in this repo yet** (Phase 1/4 → `infra/`).

### KI-502 — Single server (resolved: this host *is* production) · 🟢
This repo's working host (`HZ-Agent`) is in **Germany**, with 4 vCPU, 7 GB RAM, **~11 GB free disk** and no `cloudflared`. That isn't enough to hold the archive, and it is blocked by BMA. **Phase 0 tests must run on the production VPS** (region and specs in [OPEN_QUESTIONS](plan/OPEN_QUESTIONS.md)).

### KI-503 — No license; repository is private · 🟡
The GitHub repo `bejranonda/flood2026` was created **private** (D-011), and there is no LICENSE file, so all rights are reserved by default. The old README's MIT badge was removed because no license had been chosen. **Before going public:** the owner picks a license ([OPEN_QUESTIONS Q10](plan/OPEN_QUESTIONS.md)), a fresh secrets scan of the full history runs, and permissions from HII, BMA and Traffy are considered (Q3). Third-party data keeps its own terms regardless of the code license ([SOURCES §7](SOURCES.md)).

> **Update 2026-09-26 (KI-502):** the owner confirmed there is only one server, so this host is production (D-013). The remaining risks are disk space (~13 GB free, shared with other projects) and BMA blocking the German IP (D-014).

### KI-504 — Tunnel live; API token lacks Tunnel/R2 rights; no off-site backup · 🟡
- **Done:** the Cloudflare Tunnel is running (`cloudflared` container, `--url http://app:3000`), the DNS record is a proxied CNAME to the tunnel, ports 80/443 are closed and the Caddy origin is retired. Verified 2026-09-26.
- **Open:** the `CLOUDFLARE_API_TOKEN` in `.env` is *active* but **can't manage the tunnel** (get-by-id → "Not authorized") and **R2 returns HTTP 403**, although the owner reported adding both permissions. Either a different token was edited, or `.env` still holds the old value.
- **R2 also needs S3 API credentials** (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`), separate from the API token, and neither exists yet → the raw archive and DB are **only on this disk**.
- **Fixed:** `CLOUDFLARE_ACCOUNT_ID` in `.env` belonged to another account; the zone and tunnel token belong to account `6914a3…1a45` (corrected).
- **Legacy:** `infra/Caddyfile` and the `caddy` service (profile `origin`) are no longer used.
- **2026-09-26 09:19 UTC:** the owner replaced `CLOUDFLARE_TUNNEL_TOKEN`. The new token runs tunnel `d62b426d…`, and the old `ecd8a7b9…` stopped. `flood.bejranonda.com` briefly returned **HTTP 530** until both CNAMEs were re-pointed to the new tunnel (the API token has DNS edit on both zones). **Lesson:** when the tunnel token changes, update every CNAME that targets `<old-id>.cfargotunnel.com` in the same step.

### KI-505 — Public VPN relay is untrusted and flaky · 🟡
The Thai egress uses a VPN Gate volunteer relay ([D-016](plan/DECISIONS.md)). Risks: the operator can see destinations and unencrypted metadata; the relay can drop or throttle (it needed one restart during testing); its IP class is blocked by some sites; legacy AES-128-CBC/SHA1. **Mitigations:** the proxy is opt-in per request; HTTPS certificates are verified; no credentials or personal data go through it; a watchdog restarts the tunnel; the `.ovpn` is git-ignored. **Better:** an owner-controlled Thai host (SSH SOCKS) or a paid VPN with a Thai exit.
- 2026-09-26 ~09:30 UTC: the exit IP was up (49.48.220.198), but `dds.bangkok.go.th` **timed out** through it; `bma_dds` had 2 consecutive proxy failures ("Tunnel connection failed: 500"). Treat BMA collection as best-effort until a better Thai egress exists.

### KI-506 — `autobahn.bot` zone challenges non-browser clients · 🟡
The new main domain `flood.autobahn.bot` (proxied CNAME → tunnel, created 2026-09-26) answers **HTTP 403 "Just a moment…"** to `curl` and to headless Chrome. **Every** proxied host in the `autobahn.bot` zone does the same (`autobahn.bot`, `www`), so it is a zone-wide security setting (Bot Fight Mode, Security Level or a WAF rule). The API token can't read it (`Authentication error` on `bot_management` and rulesets).
- **Impact:**
  - People on phones probably pass after a short interstitial.
  - **Link previews** (LINE, Facebook), API users, uptime monitors and search engines are **blocked**.
  - A flood site must load instantly on slow phones.
- **Fix (owner, dashboard):** for `flood.autobahn.bot`, add a Configuration Rule "Security Level: Essentially Off" and a WAF skip for managed challenges, or turn off Bot Fight Mode for the zone. Bot Fight Mode can't be skipped per host on the Free plan.
- **Until then:** `flood.bejranonda.com` stays a full alias (same tunnel, no redirect), and the page declares `rel=canonical` → `flood.autobahn.bot`.

### KI-507 — User feedback can be wrong or manipulated · 🟡
Feedback (`/api/feedback`, [APPROACH §3.5](APPROACH_AND_METHODS.md)) is subjective and position-dependent: people report their own street, not the gauge. It is also open to brigading.
- **Mitigations:**
  - rate limit of 10 per hour per daily-salted IP hash, plus a honeypot field;
  - a server-side snapshot of what was shown;
  - counts only in public, notes never published;
  - the `review` flag drives **human review, never an automatic model change**.
- **Open:** no moderation UI yet; operators read `user_feedback` in SQL.

### KI-307 — Point check is not a depth or level at the pin · ℹ️
`/api/point` summarises gauges *around* a pin as a status category (D-021). It can't know the ground height, drains, walls or polder of the pin itself: Bangkok is not flat (KI-202, [APPROACH §2.10](APPROACH_AND_METHODS.md)).
- **Mitigations:** confidence is never "high"; at very low confidence no verdict is shown; four warnings are always visible; citizen reports near the pin are shown.
- **Fix path:** polder polygons → controlling gauge; FABDEM + σ → probability categories calibrated with user depth reports.

### KI-508 — Workers AI quota, outages and wording drift · 🟢 (mitigated)
- The free allocation is 10,000 neurons/day. When exhausted, Workers AI returns error 3036 (HTTP 429) until 00:00 UTC.
- **Mitigations:**
  - AI is used only in the worker (`ai_triage`, D-022);
  - a daily budget (3,000) and a circuit breaker (3 failures → 1 h; 3036 → until 00:05 UTC);
  - rule labels always exist.
  - Tested 2026-09-26: budget 0 and an invalid token both leave the site unaffected (HTTP 200).
- **Wording drift:** tested models mislabelled warning levels in free-text summaries, so AI writes no status text.
- **Token scope:** the fallback token also has DNS rights. Use a dedicated `CF_AI_TOKEN` (Q21).
