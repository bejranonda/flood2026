"""Checks over a gauge's recent series that a single reading cannot show (KI-237).

`qc_level` judges one reading against the bank and ground. Two faults pass it:

* **Dropouts**: a steady gauge reads a wrong value for one or two readings and comes straight back (WL.LPT.03 and
  WL.KPM.05 drop to exactly -2.00 m; CPY016 to 2.20 m). The values are flagged `dropout` and kept out of every view.
* **Erratic gauges**: the level jumps back and forth by tens of centimetres between consecutive readings, from pumps
  working next to the sensor (WL.BNJ.02, WL.BSK.01) or from a faulty sensor (WL.SSB.08: ±0.8 m every 5-15 min).
  No level or forecast from such a gauge means anything to a resident, and pumping is not predictable from the
  level (owner, 2026-09-28). The station stays on the map; its level, status and trend are hidden (D-024).
"""
from __future__ import annotations

STEP_M = 0.30        # a change between consecutive readings this large is a "step"
MAX_GAP_S = 1800     # only readings at most 30 min apart are compared (hourly history is not judged)
BACK_M = 0.10        # a dropout ends when the level is back within 10 cm of the level before it
MAX_DROPOUT_RUN = 2  # dropouts seen at BMA gauges last one or two readings
ERRATIC_STEPS = 3    # steps (not counting dropouts) in the window that mark a gauge erratic
WINDOW_S = 24 * 3600  # the window: a gauge calm for 12 h between bursts (WL.SSB.08) stays flagged


def dropouts(xs: list[tuple[float, float]]) -> list[int]:
    """Indices of readings that leave the level before them by >= STEP_M for at most MAX_DROPOUT_RUN readings and
    come back to within BACK_M of it, every gap <= MAX_GAP_S. `xs` = [(epoch seconds, level)] in time order.
    The newest readings are never dropouts: only a later reading can show that the level came back."""
    out: list[int] = []
    i = 1
    while i < len(xs) - 1:
        base_t, base = xs[i - 1]
        for run in range(1, MAX_DROPOUT_RUN + 1):
            j = i + run  # the reading after the run
            if j >= len(xs):
                break
            seg = xs[i - 1:j + 1]
            if any(b[0] - a[0] > MAX_GAP_S for a, b in zip(seg, seg[1:])):
                break
            if (all(abs(v - base) >= STEP_M for _, v in xs[i:j]) and abs(xs[j][1] - base) <= BACK_M):
                out.extend(range(i, j))
                i = j
                break
        i += 1
    return out


def erratic_steps(xs: list[tuple[float, float]], drop: list[int] | None = None) -> int:
    """Steps of >= STEP_M between consecutive readings <= MAX_GAP_S apart, with the dropouts left out."""
    skip = set(dropouts(xs) if drop is None else drop)
    kept = [x for k, x in enumerate(xs) if k not in skip]
    return sum(1 for a, b in zip(kept, kept[1:]) if b[0] - a[0] <= MAX_GAP_S and abs(b[1] - a[1]) >= STEP_M)


def assess(xs: list[tuple[float, float]]) -> dict:
    """Dropout indices and erratic-step count for one gauge's window (caller passes the last WINDOW_S)."""
    drop = dropouts(xs)
    n = erratic_steps(xs, drop)
    return {"dropouts": drop, "erratic_steps": n, "erratic": n >= ERRATIC_STEPS}


def run_all(hours: float = 25) -> dict:
    """Flag dropouts (quality_flag 'dropout', never deleted) in the last `hours` of every focus gauge and store the
    erratic gauges of the last WINDOW_S in collector_state 'erratic_gauges' ({code: {"steps": n}}), which the API
    and the forecast read. A longer `hours` (e.g. 45 days) cleans the history the forecast trains on, once."""
    import datetime as dt
    import logging

    from floodwatch import db
    now = dt.datetime.now(dt.timezone.utc)
    with db.connect() as c:
        rows = c.execute(
            """SELECT o.code, o.obs_time, o.level_msl FROM observation o JOIN station s USING (code)
               WHERE s.in_focus AND o.quality_flag='ok' AND o.level_msl IS NOT NULL
                 AND o.obs_time > now() - make_interval(secs => %s) ORDER BY o.code, o.obs_time""",
            (hours * 3600,)).fetchall()
        series: dict[str, list] = {}
        for r in rows:
            series.setdefault(r["code"], []).append((r["obs_time"], float(r["level_msl"])))
        flagged, erratic = [], {}
        for code, obs in series.items():
            xs = [(t.timestamp(), v) for t, v in obs]
            drop = set(dropouts(xs))
            flagged += [(code, obs[k][0]) for k in sorted(drop)]
            start = now.timestamp() - WINDOW_S
            n = erratic_steps([x for k, x in enumerate(xs) if x[0] > start and k not in drop], [])
            if n >= ERRATIC_STEPS:
                erratic[code] = {"steps": n}
        if flagged:
            with c.cursor() as cur:
                cur.executemany("UPDATE observation SET quality_flag='dropout' WHERE code=%s AND obs_time=%s", flagged)
        db.set_state(c, "erratic_gauges", erratic)
        c.commit()
    logging.getLogger("floodwatch.qc").info("qc: %d dropouts flagged, %d erratic gauges (%s)", len(flagged),
                                            len(erratic), " ".join(sorted(erratic)))
    return {"dropouts": len(flagged), "erratic": sorted(erratic)}
