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
    assert forecaster == {"forecast", "upstream_learn", "gistda_flood"}  # long jobs live here (gistda_flood: D-071)
    assert "hii_waterlevel" in collector and "retention" in collector


def test_only_the_collector_changes_the_schema():
    # 2026-09-30 20:25 UTC: both containers ran init_schema at start; the forecaster's ALTER TABLE station deadlocked
    # with the collector's observation insert. One owner; the forecaster waits for the tables instead.
    assert worker.owns_schema("collector") and not worker.owns_schema("forecaster")


def test_rain_cells_are_fetched_at_start_not_three_hours_later():
    # 2026-09-30: after each restart the nationwide rain cells waited a full interval; pins read "ยังไม่มีข้อมูลฝน"
    assert {"openmeteo_cells", "openmeteo_prev_cells"} <= set(worker.FIRST_RUN["collector"])
    fr = worker.FIRST_RUN["forecaster"]  # forecast after upstream_learn; the satellite download never delays it
    assert fr.index("upstream_learn") < fr.index("forecast") < fr.index("gistda_flood")


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


def test_satellite_cells_are_checked_hourly_but_downloaded_at_most_every_20_hours():
    # Q45 (D-071): GISTDA's 7-day layer is ~300 MB and rebuilt daily; restarts must not download it again
    import datetime as dt
    from floodwatch import collectors
    # the download held the collector loop ~7 min (2026-10-03 06:16-06:23 UTC): it runs beside the forecasts instead,
    # so the 10-min collectors never wait (D-064)
    assert dict(worker.FORECASTER_TASKS)["gistda_flood"] == 3600 and "gistda_flood" in worker.FIRST_RUN["forecaster"]
    assert "gistda_flood" not in dict(worker.TASKS) and "gistda_flood" not in worker.FIRST_RUN["collector"]
    now = dt.datetime(2026, 10, 3, 6, tzinfo=dt.timezone.utc)
    assert collectors.gistda_due(None, now)
    assert not collectors.gistda_due(now - dt.timedelta(hours=19), now)
    assert collectors.gistda_due(now - dt.timedelta(hours=20), now)
