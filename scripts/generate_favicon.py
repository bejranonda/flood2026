#!/usr/bin/env python3
"""Generate ultra-simple Bold Wave Tile favicon assets."""
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#0369a1"/>
    </linearGradient>
    <clipPath id="tileClip">
      <rect width="64" height="64" rx="16"/>
    </clipPath>
  </defs>

  <!-- Rounded Tile Canvas -->
  <rect width="64" height="64" rx="16" fill="url(#bg)"/>

  <g clip-path="url(#tileClip)">
    <!-- Electric Cyan Underbelly -->
    <path d="M 0 34 C 18 22 34 40 64 24 L 64 64 L 0 64 Z" fill="#38bdf8"/>

    <!-- Bold Pure White Surge Wave (Instant high-contrast 16px recognition) -->
    <path d="M 0 46 C 18 34 34 48 48 34 C 54 28 60 20 64 14 L 64 64 L 0 64 Z" fill="#ffffff"/>
  </g>
</svg>
"""

def make_png(size: int) -> bytes:
    """Generate clean antialiased bitmap with 2x2 supersampling."""
    w = h = size
    raw = bytearray()
    radius = 0.25  # Corner radius (16/64 = 0.25)
    
    sub_offsets = [(-0.25, -0.25), (0.25, -0.25), (-0.25, 0.25), (0.25, 0.25)]
    
    for y in range(h):
        raw.append(0)  # filter None
        for x in range(w):
            acc_r = acc_g = acc_b = acc_a = 0
            
            for sx, sy in sub_offsets:
                nx = (x + 0.5 + sx) / w
                ny = (y + 0.5 + sy) / h
                
                # Check rounded rect boundary
                dx = max(0.0, abs(nx - 0.5) - (0.5 - radius))
                dy = max(0.0, abs(ny - 0.5) - (0.5 - radius))
                if dx * dx + dy * dy > radius * radius:
                    # Outside squircle
                    continue
                
                # 1. Base blue gradient #0284c7 -> #0369a1
                t = (nx + ny) * 0.5
                r = int(2 * (1 - t) + 3 * t)
                g = int(132 * (1 - t) + 105 * t)
                b = int(199 * (1 - t) + 161 * t)
                
                # 2. Cyan Wave Layer
                # Cubic bezier approximation: y_cyan = 0.53 - 0.16*nx + 0.08*sin(nx*6.28)
                y_cyan = 0.52 - 0.14 * nx + 0.09 * math.sin(nx * 5.2 - 0.6)
                if ny > y_cyan:
                    r, g, b = 56, 189, 248  # #38bdf8
                
                # 3. Bold White Surge Wave
                # Sweeps up with dynamic crest
                y_white = 0.70 - 0.42 * nx + 0.12 * math.cos(nx * 4.8)
                if ny > y_white:
                    r, g, b = 255, 255, 255  # #ffffff
                
                acc_r += r
                acc_g += g
                acc_b += b
                acc_a += 255
            
            raw.extend([acc_r // 4, acc_g // 4, acc_b // 4, acc_a // 4])
            
    compressed = zlib.compress(bytes(raw), 9)
    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

def make_ico(png_32: bytes, png_16: bytes) -> bytes:
    num_images = 2
    header = struct.pack('<HHH', 0, 1, num_images)
    offset_1 = 6 + 16 * num_images
    entry_1 = struct.pack('<BBBBHHII', 16, 16, 0, 0, 1, 32, len(png_16), offset_1)
    offset_2 = offset_1 + len(png_16)
    entry_2 = struct.pack('<BBBBHHII', 32, 32, 0, 0, 1, 32, len(png_32), offset_2)
    return header + entry_1 + entry_2 + png_16 + png_32

def main():
    WEB.mkdir(exist_ok=True)
    
    # 1. Write favicon.svg
    svg_path = WEB / "favicon.svg"
    svg_path.write_text(SVG_CONTENT.strip() + "\n", encoding="utf-8")
    print(f"Wrote {svg_path} ({len(SVG_CONTENT)} bytes)")
    
    # 2. Generate PNGs: 16x16, 32x32, 180x180, 192x192
    png_16 = make_png(16)
    png_32 = make_png(32)
    png_180 = make_png(180)
    png_192 = make_png(192)
    
    # 3. Write favicon.ico
    ico_bytes = make_ico(png_32, png_16)
    ico_path = WEB / "favicon.ico"
    ico_path.write_bytes(ico_bytes)
    print(f"Wrote {ico_path} ({len(ico_bytes)} bytes)")
    
    # 4. Write touch & PWA icons
    touch_path = WEB / "apple-touch-icon.png"
    touch_path.write_bytes(png_180)
    print(f"Wrote {touch_path} ({len(png_180)} bytes)")
    
    icon_192 = WEB / "icon-192.png"
    icon_192.write_bytes(png_192)
    print(f"Wrote {icon_192} ({len(png_192)} bytes)")

if __name__ == "__main__":
    main()
