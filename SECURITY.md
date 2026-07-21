# CAIRN Security Model

## Overview

CAIRN is designed to operate without trusted intermediaries. Security is enforced through economic incentives, on-chain verification, and permissionless enforcement.

This document describes the security model, known attack vectors, mitigations, trust assumptions, and protocol invariants.

---

## Security Principles

### 1. No Trusted Keepers

All enforce functions (`checkLiveness`, `checkBudget`, `checkDeadline`) are public. Anyone can call them. No trusted keeper network required.

The enforce function only succeeds if the condition is actually violated. False calls revert with no state change and no gas refund for the caller.

### 2. Escrow as Commitment

Agents cannot receive payment without completing the protocol. This makes record-writing mandatory, not voluntary. The intelligence layer grows automatically.

### 3. Stake-Based Accountability

Fallback agents and arbiters must stake capital proportional to their exposure. Bad behavior results in slashing:

| Role | Stake Requirement | Slash Condition |
|------|-------------------|-----------------|
| Fallback Agent | 10% of max eligible escrow | Fails without completing any checkpoints |
| Arbiter | 20% of max ruleable dispute | Incorrect ruling (detectable via on-chain evidence) |

### 4. Deterministic Scoring

Recovery score is a pure function of on-chain state. v2 specification:

```
r = F^0.80 × B^0.35 × D^0.15
```

with class weights LIVENESS=0.70, RESOURCE=0.30, LOGIC=0.00 and three-tier routing thresholds 0.40 / 0.35.

No oracle. No AI. No human judgment. All inputs are on-chain verifiable.

> v1 testnet uses the legacy linear formula `r = 0.5·F + 0.3·B + 0.2·D` with weights `(0.90, 0.50, 0.10)` and a single binary threshold at `0.30`. Determinism property holds for both.

---

## Attack Vectors and Mitigations

### 1. Checkpoint Gaming

**Attack:** Agent commits fake checkpoints to inflate partial payment claims.

**Severity:** High

**Mitigation:**
- Schema validation rejects CIDs that don't match declared output schema hash
- Schema hash is committed at task init and cannot be changed
- Off-chain validators (RecoveryOrchestrator, BonfiresAdapter) verify content
- Invalid checkpoints are caught before escrow settlement
- Repeated invalid attempts result in reputation decay

**Residual Risk:** If schema is too permissive, low-quality outputs may pass validation. Operators should define strict schemas.

### 2. Liveness Griefing

**Attack:** Malicious actor repeatedly calls `checkLiveness()` to force agents into FAILED state prematurely.

**Severity:** Low

**Mitigation:**
- `checkLiveness()` only succeeds if `block.number > last_heartbeat + heartbeat_interval`
- False calls revert with no state change
- Caller pays gas for failed calls
- No economic benefit to attacker

**Residual Risk:** None. The check is deterministic and tamper-proof.

### 3. Fallback Pool Sybil Attack

**Attack:** Attacker registers many low-quality fallback agents to capture recovery assignments and collect partial payments.

**Severity:** Medium

**Mitigation:**
- **Gate 1:** Minimum reputation score (50/100) in ERC-8004 for declared task_type
- **Gate 2:** Minimum stake deposit (10% of max eligible escrow)
- Stake is slashed 100% if fallback fails without completing any checkpoints
- Slashed funds go to operator, not protocol

**Residual Risk:** Attacker with sufficient capital could stake many agents. However, slashing makes this economically irrational.

### 4. Arbiter Collusion

**Attack:** Arbiter colludes with failing agent to rule in their favor (e.g., awarding escrow to agent who should not receive it).

**Severity:** Medium

**Mitigation:**
- Arbiter stake = 20% of dispute value
- Incorrect rulings are detectable via on-chain execution record evidence
- Incorrect rulings result in stake slashing
- Arbiter fee (3%) is less than stake at risk (20%)
- Economic cost of collusion exceeds benefit

**Residual Risk:** If evidence is ambiguous, arbiter has discretion. Future versions may implement multi-arbiter voting.

### 5. Recovery Score Manipulation

**Attack:** Agent manipulates failure conditions to achieve a desired recovery score (e.g., forcing RECOVERING instead of DISPUTED).

**Severity:** Low

**Mitigation:**
- Recovery score inputs are all on-chain:
  - `failure_class`: Detected automatically from failure event type
  - `budget_remaining_pct`: Computed from `budget_cap` and `cost_accrued`
  - `deadline_remaining_pct`: Computed from `deadline`, `start_block`, `current_block`
- Agent cannot control failure classification
- Agent cannot retroactively change budget or deadline

**Residual Risk:** Agent could strategically time failures, but this provides minimal benefit and wastes their own work.

### 6. Escrow Draining via Partial Completion

**Attack:** Agent completes minimal checkpoints then fails intentionally to collect partial payment without doing real work.

**Severity:** Medium

**Mitigation:**
- Checkpoint content must match declared schema
- Reputation system tracks completion rate per agent per task_type
- Agents with low completion rates are deprioritized in fallback selection
- Repeated intentional failures result in reputation below admission threshold
- Future: Operator-set minimum checkpoint count for partial payment

**Residual Risk:** Single-use attack is possible but results in permanent reputation damage.

### 7. Task Type Registry Pollution

**Attack:** Attacker registers many invalid or misleading task types to fragment the intelligence layer and reduce query accuracy.

**Severity:** Low (v1), Medium (open registry)

**Mitigation:**
- **v1:** Hardcoded task types (6 types). No open registration.
- **Future:** Registration requires stake and governance approval
- Duplicate/similar task types rejected by governance review

**Residual Risk:** None in v1. Future governance process must be robust.

### 8. Intelligence Layer Poisoning

**Attack:** Agents write false failure records to mislead future agents (e.g., claiming API X always fails to reduce competition).

**Severity:** Medium

**Mitigation:**
- Records are written automatically by protocol on state transitions
- Agents cannot directly write to the intelligence layer
- Record content matches on-chain state (checkpoint counts, costs, block numbers)
- False records would require compromising the protocol itself

**Residual Risk:** Agents could intentionally fail to create true-but-misleading failure records. However, this costs them money and reputation.

### 9. Front-Running

**Attack:** MEV searcher front-runs `assignFallback()` to capture recovery assignments for preferred agents.

**Severity:** Low

**Mitigation:**
- Fallback selection is based on reputation and stake, not transaction timing
- RecoveryOrchestrator operates off-chain and submits single transaction
- No auction or first-come-first-served mechanism

**Residual Risk:** Minimal. Selection criteria are deterministic.

### 10. Denial of Service on Enforce Functions

**Attack:** Attacker spams enforce function calls to increase gas costs for legitimate enforcement.

**Severity:** Low

**Mitigation:**
- Invalid calls revert quickly with minimal gas consumption
- No state changes on invalid calls
- Attacker pays gas costs
- No economic benefit to attacker

**Residual Risk:** None. This is expensive for attacker and ineffective.

---

## Trust Assumptions

### 1. IPFS Availability

**Assumption:** Checkpoint CIDs remain accessible for the duration of the task plus dispute period.

**Risk:** If IPFS content becomes unavailable, fallback agents cannot read prior checkpoints.

**Mitigation:** Use pinning services (Pinata, Infura, web3.storage). Operators can specify required pinning in task spec.

### 2. Block Time Consistency

**Assumption:** Base L2 maintains consistent ~2 second block times.

**Risk:** Block time variance could affect liveness interval calculations.

**Mitigation:** Intervals are specified in blocks, not seconds. Protocol adapts to actual block production.

### 3. ERC-8004 Registry Integrity

**Assumption:** ERC-8004 Reputation Registry contains accurate reputation scores.

**Risk:** Compromised reputation registry could enable unqualified fallback agents.

**Mitigation:** CAIRN inherits ERC-8004's security model. ERC-8004 has its own protections.

### 4. ERC-8183 Escrow Security

**Assumption:** ERC-8183 job escrow correctly holds and releases funds.

**Risk:** ERC-8183 vulnerability could result in lost funds.

**Mitigation:** CAIRN inherits ERC-8183's security model. Use audited ERC-8183 implementations.

### 5. Operator Honesty

**Assumption:** Operators submit accurate task specifications and schemas.

**Risk:** Malicious operator could submit impossible tasks or invalid schemas.

**Mitigation:** Agents can query task specs before accepting. Reputation flows both ways in future versions.

---

## Protocol Invariants

These properties MUST hold at all times:

### Invariant 1: Escrow Safety

Escrow MUST NOT be released until `state == RESOLVED`.

```solidity
require(task.state == TaskState.RESOLVED, "Escrow locked");
```

### Invariant 2: Deterministic Recovery Score

Recovery score MUST be deterministic given on-chain state. Same inputs MUST produce same score.

```solidity
recoveryScore = computeRecoveryScore(failureClass, budgetRemaining, deadlineRemaining);
// Pure function, no external calls
```

### Invariant 3: Checkpoint Immutability

Checkpoint CIDs MUST be immutable once committed. No deletion or modification.

```solidity
checkpointCIDs.push(cid); // Append only
```

### Invariant 4: State Irreversibility

State transitions MUST be irreversible. No backward transitions.

```
IDLE → RUNNING → {FAILED, RESOLVED}
FAILED → {RECOVERING, DISPUTED}
RECOVERING → {RESOLVED, DISPUTED}
DISPUTED → RESOLVED
RESOLVED → (terminal)
```

### Invariant 5: Fee Ordering

Protocol fee MUST be deducted before agent payments are calculated.

```solidity
uint256 distributable = escrowAmount * (1000 - protocolFeeBps) / 1000;
uint256 protocolFee = escrowAmount - distributable;
```

### Invariant 6: Liveness Enforcement

`checkLiveness()` MUST only succeed if heartbeat interval has actually elapsed.

```solidity
require(block.number > task.lastHeartbeat + task.heartbeatInterval, "Heartbeat not missed");
```

---

## Audit Status

| Auditor | Date | Scope | Status | Report |
|---------|------|-------|--------|--------|
| TBD | TBD | CairnCore.sol, RecoveryRouterV2.sol, FallbackPool.sol, ArbiterRegistry.sol, CairnGovernance.sol | Pending | - |

## Bug Bounty

A bug bounty program will be established post-launch. Details TBD.

## Responsible Disclosure

For security vulnerabilities, please contact: [security contact TBD]

Do NOT open public issues for security vulnerabilities.

---

*CAIRN Security Model — aligned with Whitepaper v2.0 (April 2026)*
