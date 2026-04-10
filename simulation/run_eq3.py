#!/usr/bin/env python3
"""Run 3: CAIRN recovery score calibration — Equation 3 (5-variable).

Tests whether adding remaining_subtasks (complexity) and fallback_skill
to the formula breaks below 20% misrouting.
"""

import time
import json
import numpy as np
from pathlib import Path
from itertools import product

from simulation.config import (
    SEED, TOTAL_BASELINE_TRIALS, DEFAULT_CLASS_WEIGHTS, TASK_TYPES,
)
from simulation.generator import generate_events_vectorized
from simulation.recovery import ground_truth_vectorized, simulate_outcomes
from simulation.scorer import (
    recovery_score_vectorized, recovery_score_eq3_vectorized,
    route_vectorized, EQ3_DEFAULTS,
)
from simulation.optimizer import evaluate, compute_f1, EvalResult

FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


def evaluate_eq3(
    events: dict[str, np.ndarray],
    outcomes: np.ndarray,
    class_weights: dict[str, float] = None,
    params: dict = None,
    upper: float = 0.45,
    lower: float = 0.40,
) -> EvalResult:
    """Evaluate Equation 3 parameters."""
    if params is None:
        params = EQ3_DEFAULTS
    if class_weights is None:
        class_weights = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    scores = recovery_score_eq3_vectorized(
        events["failure_class"],
        events["budget_remaining"],
        events["deadline_remaining"],
        events["remaining_subtasks"],
        events["fallback_skill"],
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

    tiers = ["RECOVERING_FULL", "RECOVERING_REDUCED", "DISPUTED"]
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


def experiment_9_eq3_weights(events, outcomes):
    """Experiment 9: Grid search over 5-variable formula weights (RQ9)."""
    print("=" * 70)
    print("EXPERIMENT 9: Equation 3 — 5-Variable Weight Optimization")
    print("=" * 70)

    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    # Grid: 5 weights that sum to ~1.0
    w_f_range = [0.15, 0.20, 0.25, 0.30, 0.35]
    w_b_range = [0.10, 0.15, 0.20, 0.25]
    w_d_range = [0.15, 0.20, 0.25, 0.30, 0.35]
    w_c_range = [0.05, 0.10, 0.15, 0.20, 0.25]
    w_s_range = [0.05, 0.10, 0.15, 0.20, 0.25]

    t0 = time.time()
    results = []

    for w_f, w_b, w_d, w_c, w_s in product(w_f_range, w_b_range, w_d_range, w_c_range, w_s_range):
        total = w_f + w_b + w_d + w_c + w_s
        if abs(total - 1.0) > 0.01:
            continue

        params = {"w_f": w_f, "w_b": w_b, "w_d": w_d, "w_c": w_c, "w_s": w_s}
        result = evaluate_eq3(events, outcomes, class_weights=best_cw, params=params)
        results.append((params, result))

    results.sort(key=lambda x: x[1].misrouting_rate)
    elapsed = time.time() - t0

    print(f"\n  Evaluated {len(results)} weight combinations in {elapsed:.1f}s")
    print(f"\n  Top 10 weight vectors:")
    print(f"  {'Rank':>4} {'w_f':>5} {'w_b':>5} {'w_d':>5} {'w_c':>5} {'w_s':>5} {'Misroute':>9} {'FP':>8} {'FN':>8}")
    print("  " + "-" * 63)
    for i, (p, r) in enumerate(results[:10]):
        print(f"  {i+1:4d} {p['w_f']:5.2f} {p['w_b']:5.2f} {p['w_d']:5.2f} {p['w_c']:5.2f} {p['w_s']:5.2f} {r.misrouting_rate:9.2%} {r.false_positive_rate:8.2%} {r.false_negative_rate:8.2%}")

    best_params, best_result = results[0]
    print(f"\n  Best: {best_params} → {best_result.misrouting_rate:.2%}")

    return results


def experiment_10_eq3_thresholds(events, outcomes, best_params):
    """Experiment 10: Threshold optimization for Eq3."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 10: Equation 3 — Threshold Optimization")
    print("=" * 70)

    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}
    upper_range = [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]
    lower_range = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45]

    results = []
    for upper, lower in product(upper_range, lower_range):
        if lower >= upper:
            continue
        result = evaluate_eq3(events, outcomes, class_weights=best_cw,
                              params=best_params, upper=upper, lower=lower)
        results.append((upper, lower, result))

    results.sort(key=lambda x: x[2].misrouting_rate)

    print(f"\n  Evaluated {len(results)} threshold combinations")
    print(f"\n  Top 10 threshold pairs:")
    print(f"  {'Rank':>4} {'Upper':>6} {'Lower':>6} {'Misroute':>9} {'FP':>8} {'FN':>8} {'F1-F':>5} {'F1-R':>5} {'F1-D':>5}")
    print("  " + "-" * 65)
    for i, (u, l, r) in enumerate(results[:10]):
        print(f"  {i+1:4d} {u:6.2f} {l:6.2f} {r.misrouting_rate:9.2%} {r.false_positive_rate:8.2%} {r.false_negative_rate:8.2%} {r.f1_full:5.3f} {r.f1_reduced:5.3f} {r.f1_disputed:5.3f}")

    best_upper, best_lower, best_result = results[0]
    print(f"\n  Best: upper={best_upper}, lower={best_lower} → {best_result.misrouting_rate:.2%}")

    return results, best_upper, best_lower, best_result


def experiment_11_ablation(events, outcomes, best_params, best_upper, best_lower):
    """Experiment 11: Ablation — contribution of each new variable."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 11: Ablation — Variable Contribution Analysis")
    print("=" * 70)

    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    # 3-var (Eq1 optimal from Run 1)
    result_3var = evaluate(
        events, outcomes,
        weights=(0.30, 0.25, 0.45),
        class_weights=best_cw,
        upper=best_upper, lower=best_lower,
    )

    # 4-var: add complexity only (redistribute w_s to w_d)
    params_4var_c = dict(best_params)
    params_4var_c["w_s"] = 0.0
    w_sum = params_4var_c["w_f"] + params_4var_c["w_b"] + params_4var_c["w_d"] + params_4var_c["w_c"]
    for k in ("w_f", "w_b", "w_d", "w_c"):
        params_4var_c[k] /= w_sum
    result_4var_c = evaluate_eq3(events, outcomes, class_weights=best_cw,
                                 params=params_4var_c, upper=best_upper, lower=best_lower)

    # 4-var: add skill only (redistribute w_c to w_d)
    params_4var_s = dict(best_params)
    params_4var_s["w_c"] = 0.0
    w_sum = params_4var_s["w_f"] + params_4var_s["w_b"] + params_4var_s["w_d"] + params_4var_s["w_s"]
    for k in ("w_f", "w_b", "w_d", "w_s"):
        params_4var_s[k] /= w_sum
    result_4var_s = evaluate_eq3(events, outcomes, class_weights=best_cw,
                                 params=params_4var_s, upper=best_upper, lower=best_lower)

    # 5-var: full Eq3
    result_5var = evaluate_eq3(events, outcomes, class_weights=best_cw,
                               params=best_params, upper=best_upper, lower=best_lower)

    print(f"\n  {'Configuration':>40} {'Misroute':>9} {'FP Rate':>8} {'FN Rate':>8}")
    print("  " + "-" * 70)
    print(f"  {'3-var: Eq1 (F, B, D)':>40} {result_3var.misrouting_rate:9.2%} {result_3var.false_positive_rate:8.2%} {result_3var.false_negative_rate:8.2%}")
    print(f"  {'4-var: + Complexity (F, B, D, C)':>40} {result_4var_c.misrouting_rate:9.2%} {result_4var_c.false_positive_rate:8.2%} {result_4var_c.false_negative_rate:8.2%}")
    print(f"  {'4-var: + Skill (F, B, D, S)':>40} {result_4var_s.misrouting_rate:9.2%} {result_4var_s.false_positive_rate:8.2%} {result_4var_s.false_negative_rate:8.2%}")
    print(f"  {'5-var: Full Eq3 (F, B, D, C, S)':>40} {result_5var.misrouting_rate:9.2%} {result_5var.false_positive_rate:8.2%} {result_5var.false_negative_rate:8.2%}")

    c_contrib = result_3var.misrouting_rate - result_4var_c.misrouting_rate
    s_contrib = result_3var.misrouting_rate - result_4var_s.misrouting_rate
    total = result_3var.misrouting_rate - result_5var.misrouting_rate

    print(f"\n  Complexity contribution:    {c_contrib:+.2%} pp")
    print(f"  Skill contribution:         {s_contrib:+.2%} pp")
    print(f"  Combined (non-additive):    {total:+.2%} pp")

    return {
        "3var": result_3var.misrouting_rate,
        "4var_complexity": result_4var_c.misrouting_rate,
        "4var_skill": result_4var_s.misrouting_rate,
        "5var_full": result_5var.misrouting_rate,
        "complexity_contribution_pp": c_contrib,
        "skill_contribution_pp": s_contrib,
        "total_improvement_pp": total,
    }


def experiment_12_cross_validation(best_params, best_cw, best_upper, best_lower):
    """Experiment 12: Cross-task-type validation for Eq3."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 12: Equation 3 — Cross-Task-Type Validation")
    print("=" * 70)

    rng = np.random.default_rng(SEED + 200)
    n = 50_000
    all_events = generate_events_vectorized(n, rng)
    probs = ground_truth_vectorized(
        all_events["failure_class"], all_events["budget_remaining"],
        all_events["deadline_remaining"], all_events["remaining_subtasks"],
        all_events["fallback_skill"],
    )
    all_outcomes = simulate_outcomes(probs, rng)

    print(f"\n  {'Held Out Task Type':>30} {'Misroute':>9} {'FP Rate':>8} {'FN Rate':>8} {'N':>7}")
    print("  " + "-" * 67)

    rates = []
    results = []
    for held_out in TASK_TYPES:
        test_mask = all_events["task_type"] == held_out
        test_events = {k: v[test_mask] for k, v in all_events.items()}
        test_outcomes = all_outcomes[test_mask]

        if len(test_outcomes) == 0:
            continue

        result = evaluate_eq3(test_events, test_outcomes, class_weights=best_cw,
                              params=best_params, upper=best_upper, lower=best_lower)
        rates.append(result.misrouting_rate)
        results.append({"held_out": held_out, "misrouting_rate": result.misrouting_rate,
                        "fp": result.false_positive_rate, "fn": result.false_negative_rate,
                        "n": result.n_trials})
        print(f"  {held_out:>30} {result.misrouting_rate:9.2%} {result.false_positive_rate:8.2%} {result.false_negative_rate:8.2%} {result.n_trials:7,}")

    mean_rate = np.mean(rates)
    std_rate = np.std(rates)
    print(f"\n  Mean: {mean_rate:.2%} ± {std_rate:.2%}")
    print(f"  Generalization (std < 3pp): {'PASS' if std_rate < 0.03 else 'FAIL'}")

    return results, mean_rate, std_rate


def generate_eq3_figures(events, outcomes, best_params, best_upper, best_lower, ablation):
    """Generate Equation 3 publication figures."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available — skipping figures")
        return

    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}

    # Fig 11: 3-var vs 4-var vs 5-var comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    configs = ["3-var\n(F, B, D)", "4-var\n(+ Complexity)", "4-var\n(+ Skill)", "5-var\n(F, B, D, C, S)"]
    values = [ablation["3var"], ablation["4var_complexity"],
              ablation["4var_skill"], ablation["5var_full"]]
    colors = ["#e74c3c", "#f39c12", "#f39c12", "#2ecc71"]

    bars = ax.bar(configs, [v * 100 for v in values], color=colors, alpha=0.8,
                  edgecolor="black", linewidth=0.5)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{v:.1%}", ha="center", fontsize=11, fontweight="bold")

    ax.axhline(y=10, color="green", linestyle=":", linewidth=2, alpha=0.5, label="Target (<10%)")
    ax.axhline(y=20, color="orange", linestyle=":", linewidth=2, alpha=0.5, label="Intermediate target (<20%)")
    ax.set_ylabel("Misrouting Rate (%)")
    ax.set_title("Impact of Adding Variables to Recovery Score Formula")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig11_variable_ablation.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig11_variable_ablation.svg")
    plt.close()
    print("  Generated: fig11_variable_ablation.png/svg")

    # Fig 12: Full waterfall from current → Eq3
    fig, ax = plt.subplots(figsize=(12, 6))
    categories = [
        "Current Eq1\n(0.5/0.3/0.2)",
        "Optimal Eq1\n(0.3/0.25/0.45)",
        "Eq2 piecewise\n(+interaction)",
        "Eq3 5-var\n(+C, +S)",
    ]

    # Load previous results
    try:
        with open(Path(__file__).parent / "results.json") as f:
            run1 = json.load(f)
        v_current = run1["baseline"]["misrouting_rate"]
        v_opt_eq1 = run1["optimal"]["misrouting_rate"]
    except Exception:
        v_current = 0.4756
        v_opt_eq1 = 0.3381

    try:
        with open(Path(__file__).parent / "results_eq2.json") as f:
            run2 = json.load(f)
        v_eq2 = run2["eq2_optimal"]["misrouting_rate"]
    except Exception:
        v_eq2 = 0.3317

    v_eq3 = ablation["5var_full"]
    values = [v_current, v_opt_eq1, v_eq2, v_eq3]
    colors = ["#e74c3c", "#f39c12", "#f39c12", "#2ecc71"]

    bars = ax.bar(categories, [v * 100 for v in values], color=colors, alpha=0.8,
                  edgecolor="black", linewidth=0.5)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{v:.1%}", ha="center", fontsize=11, fontweight="bold")

    ax.axhline(y=10, color="green", linestyle=":", linewidth=2, alpha=0.5, label="Target (<10%)")
    ax.axhline(y=20, color="orange", linestyle=":", linewidth=2, alpha=0.5, label="Intermediate (<20%)")
    ax.set_ylabel("Misrouting Rate (%)")
    ax.set_title("Progressive Improvement: Current → Equation 3")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig12_full_waterfall.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig12_full_waterfall.svg")
    plt.close()
    print("  Generated: fig12_full_waterfall.png/svg")

    # Fig 13: Confusion matrix comparison Eq1 vs Eq3
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    scores_eq1 = recovery_score_vectorized(
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        weights=(0.30, 0.25, 0.45), class_weights=best_cw,
    )
    scores_eq3 = recovery_score_eq3_vectorized(
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        events["remaining_subtasks"], events["fallback_skill"],
        class_weights=best_cw, params=best_params,
    )

    routes_eq1 = route_vectorized(scores_eq1, upper=best_upper, lower=best_lower)
    routes_eq3 = route_vectorized(scores_eq3, upper=best_upper, lower=best_lower)

    tiers = ["RECOVERING_FULL", "RECOVERING_REDUCED", "DISPUTED"]
    for ax, routes, title in [(ax1, routes_eq1, "Eq. 1 (3-var Linear)"),
                               (ax2, routes_eq3, "Eq. 3 (5-var)")]:
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

    plt.suptitle("Routing Confusion Matrix: 3-Variable vs 5-Variable", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig13_eq3_confusion_comparison.png", dpi=150, bbox_inches="tight")
    plt.savefig(FIGURES_DIR / "fig13_eq3_confusion_comparison.svg", bbox_inches="tight")
    plt.close()
    print("  Generated: fig13_eq3_confusion_comparison.png/svg")


def main():
    print("\n" + "=" * 70)
    print("  CAIRN RECOVERY SCORE CALIBRATION — RUN 3")
    print("  Equation 3: r = w_f*F + w_b*B + w_d*D + w_c*C + w_s*S")
    print("  (adds remaining complexity + fallback skill)")
    print("=" * 70)

    t_start = time.time()
    rng = np.random.default_rng(SEED)

    print(f"\nSeed: {SEED} | Trials: {TOTAL_BASELINE_TRIALS:,}")
    events = generate_events_vectorized(TOTAL_BASELINE_TRIALS, rng)
    probs = ground_truth_vectorized(
        events["failure_class"], events["budget_remaining"],
        events["deadline_remaining"], events["remaining_subtasks"],
        events["fallback_skill"],
    )
    outcomes = simulate_outcomes(probs, rng)
    print(f"Generated {TOTAL_BASELINE_TRIALS:,} events | Recovery rate: {outcomes.mean():.1%}")

    # Previous baselines
    from simulation.optimizer import evaluate as eval_eq1
    run1_current = eval_eq1(events, outcomes)
    run1_optimal = eval_eq1(events, outcomes, weights=(0.30, 0.25, 0.45),
                            class_weights={"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00},
                            upper=0.45, lower=0.40)
    print(f"\nRun 1 current:  {run1_current.misrouting_rate:.2%}")
    print(f"Run 1 optimal:  {run1_optimal.misrouting_rate:.2%}")

    # Experiment 9: Weight optimization
    exp9 = experiment_9_eq3_weights(events, outcomes)
    best_params = exp9[0][0]
    best_result_9 = exp9[0][1]

    # Experiment 10: Threshold optimization
    exp10, best_upper, best_lower, best_result_10 = experiment_10_eq3_thresholds(
        events, outcomes, best_params)

    # Experiment 11: Ablation
    best_cw = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}
    ablation = experiment_11_ablation(events, outcomes, best_params, best_upper, best_lower)

    # Experiment 12: Cross-validation
    cv_results, cv_mean, cv_std = experiment_12_cross_validation(
        best_params, best_cw, best_upper, best_lower)

    # Final evaluation
    final = evaluate_eq3(events, outcomes, class_weights=best_cw,
                         params=best_params, upper=best_upper, lower=best_lower)

    # Summary
    total_improvement = run1_current.misrouting_rate - final.misrouting_rate

    print("\n" + "=" * 70)
    print("RUN 3 FINAL SUMMARY")
    print("=" * 70)
    print(f"\n  Run 1 current (Eq1 0.5/0.3/0.2):  {run1_current.misrouting_rate:.2%}")
    print(f"  Run 1 optimal (Eq1 0.3/0.25/0.45): {run1_optimal.misrouting_rate:.2%}")
    print(f"  Run 3 optimal (Eq3 5-var):          {final.misrouting_rate:.2%}")
    print(f"  Total improvement:                  {total_improvement:+.2%} pp")
    print(f"\n  Eq3 optimal parameters:")
    for k, v in best_params.items():
        print(f"    {k:>5}: {v:.2f}")
    print(f"    upper: {best_upper}")
    print(f"    lower: {best_lower}")
    print(f"\n  Cross-validation: {cv_mean:.2%} ± {cv_std:.2%}")

    t_total = time.time() - t_start
    print(f"  Runtime: {t_total:.1f}s")

    # Figures
    print(f"\nGenerating publication figures...")
    generate_eq3_figures(events, outcomes, best_params, best_upper, best_lower, ablation)

    # Save results
    results = {
        "run": 3,
        "formula": "Eq3: r = w_f*F + w_b*B + w_d*D + w_c*C + w_s*S",
        "seed": SEED,
        "total_trials": TOTAL_BASELINE_TRIALS,
        "run1_comparison": {
            "current_misrouting": run1_current.misrouting_rate,
            "optimal_linear_misrouting": run1_optimal.misrouting_rate,
        },
        "eq3_optimal": {
            "params": best_params,
            "class_weights": best_cw,
            "thresholds": {"upper": best_upper, "lower": best_lower},
            "misrouting_rate": final.misrouting_rate,
            "false_positive_rate": final.false_positive_rate,
            "false_negative_rate": final.false_negative_rate,
        },
        "ablation": ablation,
        "cross_validation": {"mean": cv_mean, "std": cv_std, "results": cv_results},
        "total_improvement_pp": total_improvement,
        "runtime_seconds": t_total,
    }

    results_path = Path(__file__).parent / "results_eq3.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")
    print("Done.")


if __name__ == "__main__":
    main()
