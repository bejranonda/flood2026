"""Impact analysis page, pilot Kaeng Krachan (owner 2026-10-05; docs/plan/impact-kaeng-krachan.md, D-099): what-if release →
each point downstream: flow, level range, margin to the bank, when, and whether it is outside what our data have seen."""
import numpy as np

from floodwatch import impact


def test_release_units():
    assert abs(impact.mcm_to_cms(1.0) - 11.574) < 1e-3
    assert abs(impact.cms_to_mcm(impact.mcm_to_cms(10.8)) - 10.8) < 1e-9


def test_rating_curve_recovers_a_power_law_and_states_its_range():
    rng = np.random.default_rng(1)
    q = rng.uniform(5, 140, 3000)
    h = 23.0 + 0.12 * q ** 0.6 + rng.normal(0, 0.02, len(q))
    r = impact.fit_rating(q, h)
    for qq in (10, 60, 140):
        assert abs(impact.level_at(r, qq) - (23.0 + 0.12 * qq ** 0.6)) < 0.05
    assert 139 < r["qmax"] <= 140 and r["res"][0] < 0 < r["res"][1] and r["rmse"] < 0.05


def _point(code, role, lag, q_now, h_now, bank, qmax=150.0, **k):
    # h = 1.0 + 0.1 * Q**0.5 (a simple rating), 10-90 % residuals ±5 cm
    return {"code": code, "name_th": code, "agency": "RID", "role": role, "lag_h": lag, "window": [max(0, lag - 4), lag + 4],
            "q_now": q_now, "h_now": h_now, "bank": bank,
            "rating": {"h0": 1.0, "a": 0.1, "b": 0.5, "res": [-0.05, 0.05], "qmax": qmax, "qmin": 1.0, "rmse": 0.03}, **k}


STATE = {"dam": {"released_mcm": 10.8, "date": "2026-10-05"}, "diversion_default": 63.0,
         "points": [_point("B.18", "below_dam", 2, 140.0, 2.18, 3.0),
                    _point("B.10", "after_diversion", 32, 73.0, 1.85, 2.2, q_up_lagged=136.0),
                    _point("B.16", "river", 43, 75.0, 1.87, 2.5, qmax=300.0, q_up_lagged=72.0),
                    _point("B.15", "city", 45, None, 1.9, 2.4, rating_from="B.16")]}


def test_whatif_passes_the_release_down_the_river_with_the_diversion_and_local_inflow():
    out = impact.whatif(STATE, release_mcm=21.6, diversion_cms=63.0)
    rows = {r["code"]: r for r in out["rows"]}
    r_cms = impact.mcm_to_cms(21.6)
    local18 = 140.0 - impact.mcm_to_cms(10.8)                       # B.18 today minus today's release
    assert abs(rows["B.18"]["flow_cms"] - (r_cms + local18)) < 0.5
    local10 = max(0.0, 73.0 - max(0.0, 136.0 - 63.0))               # B.10 today minus what reached it from B.18
    assert abs(rows["B.10"]["flow_cms"] - (rows["B.18"]["flow_cms"] - 63.0 + local10)) < 0.5
    assert abs(rows["B.16"]["flow_cms"] - (rows["B.10"]["flow_cms"] + (75.0 - 72.0))) < 0.5
    # level from the rating, range from its residuals, margin to the gauge's own bank, overflow flag
    b10 = rows["B.10"]
    mid = 1.0 + 0.1 * b10["flow_cms"] ** 0.5
    assert abs(b10["level"][1] - mid) < 1e-6 and abs(b10["level"][0] - (mid - 0.05)) < 1e-6
    assert abs(b10["margin_m"] - (2.2 - mid)) < 1e-6
    assert rows["B.18"]["outside"] is True and rows["B.16"]["outside"] is False  # B.18 265 > 150 seen; B.16 205 < 300 seen
    assert rows["B.15"]["flow_cms"] is None and rows["B.15"]["level"] is not None  # the city reads B.16's flow
    assert rows["B.10"]["arrival_h"] == [28, 36]
    assert out["diversion_cms"] == 63.0 and abs(out["release_cms"] - r_cms) < 1e-9


def test_whatif_defaults_the_diversion_and_flags_overflow():
    out = impact.whatif(STATE, release_mcm=60.0)  # ~694 m³/s
    assert out["diversion_cms"] == 63.0 and out["diversion_default"] is True
    rows = {r["code"]: r for r in out["rows"]}
    assert rows["B.18"]["overflow"] == "yes"  # 1.0 + 0.1·√709 = 3.66 m > bank 3.0
    assert all(r["outside"] for r in out["rows"] if r["flow_cms"])


def test_no_verdict_words_in_what_the_page_says():
    # the app never says "safe" (D-005 spirit); engineers get margins and flags, not verdicts
    text = " ".join(str(x) for x in impact.whatif(STATE, release_mcm=5.0).values())
    assert "ปลอดภัย" not in text and "safe" not in text.lower()


def test_hii_dam_records_are_parsed_with_their_agency():
    from floodwatch.collectors import parsing
    payload = {"data": {"dam_daily": [
        {"dam_date": "2026-10-05", "dam_storage": 725.85, "dam_storage_percent": 102.23, "dam_inflow": 10.33,
         "dam_released": 10.8, "dam_spilled": 0, "dam_level": 0,
         "dam": {"id": 13, "dam_name": {"th": "แก่งกระจาน"}}, "agency": {"agency_shortname": {"en": "RID"}}},
        {"dam_date": "2026-10-04", "dam_storage": 726.3, "dam_storage_percent": 58.64, "dam_released": 3.04, "dam_level": 99.36,
         "dam": {"id": 57, "dam_name": {"th": "แก่งกระจาน"}}, "agency": {"agency_shortname": {"en": "EGAT"}}}]}}
    rows = parsing.parse_hii_dams(payload)
    assert rows[0] == {"dam_id": 13, "agency": "RID", "name_th": "แก่งกระจาน", "dam_date": "2026-10-05", "storage_mcm": 725.85,
                       "storage_pct": 102.23, "inflow_mcm": 10.33, "released_mcm": 10.8, "spilled_mcm": 0.0, "level_m": None}
    assert rows[1]["agency"] == "EGAT" and rows[1]["level_m"] == 99.36  # a level of 0 means "not reported"


def test_travel_time_and_diversion_come_from_the_data():
    rng = np.random.default_rng(3)
    n = 24 * 120
    q18 = 100 + np.cumsum(rng.normal(0, 2, n))
    q10 = np.full(n, np.nan)
    q10[30:] = q18[:-30] - 60.0  # B.10 = B.18 30 h earlier minus a 60 m³/s diversion
    assert impact.best_lag(q18, q10, max_lag=72) == 30
    assert abs(impact.diversion_now(q18, q10, lag=30) - 60.0) < 1e-6


def _river(follows: bool, seed=5):
    rng = np.random.default_rng(seed)
    n = 24 * 200
    q18 = 100 + 40 * np.sin(np.arange(n) / 90.0) + rng.normal(0, 1, n)
    q10 = np.full(n, np.nan); q16 = np.full(n, np.nan)
    if follows:  # B.10 = B.18 30 h earlier minus 60; B.16 = B.10 7 h earlier + 2
        q10[30:] = q18[:-30] - 60; q16[37:] = q10[30:-7] + 2
    else:        # the diversion dam holds B.10 steady whatever B.18 does
        q10[:] = 40 + rng.normal(0, 1, n); q16[:] = 42 + rng.normal(0, 1, n)
    lvl = lambda q: 1.0 + 0.2 * np.clip(q, 0, None) ** 0.5
    return q18, q10, q16, {"B.10": lvl(q10), "B.16": lvl(q16)}


def test_the_whatif_switches_on_only_when_a_model_beats_keeping_todays_level():
    for follows, ready in ((True, True), (False, False)):
        q18, q10, q16, h = _river(follows)
        cut = int(len(q18) * 0.6)
        out = impact.replay(q18, q10, q16, {}, {"B.10": 30, "B.16": 37, "h": h}, cut)
        assert out["whatif_ready"] is ready, (follows, out)
        assert set(out["points"]["B.10"]["methods"]) == {"keep", "absolute", "anchored", "gain"}


def test_shifts_never_wrap_the_end_of_the_year_into_its_start():
    # np.roll would put the last hours first: future data in a fit meant to use only the past
    s = impact.shift(np.array([1.0, 2.0, 3.0, 4.0]), 2)
    assert np.isnan(s[:2]).all() and list(s[2:]) == [1.0, 2.0]
    assert list(impact.shift(np.array([1.0, 2.0]), 0)) == [1.0, 2.0]
    import inspect
    assert "np.roll" not in inspect.getsource(impact)


def test_the_lag_comes_with_how_strongly_the_point_follows():
    rng = np.random.default_rng(3)
    n = 24 * 120
    q18 = 100 + np.cumsum(rng.normal(0, 2, n))
    q10 = np.full(n, np.nan)
    q10[30:] = q18[:-30] - 60.0
    lag, r = impact.lag_fit(q18, q10, max_lag=72)
    assert lag == 30 and r > 0.99
    noise = rng.normal(0, 1, n)
    assert impact.lag_fit(q18, noise, max_lag=72)[1] < 0.2  # a point that does not follow says so


def test_the_value_shown_now_comes_with_its_hour():
    x = np.array([1.0, 2.0, np.nan, np.nan])
    assert impact._last_at(x, 3) == (2.0, 1)
    assert impact._last_at(np.array([np.nan] * 10), 9) == (None, None)  # nothing in the last 6 hours: say so


def test_fixed_page_text_carries_no_numbers_that_go_stale():
    # today's values (release 10.8 vs 3.04, the year's highest flow 143) belong in the live state, not in fixed text
    text = " ".join(x["th"] + x["why"] for x in impact.DATA_REQUEST)
    assert not any(v in text for v in ("10.8", "3.04", "143"))


def test_dam_notes_raise_what_an_engineer_would_question():
    rid = {"agency": "RID", "dam_date": "2026-10-05", "released_mcm": 10.8, "storage_pct": 102.23, "spilled_mcm": 0.0}
    egat = {"agency": "EGAT", "dam_date": "2026-10-04", "released_mcm": 3.04, "storage_pct": 58.64}
    notes = impact.dam_notes(rid, egat, q18_now=140.0)
    assert any("กฟผ." in n and "3.04" in n and "140" in n for n in notes)  # the other record, as reported, and why we chose
    assert any("(4 ต.ค. 69)" in n for n in notes)  # Thai dates, like the rest of the page
    assert any("เกิน 100 %" in n and "ทางน้ำล้น" in n for n in notes)       # over full but no spill reported: a question
    assert impact.dam_notes({**rid, "storage_pct": 90.0}, None, 140.0) == []
    assert impact.dam_notes(None, None, None) == []


DAM_YEAR = {"result": "OK", "data": {
    "graph_data": [{"year": 2026, "dam_name": "แก่งกระจาน", "data": [
        {"date": "2026-10-04T00:00:00+07:00", "value": 11.2755}, {"date": "2026-10-05T00:00:00+07:00", "value": 10.8},
        {"date": "2026-10-06T00:00:00+07:00", "value": None}]}],
    "upper_rule_curve": [{"date": "2020-10-05", "value": 593.37}, {"date": "2020-02-29", "value": 600.0}],
    "lower_rule_curve": [{"date": "2020-10-05", "value": 203.8}, {"date": "2020-02-29", "value": 300.0}],
    "lower_bound": 65, "upper_bound": 900, "normal_bound": 710}}


def test_hii_dam_year_gives_daily_values_and_the_rule_curves_by_day_of_year():
    from floodwatch.collectors import parsing
    y = parsing.parse_hii_dam_year(DAM_YEAR)
    assert y["series"] == [("2026-10-04", 11.2755), ("2026-10-05", 10.8)]  # Thai dates; empty days dropped
    assert y["upper"]["10-05"] == 593.37 and y["lower"]["10-05"] == 203.8 and y["normal"] == 710.0
    assert impact.rule_curve_on(y, "2026-10-05") == {"upper": 593.37, "lower": 203.8}
    assert impact.rule_curve_on(y, "2027-02-28") is None  # a day the curve does not list: say nothing


def test_dam_notes_state_the_rule_curve_and_how_rare_todays_release_is():
    rid = {"agency": "RID", "dam_date": "2026-10-05", "released_mcm": 10.8, "storage_mcm": 725.85, "storage_pct": 99.0}
    years = {2018: (24.36, "2018-08-21"), 2019: (8.90, "2019-10-05"), 2020: (2.76, "2020-05-26"), 2021: (9.13, "2021-11-05"),
             2022: (4.75, "2022-04-07"), 2023: (3.46, "2023-11-28"), 2024: (3.89, "2024-08-01"), 2025: (3.89, "2025-11-02")}
    notes = impact.dam_notes(rid, None, None, rule={"upper": 593.37, "lower": 203.8}, years=years)
    assert any("เส้นควบคุมบน" in n and "132" in n for n in notes)               # 725.85 − 593.37, a fact, not a verdict
    assert any("2561" in n and "24.36" in n for n in notes)                       # the last year that released more
    assert not any("เส้นควบคุม" in n for n in impact.dam_notes({**rid, "storage_mcm": 500.0}, None, None,
                                                                 rule={"upper": 593.37, "lower": 203.8}))
    assert not any("2561" in n for n in impact.dam_notes({**rid, "released_mcm": 5.0}, None, None, years=years))
    gap = {y: v for y, v in years.items() if y != 2023}  # a year we have not seen: no "more than every day in …" claim
    assert not any("มากกว่าทุกวัน" in n for n in impact.dam_notes(rid, None, None, years=gap))


def test_a_dams_year_merges_release_and_storage_by_date():
    from floodwatch import collectors
    rel = {"series": [("2026-10-04", 11.2755), ("2026-10-05", 10.8)]}
    sto = {"series": [("2026-10-05", 725.849), ("2026-10-06", 725.0)]}
    rows = collectors.dam_year_rows(13, "RID", "แก่งกระจาน", rel, sto)
    by = {r["dam_date"]: r for r in rows}
    assert by["2026-10-05"]["released_mcm"] == 10.8 and by["2026-10-05"]["storage_mcm"] == 725.849
    assert by["2026-10-04"]["storage_mcm"] is None and by["2026-10-06"]["released_mcm"] is None
    assert all(r["dam_id"] == 13 and r["agency"] == "RID" for r in rows) and len(rows) == 3


def test_the_first_gauge_is_checked_against_the_dams_reported_release():
    import datetime as dt
    rng = np.random.default_rng(7)
    days = [(dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(120)]
    rel = {d: 1.0 + 9.0 * abs(np.sin(i / 9.0)) for i, d in enumerate(days)}           # ล้าน ลบ.ม./วัน
    flow = {d: impact.mcm_to_cms(rel[d]) + 10.0 + rng.normal(0, 1.0) for d in days}  # same day + 10 m³/s local inflow
    chk = impact.release_vs_flow(rel, flow)
    assert chk["days"] == 120 and chk["r"] > 0.95 and abs(chk["median_diff_cms"] - 10.0) < 1.0
    assert chk["lag0_r"] > chk["lag1_r"]                                             # it arrives the same day
    assert impact.release_vs_flow(dict(list(rel.items())[:10]), flow) is None        # too few days: no claim
