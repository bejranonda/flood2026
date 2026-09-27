import datetime as dt
import json
import math

import numpy as np

from floodwatch import forecast


def _synthetic(days=30, noise=0.02, seed=1):
    rng = np.random.default_rng(seed)
    t0 = dt.datetime(2026, 8, 27, tzinfo=dt.timezone.utc)
    times, vals = [], []
    for i in range(days * 24):
        h = t0.timestamp() / 3600 + i
        tide = 0.45 * math.cos(math.radians(15.0410686 * h + 30)) + 0.37 * math.cos(math.radians(28.9841042 * h + 80))
        times.append(t0 + dt.timedelta(hours=i))
        vals.append(1.0 + tide + rng.normal(0, noise))
    return times, vals


def test_tidal_station_prefers_tide_model_and_beats_persistence():
    times, vals = _synthetic()
    fc = forecast.forecast_station("T", times, vals, bank=2.0, rain_next24=0)
    assert fc["tide_fitted"]
    s6 = fc["skill"]["6"]
    assert s6["method"] in ("tide", "tide_trend") and s6["skill_vs_persistence"] > 0.5
    q = fc["path"][11]["q"]
    assert q == sorted(q)  # quantiles are monotone


def test_short_history_falls_back_to_persistence_without_intervals():
    times, vals = _synthetic(days=3)
    fc = forecast.forecast_station("T", times, vals, bank=2.0, rain_next24=0)
    assert fc["skill"] == {} and fc["path"][0]["q"] is None and fc["trend12"] == "unknown"


def test_status_relative_to_bank():
    assert forecast.classify_status(2.82, 2.2, -0.33)[0] == "critical"
    assert forecast.classify_status(0.0, 2.0, -2.0)[0] == "normal"
    assert forecast.classify_status(None, 2.0, -2.0)[0] == "unknown"


def test_outlook24_reports_peak_and_bank_chance():
    times, vals = _synthetic()
    fc = forecast.forecast_station("T", times, vals, bank=1.6, rain_next24=0)
    o = fc["outlook24"]
    assert 1 <= o["peak_h"] <= 24 and o["varies"]
    assert o["bank_chance"] in ("<5%", "5-25%", "25-50%", ">50%")
    far = forecast.forecast_station("T", times, vals, bank=9.0, rain_next24=0)["outlook24"]
    assert far["bank_chance"] == "<5%"


def test_long_record_backtests_recent_window_only():
    times, vals = _synthetic(days=120)
    fc = forecast.forecast_station("T", times, vals, bank=2.0, rain_next24=0)
    assert fc["skill"]["6"]["n"] <= forecast.EVAL_HOURS
    assert fc["skill"]["6"]["method"] in ("tide", "tide_trend")


def test_payload_is_json_serialisable():
    """numpy scalars (np.bool_) broke saving every forecast once; the stored payload must be plain JSON."""
    times, vals = _synthetic()
    for bank in (1.6, None):
        json.dumps(forecast.forecast_station("T", times, vals, bank=bank, rain_next24=0))


def test_no_peak_window_without_a_tide_model():
    times, vals = _synthetic(days=3)  # too short for any model -> no intervals, no outlook
    assert forecast.forecast_station("T", times, vals, bank=2.0, rain_next24=0)["outlook24"] is None
    path = [{"h": h, "method": "persistence", "q": [0.8, 0.9, 1.0 + 0.01 * h, 1.1, 1.2]} for h in range(1, 25)]
    assert forecast.outlook24(path, 2.0)["varies"] is False


# --- change_summary: "rise or fall, by how much, how sure" for citizens (D-047) ---------------------------------------
def test_change_summary_persistence_is_low_confidence_and_steady():
    # BKK008 on 2026-09-27: persistence, 12 h quantiles around a level of 1.08 m.
    out = forecast.change_summary([0.744, 0.963, 1.087, 1.25, 1.584], 1.08, {"method": "persistence",
                                  "skill_vs_persistence": 0.0, "coverage90_backtest": 0.898})
    assert out["dir"] == "steady" and out["level"] == "steady"
    assert out["confidence"] == "low"
    assert out["likely"] == [-0.12, 0.17] and out["range90"] == [-0.34, 0.5]


def test_change_summary_tide_model_with_skill_is_medium_never_high():
    # BKC002: tide model, skill 0.73 over persistence, 90 % band covered 90 % of the time in the backtest.
    out = forecast.change_summary([1.069, 1.31, 1.508, 1.713, 1.931], 2.06, {"method": "tide",
                                  "skill_vs_persistence": 0.729, "coverage90_backtest": 0.899})
    assert out["dir"] == "falling" and out["level"] == "strong_fall"  # median -0.55 m
    assert out["confidence"] == "medium"


def test_change_summary_levels_and_hidden_wide_bands():
    sk = {"method": "tide", "skill_vs_persistence": 0.5, "coverage90_backtest": 0.9}
    assert forecast.change_summary([1.0, 1.05, 1.10, 1.15, 1.2], 1.0, sk)["level"] == "rise"        # +10 cm
    assert forecast.change_summary([1.1, 1.2, 1.25, 1.3, 1.4], 1.0, sk)["level"] == "strong_rise"   # +25 cm
    assert forecast.change_summary([0.8, 0.88, 0.92, 0.95, 1.0], 1.0, sk)["level"] == "fall"        # -8 cm
    # BKK005: a ±3.5 m band says nothing; numbers are hidden with a flag (D-024), not shown.
    wide = forecast.change_summary([-5.547, -2.41, -2.064, -1.495, 1.453], -2.06, {"method": "persistence"})
    assert wide["wide"] is True and wide["likely"] is None
    assert forecast.change_summary(None, 1.0, sk) is None
    assert forecast.change_summary([1, 1, 1, 1, 1], None, sk) is None
