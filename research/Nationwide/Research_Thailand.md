> **Validity: 🔴 do not use as a source** (checked 2026-09-27, [VALIDATION_2026-09-27_nationwide.md §C](../VALIDATION_2026-09-27_nationwide.md#c-research_thailandmd--verdicts)).
> Kept unchanged below this banner as a research record (owner's choice). **Refuted:** every ThaiWater URL
> (`api2.thaiwater.net` has no DNS, already refuted in SOURCES §3), station and dam counts, DWR counts and thresholds,
> the C.13 thresholds (official: 2,176 / 2,448 / 2,720 m³/s), the MRC host, and the sample JSON (invented numbers).
> **Against project rules (⛔):** street depth from HAND (D-019/D-021), a SOCKS5/Workers egress relay (D-014/D-016),
> a non-honest User-Agent, and evacuation instructions in code (D-005). **Usable as ideas only (💡):** the regional
> zoning, SCS-CN, Muskingum-Cunge and loop-rating methods (Kirpich's formula lacks units: minutes, L in metres).

```markdown
# All-Thailand Flood Forecasting & Hydrological Modeling Engine: Technical Specification

---

## 1. Physiographic & Hydrological Zoning of Thailand

Expanding from Bangkok to the national scale requires transitioning from an **estuarine/polder urban regime** to a **multi-basin hydrological regime**. Thailand is divided into four distinct physiographic zones, each governed by different physical drivers and governing equations:


```

```
                             THAILAND REGIONAL HYDROLOGY
                                          │
┌──────────────────────┬──────────────────┴───────────────────┬──────────────────────┐
▼                      ▼                                      ▼                      ▼

```

[Zone 1: North/West]   [Zone 2: Central Plains]              [Zone 3: Isan / Khorat]  [Zone 4: South/Coastal]

* Ping, Wang, Yom, Nan - Lower Chao Phraya, Pasak            - Chi, Mun, Mekong       - Tapi, Pattani, Trang
* Mountainous catchments- Low hydraulic slope (S0 < 1e-4)    - Broad floodplains     - Short, steep basins
* Fast tc (Flash flood)- Retention fields (ทุ่งรับน้ำ)        - Confluence backwaters  - Dual monsoon timing
* Large headwater dams - Floodwalls & regulated gates         - Medium reservoirs      - Estuarine tidal surge

```

### Zone Comparison Matrix

| Hydro-Physiographic Zone | Primary Basins | Key Flood Driving Mechanisms | Dominant Wave Dynamics | Critical Regulating Infrastructure |
| :--- | :--- | :--- | :--- | :--- |
| **1. Northern & Western Highlands** | Ping, Wang, Yom, Nan, Kok, Pai, Mae Klong headwaters | Flash floods (*น้ำป่าไหลหลาก*), steep overland runoff, debris flows, riverbank overtopping | Kinematic wave, steep advection ($c_k = 2.0\text{–}3.5\text{ m/s}$), small storage attenuation | Bhumibol Dam, Sirikit Dam, Kiew Lom, Mae Ngat |
| **2. Central Floodplain** | Chao Phraya, Pasak, Sakae Krang, Lop Buri | Fluvial riverine flooding (*น้ำเอ่อล้นตลิ่ง*), channel bottlenecks, prolonged inundation | Diffusive wave, dynamic backwater, loop rating curves ($S_0 \approx 10^{-4} \text{ to } 10^{-5}$) | Chao Phraya Dam (C.13), Rama VI Dam, Pasak Jolasid, 12 Retention Basins (*ทุ่งรับน้ำ*) |
| **3. Khorat Plateau (Northeast)** | Chi, Mun, Songkhram, Mekong tributaries | Backwater confluence drowning (Chi meeting Mun at Sisaket/Ubon; Mun meeting Mekong at Khong Chiam) | Slow diffusive wave, extensive overbank storage attenuation | Ubol Ratana Dam, Lam Pao Dam, Sirindhorn Dam, Pak Mun Dam |
| **4. Southern Peninsula & Coastal** | Tapi-Phum Duang, Pattani, Kolok, Trang, Phetchaburi | Flash pluvial/fluvial floods, extreme monsoon downpours, estuarine tidal blocking | Superposition: Kinematic flash flood + coastal astronomical high tide | Kaeng Krachan Dam, Pran Buri Dam, Ratchaprapha Dam, Bang Lang Dam |

---

## 2. Core Mathematical & Computational Framework

Because full 2D hydrodynamic simulations (e.g., shallow water equations via HEC-RAS 2D or TELEMAC) cannot run in real time on a nationwide web client, the engine utilizes a **hybrid lumped/semi-distributed modeling framework**:


```

[ GPM / Radar / TMD Rain ] ───> [ 1. Rainfall-Runoff (GR4J / SCS-CN) ]
│
[ Dam Storage / Releases ] ───> [ 2. Reservoir Mass Balance Model    ]
│
▼
[ 3. Channel Routing (Muskingum-Cunge)]
│ Routed Discharge Q(x, t) & Stage H(x, t)
▼
[ 4. Terrain Inundation (HAND + DEM) ]
│
▼
Street Flood Extent & Depth d(x, y, t)

```

---

### 2.1 Catchment Runoff Transformation: Soil Moisture Accounting (SMA)

For ungauged and semi-gauged sub-catchments across Thailand, calculate surface effective runoff using the continuous **SCS-CN Soil Moisture Accounting (SMA)** or the lumped **GR4J** model.

#### SCS-CN Dynamic Soil Retention Model
The potential maximum soil retention $S(t)$ in millimeters varies continuously with the Antecedent Precipitation Index ($API$):

$$S(t) = 25.4 \left( \frac{1000}{CN(t)} - 10 \right)$$

Where the dynamic Curve Number $CN(t)$ is modulated between dry (Condition I), normal (Condition II), and wet (Condition III) states based on 5-day antecedent rainfall ($P_5$):

$$CN_{I} = \frac{CN_{II}}{2.281 - 0.01281 \cdot CN_{II}}, \quad CN_{III} = \frac{CN_{II}}{0.427 + 0.00573 \cdot CN_{II}}$$

Cumulative surface runoff depth $P_e(t)$ (in mm) over time-step $\Delta t$:

$$P_e(t) = \begin{cases}  \frac{\big(P(t) - I_a(t)\big)^2}{P(t) - I_a(t) + S(t)} & \text{for } P(t) > I_a(t) \\ 0 & \text{for } P(t) \le I_a(t) \end{cases}$$

Where initial abstraction $I_a(t) = \lambda \cdot S(t)$ (with $\lambda \approx 0.05\text{–}0.10$ for steep tropical soils in Northern Thailand).

#### Catchment Concentration Time ($t_c$)
Compute basin response time using the Kirpich/California Culverts empirical formulation for natural river channels:

$$t_c = 0.0195 \cdot L^{0.77} \cdot S_b^{-0.385}$$

* $L$ is the hydraulic channel length (meters).
* $S_b$ is the dimensionless average basin slope ($m/m$).
* In Northern flash-flood catchments, $t_c \approx 2\text{ to }6\text{ hours}$. In the low-gradient Chi-Mun basin, $t_c \approx 48\text{ to }120\text{ hours}$.

---

### 2.2 Reservoir & Dam Operational Control Model

In upper Thailand, reservoir storage dictates downstream river stage. Natural river discharges are interrupted by major reservoirs operated by the Electricity Generating Authority of Thailand (EGAT) and the Royal Irrigation Department (RID).


```

```
                  INFLOW I(t)
                       │
                       ▼
              ┌─────────────────┐
              │  RESERVOIR      │ ──> Evaporation E(t) / Seepage
              │  STORAGE S(t)   │
              └─────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
Controlled Turbines / Gates      Spillway Discharge
Q_reg(t) = f(Rule Curve)         Q_spill = C_w * L * (h - h_crest)^(3/2)

```

```

#### Mass Conservation Differential Equation
$$\frac{dS(t)}{dt} = I(t) - Q_{\text{out}}(t) - E(t)$$

Where:
* $I(t)$ is total upstream catchment inflow ($m^3/s$).
* $Q_{\text{out}}(t) = Q_{\text{turbine}}(t) + Q_{\text{spill}}(t) + Q_{\text{bottom}}(t)$ is total regulated release.
* $S(t)$ is current storage volume ($m^3$), linked to water elevation $h(t)$ via the hypsometric curve:
  $$S(h) = a \cdot (h - z_0)^b$$

#### Rule Curve Operational Logic
Dam operators determine release $Q_{\text{out}}(t)$ relative to seasonal target rule curves:
1. **$h(t) \le \text{Lower Rule Curve (LRC)}$:**
   $$Q_{\text{out}}(t) = Q_{\text{ecological\_min}}$$
2. **$\text{LRC} < h(t) \le \text{Upper Rule Curve (URC)}$:**
   $$Q_{\text{out}}(t) = \min\big(Q_{\text{demand}}(t), Q_{\text{safe\_downstream}}\big)$$
3. **$h(t) > \text{Upper Rule Curve (URC)}$:**
   Emergency flood evacuation releases:
   $$Q_{\text{out}}(t) = Q_{\text{reg}}(t) + C_w L_{\text{crest}} \max\big(0, h(t) - h_{\text{spill}}\big)^{3/2}$$

---

### 2.3 River Channel Routing: Muskingum-Cunge with Variable Celerity

To route flow hydrographs between upstream gauges (or dam release points) and downstream population centers, use the **Muskingum-Cunge diffusive wave method**:

For reach length $\Delta x$ and time step $\Delta t$:

$$Q_{j+1}^{n+1} = C_1 Q_j^{n+1} + C_2 Q_j^n + C_3 Q_{j+1}^n + C_4 \cdot q_L \Delta x$$

Where the routing coefficients are:

$$C_1 = \frac{\Delta t - 2 K X}{2 K (1 - X) + \Delta t}, \quad C_2 = \frac{\Delta t + 2 K X}{2 K (1 - X) + \Delta t}, \quad C_3 = \frac{2 K (1 - X) - \Delta t}{2 K (1 - X) + \Delta t}$$

$$\sum_{i=1}^3 C_i = 1$$

#### Physical Parameter Formulation
$$K = \frac{\Delta x}{c_k} \quad (\text{Wave travel time})$$

$$X = \frac{1}{2} \left( 1 - \frac{Q_0}{B \cdot S_0 \cdot c_k \cdot \Delta x} \right) \quad (\text{Hydrodynamic diffusion factor})$$

Where:
* $c_k = \frac{dQ}{dA} = \frac{5}{3} v$ is kinematic wave celerity ($m/s$).
* $B$ is channel top-surface width ($m$).
* $S_0$ is bed slope.
* $Q_0$ is reference discharge ($m^3/s$).
* $q_L$ is lateral un-gauged tributary inflow ($m^2/s$).

#### Stage-Discharge Loop Rating Curve (Hysteresis Correction)
In low-gradient reaches (Chao Phraya C.2 at Nakhon Sawan, Chi River at Yasothon, Mun River at Ubon Ratchathani M.7), correct for dynamic looping using the **Jones Equation**:

$$Q(t) = Q_{\text{steady}}(h) \sqrt{1 + \frac{1}{S_0 \cdot c_k} \frac{\partial h}{\partial t}}$$

* $\frac{\partial h}{\partial t} > 0$ (Rising stage): $Q > Q_{\text{steady}}$ (Discharge leads stage).
* $\frac{\partial h}{\partial t} < 0$ (Falling stage): $Q < Q_{\text{steady}}$ (Backwater ponding prolongs inundation).

---

### 2.4 Nationwide Topographic Inundation Translation: The HAND Method

To compute spatial inundation depth over broad floodplains without a 2D mesh hydrodynamic solver, implement the **Height Above Nearest Drainage (HAND)** model.


```

```
                TERRAIN PROFILE WITH EMBEDDED STREAM

```

Elevation z
▲
│        Local Hilltop (HAND = 12m)
│               /

│              /  \      Submerged Floodplain (HAND < H_stage)
│             /    \    ┌────────────────────────┐
│            /      \   │  d(x,y) = H_stage - HAND│
│           /        └──┴───────────────┐        │
│          /                            │ Water  │
│         /                             │ Level  │
│        /       Stream Channel         │ H_stage│
│       /          (HAND = 0m)          │        │
└──────┴───────────────▼────────────────┴────────┴────────► Coordinate x

```

1. **Pre-compute the HAND Normalized Topography:**
   Using the **MERIT DEM** (Hydro-conditioned 90m) or **Copernicus GLO-30 DEM**, define drainage flow directions via D8 routing to delineate the active river drainage network.
   Every raster cell $(x, y)$ is mapped to its hydrologically nearest stream cell $(x_s, y_s)$:
   $$HAND(x, y) = z(x, y) - z(x_s, y_s)$$
2. **Calculate Street Depth:**
   When the routed 1D reach model yields river stage $H_{\text{reach}}(t)$ above the local channel bed:
   $$d(x, y, t) = \max\Big(0,\; H_{\text{reach}}(t) - HAND(x, y)\Big)$$

---

## 3. Comprehensive Data Sources Inventory

### 3.1 Thai Government Data Sources


```

```
                   THAI GOVERNMENT HYDRO-DATA ECOSYSTEM
                                    │
 ┌──────────────────────┬───────────┴───────────┬──────────────────────┐
 ▼                      ▼                       ▼                      ▼

```

[ HII / ThaiWater ]    [ RID / SWOC ]         [ EGAT ]               [ GISTDA ]

* River telemetry      - Barrage discharges   - Major dam storage    - Sentinel-1 SAR flood
* Automated stations   - Dam operations       - Daily releases         vectors (Disaster GeoJSON)
* Sluice gate heads    - Retention diversion  - Rule curves          - Land subsidence maps

```

#### A. Hydro-Informatics Institute (HII / ThaiWater)
* **Primary Telemetry Endpoint:**
  * URL: `https://api2.thaiwater.net/v1/analyst/water/telemetry`
  * Data: Real-time water elevation ($m\text{ MSL}$), channel bank level, warning thresholds across $> 1,200$ stations nationwide.
* **National Dam & Reservoir Operations:**
  * URL: `https://api2.thaiwater.net/v1/analyst/water/dam`
  * Data: 35 large dams and $> 300$ medium reservoirs. Storage percentage, 24h inflow ($m^3$), 24h outflow ($m^3$).
* **Regulated Sluice Gates & Weirs:**
  * URL: `https://api2.thaiwater.net/v1/analyst/water/watergate`
  * Data: Headwater (ระดับน้ำเหนือน้ำ) and tailwater (ระดับน้ำท้ายน้ำ) stages, open gate height/number.
* **Warning & Threshold Telemetry:**
  * URL: `https://tiwrm.hii.or.th/thaiwater_l5/public/telemetering/wl/warning`
  * Data: Pre-classified sensor list (Normal, Watch, Warning, Overflow).
* **High-Resolution NWP Rainfall:**
  * WRF-ROMS operational numerical weather forecast with 7-day lead time.

#### B. Royal Irrigation Department (RID / Smart Water Operation Center - SWOC)
* **URL:** `http://swoc.rid.go.th/` and `http://wmsc.rid.go.th/`
* **Key Strategic Stations:**
  * **Chao Phraya Basin:** C.2 (Nakhon Sawan), C.13 (Chao Phraya Dam, Chai Nat), C.29A (Bang Sai).
  * **Ping Basin:** P.1 (Chiang Mai Nawarat Bridge), P.67 (Chom Thong).
  * **Wang Basin:** W.4A (Lampang).
  * **Yom Basin:** Y.1C (Phrae), Y.14 (Sukhothai - Flash-flood hotspot).
  * **Nan Basin:** N.5A (Phitsanulok), N.1 (Nan).
  * **Mun-Chi Basin:** E.20B (Chi River, Yasothon), M.7 (Mun River, Seri Minaphant Bridge, Ubon Ratchathani).
* **Controlled Water Diversion:**
  * Daily volumetric diversion into retention lowlands (*ทุ่งรับน้ำ* 12 ทุ่ง เช่น ทุ่งบางระกำ, ทุ่งเจ้าเจ็ด, ทุ่งป่าโมก).

#### C. Department of Water Resources (DWR / กรมทรัพยากรน้ำ)
* **Early Warning System (Early Warning for Flash Floods & Debris Flows):**
  * URL: `http://ews.dwr.go.th/` or `http://warning.dwr.go.th/`
  * Focus: $> 800$ automated tipping-bucket rainfall stations in upstream mountain villages.
  * Trigger: 3-tier rain accumulation threshold:
    * Green: Normal
    * Yellow: $> 100\text{ mm}/24\text{h}$ (Advisory)
    * Red: $> 150\text{ mm}/24\text{h}$ (Immediate flash-flood/evacuation warning)

#### D. Geo-Informatics and Space Technology Development Agency (GISTDA)
* **Disaster Monitoring & Flood Footprint Portal:**
  * URL: `https://disaster.gistda.or.th/`
  * Mechanism: Direct ingest of spaceborne SAR (COSMO-SkyMed, Radarsat-2, Sentinel-1).
  * Output: GeoJSON/SHP vectors of actual standing surface water footprints, updated every 24–48 hours, fully penetrating tropical monsoon cloud cover.

---

### 3.2 International & Remote Sensing Data Sources

#### A. Google Flood Hub (Global Flood Forecasting Engine)
* **URL:** `https://sites.research.google/floods`
* **Architecture:** Combines daily ECMWF/GloFAS discharge forecasts with gauge-calibrated Long Short-Term Memory (LSTM) machine learning models and local hydraulic routing.
* **National Coverage:** Covers major Thai river reaches (Chao Phraya, Ping, Nan, Mun, Chi, Mekong).

#### B. Global Flood Awareness System (Copernicus GloFAS)
* **Provider:** European Centre for Medium-Range Weather Forecasts (ECMWF) & Copernicus Emergency Management Service.
* **Spatial Resolution:** $0.1^\circ \times 0.1^\circ$ ($\approx 10\text{ km}$ grid) continuous streamflow routing.
* **Forecast Horizon:** Daily ensemble river discharge ($m^3/s$) out to 30 days.

#### C. Mekong River Commission (MRC) Flash Flood Guidance & Telemetry
* **URL:** `https://ffw-web.mrcmekong.org/`
* **Coverage:** Border river reaches along Chiang Rai, Loei, Nong Khai, Bueng Kan, Nakhon Phanom, Mukdahan, and Ubon Ratchathani (Khong Chiam).
* **Data:** Water level telemetry, flood risk indices, and Flash Flood Guidance System (FFGS) indices.

#### D. Satellite Precipitation (Near Real-Time)
* **NASA GPM IMERG Early/Late Run:** $0.1^\circ$ every 30 minutes, calibrating localized tropical convection cells.
* **JAXA GSMaP (Global Satellite Mapping of Precipitation):** Hourly microwave-calibrated precipitation fields.
* **Open-Meteo API:** ECMWF IFS/GFS hourly downscaled precipitation forecast (0-168h, free, zero API key).

---

## 4. Nationwide Spatial Data Architecture


```

```
                              DATA INGESTION PIPELINE
                                         │
  ┌──────────────────────┬───────────────┴───────────────┬──────────────────────┐
  ▼                      ▼                               ▼                      ▼

```

[ ThaiWater / DWR ]     [ EGAT / RID Dams ]             [ GISTDA SAR Vectors ]  [ Open-Meteo Rain ]
(Every 15 mins)         (Daily / 6-hour updates)        (Every 24-48 hours)     (Hourly 7-day run)
│                      │                               │                      │
└──────────────────────┴───────────────┬───────────────┴──────────────────────┘
│
▼
[ Egress Relay / Scrapers ]
(SOCKS5 / Cloudflare Workers)
│
▼
[ PostgreSQL / PostGIS Engine ]
- Tables: stations, dams, reach_segments
- Raster: HAND 90m, MERIT DEM
│
▼
[ REST & GeoJSON Vector Tiles ]
/api/v2/national-summary
/api/v2/basin/{id}/hydrograph
/api/v2/station/{code}/forecast
│
▼
[ Frontend Client (React / Leaflet) ]

```

---

### 4.1 Canonical National Station Schema (JSON)

```json
{
  "station_id": "RID-C002",
  "source_agency": "RID",
  "name_th": "สถานี C.2 เมืองนครสวรรค์",
  "name_en": "Nakhon Sawan City Station",
  "basin_code": "05_CHAO_PHRAYA",
  "coordinates": {
    "latitude": 15.6987,
    "longitude": 100.1412
  },
  "reach_metadata": {
    "chainage_km": 375.2,
    "bank_elevation_msl": 26.20,
    "warning_elevation_msl": 25.70,
    "critical_elevation_msl": 26.20,
    "bed_slope": 0.000085,
    "upstream_dam_dependencies": ["EGAT_BHUMIBOL", "EGAT_SIRIKIT"]
  },
  "current_telemetry": {
    "timestamp": "2026-09-27T08:00:00+07:00",
    "water_elevation_msl": 25.85,
    "water_depth_m": 7.45,
    "discharge_m3s": 2480.0,
    "capacity_utilization_pct": 92.5,
    "status": "WARNING"
  },
  "forecast_horizons": [
    {
      "time_horizon": "+12h",
      "timestamp": "2026-09-27T20:00:00+07:00",
      "forecast_wse_msl": 26.05,
      "forecast_discharge_m3s": 2610.0,
      "trend": "RISING",
      "primary_driver": "UPSTREAM_DISCHARGE_PROPAGATION"
    },
    {
      "time_horizon": "+24h",
      "timestamp": "2026-09-28T08:00:00+07:00",
      "forecast_wse_msl": 26.25,
      "forecast_discharge_m3s": 2750.0,
      "trend": "CRITICAL_OVERTOPPING",
      "primary_driver": "UPSTREAM_DISCHARGE_PROPAGATION"
    },
    {
      "time_horizon": "+72h",
      "timestamp": "2026-09-30T08:00:00+07:00",
      "forecast_wse_msl": 25.90,
      "forecast_discharge_m3s": 2520.0,
      "trend": "RECEDING",
      "primary_driver": "RESERVOIR_RELEASE_REGULATION"
    }
  ]
}

```

---

### 4.2 Automated Ingestion & Muskingum-Cunge Worker (Python)

```python
import os
import math
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict

# Regional Thai Proxy Configuration
THAI_PROXY = os.getenv("THAI_EGRESS_PROXY", None)

class NationalFloodEngine:
    def __init__(self):
        self.http_client = httpx.Client(
            proxy=THAI_PROXY,
            timeout=15.0,
            headers={"User-Agent": "NationalHydrologyBot/2.0"}
        )
        
    def fetch_thaiwater_telemetry(self) -> List[Dict]:
        """Fetch all active national telemetry stations from ThaiWater API"""
        url = "[https://api2.thaiwater.net/v1/analyst/water/telemetry](https://api2.thaiwater.net/v1/analyst/water/telemetry)"
        response = self.http_client.get(url)
        response.raise_for_status()
        raw_data = response.json()
        return raw_data.get("data", [])

    def fetch_major_dams(self) -> List[Dict]:
        """Fetch EGAT & RID 24-hr dam operations"""
        url = "[https://api2.thaiwater.net/v1/analyst/water/dam](https://api2.thaiwater.net/v1/analyst/water/dam)"
        response = self.http_client.get(url)
        response.raise_for_status()
        return response.json().get("data", [])

    @staticmethod
    def calculate_muskingum_cunge(
        inflow_hydrograph: List[float], 
        dx: float, 
        dt: float, 
        b: float, 
        s0: float, 
        manning_n: float
    ) -> List[float]:
        """
        Routes an inflow hydrograph downstream using Muskingum-Cunge formulation.
        dx: Reach length (meters)
        dt: Time-step (seconds)
        b: Average channel bottom width (meters)
        s0: Channel bed slope (dimensionless)
        manning_n: Roughness coefficient (e.g. 0.035)
        """
        outflow = [inflow_hydrograph[0]]
        
        for n in range(len(inflow_hydrograph) - 1):
            i_n = inflow_hydrograph[n]
            i_n1 = inflow_hydrograph[n + 1]
            o_n = outflow[n]
            
            # Estimate hydraulic parameters based on reference flow Q0
            q0 = max(10.0, 0.5 * (i_n + o_n))
            # Normal depth approximation (Manning)
            h0 = ( (q0 * manning_n) / (b * math.sqrt(s0)) ) ** 0.6
            v0 = q0 / (b * h0)
            c_k = (5.0 / 3.0) * v0  # Kinematic celerity

            # Muskingum parameters
            k = dx / max(0.1, c_k)
            x = 0.5 * (1.0 - (q0 / (b * s0 * c_k * dx)))
            x = max(0.0, min(0.5, x))  # Stability bounds: 0 <= X <= 0.5

            denom = 2.0 * k * (1.0 - x) + dt
            c1 = (dt - 2.0 * k * x) / denom
            c2 = (dt + 2.0 * k * x) / denom
            c3 = (2.0 * k * (1.0 - x) - dt) / denom

            o_n1 = (c1 * i_n1) + (c2 * i_n) + (c3 * o_n)
            outflow.append(max(0.0, o_n1))

        return outflow

    def compute_basin_warning_index(self, stage_msl: float, bank_msl: float) -> Dict:
        """Citizen-centric status mapping based on bank-full metrics"""
        freeboard = bank_msl - stage_msl
        if freeboard > 1.0:
            return {"status": "NORMAL", "badge": "ปกติ", "action": "สถานการณ์น้ำอยู่ในเกณฑ์ปกติ"}
        elif 0.0 < freeboard <= 1.0:
            return {"status": "WARNING", "badge": "เฝ้าระวังตลิ่ง", "action": "เตรียมยกสิ่งของขึ้นที่สูง ระดับน้ำใกล้ล้นตลิ่ง"}
        elif -0.5 <= freeboard <= 0.0:
            return {"status": "OVERFLOW", "badge": "น้ำเอ่อล้นตลิ่ง", "action": "น้ำท่วมล้นตลิ่งเข้าพื้นที่ลุ่มต่ำ เลี่ยงเส้นทางเลียบแม่น้ำ"}
        else:
            return {"status": "CRITICAL", "badge": "วิกฤติวิกฤติน้ำท่วม", "action": "อพยพ ตัดกระแสไฟฟ้าในจุดน้ำท่วมสูง ห้ามสัญจร"}

```

---

## 5. UI/UX Strategy for the Expanded National App

When expanding `flood.bejranonda.com` to the entire nation, the UI dynamically switches context depending on the selected region.

```
                           NATIONAL NAVIGATION HIERARCHY
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                                                 ▼
[ Interactive National Macro-Map ]                               [ "Check My Home" (GPS) ]
- 22 Major River Basins Overview                                 - Single tap resolves:
- Color-coded basin risk status                                    • Nearest River Reach / Gauge
- Critical Headwater Dam Fill %                                    • Local Ground Level (HAND / DEM)
        │                                                          • Flash Flood vs. Inundation Risk
        ▼
[ Regional Context Switcher ]
├── 1. Northern Basin View: Flash Flood Radar + Dam Release Trackers
├── 2. Central Basin View: Fluvial Wave Tracking (C.2 -> C.13 -> C.29 -> BKK) + Retention Basins
├── 3. Northeastern View: Confluence Gauges (Chi-Mun Junction) + Overbank Prolongation
└── 4. Southern Coastal View: Combined Rain Burst + Gulf Tide Forecast

```

### 5.1 Context-Aware UI Adaptations by Zone

1. **Northern Highlands (Flash Flood Focus):**
* **Hero Warning:** Flash Flood / Debris Alert (*เฝ้าระวังน้ำป่าไหลหลากและดินโคลนถล่ม*).
* **Key Metrics:** 24-hour accumulated rainfall (mm), mountain stream rate of rise ($\text{cm/hr}$), dam storage fill percentage.


2. **Central Floodplains (Downstream Propagation Focus):**
* **Hero Warning:** Upstream Flood Pulse Arrival (*คลื่นน้ำเหนือหลาก*).
* **Key Metrics:** Discharge rate ($m^3/s$) at Chao Phraya Dam (C.13), discharge threshold flags ($2,000\text{ m}^3/\text{s}$ warning; $2,500\text{ m}^3/\text{s}$ severe), and estimated arrival time in Ayutthaya/Pathum Thani.


3. **Northeastern Khorat Basin (Backwater Confluence Focus):**
* **Hero Warning:** River Confluence Overflow (*น้ำท่วมล้นตลิ่งจากน้ำหนุนแม่น้ำมูล-ชี*).
* **Key Metrics:** Stage differential between Chi and Mun rivers, Mekong River stage at Khong Chiam.
* **Visual:** Prolonged inundation duration clock (*คาดการณ์น้ำท่วมขังอีก X วัน*).


4. **Peninsular & Coastal Estuaries (Tidal Coupling Focus):**
* **Hero Warning:** Dual Rain & Tide Surge (*น้ำล้นตลิ่งร่วมกับน้ำทะเลหนุนสูง*).
* **Key Metrics:** Peak astronomical high tide window vs. monsoon cloudburst timing.



---

## 6. Implementation Roadmap

```
PHASE 1: National Multi-Source Pipeline (Weeks 1-2)
├── Deploy egress bridge/workers for ThaiWater, RID, and EGAT APIs
├── Ingest Open-Meteo national 0.1° rainfall forecast grid
└── Store station network in PostGIS database

PHASE 2: Hydrological Routing & Dam Engine (Weeks 3-4)
├── Implement Muskingum-Cunge 1D channel routing for Chao Phraya, Ping, Nan, Yom, Chi, Mun
├── Integrate EGAT/RID dam release tracking & Rule Curve alerts
└── Integrate Google Flood Hub API / GloFAS streamflow benchmarks

PHASE 3: Topographic Terrain Inundation (Weeks 5-6)
├── Generate 90m HAND raster tiles for Thailand from MERIT DEM
├── Build GPU/Canvas shader to translate 1D routed stage into 2D street inundation depth
└── Ingest GISTDA Sentinel-1 SAR flood polygons for ground-truth validation

PHASE 4: Frontend Extension & Launch (Weeks 7-8)
├── Implement 22-basin macro-map on flood.bejranonda.com
├── Add GPS geolocator mapping users to nearest river reaches and local HAND depth
└── Roll out context-aware emergency badges (Flash Flood, Dam Release, Inundation)

```

```

You can view the [ThaiWater Platform Overview and Early Warning System](https://www.youtube.com/watch?v=gpy4ISRuGOM) to explore how Thailand's Ministry of Higher Education, Science, Research and Innovation (MHESI) structures its national data feeds and automated flood alerts across northern and provincial river basins.
http://googleusercontent.com/youtube_content/1

```