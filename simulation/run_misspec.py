#!/usr/bin/env python3
"""Misspecification / distribution-shift study for the recovery score.

Evaluates routing families (fixed Eq1, fixed Eq4, Eq1 and Eq4 re-fit per world,
a logistic-regression baseline and a binned lookup table) against every
ground-truth world in ``simulation.worlds``, over multiple seeds.

Routing inputs are restricted to the on-chain observables: failure class,
budget remaining B and deadline remaining D. Misrouting and the Bayes baseline
use the definitions of ``run_eq4`` (``evaluate_generic`` and
``experiment_13_bayes_optimal``, three-tier variant).

Usage:
    python3 -m simulation.run_misspec
"""

from __future__ import annotations

import contextlib
import io
import json
import time
from pathlib import Path

import numpy as np

from simulation.config import (
    DEFAULT_CLASS_WEIGHTS, DEFAULT_LOWER_THRESHOLD, DEFAULT_UPPER_THRESHOLD, DEFAULT_WEIGHTS,
    FAILURE_CLASSES,
)
from simulation.generator import generate_events_vectorized
from simulation.optimizer import (
    experiment_1_weights, experiment_2_class_weights, experiment_3_thresholds,
)
from simulation.run_eq4 import (
    BEST_CW, evaluate_generic, experiment_13_bayes_optimal, experiment_14_multiplicative,
)
from simulation.scorer import recovery_score_eq4_multiplicative, recovery_score_vectorized
from simulation.worlds import WORLDS, world_probabilities

SEEDS = tuple(range(42, 52))
N_EVENTS = 100_000
TRAIN_FRACTION = 0.5

EQ4_DEPLOYED = {"a": 0.80, "b": 0.35, "c": 0.15}
EQ4_DEPLOYED_UPPER = 0.40
EQ4_DEPLOYED_LOWER = 0.35

FAMILIES = (
    "eq1_fixed", "eq4_fixed", "eq1_refit", "eq4_refit", "logistic", "binned_lookup",
)
FAMILY_LABELS = {
    "eq1_fixed": "Eq1 fixed (0.5/0.3/0.2, thr 0.30)",
    "eq4_fixed": "Eq4 fixed (0.80/0.35/0.15, thr 0.35/0.40)",
    "eq1_refit": "Eq1 re-fit on train",
    "eq4_refit": "Eq4 re-fit on train",
    "logistic": "Logistic (class, B, D)",
    "binned_lookup": "Binned lookup (class x B x D)",
}

RESULTS_MD = Path(__file__).parent / "RESULTS_MISSPEC.md"
RESULTS_JSON = Path(__file__).parent / "results_misspec.json"

# Two-sided 95% Student-t critical values by degrees of freedom.
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
         9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
         16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042}


def t_critical(df: int) -> float:
    if df in _T975:
        return _T975[df]
    if df > 30:
        return 1.96
    return _T975[max(k for k in _T975 if k <= df)]


def mean_ci(values) -> tuple[float, float]:
    """Mean and 95% CI half-width (Student-t over seeds)."""
    v = np.asarray(values, dtype=float)
    if len(v) < 2:
        return float(v.mean()), 0.0
    half = t_critical(len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
    return float(v.mean()), float(half)


##############################################################################
# Baselines on (class one-hot, B, D)
##############################################################################

def design_matrix(events: dict[str, np.ndarray]) -> np.ndarray:
    """Intercept, RESOURCE and LOGIC indicators (LIVENESS is the reference), B, D."""
    fc = events["failure_class"]
    return np.column_stack([
        np.ones(len(fc)),
        (fc == "RESOURCE").astype(float),
        (fc == "LOGIC").astype(float),
        events["budget_remaining"],
        events["deadline_remaining"],
    ])


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1e-3,
                 max_iter: int = 50, tol: float = 1e-8) -> np.ndarray:
    """Logistic regression by IRLS (Newton) with a small L2 penalty on non-intercept terms."""
    y = np.asarray(y, dtype=float)
    w = np.zeros(X.shape[1])
    penalty = np.full(X.shape[1], l2)
    penalty[0] = 0.0
    for _ in range(max_iter):
        z = np.clip(X @ w, -30.0, 30.0)
        mu = 1.0 / (1.0 + np.exp(-z))
        weights = np.maximum(mu * (1.0 - mu), 1e-10)
        grad = X.T @ (y - mu) - penalty * w
        hess = (X * weights[:, None]).T @ X + np.diag(penalty)
        step = np.linalg.solve(hess, grad)
        w = w + step
        if np.max(np.abs(step)) < tol:
            break
    return w


def predict_logistic(w: np.ndarray, X: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(X @ w, -30.0, 30.0)))


BIN_EDGES = np.linspace(0.0, 1.0, 21)  # 20 bins per axis


def _bin_index(events: dict[str, np.ndarray]) -> np.ndarray:
    nb = len(BIN_EDGES) - 1
    cls = np.zeros(len(events["failure_class"]), dtype=int)
    for i, c in enumerate(FAILURE_CLASSES):
        cls[events["failure_class"] == c] = i
    b = np.clip(np.digitize(events["budget_remaining"], BIN_EDGES[1:-1]), 0, nb - 1)
    d = np.clip(np.digitize(events["deadline_remaining"], BIN_EDGES[1:-1]), 0, nb - 1)
    return (cls * nb + b) * nb + d


def fit_binned(events: dict[str, np.ndarray], outcomes: np.ndarray) -> np.ndarray:
    """Empirical success rate per (class, B bin, D bin) cell; empty cells get the class rate."""
    nb = len(BIN_EDGES) - 1
    n_cells = len(FAILURE_CLASSES) * nb * nb
    idx = _bin_index(events)
    succ = np.bincount(idx, weights=outcomes.astype(float), minlength=n_cells)
    cnt = np.bincount(idx, minlength=n_cells).astype(float)
    table = np.zeros(n_cells)
    for i, c in enumerate(FAILURE_CLASSES):
        mask = events["failure_class"] == c
        class_rate = outcomes[mask].mean() if mask.any() else outcomes.mean()
        sl = slice(i * nb * nb, (i + 1) * nb * nb)
        table[sl] = np.where(cnt[sl] > 0, succ[sl] / np.maximum(cnt[sl], 1.0), class_rate)
    return table


def predict_binned(table: np.ndarray, events: dict[str, np.ndarray]) -> np.ndarray:
    return table[_bin_index(events)]


##############################################################################
# Fitting helpers (reuse run_eq4 / optimizer; their progress output is discarded)
##############################################################################

def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def bayes_three_tier(events, outcomes, probs) -> float:
    """Three-tier Bayes misrouting exactly as run_eq4.experiment_13_bayes_optimal."""
    return float(_quiet(experiment_13_bayes_optimal, events, outcomes, probs)["three_tier_misrouting"])


def fit_score_thresholds(scores: np.ndarray, outcomes: np.ndarray) -> tuple[float, float]:
    """Pick (upper, lower) for a probability-like score on the same grid as the Bayes sweep."""
    res = _quiet(experiment_13_bayes_optimal, None, outcomes, scores)
    return float(res["three_tier_upper"]), float(res["three_tier_lower"])


def fit_eq1(events, outcomes) -> dict:
    """Run 1 sequence: weights, then class weights, then thresholds (optimizer.py grids)."""
    best_w = experiment_1_weights(events, outcomes)[0].weights
    best_cw = experiment_2_class_weights(events, outcomes, best_weights=best_w)[0].class_weights
    best_thr = experiment_3_thresholds(events, outcomes, best_weights=best_w,
                                       best_class_weights=best_cw)[0]
    return {"weights": tuple(best_w), "class_weights": best_cw,
            "upper": best_thr.upper_threshold, "lower": best_thr.lower_threshold}


def fit_eq4(events, outcomes) -> dict:
    """run_eq4 Experiment 14 grid (class weights fixed at BEST_CW)."""
    params, upper, lower, _, _ = _quiet(experiment_14_multiplicative, events, outcomes)
    return {"params": dict(params), "upper": float(upper), "lower": float(lower)}


def eq1_scores(events, weights=DEFAULT_WEIGHTS, class_weights=None):
    return recovery_score_vectorized(
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        weights=weights, class_weights=class_weights or DEFAULT_CLASS_WEIGHTS,
    )


def eq4_scores(events, params=None, class_weights=None):
    return recovery_score_eq4_multiplicative(
        events["failure_class"], events["budget_remaining"], events["deadline_remaining"],
        class_weights=class_weights or BEST_CW, params=params or EQ4_DEPLOYED,
    )


##############################################################################
# One (seed, world) cell
##############################################################################

def split(events: dict[str, np.ndarray], outcomes: np.ndarray, probs: np.ndarray):
    n_train = int(len(outcomes) * TRAIN_FRACTION)
    tr = slice(0, n_train)
    te = slice(n_train, len(outcomes))
    return ({k: v[tr] for k, v in events.items()}, outcomes[tr], probs[tr],
            {k: v[te] for k, v in events.items()}, outcomes[te], probs[te])


def simulate_world(name: str, seed: int, n: int = N_EVENTS):
    """Events, true probabilities and outcomes for one world and seed.

    Events and the outcome uniforms are drawn from default_rng(seed) in the same
    order as run_eq4 (events, then one uniform per event), so all worlds share
    the same events and uniforms, and the multiplicative world at seed 42
    reproduces run_eq4's outcomes. heavy_tail shocks use default_rng([seed, 1]).
    """
    rng = np.random.default_rng(seed)
    events = generate_events_vectorized(n, rng)
    u = rng.random(n)
    probs = world_probabilities(name, events, rng=np.random.default_rng([seed, 1]))
    return events, probs, u < probs


def evaluate_cell(name: str, seed: int, n: int = N_EVENTS) -> dict:
    events, probs, outcomes = simulate_world(name, seed, n)
    ev_tr, y_tr, _, ev_te, y_te, p_te = split(events, outcomes, probs)

    scores: dict[str, np.ndarray] = {}
    thresholds: dict[str, tuple[float, float]] = {}
    fitted: dict[str, dict] = {}

    scores["eq1_fixed"] = eq1_scores(ev_te)
    thresholds["eq1_fixed"] = (DEFAULT_UPPER_THRESHOLD, DEFAULT_LOWER_THRESHOLD)

    scores["eq4_fixed"] = eq4_scores(ev_te)
    thresholds["eq4_fixed"] = (EQ4_DEPLOYED_UPPER, EQ4_DEPLOYED_LOWER)

    f1 = fit_eq1(ev_tr, y_tr)
    fitted["eq1_refit"] = f1
    scores["eq1_refit"] = eq1_scores(ev_te, f1["weights"], f1["class_weights"])
    thresholds["eq1_refit"] = (f1["upper"], f1["lower"])

    f4 = fit_eq4(ev_tr, y_tr)
    fitted["eq4_refit"] = f4
    scores["eq4_refit"] = eq4_scores(ev_te, f4["params"])
    thresholds["eq4_refit"] = (f4["upper"], f4["lower"])

    w = fit_logistic(design_matrix(ev_tr), y_tr)
    fitted["logistic"] = {"coef": [float(x) for x in w]}
    thresholds["logistic"] = fit_score_thresholds(predict_logistic(w, design_matrix(ev_tr)), y_tr)
    scores["logistic"] = predict_logistic(w, design_matrix(ev_te))

    table = fit_binned(ev_tr, y_tr)
    thresholds["binned_lookup"] = fit_score_thresholds(predict_binned(table, ev_tr), y_tr)
    scores["binned_lookup"] = predict_binned(table, ev_te)

    y_f = y_te.astype(float)
    out = {
        "world": name, "seed": seed, "n_train": len(y_tr), "n_test": len(y_te),
        "test_success_rate": float(y_te.mean()),
        "bayes_misrouting": bayes_three_tier(ev_te, y_te, p_te),
        "oracle_brier": float(np.mean((p_te - y_f) ** 2)),
        "families": {},
    }
    for fam in FAMILIES:
        upper, lower = thresholds[fam]
        r = evaluate_generic(scores[fam], y_te, upper, lower)
        out["families"][fam] = {
            "misrouting": float(r["misrouting_rate"]),
            "brier": float(np.mean((scores[fam] - y_f) ** 2)),
            "upper": float(upper), "lower": float(lower),
            "fitted": fitted.get(fam),
        }
    return out


##############################################################################
# Aggregation and reporting
##############################################################################

def aggregate(cells: list[dict]) -> dict:
    agg = {}
    for world in WORLDS:
        wc = [c for c in cells if c["world"] == world]
        entry = {
            "test_success_rate": mean_ci([c["test_success_rate"] for c in wc]),
            "bayes_misrouting": mean_ci([c["bayes_misrouting"] for c in wc]),
            "oracle_brier": mean_ci([c["oracle_brier"] for c in wc]),
            "families": {},
        }
        for fam in FAMILIES:
            mis = [c["families"][fam]["misrouting"] for c in wc]
            gap = [c["families"][fam]["misrouting"] - c["bayes_misrouting"] for c in wc]
            vs_eq4 = [c["families"][fam]["misrouting"] - c["families"]["eq4_fixed"]["misrouting"]
                      for c in wc]
            entry["families"][fam] = {
                "misrouting": mean_ci(mis),
                "gap_to_bayes": mean_ci(gap),
                "diff_vs_eq4_fixed": mean_ci(vs_eq4),
                "brier": mean_ci([c["families"][fam]["brier"] for c in wc]),
            }
        agg[world] = entry
    return agg


def _pct(m_ci: tuple[float, float]) -> str:
    m, h = m_ci
    return f"{m * 100:.2f} ± {h * 100:.2f}"


def _pp(m_ci: tuple[float, float]) -> str:
    m, h = m_ci
    return f"{m * 100:+.2f} ± {h * 100:.2f}"


def _brier(m_ci: tuple[float, float]) -> str:
    m, h = m_ci
    return f"{m:.4f} ± {h:.4f}"


def _eq4_refit_params(cells: list[dict], world: str) -> str:
    from collections import Counter
    wc = [c for c in cells if c["world"] == world]
    combos = Counter(
        (c["families"]["eq4_refit"]["fitted"]["params"]["a"],
         c["families"]["eq4_refit"]["fitted"]["params"]["b"],
         c["families"]["eq4_refit"]["fitted"]["params"]["c"],
         c["families"]["eq4_refit"]["upper"], c["families"]["eq4_refit"]["lower"])
        for c in wc
    )
    (a, b, cc, u, l), k = combos.most_common(1)[0]
    return f"a={a:.2f}, b={b:.2f}, c={cc:.2f}, upper={u:.2f}, lower={l:.2f} ({k}/{len(wc)} seeds)"


def _eq1_refit_params(cells: list[dict], world: str) -> str:
    from collections import Counter
    wc = [c for c in cells if c["world"] == world]
    combos = Counter(
        (tuple(c["families"]["eq1_refit"]["fitted"]["weights"]),
         tuple(c["families"]["eq1_refit"]["fitted"]["class_weights"][k] for k in FAILURE_CLASSES),
         c["families"]["eq1_refit"]["upper"], c["families"]["eq1_refit"]["lower"])
        for c in wc
    )
    (w, cw, u, l), k = combos.most_common(1)[0]
    return (f"w=({w[0]:.2f}, {w[1]:.2f}, {w[2]:.2f}), F=({cw[0]:.2f}, {cw[1]:.2f}, {cw[2]:.2f}), "
            f"upper={u:.2f}, lower={l:.2f} ({k}/{len(wc)} seeds)")


def _significant(m_ci: tuple[float, float]) -> bool:
    return abs(m_ci[0]) > m_ci[1]


def observations(agg: dict) -> list[str]:
    """Statements derived mechanically from the aggregated numbers."""
    obs = []
    for world, e in agg.items():
        fams = e["families"]
        ranked = sorted(FAMILIES, key=lambda f: fams[f]["misrouting"][0])
        best = ranked[0]
        eq4 = fams["eq4_fixed"]
        line = (f"`{world}`: lowest mean misrouting among the evaluated families is "
                f"{FAMILY_LABELS[best]} ({_pct(fams[best]['misrouting'])}%); "
                f"Eq4 fixed is {_pct(eq4['misrouting'])}%, "
                f"{_pp(eq4['gap_to_bayes'])} pp from the Bayes baseline "
                f"({_pct(e['bayes_misrouting'])}%).")
        obs.append(line)

    for fam in ("logistic", "eq4_refit", "binned_lookup", "eq1_refit"):
        better = [w for w, e in agg.items()
                  if e["families"][fam]["diff_vs_eq4_fixed"][0] < 0
                  and _significant(e["families"][fam]["diff_vs_eq4_fixed"])]
        worse = [w for w, e in agg.items()
                 if e["families"][fam]["diff_vs_eq4_fixed"][0] > 0
                 and _significant(e["families"][fam]["diff_vs_eq4_fixed"])]
        tied = [w for w in agg if w not in better and w not in worse]
        obs.append(
            f"{FAMILY_LABELS[fam]} vs Eq4 fixed (paired over seeds, 95% CI excludes 0): "
            f"lower misrouting in {', '.join(f'`{w}`' for w in better) or 'no world'}; "
            f"higher in {', '.join(f'`{w}`' for w in worse) or 'no world'}; "
            f"not distinguishable in {', '.join(f'`{w}`' for w in tied) or 'no world'}."
        )

    worst = max(agg, key=lambda w: agg[w]["families"]["eq4_fixed"]["gap_to_bayes"][0])
    obs.append(
        f"The largest Eq4-fixed gap to the Bayes baseline is in `{worst}` "
        f"({_pp(agg[worst]['families']['eq4_fixed']['gap_to_bayes'])} pp)."
    )
    brier_best = {w: min(("logistic", "binned_lookup", "eq4_fixed", "eq4_refit", "eq1_fixed",
                          "eq1_refit"), key=lambda f: e["families"][f]["brier"][0])
                  for w, e in agg.items()}
    obs.append(
        "Lowest mean Brier score per world: "
        + "; ".join(f"`{w}` {FAMILY_LABELS[f]}" for w, f in brier_best.items()) + "."
    )
    return obs


WORLD_FORMULAS = {
    "multiplicative": "p = base · sB · sD · C · S (existing `recovery.py` model)",
    "additive": "p = clip(0.60·base + 0.20·sB + 0.15·sD + 0.15·C + 0.10·S − 0.5074, 0, 1)",
    "threshold": "p = 0.7872 · base · sig(B; 200, 0.15) · sig(D; 200, 0.10)",
    "interaction": ("p = clip(0.45·base + 0.10·sB + 0.05·sD + 0.05·C + 0.05·S "
                    "+ 0.25·sB·S + 0.20·sD·C − 0.4550, 0, 1)"),
    "heavy_tail": ("p = sigmoid(logit(p_mult) + 0.5·ε), ε ~ Student-t(ν=2), "
                   "one draw per event"),
    "nonstationary": ("p = base_c(t) · sig(B; kB(t), cB(t)) · sig(D; kD(t), cD(t)) · C · S, "
                      "t = event index / (n − 1); base LIVENESS 0.92→0.80, RESOURCE 0.48→0.62, "
                      "LOGIC 0.08→0.15; cB 0.15→0.35, kB 15→8; cD 0.10→0.25, kD 20→10"),
}


def write_markdown(agg: dict, cells: list[dict], path: Path = RESULTS_MD) -> None:
    n_train = cells[0]["n_train"]
    n_test = cells[0]["n_test"]
    L = []
    L.append("# Recovery Score Misspecification Study")
    L.append("")
    L.append(f"> Seeds: {SEEDS[0]}–{SEEDS[-1]} ({len(SEEDS)} seeds) | "
             f"Events per seed and world: {N_EVENTS:,} "
             f"(train {n_train:,} / test {n_test:,}) | Intervals: mean ± 95% CI (Student-t over seeds)")
    L.append("")
    L.append("## Reproduction")
    L.append("")
    L.append("```bash")
    L.append("python3 -m simulation.run_misspec")
    L.append("```")
    L.append("")
    L.append("Deterministic for the fixed seed list. Writes this file and `simulation/results_misspec.json`.")
    L.append("")
    L.append("## Setup")
    L.append("")
    L.append("### Events and splits")
    L.append("")
    L.append("- Events come from `generate_events_vectorized` (unchanged). For each seed, events and one "
             "uniform per event are drawn from `numpy.random.default_rng(seed)` in the same order as "
             "`run_eq4`; the outcome is `uniform < p`. All worlds share the same events and uniforms "
             "for a given seed.")
    L.append(f"- Train split: first {TRAIN_FRACTION:.0%} of events by index; test split: remaining events. "
             "All reported metrics are on the test split. For `nonstationary`, index order is time order, "
             "so fitting uses the first half of the stream and evaluation the second half.")
    L.append("- Routing inputs are limited to failure class, B and D. `remaining_subtasks`, "
             "`fallback_skill` and the `heavy_tail` shock enter the ground truth only.")
    L.append("")
    L.append("### Worlds")
    L.append("")
    L.append("Notation: base = class base rate (LIVENESS 0.92, RESOURCE 0.48, LOGIC 0.08); "
             "sig(x; k, c) = 1/(1+exp(−k(x−c))); sB = sig(B; 15, 0.15); sD = sig(D; 20, 0.10); "
             "C = 1/(1+0.02·remaining_subtasks); S = 0.4 + 0.6·fallback_skill. "
             "Offsets/scales in `additive`, `threshold` and `interaction` are fixed constants chosen so "
             "the mean success probability equals the multiplicative world's on a reference sample "
             "(seed 0, 400,000 events). Definitions: `simulation/worlds.py`.")
    L.append("")
    L.append("| World | Ground truth | Test success rate (%) |")
    L.append("|---|---|---|")
    for w in WORLDS:
        L.append(f"| `{w}` | {WORLD_FORMULAS[w]} | {_pct(agg[w]['test_success_rate'])} |")
    L.append("")
    L.append("### Routing families")
    L.append("")
    L.append("| Family | Score | Parameters and thresholds |")
    L.append("|---|---|---|")
    L.append("| Eq1 fixed | r = w_f·F + w_b·B + w_d·D | w = (0.5, 0.3, 0.2); F = (0.9, 0.5, 0.1); "
             "upper 0.60, lower 0.30 (`config.py` defaults) |")
    L.append("| Eq4 fixed | r = F^a · B^b · D^c | a = 0.80, b = 0.35, c = 0.15; F = (0.70, 0.30, 0.00); "
             "upper 0.40, lower 0.35 |")
    L.append("| Eq1 re-fit | as Eq1 | train split, `optimizer.py` sequence: weights grid → class-weight grid "
             "→ threshold grid |")
    L.append("| Eq4 re-fit | as Eq4 | train split, `run_eq4` Experiment 14 grid (exponents × threshold "
             "pairs, then threshold refinement); F fixed at (0.70, 0.30, 0.00) |")
    L.append("| Logistic | P(success) = sigmoid(β0 + β1·[RESOURCE] + β2·[LOGIC] + β3·B + β4·D) | "
             "IRLS on the train split (L2 1e-3 on non-intercept terms); thresholds chosen on train "
             "with the Bayes-baseline grid |")
    L.append("| Binned lookup | empirical train success rate per (class, B bin, D bin), 20 × 20 bins | "
             "thresholds chosen on train with the Bayes-baseline grid |")
    L.append("")
    L.append("F values are listed as (LIVENESS, RESOURCE, LOGIC).")
    L.append("")
    L.append("### Metrics")
    L.append("")
    L.append("- **Misrouting** (`run_eq4.evaluate_generic`): (routed to FULL or REDUCED and failed + "
             "routed to DISPUTED and succeeded) / n.")
    L.append("- **Bayes baseline** (`run_eq4.experiment_13_bayes_optimal`, three-tier): minimum "
             "misrouting over the threshold grid when routing on the true p, computed on the test "
             "split. The true p includes the hidden variables (and the `heavy_tail` shock), so this "
             "baseline uses more information than any rule restricted to class, B and D.")
    L.append("- **Brier score**: mean (score − outcome)² on the test split. Eq1 and Eq4 scores are "
             "not constructed as probabilities; their Brier scores are reported for completeness. "
             "The oracle row uses the true p.")
    L.append("")
    L.append("## Results")
    L.append("")
    L.append("### Misrouting (%) on the test split")
    L.append("")
    header = "| Family | " + " | ".join(f"`{w}`" for w in WORLDS) + " |"
    L.append(header)
    L.append("|---|" + "---|" * len(WORLDS))
    L.append("| Bayes baseline (true p) | "
             + " | ".join(_pct(agg[w]["bayes_misrouting"]) for w in WORLDS) + " |")
    for fam in FAMILIES:
        L.append(f"| {FAMILY_LABELS[fam]} | "
                 + " | ".join(_pct(agg[w]["families"][fam]["misrouting"]) for w in WORLDS) + " |")
    L.append("")
    L.append("### Gap to the Bayes baseline (pp, paired over seeds)")
    L.append("")
    L.append(header)
    L.append("|---|" + "---|" * len(WORLDS))
    for fam in FAMILIES:
        L.append(f"| {FAMILY_LABELS[fam]} | "
                 + " | ".join(_pp(agg[w]["families"][fam]["gap_to_bayes"]) for w in WORLDS) + " |")
    L.append("")
    L.append("### Difference vs Eq4 fixed (pp, paired over seeds; negative = lower misrouting than Eq4 fixed)")
    L.append("")
    L.append(header)
    L.append("|---|" + "---|" * len(WORLDS))
    for fam in FAMILIES:
        if fam == "eq4_fixed":
            continue
        L.append(f"| {FAMILY_LABELS[fam]} | "
                 + " | ".join(_pp(agg[w]["families"][fam]["diff_vs_eq4_fixed"]) for w in WORLDS) + " |")
    L.append("")
    L.append("### Brier score on the test split")
    L.append("")
    L.append(header)
    L.append("|---|" + "---|" * len(WORLDS))
    L.append("| Oracle (true p) | " + " | ".join(_brier(agg[w]["oracle_brier"]) for w in WORLDS) + " |")
    for fam in FAMILIES:
        L.append(f"| {FAMILY_LABELS[fam]} | "
                 + " | ".join(_brier(agg[w]["families"][fam]["brier"]) for w in WORLDS) + " |")
    L.append("")
    L.append("### Re-fit parameters (most frequent selection across seeds)")
    L.append("")
    L.append("| World | Eq1 re-fit | Eq4 re-fit |")
    L.append("|---|---|---|")
    for w in WORLDS:
        L.append(f"| `{w}` | {_eq1_refit_params(cells, w)} | {_eq4_refit_params(cells, w)} |")
    L.append("")
    L.append("## Observations")
    L.append("")
    for o in observations(agg):
        L.append(f"- {o}")
    L.append("")
    path.write_text("\n".join(L))


def print_summary(agg: dict) -> None:
    print("\n" + "=" * 110)
    print("MISROUTING (%) ON TEST SPLIT — mean ± 95% CI over seeds")
    print("=" * 110)
    col = 16
    print(f"  {'Family':<42}" + "".join(f"{w:>{col}}" for w in WORLDS))
    print("  " + "-" * (42 + col * len(WORLDS)))
    print(f"  {'Bayes baseline (true p)':<42}"
          + "".join(f"{_pct(agg[w]['bayes_misrouting']):>{col}}" for w in WORLDS))
    for fam in FAMILIES:
        print(f"  {FAMILY_LABELS[fam]:<42}"
              + "".join(f"{_pct(agg[w]['families'][fam]['misrouting']):>{col}}" for w in WORLDS))
    print("\n  Brier score")
    print(f"  {'Oracle (true p)':<42}" + "".join(f"{_brier(agg[w]['oracle_brier']):>{col + 2}}"
                                                 for w in WORLDS))
    for fam in FAMILIES:
        print(f"  {FAMILY_LABELS[fam]:<42}"
              + "".join(f"{_brier(agg[w]['families'][fam]['brier']):>{col + 2}}" for w in WORLDS))


def main(seeds=SEEDS, n_events: int = N_EVENTS) -> dict:
    print("\n" + "=" * 70)
    print("  CAIRN RECOVERY SCORE — MISSPECIFICATION STUDY")
    print(f"  Worlds: {', '.join(WORLDS)}")
    print(f"  Seeds: {seeds[0]}..{seeds[-1]} | Events per seed/world: {n_events:,}")
    print("=" * 70)

    t0 = time.time()
    cells = []
    for world in WORLDS:
        for seed in seeds:
            t1 = time.time()
            cell = evaluate_cell(world, seed, n_events)
            cells.append(cell)
            print(f"  {world:<15} seed={seed}  bayes={cell['bayes_misrouting']:.2%}  "
                  f"eq4_fixed={cell['families']['eq4_fixed']['misrouting']:.2%}  "
                  f"logistic={cell['families']['logistic']['misrouting']:.2%}  "
                  f"({time.time() - t1:.1f}s)")

    agg = aggregate(cells)
    print_summary(agg)
    runtime = time.time() - t0
    print(f"\n  Runtime: {runtime:.1f}s")

    write_markdown(agg, cells)
    with open(RESULTS_JSON, "w") as f:
        json.dump({"seeds": list(seeds), "n_events": n_events, "train_fraction": TRAIN_FRACTION,
                   "aggregate": agg, "cells": cells}, f, indent=2, default=str)
    print(f"  Wrote {RESULTS_MD}")
    print(f"  Wrote {RESULTS_JSON}")
    return agg


if __name__ == "__main__":
    main()
