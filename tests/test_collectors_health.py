"""The collector wrapper's health bookkeeping (2026-10-05: hii_dams_history returns a count of dam-days; _run passed it as
the data time, the success write failed on the timestamp column and every run was recorded as a failure)."""
import datetime as dt

from floodwatch import collectors


def test_a_collector_that_returns_a_count_is_recorded_as_a_success_without_a_data_time(monkeypatch):
    calls = []
    monkeypatch.setattr(collectors.db, "record_health", lambda source, ok, error=None, data_time=None: calls.append((source, ok, data_time)))
    collectors._run("hii_dams_history", lambda: 16160)
    assert calls == [("hii_dams_history", True, None)]
    t = dt.datetime(2026, 10, 5, 16, tzinfo=dt.timezone.utc)
    calls.clear()
    collectors._run("hii_dams", lambda: t)
    assert calls == [("hii_dams", True, t)]


def test_older_river_months_become_daily_means_of_thai_days_from_good_readings_only():
    obs = [{"obs_time": dt.datetime(2024, 9, 30, 17, 0, tzinfo=dt.timezone.utc), "level_msl": 2.0, "discharge": 10.0, "quality_flag": "ok"},
           {"obs_time": dt.datetime(2024, 9, 30, 18, 0, tzinfo=dt.timezone.utc), "level_msl": 4.0, "discharge": None, "quality_flag": "ok"},
           {"obs_time": dt.datetime(2024, 9, 30, 19, 0, tzinfo=dt.timezone.utc), "level_msl": 99.0, "discharge": 30.0, "quality_flag": "out_of_range"},
           {"obs_time": dt.datetime(2024, 9, 30, 16, 0, tzinfo=dt.timezone.utc), "level_msl": 8.0, "discharge": None, "quality_flag": "ok"}]
    h, q = collectors.daily_means(obs)
    assert h == {"2024-10-01": 3.0, "2024-09-30": 8.0}  # 17:00 UTC = 00:00 on 1 Oct in Thailand; the flagged reading left out
    assert q == {"2024-10-01": 20.0}  # discharge: every reported value of the day
