"""Single-process scheduler: collectors, forecasts and a disk guard on fixed intervals.

Run: python -m floodwatch.worker                     (collectors, QC, retention)
     python -m floodwatch.worker --role forecaster  (forecasts and learned upstream gauges, own container, D-064)
"""
from __future__ import annotations

import datetime as dt
import logging
import time

from floodwatch import ai, archive, collectors, db, forecast, qc, retention
from floodwatch.config import settings

log = logging.getLogger("floodwatch.worker")

# (task, interval seconds). Polite: never faster than the source updates (GUIDELINES §5).
TASKS = [
    ("hii_waterlevel", 600),
    ("traffy", 600),
    ("bma_klong", 600),  # BMA khlong gauges via the flood69 relay (relay refreshes every 5 min)
    ("qc", 600),  # dropouts and erratic (pump-affected) gauges over the last 24 h (KI-237)
    ("hii_rain", 900),  # every 15 min, every province (v0.16.3): measured rain in the panel during a downpour
    ("openmeteo", 3600),
    ("hii_stations", 6 * 3600),
    ("hii_history", 6 * 3600),
    ("hii_backfill", 600),  # a few stations per run until the 1-year backfill is complete (D-018)
    ("bma_dds", 3 * 3600),
    ("hii_fews_forecast", 3 * 3600),
    ("openmeteo_prev", 24 * 3600),
    ("openmeteo_cells", 3 * 3600),  # rain forecast for the 0.5° cells of gauges outside the focus area (D-064)
    ("openmeteo_prev_cells", 3600),
    ("openmeteo_fine", 3600),
    ("hii_geo", 7 * 24 * 3600),  # HII basin + main-river map files: basin22, river and river system per gauge (v0.17)  # Bangkok region at the model's ~8 km grid, for pins and region lines (Q42, v0.16.4)  # their rain history: a year for 8 new cells per run, then 4 days daily
    ("bma_history", 600),  # BMA canal history from HII: backfill 5 gauges per run, then a daily 3-day refresh (D-054)  # rain as forecast 1-2 days earlier: training data for the star model (D-052)  # HII official forecast files, new issue ~daily (D-050)
    ("ai_triage", 900),  # optional Workers AI labels for feedback notes; a no-op when AI is unavailable
    ("disk", 3600),
    ("retention", 24 * 3600),  # HII-network readings older than 400 days, rain-forecast issues older than 3 days (D-064)
]

# The forecaster runs in its own container (D-064): ~1,000 gauges take minutes, and the 10-min collectors must never
# wait for them (the forecast of 277 gauges held the single loop ~4.5 min on 2026-09-30).
FORECASTER_TASKS = [
    ("forecast", 1800),
    ("upstream_learn", 24 * 3600),  # upstream gauges learned per basin for gauges off the Chao Phraya chain (daily: history grows)
    # satellite-flooded cells (GISTDA 7-day layer, D-071): checked hourly, downloaded <= every 20 h; ~7 min per download,
    # so it lives here, never in the collector loop
    ("gistda_flood", 3600),
    ("risk_record", 24 * 3600),  # track records of the จับตา groups ("6 ใน 10") from the forecast archive (D-077)
]


# First run order at start: latest values -> history -> weather (rain cells too, or pins wait 3 h for rain).
FIRST_RUN = {
    "collector": ("hii_waterlevel", "hii_stations", "hii_history", "hii_backfill", "openmeteo", "openmeteo_prev",
                  "openmeteo_cells", "openmeteo_prev_cells", "openmeteo_fine", "hii_geo", "traffy", "bma_klong", "qc", "hii_rain", "disk"),
    "forecaster": ("upstream_learn", "forecast", "risk_record", "gistda_flood"),  # upstream_learn only when never learned
}


def upstream_due(learned, updated_at, now) -> bool:
    """Learn upstream gauges at start unless a non-empty result younger than a day exists (restarts reset the daily
    timer; an empty result means it was learned before the history existed)."""
    return not learned or updated_at is None or (now - updated_at).total_seconds() >= 24 * 3600


def owns_schema(role: str) -> bool:
    """Only the collector runs schema.sql: two containers altering tables at start deadlocked with inserts."""
    return role != "forecaster"


def tasks_for(role: str) -> list[tuple[str, int]]:
    return FORECASTER_TASKS if role == "forecaster" else TASKS


BACKOFF_CAP = {"hii_waterlevel": 2, "hii_history": 2}  # core telemetry: never fall more than 2 intervals behind
                                                       # (default cap 6 for optional sources such as Traffy)


def backoff_factor(failures: int, cap: int = 6) -> int:
    """Interval multiplier for a task that keeps failing: none below 3 consecutive failures, then x2, x4, x6 (cap).
    A dead upstream (Traffy answered HTTP 502 for ~2.5 h on 2026-09-26) otherwise costs the single worker loop
    minutes per run, delaying the collectors that work (KI-213)."""
    return 1 if failures < 3 else min(cap, 2 ** (failures - 2))


def failures_of(name: str) -> int:
    try:
        with db.connect() as c:
            row = c.execute("SELECT consecutive_failures FROM source_health WHERE source=%s", (name,)).fetchone()
        return row["consecutive_failures"] if row else 0
    except Exception:
        return 0


def disk_check() -> None:
    free = archive.free_disk_gb()
    if free < settings.min_free_disk_gb:
        log.error("LOW DISK: %.1f GB free (< %.1f). Raw archive %.2f GB. Replicate to R2 / add disk.",
                  free, settings.min_free_disk_gb, archive.archive_size_gb())
        db.record_health("disk", False, error=f"free {free:.1f} GB")
    else:
        db.record_health("disk", True)


def run_task(name: str) -> None:
    if name == "forecast":
        try:
            forecast.run_all()
            db.record_health("forecast", True)
        except Exception as e:
            log.exception("forecast failed")
            db.record_health("forecast", False, error=str(e))
    elif name == "upstream_learn":
        try:
            from floodwatch.forecast import upstream
            upstream.run_all()
            db.record_health("upstream_learn", True)
        except Exception as e:
            log.exception("upstream_learn failed")
            db.record_health("upstream_learn", False, error=str(e))
    elif name == "risk_record":
        try:
            from floodwatch import risks
            with db.connect() as c:
                risks.compute_records(c)
            db.record_health("risk_record", True)
        except Exception as e:
            log.exception("risk_record failed")
            db.record_health("risk_record", False, error=str(e))
    elif name == "qc":
        try:
            qc.run_all()
            db.record_health("qc", True)
        except Exception as e:
            log.exception("qc failed")
            db.record_health("qc", False, error=str(e))
    elif name == "disk":
        disk_check()
    elif name == "retention":
        try:
            with db.connect() as c:
                retention.run(c)
            db.record_health("retention", True)
        except Exception as e:
            log.exception("retention failed")
            db.record_health("retention", False, error=str(e))
    elif name == "ai_triage":
        try:  # never let AI problems touch the collectors
            n = ai.triage_pending()
            if n:
                log.info("ai_triage: labelled %d notes", n)
        except Exception:
            log.exception("ai_triage failed (ignored)")
    else:
        collectors.run(name)


def main(role: str = "collector") -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    for attempt in range(60):  # wait for the database container (and, for the forecaster, for the schema)
        try:
            if owns_schema(role):
                db.init_schema()
            else:
                with db.connect() as c:
                    c.execute("SELECT 1 FROM forecast_model LIMIT 1")
            break
        except Exception as e:
            log.warning("db not ready (%s), retrying", e)
            time.sleep(5)
    first = FIRST_RUN[role if role == "forecaster" else "collector"]
    if role == "forecaster":
        with db.connect() as c:
            row = c.execute("SELECT value, updated_at FROM collector_state WHERE key='upstream_learned'").fetchone()
        if not upstream_due(row["value"] if row else None, row["updated_at"] if row else None,
                            dt.datetime.now(dt.timezone.utc)):
            first = tuple(n for n in first if n != "upstream_learn")
    for name in first:
        run_task(name)
    active = [(n, i) for n, i in tasks_for(role) if n != "bma_dds" or settings.thai_egress_proxy]
    next_run = {name: time.time() + interval for name, interval in active}
    while True:
        now = time.time()
        for name, interval in active:
            if now >= next_run[name]:
                run_task(name)
                next_run[name] = time.time() + interval * backoff_factor(failures_of(name), BACKOFF_CAP.get(name, 6))
        time.sleep(15)

if __name__ == "__main__":
    import sys
    main(sys.argv[sys.argv.index("--role") + 1] if "--role" in sys.argv else "collector")
