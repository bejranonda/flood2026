# `web/` — Thai, mobile-first web app

> **Status:** Production live at https://flood.autobahn.bot (**v0.9.0**). Built with vanilla HTML5, CSS3, and JavaScript, served directly by FastAPI and Cloudflare Tunnel for high performance on mobile devices. Includes 199 BMA canal gauges and 30-day 10-minute telemetry history via HII TIWRM.

## Features
- **Mobile-first Thai interface**: Summary statistics, status chips, Bangkok first, Leaflet interactive map with custom telemetry markers, bottom-sheet station details with 24 h outlook, trend arrows, recovery date predictions, and BMA drainage criteria.
- **Point check (`#p=lat,lon`, D-021, D-051)**: tap anywhere on the map or use GPS. One panel: 12–24 h outlook headline, "ปัจจัยที่ใช้คาดการณ์" (canal / rain / street reports, each a coloured dot + word; the canal dot follows the confidence gate), district line from `/api/reverse`, sources and caveats behind one ⓘ, report form behind a button (popup). Station lists below: gauges with a forecast (12/24 h change, 48 h only where proven, D-050) and nearest active gauges.
- **Enhanced Traffy street flood layer**: Increased hotspot visibility with refined purple stroke and translucent fill to make citizen street flooding instantly clear.
- **Place search**: Fast geocoding via OpenStreetMap Nominatim for soi / street / district search without third-party tracking.
- **Brand & Web Assets**: Modern, high-contrast, scalable favicon and PWA icon suite:
  - `favicon.svg`: Scalable SVG featuring the Flood Droplet & Wave motif with luminous sky-blue rim and soft drop shadow.
  - `favicon.ico`: Dual-resolution (16×16 and 32×32) Windows and browser tab icon.
  - `apple-touch-icon.png`: 180×180 high-res icon on a deep oceanic squircle canvas (preventing black backgrounds on iOS home screens).
  - `icon-192.png`: 192×192 PWA / Android home screen icon.
  - Generated via `scripts/generate_favicon.py` using 2×2 supersampling pure Python (zero external dependencies).

## Rules
- Talks only to our own `/api/*` endpoints. Minimal bundle size; loads fast on 3G/4G connections.
- Design tokens defined via CSS variables in `style.css`.
- All external strings escaped via `esc()`; no unsanitized `innerHTML`.
- Cache-busters (`?v=N`) maintained on scripts, stylesheets, and icon tags in `index.html`.
