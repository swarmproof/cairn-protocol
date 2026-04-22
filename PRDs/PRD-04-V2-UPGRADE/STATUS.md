# PRD-04 Status: CAIRN v2 Protocol Upgrade

| Field | Value |
|---|---|
| **Status** | NOT STARTED |
| **Last Updated** | 2026-04-22 |
| **Blocked By** | None (PRD-03 complete) |
| **Blocks** | Whitepaper peer-review submission; §6.5 gas table backfill; arXiv v2 revision |

---

## Phase Progress

| Phase | Duration | Status | Notes |
|---|---|---|---|
| 1 — RecoveryRouter v2 | 2 days | TODO | Install PRBMath, implement multiplicative formula, unit tests |
| 2 — Three-tier routing | 1 day | TODO | Add `RecoveryScope` enum, update CairnCore routing |
| 3 — Arbiter stake + Schema validation | 1 day | TODO | 15% → 20%, `specHash` enforcement |
| 4 — MVP deprecation | 0.5 day | TODO | Freeze flag + migration doc |
| 5 — Gas benchmarks + whitepaper backfill | 1 day | TODO | `forge test --gas-report` + update §6.5, §10.3 |
| 6 — Test, audit, testnet deploy | 1–2 days | TODO | Coverage ≥95%, Base Sepolia deploy |

**Total estimated duration: 6.5–7.5 days**

---

## Acceptance Criteria Tracker

| AC | Criterion | Target | Status |
|---|---|---|---|
| AC-01 | `RecoveryRouter.score()` matches simulation EQ4_DEFAULTS | 1e-6 precision | PENDING |
| AC-02 | Three-tier routing matches thresholds 0.40 / 0.35 | Exact | PENDING |
| AC-03 | Class weights (0.70, 0.30, 0.00) governance-adjustable | Yes | PENDING |
| AC-04 | Arbiter stake = 20% of dispute value | Exact | PENDING |
| AC-05 | `commitCheckpointBatch` reverts on schema mismatch | Yes | PENDING |
| AC-06 | `recoveryScore` gas ≤ 10,000 (target 6,200) | Yes | PENDING |
| AC-07 | Backward compat with v1 tasks | Yes | PENDING |
| AC-08 | UUPS upgrade deployable without state migration | Yes | PENDING |

---

## Next Action

Start Phase 1 (RecoveryRouter v2). First task: install PRBMath via `forge install paulrberg/prb-math` and update `foundry.toml` / `remappings.txt`.
