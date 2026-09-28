"""Real-user walk of https://flood.autobahn.bot on a phone and a desktop (2026-09-28 UX round 12).
Personas: P1 Bang Khen resident at home (GPS), P2 someone checking a relative's area by name (search),
P3 map browser, P4 riverside condo (Chao Phraya profile), P5 reporter (report form). Screenshots + timings + errors."""
import json, sys, time
from playwright.sync_api import sync_playwright

OUT = sys.argv[1]
URL = "https://flood.autobahn.bot/"
log = {}


def walk(p, name, ctx_args):
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(**ctx_args, geolocation={"latitude": 13.8545, "longitude": 100.588},
                        permissions=["geolocation"], locale="th-TH")
    pg = ctx.new_page()
    errs, reqs = [], []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("requestfinished", lambda r: reqs.append(r))
    t0 = time.time()
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_selector("#list li", timeout=30000)
    t_list = time.time() - t0
    pg.wait_for_timeout(1500)
    pg.screenshot(path=f"{OUT}/{name}-1-home.png")
    # P1: near me (GPS)
    pg.click("#gps"); pg.wait_for_timeout(5000)
    pg.screenshot(path=f"{OUT}/{name}-2-near.png")
    # P2: search a district by name
    pg.goto(URL, wait_until="domcontentloaded"); pg.wait_for_selector("#list li", timeout=30000)
    pg.fill("#q", "ลาดพร้าว"); pg.wait_for_timeout(2500)
    pg.screenshot(path=f"{OUT}/{name}-3-search.png")
    # P3: map tab, then tap the map centre (point check)
    tab = pg.locator('[data-tab="map"]')
    if tab.is_visible(): tab.click()
    pg.wait_for_timeout(3000)
    pg.screenshot(path=f"{OUT}/{name}-4-map.png")
    box = pg.locator("#map").bounding_box()
    if box:
        pg.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.55); pg.wait_for_timeout(4000)
        pg.screenshot(path=f"{OUT}/{name}-5-mapclick.png")
    # P4: Chao Phraya profile
    pg.goto(URL, wait_until="domcontentloaded"); pg.wait_for_selector("#list li", timeout=30000)
    pg.locator('[data-tab="river"]').first.click(); pg.wait_for_timeout(3500)
    pg.screenshot(path=f"{OUT}/{name}-6-river.png", full_page=False)
    # P5: station sheet + report form (first flooded station in the list)
    pg.goto(URL + "#s=BKK021", wait_until="domcontentloaded"); pg.wait_for_timeout(5000)
    pg.screenshot(path=f"{OUT}/{name}-7-sheet.png")
    size = sum((r.sizes() or {}).get("responseBodySize", 0) for r in reqs if r.sizes())
    log[name] = {"first_list_s": round(t_list, 1), "requests": len(reqs), "kb": round(size / 1024), "errors": errs[:10]}
    b.close()


with sync_playwright() as p:
    walk(p, "m", {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2, "is_mobile": True, "has_touch": True,
                  "user_agent": "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"})
    walk(p, "d", {"viewport": {"width": 1440, "height": 900}})
print(json.dumps(log, ensure_ascii=False, indent=1))
