#!/usr/bin/env python3
"""Generate BKK FloodWatch favicon assets: favicon.svg, favicon.ico, apple-touch-icon.png."""
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d3b66"/>
      <stop offset="100%" stop-color="#061c33"/>
    </linearGradient>
    <linearGradient id="wave1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0077b6" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#0096c7" stop-opacity="0.7"/>
    </linearGradient>
    <linearGradient id="wave2" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00b4d8"/>
      <stop offset="50%" stop-color="#48cae4"/>
      <stop offset="100%" stop-color="#90e0ef"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1.5" stdDeviation="1" flood-color="#000" flood-opacity="0.35"/>
    </filter>
  </defs>

  <!-- Background tile with subtle border -->
  <rect width="64" height="64" rx="14" fill="url(#bg)"/>
  <rect width="62" height="62" x="1" y="1" rx="13" fill="none" stroke="#255585" stroke-width="1" opacity="0.6"/>

  <!-- Back Water Wave -->
  <path d="M3 41 C13 35, 23 44, 35 38 C45 32, 53 36, 61 40 L61 54 C61 57.5 57.5 61 54 61 L10 61 C6.5 61 3 57.5 3 54 Z" fill="url(#wave1)"/>

  <!-- Front Water Wave -->
  <path d="M3 47 C15 40, 25 50, 39 43 C47 38, 55 41, 61 44 L61 54 C61 57.5 57.5 61 54 61 L10 61 C6.5 61 3 57.5 3 54 Z" fill="url(#wave2)"/>

  <!-- Water Gauge & Telemetry Beacon -->
  <g filter="url(#shadow)">
    <!-- Water droplet shape -->
    <path d="M32 10 C32 10, 19 26, 19 33 C19 40.2 24.8 46 32 46 C39.2 46 45 40.2 45 33 C45 26, 32 10, 32 10 Z" fill="#ffffff" opacity="0.95"/>
    <path d="M32 14 C32 14, 22 27, 22 33 C22 38.5 26.5 43 32 43 C37.5 43 42 38.5 42 33 C42 27, 32 14, 32 14 Z" fill="#0077b6"/>
    <path d="M32 18 C32 18, 25 28, 25 33 C25 36.9 28.1 40 32 40 C35.9 40 39 36.9 39 33 C39 28, 32 18, 32 18 Z" fill="#00b4d8"/>

    <!-- Pulse beacon center (FloodWatch gold #f4d35e) -->
    <circle cx="32" cy="33" r="4" fill="#f4d35e"/>
    <circle cx="32" cy="33" r="1.8" fill="#ffffff"/>

    <!-- Specular highlight reflection -->
    <ellipse cx="27" cy="27" rx="1.5" ry="3" transform="rotate(-30 27 27)" fill="#ffffff" opacity="0.8"/>
  </g>

  <!-- Measuring gauge ticks on the right -->
  <line x1="49" y1="18" x2="55" y2="18" stroke="#f4d35e" stroke-width="2" stroke-linecap="round"/>
  <line x1="51" y1="24" x2="55" y2="24" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" opacity="0.85"/>
  <line x1="49" y1="30" x2="55" y2="30" stroke="#48cae4" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

def make_png(size: int) -> bytes:
    """Generate a clean, antialiased icon bitmap matching the SVG design."""
    w = h = size
    raw = bytearray()
    
    # Precompute shape metrics normalized to 0..1
    radius = 0.22  # corner radius
    
    for y in range(h):
        raw.append(0)  # filter None
        ny = (y + 0.5) / h
        for x in range(w):
            nx = (x + 0.5) / w
            
            # Distance to rounded rect border (0..1 space)
            dx = max(0.0, abs(nx - 0.5) - (0.5 - radius))
            dy = max(0.0, abs(ny - 0.5) - (0.5 - radius))
            dist_sq = dx*dx + dy*dy
            in_rect = dist_sq <= radius * radius
            
            if not in_rect:
                # Outside rounded rect
                raw.extend([0, 0, 0, 0])
                continue
            
            # Base color gradient: #0d3b66 (13, 59, 102) -> #061c33 (6, 28, 51)
            t = (nx + ny) * 0.5
            r = int(13 * (1 - t) + 6 * t)
            g = int(59 * (1 - t) + 28 * t)
            b = int(102 * (1 - t) + 51 * t)
            a = 255
            
            # Wave layer 1 (back wave): y > 0.60 + 0.08*sin(nx*6)
            wave1_y = 0.62 + 0.07 * math.sin(nx * 5.5 + 0.5)
            if ny > wave1_y:
                # Wave 1 color: #0077b6
                r = int(r * 0.3 + 0 * 0.7)
                g = int(g * 0.3 + 119 * 0.7)
                b = int(b * 0.3 + 182 * 0.7)
            
            # Wave layer 2 (front wave): y > 0.70 + 0.06*sin(nx*7 + 2)
            wave2_y = 0.72 + 0.06 * math.sin(nx * 6.5 + 2.0)
            if ny > wave2_y:
                # Wave 2 color: #00b4d8 -> #48cae4
                wt = nx
                r = int(0 * (1 - wt) + 72 * wt)
                g = int(180 * (1 - wt) + 202 * wt)
                b = int(216 * (1 - wt) + 228 * wt)
            
            # Droplet & Beacon in upper/center: center at (0.50, 0.48)
            cx, cy = 0.50, 0.48
            ddx = (nx - cx)
            ddy = (ny - cy)
            d_center = math.sqrt(ddx*ddx + ddy*ddy)
            
            # Droplet outline/body check
            # Top tip around (0.50, 0.18), bottom circle radius 0.20 centered at (0.50, 0.48)
            in_drop_circle = d_center <= 0.19
            # Upper cone: ny between 0.18 and 0.48, abs(ddx) <= (ny - 0.18) * 0.58
            in_drop_cone = (0.17 <= ny <= 0.48) and (abs(ddx) <= (ny - 0.17) * 0.60)
            
            if in_drop_circle or in_drop_cone:
                # Outer white rim
                r, g, b = 255, 255, 255
                # Inner droplet: slightly smaller
                in_inner_circle = d_center <= 0.15
                in_inner_cone = (0.22 <= ny <= 0.48) and (abs(ddx) <= (ny - 0.22) * 0.55)
                if in_inner_circle or in_inner_cone:
                    # Droplet blue: #0096c7
                    r, g, b = 0, 150, 199
                    
                    # Yellow center beacon: radius 0.065
                    if d_center <= 0.075:
                        r, g, b = 244, 211, 94  # #f4d35e
                        if d_center <= 0.030:
                            r, g, b = 255, 255, 255
                    elif ddx < -0.04 and -0.08 < ddy < 0.02:
                        # specular highlight
                        r, g, b = 200, 240, 255

            # Gauge tick marks on the right side: nx between 0.76 and 0.88
            if 0.76 <= nx <= 0.88:
                # Tick 1: ny ~ 0.28
                if abs(ny - 0.28) <= 0.020:
                    r, g, b = 244, 211, 94  # gold
                # Tick 2: ny ~ 0.38
                elif abs(ny - 0.38) <= 0.016 and nx >= 0.80:
                    r, g, b = 255, 255, 255  # white
                # Tick 3: ny ~ 0.48
                elif abs(ny - 0.48) <= 0.020:
                    r, g, b = 72, 202, 228  # cyan

            raw.extend([r, g, b, a])
            
    compressed = zlib.compress(bytes(raw), 9)
    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')


def make_ico(png_32: bytes, png_16: bytes) -> bytes:
    """Build a valid standard Windows/browser .ico holding 16x16 and 32x32 PNG images."""
    num_images = 2
    header = struct.pack('<HHH', 0, 1, num_images)  # reserved, type 1 (ICO), count
    
    offset_1 = 6 + 16 * num_images
    entry_1 = struct.pack(
        '<BBBBHHII',
        16, 16, 0, 0, 1, 32, len(png_16), offset_1
    )
    offset_2 = offset_1 + len(png_16)
    entry_2 = struct.pack(
        '<BBBBHHII',
        32, 32, 0, 0, 1, 32, len(png_32), offset_2
    )
    return header + entry_1 + entry_2 + png_16 + png_32


def main():
    WEB.mkdir(exist_ok=True)
    
    # 1. Write favicon.svg
    svg_path = WEB / "favicon.svg"
    svg_path.write_text(SVG_CONTENT.strip() + "\n", encoding="utf-8")
    print(f"Wrote {svg_path} ({len(SVG_CONTENT)} bytes)")
    
    # 2. Generate PNGs: 16x16, 32x32, 180x180 (Apple touch icon), 192x192
    png_16 = make_png(16)
    png_32 = make_png(32)
    png_180 = make_png(180)
    png_192 = make_png(192)
    
    ico_bytes = make_ico(png_32, png_16)
    ico_path = WEB / "favicon.ico"
    ico_path.write_bytes(ico_bytes)
    print(f"Wrote {ico_path} ({len(ico_bytes)} bytes)")
    
    touch_path = WEB / "apple-touch-icon.png"
    touch_path.write_bytes(png_180)
    print(f"Wrote {touch_path} ({len(png_180)} bytes)")
    
    icon_192 = WEB / "icon-192.png"
    icon_192.write_bytes(png_192)
    print(f"Wrote {icon_192} ({len(png_192)} bytes)")


if __name__ == "__main__":
    main()
