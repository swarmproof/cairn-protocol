#!/usr/bin/env python3
"""Run 2: CAIRN recovery score calibration — Equation 2 (piecewise + interaction).

Experiments 6-8 from PRD-03.
"""

import time
import json
import numpy as np
from pathlib import Path
from itertools import product

from simulation.config import (
    SEED, TOTAL_BASELINE_TRIALS, DEFAULT_CLASS_WEIGHTS,
    GROUND_TRUTH_BASE_RATES,
)
from simulation.generator import generate_events_vectorized
from simulation.recovery import ground_truth_vectorized, simulate_outcomes
from simulation.scorer import (
    recovery_score_vectorized, recovery_score_eq2_vectorized,
    route_vectorized, EQ2_DEFAULTS,
)
from simulation.optimizer import evaluate, EvalResult, compute_f1

FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


def evaluate_eq2(
    events: dict[str, np.ndarray],
    outcomes: np.ndarray,
    class_weights: dict[str, float] = None,
    params: dict = None,
    upper: float = 0.45,
    lower: float = 0.40,
) -> EvalResult:
    """Evaluate Equation 2 parameters."""
    if params is None:
        params = EQ2_DEFAULTS
    if class_weights is None:
        class_weights = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    scores = recovery_score_eq2_vectorized(
        events["failure_class"],
        events["budget_remaining"],
        events["deadline_remaining"],
        class_weights=class_weights,
        params=params,
    )

    routes = route_vectorized(scores, upper=upper, lower=lower)

    routed_to_recover = (routes == "RECOVERING_FULL") | (routes == "RECOVERING_REDUCED")
    routed_to_dispute = routes == "DISPUTED"

    false_positives = routed_to_recover & ~outcomes
    false_negatives = routed_to_dispute & outcomes

    n = len(outcomes)
    n_misrouted = false_positives.sum() + false_negatives.sum()

    fp_rate = false_positives.sum() / routed_to_recover.sum() if routed_to_recover.sum() > 0 else 0.0
    fn_rate = false_negatives.sum() / routed_to_dispute.sum() if routed_to_dispute.sum() > 0 else 0.0

    is_full = routes == "RECOVERING_FULL"
    is_reduced = routes == "RECOVERING_REDUCED"
    is_disputed = routes == "DISPUTED"

    tp_full = (is_full & outcomes).sum()
    fp_full = (is_full & ~outcomes).sum()
    tp_reduced = (is_reduced & outcomes).sum()
    fp_reduced = (is_reduced & ~outcomes).sum()
    tp_disputed = (is_disputed & ~outcomes).sum()
    fp_disputed = (is_disputed & outcomes).sum()
    fn_disputed = (~is_disputed & ~outcomes).sum()

    return EvalResult(
        weights=(params["w_f"], params["w_b"], params["w_d"]),
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


def experiment_6_eq2_grid(events, outcomes):
    """Experiment 6: Grid search over Equation 2 parameters (RQ6, RQ7)."""
    print("=" * 70)
    print("EXPERIMENT 6: Equation 2 — Piecewise + Interaction Grid Search")
    print("=" * 70)

    # Best class weights from Run 1
    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    # Grid over the new parameters
    w_int_range = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    b_crit_range = [0.10, 0.15, 0.20, 0.25]
    d_crit_range = [0.05, 0.10, 0.15, 0.20]
    penalty_b_range = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    penalty_d_range = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]

    # Base weights from Run 1 optimal
    base_w_f, base_w_b = 0.30, 0.20

    # Threshold range (narrow, informed by Run 1)
    upper_range = [0.40, 0.45, 0.50, 0.55]
    lower_range = [0.30, 0.35, 0.40]

    t0 = time.time()

    # Phase A: Fix weights, sweep piecewise params + interaction
    print("\nPhase A: Sweeping piecewise parameters + interaction weight...")
    phase_a_results = []

    for b_crit, d_crit, penalty_b, penalty_d, w_int in product(
        b_crit_range, d_crit_range, penalty_b_range, penalty_d_range, w_int_range
    ):
        w_d = 1.0 - base_w_f - base_w_b - w_int
        if w_d < 0.05:
            continue

        params = {
            "w_f": base_w_f, "w_b": base_w_b, "w_d": round(w_d, 2), "w_int": w_int,
            "b_crit": b_crit, "d_crit": d_crit,
            "penalty_b": penalty_b, "penalty_d": penalty_d,
        }

        result = evaluate_eq2(events, outcomes, class_weights=best_cw, params=params)
        phase_a_results.append((params, result))

    phase_a_results.sort(key=lambda x: x[1].misrouting_rate)
    elapsed_a = time.time() - t0

    print(f"  Evaluated {len(phase_a_results)} combinations in {elapsed_a:.1f}s")
    print(f"\n  Top 5 parameter sets:")
    print(f"  {'Rank':>4} {'w_int':>5} {'b_crit':>6} {'d_crit':>6} {'pen_b':>5} {'pen_d':>5} {'w_d':>5} {'Misroute':>9} {'FP':>8} {'FN':>8}")
    print("  " + "-" * 70)
    for i, (p, r) in enumerate(phase_a_results[:5]):
        print(f"  {i+1:4d} {p['w_int']:5.2f} {p['b_crit']:6.2f} {p['d_crit']:6.2f} {p['penalty_b']:5.2f} {p['penalty_d']:5.2f} {p['w_d']:5.2f} {r.misrouting_rate:9.2%} {r.false_positive_rate:8.2%} {r.false_negative_rate:8.2%}")

    best_params = phase_a_results[0][0]
    best_result_a = phase_a_results[0][1]

    # Phase B: Sweep thresholds with best params
    print(f"\nPhase B: Sweeping thresholds with best piecewise params...")
    phase_b_results = []

    for upper, lower in product(upper_range, lower_range):
        if lower >= upper:
            continue
        result = evaluate_eq2(events, outcomes, class_weights=best_cw,
                              params=best_params, upper=upper, lower=lower)
        phase_b_results.append((upper, lower, result))

    phase_b_results.sort(key=lambda x: x[2].misrouting_rate)

    print(f"  Evaluated {len(phase_b_results)} threshold combinations")
    print(f"\n  Top 5 threshold pairs:")
    print(f"  {'Rank':>4} {'Upper':>6} {'Lower':>6} {'Misroute':>9} {'FP':>8} {'FN':>8} {'F1-F':>5} {'F1-R':>5} {'F1-D':>5}")
    print("  " + "-" * 65)
    for i, (u, l, r) in enumerate(phase_b_results[:5]):
        print(f"  {i+1:4d} {u:6.2f} {l:6.2f} {r.misrouting_rate:9.2%} {r.false_positive_rate:8.2%} {r.false_negative_rate:8.2%} {r.f1_full:5.3f} {r.f1_reduced:5.3f} {r.f1_disputed:5.3f}")

    best_upper, best_lower, best_result_b = phase_b_results[0]
    elapsed_total = time.time() - t0

    print(f"\n  Total Experiment 6 time: {elapsed_total:.1f}s")
    print(f"  Best Eq2 misrouting: {best_result_b.misrouting_rate:.2%}")
    print(f"  Best params: {best_params}")
    print(f"  Best thresholds: upper={best_upper}, lower={best_lower}")

    return best_params, best_upper, best_lower, best_result_b, phase_a_results, phase_b_results


def experiment_7_ablation(events, outcomes, best_params, best_upper, best_lower):
    """Experiment 7 (RQ8): Ablation — with vs without interaction term."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 7: Ablation — Interaction Term Contribution")
    print("=" * 70)

    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    # With interaction (full Eq2)
    result_with = evaluate_eq2(events, outcomes, class_weights=best_cw,
                               params=best_params, upper=best_upper, lower=best_lower)

    # Without interaction (Eq2 but w_int=0, redistribute to w_d)
    params_no_int = dict(best_params)
    params_no_int["w_d"] = params_no_int["w_d"] + params_no_int["w_int"]
    params_no_int["w_int"] = 0.0
    result_without = evaluate_eq2(events, outcomes, class_weights=best_cw,
                                  params=params_no_int, upper=best_upper, lower=best_lower)

    # Piecewise only (no interaction, no piecewise = just linear with best Run 1 params)
    from simulation.optimizer import evaluate as evaluate_eq1
    result_linear = evaluate_eq1(
        events, outcomes,
        weights=(0.30, 0.25, 0.45),
        class_weights=best_cw,
        upper=best_upper, lower=best_lower,
    )

    print(f"\n  {'Configuration':>35} {'Misroute':>9} {'FP Rate':>8} {'FN Rate':>8}")
    print("  " + "-" * 65)
    print(f"  {'Eq1 Linear (Run 1 optimal)':>35} {result_linear.misrouting_rate:9.2%} {result_linear.false_positive_rate:8.2%} {result_linear.false_negative_rate:8.2%}")
    print(f"  {'Eq2 Piecewise only (w_int=0)':>35} {result_without.misrouting_rate:9.2%} {result_without.false_positive_rate:8.2%} {result_without.false_negative_rate:8.2%}")
    print(f"  {'Eq2 Full (piecewise + interaction)':>35} {result_with.misrouting_rate:9.2%} {result_with.false_positive_rate:8.2%} {result_with.false_negative_rate:8.2%}")

    piecewise_contrib = result_linear.misrouting_rate - result_without.misrouting_rate
    interaction_contrib = result_without.misrouting_rate - result_with.misrouting_rate
    total_improvement = result_linear.misrouting_rate - result_with.misrouting_rate

    print(f"\n  Piecewise contribution:    {piecewise_contrib:+.2%} pp")
    print(f"  Interaction contribution:  {interaction_contrib:+.2%} pp")
    print(f"  Total Eq1 → Eq2:          {total_improvement:+.2%} pp")

    return {
        "eq1_linear": result_linear.misrouting_rate,
        "eq2_piecewise_only": result_without.misrouting_rate,
        "eq2_full": result_with.misrouting_rate,
        "piecewise_contribution_pp": piecewise_contrib,
        "interaction_contribution_pp": interaction_contrib,
        "total_improvement_pp": total_improvement,
    }


def experiment_8_sensitivity_eq2(events, outcomes, best_params, best_upper, best_lower):
    """Experiment 8: Sensitivity of Eq2 parameters."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 8: Equation 2 Sensitivity Analysis")
    print("=" * 70)

    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}
    baseline = evaluate_eq2(events, outcomes, class_weights=best_cw,
                            params=best_params, upper=best_upper, lower=best_lower)
    base_rate = baseline.misrouting_rate

    param_names = ["w_f", "w_b", "w_d", "w_int", "b_crit", "d_crit", "penalty_b", "penalty_d"]
    perturbations = [0.10, 0.20]

    print(f"\n  Baseline misrouting: {base_rate:.2%}")
    print(f"\n  {'Parameter':>12} {'−20%':>8} {'−10%':>8} {'+10%':>8} {'+20%':>8}")
    print("  " + "-" * 48)

    sensitivity = {}
    for name in param_names:
        deltas = {}
        for p in perturbations:
            for sign in [-1, 1]:
                test_params = dict(best_params)
                test_params[name] = test_params[name] * (1.0 + sign * p)

                # Re-normalize weights if needed
                if name in ("w_f", "w_b", "w_d", "w_int"):
                    w_sum = test_params["w_f"] + test_params["w_b"] + test_params["w_d"] + test_params["w_int"]
                    if w_sum > 0:
                        for w in ("w_f", "w_b", "w_d", "w_int"):
                            test_params[w] /= w_sum

                result = evaluate_eq2(events, outcomes, class_weights=best_cw,
                                      params=test_params, upper=best_upper, lower=best_lower)
                deltas[sign * p] = result.misrouting_rate - base_rate

        sensitivity[name] = deltas
        print(f"  {name:>12} {deltas.get(-0.20, 0):+7.2%} {deltas.get(-0.10, 0):+7.2%} {deltas.get(0.10, 0):+7.2%} {deltas.get(0.20, 0):+7.2%}")

    max_10 = max(abs(v) for d in sensitivity.values() for k, v in d.items() if abs(k) == 0.10)
    print(f"\n  Max change at ±10%: {max_10:.2%}")
    print(f"  Stability (< 5pp): {'PASS' if max_10 < 0.05 else 'FAIL'}")

    return {"baseline": base_rate, "sensitivity": sensitivity, "max_10pct": max_10}


def generate_eq2_figures(events, outcomes, best_params, best_upper, best_lower, phase_a_results):
    """Generate Equation 2 publication figures."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available — skipping figures")
        return

    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    # Fig 7: Eq1 vs Eq2 comparison bar chart
    fig, ax = plt.subplots(figsize=(10, 6))

    scores_eq1 = recovery_score_vectorized(
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        weights=(0.30, 0.25, 0.45), class_weights=best_cw,
    )
    scores_eq2 = recovery_score_eq2_vectorized(
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        class_weights=best_cw, params=best_params,
    )

    routes_eq1 = route_vectorized(scores_eq1, upper=best_upper, lower=best_lower)
    routes_eq2 = route_vectorized(scores_eq2, upper=best_upper, lower=best_lower)

    tiers = ["RECOVERING_FULL", "RECOVERING_REDUCED", "DISPUTED"]
    labels = ["FULL", "REDUCED", "DISPUTED"]
    x = np.arange(len(tiers))
    width = 0.35

    eq1_counts = [(routes_eq1 == t).sum() for t in tiers]
    eq2_counts = [(routes_eq2 == t).sum() for t in tiers]

    ax.bar(x - width/2, eq1_counts, width, label="Eq. 1 (Linear)", color="#3498db", alpha=0.8)
    ax.bar(x + width/2, eq2_counts, width, label="Eq. 2 (Piecewise)", color="#e74c3c", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Number of Tasks")
    ax.set_title("Routing Distribution: Equation 1 vs Equation 2")
    ax.legend()

    for i, (c1, c2) in enumerate(zip(eq1_counts, eq2_counts)):
        ax.text(i - width/2, c1 + 500, f"{c1:,}", ha="center", fontsize=9)
        ax.text(i + width/2, c2 + 500, f"{c2:,}", ha="center", fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig7_eq1_vs_eq2_routing.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig7_eq1_vs_eq2_routing.svg")
    plt.close()
    print("  Generated: fig7_eq1_vs_eq2_routing.png/svg")

    # Fig 8: Score scatter — Eq1 vs Eq2 colored by outcome
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    colors = np.where(outcomes, "#2ecc71", "#e74c3c")
    ax1.scatter(scores_eq1[outcomes], scores_eq2[outcomes], alpha=0.1, c="#2ecc71", s=3, label="Recovery succeeded")
    ax1.scatter(scores_eq1[~outcomes], scores_eq2[~outcomes], alpha=0.1, c="#e74c3c", s=3, label="Recovery failed")
    ax1.axhline(y=best_upper, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax1.axhline(y=best_lower, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax1.axvline(x=best_upper, color="black", linestyle="--", linewidth=0.8, alpha=0.5)
    ax1.axvline(x=best_lower, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    ax1.set_xlabel("Eq. 1 Score")
    ax1.set_ylabel("Eq. 2 Score")
    ax1.set_title("Score Comparison by Recovery Outcome")
    ax1.legend(markerscale=5)

    # Fig 8b: Eq2 score distributions by class
    for cls, color in zip(["LIVENESS", "RESOURCE", "LOGIC"], ["#2ecc71", "#f39c12", "#e74c3c"]):
        mask = events["failure_class"] == cls
        ax2.hist(scores_eq2[mask], bins=40, alpha=0.6, label=cls, color=color, density=True)
    ax2.axvline(x=best_upper, color="black", linestyle="--", linewidth=1.5, label=f"Upper ({best_upper})")
    ax2.axvline(x=best_lower, color="gray", linestyle="--", linewidth=1.5, label=f"Lower ({best_lower})")
    ax2.set_xlabel("Eq. 2 Recovery Score")
    ax2.set_ylabel("Density")
    ax2.set_title("Eq. 2 Score Distributions by Failure Class")
    ax2.legend()

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig8_eq2_score_analysis.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig8_eq2_score_analysis.svg")
    plt.close()
    print("  Generated: fig8_eq2_score_analysis.png/svg")

    # Fig 9: Confusion matrix for Eq2
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    for ax, routes, scores, title in [
        (ax1, routes_eq1, scores_eq1, "Eq. 1 (Linear)"),
        (ax2, routes_eq2, scores_eq2, "Eq. 2 (Piecewise + Interaction)"),
    ]:
        matrix = np.zeros((3, 2))
        for i, tier in enumerate(tiers):
            mask = routes == tier
            matrix[i, 0] = (mask & outcomes).sum()
            matrix[i, 1] = (mask & ~outcomes).sum()
        matrix_pct = matrix / matrix.sum() * 100

        im = ax.imshow(matrix_pct, cmap="Blues", aspect="auto")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Succeeded", "Failed"])
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(["FULL", "REDUCED", "DISPUTED"])
        ax.set_ylabel("Routing Decision")
        ax.set_xlabel("Actual Outcome")
        ax.set_title(title)
        for i in range(3):
            for j in range(2):
                color = "white" if matrix_pct[i, j] > 15 else "black"
                ax.text(j, i, f"{matrix_pct[i,j]:.1f}%\n({int(matrix[i,j]):,})",
                        ha="center", va="center", fontsize=10, color=color)

    plt.suptitle("Routing Confusion Matrix Comparison", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig9_eq2_confusion_comparison.png", dpi=150, bbox_inches="tight")
    plt.savefig(FIGURES_DIR / "fig9_eq2_confusion_comparison.svg", bbox_inches="tight")
    plt.close()
    print("  Generated: fig9_eq2_confusion_comparison.png/svg")

    # Fig 10: Improvement waterfall
    fig, ax = plt.subplots(figsize=(10, 6))
    categories = [
        "Current\n(Eq1 0.5/0.3/0.2)",
        "Optimized Eq1\n(0.3/0.25/0.45)",
        "+ Class weights\n(0.7/0.3/0.0)",
        "+ Thresholds\n(0.45/0.40)",
        "+ Piecewise\n(cliffs)",
        "+ Interaction\n(B×D)",
    ]

    # Load Run 1 baseline from results.json
    try:
        with open(Path(__file__).parent / "results.json") as f:
            run1 = json.load(f)
        val_current = run1["baseline"]["misrouting_rate"]
    except Exception:
        val_current = 0.4756

    # Reconstruct intermediate values
    result_opt_weights = evaluate_eq2(
        events, outcomes,
        class_weights={"LIVENESS": 0.9, "RESOURCE": 0.5, "LOGIC": 0.1},
        params={"w_f": 0.30, "w_b": 0.25, "w_d": 0.45, "w_int": 0.0,
                "b_crit": 0.0, "d_crit": 0.0, "penalty_b": 1.0, "penalty_d": 1.0},
        upper=0.6, lower=0.3,
    )
    result_opt_cw = evaluate_eq2(
        events, outcomes,
        class_weights=best_cw,
        params={"w_f": 0.30, "w_b": 0.25, "w_d": 0.45, "w_int": 0.0,
                "b_crit": 0.0, "d_crit": 0.0, "penalty_b": 1.0, "penalty_d": 1.0},
        upper=0.6, lower=0.3,
    )
    result_opt_thresh = evaluate_eq2(
        events, outcomes,
        class_weights=best_cw,
        params={"w_f": 0.30, "w_b": 0.25, "w_d": 0.45, "w_int": 0.0,
                "b_crit": 0.0, "d_crit": 0.0, "penalty_b": 1.0, "penalty_d": 1.0},
        upper=best_upper, lower=best_lower,
    )
    # Piecewise only (no interaction)
    params_pw_only = dict(best_params)
    params_pw_only["w_d"] = params_pw_only["w_d"] + params_pw_only["w_int"]
    params_pw_only["w_int"] = 0.0
    result_piecewise = evaluate_eq2(events, outcomes, class_weights=best_cw,
                                    params=params_pw_only, upper=best_upper, lower=best_lower)
    result_full = evaluate_eq2(events, outcomes, class_weights=best_cw,
                               params=best_params, upper=best_upper, lower=best_lower)

    values = [
        val_current,
        result_opt_weights.misrouting_rate,
        result_opt_cw.misrouting_rate,
        result_opt_thresh.misrouting_rate,
        result_piecewise.misrouting_rate,
        result_full.misrouting_rate,
    ]

    colors = ["#e74c3c"] + ["#f39c12"] * 3 + ["#2ecc71"] * 2
    ax.bar(range(len(categories)), [v * 100 for v in values], color=colors, alpha=0.8, edgecolor="black", linewidth=0.5)
    for i, v in enumerate(values):
        ax.text(i, v * 100 + 0.5, f"{v:.1%}", ha="center", fontsize=10, fontweight="bold")

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylabel("Misrouting Rate (%)")
    ax.set_title("Progressive Improvement: Current → Equation 2")
    ax.axhline(y=10, color="green", linestyle=":", linewidth=2, alpha=0.5, label="Target (<10%)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig10_improvement_waterfall.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig10_improvement_waterfall.svg")
    plt.close()
    print("  Generated: fig10_improvement_waterfall.png/svg")


def main():
    print("\n" + "=" * 70)
    print("  CAIRN RECOVERY SCORE CALIBRATION — RUN 2")
    print("  Equation 2: r = w_f*F + w_b*B_adj + w_d*D_adj + w_int*B_adj*D_adj")
    print("=" * 70)

    t_start = time.time()
    rng = np.random.default_rng(SEED)

    # Generate same event set as Run 1 for comparability
    print(f"\nSeed: {SEED} | Trials: {TOTAL_BASELINE_TRIALS:,}")
    print("Generating events (same seed as Run 1 for comparability)...")
    events = generate_events_vectorized(TOTAL_BASELINE_TRIALS, rng)
    probs = ground_truth_vectorized(
        events["failure_class"], events["budget_remaining"],
        events["deadline_remaining"], events["remaining_subtasks"],
        events["fallback_skill"],
    )
    outcomes = simulate_outcomes(probs, rng)
    print(f"Generated {TOTAL_BASELINE_TRIALS:,} events | Recovery rate: {outcomes.mean():.1%}")

    # Run 1 baseline for comparison
    from simulation.optimizer import evaluate as eval_eq1
    run1_baseline = eval_eq1(events, outcomes)
    run1_optimal = eval_eq1(events, outcomes, weights=(0.30, 0.25, 0.45),
                            class_weights={"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00},
                            upper=0.45, lower=0.40)
    print(f"\nRun 1 reference — Current params: {run1_baseline.misrouting_rate:.2%}")
    print(f"Run 1 reference — Optimal linear: {run1_optimal.misrouting_rate:.2%}")

    # Experiment 6
    best_params, best_upper, best_lower, best_result, phase_a, phase_b = experiment_6_eq2_grid(events, outcomes)

    # Experiment 7
    ablation = experiment_7_ablation(events, outcomes, best_params, best_upper, best_lower)

    # Experiment 8
    sensitivity = experiment_8_sensitivity_eq2(events, outcomes, best_params, best_upper, best_lower)

    # Summary
    print("\n" + "=" * 70)
    print("RUN 2 FINAL SUMMARY")
    print("=" * 70)
    print(f"\n  Run 1 current params:      {run1_baseline.misrouting_rate:.2%}")
    print(f"  Run 1 optimal linear:      {run1_optimal.misrouting_rate:.2%}")
    print(f"  Run 2 Eq2 optimal:         {best_result.misrouting_rate:.2%}")
    print(f"  Total improvement:         {run1_baseline.misrouting_rate - best_result.misrouting_rate:+.2%} pp")
    print(f"\n  Eq2 optimal parameters:")
    for k, v in best_params.items():
        print(f"    {k:>12}: {v}")
    print(f"    {'upper':>12}: {best_upper}")
    print(f"    {'lower':>12}: {best_lower}")

    t_total = time.time() - t_start
    print(f"\n  Total runtime: {t_total:.1f}s")

    # Generate figures
    print(f"\nGenerating publication figures...")
    generate_eq2_figures(events, outcomes, best_params, best_upper, best_lower, phase_a)

    # Save results
    results = {
        "run": 2,
        "formula": "Eq2: r = w_f*F + w_b*B_adj + w_d*D_adj + w_int*B_adj*D_adj",
        "seed": SEED,
        "total_trials": TOTAL_BASELINE_TRIALS,
        "run1_comparison": {
            "current_misrouting": run1_baseline.misrouting_rate,
            "optimal_linear_misrouting": run1_optimal.misrouting_rate,
        },
        "eq2_optimal": {
            "params": best_params,
            "class_weights": {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00},
            "thresholds": {"upper": best_upper, "lower": best_lower},
            "misrouting_rate": best_result.misrouting_rate,
            "false_positive_rate": best_result.false_positive_rate,
            "false_negative_rate": best_result.false_negative_rate,
        },
        "ablation": ablation,
        "sensitivity": {
            "max_10pct": sensitivity["max_10pct"],
        },
        "total_improvement_pp": run1_baseline.misrouting_rate - best_result.misrouting_rate,
        "runtime_seconds": t_total,
    }

    results_path = Path(__file__).parent / "results_eq2.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")
    print("Done.")


if __name__ == "__main__":
    main()
