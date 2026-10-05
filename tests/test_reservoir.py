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


def test_the_dams_layer_carries_each_dams_outlook_when_one_exists():
    from floodwatch import impact
    meta = [{"dam_id": 12, "agency": "RID", "name_th": "สิริกิติ์", "lat": 17.76, "lon": 100.56, "normal_mcm": 9510.0, "max_mcm": 10500.0, "sub_basin_id": 2}]
    latest = {12: {"dam_date": "2026-10-05", "storage_mcm": 9000.0, "storage_pct": 94.6, "released_mcm": 12.0, "inflow_mcm": 40.0}}
    layer = impact.dams_layer(meta, latest, {}, {}, outlooks={12: {"days": [{"storage": 9100.0}] * 7, "methods": {"1-3": "model", "4-7": "model"}}})
    assert layer[0]["outlook"]["methods"]["1-3"] == "model" and layer[0]["records"][0]["agency"] == "RID"
    assert impact.dams_layer(meta, latest, {}, {})[0].get("outlook") is None
