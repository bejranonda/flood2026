"""Task 1 (v0.16, D-064): history for every HII-network gauge, bounded by a retention that never touches BMA."""
import inspect

from floodwatch import collectors, retention


def test_history_slices_cover_every_gauge_once_over_six_runs():
    codes = [f"G{i:03d}" for i in range(733)]
    seen = [c for run in range(6) for c in collectors.history_slice(codes, run)]
    assert sorted(seen) == codes  # each gauge refilled once a day (6 runs x 6 h), none twice
    assert max(len(collectors.history_slice(codes, r)) for r in range(6)) <= 123
    assert collectors.history_slice(codes, 6) == collectors.history_slice(codes, 0)


class FakeConn:
    """Captures statements; each DELETE reports the next rowcount from `counts`."""
    def __init__(self, counts):
        self.counts, self.calls, self.commits = list(counts), [], 0

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        n = self.counts.pop(0) if self.counts else 0
        return type("Cur", (), {"rowcount": n})()

    def commit(self):
        self.commits += 1


def test_retention_keeps_bma_and_400_days_and_deletes_in_batches():
    c = FakeConn([retention.BATCH, 10, 0])  # observation: a full batch, then a partial one; weather: nothing
    out = retention.run(c)
    obs = [(s, p) for s, p in c.calls if "FROM observation" in s]
    assert len(obs) == 2  # stops after a partial batch
    sql, p = obs[0]
    assert "agency IS DISTINCT FROM 'BMA'" in sql  # BMA relay history is not re-fetchable (KI-218)
    assert p["days"] == retention.OBS_KEEP_DAYS == 400 and p["batch"] == retention.BATCH
    assert out == {"observation": retention.BATCH + 10, "weather_forecast": 0, "forecast_run": 0, "rain_obs": 0, "dwr_obs": 0}
    assert c.commits >= 2  # short transactions: one per batch


def test_retention_drops_old_weather_forecast_issues_only():
    c = FakeConn([0, 5])
    retention.run(c)
    sql, p = [(s, p) for s, p in c.calls if "weather_forecast" in s][0]
    assert "issue_time <" in sql and p["days"] == retention.WF_KEEP_DAYS == 3


def test_history_collectors_cover_the_whole_hii_network():
    for fn in (collectors.hii_backfill, collectors.hii_history):
        src = inspect.getsource(fn)
        assert "WHERE in_focus" not in src and "WHERE in_focus AND" not in src


def test_health_ignores_future_stamped_and_flagged_rows():
    from floodwatch import api
    src = inspect.getsource(api.health)
    assert "quality_flag='ok'" in src and "now() + interval '15 minutes'" in src  # KI-247


def test_forecast_runs_are_thinned_after_two_days_and_dropped_after_fourteen():
    sql = retention.FC_SQL
    assert "forecast_run" in sql and "%(keep_all_days)s" in sql and "%(days)s" in sql
    assert retention.FC_KEEP_ALL_DAYS == 2 and retention.FC_KEEP_DAYS == 14


def test_rain_gauge_readings_are_bounded_too():
    # 4,651 gauges x 24 readings a day. Hourly rain cannot be fetched again from HII (only the last 24 h is public),
    # so gauges near a water gauge (model inputs, Q43) keep a year; the others two weeks (panel only reads 3 h)
    assert "rain_obs" in retention.RAIN_SQL and retention.RAIN_KEEP_DAYS == 14 and retention.RAIN_MODEL_KEEP_DAYS == 400
    assert "NOT EXISTS (SELECT 1 FROM station" in retention.RAIN_SQL and "%(model_days)s" in retention.RAIN_SQL


def test_dwr_readings_are_kept_400_days_because_dwr_serves_only_11_hours():
    # 2026-10-03: ews.dwr.go.th's chart gives the last ~11 h; our archive is the only history
    assert retention.DWR_KEEP_DAYS == 400 and "dwr_obs" in inspect.getsource(retention.run)
