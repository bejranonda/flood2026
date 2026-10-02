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
