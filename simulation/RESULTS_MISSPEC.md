# Recovery Score Misspecification Study

> Seeds: 42–51 (10 seeds) | Events per seed and world: 100,000 (train 50,000 / test 50,000) | Intervals: mean ± 95% CI (Student-t over seeds)

## Reproduction

```bash
python3 -m simulation.run_misspec
```

Deterministic for the fixed seed list. Writes this file and `simulation/results_misspec.json`.

## Setup

### Events and splits

- Events come from `generate_events_vectorized` (unchanged). For each seed, events and one uniform per event are drawn from `numpy.random.default_rng(seed)` in the same order as `run_eq4`; the outcome is `uniform < p`. All worlds share the same events and uniforms for a given seed.
- Train split: first 50% of events by index; test split: remaining events. All reported metrics are on the test split. For `nonstationary`, index order is time order, so fitting uses the first half of the stream and evaluation the second half.
- Routing inputs are limited to failure class, B and D. `remaining_subtasks`, `fallback_skill` and the `heavy_tail` shock enter the ground truth only.

### Worlds

Notation: base = class base rate (LIVENESS 0.92, RESOURCE 0.48, LOGIC 0.08); sig(x; k, c) = 1/(1+exp(−k(x−c))); sB = sig(B; 15, 0.15); sD = sig(D; 20, 0.10); C = 1/(1+0.02·remaining_subtasks); S = 0.4 + 0.6·fallback_skill. Offsets/scales in `additive`, `threshold` and `interaction` are fixed constants chosen so the mean success probability equals the multiplicative world's on a reference sample (seed 0, 400,000 events). Definitions: `simulation/worlds.py`.

| World | Ground truth | Test success rate (%) |
|---|---|---|
| `multiplicative` | p = base · sB · sD · C · S (existing `recovery.py` model) | 37.15 ± 0.12 |
| `additive` | p = clip(0.60·base + 0.20·sB + 0.15·sD + 0.15·C + 0.10·S − 0.5074, 0, 1) | 37.17 ± 0.11 |
| `threshold` | p = 0.7872 · base · sig(B; 200, 0.15) · sig(D; 200, 0.10) | 37.12 ± 0.09 |
| `interaction` | p = clip(0.45·base + 0.10·sB + 0.05·sD + 0.05·C + 0.05·S + 0.25·sB·S + 0.20·sD·C − 0.4550, 0, 1) | 37.19 ± 0.17 |
| `heavy_tail` | p = sigmoid(logit(p_mult) + 0.5·ε), ε ~ Student-t(ν=2), one draw per event | 37.55 ± 0.15 |
| `nonstationary` | p = base_c(t) · sig(B; kB(t), cB(t)) · sig(D; kD(t), cD(t)) · C · S, t = event index / (n − 1); base LIVENESS 0.92→0.80, RESOURCE 0.48→0.62, LOGIC 0.08→0.15; cB 0.15→0.35, kB 15→8; cD 0.10→0.25, kD 20→10 | 28.84 ± 0.14 |

### Routing families

| Family | Score | Parameters and thresholds |
|---|---|---|
| Eq1 fixed | r = w_f·F + w_b·B + w_d·D | w = (0.5, 0.3, 0.2); F = (0.9, 0.5, 0.1); upper 0.60, lower 0.30 (`config.py` defaults) |
| Eq4 fixed | r = F^a · B^b · D^c | a = 0.80, b = 0.35, c = 0.15; F = (0.70, 0.30, 0.00); upper 0.40, lower 0.35 |
| Eq1 re-fit | as Eq1 | train split, `optimizer.py` sequence: weights grid → class-weight grid → threshold grid |
| Eq4 re-fit | as Eq4 | train split, `run_eq4` Experiment 14 grid (exponents × threshold pairs, then threshold refinement); F fixed at (0.70, 0.30, 0.00) |
| Logistic | P(success) = sigmoid(β0 + β1·[RESOURCE] + β2·[LOGIC] + β3·B + β4·D) | IRLS on the train split (L2 1e-3 on non-intercept terms); thresholds chosen on train with the Bayes-baseline grid |
| Binned lookup | empirical train success rate per (class, B bin, D bin), 20 × 20 bins | thresholds chosen on train with the Bayes-baseline grid |

F values are listed as (LIVENESS, RESOURCE, LOGIC).

### Metrics

- **Misrouting** (`run_eq4.evaluate_generic`): (routed to FULL or REDUCED and failed + routed to DISPUTED and succeeded) / n.
- **Bayes baseline** (`run_eq4.experiment_13_bayes_optimal`, three-tier): minimum misrouting over the threshold grid when routing on the true p, computed on the test split. The true p includes the hidden variables (and the `heavy_tail` shock), so this baseline uses more information than any rule restricted to class, B and D.
- **Brier score**: mean (score − outcome)² on the test split. Eq1 and Eq4 scores are not constructed as probabilities; their Brier scores are reported for completeness. The oracle row uses the true p.

## Results

### Misrouting (%) on the test split

| Family | `multiplicative` | `additive` | `threshold` | `interaction` | `heavy_tail` | `nonstationary` |
|---|---|---|---|---|---|---|
| Bayes baseline (true p) | 22.34 ± 0.11 | 29.51 ± 0.12 | 21.38 ± 0.12 | 30.81 ± 0.08 | 20.89 ± 0.11 | 22.87 ± 0.10 |
| Eq1 fixed (0.5/0.3/0.2, thr 0.30) | 47.50 ± 0.18 | 48.60 ± 0.17 | 47.37 ± 0.16 | 49.10 ± 0.23 | 47.62 ± 0.22 | 55.54 ± 0.19 |
| Eq4 fixed (0.80/0.35/0.15, thr 0.35/0.40) | 23.33 ± 0.14 | 30.76 ± 0.14 | 23.34 ± 0.12 | 31.59 ± 0.07 | 25.13 ± 0.11 | 26.92 ± 0.15 |
| Eq1 re-fit on train | 33.54 ± 0.18 | 41.10 ± 0.19 | 34.43 ± 0.16 | 38.68 ± 0.14 | 34.53 ± 0.16 | 33.12 ± 0.16 |
| Eq4 re-fit on train | 23.34 ± 0.13 | 30.78 ± 0.14 | 22.83 ± 0.12 | 31.60 ± 0.08 | 25.14 ± 0.11 | 24.89 ± 0.33 |
| Logistic (class, B, D) | 24.47 ± 0.15 | 29.80 ± 0.14 | 24.09 ± 0.15 | 32.71 ± 0.24 | 26.32 ± 0.13 | 25.27 ± 0.34 |
| Binned lookup (class x B x D) | 22.48 ± 0.11 | 29.67 ± 0.14 | 21.51 ± 0.13 | 31.05 ± 0.09 | 24.47 ± 0.13 | 24.98 ± 0.20 |

### Gap to the Bayes baseline (pp, paired over seeds)

| Family | `multiplicative` | `additive` | `threshold` | `interaction` | `heavy_tail` | `nonstationary` |
|---|---|---|---|---|---|---|
| Eq1 fixed (0.5/0.3/0.2, thr 0.30) | +25.16 ± 0.18 | +19.09 ± 0.13 | +25.99 ± 0.19 | +18.28 ± 0.26 | +26.72 ± 0.21 | +32.67 ± 0.22 |
| Eq4 fixed (0.80/0.35/0.15, thr 0.35/0.40) | +0.99 ± 0.06 | +1.25 ± 0.09 | +1.95 ± 0.09 | +0.77 ± 0.05 | +4.24 ± 0.13 | +4.05 ± 0.13 |
| Eq1 re-fit on train | +11.21 ± 0.16 | +11.59 ± 0.16 | +13.04 ± 0.18 | +7.86 ± 0.15 | +13.63 ± 0.16 | +10.25 ± 0.13 |
| Eq4 re-fit on train | +1.00 ± 0.06 | +1.27 ± 0.07 | +1.45 ± 0.09 | +0.79 ± 0.06 | +4.25 ± 0.13 | +2.02 ± 0.31 |
| Logistic (class, B, D) | +2.13 ± 0.10 | +0.28 ± 0.09 | +2.71 ± 0.12 | +1.90 ± 0.21 | +5.42 ± 0.16 | +2.40 ± 0.35 |
| Binned lookup (class x B x D) | +0.14 ± 0.03 | +0.15 ± 0.06 | +0.12 ± 0.03 | +0.23 ± 0.05 | +3.58 ± 0.17 | +2.12 ± 0.17 |

### Difference vs Eq4 fixed (pp, paired over seeds; negative = lower misrouting than Eq4 fixed)

| Family | `multiplicative` | `additive` | `threshold` | `interaction` | `heavy_tail` | `nonstationary` |
|---|---|---|---|---|---|---|
| Eq1 fixed (0.5/0.3/0.2, thr 0.30) | +24.17 ± 0.17 | +17.84 ± 0.13 | +24.03 ± 0.14 | +17.51 ± 0.23 | +22.49 ± 0.18 | +28.62 ± 0.18 |
| Eq1 re-fit on train | +10.21 ± 0.16 | +10.34 ± 0.15 | +11.09 ± 0.16 | +7.09 ± 0.13 | +9.40 ± 0.16 | +6.21 ± 0.09 |
| Eq4 re-fit on train | +0.01 ± 0.02 | +0.02 ± 0.05 | -0.50 ± 0.04 | +0.01 ± 0.04 | +0.01 ± 0.02 | -2.02 ± 0.37 |
| Logistic (class, B, D) | +1.14 ± 0.10 | -0.96 ± 0.10 | +0.76 ± 0.10 | +1.12 ± 0.22 | +1.19 ± 0.12 | -1.65 ± 0.31 |
| Binned lookup (class x B x D) | -0.85 ± 0.08 | -1.09 ± 0.11 | -1.83 ± 0.10 | -0.54 ± 0.08 | -0.66 ± 0.11 | -1.93 ± 0.25 |

### Brier score on the test split

| Family | `multiplicative` | `additive` | `threshold` | `interaction` | `heavy_tail` | `nonstationary` |
|---|---|---|---|---|---|---|
| Oracle (true p) | 0.1526 ± 0.0006 | 0.1904 ± 0.0005 | 0.1465 ± 0.0007 | 0.1943 ± 0.0003 | 0.1417 ± 0.0005 | 0.1452 ± 0.0005 |
| Eq1 fixed (0.5/0.3/0.2, thr 0.30) | 0.1999 ± 0.0006 | 0.2240 ± 0.0006 | 0.2004 ± 0.0006 | 0.2278 ± 0.0005 | 0.2057 ± 0.0007 | 0.2158 ± 0.0007 |
| Eq4 fixed (0.80/0.35/0.15, thr 0.35/0.40) | 0.1701 ± 0.0006 | 0.2063 ± 0.0007 | 0.1698 ± 0.0005 | 0.2108 ± 0.0007 | 0.1797 ± 0.0007 | 0.1576 ± 0.0006 |
| Eq1 re-fit on train | 0.1973 ± 0.0006 | 0.2270 ± 0.0008 | 0.1982 ± 0.0006 | 0.2187 ± 0.0005 | 0.2025 ± 0.0006 | 0.1836 ± 0.0005 |
| Eq4 re-fit on train | 0.1701 ± 0.0005 | 0.2053 ± 0.0010 | 0.1672 ± 0.0005 | 0.2119 ± 0.0011 | 0.1797 ± 0.0007 | 0.1560 ± 0.0006 |
| Logistic (class, B, D) | 0.1704 ± 0.0006 | 0.1940 ± 0.0005 | 0.1710 ± 0.0006 | 0.2038 ± 0.0004 | 0.1796 ± 0.0006 | 0.1596 ± 0.0006 |
| Binned lookup (class x B x D) | 0.1550 ± 0.0006 | 0.1922 ± 0.0005 | 0.1483 ± 0.0007 | 0.1964 ± 0.0003 | 0.1659 ± 0.0007 | 0.1590 ± 0.0006 |

### Re-fit parameters (most frequent selection across seeds)

| World | Eq1 re-fit | Eq4 re-fit |
|---|---|---|
| `multiplicative` | w=(0.30, 0.25, 0.45), F=(0.70, 0.30, 0.00), upper=0.45, lower=0.40 (5/10 seeds) | a=0.80, b=0.35, c=0.15, upper=0.40, lower=0.35 (5/10 seeds) |
| `additive` | w=(0.30, 0.30, 0.40), F=(0.70, 0.30, 0.00), upper=0.45, lower=0.40 (4/10 seeds) | a=0.80, b=0.35, c=0.15, upper=0.40, lower=0.35 (3/10 seeds) |
| `threshold` | w=(0.30, 0.25, 0.45), F=(0.70, 0.30, 0.00), upper=0.45, lower=0.40 (3/10 seeds) | a=0.80, b=0.35, c=0.10, upper=0.40, lower=0.35 (6/10 seeds) |
| `interaction` | w=(0.30, 0.25, 0.45), F=(0.70, 0.30, 0.00), upper=0.45, lower=0.40 (4/10 seeds) | a=0.80, b=0.35, c=0.20, upper=0.40, lower=0.35 (4/10 seeds) |
| `heavy_tail` | w=(0.30, 0.20, 0.50), F=(0.70, 0.30, 0.00), upper=0.45, lower=0.40 (4/10 seeds) | a=0.80, b=0.35, c=0.15, upper=0.40, lower=0.35 (4/10 seeds) |
| `nonstationary` | w=(0.30, 0.25, 0.45), F=(0.70, 0.30, 0.00), upper=0.45, lower=0.40 (3/10 seeds) | a=0.80, b=0.35, c=0.25, upper=0.40, lower=0.35 (2/10 seeds) |

## Observations

- `multiplicative`: lowest mean misrouting among the evaluated families is Binned lookup (class x B x D) (22.48 ± 0.11%); Eq4 fixed is 23.33 ± 0.14%, +0.99 ± 0.06 pp from the Bayes baseline (22.34 ± 0.11%).
- `additive`: lowest mean misrouting among the evaluated families is Binned lookup (class x B x D) (29.67 ± 0.14%); Eq4 fixed is 30.76 ± 0.14%, +1.25 ± 0.09 pp from the Bayes baseline (29.51 ± 0.12%).
- `threshold`: lowest mean misrouting among the evaluated families is Binned lookup (class x B x D) (21.51 ± 0.13%); Eq4 fixed is 23.34 ± 0.12%, +1.95 ± 0.09 pp from the Bayes baseline (21.38 ± 0.12%).
- `interaction`: lowest mean misrouting among the evaluated families is Binned lookup (class x B x D) (31.05 ± 0.09%); Eq4 fixed is 31.59 ± 0.07%, +0.77 ± 0.05 pp from the Bayes baseline (30.81 ± 0.08%).
- `heavy_tail`: lowest mean misrouting among the evaluated families is Binned lookup (class x B x D) (24.47 ± 0.13%); Eq4 fixed is 25.13 ± 0.11%, +4.24 ± 0.13 pp from the Bayes baseline (20.89 ± 0.11%).
- `nonstationary`: lowest mean misrouting among the evaluated families is Eq4 re-fit on train (24.89 ± 0.33%); Eq4 fixed is 26.92 ± 0.15%, +4.05 ± 0.13 pp from the Bayes baseline (22.87 ± 0.10%).
- Logistic (class, B, D) vs Eq4 fixed (paired over seeds, 95% CI excludes 0): lower misrouting in `additive`, `nonstationary`; higher in `multiplicative`, `threshold`, `interaction`, `heavy_tail`; not distinguishable in none.
- Eq4 re-fit on train vs Eq4 fixed (paired over seeds, 95% CI excludes 0): lower misrouting in `threshold`, `nonstationary`; higher in none; not distinguishable in `multiplicative`, `additive`, `interaction`, `heavy_tail`.
- Binned lookup (class x B x D) vs Eq4 fixed (paired over seeds, 95% CI excludes 0): lower misrouting in `multiplicative`, `additive`, `threshold`, `interaction`, `heavy_tail`, `nonstationary`; higher in none; not distinguishable in none.
- Eq1 re-fit on train vs Eq4 fixed (paired over seeds, 95% CI excludes 0): lower misrouting in none; higher in `multiplicative`, `additive`, `threshold`, `interaction`, `heavy_tail`, `nonstationary`; not distinguishable in none.
- The largest Eq4-fixed gap to the Bayes baseline is in `heavy_tail` (+4.24 ± 0.13 pp).
- Lowest mean Brier score per world: `multiplicative` Binned lookup (class x B x D); `additive` Binned lookup (class x B x D); `threshold` Binned lookup (class x B x D); `interaction` Binned lookup (class x B x D); `heavy_tail` Binned lookup (class x B x D); `nonstationary` Eq4 re-fit on train.
