"""The "⚠️ จับตา" tab (owner 2026-10-03: "the list of potential risks according to the water level in next 24 or 48 hr
… link to the stations or areas … with the confidence"; spec docs/superpowers/specs/2026-10-03-watch-tab-satellite-design.md,
D-077). A gauge is listed once, in its worst group; track records are counts out of ten from our own forecast archive."""
import datetime as dt

import numpy as np

from floodwatch import risks


def g(code, status="normal", **k):
    base = {"code": code, "name_th": code, "province": "ชัยนาท", "region": "up", "status": status, "stale": False,
            "freeboard_m": 0.5, "bank_chance24": "<5%", "bank_chance48": "<5%", "change24": None, "upstream": None,
            "observed24": None, "trend": None}
    return {**base, **k}


def keys(out):
    return {grp["key"]: [i.get("code") or i.get("province") for i in grp["items"]] for grp in out["groups"]}


def test_a_gauge_appears_once_in_its_worst_group():
    st = [g("A", "critical", freeboard_m=-0.2, change24={"level": "strong_rise", "median": 0.3}),
          g("B", "warning", bank_chance24=">50%", change24={"level": "strong_rise", "median": 0.3}),
          g("C", change24={"level": "strong_rise", "median": 0.25})]
    out = risks.build(st, {}, None)
    assert [g["key"] for g in out["groups"]] == ["over_bank", "may_reach", "fast_rise"]
    assert [i["code"] for i in out["groups"][1]["items"]] == ["B"] and [i["code"] for i in out["groups"][2]["items"]] == ["C"]


def test_over_bank_splits_by_trend_then_province():
    # owner 2026-10-04: "classify ล้นตลิ่งแล้ว into 2 sub-categories … กำลังเพิ่มขึ้น … คงที่หรือลดลง" (names: น้ำยังขึ้น /
    # ทรงตัวหรือลดลง); the trend group is the station row's own (status.trend, D-083)
    up, flat = {"group": "rising"}, {"group": "flat_or_falling"}
    st = [g("A", "critical", trend=flat), g("B", "critical", trend=up), g("C", "critical", province="สิงห์บุรี", trend=up),
          g("D", "critical", trend=None)]
    grp = risks.build(st, {}, None)["groups"][0]
    assert grp["key"] == "over_bank"
    assert [(sub["sub"], [(p["province"], len(p["gauges"])) for p in sub["provinces"]]) for sub in grp["items"]] == [
        ("rising", [("ชัยนาท", 1), ("สิงห์บุรี", 1)]), ("flat_or_falling", [("ชัยนาท", 1)]), ("unknown", [("ชัยนาท", 1)])]


def test_may_reach_uses_only_the_two_upper_bands_and_says_which_window():
    st = [g("A", bank_chance24="25-50%"), g("B", bank_chance24="<5%", bank_chance48=">50%"), g("C", bank_chance24="5-25%")]
    items = risks.build(st, {}, None)["groups"][0]["items"]
    assert [(i["code"], i["band"], i["hours"]) for i in items] == [("B", ">50%", 48), ("A", "25-50%", 24)]


def test_may_reach_puts_rising_gauges_first_and_marks_each_with_its_trend():
    # owner 2026-10-04: the ticker said "ควรจับตา กรุงเทพฯ … ที่น้ำอาจถึงตลิ่งใน 24–48 ชม." but no Bangkok gauge was rising:
    # they sat steady 6–19 cm below the bank, inside the band. Each item says which trend group it is in (status.trend)
    up, flat = {"group": "rising"}, {"group": "flat_or_falling"}
    st = [g("A", bank_chance24=">50%", trend=flat, freeboard_m=0.06), g("B", bank_chance24="25-50%", trend=up),
          g("C", bank_chance48=">50%", trend=None)]
    items = risks.build(st, {}, None)["groups"][0]["items"]
    assert [(i["code"], i["sub"]) for i in items] == [("B", "rising"), ("A", "flat_or_falling"), ("C", "unknown")]


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
    assert out["groups"][0]["left_stale"] == 1 and len(out["groups"][0]["items"][0]["provinces"][0]["gauges"]) == 1


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


def test_lean_record_counts_how_often_an_unsure_row_went_the_measured_way():
    # runs whose 24 h row is unsure (persistence, wide range); the gauge rose 1 cm/h for 24 h before issue
    path = [{"h": h, "q": [0.8, 0.9, 1.04, 1.1, 1.2], "method": "persistence"} for h in range(1, 73)]  # median +4 cm: same way
    hours = [T0 + k * H for k in range(-30, 80)]
    up = {t: 1.0 + 0.01 * (t - T0).total_seconds() / 3600 for t in hours}          # keeps rising: hit
    flat_after = {t: (1.0 + 0.01 * min(0, (t - T0).total_seconds() / 3600)) for t in hours}  # rose, then stays: miss
    runs = [{"code": "A", "issue_time": T0, "now": 1.0, "path": path}, {"code": "B", "issue_time": T0, "now": 1.0, "path": path}]
    rec = risks.lean_record(runs, {"A": up, "B": flat_after})
    assert rec["24"] == {"n": 2, "hit": 0.5}


def test_band90_factor_is_the_smallest_widening_that_makes_the_90_band_hold_and_never_below_one():
    # Q54 (owner 2026-10-05: "Yes"): rolling, no future — research/2026-10-05_band_calibration_rolling.log
    now = T0 + 10 * 24 * H
    q = [0.9, 0.95, 1.0, 1.05, 1.1]  # 90 % band ±10 cm around the median 1.0
    def runs(code, n):
        return [{"code": code, "issue_time": now - (k + 30) * H, "now": 1.0,
                 "path": [{"h": 24, "q": q, "method": "star"}, None, None]} for k in range(n)]
    wide = {now - (k + 30) * H + 24 * H: 1.0 + (0.15 if k % 5 == 0 else 0.0) for k in range(150)}  # 20 % land 15 cm out
    f = risks.band90_factors(runs("A", 150), {"A": wide}, now)
    assert f["24"]["model"] == 1.5  # the smallest k with 90 % inside: 0.10 × 1.5 = 0.15
    calm = {t: 1.0 for t in wide}
    assert risks.band90_factors(runs("A", 150), {"A": calm}, now)["24"]["model"] == 1.0  # never narrows
    assert risks.band90_factors(runs("A", 40), {"A": wide}, now)["24"]["model"] == 1.0  # too few cases: unchanged


def test_band90_factor_is_found_on_the_range_before_widening():
    # KI-287 (2026-10-06): stored runs carry ranges already widened by the factor in force when they were issued
    # (forecast.widen90, payload band90); the new factor is applied to the raw range, so it must be found on the raw range,
    # or the calibration undoes itself once the window holds only widened runs
    now = T0 + 10 * 24 * H
    served = [0.85, 0.95, 1.0, 1.05, 1.15]  # a raw ±10 cm range stored after widening ×1.5 → ±15 cm
    runs = [{"code": "A", "issue_time": now - (k + 30) * H, "now": 1.0, "band90": {"24": {"model": 1.5, "no change": 1.0}},
             "path": [{"h": 24, "q": served, "method": "star"}, None, None]} for k in range(150)]
    wide = {now - (k + 30) * H + 24 * H: 1.0 + (0.15 if k % 5 == 0 else 0.0) for k in range(150)}  # 20 % land 15 cm out
    assert risks.band90_factors(runs, {"A": wide}, now)["24"]["model"] == 1.5  # ±15 cm on the raw ±10 cm: ×1.5 again
