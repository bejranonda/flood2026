You don't need any API key to start: the core of the app runs entirely on keyless sources. Keys only matter for two optional extras, and both are free to register.

**No key needed (enough for v1)**

- **HII ThaiWater** is the backbone: real-time water level, bank level, rainfall and history. The open-source project I found calls its public endpoints (`waterlevel_load`, `rain_24h`, `waterlevel_graph`) with just a User-Agent header, no key. Since it isn't a formally documented public API, cache your data and contact HII for permission before going public.
- **Open-Meteo** covers the rain forecast, ensembles, and GloFAS river discharge. No key or account is needed for non-commercial use. If the app ever earns money, you'd switch to their paid plan.
- **Navy tide tables** are a PDF download, so you parse the file once a year.
- **BMA DDS pages and radar** are public web pages. You read the JSON the pages load (visible in browser DevTools) or scrape the pages politely.
- **Historical data** comes from DWR daily report PDFs and data.go.th CSV downloads. Downloading from data.go.th needs no key.

**Free keys (optional, register yourself)**

| Source | What it adds | How to get the key | Keyless alternative |
|---|---|---|---|
| TMD (กรมอุตุฯ) | Official Thai weather observations and forecasts | Register free at data.tmd.go.th/api. It provides 3-hourly and daily observations, daily and weekly forecasts, and automatic weather station data. | Open-Meteo for forecasts; HII rain gauges for observations |
| GISTDA | Daily satellite flood extent and flood recurrence in Thailand | Register free at api-gateway.gistda.or.th/v2. The flood extent endpoint takes lat/lon plus your key. | Copernicus GFM (see below) |

**Best free alternative for satellite flood maps: Copernicus GFM**

Copernicus Global Flood Monitoring processes every incoming Sentinel-1 radar image automatically, with three flood detection algorithms. You can access it three ways:
- the GloFAS map viewer,
- an API at `api.gfm.eodc.eu/v2`,
- a web portal where you can download data and get notifications.

Access is free and open, but you need to register an account for the map viewer. Registered users can draw up to 25 areas of interest and get notified when new flood layers arrive. Draw one area over Bangkok and one over Ayutthaya/Pathum Thani.

**Other free options**

- **NASA GPM IMERG**: satellite rainfall for the upstream basin. It needs a free NASA Earthdata login, not a paid key.
- **Copernicus Data Space**: raw Sentinel-1 imagery, with a free account, if you ever want to run your own flood detection.
- **FABDEM / Copernicus DEM**: elevation data, downloadable free without any key.

**My recommendation:** build v1 on HII, Open-Meteo, and the Navy tide tables, all keyless. Then register TMD and GISTDA in parallel, since registration takes a few minutes but approval may take days. Add Copernicus GFM as the satellite layer if GISTDA approval is slow.

Would you like me to add this key-and-alternatives table to `SOURCES.md`?