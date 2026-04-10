"""CAIRN recovery score formula and routing logic."""

import numpy as np
from simulation.config import DEFAULT_CLASS_WEIGHTS, DEFAULT_WEIGHTS


def recovery_score(
    failure_class: str,
    budget_remaining: float,
    deadline_remaining: float,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    class_weights: dict[str, float] = None,
) -> float:
    """Compute CAIRN recovery score (Whitepaper V2, Equation 1)."""
    if class_weights is None:
        class_weights = DEFAULT_CLASS_WEIGHTS
    w_f, w_b, w_d = weights
    F = class_weights[failure_class]
    return w_f * F + w_b * budget_remaining + w_d * deadline_remaining


def recovery_score_vectorized(
    failure_classes: np.ndarray,
    budget_remaining: np.ndarray,
    deadline_remaining: np.ndarray,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    class_weights: dict[str, float] = None,
) -> np.ndarray:
    """Vectorized score computation for batch evaluation."""
    if class_weights is None:
        class_weights = DEFAULT_CLASS_WEIGHTS
    w_f, w_b, w_d = weights

    F = np.zeros(len(failure_classes))
    for cls, weight in class_weights.items():
        F[failure_classes == cls] = weight

    return w_f * F + w_b * budget_remaining + w_d * deadline_remaining


##############################################################################
# Equation 2: Piecewise-Linear with Interaction Term
##############################################################################

# Default Equation 2 parameters
EQ2_DEFAULTS = {
    "w_f": 0.30,
    "w_b": 0.20,
    "w_d": 0.35,
    "w_int": 0.15,
    "b_crit": 0.15,
    "d_crit": 0.10,
    "penalty_b": 0.30,
    "penalty_d": 0.25,
}


def piecewise_adjust(value: np.ndarray, crit: float, penalty: float) -> np.ndarray:
    """Apply piecewise penalty below critical threshold."""
    adj = value.copy()
    below = value < crit
    adj[below] = value[below] * penalty
    return adj


def recovery_score_eq2_vectorized(
    failure_classes: np.ndarray,
    budget_remaining: np.ndarray,
    deadline_remaining: np.ndarray,
    class_weights: dict[str, float] = None,
    params: dict = None,
) -> np.ndarray:
    """Equation 2: Piecewise-linear with interaction term.

    r = w_f*F + w_b*B_adj + w_d*D_adj + w_int*B_adj*D_adj
    Where B_adj and D_adj apply piecewise penalties below critical thresholds.
    """
    if class_weights is None:
        class_weights = DEFAULT_CLASS_WEIGHTS
    if params is None:
        params = EQ2_DEFAULTS

    F = np.zeros(len(failure_classes))
    for cls, weight in class_weights.items():
        F[failure_classes == cls] = weight

    B_adj = piecewise_adjust(budget_remaining, params["b_crit"], params["penalty_b"])
    D_adj = piecewise_adjust(deadline_remaining, params["d_crit"], params["penalty_d"])

    score = (params["w_f"] * F
             + params["w_b"] * B_adj
             + params["w_d"] * D_adj
             + params["w_int"] * B_adj * D_adj)

    return np.clip(score, 0.0, 1.0)


##############################################################################
# Equation 3: 5-Variable Formula (adds complexity + fallback skill)
##############################################################################

EQ3_DEFAULTS = {
    "w_f": 0.25,
    "w_b": 0.20,
    "w_d": 0.25,
    "w_c": 0.15,   # complexity factor weight
    "w_s": 0.15,   # fallback skill weight
}


def recovery_score_eq3_vectorized(
    failure_classes: np.ndarray,
    budget_remaining: np.ndarray,
    deadline_remaining: np.ndarray,
    remaining_subtasks: np.ndarray,
    fallback_skill: np.ndarray,
    class_weights: dict[str, float] = None,
    params: dict = None,
) -> np.ndarray:
    """Equation 3: 5-variable linear formula.

    r = w_f*F + w_b*B + w_d*D + w_c*C + w_s*S
    Where C = 1/(1 + 0.02*remaining_subtasks) and S = fallback_skill.
    """
    if class_weights is None:
        class_weights = DEFAULT_CLASS_WEIGHTS
    if params is None:
        params = EQ3_DEFAULTS

    F = np.zeros(len(failure_classes))
    for cls, weight in class_weights.items():
        F[failure_classes == cls] = weight

    # Complexity factor: 1/(1+0.02*n) — higher when fewer subtasks remain
    C = 1.0 / (1.0 + 0.02 * remaining_subtasks)

    # Fallback skill: direct pass-through (already 0.0-1.0)
    S = fallback_skill

    score = (params["w_f"] * F
             + params["w_b"] * budget_remaining
             + params["w_d"] * deadline_remaining
             + params["w_c"] * C
             + params["w_s"] * S)

    return np.clip(score, 0.0, 1.0)


##############################################################################
# Equation 4: Multiplicative Formula
##############################################################################

EQ4_DEFAULTS = {
    "a": 0.50,  # F exponent
    "b": 0.25,  # B exponent
    "c": 0.25,  # D exponent
}


def recovery_score_eq4_multiplicative(
    failure_classes: np.ndarray,
    budget_remaining: np.ndarray,
    deadline_remaining: np.ndarray,
    class_weights: dict[str, float] = None,
    params: dict = None,
) -> np.ndarray:
    """Equation 4: Multiplicative formula — r = F^a × B^b × D^c."""
    if class_weights is None:
        class_weights = DEFAULT_CLASS_WEIGHTS
    if params is None:
        params = EQ4_DEFAULTS

    F = np.zeros(len(failure_classes))
    for cls, weight in class_weights.items():
        F[failure_classes == cls] = weight

    # Clamp to avoid log(0); minimum 1e-6
    F_safe = np.maximum(F, 1e-6)
    B_safe = np.maximum(budget_remaining, 1e-6)
    D_safe = np.maximum(deadline_remaining, 1e-6)

    score = (F_safe ** params["a"]) * (B_safe ** params["b"]) * (D_safe ** params["c"])
    return np.clip(score, 0.0, 1.0)


##############################################################################
# Equation 4b: Hybrid (alpha × linear + (1-alpha) × multiplicative)
##############################################################################

EQ4H_DEFAULTS = {
    "alpha": 0.50,  # blend: 0=pure multiplicative, 1=pure linear
    "w_f": 0.30, "w_b": 0.25, "w_d": 0.45,  # linear weights
    "a": 0.50, "b": 0.25, "c": 0.25,         # multiplicative exponents
}


def recovery_score_eq4_hybrid(
    failure_classes: np.ndarray,
    budget_remaining: np.ndarray,
    deadline_remaining: np.ndarray,
    class_weights: dict[str, float] = None,
    params: dict = None,
) -> np.ndarray:
    """Equation 4b: Hybrid — blend of linear and multiplicative."""
    if class_weights is None:
        class_weights = DEFAULT_CLASS_WEIGHTS
    if params is None:
        params = EQ4H_DEFAULTS

    F = np.zeros(len(failure_classes))
    for cls, weight in class_weights.items():
        F[failure_classes == cls] = weight

    # Linear component
    linear = params["w_f"] * F + params["w_b"] * budget_remaining + params["w_d"] * deadline_remaining

    # Multiplicative component
    F_safe = np.maximum(F, 1e-6)
    B_safe = np.maximum(budget_remaining, 1e-6)
    D_safe = np.maximum(deadline_remaining, 1e-6)
    mult = (F_safe ** params["a"]) * (B_safe ** params["b"]) * (D_safe ** params["c"])

    score = params["alpha"] * linear + (1.0 - params["alpha"]) * mult
    return np.clip(score, 0.0, 1.0)


def route(score: float, upper: float = 0.6, lower: float = 0.3) -> str:
    """Map score to routing tier."""
    if score >= upper:
        return "RECOVERING_FULL"
    elif score >= lower:
        return "RECOVERING_REDUCED"
    else:
        return "DISPUTED"


def route_vectorized(
    scores: np.ndarray, upper: float = 0.6, lower: float = 0.3
) -> np.ndarray:
    """Vectorized routing for batch evaluation."""
    routes = np.full(len(scores), "DISPUTED", dtype="U20")
    routes[scores >= lower] = "RECOVERING_REDUCED"
    routes[scores >= upper] = "RECOVERING_FULL"
    return routes
