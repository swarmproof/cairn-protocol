# PRD-03: Recovery Score Empirical Calibration

> Monte Carlo simulation to validate and optimize CAIRN's recovery score formula

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-03 |
| **Title** | Recovery Score Empirical Calibration via Simulation |
| **Status** | Draft |
| **Priority** | P1 — Required before mainnet; blocks whitepaper finalization |
| **Author** | CAIRN Team |
| **Created** | April 2026 |
| **Timeline** | ~2 weeks |
| **Complexity** | M (standalone Python simulation, no contract changes) |
| **Location** | `simulation/` (new directory) |
| **Depends On** | Whitepaper V2 (Section 6.4 formula definition) |
| **Blocks** | Mainnet deployment (recovery parameters must be validated), whitepaper Section 10.1 (removes "not empirically validated" caveat) |

---

## 0. Context

### The Problem

CAIRN's recovery score formula (Whitepaper V2, Equation 1) determines whether a failed task is routed to RECOVERING or DISPUTED:

```
r = 0.5 × F + 0.3 × B + 0.2 × D
```

Where:
- *F* = failure class weight (LIVENESS=0.9, RESOURCE=0.5, LOGIC=0.1)
- *B* = budget remaining percentage
- *D* = deadline remaining percentage

**Three-tier routing:**
- *r* ≥ 0.6 → RECOVERING (full scope)
- 0.3 ≤ *r* < 0.6 → RECOVERING (reduced scope)
- *r* < 0.3 → DISPUTED

The weights (0.5/0.3/0.2), class weights (0.9/0.5/0.1), and thresholds (0.6/0.3) are currently based on domain reasoning (Whitepaper V2, Section 6.4). They have not been validated empirically.

### What This PRD Delivers

A Monte Carlo simulation that:
1. Generates 100,000+ synthetic task-failure events across realistic distributions
2. Simulates recovery outcomes for each failure under varying parameters
3. Identifies optimal weights and thresholds that minimize misrouting
4. Produces publication-ready charts and statistical analysis for the whitepaper
5. Validates that the current formula is either (a) already optimal or (b) produces specific improvements

### Why Monte Carlo Simulation

Existing agent simulation frameworks (AgentBench, GAIA, SWE-bench) focus on measuring agent *accuracy*, not failure *recoverability*. No existing framework models the specific variables CAIRN needs: failure class × budget remaining × deadline remaining → recovery success probability.

A purpose-built Monte Carlo simulator (~600-800 lines Python) is the correct approach: the formula evaluates in nanoseconds (enabling exhaustive grid search over 3.5M parameter-trial combinations in ~2 minutes), the parameter space is small (~6 free dimensions), and we need frequentist counting statistics (misrouting rates, F1 scores) — not Bayesian posteriors. More sophisticated methods (MCMC, Bayesian Optimization, evolutionary algorithms) add complexity without adding value when brute-force evaluation is this cheap.

MCMC becomes the right tool *after* production deployment, when real failure/recovery data enables Bayesian posterior inference over optimal weights. The staged approach: Monte Carlo now (synthetic data) → Bayesian update at testnet (small real data) → full MCMC at mainnet (large real data).

> **Detailed methodology rationale:** See `local-docs/SIMULATION_METHODOLOGY.md` for the full comparison of Monte Carlo vs MCMC vs Bayesian Optimization vs evolutionary methods, the ground truth model design, and the staged calibration roadmap.

---

## 1. Purpose & Goals

### 1.1 Research Questions

| # | Question | Method | Simulation Run |
|---|----------|--------|---------------|
| RQ1 | Are the current formula weights (0.5/0.3/0.2) optimal for minimizing misrouting? | Grid search over weight space | Run 1 (Eq. 1 linear) |
| RQ2 | Are the current class weights (0.9/0.5/0.1) optimal? | Grid search over class weight space | Run 1 |
| RQ3 | Are the thresholds (0.6/0.3) optimal for three-tier routing? | Threshold sweep with F1 measurement | Run 1 |
| RQ4 | How sensitive is the routing to weight perturbations? | Sensitivity analysis (±20% per weight) | Run 1 |
| RQ5 | Does the formula generalize across different task-type distributions? | Cross-task-type validation | Run 1 |
| RQ6 | Can a piecewise-linear formula with interaction terms break below 20% misrouting? | Equation 2: piecewise cliffs + B×D interaction | Run 2 (Eq. 2 piecewise) |
| RQ7 | What are the optimal cliff thresholds (B_CRIT, D_CRIT) and penalty slopes? | Grid search over piecewise parameters | Run 2 |
| RQ8 | How much does the interaction term (B×D) contribute independently? | Ablation: Eq. 2 with vs without interaction term | Run 2 |

### 1.2 Success Metrics

| Metric | Target | Method |
|--------|--------|--------|
| Misrouting rate (overall) | < 10% | Count tasks sent to wrong tier vs. ground-truth outcome |
| False positive rate (recover tasks that fail) | < 15% | Count RECOVERING-routed tasks where recovery actually fails |
| False negative rate (dispute tasks that could recover) | < 10% | Count DISPUTED-routed tasks where recovery would have succeeded |
| Sensitivity stability | < 5% change in misrouting for ±10% weight perturbation | Perturbation analysis |
| Statistical confidence | p < 0.01 for all key findings | Chi-squared test on routing outcomes |

### 1.3 Deliverables

| Deliverable | Format | Purpose |
|-------------|--------|---------|
| Simulation code | `simulation/` Python package | Reproducible calibration tool |
| Run 1 results (Eq. 1 linear) | `simulation/RESULTS.md` | Linear formula optimization: RQ1-RQ5 |
| Run 2 results (Eq. 2 piecewise) | `simulation/RESULTS_EQ2.md` | Piecewise + interaction formula: RQ6-RQ8 |
| Publication figures (Run 1) | `simulation/figures/fig1-fig6` PNG/SVG | Charts for linear formula analysis |
| Publication figures (Run 2) | `simulation/figures/fig7-fig12` PNG/SVG | Charts for piecewise formula analysis |
| Whitepaper update | `WHITEPAPER_V2.md` amendment | Replace "domain reasoning" caveat with empirical evidence |

### 1.4 Simulation Run Index

| Run | Formula | Experiments | Results File | Status |
|-----|---------|-------------|-------------|--------|
| **Run 1** | Eq. 1: `r = w_f×F + w_b×B + w_d×D` | Exp 1-5 (RQ1-RQ5) | `simulation/RESULTS.md` | COMPLETE |
| **Run 2** | Eq. 2: `r = w_f×F + w_b×B_adj + w_d×D_adj + w_int×B_adj×D_adj` | Exp 6-8 (RQ6-RQ8) | `simulation/RESULTS_EQ2.md` | COMPLETE |
| **Run 3** | Eq. 3: `r = w_f×F + w_b×B + w_d×D + w_c×C + w_s×S` (adds complexity + skill) | Exp 9-12 (RQ9-RQ12) | `simulation/RESULTS_EQ3.md` | COMPLETE |
| **Run 4** | Eq. 4: `r = F^a × B^b × D^c` (multiplicative) + Bayes baseline | Exp 13-16 (RQ13-RQ16) | `simulation/RESULTS_EQ4.md` | COMPLETE |

---

## 2. Simulation Design

### 2.1 Architecture

```
simulation/
├── __init__.py
├── config.py          # All parameters, distributions, ground truth model
├── generator.py       # Task + failure event generation
├── recovery.py        # Recovery outcome simulation (ground truth)
├── scorer.py          # CAIRN recovery score formula (candidate)
├── optimizer.py       # Grid search + scipy optimization
├── sensitivity.py     # Weight perturbation analysis
├── visualizer.py      # Publication-ready charts
├── run.py             # Main entry point
├── tests/
│   ├── test_generator.py
│   ├── test_recovery.py
│   ├── test_scorer.py
│   └── test_optimizer.py
├── figures/            # Generated charts
└── RESULTS.md          # Findings
```

### 2.2 Ground Truth Model

The simulation requires a **ground truth model** that determines whether a recovery attempt *actually succeeds*, independent of the score formula. This model represents reality — the formula is then evaluated against it.

**Ground truth recovery success probability:**

```python
def ground_truth_recovery_probability(
    failure_class: str,      # LIVENESS | RESOURCE | LOGIC
    budget_remaining: float,  # 0.0 to 1.0
    deadline_remaining: float, # 0.0 to 1.0
    task_complexity: int,     # remaining subtasks (1-50)
    fallback_skill: float     # fallback agent capability (0.0 to 1.0)
) -> float:
```

The ground truth model encodes domain knowledge about when recovery actually works:

| Factor | Effect on Recovery Success | Rationale |
|--------|---------------------------|-----------|
| **Failure class** | LIVENESS: base 90% success; RESOURCE: base 50%; LOGIC: base 10% | A crashed agent is almost always resumable; a reasoning failure is not |
| **Budget remaining** | Multiplier: recovery needs budget for the fallback agent | Below 20% budget, even LIVENESS recovery often fails (insufficient gas) |
| **Deadline remaining** | Multiplier: recovery needs time for the fallback agent | Below 10% deadline, time pressure causes cascading failures |
| **Task complexity** | Negative correlation: more remaining subtasks = harder recovery | 1 remaining step is trivial; 30 remaining steps is risky |
| **Fallback skill** | Multiplier: higher-skill fallback agents succeed more often | Reputation-gated pool means minimum 0.5 skill, average ~0.7 |

**Ground truth formula:**

```python
# Base probability from failure class
base = {"LIVENESS": 0.92, "RESOURCE": 0.48, "LOGIC": 0.08}[failure_class]

# Budget factor: sigmoid centered at 0.15 (below 15% budget, recovery drops sharply)
budget_factor = 1 / (1 + math.exp(-15 * (budget_remaining - 0.15)))

# Deadline factor: sigmoid centered at 0.10 (below 10% deadline, recovery drops)
deadline_factor = 1 / (1 + math.exp(-20 * (deadline_remaining - 0.10)))

# Complexity penalty: more remaining work = lower success
complexity_factor = 1 / (1 + 0.02 * remaining_subtasks)

# Fallback skill multiplier
skill_factor = 0.4 + 0.6 * fallback_skill  # range: 0.4 to 1.0

# Final probability (clamped to [0, 1])
p_success = base * budget_factor * deadline_factor * complexity_factor * skill_factor
```

**Why these specific values:** The base rates (0.92/0.48/0.08) are derived from the MAST taxonomy finding that system design failures (mapped to LIVENESS) are the most recoverable, while logic/reasoning failures are rarely fixable by a different agent [1]. The sigmoid budget/deadline factors model the sharp drop-off below critical resource thresholds — consistent with operational experience where gas exhaustion or time pressure causes cascading failures. The complexity factor follows the empirical 85%-per-step accuracy (0.85^n success for n remaining steps, approximated by the 1/(1+0.02n) curve). The fallback skill range (0.4-1.0) reflects the admission gate (min reputation 50/100) filtering out the worst agents.

### 2.3 Task-Failure Event Generation

Each trial generates a task with sampled parameters:

```python
@dataclass
class TaskFailureEvent:
    task_type: str          # sampled from ["defi.price_fetch", "defi.trade_execute",
                            #   "data.report_generate", "governance.vote_delegate",
                            #   "compute.model_inference"]
    total_subtasks: int     # sampled from Poisson(λ=8) + 2, range [2, 50]
    failure_subtask: int    # sampled from Uniform(1, total_subtasks)
    failure_class: str      # sampled from weighted distribution (below)
    budget_remaining: float # derived from failure_subtask / total_subtasks + noise
    deadline_remaining: float # derived from failure timing + noise
    escrow: float           # sampled from LogNormal(μ=-4.6, σ=1.5), range [0.001, 10] ETH
    fallback_skill: float   # sampled from Beta(α=5, β=2), range [0.5, 1.0] (reputation-gated)
```

**Failure class distribution** (based on MAST taxonomy [1] and agent reliability research [2, 3]):

| Failure Class | Probability | Source |
|---------------|-------------|--------|
| LIVENESS | 45% | Most common in production: crashes, network issues, heartbeat timeouts |
| RESOURCE | 35% | Rate limits, budget exhaustion, context overflow |
| LOGIC | 20% | Reasoning errors, hallucinations, spec mismatches |

These proportions are derived from the MAST finding that "system design issues" (mapped to LIVENESS) are the most frequent category, followed by "task verification" failures (RESOURCE), and "inter-agent misalignment" (LOGIC) [1].

**Budget remaining distribution:** Correlated with failure point. Early failures (subtask 1-2) have ~80-95% budget remaining. Late failures (subtask n-1) have ~5-20%. Gaussian noise (σ=0.05) models cost variance.

**Deadline remaining distribution:** Correlated with failure timing. Tasks failing in the first quarter have ~75-90% deadline remaining. Tasks failing near deadline have ~5-15%. Gaussian noise (σ=0.03).

### 2.4 Experiment Design

**Experiment 1: Weight Optimization (RQ1)**

Grid search over the weight space:
```
w_f ∈ {0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7}  # failure class weight
w_b ∈ {0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4}               # budget weight
w_d = 1.0 - w_f - w_b                                         # deadline weight (constrained)

Constraint: w_d ≥ 0.05 (deadline must have non-trivial influence)
```

For each weight vector, run 10,000 trials. Measure:
- Overall misrouting rate
- Per-class misrouting rate (LIVENESS, RESOURCE, LOGIC separately)
- F1 score for each routing tier

Total trials: ~350 weight combinations × 10,000 = 3.5M (runs in ~2 minutes on modern hardware with numpy vectorization).

**Experiment 2: Class Weight Optimization (RQ2)**

Grid search over class weights:
```
F_LIVENESS ∈ {0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0}
F_RESOURCE ∈ {0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6}
F_LOGIC    ∈ {0.0, 0.05, 0.1, 0.15, 0.2}
```

For each combination, run 10,000 trials. Measure same metrics as Experiment 1.

Total trials: ~245 class weight combinations × 10,000 = 2.45M.

**Experiment 3: Threshold Optimization (RQ3)**

Sweep threshold values:
```
upper_threshold ∈ {0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8}
lower_threshold ∈ {0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4}

Constraint: lower_threshold < upper_threshold
```

For each threshold pair (using current best weights from Experiments 1-2), run 10,000 trials. Measure:
- Per-tier precision and recall
- Overall misrouting rate
- Economic loss from misrouting (escrow wasted on failed recovery + escrow delayed by unnecessary disputes)

**Experiment 4: Sensitivity Analysis (RQ4)**

Starting from the optimal weight vector found in Experiments 1-2:
- Perturb each weight individually by ±5%, ±10%, ±15%, ±20%
- Re-normalize remaining weights to sum to 1.0
- Measure misrouting rate change

This produces a sensitivity surface showing how robust the formula is to parameter drift.

**Experiment 5: Cross-Task-Type Validation (RQ5)**

Train optimal weights on 4 task types, evaluate on the held-out 5th. Repeat for all 5 folds (leave-one-out cross-validation). This tests whether the formula generalizes or overfits to specific task-type distributions.

### 2.5 Metrics

**Primary metric: Misrouting Rate**

A task is **misrouted** when the recovery score routes it to a tier that produces a worse outcome than the correct tier would have:

| Actual Outcome | Routed To | Misrouting? | Cost |
|----------------|-----------|-------------|------|
| Recovery succeeds | RECOVERING (full) | No | Optimal |
| Recovery succeeds | RECOVERING (reduced) | Partial | Reduced scope may still succeed |
| Recovery succeeds | DISPUTED | **Yes (false negative)** | Unnecessary dispute delay + arbiter fee |
| Recovery fails | RECOVERING (full) | **Yes (false positive)** | Wasted fallback budget + time |
| Recovery fails | RECOVERING (reduced) | Partial | Capped loss from budget constraint |
| Recovery fails | DISPUTED | No | Correct routing |

**F1 Score per tier:**
```
Precision_tier = correct_routes_to_tier / total_routes_to_tier
Recall_tier = correct_routes_to_tier / total_tasks_that_should_go_to_tier
F1_tier = 2 × (Precision × Recall) / (Precision + Recall)
```

**Economic Loss:**
```
Loss_false_positive = sum(escrow_wasted on failed recovery attempts)
Loss_false_negative = sum(arbiter_fee + delay_cost for unnecessarily disputed tasks)
Total_economic_loss = Loss_false_positive + Loss_false_negative
```

---

## 3. Implementation

### 3.1 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Core simulation | Python 3.10+ | Consistent with CAIRN SDK |
| Random sampling | `numpy` | Vectorized generation for 100k+ events |
| Optimization | `scipy.optimize` | Grid search + gradient-free optimization (Nelder-Mead) |
| Data analysis | `pandas` | Aggregation, pivot tables, statistical tests |
| Visualization | `matplotlib` + `seaborn` | Publication-quality figures |
| Statistical tests | `scipy.stats` | Chi-squared, KS test, confidence intervals |
| Parallelism | `multiprocessing.Pool` | Scale across CPU cores |
| Reproducibility | Fixed random seed (42) | All results reproducible |

### 3.2 Core Implementation

**Scorer (the CAIRN formula being tested):**

```python
def recovery_score(
    failure_class: str,
    budget_remaining: float,
    deadline_remaining: float,
    weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
    class_weights: dict[str, float] = {"LIVENESS": 0.9, "RESOURCE": 0.5, "LOGIC": 0.1}
) -> float:
    w_f, w_b, w_d = weights
    F = class_weights[failure_class]
    return w_f * F + w_b * budget_remaining + w_d * deadline_remaining
```

**Router (maps score to tier):**

```python
def route(score: float, upper: float = 0.6, lower: float = 0.3) -> str:
    if score >= upper:
        return "RECOVERING_FULL"
    elif score >= lower:
        return "RECOVERING_REDUCED"
    else:
        return "DISPUTED"
```

**Ground truth evaluator:**

```python
def simulate_recovery(event: TaskFailureEvent, rng: np.random.Generator) -> bool:
    p = ground_truth_recovery_probability(
        event.failure_class,
        event.budget_remaining,
        event.deadline_remaining,
        event.total_subtasks - event.failure_subtask,  # remaining subtasks
        event.fallback_skill
    )
    return rng.random() < p
```

**Misrouting evaluator:**

```python
def is_misrouted(route: str, recovery_succeeded: bool) -> bool:
    if route in ("RECOVERING_FULL", "RECOVERING_REDUCED") and not recovery_succeeded:
        return True   # false positive: attempted recovery that failed
    if route == "DISPUTED" and recovery_succeeded:
        return True   # false negative: disputed a recoverable task
    return False
```

### 3.3 Output Format

**Console output (per experiment):**
```
Experiment 1: Weight Optimization
  Trials: 3,500,000 (350 combos × 10,000 each)
  Best weights: w_f=0.50, w_b=0.30, w_d=0.20
  Misrouting rate: 8.3% (target: <10%)
  False positive rate: 11.2% (target: <15%)
  False negative rate: 5.1% (target: <10%)
  Improvement over baseline: +0.0% (current weights already optimal)
  p-value: <0.001
```

**RESULTS.md structure:**
```markdown
# Recovery Score Calibration Results

## Executive Summary
[1-paragraph finding: current weights are/aren't optimal, recommended changes]

## Experiment 1: Weight Optimization
[Heatmap of misrouting rate across weight space]
[Table of top 10 weight vectors]
[Statistical significance test]

## Experiment 2: Class Weight Optimization
[Same structure]

## Experiment 3: Threshold Optimization
[Precision-recall curve per tier]
[Optimal threshold pair with confidence interval]

## Experiment 4: Sensitivity Analysis
[Tornado chart showing weight sensitivity]
[Stability assessment]

## Experiment 5: Cross-Task-Type Validation
[Leave-one-out results table]
[Generalization assessment]

## Recommended Parameters
[Final recommended weights, class weights, thresholds with evidence]

## Whitepaper Amendment
[Exact text to add/change in WHITEPAPER_V2.md Section 6.4]
```

### 3.4 Publication Figures

| Figure | Type | Shows | Whitepaper Location |
|--------|------|-------|-------------------|
| Fig 1 | Heatmap | Misrouting rate across (w_f, w_b) space | Section 6.4 |
| Fig 2 | 3D surface | Recovery success probability vs (budget, deadline) per class | Section 6.4 |
| Fig 3 | Precision-recall curve | Per-tier routing accuracy across threshold sweep | Section 6.4 |
| Fig 4 | Tornado chart | Weight sensitivity (±20% perturbation impact) | Section 6.4 |
| Fig 5 | Confusion matrix | Routing outcomes (3×2: tier × success/fail) | Section 7.5 |
| Fig 6 | Box plot | Score distributions by failure class | Section 3.1 |

---

## 4. Acceptance Criteria

### 4.1 Simulation Correctness

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC-01 | Ground truth model produces recovery rates consistent with literature (LIVENESS ~90%, RESOURCE ~50%, LOGIC ~10% at full budget/deadline) | Unit test against base rates |
| AC-02 | Generated events have correct distributions (failure class: 45/35/20, budget/deadline correlated with failure point) | Histogram + KS test against expected distributions |
| AC-03 | Score formula matches Whitepaper V2 Equation 1 exactly | Unit test: `recovery_score("LIVENESS", 0.85, 0.88) == 0.881` |
| AC-04 | Router matches three-tier logic exactly | Unit test: score 0.61→FULL, 0.35→REDUCED, 0.29→DISPUTED |
| AC-05 | Results reproducible with fixed seed (42) | Run twice, compare outputs |

### 4.2 Calibration Quality

| ID | Criterion | Target |
|----|-----------|--------|
| AC-06 | Overall misrouting rate with optimal parameters | < 10% |
| AC-07 | False positive rate (failed recoveries) | < 15% |
| AC-08 | False negative rate (missed recoveries) | < 10% |
| AC-09 | Weight sensitivity: misrouting change for ±10% perturbation | < 5 percentage points |
| AC-10 | Cross-task-type generalization: misrouting variance across folds | Standard deviation < 3% |
| AC-11 | Statistical significance for all key comparisons | p < 0.01 |

### 4.3 Deliverable Quality

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC-12 | All 6 publication figures generated as PNG and SVG | File existence check |
| AC-13 | RESULTS.md contains all 5 experiment findings | Manual review |
| AC-14 | Whitepaper amendment text provided (exact text for Section 6.4) | Included in RESULTS.md |
| AC-15 | All tests pass (`pytest simulation/tests/`) | CI green |
| AC-16 | Simulation runs in < 5 minutes on a single machine (M1 Mac or equivalent) | Timing test |

---

## 5. Implementation Plan

### Phase 1: Core Simulation (Days 1-3)

| Task | Estimate | Output |
|------|----------|--------|
| Project setup (`simulation/` package, pyproject.toml, dependencies) | 2h | Package structure |
| Implement `config.py` (all parameters, distributions) | 2h | Config dataclass |
| Implement `generator.py` (task-failure event sampling) | 4h | TaskFailureEvent generator |
| Implement `recovery.py` (ground truth model) | 4h | Ground truth function |
| Implement `scorer.py` (CAIRN formula) | 1h | Score calculator |
| Unit tests for generator, recovery, scorer | 4h | Test suite |

### Phase 2: Optimization Engine (Days 4-6)

| Task | Estimate | Output |
|------|----------|--------|
| Implement `optimizer.py` (grid search + scipy) | 6h | Weight optimizer |
| Implement Experiment 1 (weight optimization) | 3h | Optimal weights |
| Implement Experiment 2 (class weight optimization) | 2h | Optimal class weights |
| Implement Experiment 3 (threshold optimization) | 3h | Optimal thresholds |
| Unit tests for optimizer | 3h | Test suite |

### Phase 3: Analysis & Visualization (Days 7-9)

| Task | Estimate | Output |
|------|----------|--------|
| Implement `sensitivity.py` (Experiment 4) | 3h | Sensitivity analysis |
| Implement cross-validation (Experiment 5) | 3h | Generalization results |
| Implement `visualizer.py` (all 6 figures) | 6h | Publication figures |
| Statistical significance tests | 3h | p-values for all findings |

### Phase 4: Documentation & Integration (Days 10-12)

| Task | Estimate | Output |
|------|----------|--------|
| Write RESULTS.md with all findings | 4h | Results report |
| Draft whitepaper amendment text | 2h | Section 6.4 update |
| Run full simulation suite, verify reproducibility | 2h | Final validation |
| Code review and cleanup | 3h | Clean codebase |
| Update WHITEPAPER_V2.md with empirical evidence | 2h | Whitepaper amendment |

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ground truth model is wrong (doesn't reflect real failure dynamics) | Medium | High | Base rates from literature [1][2][3]; validate against testnet data when available |
| Current weights are already optimal (no improvement possible) | Medium | Low | This is a valid finding — confirms the domain reasoning was correct |
| Optimal weights differ significantly from current (requires contract change) | Low | Medium | Weights are governance-adjustable; no redeploy needed |
| Simulation too slow for 100k+ trials | Low | Low | Numpy vectorization; multiprocessing; expected <5 min |
| Overfitting to synthetic distributions | Medium | Medium | Cross-validation (Experiment 5) detects this; use multiple distribution shapes |

---

## 7. Ground Truth Calibration Sources

The ground truth model parameters are derived from these sources:

| Parameter | Value | Source |
|-----------|-------|--------|
| LIVENESS base recovery rate | 0.92 | MAST taxonomy: system design failures are most recoverable [1]; Kubernetes liveness probe recovery rates |
| RESOURCE base recovery rate | 0.48 | MAST: task verification failures partially recoverable [1]; API rate limit retry success rates (~50%) |
| LOGIC base recovery rate | 0.08 | MAST: inter-agent misalignment rarely self-corrects [1]; "Exploring Autonomous Agents" [3]: reasoning failures persist across retries |
| Failure class distribution (45/35/20) | Production estimates | MAST category frequencies [1]; weighted toward LIVENESS based on operational reports |
| Budget critical threshold | 15% remaining | Operational: below ~15% budget, gas costs for recovery transactions consume remaining escrow |
| Deadline critical threshold | 10% remaining | Operational: below ~10% time, fallback agent startup + execution exceeds remaining window |
| Per-step success rate | ~85% | "Exploring Autonomous Agents" [3]: 50% completion at 10 steps implies ~93% per step; conservative estimate 85% |
| Fallback skill distribution | Beta(5, 2) mean=0.71 | Admission gate (reputation ≥ 50/100) truncates distribution; agents above threshold average ~71% |

---

## 8. Expected Outcomes

### Scenario A: Current Weights Are Optimal

If the simulation confirms the current weights (0.5/0.3/0.2) are within 1% of optimal, the whitepaper amendment reads:

> "Monte Carlo simulation across 100,000 synthetic task-failure events (Section 10.1) validates the recovery score weights. Grid search over 350 weight combinations finds that the current weights (w_f=0.5, w_b=0.3, w_d=0.2) produce a misrouting rate of X.X%, within Y.Y% of the global optimum. Sensitivity analysis confirms stability: ±10% weight perturbation changes misrouting by less than Z percentage points. The three-tier thresholds (0.6/0.3) achieve F1 scores of A.AA/B.BB/C.CC for the full/reduced/disputed tiers respectively."

### Scenario B: Better Weights Found

If the simulation finds significantly better weights (>2% misrouting improvement), the whitepaper amendment includes the new weights and the governance proposal to update them:

> "Monte Carlo simulation identifies improved recovery score weights (w_f=X.X, w_b=Y.Y, w_d=Z.Z) that reduce misrouting from A.A% to B.B% — a C.C percentage point improvement (p < 0.01). The current weights are used at launch; governance proposal GP-XXX will update to the calibrated weights after testnet validation."

### Scenario C: Formula Structure Needs Revision

If the simulation shows that no linear combination of (F, B, D) achieves < 10% misrouting, the finding suggests the formula may need non-linear terms (e.g., interaction effects between budget and deadline) or additional input variables. This would be documented as a research finding for a future protocol version.

---

## 9. References

[1] M. Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", NeurIPS 2025, arXiv:2503.13657

[2] S. Rabanser et al., "Towards a Science of AI Agent Reliability", arXiv:2602.16666, Feb 2026

[3] "Exploring Autonomous Agents: A Closer Look at Why They Fail", ASE 2025, arXiv:2508.13143

[4] CAIRN Protocol Whitepaper V2, Section 6.4 (Equation 1), April 2026
