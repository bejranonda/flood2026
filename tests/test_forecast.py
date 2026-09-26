import datetime as dt
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
