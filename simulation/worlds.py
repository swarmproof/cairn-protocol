"""Alternative ground-truth "worlds" for the misspecification study.

Each world maps the same event variables as ``recovery.ground_truth_vectorized``
(failure class, budget remaining B, deadline remaining D, remaining_subtasks,
fallback_skill) to a probability of recovery success in [0, 1]. Class base
rates come from ``config.GROUND_TRUTH_BASE_RATES`` in every world.

Shared factor notation used in the docstrings below:

    base   = GROUND_TRUTH_BASE_RATES[class]      (0.92 / 0.48 / 0.08)
    sig(x; k, c) = 1 / (1 + exp(-k · (x - c)))
    sB     = sig(B; 15, 0.15)
    sD     = sig(D; 20, 0.10)
    C      = 1 / (1 + 0.02 · remaining_subtasks)
    S      = 0.4 + 0.6 · fallback_skill

Offsets and scale constants marked "calibrated" were set once so that the
world's mean success probability matches the multiplicative world's mean on a
reference sample (``generate_events_vectorized(400_000, default_rng(0))``);
see ``calibration_reference_mean``. They are fixed constants, not re-fit per run.

Two worlds take keyword-only extras:
    heavy_tail    — ``rng`` (numpy Generator) for the per-event shock draw.
    nonstationary — ``t`` (event position in [0, 1]; defaults to
                    ``linspace(0, 1, n)``, i.e. array order is time order).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from simulation.config import GROUND_TRUTH_BASE_RATES
from simulation.recovery import ground_truth_vectorized

# Calibrated constants (see module docstring).
ADDITIVE_OFFSET = -0.5074
THRESHOLD_SCALE = 0.7872
INTERACTION_OFFSET = -0.4550

HEAVY_TAIL_DF = 2.0
HEAVY_TAIL_SCALE = 0.5

# Nonstationary drift: parameter value at t=0 -> value at t=1 (linear in t).
NONSTATIONARY_BASE_END = {"LIVENESS": 0.80, "RESOURCE": 0.62, "LOGIC": 0.15}
NONSTATIONARY_B_CENTER = (0.15, 0.35)
NONSTATIONARY_B_SLOPE = (15.0, 8.0)
NONSTATIONARY_D_CENTER = (0.10, 0.25)
NONSTATIONARY_D_SLOPE = (20.0, 10.0)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _base_rates(failure_classes: np.ndarray, rates: dict[str, float]) -> np.ndarray:
    base = np.zeros(len(failure_classes))
    for cls, rate in rates.items():
        base[failure_classes == cls] = rate
    return base


def _factors(failure_classes, budget_remaining, deadline_remaining,
             remaining_subtasks, fallback_skill):
    base = _base_rates(failure_classes, GROUND_TRUTH_BASE_RATES)
    sB = _sigmoid(15.0 * (budget_remaining - 0.15))
    sD = _sigmoid(20.0 * (deadline_remaining - 0.10))
    C = 1.0 / (1.0 + 0.02 * remaining_subtasks)
    S = 0.4 + 0.6 * fallback_skill
    return base, sB, sD, C, S


def multiplicative(failure_classes, budget_remaining, deadline_remaining,
                   remaining_subtasks, fallback_skill) -> np.ndarray:
    """The existing ground truth (delegates to recovery.ground_truth_vectorized).

    p = base · sB · sD · C · S
    """
    return ground_truth_vectorized(
        failure_classes, budget_remaining, deadline_remaining,
        remaining_subtasks, fallback_skill,
    )


def additive(failure_classes, budget_remaining, deadline_remaining,
             remaining_subtasks, fallback_skill) -> np.ndarray:
    """Weighted sum of the same monotone factors, clipped to [0, 1].

    p = clip(0.60·base + 0.20·sB + 0.15·sD + 0.15·C + 0.10·S + k, 0, 1)
    k = ADDITIVE_OFFSET (calibrated).
    """
    base, sB, sD, C, S = _factors(failure_classes, budget_remaining, deadline_remaining,
                                  remaining_subtasks, fallback_skill)
    p = 0.60 * base + 0.20 * sB + 0.15 * sD + 0.15 * C + 0.10 * S + ADDITIVE_OFFSET
    return np.clip(p, 0.0, 1.0)


def threshold(failure_classes, budget_remaining, deadline_remaining,
              remaining_subtasks, fallback_skill) -> np.ndarray:
    """Near-step hard minimums on B and D; flat otherwise.

    p = κ · base · sig(B; 200, 0.15) · sig(D; 200, 0.10)
    κ = THRESHOLD_SCALE (calibrated). remaining_subtasks and fallback_skill
    have no effect in this world.
    """
    base = _base_rates(failure_classes, GROUND_TRUTH_BASE_RATES)
    hB = _sigmoid(200.0 * (budget_remaining - 0.15))
    hD = _sigmoid(200.0 * (deadline_remaining - 0.10))
    return np.clip(THRESHOLD_SCALE * base * hB * hD, 0.0, 1.0)


def interaction(failure_classes, budget_remaining, deadline_remaining,
                remaining_subtasks, fallback_skill) -> np.ndarray:
    """Additive main effects plus explicit pairwise interactions, clipped to [0, 1].

    p = clip(0.45·base + 0.10·sB + 0.05·sD + 0.05·C + 0.05·S
             + 0.25·sB·S + 0.20·sD·C + k, 0, 1)
    k = INTERACTION_OFFSET (calibrated). The interactions are budget × skill
    and deadline × complexity.
    """
    base, sB, sD, C, S = _factors(failure_classes, budget_remaining, deadline_remaining,
                                  remaining_subtasks, fallback_skill)
    p = (0.45 * base + 0.10 * sB + 0.05 * sD + 0.05 * C + 0.05 * S
         + 0.25 * sB * S + 0.20 * sD * C + INTERACTION_OFFSET)
    return np.clip(p, 0.0, 1.0)


def heavy_tail(failure_classes, budget_remaining, deadline_remaining,
               remaining_subtasks, fallback_skill, *,
               rng: np.random.Generator | None = None) -> np.ndarray:
    """Multiplicative core with a heavy-tailed per-event shock on the log-odds.

    p = sigmoid(logit(clip(p_mult, 1e-6, 1 - 1e-6)) + s · ε),  ε ~ Student-t(ν)
    s = HEAVY_TAIL_SCALE (0.5), ν = HEAVY_TAIL_DF (2). p_mult is the
    multiplicative world. The shock is independent of all event variables and
    is not observable to any routing rule. Not re-calibrated: the mean differs
    slightly from the multiplicative world's.
    """
    if rng is None:
        rng = np.random.default_rng(0)
    p_mult = multiplicative(failure_classes, budget_remaining, deadline_remaining,
                            remaining_subtasks, fallback_skill)
    p_mult = np.clip(p_mult, 1e-6, 1.0 - 1e-6)
    eps = rng.standard_t(HEAVY_TAIL_DF, size=len(p_mult))
    logit = np.log(p_mult) - np.log1p(-p_mult)
    return _sigmoid(logit + HEAVY_TAIL_SCALE * eps)


def nonstationary(failure_classes, budget_remaining, deadline_remaining,
                  remaining_subtasks, fallback_skill, *,
                  t: np.ndarray | None = None) -> np.ndarray:
    """Multiplicative form whose base rates and B/D sensitivities drift over time.

    With t ∈ [0, 1] the event's position in the stream and lerp(a, b) = a + (b - a)·t:

    p = base_c(t) · sig(B; kB(t), cB(t)) · sig(D; kD(t), cD(t)) · C · S
        base_c(t): LIVENESS 0.92→0.80, RESOURCE 0.48→0.62, LOGIC 0.08→0.15
        cB(t): 0.15→0.35   kB(t): 15→8
        cD(t): 0.10→0.25   kD(t): 20→10

    At t = 0 this equals the multiplicative world. The study fits on the
    first half of the stream and evaluates on the second half.
    """
    n = len(failure_classes)
    if t is None:
        t = np.linspace(0.0, 1.0, n) if n > 1 else np.zeros(n)
    t = np.asarray(t, dtype=float)

    def lerp(pair):
        a, b = pair
        return a + (b - a) * t

    base0 = _base_rates(failure_classes, GROUND_TRUTH_BASE_RATES)
    base1 = _base_rates(failure_classes, NONSTATIONARY_BASE_END)
    base = base0 + (base1 - base0) * t
    sB = _sigmoid(lerp(NONSTATIONARY_B_SLOPE) * (budget_remaining - lerp(NONSTATIONARY_B_CENTER)))
    sD = _sigmoid(lerp(NONSTATIONARY_D_SLOPE) * (deadline_remaining - lerp(NONSTATIONARY_D_CENTER)))
    C = 1.0 / (1.0 + 0.02 * remaining_subtasks)
    S = 0.4 + 0.6 * fallback_skill
    return np.clip(base * sB * sD * C * S, 0.0, 1.0)


WORLDS: dict[str, Callable[..., np.ndarray]] = {
    "multiplicative": multiplicative,
    "additive": additive,
    "threshold": threshold,
    "interaction": interaction,
    "heavy_tail": heavy_tail,
    "nonstationary": nonstationary,
}


def world_probabilities(
    name: str,
    events: dict[str, np.ndarray],
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Evaluate world ``name`` on an event dict from generate_events_vectorized."""
    fn = WORLDS[name]
    args = (
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        events["remaining_subtasks"], events["fallback_skill"],
    )
    if name == "heavy_tail":
        return fn(*args, rng=rng)
    return fn(*args)


def calibration_reference_mean(name: str, n: int = 400_000) -> float:
    """Mean success probability of a world on the fixed calibration sample."""
    from simulation.generator import generate_events_vectorized

    events = generate_events_vectorized(n, np.random.default_rng(0))
    return float(world_probabilities(name, events, rng=np.random.default_rng(1)).mean())
