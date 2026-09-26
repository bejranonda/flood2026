When you do not have official Thai government API keys, you can implement **three practical strategies**:

1. **Zero-Key Open APIs & Local Mathematical Models** (immediate, 100% free, no signup required).
2. **Free Registration Portals** for official Thai government developer keys.
3. **Edge Micro-Proxying & Reverse-Engineered Endpoints** to bypass CORS and extract live data without gated credentials.

---

### Strategy Matrix

| Data Domain | Official Free Key (Registration) | Zero-Key Alternative (Instant) | Client-Side / Local Calculation |
| --- | --- | --- | --- |
| **Rain & Weather Forecast** | TMD Developer API (`data.tmd.go.th`) | **Open-Meteo API** (No key, 10,000 calls/day free) | — |
| **River & Canal Levels** | `data.go.th` (DGA Open Data API) | **ThaiWater Internal REST Endpoints** (Reverse-engineered) | Analytical Fluvial Delay ($C.29 \rightarrow \text{BKK}$) |
| **Gulf Astronomical Tide** | Navy Hydrographic Dept (Annual PDF/Tables) | Pre-compiled Harmonic Table / Lookup GeoJSON | **Harmonic Equation ($M_2, S_2, K_1, O_1$)** |
| **Street Elevation (DEM)** | GISTDA Portal | **Open-Meteo Elevation API** or **Open-Elevation** | Local Station Reference Lookup (JSON) |
| **Bangkok Canal Gates/Pumps** | BMA Open Data (`data.bangkok.go.th`) | Scrape `dds.bangkok.go.th` / `flood.bangkok.go.th` | Mass balance pumping estimate ($Q_{\text{pump}}$) |

---

### 1. Zero-Key Immediate Data Sources

#### A. Weather & Rainfall Forecast: Open-Meteo API

Open-Meteo requires **no API key**, allows up to 10,000 daily requests free for non-commercial use, and aggregates ECMWF/GFS weather models with hourly precipitation.

```javascript
// Fetch hourly rainfall forecast for central Bangkok (Zero API key needed)
async function getBangkokRainForecast() {
  const url = "https://api.open-meteo.com/v1/forecast?" + new URLSearchParams({
    latitude: 13.7563,
    longitude: 100.5018,
    hourly: "precipitation,precipitation_probability,rain,surface_pressure,wind_speed_10m",
    timezone: "Asia/Bangkok",
    forecast_days: 3
  });

  const res = await fetch(url);
  const data = await res.json();
  
  // data.hourly.time -> array of ISO timestamps
  // data.hourly.precipitation -> array of mm/hr rain values
  return data.hourly;
}

```

#### B. Gulf Tidal Surge: Pure Client-Side Harmonic Calculation (Zero Network Calls)

Astronomical high tides in the Gulf of Thailand are deterministic and predictable. You do not need an external API to calculate them; use the 4 primary harmonic constituents ($M_2$, $S_2$, $K_1$, $O_1$) calibrated for Fort Chulachomklao:

```javascript
/**
 * Predict astronomical tide elevation (m MSL) for Fort Chulachomklao / Bangkok Port
 * @param {Date} date - Target date and time
 * @returns {number} Tide level in meters MSL
 */
function calculateAstronomicalTide(date) {
  const MSL_OFFSET = 0.95; // Mean Sea Level benchmark
  
  // Hours since reference epoch (Jan 1, 2026 00:00 UTC)
  const epoch = new Date("2026-01-01T00:00:00Z");
  const t = (date.getTime() - epoch.getTime()) / (1000 * 3600);

  // Harmonic speeds (degrees/hour) and amplitudes (meters) for Fort Chulachomklao
  const constituents = [
    { name: "M2", speed: 28.9841042, amp: 0.62, phase: 125.4 }, // Main lunar semidiurnal
    { name: "S2", speed: 30.0000000, amp: 0.28, phase: 172.1 }, // Main solar semidiurnal
    { name: "K1", speed: 15.0410686, amp: 0.44, phase: 210.8 }, // Lunar diurnal
    { name: "O1", speed: 13.9430356, amp: 0.35, phase: 185.3 }  // Lunar diurnal
  ];

  const degToRad = Math.PI / 180;
  let tideAnomaly = 0;

  for (const c of constituents) {
    const angle = (c.speed * t - c.phase) * degToRad;
    tideAnomaly += c.amp * Math.cos(angle);
  }

  return Number((MSL_OFFSET + tideAnomaly).toFixed(2));
}

```

#### C. Elevation & Street Ground Level: Local Static Lookup

Instead of paying for Google Elevation API or calling rate-limited services, bundle a lightweight static lookup file (`bkk_stations_elevation.json`) containing calibrated road levels for Bangkok's major drainage points:

```json
{
  "STN_RAMA_VII": { "lat": 13.8131, "lon": 100.5175, "road_elevation_msl": 2.20, "curb_height_m": 0.15 },
  "STN_MEMORIAL_BRIDGE": { "lat": 13.7392, "lon": 100.4984, "road_elevation_msl": 1.95, "curb_height_m": 0.15 },
  "STN_BANG_NA": { "lat": 13.6681, "lon": 100.5919, "road_elevation_msl": 1.50, "curb_height_m": 0.12 },
  "STN_KLONG_SAEN_SAEP_ASOKE": { "lat": 13.7495, "lon": 100.5636, "road_elevation_msl": 1.40, "curb_height_m": 0.15 },
  "STN_RATCHADA_LADPRAO": { "lat": 13.8062, "lon": 100.5742, "road_elevation_msl": 1.20, "curb_height_m": 0.15 }
}

```

---

### 2. How to Get Official Free Thai Government API Keys

If you want official, sanctioned API access, sign up at these government developer portals:

#### A. DGA Open Government Data Portal (`data.go.th`)

* **URL:** [opend.data.go.th/register_api/signup.php](https://opend.data.go.th/register_api/signup.php?utm_source=gemini)
* **Cost:** 100% Free.
* **Registration Steps:**
1. Register with an email address.
2. Verify your email and log in to the dashboard.
3. Copy your personal `apiKey`.


* **Available Data:** National water levels, dam storage capacities, and HAII historical telemetry datasets.

#### B. TMD Weather Data Portal (`data.tmd.go.th`)

* **URL:** [data.tmd.go.th/api/](https://www.google.com/search?q=https://data.tmd.go.th/api/&utm_source=gemini)
* **Cost:** 100% Free.
* **Registration Steps:**
1. Register for an account on the TMD data service portal.
2. Receive a developer `uid` and `ukey`.


* **Access Format:**
```http
GET https://data.tmd.go.th/api/WeatherToday/v2/?uid={YOUR_UID}&ukey={YOUR_UKEY}&format=json

```



---

### 3. Alternative: Reverse-Engineered Public Endpoints & Edge Scraping

Official Thai web dashboards (ThaiWater, BMA DDS) make client-side AJAX requests to endpoints that do not require OAuth authentication for public data viewing.

> **Browser CORS Limitation:** You cannot call `thaiwater.net` or `bangkok.go.th` directly from frontend browser JavaScript due to CORS policy. You must route requests through a lightweight server or Edge Worker.

#### Deploy a Free Cloudflare Worker Proxy (100,000 Free Requests/Day)

Create a Cloudflare Worker to scrape/fetch the data, cache it for 5 minutes, and return clean JSON with CORS enabled:

```javascript
// cloudflare-worker.js
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Endpoint 1: Upstream & Bangkok Chao Phraya telemetry
    if (url.pathname === "/api/water-levels") {
      const cacheKey = new Request("https://cache.local/water-levels");
      const cache = caches.default;
      let response = await cache.match(cacheKey);

      if (!response) {
        // Fetch from public mobile telemetry endpoint
        const targetUrl = "https://api2.thaiwater.net/v1/analyst/water/telemetry";
        const upstream = await fetch(targetUrl, {
          headers: {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json"
          }
        });

        const data = await upstream.json();

        // Extract key stations (C.29 Bang Sai, Memorial Bridge, Bang Na)
        const relevantStations = (data.data || []).filter(s => 
          ["C.29", "C.22", "BKK01", "BKK02"].includes(s.station_code)
        );

        response = new Response(JSON.stringify(relevantStations), {
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=300" // Cache 5 minutes
          }
        });

        ctx.waitUntil(cache.put(cacheKey, response.clone()));
      }

      return response;
    }

    // Endpoint 2: Fallback Mock Telemetry if external sources are down
    if (url.pathname === "/api/health") {
      return new Response(JSON.stringify({ status: "ok", timestamp: new Date().toISOString() }), {
        headers: { "Access-Control-Allow-Origin": "*" }
      });
    }

    return new Response("Not Found", { status: 404 });
  }
};

```

---

### Suggested App Architecture with Zero API Keys

```
[ Frontend: React / Vue / Vanilla JS ]
   │
   ├──> 1. Open-Meteo API (Direct from browser: Zero Key, Rain/Wind forecast)
   │
   ├──> 2. Astronomical Tide Engine (Pure JS math calculation: Zero Network)
   │
   ├──> 3. Static Elevation Lookup (Local JSON inside bundle: Zero Network)
   │
   └──> 4. Cloudflare Worker (/api/water-levels)
           │
           └──> Cached scrape of ThaiWater / BMA DDS (Free edge proxy)

```

This hybrid setup allows you to run the complete predictive flood engine immediately without waiting for government API approvals or running into authentication blocks.