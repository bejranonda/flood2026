# KNOWLEDGE.md — Bangkok & Central Thailand Hydroinformatics Knowledge Base

> **Project:** Bangkok & Central Thailand Flood Intelligence & Hydrodynamic Forecasting Platform (2026)  
> **Audience:** Hydroinformaticians, Software Engineers, Data Scientists, and Operations Teams  
> **Last Updated:** 26 September 2026 (During Active Bangkok & Chao Phraya Basin Flooding)

---

## 1. Domain Foundation: The "Three Waters" Triad (น้ำสามน้ำ)

Flooding in the Bangkok Metropolitan Region (BMR) and the lower Central Plains is an estuarine hydraulic challenge governed by the non-linear interaction of three independent hydrodynamic forces:

```
                            [ 1. Fluvial Upstream Inflow ]
                                (น้ำเหนือ: C.2 / C.13 / C.29)
                                             │
                                             ▼
                                  Chao Phraya River Mainstem
                                             ▲
                                             │
        [ 3. Pluvial Runoff ]  ──►  BMA Khlong Network  ◄──  [ 2. Tidal Surge ]
          (น้ำฝน: Convective)          (Canals & Polders)      (น้ำหนุน: Gulf of Thailand)
                                             │
                                             ▼
                                [ Human Control Boundary ]
                           (อุโมงค์ยักษ์ / ประตูระบายน้ำ / แก้มลิง)
```

### 1.1 Fluvial Inflow (น้ำเหนือ)
* **Origin:** Rainfall in the Northern basins (Ping, Wang, Yom, Nan) converges at Nakhon Sawan (station **C.2**), passes into Chai Nat where discharge is regulated by the Chao Phraya Dam (**C.13**), joins the Pa Sak River at Ayutthaya, and enters Bangkok via Bang Sai (**C.29 / C.29A**).
* **Behavior:** Slow-moving flood waves with a travel lag of **8 to 30 hours** from Bang Sai to central Bangkok, and **2 to 4 days** from Nakhon Sawan.
* **Critical Discharge Thresholds at Bang Sai (C.29):**
  * `< 1,500 m³/s`: Normal dry/early monsoon flow; gravity drainage operates unimpeded.
  * `1,800 – 2,200 m³/s`: Warning stage; low-lying communities outside floodwalls in Nonthaburi and Ayutthaya experience inundation.
  * `2,500 – 2,800 m³/s`: High alert; floodwalls in Bangkok (typically 2.80–3.00 m MSL) are tested, especially during high tides.
  * `> 3,000 m³/s`: Critical flood risk comparable to 2011/2021; extensive out-of-dike overtopping.

### 1.2 Marine Tidal Surge & Backwater (น้ำหนุน)
* **Origin:** Mixed diurnal and semi-diurnal tides from the Gulf of Thailand entering at the river mouth (Fort Chulachomklao, Samut Prakan, km 0.0).
* **Seasonal Amplification:** During the Northeast Monsoon (October–December), strong southerly and easterly winds push Gulf waters northward into the Bight of Bangkok, causing a seasonal sea-level anomaly of **+0.30 to +0.55 m MSL**.
* **Backwater Effect:** High tides travel upriver past Memorial Bridge (km 48) and Nonthaburi (km 65). When the river level exceeds canal levels ($H_{\text{river}} > H_{\text{khlong}}$), gravity flap gates automatically slam shut, preventing natural discharge into the river.

### 1.3 Pluvial Urban Runoff (น้ำฝน)
* **Origin:** Intense tropical convective storms and monsoon troughs dropping 80–150+ mm within 1–3 hours directly onto the urban core.
* **Imperviousness:** Bangkok is 85–90% concrete and asphalt ($C \approx 0.85–0.92$), leaving negligible natural soil infiltration.
* **Drainage Limit:** Bangkok's standard subterranean pipe network is engineered for a rainfall intensity of only **50 to 60 mm/hr**. Any burst exceeding 60 mm/hr triggers immediate street-level ponding (*น้ำท่วมขังรอการระบาย*).

### 1.4 The Control Boundary (การบริหารจัดการน้ำ)
* **Sluice Gates (ประตูระบายน้ำ):** Control flow between canals and the main river.
* **Giant Drainage Tunnels (อุโมงค์ระบายน้ำยักษ์):** High-velocity subterranean pressure tunnels bypassing congested canal networks directly to the river:
  * **Bang Sue Tunnel:** $60\text{ m}^3/\text{s}$ capacity (serving Chatuchak, Bang Sue, Din Daeng, Phaya Thai).
  * **Rama IX – Ramkhamhaeng Tunnel:** $60\text{ m}^3/\text{s}$ capacity (serving Saen Saep and Lat Phrao).
  * **Phra Khanong Pumping Complex:** $155–205\text{ m}^3/\text{s}$ total pumping capacity discharging Khlong Phra Khanong/Tan into Chao Phraya.
  * **Don Mueang / Prem Prachakon Tunnel:** $30\text{ m}^3/\text{s}$ under active development.
* **Retention Basins (แก้มลิง):** Natural and engineered holding reservoirs buffering peak runoff volumes.

---

## 2. Hydrographic Datums & Geodesy Standards

A primary failure mode in Thai hydroinformatics is the improper mixing of vertical datums. This project strictly mandates the following conversions:

| Datum Name | Abbreviation | Reference Point | Usage / Where Found | Translation to Ko Lak MSL |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Sea Level (Ko Lak 1915)** | **m MSL / ม.รทก.** | Ko Lak Lighthouse, Prachuap Khiri Khan | Official Thai standard (RID, HAII, BMA floodwalls, GISTDA) | $H_{\text{MSL}} \equiv H_{\text{standard}}$ (Base Datum) |
| **Lowest Low Water** | **LLW / ม.ตลน.** | Astronomical lowest low water | Royal Thai Navy Hydrographic Dept annual tide tables | $H_{\text{MSL}} = H_{\text{LLW}} - \Delta Z_{\text{station}}$ (Check station table; typically $\Delta Z \approx 1.20 - 1.60\text{ m}$) |
| **BMA Staff Gauge Zero** | **Staff / ระดับศูนย์เสาวัด** | Local benchmark peg at canal division | DDS canal gauge indicators in ASPX tables | $H_{\text{MSL}} = H_{\text{staff}} + Z_{\text{zero\_offset}}$ (Often $-1.00\text{ m}$ depending on canal division) |
| **EGM2008 / WGS84 Ellipsoid** | **Ellipsoidal** | Global Earth Gravity Model | Global DEMs (Copernicus 30m, AW3D30, FABDEM) | $Z_{\text{MSL}} = Z_{\text{ellipsoid}} - N_{\text{geoid}}$ (Geoid height $N \approx -27.5\text{ m}$ in Bangkok) |

> [!CAUTION]
> Never subtract a DEM elevation from a raw canal gauge reading without first verifying that both are normalized to **Mean Sea Level (ม.รทก.)**. A 1-meter datum error will invert the flood prediction!

---

## 3. River Basin Topology & Key Telemetry Stations

### 3.1 Chao Phraya River Chainage (Upstream to Downstream)

```
[ C.2 Nakhon Sawan ] (km 380, Inflow from Ping/Nan)
        │ (~24-36 hrs wave travel)
        ▼
[ C.13 Chao Phraya Dam ] (km 275, Chai Nat Diversion & Release)
        │ (~18-24 hrs)
        ▼
[ C.3 Sing Buri ] (km 210)
        │ (~12-18 hrs)
        ▼
[ C.35 Ayutthaya ] (km 155, Junction with Pa Sak River)
        │ (~8-14 hrs)
        ▼
[ C.29 / C.29A Bang Sai ] (km 112, Gateway discharge to Greater Bangkok)
        │ (~12-24 hrs depending on flow celerity)
        ▼
[ C.21 Rama VII Bridge ] (km 58.4, Nonthaburi/Bangkok border)
        │ (~2.5 hrs)
        ▼
[ C.22 Memorial Bridge / สะพานพุทธ ] (km 48.2, Historical central Bangkok gauge)
        │ (~3.5 hrs)
        ▼
[ Bangkok Port / Khlong Toei ] (km 34.0, Major shipping basin & drainage outlet)
        │ (~2.0 hrs)
        ▼
[ Bang Na ] (km 26.5)
        │ (~4.5 hrs)
        ▼
[ Fort Chulachomklao / ป้อมพระจุลจอมเกล้า ] (km 0.0, Gulf of Thailand Mouth)
```

### 3.2 Canonical Station Metadata

| Station Code | Agency | Location | Latitude | Longitude | Bank Level (m MSL) | Warning Level (m MSL) | Key Function |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **C.2** | RID | Mueang Nakhon Sawan | 15.6722 | 100.1258 | 26.20 | 25.70 | Fluvial wave early trigger (3-4 days ahead) |
| **C.13** | RID | Chao Phraya Dam, Chai Nat | 15.1583 | 100.1833 | 17.21 | 16.50 | Upstream boundary control condition |
| **C.35** | RID | Phra Nakhon Si Ayutthaya | 14.3486 | 100.5603 | 4.58 | 4.20 | Combined Chao Phraya + Pa Sak stage |
| **C.29A** | RID | Bang Sai, Phra Nakhon Si Ayutthaya | 14.1333 | 100.5000 | 3.40 | 3.00 | **Bangkok Gateway Discharge Monitor** |
| **C.21** | RID / BMA | Rama VII Bridge | 13.8139 | 100.5147 | 2.80 | 2.50 | Northern Bangkok barrier check |
| **C.22** | RID / BMA | Memorial Bridge (สะพานพุทธ) | 13.7397 | 100.4981 | 2.80 | 2.27 | Historic BKK mainstem benchmark |
| **BKK008** | BMA / HAII | Khlong Saen Saep (บางกะปิ) | 13.7667 | 100.6500 | 1.20 | 0.80 | Eastern canal urban runoff indicator |
| **BKK021** | BMA / HAII | Khlong Lat Phrao (วัดลาดพร้าว) | 13.8055 | 100.5917 | 1.10 | 0.70 | Northern urban khlong corridor |
| **FORT_CHULA** | RTN | Fort Chulachomklao, Samut Prakan | 13.5417 | 100.5833 | — | — | **Tidal seaward boundary condition** |

---

## 4. The Bangkok Polder System (ระบบปิดล้อม กทม.)

Bangkok is not a free-draining sloping basin; it is an archipelago of **enclosed polders** (*พื้นที่ปิดล้อม*):

1. **Flood Protection Dikes (คันกั้นน้ำ):**
   * The Chao Phraya mainstem is lined with concrete floodwalls averaging **2.80 to 3.00 m MSL** (Pak Khlong Talat: 3.00 m; Bang Khen Mai: 3.50 m).
   * Communities outside the dikes (*ชุมชนนอกคันกั้นน้ำ*, e.g., in Sena, Bang Ban, Nonthaburi pier areas) flood whenever river stage exceeds 1.50–2.00 m MSL.
2. **Internal Canal Holding Levels:**
   * Canals are artificially pumped down to **$-0.20$ to $-0.80\text{ m MSL}$** ahead of forecasted rain storms to maximize in-channel storage capacity.
3. **Gravity Sluice Gate Logic:**
   * When $H_{\text{canal}} > H_{\text{river}}$, sluice gates open to discharge water into the river at zero energy cost.
   * When $H_{\text{river}} \ge H_{\text{canal}}$ (during high tide or upstream river surges), gates are locked tight to prevent river water from invading the streets.

---

## 5. The 2026 Flood Event Anatomy

In late September 2026, two concurrent flooding mechanisms emerged across Central Thailand:

1. **Urban Pluvial Crisis (East Bangkok):**
   * Heavy 24-hour rainfall (Min Buri: 99 mm; Khlong Sam Wa: 154 mm) inundated the eastern polders.
   * Canals (Prawet Burirom, Saen Saep, Khlong Sam Wa) reached capacity while gravity outlets were restricted.
   * BMA declared disaster zones in Nong Chok, Suan Luang, and Khan Na Yao; DDPM activated emergency Cell Broadcast alerts on 26 September 2026.
2. **Upstream Riverine Flood Wave (Chao Phraya Mainstem):**
   * Upstream discharge at C.2 Nakhon Sawan reached 1,737 m³/s, and C.13 release was increased up to 2,000 m³/s.
   * River levels downstream rose 0.70–1.20 m outside the flood dikes in Ayutthaya, Pathum Thani, and Nonthaburi.

This dual reality underscores why a single simplistic model fails: **East Bangkok requires an urban runoff storage-balance model, while riverside Bangkok and Ayutthaya require an upstream routing and tidal superposition model.**

---

## 6. Official Warning Levels & Citizen Impact Translation

To make technical telemetry actionable for citizens under stress, metrics must be translated into plain, relatable physical landmarks:

```
[ > 50 cm ]  EMERGENCY  (แดงเข้ม) ── น้ำท่วมระดับหัวเข่า/มิดล้อรถ / ห้ามสัญจร / อพยพ
[36-50 cm]  CRITICAL   (แดง)     ── น้ำท่วมครึ่งล้อรถ / ห้ามรถเก๋งผ่าน / น้ำเริ่มเข้าบ้าน
[21-35 cm]  HIGH ALERT (ส้มเข้ม) ── น้ำท่วมเกินระดับฟุตบาท / รถเล็กเสี่ยงจอดดับ / เลี่ยงเส้นทาง
[11-20 cm]  ALERT      (ส้มอ่อน) ── น้ำท่วมเสมอระดับทางเท้า / รถเล็กชะลอความเร็ว
[ 1-10 cm]  CAUTION    (เหลือง)  ── น้ำขังรอการระบายบนผิวถนน / สัญจรได้ระมัดระวัง
[   0 cm ]  NORMAL     (เขียว)   ── ผิวถนนแห้ง / สัญจรได้ตามปกติ
```

### Emergency Hotlines in Thailand
* **ปภ. (Department of Disaster Prevention and Mitigation):** Call 1784
* **ศูนย์ป้องกันน้ำท่วม กรุงเทพมหานคร (BMA Flood Control):** Call 1555 or 02-248-5115
* **กรมชลประทาน (RID Hotline):** Call 1460
* **Traffy Fondue:** LINE OA `@traffyfondue`
