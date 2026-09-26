"""Single-process scheduler: collectors, forecasts and a disk guard on fixed intervals.

Run: python -m floodwatch.worker
"""
from __future__ import annotations

import logging
import time

from floodwatch import ai, archive, collectors, db, forecast
from floodwatch.config import settings

log = logging.getLogger("floodwatch.worker")

# (task, interval seconds). Polite: never faster than the source updates (GUIDELINES §5).
TASKS = [
    ("hii_waterlevel", 600),
    ("traffy", 600),
    ("hii_rain", 1800),
    ("openmeteo", 3600),
    ("hii_stations", 6 * 3600),
    ("hii_history", 6 * 3600),
    ("hii_backfill", 600),  # a few stations per run until the 1-year backfill is complete (D-018)
    ("bma_dds", 3 * 3600),
    ("forecast", 1800),
    ("ai_triage", 900),  # optional Workers AI labels for feedback notes; a no-op when AI is unavailable
    ("disk", 3600),
]


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
    elif name == "disk":
        disk_check()
    elif name == "ai_triage":
        try:  # never let AI problems touch the collectors
            n = ai.triage_pending()
            if n:
                log.info("ai_triage: labelled %d notes", n)
        except Exception:
            log.exception("ai_triage failed (ignored)")
    else:
        collectors.run(name)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    for attempt in range(30):  # wait for the database container
        try:
            db.init_schema()
            break
        except Exception as e:
            log.warning("db not ready (%s), retrying", e)
            time.sleep(2)
    # First run order: latest values -> history -> weather -> forecast.
    for name in ("hii_waterlevel", "hii_stations", "hii_history", "openmeteo", "traffy", "hii_rain", "forecast", "disk"):
        run_task(name)
    active = [(n, i) for n, i in TASKS if n != "bma_dds" or settings.thai_egress_proxy]
    next_run = {name: time.time() + interval for name, interval in active}
    while True:
        now = time.time()
        for name, interval in active:
            if now >= next_run[name]:
                run_task(name)
                next_run[name] = time.time() + interval
        time.sleep(15)


if __name__ == "__main__":
    main()
