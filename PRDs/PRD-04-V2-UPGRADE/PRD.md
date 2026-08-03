# PRD-04: CAIRN v2 Protocol Upgrade

> Align the deployed contracts with the simulation-validated v2 specification in WHITEPAPER_V2.md

| Field | Value |
|---|---|
| **PRD ID** | PRD-04 |
| **Title** | CAIRN v2 Protocol Upgrade (Multiplicative Recovery Score + Three-Tier Routing) |
| **Status** | Draft |
| **Priority** | P0 (blocks peer-reviewed publication of whitepaper) |
| **Author** | Maroua Boudoukha |
| **Created** | April 2026 |
| **Estimated Complexity** | M (contained to 3 contracts + tests + one dependency) |
| **Blocks** | Whitepaper peer-review submission; §6.5 gas table backfill |
| **Blocked by** | PRD-03 (complete — recovery-score calibration delivered the v2 formula) |

---

## 1. Problem Statement

The deployed v1 testnet contract (`contracts/src/RecoveryRouter.sol` and upgradeable sibling) implements the pre-calibration linear recovery formula `r = 0.5·F + 0.3·B + 0.2·D` with class weights (0.90, 0.50, 0.10) and a single binary threshold at 0.30. The simulation work in PRD-03 (complete, Runs 1–4, 16 experiments, 100,000 events) identified a simulation-validated v2 formula that **achieves 23.46% misrouting vs. the v1 formula's 47.56%** — a 60% reduction in misrouting cost (~0.45 ETH / 1,000 tasks at 0.01 ETH average escrow).

The whitepaper (v2.0, April 2026) specifies v2 throughout while explicitly labeling v1 parameters in side-notes. Peer-review submission of the whitepaper is blocked until §6.5 gas costs are backed by measured `forge test --gas-report` output against the v2 implementation.

This PRD specifies the minimum v2 upgrade that (a) implements the multiplicative formula, (b) enables three-tier routing, (c) raises arbiter stake to match the incentive analysis, (d) activates per-checkpoint schema validation, and (e) produces the gas benchmark report needed to backfill §6.5.

---

## 2. Goals / Non-Goals

### Goals

- **G1**: Deployed `RecoveryRouter` computes `r = F^0.80 × B^0.35 × D^0.15` using fixed-point arithmetic.
- **G2**: `CairnCore` routes on three tiers (`r ≥ 0.40` → RECOVERING full, `0.35 ≤ r < 0.40` → RECOVERING reduced, `r < 0.35` → DISPUTED).
- **G3**: Class weights updated to (LIVENESS 0.70, RESOURCE 0.30, LOGIC 0.00). Thresholds at 0.40 / 0.35.
- **G4**: Arbiter minimum stake raised to **20% of max ruleable dispute** (from 15%), aligning with Proposition 3 of §7.5.
- **G5**: `commitCheckpointBatch` enforces schema-hash validation: each checkpoint CID's payload must match the `specHash` committed at task initialization.
- **G6**: Produce `forge test --gas-report` output covering `submitTask`, `commitCheckpointBatch` (batches of 1, 10, 50), `heartbeat`, `settle`, `recoveryScore` (both PRBMath and lookup variants).
- **G7**: The upgrade is deployable on existing v1 tasks via the governance path (no state-breaking migration).

### Non-Goals

- Multi-fallback chains (Section 10.2 future work — out of scope).
- Cross-chain fallback (Section 10.2 — out of scope).
- ZK-based private intelligence (Section 10.2 — out of scope).
- Olas Mech Marketplace integration (Section 4.4 optional — out of scope; interface left open).

---

## 3. Specification (aligned to WHITEPAPER_V2 §6.4, §6.5, §7.5)

### 3.1 RecoveryRouter v2

**Formula:**
```
r = F^a × B^b × D^c    (default: a=0.80, b=0.35, c=0.15)
```

**Class weights (v2 default):**
- `F_LIVENESS = 0.70e18` (18-decimal fixed-point)
- `F_RESOURCE = 0.30e18`
- `F_LOGIC   = 0.00e18` (routes directly to DISPUTED)

**Pre-computed F^0.80 lookup (saves 2 pow calls per score):**
- LIVENESS: `F^0.80 = 751758646650045568` (0.7518e18)
- RESOURCE: `F^0.80 = 381677890961817600` (0.3817e18)
- LOGIC:    `F^0.80 = 0`

> Note: the arithmetically correct constants are 0.7518 and 0.3817. The earlier draft in `simulation/RESULTS_EQ4.md` contained transcription errors (0.7639 / 0.3585) that were corrected in commit `fe9ce13`.

**Remaining terms `B^0.35` and `D^0.15`:**
- **Option A — PRBMath**: use `PRBMathUD60x18.pow(base, exp)` (≈3,000–6,000 gas per call, exponent-dependent).
- **Option B — binned lookup**: precompute 100 values for each of `B^0.35` (B ∈ [0, 1], step 0.01) and `D^0.15` (same). Lookup is O(1) via bucket math; total ~2,500 gas.
- **Decision**: ship Option A first (simpler, sufficient for Base L2 economics per §6.5). Keep Option B as an optimization PR if the gas report reveals >10k gas.

### 3.2 CairnCore three-tier routing

Replace the single-threshold logic at `CairnCore.sol:43, 416` with:
```solidity
uint256 public constant upperThreshold = 0.40e18;
uint256 public constant lowerThreshold = 0.35e18;

if (r >= upperThreshold) {
    // RECOVERING (full scope): fallback receives remaining escrow in full
    task.state = TaskState.RECOVERING;
    task.recoveryScope = RecoveryScope.FULL;
} else if (r >= lowerThreshold) {
    // RECOVERING (reduced scope): fallback receives capped budget (e.g., 50% of remaining)
    task.state = TaskState.RECOVERING;
    task.recoveryScope = RecoveryScope.REDUCED;
} else {
    // DISPUTED
    task.state = TaskState.DISPUTED;
}
```

**New type:**
```solidity
enum RecoveryScope { FULL, REDUCED }  // stored on Task
```

**Reduced-scope budget cap:** 50% of remaining escrow (governance-adjustable; ties to §6.6 "~25% of remaining escrow" cost coefficient for REDUCED-tier false positives).

### 3.3 Arbiter stake raise

Change `ArbiterRegistry.sol:348–350` (and upgradeable sibling) from 15% to 20% of `escrowAmount`. Update `minArbiterStake` floor if needed (currently 0.15 ETH — raise to 0.20 ETH for symmetry, optional).

### 3.4 Schema validation

Add to `commitCheckpointBatch` in `CairnCore.sol` and interface:
```solidity
function commitCheckpointBatch(
    bytes32 taskId,
    uint256 count,
    bytes32 merkleRoot,
    bytes32 latestCID,
    bytes32 schemaHash   // NEW: per-checkpoint schema hash (matches task.specHash)
) external;
```

**Enforcement:**
```solidity
if (schemaHash != task.specHash) revert InvalidCheckpointSchema();
```

This is the on-chain invariant that backs Proposition 1's "faking checkpoints is strictly dominated" claim and the §7.3 "Checkpoint gaming" mitigation. v1 stored `specHash` but never enforced it; v2 makes the comparison a transaction-revert condition.

### 3.5 MVP contract parity

`contracts/src/CairnTaskMVP.sol` exposes `commitCheckpoint(bytes32, bytes32)` (non-batched). For v2, either:
- **Option A (preferred):** deprecate MVP; route all traffic through `CairnCore`. MVP was for the hackathon ship — it can be sunset.
- **Option B:** add `commitCheckpointBatch` to MVP with the same signature as CairnCore's v2 version.

Decision: **Option A**. Emit a deprecation event on MVP at v2 activation; freeze new task submissions on MVP; allow existing MVP tasks to settle normally.

---

## 4. Task Breakdown

### Phase 1 — RecoveryRouter v2 (2 days)

| # | Task | Files | AC |
|---|---|---|---|
| T1.1 | Install PRBMath dependency | `foundry.toml`, `remappings.txt` | `forge install paulrberg/prb-math`; `remappings.txt` includes `prb-math/=lib/prb-math/src/` |
| T1.2 | Implement `RecoveryRouter` v2 logic | `contracts/src/RecoveryRouter.sol` | `score()` computes `r = F^0.80 × B^0.35 × D^0.15` using PRBMath pow for B, D; lookup for F |
| T1.3 | Update `RecoveryRouterUpgradeable` | `contracts/src/upgradeable/RecoveryRouterUpgradeable.sol` | Parity with non-upgradeable sibling |
| T1.4 | Update class weights and thresholds | `contracts/src/RecoveryRouter.sol:69–73, 274` | LIVENESS=0.70e18, RESOURCE=0.30e18, LOGIC=0 |
| T1.5 | Unit tests — formula output | `contracts/test/RecoveryRouter.t.sol` | `r(0.70, 0.85, 0.88) == 0.697e18` (±rounding); matches §2.4 worked example |
| T1.6 | Unit tests — three thresholds | same | LIVENESS w/ good resources → FULL; RESOURCE marginal → REDUCED; LOGIC → DISPUTED |

### Phase 2 — CairnCore three-tier routing (1 day)

| # | Task | Files | AC |
|---|---|---|---|
| T2.1 | Add `RecoveryScope` enum | `contracts/src/interfaces/ICairnTypes.sol` | New enum member available in type library |
| T2.2 | Add `recoveryScope` field to Task struct | `ICairnTypes.sol`, `CairnCore.sol` | Storage layout preserved for upgrade (append-only) |
| T2.3 | Replace single-threshold routing with three-tier | `CairnCore.sol:~416` | Three branches; reduced-tier sets budget cap |
| T2.4 | Reduced-scope budget cap logic | `CairnCore.sol` | Fallback escrow = `remainingEscrow × 0.5` for REDUCED |
| T2.5 | State-machine tests | `contracts/test/CairnCore.t.sol` | Can transition FAILED → RECOVERING(FULL), FAILED → RECOVERING(REDUCED), FAILED → DISPUTED |

### Phase 3 — Arbiter stake + Schema validation (1 day)

| # | Task | Files | AC |
|---|---|---|---|
| T3.1 | Raise arbiter stake 15% → 20% | `ArbiterRegistry.sol:348–350`, upgradeable sibling | `requiredStake = (escrowAmount * 20) / PRECISION` |
| T3.2 | Add `schemaHash` parameter to `commitCheckpointBatch` | `ICairnCore.sol`, `CairnCore.sol`, upgradeable | Signature change + enforcement revert |
| T3.3 | Add `InvalidCheckpointSchema` custom error | `CairnCore.sol` | Revert condition tested |
| T3.4 | Schema validation tests | `CairnCore.t.sol` | Happy path + fake-schema reverts |

### Phase 4 — MVP deprecation (0.5 day)

| # | Task | Files | AC |
|---|---|---|---|
| T4.1 | Add `MVPDeprecated` event + freeze flag | `CairnTaskMVP.sol` | `submitTask` reverts when frozen |
| T4.2 | Document migration path | `PRDs/PRD-04-V2-UPGRADE/MIGRATION.md` | Step-by-step for operators |

### Phase 5 — Gas benchmarks + whitepaper backfill (1 day)

| # | Task | Files | AC |
|---|---|---|---|
| T5.1 | Write gas-snapshot test | `contracts/test/GasSnapshot.t.sol` | Snapshots for all ops in §6.5 table |
| T5.2 | Run `forge test --gas-report` | — | Output written to `contracts/gas-report.txt` |
| T5.3 | Update WHITEPAPER_V2 §6.5 | `WHITEPAPER_V2.md:~660` | Replace "~80k estimate" etc. with measured values; drop "design-target estimates" label |
| T5.4 | Update PUBLICATION/arxiv/cairn-whitepaper.md snapshot | `PUBLICATION/arxiv/cairn-whitepaper.md` | Re-copy from updated WHITEPAPER_V2.md |
| T5.5 | Update §10.3 Limitations "v1/v2 gap" note | `WHITEPAPER_V2.md:~1035` | Mark v2 gas numbers as measured; retain v1 vs v2 migration note |

### Phase 6 — Test, audit, testnet deploy (1–2 days)

| # | Task | Files | AC |
|---|---|---|---|
| T6.1 | Full test suite passes | — | `forge test -vvv` green |
| T6.2 | Coverage ≥ 95% | — | `forge coverage` |
| T6.3 | Manual audit against WHITEPAPER_V2 §7 | — | Every "v2" claim has an on-chain enforcement |
| T6.4 | Deploy v2 to Base Sepolia | — | Address added to README "Deployed Contracts" table per CLAUDE.md §1.3 |
| T6.5 | Governance proposal to activate v2 | — | Operator-facing proposal draft |

---

## 5. Acceptance Criteria (whitepaper-linked)

| AC | Spec | WHITEPAPER_V2 § |
|---|---|---|
| AC-01 | `RecoveryRouter.score()` matches simulation's `scorer.EQ4_DEFAULTS` to 1e-6 precision | §6.4 |
| AC-02 | Three-tier routing matches simulation thresholds (0.40 / 0.35) | §2.2, §6.4 |
| AC-03 | Class weights (0.70, 0.30, 0.00) are governance-adjustable | §8.1 |
| AC-04 | Arbiter stake = 20% of dispute value (no floor below that ratio for disputes ≥ 1 ETH) | §6.3, §7.5 Prop 3 |
| AC-05 | `commitCheckpointBatch` reverts with `InvalidCheckpointSchema` when `schemaHash != task.specHash` | §7.3, §7.5 Prop 1 |
| AC-06 | Gas report produced, `recoveryScore` ≤ 10,000 gas (target 6,200), `commitCheckpointBatch(10)` ≤ 150,000 gas | §6.5 |
| AC-07 | Existing v1 tasks continue to settle normally under v2 (backward compatibility) | §8.3 |
| AC-08 | Upgrade is deployable via UUPS without state migration | §8.3 |

---

## 6. Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| PRBMath gas cost exceeds estimate (>10k per `pow` call) | Medium | Fall back to Option B (binned lookup); pre-written as an alternative |
| Three-tier routing breaks existing v1 integration tests | Medium | Add v2-specific test file; keep v1 tests passing until deprecation |
| Schema validation change is a breaking interface change | High | Deploy via UUPS upgrade path; new signature is additive (schemaHash appended); old MVP contract frozen but continues to settle existing tasks |
| Arbiter stake raise disincentivizes existing arbiters | Low | Grandfather existing arbiter deposits; raise applies only to new registrations |
| Gas benchmark differs on mainnet Base from Sepolia | Low | Document both; publish Sepolia numbers in §6.5 with mainnet verification noted as future work |

---

## 7. Timeline

| Phase | Duration | Deliverable |
|---|---|---|
| 1 — RecoveryRouter v2 | 2 days | Formula implemented + unit-tested |
| 2 — Three-tier routing | 1 day | State machine aligned with §2.2 |
| 3 — Arbiter + Schema | 1 day | Security invariants enforced |
| 4 — MVP deprecation | 0.5 day | Clean migration path |
| 5 — Gas benchmarks + whitepaper backfill | 1 day | §6.5 backed by measured numbers |
| 6 — Test, audit, testnet deploy | 1–2 days | READY_FOR_DEPLOYMENT verdict |
| **Total** | **6.5–7.5 days** | |

---

## 8. Dependencies

- **PRD-03** (Recovery Score Calibration) — ✅ Complete. Provides the simulation-validated v2 parameters.
- **PRD-01** (MVP Hackathon) — ✅ Complete. Provides the v1 baseline being upgraded.
- **PRD-02** (Audit Hardening) — Status uncertain; check `PRDs/PRD-02-AUDIT-HARDENING/STATUS.md` before starting to ensure security findings from that audit are not re-introduced.

---

## 9. After Completion

1. Update `WHITEPAPER_V2.md` §6.5 and §10.3 with measured gas numbers; mark v1/v2 gap as closed.
2. Re-run the four-audit pipeline (Tasks #1–#4 from audit session) as a regression check — confirm no new discrepancies.
3. Refresh `PUBLICATION/arxiv/cairn-whitepaper.md` snapshot.
4. Submit v2 whitepaper revision to arXiv (upgrades the v1.0 or v1.1 on arXiv to v2.0).
5. Proceed to peer-reviewed journal submission per `PUBLICATION/arxiv/README.md` post-submission section.

---

## 10. References

- [WHITEPAPER_V2.md §6.4](../../WHITEPAPER_V2.md) — the v2 formula specification
- [WHITEPAPER_V2.md §10.1](../../WHITEPAPER_V2.md) — simulation methodology and results
- [simulation/RESULTS_EQ4.md](../../simulation/RESULTS_EQ4.md) — Run 4 raw results + corrected Solidity constants
- [PRD-03](../PRD-03-RECOVERY-CALIBRATION/PRD.md) — calibration work that produced the v2 formula
- Audit reports from April 2026 session (retained in commit history on `claude/audit-fixes`)
