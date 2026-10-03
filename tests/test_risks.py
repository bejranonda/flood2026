"""The "⚠️ จับตา" tab (owner 2026-10-03: "the list of potential risks according to the water level in next 24 or 48 hr
… link to the stations or areas … with the confidence"; spec docs/superpowers/specs/2026-10-03-watch-tab-satellite-design.md,
D-077). A gauge is listed once, in its worst group; track records are counts out of ten from our own forecast archive."""
import datetime as dt

import numpy as np

from floodwatch import risks


def g(code, status="normal", **k):
    base = {"code": code, "name_th": code, "province": "ชัยนาท", "region": "up", "status": status, "stale": False,
            "freeboard_m": 0.5, "bank_chance24": "<5%", "bank_chance48": "<5%", "change24": None, "upstream": None,
            "observed24": None}
    return {**base, **k}


def keys(out):
    return {grp["key"]: [i.get("code") or i.get("province") for i in grp["items"]] for grp in out["groups"]}


def test_a_gauge_appears_once_in_its_worst_group():
    st = [g("A", "critical", freeboard_m=-0.2, change24={"level": "strong_rise", "median": 0.3}),
          g("B", "warning", bank_chance24=">50%", change24={"level": "strong_rise", "median": 0.3}),
          g("C", change24={"level": "strong_rise", "median": 0.25})]
    assert keys(risks.build(st, {}, None, None)) == {"over_bank": ["ชัยนาท"], "may_reach": ["B"], "fast_rise": ["C"]}


def test_over_bank_is_grouped_by_province_with_its_gauges():
    st = [g("A", "critical"), g("B", "critical"), g("C", "critical", province="สิงห์บุรี")]
    grp = risks.build(st, {}, None, None)["groups"][0]
    assert grp["key"] == "over_bank"
    assert [(i["province"], len(i["gauges"])) for i in grp["items"]] == [("ชัยนาท", 2), ("สิงห์บุรี", 1)]


def test_may_reach_uses_only_the_two_upper_bands_and_says_which_window():
    st = [g("A", bank_chance24="25-50%"), g("B", bank_chance24="<5%", bank_chance48=">50%"), g("C", bank_chance24="5-25%")]
    items = risks.build(st, {}, None, None)["groups"][0]["items"]
    assert [(i["code"], i["band"], i["hours"]) for i in items] == [("B", ">50%", 48), ("A", "25-50%", 24)]


def test_upstream_needs_a_fresh_strong_rise_upstream_and_a_gauge_at_watch_or_warning():
    up = g("U", observed24={"change_cm": 45, "level": "strong_rise"})
    st = [up, g("W", "watch", upstream=[{"code": "U", "lag_h": 20}]),
          g("N", "normal", upstream=[{"code": "U", "lag_h": 20}]),          # normal: not listed
          g("L", "warning", upstream=[{"code": "U", "lag_h": 60}]),         # travel time too long
          g("Q", "warning", upstream=[{"code": "U", "lag_h": None}]),       # travel time unknown
          g("S", "watch", upstream=[{"code": "V", "lag_h": 10}]),
          g("V", stale=True, observed24={"change_cm": 80, "level": "strong_rise"}),  # stale upstream
          g("M", "watch", upstream=[{"code": "Z", "lag_h": 10}]), g("Z", observed24=None)]
    items = [grp for grp in risks.build(st, {}, None, None)["groups"] if grp["key"] == "upstream"][0]["items"]
    assert [(i["code"], i["up"]["code"], i["up"]["lag_h"], i["up"]["rise_cm"]) for i in items] == [("W", "U", 20, 45)]


def test_stale_gauges_are_counted_not_listed():
    out = risks.build([g("A", "critical", stale=True), g("B", "critical")], {}, None, None)
    assert out["groups"][0]["left_stale"] == 1 and len(out["groups"][0]["items"][0]["gauges"]) == 1


def test_area_groups_rain_and_satellite_sorted_by_amount():
    sat = {"province": {"นครสวรรค์": 483000, "พิจิตร": 196000}, "img_from": "2026-09-28", "img_to": "2026-10-02"}
    out = risks.build([], {"เชียงใหม่": 20.0, "น่าน": 52.4, "ตาก": 36.0}, sat, None)
    assert keys(out) == {"rain": ["น่าน", "ตาก"], "satellite": ["นครสวรรค์", "พิจิตร"]}
    assert out["sat_dates"] == ["2026-09-28", "2026-10-02"]
    assert {i["province"]: i["region"] for i in out["groups"][1]["items"]}["นครสวรรค์"] == "up"


def test_nothing_to_report_gives_no_groups():
    out = risks.build([g("A")], {}, None, None)
    assert out["groups"] == [] and out["records"] == {} and out["sat_dates"] is None
