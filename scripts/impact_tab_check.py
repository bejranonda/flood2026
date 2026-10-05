"""Run: IMPACT_PW="$(sed -n 's/^IMPACT_PASSWORD=//p' .env)" python3 scripts/impact_tab_check.py [base_url]   (screenshots to $OUT_DIR, default /tmp)
ONWR-engineer view of /impact as the main app + 💧 ผลกระทบ tab (D-100): login in the tab, national dams list and map
markers, the Kaeng Krachan case on the map, the other tabs still working; console/CSP errors; 390 px and desktop.
The password comes from IMPACT_PW and is never printed."""
import json, os, sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://flood.autobahn.bot"
OUT = os.environ.get("OUT_DIR", "/tmp")
rep = {}
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    for name, vp in (("m390", {"width": 390, "height": 844}), ("desk", {"width": 1366, "height": 900})):
        ctx = b.new_context(viewport=vp, locale="th-TH", timezone_id="Asia/Bangkok")
        pg = ctx.new_page()
        errs = []
        pg.on("console", lambda m: errs.append(m.text[:140]) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:200]))
        pg.goto(BASE + "/impact", wait_until="networkidle")
        pg.wait_for_selector("#imp-login", timeout=15000)
        r = {"opens_on": pg.evaluate("document.body.dataset.tab"),
             "tabs": pg.eval_on_selector_all(".tabs [data-tab]", "els => els.map(e => e.dataset.tab)")}
        pg.fill("#imp-pw", os.environ["IMPACT_PW"]); pg.click("#imp-login button[type=submit]")
        pg.wait_for_selector(".imp-dams .item", timeout=20000)
        pg.wait_for_timeout(1500)
        r["dam_cards"] = pg.locator(".imp-dams .item").count()
        r["summary"] = pg.inner_text(".imp-sum")
        r["dam_markers"] = pg.locator(".imp-dam-icon").count()
        r["logout_visible"] = pg.is_visible("#imp-logout")
        pg.screenshot(path=f"{OUT}/tab_{name}_dams.png", full_page=False)
        # a dam card opens its popup on the map (on phones the map tab)
        pg.locator(".imp-dams .item").first.click(); pg.wait_for_timeout(1200)
        r["after_card_tab"] = pg.evaluate("document.body.dataset.tab")
        r["popup"] = pg.inner_text(".leaflet-popup-content")[:160] if pg.locator(".leaflet-popup-content").count() else None
        pg.screenshot(path=f"{OUT}/tab_{name}_popup.png", full_page=False)
        # the case
        pg.click('.tabs [data-tab="impact"]'); pg.wait_for_timeout(500)
        pg.click('[data-imp="kaeng-krachan"]'); pg.wait_for_selector("#imp-river", timeout=20000)
        r["case_title"] = pg.inner_text(".imp-title")
        pg.screenshot(path=f"{OUT}/tab_{name}_case.png", full_page=False)
        pg.click("#imp-onmap"); pg.wait_for_timeout(1500)
        r["case_tooltips"] = pg.locator(".imp-tip").count()
        r["river_paths"] = pg.locator(".leaflet-overlay-pane path, .leaflet-impact-pane path").count()
        pg.screenshot(path=f"{OUT}/tab_{name}_casemap.png", full_page=False)
        # the main app still works in impact mode
        for t in ("list", "river", "watch"):
            pg.click(f'.tabs [data-tab="{t}"]'); pg.wait_for_timeout(1200)
        r["list_items"] = (pg.click('.tabs [data-tab="list"]'), pg.wait_for_timeout(800), pg.locator("#list .item").count())[2]
        r["watch_visible"] = (pg.click('.tabs [data-tab="watch"]'), pg.wait_for_timeout(800), pg.is_visible("#view-watch"))[2]
        r["impact_hidden_elsewhere"] = pg.evaluate("document.getElementById('view-impact').hidden")
        over = pg.evaluate("""() => { const w = document.documentElement.clientWidth; const bad = [];
            for (const el of document.querySelectorAll('body *')) { if (el.closest('.imp-scroll, .leaflet-container, .tabs')) continue;
              const q = el.getBoundingClientRect(); if (q.width && q.right > w + 1) bad.push(el.tagName + '.' + (el.className || '').toString().slice(0, 30)); }
            return {w, sw: document.documentElement.scrollWidth, bad: bad.slice(0, 6)}; }""")
        r["overflow"] = over
        r["tab_label_fits"] = pg.evaluate("""() => [...document.querySelectorAll('.tabs button')].filter(b => b.offsetParent)
            .every(b => b.scrollWidth <= b.clientWidth + 1)""")
        pg.click("#imp-logout"); pg.wait_for_selector("#imp-login", timeout=8000)
        r["after_logout_markers"] = pg.locator(".imp-dam-icon").count()
        r["console_errors"] = [e for e in errs if "status of 401" not in e]
        rep[name] = r
        ctx.close()
    b.close()
print(json.dumps(rep, ensure_ascii=False, indent=1))
