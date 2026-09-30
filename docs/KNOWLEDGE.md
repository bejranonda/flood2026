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

13. **Across all 310 gauges and 67 Bangkok pins the UI now tells one story** ✅ (consistency proof 2026-09-28 20:10 UTC, KI-244): list, sheet and pin panel agree for every gauge; before the fixes 7 of 67 pins had a headline contradicting the rows below it.
12. **Whether a canal's trend continues is close to a coin flip** ✅ (45 days to 2026-09-28, all focus gauges): a steady 24 h fall continued 12 h later 59–64 % and 24 h later 53–55 % of the time; large falls (≥ 20 cm/24 h, pump drawdowns) 47–49 %. Rivers carry momentum: 70–88 % for falls, 79–96 % for rises. Per gauge, 22 of 166 canals continue ≥ 70 % at 24 h.
11. **Some BMA loggers stick at exactly 1.00 m** ✅ (2026-09-28, KI-241): four gauges at 1.00 m and one at 0.40 m for 48 h, WL.KPM.03 at 1.00 m in 94 %; ⚠️ a placeholder value is our reading, not BMA's statement.
10. **After the peak, many canals recede slowly and steadily** ✅ (live API 2026-09-28 06:45 UTC, KI-240): 48 gauges fell ≥ 5 cm in 24 h along a straight line (R² ≥ 0.7), e.g. BKK021 −4.6 cm (still 54 cm over its bank), WL.BPM.03 −22 cm, WL.CKS.01 −91 cm; yet "recent slope continues" forecasts lose to "no change" at 24 h in the 45-day backtest (e.g. WL.BPM.03 RMSE 0.111 vs 0.099 m), so the fall is reported as a measurement, not a forecast.
9. **Some BMA gauges sit next to pumps or have faulty sensors** ✅ (our data, 2026-09-27/28, KI-237): pump cycling draws the level down 0.5-1 m in 10-20 min and back (WL.BNJ.02, WL.BSK.01, WL.LSM.01); WL.SSB.08 jumped ±0.8 m every 5-15 min for hours, then was calm for 12 h; loggers drop to exactly −2.00 m for one or two readings (WL.LPT.03, WL.KPM.05); WL.MSW.03's `wl_in` switched to another smooth series for 2 h 20 min. On 2026-09-28 10-11 of ~300 focus gauges were erratic in any 24 h, and 2,006 dropout readings were found in 45 days at 54 gauges.

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

### 6.3 Favicon and Brand Visual Standards (D-039)
- **Brand Emoji:** `🌊` (Great Wave) in `🌊 BKK FloodWatch`.
- **Favicon Motif:** Bold white surge wave over cyan water on vibrant royal blue squircle tile (`#0284c7` to `#0369a1`).
- **Tab scale rule:** 16×16 CSS pixels. No micro-details (dots, rings, ticks). Fill the canvas footprint to avoid narrow empty margins.
- **Contrast standard:** > 5:1 contrast against both dark-mode tabs (`#202124`) and light-mode tabs (`#dee1e6` / `#ffffff`).
- **Mobile PWA / Touch:** 180×180 and 192×192 assets use solid background canvases so iOS does not render transparent areas as black.

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

## 9. Thailand beyond Bangkok (facts checked 2026-09-27)
Live-probed facts for the national scope (D-044); details and evidence in [research/VALIDATION_2026-09-27_nationwide.md](../research/VALIDATION_2026-09-27_nationwide.md). Research claims not yet checked are marked ⚠️.
- **Gauges:** HII `waterlevel_load` 805 stations nationwide (HII 330, RID 315, FOP 89, EGAT 71). RID Telerid lists 921 stations. DWR EWS has 2,275 village stations (1,819 rain, 455 level, with soil moisture); 783 show status `9` (probably offline ⚠️).
- **Official thresholds:** HII FEWS lists alarm/warning/critical for 66 level stations (m MSL; Northeast 26, Chao Phraya 20, South-West 12, East 8) and for 87 RID discharge stations (m³/s). C.13 below the Chao Phraya Dam: **2,176 / 2,448 / 2,720 m³/s**; C.2 Nakhon Sawan: **2,988 / 3,362 / 3,735 m³/s**.
- **Reservoirs:** 50 large dams report daily (storage, inflow, release, spill; 14 at ≥ 80 % storage and none spilling on 2026-09-27); 862 medium reservoirs, of which 448 report; 60 small-dam telemetry stations give level against spillway. **No rule curves** in any feed reached.
- **Tide:** Navy predictions for **28 stations** on both coasts (Gulf and Andaman), daily high/low and 4-hourly values, via HII FEWS.
- **Satellite:** GISTDA flooded H3 cells nationally (~50,000 over 7 days on 2026-09-27) with exposure; empty over central Bangkok despite street flooding (radar limitation ⚠️).
- **Flood types differ by region** (research, ⚠️ not independently checked): flash floods in the North and on the Western range; slow, long floods with backwater in the Mun/Chi basins and against the Mekong; regulated floods below the large dams; coastal/lagoon effects in the South (Songkhla Lake). Main season Jul–Oct; the Gulf-side South mainly Oct–Jan.
- **Rain words:** TMD rain-amount categories ฝนเล็กน้อย 0.1–10.0 · ฝนปานกลาง 10.1–35.0 · ฝนหนัก 35.1–90.0 · ฝนหนักมาก ≥ 90.1 mm (tmd.go.th "เกณฑ์อากาศ", read 2026-09-27; the page gives no period ⚠️). They are national words for amounts, not local flood thresholds (KI-224).

## 10. Forecast Presentation & UI Principles (v0.6.4 / v0.6.5, D-048, D-049)
UX principles established through visitor testing during the 2026 flood season:
- **Zero-crossing interval phrasing:** Conformal prediction intervals crossing zero under steady conditions (e.g. `[-0.11, +0.17] m`) must not be phrased as contradictory words ("ลด 11 ถึงเพิ่ม 17 ซม."). Use `ทรงตัว (อาจแกว่งตัว -11 ถึง +17 ซม.)`.
- **Single ⓘ confidence symbol:** Citizens perceive "มั่นใจต่ำ" as a severe system error. Confidence is presented as a single circular `ⓘ` button color-coded by model class (sky-blue `.conf-medium` for tide-calibrated models beating persistence >10%; slate-gray `.conf-low` for baseline persistence/statistical models). On desktop, hover displays the backtest summary. On touchscreens, tap triggers a non-blocking toast.
- **Progressive technical disclosure:** The primary line prioritizes actionable freshness (`ข้อมูล 27 ก.ย. 18:40 (15 นาทีที่แล้ว)`). Technical surveying datums (`ม.รทก.`) are tucked into an adjacent `[ม.รทก. ⓘ]` button.
- **Collapsible visual metadata:** Dense textual legends (such as 3-line SVG chart curve explanations) are collapsed into `<details class="chart-legend"><summary>ℹ️ สัญลักษณ์กราฟ</summary>...` to preserve vertical screen height on mobile devices.


## 10. Forecast horizons and official forecasts (checked 2026-09-27)
- **Our model's reach:** at 12 h, 37 of 102 gauges beat "no change" by ≥ 30 %; at 24 h 18; at 48 h 7 (tidal river/estuary only). Median 90 % range: 46 cm at 12 h, 47 cm at 24 h, 80 cm at 48 h, 109 cm at 72 h. Bangkok canal gauges: no skill at any horizon yet (no rain/upstream inputs; BMA gauges have < 2 days of history).
- **HII's official forecast:** hourly, 7 days ahead, per station at `fews2.hii.or.th/model-output/data_portal/hii_waterlevel/forecast/{CODE}.txt` (m MSL) and `…/rid_discharge/forecast/{CODE}.txt` (m³/s); issued ~17:00 ICT (Last-Modified 10:05 UTC on 2026-09-27); near Bangkok only CPY011, CPY014, PAS008 and discharges C.13/C.2/C.3/C.7A/C.35. The C.13 dam release is held constant (1,950 m³/s). Datum m MSL and Thai time, matching our observations within 1–4 cm around the issue time.
- **Rain archives for training:** Open-Meteo `historical-forecast-api` (stitched early hours, ≈ known rain) and `previous-runs-api` (`*_previous_day1..` = forecasts issued 1–2 days earlier), keyless for non-commercial use, back at least to 2025-09.
- **ONWR National Thai Water** (`nationalthaiwater.onwr.go.th/waterlevel`, `/dam`) is a front end over the same HII `api-v3` endpoints we use; its own API `ntw-admin.onwr.go.th/api/v1/public/{disaster,reportwater/events}` answers only from a Thai IP (8 event reports in 2026, none in Bangkok; disaster list empty on 2026-09-27).
- **Since v0.8.0 (D-052):** the `star` method (own tide/trend + 2 upstream Chao Phraya gauges + C.13 release + forecast rain) wins the backtest at ~50–60 of ~100 gauges per horizon; gauges with 48 h skill ≥ 0.3 went 8 → 35. Biggest gains on the non-tidal upper river (Ayutthaya 48 h RMSE 27 → 17 cm).

## 11. BMA Canal Telemetry Architecture & Coding Systems (v0.9.0, D-053)
> **Correction (2026-09-27, D-054):** the `BKK*` gauges below are **HII's own** gauges, not BMA's, and most had a year of hourly history before v0.9.0. BMA's own `WL.*` gauges have history in HII too: `api-v3…/thaiwater30/public/waterlevel_graph?station_type=canal&station_id={HII canal id}` returns 15-min values back to at least 2024-01, **identical to the relay** (46 matching times on 2026-09-27, difference 0.0 m). The datum of BMA gauges is not documented; treat "BMA local datum" as ⚠️ unverified. **Coverage (2026-09-27 backfill):** 162 of our 199 relay gauges are in HII's canal feed and got one year of hourly history; **37 are not in HII's feed at all** (ordinary canal gauges such as WL.AJP.01, WL.ANX.01, WL.BKT.01 — probably newer), so their history starts with our relay polling on 2026-09-26.
- **BMA Station Naming Schema (`WL.*`):**
  - Prefix `WL`: Water Level (สำนักการระบายน้ำ กทม.).
  - 3-letter canal acronym: e.g. `KTY` (คลองเตย), `AJP` (อาจารย์พร), `BKY` (บางเชือกหนัง), `KLA` (คลองลาว), `LPW` (ลาดพร้าว), `SSB` (แสนแสบ), `SST` (สองสายใต้), `TWW` (ทวีวัฒนา), `LPT` (ลำปลาทิว).
  - 2-digit sequence: `.01`, `.02` along the canal chain.
  - Total count: 199 telemetry stations across Bangkok (135 canal gauges, 45 pump gates, 19 flow/special sites).
- **HII Bangkok Telemetering Schema (`BKK*`):**
  - Prefix `BKK`: Bangkok telemetering stations operated or ingested by HII / ThaiWater.
  - Numbers: `BKK001` through `BKK021`.
  - **Key architectural discovery:** HII maintains parallel telemetry gauges matching primary BMA canal reaches. Unlike BMA's direct portals (which are geo-blocked, blackhole VPN relays, and only offer real-time snapshots), HII provides **30 days of 10-minute resolution telemetering history** (4,310+ points) via `https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{CODE}` without any authentication or geo-blocking.
- **Cross-System Station Equivalents:**
  - `BKK001` (คลองลาดพร้าว ท้าย ปตร.คลอง 2) ↔ `WL.SST.01` (60 m distance).
  - `BKK020` (คลองลาดพร้าว ปากคลอง 2 สายใต้) ↔ `WL.ANX.01` (610 m distance).
  - `BKK021` (คลองลาดพร้าว วัดบางบัว) ↔ `WL.BBU.01` (460 m distance).
  - `BKK008` (คลองแสนแสบ บางกะปิ) ↔ `WL.SSB.06` (80 m distance) / `WL.SSB.07`.
  - `BKK005` (คลองภาษีเจริญ เพชรเกษม 69) ↔ `WL.TWW.05` (20 m distance).
  - `BKK009` (คลองลำปลาทิว ลาดกระบัง) ↔ `WL.LPT.03` (10 m distance).
- **Datum separation reminder (KI-217):** BMA gauges are referenced to local zero/datum, while HII stations are referenced to Mean Sea Level (m MSL / Ko Lak datum). Always display with proper unit attribution (`ม. (หมุด กทม.)` vs `ม.รทก.`).

- **Trend display rule (v0.11, D-056):** a chip states a direction only where the backtest chose a real model (not "no change") at that horizon. On 2026-09-27 most BMA canal gauges therefore show "? ไม่แน่ชัด" at 24 h with their error range — pumps and gates, not tide or rain, drive them (research §10).

- **Site head and crawlers (v0.15.3, KI-248, verified live 2026-09-30):** `/robots.txt` and `/sitemap.xml` are served by the app (200, `text/plain` / `application/xml`); `og:image` is `/static/og-image.jpg` (1200×630, 100 KB); the header/footer version is filled by the server (`__VERSION__`). `#fragment` views are not separate pages for search engines, so the sitemap lists only the home page. See [APPROACH §21](APPROACH_AND_METHODS.md).
- **HII can stamp readings in the future (KI-247, 2026-09-30):** one `waterlevel_data` fetch carried 28 gauges at 2026-10-01 16:00 UTC, ~21 h ahead of the fetch; cause unknown ⚠️. Such rows are flagged `future_time` (15-min tolerance, as for BMA).
