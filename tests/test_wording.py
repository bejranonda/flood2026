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


def test_heavy_rain_reaches_the_top_bar_through_the_ticker_only():
    # KI-265 (rain only when heavy, one line) now lives in the ticker's facts (situation.HEAVY_MM = 35.1, D-089)
    from floodwatch import situation
    assert situation.HEAVY_MM == 35.1 and "SUMMARY_RAIN_MIN_MM" not in CODE


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


def test_one_where_row_for_both_tabs_with_region_and_province():
    # owner 2026-10-03: "if the users like to see stations in their province?" → "Shared where-row + river row":
    # [ภาค ▾][จังหวัด ▾] in the list AND the river tab (one state), replacing the list's 4 rows of region chips
    assert 'class="pick-region${sfx}"' in APP and 'class="pick-prov${sfx}"' in APP  # sfx "-w": the จับตา tab's own place
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
    assert "function prowHTML(s, " in APP


def test_a_thin_province_says_so_in_the_shared_where_row():
    # owner chose "Yes, one line": 1-2 gauges in a province is a gap of the national network, not of the app
    where = APP.split("function whereRow(")[1].split("document.addEventListener")[0]
    assert "สถานีวัดระดับน้ำเพียง" in where and "THIN_MAX" in where


def test_dwr_posts_are_a_trend_only_layer_without_status_or_bank():
    # owner 2026-10-03: "archive first, and show as trend-only layer". Depth on a local post, not m MSL; alarm levels
    # mostly a 4.00 m default: no status colour, no "ตลิ่ง", only the measured change in the list's own words (obsLine).
    js = APP.split("function dwrPopup(")[1].split("\n}\n")[0]
    assert "obsLine({ observed24: d.trend })" in js and "ตลิ่ง" not in js.replace("ไม่มีระดับตลิ่ง", "")
    assert "เสาวัดน้ำ กรมทรัพยากรน้ำ" in APP and "/api/dwr" in APP
    assert "กำลังเก็บข้อมูล" in js and "ค่าค้าง" in js


# --- v0.21.0: the "⚠️ จับตา" tab (D-077), satellite (D-078), every gauge with data on the map (D-079) -------------------
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")


def test_watch_tab_is_named_jabta_not_an_official_or_status_word():
    # "เฝ้าระวัง" is the yellow status (70-90 % of bank); "เตือนภัย" reads as an official warning (owner chose จับตา)
    assert 'data-tab="watch"' in INDEX and "⚠️ จับตา" in INDEX
    assert ">⚠️ เฝ้าระวัง<" not in INDEX and "เตือนภัย</button>" not in INDEX


def test_track_record_chip_is_counts_out_of_ten():
    # owner 2026-10-03 kept "6 ใน 10" over a percent: counts read better and match "… 7 ใน 10 ครั้ง"
    chip = APP.split("function recChip(")[1][:500]
    assert "ใน 10" in chip and "%" not in chip and "MIN_REC_N" in chip


def test_map_has_no_forecast_checkbox_and_draws_rings_for_gauges_without_one():
    assert "แสดงสถานีที่ยังคาดการณ์ไม่ได้" not in APP and "เฉพาะที่คาดการณ์ได้" not in APP
    assert "ยังไม่มีพยากรณ์" in APP


def test_tributaries_appear_with_their_river_not_under_other_waterways():
    # owner 2026-10-03: "คลองนางน้อย is under basin แม่น้ำตรัง" → same HII sub-basin = shown with the river
    assert "tribOf.get(s.code)" in APP and "ลำน้ำสาขาในลุ่ม" in APP and "รวมลำน้ำสาขา" in APP
    assert "padding-left: 12px" in (ROOT / "web" / "style.css").read_text(encoding="utf-8")  # text off the province bar


def test_no_satellite_cells_anywhere_in_the_app():
    # D-084: GISTDA's cells could mislead (owner 2026-10-04); a future source will get its own design
    assert "ดาวเทียม" not in CODE and "/api/satellite" not in APP and "sat_near_rai" not in APP


def test_over_bank_is_split_by_the_one_trend_rule_with_both_labels():
    # owner 2026-10-04: ล้นตลิ่งแล้ว → "น้ำยังขึ้น" / "ทรงตัวหรือลดลง"; labels "วัดได้ ↗ · คาด ?" (D-083)
    assert 'rising: "⬆ น้ำยังขึ้น"' in APP and 'flat_or_falling: "→ ทรงตัวหรือลดลง"' in APP
    assert "function trendLabels(t)" in APP and "`วัดได้ ${" in APP and "`คาด ${" in APP


def test_rivers_and_other_waterways_share_one_two_dimension_card():
    # owner 2026-10-04: "Keep format of summary show แม่น้ำหลัก and ลำน้ำอื่น consistency … status in 2 dimensions"
    assert APP.count("cardHTML(") >= 3 and "function summaryOf(gs" in APP
    card = APP.split("function cardHTML(")[1].split("\n}\n")[0]
    assert "ล้นตลิ่ง" in card and "ใกล้ตลิ่ง" in card and "น้ำยังขึ้น" in card and "ทรงตัวหรือลดลง" in card


def test_all_rivers_overview_counts_the_rows_own_trend_group():
    # v0.22.0 (D-083): the overview counts status.trend (forecast when sure, measured otherwise) and the statuses, the
    # same fields every row and the จับตา tab read; no second counting rule
    so = APP.split("function summaryOf(gs")[1].split("\n}\n")[0]
    assert "s.trend?.group" in so and '"rising"' in so and '"flat_or_falling"' in so and "directional(" not in so


def test_the_map_has_one_layer_box_whose_legend_lines_are_switches():
    # owner 2026-10-04: "Let the all stations can be show and hide … simplify the categories" → one box (D-085)
    assert 'L.control({ position: "topleft" })' not in APP and "ไม่มีพิกัด (ดูในรายการ)" not in APP
    box = APP.split("legend.onAdd = () => {")[1].split("legend.addTo(map)")[0]
    for k in ("critical", "warning", "watch", "normal", "unknown", "ring", "dwr", "traffy"):
        assert f'"{k}"' in box
    assert 'localStorage.setItem("layers"' in box and "<summary>ชั้นข้อมูล</summary>" in box


def test_the_measured_line_says_when_the_last_6_h_changed_course():
    # 2026-10-04: 101 gauges read "24 ชม. ที่ผ่านมา: เพิ่มขึ้น" while their group (the recent pace) was "ทรงตัวหรือลดลง";
    # the line now says what the last 6 h did whenever it differs, so card and group tell one story (D-083)
    ob = APP.split("const obsLine = (s) => {")[1].split("\n};\n")[0]
    assert "6 ชม. ล่าสุด" in ob and "s.trend" in ob


def test_forecast_rows_are_24_48_72_h_and_never_12_h():
    # owner 2026-10-04: "Can we remove trend 12 hr from stations, it is too much now … 24, 48, 72 hr"
    assert "[24, 48, 72]" in APP and "[12, 24, 48]" not in CODE and "ในอีก 12 ชม." not in CODE
    assert "trendRows(s, [s.change24 ? 24 : 12])" not in APP


def test_over_bank_subgroups_are_coloured_pills_with_province_chips():
    # owner 2026-10-04: "For subcategories, can we use color or symbol to make it easy to read. Currently, we see a lot
    # of text under subcategories" → coloured sub-group pill + province chips with a count badge
    w = APP.split("async function renderWatch()")[1].split("\n}\n")[0]
    assert 'class="wsubh ${' in w and 'class="wchip ${' in w and "สถานี ›" not in w.split('g.key === "over_bank"')[1].split("} else if")[0]


def test_top_bar_is_the_national_overview_and_one_ticker():
    # owner 2026-10-04: "Do not need to focus only สถานีในภาคกลาง, but provide only the overview of the nation"; rain
    # line and urgent line replaced by one running AI ticker for all of Thailand (D-089), refreshed every 30 min
    sm = APP.split("function renderSummary(")[1].split("\n}\n")[0]
    assert "ทั่วประเทศ" in sm and "const nat = stations" in sm and "mine.filter((s) => s.status === k)" not in sm
    assert "rainSummary(" not in sm and "ล้นตลิ่งและน้ำยังขึ้น" not in sm
    assert 'class="ticker' in sm and "/api/situation" in APP and "prefers-reduced-motion" in (ROOT / "web" / "style.css").read_text(encoding="utf-8")


def test_unsure_rows_lean_with_their_record_and_the_past_comes_first():
    # owner 2026-10-04: "Lean the rows by the trend" and "move 24 ชม. ที่ผ่านมา … before 24 hr prediction … the last and then
    # the future"; the word leans, the numbers stay the model's range (= the chart band)
    tr = APP.split("function trendRow(")[1].split("\n}\n")[0]
    assert "ch.lean" in tr and "น่าจะขึ้น" in tr and "น่าจะลดลง" in tr and "lean_rec" in tr
    assert "${obsLine(s)}${trendRows(s, [24])}" in APP and "${changeLines(s)}${trendRows(s, [24, 48, 72])}" in APP
