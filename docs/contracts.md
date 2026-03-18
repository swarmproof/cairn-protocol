# CAIRN Contracts Reference

> Solidity interfaces, data schemas, events, and deployment information.

---

> **Note: Full Protocol vs MVP**
>
> This document describes the **full protocol vision** (PRD-00). The current **MVP implementation** (PRD-01) is simplified:
>
> | Feature | Full Protocol | MVP |
> |---------|---------------|-----|
> | States | 6 (IDLE, RUNNING, FAILED, RECOVERING, RESOLVED, DISPUTED) | 4 (RUNNING, FAILED, RECOVERING, RESOLVED) |
> | Failure Classification | FailureClass enum | Not implemented |
> | Arbiter | Full dispute resolution | Deferred to PRD-05 |
> | Recovery Score | Computed on-chain | Deferred to PRD-02 |
> | Schema Validation | Hash-based | CID storage only |
>
> See `contracts/src/interfaces/ICairnTaskMVP.sol` for the current MVP interface.

---

## Table of Contents

1. [Contract Interface](#contract-interface)
2. [Data Schemas](#data-schemas)
3. [Events](#events)
4. [CairnHook Interface](#cairnhook-interface)

---

## Contract Interface

The canonical interface every external system interacts with. This interface is what needs to be deployed.

```solidity
// SPDX-License-Identifier: MIT
// CAIRN — Agent Failure and Recovery Protocol
// CairnTask.sol — canonical interface

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
        bytes32     taskType;           // keccak256("domain.operation")
        uint256     budgetCap;          // wei
        uint256     deadline;           // block number
        uint256     heartbeatInterval;  // blocks
        uint256     subtaskCount;
        bytes32[]   subtaskSchemaHashes; // keccak256 of each subtask output schema
        string      descriptionCID;     // IPFS CID of task description
    }

    struct Task {
        address     operator;
        address     agentId;            // ERC-8004 NFT address
        TaskState   state;
        bytes32     taskType;
        uint256     budgetCap;
        uint256     costAccrued;
        uint256     deadline;
        uint256     heartbeatInterval;
        uint256     lastHeartbeat;      // block number
        uint256     startBlock;
        uint256     subtaskCount;
        uint256     completedSubtasks;
        address     fallbackAgentId;
        uint256     fallbackSubtasks;
        string[]    checkpointCIDs;     // one per completed subtask
        string      failureRecordCID;
        string      resolutionRecordCID;
    }

    // ── Write Methods ────────────────────────────────────────────────────────

    /// @notice Operator initiates task. Locks escrow. Returns taskId.
    function startTask(TaskSpec calldata spec, address agentId)
        external payable returns (bytes32 taskId);

    /// @notice Agent emits liveness signal. Must be called within heartbeatInterval blocks.
    function heartbeat(bytes32 taskId) external;

    /// @notice Agent commits completed subtask checkpoint. CID validated against schema hash.
    function commitCheckpoint(bytes32 taskId, uint256 subtaskIndex, string calldata cid, uint256 cost)
        external;

    /// @notice Agent signals task complete. Triggers RESOLVED if all subtasks committed.
    function completeTask(bytes32 taskId) external;

    /// @notice Public enforce function — anyone can call, no trust required.
    /// @dev Triggers FAILED if heartbeat missed
    function checkLiveness(bytes32 taskId) external;

    /// @notice Public enforce function — triggers FAILED if budget_cap exceeded
    function checkBudget(bytes32 taskId) external;

    /// @notice Public enforce function — triggers FAILED if deadline passed
    function checkDeadline(bytes32 taskId) external;

    /// @notice Recovery orchestrator assigns fallback agent (after querying Olas + Bonfires off-chain).
    function assignFallback(bytes32 taskId, address fallbackAgentId) external;

    /// @notice Arbiter submits ruling on disputed task.
    /// @param outcome 0=refund, 1=original, 2=split
    function rule(bytes32 taskId, uint8 outcome) external;

    // ── Read Methods ─────────────────────────────────────────────────────────

    function getTask(bytes32 taskId) external view returns (Task memory);
    function getCheckpoints(bytes32 taskId) external view returns (string[] memory);
    function getRecoveryScore(bytes32 taskId) external view returns (uint256); // scaled 0–1000
    function isArbiterEligible(address arbiter, bytes32 taskId) external view returns (bool);
}
```

---

## Data Schemas

### Task Specification (Input to startTask)

```typescript
interface TaskSpec {
  task_type: string;              // "domain.operation" format
  budget_cap: bigint;             // in wei
  deadline: number;               // block number
  heartbeat_interval?: number;    // blocks (optional, defaults computed)
  subtask_count: number;          // total subtasks declared
  subtask_schemas: SubtaskSchema[]; // output schema per subtask
  description: string;            // human-readable task description
  output_format: string;          // IPFS CID of JSON schema for final output
}

interface SubtaskSchema {
  index: number;
  description: string;
  output_schema_cid: string;     // IPFS CID of JSON schema for this subtask output
}
```

### Checkpoint Commit (Input to commitCheckpoint)

```typescript
interface CheckpointCommit {
  task_id: bytes32;
  subtask_index: number;
  output_cid: string;            // IPFS CID of subtask output
  cost_wei: bigint;              // cost of this subtask
}
```

### Failure Record (Written on FAILED)

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
  "timestamp": "uint",
  "api_endpoint": "string | null",
  "error_code": "string | null",
  "error_message": "string | null"
}
```

### Resolution Record (Written on RESOLVED)

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

---

## Events

All state transitions emit events that can be indexed by The Graph and consumed by the BonfiresAdapter.

```solidity
// Task lifecycle events
event TaskStarted(
    bytes32 indexed taskId,
    address indexed agentId,
    bytes32 taskType
);

event CheckpointCommitted(
    bytes32 indexed taskId,
    uint256 subtaskIndex,
    string cid,
    uint256 cost
);

event TaskFailed(
    bytes32 indexed taskId,
    string recordCID,
    uint256 recoveryScore,
    FailureClass failureClass
);

event FallbackAssigned(
    bytes32 indexed taskId,
    address fallbackAgentId
);

event TaskResolved(
    bytes32 indexed taskId,
    string recordCID,
    uint256 originalShare,
    uint256 fallbackShare
);

event TaskDisputed(
    bytes32 indexed taskId,
    string recordCID,
    uint256 arbiterTimeout
);

event TaskRefunded(
    bytes32 indexed taskId,
    uint256 refundAmount
);

event ArbiterRuled(
    bytes32 indexed taskId,
    address arbiter,
    uint8 outcome
);
```

---

## CairnHook Interface

CairnHook.sol implements the ERC-8183 hook interface. CairnTask is set as the ERC-8183 `evaluator` address when the job is created. CairnHook delegates to CairnTask.

```solidity
interface ICairnHook {
    /// @notice Called by ERC-8183 job contract before funding
    function beforeFund(bytes32 jobId, bytes calldata params) external;

    /// @notice Called by ERC-8183 job contract after funding
    function afterFund(bytes32 jobId, bytes calldata params) external;

    /// @notice Called by ERC-8183 job contract before completion
    function beforeComplete(bytes32 jobId, bytes calldata params) external;

    /// @notice Called by ERC-8183 job contract after completion
    function afterComplete(bytes32 jobId, bytes calldata params) external;

    /// @notice Called by ERC-8183 job contract before rejection
    function beforeReject(bytes32 jobId, bytes calldata params) external;

    /// @notice Called by ERC-8183 job contract after rejection
    function afterReject(bytes32 jobId, bytes calldata params) external;
}
```

---

## Protocol Constants

| Constant | Default Value | Configurable |
|----------|---------------|--------------|
| `MIN_HEARTBEAT_INTERVAL` | 30 seconds (15 blocks) | No |
| `PROTOCOL_FEE` | 0.5% | Yes (governance) |
| `MIN_REPUTATION_THRESHOLD` | 50/100 | Yes (governance) |
| `MIN_FALLBACK_STAKE_RATIO` | 10% of max escrow | Yes (governance) |
| `MIN_ARBITER_STAKE_RATIO` | 20% of max dispute | Yes (governance) |
| `ARBITER_FEE` | 3% of dispute value | Yes (governance) |
| `DISPUTE_TIMEOUT` | 7 days (~302,400 blocks) | Yes (governance) |

---

*See also: [Concepts](./concepts.md) · [Architecture](./architecture.md) · [Integration](./integration.md) · [Standards](./standards.md)*
