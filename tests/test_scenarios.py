"""7-day release scenarios for the impact tab (owner 2026-10-05: scenarios found by calculation, each effect, the optimal by
a stated rule; D-101). Pure functions; the state comes from impact.build_state."""
import numpy as np

from floodwatch import scenarios as sc


def test_water_balance_adds_inflow_subtracts_release_and_never_goes_negative():
    assert sc.water_balance(700.0, [10.0, 10.0], [5.0, 5.0]) == [705.0, 710.0]
    assert sc.water_balance(3.0, [0.0, 0.0], [5.0, 5.0]) == [0.0, 0.0]


def test_candidate_plans_are_searched_not_fixed_steps_and_stay_feasible():
    plans = sc.candidate_plans(today=10.0, max_release=25.0, days=7)
    assert all(len(p["release"]) == 7 and min(p["release"]) >= 0 and max(p["release"]) <= 25.0 for p in plans)
    assert {"hold", "constant", "ramp", "front"} <= {p["kind"] for p in plans}
    assert any(p["kind"] == "hold" and p["release"] == [10.0] * 7 for p in plans)
    assert 100 <= len(plans) <= 2000  # a real search, still cheap


def test_effects_measure_city_worst_total_dam_curve_water_and_warning():
    eff = sc.effects(release=[10, 12, 12, 12, 12, 12, 12], storage=[720, 715, 710, 705, 700, 695, 690],
                     upper=[600] * 7, lower=[200] * 7, normal=710.0,
                     margins={"B.10": [2, 2, 1.5, 1.5, 1.5, 1.5, 1.5], "B.15": [1, 0.8, 0.5, 0.5, 0.5, 0.5, 0.5],
                              "PCH001": [1.2, 1, 0.7, 0.7, 0.7, 0.7, -0.2]}, city=("B.15", "PCH001"))
    assert eff["city_margin_min"] == -0.2 and eff["worst_margin_min"] == -0.2 and abs(eff["overtop_sum"] - 0.2) < 1e-9
    assert eff["storage_peak"] == 720 and eff["days_above_normal"] == 2 and eff["under_curve_day"] is None
    assert eff["storage_end"] == 690 and eff["end_vs_lower"] == 490 and eff["ramp_max"] == 2 and eff["release_mean"] > 11.7
    # the step from today's release counts as warning time too; the model's own error per point is a required margin
    eff3 = sc.effects(release=[19.0] * 7, storage=[720] * 7, upper=[600] * 7, lower=[200] * 7, normal=710.0,
                      margins={"B.10": [0.08] * 7, "B.16": [0.9] * 7}, city=("B.15",), today=10.8, margin_req={"B.10": 0.39, "B.16": 0.48})
    assert abs(eff3["ramp_max"] - 8.2) < 1e-9 and abs(eff3["margin_vs_req_min"] - (0.08 - 0.39)) < 1e-9
    eff2 = sc.effects(release=[10] * 7, storage=[650, 620, 600, 590, 580, 570, 560], upper=[600] * 7, lower=[200] * 7, normal=710.0,
                      margins={"B.15": [1] * 7}, city=("B.15",))
    assert eff2["under_curve_day"] == 3 and eff2["days_above_normal"] == 0


def _row(i, **e):
    base = {"city_margin_min": 1.0, "worst_margin_min": 1.0, "overtop_sum": 0.0, "storage_peak": 700.0, "days_above_normal": 0,
            "under_curve_day": 7, "storage_end": 650.0, "end_vs_lower": 400.0, "ramp_max": 0.0, "release_mean": 10.0,
            "margin_vs_req_min": 0.5}
    return {"id": i, "effects": {**base, **e}}


def test_best_for_each_effect_and_the_stated_optimal_rule_are_explainable():
    # storage today 725 above the upper curve (600): a plan must not overtop any gauge (C1), not exceed the maximum
    # storage (C2) and not leave the reservoir higher than today (C3); ★ = fastest return toward the curve, then the
    # gentlest change of release. Per-effect bests are taken among the same feasible plans.
    rows = [_row("hold", city_margin_min=2.0, worst_margin_min=1.8, under_curve_day=None, storage_peak=740.0, storage_end=740.0,
                 days_above_normal=7),
            _row("zero", city_margin_min=2.3, worst_margin_min=2.3, under_curve_day=None, storage_peak=798.0, storage_end=798.0,
                 days_above_normal=7),
            _row("more", city_margin_min=1.2, worst_margin_min=1.0, under_curve_day=None, storage_peak=725.0, storage_end=690.0,
                 days_above_normal=2, ramp_max=3.0),
            _row("most", city_margin_min=-0.3, worst_margin_min=-0.3, overtop_sum=0.9, under_curve_day=7, storage_peak=725.0,
                 storage_end=598.0, days_above_normal=1, end_vs_lower=300.0, ramp_max=8.0),
            _row("ramp", city_margin_min=1.4, worst_margin_min=1.1, under_curve_day=None, storage_peak=725.0, storage_end=690.0,
                 days_above_normal=3, ramp_max=1.0)]
    feas = sc.feasible(rows, storage0=725.0, upper_today=600.0, max_storage=900.0)
    assert [r["id"] for r in feas] == ["more", "ramp"]  # hold/zero let the reservoir rise; most overtops
    thin = _row("thin", worst_margin_min=0.08, storage_end=660.0, margin_vs_req_min=-0.31)  # 8 cm margin, model error 39 cm
    assert "thin" not in [r["id"] for r in sc.feasible(rows + [thin], storage0=725.0, upper_today=600.0, max_storage=900.0)]
    best = sc.best_for(feas)
    assert best["city"] == "ramp" and best["worst"] == "ramp" and best["warning"] == "ramp" and best["water"] in ("more", "ramp")
    opt = sc.optimal(rows, storage0=725.0, upper_today=600.0, normal=710.0, max_storage=900.0)
    assert opt["id"] == "ramp" and opt["constraints_met"] is True and "ตลิ่ง" in opt["reason"] and "เส้นควบคุม" in opt["reason"]
    # nothing meets the constraints: say so, pick the plan that overtops least while still lowering the reservoir
    only = sc.optimal([rows[0], rows[1], rows[3]], storage0=725.0, upper_today=600.0, normal=710.0, max_storage=900.0)
    assert only["constraints_met"] is False and only["id"] == "most" and "ไม่มีแผน" in only["reason"]


def test_daily_downstream_uses_whole_day_travel_times_and_todays_release_before_day_one():
    from test_impact import STATE
    path = [21.6] * 7  # double today's 10.8
    out = sc.daily_downstream(STATE, path, diversion_cms=63.0)
    assert set(out) == {"B.18", "B.10", "B.16", "B.15"} and all(len(v) == 7 for v in out.values())
    # B.18 (lag 2 h → same day) feels the new release on day 1; B.10 (lag 32 h → 1 day) still shows today's release on day 1
    assert out["B.18"][0]["flow_cms"] > 200 and abs(out["B.10"][0]["flow_cms"] - (140.0 - 63.0 + max(0.0, 73.0 - (136.0 - 63.0)))) < 0.5
    assert out["B.10"][1]["flow_cms"] > out["B.10"][0]["flow_cms"] and "margin_m" in out["B.15"][6]


def test_the_inflow_band_widens_in_the_high_inflow_regime():
    lo_n, hi_n = sc.inflow_band(3.0, 7)
    lo_h, hi_h = sc.inflow_band(12.0, 7)
    assert lo_n < 0 < hi_n and (sc.HIGH_BAND is None or (lo_h < lo_n and hi_h > hi_n))
    assert sc.inflow_band(3.0, 9) == sc.inflow_band(3.0, 7)  # beyond 7 days the 7-day band holds


def test_the_explanation_names_the_plan_the_rule_and_the_label_without_verdict_words():
    from floodwatch import explain
    plan = {"id": "p1", "kind": "ramp", "release": [10.8, 12.0, 13.2, 14.4, 15.6, 16.8, 18.0], "storage": [724] * 7, "storage_low": [700] * 7,
            "storage_high": [740] * 7, "best_for": ["curve", "dam"], "optimal": True, "feasible": True,
            "effects": {"city_margin_min": 1.4, "worst_margin_min": 1.1, "overtop_sum": 0.0, "storage_peak": 725.0, "days_above_normal": 3,
                        "under_curve_day": None, "storage_end": 690.0, "end_vs_lower": 486.0, "ramp_max": 1.2, "release_mean": 14.4}}
    cmp = {"dam": {"name_th": "แก่งกระจาน", "dam_date": "2026-10-05", "storage_mcm": 725.85, "storage_pct": 102.2, "released_mcm": 10.8,
                   "inflow_mcm": 10.33}, "upper": [597.7] * 7, "lower": [204.0] * 7, "normal": 710.0,
           "inflow": {"mid": [10.33] * 7, "low": [0.0] * 7, "high": [15.7] * 7, "regime": "high", "method": "hold", "note": "x"},
           "inputs": {"rain7": {"mm": [6.9, 7.6, 4.6, 3.9, 14.3, 17.2, 6.1]}},
           "optimal": {"id": "p1", "constraints_met": True, "reason": "ลดปริมาตรอ่างได้มากที่สุด โดยไม่มีจุดใดเกินตลิ่ง", "rule": "r"},
           "best_for": {"city": "p1", "worst": "p1", "total": "p1", "dam": "p1", "curve": "p1", "water": "p1", "warning": "p1"},
           "plans": [plan], "downstream_validated": False}
    lines, story = explain.scenarios(cmp)
    text = " ".join(lines) + story
    assert "แก่งกระจาน" in text and "ทยอย" in text and "10.8" in text and "18.0" in text and "เส้นควบคุม" in text
    assert "ยังไม่ผ่านการทดสอบ" in text and "ปลอดภัย" not in text and "safe" not in text.lower()
    assert explain.plan_words({"kind": "constant", "release": [14.0] * 7}) == "14.0 ล้าน ลบ.ม./วัน คงที่ 7 วัน"
    assert explain.plan_words({"kind": "front", "release": [20.0, 20.0, 10.0, 10.0, 10.0, 10.0, 10.0]}) == "20.0 ล้าน ลบ.ม./วัน 2 วันแรก แล้ว 10.0"
