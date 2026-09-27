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


def test_score_external_compares_with_persistence_at_each_lead():
    # pairs: (lead_h, forecast, observed_at_valid, observed_at_issue)
    pairs = [(24, 2.10, 2.14, 2.50), (24, 2.30, 2.20, 2.20), (48, 2.0, 2.3, 2.25)]
    out = forecast.score_external(pairs)
    assert out[24]["n"] == 2 and abs(out[24]["mae"] - 0.07) < 1e-9 and abs(out[24]["mae_persistence"] - 0.18) < 1e-9
    assert abs(out[24]["skill"] - (1 - 0.07 / 0.18)) < 1e-9
    assert out[48]["skill"] < 0  # worse than "no change" at 48 h
    assert forecast.score_external([]) == {}


# --- network space-time AR + rain ("star", D-052) ------------------------------------------------------------------
def _driven(days=120, seed=3, lag=24, rain_gain=0.004):
    """A gauge driven by an upstream gauge (lag hours) and by rain falling in the next hours, plus noise."""
    rng = np.random.default_rng(seed)
    t0 = dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc)
    n = days * 24
    up = np.cumsum(rng.normal(0, 0.02, n + 200))           # slow random upstream wave
    rain = np.where(rng.random(n + 200) < 0.03, rng.gamma(2, 6, n + 200), 0.0)  # showers, mm/h
    y = np.empty(n)
    for i in range(n):
        y[i] = 0.8 * up[i + 200 - lag] + rain_gain * rain[i + 200 - 6:i + 200].sum() * 10 + rng.normal(0, 0.01)
    times = [t0 + dt.timedelta(hours=i) for i in range(n)]
    base = int(t0.timestamp() // 3600)
    exo = {"up": [(times, list(up[200:]))], "q": None,
           "rain": {"hind": {base + i: (float(rain[i + 200]), float(rain[i + 200])) for i in range(n)},
                    "live": {base + n + k: 0.0 for k in range(72)}}}
    return times, list(y), exo


def test_rain_arrays_use_hindcast_for_history_and_the_live_run_for_the_future():
    t = np.arange(100.0, 105.0)
    r1, r2 = forecast.rain_arrays(t, {100: (1.0, 2.0), 101: (0.5, 0.0)}, {105: 3.0, 106: 4.0})
    assert r1.shape == (5 + 72,) and r1[0] == 1.0 and r2[0] == 2.0 and np.isnan(r1[2])
    assert r1[5] == 3.0 and r2[5] == 3.0 and r1[6] == 4.0  # future: the latest run fills both leads


def test_star_features_never_use_future_levels():
    times, y, exo = _driven(days=40)
    t, yy = forecast.hourly_grid(times, y)
    ex = forecast.align_exo(t, exo)
    X1 = forecast.star_features(t, yy, None, forecast.trailing_mean(yy, 25), 24, ex)
    yy2 = yy.copy(); yy2[500:] += 5.0  # change the future only
    X2 = forecast.star_features(t, yy2, None, forecast.trailing_mean(yy2, 25), 24, ex)
    assert np.allclose(X1[:500], X2[:500], equal_nan=True)


def test_evaluate_picks_star_when_upstream_and_rain_drive_the_gauge():
    times, y, exo = _driven()
    t, yy = forecast.hourly_grid(times, y)
    ev = forecast.evaluate(t, yy, forecast.align_exo(t, exo))
    assert ev[24]["method"] == "star" and ev[24]["skill_vs_persistence"] > 0.2


def test_star_is_not_made_worse_by_noise_inputs():
    times, vals = _synthetic(days=60)
    rng = np.random.default_rng(7)
    base = int(times[0].timestamp() // 3600)
    noise = {"up": [(times, list(rng.normal(0, 1, len(times))))], "q": None,
             "rain": {"hind": {base + i: (float(rng.random()), float(rng.random())) for i in range(len(times))}, "live": {}}}
    t, yy = forecast.hourly_grid(times, vals)
    ev = forecast.evaluate(t, yy, forecast.align_exo(t, noise))
    # star also carries the tide change and the own trend, so it may win on a tidal gauge; what must not happen is
    # random inputs making the forecast worse than the gauge's own tide model (overfitting)
    for h in (12, 24):
        assert ev[h]["rmse"]["star"] <= 1.05 * ev[h]["rmse"]["tide"]


def test_forecast_station_uses_star_in_the_path_where_it_won():
    times, y, exo = _driven()
    fc = forecast.forecast_station("X", times, y, None, None, exo)
    assert fc["skill"]["24"]["method"] == "star"
    assert fc["path"][23]["method"] == "star" and fc["path"][23]["q"] is not None


def test_upstream_of_follows_the_river_not_the_map():
    chain = forecast._chainage()
    assert forecast.upstream_of("CPY011", chain) == ["CPY008", "C.7A"]   # skips co-located C.35, 30-36 km upstream
    assert forecast.upstream_of("CPY014", chain)[0] == "CPY012"
    assert "C.13" not in forecast.upstream_of("CPY005", chain)             # the dam enters as discharge, not level
    assert forecast.upstream_of("BKK021", chain) == []                    # canal: rain only


def test_star_still_forecasts_when_the_gauge_has_a_short_gap():
    # CPY011 on 2026-09-27: gaps in its own record left the 24 h change undefined at the latest hour, so the live
    # path fell back to tide_trend although star had won the backtest. Short gaps must not disable star.
    times, y, exo = _driven()
    keep = [i for i in range(len(times)) if not (len(times) - 30 <= i < len(times) - 20)]  # a 10 h gap a day ago
    fc = forecast.forecast_station("X", [times[i] for i in keep], [y[i] for i in keep], None, None, exo)
    assert fc["skill"]["24"]["method"] == "star" and fc["path"][23]["method"] == "star"
