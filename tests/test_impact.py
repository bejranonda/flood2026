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
