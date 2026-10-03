"""Consistency proof for the live UI (owner 2026-09-28: "prove the consistency of panel and text"; "validate the UI
in many possibilities"). One browser session, views compared at the same moment:
  C1 list card = station sheet = pin panel for the same gauge (24 h row: chip + numbers; measured line). A mismatch is
     re-checked after reloading, so a qc/forecast refresh between two reads is not counted;
  C2 a chip never contradicts its numbers ("ลดลง" with numbers above zero; "ทรงตัว" wider than ±5 cm);
  C3 a longer horizon is never surer than a shorter one ("?" then "→ ทรงตัว");
  C4 no "undefined"/"NaN"/"null", no horizontal overflow, no line printed twice (outside the trend rows);
  C5 viewports 360 / 390 / 768 / 1440 px: home, a sheet and a pin panel load without overflow;
  C6 the pin headline never contradicts the nearest gauge's rows ("ทรงตัว" above "↘ ลดลง");
  C7 (v0.16, D-064) a pin outside Bangkok never speaks of Bangkok's polders ("พื้นที่ปิดล้อม") and never says "no gauge
     near" while a gauge within 3 km is listed;
  C8 (v0.16.1) every region chip is visible without scrolling, and the map shows gauges outside Bangkok (Chiang Mai
     view) whatever the chosen chip — owner 2026-10-01: "App shows only Bangkok stations";
  C9 (v0.16.3-5) rain and river lines agree with the API and with each other: a measured-rain line carries its reading
     time; the "ฝนตกหนักในพื้นที่" headline only with a heavy measured line; the panel's forecast mm = /api/point's;
     a river line only on Bangkok pins and within 3 km; each region's summary rain word = /api/rain by_region;
  C10 (v0.16.6) a measured-trend row never points opposite to a direction a model proved at another horizon of the
     same gauge (TRD001 read ⬆ / ⬇ / ⬆); model vs model may differ (tides, rain arriving later).
  C11 (v0.17.1) rain uses the water rows' layout in the panel and the summary (forecast = a chip row), and the panel
     headline never repeats a rain amount (owner 2026-10-02: "rainfall info … one long sentence").
  C14 (v0.20.0, D-072) the แม่น้ำ tab: every river loads, downstream first, no BMA gauge, 24 h row where a forecast exists.
  C13 (v0.19.0, D-071) the satellite line appears exactly when /api/point reports GISTDA flooding within 1 km, never "no flood".
  C12 (v0.18.6, D-068) the plain line never calls a far or missing gauge "แถวนี้"; on the first pins the one AI button
     opens a story with no verdict word (ปลอดภัย, ไม่ท่วม, ได้ครับ, ไปได้, ปกติ) and no rain amount.
Every Bangkok-area gauge is checked, plus PER_REGION random gauges from each other region (1,040 gauges would take
~30 min). Usage: python3 scripts/ux_consistency.py [out.json] [per_region=15]   (Python Playwright; Chromium --no-sandbox)"""
import json, math, re, sys
from playwright.sync_api import sync_playwright

URL = "https://flood.autobahn.bot/"
PARSE = """(root) => { const rows = (el) => [...el.querySelectorAll('.tr-rows')].map(r => { const c = [...r.children], o = [];
    for (let i = 0; i + 2 < c.length; i += 4) o.push([c[i].textContent.trim(), c[i+1].textContent.trim(), c[i+2].textContent.trim()]); return o; }).flat();
  const obs = (el) => [...el.querySelectorAll('.pf-obs')].map(e => e.textContent.trim());
  return { rows, obs }; }"""
LIST_JS = "() => { const f = " + PARSE + "; return Object.fromEntries([...document.querySelectorAll('#list li.item')].map(li => { const x = f(null); return [li.dataset.code, { rows: [...li.querySelectorAll('.tr-rows')].map(r => { const c = [...r.children], o = []; for (let i = 0; i + 2 < c.length; i += 4) o.push([c[i].textContent.trim(), c[i+1].textContent.trim(), c[i+2].textContent.trim()]); return o; }).flat(), obs: [...li.querySelectorAll('.pf-obs')].map(e => e.textContent.trim()) }]; })); }"
BLOCKS_JS = """() => [...document.querySelectorAll('#detail li.item, #detail .pf-gauge[data-code]')].map(el => ({ code: el.dataset.code,
  rows: [...el.querySelectorAll('.tr-rows')].map(r => { const c = [...r.children], o = []; for (let i = 0; i + 2 < c.length; i += 4) o.push([c[i].textContent.trim(), c[i+1].textContent.trim(), c[i+2].textContent.trim()]); return o; }).flat(),
  obs: [...el.querySelectorAll('.pf-obs')].map(e => e.textContent.trim()) }))"""
SHEET_JS = """(scope) => { const d = document.querySelector('#detail'); if (!d) return null;
  const rows = [...d.querySelectorAll('.tr-rows')].map(r => { const c = [...r.children], o = []; for (let i = 0; i + 2 < c.length; i += 4) o.push([c[i].textContent.trim(), c[i+1].textContent.trim(), c[i+2].textContent.trim()]); return o; })[0] || [];
  const box = (scope && d.querySelector(scope)) || d;  // rendered text of one block (hidden dialogs are not text)
  const rowText = new Set([...box.querySelectorAll('.tr-rows > *')].map(e => e.textContent.trim()));
  const lines = box.innerText.split('\\n').map(s => s.trim()).filter(s => s.length > 12 && !rowText.has(s));
  return { rows, obs: [...d.querySelectorAll('.pf-obs')].map(e => e.textContent.trim()).slice(0, 1), text: d.innerText,
           dup: [...new Set(lines.filter((s, i) => lines.indexOf(s) !== i))],
           overflow: document.scrollingElement.scrollWidth > window.innerWidth + 1 }; }"""
num = lambda t: [int(x.replace("−", "-").replace("+", "")) for x in re.findall(r"[−+]?\d+", t.split("ซม")[0])]
BANDS9 = [(0.1, "ไม่มีฝน"), (10.0, "ฝนเล็กน้อย"), (35.0, "ฝนปานกลาง"), (90.0, "ฝนหนัก"), (1e9, "ฝนหนักมาก")]  # web/app.js RAIN_TMD
word9 = lambda mm: next(l for i, (mx, l) in enumerate(BANDS9) if (mm < mx if i == 0 else mm <= mx))
issues, counts = [], {"sheets": 0, "pins": 0, "pin_blocks": 0, "rows": 0}


def note(kind, where, msg):
    issues.append({"check": kind, "where": where, "msg": msg})


def check_rows(where, rows):
    unsure = False
    for h, chip, rng in rows:
        counts["rows"] += 1
        n = num(rng)
        if n and ("ลดลง" in chip and max(n) > 0 or "เพิ่มขึ้น" in chip and min(n) < 0):
            note("C2", where, f"{h} {chip} {rng}")
        if "ทรงตัว" in chip and n and max(abs(x) for x in n) > 5:
            note("C2", where, f"{h} {chip} {rng} (wider than ±5)")
        if "ทรงตัว" in chip and unsure:
            note("C3", where, f"{h} {chip} after a '?' row")
        unsure = unsure or "?" in chip


def check_text(where, v):
    for bad in ("undefined", "NaN", "null"):
        if re.search(rf"\b{bad}\b", v["text"]):
            note("C4", where, f"text contains '{bad}'")
    if v["overflow"]:
        note("C4", where, "horizontal overflow")
    for d in v["dup"]:
        if re.match(r"^\d+ ชม\. ที่ผ่านมา:", d):  # the measured line under two different gauges (v0.17.3), not a repeat
            continue
        note("C4", where, f"line printed twice: {d[:70]}")


def r24(rows):
    return next((r[1:] for r in rows if r[0].startswith("อีก 24")), None)


def same(a, b):
    return (r24(a["rows"]) is None or r24(b["rows"]) is None or r24(a["rows"]) == r24(b["rows"])) and \
           (not a["obs"] or not b["obs"] or a["obs"][0] == b["obs"][0])


def open_home(pg):
    pg.goto(URL, wait_until="domcontentloaded"); pg.wait_for_selector("#list li", timeout=30000)
    pg.locator('.rchip[data-region="all"]').click(); pg.wait_for_timeout(800)


with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="th-TH")
    open_home(pg)
    listed = pg.evaluate(LIST_JS)
    import random
    random.seed(3)
    per_region = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    reg = dict(pg.evaluate("() => stations.map(s => [s.code, s.region])"))
    codes = [c for c in listed if reg.get(c) in ("bkk", "metro", "up")]
    for r in ("north", "northeast", "east", "west", "south"):
        pool = [c for c in listed if reg.get(c) == r]
        codes += random.sample(pool, min(per_region, len(pool)))
    for k, code in enumerate(codes):
        if k and k % 40 == 0:  # refresh the list snapshot often: qc updates every 10 min
            open_home(pg); listed = pg.evaluate(LIST_JS)
        card = listed.get(code) or {"rows": [], "obs": []}
        check_rows(f"list {code}", card["rows"])
        pg.evaluate("(c) => showDetail(c)", code)
        try:
            pg.wait_for_function("(c) => document.querySelector('#detail h2 .muted')?.textContent.includes(c)", arg=code, timeout=20000)
        except Exception:
            note("C4", f"sheet {code}", "sheet did not load"); continue
        pg.wait_for_timeout(300)
        v = pg.evaluate(SHEET_JS, None); counts["sheets"] += 1
        check_rows(f"sheet {code}", v["rows"]); check_text(f"sheet {code}", v)
        if not same(card, v):  # the sheet updates its list item (v0.16.6): re-read the card the user now sees
            pg.evaluate("() => closeDetail()"); pg.wait_for_timeout(300)
            card = pg.evaluate(LIST_JS).get(code) or card
            pg.evaluate("(c) => showDetail(c)", code); pg.wait_for_timeout(1500); v = pg.evaluate(SHEET_JS, None)
        if not same(card, v):  # re-check after a fresh list: a refresh between the two reads is not a UI fault
            open_home(pg); listed = pg.evaluate(LIST_JS); card = listed.get(code) or card
            pg.evaluate("(c) => showDetail(c)", code); pg.wait_for_timeout(1500); v = pg.evaluate(SHEET_JS, None)
            if not same(card, v):
                note("C1", f"list vs sheet {code}", f"{r24(card['rows'])} / {card['obs'][:1]} vs {r24(v['rows'])} / {v['obs'][:1]}")
        pg.evaluate("() => closeDetail()")
    pins = [(13.62 + i * 0.04, 100.42 + j * 0.05) for i in range(8) for j in range(8)]
    pins += [(13.7003, 100.4928), (14.40, 100.60), (13.50, 100.30)]
    national = [(17.49, 101.72), (18.79, 98.98), (7.01, 100.47), (15.24, 104.85), (12.61, 102.10), (14.02, 99.53),
                (16.82, 100.26), (16.44, 102.83), (8.43, 99.96)]  # Loei, Chiang Mai, Hat Yai, Ubon, Chanthaburi,
    pins += national                                            # Kanchanaburi, Phitsanulok, Khon Kaen, Nakhon Si Thammarat
    open_home(pg); listed = pg.evaluate(LIST_JS)
    for k, (la, lo) in enumerate(pins):
        if k and k % 15 == 0:
            open_home(pg); listed = pg.evaluate(LIST_JS)
        pg.evaluate("([a, o]) => checkPoint(a, o, 'pin')", [la, lo])
        try:
            pg.wait_for_selector("#detail .pf, #detail p", timeout=30000); pg.wait_for_timeout(1200)
        except Exception:
            note("C4", f"pin {la:.3f},{lo:.3f}", "panel did not load"); continue
        counts["pins"] += 1
        v = pg.evaluate(SHEET_JS, ".pf"); check_text(f"pin {la:.3f},{lo:.3f}", v)
        api = json.loads(pg.evaluate("async ([a, o]) => JSON.stringify(await (await fetch(`/api/point?lat=${a.toFixed(5)}&lon=${o.toFixed(5)}`)).json())", [la, lo]))
        full9 = pg.evaluate("() => document.querySelector('#detail').innerText")
        where9 = f"pin {la:.3f},{lo:.3f}"
        rain_box = pg.evaluate("() => { const li = [...document.querySelectorAll('#detail .pf-factors > li')].find(e => e.querySelector('.pf-word') && /ฝน/.test(e.querySelector('.pf-word').textContent)); return li ? li.textContent + ' ' + [...li.querySelectorAll('[title]')].map(b => b.title).join(' ') : ''; }")  # incl. the ⓘ
        if api.get("rain_measured") and "ข้อมูลถึง" not in rain_box:  # the folded details carry the reading time
            note("C9", where9, "measured rain without its reading time")
        if api.get("rain_measured") and "24 ชม. ที่ผ่านมา" not in rain_box:
            note("C9", where9, "measured rain not shown in the rain factor")
        head9 = pg.evaluate("() => [document.querySelector('#detail .pf-title'), document.querySelector('#detail .pf-desc')].map(e => e ? e.textContent : '').join(' ')")
        heavy = (api.get("rain_measured") or {}).get("band") in ("heavy", "very_heavy")
        if ("ฝนตกหนักในพื้นที่" in head9 and not heavy) or (heavy and "ฝนหนัก" not in rain_box):
            note("C9", where9, "heavy-rain headline and the rain factor disagree")
        # C11: rain in the water rows' layout; the headline never repeats the rows' amounts (owner 2026-10-02)
        if api.get("rain_next24_mm") is not None and not pg.evaluate("() => !!document.querySelector('#detail .pf-factors .rain-rows .chg')"):
            note("C11", where9, "rain forecast not shown as a row")
        if "มม." in (pg.evaluate("() => document.querySelector('#detail .pf-desc')?.innerText || ''") or ""):
            note("C11", where9, "the headline repeats a rain amount")
        if api.get("rain_next24_mm") is not None and api["rain_next24_mm"] >= 0.1:
            mm = api["rain_next24_mm"]  # the panel's rainMm(): one decimal below 1 mm or at a TMD band edge; JS rounding
            r0 = math.floor(mm + 0.5)
            want = f"{mm:.1f}" if mm < 1 or word9(r0) != word9(mm) else str(r0)
            if f"ราว {want} มม." not in rain_box:
                note("C9", where9, f"panel rain differs from /api/point ({api['rain_next24_mm']} mm)")
        # C12 (D-068): the plain line never calls a far or missing gauge "here"; on the first pins the one AI button opens
        # a story (AI or rule) with no verdict word and no rain amount (each tap may call GLM)
        desc12 = pg.evaluate("() => document.querySelector('#detail .pf-desc')?.innerText || ''") or ""
        lead12 = api.get("nearest_canal_trend") or api.get("nearest_canal")
        far12 = not lead12 or lead12.get("far") or (api.get("area") or {}).get("confidence") not in ("low", "medium")
        here12 = r"แถวนี้\S{0,12}(ใกล้\S{0,4}เต็ม|ยังรับน้ำ|ล้นตลิ่ง|เริ่มสูง|ต่ำกว่าตลิ่ง|ค่อนข้างสูง)"
        if far12 and re.search(here12, desc12):
            note("C12", where9, f"plain line calls a far gauge 'here': {desc12[:60]}")
        if counts["pins"] <= 10:
            pg.locator("#detail .ai-btn").click()
            try:
                pg.wait_for_selector("#detail .story .story-text:not(.shimmer)", timeout=15000)
                story12 = pg.evaluate("() => document.querySelector('#detail .story .story-text').innerText")
                bad = [w for w in ("ปลอดภัย", "ไม่ท่วม", "ได้ครับ", "ไปได้", "ปกติ", "มม.") if w in story12]
                if bad:
                    note("C12", where9, f"story says {bad}")
                if far12 and "ไกล" not in story12 and re.search(here12, story12):
                    note("C12", where9, f"story calls a far gauge 'here': {story12[:60]}")
            except Exception:
                note("C12", where9, "AI button opened no story")
        # C13 (Q45, D-071): the satellite line exactly when /api/point has one; it never says "not flooded"
        sat_line = pg.locator("#detail .pf-word", has_text="ดาวเทียมเห็นน้ำท่วม").count()
        if bool(sat_line) != bool(api.get("satellite")):
            note("C13", where9, f"satellite line {'shown' if sat_line else 'missing'} vs API {api.get('satellite')}")
        if "ดาวเทียม" in full9 and re.search(r"ดาวเทียม\S{0,20}ไม่(?:เห็น)?(?:มี)?น้ำท่วม(?!\s*·)", full9.replace("ไม่เห็นไม่ได้แปลว่าไม่มีน้ำท่วม", "")):
            note("C13", where9, "satellite text says 'no flood'")
        river_line = pg.locator("#detail .pf-word", has_text="แม่น้ำใกล้จุด:").count()  # the line, not a sentence
        if river_line and (api.get("mode") != "bkk" or not api.get("nearest_river") or api["nearest_river"]["distance_km"] > 3):
            note("C9", where9, "river line without a Bangkok river gauge within 3 km")
        if (la, lo) in national:  # C7
            full = pg.evaluate("() => document.querySelector('#detail').innerText")
            if "ปิดล้อม" in full:
                note("C7", f"pin {la:.3f},{lo:.3f}", "a national pin speaks of Bangkok polders")
            near = pg.evaluate("() => [...document.querySelectorAll('#detail li.item .meta')].map(e => e.textContent).find(t => /ห่าง [0-2]\\.\\d กม\\./.test(t)) || ''")
            if near and "ไม่มีสถานีวัดน้ำใกล้จุดนี้" in full:
                note("C7", f"pin {la:.3f},{lo:.3f}", f"'no gauge near' while a gauge is listed ({near.strip()[:40]})")
        head = pg.evaluate("() => [document.querySelector('#detail .pf-title'), document.querySelector('#detail .pf-desc')].map(e => e ? e.textContent : '').join(' ')")
        g = next(iter(pg.evaluate(BLOCKS_JS)), None)  # C6: the headline never contradicts the nearest gauge's rows
        chips = " ".join(r[1] for r in (g or {}).get("rows", []))
        if g and (("ทรงตัว" in head and ("ลดลง" in chips or "เพิ่มขึ้น" in chips) and "ทรงตัว" not in chips)
                  or ("ลดลง" in head and "เพิ่มขึ้น" in chips and "ลดลง" not in chips)
                  or ("เพิ่มขึ้น" in head and "ลดลง" in chips and "เพิ่มขึ้น" not in chips)):
            note("C6", f"pin {la:.3f},{lo:.3f}", f"headline '{head.strip()[:70]}' vs rows '{chips}'")
        for blk in pg.evaluate(BLOCKS_JS):
            counts["pin_blocks"] += 1
            check_rows(f"pin {la:.3f},{lo:.3f} {blk['code']}", blk["rows"])
            card = listed.get(blk["code"])
            if card and not same(card, blk):  # the pin updates its gauges in the list (v0.16.8): re-read the card
                card = pg.evaluate(LIST_JS).get(blk["code"]) or card
            if card and not same(card, blk):  # re-read both after a refresh: a qc run between two reads is not a UI fault
                open_home(pg); listed = pg.evaluate(LIST_JS); card = listed.get(blk["code"])
                pg.evaluate("([a, o]) => checkPoint(a, o, 'pin')", [la, lo]); pg.wait_for_timeout(2000)
                blk2 = next((x for x in pg.evaluate(BLOCKS_JS) if x["code"] == blk["code"]), blk)
                if card and not same(card, blk2):
                    note("C1", f"pin {la:.3f},{lo:.3f} vs list {blk['code']}", f"{r24(blk2['rows'])} / {blk2['obs'][:1]} vs {r24(card['rows'])} / {card['obs'][:1]}")
        pg.evaluate("() => closeDetail()")
    # C10: per gauge, a measured-trend row never opposes a model-proven direction (checked on the API rows)
    rows10 = json.loads(pg.evaluate("async () => JSON.stringify((await (await fetch('/api/stations')).json()).stations.map(s => [s.code, s.change12, s.change24, s.change48]))"))
    for code, *chs in rows10:
        # a model row counts only where the UI shows its direction (web/app.js directional(): not persistence, not
        # steady, the likely range agrees); otherwise the UI says "?" or "ทรงตัว" there (MOU494 false positive 2026-10-02)
        def ui_dir(c):
            if not c or c.get("dir") not in ("rising", "falling"):
                return None
            if c.get("basis") == "measured_trend":
                return c["dir"]
            lk = c.get("likely")
            ok = c.get("method") not in (None, "persistence") and c.get("level") != "steady" and (
                not lk or (lk[1] < 0 if c["dir"] == "falling" else lk[0] > 0))
            return c["dir"] if ok else None
        dirs = [(ui_dir(c), c.get("basis") == "measured_trend") for c in chs if ui_dir(c)]
        if {"rising", "falling"} <= {d for d, _ in dirs} and any(m for _, m in dirs):
            note("C10", f"rows {code}", f"measured trend opposes a model direction: {dirs}")
    # C14 (v0.20.0 D-072, v0.20.1 D-074): the "แม่น้ำ" tab — every river in the picker loads, upstream first as the API
    # orders it, no BMA gauge in an HII/RID chain (KI-217), a 24 h row for every fresh gauge with a forecast, stale
    # gauges say "ไม่อัปเดต", no river km in the rows; a station's river tag opens its river
    open_home(pg)
    pg.locator('.tabs [data-tab=river]').click(); pg.wait_for_selector("#view-river #rv-river", timeout=30000)
    pg.select_option("#rv-region", "all"); pg.wait_for_timeout(1200)  # every river (v0.20.2: the picker follows the region)
    # v0.20.3 overview ("ทุกสาย", the default): each river's "↗ เพิ่มขึ้น N" must equal the rising rows in its own view
    over = pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#view-river .rv-sum')].map(e => {
        const n = (re) => { const m = e.innerText.match(re); return m ? +m[1] : 0; };
        return [e.dataset.river, n(/เพิ่มขึ้นมาก (\\d+)/) + n(/เพิ่มขึ้น (\\d+)/)]; }))""")
    if not over:
        note("C14", "overview", "ทุกสาย shows no rivers")
    for rv in [v for v in pg.evaluate("() => [...document.querySelectorAll('#rv-river option')].map(o => o.value)") if v]:
        pg.select_option("#rv-river", rv); pg.wait_for_timeout(700)
        prof = json.loads(pg.evaluate("async (r) => JSON.stringify(await (await fetch('/api/profile?river=' + encodeURIComponent(r))).json())", rv))
        byc = {x["code"]: x for x in prof["stations"]}
        shown = pg.evaluate("() => [...document.querySelectorAll('#view-river .prow')].map(r => ({code: r.dataset.code, text: r.innerText, fc: !!r.querySelector('.pfc .chg')}))")
        counts["river_rows"] = counts.get("river_rows", 0) + len(shown)
        rising = pg.evaluate("() => [...document.querySelectorAll('#view-river .prow .pfc .chg')].filter(c => /เพิ่มขึ้น/.test(c.innerText)).length")
        if rv in over and over[rv] != rising:
            note("C14", rv, f"overview says {over[rv]} rising, the river view shows {rising}")
        counts["rivers"] = counts.get("rivers", 0) + 1
        if not shown:
            note("C14", rv, "no rows"); continue
        if [x["code"] for x in shown] != [x["code"] for x in prof["stations"]]:
            note("C14", rv, "rows not in the API's upstream-first order")
        for x in shown:
            st = byc.get(x["code"]) or {}
            if st.get("agency") == "BMA":
                note("C14", f"{rv} {x['code']}", "BMA gauge in a river view")
            old = st.get("stale") or st.get("status") == "unknown"
            if old and "ไม่อัปเดต" not in x["text"]:
                note("C14", f"{rv} {x['code']}", "stale gauge shows a value")
            if not old and st.get("change24") and not x["fc"]:
                note("C14", f"{rv} {x['code']}", "forecast missing in the river row")
            if "จากปลายน้ำ" in x["text"]:
                note("C14", f"{rv} {x['code']}", "river km still in the row")
    for code in [x["code"] for x in prof["stations"]][:2] if prof.get("stations") else []:
        rv = prof["river"]
        pg.goto(f"{URL}#s={code}", wait_until="domcontentloaded"); pg.wait_for_selector("#detail .rv-tag", timeout=30000)
        pg.locator("#detail .rv-tag").click(); pg.wait_for_selector("#view-river .prow", timeout=30000); pg.wait_for_timeout(800)
        if pg.evaluate("() => document.querySelector('#rv-river')?.value") != rv or not pg.locator(f'#view-river .prow.focus[data-code="{code}"]').count():
            note("C14", f"tag {code}", "river tag did not open its river at the station")
    # C9: the summary rain line of every region chip = /api/rain by_region (TMD word of the wettest forecast point)
    open_home(pg)
    rainreg = json.loads(pg.evaluate("async () => JSON.stringify((await (await fetch('/api/rain')).json()).by_region)"))
    bands = [(0.1, "ไม่มีฝน"), (10.0, "ฝนเล็กน้อย"), (35.0, "ฝนปานกลาง"), (90.0, "ฝนหนัก"), (1e9, "ฝนหนักมาก")]
    word = lambda mm: next(l for i, (mx, l) in enumerate(bands) if (mm < mx if i == 0 else mm <= mx))
    for reg in ("bkk", "metro", "up", "north", "northeast", "east", "west", "south", "all"):
        if pg.locator(f'.rchip[data-region="{reg}"]').count() == 0:
            continue
        pg.locator(f'.rchip[data-region="{reg}"]').click(); pg.wait_for_timeout(500)
        line = pg.evaluate("() => document.querySelector('#summary .sumrain')?.innerText || ''")
        r = rainreg.get(reg) or {}
        fc, mm = r.get("forecast_mm24"), (r.get("measured") or {}).get("rain_24h")
        heavy = (fc is not None and fc >= 35.1) or (mm is not None and float(mm) >= 35.1)
        # C9 (v0.18.9, owner "Only when heavy"): a rain line exactly when the region expects or measured heavy rain
        if heavy != bool(line):
            note("C9", f"summary {reg}", f"rain line {'missing' if heavy else 'shown'}: '{line[:60]}' (API fc {fc} mm, measured {mm} mm)")
        if heavy and fc is not None and fc >= 35.1 and word(fc) not in line.split("ที่ผ่านมา")[0]:
            note("C9", f"summary {reg}", f"rain line '{line[:60]}' vs API {fc} mm ({word(fc)})")
        # C11: the strip's rain is one line, never the panel's row grid (owner 2026-10-02: "too much space again")
        if pg.locator("#summary .rain-rows, #summary .tr-rows").count():
            note("C11", f"summary {reg}", "summary rain uses the multi-row layout")
    b.close()
    for w, h in ((360, 740), (390, 844), (768, 1024), (1440, 900)):  # C5 viewport sweep
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": w, "height": h}, is_mobile=w < 700, has_touch=w < 700, locale="th-TH")
        pg.goto(URL, wait_until="domcontentloaded"); pg.wait_for_selector(".rchip", timeout=30000); pg.wait_for_timeout(2500)
        hidden = pg.evaluate("() => [...document.querySelectorAll('.rchip[data-region]')].filter(b => { const r = b.getBoundingClientRect(); return r.right > window.innerWidth || r.left < 0; }).map(b => b.innerText)")
        if hidden:
            note("C8", f"{w}px home", f"region chips off-screen: {hidden}")
        if pg.locator(".tabs [data-tab=map]").is_visible():  # phones and tablets: the map sits behind its tab
            pg.locator(".tabs [data-tab=map]").click(); pg.wait_for_timeout(1200)
        pg.evaluate("() => { map.setView([18.79, 98.98], 9); }"); pg.wait_for_timeout(1200)
        n_cm = pg.evaluate("() => { let n = 0; layer.eachLayer(l => { if (l.getLatLng && map.getBounds().contains(l.getLatLng())) n++; }); return n; }")
        if not n_cm:
            note("C8", f"{w}px map", "no gauge on the map around Chiang Mai with the default chip")
        for path in ("", "#s=BKK021", "#s=WL.SSB.08", "#s=WL.KPM.03", "#s=CPY015", "#p=13.8545,100.5880", "#p=13.5000,100.3000",
                     "#s=URTU07", "#s=X.77", "#s=MUN009", "#p=17.4900,101.7200", "#p=7.0100,100.4700"):
            pg.goto(URL + path, wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
            v = pg.evaluate(SHEET_JS, ".pf" if path.startswith("#p") else None) if path else None
            over = pg.evaluate("() => document.scrollingElement.scrollWidth > window.innerWidth + 1")
            if over:
                note("C5", f"{w}px {path or 'home'}", "horizontal overflow")
            if v:
                check_text(f"{w}px {path}", v)
        b.close()
summary = {**counts, "issues": len(issues), "by_check": {k: sum(1 for i in issues if i["check"] == k) for k in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14")}}
print(json.dumps(summary, ensure_ascii=False))
for i in issues[:40]:
    print(i["check"], "|", i["where"], "|", i["msg"])
if len(sys.argv) > 1:
    json.dump({"summary": summary, "issues": issues}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
