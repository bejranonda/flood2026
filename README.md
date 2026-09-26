# BKK FloodWatch 2026 🌊
### Bangkok & Central Thailand Flood Intelligence & Hydrodynamic Forecasting Platform
> **ระบบพยากรณ์และเตือนภัยระดับน้ำท่วมขังกรุงเทพมหานครและลุ่มน้ำเจ้าพระยาตอนล่าง (พ.ศ. 2569)**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Cloudflare: Edge + CDN](https://img.shields.io/badge/Cloudflare-Edge%20%2B%20R2%20%2B%20Tunnel-orange.svg)](https://cloudflare.com/)
[![Hydroinformatics](https://img.shields.io/badge/Domain-Hydroinformatics%20%26%20Estuarine%20Hydraulics-darkgreen.svg)](#)

---

## 📖 Table of Contents
1. [Project Overview & 2026 Flood Context](#-project-overview--2026-flood-context)
2. [The Two Golden Questions](#-the-two-golden-questions)
3. [The "Three Waters" Triad (น้ำสามน้ำ)](#-the-three-waters-triad-น้ำสามน้ำ)
4. [System Architecture & Hybrid Cloud Topology](#-system-architecture--hybrid-cloud-topology)
5. [Documentation Directory](#-documentation-directory)
6. [Data Sources & Telemetry Ingestion](#-data-sources--telemetry-ingestion)
7. [Hydrodynamic & Machine Learning Engine](#-hydrodynamic--machine-learning-engine)
8. [Dual-View User Experience (Citizen vs. Expert)](#-dual-view-user-experience-citizen-vs-expert)
9. [Configuration & Environment Variables (.env)](#-configuration--environment-variables-env)
10. [Quick Start & Local Verification](#-quick-start--local-verification)
11. [Verification Standards & Acceptance Gates](#-verification-standards--acceptance-gates)
12. [Disaster Relief Contacts & Attribution](#-disaster-relief-contacts--attribution)

---

## 🌊 Project Overview & 2026 Flood Context

During late September 2026, severe and widespread flooding impacted Bangkok and the lower Chao Phraya river basin. Heavy monsoon rainfall saturated urban catchments in Eastern Bangkok (Min Buri, Khlong Sam Wa, Nong Chok, Lat Krabang), while simultaneously upstream river discharges from the Chao Phraya Dam (C.13) exceeded 1,800–2,000 m³/s, threatening riverside communities across Ayutthaya, Pathum Thani, Nonthaburi, and Bangkok.

Traditional government portals provide fragmented telemetry (river discharge in cubic meters per second, canal levels referenced to arbitrary staff zeros, or astronomical tide tables in annual PDFs). Residents facing rising waters struggle to answer the basic questions needed to protect their families, vehicles, and homes.

**BKK FloodWatch** bridges the gap between raw hydroinformatics and citizen action. It continuously ingests river flow, canal gauges, astronomical tides, storm surges, radar reflectivity, and ground elevation models to synthesize a real-time, neighborhood-specific predictive state.

---

## 🎯 The Two Golden Questions

The platform is engineered to deliver immediate answers to two fundamental questions within the user's initial screen viewport:

| # | Citizen Question | Technical Formulation | Practical Output |
| :---: | :--- | :--- | :--- |
| **1** | **"น้ำแถวบ้านฉันจะขึ้นหรือจะลงในอีก 12 ชม. ถึง 3 วัน?"** | $\Delta H_{\text{street}}(t+h) = H_{\text{water}}(t+h) - Z_{\text{road}}$ | Trend arrow + Peak timing + Depth in centimeters relative to curbs/wheels |
| **2** | **"น้ำจะแห้งและกลับสู่ภาวะปกติเมื่อไหร่?"** | $T_{\text{dry}} = \frac{V_{\text{ponding}}}{Q_{\text{pump}} + Q_{\text{gravity}} - Q_{\text{residual\_rain}}}$ | Live recovery countdown clock (e.g., *"อีก 3 ชั่วโมง 45 นาที / ประมาณ 18:30 น."*) |

---

## 🔱 The "Three Waters" Triad (น้ำสามน้ำ)

Bangkok's flood vulnerability is governed by the non-linear superposition of three independent hydrodynamic forces modulated by an artificial human control boundary:

```
                          [ 1. Fluvial Inflow (น้ำเหนือ) ]
                            C.2 Nakhon Sawan ──► C.13 Dam ──► C.29 Bang Sai
                            (Travel lag: 8 to 30 hours to Bangkok)
                                          │
                                          ▼
                               Chao Phraya Mainstem River
                                          ▲
                                          │
    [ 3. Pluvial Runoff (น้ำฝน) ]   ──►   BMA Khlong System   ◄──   [ 2. Tidal Surge (น้ำหนุน) ]
    Convective bursts > 60 mm/hr         (Canals & Polders)         Gulf of Thailand High Tide
    Subterranean pipe overflow           Saen Saep / Lat Phrao      Backwater blocks gravity gates
                                          │
                                          ▼
                            [ Artificial Control Boundary ]
                        (อุโมงค์ยักษ์ / ประตูระบายน้ำ / สถานีสูบน้ำ / แก้มลิง)
```

1. **Fluvial Inflow (น้ำเหนือ):** Regulated upstream dam releases propagating down the Chao Phraya River.
2. **Tidal Surge (น้ำหนุน):** Astronomical tides and monsoonal storm surges from the Gulf of Thailand creating estuarine backwater stacking.
3. **Pluvial Runoff (น้ำฝน):** Intense tropical convective cloudbursts overwhelming Bangkok's 50–60 mm/hr pipe drainage capacity.
4. **Human Control:** BMA's giant drainage tunnels (*อุโมงค์ยักษ์*, e.g., Bang Sue, Rama IX, Phra Khanong), sluice gates, and pump stations.

---

## 🏗️ System Architecture & Hybrid Cloud Topology

To survive extreme traffic surges during flood emergencies while maintaining low latency to Thai telemetry APIs, the system utilizes a **Hybrid VPS Core + Cloudflare Edge** architecture:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                THAI TELEMETRY INGESTION                                │
│   HAII ThaiWater v3 ──► RID SWOC ──► BMA DDS ──► RTN Navy Tides ──► TMD / Open-Meteo   │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ (Every 5-10 mins)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              VPS CORE (SINGAPORE / THAILAND)                           │
│                                                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────────────┐  │
│  │ Data Ingestion Broker │   │ Raw Immutable Gzip    │──►│ Replicate to CF R2       │  │
│  │ - Proxy / Rate Limits │   │ TimescaleDB Database  │   │ Object Storage Archive   │  │
│  └──────────┬────────────┘   └───────────────────────┘   └──────────────────────────┘  │
│             │                                                                          │
│             ▼                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ BKK HydroEngine Computational Core                                               │  │
│  │ - 1D Fluvial Wave Routing (Saint-Venant kinematic celerity)                      │  │
│  │ - 4-Constituent Astronomical Harmonic Superposition (utide)                     │  │
│  │ - Polder Continuity Storage Balance & Sluice Gate Hydraulics                    │  │
│  │ - LightGBM Multi-Horizon Quantile Residual Engine (tau = 0.05..0.95)             │  │
│  │ - Conformalized Quantile Regression (CQR / ACI) Interval Calibration             │  │
│  └──────────────────────────────────────┬───────────────────────────────────────────┘  │
│                                         │ (FastAPI JSON API / Localhost:3000)          │
│                                         ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Cloudflare Tunnel Daemon (cloudflared)                                           │  │
│  │ (Zero exposed inbound ports on VPS; encrypted tunnel to Cloudflare Edge)         │  │
│  └──────────────────────────────────────┬───────────────────────────────────────────┘  │
└─────────────────────────────────────────┼──────────────────────────────────────────────┘
                                          │
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               CLOUDFLARE EDGE & CDN                                    │
│  - DDoS Protection & Global Anycast DNS                                                │
│  - Edge Cache (1-5 min TTL + stale-while-revalidate for public forecast payloads)      │
│  - Cloudflare Pages (Mobile-First Thai Web Application)                                │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
                                [ 📱 Citizen & Mobile Users ]
```

---

## 📚 Documentation Directory

Comprehensive technical guides and operational documentation are organized in [`docs/`](docs/) and [`research/`](research/):

| Document | Description |
| :--- | :--- |
| **[`docs/KNOWLEDGE.md`](docs/KNOWLEDGE.md)** | **Domain Knowledge Base:** Deep dive into the "Three Waters", Chao Phraya station chainage (C.2 to C.29), vertical datums (Ko Lak MSL vs LLW vs Staff zeros), BMA polder networks, giant tunnels, and 2026 event timeline. |
| **[`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md)** | **Bottlenecks & Technical Workarounds:** Thai government API egress 403 firewalls, RTN Navy tide PDF parsing, DDS ASPX scraping, DEM vertical errors (FABDEM vs SRTM), and Cloudflare tunnel gotchas. |
| **[`docs/GUIDELINES.md`](docs/GUIDELINES.md)** | **Engineering & UX Standards:** Hybrid architecture rules, immutability of raw data, walk-forward testing gates (skill vs persistence), zero-trust security, and citizen communication ethics. |
| **[`docs/APPROACH_AND_METHODS.md`](docs/APPROACH_AND_METHODS.md)** | **Mathematical Modeling & ML:** Wave celerity equations, tidal harmonic formulation, polder continuity equations, street depth $d_{\text{street}}$, Time-to-Dry $T_{\text{dry}}$, LightGBM quantile regression, and conformal prediction. |
| **[`research/`](research/)** | Raw research source audits, extraction scripts, and hydrodynamic mathematical whitepapers. |

---

## 📡 Data Sources & Telemetry Ingestion

The platform integrates five operational data domains:

| Domain | Primary Source | Extracted Metrics | Format / Route |
| :--- | :--- | :--- | :--- |
| **Fluvial Inflow** | **HAII ThaiWater v3 / RID** | C.2, C.13, C.29 river levels (m MSL), discharge (m³/s) | REST API / JSON |
| **Canal Telemetry** | **BMA DDS / HAII** | 120+ canal stations (Khlong Saen Saep BKK008, Lat Phrao BKK021) | JSON & HTML Scraper |
| **Tidal Dynamics** | **Royal Thai Navy Hydrographic** | Hourly astronomical heights, Fort Chulachomklao sea level | PDF / Harmonic Engine |
| **Weather & Radar** | **TMD & Open-Meteo** | Hourly convective precipitation, barometric pressure, wind | REST JSON / Radar GIF |
| **Topography** | **FABDEM / Copernicus GLO-30** | Road surface elevation ($Z_{\text{road}}$), HAND drainage height | Cloud-Optimized GeoTIFF |
| **Ground Truth** | **BMA Traffy Fondue** | Citizen incident reports (category = `น้ำท่วม`), photo feeds | Open API / Webhook |

---

## 🧮 Hydrodynamic & Machine Learning Engine

The computational core implements a 4-tier hybrid model ladder:

```
[ Ingested Telemetry ]
          │
          ▼
[ 1. Physical Baseline ]
  ├── Mainstem River: Saint-Venant kinematic celerity routing: c_k(Q) = c_0 * (Q / Q_bankfull)^0.38
  ├── Estuary Tide: Astronomical harmonics (M2, S2, K1, O1) + estuarine frictional damping
  └── Urban Polder: Storage balance: dS/dt = Runoff - Pumps - GravityGates
          │
          ▼
[ 2. LightGBM Residual ML Engine ]
  └── Multi-horizon direct forecasting (tau = 0.05, 0.25, 0.50, 0.75, 0.95) with monotonic physics constraints
          │
          ▼
[ 3. Error Correction & Weather Ensembles ]
  ├── Autoregressive bias fading: epsilon(t+h) = phi^h * [H_obs(t) - H_model(t)]
  └── Multi-member NWP precipitation ensemble (ECMWF, GFS, ICON)
          │
          ▼
[ 4. Conformal Calibration (CQR / ACI) ]
  └── Statistically guaranteed 90% confidence bands across all horizons (+12h, +24h, +48h, +72h)
```

---

## 📱 Dual-View User Experience (Citizen vs. Expert)

The user interface is designed mobile-first in natural Thai language, featuring a dual-perspective toggle:

### 1. Citizen Mode (Default)
* **Status Badges:** ปลอดภัย (เขียว) / เฝ้าระวัง (เหลือง) / น้ำท่วมขังบนผิวถนน (ส้ม) / วิกฤติ (แดง).
* **Physical Landmarks:** Depths reported in centimeters relative to recognizable objects (*"ท่วมเสมอระดับทางเท้า ~15 ซม."*, *"ระดับครึ่งล้อรถยนต์ ~25 ซม."*).
* **Action Checklists:** Immediate advice (*"ยกของขึ้นที่สูง"*, *"เลี่ยงรถเล็กผ่านเส้นทาง"*).
* **Clear Conditions:** Recovery time conditioned on explicit assumptions (*"หากไม่มีฝนตกหนักเพิ่มเติม"*).

### 2. Expert Mode
* Full hydrographs in meters MSL (ม.รทก.).
* Real-time discharge hydrographs at Bang Sai (C.29) in m³/s.
* Astronomical harmonic curves and storm surge anomalies.
* BMA active pump capacity and gate opening status.

---

## ⚙️ Configuration & Environment Variables (.env)

The application requires an environment file `.env` containing your live credentials. A clean template is provided in [`.env.example`](.env.example).

### Step 1: Create your local `.env`
```bash
cp .env.example .env
```

### Step 2: Configure your Cloudflare Token & Credentials
Open `.env` in your editor and provide your **Cloudflare API Token**:

```env
# ------------------------------------------------------------------------------
# 1. Cloudflare Configuration (Zero Trust / Tunnel / Workers / Pages / DNS)
# ------------------------------------------------------------------------------
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
CLOUDFLARE_ZONE_ID=your_cloudflare_zone_id_here
CLOUDFLARE_TUNNEL_TOKEN=your_cloudflare_tunnel_token_here

# ------------------------------------------------------------------------------
# 2. Hydrological & Meteorological Telemetry APIs
# ------------------------------------------------------------------------------
THAIWATER_API_KEY=
TMD_API_KEY=
GISTDA_API_KEY=
OPEN_METEO_API_KEY=

# ------------------------------------------------------------------------------
# 3. Application Runtime & Server Settings
# ------------------------------------------------------------------------------
NODE_ENV=development
PORT=3000
HOST=0.0.0.0
LOG_LEVEL=info
DATABASE_URL=sqlite:///data/flood2026.db
```

> [!IMPORTANT]
> The `.env` file contains private tokens and is strictly ignored by `.gitignore`. Never commit `.env` into public version control.

---

## 🚀 Quick Start & Local Verification

### 1. System Requirements
* Python 3.11+ (with `pip`, `venv`)
* Node.js 18+ (for frontend / worker tools)
* Docker & Docker Compose (optional for production containerized deployment)

### 2. Run the Hydrodynamic Engine Verification
A self-contained simulation runner is included to verify the computational core:

```bash
# Run the hydrodynamic demonstration runner
python3 research/bangkok_flood_calculation_forecasting_engine.md
```

*(Alternatively, run the sample script extracted to `scratch/` or `src/`)*.

Sample Simulation Output:
```text
==========================================================================================
BKK HydroEngine Simulation Output: Sukhumvit 71 / Phra Khanong Polder
==========================================================================================
Hour  | Rain   | River (m) | Khlong (m) | Street (cm) | Status                           | ETA Dry
------------------------------------------------------------------------------------------
+0    | 0.0    | 1.15      | -0.10      | 0.0         | DRY / ปลอดภัย (0 ซม.)            | สภาวะปกติ
+1    | 42.0   | 1.28      | 0.24       | 0.0         | DRY / ปลอดภัย (0 ซม.)            | สภาวะปกติ
+2    | 68.0   | 1.42      | 0.88       | 29.0        | HIGH / รถเก๋งเสี่ยงจอดดับ        | 21:30 น. (26/09)
+3    | 25.0   | 1.35      | 0.65       | 0.0         | DRY / ปลอดภัย (0 ซม.)            | สภาวะปกติ
==========================================================================================
```

### 3. Deploy via Docker Compose (VPS Core)
```bash
docker compose up -d --build
```

---

## 🛡️ Verification Standards & Acceptance Gates

To guarantee scientific integrity, every predictive model must pass the following deployment gates defined in [`docs/GUIDELINES.md`](docs/GUIDELINES.md):

1. **Skill vs. Persistence:** Model skill score $\text{Skill} = 1 - \frac{\text{RMSE}_{\text{model}}}{\text{RMSE}_{\text{persistence}}} > 0.10$ on held-out flood events (2011, 2017, 2021, 2022, 2026).
2. **Empirical Coverage:** Conformalized 90% confidence intervals must achieve **85% to 95%** coverage on rolling 14-day validation data.
3. **Peak Timing Precision:** Target $|\Delta t_{\text{peak}}| \le 45\text{ minutes}$ against crowdsourced Traffy Fondue reports.
4. **Mass Conservation:** Hydraulic continuity volume balance closure error $< 3\%$.

---

## 📞 Disaster Relief Contacts & Attribution

This platform is a civil-tech disaster informatics initiative intended to support Thai citizens during monsoon emergencies. Always cross-check alerts with official government authorities:

* **กรมป้องกันและบรรเทาสาธารณภัย (DDPM):** สายด่วน ปภ. **1784**
* **ศูนย์ควบคุมระบบป้องกันน้ำท่วม กรุงเทพมหานคร (BMA DDS):** โทร. **1555** หรือ **02-248-5115**
* **ศูนย์ปฏิบัติการน้ำอัจฉริยะ กรมชลประทาน (RID SWOC):** สายด่วน **1460**
* **สถาบันสารสนเทศทรัพยากรน้ำ (องค์การมหาชน) - สสน. (HAII):** [thaiwater.net](https://www.thaiwater.net)
* **กรมอุทกศาสตร์ กองทัพเรือ (Royal Thai Navy Hydrographic Dept):** [hydro.navy.mi.th](https://www.hydro.navy.mi.th)

---
*Developed with modern hydroinformatics, physics-informed machine learning, and disaster informatics principles.*
