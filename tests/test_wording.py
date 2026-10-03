"""One way to say "when" across the app (owner 2026-10-02: '"ใน 24 ชม.", "ใน 48 ชม." are not clear. I cannot understand
that it is about the future … Consider the consistency in using across app too').

Rule: a forecast horizon is "อีก N ชม." in a row label and "ในอีก N ชม." in a sentence; the past is "N ชม. ที่ผ่านมา".
A bare "ใน N ชม." is allowed only for the past ("ใน 6 ชม." of street reports, "ภายใน 1 ชม." freshness) and is
written with "ที่ผ่านมา"/"ล่าสุด"/"ภายใน" or a report count beside it.
"""
import pathlib
import re

from floodwatch import point

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
CODE = "\n".join(l for l in APP.splitlines() if not l.lstrip().startswith("//"))  # comments may quote old wording


def test_trend_and_rain_rows_label_the_future_with_ik():
    assert 'class="tr-h">อีก ${hours} ชม.' in APP  # water rows: อีก 12/24/48 ชม.
    assert 'class="tr-h">อีก 24 ชม.' in APP  # rain row, same column
    assert 'class="tr-h">ใน ' not in APP


def test_no_bare_future_horizon_in_the_app_text():
    # every "ใน 12/24/48 ชม." must be "ในอีก …", or past ("… ที่ผ่านมา", "… ล่าสุด"), or a count of reports
    for m in re.finditer(r"(?<!อีก)(?<!ภาย)ใน (?:\$\{\w+\}|12|24|48) ?ชม\.", CODE):
        tail = CODE[m.end():m.end() + 14]
        assert "ที่ผ่านมา" in tail or "ล่าสุด" in tail, f"bare future horizon: {CODE[m.start() - 30:m.end() + 14]!r}"


def test_server_texts_use_nai_ik_for_the_future():
    assert point._rain_phrase(0.0)[1] == "ไม่คาดว่าจะมีฝนในอีก 24 ชม."
    rising = [{"code": "K1", "lat": 13.87, "lon": 100.71, "status": "watch", "stale": False, "river": "คลองหกวา",
               "trend12": "rising", "delta12_median": 0.12}]
    fc = point.assess(13.87, 100.71, rising, 0, {}, 1.0)["forecast"]
    assert "ในอีก 24 ชม." in fc["title"] + fc["desc"] and not re.search(r"(?<!อีก)ใน 24 ชม\.", fc["title"] + fc["desc"])


def test_a_distance_reads_hang_n_km_like_the_list():
    # owner 2026-10-02: "Distance > ห่าง 1.5 กม." — the pin panel's gauge line said a bare "1.5 กม."
    assert 'ห่าง ${esc(c.distance_km)} กม.' in CODE
    assert '<span class="muted">${esc(c.distance_km)} กม.' not in CODE


def test_no_jargon_for_a_gauge_without_a_forecast():
    # "(ยังไม่ผ่านการทดสอบย้อนหลัง)" goes behind an ⓘ; the line itself shows what was measured
    assert "ยังไม่มีคาดการณ์ (ยังไม่ผ่านการทดสอบย้อนหลัง)" not in CODE


def test_summary_rain_shows_only_heavy_rain_in_one_line():
    # owner 2026-10-02 (screenshot of the top strip): "it used too much space again!! and it showed specifically for
    # Bangkok, for what?" -> chose "Only when heavy": no rain in the strip unless the region expects or measured heavy
    # rain (TMD: heavy from 35.1 mm, the same bands as point.py), then one line, never the 3-row panel layout.
    m = re.search(r"const SUMMARY_RAIN_MIN_MM = ([\d.]+);", APP)
    assert m and float(m.group(1)) > point.RAIN_MODERATE_MAX_MM
    body = APP[APP.index("function rainSummary("):APP.index("let lastStats")]
    assert "rainRows(" not in body and "SUMMARY_RAIN_MIN_MM" in body


def test_the_satellite_factor_says_only_what_was_seen():
    # Q45 (D-071): one factor line when the satellite saw flooding within 1 km; never "not flooded"; the blind spot
    # (city, trees) is said behind the ⓘ
    body = APP[APP.index("const satDates"):APP.index("const panel")]
    assert "d.satellite" in body and "ดาวเทียมเห็นน้ำท่วม" in body and "ไม่ท่วม" not in body
    assert "ไม่เห็นไม่ได้แปลว่าไม่มีน้ำท่วม" in body and "GISTDA" in body


def test_river_view_is_one_line_of_pickers_without_river_km_and_stations_carry_a_river_tag():
    # owner 2026-10-03 (screenshot of the แม่น้ำ tab): chips took three rows; "Is necessary to show: ระยะห่างจากปลายน้ำ?";
    # "add tag แม่น้ำ to each station" → one line "Province & river", no km, tag on list rows and sheets; upstream on top
    body = APP[APP.index("async function renderRiver"):APP.index("function scrollRiver")]
    # v0.20.2 (owner: "Change filter from จังหวัด to ภาค?", "no long description อ่านจากบนลงล่าง") → ภาค picker synced
    # with the list's region chip; the explanation lives behind one ⓘ
    assert 'id="rv-river"' in body and "rv-prov" not in body and "rchip" not in body
    assert "อ่านจากบนลงล่าง" not in body and "<details" not in body and "infoBtn(" in body
    assert "whereRow(" in body  # v0.20.4: the shared where-row (region + province) drives setRegion/setProv
    assert "จากปลายน้ำ" not in body and "chainage_km" not in body
    assert "↑ ต้นน้ำ" in body and body.index("↑ ต้นน้ำ") < body.index("↓ ปลายน้ำ")
    assert "${riverTag(s)}" in APP and "hasRiverView(s) ?" in APP


def test_region_chips_use_the_usual_names_and_metro_includes_bangkok():
    assert 'metro: "กทม. และปริมณฑล"' in APP and 'up: "ภาคกลาง"' in APP and "เหนือ กทม." not in CODE
    assert 'th: "ทั่วประเทศ"' in APP and "ทั้งประเทศ" not in CODE  # one word for "all of Thailand"
    assert 'metro: (s) => s.region === "metro" || s.region === "bkk"' in APP


def test_all_rivers_is_an_overview_counted_like_the_rows():
    # owner 2026-10-03: "Can user select all rivers under river filter?" → "ทุกสาย": one row per river (over/near the
    # bank, rising/falling in 24 h), counted with the rows' own rules (directional, D-060), the default view
    body = APP[APP.index("async function renderRiver"):APP.index("function scrollRiver")]
    assert '<option value=""' in body and "ทุกสาย" in body
    rs = APP[APP.index("function riverSummary"):APP.index("async function renderRiver")]
    assert "directional(s.change24)" in rs and "stale" in rs


def test_overview_says_strong_rises_like_the_rows():
    # 2026-10-03 live check: คลองอู่ตะเภา (Hat Yai) had 3 "⬆ เพิ่มขึ้นมาก" rows; the overview said "↗ เพิ่มขึ้น 3"
    rs = APP[APP.index("function riverSummary"):APP.index("async function renderRiver")]
    assert "strong_rise" in rs and "CHANGE.strong_rise" in rs and "เพิ่มขึ้นมาก" in rs


def test_one_where_row_for_both_tabs_with_region_and_province():
    # owner 2026-10-03: "if the users like to see stations in their province?" → "Shared where-row + river row":
    # [ภาค ▾][จังหวัด ▾] in the list AND the river tab (one state), replacing the list's 4 rows of region chips
    assert 'class="pick-region"' in APP and 'class="pick-prov"' in APP
    rr = APP[APP.index("function renderRegions"):APP.index("function setRegion")]
    assert "data-region" not in rr  # no region chips any more; the forecast-only toggle stays
    assert "const inRegion = (s) => REGIONS[region].test(s) && (!prov || s.province === prov);" in APP
    body = APP[APP.index("async function renderRiver"):APP.index("function scrollRiver")]
    assert "whereRow(" in body and 'id="rv-region"' not in body
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'placeholder="ค้นหา จังหวัด/อำเภอ/สถานี"' in html


def test_one_forecaster_rows_and_chart_come_from_the_same_model_path():
    # owner 2026-10-03 (Kgt.19A): "Why trend and model forecast in the chart are different? … I thought the trend were
    # calculated by the model". No second forecaster beside the model: no measured-trend rows, no orange trend line;
    # the chart marks the model's 50 % range at 12/24/48 h, which the rows print (live check C15).
    assert "measured_trend" not in CODE and "trendPts" not in CODE
    assert 'class="fc-pt"' in APP and "data-lo=" in APP and "data-hi=" in APP
    assert 'recent: "แนวโน้มล่าสุด"' in APP
    legend = APP.split('class="legend-body">')[1][:300]
    assert "ตัวเลขในแถว" in legend


def test_river_tab_shows_every_gauge_of_a_picked_province():
    # owner 2026-10-03 (ชลบุรี, 1 gauge: "ทุกสาย (0)" and a pointer elsewhere): 13 provinces showed nothing. Gauges
    # outside a full river view (< 3 gauges per waterway) are listed below it, grouped by waterway, one line each.
    river = APP.split("async function renderRiver()")[1].split("function scrollRiver()")[0]
    assert "ลำน้ำอื่นใน" in river and "prowHTML(" in river and "ไม่ระบุชื่อลำน้ำ" in river
    assert "function prowHTML(s)" in APP


def test_a_thin_province_says_so_in_the_shared_where_row():
    # owner chose "Yes, one line": 1-2 gauges in a province is a gap of the national network, not of the app
    where = APP.split("function whereRow()")[1].split("document.addEventListener")[0]
    assert "สถานีวัดระดับน้ำเพียง" in where and "THIN_MAX" in where
