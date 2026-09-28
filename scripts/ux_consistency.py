"""Consistency proof for the live UI (owner 2026-09-28: "prove the consistency of panel and text"; "validate the UI
in many possibilities"). One browser session, views compared at the same moment:
  C1 list card = station sheet = pin panel for the same gauge (24 h row: chip + numbers; measured line). A mismatch is
     re-checked after reloading, so a qc/forecast refresh between two reads is not counted;
  C2 a chip never contradicts its numbers ("ลดลง" with numbers above zero; "ทรงตัว" wider than ±5 cm);
  C3 a longer horizon is never surer than a shorter one ("?" then "→ ทรงตัว");
  C4 no "undefined"/"NaN"/"null", no horizontal overflow, no line printed twice (outside the trend rows);
  C5 viewports 360 / 390 / 768 / 1440 px: home, a sheet and a pin panel load without overflow;
  C6 the pin headline never contradicts the nearest gauge's rows ("ทรงตัว" above "↘ ลดลง").
Usage: python3 scripts/ux_consistency.py [out.json]   (Python Playwright; Chromium with --no-sandbox as root)"""
import json, re, sys
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
        note("C4", where, f"line printed twice: {d[:70]}")


def r24(rows):
    return next((r[1:] for r in rows if r[0].startswith("ใน 24")), None)


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
    codes = list(listed)
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
        if not same(card, v):  # re-check after a fresh list: a refresh between the two reads is not a UI fault
            open_home(pg); listed = pg.evaluate(LIST_JS); card = listed.get(code) or card
            pg.evaluate("(c) => showDetail(c)", code); pg.wait_for_timeout(1500); v = pg.evaluate(SHEET_JS, None)
            if not same(card, v):
                note("C1", f"list vs sheet {code}", f"{r24(card['rows'])} / {card['obs'][:1]} vs {r24(v['rows'])} / {v['obs'][:1]}")
        pg.evaluate("() => closeDetail()")
    pins = [(13.62 + i * 0.04, 100.42 + j * 0.05) for i in range(8) for j in range(8)]
    pins += [(13.7003, 100.4928), (14.40, 100.60), (13.50, 100.30)]
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
            if card and not same(card, blk):  # re-read both after a refresh: a qc run between two reads is not a UI fault
                open_home(pg); listed = pg.evaluate(LIST_JS); card = listed.get(blk["code"])
                pg.evaluate("([a, o]) => checkPoint(a, o, 'pin')", [la, lo]); pg.wait_for_timeout(2000)
                blk2 = next((x for x in pg.evaluate(BLOCKS_JS) if x["code"] == blk["code"]), blk)
                if card and not same(card, blk2):
                    note("C1", f"pin {la:.3f},{lo:.3f} vs list {blk['code']}", f"{r24(blk2['rows'])} / {blk2['obs'][:1]} vs {r24(card['rows'])} / {card['obs'][:1]}")
        pg.evaluate("() => closeDetail()")
    b.close()
    for w, h in ((360, 740), (390, 844), (768, 1024), (1440, 900)):  # C5 viewport sweep
        b = p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": w, "height": h}, is_mobile=w < 700, has_touch=w < 700, locale="th-TH")
        for path in ("", "#s=BKK021", "#s=WL.SSB.08", "#s=WL.KPM.03", "#s=CPY015", "#p=13.8545,100.5880", "#p=13.5000,100.3000"):
            pg.goto(URL + path, wait_until="domcontentloaded"); pg.wait_for_timeout(3500)
            v = pg.evaluate(SHEET_JS, ".pf" if path.startswith("#p") else None) if path else None
            over = pg.evaluate("() => document.scrollingElement.scrollWidth > window.innerWidth + 1")
            if over:
                note("C5", f"{w}px {path or 'home'}", "horizontal overflow")
            if v:
                check_text(f"{w}px {path}", v)
        b.close()
summary = {**counts, "issues": len(issues), "by_check": {k: sum(1 for i in issues if i["check"] == k) for k in ("C1", "C2", "C3", "C4", "C5", "C6")}}
print(json.dumps(summary, ensure_ascii=False))
for i in issues[:40]:
    print(i["check"], "|", i["where"], "|", i["msg"])
if len(sys.argv) > 1:
    json.dump({"summary": summary, "issues": issues}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
