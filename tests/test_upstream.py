"""Task 3 (v0.16, D-064): upstream gauges learned from the data, for gauges off the Chao Phraya chain."""
import numpy as np

from floodwatch.forecast import upstream

N, CUT = 5200, 5000  # hours; learning may only use hours before CUT


def _walk(seed, n=N):
    rng = np.random.default_rng(seed)
    return np.cumsum(rng.normal(0, 0.05, n))


def _shift(x, lag):
    out = np.full(len(x), np.nan)
    out[lag:] = x[:-lag]
    return out


def _grid(y):
    return np.arange(len(y), dtype=float) + 480000.0, y  # absolute hours, as forecast.hourly_grid returns


def test_a_gauge_that_leads_by_12_hours_is_found():
    s = _walk(1)
    tgt = _shift(s, 12) + np.random.default_rng(2).normal(0, 0.005, N)
    lag, r = upstream.score(tgt[:CUT], s[:CUT])
    assert 10 <= lag <= 14 and r > 0.9


def test_a_copy_or_a_co_located_gauge_is_not_upstream():
    s = _walk(3)
    lag, r = upstream.score(s, s + 0.3)  # another agency at the same place: best at lag 0, never "leads"
    assert lag == 0


META = {"T": {"basin": "น้ำพอง", "lat": 16.5, "lon": 101.3}, "UP": {"basin": "น้ำพอง", "lat": 16.8, "lon": 101.6},
        "TWIN": {"basin": "น้ำพอง", "lat": 16.5, "lon": 101.3}, "FAR": {"basin": "น้ำพอง", "lat": 19.9, "lon": 101.3},
        "OTHER": {"basin": "ชี", "lat": 16.6, "lon": 101.4}, "LATE": {"basin": "น้ำพอง", "lat": 16.6, "lon": 101.4}}


def _series():
    s = _walk(5)
    tgt = _shift(s, 12)
    late = _walk(9)
    late[CUT:] = s[CUT - 12:N - 12]  # matches the target only after the cutoff: a leak if it were chosen
    return {"T": _grid(tgt), "UP": _grid(s), "TWIN": _grid(tgt + 0.4), "FAR": _grid(s),
            "OTHER": _grid(s), "LATE": _grid(late)}


def test_learn_picks_only_leading_gauges_in_the_same_basin_within_reach_before_the_cutoff():
    ser = _series()
    picked = upstream.learn(ser, META, cutoff_h=int(ser["T"][0][CUT]))
    assert [p[0] for p in picked["T"]] == ["UP"]  # not TWIN (lag 0), FAR (> 250 km), OTHER (basin), LATE (leak)
    code, lag, r = picked["T"][0]
    assert 10 <= lag <= 14 and r >= upstream.MIN_R


def test_learn_keeps_at_most_four():
    # D-093 (2026-10-04): up to 4 learned gauges (was 2) — on gauges the choice never saw, the served error vs "no change"
    # improved at every horizon (24 h −6.6 → −9.1 %), research/2026-10-04_upstream_k_s{1,2}.log
    s = _walk(11)
    ser = {"T": _grid(_shift(s, 12))}
    meta = {"T": META["T"]}
    for i in range(6):
        ser[f"U{i}"] = _grid(s + i * 0.1)
        meta[f"U{i}"] = {"basin": "น้ำพอง", "lat": 16.6 + i * 0.05, "lon": 101.3}
    assert len(upstream.learn(ser, meta, cutoff_h=int(ser["T"][0][CUT]))["T"]) == upstream.K == 4


def test_ninety_days_of_pairs_are_enough_to_learn_from():
    assert upstream.MIN_PAIRS == 90 * 24  # was 180 days (D-093)


def test_short_overlap_is_not_enough():
    s = _walk(13)
    ser = {"T": _grid(_shift(s, 12)), "UP": (np.arange(1000, dtype=float) + 480000.0, s[:1000])}
    assert upstream.learn(ser, {"T": META["T"], "UP": META["UP"]}, cutoff_h=480000 + CUT) == {}


def test_chain_gauges_and_focus_gauges_keep_the_bangkok_rule():
    from floodwatch import forecast
    chain = {"C.2": 200.0, "C.13": 275.3, "C.3": 230.0, "C.7A": 150.0}
    learned = {"URTU07": [["E.29A", 6, 0.8]], "BKK013": [["X", 3, 0.9]]}
    assert forecast.upstream_codes("C.7A", chain, True, learned) == forecast.upstream_of("C.7A", chain)
    assert forecast.upstream_codes("BKK013", chain, True, learned) == []  # focus canal: rain only, as proven
    assert forecast.upstream_codes("URTU07", chain, False, learned) == ["E.29A"]
    assert forecast.upstream_codes("N.54", chain, False, learned) == []


def test_gauges_whose_upstream_changed_get_a_fresh_backtest():
    old = {"A": [["U", 6, 0.8]], "B": [["V", 3, 0.7]]}
    new = {"A": [["U", 6, 0.81]], "B": [["W", 4, 0.9]], "C": [["Z", 2, 0.6]]}
    assert upstream.changed_codes(old, new) == {"B", "C"}  # same upstream codes (A) is not a change
    assert upstream.changed_codes({}, new) == {"A", "B", "C"}


def test_candidates_from_another_river_system_are_never_upstream():
    # owner 2026-10-02 (basin data, item 4): Kolok and Sai Buri reach the sea apart; experiment: links changed 1/39
    ser = _series()
    meta = {k: {**v, "system": 1} for k, v in META.items()}
    meta["UP"] = {**meta["UP"], "system": 2}  # leads the target perfectly, but on another river system
    assert "T" not in upstream.learn(ser, meta, cutoff_h=int(ser["T"][0][CUT]))
    meta["UP"] = {**meta["UP"], "system": None}  # a small stream (no main river): the basin rule alone applies
    assert [p[0] for p in upstream.learn(ser, meta, cutoff_h=int(ser["T"][0][CUT]))["T"]] == ["UP"]
