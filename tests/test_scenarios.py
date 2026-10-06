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
    assert best["city"] == "ramp" and best["worst"] == "ramp" and best["warning"] == "ramp"
    assert best["water"] is None  # both end at 690: no plan keeps more water (D-110)
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


def _r7_state():
    import copy
    from test_impact import STATE
    st = copy.deepcopy(STATE)
    mae = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
    st["river7"] = {"method": "hybrid", "lag_days": {"B.18": 0, "B.10": 1, "B.16": 2, "B.15": 2},
                    "gains_cm_per_cms": {"B.18": [0.0] * 7, "B.10": [0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                                         "B.16": [0, 0, 0.4, 0.4, 0.4, 0.4, 0.4], "B.15": [0.0] * 7},
                    "errors": {c: {"mae_m": mae, "p90_m": [2 * x for x in mae]} for c in ("B.18", "B.10", "B.16", "B.15")}}
    return st


def test_plans_use_the_river7_levels_once_the_release_reaches_each_point():
    from floodwatch import impact
    out = sc.daily_downstream(_r7_state(), [21.6] * 7)
    dq = impact.mcm_to_cms(21.6) - impact.mcm_to_cms(10.8)
    b10 = out["B.10"]  # today's level + 0.5 cm per m³/s from the day the new release reaches it (one day's travel → day 2)
    assert abs(b10[0]["level"][1] - 1.85) < 1e-9 and abs(b10[1]["level"][1] - (1.85 + 0.005 * dq)) < 1e-6
    assert abs(b10[1]["margin_m"] - (2.2 - 1.85 - 0.005 * dq)) < 1e-6 and abs(b10[1]["level"][2] - b10[1]["level"][1] - 0.3) < 1e-9
    loc = 140.0 - impact.mcm_to_cms(10.8)  # B.18: its own rating, anchored on today's level
    want = 2.18 + 0.1 * ((impact.mcm_to_cms(21.6) + loc) ** 0.5 - (impact.mcm_to_cms(10.8) + loc) ** 0.5)
    assert abs(out["B.18"][0]["level"][1] - want) < 1e-6
    assert all(abs(r["level"][1] - 1.9) < 1e-9 for r in out["B.15"])  # no detectable response: today's level


def test_a_plan_keeps_the_river_models_margin_for_each_day():
    eff = sc.effects(release=[10.8] * 7, storage=[720] * 7, upper=[600] * 7, lower=[200] * 7, normal=710.0,
                     margins={"B.10": [0.5] * 7}, city=("B.15",), today=10.8, margin_req={"B.10": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]})
    assert abs(eff["margin_vs_req_min"] - (0.5 - 0.7)) < 1e-9
    cmp = sc.compare(_r7_state(), inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0)
    assert cmp["margin_req"]["B.10"] == [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
    assert any("B.10 ≥ 0.10–0.40 ม." in c for c in cmp["constraints"])


def test_the_plan_says_which_downstream_model_it_used_and_the_story_states_its_tested_error():
    from floodwatch import explain
    cmp = sc.compare(_r7_state(), inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0)
    ds = cmp["downstream"]
    assert ds["method"] == "hybrid" and ds["mae_cm"]["B.10"] == [10, 15, 20, 25, 30, 35, 40]
    lines, story = explain.scenarios(cmp)
    text = " ".join(lines) + story
    assert "ทดสอบย้อนหลังแล้ว" in text and "±40 ซม." in text and "ยังไม่ผ่านการทดสอบ" not in text
    from test_impact import STATE
    assert sc.compare(STATE, inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0)["downstream"]["method"] == "whatif"


def test_plans_can_run_on_the_tested_7_day_inflow_path_and_say_so():
    path = [{"mid": 10.0 + k, "lo": 9.0 + k, "hi": 12.0 + k, "method": "model" if k else "persistence"} for k in range(7)]
    st = _r7_state()
    st["dam"]["storage_mcm"] = 700.0
    cmp = sc.compare(st, inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0, inflow_path=path)
    inf = cmp["inflow"]
    assert inf["mid"] == [10.0 + k for k in range(7)] and inf["low"][6] == 15.0 and inf["high"][6] == 18.0
    assert inf["method"] == "model" and "แบบจำลอง" in inf["note"]
    hold = next(p for p in cmp["plans"] if p["kind"] == "hold")
    assert abs(hold["storage"][0] - (700.0 + 10.0 - 10.8)) < 1e-6  # day 1 on the model's inflow, today's release held


def test_the_story_says_the_rain_forecast_drives_the_inflow_when_the_tested_model_is_used():
    from floodwatch import explain
    path = [{"mid": 10.0, "lo": 9.0, "hi": 12.0, "method": "model" if k >= 3 else "persistence"} for k in range(7)]
    st = _r7_state()
    st["dam"].update({"storage_mcm": 700.0, "inflow_mcm": 10.3, "name_th": "แก่งกระจาน"})
    cmp = sc.compare(st, inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0, inflow_path=path)
    cmp["inputs"] = {"rain7": {"mm": [6.9, 7.6, 4.6, 3.9, 14.3, 17.2, 6.1]}}
    cmp["dam"] = st["dam"]
    lines, story = explain.scenarios(cmp)
    text = " ".join(lines) + story
    assert "ใช้ในแบบจำลองน้ำไหลเข้า" in text and "ไม่ได้ใช้คำนวณ" not in text and "คิดว่าไหลเข้าเท่านี้ต่อไป" not in text


def test_a_goal_has_a_best_plan_only_when_the_plans_differ_on_it():
    # D-110: "ท่วมรวมน้อยสุด" and "ไม่มีจุดใดล้นหนัก" were awarded to 9.5 while no plan overtopped and every margin was > 2 m
    rows = [_row("a", worst_margin_min=2.11, city_margin_min=2.13, storage_end=715.0, ramp_max=0.0),
            _row("b", worst_margin_min=2.13, city_margin_min=2.13, storage_end=723.0, ramp_max=1.13),
            _row("c", worst_margin_min=0.18, city_margin_min=1.73, storage_end=639.0, ramp_max=10.87)]
    best = sc.best_for(rows)
    assert best["total"] is None  # nothing overtops anywhere
    assert best["worst"] == "b" and best["water"] == "b" and best["warning"] == "a" and best["city"] in ("a", "b")
    same = [_row("x", storage_end=700.0), _row("y", storage_end=700.4)]
    assert sc.best_for(same)["water"] is None and sc.best_for(same)["city"] is None
    assert sc.EFFECT_TH["worst"] == "ห่างตลิ่งมากสุด"


def test_a_day_cell_is_the_worst_gauge_with_outside_and_km_and_rows_carry_their_status():
    b18 = {"margin_m": 0.18, "outside": True}
    down = {"B.18": [b18, dict(b18)],
            "B.10": [{"margin_m": 5.0, "outside": False}, {"margin_m": 0.1, "outside": False}],
            "B.16": [{"margin_m": None, "outside": False}, {"margin_m": -0.2, "outside": True}]}
    req = {"B.18": [0.08, 0.1], "B.10": [0.12, 0.22], "B.16": 0.3}
    cells = sc.day_cells(down, req, {"B.18": 62.4, "B.10": 45.8, "B.16": 11.4}, days=2)
    assert cells[0] == {"status": "ok", "outside": True, "km": 0.0, "codes": [], "worst_code": "B.18", "worst_margin": 0.18,
                        "worst_req": 0.08}
    assert cells[1]["status"] == "over" and cells[1]["codes"] == ["B.10", "B.16"] and cells[1]["km"] == 57.2
    assert cells[1]["worst_code"] == "B.16" and cells[1]["outside"] is True
    assert down["B.10"][1]["status"] == "near" and down["B.16"][0]["status"] == "none" and down["B.18"][0]["status"] == "ok"


def test_a_day_without_any_margin_is_none_not_ok():
    # Review Focus 1: a stale feed (every margin None) is grey "none" with 0 km, never blue
    cells = sc.day_cells({"B.10": [{"margin_m": None}], "B.16": [{"margin_m": None}]}, {"B.10": [0.1]}, {"B.10": 45.8}, days=1)
    assert cells == [{"status": "none", "outside": False, "km": 0.0, "codes": [], "worst_code": None, "worst_margin": None,
                      "worst_req": None}]


def test_outside_detail_names_each_gauge_its_days_its_highest_flow_and_the_ratings_range():
    from test_impact import STATE
    down = sc.daily_downstream(STATE, [21.6] * 7, diversion_cms=63.0)
    det = {o["code"]: o for o in sc.outside_detail(down, STATE["points"])}
    assert det["B.18"]["days"] == [1, 2, 3, 4, 5, 6, 7] and det["B.18"]["qmax"] == 150.0 and det["B.18"]["flow_max"] > 260
    assert det["B.10"]["days"] == [2, 3, 4, 5, 6, 7]
    assert "B.16" not in det  # 205 m³/s < the 300 its rating has seen
    # the city gauge reads B.16's flow (its rating_from), as impact.whatif does
    assert det["B.15"]["days"] == [3, 4, 5, 6, 7] and abs(det["B.15"]["flow_max"] - max(r["flow_cms"] for r in down["B.16"])) < 0.2


def test_short_labels_for_the_grid():
    assert sc.short_label({"kind": "hold", "release": [10.63] * 7}) == "10.6 วันนี้"
    assert sc.short_label({"kind": "constant", "release": [21.5] * 7}) == "21.5 คงที่"
    assert sc.short_label({"kind": "ramp", "release": [22.0, 18.67, 15.33, 12.0, 8.67, 5.33, 2.0]}) == "22→2 ทยอย"
    assert sc.short_label({"kind": "front", "release": [6.0] * 3 + [12.0] * 4}) == "6→12 สองช่วง"
    assert sc.short_label({"kind": "custom", "release": [12.5] * 7}) == "กำหนดเอง 12.5"
    assert sc.short_label({"kind": "custom", "release": [12.0, 13, 14, 15, 16, 17, 18.5]}) == "กำหนดเอง 12→18.5"


def test_the_comparison_carries_the_grid_ladder_roles_labels_days_and_outside_flags():
    st = _r7_state()
    st["reach_km"] = {"B.18": 62.4, "B.10": 45.8, "B.16": 11.4, "B.15": 21.0}
    st["places"] = {"B.10": [{"village": "บ้านท่าโล้", "amphoe": "ท่ายาง"}]}
    cmp = sc.compare(st, inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0,
                     customs=[[12.0] * 7, [20.0] * 7])
    by = {p["id"]: p for p in cmp["plans"]}
    assert [by[i]["release"][0] for i in cmp["ladder"]] == [float(x) for x in range(0, 25, 2)]  # 0, 2 … 24
    assert all("ladder" in by[i]["roles"] for i in cmp["ladder"])
    star = by[cmp["optimal"]["id"]]
    assert "star" in star["roles"] and star["label"] and len(star["days"]) == 7
    assert {"status", "outside", "km", "codes"} <= set(star["days"][0])
    customs = [p for p in cmp["plans"] if p["kind"] == "custom"]
    assert [p["release"][0] for p in customs] == [12.0, 20.0] and all("custom" in p["roles"] for p in customs)
    big = next(p for p in customs if p["release"][0] == 20.0)
    assert big["outside_any"] and big["outside_detail"][0]["code"] == "B.18"  # ≈ 231 m³/s + local > 150 seen
    assert cmp["places"]["B.10"][0]["village"] == "บ้านท่าโล้" and cmp["reach_km"]["B.18"] == 62.4
    assert all(p["downstream"]["B.10"][0].get("status") for p in cmp["plans"])
    only = [p for p in cmp["plans"] if p["roles"] == ["ladder"]]
    assert only and "level" not in only[0]["downstream"]["B.10"][0]  # ladder rungs travel light
    assert set(cmp["picks"]) <= set(by) and all("pick" in by[i]["roles"] for i in cmp["picks"])
    import json as _j
    assert len(_j.dumps(cmp, ensure_ascii=False)) < 150_000


def test_a_custom_plan_equal_to_todays_keeps_both_rows():
    # Review Focus 4: today's release typed again is a custom row beside the hold row, not a replacement
    cmp = sc.compare(_r7_state(), inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0,
                     customs=[[10.8] * 7])
    kinds = [p["kind"] for p in cmp["plans"] if p["release"] == [10.8] * 7]
    assert sorted(kinds) == ["custom", "hold"]
