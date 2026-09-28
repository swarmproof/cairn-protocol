"""Tests for the misspecification-study worlds and baselines."""

import numpy as np
import pytest

from simulation import worlds
from simulation.generator import generate_events_vectorized
from simulation.recovery import ground_truth_probability, ground_truth_vectorized
from simulation.run_misspec import (
    design_matrix, evaluate_cell, fit_binned, fit_logistic, mean_ci, predict_binned,
    predict_logistic, simulate_world,
)


@pytest.fixture(scope="module")
def events():
    return generate_events_vectorized(5_000, np.random.default_rng(123))


@pytest.mark.parametrize("name", list(worlds.WORLDS))
def test_world_returns_probabilities_in_unit_interval(name, events):
    p = worlds.world_probabilities(name, events, rng=np.random.default_rng(7))
    assert p.shape == (len(events["failure_class"]),)
    assert np.all(np.isfinite(p))
    assert np.all((p >= 0.0) & (p <= 1.0))


@pytest.mark.parametrize("name", list(worlds.WORLDS))
def test_world_bounded_on_extreme_inputs(name):
    n = 6
    fc = np.array(["LIVENESS", "RESOURCE", "LOGIC"] * 2)
    zeros, ones = np.zeros(n), np.ones(n)
    for B, D, rem, skill in [(zeros, zeros, ones * 48, zeros), (ones, ones, zeros, ones)]:
        fn = worlds.WORLDS[name]
        kwargs = {"rng": np.random.default_rng(0)} if name == "heavy_tail" else {}
        p = fn(fc, B, D, rem, skill, **kwargs)
        assert np.all((p >= 0.0) & (p <= 1.0))


def test_multiplicative_world_equals_existing_ground_truth(events):
    args = (events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
            events["remaining_subtasks"], events["fallback_skill"])
    np.testing.assert_array_equal(worlds.multiplicative(*args), ground_truth_vectorized(*args))
    for i in range(20):
        scalar = ground_truth_probability(
            str(events["failure_class"][i]), float(events["budget_remaining"][i]),
            float(events["deadline_remaining"][i]), float(events["remaining_subtasks"][i]),
            float(events["fallback_skill"][i]),
        )
        assert worlds.multiplicative(*[a[i:i + 1] for a in args])[0] == pytest.approx(scalar)


def test_nonstationary_matches_multiplicative_at_time_zero(events):
    args = (events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
            events["remaining_subtasks"], events["fallback_skill"])
    t0 = np.zeros(len(events["failure_class"]))
    np.testing.assert_allclose(worlds.nonstationary(*args, t=t0), worlds.multiplicative(*args))


@pytest.mark.parametrize("name", ["additive", "threshold", "interaction"])
def test_calibrated_worlds_match_multiplicative_mean(name):
    target = worlds.calibration_reference_mean("multiplicative", n=100_000)
    assert worlds.calibration_reference_mean(name, n=100_000) == pytest.approx(target, abs=0.01)


@pytest.mark.parametrize("name", list(worlds.WORLDS))
def test_simulate_world_deterministic_for_fixed_seed(name):
    ev1, p1, y1 = simulate_world(name, seed=42, n=3_000)
    ev2, p2, y2 = simulate_world(name, seed=42, n=3_000)
    np.testing.assert_array_equal(p1, p2)
    np.testing.assert_array_equal(y1, y2)
    np.testing.assert_array_equal(ev1["budget_remaining"], ev2["budget_remaining"])
    _, p3, _ = simulate_world(name, seed=43, n=3_000)
    assert not np.array_equal(p1, p3)


def test_evaluate_cell_deterministic_for_fixed_seed():
    a = evaluate_cell("additive", seed=42, n=4_000)
    b = evaluate_cell("additive", seed=42, n=4_000)
    assert a["bayes_misrouting"] == b["bayes_misrouting"]
    for fam in a["families"]:
        assert a["families"][fam]["misrouting"] == b["families"][fam]["misrouting"]
        assert a["families"][fam]["brier"] == b["families"][fam]["brier"]


def _separable_events(n, rng):
    return {
        "failure_class": rng.choice(["LIVENESS", "RESOURCE", "LOGIC"], size=n),
        "budget_remaining": rng.random(n),
        "deadline_remaining": rng.random(n),
    }


def test_logistic_beats_constant_predictor_on_separable_case():
    rng = np.random.default_rng(0)
    ev = _separable_events(4_000, rng)
    y = ev["budget_remaining"] > 0.5
    w = fit_logistic(design_matrix(ev), y)

    ev_test = _separable_events(2_000, rng)
    y_test = ev_test["budget_remaining"] > 0.5
    p = predict_logistic(w, design_matrix(ev_test))

    const = np.full(len(y_test), y.mean())
    brier_logit = np.mean((p - y_test) ** 2)
    brier_const = np.mean((const - y_test) ** 2)
    err_logit = np.mean((p >= 0.5) != y_test)
    err_const = min(y_test.mean(), 1 - y_test.mean())

    assert brier_logit < 0.25 * brier_const
    assert err_logit < 0.02
    assert err_logit < err_const


def test_binned_lookup_recovers_cell_rates():
    rng = np.random.default_rng(1)
    ev = _separable_events(20_000, rng)
    y = (ev["failure_class"] == "LIVENESS") & (ev["deadline_remaining"] > 0.5)
    table = fit_binned(ev, y)
    p = predict_binned(table, ev)
    assert np.mean((p >= 0.5) != y) < 0.01


def test_mean_ci():
    m, h = mean_ci([1.0, 1.0, 1.0])
    assert m == 1.0 and h == 0.0
    m, h = mean_ci([0.0, 2.0])
    assert m == 1.0 and h == pytest.approx(12.706 * np.sqrt(2.0) / np.sqrt(2.0))
