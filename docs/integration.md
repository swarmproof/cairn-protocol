# CAIRN Integration Guide

> How to integrate CAIRN into your agent: checkpoint protocol, fallback pool registration, and component wrappers.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Key Design Decisions](#key-design-decisions)
3. [Checkpoint Protocol](#checkpoint-protocol)
4. [Adaptive Liveness Interval](#adaptive-liveness-interval)
5. [Fallback Pool Admission](#fallback-pool-admission)
6. [Arbiter Registration](#arbiter-registration)
7. [Component Summary](#component-summary)
8. [CairnAgent Wrapper](#cairnagent-wrapper)

---

## Quick Start

### 5-Minute Integration

1. **Install the CairnAgent wrapper** for your framework (LangGraph, Olas SDK, etc.)
2. **Register your agent's task types** in your ERC-8004 identity card
3. **Wrap your execution loop** with CAIRN's checkpoint + heartbeat nodes
4. **Deploy** — CAIRN handles failure detection, recovery, and settlement automatically

```python
from cairn import CairnAgent

# Wrap your existing agent
agent = CairnAgent(
    your_agent,
    task_types=["defi.price_fetch", "data.report_generate"],
    heartbeat_interval=60  # seconds
)

# Run with CAIRN protection
result = agent.execute(task_spec)
```

---

## Key Design Decisions

### Resume, Not Restart

The core innovation that makes recovery meaningful. Without checkpoints, a fallback agent must restart the entire task — wasting the original agent's completed work and the budget spent on it.

**Checkpoint write flow:**
```
Agent completes subtask N
→ Agent writes output to IPFS → receives CID
→ Agent calls commitCheckpoint(taskId, subtaskIndex, CID, cost)
→ CAIRN validates CID against declared output schema for subtask N
→ Valid: CID stored, cost recorded, subtask marked complete
→ Invalid: CID rejected, agent must retry
```

**Checkpoint read flow (on RECOVERING):**
```
Fallback agent receives task state:
  - checkpoint_cids: [CID_0, CID_1, CID_2, ...]  // all validated outputs
  - next_subtask_index: 3                        // resume from here
  - remaining_budget: X
  - remaining_deadline: Y
→ Fallback reads CID_2 from IPFS → gets subtask 2 output
→ Fallback begins subtask 3 using subtask 2 output as input
```

---

## Checkpoint Protocol

> ⚠️ **Centralization Note**: The default CAIRN SDK uses Pinata for IPFS pinning. While checkpoint CIDs are stored on-chain (decentralized), the actual checkpoint data depends on Pinata's availability for pinning and retrieval. For production deployments, consider running your own IPFS node or using multiple pinning services for redundancy.

### Schema Validation

The output schema for each subtask is declared by the operator at task init. CAIRN stores the schema hash. On checkpoint commit, CAIRN verifies the CID content matches the schema hash. This is deterministic — no AI, no oracle.

Agents that attempt to commit fake checkpoints are caught at validation.

### Incentive Alignment

Agents are paid proportionally to their verified checkpoint count:

```
More checkpoints written = more partial payment if failure occurs
```

This incentivizes frequent, honest checkpointing. It also means the original agent has a financial interest in writing checkpoints — not just the operator.

### Implementation

```python
async def commit_checkpoint(task_id: str, subtask_index: int, output: dict, cost: int):
    """Commit a checkpoint after completing a subtask."""

    # 1. Write output to IPFS
    cid = await ipfs.add(json.dumps(output))

    # 2. Call CAIRN contract
    tx = await cairn_task.commitCheckpoint(
        task_id,
        subtask_index,
        cid,
        cost
    )

    # 3. Wait for confirmation
    await tx.wait()

    return cid
```

---

## Adaptive Liveness Interval

A fixed heartbeat interval is incorrect. A 30-second API call and a 3-hour analysis task should not have the same liveness requirement.

### Rule

```
heartbeat_interval = operator_declared_value

subject to:
  min(heartbeat_interval) = 30 seconds (Base block time ≈ 2s → min = 15 blocks)
  max(heartbeat_interval) = task_deadline / 4
```

The interval is declared by the operator at task init and committed to the CAIRN contract. It cannot be changed during RUNNING.

### Default Calculation

If the operator does not declare an interval:

```
default_interval = min(task_deadline / 10, 300 seconds)
```

This ensures at least 10 liveness signals per task by default, with a 5-minute cap per interval.

### Implementation

```python
async def heartbeat_loop(task_id: str, interval: int):
    """Emit heartbeat signals at the configured interval."""

    while task_is_running(task_id):
        await cairn_task.heartbeat(task_id)
        await asyncio.sleep(interval)
```

---

## Fallback Pool Admission

Open registration creates a vulnerability: malicious or unreliable agents could register for all task types, accept recovery assignments, collect partial payment without completing work, and repeat.

### Two-Gate Admission

**Gate 1 — Reputation threshold:**

Agent must have a minimum reputation score in ERC-8004 ReputationRegistry for the declared task_type.

- Threshold is configurable by CAIRN governance
- Default: score ≥ 50 on a 0–100 scale
- 0 = new agent, 100 = extensively attested

**Gate 2 — Stake deposit:**

Agent must deposit a stake proportional to the maximum escrow value it is eligible to take.

```
min_stake = max_eligible_escrow × 0.1
```

If the fallback agent accepts a recovery assignment and fails without completing any checkpoints, the full stake is slashed and distributed to the operator.

### Registration

```python
async def register_as_fallback(task_types: list[str], stake_amount: int):
    """Register as a fallback agent for specified task types."""

    # 1. Deposit stake
    await cairn_task.depositStake(stake_amount)

    # 2. Register task types in ERC-8004 identity
    await identity_registry.updateServices({
        "cairn_task_types": task_types,
        "cairn_admission_stake": stake_amount
    })
```

---

## Arbiter Registration

The arbiter role in DISPUTED must be trustless, permissionless, and resistant to Sybil attacks — without a DAO and without centralization.

### Arbiter Design

The arbiter role is itself an agent service. Arbiter agents register in CAIRN with a stake. They read public execution records. They call `rule(taskId, outcome)`. They earn fees.

### Sybil Resistance

Arbiter registration requires a stake proportional to the maximum dispute value the arbiter is eligible to rule on:

```
min_arbiter_stake = max_ruleable_dispute_value × 0.2
```

A bad arbiter who rules incorrectly (detectable by the on-chain execution record evidence) loses stake. This makes collusion expensive at scale.

### Timeout Mechanism

If no arbiter rules within `dispute_timeout` blocks, the escrow auto-refunds to the operator. This prevents funds from being locked indefinitely.

- Default `dispute_timeout` = 7 days (in blocks)
- Configurable by governance

### Arbiter Fee

```
arbiter_fee = dispute_escrow_value × 0.03  // 3% of dispute value
```

---

## Component Summary

### CairnTask.sol

The state machine contract. Deployed on Base. ~250 lines of Solidity.

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
- CairnTask is set as the ERC-8183 job evaluator

### RecoveryOrchestrator

Off-chain component. ~150 lines Python.

- Listens for `TaskFailed` events with `score ≥ 0.3`
- Queries Bonfires API for best fallback agent by `task_type`
- Queries Olas Mech Marketplace for agent availability
- Calls `assignFallback(taskId, fallbackAgentId)` on CairnTask

### BonfiresAdapter

Event listener + writer. ~100 lines Python.

- Listens for `TaskFailed` and `TaskResolved` events
- Fetches full record from IPFS using the emitted CID
- Writes structured record to Bonfires data room via API
- Enables Bonfires visualization and query without modifying the protocol

---

## CairnAgent Wrapper

LangGraph nodes. ~200 lines Python.

Six nodes added to any existing agent graph:

| Node | Purpose |
|------|---------|
| `pre_task_query` | Query intelligence layer for failure patterns + recommended agent |
| `start_task` | Initialize task, lock escrow, pre-authorize delegation |
| `heartbeat_loop` | Emit liveness signals at configured interval |
| `execute_subtask` | Run subtask with CAIRN context |
| `commit_checkpoint` | Write output to IPFS, commit CID on-chain |
| `report_cost` | Report subtask cost for escrow accounting |

### Usage

```python
from cairn.langgraph import CairnAgentWrapper

# Your existing LangGraph agent
my_agent = StateGraph(...)

# Wrap with CAIRN
cairn_agent = CairnAgentWrapper(
    my_agent,
    contract_address="0x...",
    ipfs_gateway="https://ipfs.io"
)

# Execute with full CAIRN protection
result = await cairn_agent.invoke({
    "task_type": "defi.price_fetch",
    "budget_cap": 10**16,  # 0.01 ETH
    "deadline": current_block + 1000,
    "subtasks": [...]
})
```

---

*See also: [Concepts](./concepts.md) · [Architecture](./architecture.md) · [Contracts](./contracts.md) · [Standards](./standards.md)*

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
