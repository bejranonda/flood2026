"""Google Flood Hub (Flood Forecasting API v1; owner 2026-10-04: "I have already Google flood forecasting API … research,
and experiment how can we apply this key"; chose "Validate first, then a 3–7 day outlook", D-087). Shapes copied from the
live answers of 2026-10-04 08:24 UTC (103 HYBAS virtual gauges in Thailand)."""
import datetime as dt

from floodwatch.collectors import parsing

GAUGES = [{"location": {"latitude": 6.44375, "longitude": 101.83542}, "siteName": "", "source": "HYBAS", "river": "",
           "gaugeId": "hybas_4120019660", "qualityVerified": True, "hasModel": True}]
STATUS = [{"gaugeId": "hybas_4121122960", "issuedTime": "2026-10-04T08:24:32.363885Z",
           "forecastTimeRange": {"start": "2026-10-09T00:00:00Z", "end": "2026-10-10T00:00:00Z"}, "forecastTrend": "FALL",
           "severity": "SEVERE", "source": "HYBAS", "gaugeLocation": {"latitude": 14.03542, "longitude": 101.05625},
           "qualityVerified": True, "inundationMapSet": {"inundationMapType": "PROBABILITY"}}]
MODELS = [{"gaugeId": "hybas_4121122960", "thresholds": {"warningLevel": 169.2, "dangerLevel": 216.0, "extremeDangerLevel": 272.9},
           "gaugeValueUnit": "CUBIC_METERS_PER_SECOND", "qualityVerified": True, "gaugeModelId": "7325f4"}]
FORECASTS = {"forecasts": {"hybas_4121122960": {"forecasts": [{"issuedTime": "2026-10-04T08:24:32Z", "forecastRanges": [
    {"forecastStartTime": "2026-10-04T00:00:00Z", "forecastEndTime": "2026-10-05T00:00:00Z", "value": 300.6},
    {"forecastStartTime": "2026-10-05T00:00:00Z", "forecastEndTime": "2026-10-06T00:00:00Z", "value": 293.8}]}]}}}


def test_gauges_statuses_thresholds_and_forecasts_parse_to_rows():
    g = parsing.parse_gfh_gauges(GAUGES)
    assert g == [{"gauge_id": "hybas_4120019660", "lat": 6.44375, "lon": 101.83542, "source": "HYBAS",
                  "quality_verified": True, "has_model": True}]
    s = parsing.parse_gfh_status(STATUS)[0]
    assert s["severity"] == "SEVERE" and s["trend"] == "FALL" and s["inundation"] == "PROBABILITY"
    assert s["issued_time"] == dt.datetime(2026, 10, 4, 8, 24, 32, 363885, tzinfo=dt.timezone.utc)
    assert s["range_start"] == dt.datetime(2026, 10, 9, tzinfo=dt.timezone.utc)
    m = parsing.parse_gfh_models(MODELS)[0]
    assert (m["warning"], m["danger"], m["extreme"], m["unit"]) == (169.2, 216.0, 272.9, "CUBIC_METERS_PER_SECOND")
    f = parsing.parse_gfh_forecasts(FORECASTS)
    assert [(r["start_time"].day, r["value"]) for r in f] == [(4, 300.6), (5, 293.8)] and f[0]["gauge_id"] == "hybas_4121122960"


def test_flood_hub_runs_every_6_h_in_the_collector_loop():
    from floodwatch import worker
    assert dict(worker.TASKS)["google_floodhub"] == 6 * 3600
