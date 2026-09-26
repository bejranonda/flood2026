# KNOWN_ISSUES.md — Bottlenecks, API Limitations & Workarounds

> **Project:** Bangkok & Central Thailand Flood Intelligence & Hydrodynamic Forecasting Platform (2026)  
> **Audience:** Developers, DevOps Engineers, and System Operators  
> **Last Updated:** 26 September 2026

---

## Executive Summary

During hydroinformatics research and empirical API testing across Thai government, military, and meteorological sources, several operational bottlenecks, firewall restrictions, and data formatting anomalies were identified. This document records each known issue alongside its verified engineering workaround.

---

## 1. Thai Government Telemetry API Egress Firewalls & HTTP 403 Forbidden

### Symptom
When querying `https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load` or other HAII endpoints from international cloud datacenters (AWS, GCP, DigitalOcean) or sandboxed environments, requests may return:
```http
HTTP/1.1 403 Forbidden
Content-Type: text/html
Connection: close
```

### Root Cause
1. **Geo-IP / Datacenter Filtering:** Thai government infrastructure frequently implements strict perimeter WAFs (Web Application Firewalls) that throttle or outright reject inbound traffic originating from non-Thai IP ranges or known cloud provider ASNs (Autonomous System Numbers).
2. **Strict User-Agent Inspection:** Generic HTTP clients (e.g. `curl`, `python-requests/2.x`, `Go-http-client`) without complete browser headers are blocked by default anti-scraping rules.

### Solution & Workaround
* **Host Location:** Deploy the core VPS and data collectors in **Singapore or directly inside Thailand** (e.g., local Thai cloud or colocation provider).
* **Cloudflare Workers Proxy:** If running the VPS in a region that is blocked, route collector requests through a lightweight Cloudflare Worker or reverse proxy operating from Bangkok/Singapore edge nodes.
* **Header Spoofing & Custom User-Agent:**
  ```python
  headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*",
      "Accept-Language": "th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7",
      "Origin": "https://www.thaiwater.net",
      "Referer": "https://www.thaiwater.net/"
  }
  ```
* **Single-Flight Request Caching:** Cache responses for 5 minutes locally; avoid rapid multi-threaded polling that triggers rate-limit IP bans.

---

## 2. Royal Thai Navy Astronomical Tide Tables Locked in Annual PDFs

### Symptom
The Hydrographic Department of the Royal Thai Navy (RTN / กรมอุทกศาสตร์ กองทัพเรือ) provides the most authoritative tidal constituent predictions for the Gulf of Thailand and the Chao Phraya estuarine reach, but publishes them primarily as:
- Annual PDF documents (e.g., `https://www.hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf`)
- Interactive ASP.NET web forms without a documented public REST API.

### Technical Complications
1. **Vertical Datum Mismatch:** Navy tide tables are referenced to **Lowest Low Water (LLW / ม.ตลน.)**, whereas all urban floodwalls, street elevations, and RID river gauges use **Mean Sea Level (Ko Lak MSL / ม.รทก.)**.
2. **Table Parsing Fragility:** Annual PDF formats shift slightly between years, risking parser breakage.

### Solution & Workaround
* **Automated Annual Ingestion Script:** Parse the PDF once per calendar year using `pdfplumber` / `pypdf` into a persistent SQLite/TimescaleDB lookup table: `tide_astronomical_hourly(station_id, timestamp, height_llw, height_msl)`.
* **Datum Translation Offsets:** Calibrate station-specific LLW $\to$ MSL translation constants based on official hydrographic benchmarks:
  $$\Delta Z_{\text{Fort\_Chula}} = -1.55\text{ m MSL}$$
  $$\Delta Z_{\text{Bangkok\_Port}} = -1.35\text{ m MSL}$$
  $$\Delta Z_{\text{Memorial\_Bridge}} = -1.25\text{ m MSL}$$
* **Self-Contained Harmonic Engine Fallback (`utide`):**
  Train a local harmonic tidal model using Python's `utide` on historical sea-level records. The engine computes:
  $$H_{\text{ast}}(t) = Z_0 + \sum_{k=1}^{M} f_k A_k \cos\left( \omega_k t + V_k + u_k - \kappa_k \right)$$
  using the 4 primary constituents ($M_2, S_2, K_1, O_1$) plus shallow water overtides ($M_4, MS_4$), enabling sub-second local tide generation without hitting external servers.

---

## 3. BMA Department of Drainage & Sewerage (DDS) Telemetry Inaccessibility

### Symptom
BMA's Department of Drainage and Sewerage operates over 120 canal gauges, 55 flow stations, and 270 pump stations (`https://dds.bangkok.go.th/` and `http://weather.bangkok.go.th/water/`), but does not provide an open developer API gateway with API keys.

### Technical Complications
* Endpoints use legacy ASP.NET WebForms (`.aspx`) with dynamic `__VIEWSTATE` and `__EVENTVALIDATION` tokens.
* Network timeouts during storm peaks when citizen traffic spikes on DDS servers.

### Solution & Workaround
1. **Mirroring via HAII ThaiWater:** Many key BMA canal stations (such as `BKK008` Khlong Saen Saep, `BKK021` Khlong Lat Phrao) are already aggregated by HAII ThaiWater v3 API under the `agency: "bma"` tag. **Always query HAII first.**
2. **Resilient Headless Scraper:** For stations exclusive to BMA DDS:
   * Query `http://weather.bangkok.go.th/water/CanalList.aspx` every 10 minutes using `cheerio` / `BeautifulSoup`.
   * Apply a **Circuit Breaker pattern**: if BMA fails 3 consecutive times, fall back to the last known canal state with an exponential backoff warning flag (`degraded_mode: true`).

---

## 4. HAII ThaiWater 7-Day History Retention Horizon

### Symptom
The public REST API of HAII guarantees only **7 rolling days of historical observations** on several endpoints. Older time series are either archived behind internal permissions or trimmed.

### Impact on ML Training
Machine learning models (LightGBM, Random Forest, LSTMs) require multiple flood seasons (e.g., 2011, 2017, 2021, 2022, 2024, 2026) to learn non-linear catchment responses and recession curves.

### Solution & Workaround
* **Immediate Raw Archiving:** Start the raw time-series collector on Day 1. Store every incoming JSON response in raw, gzip-compressed format (`YYYY/MM/DD/source_payload_hash.json.gz`) replicated to **Cloudflare R2**.
* **Historical Backfilling Pipeline:**
  * Pull multi-year daily maximums from data.go.th (e.g. Chao Phraya at Pak Khlong Talat dataset).
  * Ingest GloFAS v4 1984–present daily discharge reanalysis via Open-Meteo Flood API.
  * Extract RID annual hydrology yearbooks (hydro-c2, c13, c29 tables).

---

## 5. DEM Vertical Accuracy Discrepancy vs Street Flood Depths

### Symptom
Freely available global Digital Elevation Models (such as Copernicus GLO-30 or NASA SRTM) have a vertical Root Mean Square Error (RMSE) of $\pm 1.0\text{ m}$ to $\pm 1.5\text{ m}$ in flat, coastal delta environments like Bangkok.

### Impact on Citizen Experience
Urban street floods operate at a scale of **10 to 35 centimeters** (sidewalk height vs car exhaust level). A 1-meter vertical terrain error will incorrectly report dry streets as underwater or flooded streets as safe.

### Solution & Workaround
1. **FABDEM Integration:** Utilize **FABDEM** (Forest And Buildings removed Copernicus DEM), which reduces building/forest canopy bias and achieves the highest vertical fidelity in Bangkok.
2. **HAND (Height Above Nearest Drainage):** Rather than raw absolute elevation, calculate relative height above the receiving canal embankment.
3. **Probabilistic Inundation Output:**
   Never state an absolute depth with false precision. Report the depth as a confidence distribution:
   $$P(d > 0) = \Phi\left(\frac{H_{\text{water}} - Z_{\text{road}}}{\sqrt{\sigma_{\text{DEM}}^2 + \sigma_{\text{forecast}}^2}}\right)$$
   Categorize into practical physical bands:
   * **1–10 cm:** Footpath wash / caution for motorcycles
   * **11–20 cm:** Curb height / small cars slow down
   * **21–35 cm:** Half-wheel / sedans avoid passage
   * **> 50 cm:** Floor height / emergency evacuation
4. **User Calibration Input:** Allow citizens to adjust their local threshold: *"ถนนหน้าบ้านสูงกว่าคลองกี่ ซม."* (Personalized road elevation offset).

---

## 6. Managed Hydraulic Interventions & Non-Stationary Operations

### Symptom
Bangkok's flood levels are heavily manipulated by human intervention. When RID suddenly increases the Chao Phraya Dam release from $1,500\text{ m}^3/\text{s}$ to $2,000\text{ m}^3/\text{s}$, or BMA shuts a major canal gate, purely statistical models produce erroneous forecasts.

### Solution & Workaround
* **Scenario-Based Boundary Conditions:** Treat announced RID dam release schedules as deterministic upstream boundaries:
  *"พยากรณ์อิงตามแผนการระบายน้ำของกรมชลประทานที่ 2,000 ลบ.ม./วินาที"*
* **Event-Flag Features in ML Models:** Feed active gate state, pump availability percentage, and announced warning alerts as binary/continuous features into LightGBM.
* **Fast Error Fading:** Blend in an autoregressive residual correction:
  $$\hat{\varepsilon}(t+h) = \phi^h \cdot \left( H_{\text{obs}}(t) - H_{\text{model}}(t) \right)$$
  which eliminates instantaneous bias and naturally decays over longer forecast horizons.

---

## 7. Cloudflare Token Scope & Tunnel Routing Configuration

### Symptom
When establishing Cloudflare Tunnels (`cloudflared`) or deploying edge functions, authentication failures or routing drops occur if tokens are misconfigured.

### Solution & Workaround
* **Token Creation Requirements in Cloudflare Dashboard:**
  * **Permissions:**
    * `Account.Cloudflare Tunnel`: Edit
    * `Account.Workers / Pages`: Edit
    * `Zone.DNS`: Edit
    * `Zone.Cache Purge`: Purge
* **Zero-Expose Ingress Rule:**
  The production VPS should **never expose port 80/443 directly to the public internet**. Run `cloudflared tunnel run` locally on the VPS, routing inbound traffic from `flood.yourdomain.com` directly to `http://localhost:3000`. This completely shields the origin server from DDoS attacks and port scanning.

---

## 8. Browser Cross-Origin (CORS) Restrictions on Thai Telemetry Endpoints

### Symptom
When calling `https://api-v3.thaiwater.net` or `https://weather.bangkok.go.th` directly from frontend browser JavaScript (`fetch()` or `axios`), browsers block the request:
```text
Access to fetch at 'https://api-v3.thaiwater.net/...' from origin 'https://flood.bejranonda.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### Technical Complications
Thai government endpoints do not return permissive wildcard CORS headers (`Access-Control-Allow-Origin: *`). Direct frontend calls will always fail in modern browsers.

### Solution & Workaround
* **Never call external Thai endpoints directly from frontend clients.**
* **Deploy Cloudflare Edge Micro-Proxy / Worker:**
  * Route requests to `https://flood.bejranonda.com/api/water-levels`.
  * The Cloudflare Worker / VPS backend fetches upstream data with appropriate `User-Agent` headers.
  * Adds `Access-Control-Allow-Origin: *` and `Cache-Control: public, max-age=300`.
  * Edge caches the response for 5 minutes, eliminating redundant external queries and protecting against rate limits.

---

## 9. Third-Party Elevation API Throttling & Cost Discrepancy

### Symptom
Calling commercial elevation services (e.g., Google Elevation API) for every user GPS coordinate query creates recurring API costs and latency spikes (> 1.5 seconds) during flood traffic surges.

### Solution & Workaround
1. **Pre-Compiled Benchmark Lookup:** Bundle `bkk_stations_elevation.json` covering the top 50 flood-prone road segments in Bangkok with sub-millisecond local RAM lookup.
2. **Open-Meteo Elevation API:** For points outside the curated benchmark list, query `https://api.open-meteo.com/v1/elevation` (free, keyless).
3. **Open-Elevation Open-Source Fallback:** Maintain an offline raster lookup using FABDEM COG tiles loaded locally on the VPS.

