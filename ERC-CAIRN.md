---
eip: TBD
title: Agent Failure and Recovery Standard
description: A standard interface for agent task lifecycle, failure classification, checkpoint-based recovery, and execution intelligence accumulation
author: Maroua BOUDOUKHA (@marouaboudoukha)
status: Draft
type: Standards Track
category: ERC
created: 2025-03-16
requires: 8183, 8004, 7710
license: CC0-1.0
---

## Abstract

CAIRN defines a standard interface for agent task lifecycle management, failure classification, checkpoint-based recovery, and execution intelligence accumulation. It extends ERC-8183 (Agentic Commerce) with a failure and recovery layer and integrates ERC-8004 (Trustless Agents) for identity and reputation.

The protocol enables autonomous recovery from agent failures by: (1) classifying failures by recoverability, (2) routing recoverable failures to qualified fallback agents, (3) settling escrow proportionally to verified work, and (4) accumulating execution intelligence that future agents inherit.

---

## Motivation

The Ethereum agentic economy generates significant economic activity but lacks standardized failure handling. When an agent fails mid-task, there is:

- No standard definition of what a failure is
- No standard protocol for what happens when one is detected
- No standard mechanism for task handoff to a fallback agent
- No standard escrow settlement rule for partial completion
- No shared record of what failed, why, and what worked instead

Every team building agents has written bespoke, incompatible failure handling. CAIRN provides the missing standard.

---

## Specification

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in RFC 2119 and RFC 8174.

### Definitions

#### Liveness Signal

A periodic on-chain ping that an agent emits to prove it is still alive and executing. The interval is set at task initialization and bounded by:

```
min(heartbeat_interval) = 30 seconds
max(heartbeat_interval) = task_deadline / 4
```

If a liveness signal is missed, the enforce function can be called by anyone to trigger the FAILED state transition.

#### Checkpoint

A committed record of a completed subtask. After each subtask, the agent:
1. Writes the subtask output to IPFS
2. Receives a content-addressed CID
3. Calls `commitCheckpoint(taskId, subtaskIndex, CID)` on the CAIRN contract
4. Reports the cost of that subtask

The CAIRN contract validates the CID against the declared output schema for that subtask.

#### Task Type

A two-level hierarchical identifier:

```
domain.operation
```

Examples:
- `defi.price_fetch`
- `defi.trade_execute`
- `data.report_generate`
- `governance.vote_delegate`

#### Recovery Score

A deterministic score computed on FAILED state entry:

```
recovery_score = (failure_class_weight × 0.5) + (budget_remaining_pct × 0.3) + (deadline_remaining_pct × 0.2)
```

Where:
- `failure_class_weight`: Liveness = 0.9 | Resource = 0.5 | Logic = 0.1
- `budget_remaining_pct`: (budget_cap - cost_accrued) / budget_cap
- `deadline_remaining_pct`: (deadline - current_block) / (deadline - start_block)

#### Escrow Split Rule

On RESOLVED, escrow is distributed proportionally to verified work:

```
original_agent_share = (original_checkpoint_count / total_checkpoint_count) × escrow_amount × (1 - protocol_fee)
fallback_agent_share = (fallback_checkpoint_count / total_checkpoint_count) × escrow_amount × (1 - protocol_fee)
```

#### Execution Record

A structured JSON document written to IPFS on every state transition. The CID is stored on-chain as an event.

### Failure Taxonomy

CAIRN classifies failures by **recoverability**, not by symptom.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLASS             │ FAILURE TYPES                    │ RECOVERY SCORE WEIGHT │
├─────────────────────────────────────────────────────────────────────────────┤
│ LIVENESS          │ Heartbeat missed                 │ 0.9 (HIGH)            │
│ (agent stopped)   │ Process crash                    │                       │
│                   │ Network partition                │                       │
│                   │ Infrastructure timeout           │                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ RESOURCE          │ Budget cap hit                   │ 0.5 (MEDIUM)          │
│ (agent exhausted) │ Deadline exceeded                │                       │
│                   │ API rate limit                   │                       │
│                   │ Context window overflow          │                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ LOGIC             │ Step repetition loop             │ 0.1 (LOW)             │
│ (agent reasoning) │ Wrong tool selected              │                       │
│                   │ Hallucinated output              │                       │
│                   │ Spec misalignment                │                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Classification Algorithm

```
function classifyFailure(failureEvent):
  if failureEvent.type == HEARTBEAT_MISSED:
    return LIVENESS
  if failureEvent.type in [BUDGET_HIT, DEADLINE_EXCEEDED, RATE_LIMIT, CONTEXT_OVERFLOW]:
    return RESOURCE
  if failureEvent.type in [LOOP_DETECTED, WRONG_TOOL, INVALID_OUTPUT, SPEC_MISMATCH]:
    return LOGIC
  default:
    return LOGIC  // conservative — unknown failures treated as logic failures
```

### State Machine

Six states. Every transition is deterministic. No human is required to trigger any state change.

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
                        ┌─────────┐   score≥0.3  ┌───┴──────┐
                        │         │ ────────────► │          │
                        │ FAILED  │               │RECOVERING│
                        │         │ ◄──────────── │          │
                        └────┬────┘  fallback     └──────────┘
                             │       fails
                      score  │
                      <0.3   │
                             ▼
                        ┌──────────┐  arbiter  ┌──────────┐
                        │          │ ─────────► │          │
                        │ DISPUTED │            │ RESOLVED │ (terminal)
                        │          │ timeout    │          │
                        └──────────┘ ─────────► └──────────┘
                                      refund    (auto-refund)
```

#### IDLE State

| Attribute | Value |
|---|---|
| Entry trigger | Operator submits task spec |
| Who can enter | Operator (task creator) |
| Actions | Query execution intelligence layer. Operator reviews. Confirms. Locks escrow. Pre-authorizes CAIRN for fallback sub-delegation. |
| Exit | Operator confirmation → RUNNING |

#### RUNNING State

| Attribute | Value |
|---|---|
| Entry trigger | Operator confirmation. Escrow locked. Agent assigned. |
| Who can enter | From IDLE only |
| Actions | Agent executes subtasks. Writes checkpoint CID after each. Reports cost. Emits liveness ping every N blocks. |
| Exit — success | All subtasks complete → RESOLVED |
| Exit — failure | Liveness missed / Budget hit / Deadline exceeded → FAILED |

#### FAILED State

| Attribute | Value |
|---|---|
| Entry trigger | Any RUNNING exit condition fires |
| Who can enter | From RUNNING only |
| Actions | Classify failure type. Compute recovery score. Write Failure Record to IPFS. Store CID on-chain. Hold escrow. |
| Exit — recoverable | Score ≥ 0.3 → RECOVERING |
| Exit — unrecoverable | Score < 0.3 → DISPUTED |

#### RECOVERING State

| Attribute | Value |
|---|---|
| Entry trigger | Recovery score ≥ 0.3 from FAILED |
| Who can enter | From FAILED only |
| Preconditions | Budget headroom. Deadline headroom. Fallback agent available. |
| Actions | Select fallback agent. Transfer task state (checkpoint CIDs, remaining budget, permissions). Fallback resumes from last checkpoint. |
| Exit — success | Fallback completes → RESOLVED |
| Exit — failure | Fallback fails → DISPUTED |

#### RESOLVED State

| Attribute | Value |
|---|---|
| Entry trigger | Task completed by any agent in the chain |
| Who can enter | From RUNNING or RECOVERING |
| Actions | Compute escrow split. Release escrow. Write Resolution Record. Write reputation signals to ERC-8004. |
| Exit | Terminal. No exit. |

#### DISPUTED State

| Attribute | Value |
|---|---|
| Entry trigger | Score < 0.3, no fallback, or fallback failed |
| Who can enter | From FAILED only |
| Actions | Hold escrow. Write negative reputation. Expose Failure Record. Start arbiter timeout. |
| Exit — arbiter rules | Arbiter submits ruling → RESOLVED |
| Exit — timeout | No ruling within timeout → auto-refund to operator |

### Action Sequence

14 actions across 6 phases.

#### Phase 1: Initialization (A1-A3)

| Action | Actor | Description |
|---|---|---|
| A1 | Operator | Submit task spec: task_type, budget_cap, deadline, subtask schemas |
| A2 | Protocol | Query intelligence layer: failure patterns, cost estimate, recommended agent |
| A3 | Operator | Confirm task. Lock escrow. Pre-authorize fallback delegation (ERC-7710). |

#### Phase 2: Running (A4-A6)

| Action | Actor | Description |
|---|---|---|
| A4 | Agent | Complete subtask. Write output to IPFS. Call commitCheckpoint(). |
| A5 | Agent | Emit heartbeat(taskId) within interval. |
| A6 | Anyone | Call enforce functions: checkLiveness(), checkBudget(), checkDeadline(). |

#### Phase 3: Failed (A7-A8)

| Action | Actor | Description |
|---|---|---|
| A7 | Protocol | Classify failure. Compute recovery score. Write Failure Record. |
| A8 | Protocol | Route: score ≥ 0.3 → RECOVERING; score < 0.3 → DISPUTED. |

#### Phase 4: Recovering (A9-A11)

| Action | Actor | Description |
|---|---|---|
| A9 | Protocol | Query for best fallback agent by task_type + reputation. |
| A10 | Protocol | Transfer state: checkpoint CIDs, remaining budget, permissions. |
| A11 | Fallback | Resume from last checkpoint. Continue A4/A5/A6 cycle. |

#### Phase 5: Resolved (A12)

| Action | Actor | Description |
|---|---|---|
| A12 | Protocol | Compute escrow split. Release funds. Write Resolution Record. Update reputation. |

#### Phase 6: Disputed (A13-A14)

| Action | Actor | Description |
|---|---|---|
| A13 | Protocol | Hold escrow. Write negative reputation. Start arbiter timeout. |
| A14 | Arbiter | Rule on dispute OR timeout triggers auto-refund. |

### Data Structures

#### TaskSpec

```typescript
interface TaskSpec {
  task_type: string;              // "domain.operation" format
  budget_cap: bigint;             // in wei
  deadline: number;               // block number
  heartbeat_interval?: number;    // blocks (optional)
  subtask_count: number;
  subtask_schemas: SubtaskSchema[];
  description: string;
  output_format: string;          // IPFS CID of JSON schema
}

interface SubtaskSchema {
  index: number;
  description: string;
  output_schema_cid: string;
}
```

#### CheckpointCommit

```typescript
interface CheckpointCommit {
  task_id: bytes32;
  subtask_index: number;
  output_cid: string;
  cost_wei: bigint;
}
```

#### Failure Record

```json
{
  "$schema": "https://cairn.protocol/schemas/failure-record-v1.json",
  "record_type": "failure",
  "task_id": "bytes32",
  "agent_id": "erc8004://chain_id/contract_address/agent_token_id",
  "task_type": "domain.operation",
  "failure_class": "LIVENESS | RESOURCE | LOGIC",
  "failure_type": "HEARTBEAT_MISSED | BUDGET_HIT | DEADLINE_EXCEEDED | RATE_LIMIT | CONTEXT_OVERFLOW | LOOP_DETECTED | WRONG_TOOL | INVALID_OUTPUT | SPEC_MISMATCH",
  "checkpoint_count_at_failure": "uint",
  "cost_at_failure_wei": "uint",
  "budget_remaining_pct": "float [0,1]",
  "deadline_remaining_pct": "float [0,1]",
  "recovery_score": "float [0,1]",
  "block_number": "uint",
  "timestamp": "uint"
}
```

#### Resolution Record

```json
{
  "$schema": "https://cairn.protocol/schemas/resolution-record-v1.json",
  "record_type": "resolution",
  "task_id": "bytes32",
  "states_traversed": ["RUNNING", "FAILED?", "RECOVERING?", "RESOLVED"],
  "original_agent_id": "erc8004://...",
  "fallback_agent_id": "erc8004://... | null",
  "task_type": "domain.operation",
  "total_cost_wei": "uint",
  "total_duration_blocks": "uint",
  "original_checkpoint_count": "uint",
  "fallback_checkpoint_count": "uint",
  "escrow_split": {
    "original_agent_wei": "uint",
    "fallback_agent_wei": "uint",
    "protocol_fee_wei": "uint"
  },
  "failure_record_cid": "string | null",
  "block_number": "uint",
  "timestamp": "uint"
}
```

### Contract Interface

```solidity
// SPDX-License-Identifier: MIT
// CAIRN — Agent Failure and Recovery Protocol

interface ICairnTask {

    // ── Enums ────────────────────────────────────────────────────────────────

    enum TaskState { IDLE, RUNNING, FAILED, RECOVERING, RESOLVED, DISPUTED }
    enum FailureClass { LIVENESS, RESOURCE, LOGIC }
    enum FailureType {
        HEARTBEAT_MISSED,
        BUDGET_HIT,
        DEADLINE_EXCEEDED,
        RATE_LIMIT,
        CONTEXT_OVERFLOW,
        LOOP_DETECTED,
        WRONG_TOOL,
        INVALID_OUTPUT,
        SPEC_MISMATCH
    }

    // ── Structs ──────────────────────────────────────────────────────────────

    struct TaskSpec {
        bytes32     taskType;
        uint256     budgetCap;
        uint256     deadline;
        uint256     heartbeatInterval;
        uint256     subtaskCount;
        bytes32[]   subtaskSchemaHashes;
        string      descriptionCID;
    }

    struct Task {
        address     operator;
        address     agentId;
        TaskState   state;
        bytes32     taskType;
        uint256     budgetCap;
        uint256     costAccrued;
        uint256     deadline;
        uint256     heartbeatInterval;
        uint256     lastHeartbeat;
        uint256     startBlock;
        uint256     subtaskCount;
        uint256     completedSubtasks;
        address     fallbackAgentId;
        uint256     fallbackSubtasks;
        string[]    checkpointCIDs;
        string      failureRecordCID;
        string      resolutionRecordCID;
    }

    // ── Events ───────────────────────────────────────────────────────────────

    event TaskStarted(bytes32 indexed taskId, address indexed agentId, bytes32 taskType);
    event CheckpointCommitted(bytes32 indexed taskId, uint256 subtaskIndex, string cid, uint256 cost);
    event TaskFailed(bytes32 indexed taskId, string recordCID, uint256 recoveryScore, FailureClass failureClass);
    event FallbackAssigned(bytes32 indexed taskId, address fallbackAgentId);
    event TaskResolved(bytes32 indexed taskId, string recordCID, uint256 originalShare, uint256 fallbackShare);
    event TaskDisputed(bytes32 indexed taskId, string recordCID, uint256 arbiterTimeout);
    event TaskRefunded(bytes32 indexed taskId, uint256 refundAmount);
    event ArbiterRuled(bytes32 indexed taskId, address arbiter, uint8 outcome);

    // ── Write Methods ────────────────────────────────────────────────────────

    function startTask(TaskSpec calldata spec, address agentId)
        external payable returns (bytes32 taskId);

    function heartbeat(bytes32 taskId) external;

    function commitCheckpoint(bytes32 taskId, uint256 subtaskIndex, string calldata cid, uint256 cost)
        external;

    function completeTask(bytes32 taskId) external;

    // Public enforce functions — anyone can call
    function checkLiveness(bytes32 taskId) external;
    function checkBudget(bytes32 taskId) external;
    function checkDeadline(bytes32 taskId) external;

    function assignFallback(bytes32 taskId, address fallbackAgentId) external;

    function rule(bytes32 taskId, uint8 outcome) external;

    // ── Read Methods ─────────────────────────────────────────────────────────

    function getTask(bytes32 taskId) external view returns (Task memory);
    function getCheckpoints(bytes32 taskId) external view returns (string[] memory);
    function getRecoveryScore(bytes32 taskId) external view returns (uint256);
    function isArbiterEligible(address arbiter, bytes32 taskId) external view returns (bool);
}
```

#### ICairnHook (ERC-8183 Hook)

```solidity
interface ICairnHook {
    function beforeFund(bytes32 jobId, bytes calldata params) external;
    function afterFund(bytes32 jobId, bytes calldata params) external;
    function beforeComplete(bytes32 jobId, bytes calldata params) external;
    function afterComplete(bytes32 jobId, bytes calldata params) external;
    function beforeReject(bytes32 jobId, bytes calldata params) external;
    function afterReject(bytes32 jobId, bytes calldata params) external;
}
```

### Events

| Event | When Emitted | Parameters |
|-------|--------------|------------|
| `TaskStarted` | A3: Task confirmed | taskId, agentId, taskType |
| `CheckpointCommitted` | A4: Checkpoint written | taskId, subtaskIndex, cid, cost |
| `TaskFailed` | A7: Failure detected | taskId, recordCID, recoveryScore, failureClass |
| `FallbackAssigned` | A10: Fallback selected | taskId, fallbackAgentId |
| `TaskResolved` | A12: Task completed | taskId, recordCID, originalShare, fallbackShare |
| `TaskDisputed` | A13: Dispute opened | taskId, recordCID, arbiterTimeout |
| `TaskRefunded` | A14: Timeout refund | taskId, refundAmount |
| `ArbiterRuled` | A14: Arbiter decision | taskId, arbiter, outcome |

---

## Rationale

### Why Checkpoint-Based Recovery

Without checkpoints, a fallback agent must restart the entire task — wasting completed work and budget. Checkpoints enable resume-not-restart, where fallback agents inherit exactly what the original completed.

### Why Three Failure Classes

Prior taxonomies identify 14+ failure modes but classify by symptom, not recoverability. CAIRN's three-class system directly determines protocol behavior:
- LIVENESS → high recovery chance → assign fallback
- RESOURCE → medium → attempt if headroom exists
- LOGIC → low → route to dispute (fallback would likely fail the same way)

### Why Permissionless Enforcement

Trusted keeper networks create centralization risk. CAIRN's enforce functions are public — anyone can call them, and they only succeed if the condition is actually violated.

### Why Pre-Authorized Delegation

Requiring a new signature at recovery time creates latency and may fail if the operator is offline. Pre-authorization via ERC-7710 caveat at task init enables instant fallback assignment.

### Why Escrow-Enforced Record Writing

Optional participation creates a cold-start problem. By making record-writing mandatory for escrow settlement, CAIRN bootstraps the intelligence layer from day one.

---

## Backwards Compatibility

### Relationship to ERC-8183

CAIRN implements the ERC-8183 Hook interface. Existing ERC-8183 jobs can adopt CAIRN by setting CairnTask as the evaluator address. No changes to ERC-8183 are required.

### Relationship to ERC-8004

CAIRN reads agent identity from and writes reputation signals to ERC-8004 registries. No changes to ERC-8004 are required.

### Relationship to ERC-7710

CAIRN uses ERC-7710 caveat-enforced delegation for fallback authorization. No changes to ERC-7710 are required.

### Migration Path

Existing agents can integrate CAIRN by:
1. Adding checkpoint commit calls after each subtask
2. Adding heartbeat calls within the declared interval
3. Registering supported task types in their ERC-8004 identity

No protocol-level migration is required.

---

## Test Cases

### Test Case 1: Successful Task Completion

```
Given: Task initialized with 5 subtasks
When: Agent completes all 5 subtasks with valid checkpoints
Then: State transitions IDLE → RUNNING → RESOLVED
And: 100% escrow released to agent minus protocol fee
And: Positive reputation signal written to ERC-8004
```

### Test Case 2: Liveness Failure with Recovery

```
Given: Task in RUNNING with 3/5 subtasks complete
When: Agent misses heartbeat by 1 block
And: Anyone calls checkLiveness(taskId)
Then: State transitions RUNNING → FAILED
And: Recovery score = 0.9 × 0.5 + budget_pct × 0.3 + deadline_pct × 0.2
And: If score ≥ 0.3: State → RECOVERING
And: Fallback assigned, resumes from checkpoint 3
```

### Test Case 3: Logic Failure Routes to Dispute

```
Given: Task in RUNNING with loop detected
When: Failure classified as LOGIC class
Then: Recovery score < 0.3 (logic weight = 0.1)
And: State transitions RUNNING → FAILED → DISPUTED
And: Escrow held, not released
```

### Test Case 4: Escrow Split Calculation

```
Given: Total escrow = 1 ETH, protocol fee = 0.5%
And: Original agent completed 3 checkpoints
And: Fallback agent completed 2 checkpoints
When: Task resolves
Then: Original receives 3/5 × 0.995 ETH = 0.597 ETH
And: Fallback receives 2/5 × 0.995 ETH = 0.398 ETH
And: Protocol receives 0.005 ETH
```

### Test Case 5: Arbiter Timeout Refund

```
Given: Task in DISPUTED state
And: Arbiter timeout = 302,400 blocks (7 days)
When: 302,401 blocks pass with no arbiter ruling
Then: Anyone can call checkTimeout(taskId)
And: Escrow auto-refunds to operator
And: TaskRefunded event emitted
```

---

## Reference Implementation

### CairnTask.sol

The core state machine contract. ~250 lines of Solidity.
- State management for all six states
- Liveness, budget, and deadline enforcement (public functions)
- Checkpoint storage and schema validation
- Recovery score computation
- Escrow split computation
- Event emission for all state transitions

### CairnHook.sol

ERC-8183 hook implementation. ~80 lines.
- Implements the ERC-8183 hook interface
- Called by ERC-8183 job contract on state transitions
- Delegates to CairnTask for CAIRN-specific logic

See [contracts documentation](./docs/contracts.md) for full implementation details.

---

## Security Considerations

### Attack Vector Analysis

#### 1. Checkpoint Gaming

**Attack:** Agent commits fake checkpoints to inflate partial payment claims.

**Mitigation:** Schema validation rejects CIDs that don't match declared output schema hash. Off-chain validators verify content. Invalid checkpoints caught before escrow settlement.

#### 2. Liveness Griefing

**Attack:** Malicious actor repeatedly calls checkLiveness() to force agents into FAILED state.

**Mitigation:** checkLiveness() only succeeds if heartbeat_interval has actually passed since last_heartbeat. False calls revert with no state change.

#### 3. Fallback Pool Sybil Attack

**Attack:** Attacker registers many low-quality fallback agents to capture recovery assignments.

**Mitigation:** Two-gate admission: minimum reputation score (50/100) AND minimum stake (10% of max eligible escrow). Stake slashed if fallback fails without completing any checkpoints.

#### 4. Arbiter Collusion

**Attack:** Arbiter colludes with failing agent to rule in their favor.

**Mitigation:** Arbiter stake proportional to dispute value (15%). Incorrect rulings (detectable via on-chain evidence) result in stake slashing. Economic cost of collusion exceeds benefit.

#### 5. Recovery Score Manipulation

**Attack:** Agent manipulates failure conditions to achieve desired recovery score.

**Mitigation:** Recovery score is deterministic function of: failure_class (detected automatically), budget_remaining (on-chain), deadline_remaining (on-chain). No agent-controlled inputs.

#### 6. Escrow Draining via Partial Completion

**Attack:** Agent completes minimal checkpoints then fails intentionally to collect partial payment.

**Mitigation:** Checkpoint content must match schema (verified). Reputation system tracks completion rate. Repeated failures result in reputation decay and exclusion from assignments.

#### 7. Task Type Registry Pollution

**Attack:** Attacker registers many invalid task types to fragment the intelligence layer.

**Mitigation:** (v1) Hardcoded task types. (Production) Registration requires stake and governance approval.

#### 8. Intelligence Layer Poisoning

**Attack:** Agents write false failure records to mislead future agents.

**Mitigation:** Records are written automatically by protocol on state transitions, not by agents directly. Content is on-chain verifiable.

### Trust Assumptions

1. **IPFS availability:** Checkpoint CIDs must remain accessible for fallback recovery.
2. **Block time consistency:** Liveness intervals assume consistent block production.
3. **ERC-8004 registry integrity:** Reputation signals trusted to be accurate.

### Invariants

1. Escrow MUST NOT be released until state = RESOLVED
2. Recovery score MUST be deterministic given on-chain state
3. Checkpoint CIDs MUST be immutable once committed
4. State transitions MUST be irreversible (no RESOLVED → RUNNING)
5. Protocol fee MUST be deducted before agent payment

---

## Copyright

Copyright (c) 2025 Maroua BOUDOUKHA. Licensed under [MPL-2.0](./LICENSE).
