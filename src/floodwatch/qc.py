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


STUCK_SHARE = 0.90    # one exact value in >= 90 % of the last 24 h: a stuck logger (six BMA gauges at 1.00 m, 2026-09-28)
STUCK_MIN_READINGS = 50


def stuck(xs: list[tuple[float, float]]) -> float | None:
    """The repeated value when one exact level makes up >= STUCK_SHARE of the readings (a placeholder, not water:
    WL.BKA.04, BYI.01, PWT.06, SSB.11 at exactly 1.00 m and SSB.07 at 0.40 m for 48 h; KI-241). None otherwise."""
    if len(xs) < STUCK_MIN_READINGS:
        return None
    counts: dict[float, int] = {}
    for _, v in xs:
        counts[v] = counts.get(v, 0) + 1
    top, n = max(counts.items(), key=lambda kv: kv[1])
    return top if n / len(xs) >= STUCK_SHARE else None


OBS_MIN_SPAN_H = 20   # a "24 h" change needs readings over at least 20 of the 24 hours
OBS_STEADY_R2 = 0.5   # below this the level went up and down: say so instead of a direction
OBS_WIGGLE_M = 0.05   # ... unless the ups and downs are within 5 cm (then a small net change is still "steady")


def observed24(xs: list[tuple[float, float]], hours: int = 24) -> dict | None:
    """What the level did over the last 24 h, as a fact (owner 2026-09-28: "a few cm lower in a flood is
    significant"). Straight-line fit over `xs` = [(epoch s, level)] (the caller passes the last 24 h, dropouts
    removed): change = slope × 24 h. Words follow the *rounded* centimetres so they match the number shown:
    < 2 steady · 2-4 small · 5-19 plain · ≥ 20 strong; "mixed" when the level went up and down (tide, pumps)."""
    if len(xs) < 6 or xs[-1][0] - xs[0][0] < OBS_MIN_SPAN_H / 24 * hours * 3600:
        return None
    n = len(xs)
    mx = sum(t for t, _ in xs) / n
    my = sum(v for _, v in xs) / n
    sxx = sum((t - mx) ** 2 for t, _ in xs)
    b = sum((t - mx) * (v - my) for t, v in xs) / sxx
    ss = sum((v - my) ** 2 for _, v in xs)
    res = sum((v - (my + b * (t - mx))) ** 2 for t, v in xs)
    r2 = 1 - res / ss if ss > 0 else 1.0
    change = b * hours * 3600
    cm = round(change * 100)
    wiggle = (res / n) ** 0.5
    if r2 < OBS_STEADY_R2 and wiggle >= OBS_WIGGLE_M:
        level = "mixed"  # big ups and downs (tide, pumps)
    elif abs(cm) < 2:
        level = "steady"
    elif r2 < OBS_STEADY_R2 and wiggle > abs(change) / 2:
        level = "mixed"  # small change lost in noise
    else:  # incl. a slow trend under whole-cm steps (WL.LBK.03: −1 cm/day, R² 0.43, wiggle < 1 cm), D-060
        size = "small_" if abs(cm) < 5 else "strong_" if abs(cm) >= 20 else ""
        level = size + ("rise" if cm > 0 else "fall")
    return {"change_cm": cm, "r2": round(r2, 2), "level": level, "hours": hours}


def observed(xs: list[tuple[float, float]]) -> dict | None:
    """The measured trend shown to residents: the last 24 h, or the last 48 h when 24 h shows no clear trend (owner
    2026-09-28: "the trend in chart shows lowering slowly in 48 hr, but we said ทรงตัว"; ~1 cm/day is clear over two
    days, lost in whole-cm steps over one). `xs` = the last 48 h, dropouts removed."""
    if not xs:
        return None
    end = xs[-1][0]
    o24 = observed24([x for x in xs if x[0] > end - 24 * 3600], 24)
    if o24 and o24["level"] not in ("steady", "mixed"):
        return o24
    o48 = observed24([x for x in xs if x[0] > end - 48 * 3600], 48)
    return o48 if o48 and o48["level"] not in ("steady", "mixed") else o24


def run_all(hours: float = 49) -> dict:
    """Flag dropouts (quality_flag 'dropout', never deleted) in the last `hours` of every focus gauge and store the
    erratic gauges of the last WINDOW_S in collector_state 'erratic_gauges' ({code: {"steps": n}}), which the API
    and the forecast read, and every other gauge's measured 24 h change in 'observed24' (`observed24`). A longer `hours` (e.g. 45 days) cleans the history the forecast trains on, once."""
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
        flagged, erratic, trends = [], {}, {}
        for code, obs in series.items():
            xs = [(t.timestamp(), v) for t, v in obs]
            drop = set(dropouts(xs))
            flagged += [(code, obs[k][0]) for k in sorted(drop)]
            start = now.timestamp() - WINDOW_S
            recent = [x for k, x in enumerate(xs) if x[0] > start and k not in drop]
            n = erratic_steps(recent, [])
            flat = stuck(recent)
            if flat is not None:
                erratic[code] = {"kind": "stuck", "value": flat}
            elif n >= ERRATIC_STEPS:
                erratic[code] = {"kind": "erratic", "steps": n}
            else:
                o = observed([x for k, x in enumerate(xs) if k not in drop and x[0] > now.timestamp() - 48 * 3600])
                if o:
                    trends[code] = o
        if flagged:
            with c.cursor() as cur:
                cur.executemany("UPDATE observation SET quality_flag='dropout' WHERE code=%s AND obs_time=%s", flagged)
        db.set_state(c, "erratic_gauges", erratic)
        db.set_state(c, "observed24", trends)  # the measured 24 h change per gauge, read by the API
        c.commit()
    logging.getLogger("floodwatch.qc").info("qc: %d dropouts flagged, %d erratic gauges (%s)", len(flagged),
                                            len(erratic), " ".join(sorted(erratic)))
    return {"dropouts": len(flagged), "erratic": sorted(erratic)}
