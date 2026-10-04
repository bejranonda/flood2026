from floodwatch import worker


def test_backoff_grows_with_consecutive_failures_and_is_capped():
    assert [worker.backoff_factor(n) for n in (0, 1, 2)] == [1, 1, 1]
    assert [worker.backoff_factor(n) for n in (3, 4, 5, 6, 20)] == [2, 4, 6, 6, 6]


def test_core_telemetry_backs_off_at_most_twofold():
    cap = worker.BACKOFF_CAP["hii_waterlevel"]
    assert max(worker.backoff_factor(n, cap) for n in range(0, 50)) == 2
    assert worker.BACKOFF_CAP.get("traffy", 6) == 6


def test_hii_history_never_asks_hii_for_bma_stations():
    # 2026-09-26: the 199 BMA gauges (WL.*, no hii_id) were sent to HII's chart endpoint, HTTP 500 x3 retries each,
    # and starved the single worker loop for 30+ minutes. The query must exclude agency BMA.
    import inspect
    from floodwatch import collectors
    src = inspect.getsource(collectors.hii_history)
    assert "agency IS DISTINCT FROM 'BMA'" in src


def test_collectors_never_wait_for_forecasts():
    collector = {n for n, _ in worker.tasks_for("collector")}
    forecaster = {n for n, _ in worker.tasks_for("forecaster")}
    assert "forecast" not in collector and "upstream_learn" not in collector
    assert forecaster == {"forecast", "upstream_learn", "risk_record", "dwr_ews"}  # long jobs live here (gistda_flood: D-071)
    assert "hii_waterlevel" in collector and "retention" in collector


def test_only_the_collector_changes_the_schema():
    # 2026-09-30 20:25 UTC: both containers ran init_schema at start; the forecaster's ALTER TABLE station deadlocked
    # with the collector's observation insert. One owner; the forecaster waits for the tables instead.
    assert worker.owns_schema("collector") and not worker.owns_schema("forecaster")


def test_rain_cells_are_fetched_at_start_not_three_hours_later():
    # 2026-09-30: after each restart the nationwide rain cells waited a full interval; pins read "ยังไม่มีข้อมูลฝน"
    assert {"openmeteo_cells", "openmeteo_prev_cells"} <= set(worker.FIRST_RUN["collector"])
    fr = worker.FIRST_RUN["forecaster"]  # forecast after upstream_learn; slow downloads (DWR) never delay it
    assert fr.index("upstream_learn") < fr.index("forecast") < fr.index("dwr_ews")


def test_upstream_gauges_are_relearned_daily():
    # the first learn after a deploy sees only days of nationwide history; a weekly cycle left star without inputs
    assert dict(worker.FORECASTER_TASKS)["upstream_learn"] <= 24 * 3600


def test_bangkok_fine_rain_is_collected_hourly_and_at_start():
    assert dict(worker.TASKS)["openmeteo_fine"] == 3600 and "openmeteo_fine" in worker.FIRST_RUN["collector"]


def test_upstream_is_relearned_at_start_when_empty_or_a_day_old():
    # 2026-10-01: learned once with 4 days of history ({}); every restart skipped it ({} is "not None") and reset the
    # daily timer, so nationwide gauges never got their learned upstream inputs
    import datetime as dt
    now = dt.datetime(2026, 10, 1, 14, tzinfo=dt.timezone.utc)
    assert worker.upstream_due(None, None, now)
    assert worker.upstream_due({}, now - dt.timedelta(hours=1), now)  # empty: learn again
    assert worker.upstream_due({"X": [["Y", 6, 0.8]]}, now - dt.timedelta(hours=25), now)
    assert not worker.upstream_due({"X": [["Y", 6, 0.8]]}, now - dt.timedelta(hours=2), now)


def test_basin_and_river_maps_are_refreshed_weekly_and_at_start():
    assert dict(worker.TASKS)["hii_geo"] == 7 * 24 * 3600 and "hii_geo" in worker.FIRST_RUN["collector"]


def test_risk_record_runs_daily_in_the_forecaster_after_the_forecast():
    # v0.21.0 (D-077): the จับตา tab's "6 ใน 10" records come from the forecast archive, recomputed daily
    assert dict(worker.FORECASTER_TASKS)["risk_record"] == 24 * 3600
    f = worker.FIRST_RUN["forecaster"]
    assert f.index("risk_record") > f.index("forecast")


def test_dwr_posts_are_archived_every_30_min_in_the_forecaster():
    # one 3 MB request through the Thai egress takes ~45 s: never in the 10-min collector loop
    assert dict(worker.FORECASTER_TASKS)["dwr_ews"] == 1800 and "dwr_ews" in worker.FIRST_RUN["forecaster"]




def test_gistda_is_gone_from_the_schedule_and_the_collectors():
    # owner 2026-10-04: "The satellite cell-info for flood showed in App is not so correct, and might mislead" →
    # "Hide everywhere and stop the collector" (D-084)
    from floodwatch import collectors
    assert "gistda_flood" not in dict(worker.FORECASTER_TASKS) and "gistda_flood" not in worker.FIRST_RUN["forecaster"]
    assert not hasattr(collectors, "gistda_flood")
