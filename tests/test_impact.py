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


# --- national dams at risk (owner 2026-10-05: "National dams at risk", D-100) ------------------------------------------
def test_dam_metadata_comes_with_coordinates_and_storage_bounds():
    from floodwatch.collectors import parsing
    payload = {"data": {"dam_daily": [{"dam_date": "2026-10-05", "dam": {"id": 13, "dam_name": {"th": "แก่งกระจาน"},
               "dam_lat": 12.917017, "dam_long": 99.629886, "normal_storage": 710, "max_storage": 900, "sub_basin_id": 7},
               "agency": {"agency_shortname": {"en": "RID"}}}]}}
    assert parsing.parse_hii_dam_meta(payload) == [{"dam_id": 13, "agency": "RID", "name_th": "แก่งกระจาน", "lat": 12.917017,
                                                    "lon": 99.629886, "normal_mcm": 710.0, "max_mcm": 900.0, "sub_basin_id": 7}]


def test_a_dams_position_against_its_rule_curve_is_a_fact_not_a_verdict():
    rule = {"upper": 593.37, "lower": 203.8}
    assert impact.dam_position(725.85, rule) == "above" and impact.dam_position(150.0, rule) == "below"
    assert impact.dam_position(400.0, rule) == "between"
    assert impact.dam_position(None, rule) is None and impact.dam_position(400.0, None) is None


def test_the_release_note_is_the_same_rule_the_case_page_uses():
    years = {y: (v, f"{y}-08-01") for y, v in ((2018, 24.36), (2019, 8.9), (2020, 2.76), (2021, 9.13), (2022, 4.75),
                                                (2023, 3.46), (2024, 3.89), (2025, 3.89))}
    note = impact.release_note(10.8, "2026-10-05", years)
    assert "2562–2568" in note and "2561" in note
    assert impact.release_note(9.5, "2026-10-05", {**years, 2025: (9.6, "2025-09-01")}) is None  # last year released more


def test_one_marker_per_physical_dam_with_both_agencies_side_by_side():
    meta = [{"dam_id": 13, "agency": "RID", "name_th": "แก่งกระจาน", "lat": 12.917, "lon": 99.630, "normal_mcm": 710.0,
             "max_mcm": 900.0, "sub_basin_id": 7},
            {"dam_id": 57, "agency": "EGAT", "name_th": "แก่งกระจาน", "lat": 12.916, "lon": 99.633, "normal_mcm": 710.0,
             "max_mcm": 900.0, "sub_basin_id": 7},
            {"dam_id": 1, "agency": "RID", "name_th": "ภูมิพล", "lat": 17.24, "lon": 98.97, "normal_mcm": 13462.0,
             "max_mcm": 13462.0, "sub_basin_id": 1}]
    latest = {13: {"dam_date": "2026-10-05", "storage_mcm": 725.85, "storage_pct": 102.23, "released_mcm": 10.8,
                   "inflow_mcm": 10.33, "spilled_mcm": 0.0},
              57: {"dam_date": "2026-10-04", "storage_mcm": 726.3, "storage_pct": 58.64, "released_mcm": 3.04},
              1: {"dam_date": "2026-10-05", "storage_mcm": 9000.0, "storage_pct": 66.9, "released_mcm": 1.0}}
    curves = {13: {"upper": {"10-05": 593.37}, "lower": {"10-05": 203.8}}, 1: {"upper": {"10-05": 12000.0}, "lower": {"10-05": 7000.0}}}
    layer = impact.dams_layer(meta, latest, curves, {}, cases={13: "kaeng-krachan"})
    by = {d["name_th"]: d for d in layer}
    kk = by["แก่งกระจาน"]
    assert [r["agency"] for r in kk["records"]] == ["RID", "EGAT"] and kk["position"] == "above" and kk["case"] == "kaeng-krachan"
    assert kk["records"][1]["position"] is None  # EGAT's record on 4 Oct, no curve listed for its id: no claim
    assert by["ภูมิพล"]["position"] == "between" and layer[0]["name_th"] == "แก่งกระจาน"  # above the curve listed first


def test_one_percent_definition_ranks_the_list_and_egat_zeros_are_missing_not_empty():
    # HII 2026-10-04/05: RID's % is storage ÷ normal storage (±0.16 points over 35 dams); EGAT reports 0 % for 11 of 15
    # dams with water in them and a % ≠ storage ÷ normal for the rest (Kaeng Krachan 58.64 vs 102.3); ปากมูล reports 0 for
    # storage, inflow and release. The badge uses storage ÷ the agency's own normal storage (KI-305).
    meta = [{"dam_id": 47, "agency": "EGAT", "name_th": "ห้วยกุ่ม", "lat": 16.413056, "lon": 101.797222, "normal_mcm": 20.23, "max_mcm": 25.14},
            {"dam_id": 48, "agency": "EGAT", "name_th": "ปากมูล", "lat": 15.282103, "lon": 105.466051, "normal_mcm": 229.6, "max_mcm": None},
            {"dam_id": 1, "agency": "RID", "name_th": "ภูมิพล", "lat": 17.24, "lon": 98.97, "normal_mcm": 13462.0, "max_mcm": 13462.0}]
    latest = {47: {"dam_date": "2026-10-04", "storage_mcm": 18.31, "storage_pct": 0.0, "inflow_mcm": 0.1, "released_mcm": 0.4},
              48: {"dam_date": "2026-10-04", "storage_mcm": 0.0, "storage_pct": 0.0, "inflow_mcm": 0.0, "released_mcm": 0.0},
              1: {"dam_date": "2026-10-05", "storage_mcm": 9097.36, "storage_pct": 67.58, "inflow_mcm": 30.0, "released_mcm": 20.0}}
    layer = impact.dams_layer(meta, latest, {}, {})
    by = {d["name_th"]: d["records"][0] for d in layer}
    assert by["ห้วยกุ่ม"]["storage_pct"] is None and by["ห้วยกุ่ม"]["pct_normal"] == 90.5  # 0 % reported with water in it: missing
    assert by["ภูมิพล"]["storage_pct"] == 67.58 and by["ภูมิพล"]["pct_normal"] == 67.6  # RID's own figure kept beside it
    pm = by["ปากมูล"]
    assert pm["no_data"] and pm["storage_mcm"] is None and pm["inflow_mcm"] is None and pm["released_mcm"] is None and pm["pct_normal"] is None
    assert not by["ห้วยกุ่ม"]["no_data"]
    assert [d["name_th"] for d in layer] == ["ห้วยกุ่ม", "ภูมิพล", "ปากมูล"]  # one definition ranks the list; no data last


def test_an_egat_dam_at_an_rid_dam_with_the_same_normal_storage_is_one_dam_under_the_rid_name():
    # HII metadata: EGAT แม่งัด (53) and RID แม่งัดสมบูรณ์ชล (23) are 0.3 km apart, both 265.0 ล้าน ลบ.ม. normal storage;
    # every other EGAT/RID pair within 1.2 km already shares its name. Records stay apart (KI-217), RID first.
    meta = [{"dam_id": 23, "agency": "RID", "name_th": "แม่งัดสมบูรณ์ชล", "lat": 19.16138, "lon": 99.04011, "normal_mcm": 265.0, "max_mcm": 322.89},
            {"dam_id": 53, "agency": "EGAT", "name_th": "แม่งัด", "lat": 19.1625, "lon": 99.043056, "normal_mcm": 265.0, "max_mcm": 325.0},
            {"dam_id": 48, "agency": "EGAT", "name_th": "ปากมูล", "lat": 15.282103, "lon": 105.466051, "normal_mcm": 229.6, "max_mcm": None},
            {"dam_id": 3, "agency": "RID", "name_th": "สิรินธร", "lat": 15.202778, "lon": 105.42089, "normal_mcm": 1966.47, "max_mcm": 1966.0}]
    latest = {23: {"dam_date": "2026-10-05", "storage_mcm": 248.07, "storage_pct": 93.72},
              53: {"dam_date": "2026-10-04", "storage_mcm": 247.74, "storage_pct": 0.0},
              48: {"dam_date": "2026-10-04", "storage_mcm": 120.0, "storage_pct": 52.0},
              3: {"dam_date": "2026-10-05", "storage_mcm": 1828.0, "storage_pct": 93.0}}
    layer = impact.dams_layer(meta, latest, {}, {})
    by = {d["name_th"]: d for d in layer}
    assert "แม่งัด" not in by and [(r["agency"], r["dam_id"]) for r in by["แม่งัดสมบูรณ์ชล"]["records"]] == [("RID", 23), ("EGAT", 53)]
    assert len(layer) == 3  # ปากมูล, 10 km from สิรินธร with another normal storage, stays its own dam


def test_dam_history_comes_in_small_batches_current_year_first():
    import datetime as dt
    now = dt.datetime(2026, 10, 5, 12, tzinfo=dt.timezone.utc)
    todo = impact_todo = __import__("floodwatch.collectors", fromlist=["x"]).dam_history_todo(
        ids=[1, 13, 57], complete={(13, y) for y in range(2018, 2026)}, refreshed={13: now - dt.timedelta(hours=2)},
        this_year=2026, first_year=2018, per_run=4, case_dams=(13,), now=now)
    assert todo[:2] == [(1, 2026), (57, 2026)]  # stale current years first; 13 refreshed 2 h ago
    assert len(todo) == 4 and all(y < 2026 for _, y in todo[2:]) and all(d != 13 for d, _ in todo)


def test_the_case_river_is_drawn_from_hiis_line_as_lat_lon_parts():
    geo = {"features": [{"properties": {"STR_NAMT": "แม่น้ำเพชรบุรี"},
                         "geometry": {"type": "MultiLineString", "coordinates": [[[99.63, 12.92], [99.70, 12.95]], [[99.9, 13.1]]]}},
                        {"properties": {"STR_NAMT": "แม่น้ำท่าจีน"}, "geometry": {"type": "LineString", "coordinates": [[100.1, 14.0]]}}]}
    assert impact.river_line(geo, "แม่น้ำเพชรบุรี") == [[[12.92, 99.63], [12.95, 99.70]], [[13.1, 99.9]]]
    assert impact.river_line(geo, "แม่น้ำท่าจีน") == [[[14.0, 100.1]]] and impact.river_line(None, "x") == []


def test_a_dams_year_also_merges_inflow_and_the_curves_are_looked_up_for_the_days_ahead():
    from floodwatch import collectors
    rows = collectors.dam_year_rows(13, "RID", "แก่งกระจาน", {"series": [("2026-10-05", 10.8)]}, {"series": []},
                                    inflow={"series": [("2026-10-05", 10.33), ("2026-10-06", 9.9)]})
    by = {r["dam_date"]: r for r in rows}
    assert by["2026-10-05"]["inflow_mcm"] == 10.33 and by["2026-10-06"]["released_mcm"] is None and len(rows) == 2
    curves = {"upper": {"10-06": 590.0, "10-07": 588.0, "02-29": 600.0}, "lower": {"10-06": 203.0, "10-07": 202.0, "02-29": 300.0}}
    ahead = impact.curves_ahead(curves, "2026-10-05", 2)
    assert ahead == {"upper": [590.0, 588.0], "lower": [203.0, 202.0], "dates": ["2026-10-06", "2026-10-07"]}
    assert impact.curves_ahead(curves, "2028-02-28", 2)["upper"] == [600.0, None]  # 29 Feb listed, 1 Mar not


def test_a_largest_since_claim_needs_enough_years_and_says_whose_records():
    # live 2026-10-05: "มากกว่าทุกวันในปี 2568–2568 (เท่าที่ สสน. มีข้อมูล)" — one year fetched so far, and HII has more
    one = {2025: (3.0, "2025-09-01")}
    assert impact.release_note(3.66, "2026-10-05", one) is None
    seven = {y: (2.0, f"{y}-09-01") for y in range(2019, 2026)}
    note = impact.release_note(3.66, "2026-10-05", seven)
    assert "2562–2568" in note and "ข้อมูลในระบบเริ่มปี 2562" in note and "เท่าที่ สสน. มีข้อมูล" not in note
    two_ago = {**seven, 2024: (4.0, "2024-09-01")}  # the last year that released more was 2024: one year since is not news
    assert impact.release_note(3.66, "2026-10-05", two_ago) is None


def _river_series(gain_cm_per_cms=0.6, sign=1.0, days=200, seed=3):
    """Hourly B.18 (on its rating) and B.10 (following the release two days later) under step releases every 15 days."""
    import datetime as dt
    rng = np.random.default_rng(seed)
    t0 = dt.datetime(2025, 12, 31, 17, tzinfo=dt.timezone.utc)  # 00:00 on 1 Jan in Thailand
    rel, cur = [], 8.0
    for d in range(days):
        if d % 15 == 0:
            cur = float(rng.uniform(2, 20))
        rel.append(cur)
    n = days * 24
    H = {"B.18": np.full(n, np.nan), "B.10": np.full(n, np.nan)}
    Q = {"B.18": np.full(n, np.nan), "B.10": np.full(n, np.nan)}
    for i in range(n):
        d = i // 24
        Q["B.18"][i] = impact.mcm_to_cms(rel[d]) + 12.0
        H["B.18"][i] = 1.0 + 0.1 * Q["B.18"][i] ** 0.5
        Q["B.10"][i] = impact.mcm_to_cms(rel[max(0, d - 2)])
        H["B.10"][i] = 2.0 + sign * gain_cm_per_cms / 100.0 * Q["B.10"][i] + rng.normal(0, 0.005)
    rel_daily = {(dt.date(2026, 1, 1) + dt.timedelta(days=d)).isoformat(): rel[d] for d in range(days)}
    pts = [{"code": "B.18", "role": "below_dam", "lag_h": 0,
            "rating": {"h0": 1.0, "a": 0.1, "b": 0.5, "res": [-0.05, 0.05], "qmax": 1e9, "qmin": 0.0}},
           {"code": "B.10", "role": "after_diversion", "lag_h": 48, "rating": None}]
    return H, Q, t0, rel_daily, pts


def test_river7_learns_how_each_point_follows_a_release_change_and_scores_it_per_day():
    # E-7D-DOWN (research/2026-10-05_e7d_down.log): below the dam the rating anchored on today's level; past the diversion
    # a gain per day fitted on the year; the same method hindcast on the last days gives each point's error per day
    H, Q, t0, rel, pts = _river_series()
    r7 = impact.river7(H, Q, t0, rel, pts, test_days=60)
    g = r7["gains_cm_per_cms"]["B.10"]
    assert g[0] == 0 and g[1] == 0 and all(abs(x - 0.6) < 0.15 for x in g[2:])  # reaches B.10 on day 3 (two days' travel)
    e = r7["errors"]["B.10"]
    assert len(e["mae_m"]) == len(e["p90_m"]) == len(e["keep_mae_m"]) == 7 and e["n"] >= 50
    assert sum(e["mae_m"][2:]) < sum(e["keep_mae_m"][2:])  # knowing the plan beats keeping today's level
    assert r7["errors"]["B.18"]["mae_m"][0] < 0.02 and r7["lag_days"] == {"B.18": 0, "B.10": 2}


def test_river7_never_lets_more_release_lower_a_point_downstream():
    H, Q, t0, rel, pts = _river_series(sign=-1.0)
    assert all(x == 0 for x in impact.river7(H, Q, t0, rel, pts, test_days=60)["gains_cm_per_cms"]["B.10"])


def test_river7_needs_enough_days():
    H, Q, t0, rel, pts = _river_series(days=40)
    assert impact.river7(H, Q, t0, rel, pts, test_days=60) is None


def test_a_points_now_is_its_latest_reading_within_36_hours_with_its_time():
    # RID's gauges below Kaeng Krachan post in batches: at 05:10 ICT the latest reading was 6 h 10 min old, so a 6-hour
    # window left the case without "now" and the plans on missing flows (2026-10-05)
    x = np.full(100, np.nan)
    x[90] = 2.5
    assert impact._last_at(x, 96, impact.NOW_HOURS) == (2.5, 90) and impact.NOW_HOURS == 36
    assert impact._last_at(x, 130 if len(x) > 130 else 99, 3) == (None, None)


def test_the_river_is_split_by_nearest_gauge_and_never_coloured_far_from_one():
    # owner 2026-10-06 ("show flood area … for each release scenario"; D-019): the map colours the river, not land — each
    # piece by its nearest gauge's margin, and nothing more than 10 km from a gauge (no gauge speaks for it)
    line = [[[13.0, 99.0 + 0.01 * k] for k in range(26)]]  # ~1.08 km per step along 13°N
    pts = [{"code": "A", "lat": 13.0, "lon": 99.02}, {"code": "B", "lat": 13.0, "lon": 99.11}, {"code": "X", "lat": None, "lon": None}]
    reaches = impact.river_reaches(line, pts, max_km=10.0)
    codes = [r["code"] for r in reaches]
    assert codes == ["A", "B"]
    a, b = reaches
    assert [round(x, 2) for x in (a["line"][0][1], a["line"][-1][1])] == [99.0, 99.07]  # A to the midpoint, joined to B's first vertex
    assert [round(x, 2) for x in (b["line"][0][1], b["line"][-1][1])] == [99.07, 99.2]  # B until 10 km away (99.20 ≈ 9.8 km, 99.21 > 10)
    assert impact.river_reaches([], pts) == [] and impact.river_reaches(line, []) == []


def test_river7_fits_on_older_daily_history_too_and_can_move_every_point_by_its_gain():
    # E-7D-DOWN-3Y (research/2026-10-06_e7d_down_3y_gate.log): on three wet seasons the gain at every point — B.18 too —
    # beat the hybrid at days 3 and 7 in both samples; the database keeps 400 days, older years come as daily means
    import datetime as dt
    H, Q, t0, rel, pts = _river_series(days=200)
    short = {k: v[-100 * 24:] for k, v in H.items()}, {k: v[-100 * 24:] for k, v in Q.items()}
    t_short = t0 + dt.timedelta(days=100)
    hist = {"B.18": {"h": {}, "q": {}}, "B.10": {"h": {}, "q": {}}}
    for d in range(100):
        day = (dt.date(2026, 1, 1) + dt.timedelta(days=d)).isoformat()
        for code in ("B.18", "B.10"):
            hist[code]["h"][day] = float(np.nanmean(H[code][d * 24:(d + 1) * 24]))
            hist[code]["q"][day] = float(np.nanmean(Q[code][d * 24:(d + 1) * 24]))
    alone = impact.river7(short[0], short[1], t_short, rel, pts, test_days=30)
    both = impact.river7(short[0], short[1], t_short, rel, pts, test_days=30, history=hist)
    assert both["fit_days"] > alone["fit_days"] + 90
    g = impact.river7(short[0], short[1], t_short, rel, pts, test_days=30, history=hist, method="gain")
    assert g["method"] == "gain" and max(g["gains_cm_per_cms"]["B.18"]) > 0  # B.18 moves by its fitted gain now
    p18 = {"code": "B.18", "role": "below_dam", "h_now": 2.0, "q_now": 140.0, "rating": pts[0]["rating"]}
    assert impact.level7(p18, 20.0, 10.0, 1, [0.5] * 7, method="gain") == 2.0 + 0.005 * (impact.mcm_to_cms(20.0) - impact.mcm_to_cms(10.0))


def test_stored_onwr_layers_are_clipped_to_their_box_when_served():
    # KI-318: copies stored before the collector clipped are clipped when served; the stored state is not changed
    near = {"cls": 2, "tb": None, "rai": None, "rings": [[[13.07, 99.94], [13.08, 99.95], [13.07, 99.96]]]}
    far = {"cls": 2, "tb": None, "rai": None, "rings": [[[13.51, 99.80], [13.52, 99.81], [13.51, 99.82]]]}
    stored = {"fetched": "2026-10-06T12:03:05+00:00", "bbox": [12.618, 99.237, 13.274, 100.043],
              "layers": {"flood-warn": {"updated": "2026-10-06T11:12:42+00:00", "features": [near, far]},
                         "flood-forecast-d3": {"updated": None, "features": []}}}
    out = impact.clip_onwr(stored)
    assert out["layers"]["flood-warn"]["features"] == [near] and out["layers"]["flood-forecast-d3"]["features"] == []
    assert len(stored["layers"]["flood-warn"]["features"]) == 2 and out["layers"]["flood-warn"]["updated"] == "2026-10-06T11:12:42+00:00"
    assert impact.clip_onwr(None) is None
    old = {"layers": {"flood-warn": {"features": [far]}}}  # an older copy without its box passes through unchanged
    assert impact.clip_onwr(old) is old
