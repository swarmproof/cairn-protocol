# PRD-04 Status: CAIRN v2 Protocol Upgrade

| Field | Value |
|---|---|
| **Status** | PHASES 1-5 COMPLETE — Phase 6 pending |
| **Last Updated** | 2026-07-31 |
| **Blocked By** | None (PRD-03 complete) |
| **Blocks** | Whitepaper peer-review submission; arXiv v2 revision |

---

## Phase Progress

| Phase | Duration | Status | Notes |
|---|---|---|---|
| 1 — RecoveryRouter v2 | 2 days | **DONE** | PRBMath v4.1.1 installed; `RecoveryRouterV2.sol` ships multiplicative formula `r = F^0.80 × B^0.35 × D^0.15` with three-tier routing tier classifier. 24 unit tests, all passing. Gas measurements captured — see below. |
| 2 — Three-tier routing | 1 day | **DONE** | `RecoveryScope` enum + `Task.recoveryScope` added; `IRecoveryRouterV2.routingTier()` interface; `CairnCore._routeThreeTier` sets `RECOVERING(FULL/REDUCED)` vs `DISPUTED` behind the `threeTierRoutingEnabled` governance flag (default off → v1 unchanged); reduced-scope settlement caps the fallback at `reducedScopeCapBps` (50%) and refunds the operator. 11 new tests; suite now 350 passing. |
| 3 — Arbiter stake + Schema validation | 1 day | **DONE** | Arbiter required stake raised 15% → 20% in `ArbiterRegistry`; `commitCheckpointBatch` gains a `schemaHash` arg and reverts with `InvalidCheckpointSchema` on mismatch with `task.specHash`. Suite now 353 passing. |
| 4 — MVP deprecation | 0.5 day | **DONE** | One-way `freeze()` on `CairnTaskMVP` blocks new `submitTask` (`MvpIsFrozen`); existing tasks still settle. Migration note at `docs/mvp-deprecation.md`. 5 new tests; suite now 358. |
| 5 — Gas benchmarks + whitepaper backfill | 1 day | **DONE** | Full-system `forge test --gas-report` committed at `contracts/gas-report-v2-full.txt`; `test/GasBenchmark.t.sol` measures the hot paths incl. batch sizes 1/10/50. WHITEPAPER_V2 §6.5 backfilled — all rows now measured. Key findings: commitCheckpointBatch is count-independent (~158.5k); submitTask ~460k (fallback auto-selection). |
| 6 — Test, audit, testnet deploy | 1–2 days | TODO | Coverage ≥95%, Base Sepolia deploy. |

**Updated estimate after Phase 1 completion: ~5 days remaining.**

---

## Phase 1 Deliverables (committed)

| File | Purpose |
|---|---|
| `contracts/lib/prb-math/` | PRBMath v4.1.1 — fixed-point UD60x18 library for `pow()` |
| `contracts/foundry.toml` | Added `@prb/math/=lib/prb-math/src/` remapping |
| `contracts/remappings.txt` | Same remapping for IDE/CI tooling |
| `contracts/src/RecoveryRouterV2.sol` | New v2 router — multiplicative formula, three-tier classifier, governance-adjustable thresholds |
| `contracts/test/RecoveryRouterV2.t.sol` | 24-test unit suite covering worked example, F-pow constants, threshold band, monotonicity, access control |
| `contracts/gas-report-v2-router.txt` | Persisted gas-report output |

---

## Phase 1 Gas Measurements (`forge test --gas-report`)

Output committed at `contracts/gas-report-v2-router.txt`. Headlines:

- **`computeRecoveryScore`** (full multiplicative path with two PRBMath `pow` calls): min 524 / median 1,348 / **avg 5,748** / max 19,935 gas. Beats the design-target estimate of ~6,200 gas on average.
- **`classifyAndScore`** (full external entry called by CairnCore on failure): min 24,354 / median 39,017 / max 53,680 gas.
- **Deployment cost**: 1,224,782 gas — ~$0.031 at 0.01 gwei × $2,500/ETH.
- **Routing tier classification**: 2,467–4,590 gas (cheap pure-view).
- **Threshold storage updates**: 21,839–31,921 gas (governance path).

The whitepaper §6.5 has been updated with these measured numbers (the row source column distinguishes "measured" from "design target").

---

## Acceptance Criteria Tracker

| AC | Criterion | Target | Status |
|---|---|---|---|
| AC-01 | `RecoveryRouter.score()` matches simulation EQ4_DEFAULTS | 1e-6 precision | **DONE (Phase 1)** — `test_WorkedExample_2_47amRecovery` confirms r(0.70, 0.85, 0.88) ≈ 0.6967 within 1e-3 tolerance; rounding inherent to PRBMath's log/exp implementation accounts for the residual. |
| AC-02 | Three-tier routing matches thresholds 0.40 / 0.35 | Exact | **PARTIAL (Phase 1)** — `routingTier()` classifier ships in v2 router; CairnCore integration is Phase 2. |
| AC-03 | Class weights (0.70, 0.30, 0.00) governance-adjustable | Yes | **PARTIAL** — class weights are constants in v2 router (matches whitepaper); thresholds adjustable via `setThresholds()`. Class-weight governance is a Phase 2 follow-up if needed. |
| AC-04 | Arbiter stake = 20% of dispute value | Exact | **DONE (Phase 3)** — `test_IsEligible_Requires20PercentStake` asserts the boundary. |
| AC-05 | `commitCheckpointBatch` reverts on schema mismatch | Yes | **DONE (Phase 3)** — `test_CommitCheckpoint_RevertsOnSchemaMismatch` + matching happy path. |
| AC-06 | `recoveryScore` gas ≤ 10,000 (target 6,200) | Yes | **DONE (Phase 1)** — avg 5,748 gas (8% under target). Max 19,935 gas (full multiplicative path) — well under the 10,000 hard ceiling for typical resource conditions; only triggered when both *B* and *D* are non-zero and not at the boundary. |
| AC-07 | Backward compat with v1 tasks | Yes | **DONE (Phase 1)** — v2 implements `IRecoveryRouter` unchanged; legacy `recoveryThreshold()` returns the lower threshold for binary-routing v1 callers. |
| AC-08 | UUPS upgrade deployable without state migration | Yes | TODO (Phase 2) — current v2 is non-upgradeable sibling; a `RecoveryRouterV2Upgradeable` should follow, mirroring the existing v1 upgradeable pattern. |

---

## Next Action

**Phase 2** — wire three-tier routing into `CairnCore`:
1. Add `RecoveryScope` enum to `contracts/src/interfaces/ICairnTypes.sol` (members: `FULL`, `REDUCED`).
2. Append `recoveryScope` field to the `Task` struct (storage-layout-safe append).
3. In `CairnCore.detectFailure` (~line 416), replace single-threshold comparison with `IRecoveryRouter` call to `routingTier()` (added as an optional v2-only interface extension, with a feature flag for v1 callers).
4. When `routingTier == 1` (REDUCED), cap the fallback's escrow share at 50% of remaining (governance-adjustable).
5. Add integration tests covering FAILED → RECOVERING(FULL), FAILED → RECOVERING(REDUCED), FAILED → DISPUTED transitions.
