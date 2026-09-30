"""Builds the link-preview image (web/og-image.jpg, 1200x630) and the GitHub social preview (docs/img/social-preview.png,
1280x640) from the real phone screenshots in docs/img. Usage: python3 scripts/make_social_images.py (Python Playwright)."""
import base64, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
uri = lambda n: "data:image/webp;base64," + base64.b64encode((ROOT / "docs/img" / n).read_bytes()).decode()
HTML = """<!doctype html><meta charset=utf-8><style>
*{box-sizing:border-box}body{margin:0;width:%(w)dpx;height:%(h)dpx;overflow:hidden;background:linear-gradient(135deg,#0d3b66,#14608f);
font-family:"Noto Sans Thai","Tlwg Typo","Garuda",system-ui,sans-serif;color:#fff;position:relative}
.t{position:absolute;left:56px;top:84px;width:%(tw)dpx}
.b{font-size:28px;font-weight:700;letter-spacing:.5px;opacity:.85}
h1{font-size:47px;line-height:1.2;margin:18px 0 22px;font-weight:700}
p{font-size:28px;line-height:1.45;margin:0;opacity:.92}
.u{position:absolute;left:56px;bottom:52px;font-size:30px;font-weight:700;background:#fff;color:#0d3b66;padding:8px 22px;border-radius:999px}
.ph{position:absolute;top:40px;width:250px;border-radius:26px;border:6px solid #07243f;box-shadow:0 18px 40px rgba(0,0,0,.4)}
</style><div class=t><div class=b>BKK FloodWatch</div><h1>ระดับน้ำ กทม.<br>ตอนนี้ และ 12–48 ชม.</h1>
<p>กี่ ซม. ถึงตลิ่ง · แนวโน้มที่วัดจริง<br>Bangkok water levels &amp; trends</p></div>
<div class=u>flood.autobahn.bot</div>
<img class=ph style="right:%(r1)dpx;top:%(t1)dpx" src="%(a)s"><img class=ph style="right:%(r2)dpx;top:%(t2)dpx" src="%(b)s">"""
with sync_playwright() as p:
    br = p.chromium.launch(args=["--no-sandbox"])
    for w, h, out in ((1200, 630, "web/og-image.jpg"), (1280, 640, "docs/img/social-preview.png")):
        pg = br.new_page(viewport={"width": w, "height": h})
        pg.set_content(HTML % dict(w=w, h=h, tw=w - 500, r1=60, t1=70, r2=330, t2=-20, a=uri("phone-point-check.webp"), b=uri("phone-station-sheet.webp")))
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(ROOT / out), type="jpeg" if out.endswith(".jpg") else "png", **({"quality": 86} if out.endswith(".jpg") else {}))
    br.close()
