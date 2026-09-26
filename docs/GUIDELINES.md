# GUIDELINES.md — Engineering, Modeling & Operational Standards

> **Project:** Bangkok & Central Thailand Flood Intelligence & Hydrodynamic Forecasting Platform (2026)  
> **Audience:** Core Maintainers, Contributors, and Automation Agents  
> **Last Updated:** 26 September 2026

---

## 1. Core Engineering Philosophy

The platform operates on three non-negotiable principles:

1. **Hybrid Hydroinformatics Principle:**
   $$\text{Forecast} = \text{Physically Structured Baseline} + \text{ML Residual Correction} + \text{Calibrated Uncertainty}$$
   Pure "black-box" machine learning extrapolates dangerously during record floods. Pure numerical shallow-water equations (e.g., 2D Saint-Venant) are too computationally demanding for real-time edge updates. We combine physical hydraulic routing with gradient-boosted residuals and conformalized uncertainty bounds.

2. **Mandatory Baseline Verification:**
   Every station and horizon must beat simple baselines in walk-forward backtesting before its forecast is exposed to the public:
   * **Regime A (Rivers):** Must outperform **L0 Persistence** ($H_{t+h} = H_t$).
   * **Regime B (Tidal Reaches):** Must outperform **L1 Persistence + Astronomical Tide Change** ($H_t + \eta_{t+h} - \eta_t$).
   * **Skill Metric:** $\text{Skill} = 1 - \frac{\text{RMSE}_{\text{model}}}{\text{RMSE}_{\text{persistence}}} > 0.10$.
   If a model fails this acceptance gate for a given horizon, the UI automatically falls back to the baseline with widened confidence intervals.

3. **Total Transparency & Provenance:**
   Every screen must display:
   * Timestamp of last observed sensor reading (in Thai ICT: `Asia/Bangkok`).
   * Primary telemetry agency attribution (HAII, RID, BMA, RTN, TMD).
   * Direct emergency contact numbers (DDPM 1784, BMA Flood Center 1555).

---

## 2. Architecture & Hybrid Deployment Standards

To maximize resilience during flood peaks when government servers face heavy load:

```
[ Thai Government / Military Feeds ] ──► [ Local Ingestion Engine ]
(HAII, RID, BMA DDS, RTN Navy, TMD)      (Async Python Collectors, 5-10 min)
                                                    │
                                                    ▼
                                       ┌─────────────────────────┐
                                       │ 1. Immutable Raw Gzip   │ ──► Replicate to Cloudflare R2
                                       │ 2. PostgreSQL + Timescale│
                                       └─────────────────────────┘
                                                    │
                                                    ▼
                                       [ FastAPI Prediction Engine ]
                                       (HydroEngine + LightGBM + CQR)
                                                    │
                                                    ▼ (Localhost port 3000)
                                       [ Cloudflare Tunnel (Zero-Open Port) ]
                                                    │
                                                    ▼
                                       [ Cloudflare CDN Edge Cache ]
                                       (TTL: 1-5 mins, stale-while-revalidate)
                                                    │
                                                    ▼
                                       [ Citizen & Expert Users ]
                                       (Mobile-first Thai Web App)
```

### Ingestion Hygiene Rules
* **Immutability First:** Store every external API payload as raw, gzip-compressed data with SHA-256 hash before parsing. If an upstream schema changes or a parsing bug occurs, raw data can be reprocessed without data loss.
* **Circuit Breaker:** If an external agency fails or returns HTTP 4xx/5xx:
  * Retry with exponential backoff (1s, 2s, 4s, 8s max).
  * Do not crash the application.
  * Enter **Degraded Mode**: serve the last verified reading with an explicit visual warning: *"ข้อมูลล่าสุดเมื่อ 14:15 น. (ระบบตรวจวัดต้นทางขัดข้องชั่วคราว)"*.
* **Single-Flight Requests:** Coalesce overlapping collector requests so that only one outgoing HTTP call hits an agency per refresh cycle.

---

## 3. Modeling & Scientific Rigor

### 3.1 Training & Validation Protocol
* **No Future Data Leakage:** Always train on **as-issued weather forecasts** (archived NWP runs), never on actual future observed rainfall. Training on observed rainfall (*perfect prognosis*) artificially inflates model accuracy that collapses during live deployment.
* **Time-Series Splits Only:** Never use random K-fold cross-validation or shuffle time-series data. Use **Rolling-Origin Walk-Forward Backtesting**:
  * Train up to event $T$.
  * Predict $T + 12\text{h} \dots T + 72\text{h}$.
  * Advance window by step $\Delta t$.
* **Held-Out Test Benchmarks:** Evaluate performance specifically on historical benchmark flood events:
  * **2011 Mega-Flood:** Tests extreme floodplain overland travel and channel overtopping.
  * **2017 & 2021 Events:** Tests combined upstream release and seasonal high tide interaction.
  * **2022 Event:** Tests intense pluvial cloudbursts and BMA giant tunnel drawdown.
  * **Current 2026 Event:** Live validation.

### 3.2 Conformalized Uncertainty Calibration
* Fit models using **Quantile Loss** ($\tau \in \{0.05, 0.25, 0.50, 0.75, 0.95\}$).
* Calibrate prediction intervals using **Conformalized Quantile Regression (CQR)** via `mapie`.
* **Coverage Guarantee:** The empirical 90% confidence band must capture between **85% and 95%** of observed data points on the rolling 14-day validation window. If empirical coverage falls below 85%, automatically widen the interval.

---

## 4. Code & Security Standards

### 4.1 Security & Secret Management
* **Never Commit `.env`:** Ensure `.env` is strictly ignored by version control. Commit only `.env.example` with sanitized placeholders.
* **Cloudflare Zero-Trust Ingress:**
  * Do **NOT** bind FastAPI or web servers directly to `0.0.0.0:80` or `0.0.0.0:443` on public internet interfaces.
  * Bind to `127.0.0.1:3000` and route inbound traffic strictly through an authenticated **Cloudflare Tunnel (`cloudflared`)**.
  * Restrict SSH access to cryptographic key authentication; disable password authentication and root SSH login.

### 4.2 Code Quality & Structure
* **Python Backend:**
  * Target Python 3.11+.
  * Strict PEP 8 compliance, enforced via `ruff` or `flake8`.
  * Comprehensive type hinting (`typing.Dict`, `typing.List`, `typing.Tuple`, `typing.Optional`).
  * Structured JSON logging via standard `logging` library; no raw `print()` statements in production services.
* **Frontend:**
  * Vanilla modern JavaScript (ES6+) or Vue 3 / React with clean component separation.
  * Vanilla CSS or curated utility CSS using HSL color tokens and CSS variables.
  * Zero heavy external bundles; maximize mobile loading performance on weak 3G/4G cellular networks.

---

## 5. Citizen-Centric UX & Communication Standards

People consulting this platform are often stressed, in transit, or protecting their homes from floodwaters. The interface must be immediate, calming, and unambiguous.

```
┌────────────────────────────────────────────────────────────────────────┐
│  📍 คลองแสนแสบ - ประตูน้ำบางกะปิ (BKK008)                               │
│  อัปเดตล่าสุด: 14:30 น. (สถานี สสน./กทม.)                                │
├────────────────────────────────────────────────────────────────────────┤
│  ⚠️ สถานะ: น้ำเอ่อล้นระดับทางเท้า (ท่วมผิวถนน ~18 ซม.)                   │
│                                                                        │
│  📈 แนวโน้ม 12 ชม. ข้างหน้า: น้ำจะขึ้นสูงสุดอีก ~5 ซม. เวลา 16:30 น.    │
│     (สาเหตุ: น้ำทะเลหนุนสูงในแม่น้ำเจ้าพระยา ประตูระบายน้ำต้องปิดชั่วคราว)  │
│                                                                        │
│  ⏱️ คาดการณ์น้ำลดแห้ง: อีก 4 ชั่วโมง (ประมาณ 18:30 น.)                    │
│     (สมมติฐาน: เดินเครื่องสูบน้ำอุโมงค์พระโขนงเต็มกำลัง และไม่มีฝนตกหนักเพิ่ม)│
└────────────────────────────────────────────────────────────────────────┘
```

### Essential UX Rules
1. **The "Two Golden Questions" Above the Fold:**
   * Question 1: *"น้ำแถวบ้านจะขึ้นหรือลง?"* (Trend & Delta $\Delta H$).
   * Question 2: *"น้ำจะแห้งเมื่อไหร่?"* (Recovery ETA Countdown $T_{\text{dry}}$).
2. **Citizen Mode vs Expert Mode:**
   * **Citizen Mode (Default):** Depths in centimeters relative to curbs/wheels, actionable checklists (*"ย้ายปลั๊กไฟ"*, *"เลี่ยงรถเล็กผ่าน"*), simple trend arrows.
   * **Expert Mode (Toggle):** Hydrographs in meters MSL (ม.รทก.), discharge in m³/s, tidal harmonics, radar hyetographs.
3. **Conditionality Language:**
   Never promise an unconditional dry time. Always explicitly state the condition:
   *"คาดการณ์น้ำลดสู่ภาวะปกติ 18:30 น. (หากไม่มีฝนตกหนักเพิ่มเติม และเครื่องสูบน้ำทำงานปกติ)"*.
