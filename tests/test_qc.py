"""Erratic (pump-affected) gauges and single-reading dropouts (KI-237). Series are shaped like the real gauges of
2026-09-27: WL.LPT.03 / WL.KPM.05 (steady, with dropouts to -2.00), WL.SSB.08 (±0.8 m every 5-15 min),
WL.BNJ.02 (pump drawdowns of 0.5-1 m in 20 min)."""
from floodwatch import qc

T0 = 1_790_000_000


def _ser(levels, step_s=600):
    return [(T0 + i * step_s, v) for i, v in enumerate(levels)]


def test_steady_gauge_with_dropouts_keeps_its_values_and_is_not_erratic():
    # LPT.03: a real critical canal at 0.99 m; the logger drops to -2.00 for one reading, twice for two.
    xs = _ser([0.99, 0.99, -2.00, 0.99, 0.98, 0.98, -2.00, -2.00, 0.98, 0.97, 0.65, 0.97, 0.96])
    r = qc.assess(xs)
    assert r["dropouts"] == [2, 6, 7, 10]
    assert r["erratic_steps"] == 0 and not r["erratic"]


def test_oscillating_gauge_is_erratic():
    # SSB.08: no stable baseline, jumps of 0.5-1.5 m between consecutive 10-min readings.
    xs = _ser([0.70, -0.49, 0.43, 0.71, 0.16, -0.80, 0.43, 0.55, -0.04, 0.29, -0.74, 0.63])
    r = qc.assess(xs)
    assert r["erratic"] and r["erratic_steps"] >= qc.ERRATIC_STEPS


def test_pump_cycling_gauge_is_erratic():
    # BNJ.02: repeated drawdowns of ~0.5 m in 10-20 min and recoveries: real, but not predictable from the level.
    xs = _ser([-2.10, -2.24, -2.53, -2.86, -2.80, -2.27, -2.31, -2.46, -2.73, -2.38, -2.10, -2.43, -2.79, -2.83,
               -2.42, -2.22])
    assert qc.assess(xs)["erratic"]


def test_smooth_rise_and_a_single_real_step_are_not_erratic():
    rise = _ser([0.10 + 0.03 * i for i in range(40)])  # 1.2 m in 6.5 h: fast for a canal, but smooth
    assert qc.assess(rise) == {"dropouts": [], "erratic_steps": 0, "erratic": False}
    gate = _ser([1.20] * 6 + [0.80] * 6)  # one gate operation: one step, not a pattern
    assert qc.assess(gate)["erratic_steps"] == 1 and not qc.assess(gate)["erratic"]


def _day(f, step_s=600):
    return [(T0 + k * step_s, f(k * step_s / 3600)) for k in range(24 * 3600 // step_s + 1)]


def test_observed24_words_follow_the_rounded_centimetres():
    # BKK021 on 2026-09-28: -4.6 cm in 24 h, steady (R² 0.83) -> shown as 5 cm, so the word is "ลดลง" (not "เล็กน้อย")
    bkk021 = qc.observed24(_day(lambda h: 2.80 - 0.046 * h / 24))
    assert bkk021["change_cm"] == -5 and bkk021["level"] == "fall"
    assert qc.observed24(_day(lambda h: 2.80 - 0.035 * h / 24))["level"] == "small_fall"
    assert qc.observed24(_day(lambda h: 2.80 - 0.22 * h / 24))["level"] == "strong_fall"
    assert qc.observed24(_day(lambda h: 2.80 + 0.03 * h / 24))["level"] == "small_rise"
    assert qc.observed24(_day(lambda h: 2.80 + 0.01 * h / 24))["level"] == "steady"


def test_observed24_says_mixed_for_tide_and_nothing_without_a_day_of_data():
    import math
    tide = qc.observed24(_day(lambda h: 1.0 + 0.6 * math.sin(2 * math.pi * h / 12.42) - 0.03 * h / 24))
    assert tide["level"] == "mixed"
    assert qc.observed24(_day(lambda h: 2.0 - 0.1 * h / 24)[:60]) is None  # 10 h of data: no "24 h" claim


def test_readings_far_apart_are_not_steps_and_the_newest_is_never_a_dropout():
    hourly = _ser([0.2, 0.9, 0.2, 0.9, 0.2], step_s=3600)  # hourly history: a 0.7 m change in 1 h is not judged
    assert qc.assess(hourly)["erratic_steps"] == 0
    tail = _ser([1.61, 1.61, 1.61, 0.66])  # the latest reading may be a dropout, but only the next one can tell
    assert qc.assess(tail)["dropouts"] == []


def test_a_logger_stuck_at_one_value_is_caught_but_a_calm_canal_is_not():
    assert qc.stuck(_ser([1.00] * 120 + [1.01] * 6)) == 1.00  # WL.BKA.04-like: exactly 1.00 m for a day
    calm = _ser([0.50 + 0.01 * ((k // 7) % 3) for k in range(126)])  # held by a gate, moving by a cm now and then
    assert qc.stuck(calm) is None and qc.stuck(_ser([1.0] * 20)) is None


def test_a_slow_fall_under_whole_cm_steps_is_a_small_fall_not_mixed():
    # WL.LBK.03, 2026-09-28: 0.90 -> 0.87 m over 3 days, logged in whole cm; R² only ~0.4 but ups and downs < 1 cm
    import random
    rnd = random.Random(1)
    xs = _day(lambda h: round(0.89 - 0.02 * h / 24 + rnd.choice((-0.005, 0, 0.005)), 2))
    assert qc.observed24(xs)["level"] in ("small_fall", "fall")


def test_a_fall_too_slow_for_24_h_is_reported_over_48_h():
    xs = _day(lambda h: 0.90 - 0.015 * h / 24) + [(T0 + 86400 + k * 600, 0.885 - 0.015 * k / 144) for k in range(1, 145)]
    o = qc.observed(xs)  # 1.5 cm/day: "steady" over 24 h, a small fall over 48 h
    assert o["hours"] == 48 and o["level"] == "small_fall" and o["change_cm"] == -3
    assert qc.observed(_day(lambda h: 0.9 - 0.1 * h / 24))["hours"] == 24  # a clear 24 h trend is reported as such


def test_run_all_end_to_end_with_a_fake_database(monkeypatch):
    # v0.14.0 slip: a local dict named `observed` shadowed qc.observed() and every run failed in production
    import datetime as dt
    from floodwatch import db
    now = dt.datetime.now(dt.timezone.utc)
    rows = [{"code": "K", "obs_time": now - dt.timedelta(minutes=10 * k), "level_msl": 1.0 + 0.001 * k} for k in range(300)][::-1]
    rows += [{"code": "S", "obs_time": now - dt.timedelta(minutes=10 * k), "level_msl": 1.0} for k in range(200)][::-1]
    state = {}

    class C:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a, **k): return type("R", (), {"fetchall": lambda _s: rows})()
        def cursor(self): return self
        def executemany(self, *a): pass
        def commit(self): pass

    monkeypatch.setattr(db, "connect", lambda: C())
    monkeypatch.setattr(db, "set_state", lambda c, k, v: state.update({k: v}))
    out = qc.run_all()
    assert out["erratic"] == ["S"] and state["erratic_gauges"]["S"]["kind"] == "stuck"
    assert state["observed24"]["K"]["level"] in ("fall", "strong_fall")


def test_observed_also_says_what_the_last_6_h_did():
    # owner 2026-10-03 (Kgt.19A): the canal jumped 70 cm in 6 h, then levelled off; the 24 h line (+124 cm) said
    # "+75 ซม. ใน 24 ชม." while the rise had stopped. The last 6 h tell whether a trend is still going.
    t0 = 1_790_000_000.0
    xs = [(t0 + k * 3600, 15.78 if k < 8 else min(16.6, 15.78 + 0.14 * (k - 7)) if k < 14 else 16.6) for k in range(25)]
    o = qc.observed(xs)
    assert o["level"] == "strong_rise" and o["change_cm"] > 60
    assert abs(o["change6_cm"]) < 3
    rising = [(t0 + k * 3600, 1.0 + 0.01 * k) for k in range(25)]
    assert abs(qc.observed(rising)["change6_cm"] - 6) < 0.5
