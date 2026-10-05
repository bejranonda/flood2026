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
    # 90 days: since STAR_INPUTS 2 the 30-day mean needs 15 days of readings, so star trains only with ~90 days of history
    times, vals = _synthetic(days=90)
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


def test_trailing_mean_vectorised_matches_the_reference_loop():
    def ref(y, w, centered=False):  # the original per-element implementation
        out = np.full(len(y), np.nan)
        for i in range(len(y)):
            lo, hi = (i - w // 2, i + w // 2 + 1) if centered else (i - w + 1, i + 1)
            seg = y[max(0, lo):min(len(y), hi)]
            seg = seg[np.isfinite(seg)]
            if len(seg) >= w // 2:
                out[i] = seg.mean()
        return out
    rng = np.random.default_rng(5)
    y = rng.normal(0, 1, 2000); y[rng.random(2000) < 0.3] = np.nan; y[100:160] = np.nan
    for centered in (False, True):
        assert np.allclose(forecast.trailing_mean(y, 25, centered), ref(y, 25, centered), equal_nan=True)


# --- v0.16 (D-064): a daily cached backtest; the 30-min run only applies it --------------------------------------
def test_a_cached_backtest_gives_the_same_forecast_as_a_fresh_one():
    times, y, exo = _driven()
    fresh = forecast.forecast_station("X", times, y, None, None, exo)
    cached = forecast.ev_from_json(json.loads(json.dumps(fresh["skill"])))  # as stored in forecast_model (jsonb)
    again = forecast.forecast_station("X", times, y, None, None, exo, ev=cached)
    assert again["path"] == fresh["path"] and again["skill"] == fresh["skill"]


def test_a_gauge_without_rain_history_still_gets_a_forecast():
    times, vals = _synthetic(days=30)
    fc = forecast.forecast_station("X", times, vals, 2.0, None, None)  # load_exo returned None (no hindcast yet)
    assert fc and len(fc["path"]) == 72


def test_cached_backtests_expire_after_a_day_or_when_history_grows():
    now = dt.datetime(2026, 10, 1, 12, tzinfo=dt.timezone.utc)
    row = {"trained_at": now - dt.timedelta(hours=5), "n_rows": 1000}
    assert forecast.model_is_fresh(row, 1100, now)
    assert not forecast.model_is_fresh(row, 1300, now)  # a backfill added history: backtest again
    assert not forecast.model_is_fresh({**row, "trained_at": now - dt.timedelta(hours=21)}, 1000, now)
    assert not forecast.model_is_fresh(None, 1000, now)


def test_star_takes_extra_known_at_issue_columns_and_is_unchanged_without_them():
    # v0.16.5 experiment hook (Q43): measured-rain features enter as extra columns aligned to the hourly grid
    times, y, exo = _driven(days=40)
    t, yy = forecast.hourly_grid(times, y)
    ex = forecast.align_exo(t, exo)
    base = forecast.star_features(t, yy, None, forecast.trailing_mean(yy, 25), 12, ex)
    extra = np.arange(len(t), dtype=float)
    more = forecast.star_features(t, yy, None, forecast.trailing_mean(yy, 25), 12, {**ex, "extra": [extra]})
    assert more.shape[1] == base.shape[1] + 1 and np.allclose(more[:, -1], extra)
    assert np.allclose(base, forecast.star_features(t, yy, None, forecast.trailing_mean(yy, 25), 12, {**ex, "extra": []}), equal_nan=True)


# --- v0.21.0 (D-077): the จับตา tab needs the bank chance over 24 h and 48 h --------------------------------------
def test_bank_chance_bands_over_a_window():
    from floodwatch.forecast import bank_chance
    path = [{"h": h, "q": [1.0, 1.1, 1.2, 1.3, 1.4 + (0.5 if h == 40 else 0)], "method": "star"} for h in range(1, 49)]
    assert bank_chance(path, 1.25, 24) == "25-50%"
    assert bank_chance(path, 1.85, 24) == "<5%" and bank_chance(path, 1.85, 48) == "5-25%"
    assert bank_chance(path, 1.15, 48) == ">50%" and bank_chance(path, None, 24) is None


# --- v0.20.7: one forecaster (owner 2026-10-03: "Why trend and model forecast in the chart are different? … I thought
# the trend were calculated by the model"). The recent-pace rule is a method of the model, not an override beside it.
def test_recent_pace_is_the_smaller_of_24_and_6_h_and_none_when_they_disagree():
    from floodwatch.forecast import recent_rate
    import numpy as np
    step = np.concatenate([np.full(20, 15.78), np.linspace(15.78, 16.5, 7), np.full(12, 16.6)])   # jump, then flat
    assert abs(recent_rate(step, len(step) - 1)) < 0.003                                           # m/h: stopped
    steady_fall = 2.0 - 0.01 * np.arange(40)                                                       # 1 cm/h for 40 h
    assert abs(recent_rate(steady_fall, 39) + 0.01) < 1e-6
    turned = np.concatenate([1.0 + 0.01 * np.arange(30), 1.29 - 0.01 * np.arange(1, 8)])
    assert recent_rate(turned, len(turned) - 1) == 0.0


def test_recent_competes_in_the_backtest_and_wins_on_a_gauge_that_keeps_draining():
    from floodwatch.forecast import evaluate
    import numpy as np
    n = 24 * 60
    t = np.arange(n, dtype=float)
    rng = np.random.default_rng(1)
    # slow drains that stop and restart (a canal after rain): persistence lags, the recent pace follows
    y = np.cumsum(np.where((t // 72) % 2 == 0, -0.004, 0.0)) + rng.normal(0, 0.002, n) + 3.0
    ev = evaluate(t, y)
    assert "recent" in ev[24]["rmse"]
    assert ev[24]["rmse"]["recent"] < ev[24]["rmse"]["persistence"]


def test_a_cached_backtest_without_the_recent_method_is_redone():
    # v0.20.7: "recent" joined the ladder; a backtest stored before it would keep serving yesterday's choice for ~20 h
    import datetime as dt
    from floodwatch.forecast import model_is_fresh
    now = dt.datetime(2026, 10, 3, 20, tzinfo=dt.timezone.utc)
    old = {"trained_at": now - dt.timedelta(hours=1), "n_rows": 1000,
           "payload": {"24": {"method": "persistence", "rmse": {"persistence": 0.1, "trend": 0.12}}}}
    from floodwatch.forecast import STAR_INPUTS
    new = {**old, "payload": {"24": {"method": "recent", "rmse": {"persistence": 0.1, "recent": 0.08}, "star_inputs": STAR_INPUTS}}}
    assert not model_is_fresh(old, 1000, now) and model_is_fresh(new, 1000, now)


def test_star_reads_the_7_and_30_day_means_and_the_1_3_72_h_changes():
    # Q52 step 3 (owner 2026-10-04: "improve the model forecasting performance … not fake the result"): on gauges the
    # choice never saw, these inputs cut the served error vs "no change" from −5.3…−6.6 % to −8.3…−9.4 % at 24–72 h
    # (research/2026-10-04_star_variants*.py, _star_selection*.py)
    times, y, exo = _driven(days=60)
    t, yy = forecast.hourly_grid(times, y)
    X = forecast.star_features(t, yy, None, forecast.trailing_mean(yy, 25), 24, forecast.align_exo(t, exo))
    assert np.allclose(X[:, 4], yy - forecast.trailing_mean(yy, 24 * 7), equal_nan=True)
    assert np.allclose(X[:, 5], yy - forecast.trailing_mean(yy, 24 * 30), equal_nan=True)
    for col, k in ((6, 1), (7, 3), (8, 72)):
        assert np.allclose(X[:, col], forecast._lagdiff(yy, k), equal_nan=True)


def test_a_cached_backtest_from_older_star_inputs_is_redone():
    # the live star must use the inputs its backtest (and so its band) was made with
    import datetime as dt
    now = dt.datetime(2026, 10, 4, 18, tzinfo=dt.timezone.utc)
    row = {"trained_at": now - dt.timedelta(hours=1), "n_rows": 1000,
           "payload": {"24": {"method": "star", "rmse": {"persistence": 0.1, "recent": 0.09, "star": 0.08}}}}
    assert not forecast.model_is_fresh(row, 1000, now)
    row["payload"]["24"]["star_inputs"] = forecast.STAR_INPUTS
    assert forecast.model_is_fresh(row, 1000, now)
    assert forecast.evaluate(*forecast.hourly_grid(*_synthetic(days=30)))[24]["star_inputs"] == forecast.STAR_INPUTS


def test_widen90_scales_only_the_90_band_around_the_median_by_horizon_and_kind():
    path = [{"h": h, "method": "star" if h > 12 else "persistence", "q": [0.8, 0.9, 1.0, 1.1, 1.2]} for h in (12, 24, 48, 72)]
    f = {"24": {"model": 1.2, "no change": 1.4}, "48": {"model": 1.5, "no change": 1.5}, "72": {"model": 2.0, "no change": 2.0}}
    out = forecast.widen90(path, f)
    by = {p["h"]: p["q"] for p in out}
    assert by[24] == [0.76, 0.9, 1.0, 1.1, 1.24] and by[72] == [0.6, 0.9, 1.0, 1.1, 1.4]
    assert by[12] == [0.76, 0.9, 1.0, 1.1, 1.24]  # 12 h: half way from 1.0 to the 24 h "no change" factor 1.4 -> 1.2
    assert forecast.widen90(path, None) == path


def test_flood_hub_change_uses_only_forecasts_issued_before_the_hour():
    # Q55 (owner 2026-10-05: "Yes", D-097): the forecast's relative discharge change from the issue day to the target day,
    # from the latest Flood Hub forecast issued at or before each hour (research/2026-10-04_floodhub_input.log)
    import datetime as dt
    utc = dt.timezone.utc
    day = lambda d: dt.datetime(2026, 10, 1, tzinfo=utc) + dt.timedelta(days=d)
    rows = [{"issued_time": day(0) + dt.timedelta(hours=14), "start_time": day(k), "value": 100.0 + 10 * k} for k in range(-2, 6)]
    rows += [{"issued_time": day(1) + dt.timedelta(hours=14), "start_time": day(1 + k), "value": 300.0} for k in range(-2, 6)]
    m = forecast.gfh_matrix(rows)
    t = np.array([day(0).timestamp() / 3600 + 20, day(1).timestamp() / 3600 + 10, day(1).timestamp() / 3600 + 20])
    x = forecast.gfh_change(t, m, 24)
    assert abs(x[0] - np.log(111 / 101)) < 1e-9          # 1 Oct 20:00 → the 1 Oct forecast, day 0 → day 1
    assert abs(x[1] - np.log(121 / 111)) < 1e-9          # 2 Oct 10:00: the 2 Oct forecast (issued 14:00) is not known yet
    assert abs(x[2]) < 1e-9                              # 2 Oct 20:00 → the 2 Oct forecast (flat 300)
    assert np.isnan(forecast.gfh_change(np.array([day(0).timestamp() / 3600]), m, 24)[0])  # before any forecast


def test_star_reads_flood_hub_only_where_a_point_is_near():
    times, y, exo = _driven(days=90)
    t, yy = forecast.hourly_grid(times, y)
    ex = forecast.align_exo(t, exo)
    base = forecast.star_features(t, yy, None, forecast.trailing_mean(yy, 25), 24, ex)
    rows = [{"issued_time": times[i], "start_time": times[i] + forecast.dt.timedelta(days=k), "value": 50.0 + k}
            for i in range(0, len(times), 24) for k in range(-2, 6)]
    more = forecast.star_features(t, yy, None, forecast.trailing_mean(yy, 25), 24, {**ex, "gfh": forecast.gfh_matrix(rows)})
    assert more.shape[1] == base.shape[1] + 1
    pts = [("g1", 14.00, 100.00), ("g2", 15.0, 100.0)]
    assert forecast.nearest_gfh(14.05, 100.0, pts) == "g1" and forecast.nearest_gfh(14.2, 100.0, pts) is None  # 10 km
