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
        r["summary"] = pg.inner_text("#imp-body .sumline")
        r["dam_markers"] = pg.locator(".imp-dam-icon").count()
        r["logout_visible"] = pg.is_visible("#imp-logout")
        pg.screenshot(path=f"{OUT}/tab_{name}_dams.png", full_page=False)
        # a dam row opens its sheet, as a station row does (v0.31; was the map popup)
        pg.locator(".imp-dams .item").first.click(); pg.wait_for_selector("#sheet:not([hidden]) .imp-dam-sheet", timeout=8000)
        r["after_card_tab"] = pg.evaluate("document.body.dataset.tab")
        r["popup"] = pg.inner_text("#detail .imp-dam-sheet")[:160]
        r["dam_rows"] = {"h_median": pg.evaluate("(() => { const h = [...document.querySelectorAll('.imp-dams .item')].map(c => c.getBoundingClientRect().height).sort((a,b)=>a-b); return h[Math.floor(h.length/2)]; })()"),
                         "groups": pg.locator("#imp-body .imp-grp").count()}
        pg.screenshot(path=f"{OUT}/tab_{name}_popup.png", full_page=False)
        pg.click("#detail .close"); pg.wait_for_timeout(300)
        # a ◆ on the map opens the same sheet (desktop only: on phones the map is its own tab)
        if name == "desk":
            box = pg.evaluate("""() => { const m = document.querySelector('#map').getBoundingClientRect();
                const el = [...document.querySelectorAll('.imp-dam-icon')].find(e => { const r = e.getBoundingClientRect();
                  return r.left > m.left + 30 && r.right < m.right - 320 && r.top > m.top + 30 && r.bottom < m.bottom - 30; });
                if (!el) return null; const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }""")
            if box:
                pg.mouse.click(box[0], box[1]); pg.wait_for_timeout(800)
                r["marker_opens_sheet"] = pg.evaluate("!document.getElementById('sheet').hidden && !!document.querySelector('#detail .imp-dam-sheet')")
                pg.click("#detail .close"); pg.wait_for_timeout(300)
            else:
                r["marker_opens_sheet"] = "no marker in view"
        # the case (D-110): the comparison grid, the map following the case, ONWR's group in the app's box
        pg.click('.tabs [data-tab="impact"]'); pg.wait_for_timeout(500)
        pg.click('[data-imp="kaeng-krachan"]'); pg.wait_for_selector("#imp-sc .imp-grid", timeout=40000)
        pg.wait_for_timeout(1500)
        r["case_title"] = pg.inner_text(".imp-title")
        long_p = """(sel) => [...document.querySelectorAll(sel + ' p, ' + sel + ' li')].filter(p => p.innerText.length > 160 &&
            !p.closest('details:not([open])') && !p.closest('.story')).map(p => p.innerText.slice(0, 60))"""
        r["long_paragraphs"] = {"view": pg.evaluate(long_p, "#imp-body")}
        r["chips"] = pg.locator("#imp-body .imp-chips-num .chip").count()
        r["grid_rows"] = pg.locator("#imp-sc .imp-grid > tbody:first-of-type .imp-gr").count()
        r["grid_cells"] = pg.locator("#imp-sc .imp-grid > tbody:first-of-type .imp-gr").first.locator(".imp-c").count()
        r["hatched_cells"] = pg.locator("#imp-sc .imp-c-x").count()
        r["first_screen_chars"] = pg.evaluate("document.getElementById('imp-body').innerText.length")
        r["onwr_group_in_box"] = pg.locator(".legend.layers .imp-onwr-grp").count()
        r["onwr_unchecked"] = pg.evaluate("[...document.querySelectorAll('[data-onwr]')].every(c => !c.checked)")
        r["old_onwr_ctl"] = pg.locator(".imp-onwr-ctl").count()
        if name == "desk":
            r["map_follows_case"] = pg.evaluate("(() => { const c = map.getCenter(); return c.lat > 12.5 && c.lat < 13.4 && c.lng > 99.2 && c.lng < 100.2; })()")
            pg.locator("#imp-sc .imp-gr").nth(1).click(); pg.wait_for_timeout(500)
            r["row_select_sel"] = pg.locator("#imp-sc .imp-gr.imp-sel").count()
            pg.click('[data-dayh="2"]'); pg.wait_for_timeout(500)
            r["day_click_legend"] = "วันที่ 3" in pg.inner_text(".imp-reach-legend")
            pg.click('[data-dayh="2"]'); pg.wait_for_timeout(300)
        pg.click("#imp-sc .imp-ladder-btn"); pg.wait_for_timeout(300)
        r["ladder_rows"] = pg.locator("#imp-sc .imp-ladder .imp-gr").count()
        pg.click("#imp-sc .imp-ladder-btn"); pg.wait_for_timeout(200)
        pg.screenshot(path=f"{OUT}/tab_{name}_case_first.png", full_page=False)
        # the ★ row → its sheet: chart, reservoir table, river grid, coverage, (outside), compare
        pg.locator("#imp-sc .imp-gr").first.locator(".imp-open").click()
        pg.wait_for_selector("#sheet:not([hidden]) .imp-rgrid", timeout=8000); pg.wait_for_timeout(800)
        r["sheet_river_cells"] = pg.locator("#detail .imp-rgrid td.imp-m").count()
        r["coverage_line"] = pg.inner_text("#detail .imp-cover")[:120]
        r["plan_day_chips"] = pg.locator("#detail .imp-days [data-day]").count()
        r["long_paragraphs"]["plan_sheet"] = pg.evaluate(long_p, "#detail")
        r["reach_legend"] = pg.locator(".imp-reach-legend").count()
        pg.screenshot(path=f"{OUT}/tab_{name}_plan_sheet.png", full_page=False)
        if pg.locator("#detail .ai-btn").count():
            pg.click("#detail .ai-btn"); pg.wait_for_selector("#detail .story-text:not(.shimmer)", timeout=30000)
            r["compare_story"] = pg.inner_text("#detail .story-text")[:200]
        pg.click("#detail .close"); pg.wait_for_timeout(300)
        # the ℹ️ sheets are the on-demand method prose (GUIDELINES §6c-9): measured and reported, not a failure
        pg.click(".imp-info summary")
        r["long_paragraphs_info"] = {}
        for k in ("val", "river", "matrix", "method", "req"):
            pg.click(f'[data-info="{k}"]'); pg.wait_for_selector("#sheet:not([hidden]) #detail h2", timeout=8000)
            r["long_paragraphs_info"][k] = len(pg.evaluate(long_p, "#detail"))
            pg.click("#detail .close"); pg.wait_for_timeout(200)
        # a chip → the dam sheet; a river node → the station's own sheet
        pg.locator("#imp-body .imp-chips-num .chip").first.click(); pg.wait_for_selector("#sheet:not([hidden]) .imp-kv", timeout=8000)
        r["dam_sheet"] = pg.inner_text("#detail h2")[:40]
        pg.click("#detail .close"); pg.wait_for_timeout(300)
        pg.locator(".imp-strip .imp-node").nth(1).click(); pg.wait_for_selector("#sheet:not([hidden]) #detail h2", timeout=15000)
        r["station_sheet"] = pg.inner_text("#detail h2")[:40]
        pg.click("#detail .close"); pg.wait_for_timeout(300)
        # a plan typed in Thai fills the boxes; คำนวณ adds a custom row
        pg.click("#imp-custom-btn"); pg.wait_for_selector("#sheet:not([hidden]) #imp-custom", timeout=8000)
        pg.fill("#imp-parse-text", "ระบาย 15 สามวันแล้วลดเหลือ 10"); pg.click("#imp-parse-btn")
        pg.locator("#imp-parse-msg", has_text="กดคำนวณ").wait_for(timeout=20000)
        r["parsed_plan"] = pg.eval_on_selector_all("#imp-custom input", "els => els.map(e => Number(e.value))")
        r["long_paragraphs"]["custom_sheet"] = pg.evaluate(long_p, "#detail")
        pg.click("#imp-custom button[type=submit]"); pg.wait_for_selector("#imp-sc .imp-custom-row", timeout=30000)
        r["custom_row"] = pg.locator("#imp-sc .imp-custom-row").count()
        # ✨ menu: the simple story and the executive brief (bullets + copy)
        pg.click("#imp-sc .imp-ai > summary"); pg.wait_for_timeout(300)
        pg.click("#imp-sc .imp-ai-body .ai-btn:not(.imp-brief-btn)"); pg.wait_for_selector("#imp-sc .story-text:not(.shimmer)", timeout=30000)
        r["ai_story"] = pg.inner_text("#imp-sc .story-text")[:200]
        pg.click("#imp-sc .imp-brief-btn"); pg.wait_for_selector("#imp-sc .imp-brief li", timeout=30000)
        r["brief_items"] = pg.locator("#imp-sc .imp-brief li").count()
        r["long_paragraphs"]["brief"] = pg.evaluate(long_p, "#imp-sc .imp-brief")
        pg.screenshot(path=f"{OUT}/tab_{name}_scenarios.png", full_page=False)
        pg.click("#imp-onmap"); pg.wait_for_timeout(1500)
        r["case_tooltips"] = pg.locator(".imp-tip").count()
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
        # Review Focus 5: an expired session in the middle of the work shows the login form
        pg.click('.tabs [data-tab="impact"]'); pg.wait_for_timeout(500)
        ctx.clear_cookies()
        pg.click('[data-imp="dams"]'); pg.click('[data-imp="kaeng-krachan"]')
        try:
            pg.wait_for_selector("#imp-login", timeout=15000)
            r["session_expiry_shows_login"] = True
        except Exception:
            r["session_expiry_shows_login"] = False
        if r["session_expiry_shows_login"]:
            pg.fill("#imp-pw", os.environ["IMPACT_PW"]); pg.click("#imp-login button[type=submit]")
            pg.wait_for_selector("#imp-sc .imp-grid, .imp-dams .item", timeout=40000)  # back on the case it was showing
        pg.click("#imp-logout"); pg.wait_for_selector("#imp-login", timeout=8000)
        r["after_logout_markers"] = pg.locator(".imp-dam-icon").count()
        r["after_logout_overlays"] = pg.evaluate("document.querySelectorAll('.imp-onwr-grp, .imp-reach-legend').length")
        r["console_errors"] = [e for e in errs if "status of 401" not in e]
        rep[name] = r
        ctx.close()
    b.close()
fails = []
for name, r in rep.items():
    lp = r.get("long_paragraphs", {})
    if any(v for v in lp.values()):
        fails.append(f"{name}: paragraphs over 160 characters {lp}")
    for k, want in (("grid_cells", 7), ("onwr_group_in_box", 1), ("old_onwr_ctl", 0), ("ladder_rows", 13), ("sheet_river_cells", 35),
                    ("session_expiry_shows_login", True), ("after_logout_overlays", 0)):
        if r.get(k) != want:
            fails.append(f"{name}: {k} = {r.get(k)!r}, want {want!r}")
    if not r.get("onwr_unchecked"):
        fails.append(f"{name}: an ONWR layer is on by default")
    if r.get("parsed_plan") != [15, 15, 15, 10, 10, 10, 10]:
        fails.append(f"{name}: parsed_plan {r.get('parsed_plan')}")
    if name == "desk" and not (r.get("map_follows_case") and r.get("day_click_legend") and r.get("row_select_sel") == 1):
        fails.append(f"{name}: map_follows_case/day_click_legend/row_select_sel {r.get('map_follows_case')}/{r.get('day_click_legend')}/{r.get('row_select_sel')}")
    if r.get("console_errors"):
        fails.append(f"{name}: console errors {r['console_errors']}")
rep["fails"] = fails
print(json.dumps(rep, ensure_ascii=False, indent=1))
