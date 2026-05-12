# PRD-05: H8 — Baseline Comparison Against Existing Recovery Systems

> An empirical comparison of CAIRN v2 recovery against LangGraph `SqliteSaver`, Temporal workflow recovery, and naive restart on a toy task — closing the reviewer-flagged gap that the whitepaper currently claims a 23.46% misrouting result against a calibrated simulation but provides no real-system comparison.

| Field | Value |
|---|---|
| **PRD ID** | PRD-05 |
| **Title** | H8 — Baseline Comparison Against Existing Recovery Systems |
| **Status** | Draft (scope) |
| **Priority** | P1 (strengthens arXiv credibility; not blocking initial submission) |
| **Author** | Maroua Boudoukha |
| **Created** | 2026-05-11 |
| **Estimated Complexity** | S (2-3 days; single toy task, four wrappers, deterministic harness) |
| **Blocks** | Whitepaper revision to v2.1 (new Section 10.4) |
| **Blocked by** | None — fully independent of PRD-04 v2 contract upgrade |
| **Parallel to** | arXiv submission of current whitepaper (this experiment is the v2.1 follow-up) |

---

## 1. Problem Statement

The external PhD-level review of the CAIRN whitepaper flagged one finding more often than any other: **"The lack of a baseline experiment against an existing system (LangGraph's SqliteSaver, Temporal recovery, etc.) is the gap an arXiv reviewer is most likely to flag. A small empirical comparison — even on a toy task — would strengthen this enormously."**

The current whitepaper validates CAIRN's recovery formula against a *calibrated simulation* (23.46% misrouting against the synthetic ground truth, 0.93pp from Bayes-optimal). This is rigorous as a calibration exercise but does not demonstrate that CAIRN delivers superior recovery to systems that already exist. A reviewer will ask: how does CAIRN compare to LangGraph's checkpointing today? To Temporal's workflow replay? To just restarting from scratch?

This PRD scopes a *minimal but defensible* empirical answer to that question.

---

## 2. Goals / Non-Goals

### Goals

- **G1**: Run a single deterministic toy-task experiment comparing four recovery systems on the same failure injections.
- **G2**: Produce a comparison table with three metrics (recovery success rate, work preserved, recovery wall-clock time) and one boolean (cross-framework portability).
- **G3**: Publish a 2-3 page report (`experiments/baseline-comparison/REPORT.md`) with the table, two figures, and one paragraph of analysis.
- **G4**: Integrate the result into the whitepaper as new **Section 10.4 "Empirical Comparison Against Existing Systems"** for a v2.1 revision.
- **G5**: Make the experiment fully reproducible (seed-controlled, `python3 -m experiments.baseline_comparison.run`).

### Non-Goals

- **NG1**: Production-scale evaluation. This is a toy comparison, not a benchmarking suite.
- **NG2**: Statistical significance testing across many task types. n = 32 runs (4 systems × 4 failure points × 2 failure modes) is sufficient for qualitative comparison; statistical power analysis is deferred to v3.
- **NG3**: Performance benchmarking beyond the recovery dimension (throughput, latency under load, etc.).
- **NG4**: Multi-framework agent execution. We compare *recovery mechanisms*, not agent backbones; each wrapper executes the same Python pipeline.
- **NG5**: On-chain execution. CAIRN's recovery decision is exercised via the v2 router logic in `simulation/scorer.py` (Python sim of the Solidity formula); no testnet calls. The comparison is *recovery quality*, not *gas cost*.

---

## 3. Experimental Design

### 3.1 Toy Task

A 5-step data pipeline matching CAIRN's "Fully portable" and "Portable with context" classes per Whitepaper §4.1.1 — the regime where CAIRN's recovery guarantees fully apply:

| Step | Operation | Output | Approx duration |
|---|---|---|---|
| 1 | `fetch_prices(symbols)` | dict of {symbol: price} (mock, deterministic) | 1s |
| 2 | `compute_stats(prices)` | dict of {mean, stddev, min, max} | 1s |
| 3 | `format_report(stats)` | JSON report blob | 0.5s |
| 4 | `sign_report(report)` | report + sha256 hash | 0.5s |
| 5 | `submit_report(signed)` | mock submission receipt | 1s |

Total task wall-clock at zero failures: ~4s. Each step produces a deterministic output given its input (no randomness, no network — all mocked). Each step's output is serialisable to JSON and matches CAIRN's checkpoint schema (`{task_id, subtask_index, output, context, schema_version}`).

### 3.2 Systems Under Test

| System | What's measured | Implementation |
|---|---|---|
| **CAIRN v2 sim** | On failure, route via `r = F^0.80 × B^0.35 × D^0.15`; if `r ≥ 0.40` resume from last checkpoint via a different worker; if `0.35 ≤ r < 0.40` resume with capped budget; else "dispute" (in the simulation, this counts as work-lost). Reads `simulation/scorer.py`. | Python; reuses CAIRN simulation infrastructure |
| **LangGraph SqliteSaver** | Wrap the 5-step pipeline as a LangGraph `StateGraph` with `SqliteSaver` checkpointing. On failure, recover by re-instantiating the graph and replaying from the last persisted state. | Python; `langgraph` + `langgraph-checkpoint-sqlite` |
| **Temporal workflow** | Each step is a Temporal activity. On failure, Temporal replays the workflow history and resumes from the last completed activity. Uses the `temporalio` test environment (no server required). | Python; `temporalio` |
| **Naive restart** | No checkpointing. On failure, restart the entire pipeline from step 1. | Python; trivial |

### 3.3 Failure Injection

Failures are injected at **4 progress points** (after step 1, 2, 3, 4) under **2 failure modes**:

| Failure mode | Mechanism | CAIRN classification |
|---|---|---|
| **Process crash (LIVENESS)** | Worker process killed mid-task via `os.kill` | LIVENESS |
| **Budget exhaustion (RESOURCE)** | Worker hits a synthetic budget cap and raises `BudgetExceededError` | RESOURCE |

LOGIC failures are *not* in scope: by construction, the toy task produces deterministic output, so semantic-error failures don't occur. (The whitepaper itself notes LOGIC failures route to dispute regardless; the comparison is meaningful only for the recoverable classes.)

Total runs: **4 systems × 4 failure points × 2 failure modes = 32 runs**. Plus 4 baseline runs (no failure, one per system) for sanity = **36 runs**.

### 3.4 Metrics

| Metric | Definition | Source of truth |
|---|---|---|
| **Recovery success rate** | Did the task ultimately produce the correct final output (step 5) within a 30-second wall-clock budget from initial submission? | Equality check against the no-failure baseline output |
| **Work preserved (%)** | Fraction of pre-failure completed steps not re-executed on recovery | Per-step timestamp logs |
| **Recovery wall-clock time** | Seconds from failure injection to final task completion | Wall-clock timer |
| **Cross-framework portability** | Boolean: can the recovery worker be a different framework than the original? | Architectural property — only CAIRN passes |

---

## 4. Implementation Plan

### Phase 1 — Task scaffold (0.5 day)

- `experiments/baseline-comparison/task.py` — the 5 step functions, deterministic given seed
- `experiments/baseline-comparison/schema.py` — checkpoint JSON schema (matches CAIRN §4.1)
- Validate: run the pipeline end-to-end, assert deterministic output

### Phase 2 — Three system wrappers + naive (0.5 day)

- `cairn_wrapper.py` — invokes the 5 step functions, writes JSON checkpoints to a file directory; on failure, looks up checkpoints, queries `simulation.scorer.compute_score`, and routes to a "fallback worker" function (a second Python process simulated via subprocess or just a function call)
- `langgraph_wrapper.py` — same pipeline as a LangGraph `StateGraph`; uses `langgraph.checkpoint.sqlite.SqliteSaver`
- `temporal_wrapper.py` — same pipeline as a Temporal workflow with 5 activities; uses `temporalio.testing.WorkflowEnvironment` (no server)
- `naive_wrapper.py` — restart from scratch on any failure

### Phase 3 — Failure injection harness (0.5 day)

- `harness.py` — runs each system × failure point × failure mode combination
- Captures: per-step timestamps, final output, total wall-clock
- Output: `results.json` (32 records + 4 baselines)

### Phase 4 — Analysis + figures (0.5 day)

- `analyze.py` — aggregates `results.json` into the comparison table
- Figure 1: bar chart of work-preserved (%) by system × failure point
- Figure 2: comparison matrix (system × failure-mode → success/fail + recovery time)

### Phase 5 — Whitepaper integration (0.5 day)

- `experiments/baseline-comparison/REPORT.md` — 2-3 page write-up
- New whitepaper section 10.4 — single page max, table, one figure inline, paragraph of analysis
- Reference [20] in §11 pointing to the experiment artifact
- One sentence in §10.1 cross-referencing 10.4 as the cheapest external validation

### Phase 6 — Test, document, commit (0.5 day, buffer)

- Reproducibility check: clean install, run, confirm identical outputs
- Update PRD-05 STATUS.md with measured numbers
- Open PR

**Total: 3 days nominal, 2-day stretch goal if Phase 6 buffer collapses.**

---

## 5. Acceptance Criteria

| AC | Criterion | How verified |
|---|---|---|
| AC-01 | All 36 runs complete deterministically given seed=42 | Two consecutive `run.py` invocations produce identical `results.json` |
| AC-02 | Comparison table populates for all 4 systems × 4 failure points × 2 failure modes | Inspection of `REPORT.md` |
| AC-03 | CAIRN average work-preserved ≥ LangGraph average work-preserved | Sanity check — CAIRN should match in-framework checkpointing for within-framework cases |
| AC-04 | CAIRN is the *only* system to score true for cross-framework portability | Architectural property |
| AC-05 | Naive restart scores 0% work-preserved on every non-baseline run | Trivially true; serves as the floor |
| AC-06 | `python3 -m experiments.baseline_comparison.run` is the single entry point and runs in ≤ 5 minutes wall-clock | Profiling |
| AC-07 | Whitepaper section 10.4 added with the table, one figure, and a paragraph of analysis citing the artifact | Diff review |
| AC-08 | Two figures generated to `experiments/baseline-comparison/figures/` (PNG + SVG) | File existence + visual sanity |

---

## 6. Output Integration

### Whitepaper changes (new commit on top of v2.1)

- **New Section 10.4** "Empirical Comparison Against Existing Systems" (≤1 page): comparison table, 1 inline figure (work-preserved bar chart), one-paragraph honest analysis (incl. the cases where CAIRN ties or slightly underperforms — see §8 Risks below)
- **Section 10.1** — one sentence at the top of "Open Research Questions" cross-referencing 10.4
- **Section 1.4 Scope and Limitations** — refine the "Empirical scope" bullet to note that 10.4 provides the first real-system comparison; the simulation-vs-production caveat remains for the broader claim
- **Reference [20]** added: experiment artifact and reproduction command
- **Abstract** — *no change* unless the result is unexpectedly strong; a 2-3 word addition like "with empirical baseline comparison" could be added but is not required

### Repository changes

```
experiments/
└── baseline-comparison/
    ├── __init__.py
    ├── task.py
    ├── schema.py
    ├── cairn_wrapper.py
    ├── langgraph_wrapper.py
    ├── temporal_wrapper.py
    ├── naive_wrapper.py
    ├── harness.py
    ├── analyze.py
    ├── run.py
    ├── results.json
    ├── REPORT.md
    └── figures/
        ├── fig17_work_preserved.png
        └── fig18_comparison_matrix.png
```

Figures numbered 17 and 18 to continue the simulation/figures/ series (fig1–fig16) rather than restart.

---

## 7. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| LangGraph SqliteSaver doesn't isolate cleanly — too much LangGraph infrastructure overhead for a fair toy comparison | Medium | Strip the LangGraph wrapper to just the checkpoint+resume flow; don't use LangGraph's full agent loop. The comparison is recovery mechanism, not orchestration. |
| Temporal requires a running server; setup is non-trivial | Medium | Use `temporalio.testing.WorkflowEnvironment` (in-memory test harness); no server needed. Documented in the Temporal Python SDK. |
| Results show CAIRN underperforming LangGraph on some axis | Low | Report honestly. The paper's claim is not "CAIRN is fastest in-framework" — it is "CAIRN matches in-framework checkpointing AND adds cross-framework portability AND adds economic settlement." An honest comparison is the right comparison. The reviewer will trust the paper *more* if §10.4 is honest about where CAIRN ties rather than wins. |
| 32 runs is not statistically significant | Low | Explicitly note this in §10.4: "qualitative comparison on a single toy task; statistical power analysis across task families deferred to v3." The reviewer asked for "even a toy task" — meeting that bar honestly is the goal. |
| Subprocess-based "fallback worker" in the CAIRN wrapper is unrealistic vs. a real cross-framework handoff | Low | Document this as a simplification. The cross-framework portability claim rests on the checkpoint schema being framework-agnostic (which is a property of the JSON schema, not the simulation harness); the experiment demonstrates the property holds within Python, not across runtimes. A genuine cross-runtime test (Python → Node, Python → Rust) is a v3 follow-up. |
| Adding `langgraph`, `langgraph-checkpoint-sqlite`, and `temporalio` introduces dependency drift | Low | All three are Python-only, well-maintained, and used only in `experiments/`. Pin versions in a `experiments/baseline-comparison/requirements.txt`. |

---

## 8. Dependencies

### New Python packages (experiments only)

```
langgraph>=0.2.0
langgraph-checkpoint-sqlite>=2.0.0
temporalio>=1.6.0
matplotlib>=3.7.0  # may already be installed for simulation/figures/
```

Pin in `experiments/baseline-comparison/requirements.txt`. Not added to the main project requirements; the experiment is opt-in.

### No new on-chain dependencies

CAIRN's recovery-decision logic is exercised via `simulation/scorer.py` (the Python mirror of the Solidity formula). No contract calls, no Foundry test runs, no gas measurements — those are PRD-04's concern.

### Cross-references

- **PRD-04** (v2 contract upgrade): independent. PRD-05 only needs the Python simulation of the v2 formula, which already exists.
- **PR #21** (whitepaper hardening): independent. PRD-05 lands as a v2.1 follow-up after #21 merges.

---

## 9. Next Action

When PRD-05 is approved for implementation:

1. Create `claude/h8-baseline-comparison-impl` branch from `main`.
2. Phase 1: scaffold `experiments/baseline-comparison/` with the 5-step task and schema.
3. Phase 2–6 per the plan above.
4. Open PR (target: `main`) for review.
5. After merge, the whitepaper §10.4 commit (a single subsequent commit) becomes the v2.1 revision and triggers an arXiv revision upload.

---

## 10. References

- Whitepaper §4.1.1 (checkpoint portability classes) — defines the regime in which CAIRN's recovery guarantee fully applies; the toy task is chosen to live in that regime
- Whitepaper §6.4 (recovery score formula) — the multiplicative formula the CAIRN wrapper implements
- Whitepaper §10.1 (open research questions) — empirical validation against existing systems is listed there; PRD-05 is the cheapest first answer
- External reviewer note: "The lack of a baseline experiment against an existing system (LangGraph's SqliteSaver, Temporal recovery, etc.) is the gap an arXiv reviewer is most likely to flag." — direct motivation
- LangGraph documentation: https://langchain-ai.github.io/langgraph/concepts/persistence/
- Temporal Python SDK testing: https://docs.temporal.io/develop/python/testing-suite
