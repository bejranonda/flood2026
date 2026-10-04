"""Bounded history (D-064): a year of history for every gauge, never an ever-growing table.

HII-network readings older than OBS_KEEP_DAYS are deleted: HII serves them again (`waterlevel_graph`, one year).
BMA readings are never deleted: the flood69 relay keeps no history, so ours is the only copy (KI-218).
Old rain-forecast issues are deleted after WF_KEEP_DAYS: only the latest issue is read; training uses
`rain_hindcast`. Forecast runs are thinned after FC_KEEP_ALL_DAYS and dropped after FC_KEEP_DAYS. Deletes run in small batches so no statement holds locks for long (KI-246).
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

OBS_KEEP_DAYS = 400  # the one-year training window (forecast.LOOKBACK_DAYS = 370) plus a margin
WF_KEEP_DAYS = 3
FC_KEEP_ALL_DAYS = 2  # every 30-min forecast run for 2 days ...
FC_KEEP_DAYS = 31     # ... then one run per gauge every 6 h (hh:00-hh:29 at 00/06/12/18 UTC) up to 31 days: the track
                      # records read 30 days (risks.WINDOW_DAYS; was 14 until v0.25.2, KI-290) and
                      # scripts/score_hii_forecast.py; ~4.6 KB a run -> ~0.5 GB for the thinned month
RAIN_KEEP_DAYS = 14  # rain-gauge readings (rain_obs) far from any water gauge: the panel reads only the last 3 h
RAIN_MODEL_KEEP_DAYS = 400  # gauges within ~10 km of a water gauge: hourly rain is not re-fetchable (model input, Q43)
RAIN_NEAR_DEG = 0.09  # ~10 km box around a water gauge
DWR_KEEP_DAYS = 400  # DWR serves ~11 h of history (2026-10-03): our archive is the only one
BATCH = 50_000

OBS_SQL = """DELETE FROM observation WHERE ctid IN (
  SELECT o.ctid FROM observation o JOIN station s USING (code)
  WHERE s.agency IS DISTINCT FROM 'BMA' AND o.obs_time < now() - make_interval(days => %(days)s)
  LIMIT %(batch)s)"""
WF_SQL = """DELETE FROM weather_forecast WHERE ctid IN (
  SELECT ctid FROM weather_forecast WHERE issue_time < now() - make_interval(days => %(days)s) LIMIT %(batch)s)"""

RAIN_SQL = """DELETE FROM rain_obs WHERE ctid IN (
  SELECT r.ctid FROM rain_obs r WHERE r.obs_time < now() - make_interval(days => %(model_days)s)
     OR (r.obs_time < now() - make_interval(days => %(days)s)
         AND NOT EXISTS (SELECT 1 FROM station s WHERE s.lat IS NOT NULL
                         AND abs(s.lat - r.lat) < %(near)s AND abs(s.lon - r.lon) < %(near)s))
  LIMIT %(batch)s)"""
DWR_SQL = """DELETE FROM dwr_obs WHERE ctid IN (
  SELECT ctid FROM dwr_obs WHERE obs_time < now() - make_interval(days => %(days)s) LIMIT %(batch)s)"""
FC_SQL = """DELETE FROM forecast_run WHERE id IN (
  SELECT id FROM forecast_run WHERE issue_time < now() - make_interval(days => %(keep_all_days)s)
  AND (issue_time < now() - make_interval(days => %(days)s)
       OR NOT (extract(hour FROM issue_time)::int %% 6 = 0 AND extract(minute FROM issue_time) < 30))
  LIMIT %(batch)s)"""


def _drain(c, sql: str, days: int, **extra) -> int:
    total = 0
    while True:
        n = c.execute(sql, {"days": days, "batch": BATCH, **extra}).rowcount or 0
        c.commit()
        total += n
        if n < BATCH:
            return total


def run(c) -> dict:
    out = {"observation": _drain(c, OBS_SQL, OBS_KEEP_DAYS), "weather_forecast": _drain(c, WF_SQL, WF_KEEP_DAYS),
           "forecast_run": _drain(c, FC_SQL, FC_KEEP_DAYS, keep_all_days=FC_KEEP_ALL_DAYS),
           "rain_obs": _drain(c, RAIN_SQL, RAIN_KEEP_DAYS, model_days=RAIN_MODEL_KEEP_DAYS, near=RAIN_NEAR_DEG),
           "dwr_obs": _drain(c, DWR_SQL, DWR_KEEP_DAYS)}
    log.info("retention: deleted %s", out)
    return out
