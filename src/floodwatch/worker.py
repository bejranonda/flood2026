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
    ("bma_klong", 600),  # BMA khlong gauges via the flood69 relay (relay refreshes every 5 min)
    ("hii_rain", 1800),
    ("openmeteo", 3600),
    ("hii_stations", 6 * 3600),
    ("hii_history", 6 * 3600),
    ("hii_backfill", 600),  # a few stations per run until the 1-year backfill is complete (D-018)
    ("bma_dds", 3 * 3600),
    ("hii_fews_forecast", 3 * 3600),
    ("openmeteo_prev", 24 * 3600),  # rain as forecast 1-2 days earlier: training data for the star model (D-052)  # HII official forecast files, new issue ~daily (D-050)
    ("forecast", 1800),
    ("ai_triage", 900),  # optional Workers AI labels for feedback notes; a no-op when AI is unavailable
    ("disk", 3600),
]


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
    for name in ("hii_waterlevel", "hii_stations", "hii_history", "hii_backfill", "openmeteo", "openmeteo_prev", "traffy", "bma_klong", "hii_rain", "forecast", "disk"):
        run_task(name)
    active = [(n, i) for n, i in TASKS if n != "bma_dds" or settings.thai_egress_proxy]
    next_run = {name: time.time() + interval for name, interval in active}
    while True:
        now = time.time()
        for name, interval in active:
            if now >= next_run[name]:
                run_task(name)
                next_run[name] = time.time() + interval * backoff_factor(failures_of(name), BACKOFF_CAP.get(name, 6))
        time.sleep(15)


if __name__ == "__main__":
    main()
