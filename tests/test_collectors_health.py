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
