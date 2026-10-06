"""7-day reservoir outlook for the dams list (Q58, D-102): inflow from the rain model only where it passed the operational
test (per dam, per horizon), persistence with its own band elsewhere; storage by water balance with the monthly loss term."""
import numpy as np

from floodwatch import reservoir as R

MODEL = {"dam_id": 12, "beta": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],  # inflow(t) = rain(t): a model that mirrors the day's rain
         "loss_by_month": {"10": -0.5, "11": -0.3}, "op_gain": {"1": 24.0, "3": 32.0, "7": 5.0},
         "bias": {str(k): v for k, v in zip(range(1, 8), (1.0, 0.9, 0.8, 0.8, 0.7, 0.6, 0.5))},
         "band_model": {str(h): [-1.0 * h, 1.5 * h] for h in range(1, 8)}, "band_persist": {str(h): [-2.0 * h, 2.0 * h] for h in range(1, 8)},
         "test_days": 43, "test_from": "2026-08-22", "test_to": "2026-10-04", "points": [(17.2, 98.9, 1000)]}
RAIN_PAST = [0.0] * 7                      # the 7 days before today
RAIN_FC = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]  # forecast for days 1..7 (lead = day)


def test_the_model_runs_where_it_passed_and_persistence_takes_over_where_it_did_not():
    path = R.inflow_path(MODEL, inflow_today=8.0, rain_past7=RAIN_PAST, rain_fc7=RAIN_FC)
    assert [p["method"] for p in path] == ["model"] * 3 + ["persistence"] * 4  # 3 d gain 32 % ≥ 10; 7 d gain 5 % < 10
    assert abs(path[0]["mid"] - 10.0 * 1.0) < 1e-9 and abs(path[1]["mid"] - 20.0 * 0.9) < 1e-9 and abs(path[2]["mid"] - 30.0 * 0.8) < 1e-9
    assert all(p["mid"] == 8.0 for p in path[3:])                          # held at today's inflow
    assert path[0]["lo"] == 9.0 and path[0]["hi"] == 11.5                   # the model's tested residual band at 1 day
    assert path[3]["lo"] == 0.0 and path[3]["hi"] == 16.0                   # persistence band, floored at zero


def test_a_dam_whose_model_failed_at_three_days_is_persistence_throughout():
    weak = {**MODEL, "op_gain": {"1": 2.0, "3": 4.0, "7": 12.0}}
    path = R.inflow_path(weak, inflow_today=8.0, rain_past7=RAIN_PAST, rain_fc7=RAIN_FC)
    assert [p["method"] for p in path[:3]] == ["persistence"] * 3 and [p["method"] for p in path[3:]] == ["model"] * 4


def test_storage_adds_inflow_subtracts_release_and_the_monthly_loss():
    dates = [f"2026-10-{d:02d}" for d in range(28, 32)] + ["2026-11-01", "2026-11-02", "2026-11-03"]
    inflow = [10.0] * 7
    s = R.storage_path(700.0, inflow, release=4.0, loss_by_month=MODEL["loss_by_month"], dates=dates)
    assert abs(s[0] - 705.5) < 1e-9 and abs(s[3] - 722.0) < 1e-9 and abs(s[4] - 727.7) < 1e-9  # Oct −0.5/day, Nov −0.3/day


def test_the_outlook_bundles_inflow_storage_bands_curve_position_and_the_test_result():
    dam = {"storage_mcm": 700.0, "inflow_mcm": 8.0, "released_mcm": 4.0, "dam_date": "2026-10-05"}
    rain14 = {"dates": ["2026-09-29", "2026-09-30"] + ["2026-10-%02d" % d for d in range(1, 13)],  # 7 days to today + 7 ahead
              "mm": RAIN_PAST + RAIN_FC}
    out = R.outlook(MODEL, dam, rain14, curves7={"upper": [690.0] * 7, "lower": [300.0] * 7, "dates": ["2026-10-%02d" % d for d in range(6, 13)]}, normal=710.0)
    assert len(out["days"]) == 7 and out["days"][0]["storage"] > 700.0 and out["days"][0]["above_upper"] is True
    assert out["days"][0]["storage_lo"] <= out["days"][0]["storage"] <= out["days"][0]["storage_hi"]
    assert out["methods"] == {"1-3": "model", "4-7": "persistence"} and out["test"]["gain_3d"] == 32.0 and out["test"]["days"] == 43
    assert out["release_assumed"] == 4.0 and "ปล่อยเท่าวันนี้" in out["note"]


def test_catchment_rain_covers_the_past_week_and_the_next_week_area_weighted():
    from floodwatch import impact
    calls = []

    def fake(url):
        calls.append(url)
        base = 1.0 if "latitude=12.848" in url else 3.0
        return {"daily": {"time": ["2026-09-%02d" % d for d in range(29, 31)] + ["2026-10-%02d" % d for d in range(1, 13)],
                          "precipitation_sum": [base] * 14}}
    out = impact.catchment_rain14([(12.848, 99.288, 300), (13.102, 99.422, 100)], fetch=fake)
    assert len(out["dates"]) == 14 and len(calls) == 2 and "past_days=7" in calls[0] and "forecast_days=7" in calls[0]
    assert abs(out["mm"][0] - (1.0 * 300 + 3.0 * 100) / 400) < 1e-9


def test_no_outlook_from_a_record_of_zeros():
    import datetime as dt
    days = [(dt.date(2026, 1, 1) + dt.timedelta(days=k)).isoformat() for k in range(270)]
    assert R.persistence_model(48, "ปากมูล", {d: 0.0 for d in days}) is None  # inflow only ever reported as 0: nothing to hold
    m = R.persistence_model(48, "ปากมูล", {d: 10.0 + (k % 5) for k, d in enumerate(days)})
    dam = {"storage_mcm": 0.0, "inflow_mcm": 0.0, "released_mcm": 0.0, "dam_date": "2026-10-04"}
    assert R.outlook(m, dam, None, None, 229.6) is None  # a reservoir reported empty is a missing value, not a start point


def test_the_dams_layer_carries_each_dams_outlook_when_one_exists():
    from floodwatch import impact
    meta = [{"dam_id": 12, "agency": "RID", "name_th": "สิริกิติ์", "lat": 17.76, "lon": 100.56, "normal_mcm": 9510.0, "max_mcm": 10500.0, "sub_basin_id": 2}]
    latest = {12: {"dam_date": "2026-10-05", "storage_mcm": 9000.0, "storage_pct": 94.6, "released_mcm": 12.0, "inflow_mcm": 40.0}}
    layer = impact.dams_layer(meta, latest, {}, {}, outlooks={12: {"days": [{"storage": 9100.0}] * 7, "methods": {"1-3": "model", "4-7": "model"}}})
    assert layer[0]["outlook"]["methods"]["1-3"] == "model" and layer[0]["records"][0]["agency"] == "RID"
    assert impact.dams_layer(meta, latest, {}, {})[0].get("outlook") is None


def test_the_tested_models_ship_with_the_package_and_carry_their_evidence():
    models = R.load_models()
    assert len(models) >= 15 and 13 in models and models[13]["name_th"] == "แก่งกระจาน"
    for m in models.values():
        assert len(m["beta"]) == 8 and set(m["op_gain"]) == {"1", "3", "7"} and set(m["bias"]) == {str(k) for k in range(1, 8)}
        assert set(m["band_model"]) == set(m["band_persist"]) == {str(k) for k in range(1, 8)} and m["test_days"] >= 30 and "research/" in m["source"]


def test_dams_without_a_tested_model_get_a_persistence_outlook_from_their_own_inflow():
    import datetime as dt
    inflow = {(dt.date(2026, 1, 1) + dt.timedelta(days=k)).isoformat(): 10.0 + (k % 5) for k in range(270)}
    m = R.persistence_model(41, "ป่าสักชลสิทธิ์", inflow)
    assert m["beta"] is None and m["method"] == "persistence" and set(m["band_persist"]) == {str(h) for h in range(1, 8)}
    assert m["test_days"] >= 260 and m["band_persist"]["7"][0] < 0 < m["band_persist"]["7"][1]
    path = R.inflow_path(m, inflow_today=34.4, rain_past7=[0.0] * 7, rain_fc7=[0.0] * 7)
    assert all(p["method"] == "persistence" and p["mid"] == 34.4 for p in path)
    assert R.persistence_model(41, "x", dict(list(inflow.items())[:100])) is None  # too little history: no outlook


def test_a_persistence_outlook_needs_no_rain_and_says_it_is_a_projection():
    import datetime as dt
    inflow = {(dt.date(2026, 1, 1) + dt.timedelta(days=k)).isoformat(): 30.0 for k in range(270)}
    m = R.persistence_model(41, "ป่าสักชลสิทธิ์", inflow)
    dam = {"storage_mcm": 957.0, "inflow_mcm": 34.4, "released_mcm": 43.2, "dam_date": "2026-10-05"}
    o = R.outlook(m, dam, None, curves7={"upper": [465.0] * 7, "lower": [132.0] * 7}, normal=870.0)
    assert o and abs(o["days"][6]["storage"] - (957.0 + 7 * (34.4 - 43.2))) < 0.05 and o["methods"] == {"1-3": "persistence", "4-7": "persistence"}
    assert "ถ้าไหลเข้าและระบายเท่าวันนี้" in o["note"] and o["test"]["model"] is False


def test_rain_as_known_at_issue_time_era5_to_five_days_back_then_the_scaled_model_mean():
    import datetime as dt
    d0 = dt.date(2026, 9, 1)
    days = [(d0 - dt.timedelta(days=k)).isoformat() for k in range(40)]
    era = {d: 1.0 for d in days}
    fc = {"best_match": {(d0 + dt.timedelta(days=k)).isoformat(): 2.0 for k in range(-6, 9)},
          "gfs_seamless": {(d0 + dt.timedelta(days=k)).isoformat(): 4.0 for k in range(-6, 9)}}
    scale = {"best_match": {str(k): 1.0 for k in range(8)}, "gfs_seamless": {**{str(k): 0.5 for k in range(8)}, "7": None}}
    past, fut = R.compose_rain(era, fc, scale, d0, ["best_match", "gfs_seamless"])
    assert len(past) == 30 and past[:25] == [1.0] * 25 and past[25:] == [2.0] * 5  # ERA5 to d0−5; (2·1 + 4·0.5)/2 after
    assert fut[:6] == [2.0] * 6 and fut[6] == 2.0  # lead 7: GFS has no scale → the other model alone


def test_the_7_day_inflow_features_are_the_tested_ones_and_a_lead_without_a_forecast_falls_back_to_persistence():
    import datetime as dt, math
    inflow30 = [5.0] * 28 + [6.0, 8.0]
    past30 = [1.0] * 27 + [0.0, 2.0, 4.0]
    fut7 = [10.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    d0 = dt.date(2026, 9, 1)
    doy = d0.timetuple().tm_yday
    x = R.features7("D", inflow30, past30, fut7, 2, d0)
    wet = sum(past30)
    assert x == [8.0, 6.0, math.sqrt(8.0), 4.0, 6.0, 10.0, wet, 15.0, 15.0, 15.0 * wet / 100.0,
                 math.sin(2 * math.pi * doy / 365.25), math.cos(2 * math.pi * doy / 365.25)]
    assert R.features7("L", inflow30, past30, fut7, 2, d0)[:2] == [math.log1p(8.0), math.log1p(6.0)]
    m30 = sum(inflow30) / 30
    assert R.features7("KF", inflow30, past30, fut7, 1, d0) == [8.0 - m30, 10.0, 10.0, wet, 10.0 * wet / 100.0]
    # a model that adds 1 to today's inflow at day 1 (only the first weight), persistence at day 2, no forecast at day 3
    par = {"mu": [0.0] * 12, "sd": [1.0] * 12, "w": [1.0] + [0.0] * 11, "ymean": 1.0}
    m7 = {"family": "D_E4", "horizons": {"1": {"use": "D_E4", "params": par, "band_model": [-1.0, 2.0], "band_persist": [-3.0, 3.0]},
                                         "2": {"use": "persistence", "params": par, "band_model": [-1.0, 1.0], "band_persist": [-3.0, 3.0]},
                                         "3": {"use": "D_E4", "params": par, "band_model": [-1.0, 1.0], "band_persist": [-3.0, 3.0]}}}
    p = R.inflow_path7(m7, inflow30, past30, [10.0, 5.0, float("nan"), 0, 0, 0, 0], d0)
    assert p[0] == {"h": 1, "mid": 9.0, "lo": 8.0, "hi": 11.0, "method": "model"}
    assert p[1]["mid"] == 8.0 and p[1]["method"] == "persistence" and p[1]["lo"] == 5.0
    assert p[2]["method"] == "persistence" and p[2]["mid"] == 8.0  # no forecast at lead 3 → persistence
    assert len(p) == 7 and p[6]["method"] == "persistence"  # a horizon the dam has no entry for


def test_rain_inputs7_weights_the_points_and_reads_each_models_series():
    import datetime as dt
    d0 = dt.date(2026, 10, 5)
    def fake(url):
        lat = float(url.split("latitude=")[1].split("&")[0])
        k = 1.0 if lat < 13 else 3.0
        if "archive-api" in url:
            return {"daily": {"time": ["2026-09-01", "2026-09-02"], "precipitation_sum": [k, None]}}
        return {"daily": {"time": ["2026-10-06"], "precipitation_sum_best_match": [k], "precipitation_sum_gfs_seamless": [2 * k]}}
    era, fc = R.rain_inputs7([[12.0, 99.0, 100.0], [14.0, 99.0, 300.0]], ["best_match", "gfs_seamless"], d0, fetch=fake)
    assert era == {"2026-09-01": 2.5}  # (1·100 + 3·300) / 400; a day nobody has stays out
    assert fc == {"best_match": {"2026-10-06": 2.5}, "gfs_seamless": {"2026-10-06": 5.0}}


def test_outlook7_runs_the_storage_path_on_the_7_day_inflow_and_states_its_test():
    import datetime as dt
    par = {"mu": [0.0] * 12, "sd": [1.0] * 12, "w": [1.0] + [0.0] * 11, "ymean": 1.0}
    m7 = {"family": "D_E4", "models": ["best_match"], "loss_by_month": {"10": -0.5}, "test_days": 43, "test_from": "2026-08-19",
          "test_to": "2026-09-28", "horizons": {str(h): {"use": "D_E4", "params": par, "band_model": [-1.0, 1.0], "band_persist": [-2.0, 2.0],
                                                         "mae_test": [3.0, 4.0]} for h in range(1, 8)}}
    dam = {"storage_mcm": 700.0, "inflow_mcm": 10.0, "released_mcm": 12.0, "dam_date": "2026-10-05"}
    o = R.outlook7(m7, dam, [9.0] * 29 + [10.0], [1.0] * 30, [2.0] * 7, {"upper": [600.0] * 7, "lower": [200.0] * 7}, 710.0)
    assert [d["inflow"] for d in o["days"]] == [11.0] * 7 and o["days"][0]["method"] == "model"
    assert abs(o["days"][6]["storage"] - (700.0 + 7 * (11.0 - 12.0 - 0.5))) < 1e-6 and o["days"][0]["above_upper"] is True
    assert o["test"]["model"] is True and o["test"]["gain_3d"] == 25.0 and o["methods"] == {"1-3": "model", "4-7": "model"}
    assert o["rain7_mm"] == 14.0 and "E-7D" in o["test"]["source"]


def test_the_q58_bands_are_read_as_observed_minus_predicted():
    # KI-309: research/2026-10-05_q58_operational.py stored quantiles of (predicted − observed); inflow_path adds a band to
    # the prediction, so it must be (observed − predicted) — Bhumibol's 7-day model band [−38.3, −0.07] means the inflow
    # came in *above* the model, and the range shown must lie above the line, not below
    m = R.load_models()
    bh = next(v for v in m.values() if v["name_th"] == "ภูมิพล")
    assert bh["band_model"]["7"] == [0.07, 38.303] and bh["band_persist"]["7"] == [-11.542, 40.578]


def test_a_missing_inflow_day_falls_back_to_persistence_not_to_nan():
    import datetime as dt
    par = {"mu": [0.0] * 12, "sd": [1.0] * 12, "w": [1.0] + [0.0] * 11, "ymean": 1.0}
    m7 = {"family": "D_E4", "horizons": {"1": {"use": "D_E4", "params": par, "band_model": [-1.0, 1.0], "band_persist": [-2.0, 2.0]}}}
    p = R.inflow_path7(m7, [5.0] * 28 + [float("nan"), 8.0], [1.0] * 30, [1.0] * 7, dt.date(2026, 10, 5))
    assert p[0]["method"] == "persistence" and p[0]["mid"] == 8.0


def test_the_recursive_model_runs_on_the_composed_rain_day_by_day():
    import datetime as dt
    beta = [0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]  # inflow(d) = inflow(d−1) + rain(d)
    m7 = {"family": "R_E4", "horizons": {str(h): {"use": "R_E4" if h >= 2 else "persistence", "params": {"beta": beta},
                                                  "band_model": [-1.0, 1.0], "band_persist": [-2.0, 2.0]} for h in range(1, 8)}}
    p = R.inflow_path7(m7, [5.0] * 30, [0.0] * 30, [1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 0.0], dt.date(2026, 10, 5))
    assert p[0]["method"] == "persistence" and p[0]["mid"] == 5.0
    assert [x["mid"] for x in p[1:]] == [8.0, 11.0, 11.0, 11.0, 11.0, 11.0] and p[1]["method"] == "model"


def test_each_horizon_can_use_its_own_family_and_rain_source():
    import datetime as dt
    d0 = dt.date(2026, 10, 5)
    par_d = {"mu": [0.0] * 12, "sd": [1.0] * 12, "w": [1.0] + [0.0] * 11, "ymean": 1.0}      # today's inflow + 1
    beta = [0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]                                          # inflow(d−1) + rain(d)
    m7 = {"family": "D_E3", "horizons": {
        "1": {"use": "D_bm", "family": "D_bm", "params": par_d, "band_model": [0, 0], "band_persist": [0, 0]},
        "2": {"use": "R_gfs", "family": "R_gfs", "params": {"beta": beta}, "band_model": [0, 0], "band_persist": [0, 0]}}}
    rain = {"bm": ([0.0] * 30, [9.0] * 7), "gfs": ([0.0] * 30, [1.0, 2.0, 0, 0, 0, 0, 0])}
    p = R.inflow_path7(m7, [5.0] * 30, [0.0] * 30, [0.0] * 7, d0, rain=rain)
    assert p[0]["mid"] == 6.0 and p[0]["method"] == "model"     # the direct model (bm rain does not enter its first weight)
    assert p[1]["mid"] == 8.0 and p[1]["method"] == "model"     # the recursion on GFS's rain: 5 + 1 + 2
    assert p[2]["method"] == "persistence"


def test_the_note_names_each_day_ranges_model_and_rain():
    import datetime as dt
    par = {"mu": [0.0] * 5, "sd": [1.0] * 5, "w": [0.0] * 5, "ymean": 0.0}  # KF: the 30-day mean
    beta = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    m7 = {"family": "R_E4", "models": ["best_match", "ecmwf_ifs025", "gfs_seamless", "icon_seamless"], "horizons": {
        **{str(h): {"use": "R_E4", "family": "R_E4", "params": {"beta": beta}, "band_model": [0, 0], "band_persist": [0, 0], "mae_test": [1.0, 2.0]} for h in (1, 2)},
        **{str(h): {"use": "KF_ec", "family": "KF_ec", "params": par, "band_model": [0, 0], "band_persist": [0, 0], "mae_test": [1.0, 2.0]} for h in range(3, 8)}}}
    dam = {"storage_mcm": 700.0, "inflow_mcm": 10.0, "released_mcm": 10.0, "dam_date": "2026-10-05"}
    rain = {"E4": ([1.0] * 30, [1.0] * 7), "ec": ([1.0] * 30, [2.0] * 7)}
    o = R.outlook7(m7, dam, [10.0] * 30, [1.0] * 30, [1.0] * 7, None, 710.0, rain=rain)
    assert "ฝนคาดการณ์ 4 แบบ (วันที่ 1–2)" in o["note"] and "ฝนคาดการณ์ ECMWF (วันที่ 3–7)" in o["note"]
