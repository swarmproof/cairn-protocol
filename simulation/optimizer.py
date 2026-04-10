"""Grid search optimization for recovery score parameters."""

import numpy as np
from dataclasses import dataclass
from simulation.config import (
    GridSearchConfig,
    DEFAULT_CLASS_WEIGHTS,
    DEFAULT_WEIGHTS,
    DEFAULT_UPPER_THRESHOLD,
    DEFAULT_LOWER_THRESHOLD,
    TRIALS_PER_COMBO,
    SEED,
)
from simulation.generator import generate_events_vectorized
from simulation.recovery import ground_truth_vectorized, simulate_outcomes
from simulation.scorer import recovery_score_vectorized, route_vectorized


@dataclass
class EvalResult:
    weights: tuple[float, float, float]
    class_weights: dict[str, float]
    upper_threshold: float
    lower_threshold: float
    misrouting_rate: float
    false_positive_rate: float
    false_negative_rate: float
    f1_full: float
    f1_reduced: float
    f1_disputed: float
    n_trials: int


def compute_f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def evaluate(
    events: dict[str, np.ndarray],
    outcomes: np.ndarray,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    class_weights: dict[str, float] = None,
    upper: float = DEFAULT_UPPER_THRESHOLD,
    lower: float = DEFAULT_LOWER_THRESHOLD,
) -> EvalResult:
    """Evaluate a parameter set against pre-generated events and outcomes."""
    if class_weights is None:
        class_weights = DEFAULT_CLASS_WEIGHTS

    scores = recovery_score_vectorized(
        events["failure_class"],
        events["budget_remaining"],
        events["deadline_remaining"],
        weights=weights,
        class_weights=class_weights,
    )

    routes = route_vectorized(scores, upper=upper, lower=lower)

    # Misrouting analysis
    routed_to_recover = (routes == "RECOVERING_FULL") | (routes == "RECOVERING_REDUCED")
    routed_to_dispute = routes == "DISPUTED"

    # False positive: routed to recovery but recovery fails
    false_positives = routed_to_recover & ~outcomes
    # False negative: routed to dispute but recovery would have succeeded
    false_negatives = routed_to_dispute & outcomes

    n = len(outcomes)
    n_misrouted = false_positives.sum() + false_negatives.sum()

    fp_rate = false_positives.sum() / routed_to_recover.sum() if routed_to_recover.sum() > 0 else 0.0
    fn_rate = false_negatives.sum() / routed_to_dispute.sum() if routed_to_dispute.sum() > 0 else 0.0

    # F1 per tier
    # FULL tier
    is_full = routes == "RECOVERING_FULL"
    tp_full = (is_full & outcomes).sum()
    fp_full = (is_full & ~outcomes).sum()
    fn_full = (~is_full & outcomes & (scores < upper)).sum()  # would-succeed tasks not sent to FULL

    # REDUCED tier
    is_reduced = routes == "RECOVERING_REDUCED"
    tp_reduced = (is_reduced & outcomes).sum()
    fp_reduced = (is_reduced & ~outcomes).sum()

    # DISPUTED tier
    is_disputed = routes == "DISPUTED"
    tp_disputed = (is_disputed & ~outcomes).sum()  # correctly disputed (would have failed)
    fp_disputed = (is_disputed & outcomes).sum()    # incorrectly disputed (would have succeeded)
    fn_disputed = (~is_disputed & ~outcomes).sum()  # should have been disputed but wasn't

    return EvalResult(
        weights=weights,
        class_weights=dict(class_weights),
        upper_threshold=upper,
        lower_threshold=lower,
        misrouting_rate=n_misrouted / n,
        false_positive_rate=float(fp_rate),
        false_negative_rate=float(fn_rate),
        f1_full=compute_f1(int(tp_full), int(fp_full), 0),
        f1_reduced=compute_f1(int(tp_reduced), int(fp_reduced), 0),
        f1_disputed=compute_f1(int(tp_disputed), int(fp_disputed), int(fn_disputed)),
        n_trials=n,
    )


def experiment_1_weights(
    events: dict[str, np.ndarray],
    outcomes: np.ndarray,
    config: GridSearchConfig = None,
) -> list[EvalResult]:
    """Experiment 1: Grid search over formula weights."""
    if config is None:
        config = GridSearchConfig()

    results = []
    for w_f in config.w_f_range:
        for w_b in config.w_b_range:
            w_d = 1.0 - w_f - w_b
            if w_d < config.min_w_d:
                continue
            result = evaluate(events, outcomes, weights=(w_f, w_b, round(w_d, 2)))
            results.append(result)

    results.sort(key=lambda r: r.misrouting_rate)
    return results


def experiment_2_class_weights(
    events: dict[str, np.ndarray],
    outcomes: np.ndarray,
    best_weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    config: GridSearchConfig = None,
) -> list[EvalResult]:
    """Experiment 2: Grid search over failure class weights."""
    if config is None:
        config = GridSearchConfig()

    results = []
    for f_l in config.f_liveness_range:
        for f_r in config.f_resource_range:
            for f_lg in config.f_logic_range:
                cw = {"LIVENESS": f_l, "RESOURCE": f_r, "LOGIC": f_lg}
                result = evaluate(events, outcomes, weights=best_weights, class_weights=cw)
                results.append(result)

    results.sort(key=lambda r: r.misrouting_rate)
    return results


def experiment_3_thresholds(
    events: dict[str, np.ndarray],
    outcomes: np.ndarray,
    best_weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    best_class_weights: dict[str, float] = None,
    config: GridSearchConfig = None,
) -> list[EvalResult]:
    """Experiment 3: Grid search over routing thresholds."""
    if config is None:
        config = GridSearchConfig()
    if best_class_weights is None:
        best_class_weights = DEFAULT_CLASS_WEIGHTS

    results = []
    for upper in config.upper_range:
        for lower in config.lower_range:
            if lower >= upper:
                continue
            result = evaluate(
                events, outcomes,
                weights=best_weights,
                class_weights=best_class_weights,
                upper=upper,
                lower=lower,
            )
            results.append(result)

    results.sort(key=lambda r: r.misrouting_rate)
    return results


def experiment_4_sensitivity(
    events: dict[str, np.ndarray],
    outcomes: np.ndarray,
    base_weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    perturbations: tuple = (0.05, 0.10, 0.15, 0.20),
) -> dict[str, list[tuple[float, float]]]:
    """Experiment 4: Sensitivity analysis — perturb each weight ±X%."""
    baseline = evaluate(events, outcomes, weights=base_weights)
    base_rate = baseline.misrouting_rate

    results = {"w_f": [], "w_b": [], "w_d": []}
    weight_names = ["w_f", "w_b", "w_d"]

    for p in perturbations:
        for sign in [-1, 1]:
            for idx, name in enumerate(weight_names):
                w = list(base_weights)
                w[idx] *= (1.0 + sign * p)
                # Re-normalize
                total = sum(w)
                w = tuple(round(x / total, 4) for x in w)
                result = evaluate(events, outcomes, weights=w)
                delta = result.misrouting_rate - base_rate
                results[name].append((sign * p, delta))

    return {"baseline_rate": base_rate, "perturbations": results}


def experiment_5_cross_validation(
    n_trials: int = TRIALS_PER_COMBO,
    seed: int = SEED,
    best_weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    best_class_weights: dict[str, float] = None,
) -> list[dict]:
    """Experiment 5: Leave-one-task-type-out cross-validation."""
    from simulation.config import TASK_TYPES

    if best_class_weights is None:
        best_class_weights = DEFAULT_CLASS_WEIGHTS

    rng = np.random.default_rng(seed + 100)
    all_events = generate_events_vectorized(n_trials * 5, rng)
    probs = ground_truth_vectorized(
        all_events["failure_class"],
        all_events["budget_remaining"],
        all_events["deadline_remaining"],
        all_events["remaining_subtasks"],
        all_events["fallback_skill"],
    )
    outcomes = simulate_outcomes(probs, rng)

    results = []
    for held_out in TASK_TYPES:
        mask = all_events["task_type"] != held_out
        test_mask = all_events["task_type"] == held_out

        # Evaluate on held-out task type
        test_events = {k: v[test_mask] for k, v in all_events.items()}
        test_outcomes = outcomes[test_mask]

        if len(test_outcomes) == 0:
            continue

        result = evaluate(
            test_events, test_outcomes,
            weights=best_weights,
            class_weights=best_class_weights,
        )
        results.append({
            "held_out": held_out,
            "misrouting_rate": result.misrouting_rate,
            "false_positive_rate": result.false_positive_rate,
            "false_negative_rate": result.false_negative_rate,
            "n_trials": result.n_trials,
        })

    return results
