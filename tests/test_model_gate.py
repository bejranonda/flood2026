"""When a model change counts as making a unit worse (owner 2026-10-06, D-107): the error must rise by more than 3 % and a
resampling test must say the rise is real, not chance; every unit's change is reported either way."""
import numpy as np

from floodwatch import model_gate


def test_a_steady_rise_beyond_three_percent_is_worse():
    old = np.random.default_rng(1).uniform(0.5, 1.5, 120)
    r = model_gate.made_worse(1.10 * old, old, block=7)
    assert r["tested"] and r["worse"] and abs(r["rise"] - 0.10) < 1e-9 and r["low"] > 0


def test_a_rise_under_the_threshold_is_not_worse_however_steady():
    old = np.random.default_rng(2).uniform(0.5, 1.5, 120)
    r = model_gate.made_worse(1.02 * old, old, block=7)
    assert r["tested"] and not r["worse"] and r["low"] > 0


def test_the_same_rise_from_one_bad_spell_is_chance_not_worse():
    # the same 10 % rise as above, but all of it from one week: a resample without that week shows no rise at all
    old, new = np.ones(60), np.ones(60)
    new[:7] = 1 + 0.10 * 60 / 7
    r = model_gate.made_worse(new, old, block=7)
    assert abs(r["rise"] - 0.10) < 1e-9 and r["tested"] and not r["worse"] and r["low"] <= 0


def test_too_little_data_to_resample_lets_the_size_decide():
    old = np.ones(10)
    r = model_gate.made_worse(1.05 * old, old, block=7)
    assert not r["tested"] and r["worse"] and r["low"] is None
    assert not model_gate.made_worse(1.01 * old, old, block=7)["worse"]


def test_errors_of_either_sign_and_missing_pairs():
    old = np.array([1.0, -1.0, np.nan, 2.0] * 30)
    new = np.array([-1.1, 1.1, 5.0, np.nan] * 30)
    r = model_gate.made_worse(new, old, block=4)
    assert r["n"] == 60 and abs(r["rise"] - 0.10) < 1e-9 and r["worse"]


def test_rmse_as_the_measure():
    old = np.random.default_rng(3).normal(0, 1, 200)
    r = model_gate.made_worse(1.10 * old, old, block=24, metric="rmse")
    assert abs(r["rise"] - 0.10) < 1e-9 and r["worse"]


def test_a_unit_that_had_no_error_and_now_has_some_is_worse():
    assert model_gate.made_worse(np.full(30, 0.1), np.zeros(30), block=7)["worse"]
    assert not model_gate.made_worse(np.zeros(30), np.zeros(30), block=7)["worse"]
