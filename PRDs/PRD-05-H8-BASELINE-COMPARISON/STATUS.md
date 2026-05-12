# PRD-05 Status: H8 Baseline Comparison

| Field | Value |
|---|---|
| **Status** | SCOPED — implementation not started |
| **Last Updated** | 2026-05-11 |
| **Blocked By** | None |
| **Blocks** | Whitepaper v2.1 (new Section 10.4) |
| **Parallel to** | arXiv submission of current v2 paper |

---

## Phase Progress

| Phase | Duration | Status | Notes |
|---|---|---|---|
| 0 — Scoping | 0.5 day | **DONE** | This PRD |
| 1 — Task scaffold | 0.5 day | TODO | 5-step pipeline + checkpoint schema |
| 2 — System wrappers | 0.5 day | TODO | CAIRN sim, LangGraph SqliteSaver, Temporal test env, naive |
| 3 — Failure injection harness | 0.5 day | TODO | 36 runs, deterministic |
| 4 — Analysis + figures | 0.5 day | TODO | fig17, fig18; comparison table |
| 5 — Whitepaper integration | 0.5 day | TODO | Section 10.4 + REPORT.md |
| 6 — Test/document/commit | 0.5 day | TODO | Reproducibility check + PR |

**Total estimated duration: 3 days (2-day stretch if Phase 6 buffer collapses).**

---

## Acceptance Criteria Tracker

| AC | Criterion | Status |
|---|---|---|
| AC-01 | Deterministic 36 runs given seed=42 | PENDING |
| AC-02 | Comparison table populated | PENDING |
| AC-03 | CAIRN work-preserved ≥ LangGraph | PENDING |
| AC-04 | CAIRN unique on cross-framework portability | PENDING (architectural) |
| AC-05 | Naive restart 0% work-preserved | PENDING (trivially expected) |
| AC-06 | Single `run.py` entry, ≤ 5 min wall-clock | PENDING |
| AC-07 | Whitepaper section 10.4 added | PENDING |
| AC-08 | Figures 17 + 18 generated (PNG + SVG) | PENDING |

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-11 | Scope as parallel to arXiv submission, not blocking | The hardening pass in PR #21 closes the prose-level reviewer concerns; H8 is additive credibility, not corrective. Submission can proceed; H8 lands in v2.1 revision. |
| 2026-05-11 | Skip LOGIC failures in injection | Toy task is deterministic by construction; LOGIC failures don't arise. Comparison is meaningful for LIVENESS/RESOURCE classes only — the recoverable regime. |
| 2026-05-11 | Use `temporalio.testing.WorkflowEnvironment` instead of Temporal server | Removes infrastructure dependency for reproducibility. |
| 2026-05-11 | Defer cross-runtime (Python → Node/Rust) test to v3 | This experiment tests the JSON-schema portability *within* Python; cross-runtime is a stronger claim requiring more setup. |
| 2026-05-11 | Number new figures 17 + 18 (continuing simulation/figures/ series) | Avoids renumbering existing figures; reviewers comparing v2.0 → v2.1 see only additions. |

---

## Next Action

Approve this PRD. On approval:
1. Create `claude/h8-baseline-comparison-impl` from `main`.
2. Begin Phase 1 (task scaffold).
