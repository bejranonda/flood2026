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
    assert keys(risks.build(st, {}, None)) == {"over_bank": ["ชัยนาท"], "may_reach": ["B"], "fast_rise": ["C"]}


def test_over_bank_is_grouped_by_province_with_its_gauges():
    st = [g("A", "critical"), g("B", "critical"), g("C", "critical", province="สิงห์บุรี")]
    grp = risks.build(st, {}, None)["groups"][0]
    assert grp["key"] == "over_bank"
    assert [(i["province"], len(i["gauges"])) for i in grp["items"]] == [("ชัยนาท", 2), ("สิงห์บุรี", 1)]


def test_may_reach_uses_only_the_two_upper_bands_and_says_which_window():
    st = [g("A", bank_chance24="25-50%"), g("B", bank_chance24="<5%", bank_chance48=">50%"), g("C", bank_chance24="5-25%")]
    items = risks.build(st, {}, None)["groups"][0]["items"]
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
    items = [grp for grp in risks.build(st, {}, None)["groups"] if grp["key"] == "upstream"][0]["items"]
    assert [(i["code"], i["up"]["code"], i["up"]["lag_h"], i["up"]["rise_cm"]) for i in items] == [("W", "U", 20, 45)]


def test_stale_gauges_are_counted_not_listed():
    out = risks.build([g("A", "critical", stale=True), g("B", "critical")], {}, None)
    assert out["groups"][0]["left_stale"] == 1 and len(out["groups"][0]["items"][0]["gauges"]) == 1


def test_heavy_rain_provinces_sorted_by_amount():
    out = risks.build([], {"เชียงใหม่": 20.0, "น่าน": 52.4, "ตาก": 36.0}, None)
    assert keys(out) == {"rain": ["น่าน", "ตาก"]}
    assert out["groups"][0]["items"][0]["region"] == "north"


def test_nothing_to_report_gives_no_groups():
    out = risks.build([g("A")], {}, None)
    assert out["groups"] == [] and out["records"] == {} and "sat_dates" not in out


# --- track records (risk_record): counts out of ten from our own forecasts and readings ------------------------------
T0 = dt.datetime(2026, 9, 26, tzinfo=dt.timezone.utc)
H = dt.timedelta(hours=1)


def test_bank_record_counts_runs_below_bank_that_reached_it():
    path = [{"h": h, "q": [0.0, 0.0, 2.0, 2.0, 2.0]} for h in range(1, 49)]  # median over the bank: ">50%"
    runs = [{"code": "A", "issue_time": T0, "path": path, "now": 1.0}, {"code": "B", "issue_time": T0, "path": path, "now": 1.0},
            {"code": "C", "issue_time": T0, "path": path, "now": 2.5}]         # C already over the bank: not counted
    obs = {"A": [(T0 + k * H, 1.0 + (1.0 if k == 10 else 0)) for k in range(1, 25)],
           "B": [(T0 + k * H, 1.0) for k in range(1, 25)], "C": [(T0 + k * H, 2.5) for k in range(1, 25)]}
    assert risks.bank_record(runs, obs, {"A": 1.5, "B": 1.5, "C": 1.5}, 24) == {">50%": {"n": 2, "hit": 0.5}}


def test_rise_record_checks_the_reading_24_h_later():
    path = [{"h": 24, "q": [0, 0, 1.3, 0, 0]}]
    runs = [{"code": "A", "issue_time": T0, "path": path, "now": 1.0}, {"code": "B", "issue_time": T0, "path": path, "now": 1.0},
            {"code": "C", "issue_time": T0, "path": [{"h": 24, "q": [0, 0, 1.1, 0, 0]}], "now": 1.0}]  # +10 cm: no signal
    obs = {"A": [(T0 + 24 * H, 1.15)], "B": [(T0 + 24 * H, 1.02)], "C": [(T0 + 24 * H, 1.5)]}
    assert risks.rise_record(runs, obs) == {"n": 2, "hit": 0.5}


def test_upstream_record_uses_the_fitted_24_h_change_like_the_live_rule():
    up = np.concatenate([np.full(30, 1.0), np.linspace(1.0, 1.5, 25), np.full(40, 1.5)])  # +50 cm over 24 h
    rises = np.concatenate([np.full(64, 2.0), np.full(31, 2.3)])                           # +30 cm ~10 h after the ramp
    flat = np.full(95, 2.0)
    a = risks.upstream_record([("D", "U", 12)], {"U": up, "D": rises}, step=1)
    b = risks.upstream_record([("D", "U", 12)], {"U": up, "D": flat}, step=1)
    assert a["n"] == b["n"] > 0 and a["hit"] > 0.4 and b["hit"] == 0.0


def test_chip_text_is_counts_out_of_ten_and_needs_30_cases():
    # owner 2026-10-03 kept "6 ใน 10" over a percent: counts read better and match "… 7 ใน 10 ครั้ง" in the ⓘ
    assert risks.chip_text({"n": 132, "hit": 0.614}) == "6 ใน 10"
    assert risks.chip_text({"n": 345, "hit": 0.035}) == "< 1 ใน 10"
    assert risks.chip_text({"n": 12, "hit": 0.9}) is None and risks.chip_text(None) is None
