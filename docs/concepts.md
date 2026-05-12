# CAIRN Concepts

> Core concepts, failure taxonomy, state machine, and glossary for the CAIRN Protocol.

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Failure Taxonomy](#failure-taxonomy)
3. [State Machine](#state-machine)
4. [Glossary](#glossary)

---

## Core Concepts

### Liveness Signal

A periodic on-chain ping that an agent emits to prove it is still alive and executing. The interval is set at task initialization and bounded by:

```
min(heartbeat_interval) = 30 seconds
max(heartbeat_interval) = task_deadline / 4
```

This ensures even the longest task emits at least four liveness signals before its deadline. If a liveness signal is missed, the enforce function can be called by anyone — another agent, a watcher, a keeper — to trigger the FAILED state transition. No oracle. No human required.

### Checkpoint

A committed record of a completed subtask. After each subtask, the agent:
1. Writes the subtask output to IPFS
2. Receives a content-addressed CID
3. Calls `commitCheckpoint(taskId, subtaskIndex, CID)` on the CAIRN contract
4. Reports the cost of that subtask

The CAIRN contract validates the CID against the declared output schema for that subtask. Invalid CIDs (schema mismatch) are rejected. Valid CIDs are committed and stored.

**Why checkpoints matter:** On recovery, the fallback agent reads the committed CID list and resumes from the last verified output. No restart from zero. The fallback inherits exactly what the original completed.

**Why checkpoints prevent gaming:** The original agent cannot fake checkpoints to inflate partial payment claims — schema validation rejects mismatched outputs. Checkpoints committed before failure are provably correct.

### Task Type

A two-level hierarchical identifier:

```
domain.operation
```

Examples:
- `defi.price_fetch`
- `defi.trade_execute`
- `data.report_generate`
- `governance.vote_delegate`
- `compute.model_inference`

Agents register which `domain.operation` pairs they support in their ERC-8004 identity card. The execution intelligence layer indexes all records by `task_type`. Fallback selection matches on `domain.operation` first, `domain` only as fallback if no exact match exists.

### Recovery Score

A deterministic score computed on FAILED state entry. No oracle. Pure math.

**v2 formula (multiplicative — simulation-validated):**
```
r = F^0.80 × B^0.35 × D^0.15
```

Where:
- `F` = `failure_class_weight`: LIVENESS = 0.70 | RESOURCE = 0.30 | LOGIC = 0.00
- `B` = `budget_remaining_pct`: (budget_cap - cost_accrued) / budget_cap, scaled to [0, 1]
- `D` = `deadline_remaining_pct`: (deadline - current_block) / (deadline - start_block), scaled to [0, 1]
- Exponents (0.80, 0.35, 0.15) are governance-adjustable.

The multiplicative form captures the "any-factor-kills-it" dynamic: if budget, deadline, or class recoverability approaches zero, the score collapses to zero — matching the ground-truth recovery dynamics. See [Whitepaper §6.4](../WHITEPAPER_V2.md) for the simulation methodology and [`simulation/RESULTS_EQ4.md`](../simulation/RESULTS_EQ4.md) for the calibration results (23.46% misrouting, within 0.93pp of Bayes-optimal).

**Three-tier routing (v2 thresholds):**
- `r ≥ 0.40` → **RECOVERING (full scope)** — high confidence, fallback receives full remaining budget
- `0.35 ≤ r < 0.40` → **RECOVERING (reduced scope)** — medium confidence, fallback receives capped budget
- `r < 0.35` → **DISPUTED** (requires arbiter resolution)

> **v1 testnet note.** The contract currently deployed on Base Sepolia (`RecoveryRouter.sol`) implements the pre-calibration linear formula `r = 0.5·F + 0.3·B + 0.2·D` with class weights `(0.90, 0.50, 0.10)` and a single binary threshold at `0.30`. The v2 multiplicative formula ships in `RecoveryRouterV2.sol` and migrates via governance through the `IRecoveryRouter` interface; see [PRD-04](../PRDs/PRD-04-V2-UPGRADE/PRD.md). Both `recoveryThresholdUpper` (0.40) and `recoveryThresholdLower` (0.35) are governance-adjustable in v2.

### Escrow Split Rule

On RESOLVED, escrow is distributed proportionally to verified work:

```
original_agent_share = (original_checkpoint_count / total_checkpoint_count) × escrow_amount × (1 - protocol_fee)
fallback_agent_share = (fallback_checkpoint_count / total_checkpoint_count) × escrow_amount × (1 - protocol_fee)
protocol_fee = 0.5% (configurable by governance)
```

If no recovery occurred (original agent completed solo): 100% to original agent minus protocol fee.

### Execution Record

A structured JSON document written to IPFS on every state transition. The CID is stored on-chain as an event. The full record is queryable off-chain via The Graph subgraph and Bonfires.

Two record types: Failure Record (written on FAILED) and Resolution Record (written on RESOLVED).

### The Cairn Metaphor

Travelers in wilderness stack stones — cairns — to mark where they have been, which paths are safe, and which lead nowhere. Each cairn is left by one traveler but read by every traveler who comes after. No traveler owns the cairn network. Every traveler benefits from it.

CAIRN applies this to agents. Every failure leaves a cairn — an execution record that marks this exact task type, this exact failure mode, this exact cost. Every future agent reads the cairns before setting out. The ecosystem navigates by accumulated failure intelligence, not blind optimism.

---

## Failure Taxonomy

CAIRN classifies failures by **recoverability**, not by symptom. Prior research identifies 14+ failure modes in multi-agent systems but most taxonomies describe surface symptoms ("step repetition") without prescribing what to do next. CAIRN's classification directly determines protocol behavior.

### Three Classes (Spec Level)

CAIRN's protocol-level taxonomy uses **three failure classes** for recovery scoring:

| Class | Class weight *F* (v2) | Description |
|-------|------------------------|-------------|
| **LIVENESS** (agent stopped) | 0.70 (high recovery) | Agent stopped responding — highly recoverable |
| **RESOURCE** (agent exhausted) | 0.30 (partial recovery) | Budget/deadline/external limits hit — partially recoverable |
| **LOGIC** (agent reasoning) | 0.00 (no recovery) | Invalid output or reasoning error — routes directly to DISPUTED |

> **v1 values:** LIVENESS=0.90, RESOURCE=0.50, LOGIC=0.10. The v2 weights were derived from the calibration simulation; see [Whitepaper §6.4](../WHITEPAPER_V2.md) for the rationale (LOGIC → 0.00 because at 8% base recovery rate, the expected value of a recovery attempt is less than the expected cost — direct dispute is the economically correct routing).

### Five Types (Contract Level)

The `RecoveryRouter` contract implements five specific **failure types** that map to the three classes:

| Failure Type | Maps To Class | Trigger |
|--------------|---------------|---------|
| `HEARTBEAT_MISS` | LIVENESS | Agent missed liveness signal deadline |
| `NETWORK_PARTITION` | LIVENESS | Agent disconnected from network |
| `RATE_LIMIT` | RESOURCE | External API rate limit exceeded |
| `GAS_EXHAUSTED` | RESOURCE | Budget depleted during execution |
| `VALIDATION_FAILED` | LOGIC | Output failed schema validation |

> **Note:** The FailureClass enum also includes `DEADLINE` for deadline-exceeded scenarios, which maps to RESOURCE behavior.

### Why Recoverability, Not Symptom

- **Liveness failures are almost always recoverable.** The agent stopped — not because the task is impossible, but because the agent crashed. A fallback can pick up exactly where it left off via the checkpoint list. Recovery score = HIGH.

- **Resource failures are partially recoverable.** The task may still be completable if the fallback operates more efficiently or if the remaining budget is sufficient. Recovery score = MEDIUM. Context depends on how much headroom remains.

- **Logic failures are rarely recoverable.** If the agent was reasoning incorrectly, a fallback with the same task spec will likely fail the same way. Assigning a fallback wastes more budget. Recovery score = LOW. Route to DISPUTED.

### Classification Algorithm

```python
def classifyFailure(failureEvent):
    if failureEvent.type == HEARTBEAT_MISSED:
        return LIVENESS
    if failureEvent.type in [BUDGET_HIT, DEADLINE_EXCEEDED, RATE_LIMIT, CONTEXT_OVERFLOW]:
        return RESOURCE
    if failureEvent.type in [LOOP_DETECTED, WRONG_TOOL, INVALID_OUTPUT, SPEC_MISMATCH]:
        return LOGIC
    # conservative — unknown failures treated as logic failures
    return LOGIC
```

---

## State Machine

Six states. Every transition is deterministic. No human is required to trigger any state change. The enforce functions are public — any external actor can call them.

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   CAIRN State Machine                   │
                    └─────────────────────────────────────────────────────────┘

    ┌──────┐  confirm   ┌─────────┐  task done  ┌──────────┐
    │      │ ─────────► │         │ ───────────► │          │
    │ IDLE │            │ RUNNING │              │ RESOLVED │ (terminal)
    │      │ ◄───────── │         │              │          │
    └──────┘            └────┬────┘              └────▲─────┘
                             │                        │
                    fault    │                        │ complete
                  detected   │                        │
                             ▼                        │
                        ┌─────────┐  r ≥ 0.35    ┌───┴──────┐
                        │         │ ────────────► │          │
                        │ FAILED  │  (≥0.40 full │RECOVERING│
                        │         │ ◄──────────── │ (full or │
                        └────┬────┘  0.35-0.40   │ reduced) │
                             │       reduced or   └──────────┘
                             │       fails
                       r     │
                      <0.35  │
                             ▼
                        ┌──────────┐  arbiter  ┌──────────┐
                        │          │ ─────────► │          │
                        │ DISPUTED │            │ RESOLVED │ (terminal)
                        │          │ timeout    │          │
                        └──────────┘ ─────────► └──────────┘
                                      refund    (auto-refund)
```

### IDLE

| Attribute | Value |
|---|---|
| Entry trigger | Operator submits task spec |
| Who can enter | Operator (task creator) |
| Actions | Query execution intelligence layer → receive known failure patterns + cost estimate + recommended agent. Operator reviews. Confirms. Locks escrow. Pre-authorizes CAIRN for fallback sub-delegation. |
| Exit | Operator confirmation → RUNNING |

**Critical action in IDLE:** The operator pre-authorizes CAIRN to sub-delegate permissions to a fallback agent. This is a caveat-enforced delegation scoped to: allowed actions, budget cap, allowed fallback agent pool. This authorization is committed at init — no new signature is required at recovery time.

### RUNNING

| Attribute | Value |
|---|---|
| Entry trigger | Operator confirmation. Escrow locked. Agent assigned. |
| Who can enter | From IDLE only |
| Actions | Agent executes subtasks. Writes checkpoint CID after each. Reports cost after each. Emits liveness ping every N time units. Protocol enforces liveness, budget, deadline — public enforce functions, anyone can call. |
| Exit — success | All subtasks complete → RESOLVED |
| Exit — failure | Liveness missed → FAILED (liveness class) |
| | Budget cap hit → FAILED (resource class) |
| | Deadline exceeded → FAILED (resource class) |

**Liveness enforcement detail:** The enforce function `checkLiveness(taskId)` can be called by any address after `last_heartbeat + heartbeat_interval` blocks have passed. This makes the protocol permissionless — no trusted keeper required.

### FAILED

| Attribute | Value |
|---|---|
| Entry trigger | Any RUNNING exit condition fires |
| Who can enter | From RUNNING only |
| Actions | Classify failure type. Compute recovery score. Write Failure Record to IPFS. Store CID on-chain (emit `TaskFailed(taskId, recordCID, recoveryScore)`). Hold escrow. |
| Exit — recoverable | `r ≥ 0.35` → RECOVERING (full or reduced) |
| Exit — unrecoverable | `r < 0.35` → DISPUTED |

**FAILED is not terminal.** It is a routing state. The only actions that happen here are classification, scoring, and record writing. The routing to RECOVERING (full or reduced) or DISPUTED happens automatically based on the score, partitioned by two thresholds in v2 (`recoveryThresholdUpper = 0.40`, `recoveryThresholdLower = 0.35`) or a single binary threshold in v1 (`recoveryThreshold = 0.30`).

### RECOVERING

| Attribute | Value |
|---|---|
| Entry trigger | Recovery score `r ≥ 0.35` from FAILED (v2; v1: `r ≥ 0.30`) |
| Who can enter | From FAILED only |
| Preconditions | Budget headroom must remain. Deadline headroom must remain. At least one fallback agent available in pool for this task_type above admission threshold. |
| Actions | Query execution intelligence layer for best fallback agent by task_type + reputation score. Select top available agent. Transfer task state: checkpoint CID list + remaining budget + remaining deadline. Transfer scoped permissions (pre-authorized caveat from IDLE). Fallback agent resumes from last committed checkpoint. New liveness clock starts for fallback. |
| Exit — success | Fallback completes → RESOLVED |
| Exit — failure | Fallback fails again → write second Failure Record → DISPUTED |
| Exit — unavailable | No fallback available → DISPUTED |

### RESOLVED

| Attribute | Value |
|---|---|
| Entry trigger | Task completed by any agent in the chain |
| Who can enter | From RUNNING (direct success) or RECOVERING (fallback success) |
| Actions | Compute escrow split by verified checkpoint count. Release escrow to original agent and/or fallback agent. Write Resolution Record to IPFS. Store CID on-chain (emit `TaskResolved(taskId, recordCID)`). Write positive reputation signal to ERC-8004 ReputationRegistry for completing agent(s). Close task. |
| Exit | Terminal. No exit. |

### DISPUTED

| Attribute | Value |
|---|---|
| Entry trigger | `r < 0.35` (v2; v1: `r < 0.30`), no fallback available, or all fallbacks failed |
| Who can enter | From FAILED only |
| Actions | Hold escrow — funds do not move. Write negative reputation signal to ERC-8004 ReputationRegistry for failing agent. Expose Failure Record CID publicly as arbitration evidence. Start arbiter timeout clock (N blocks, configurable). Any registered arbiter agent (staked, above reputation threshold) may call `rule(taskId, outcome)` within timeout window. Arbiter receives fee from held escrow on successful ruling. |
| Exit — arbiter rules | Arbiter submits ruling → RESOLVED (escrow distributed per ruling) |
| Exit — timeout | No arbiter rules within timeout → auto-refund to operator (terminal) |

---

## Glossary

| Term | Definition | UI/API Label |
|------|------------|--------------|
| **Agent** | An autonomous software entity that executes tasks on behalf of an operator | Agent |
| **Arbiter** | A staked agent registered to resolve disputes by evaluating execution records | Dispute Resolver |
| **Checkpoint** | A committed record of a completed subtask, stored as an IPFS CID | Saved Progress |
| **CID** | Content Identifier — a cryptographic hash of content stored on IPFS | Content ID |
| **Escrow** | Funds locked at task initialization, released on resolution | Held Payment |
| **Execution Record** | JSON document written to IPFS on state transitions (Failure or Resolution) | Execution Receipt |
| **Fallback Agent** | An agent that takes over a failed task from the original agent | Backup Agent |
| **Fallback Pool** | Registry of agents available for recovery assignments | Available Backups |
| **Heartbeat** | Periodic on-chain liveness signal emitted by an executing agent | Status Signal |
| **Liveness Signal** | See Heartbeat | Status Signal |
| **Operator** | The human or system that initiates a task and locks escrow | Task Owner |
| **Recovery Score** | Deterministic score (0-1) computed on failure to route to recovery or dispute | Recovery Likelihood |
| **Task Type** | Hierarchical identifier (`domain.operation`) classifying the work | Task Category |
| **Watcher** | Bot that monitors tasks and calls public enforce functions | Enforcement Monitor |

### Failure Class Labels

| Technical Class | Display Label | Description |
|-----------------|---------------|-------------|
| **LIVENESS** | Agent Unresponsive | Agent stopped emitting heartbeat signals |
| **RESOURCE** | Resource Exhausted | Budget, deadline, or external limits exceeded |
| **LOGIC** | Reasoning Error | Agent produced invalid output or entered invalid state |

### State Labels

| Technical State | Display Label | Description |
|-----------------|---------------|-------------|
| **IDLE** | Pending | Task initialized, awaiting confirmation |
| **RUNNING** | In Progress | Agent actively executing |
| **FAILED** | Failed | Failure detected, routing to recovery or dispute |
| **RECOVERING** | Recovering | Fallback agent assigned and executing |
| **RESOLVED** | Completed | Task finished, escrow distributed |
| **DISPUTED** | Under Review | Awaiting arbiter resolution |

### Recovery Score Display (v2 three-tier)

| Score Range | Display | Routing Outcome |
|-------------|---------|-----------------|
| `r ≥ 0.40` | Recoverable — full scope | Automatic recovery via fallback agent, full remaining budget |
| `0.35 ≤ r < 0.40` | Recoverable — reduced scope | Recovery attempt with capped budget |
| `r < 0.35` | Not recoverable | Routed to dispute resolution |

> **v1 testnet implementation:** uses a single threshold at `r = 0.30` (binary recover/dispute). The three-tier band above is the v2 specification; it ships on-chain via the `RecoveryRouterV2` migration ([PRD-04](../PRDs/PRD-04-V2-UPGRADE/PRD.md)).

---

*See also: [Architecture](./architecture.md) · [Integration](./integration.md) · [Contracts](./contracts.md)*

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
