"""One trend rule for the whole app (owner 2026-10-04: "Forecast if sure direction: higher, lower, stable. ไม่แน่ชัด can
suggest with measured recent change as fallback … show two labels as summary"; D-083). Groups: "rising" (น้ำยังขึ้น)
and "flat_or_falling" (ทรงตัวหรือลดลง)."""
from floodwatch import status

UP = {"dir": "rising", "level": "rise", "method": "star", "likely": [0.03, 0.12], "wide": False}
DOWN = {"dir": "falling", "level": "fall", "method": "recent", "likely": [-0.15, -0.04], "wide": False}
STEADY = {"dir": "steady", "level": "steady", "method": "persistence", "likely": [-0.02, 0.03], "wide": False}
UNSURE = {"dir": "steady", "level": "steady", "method": "persistence", "likely": [-0.10, 0.12], "wide": False}
UNSURE_UP, UNSURE_DOWN = {**UNSURE, "median": 0.03}, {**UNSURE, "median": -0.03}
PERSIST_UP = {"dir": "rising", "level": "rise", "method": "persistence", "likely": [0.01, 0.2], "wide": False}
OBS_UP = {"change_cm": 30, "hours": 24, "level": "strong_rise", "change6_cm": 5.0}
OBS_STOPPED = {"change_cm": 30, "hours": 24, "level": "strong_rise", "change6_cm": -1.0}
OBS_DOWN = {"change_cm": -12, "hours": 24, "level": "fall", "change6_cm": -2.0}


def g(ch=None, obs=None, stale=False, ch12=None):
    return status.trend({"change24": ch, "change12": ch12, "observed24": obs, "stale": stale})


def test_a_sure_forecast_decides():
    assert g(UP, OBS_DOWN) == {"group": "rising", "forecast": "up", "measured": "down", "basis": "forecast"}
    assert g(DOWN, OBS_UP)["group"] == "flat_or_falling"
    assert g(STEADY, OBS_UP) == {"group": "flat_or_falling", "forecast": "steady", "measured": "up", "basis": "forecast"}


def test_an_unsure_forecast_falls_back_to_the_measured_recent_change():
    assert g(UNSURE, OBS_UP) == {"group": "rising", "forecast": "unsure", "measured": "up", "basis": "measured"}
    assert g(PERSIST_UP, OBS_DOWN)["group"] == "flat_or_falling"  # "no change" model rows are not a proven direction
    assert g(None, OBS_UP)["forecast"] is None and g(None, OBS_UP)["group"] == "rising"


def test_a_rise_that_stopped_in_the_last_6_h_is_not_rising():
    # the model's own "recent" rule: the smaller of the 24 h and 6 h pace, none when they disagree (Kgt.19A)
    assert g(UNSURE, OBS_STOPPED)["measured"] == "steady" and g(UNSURE, OBS_STOPPED)["group"] == "flat_or_falling"


def test_no_trend_without_data_or_when_stale():
    assert g(None, None) is None
    assert g(UP, OBS_UP, stale=True) is None


def test_the_12_h_row_is_used_when_there_is_no_24_h_row():
    assert g(None, OBS_DOWN, ch12=UP)["group"] == "rising"


# --- v0.24.0: a "? ไม่แน่ชัด" row leans by the measured pace (owner 2026-10-04: "Lean the rows by the trend") ----------
def test_an_unsure_row_leans_by_the_measured_pace_and_a_sure_row_never_does():
    assert status.lean(UNSURE_UP, OBS_UP) == "up" and status.lean(UNSURE_DOWN, OBS_DOWN) == "down"
    assert status.lean(UNSURE_UP, OBS_STOPPED) is None       # the last 6 h stopped: no lean (same rule as the groups)
    assert status.lean(UP, OBS_DOWN) is None and status.lean(STEADY, OBS_UP) is None
    assert status.lean(UNSURE, None) is None and status.lean(None, OBS_UP) is None


def test_a_row_leans_only_where_the_chart_line_goes_the_same_way():
    # owner 2026-10-04 (BKK017: "↘ น่าจะลดลง" beside "0 ถึง +8 ซม." and a rising dashed line; T.13: a flat line): lean only
    # when the model's median (the chart's dashed line) visibly moves >= 3 cm the measured way; backtest: right 82.9/80.3/82.3 %
    up_line = {**UNSURE, "median": 0.04}
    flat_line = {**UNSURE, "median": 0.0}
    assert status.lean(up_line, OBS_UP) == "up"
    assert status.lean(up_line, OBS_DOWN) is None        # BKK017: measured down, chart up → "?"
    assert status.lean(flat_line, OBS_DOWN) is None      # T.13: chart flat → "?"
    assert status.lean({**UNSURE, "median": -0.04}, OBS_DOWN) == "down"
    assert status.lean({**UNSURE, "median": -0.01}, OBS_DOWN) is None   # T.13 at 72 h: a 1 cm move is not visible
