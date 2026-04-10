#!/usr/bin/env python3
"""Run 4: CAIRN recovery score — Multiplicative formula + Bayes-optimal baseline.

Tests whether matching the ground truth's multiplicative structure breaks below 20%.
"""

import time
import json
import numpy as np
from pathlib import Path
from itertools import product

from simulation.config import (
    SEED, TOTAL_BASELINE_TRIALS, TASK_TYPES,
)
from simulation.generator import generate_events_vectorized
from simulation.recovery import ground_truth_vectorized, simulate_outcomes
from simulation.scorer import (
    recovery_score_vectorized, recovery_score_eq4_multiplicative,
    recovery_score_eq4_hybrid, route_vectorized,
    EQ4_DEFAULTS, EQ4H_DEFAULTS,
)
from simulation.optimizer import evaluate, compute_f1, EvalResult

FIGURES_DIR = Path(__file__).parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

BEST_CW = {"LIVENESS": 0.70, "RESOURCE": 0.30, "LOGIC": 0.00}


def evaluate_generic(
    scores: np.ndarray,
    outcomes: np.ndarray,
    upper: float,
    lower: float,
    label: str = "",
) -> dict:
    """Evaluate pre-computed scores against outcomes."""
    routes = route_vectorized(scores, upper=upper, lower=lower)
    routed_recover = (routes == "RECOVERING_FULL") | (routes == "RECOVERING_REDUCED")
    routed_dispute = routes == "DISPUTED"

    fp = routed_recover & ~outcomes
    fn = routed_dispute & outcomes
    n = len(outcomes)
    n_misrouted = fp.sum() + fn.sum()

    fp_rate = fp.sum() / routed_recover.sum() if routed_recover.sum() > 0 else 0.0
    fn_rate = fn.sum() / routed_dispute.sum() if routed_dispute.sum() > 0 else 0.0

    return {
        "label": label,
        "misrouting_rate": n_misrouted / n,
        "false_positive_rate": float(fp_rate),
        "false_negative_rate": float(fn_rate),
        "n": n,
        "routed_full": int((routes == "RECOVERING_FULL").sum()),
        "routed_reduced": int((routes == "RECOVERING_REDUCED").sum()),
        "routed_disputed": int(routed_dispute.sum()),
    }


def experiment_13_bayes_optimal(events, outcomes, probs):
    """Experiment 13: Compute Bayes-optimal baseline (theoretical minimum)."""
    print("=" * 70)
    print("EXPERIMENT 13: Bayes-Optimal Baseline (Theoretical Minimum)")
    print("=" * 70)

    # The Bayes-optimal classifier routes based on the TRUE probability:
    # If p >= threshold → RECOVERING; else → DISPUTED
    # The optimal threshold minimizes total misrouting.

    print("\n  Sweeping Bayes-optimal threshold...")

    best_rate = 1.0
    best_t = 0.5
    results = []

    for t in np.arange(0.05, 0.95, 0.01):
        # Route: p >= t → attempt recovery; p < t → dispute
        attempt = probs >= t
        dispute = ~attempt

        # Misrouting: attempted recovery that fails + disputed that would succeed
        fp = attempt & ~outcomes     # attempted but failed
        fn = dispute & outcomes      # disputed but would have succeeded
        rate = (fp.sum() + fn.sum()) / len(outcomes)
        results.append((t, rate, fp.sum(), fn.sum()))

        if rate < best_rate:
            best_rate = rate
            best_t = t

    print(f"\n  Bayes-optimal threshold: p ≥ {best_t:.2f}")
    print(f"  Bayes-optimal misrouting: {best_rate:.2%}")
    print(f"  This is the THEORETICAL MINIMUM — no formula can do better.")

    # Also compute three-tier Bayes-optimal
    print(f"\n  Three-tier Bayes-optimal (sweeping two thresholds)...")
    best_3t_rate = 1.0
    best_3t = (0.5, 0.3)

    for upper_t in np.arange(0.3, 0.9, 0.05):
        for lower_t in np.arange(0.1, upper_t, 0.05):
            full = probs >= upper_t
            reduced = (probs >= lower_t) & (probs < upper_t)
            dispute = probs < lower_t

            # For three-tier, "misrouting" for reduced tier is nuanced:
            # we'll use same definition as formula evaluation
            fp = (full | reduced) & ~outcomes
            fn = dispute & outcomes
            rate = (fp.sum() + fn.sum()) / len(outcomes)

            if rate < best_3t_rate:
                best_3t_rate = rate
                best_3t = (upper_t, lower_t)

    print(f"  Bayes-optimal three-tier: upper={best_3t[0]:.2f}, lower={best_3t[1]:.2f}")
    print(f"  Bayes-optimal three-tier misrouting: {best_3t_rate:.2%}")

    return {
        "binary_threshold": best_t,
        "binary_misrouting": best_rate,
        "three_tier_upper": best_3t[0],
        "three_tier_lower": best_3t[1],
        "three_tier_misrouting": best_3t_rate,
        "sweep": results,
    }


def experiment_14_multiplicative(events, outcomes):
    """Experiment 14: Grid search over multiplicative formula exponents."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 14: Equation 4 — Multiplicative Formula")
    print("=" * 70)

    a_range = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80]
    b_range = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    c_range = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    upper_range = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
    lower_range = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]

    t0 = time.time()

    # Phase A: sweep exponents with default thresholds
    print("\n  Phase A: Sweeping exponents...")
    phase_a = []
    for a, b, c in product(a_range, b_range, c_range):
        params = {"a": a, "b": b, "c": c}
        scores = recovery_score_eq4_multiplicative(
            events["failure_class"], events["budget_remaining"],
            events["deadline_remaining"], class_weights=BEST_CW, params=params,
        )
        # Try several threshold pairs quickly
        for upper, lower in [(0.35, 0.20), (0.40, 0.25), (0.45, 0.30),
                              (0.50, 0.35), (0.30, 0.15), (0.25, 0.10)]:
            result = evaluate_generic(scores, outcomes, upper, lower,
                                       label=f"a={a},b={b},c={c},u={upper},l={lower}")
            phase_a.append((params, upper, lower, result))

    phase_a.sort(key=lambda x: x[3]["misrouting_rate"])
    elapsed_a = time.time() - t0

    print(f"  Evaluated {len(phase_a)} combinations in {elapsed_a:.1f}s")
    print(f"\n  Top 10:")
    print(f"  {'Rank':>4} {'a':>5} {'b':>5} {'c':>5} {'Upper':>6} {'Lower':>6} {'Misroute':>9} {'FP':>8} {'FN':>8}")
    print("  " + "-" * 63)
    for i, (p, u, l, r) in enumerate(phase_a[:10]):
        print(f"  {i+1:4d} {p['a']:5.2f} {p['b']:5.2f} {p['c']:5.2f} {u:6.2f} {l:6.2f} {r['misrouting_rate']:9.2%} {r['false_positive_rate']:8.2%} {r['false_negative_rate']:8.2%}")

    best_params_a = phase_a[0][0]
    best_upper_a = phase_a[0][1]
    best_lower_a = phase_a[0][2]

    # Phase B: fine-tune thresholds with best exponents
    print(f"\n  Phase B: Fine-tuning thresholds for best exponents {best_params_a}...")
    phase_b = []
    scores_best = recovery_score_eq4_multiplicative(
        events["failure_class"], events["budget_remaining"],
        events["deadline_remaining"], class_weights=BEST_CW, params=best_params_a,
    )
    for upper in upper_range:
        for lower in lower_range:
            if lower >= upper:
                continue
            result = evaluate_generic(scores_best, outcomes, upper, lower)
            phase_b.append((upper, lower, result))

    phase_b.sort(key=lambda x: x[2]["misrouting_rate"])

    print(f"  Evaluated {len(phase_b)} threshold pairs")
    print(f"\n  Top 5:")
    print(f"  {'Rank':>4} {'Upper':>6} {'Lower':>6} {'Misroute':>9} {'FP':>8} {'FN':>8}")
    print("  " + "-" * 50)
    for i, (u, l, r) in enumerate(phase_b[:5]):
        print(f"  {i+1:4d} {u:6.2f} {l:6.2f} {r['misrouting_rate']:9.2%} {r['false_positive_rate']:8.2%} {r['false_negative_rate']:8.2%}")

    best_upper = phase_b[0][0]
    best_lower = phase_b[0][1]
    best_result = phase_b[0][2]

    print(f"\n  Best multiplicative: a={best_params_a['a']}, b={best_params_a['b']}, c={best_params_a['c']}")
    print(f"  Thresholds: upper={best_upper}, lower={best_lower}")
    print(f"  Misrouting: {best_result['misrouting_rate']:.2%}")

    return best_params_a, best_upper, best_lower, best_result, phase_a


def experiment_15_hybrid(events, outcomes, best_mult_params, best_mult_upper, best_mult_lower):
    """Experiment 15: Hybrid (linear + multiplicative blend)."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 15: Equation 4b — Hybrid (Linear + Multiplicative)")
    print("=" * 70)

    alpha_range = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    upper_range = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    lower_range = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]

    t0 = time.time()
    results = []

    for alpha in alpha_range:
        params = {
            "alpha": alpha,
            "w_f": 0.30, "w_b": 0.25, "w_d": 0.45,
            "a": best_mult_params["a"],
            "b": best_mult_params["b"],
            "c": best_mult_params["c"],
        }
        scores = recovery_score_eq4_hybrid(
            events["failure_class"], events["budget_remaining"],
            events["deadline_remaining"], class_weights=BEST_CW, params=params,
        )
        for upper, lower in product(upper_range, lower_range):
            if lower >= upper:
                continue
            result = evaluate_generic(scores, outcomes, upper, lower,
                                       label=f"alpha={alpha}")
            results.append((params, upper, lower, result))

    results.sort(key=lambda x: x[3]["misrouting_rate"])
    elapsed = time.time() - t0

    print(f"\n  Evaluated {len(results)} combinations in {elapsed:.1f}s")
    print(f"\n  Top 10:")
    print(f"  {'Rank':>4} {'Alpha':>6} {'Upper':>6} {'Lower':>6} {'Misroute':>9} {'FP':>8} {'FN':>8}")
    print("  " + "-" * 55)
    for i, (p, u, l, r) in enumerate(results[:10]):
        print(f"  {i+1:4d} {p['alpha']:6.2f} {u:6.2f} {l:6.2f} {r['misrouting_rate']:9.2%} {r['false_positive_rate']:8.2%} {r['false_negative_rate']:8.2%}")

    best = results[0]
    print(f"\n  Best hybrid: alpha={best[0]['alpha']}, upper={best[1]}, lower={best[2]}")
    print(f"  Misrouting: {best[3]['misrouting_rate']:.2%}")

    # Alpha analysis: how does misrouting vary with blend ratio?
    print(f"\n  Alpha sweep (best threshold per alpha):")
    print(f"  {'Alpha':>6} {'Best Misroute':>13} {'Type':>20}")
    print("  " + "-" * 45)
    for alpha in alpha_range:
        alpha_results = [r for r in results if r[0]["alpha"] == alpha]
        if alpha_results:
            best_for_alpha = min(alpha_results, key=lambda x: x[3]["misrouting_rate"])
            label = "pure multiplicative" if alpha == 0.0 else "pure linear" if alpha == 1.0 else f"hybrid {alpha:.0%}/{1-alpha:.0%}"
            print(f"  {alpha:6.1f} {best_for_alpha[3]['misrouting_rate']:13.2%} {label:>20}")

    return results


def experiment_16_cross_validation(events_fn, best_params, best_upper, best_lower, formula_type):
    """Experiment 16: Cross-validation for the best formula."""
    print(f"\n" + "=" * 70)
    print(f"EXPERIMENT 16: Cross-Task-Type Validation ({formula_type})")
    print("=" * 70)

    rng = np.random.default_rng(SEED + 300)
    n = 50_000
    all_events = generate_events_vectorized(n, rng)
    probs = ground_truth_vectorized(
        all_events["failure_class"], all_events["budget_remaining"],
        all_events["deadline_remaining"], all_events["remaining_subtasks"],
        all_events["fallback_skill"],
    )
    all_outcomes = simulate_outcomes(probs, rng)

    print(f"\n  {'Held Out Task Type':>30} {'Misroute':>9} {'FP':>8} {'FN':>8} {'N':>7}")
    print("  " + "-" * 67)

    rates = []
    for held_out in TASK_TYPES:
        test_mask = all_events["task_type"] == held_out
        test_events = {k: v[test_mask] for k, v in all_events.items()}
        test_outcomes = all_outcomes[test_mask]

        if len(test_outcomes) == 0:
            continue

        scores = recovery_score_eq4_multiplicative(
            test_events["failure_class"], test_events["budget_remaining"],
            test_events["deadline_remaining"], class_weights=BEST_CW, params=best_params,
        )
        result = evaluate_generic(scores, test_outcomes, best_upper, best_lower)
        rates.append(result["misrouting_rate"])
        print(f"  {held_out:>30} {result['misrouting_rate']:9.2%} {result['false_positive_rate']:8.2%} {result['false_negative_rate']:8.2%} {result['n']:7,}")

    mean_r = np.mean(rates)
    std_r = np.std(rates)
    print(f"\n  Mean: {mean_r:.2%} ± {std_r:.2%}")
    print(f"  Generalization (std < 3pp): {'PASS' if std_r < 0.03 else 'FAIL'}")
    return rates, mean_r, std_r


def generate_eq4_figures(events, outcomes, probs, bayes, best_mult_params, best_upper, best_lower):
    """Generate Run 4 publication figures."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not available")
        return

    # Fig 14: Full waterfall including multiplicative
    fig, ax = plt.subplots(figsize=(14, 6))

    try:
        with open(Path(__file__).parent / "results.json") as f:
            r1 = json.load(f)
        v_current = r1["baseline"]["misrouting_rate"]
        v_eq1_opt = r1["optimal"]["misrouting_rate"]
    except Exception:
        v_current, v_eq1_opt = 0.4756, 0.3381

    scores_mult = recovery_score_eq4_multiplicative(
        events["failure_class"], events["budget_remaining"],
        events["deadline_remaining"], class_weights=BEST_CW, params=best_mult_params,
    )
    r_mult = evaluate_generic(scores_mult, outcomes, best_upper, best_lower)
    v_mult = r_mult["misrouting_rate"]

    categories = [
        "Current Eq1\n(0.5/0.3/0.2)",
        "Optimal Eq1\n(0.3/0.25/0.45)",
        "Eq4 Multiplicative\n(F^a × B^b × D^c)",
        f"Bayes Optimal\n(theoretical min)",
    ]
    values = [v_current, v_eq1_opt, v_mult, bayes["three_tier_misrouting"]]
    colors = ["#e74c3c", "#f39c12", "#2ecc71", "#3498db"]

    bars = ax.bar(categories, [v * 100 for v in values], color=colors, alpha=0.8,
                  edgecolor="black", linewidth=0.5)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{v:.1%}", ha="center", fontsize=12, fontweight="bold")

    ax.axhline(y=10, color="green", linestyle=":", linewidth=2, alpha=0.5, label="Target (<10%)")
    ax.axhline(y=20, color="orange", linestyle=":", linewidth=2, alpha=0.5, label="Intermediate (<20%)")
    ax.set_ylabel("Misrouting Rate (%)", fontsize=12)
    ax.set_title("Recovery Score Formula Comparison (All Runs)", fontsize=14)
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig14_full_comparison.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig14_full_comparison.svg")
    plt.close()
    print("  Generated: fig14_full_comparison.png/svg")

    # Fig 15: Bayes-optimal sweep curve
    fig, ax = plt.subplots(figsize=(10, 6))
    thresholds = [t for t, _, _, _ in bayes["sweep"]]
    rates = [r * 100 for _, r, _, _ in bayes["sweep"]]
    ax.plot(thresholds, rates, "b-", linewidth=2)
    ax.axvline(x=bayes["binary_threshold"], color="red", linestyle="--",
               label=f"Optimal threshold ({bayes['binary_threshold']:.2f})")
    ax.axhline(y=bayes["binary_misrouting"] * 100, color="red", linestyle=":",
               label=f"Minimum misrouting ({bayes['binary_misrouting']:.1%})")
    ax.set_xlabel("Decision Threshold (route to RECOVERING if p ≥ threshold)")
    ax.set_ylabel("Misrouting Rate (%)")
    ax.set_title("Bayes-Optimal Misrouting vs Decision Threshold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig15_bayes_optimal_curve.png", dpi=150)
    plt.savefig(FIGURES_DIR / "fig15_bayes_optimal_curve.svg")
    plt.close()
    print("  Generated: fig15_bayes_optimal_curve.png/svg")

    # Fig 16: Confusion matrices — Eq1 vs Multiplicative vs Bayes
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    scores_eq1 = recovery_score_vectorized(
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        weights=(0.30, 0.25, 0.45), class_weights=BEST_CW,
    )
    routes_eq1 = route_vectorized(scores_eq1, upper=0.45, lower=0.40)
    routes_mult = route_vectorized(scores_mult, upper=best_upper, lower=best_lower)

    # Bayes routes using ground truth probability
    routes_bayes = route_vectorized(probs, upper=bayes["three_tier_upper"], lower=bayes["three_tier_lower"])

    tiers = ["RECOVERING_FULL", "RECOVERING_REDUCED", "DISPUTED"]
    for ax, routes, title in [
        (axes[0], routes_eq1, "Eq. 1 (Linear)"),
        (axes[1], routes_mult, "Eq. 4 (Multiplicative)"),
        (axes[2], routes_bayes, "Bayes Optimal"),
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
        ax.set_ylabel("Routing")
        ax.set_xlabel("Outcome")
        ax.set_title(title)
        for i in range(3):
            for j in range(2):
                color = "white" if matrix_pct[i, j] > 15 else "black"
                ax.text(j, i, f"{matrix_pct[i,j]:.1f}%\n({int(matrix[i,j]):,})",
                        ha="center", va="center", fontsize=9, color=color)

    plt.suptitle("Confusion Matrix: Linear vs Multiplicative vs Bayes Optimal", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "fig16_triple_confusion.png", dpi=150, bbox_inches="tight")
    plt.savefig(FIGURES_DIR / "fig16_triple_confusion.svg", bbox_inches="tight")
    plt.close()
    print("  Generated: fig16_triple_confusion.png/svg")


def main():
    print("\n" + "=" * 70)
    print("  CAIRN RECOVERY SCORE CALIBRATION — RUN 4")
    print("  Equation 4: r = F^a × B^b × D^c (Multiplicative)")
    print("  + Bayes-Optimal Baseline")
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

    # References
    from simulation.optimizer import evaluate as eval_eq1
    run1_current = eval_eq1(events, outcomes)
    run1_optimal = eval_eq1(events, outcomes, weights=(0.30, 0.25, 0.45),
                            class_weights=BEST_CW, upper=0.45, lower=0.40)
    print(f"\nRun 1 current:  {run1_current.misrouting_rate:.2%}")
    print(f"Run 1 optimal:  {run1_optimal.misrouting_rate:.2%}")

    # Experiment 13: Bayes-optimal
    bayes = experiment_13_bayes_optimal(events, outcomes, probs)

    # Experiment 14: Multiplicative
    best_mult, best_upper, best_lower, best_mult_result, _ = experiment_14_multiplicative(events, outcomes)

    # Experiment 15: Hybrid
    hybrid_results = experiment_15_hybrid(events, outcomes, best_mult, best_upper, best_lower)
    best_hybrid = hybrid_results[0]

    # Experiment 16: Cross-validation
    cv_rates, cv_mean, cv_std = experiment_16_cross_validation(
        events, best_mult, best_upper, best_lower, "Multiplicative"
    )

    # Summary
    t_total = time.time() - t_start

    print("\n" + "=" * 70)
    print("RUN 4 FINAL SUMMARY")
    print("=" * 70)
    print(f"\n  {'Formula':>35} {'Misrouting':>11}")
    print("  " + "-" * 50)
    print(f"  {'Bayes Optimal (theoretical min)':>35} {bayes['three_tier_misrouting']:11.2%}")
    print(f"  {'':>35} {'─────────'}")
    print(f"  {'Eq4 Multiplicative (best)':>35} {best_mult_result['misrouting_rate']:11.2%}")
    print(f"  {'Eq4b Hybrid (best)':>35} {best_hybrid[3]['misrouting_rate']:11.2%}")
    print(f"  {'Eq1 Linear (Run 1 optimal)':>35} {run1_optimal.misrouting_rate:11.2%}")
    print(f"  {'Eq1 Linear (current)':>35} {run1_current.misrouting_rate:11.2%}")

    gap_to_bayes = best_mult_result["misrouting_rate"] - bayes["three_tier_misrouting"]
    total_improvement = run1_current.misrouting_rate - best_mult_result["misrouting_rate"]
    pct_of_possible = total_improvement / (run1_current.misrouting_rate - bayes["three_tier_misrouting"]) * 100

    print(f"\n  Gap to Bayes optimal: {gap_to_bayes:+.2%} pp")
    print(f"  Total improvement vs current: {total_improvement:+.2%} pp")
    print(f"  % of theoretically achievable: {pct_of_possible:.0f}%")

    print(f"\n  Best multiplicative parameters:")
    print(f"    a (failure class exponent): {best_mult['a']}")
    print(f"    b (budget exponent):        {best_mult['b']}")
    print(f"    c (deadline exponent):      {best_mult['c']}")
    print(f"    upper threshold:            {best_upper}")
    print(f"    lower threshold:            {best_lower}")

    print(f"\n  Best hybrid: alpha={best_hybrid[0]['alpha']}")
    print(f"    upper={best_hybrid[1]}, lower={best_hybrid[2]}")
    print(f"    misrouting: {best_hybrid[3]['misrouting_rate']:.2%}")

    print(f"\n  Cross-validation: {cv_mean:.2%} ± {cv_std:.2%}")
    print(f"  Runtime: {t_total:.1f}s")

    # Figures
    print(f"\nGenerating publication figures...")
    generate_eq4_figures(events, outcomes, probs, bayes, best_mult, best_upper, best_lower)

    # Save results
    results = {
        "run": 4,
        "formula": "Eq4: r = F^a × B^b × D^c",
        "seed": SEED,
        "total_trials": TOTAL_BASELINE_TRIALS,
        "bayes_optimal": {
            "binary_threshold": bayes["binary_threshold"],
            "binary_misrouting": bayes["binary_misrouting"],
            "three_tier_upper": float(bayes["three_tier_upper"]),
            "three_tier_lower": float(bayes["three_tier_lower"]),
            "three_tier_misrouting": bayes["three_tier_misrouting"],
        },
        "eq4_multiplicative": {
            "params": best_mult,
            "class_weights": BEST_CW,
            "thresholds": {"upper": best_upper, "lower": best_lower},
            "misrouting_rate": best_mult_result["misrouting_rate"],
            "false_positive_rate": best_mult_result["false_positive_rate"],
            "false_negative_rate": best_mult_result["false_negative_rate"],
        },
        "eq4b_hybrid": {
            "alpha": best_hybrid[0]["alpha"],
            "thresholds": {"upper": best_hybrid[1], "lower": best_hybrid[2]},
            "misrouting_rate": best_hybrid[3]["misrouting_rate"],
        },
        "cross_validation": {"mean": cv_mean, "std": cv_std},
        "comparison": {
            "current": run1_current.misrouting_rate,
            "eq1_optimal": run1_optimal.misrouting_rate,
            "eq4_multiplicative": best_mult_result["misrouting_rate"],
            "bayes_optimal": bayes["three_tier_misrouting"],
        },
        "gap_to_bayes_pp": gap_to_bayes,
        "total_improvement_pp": total_improvement,
        "pct_of_achievable": pct_of_possible,
        "runtime_seconds": t_total,
    }

    results_path = Path(__file__).parent / "results_eq4.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {results_path}")
    print("Done.")


if __name__ == "__main__":
    main()
