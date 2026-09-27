# KNOWN_ISSUES.md — Limitations, pitfalls and workarounds

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-09-27
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
| KI-109 | Key stations missing from HII (C.29A, Memorial Bridge, Fort Chula) | Data access | 🔴 (Fort Chula tide *predictions* found in HII FEWS, 2026-09-27) |
| KI-110 | DWR EWS and RID Telerid answer only from a Thai IP; DWR status `9` on a third of stations; Buddhist-year dates | Data access | 🟡 (Thai egress; not collected yet) |
| KI-112 | HII FEWS forecast files: overwritten each issue; pre-issue part equals observations; C.13 held constant; discharge > 1000 dropped by a sentinel rule | Data quality | 🟡 archived + scored (D-050); sentinel fixed |
| KI-111 | HII national feeds mix fresh and long-dead rows (gates 12/2,315 fresh; 1970 placeholders) | Data quality | 🟡 (freshness filter required) |
| KI-207 | Chart-only stations: missing from the main feed, HTTP 500, no coordinates or bank | Data access | 🟡 |
| KI-201 | Datum mixing (MSL / LLW / gauge zero / EGM2008); LLW offsets unknown | Data quality | 🔴 |
| KI-202 | DEM vertical error ≫ flood depth | Data quality | ℹ️ |
| KI-203 | Station code and metadata ambiguity | Data quality | 🔴 |
| KI-204 | Duplicate stations across agencies | Data quality | 🟡 |
| KI-205 | Mixed timestamp conventions | Data quality | 🟡 |
| KI-206 | Sentinel values, stale stations, spikes | Data quality | 🟡 |
| KI-208 | HII `ground_level` at river gauges is the channel bed, not land | Data quality | ℹ️ |
| KI-209 | HII test gauges (`TEST*`) appear in station lists | Data quality | 🟢 |
| KI-210 | GLF002 (Tha Chin mouth) values are not m MSL | Data quality | 🟡 (shown, values hidden) |
| KI-211 | Implausible readings far above bank (sensor ceiling, spikes) | Data quality | 🟢 (flagged) |
| KI-215 | BMA `warning`/`critical` are operating levels, not banks | Data quality | 🟢 used as drainage levels, never as bank (D-038) |
| KI-216 | A freeboard of −0.4 cm displayed as "0 cm below the bank" next to "overflowing" | UI | 🟢 fixed |
| KI-217 | BMA and HII gauges 7–100 m apart disagree by 0.3–0.6 m (level and bank) | Data quality | 🟡 open (handled: never mixed) |
| KI-218 | BMA data depends on a third-party political relay | Data access | 🟡 accepted (D-031); HII serves the same BMA canals (validated 2026-09-27, D-045) |
| KI-219 | BMA codes sent to HII's chart endpoint stalled the worker ~1 h | Infrastructure | 🟢 fixed v0.3.2 |
| KI-220 | Canal "normal" next to flooded streets read as a contradiction; Traffy overloaded | UX / Data access | 🟢 relabelled (D-036); 🟡 Traffy down |
| KI-221 | Favicon unrecognizable at 16×16 and blends into dark-mode browser tabs | UI / Brand | 🟢 redesigned with Flood Droplet & Wave (D-039) |
| KI-222 | Point check lacked localized 12–24h forecast summary; static BMA portal link was misleading | UX / Product | 🟢 resolved in v0.6.0 (D-040, D-041) |
| KI-223 | D-041 outlook gave a canal verdict with zero or far/disagreeing gauges; contradicted the overview card | UX / Product | 🟢 fixed v0.6.1 (D-042) |
| KI-224 | "~27 มม." read as "−27 มม."; rain amount had no meaning (issue #1) | UI | 🟢 fixed on branch (TMD categories) |
| KI-232 | Nearest canal had no forecast (relay-only BMA gauge), so the panel showed no trend at all; summary wording not understood | UX / Product | 🟢 fixed v0.10.2 (D-054 amended) |
| KI-229 | Canal factor said "ประเมินไม่ได้" at 83 % of Bangkok pins (8 km agreement rule) | UX / Product | 🟢 fixed v0.10.0 (D-054: 39 %) |
| KI-230 | BMA gauges had no forecast (≈ 28 h of history) | Modelling | 🟢 v0.10.0: 1-year backfill from HII (D-054) |
| KI-231 | Recovery window printed to the minute over days ("01:12 – 05:12") | UX | 🟢 fixed v0.10.0 (D-055) |
| KI-227 | "Nearest canal" fallback showed a river gauge (CPY015, tide) at very low confidence | UX / Product | 🟢 fixed v0.7.0 (D-051) |
| KI-228 | Tapping ⓘ inside a list item opened the station instead of the tip | UI | 🟢 fixed v0.7.0 |
| KI-225 | Literal delta interval "ลด 11 ถึงเพิ่ม 17 ซม." and "มั่นใจต่ำ" caused citizen confusion | UX / Product | 🟢 fixed v0.6.4 (D-048) |
| KI-301 | Placeholder tide constants (inverted phase) | Modelling | 🟢 (don't use; fit our own) |
| KI-302 | Draft `BKKHydroEngine` gives implausible output | Modelling | 🟢 (don't port) |
| KI-303 | Managed operations make the system non-stationary | Modelling | ℹ️ |
| KI-304 | Unsourced street-elevation benchmarks | Modelling | 🔴 |
| KI-305 | No archive of as-issued forecasts yet (perfect-prognosis risk) | Modelling | 🔴 |
| KI-306 | Spatial and temporal scale mismatch between data sources | Modelling | ℹ️ |
| KI-401 | Research files of mixed validity | Docs integrity | 🟢 |
| KI-402 | Config contradictions (`.env.example` vs guidelines) | Docs integrity | 🟢 |
| KI-403 | Old README: fake quick start, sample output, missing files | Docs integrity | 🟢 |
| KI-404 | Research_Thailand.md: refuted host, invented numbers, rule-breaking methods | Docs integrity | 🟢 (banner; not used as a source) |
| KI-501 | Cloudflare token scopes and tunnel config | Infrastructure | 🟡 |
| KI-502 | Single server; this host is production | Infrastructure | 🟢 |
| KI-503 | Open source license (MIT) | Infrastructure | 🟢 (resolved: MIT License added, D-043) |
| KI-504 | R2 off-site backup | Infrastructure | 🟢 (kept disabled by owner choice, D-029) |
| KI-505 | Public VPN relay is untrusted and flaky | Infrastructure | 🟡 |
| KI-506 | `autobahn.bot` zone challenged non-browser clients (Bot Fight Mode) | Infrastructure | 🟢 fixed 2026-09-26 (owner, D-035) |
| KI-507 | User feedback can be wrong or manipulated | Data quality | 🟡 |
| KI-212 | A worker restart reset the schedule, so the backfill never advanced | Infrastructure | 🟢 (fixed v0.2.1) |
| KI-213 | A slow-failing upstream steals the single worker loop (Traffy HTTP 502) | Infrastructure | 🟢 (mitigated v0.2.1) |
| KI-214 | Public repository: what history reveals; SSH exposure of the host | Infrastructure | 🟡 |
| KI-307 | Point check is not a depth or level at the pin | Modelling | ℹ️ |
| KI-508 | AI triage provider (GLM / Workers AI) | Infrastructure | 🟢 (GLM live verified, D-030) |
| KI-509 | A GloFAS point query can hit a side cell (Nong Khai 3 vs ~9,000 m³/s) | Data quality | 🟡 (snap rule, APPROACH §19.5) |
| KI-510 | GISTDA answered 404 (outdated path, key sent as a query parameter) while `owner_status.py` showed ✅ | Infrastructure | 🟢 fixed 2026-09-27 (documented API; real check in the script) |
| KI-512 | Access logs kept place-search text and point coordinates (D-032 breach) | Privacy | 🟢 fixed v0.7.0 (redaction filter) |
| KI-511 | No database backup at all; disk 84 % full (12 GB free, shared host) | Infrastructure | 🔴 risk accepted by the owner for now (Q29, 2026-09-27) |

---

## 1. Data access

### KI-101 — Geo/datacenter IP blocking · 🟡
**Probe (2026-09-26, from Germany):** HII `api-v3` and `tiwrm` work. **All BMA hosts** (`dds.bangkok.go.th`, `weather.bangkok.go.th`) reset the connection, and `www.bangkok.go.th` returns 403. `ews.dwr.go.th` timed out. The earlier claim that HII returns 403 to foreign datacenters is **not** supported. That 403 came from a sandbox with restricted egress.
**Update 2026-09-26 (D-016):** a Thai VPN egress was tested. Exit: a VPN Gate relay in Ayutthaya, TH. **Opens from it:** `ews.dwr.go.th` (timed out from DE), `hydro.navy.mi.th` (bot wall from DE), `dds.bangkok.go.th`. **Still blocked:** `weather.bangkok.go.th` returns an IIS 403 even with a browser User-Agent → an IP-class block on that relay. It's not being evaded; get an owner-controlled Thai host instead.
**Workaround:**
- Run the collectors from the production VPS in Singapore or Thailand, and **re-test everything there** (Phase 0).
- If BMA still blocks the VPS, use a **small collector node on a Thai IP**, as the brief suggests, and **ask BMA for access**.
- **Do not** spoof browser User-Agents or rotate proxies to get around blocks ([GUIDELINES §5](GUIDELINES.md)).

### KI-102 — Navy tide tables · 🔴
**Symptom:** `www.hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf` redirects to `hydro.navy.mi.th/…`, which returns **404**. The site is behind a Cloudflare bot challenge, so scripts can't fetch it. The tables are referenced to **LLW**, not MSL.
**Workaround:**
- Find the current PDF by hand in a browser and archive it once a year. Parse it with `pdfplumber` into `tide_prediction` (LLW and MSL).
- **Interim / fallback:** fit our own harmonic model on HII tidal stations. A 4-constituent fit on 30 days at CPY015 already explains 92 % of the tidal variance. Use `utide` with ≥1 year of data for production ([APPROACH §5](APPROACH_AND_METHODS.md)).

### KI-103 — BMA DDS has no API and isn't mirrored in HII · 🟢 (resolved via BKK mapping + relay)
**Symptom:** BMA's internal site (`weather.bangkok.go.th` / `dds.bangkok.go.th`) has no open historical API and blocks foreign datacenters as well as public VPN relays (KI-505). HII's `waterlevel_load` has no BMA-agency rows.
**Resolution (v0.3.0 + v0.9.0, D-031, D-053):**
- **Live snapshots (199 stations):** Ingested every 5 min via the People's Party relay (`bma_klong`, `flood69.peoplesparty.or.th/api/klongmap`). Codes are `WL.xxx.nn` (e.g. `WL.KTY.01` ส.คลองเตย, `WL.AJP.01` ค.อาจารย์พร, `WL.BKY.02` ค.บางเชือกหนัง).
- **30-day historical telemetering:** For key Bangkok canals (Khlong Lat Phrao, Khlong Saen Saep, Khlong Phasi Charoen, Khlong Lam Pla Thio, etc.), HII operates parallel telemetry stations under the `BKKxxx` series (`BKK001`, `BKK008`, `BKK020`, `BKK021`, etc.). HII exposes **30 full days of 10-minute resolution history** without geo-blocking via `GET https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}` (4,300+ points per station).
- **Cross-reference mapping:**
  - `BKK001` (คลองลาดพร้าว ท้าย ปตร.คลอง 2) ↔ `WL.SST.01` (60 m away) / `WL.KLA.01` reach.
  - `BKK020` (คลองลาดพร้าว ปากคลอง 2 สายใต้) ↔ `WL.ANX.01`.
  - `BKK021` (คลองลาดพร้าว วัดบางบัว) ↔ `WL.BBU.01` / `WL.LPW.01`.
  - `BKK008` (คลองแสนแสบ บางกะปิ) ↔ `WL.SSB.06` (80 m away) / `WL.SSB.07`.
  - `BKK005` (คลองภาษีเจริญ เพชรเกษม 69) ↔ `WL.TWW.05` (20 m away).
  - `BKK009` (คลองลำปลาทิว ลาดกระบัง) ↔ `WL.LPT.03` (10 m away).

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
  - **34 focus stations had no coordinates** (the map feed covers only ~110 stations). **2026-09-26 (D-023):** the map feed now also fills existing stations, which fixed BKK008. **29 remain** (all absent from the feed): ATG011 ATG021 ATG031 ATG032 ATG042 ATG051 ATG052 ATG081 ATG082 ATG091 ATG092 ATG101 ATG111 ATG112 ATG122 ATG151 ATG152 ATG161 ATG162 ATG171 ATG181 ATG182 BKC006 FROC02 HDA001 HDA002 HDA003 TBW014 TCP013. Most are Ayutthaya gate pairs (upstream/downstream, e.g. ATG081/082 at ปตร.พระธรรมราชา).
    - **2026-09-26 (D-024):** Nominatim found none of the gate names. An Overpass name search matched **14** to an OSM town, canal, temple or RID office in the right province, now placed **approximately** (±2–5 km, dashed markers, cited in [station_coords_approx.json](../src/floodwatch/data/station_coords_approx.json)).
    - **15 unplaced** (listed, counted on the map): ATG011 ATG042 ATG051 ATG052 ATG081 ATG082 ATG091 ATG092 ATG101 ATG111 ATG112 FROC02 HDA002 HDA003 TCP013. The proper fix is RID's gate coordinates.
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

### KI-210 — GLF002 (Tha Chin mouth) values are not m MSL · 🟡 (shown, values hidden)
`getGraphFirst/GLF002` serves 4,410 values over 30 days with a **median of 5.53 m, a maximum of 7.40 m and spikes to −28.59 m**. The map feed's latest was 6.816. At a river mouth, MSL values should be around 0–2 m (CPY015 over the same period: −0.94 to 1.58, median 0.44). So the series is on another datum (LLW or gauge zero, KI-201), with bad spikes. **Since D-024:** collected and shown on the map with the note "not m MSL"; its level, chart and forecast are hidden (`DATUM_SUSPECT` in `config.py`). It would be a valuable tide reference for the western side once HII confirms its datum offset. Same gauge family as GLF001 (Fort Chula, HTTP 500).

### KI-211 — Implausible readings far above bank · 🟢 (flagged)
BKK003 (คลองมหาสวัสดิ์ บางกรวย-สวนผัก, bank 2.07 m) alternates daily between plausible 0.5–1.9 m and a **flat 7.45 m** (+5.4 m over bank). That is a sensor ceiling or stuck value, not water; HII's own table shows the same 7.453. It was ranked first as "538 cm over bank".
- **Rule (D-024):** a level > **bank + 3 m** is flagged `out_of_range`, using the station's *stored* bank on every insert (the latest-values feed lacks BKK003's bank).
- **Evidence:** over 30 days of all focus gauges, genuine maxima reach +1.90 m (C.67); above +3 m there were only BKK003 (2,798 readings), BKK006 (4 spikes) and CPY012 (3). 3,104 stored readings were re-flagged, not deleted.
- **UI:** the last plausible value is shown, marked stale, with the note "ค่าล่าสุดผิดปกติ … จึงซ่อนไว้".
- **Open:** spikes below the ceiling and stuck values within range (flatline and rate-of-change rules still to add, KI-206).

### KI-215 — BMA `warning`/`critical` are not bank levels (⚠️ hypothesis) · 🟢 handled in v0.3.0
**Update 2026-09-26 (D-038):** tested against street-flood reports: over BMA critical is a much better sign of flooded streets than over the bank (60 % vs 18 % of gauges near flooded streets). Now stored (`critical_msl`, `warning_msl`) and used for BMA status as a *drainage* level; the bank is still the lower bank.
In the BMA KlongMap data (via the flood69 relay, 2026-09-26 16:12 UTC), **84 of 199 stations are at or above `critical`**, yet their banks are far higher: WL.BPM.03 has `critical` 0.70 m, `left_bank` 1.91 m, level 1.10 m. So `critical` looks like BMA's **drainage operating target** (the level at which they run pumps), not overflow. ⚠️ Not confirmed by BMA. **Rule before any BMA use:** status and "cm to the bank" come from `min(left_bank, right_bank)`, never from `critical`. Also unconfirmed: that BMA levels are m MSL; check the five co-located pairs with HII gauges (SOURCES §2c) first. At gates, `wl_in` is inside and `wl_out01` outside; don't mix them.

### KI-217 — BMA and HII disagree at the same place · 🟡
Co-located pairs, latest values on 2026-09-26 ~16:20 UTC:

| Pair (distance) | HII level / bank | BMA level / bank |
|---|---|---|
| BKK008 ↔ WL.SSB.06 Saen Saep (76 m) | 1.15 / 0.88 (27 cm over) | 0.53 / 0.65 (12 cm under) |
| BKK009 ↔ WL.LPT.03 Lam Pla Thio (7 m) | 0.62 / 0.62 (at bank) | 0.96 / 0.50 (46 cm over) |
| BKK005 ↔ WL.TWW.05 (23 m) | **−1.87** / 1.42 | 1.00 / 1.20 |

Datums, sensor placement or bank definitions differ, and HII's BKK005 value itself looks wrong. **Rule (D-031):** never compare, average or interpolate levels across agencies; status is each gauge against its own bank; the point check mixes only status ranks. **Next:** once a week of BMA history exists, compare the pairs' *changes* (not levels) to see whether they are the same water.

### KI-218 — BMA data comes through a third-party relay · 🟡 accepted
`flood69.peoplesparty.or.th/api/klongmap` is run by a political party and has no stated licence. If it changes shape the collector fails loudly (< 50 stations) and keeps the last good data; after 24 h the BMA gauges show "unknown". Mitigations: attribution on every BMA detail, a courtesy note (OWNER_ACTIONS), and BMA direct access if a Thai egress ever works (Q17: none available).

### KI-219 — A new source's stations leaked into another collector's query · 🟢 fixed
`hii_history` selected *all* focus stations. After v0.3.0 added 199 BMA gauges (`WL.*`, no `hii_id`), it asked HII's chart endpoint for each: HTTP 500 with 3 retries ≈ 10 s per code ≈ 33 min, on the single worker loop. Result 16:33–17:46 UTC: no BMA readings, no forecast refresh. The owner saw BMA gauges with near-empty charts and read it as "history and forecasts lost" (nothing was deleted: 3.2 M observations intact, HII gauges kept their year of history). **Fix:** `agency IS DISTINCT FROM 'BMA'` in the query + a regression test. **Rule:** when adding a source, check every collector's and the forecaster's station query (GUIDELINES §3).
**Related:** BMA logger clocks can run a few minutes ahead (WL.KKD.04 stamped 18:00 at 17:55 UTC, so `/api/health` showed a latest-observation age of −4 min). Readings more than 15 min in the future are flagged `future_time` and not shown.

### KI-220 — "Canal normal, street flooded" and a Traffy outage · 🟢 / 🟡
- **Perceived conflict (owner, 2026-09-26):** 34 BMA gauges showed green "ปกติ" with ≥ 5 street-flood reports within 1 km. Both were right: canal vs street (D-036). The word "normal" was the bug. Fixed in v0.4.0: "ต่ำกว่าตลิ่ง" in blue, street reports beside the gauge, a point-check warning.
- **Traffy overload:** `publicapi.traffy.in.th` answered HTTP 502 from 15:11 UTC (limit=500); at 18:10 limit=50 took 51 s and the gateway cuts at 60 s, so even limit=40 got 502. The collector now asks for 40 (lighter); the UI states the street layer's age whenever it is > 60 min. As the outage lasts, the 6 h window empties: "no street reports" then means "no fresh data", which the age note says.

### KI-216 — "0 cm below the bank" next to "overflowing" · 🟢 fixed
BKK009 was at 0.624 m against a 0.620 m bank: the freeboard of −0.4 cm rounded to −0, and `-0 < 0` is false in JavaScript, so the text said "ต่ำกว่าตลิ่ง 0 ซม." under a red "ล้นตลิ่ง" badge. **Fix:** round first; 0 cm reads "ระดับเท่าตลิ่ง".

### KI-221 — Favicon unrecognizable at 16×16 and blends into dark-mode browser tabs · 🟢 fixed (D-039)
- **Problem (owner screenshot, 2026-09-26):** In real browser tabs (16×16 CSS pixels), the original icon was unreadable. Root causes:
  1. The dark navy background (`#0d3b66` to `#061c33`) had zero edge contrast against dark browser tabs (`#202124` / `#1e1e1e`), vanishing completely.
  2. The SVG crammed 6 micro-details (1px border, triple nested drops, 1.8px center beacon dot, 1.5px specular highlight, and 3 side gauge ticks) into 64×64. When scaled to 16×16, these collapsed into a murky, illegible pixel blur.
  3. A narrow droplet left empty space on left and right, making the visible graphic only ~8px wide, and the yellow beacon looked like an ambiguous pyramid/eye.
- **Resolution (D-039):**
  - Redesigned with bold, ultra-simple geometry: vibrant royal blue squircle (`#0284c7` to `#0369a1`) filling the 14×14 area, with ONE bold white wave crest (`#ffffff`) over electric cyan water (`#38bdf8`), directly matching the `🌊` brand.
  - Zero tiny dots, zero rings, zero micro-clutter.
  - 2×2 supersampled pure Python generator in `scripts/generate_favicon.py` outputs `web/favicon.svg`, dual-resolution `web/favicon.ico` (16×16 and 32×32), `web/apple-touch-icon.png` (180×180), and `web/icon-192.png`. Cache-busters bumped to `?v=3`.

### KI-222 — Point check lacked localized 12–24h forecast summary; static BMA link was misleading · 🟢 fixed (D-040, D-041)
- **Problem (owner UX validation, 2026-09-26):**
  1. Clicking a coordinate displayed only current canal status and 24h precipitation, missing an actionable forward-looking synthesis ("Will it flood at my location in the next 12–24 hours?").
  2. The point card included a static link to BMA DDS portal (`dds.bangkok.go.th`) which led to a generic news homepage without specific street flood alerts for the clicked coordinates, creating user confusion.
- **Resolution:**
  1. Implemented `point_forecast()` in `src/floodwatch/point.py` synthesizing channel ML trend, rain forcing, canal capacity, and citizen street reports into a prominent `.forecast-banner` (D-041).
  2. Removed misleading static BMA homepage link; replaced with direct map-guided Traffy status (`🚗 น้ำท่วมบนถนน (1 กม.): มีแจ้ง N จุด (ดูจุดสีม่วงบนแผนที่)`).

### KI-209 — HII test gauges in station lists · 🟢
`queryStation` lists test gauges (`TEST02` and three more `TEST*` codes in Bangkok). **Fixed:** `hii_stations` skips `TEST*`, the API filters them out, and the 4 existing rows were set to `in_focus=false`.

### KI-225 — Literal zero-crossing delta intervals ("ลด X ถึงเพิ่ม Y") confused citizens under steady conditions · 🟢 fixed in v0.6.4 (D-048)
- **Problem (visitor feedback, 2026-09-27):** Conformal delta intervals spanning negative and positive values (e.g. `[-0.11, +0.17] m`) were displayed literally as "น่าจะลด 11 ถึงเพิ่ม 17 ซม.", which read as a bizarre contradiction next to a "ทรงตัว" badge.
- **Resolution:** Replaced with intuitive citizen-friendly wording: `ทรงตัว (อาจแกว่งตัว -11 ถึง +17 ซม.)`.

### KI-226 — Mobile UI line wrapping from verbose confidence labels and uncollapsed metadata · 🟢 fixed in v0.6.5 (D-049)
- **Problem (visitor feedback, 2026-09-27):**
  1. Multi-dot meters (`●○○`) combined with text ("คาดการณ์เบื้องต้น") caused line wrapping on 390px mobile viewports.
  2. Technical surveying elevation in meters above mean sea level (`ม.รทก.`) cluttered the top of the station sheet, distracting citizens from measurement freshness ("15 นาทีที่แล้ว").
  3. The SVG chart's dense 3-line textual legend pushed user survey and feedback controls below the fold.
- **Resolution:**
  1. Replaced verbose meter with a single circular `ⓘ` button (sky-blue `.conf-medium` for tide-calibrated models, slate-gray `.conf-low` for baseline statistical models) with desktop hover tooltip and touch-triggered non-blocking toast on mobile.
  2. Prioritized observation freshness on the main line; tucked raw surveying numbers into an adjacent `[ม.รทก. ⓘ]` button.
  3. Collapsed chart curve definitions into `<details class="chart-legend"><summary>ℹ️ สัญลักษณ์กราฟ</summary>...`.
  4. Moved forecast basis to a top-row button (`อ้างอิงข้อมูล ⓘ`) and canal disclaimer to a label tooltip `ⓘ`.

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

### KI-503 — Open source license added (MIT License) · 🟢 (closed)
The repository was released as open source under the **MIT License** ([LICENSE](../LICENSE), [D-043](plan/DECISIONS.md)) on 2026-09-27 per the owner's request. Free reuse, modification, and integration with attribution is granted. Third-party data keeps its original terms ([SOURCES](SOURCES.md)). Q10 closed.

### KI-504 — Tunnel live; R2 off-site backups kept disabled by owner choice · 🟢 (closed)
- **Done:** the Cloudflare Tunnel runs (`cloudflared`, `--url http://app:3000`); both hostnames are proxied CNAMEs to it; ports 80/443 are closed; the Caddy origin is retired. Verified 2026-09-26.
- **Fixed by the owner (verified 11:15 UTC):** the API token can now manage tunnels, and the old tunnel `ecd8a7b9…` is deleted.
- **Owner decision (2026-09-26, D-029):** the owner chose to **keep R2 disabled** (`keep disable`). Telemetry raw archive (`data/raw_archive`) and Postgres data (`data/pg`) remain stored on the local server disk (13+ GB free). Off-site R2 replication is not required, closing Q15b/Q16.
- **Fixed earlier:** `CLOUDFLARE_ACCOUNT_ID` in `.env` belonged to another account; the zone and tunnel belong to `6914a3…1a45`.
- **Legacy:** `infra/Caddyfile` and the `caddy` service (profile `origin`) are unused.
- **Lesson (tunnel token change, 09:19 UTC):** the old domain returned HTTP 530 until both CNAMEs were re-pointed to the new tunnel. When the token changes, update every CNAME that targets `<old-id>.cfargotunnel.com` in the same step.

### KI-505 — Public VPN relay is untrusted and flaky · 🟡
The Thai egress uses a VPN Gate volunteer relay ([D-016](plan/DECISIONS.md)). Risks: the operator can see destinations and unencrypted metadata; the relay can drop or throttle (it needed one restart during testing); its IP class is blocked by some sites; legacy AES-128-CBC/SHA1. **Mitigations:** the proxy is opt-in per request; HTTPS certificates are verified; no credentials or personal data go through it; a watchdog restarts the tunnel; the `.ovpn` is git-ignored. **Better:** an owner-controlled Thai host (SSH SOCKS) or a paid VPN with a Thai exit.
- **Probe Update (2026-09-27 19:30 UTC, Exit the VPN Gate relay in Ayutthaya, TH):**
  - **Reachable via VPN:** `https://ews.dwr.go.th/` (200 OK) and `https://hydro.navy.mi.th/` (200 OK) — successfully bypasses foreign IP geo-blocks.
  - **Still failing via VPN:** Both `weather.bangkok.go.th` (BMA server) and `dds.bangkok.go.th` (BMA server) time out on ports 80 and 443. Traceroute shows packets are completely dropped at BMA's perimeter firewall subnet BMA server subnet. Tinyproxy returns `500 Unable to connect`.
  - **Resolution (D-053):** Do not rely on BMA direct web pages for historical telemetry. Use HII TIWRM (`getGraphFirst/{BKK_CODE}`) for 30-day high-resolution history and the `bma_klong` relay for 199 live 5-minute snapshot gauges.

### KI-506 — `autobahn.bot` zone challenges non-browser clients · 🟡
**RESOLVED 17:33 UTC (D-035):** the owner turned Bot Fight Mode off; curl, Facebook and LINE user agents get HTTP 200 and the alias now redirects everything, API included. Lesson: page rules and security-level changes could not remove a Bot Fight Mode challenge (tried, no effect).
**Update 2026-09-26 16:58 UTC (D-034):** the owner moved everything to the main domain, so the alias's pages now 301 there; `/api/*` stays on the alias. A headless browser following an old link got the interactive "Verify you are human" checkbox. The token cannot see zone security settings, so the cause (Bot Fight Mode, most likely) can only be checked and switched off in the dashboard.
**17:11–17:15 UTC:** with new token rights (Zone Settings, Firewall Services, Page Rules edit) the zone showed security level medium, Browser Integrity Check on, no firewall/IP/UA rules. A flood-only page rule turning both off (owner-approved) **did not remove the challenge** → the cause is Bot Fight Mode or a WAF custom rule (neither readable with this token). Fix: Bot Fight Mode off (owner, OWNER_ACTIONS Q18 option A).
The main domain `flood.autobahn.bot` answers **HTTP 403 with `cf-mitigated: challenge`** ("Just a moment…") to `curl`, headless Chrome and the Facebook and LINE user agents. The same happens on every proxied host of the zone (`autobahn.bot`, `www`). Status: **still open at ~11:20 UTC** ([OWNER_ACTIONS](OWNER_ACTIONS.md) Q18).
- **Evidence 2026-09-26:**
  - `/` and `/api/*` are challenged, `/static/*` is not.
  - The result **depends on the client's TLS fingerprint**: Python's urllib got HTTP 200 seconds after curl got 403. A status script that used urllib once reported "fixed" wrongly, so it now uses curl and reads the `cf-mitigated` header.
  - This fits **Bot Fight Mode**. Cloudflare's docs say it is zone-wide, **can't be skipped by WAF rules or Page Rules**, and enables JavaScript detections that can't be turned off. The API token can't read the zone's bot settings. To confirm: dashboard → Security → Analytics → Events → the *Service* field.
- **Correction:** my earlier advice (a Configuration Rule "Security Level: Essentially Off" plus a WAF skip) does **not** apply to Bot Fight Mode. The options are: turn Bot Fight Mode off for the zone (free, affects all `*.autobahn.bot` sites), upgrade to Pro for Super Bot Fight Mode with a Skip rule, or share the alias.
- **Impact:** LINE and Facebook link previews, uptime monitors, API users and crawlers are blocked. Phones with a normal browser probably pass after a short interstitial.
- **Mitigation shipped (v0.2.1):**
  - `flood.bejranonda.com` (no challenge) serves a page whose `canonical` and `og:url` point **to itself**. Before, the alias page pointed crawlers at the challenged host.
  - A tested **`REDIRECT_LEGACY_HOST=1`** switch (301 to the main domain, `/api/health` excluded) is ready but **off**, because redirecting now would send crawlers into the challenge.

### KI-507 — User feedback can be wrong or manipulated · 🟡
Feedback (`/api/feedback`, [APPROACH §3.5](APPROACH_AND_METHODS.md)) is subjective and position-dependent: people report their own street, not the gauge. It is also open to brigading.
- **Mitigations:**
  - rate limit of 10 per hour per daily-salted IP hash, plus a honeypot field;
  - a server-side snapshot of what was shown;
  - counts only in public, notes never published;
  - the `review` flag drives **human review, never an automatic model change**.
- **Open:** no moderation UI yet; operators read `user_feedback` in SQL.

### KI-224 — "ฝน ~27 มม." was read as "ฝน −27 มม." and meant nothing to users · 🟢 fixed on branch (issue #1)
Reported by the owner on 2026-09-27 (GitHub issue #1, phone screenshot of the point card): "ฝน -27 มม. แปลว่าอะไร อ่านละไม่เข้าใจ".
- **Causes:** the approximation sign `~` renders like a minus on phone fonts, right next to a legend that uses
  negative numbers for "below bank"; a bare mm total says nothing to most people; "ฝน 24 ชม." did not say "forecast";
  an unknown value was printed as "~0 มม.".
- **Fix:** Thai Meteorological Department rain-amount categories (tmd.go.th "เกณฑ์อากาศ", read 2026-09-27:
  เล็กน้อย 0.1–10.0 · ปานกลาง 10.1–35.0 · หนัก 35.1–90.0 · หนักมาก ≥ 90.1 mm), the words "ประมาณ"/"ราว" instead of `~`
  everywhere users read, "ข้างหน้า" for forecasts, "ไม่มีข้อมูล" for unknown, one decimal near a boundary.
- **Limits, stated in the UI legend:** the TMD words are national amount classes, not local flood thresholds. Street
  flooding depends on short-burst intensity and local drainage, which a 24 h total (and a 9–25 km model cell) cannot show.
  The TMD page lists the amounts without a period; applying them to a 24 h total is our reading ⚠️.
- **Rule (GUIDELINES §6):** no `~` in user-facing text; every rain number carries its TMD word.

### KI-307 — Point check is not a depth or level at the pin · ℹ️
`/api/point` summarises gauges *around* a pin as a status category (D-021). It can't know the ground height, drains, walls or polder of the pin itself: Bangkok is not flat (KI-202, [APPROACH §2.10](APPROACH_AND_METHODS.md)).
- **Mitigations:** confidence is never "high"; at very low confidence no verdict is shown; four warnings are always visible; citizen reports near the pin are shown.
- **Fix path:** polder polygons → controlling gauge; FABDEM + σ → probability categories calibrated with user depth reports.

### KI-223 — D-041's outlook banner gave a canal verdict without a usable gauge · 🟢 fixed v0.6.1 (D-042)
`point_forecast()` (added in D-041, v0.6.0) read `area["category"]` and any single forecast gauge's `trend12`/
`delta12_median` **without checking `area["confidence"]`** — the same gate the overview card already applies
(KI-307, D-021). Found live on 2026-09-27 ~07:47 UTC:
- `14.30,100.20` (`confidence=none`, 0 gauges within 8 km) → banner said "สถานการณ์ปกติ … ความเสี่ยงน้ำท่วมต่ำ" and
  called 18 mm of rain "light" — a calm verdict manufactured from no data.
- `13.82,100.60` (`confidence=very_low`, one gauge 5.6 km away) → the overview card correctly showed no verdict,
  but the banner directly above it said "moderate / rising" from that same gauge: a contradiction on one sheet.
- A lone tidal river gauge with routine tide movement (`delta12_median ≥ 0.04 m`) could read as the whole point
  "rising", since the code took *any* forecast gauge rather than a majority of the same water body.
- **Fix (D-042):** the canal/river layer of the outlook is now used only when `confidence ∈ {low, medium}`; trend
  needs a strict majority of same-water-body gauges; rainfall (usable everywhere) is worded by 24h band, never
  folded into "risk is low"; with no usable gauge and no strong local evidence the outlook returns `risk: "info"`
  (ℹ️) stating that gauges are too far or in another basin to judge — never `"low"`/`"ปกติ"`. Distance-vs-agreement
  evidence for the confidence bands themselves is in D-042.
- **Still true:** the underlying distance/agreement proxy (KI-307) remains a proxy for basin membership, not a
  real polder boundary; that fix is unchanged (polder polygons, HANDOFF §5 step 3).

### KI-508 — AI triage provider: GLM and Cloudflare Workers AI · 🟢 (mitigated, D-030)
- **GLM Integration (D-030):** The project now supports **GLM (`glm-5.3-flash`)** via Zhipu AI OpenAPI (`open.bigmodel.cn/api/paas/v4/chat/completions`) as the primary AI triage provider. Tested and verified live in the worker container (`Parsed: {'category': 'local_drainage', 'urgent': False}`). Reasoning tokens are handled smoothly.
- **Workers AI fallback:** Cloudflare Workers AI remains supported if configured (`AI_PROVIDER=cloudflare`).
- **Safety guarantees intact:**
  - AI is used only in the background worker (`ai_triage`, D-022) to triage feedback notes; the public site and APIs never call AI.
  - Instant urgency detection and situation summaries are **deterministic** (regex/keyword rules, templates).
  - When AI is disabled, unconfigured, or failing, deterministic rules run seamlessly without interruption.
  - Circuit breaker: 3 failures trigger a 1-hour backoff pause.

### KI-212 — A worker restart reset the schedule, so the backfill never advanced · 🟢 (fixed v0.2.1)
The single worker loop schedules every task at *start + interval*. `hii_backfill` (every 10 min) was not in the startup sequence, and the startup pass takes about 5 minutes, so each restart pushed the next batch to roughly 10–15 minutes later. During the 2026-09-26 releases the worker was restarted with every deploy; the backfill count sat at 34 of 79 stations from 11:09 UTC until the fix. **Fix:** a `hii_backfill` batch (6 stations) now runs in the startup sequence. **Lesson:** anything driven by an interval timer must also run once at start, or it starves during frequent deployments.
- **Result (verified 15:20 UTC):** after the fix the backfill completed, **79 of 79** stations, without further intervention.

### KI-213 — A slow-failing upstream steals the single worker loop · 🟢 (mitigated v0.2.1)
The Traffy public API answered **HTTP 502 for about 2.5 hours** on 2026-09-26 (12 failed runs from ~12:10 UTC; back to normal by 15:11 with 500 reports). Each failing run made 3 attempts of about a minute each, so **every 10-minute run tied up the single worker loop for over 2 minutes**, delaying HII and the other collectors. The failure itself was handled correctly (isolated, recorded in `/api/health`, recovered by itself).
- **Mitigation (v0.2.1):**
  - Traffy makes **one attempt** per run (it is polled again 10 minutes later);
  - any task that fails ≥ 3 times in a row backs off ×2, ×4, ×6 (cap);
  - the core `hii_waterlevel` and `hii_history` tasks are capped at ×2, so an HII outage never delays recovery by more than one extra interval;
  - tested in `tests/test_worker.py`.
- **Still true:** one worker thread runs everything, so a slow *first* attempt can still delay others by up to the HTTP timeout (120 s). Threads or separate workers are the structural fix (Phase 4).

### KI-214 — Public repository: what history reveals; SSH exposure · 🟡
**Full-history scan (2026-09-26 15:20 UTC, every commit, values checked without printing them):**
- **Clean:**
  - none of the Cloudflare API token, tunnel token, feedback salt or database password ever appeared in history;
  - no `.env`, `.ovpn`, certificate, key, data or archive file was ever tracked;
  - the owner's email is in no commit (author `dev@flood2026.local`);
  - the only other `.env` value found, `THAI_EGRESS_PROXY`, is `http://vpn:8888` (an internal Docker name, no credentials);
  - the Cloudflare account id and tunnel ids appear only in truncated form, in the current docs.
- **Exposed (low risk):** the host's **IP address** is in 8 old commits ([D-013](plan/DECISIONS.md) had it). It was removed from the current files. Removing it from history needs `git filter-repo` plus a force-push, which breaks clones and forks and needs the owner's go-ahead. Risk is low: the site is reachable only through the Cloudflare Tunnel, and no web ports are open.
- **SSH (host, not repo):** 15,754 failed SSH logins in 24 hours (ordinary internet scanning). `sshd -T` shows `passwordauthentication yes`, `permitrootlogin without-password` (key only), and **no account with a usable password except root**, whose password login SSH refuses. Every successful login in the last 7 days used a public key. So password guessing cannot succeed today. **This contradicts the earlier guideline "SSH by key only, password and root login disabled"**, which is now corrected. Optional hardening for the owner ([OWNER_ACTIONS](OWNER_ACTIONS.md)): `PasswordAuthentication no`, `PermitRootLogin prohibit-password` (already), and `fail2ban` to cut the log noise. An agent should not change sshd on this shared host unasked (lockout risk).

### KI-110 — DWR EWS and RID Telerid are reachable only from Thailand · 🟡
Probed 2026-09-27: both **time out from Germany** and answer through the Thai egress (VPN Gate relay, KI-505). DWR `LoadStation` returns 2,275 stations (1,819 rain, 455 level) with soil moisture; `status` is 0–3 on most stations but **`9` on 783** (undocumented; probably offline ⚠️ — ask DWR). Dates are Thai local time with a **Buddhist short year** (`27/09/69 15:45 น.` = 2026-09-27 08:45 UTC). RID Telerid lists 921 stations (readings untested).
- **Before a public national launch:** a reliable Thai egress (owner action) and a courtesy note to DWR/RID (D-046). Parse `yy` as BE−543 and convert ICT → UTC (KI-205).

### KI-111 — HII national feeds mix fresh and long-dead rows · 🟡
Probed 2026-09-27 ([validation](../research/VALIDATION_2026-09-27_nationwide.md)): `watergate_load` has **2,315 rows but only 12 fresh**, most stopped in July 2023, and no thresholds; `analyst/dam` medium reservoirs: 448 of 862 fresh, **317 dated 1970-01-01** (placeholder), 71 from 2021; `canal_waterlevel`: 47 rows older than 2026. A collector that stores "latest" without a freshness filter would present years-old values as current.
- **Rule:** every national collector drops rows older than its cadence × 3 (and any epoch-0 date) and records the fresh/total ratio in `/api/health`.

### KI-404 — Research_Thailand.md is not a usable source · 🟢 (banner)
The file builds its ingestion on `api2.thaiwater.net` (no DNS; refuted since 2026-09-26), gives wrong counts and thresholds (C.13 "2,000/2,500" vs RID's 2,176/2,448/2,720), invents a sample payload, and proposes a HAND street depth, an egress relay, a non-honest UA and evacuation instructions — all against project rules. Kept as a record with a 🔴 banner (owner's choice); see [validation §C](../research/VALIDATION_2026-09-27_nationwide.md).

### KI-509 — A GloFAS point query can land on a side cell · 🟡
On 2026-09-27 the Open-Meteo Flood API at Nong Khai (17.88, 102.74) returned **1–3 m³/s**; the cell at 17.925, 102.725, about 5 km away, returned **≈ 9,000 m³/s** — the Mekong. At Hat Yai a point gave 0.1–1.3 m³/s. A virtual gauge taken at the user's pin can therefore be off by three orders of magnitude.
- **Rule (APPROACH §19.5):** snap each virtual gauge once to the highest-discharge cell within ~5 km of the reach, store it, compare only with that cell's own climatology, and show categories only.

### KI-510 — GISTDA answered 404, while the status script said ✅ · 🟢 fixed 2026-09-27
`GET …/api/2.0/resources/gi-service/v1.0/disasters/flood-extent-1day?…&api_key=…` returned **404 `{"detail":"Service not found"}`**. `scripts/owner_status.py` had reported ✅ because it only checked that `GISTDA_API_KEY` existed.
- **Cause:** our endpoint was outdated. GISTDA's documentation (`disaster.gistda.or.th/services/open-api`, OpenAPI server `https://api-gateway.gistda.or.th/api/2.0/resources`) lists `/features/flood/{1day,3days,7days,30days}` and `/features/flood-freq` (params `limit`, `offset`, `bbox`) with the key in the **`API-Key` header**. With that, the same key returns 200.
- **Data (2026-09-27 09:54 UTC, national):** 1 day 0 cells (no satellite pass), 3 days 38,461, 7 days 49,761, 30 days 52,778 flooded **H3 cells (~0.12 km²)** with `f_area` m², province/amphoe, exposure (`population`, `building`, `length_road`, `hospital`, crop areas) and the source passes (`S1C/S1D` Sentinel-1, `rd2` Radarsat-2, `cg2/cm4` COSMO-SkyMed); `flood-freq` gives recurrence polygons (5,377 in a Bangkok-area bbox). The Bangkok bbox had **0 cells in 7 days** while streets were flooded: radar misses water between buildings (⚠️ inference), so an empty result is **not** "no flood" in cities.
- **Fixed:** `GISTDA_API_ENDPOINT` → `/features/flood/7days`; `config.py` default and `.env.example` updated; the status script sends the header and reports the cell count. **Lesson:** a status check must exercise the service, not the presence of a key.

### KI-511 — No database backup at all; disk 84 % full · 🔴 (risk accepted by the owner, Q29 2026-09-27: "no backup for now")
R2 off-site backups were declined (D-029), but **no local dump exists either**; `infra/README.md` describes one that was never built. 2026-09-27: DB 706 MB, ~74,000 rows/day, disk 60 of 75 GB used (12 GB free, shared host). BMA canal history (since 2026-09-26) and user feedback cannot be re-fetched. National collection would multiply the growth.
- **Plan (D-046):** nightly `pg_dump -Fc` into `data/backups/` (keep 3) and one tested restore into a throwaway container, **before** any national collector runs; retention of 90 days for high-volume national series; a disk alert already exists (hourly check).

### KI-225 — Literal delta interval "ลด 11 ถึงเพิ่ม 17 ซม." and "มั่นใจต่ำ" caused citizen confusion · 🟢 fixed v0.6.4 (D-048)
Conformal prediction intervals crossing zero were printed literally as "น่าจะลด 11 ถึงเพิ่ม 17 ซม.", creating a paradoxical statement where water was claimed to decrease and increase simultaneously, contradicting the "ทรงตัว" badge beside it. In addition, "มั่นใจต่ำ" sounded like a severe defect, causing citizens to distrust the telemetry. In point check, mixed canal statuses across 8 km suppressed canal gauges entirely, leaving users without the canal rise/fall information they needed.
- **Fixed (D-048, v0.6.4):**
  1. Steady intervals crossing zero are worded as `ทรงตัว (อาจแกว่งตัว -A ถึง +B ซม.)`.
  2. "มั่นใจต่ำ" replaced with progressive dot scale `●○○ คาดการณ์เบื้องต้น` and `●●○ คาดการณ์ปานกลาง` with backtest tooltips.
  3. The closest forecast canal station is displayed in the point check banner with distance attribution even when surrounding area confidence is low/none.
  4. Redundant urgent alert banner suppressed when forecast banner is active in high-risk alert mode.


### KI-112 — HII's official forecast files need care · 🟡 archived and scored (D-050)
Found 2026-09-27 (`fews2.hii.or.th/model-output/data_portal/{hii_waterlevel,rid_discharge}/forecast/{CODE}.txt`).
- **Overwritten on every issue:** no history is kept by HII, so skill can only be measured from our own archive (`external_forecast`, collector `hii_fews_forecast`).
- **The first ~6 days of each file are not a forecast:** they match our observations to 1–3 cm (assimilated/observed). Only rows after `Last-Modified` are stored.
- **C.13 dam discharge is held constant** (1,950 m³/s for 7 days on 2026-09-27): downstream forecasts assume the release stays as it is. Say so when showing them.
- **Sentinel bug (fixed before release):** the level rule "≥ 1000 = missing" dropped every discharge row (Chao Phraya ~1,200–2,700 m³/s). The FEWS parser now drops only ≥ 99,999 (the 999999 code).

### KI-227 — "Nearest canal" showed a river gauge · 🟢 fixed v0.7.0
v0.6.4 (D-048) showed `stations_forecast[0]` as "คลองใกล้เคียงที่สุด" when the area gate withheld a canal statement. At 13.70,100.50 that was CPY015 on the Chao Phraya, whose "ลดลงมาก" is the tide going out — the KI-223 error again. Now `point.py` picks the nearest **canal** gauge within 3 km with a forecast (`forecast.nearest_canal`), or nothing; covered by a test.

### KI-228 — ⓘ in a list item opened the station · 🟢 fixed v0.7.0
The document-level click handler ran after the list item's own handler, so `stopPropagation()` came too late. The handler now runs in the capture phase. Verified by driving headless Chrome over CDP (title unchanged, tip shown).

### KI-512 — Access logs kept search text and coordinates · 🟢 fixed v0.7.0
D-032 says place-search queries are never logged. Uvicorn's access log nevertheless recorded the full URL: on 2026-09-27, 124 `/api/geocode?q=…` queries and 1,236 `/api/point?lat=…&lon=…` positions in 24 h (container logs on this server only, never published). `api.RedactQuery` now strips the query string of `/api/geocode`, `/api/point`, `/api/reverse`, `/api/near` (test in `test_api.py`). Recreating the container on deploy discards the old logs.

### KI-229 — "ประเมินไม่ได้" almost everywhere in Bangkok · 🟢 fixed v0.10.0 (D-054)
Owner, 2026-09-27: "Why does it always show ระดับน้ำในคลอง · ประเมินไม่ได้? We have predicted results." Cause: the D-042 gate required *all* gauges within 8 km to agree (spread ≤ 1 level). Since the 199 BMA gauges joined (v0.3.0), nearly every 8 km circle holds both a calm and an overflowing canal: 53 of 64 grid points (83 %) were "very_low". The gate now judges agreement among up to 3 gauges within 3 km (gauges within 1–2 km agree 71–86 %, D-042 analysis); 25 of 64 remain very_low, where the nearest gauges really disagree. Tests: `test_dense_city_is_judged_by_the_nearest_gauges_not_the_whole_8_km_d054`.

### KI-230 — BMA gauges had no forecast · 🟢 v0.10.0 (D-054)
All 199 BMA gauges had only our own relay history (from 2026-09-26 16:30 UTC), so the backtest never ran and every one used "no change" without a range; the point panel's nearest canal (usually a BMA gauge) therefore showed no trend. HII serves the same BMA values back to 2024 (`waterlevel_graph?station_type=canal`); a one-year hourly backfill now lets the tide and `star` methods compete on BMA gauges.

### KI-231 — False precision in recovery windows · 🟢 fixed v0.10.0
"อาจต่ำกว่าตลิ่งราว 30 ก.ย. 01:12 – 2 ต.ค. 05:12" read as exact times although it is a 3-day low-confidence extrapolation (D-005: ranges, no minute countdowns). Windows ≥ 24 h now show dates only; shorter ones whole hours.

### KI-232 — No trend in the panel although nearby canals had one · 🟢 fixed v0.10.2
Owner screenshot 13.764,100.679 (2026-09-27): the nearest canal WL.SMK.01 (0.3 km, overflowing) is one of the 37 BMA gauges HII does not serve (history since 26 Sep) → no forecast, so the canal factor showed no trend, while WL.SSB.08 at 1.9 km had one. The folded text ("ใกล้จุด 3 แห่ง … ทั้งรัศมี 8 กม. …") was not understood either. Now `/api/point` also returns `nearest_canal_trend`; the panel shows both lines, each with "when it may drop", and the summary is one plain sentence. Test: `test_nearest_canal_with_a_trend_is_given_when_the_nearest_has_none`.
