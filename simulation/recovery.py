"""Ground truth model for recovery success probability.

This model is DELIBERATELY different from the CAIRN score formula.
It uses non-linear dynamics (sigmoids, products) to represent reality,
while the score formula is a linear approximation being tested against it.
"""

import math
import numpy as np
from simulation.config import GROUND_TRUTH_BASE_RATES


def ground_truth_probability(
    failure_class: str,
    budget_remaining: float,
    deadline_remaining: float,
    remaining_subtasks: float,
    fallback_skill: float,
) -> float:
    """Compute the probability that recovery actually succeeds.

    This is the 'reality' model — independent of the CAIRN score formula.
    """
    base = GROUND_TRUTH_BASE_RATES[failure_class]

    # Budget factor: sigmoid centered at 0.15 (sharp drop below 15%)
    budget_factor = 1.0 / (1.0 + math.exp(-15.0 * (budget_remaining - 0.15)))

    # Deadline factor: sigmoid centered at 0.10 (sharp drop below 10%)
    deadline_factor = 1.0 / (1.0 + math.exp(-20.0 * (deadline_remaining - 0.10)))

    # Complexity penalty: more remaining work = lower success
    complexity_factor = 1.0 / (1.0 + 0.02 * remaining_subtasks)

    # Fallback skill multiplier: range [0.4, 1.0]
    skill_factor = 0.4 + 0.6 * fallback_skill

    p = base * budget_factor * deadline_factor * complexity_factor * skill_factor
    return max(0.0, min(1.0, p))


def ground_truth_vectorized(
    failure_classes: np.ndarray,
    budget_remaining: np.ndarray,
    deadline_remaining: np.ndarray,
    remaining_subtasks: np.ndarray,
    fallback_skill: np.ndarray,
) -> np.ndarray:
    """Vectorized ground truth for fast batch computation."""

    # Map failure classes to base rates
    base = np.zeros(len(failure_classes))
    for cls, rate in GROUND_TRUTH_BASE_RATES.items():
        base[failure_classes == cls] = rate

    # Sigmoid factors (numpy handles vectorized exp)
    budget_factor = 1.0 / (1.0 + np.exp(-15.0 * (budget_remaining - 0.15)))
    deadline_factor = 1.0 / (1.0 + np.exp(-20.0 * (deadline_remaining - 0.10)))

    # Complexity and skill
    complexity_factor = 1.0 / (1.0 + 0.02 * remaining_subtasks)
    skill_factor = 0.4 + 0.6 * fallback_skill

    p = base * budget_factor * deadline_factor * complexity_factor * skill_factor
    return np.clip(p, 0.0, 1.0)


def simulate_outcomes(probabilities: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Given recovery probabilities, simulate binary outcomes."""
    return rng.random(len(probabilities)) < probabilities
