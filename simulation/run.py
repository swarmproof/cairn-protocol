#!/usr/bin/env python3
"""Run the full CAIRN recovery score calibration simulation.

Executes 5 experiments and produces results + figures.
"""

import time
import json
import numpy as np
from pathlib import Path

from simulation.config import (
    SEED, TOTAL_BASELINE_TRIALS, TRIALS_PER_COMBO,
    DEFAULT_WEIGHTS, DEFAULT_CLASS_WEIGHTS,
    DEFAULT_UPPER_THRESHOLD, DEFAULT_LOWER_THRESHOLD,
    GROUND_TRUTH_BASE_RATES, FAILURE_CLASS_DISTRIBUTION,
)
from simulation.generator import generate_events_vectorized
from simulation.recovery import ground_truth_vectorized, simulate_outcomes
from simulation.scorer import recovery_score_vectorized, route_vectorized
from simulation.optimizer import (
    evaluate, experiment_1_weights, experiment_2_class_weights,
    experiment_3_thresholds, experiment_4_sensitivity, experiment_5_cross_validation,
    GridSearchConfig,
)

FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


def validate_ground_truth(rng: np.random.Generator):
    """Validate that ground truth model produces rates consistent with literature."""
    print("=" * 70)
    print("GROUND TRUTH VALIDATION")
    print("=" * 70)

    n = 50_000
    events = generate_events_vectorized(n, rng)
    probs = ground_truth_vectorized(
        events["failure_class"],
        events["budget_remaining"],
        events["deadline_remaining"],
        events["remaining_subtasks"],
        events["fallback_skill"],
    )
    outcomes = simulate_outcomes(probs, rng)

    print(f"\nGenerated {n:,} events")
    print(f"Overall recovery rate: {outcomes.mean():.1%}")

    for cls in ["LIVENESS", "RESOURCE", "LOGIC"]:
        mask = events["failure_class"] == cls
        cls_count = mask.sum()
        cls_rate = outcomes[mask].mean() if cls_count > 0 else 0
        cls_pct = cls_count / n
        print(f"  {cls:10s}: {cls_count:6,} events ({cls_pct:.0%}) | recovery rate: {cls_rate:.1%} (base: {GROUND_TRUTH_BASE_RATES[cls]:.0%})")

    # Check base rates at high budget/deadline (should approximate base rates)
    high_resource = (events["budget_remaining"] > 0.8) & (events["deadline_remaining"] > 0.8)
    for cls in ["LIVENESS", "RESOURCE", "LOGIC"]:
        mask = (events["failure_class"] == cls) & high_resource
        if mask.sum() > 0:
            rate = outcomes[mask].mean()
            expected = GROUND_TRUTH_BASE_RATES[cls]
            print(f"  {cls:10s} at high budget/deadline: {rate:.1%} (expected ~{expected:.0%})")

    print()
    return events, probs, outcomes


def run_baseline(events, outcomes):
    """Evaluate current CAIRN parameters."""
    print("=" * 70)
    print("BASELINE: Current CAIRN Parameters")
    print("=" * 70)

    result = evaluate(events, outcomes)
    print(f"\nWeights: {result.weights}")
    print(f"Class weights: {result.class_weights}")
    print(f"Thresholds: upper={result.upper_threshold}, lower={result.lower_threshold}")
    print(f"Trials: {result.n_trials:,}")
    print(f"\nMisrouting rate:     {result.misrouting_rate:.2%}")
    print(f"False positive rate: {result.false_positive_rate:.2%}")
    print(f"False negative rate: {result.false_negative_rate:.2%}")
    print(f"F1 (full):           {result.f1_full:.3f}")
    print(f"F1 (reduced):        {result.f1_reduced:.3f}")
    print(f"F1 (disputed):       {result.f1_disputed:.3f}")
    print()
    return result


def run_experiment_1(events, outcomes):
    """Experiment 1: Weight optimization."""
    print("=" * 70)
    print("EXPERIMENT 1: Weight Optimization")
    print("=" * 70)

    t0 = time.time()
    results = experiment_1_weights(events, outcomes)
    elapsed = time.time() - t0

    print(f"\nEvaluated {len(results)} weight combinations in {elapsed:.1f}s")
    print(f"\nTop 5 weight vectors:")
    print(f"{'Rank':>4}  {'w_f':>5} {'w_b':>5} {'w_d':>5}  {'Misroute':>9} {'FP Rate':>8} {'FN Rate':>8}")
    print("-" * 55)
    for i, r in enumerate(results[:5]):
        print(f"{i+1:4d}  {r.weights[0]:5.2f} {r.weights[1]:5.2f} {r.weights[2]:5.2f}  {r.misrouting_rate:9.2%} {r.false_positive_rate:8.2%} {r.false_negative_rate:8.2%}")

    # Find current weights in results
    for r in results:
        if r.weights == DEFAULT_WEIGHTS:
            rank = results.index(r) + 1
            print(f"\nCurrent weights (0.5, 0.3, 0.2) rank: #{rank}/{len(results)}")
            print(f"  Misrouting: {r.misrouting_rate:.2%}")
            break

    best = results[0]
    print(f"\nBest weights: {best.weights} → misrouting: {best.misrouting_rate:.2%}")
    improvement = (evaluate(events, outcomes).misrouting_rate - best.misrouting_rate)
    print(f"Improvement over current: {improvement:+.2%} percentage points")
    print()
    return results


def run_experiment_2(events, outcomes, best_weights):
    """Experiment 2: Class weight optimization."""
    print("=" * 70)
    print("EXPERIMENT 2: Class Weight Optimization")
    print("=" * 70)

    t0 = time.time()
    results = experiment_2_class_weights(events, outcomes, best_weights=best_weights)
    elapsed = time.time() - t0

    print(f"\nEvaluated {len(results)} class weight combinations in {elapsed:.1f}s")
    print(f"\nTop 5 class weight vectors:")
    print(f"{'Rank':>4}  {'LIVE':>5} {'RES':>5} {'LOG':>5}  {'Misroute':>9} {'FP Rate':>8} {'FN Rate':>8}")
    print("-" * 55)
    for i, r in enumerate(results[:5]):
        print(f"{i+1:4d}  {r.class_weights['LIVENESS']:5.2f} {r.class_weights['RESOURCE']:5.2f} {r.class_weights['LOGIC']:5.2f}  {r.misrouting_rate:9.2%} {r.false_positive_rate:8.2%} {r.false_negative_rate:8.2%}")

    # Find current class weights
    for r in results:
        if (r.class_weights["LIVENESS"] == 0.9 and
            r.class_weights["RESOURCE"] == 0.5 and
            r.class_weights["LOGIC"] == 0.1):
            rank = results.index(r) + 1
            print(f"\nCurrent class weights (0.9, 0.5, 0.1) rank: #{rank}/{len(results)}")
            print(f"  Misrouting: {r.misrouting_rate:.2%}")
            break

    best = results[0]
    print(f"\nBest class weights: L={best.class_weights['LIVENESS']}, R={best.class_weights['RESOURCE']}, Lg={best.class_weights['LOGIC']}")
    print(f"  Misrouting: {best.misrouting_rate:.2%}")
    print()
    return results


def run_experiment_3(events, outcomes, best_weights, best_class_weights):
    """Experiment 3: Threshold optimization."""
    print("=" * 70)
    print("EXPERIMENT 3: Threshold Optimization")
    print("=" * 70)

    t0 = time.time()
    results = experiment_3_thresholds(
        events, outcomes,
        best_weights=best_weights,
        best_class_weights=best_class_weights,
    )
    elapsed = time.time() - t0

    print(f"\nEvaluated {len(results)} threshold combinations in {elapsed:.1f}s")
    print(f"\nTop 5 threshold pairs:")
    print(f"{'Rank':>4}  {'Upper':>6} {'Lower':>6}  {'Misroute':>9} {'FP Rate':>8} {'FN Rate':>8} {'F1-F':>5} {'F1-R':>5} {'F1-D':>5}")
    print("-" * 72)
    for i, r in enumerate(results[:5]):
        print(f"{i+1:4d}  {r.upper_threshold:6.2f} {r.lower_threshold:6.2f}  {r.misrouting_rate:9.2%} {r.false_positive_rate:8.2%} {r.false_negative_rate:8.2%} {r.f1_full:5.3f} {r.f1_reduced:5.3f} {r.f1_disputed:5.3f}")

    # Find current thresholds
    for r in results:
        if r.upper_threshold == 0.6 and r.lower_threshold == 0.3:
            rank = results.index(r) + 1
            print(f"\nCurrent thresholds (0.6/0.3) rank: #{rank}/{len(results)}")
            print(f"  Misrouting: {r.misrouting_rate:.2%}")
            break

    best = results[0]
    print(f"\nBest thresholds: upper={best.upper_threshold}, lower={best.lower_threshold}")
    print(f"  Misrouting: {best.misrouting_rate:.2%}")
    print()
    return results


def run_experiment_4(events, outcomes, best_weights):
    """Experiment 4: Sensitivity analysis."""
    print("=" * 70)
    print("EXPERIMENT 4: Sensitivity Analysis")
    print("=" * 70)

    result = experiment_4_sensitivity(events, outcomes, base_weights=best_weights)
    baseline = result["baseline_rate"]

    print(f"\nBaseline misrouting rate: {baseline:.2%}")
    print(f"\nPerturbation impact (change in misrouting rate):")
    print(f"{'Weight':>8} {'−20%':>8} {'−15%':>8} {'−10%':>8} {'−5%':>8} {'  +5%':>8} {'+10%':>8} {'+15%':>8} {'+20%':>8}")
    print("-" * 76)

    for name in ["w_f", "w_b", "w_d"]:
        perturbations = result["perturbations"][name]
        values = {}
        for p, delta in perturbations:
            values[p] = delta

        row = f"{name:>8}"
        for p in [-0.20, -0.15, -0.10, -0.05, 0.05, 0.10, 0.15, 0.20]:
            delta = values.get(p, 0)
            row += f" {delta:+7.2%}"
        print(row)

    # Check stability criterion: ±10% perturbation < 5 percentage points
    max_delta_10 = 0
    for name in ["w_f", "w_b", "w_d"]:
        for p, delta in result["perturbations"][name]:
            if abs(p) == 0.10:
                max_delta_10 = max(max_delta_10, abs(delta))

    print(f"\nMax misrouting change at ±10%: {max_delta_10:.2%}")
    print(f"Stability criterion (< 5pp): {'PASS' if max_delta_10 < 0.05 else 'FAIL'}")
    print()
    return result


def run_experiment_5(best_weights, best_class_weights):
    """Experiment 5: Cross-task-type validation."""
    print("=" * 70)
    print("EXPERIMENT 5: Cross-Task-Type Validation")
    print("=" * 70)

    results = experiment_5_cross_validation(
        best_weights=best_weights,
        best_class_weights=best_class_weights,
    )

    print(f"\nLeave-one-out cross-validation:")
    print(f"{'Held Out Task Type':>30}  {'Misroute':>9} {'FP Rate':>8} {'FN Rate':>8} {'N':>7}")
    print("-" * 67)

    rates = []
    for r in results:
        print(f"{r['held_out']:>30}  {r['misrouting_rate']:9.2%} {r['false_positive_rate']:8.2%} {r['false_negative_rate']:8.2%} {r['n_trials']:7,}")
        rates.append(r["misrouting_rate"])

    mean_rate = np.mean(rates)
    std_rate = np.std(rates)
    print(f"\nMean misrouting across folds: {mean_rate:.2%} ± {std_rate:.2%}")
    print(f"Generalization criterion (std < 3pp): {'PASS' if std_rate < 0.03 else 'FAIL'}")
    print()
    return results


def generate_figures(events, outcomes, exp1_results, exp3_results, sensitivity_result):
    """Generate publication-ready figures."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("matplotlib not available — skipping figure generation")
        return

    # Figure 1: Heatmap of misrouting rate across weight space
    fig, ax = plt.subplots(figsize=(10, 7))
    config = GridSearchConfig()
    w_f_vals = sorted(set(r.weights[0] for r in exp1_results))
    w_b_vals = sorted(set(r.weights[1] for r in exp1_results))

    grid = np.full((len(w_f_vals), len(w_b_vals)), np.nan)
    for r in exp1_results:
        i = w_f_vals.index(r.weights[0])
        j = w_b_vals.index(r.weights[1])
        grid[i, j] = r.misrouting_rate * 100

    im = ax.imshow(grid, cmap="RdYlGn_r", aspect="auto", origin="lower",
                   extent=[min(w_b_vals)-0.025, max(w_b_vals)+0.025,
                           min(w_f_vals)-0.025, max(w_f_vals)+0.025])
    ax.set_xlabel("Budget Weight (w_b)", fontsize=12)
    ax.set_ylabel("Failure Class Weight (w_f)", fontsize=12)
    ax.set_title("Misrouting Rate (%) Across Weight Space", fontsize=14)
    plt.colorbar(im, ax=ax, label="Misrouting Rate (%)")

    # Mark current weights
    ax.plot(0.3, 0.5, "k*", markersize=15, label="Current (0.5, 0.3, 0.2)")
    # Mark best
    best = exp1_results[0]
    ax.plot(best.weights[1], best.weights[0], "r*", markersize=15, label=f"Best ({best.weights[0]}, {best.weights[1]}, {best.weights[2]})")
    ax.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig1_weight_heatmap.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig1_weight_heatmap.svg")
    plt.close()
    print("  Generated: fig1_weight_heatmap.png/svg")

    # Figure 2: Recovery probability surface per class
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    from simulation.recovery import ground_truth_vectorized

    budget_range = np.linspace(0, 1, 50)
    deadline_range = np.linspace(0, 1, 50)
    B, D = np.meshgrid(budget_range, deadline_range)

    for idx, (cls, ax) in enumerate(zip(["LIVENESS", "RESOURCE", "LOGIC"], axes)):
        fc = np.full(B.ravel().shape, cls)
        rs = np.full(B.ravel().shape, 5.0)  # 5 remaining subtasks
        sk = np.full(B.ravel().shape, 0.71)  # mean fallback skill
        probs = ground_truth_vectorized(fc, B.ravel(), D.ravel(), rs, sk).reshape(B.shape)

        im = ax.contourf(B, D, probs, levels=20, cmap="RdYlGn")
        ax.set_xlabel("Budget Remaining")
        ax.set_ylabel("Deadline Remaining")
        ax.set_title(f"{cls}\n(base rate: {GROUND_TRUTH_BASE_RATES[cls]:.0%})")
        plt.colorbar(im, ax=ax, format="%.0f%%",
                     ticks=np.arange(0, 1.1, 0.2))

    fig.suptitle("Ground Truth Recovery Probability by Failure Class", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig2_recovery_surface.png", dpi=150, bbox_inches="tight")
    plt.savefig(FIGURES_DIR / "fig2_recovery_surface.svg", bbox_inches="tight")
    plt.close()
    print("  Generated: fig2_recovery_surface.png/svg")

    # Figure 3: Threshold sweep — misrouting by (upper, lower) pair
    fig, ax = plt.subplots(figsize=(10, 7))
    upper_vals = sorted(set(r.upper_threshold for r in exp3_results))
    lower_vals = sorted(set(r.lower_threshold for r in exp3_results))

    grid3 = np.full((len(upper_vals), len(lower_vals)), np.nan)
    for r in exp3_results:
        i = upper_vals.index(r.upper_threshold)
        j = lower_vals.index(r.lower_threshold)
        grid3[i, j] = r.misrouting_rate * 100

    im = ax.imshow(grid3, cmap="RdYlGn_r", aspect="auto", origin="lower",
                   extent=[min(lower_vals)-0.025, max(lower_vals)+0.025,
                           min(upper_vals)-0.025, max(upper_vals)+0.025])
    ax.set_xlabel("Lower Threshold", fontsize=12)
    ax.set_ylabel("Upper Threshold", fontsize=12)
    ax.set_title("Misrouting Rate (%) Across Threshold Space", fontsize=14)
    plt.colorbar(im, ax=ax, label="Misrouting Rate (%)")
    ax.plot(0.3, 0.6, "k*", markersize=15, label="Current (0.6/0.3)")
    best3 = exp3_results[0]
    ax.plot(best3.lower_threshold, best3.upper_threshold, "r*", markersize=15,
            label=f"Best ({best3.upper_threshold}/{best3.lower_threshold})")
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig3_threshold_heatmap.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig3_threshold_heatmap.svg")
    plt.close()
    print("  Generated: fig3_threshold_heatmap.png/svg")

    # Figure 4: Tornado chart — sensitivity
    fig, ax = plt.subplots(figsize=(10, 6))
    names = ["w_f (failure class)", "w_b (budget)", "w_d (deadline)"]
    keys = ["w_f", "w_b", "w_d"]

    for i, (key, name) in enumerate(zip(keys, names)):
        perturbations = sensitivity_result["perturbations"][key]
        neg_deltas = [d for p, d in perturbations if p < 0]
        pos_deltas = [d for p, d in perturbations if p > 0]
        max_neg = min(neg_deltas) if neg_deltas else 0
        max_pos = max(pos_deltas) if pos_deltas else 0
        ax.barh(i, max_pos * 100, left=0, color="#e74c3c", alpha=0.7, height=0.6, label="+20%" if i == 0 else "")
        ax.barh(i, max_neg * 100, left=0, color="#3498db", alpha=0.7, height=0.6, label="-20%" if i == 0 else "")

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("Change in Misrouting Rate (percentage points)")
    ax.set_title("Sensitivity Analysis: Impact of ±20% Weight Perturbation")
    ax.axvline(x=0, color="black", linewidth=0.5)
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig4_sensitivity_tornado.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig4_sensitivity_tornado.svg")
    plt.close()
    print("  Generated: fig4_sensitivity_tornado.png/svg")

    # Figure 5: Confusion matrix — routing outcomes
    fig, ax = plt.subplots(figsize=(8, 6))
    scores = recovery_score_vectorized(
        events["failure_class"], events["budget_remaining"],
        events["deadline_remaining"],
    )
    routes = route_vectorized(scores)
    tiers = ["RECOVERING_FULL", "RECOVERING_REDUCED", "DISPUTED"]
    matrix = np.zeros((3, 2))  # tiers × (success, fail)
    for i, tier in enumerate(tiers):
        mask = routes == tier
        matrix[i, 0] = (mask & outcomes).sum()
        matrix[i, 1] = (mask & ~outcomes).sum()

    # Normalize to percentages
    total = matrix.sum()
    matrix_pct = matrix / total * 100

    im = ax.imshow(matrix_pct, cmap="Blues", aspect="auto")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Recovery Succeeded", "Recovery Failed"])
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["FULL", "REDUCED", "DISPUTED"])
    ax.set_ylabel("Routing Decision")
    ax.set_xlabel("Actual Outcome")
    ax.set_title("Routing Confusion Matrix (%)")

    for i in range(3):
        for j in range(2):
            color = "white" if matrix_pct[i, j] > 15 else "black"
            ax.text(j, i, f"{matrix_pct[i,j]:.1f}%\n({int(matrix[i,j]):,})",
                    ha="center", va="center", fontsize=11, color=color)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig5_confusion_matrix.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig5_confusion_matrix.svg")
    plt.close()
    print("  Generated: fig5_confusion_matrix.png/svg")

    # Figure 6: Score distributions by failure class
    fig, ax = plt.subplots(figsize=(10, 6))
    for cls, color in zip(["LIVENESS", "RESOURCE", "LOGIC"], ["#2ecc71", "#f39c12", "#e74c3c"]):
        mask = events["failure_class"] == cls
        cls_scores = scores[mask]
        ax.hist(cls_scores, bins=40, alpha=0.6, label=cls, color=color, density=True)

    ax.axvline(x=0.6, color="black", linestyle="--", linewidth=1.5, label="Upper threshold (0.6)")
    ax.axvline(x=0.3, color="gray", linestyle="--", linewidth=1.5, label="Lower threshold (0.3)")
    ax.set_xlabel("Recovery Score")
    ax.set_ylabel("Density")
    ax.set_title("Score Distributions by Failure Class")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig6_score_distributions.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig6_score_distributions.svg")
    plt.close()
    print("  Generated: fig6_score_distributions.png/svg")


def main():
    print("\n" + "=" * 70)
    print("  CAIRN RECOVERY SCORE CALIBRATION SIMULATION")
    print("  Whitepaper V2, Equation 1: r = w_f*F + w_b*B + w_d*D")
    print("=" * 70)
    print(f"\nSeed: {SEED}")
    print(f"Baseline trials: {TOTAL_BASELINE_TRIALS:,}")
    print(f"Trials per parameter combo: {TRIALS_PER_COMBO:,}")

    t_start = time.time()
    rng = np.random.default_rng(SEED)

    # Validate ground truth
    _, _, _ = validate_ground_truth(np.random.default_rng(SEED + 1))

    # Generate main event set
    print("Generating main event set...")
    events = generate_events_vectorized(TOTAL_BASELINE_TRIALS, rng)
    probs = ground_truth_vectorized(
        events["failure_class"],
        events["budget_remaining"],
        events["deadline_remaining"],
        events["remaining_subtasks"],
        events["fallback_skill"],
    )
    outcomes = simulate_outcomes(probs, rng)
    print(f"Generated {TOTAL_BASELINE_TRIALS:,} events | Overall recovery rate: {outcomes.mean():.1%}\n")

    # Baseline
    baseline = run_baseline(events, outcomes)

    # Experiment 1
    exp1 = run_experiment_1(events, outcomes)
    best_weights = exp1[0].weights

    # Experiment 2
    exp2 = run_experiment_2(events, outcomes, best_weights=best_weights)
    best_class_weights = exp2[0].class_weights

    # Experiment 3
    exp3 = run_experiment_3(events, outcomes, best_weights=best_weights, best_class_weights=best_class_weights)
    best_upper = exp3[0].upper_threshold
    best_lower = exp3[0].lower_threshold

    # Experiment 4
    sens = run_experiment_4(events, outcomes, best_weights=best_weights)

    # Experiment 5
    cv = run_experiment_5(best_weights=best_weights, best_class_weights=best_class_weights)

    # Summary
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"\nBaseline (current):  misrouting = {baseline.misrouting_rate:.2%}")
    print(f"Best weights:        {best_weights} → misrouting = {exp1[0].misrouting_rate:.2%}")
    print(f"Best class weights:  L={best_class_weights['LIVENESS']}, R={best_class_weights['RESOURCE']}, Lg={best_class_weights['LOGIC']} → misrouting = {exp2[0].misrouting_rate:.2%}")
    print(f"Best thresholds:     upper={best_upper}, lower={best_lower} → misrouting = {exp3[0].misrouting_rate:.2%}")

    # Optimal combined evaluation
    optimal = evaluate(
        events, outcomes,
        weights=best_weights,
        class_weights=best_class_weights,
        upper=best_upper,
        lower=best_lower,
    )
    improvement = baseline.misrouting_rate - optimal.misrouting_rate

    print(f"\nOptimal combined:    misrouting = {optimal.misrouting_rate:.2%}")
    print(f"Improvement:         {improvement:+.2%} percentage points")
    print(f"\nOptimal parameters:")
    print(f"  Weights:        w_f={best_weights[0]}, w_b={best_weights[1]}, w_d={best_weights[2]}")
    print(f"  Class weights:  LIVENESS={best_class_weights['LIVENESS']}, RESOURCE={best_class_weights['RESOURCE']}, LOGIC={best_class_weights['LOGIC']}")
    print(f"  Thresholds:     upper={best_upper}, lower={best_lower}")

    t_total = time.time() - t_start
    print(f"\nTotal runtime: {t_total:.1f}s")

    # Generate figures
    print(f"\nGenerating publication figures...")
    generate_figures(events, outcomes, exp1, exp3, sens)

    # Save results JSON
    results_json = {
        "seed": SEED,
        "total_trials": TOTAL_BASELINE_TRIALS,
        "baseline": {
            "weights": list(baseline.weights),
            "class_weights": baseline.class_weights,
            "thresholds": {"upper": baseline.upper_threshold, "lower": baseline.lower_threshold},
            "misrouting_rate": baseline.misrouting_rate,
            "false_positive_rate": baseline.false_positive_rate,
            "false_negative_rate": baseline.false_negative_rate,
        },
        "optimal": {
            "weights": list(best_weights),
            "class_weights": best_class_weights,
            "thresholds": {"upper": best_upper, "lower": best_lower},
            "misrouting_rate": optimal.misrouting_rate,
            "false_positive_rate": optimal.false_positive_rate,
            "false_negative_rate": optimal.false_negative_rate,
        },
        "improvement_pp": improvement,
        "sensitivity_max_10pct": max(
            abs(d) for name in sens["perturbations"]
            for p, d in sens["perturbations"][name] if abs(p) == 0.10
        ),
        "cross_validation": cv,
        "runtime_seconds": t_total,
    }

    results_path = Path(__file__).parent / "results.json"
    with open(results_path, "w") as f:
        json.dump(results_json, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
