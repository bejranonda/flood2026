# `web/` — Thai, mobile-first web app

> **Status:** Production live at https://flood.autobahn.bot (**v0.5.1**). Built with vanilla HTML5, CSS3, and JavaScript, served directly by FastAPI and Cloudflare Tunnel for high performance on mobile devices.

## Features
- **Mobile-first Thai interface**: Summary statistics, status chips, Bangkok first, Leaflet interactive map with custom telemetry markers, bottom-sheet station details with 24 h outlook, trend arrows, recovery date predictions, and BMA drainage criteria.
- **Point check (`#p=lat,lon`)**: Tap anywhere on the map or use GPS to inspect nearby gauges, channel conditions, and Traffy Fondue citizen reports with clear warnings.
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
