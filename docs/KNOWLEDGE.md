# KNOWLEDGE.md — Bangkok & Central Thailand Hydro Knowledge Base

> **Project:** BKK FloodWatch 2026
> **Audience:** developers, data scientists, operators, AI agents
> **Last updated:** 2026-09-26, during the active Bangkok / Chao Phraya flood
> **Evidence markers:** ✅ confirmed (live data or cited source) · 🟡 from careful research, not re-checked · ⚠️ unverified or indicative, don't hard-code. Evidence for live checks: [research/VALIDATION_2026-09-26.md](../research/VALIDATION_2026-09-26.md)

---

## 1. The "Three Waters" (น้ำสามน้ำ) and the human control boundary

Flooding in Bangkok and the lower Central Plain comes from three drivers interacting nonlinearly. Human operations then shape the result.

```
                            [ 1. Fluvial inflow — น้ำเหนือ ]
                             C.2 → C.13 → C.3 → C.35 → C.29A Bang Sai
                                             │
                                             ▼
                                  Chao Phraya main stem
                                             ▲
                                             │
        [ 3. Pluvial runoff — น้ำฝน ] ──► BMA khlong network ◄── [ 2. Tide/surge — น้ำหนุน ]
          convective bursts              (canals & polders)       Gulf of Thailand
                                             │
                                             ▼
                              [ Human control boundary ]
                   (อุโมงค์ยักษ์ / ประตูระบายน้ำ / สถานีสูบน้ำ / แก้มลิง / dam releases)
```

### 1.1 Fluvial inflow (น้ำเหนือ)
- **Path:** the Ping, Wang, Yom and Nan rivers join at Nakhon Sawan (**C.2**). The flow is regulated at the Chao Phraya Dam, Chai Nat (**C.13**), passes Sing Buri (**C.3**) and Ayutthaya (**C.35**, where the Pasak joins; Pasak release measured at **S.26** below the Rama VI dam), and enters Greater Bangkok at Bang Sai (**C.29A** ✅, the code RID uses in its reports).
- **Travel times** ⚠️ indicative only. In-channel flood waves take roughly a day from C.2 to C.13 and one to two more days to Bang Sai. Overland floodplain flow is much slower (about 120 km in two weeks in 2011) 🟡. **Estimate the lags from data.** HII publishes discharge for C.2, C.13, C.3 and C.35 ✅, so lags can be computed ([APPROACH §7](APPROACH_AND_METHODS.md)).
- **Bang Sai discharge as a risk indicator** ⚠️: news coverage treats about 3,500 m³/s at Bang Sai as the level where Bangkok and its surroundings are at risk ([iGreen, 2022](https://www.igreenstory.co/bangkok-risk-flood-oct-2022/)). The draft thresholds used earlier (<1,500 normal, 1,800–2,200 warning, 2,500–2,800 high, >3,000 critical) are **unsourced** and need calibrating against RID warnings.

### 1.2 Tide and surge (น้ำหนุน)
- **The tide is mixed, mainly diurnal** ✅. At HII CPY015 (สะพานกรุงเทพ, Bangkok), 30 days of observations fit K1 0.45, O1 0.36, M2 0.37, S2 0.27 m, a form factor F = 1.27. This matches the literature: "the Gulf of Thailand is dominated by diurnal tides, and the strongest tidal constituent is K1" ([Ocean Science 2019](https://os.copernicus.org/articles/15/321/2019/)). The **daily high water**, set by the diurnal inequality and the spring–neap cycle, is what residents feel.
- **Seasonal high sea level** 🟡: mean sea level in the upper Gulf is seasonally elevated late in the year, in the same months as the peak river discharge. The magnitude (drafts say +0.30–0.55 m) ⚠️ must be fitted (Sa/Ssa constituents from ≥1 year).
- **Backwater:** high river stages, driven by tide and river flow together, block gravity drainage from the khlongs. When H_river ≥ H_khlong, the gates close and only pumps can drain the city.

### 1.3 Pluvial runoff (น้ำฝน)
- Bangkok is highly impervious. Runoff coefficients are about 0.85–0.92 for the dense core and 0.65–0.75 for suburbs ✅ (standard textbook ranges).
- **Drainage capacity is about 60 mm/h** 🟡 (BMA statements in the news, cited in [methods_survey](../research/methods_survey.md)). Bursts above that cause street ponding (น้ำท่วมขังรอการระบาย).

### 1.4 The control boundary
| Asset | Capacity | Evidence |
|---|---|---|
| Bang Sue drainage tunnel (อุโมงค์ใต้คลองบางซื่อ; 5 m diameter, 6.4 km) | 60 m³/s | ✅ [MGR Online](https://mgronline.com/onlinesection/detail/9600000091782) |
| Rama 9 – Ramkhamhaeng tunnel (9.5 km, outlet at the Phra Khanong pumping station) | 60 m³/s | ✅ [Spring News](https://www.springnews.co.th/keep-the-world/climate-change/852476) |
| Phra Khanong pumping station (total) | drafts say 155–205 m³/s | ⚠️ |
| Don Mueang / Prem Prachakon tunnel | drafts say 30 m³/s | ⚠️ |
| BMA network: 55 flow stations, 270 pump stations | – | 🟡 |
| Dam operations (C.13 release, Pasak Jolasid, diversions to the east and west banks) | announced by RID | 🟡. Store as operation events |

---

## 2. Vertical datums (the number-one failure mode)

| Datum | Abbrev. | Used by | Conversion to Ko Lak MSL | Status |
|---|---|---|---|---|
| Mean Sea Level, Ko Lak 1915 | **m MSL / ม.รทก.** | RID, HII (`waterlevel_msl`, `min_bank`), BMA flood walls | Base datum | ✅ |
| Lowest Low Water | **LLW / ม.ตลน.** | Navy tide tables | H_MSL = H_LLW − ΔZ_station; **ΔZ is TBD per station** | ⚠️. The −1.55/−1.35/−1.25 m values in older docs had **no source** |
| Local gauge zero | gauge / ระดับศูนย์เสาวัด | Some BMA and HII readings (`waterlevel_m`) | H_MSL = H_gauge + offset_station | ⚠️ per station (the "≈ −1.00 m" claim is unverified) |
| EGM2008 geoid heights | – | **Copernicus DEM, FABDEM, Open-Meteo elevation** | Z_KoLak = Z_EGM2008 + δ_local (δ is a local offset to determine) | ✅ that these DEMs use EGM2008. The earlier docs wrongly said "ellipsoidal" |
| WGS84 ellipsoidal heights | – | Raw GNSS | Z_EGM2008 = h − N (geoid undulation) | Only relevant for GNSS survey data |

> [!CAUTION]
> Never subtract a DEM elevation from a gauge reading without first putting both on **Ko Lak MSL**. A 1 m datum error reverses the answer.

**Datums change over time** ⚠️. Bangkok has a history of **land subsidence**, so benchmarks, bank levels and DEM-derived ground heights drift over the years. Version station metadata with effective dates, and never mix elevations from different survey years without checking.

---

## 3. River topology and stations

### 3.1 Chao Phraya chain (upstream → downstream)
Chainage values (km from the mouth) come from the drafts and are **approximate ⚠️**. Measure them along the river centreline in Phase 0/2.

```
C.2  ค่ายจิรประวัติ, Nakhon Sawan ─► C.13 ท้ายเขื่อนเจ้าพระยา, Chai Nat ─► C.3 บ้านบางพุทรา, Sing Buri
  ─► C.35 บ้านป้อม, Ayutthaya (+ Pasak via S.26) ─► C.29A Bang Sai (≈ km 112) ─► CPY014 สะพานนวลฉวี, Nonthaburi
  ─► C.12 กรมชลประทานสามเสน ─► Memorial Bridge / Pak Khlong Talat (≈ km 48; code ⚠️ C.4 vs C.22)
  ─► CPY015 สะพานกรุงเทพ ─► BKC003 ปตร.คลองลัดบางยอ 1 ─► Fort Phra Chulachomklao (mouth, ≈ km 0)
```

### 3.1b HII has two station catalogues (verified 2026-09-26)
| Catalogue | Endpoint | Stations | Coordinates | Bank / ground | History |
|---|---|---|---|---|---|
| Latest-values feed | `api-v3…/public/waterlevel_load` | 805 (nationwide) | ✅ | ✅ | via `waterlevel_graph` (numeric id): **up to 365 days, hourly** (verified 2026-09-26) |
| **Chart site list** | `tiwrm…/queryStation?prov=<Thai province name>` (e.g. `prov=กรุงเทพมหานคร`; numeric codes return `[]`) | **+162 stations** in our 18 nearest provinces that the feed lacks (BKK004/007/011/012, `ATG*`, `MOU*`, …) | ❌ (only in the map feed for 107 stations: `json/telemetering/wl/warning`) | partly (chart `0/0` = unknown) | `getGraphFirst/{code}` ≈ 30 days, 10 min. **HTTP 500 for many codes** ([KI-207](KNOWN_ISSUES.md)) |

The chart list includes the **Fort Chula tide gauge (GLF001 ป้อมพระจุลจอมเกล้า)** and **Bang Sai (CPY013 บางไทร)**: the two key stations missing from the main feed. Their history isn't retrievable: `getGraphFirst` and `POST /getGraph` both answer HTTP 500, and `queryStation`'s `water1` is frozen ([KI-207](KNOWN_ISSUES.md)). The lists also contain test gauges (`TEST*`), which are excluded (KI-209). Coverage now: **111 focus stations** (2026-09-26 11:10 UTC; Samut Sakhon and Nakhon Pathom added, D-023; GLF002 shown with its values hidden, `TEST*` excluded): 96 placed (82 by HII, 14 approximately by OSM), 15 listed without a position (D-024). By province: Ayutthaya 31, Nakhon Sawan 16, Chai Nat 13, Sing Buri 10, Bangkok 10, Pathum Thani 8, Nakhon Pathom 7, Samut Prakan 5, Ang Thong 4, Samut Sakhon 3, Nonthaburi 3. Earlier split, superseded (Ayutthaya 32, Nakhon Sawan 16, Chai Nat 13, Bangkok 13, Sing Buri 10, Pathum Thani 8, Samut Prakan 5, Ang Thong 4, Nonthaburi 3).

### 3.2 Station metadata (HII live, 2026-09-26)
Bank = HII `min_bank` (m MSL). This is the operational reference; older DWR report values differ by up to 1.5 m (see [validation §E](../research/VALIDATION_2026-09-26.md)).

| Code | Name (HII) | Lat, Lon | Bank (m MSL) | Snapshot (26 Sep) | Agency | Role |
|---|---|---|---|---|---|---|
| C.2 | ค่ายจิรประวัติ, นครสวรรค์ | 15.67059, 100.10936 | 25.70 | WL 22.25, **Q 1,824 m³/s** | RID | Fluvial trigger (days ahead) |
| C.13 | ท้ายเขื่อนเจ้าพระยา, ชัยนาท | 15.16384, 100.18792 | 16.34 ⚠️ (other sources: 17.21, 15.77) | WL 14.40, **Q 1,912** | RID | Dam release boundary |
| C.3 | บ้านบางพุทรา, สิงห์บุรี | 14.89868, 100.40186 | 13.20 | WL 10.72, Q 1,946 | RID | Mid-river |
| C.35 | บ้านป้อม, อยุธยา | 14.36910, 100.52873 | 4.35 | **WL 4.34 (at bank)**, Q 1,156 | RID | Ayutthaya |
| C.36 | บ้านบางหลวงโดด, อยุธยา | 14.41588, 100.44080 | 4.30 | **WL 5.48 (above bank)**, Q 629 | RID | Bang Ban |
| S.26 | ท้ายเขื่อนพระรามหก (Pasak) | 14.56012, 100.71994 | 7.20 | WL 5.82, Q 470 | RID | Pasak inflow |
| C.29A | Bang Sai | – | – | **Not in HII feed** | RID | Gateway to Bangkok ⚠️ feed needed |
| CPY014 | สะพานนวลฉวี, นนทบุรี | 13.94749, 100.53507 | 2.50 | WL 1.93 | HII | Nonthaburi river |
| C.12 | กรมชลประทานสามเสน, กทม. | 13.78815, 100.50915 | 2.26 | WL 1.24 | RID | Bangkok river |
| CPY015 | สะพานกรุงเทพ, กทม. | 13.70030, 100.49277 | 2.16 | WL 0.34 | HII | Bangkok river; tide reference |
| BKK008 | คลองแสนแสบ บางกะปิ | ⚠️ TBD | **0.88** (chart API) | **1.18 m (above bank)** | HII | East Bangkok khlong (user's example) |
| AIT001 | อโศก (คลองแสนแสบ) | 13.74325, 100.56216 | 2.39 | WL 1.77 | HII | Saen Saep, central |
| BKK021 | **คลองลาดพร้าว วัดบางบัว** | 13.85402, 100.58746 | **2.20** | **WL 2.82 (situation 5, ล้นตลิ่ง)** | HII | North Bangkok khlong (user's example) |
| GLF001 (Fort Chula) | ป้อมพระจุลจอมเกล้า, สมุทรปราการ | ⚠️ not in map feed | – | latest 0.03 (queryStation `water1`); chart data HTTP 500 | HII chart list | Seaward boundary / tide gauge ⚠️ history needed |
| CPY013 | บางไทร (Bang Sai), อยุธยา | ⚠️ | – | latest 1.46 (`water1`); chart HTTP 500 | HII chart list | Gateway to Bangkok ⚠️ history needed |

---

## 4. The Bangkok polder system (ระบบพื้นที่ปิดล้อม)
1. **Flood walls** 🟡: along the Chao Phraya, walls are around 2.8–3.0 m MSL (Pak Khlong Talat: wall 3.0, warning 2.8; Khlong Bang Khen Mai: 3.5 / 3.3, per BMA public reports). Communities **outside** the walls (ชุมชนนอกคันกั้นน้ำ) flood at much lower river stages.
2. **Pre-storm drawdown:** BMA pumps canals down before forecast rain to create storage 🟡. The exact target levels (drafts: −0.2 to −0.8 m MSL) are ⚠️.
3. **Gate logic:** gravity outflow only when H_khlong > H_river; otherwise the gates close and the pumps take over.
4. **Spatial structure:** each polder (drainage zone) has its own khlongs, pumps and outlets. A resident's flood risk depends on **which polder** they're in, not on straight-line distance to a gauge ([APPROACH §2](APPROACH_AND_METHODS.md)).
5. **Bangkok is not flat, and neither are its protection heights** ✅ (HII metadata, 2026-09-26). Bank levels of gauges in Bangkok, Nonthaburi, Samut Prakan and Pathum Thani range from **0.43 m (BKK017, Khlong Hua Takhe) to 4.56 m MSL (CAN001)**. River-side banks are 2.16–2.50 m (CPY015, C.12, CPY014); gates on the same cut differ (BKC003 1.51 vs BKC004 0.91). The 20 metro gauges with coordinates are **7.7 km apart** (median nearest-neighbour). So a gauge describes its own channel, not the land around it ([APPROACH §2.9](APPROACH_AND_METHODS.md), D-019).

8. **BMA's "critical" tracks street flooding better than the bank** ✅ (our data, 2026-09-26 18:40 UTC): near flooded streets 60 % of BMA gauges were over BMA critical vs 18 % over the bank; near quiet streets 38 % vs 5 %. Reading: streets flood when the canal is too full to take the drains' water, long before it overtops its wall. At 38 of 42 gates the canal side is held a median 0.64 m below the river side (pump-managed polders).
7. **Canal level and street flooding are different quantities** ✅ (our data, 2026-09-26 18:10 UTC): 34 of 188 fresh BMA gauges were below their bank while ≥ 5 Traffy flood reports lay within 1 km (Saen Saep at Bang Kapi: 35 cm below bank, 35 reports in 12 h). Street flooding in Bangkok is usually pluvial (rain beyond pipe and pump capacity); canals are drawn down to receive it (item 2). A low canal therefore does not mean a dry street, and the UI must never call it "normal" (D-036).
6. **BMA's gauge network** ✅ (BMA KlongMap via the flood69 relay, 2026-09-26): 199 gauges with coordinates (135 khlong level gauges, 45 gates with pump stations reporting the level **inside** (`wl_in`) and **outside** (`wl_out01`) the gate, 19 others), plus 6 flow stations (discharge, velocity) and 12 Khlong Prem pump sites; readings every 5 min. Banks range from about 0.5 m to 3 m. BMA's `warning`/`critical` values are ~0.4–1.2 m, often far below the bank (e.g. 0.70 vs 1.91 m), so they look like drainage **operating targets**, not flood thresholds ⚠️ (KI-215). BMA and HII gauges at the same spot differ by 0.3–0.6 m (KI-217).

---

## 5. The 2026 event (as of 26 Sep)
From news collected in [sources_survey §1](../research/sources_survey.md) 🟡, now **corroborated by HII live data** ✅:
1. **Urban pluvial crisis (East Bangkok):** 99 mm/24 h (Min Buri) and 154 mm/24 h (Khlong Sam Wa). Prawet Burirom and Saen Saep canals at critical levels. BMA declared disaster zones in Nong Chok, Suan Luang and Khan Na Yao; DDPM sent a Cell Broadcast on 26 Sep. HII shows BKK008 (Saen Saep) and BKK021 (Lat Phrao) **above bank**.
2. **Upstream flood wave:** C.2 carried 1,737 m³/s on 23 Sep, and RID announced raising the C.13 release to ≤2,000 m³/s. **HII on 26 Sep 12:00: C.2 1,824, C.13 1,912, C.3 1,946 m³/s. C.35 at bank, C.36 1.2 m above bank.**

**Lesson:** East Bangkok needs a **rain + polder storage** model; riverside Bangkok and Ayutthaya need **upstream routing + tide**. One model can't serve both.

---

## 6. Communicating with citizens

### 6.1 Depth vocabulary (UX bands, not physical claims)
| Depth | Thai landmark wording | Level |
|---|---|---|
| 0 cm | ผิวถนนแห้ง สัญจรได้ตามปกติ | ปกติ (เขียว) |
| 1–10 cm | น้ำขังผิวถนน สัญจรได้ด้วยความระมัดระวัง | เฝ้าระวัง (เหลือง) |
| 11–20 cm | เสมอระดับทางเท้า รถเล็กควรชะลอ | เตือนภัย (ส้ม) |
| 21–35 cm | เกินทางเท้า ประมาณครึ่งล้อ รถเก๋งเสี่ยง | เตือนภัยสูง (ส้มเข้ม) |
| 36–50 cm | น้ำเริ่มเข้าบ้าน ห้ามรถเล็กผ่าน | วิกฤต (แดง) |
| > 50 cm | ระดับเข่าขึ้นไป พิจารณาอพยพ | ฉุกเฉิน (แดงเข้ม) |

Depth at a location is always shown as a **probability category**, never an exact number (KI-202, [APPROACH §13](APPROACH_AND_METHODS.md)).

**Body-landmark bands for user reports** (feedback form, [APPROACH §3.5](APPROACH_AND_METHODS.md)): ไม่มีน้ำท่วม · ข้อเท้า (≤ 20 cm) · เข่า (~50 cm) · เอว (~1 m) · สูงกว่าเอว. These are easier to judge while standing in water than centimetres. They are coarse labels for validation, not measurements.

### 6.2 Official contacts (re-check every number before the UI launches)
| Service | Number / channel | Status |
|---|---|---|
| BMA hotline (กทม.) | **1555** | ✅ [Thairath](https://www.thairath.co.th/lifestyle/life/2517456) |
| BMA Flood Control Center (ศูนย์ป้องกันน้ำท่วม กทม.) | **02-248-5115** (24 h) | ✅ same source |
| DDPM (ปภ.) | **1784** | 🟡 widely published |
| RID (กรมชลประทาน) | **1460** | ⚠️ not confirmed in this run |
| Emergency medical (สพฉ.) | **1669** | 🟡 widely published; shown when a feedback note sounds urgent |
| Police | **191** | 🟡 widely published; same |
| Traffy Fondue | LINE `@traffyfondue` | 🟡 |
| HII | thaiwater.net | ✅ |

---

## 7. Sourcing strategy (keyless first, collected on the server)
"Zero-key" means **no gated API keys are needed for v1**. It does **not** mean the app runs in the browser.

| Domain | v1 keyless route (collected by our VPS) | Optional upgrade | Fallback |
|---|---|---|---|
| Rain and weather | Open-Meteo forecast + ensemble ✅ | TMD 🔑 | HII rain gauges |
| River and canal levels | HII public JSON + chart XHR ✅ | HII formal agreement; BMA feed | Last known value + degraded mode |
| Bang Sai, Memorial Bridge | RID pages 🟡 | RID telemetry service | Routing from C.35 + S.26 |
| Tide | Navy tables 🔴 (URL moved) | – | **Own harmonic fit on HII tidal stations** ✅ feasible |
| Elevation | DEM files (probabilistic) | GISTDA/BMA survey data | User-entered floor height |
| Flood extent | Copernicus GFM (free account) | GISTDA 🔑 (key configured in .env) | – |
| Citizen reports | Traffy public ✅ | Agreement with BMA/NECTEC | – |
| Feedback note triage | Deterministic keyword rules ✅ | GLM (`glm-5.3-flash` 🔑 in .env) / Workers AI | Instant hotline triggers (1669/1784/191) |
| Storage & backup | Local VPS disk (`data/raw_archive` + Postgres) ✅ | Nightly local snapshots | R2 disabled by owner choice (D-029) |

---

## 8. Glossary
| Thai | English | Note |
|---|---|---|
| ม.รทก. | m above MSL (Ko Lak) | Base datum |
| ม.ตลน. | m above Lowest Low Water | Navy tide tables |
| ระดับตลิ่ง | Bank level | HII `min_bank`; the red line on HII charts |
| ล้นตลิ่ง / ต่ำกว่าตลิ่ง | Above / below bank | HII `diff_wl_bank_text` |
| น้ำหนุน | Tidal backwater / high tide | |
| แก้มลิง | Retention basin | |
| ปตร. (ประตูระบายน้ำ) | Sluice gate | e.g. BKC003 |
| อุโมงค์ยักษ์ | Giant drainage tunnel | |
| ลบ.ม./วินาที | m³/s | |
