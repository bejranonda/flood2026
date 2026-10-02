# KNOWN_ISSUES.md — Limitations, pitfalls and workarounds

> **Project:** BKK FloodWatch 2026 · **Last updated:** 2026-10-02
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
| KI-265 | Top strip: the region's rain took 3–4 lines (v0.17.1 rows layout) and read as "Bangkok only" (it followed the region chip far below) | UI | 🟢 fixed v0.18.9 (shown only for heavy rain, one line) |
| KI-264 | A research run (49 points × 1 year) hit Open-Meteo's per-minute limit (HTTP 429); the free allowance is shared with production rain | Infrastructure | 🟡 (research runs paced and sized; production unaffected) |
| KI-263 | Pins upstream of Bangkok (focus provinces Ayutthaya–Nakhon Sawan) used the polder rules: a pin 0.1 km from LBI001 (over bank) said "no gauge close enough" | UX / Product | 🟢 fixed v0.18.9 (polder rules only in กทม.+ปริมณฑล) |
| KI-262 | GISTDA echoes the caller's API key inside every response's `links` URLs | Security | 🟡 (strip `links` before storing or logging; no collector stores them yet) |
| KI-261 | v0.18.0 plain line called a gauge 6 km away "คลองแถวนี้" ("น้ำใกล้เต็มตลิ่ง") under the headline "ไม่มีสถานีวัดน้ำใกล้พอ ยังสรุประดับคลองไม่ได้"; the AI reworded the mistake | UX / AI | 🟢 fixed v0.18.1 (far gauge named with its distance; check C12) |
| KI-260 | ai.run returned GLM's *reasoning* as the answer when the content was cut off; glm-5.3-flash took 9–10 s per call | AI | 🟢 fixed v0.18.0 (`reasoning_effort: "low"`, content only) |
| KI-259 | "ใน 24 ชม." / "ใน 48 ชม." on forecast rows was not read as the future | UX | 🟢 fixed v0.17.2 ("อีก N ชม."; tests/test_wording.py) |
| KI-258 | Rain in the pin panel read as one long sentence, and the headline repeated its amounts ("ฝนตกแล้ว 11 มม. … · ระดับน้ำ… คาดฝนเล็กน้อย") | UX | 🟢 fixed v0.17.1 (rain in the water rows' layout; check C11) |
| KI-257 | BMA canal readings stopped upstream (relay answered with readings stuck at 00:10 ICT); health said "ok"; the summary counts looked current | Data access / Ops | 🟡 upstream; v0.16.8 says so (summary line, `stale_sources` in health) |
| KI-256 | Trend rows flipped direction across horizons (⬆ / ⬇ / ⬆ at TRD001): a measured-trend row contradicted a model-proven one at 43 of 719 gauges | UX / Forecast | 🟢 fixed v0.16.6 (0 left; 19 model-vs-model by design) |
| KI-255 | Learned upstream inputs were never used: learned once with 4 days of history ({}), every forecaster restart skipped relearning | Forecast | 🟢 fixed v0.16.6 (326 gauges got inputs) |
| KI-254 | Pin panel showed only forecast rain during a downpour; region rain line only for กทม./ปริมณฑล; the river near a Bangkok pin only in the list | UX / Data | 🟢 fixed v0.16.3 |
| KI-253 | v0.16.0 looked Bangkok-only: on a phone 6 of 9 region chips were off-screen, and the map hid every gauge outside the chosen region (0 gauges around Chiang Mai with the default กทม.) | UX | 🟢 fixed v0.16.1 |
| KI-252 | Two containers ran `schema.sql` at start; an `ALTER TABLE station` deadlocked with an observation insert | Infrastructure | 🟢 fixed v0.16.0 (only the collector owns the schema) |
| KI-251 | A dead HII host (`tiwrm.hii.or.th` connect timeouts, 2026-09-30 20:32 UTC) cost ~6 min per request and stalled the collector loop | Infrastructure | 🟢 fixed v0.16.0 (10 s connect timeout, 10-min host cooldown) |
| KI-250 | `/api/stations` hung for every visitor ~13 min after the v0.16 deploy (nested memo on a non-reentrant lock) | API | 🟢 fixed v0.16.0 (RLock + test) |
| KI-249 | Nationwide gauges were never backfilled or forecast, yet their sheet promised "การคาดการณ์จะเริ่ม… (ราว 3 ต.ค.)" and said "น้ำในคลอง" for rivers | Data / UX | 🟢 fixed v0.16.0 (D-064); 🟡 backfill ~10 h, nationwide skill to re-measure |
| KI-248 | The site had no robots.txt/sitemap.xml/share image/structured data; header and footer showed a stale `v0.9.0` until the JS ran; description said 12–72 h | SEO / UI | 🟢 fixed v0.15.3 |
| KI-247 | HII `waterlevel_data` delivered 28 gauges stamped ~21 h in the future; `/api/health` showed a negative data age | Data | 🟢 new rows flagged v0.15.3; 26 old rows flagged 2026-09-30 (owner OK); health ignores them v0.16.0 (expire 2026-10-01 16:00 UTC) |
| KI-246 | DB overload: ~10 req/s each ran the station query; Postgres max_connections (40) exhausted for ~4.5 h; worker crash-looped | Infrastructure | 🟢 fixed v0.15.2; 🟡 no external uptime alert yet |
| KI-245 | GitHub #9: desktop page ~100 px taller than the screen; #8: hover outline always blue | UI | 🟢 fixed v0.15.1 |
| KI-244 | Panel texts contradicted each other (headline 12 h / majority vs 24 h rows of the nearest gauge; list vs sheet chip; model chip vs range; repeated lines; recovery lost its early end) | UX | 🟢 fixed v0.15.0 (D-062) |
| KI-243 | `qc.run_all` crashed after deploy: a local dict named `observed` shadowed the new `observed()` | Code | 🟢 fixed v0.14.0 (end-to-end test with a fake DB) |
| KI-242 | Rows said "? ไม่แน่ชัด" / "→ ทรงตัว" while the chart fell slowly (WL.KPM.04 −14 cm/24 h, WL.LBK.03 −1 cm/day) | UX / Product | 🟢 fixed v0.14.0 (D-060) |
| KI-241 | Six BMA gauges stuck at an exact value (1.00 m / 0.40 m) for 48 h showed statuses (WL.KPM.03 "ถึงตลิ่ง 25–50 %") | Data quality | 🟢 fixed v0.14.0 |
| KI-240 | "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า" shown at gauges that had clearly fallen (26 of 138), e.g. WL.CKS.01 −91 cm; small steady falls (BKK021 −5 cm) invisible | UX / Product | 🟢 fixed v0.13.0 (D-058) |
| KI-239 | Review of v0.9.0→v0.11.2: recovery line lost its "if no heavy rain" condition (D-005); one gauge ≤ 3 km decides the canal factor; headline trend from gauges 3-8 km away; daily BMA refresh blocks the worker | Product / Infrastructure | 🟢 fixed v0.13.0 (D-059) |
| KI-238 | Best method chosen per horizon gives zig-zag rows (↑ / ? / ↑) and a wavy forecast line: 94 of 224 gauges mix methods | Modelling / UX | 🟡 mitigated (3 of 221 after v0.12.0; none opposite on screen) |
| KI-237 | Pump-affected or faulty gauges (±0.8 m every 10 min) and single-reading dropouts (-2.00 m) passed QC and drove status, headline and forecast | Data quality | 🟢 fixed v0.12.0 (D-057) |
| KI-236 | Package data (`src/floodwatch/data/*.json`) was never committed: the `data/` ignore rule matched it | Repo | 🟢 fixed 2026-09-27 (`/data/`) |
| KI-235 | "Can't summarise" outlook repeated the reason at length | UX | 🟢 fixed v0.11.2 |
| KI-234 | Canal factor: one gauge name bold, the other not; labels ran into long lines | UI | 🟢 fixed v0.11.1 |
| KI-233 | Trend formats differed by horizon and view; 24 h showed a direction from the "no change" model; "ใกล้ตลิ่ง" 158 cm below the bank | UX / Product | 🟢 fixed v0.11.0 (D-056) |
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
| KI-305 | No archive of as-issued forecasts yet (perfect-prognosis risk) | Modelling | 🟢 resolved (forecast_run since 2026-09-26; rain as forecast since 2025-09-22) |
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

### KI-305 — No archive of as-issued forecasts yet · 🟢 resolved (checked 2026-09-30)
**Update 2026-09-30:** every forecast issue is stored in `forecast_run` (45,106 runs for 305 gauges since 2026-09-26) and rain *as it was forecast* 1–2 days earlier in `rain_hindcast` (80,784 hourly rows back to 2025-09-22, D-052), so skill is scored on as-issued forecasts. Original note:
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
  - **Still failing via VPN:** Both `weather.bangkok.go.th` (BMA server) and `dds.bangkok.go.th` (BMA server) time out on ports 80 and 443. Traceroute shows packets are completely dropped at BMA's perimeter firewall subnet. Tinyproxy returns `500 Unable to connect`.
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
- **2026-10-02 (lower Chao Phraya, [research](../research/2026-10-02_glofas_outlook.md)):** C.2 (Nakhon Sawan) answered 1.1 m³/s at its own point. "Largest flow within ±0.1°" over-snaps: it lands on the window corner, below a confluence (C.35 at 3.4× measured); prefer the cell closest to measured flow where a discharge gauge exists, else the nearest cell with ≥ half the largest flow.

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

### KI-233 — Inconsistent trend formats and a misleading "near bank" · 🟢 fixed v0.11.0 (D-056)
Owner, 2026-09-27: "Why do 24 h and 48 h have different formats?" and "the panel and station formats are confusing". Audit: the 48 h line put the horizon in the chip, the others in the text; 24 h chips showed "→ ทรงตัว" for gauges whose model is "no change" (a tautology, not a forecast) while 48 h withheld a direction; horizons, status styles and "when it drops" wording differed between list, panel and sheet. Separately, CPY015 read "เตือนภัย (ใกล้ตลิ่ง) · ต่ำกว่าตลิ่ง 158 ซม.": watch/warning for bank gauges come from the share of channel depth (91 % of an 18 m deep river), so the label now says "น้ำเต็มลำน้ำ 91 %" when the bank is > 30 cm away.

### KI-234 — Two gauge lines formatted differently · 🟢 fixed v0.11.1
Owner screenshot 13.748,100.668 (2026-09-27): "คลองใกล้สุด ค.หัวหมาก-ซ.รามคำแหง 68 2.2 กม. [pill] · ยังไม่มีคาดการณ์" was one muted run-on line with a plain name, while the forecast gauge below had a bold name, and "คาดการณ์จากคลองใกล้เคียง:" sat on a line of its own — two formats for the same thing. Now one `gBlock` renders both: label line → bold name · distance · status pill → rows or "ยังไม่มีคาดการณ์"; a dashed divider between gauges.

### KI-235 — Long "why" sentence in the can't-summarise outlook · 🟢 fixed v0.11.2
Owner screenshot 13.875,100.542 (2026-09-27): "สถานีรอบจุดนี้ให้ข้อมูลไม่ตรงกัน จึงยังสรุประดับคลองที่จุดนี้ไม่ได้" followed by "สถานีใกล้เคียงวัดคนละแหล่งน้ำ (แม่น้ำ/คลอง) หรือคนละพื้นที่ปิดล้อม ดูแนวโน้มของแต่ละสถานีด้านล่าง" — long and redundant with the canal factor ("คลองรอบจุดต่างกันมาก"). Now: "สถานีรอบจุดไม่ตรงกัน ยังสรุประดับคลองไม่ได้" / "ไม่มีสถานีวัดน้ำใกล้พอ ยังสรุประดับคลองไม่ได้", and the text is only the rain condition. Test: `test_info_outlook_is_short_the_reason_lives_in_the_canal_factor`.

### KI-236 — Package data files were never in git · 🟢 fixed 2026-09-27
The owner asked "not all are committed?" — and two files were not: `src/floodwatch/data/chaophraya_chainage.json` (river km per gauge; used by the Chao Phraya profile and by `star` to find upstream gauges) and `src/floodwatch/data/station_coords_approx.json` (OSM positions for gauges HII does not place, KI-207). The `.gitignore` rule `data/`, meant for the runtime folder at the repo root, matched them too. Production worked because Docker copies the files from disk; a fresh clone of the public repo would have lacked them. The rule is now `/data/`, both files are committed, and a fresh clone passes the tests.

### KI-237 — Erratic (pump-affected) gauges and dropouts passed QC · 🟢 fixed v0.12.0 (D-057)
Owner screenshot of WL.SSB.08 (2026-09-28 04:05 ICT): "110 cm below the bank", 12 h "+41 to +62 cm" (rising a lot), 24 h "uncertain", 48 h rising a lot, over a chart jumping between +0.80 and -0.80 m. The gauge alternated between about ±0.8 m every 5-15 min from 2026-09-26 09:00 UTC (e.g. 20:55 +0.70 → 21:00 -0.49), was calm 04:05-16:30 UTC, then erratic again: the "now" level, the status and both forecast methods were anchored on one random reading, so the rows changed every run (the API a few minutes later said +8 to +29 cm). `qc_level` only judges one reading against the bank, and ±0.8 m is inside that range.
Scan of all gauges, 7 days to 2026-09-27 21:25 UTC (a ≥ 0.30 m step within 30 min that reverses within the next 30 min): **41 stations**, all stored as `ok`. Four patterns: continuous oscillation (WL.SSB.08); pump cycling, 0.5-1 m drawdowns in 20 min (WL.BNJ.02, WL.BSK.01, WL.LSM.01); several stuck values (CPY016: 2.21/2.60/2.86/2.98/3.12; ATG161: -7.01/8.42); and dropouts of one or two readings from a steady level (WL.LPT.03 and WL.KPM.05 to exactly -2.00; WL.BTL.01 to ~0.9). WL.MSW.03 switched between two smooth series (1.56 → -1.42…-1.81 for 2 h 20 min → 1.32) inside BMA's own `wl_in` (all rows `bma_klongmap`; not our mixing). A plain Hampel filter (median of ±2 readings, 0.30 m) fixed 25 of 33 but not the oscillating gauges, and removed 110 readings at spike-free gauges, including real pump drawdowns.
**Fix (`floodwatch.qc`, worker task `qc` every 10 min):** (1) a reading that leaves the level before it by ≥ 0.30 m for one or two readings and comes back within 10 cm is flagged `dropout` (kept in the DB, hidden everywhere; the newest reading cannot be judged until the next one arrives); (2) ≥ 3 remaining steps of ≥ 0.30 m within 30 min in the last 24 h marks the gauge **erratic** (`collector_state.erratic_gauges`): its dot stays, level, status, trend and forecast are hidden with the note `erratic`, it is not forecast and it no longer counts in the point check (status `unknown`). On the data of 2026-09-28 04:40 UTC: 11 of 307 focus gauges erratic (ATG101, ATG111, ATG161, ATG181, CPY016, WL.ANX.01, WL.BNJ.02, WL.BSK.01, WL.LSM.01, WL.MSW.03, WL.SSB.08); WL.LPT.03 (critical) and WL.KPM.05 (warning) stay visible with their dropouts removed; 6-11 gauges per 24 h window over the week. A one-off run over 45 days (`qc.run_all(hours=45*24)`) flagged 2,006 dropout readings at 54 gauges, so charts and forecast training no longer see them. The sheet of an erratic gauge leads with "ไม่แสดงระดับน้ำ (ขึ้นลงผิดปกติ)"; the generic unknown label is now "ไม่ทราบสถานะ" (it read "ไม่มีระดับตลิ่ง" for every unknown, also old data). Verified live 05:00 UTC at 390 px (WL.SSB.08 hidden with the reason; WL.LPT.03 still "ล้นตลิ่ง" with a clean chart). Tests: `tests/test_qc.py`, `test_erratic_gauge_keeps_its_dot_but_not_its_level_status_or_trend`.

### KI-238 — Zig-zag forecast rows from per-horizon method choice · 🟡 mitigated, open
The forecast keeps, for each horizon separately, the method with the best backtest (persistence, star, tide, tide_trend). The path then switches method between horizons (WL.SSB.08: h1-6 persistence, h7-12 star, h24 persistence, h36-48 star), so the rows read "↑ a lot / ? / ↑ a lot" and the dashed line waves. On 2026-09-27 21:25 UTC, 94 of 224 gauges with 12/24/48 h rows mixed methods and 6 showed a reversal of ≥ 10 cm on both sides of 24 h (WL.SKT.01, PIN005, WL.VPV.01, Ct.5A, WL.SRE.01, WL.SSB.08). Options: one method per gauge for the whole path (e.g. the best at 24 h), or blend weights that change smoothly with the horizon.
**Re-measured 2026-09-28 06:58 UTC (after the erratic gauges were hidden):** 90 of 221 gauges mix methods, 3 show a ≥ 10 cm reversal (WL.SNO.01, PIN005, WL.VPV.01); on screen they read "→ / ↗ / ?" or "? / ↗ / ?" because "no change" rows show no direction (D-056), so no gauge shows opposite directions. Kept open: a single-method path must first win a backtest.

### KI-239 — Findings of the code review of v0.9.0 → v0.11.2 · 🟢 fixed v0.13.0 (D-059)
Checked against the code on 2026-09-27; ordered by harm.
1. **Recovery line lost its condition (D-005):** `dropText` (web/app.js) prints "คาดว่าจะต่ำกว่าตลิ่ง: 30 ก.ย. – 2 ต.ค." without "(หากไม่มีฝนตกหนักเพิ่ม)"; the extrapolated case also lost "ความเชื่อมั่นต่ำ" (both were in v0.9.0 `recoveryText`).
2. **One gauge ≤ 3 km decides the canal factor** (`point.area_index`): confidence "low" and its status even when every gauge just beyond 3 km disagrees by 2+ ranks (the issue #3 case); the gauge may be a river gauge, then shown as a canal (KI-223/KI-227).
3. **Gate and headline use different gauges** (`point.py`): the gate uses gauges ≤ 3 km, the headline trend the first 3 with a forecast within 15 km.
4. **Daily BMA history refresh runs ~158 gauges in one worker call** (`collectors.bma_history`, 1 s pause each, 5-10 min), holding back `hii_waterlevel`/`bma_klong`/`forecast`; it also fetches the full `canal_waterlevel` feed every 10 min when there is nothing to do. The backfill finished (158 done + 41 missing) on 2026-09-27; `refreshed` was still unset.
5. A gauge that keeps failing in the backfill is never marked done or missing and stays first in the queue (not happening now).
**Fixed in v0.13.0 (D-059):** (1) conditions back in `dropText`; (2) river gauges skipped in `point.area_index`, and a lone gauge within 3 km drops to very_low when a gauge within 5 km (`CHECK_KM`) differs by 2+ ranks; (3) `stations_forecast` limited to the gate's band (3 km when a canal gauge is that close, else 5 km); (4) `bma_history` reads its state first (no HII request when idle) and refreshes `BMA_REFRESH_PER_RUN` = 20 gauges per run; (5) `BMA_MAX_FAILURES` = 3 then `failed`; (6) `touchcancel` reset, 12 h fallback row, comment corrected, `ValueError` on a non-dict HII payload. Effect on a 2 km grid of 426 Bangkok pins with gauges (live stations, 2026-09-28): usable canal statement 55 % → 50 %; 29 lone-gauge statements closed (9 of them red), 11 opened or firmed up without river gauges. Tests: `tests/test_bma_history.py`, `test_river_gauges_never_decide_the_canal_factor`, `test_a_lone_close_gauge_outvoted_nearby_is_not_trusted`, `test_waterlevel_graph_string_payload_is_a_clear_error`.
6. Minor: no `touchcancel` on the sheet drag (a cancelled drag can block scrolling); a gauge with only `change12` gets no trend in the panel; the `change48.proven` comment is outdated (D-056); `parse_waterlevel_graph` fails with "'str' object has no attribute 'get'" when HII returns a string (Ct.4, Ct.5A at 21:15 UTC; next run fine).

### KI-240 — "No fall seen" at gauges that were falling; small falls invisible · 🟢 fixed v0.13.0 (D-058)
Owner screenshot of BKK021 (critical, 54 cm over the bank, 2026-09-28 13:10 ICT): the chart slides down slowly since 26 Sep, yet the sheet said "? ไม่แน่ชัด" at 12/24 h and "ยังไม่เห็นแนวโน้มลดลงใน 24 ชม. ข้างหน้า". Owner: "a few cm lower in a flood is significant, because it can reduce many affected areas"; "the sentence is good, the problem is the criteria … you can replace it with finer words for small changes".
**Cause:** the sentence was shown whenever the 24 h *forecast* row was not "falling" (status watch+), including rows from the "no change" model, which can never fall; direction also needs a median change larger than half the 50 % band (±7 cm at BKK021). The damped-trend model exists but loses to "no change" at 24 h almost everywhere in the 45-day backtest (e.g. WL.BPM.03 RMSE 0.111 vs 0.099 m), so forecasting cannot supply the direction.
**Proof (live API 2026-09-28 06:45 UTC, `research/validation/observed_trend_vs_rows.py`, 226 gauges with 24 h rows):** 97 had a clear measured 24 h trend (≥ 5 cm, straight-line R² ≥ 0.7, same sign over 48 h). **All 48 falling ones** showed no fall in the 24 h row (37 "no change" model, 7 star "steady", 4 star "rise"); 21 of 49 rising ones showed no rise. The sentence was shown at 138 gauges, at 26 of them after a clear fall (WL.CKS.01 −91, WL.BPM.03 −22, WL.LPW.03 −19 cm, critical). BKK021: −4.6 cm in 24 h (R² 0.83), −7 cm in 48 h.
**Fix:** the sentence is replaced by the measured change, a fact rather than a forecast: `qc.observed24` fits a straight line to the last 24 h (dropouts removed, ≥ 20 h of readings) every 10 min; the UI line "24 ชม. ที่ผ่านมา: ลดลง 5 ซม." uses finer words by the rounded cm (< 2 ทรงตัว · 2-4 เล็กน้อย · 5-19 ลดลง/เพิ่มขึ้น · ≥ 20 มาก) and "ขึ้นลงสลับกัน" when R² < 0.5 (tide, pumps). Dry run on 297 focus gauges: 273 get a line; mixed 91, rise 47, fall 40, steady 31, strong fall 31, strong rise 19, small fall 11, small rise 3; tidal CPY015 → mixed. The "when it drops" line no longer says "(น้ำยังไม่ลดลง)" when the gauge is measured falling. Tests: `test_observed24_*`. Verified live at 390 px (2026-09-28 07:05 UTC): BKK021 sheet, pin panel and list cards read "24 ชม. ที่ผ่านมา: ลดลง 5 ซม."; WL.BKT.01 (no forecast yet) "ลดลงเล็กน้อย 4 ซม."; CPY015 "ขึ้นลงสลับกัน". Follow-up: the home summary strip still counts only forecast trends ("มีแนวโน้มลดลง 13 สถานี (12 ชม.)").

### KI-241 — Stuck gauges shown as real · 🟢 fixed v0.14.0
Found in UX round 12 (2026-09-28 17:35 UTC): WL.BKA.04, BYI.01, PWT.06, SSB.11 read exactly 1.00 m and SSB.07 0.40 m in 100 % of 48 h (≈ 270 readings each); WL.KPM.03 1.00 m in 94 %. KPM.03 showed "คลองเต็ม · เกินเกณฑ์ กทม. 78 ซม." and "โอกาสถึงตลิ่ง 25–50 %". The next-highest gauge repeats one value in < 90 % of 24 h, so `qc.stuck` (≥ 90 % of ≥ 50 readings in 24 h) catches exactly these six. They are stored as `erratic_gauges` with `kind: stuck`; the UI note is "ค่าระดับน้ำค้างที่ค่าเดิมตลอด 24 ชม. (เครื่องวัดอาจขัดข้อง)". 1.00 m looks like a BMA placeholder (⚠️ not confirmed by BMA).

### KI-242 — Rows contradicted a falling chart · 🟢 fixed v0.14.0 (D-060)
Owner screenshots (2026-09-28): WL.PWT.03 "? / ? / → ทรงตัว"; WL.KPM.04 falling since 27 Sep, rows "? / ? / → ทรงตัว" (48 h range −32 to +29 cm); WL.LBK.03 falling ~1 cm/day, "ขึ้นลงสลับกัน" and "ทรงตัว". Causes: "no change" rows always showed "?"; a model's median ≈ 0 showed "ทรงตัว" whatever its range; whole-cm steps lowered R² (0.43) so a slow fall read as mixed; 24 h was too short for ~1 cm/day. Evidence on continuation (`research/validation/direction_persistence_2026-09-28.py`, 45 days): a steady canal fall continues 24 h later 53–55 % of the time (rivers 70–88 %); only 3 of 79 gauges falling on 2026-09-28 reach 70 %. Owner chose "always follow the measured trend"; the odds are stated in the ⓘ. Live after the fix: 386 rows follow the measured trend; KPM.04 "↘ ลดลง" at 12/24/48 h (history: continued 64/61/65 %).

### KI-243 — qc crashed after deploy (name shadowing) · 🟢 fixed v0.14.0
`run_all` kept a dict called `observed` while the new function `observed()` was called in the loop: `TypeError: 'dict' object is not callable` on the first live run. Unit tests did not cover `run_all` (needs the DB). Fixed by renaming; `test_run_all_end_to_end_with_a_fake_database` now runs it end to end.

### KI-244 — Panel texts contradicted each other · 🟢 fixed v0.15.0 (D-062)
Found by `scripts/ux_consistency.py` (2026-09-28 19:00–20:10 UTC, live, one browser session, re-checking any mismatch after a reload so a qc refresh between reads does not count). First runs: C1 list/sheet/pin 48 → 0 after same-moment comparison; C6 headline vs rows 7 (e.g. pin 13.70,100.47 "คลอง/แม่น้ำใกล้จุดนี้ยังทรงตัว" above "↘ ลดลง ราว −10 ซม."; pin 13.70,100.42 "ระดับน้ำใน 12 ชม. มีแนวโน้มเพิ่มขึ้น" while the panel shows only 24/48 h rows that fall). Causes and fixes: the outlook took a strict majority of up to 3 gauges and the 12 h label → it now takes the gauge the canal factor shows and its 24 h row; the watch/warning branch said "ทรงตัว" for falling canals → "แต่มีแนวโน้มลดลง"; the normal branch said "ยังทรงตัว" with no trend → only when the trend is steady. VLGE20: the list showed only 24 h, skipping the rule "never surer after a '?'" → every view walks 12→24→48 h. C2: three model rows "↗ เพิ่มขึ้น −1 ถึง +14" → a model direction only when its likely range agrees (API and UI). C4: the gauge pill repeated the factor word; the measured line appeared twice in the pin panel. BKK008: "คาดว่าจะต่ำกว่าตลิ่ง: หลัง 72 ชม." hid an early crossing (1 cm over the bank, falling 12 cm/day) → the window keeps its early end. Final run: 310 sheets, 67 pins, 405 panel blocks, 1,261 rows, 4 viewports: C1–C3, C5, C6 = 0; C4 = 2 (two different gauges with the same status, accepted).

### KI-245 — Desktop page taller than the screen; hover colour · 🟢 fixed v0.15.1
GitHub #9 and #8 (filed 2026-09-27, re-checked on v0.15.0 on 2026-09-29): the desktop list and map had a fixed `calc(100vh − 145px)` while header, banner, summary and tabs take ~245 px, so the page was ~100 px taller than the window at 1366×768, 1440×900 and 1920×1080 (measured: document 1002 px in a 900 px window). Now the page is a flex column of exactly 100dvh (the list and map take the rest; the footer stays visible; windows under ~670 px tall still scroll because the map keeps 420 px). A card's hover/focus border was always the accent blue; it now takes the card's urgency colour. Verified live: document height = window height at all three sizes; a critical card's hover border is `#c62828`.

### KI-246 — Database overload under load · 🟢 fixed v0.15.2; 🟡 no external alert
Found 2026-09-30 05:38 UTC while taking README screenshots: the page showed "โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่". Evidence: `pg_stat_activity` showed 40 of 40 connections active, 39 of them the same STATIONS_SQL from the app, 2–3 s each; app log 6,058 requests in 10 min (`/api/stations` 1,850, `/api/stats` 1,552, `/api/reports` 1,387, `/api/point` 347); `/api/health` HTTP 500, `/api/stations` 11 s; worker `RestartCount` 452 with "FATAL: sorry, too many clients already" from 2026-09-30 01:xx UTC (2,003 errors). Cause: every endpoint rebuilt all 310 station rows per request (the per-row `collector_state` lookups added in v0.12–v0.14 made the query heavier), so a traffic rise saturated the pool. Fix: `_station_rows` and `_memo` share the rows and the `/stations`, `/stats`, `/reports` payloads for 60 s behind a lock. Verified: health 200, `/api/stations` 0.3 s idle; load test 120 requests at 30 concurrent → 0 errors, median ~0.5 s, peak 11 connections. Gap: nothing alerted anyone for 4.5 h → OWNER_ACTIONS "UPTIME".

### KI-247 — HII readings stamped in the future · 🟢 flagged v0.15.3; old rows flagged 2026-09-30
Found 2026-09-30 19:10 UTC: `/api/health` returned `latest_observation` 2026-10-01 16:00 UTC (age −1,249 min). Query: 28 `hii_load` rows (upstream gauges such as K.12, K.3A, Gt.11, B.8A) with `obs_time` 2026-10-01 16:00 UTC, all from one fetch (one `raw_ref`), all `quality_flag='ok'`; no other source had future rows. The upstream timestamp is impossible (~21 h ahead); the cause upstream is unknown ⚠️. Fix: `parse_waterlevel_load` flags `future_time` when the stamp is > 15 min ahead (the BMA rule, test added); the database upsert never rewrites an existing flag. The 28 existing rows were not edited (a data update was declined by the session's safety check); they stop being in the future at 2026-10-01 16:00 UTC. To clear them earlier: `UPDATE observation SET quality_flag='future_time' WHERE source='hii_load' AND obs_time > now() + interval '15 minutes' AND quality_flag='ok';`. **Done 2026-09-30 ~20:25 UTC with the owner's OK: 26 rows** (the other 2 were already `out_of_range`). v0.16.0: `/api/health` takes the latest `ok` reading no more than 15 min ahead.

### KI-248 — Site-level SEO gaps · 🟢 fixed v0.15.3
`/robots.txt` and `/sitemap.xml` returned 404; no `og:image`, `twitter:card` or JSON-LD (link shares in LINE/Facebook had no picture); the header and footer showed `v0.9.0` until the JS read `/api/health`; the meta description said 12–72 h while the app shows 12–48 h. Fix: both files are served by the app (robots allows the page and keeps `/api/docs`, `/api/openapi.json` and `/api/point` out of indexes; the sitemap has one URL because every view is a `#fragment`), `og:image` 1200×630 (`web/og-image.jpg`, 100 KB, built by `scripts/make_social_images.py` from the real screenshots), `twitter:card=summary_large_image`, `og:site_name/locale`, JSON-LD `WebApplication` (no rating or price claims), a `<noscript>` line, and the server fills `__VERSION__`. Not done on purpose: `hreflang` (one language), per-station pages (the app is a single-page map; would need server-side rendering). ⚠️ Search ranking and share-card rendering were not measured: check a link in LINE/Facebook's debugger after deploy.

### KI-249 — Nationwide gauges: short history, no forecast, a false promise · 🟢 v0.16.0; 🟡 backfill running
Found 2026-09-30 (owner: "Why we have only short history for many nation-wide stations like น้ำพอง บ้านผานกเค้า (E.29) URTU07?"). The 733 gauges outside the focus area only had what `hii_waterlevel` collected since 2026-09-26 (URTU07: 104 hourly rows) because `hii_backfill`, `hii_history`, `qc` and `forecast.run_all` all filtered `in_focus`. Their sheet still promised "การคาดการณ์จะเริ่มเมื่อมีข้อมูลครบ 7 วัน (ราว 3 ต.ค.)", which could never happen, and said "น้ำในคลองต่ำกว่าตลิ่ง 983 ซม." for the Nam Phong river. Fix (D-064): the filters are gone; the notice says what is true ("กำลังดึงข้อมูลย้อนหลังจาก สสน." / "การคาดการณ์จะแสดงเมื่อทดสอบย้อนหลังแล้ว…"); the water word comes from the agency's river name. The backfill runs at 12 gauges per 10 min (~10 h from 20:25 UTC); nationwide skill must be re-measured afterwards (`scripts/backtest_nationwide.py`). ⚠️ Before the backfill ends, the map of a non-Bangkok region is empty by default (the map shows forecastable gauges only; the checkbox shows the rest).

### KI-250 — `/api/stations` hung after the v0.16 deploy · 🟢 fixed v0.16.0
2026-09-30 ~20:47–21:00 UTC: the list (and the home page's data) never answered. `_stations_data` runs inside `_memo` holding `_memo_lock`; the new `_twins()` called `_memo` again and waited forever on the same `threading.Lock`. No DB query was running; the origin itself timed out. Fix: `threading.RLock`; test `test_a_memoised_payload_may_use_another_memoised_value` (RED against the deployed code, GREEN after). Lesson (GUIDELINES §5): a cached payload may call another cached value only through a re-entrant lock; after each deploy, time `/api/stations` at the origin, not only `/api/health`.

### KI-251 — A dead HII host stalled the collector loop · 🟢 fixed v0.16.0
2026-09-30 20:32 UTC: `tiwrm.hii.or.th` stopped accepting connections (curl: connect timeout 10 s; `api-v3.thaiwater.net` answered in 3.8 s). Each chart/map-feed request waited 120 s × 3 attempts, and `hii_history`/`hii_stations` make dozens of them, so the single collector loop (and the 10-min live feed) stood still. Fix: `httpclient` connects with a 10 s timeout (reads keep 120 s) and, after a failed connect, skips that host for 10 min (`_host_down`), so other hosts keep working. Test: `tests/test_httpclient.py`.

### KI-252 — Schema deadlock between two containers at start · 🟢 fixed v0.16.0
2026-09-30 20:25 UTC: the collector and the new forecaster both ran `db.init_schema()` at start; the forecaster's `ALTER TABLE station ADD COLUMN IF NOT EXISTS` (AccessExclusiveLock on `station`) deadlocked with the collector's observation insert (FK to `station`). Postgres aborted one; no data was lost. Fix: only the collector role runs `schema.sql`; the forecaster waits until `forecast_model` exists (`worker.owns_schema`).

### KI-253 — v0.16.0 looked Bangkok-only · 🟢 fixed v0.16.1
Owner 2026-10-01 04:49 UTC: "App shows only Bangkok stations". Measured on the live site (Playwright, 390 × 844 phone and 1440 × 900 desktop): region chips visible without scrolling 3/9 on the phone (9/9 desktop); markers on the map around Chiang Mai with the default chip: 0 on both. Cause: my v0.16.0 design made the map follow the region chip (spec §3.5), and the chip row scrolled horizontally with no cue. The data was complete (e.g. อีสาน 128 gauges with forecasts). Fix: the map shows every gauge in Thailand, the chip only moves the view (`preferCanvas` for ~1,000 markers); chips wrap. After: 10/10 chips visible at 390 px; 45 (phone) / 54 (desktop) gauges around Chiang Mai. Lesson (GUIDELINES §6): a filter must never hide places the user can pan to; validate a new scope with "can a user outside Bangkok find their area in one tap?". Second cause seen on the owner's phone (screenshot 05:03 UTC: v0.16.0 with the Bangkok-only hidden count "(66)" after the fix was live): the page was cached 5 min and an open tab never reloads its code. Fix: `Cache-Control: no-cache` on `/` and a once-per-version self-reload driven by `/api/stats` (deferred while a panel is open).

### KI-254 — Forecast rain only, while it poured · 🟢 fixed v0.16.3
2026-10-01 ~12:20 UTC (19:20 ICT): the owner asked "There is no rain in panel anymore?" and forwarded a user request for Nonthaburi districts during heavy rain. Checked: the forecast was there (Open-Meteo, 4.9–7.2 mm in the next 24 h for Bangkok/Nonthaburi) but the panel had no *measured* rain, although HII rain gauges showed 60 mm in 24 h at HII001 (Bangkok); and v0.16.0 hid the summary rain line outside กทม./ปริมณฑล. Fix: measured rain from the nearest HII rain gauge (≤ 10 km, ≤ 3 h, with its time), heavy measured rain in the headline, rain line per region, every province's rain gauges every 15 min (14-day retention). ⚠️ HII rain readings are hourly and arrive up to ~1 h late: the panel shows the time of the reading so "0 มม." is not read as "no rain now". Nonthaburi: HII has only 3 live water gauges there (BKK007 บางใหญ่, CPY014 ปากเกร็ด/Chao Phraya, BKK018 ไทรน้อย); the 3 Nonthaburi rows in HII's canal feed are dead since 2019 (KI-111) — more gauges need another source (Q41).

### KI-255 — Learned upstream inputs never populated · 🟢 fixed v0.16.6
Found 2026-10-01 14:00 UTC while preparing the nationwide backtest: `collector_state.upstream_learned` was `{}`. The forecaster learned upstream gauges at its first start (2026-09-30 20:33 UTC), when nationwide gauges had ~4 days of history, so none qualified (≥ 180 days of overlap). At each later start the "already learned?" check treated `{}` as learned (`is not None`), and every restart (several on deploy day) reset the daily timer, so it never ran again: no nationwide gauge used upstream inputs in production. Fix: `worker.upstream_due` relearns at start when the result is empty or ≥ 24 h old; `upstream.run_all` deletes the cached backtest (`forecast_model`) of every gauge whose upstream set changed. First run after the fix: 326 gauges, 566 links (mean lag 7 h, mean r 0.76), ~12 min. Lesson: a daily task in a process that restarts often needs its last-run time from the database, not from the process.

### KI-256 — Trend rows flipped direction across horizons · 🟢 fixed v0.16.6
Found 2026-10-01 ~15:00 UTC while re-checking a C1 finding: TRD001 (Trat) read "⬆ เพิ่มขึ้นมาก" at 12 h, "⬇ ลดลงมาก" at 24 h, "⬆ เพิ่มขึ้นมาก" at 48 h. The 12/48 h rows were the backtested model (now with rain and upstream inputs, which saw a rise); the 24 h row had no model direction and followed the measured falling trend (D-060). Across all gauges: 63 of 719 with ≥ 2 directional rows had opposite directions; 43 involved a measured-trend row, 15–19 were model vs model. Fix: `api.reconcile_rows` — a measured-trend row that opposes a direction a model proved at another horizon falls back to the model's own reading ("? ไม่แน่ชัด" or "ทรงตัว" with the model's range). After: 0 such gauges; model vs model (tides, rain arriving later) is left alone. Check C10 in `scripts/ux_consistency.py`.

### KI-257 — BMA canal data stopped upstream while every fetch "succeeded" · 🟡 upstream; disclosed v0.16.8
Found 2026-10-01 ~21:30 UTC during the v0.16.8 consistency run (pin panels listed fewer gauges because stale gauges are hidden there). All 200 BMA gauges' newest reading was 17:10 UTC (00:10 ICT): the flood69 relay (KI-218) answered every 10 min with 198 readings carrying that old timestamp; HII's copy (`canal_waterlevel`) is older still (2026-09-28 13:30); the direct BMA channel via the Thai VPN (`bma_dds`) had failed since 18:41 UTC. No source had fresher data. `source_health` showed success (fetch ok), so neither `/api/health` nor a future uptime monitor would notice. Fix (disclosure): `/api/health.stale_sources` lists live feeds whose newest *reading* is older than 1 h (BMA) / 3 h (HII levels, rain); the summary shows "⚠️ N สถานีไม่อัปเดตเกิน 3 ชม. (ล่าสุด …)" with an ⓘ when ≥ half of the chosen region's gauges are stale. Cards already said "ข้อมูลเก่า"; status turns "ไม่ทราบ" after 24 h. Owner: add the keyword check `"stale_sources":[]` to the uptime monitor (OWNER_ACTIONS UPTIME).

### KI-258 — Rain read as one long sentence; the headline repeated its amounts · 🟢 fixed v0.17.1
Owner, 2026-10-02 (screenshot at 13.7551, 100.6679): "Text for rainfall info are one in a long sentence, not easy to read. Compare to the water level info, it is easier." The rain factor was a bold sentence plus a "·"-joined line ("ฝนตกแล้ว: ฝนปานกลาง 11 มม. ใน 24 ชม. ที่ผ่านมา" / "คาดฝนเล็กน้อย ราว 8 มม. ใน 24 ชม. ข้างหน้า · ชั่วโมงล่าสุด 0.2 มม."), and the headline under the title repeated the measured amount and appended the light-rain word ("ฝนตกแล้ว 11 มม. ใน 24 ชม. ที่ผ่านมา · ระดับน้ำในคลองใกล้จุดนี้มีแนวโน้มลดลงต่อเนื่อง คาดฝนเล็กน้อย"), against D-055. Fix: one helper `rainRows` for the panel and the summary strip, in the water rows' layout — a short bold state ("ฝนตกแล้ว" / "คาดว่าจะมีฝน" / "ไม่มีฝน") with the measured gauge behind its ⓘ; the forecast as a trend-row grid "ใน 24 ชม. [ฝนเล็กน้อย] ราว 8 มม. ⓘ"; what fell as past lines "24 ชม. ที่ผ่านมา: ฝนปานกลาง 11 มม.", "ชั่วโมงล่าสุด: 0.2 มม.". The headline is one clause without amounts: light rain is left to the rows, moderate rain stays as a warning ("…ลดลงต่อเนื่อง แต่คาดฝนปานกลาง อาจมีน้ำขังบนถนนช่วงฝนตก"), heavy measured rain in words. Check C11 in `scripts/ux_consistency.py` (rows present in panel and summary; no "มม." in the headline).

### KI-259 — "ใน 24 ชม." was not read as the future · 🟢 fixed v0.17.2
Owner, 2026-10-02 (screenshot of the pin panel): '"ใน 24 ชม.", "ใน 48 ชม." are not clear. I cannot understand that it is about the future.' "ใน N ชม." means "within N hours" and is used for the past too ("ใน 6 ชม." of street reports), so a row "ใน 24 ชม. ↘ ลดลง ราว −5 ซม." could be read as what already happened — right above "48 ชม. ที่ผ่านมา: ลดลง 17 ซม.". Fix: "อีก N ชม." in row labels (short enough for the 390 px grid; "24 ชม. ข้างหน้า" is ~60 % wider and wrapped), "ในอีก N ชม." in sentences, past always "N ชม. ที่ผ่านมา"/"ล่าสุด". 11 strings in app.js (6), point.py (3), ai.py (2); checker C1 reads "อีก 24". Guard: `tests/test_wording.py`.

### KI-260 — GLM's reasoning could be returned as the answer · 🟢 fixed v0.18.0
Found 2026-10-02 in the AI-assistance probe: glm-5.3-flash always reasons (API code 1210: thinking cannot be switched off; "low", "high" or "max"). With the default effort it spent most of the 500-token budget thinking (9–10 s), and when `content` came back empty `ai.run` returned `reasoning_content` ("The user wants me to …") as if it were the answer. Feedback triage was unaffected in practice (225 labels by glm-5.3-flash, `parse_label` rejects junk), but any free-text use would have shown English reasoning to residents. Fix: `ai._glm_payload` sends `reasoning_effort: "low"` (~1–5 s), `ai._glm_text` returns the content only (None when empty); `ai.run(..., timeout=)` lets the app use 8 s. Tests in `tests/test_ai.py`. glm-4-flash no longer exists on the API (code 1211).

### KI-261 — The plain line called a far gauge "แถวนี้" · 🟢 fixed v0.18.1
Owner, 2026-10-02 (Ko Kret pin, screenshot): headline "ไม่มีสถานีวัดน้ำใกล้พอ ยังสรุประดับคลองไม่ได้", plain line "คลองแถวนี้น้ำใกล้เต็มตลิ่ง แต่ยังบอกไม่ได้ว่าน้ำจะขึ้นหรือลง", and the AI summary "น้ำในคลองแถวนี้ตอนนี้ใกล้จะเต็มตลิ่งแล้ว". My template used the status of the only gauge (6 km away, flagged far) as the state of "คลองแถวนี้"; the AI faithfully reworded it. Owner also: the summary said little although the panel has many numbers. Fix: "แถวนี้" only when the panel's gauges are close and agree; otherwise "สถานีที่ใกล้ที่สุดอยู่ห่าง 6 กม. น้ำที่นั่นต่ำกว่าตลิ่ง 33 ซม. และยังบอกไม่ได้ว่าน้ำจะขึ้นหรือลง"; answers became rule lines that tell the story with the numbers (D-068). Guards: `tests/test_explain.py::test_a_far_gauge_is_never_described_as_here`, checker rule "far gauge called 'here'", UI check C12.

### KI-262 — GISTDA echoes the caller's API key in its responses · 🟡
Found 2026-10-02 (satellite research): every `features/flood/*` response carries `links` (`self`, `alternate`, `next`) whose URLs contain `api_key=<our key>`, although the key was sent in the `API-Key` header (checked by comparison, without printing). Anything that stores, logs or forwards a raw GISTDA response would leak the key. **Rule:** drop `links` on arrival (the research script does; `owner_status.py` already masks the key). No collector stores GISTDA responses yet; a future one must strip `links` before the raw archive. The key was shown once in a private terminal session on the server (not in any file or commit); rotating it at GISTDA is optional.

### KI-263 — Pins upstream of Bangkok used the polder rules · 🟢 fixed v0.18.9
Owner, 2026-10-02 (pin 14.4268, 100.5553, screenshot): "The point is next to station บางปะหัน LBI001, but showed no near station!!" The pin mode (D-059/D-064) was "bkk" whenever the nearest gauge was a focus gauge, and the focus area reaches Nakhon Sawan. In that mode a river gauge never judges the "canals", so LBI001 — 0.1 km away, 63 cm over its bank, forecast to rise — became a side line ("ไม่ใช่ระดับน้ำในคลอง") under "ไม่มีสถานีวัดน้ำใกล้พอ", and the plain line spoke of a canal gauge 7.9 km away. **Fix:** the polder rules apply where the nearest gauge is in กทม. or ปริมณฑล (`point.POLDER_REGIONS`); elsewhere, including Ayutthaya to Nakhon Sawan, the nearest river or stream gauge is the local evidence. Live after the fix: "ระดับน้ำในแม่น้ำล้นตลิ่ง/วิกฤต", "แม่น้ำแถวนี้ล้นตลิ่งแล้ว …". Tests: `test_a_river_gauge_upstream_of_bangkok_is_the_local_evidence`, `test_a_metro_river_gauge_still_never_judges_the_canals`.

### KI-264 — A research run hit Open-Meteo's rate limit; the allowance is shared · 🟡
2026-10-02 ~20:17 UTC: the first GloFAS snapping run asked for 49 points × 1 year per request; Open-Meteo weights a request by locations × two-week chunks (~1,300 calls each) and answered HTTP 429 after 6 gauges. It was the per-minute limit (both APIs answered again within minutes) and the production rain collectors succeeded at 20:47 UTC, but the free non-commercial allowance (KI-106) is shared by everything on this server. **Rule:** research runs fetch a year only for the one cell they need, pause ≥ 10 s between requests, and stay ≲ 1,000 weighted calls per day.

### KI-265 — The top strip's rain took too much space and read as "Bangkok only" · 🟢 fixed v0.18.9
Owner, 2026-10-02 (screenshot): "Review the topbar of UI, it used too much space again!! and it showed specifically for Bangkok, for what?" v0.17.1 had given the strip the pin panel's rain rows (title + row + past line = 3–4 lines). The block followed the region chip in the list (default กทม.), far below the strip, so it read as Bangkok-only. Owner chose **"Only when heavy"**: no rain line unless the chosen region expects or measured heavy rain (TMD ≥ 35.1 mm), then one line ("🌧️ <region>: อีก 24 ชม. ฝนหนัก ราว 48 มม. · …"). Everyday rain stays where it is about a place (pin panel, station sheet). Live check C9/C11 follow the new rule.

