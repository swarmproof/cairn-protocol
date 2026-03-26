# CAIRN Protocol Whitepaper

## Agent Failure and Recovery Protocol

### Version 1.0

---

## Abstract

CAIRN is a standardized agent failure and recovery protocol. It defines the exact sequence of events that must occur when an agent fails mid-task — from detection, through classification, through fallback assignment, through settlement — without requiring any human intervention and without requiring trust between agents.

An operator initiates a task with a budget, deadline, and task type. Before the task starts, CAIRN queries the execution intelligence layer for known failure patterns on this task type and recommends the best-fit agent. The agent runs. It emits liveness signals. It writes checkpoints after each subtask. If it fails — for any reason — CAIRN detects it automatically, classifies the failure, computes a recovery score, and either assigns a fallback agent (who resumes from the last checkpoint) or routes to dispute. On resolution, escrow splits proportionally between the original and fallback agents based on verified work done. The execution record is written. The intelligence layer grows. The next agent inherits the lesson.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Protocol Overview](#2-protocol-overview)
3. [Design Philosophy](#3-design-philosophy)
4. [Key Design Decisions](#4-key-design-decisions)
5. [Execution Intelligence Layer](#5-execution-intelligence-layer)
6. [Economic Model](#6-economic-model)
7. [Governance](#7-governance)
8. [Future Work](#8-future-work)
9. [References](#9-references)

---

## 1. Introduction

### 1.1 The Broken World

The Ethereum agentic economy is generating real economic activity — $479M+ in aGDP (as of March 2026, per Olas network metrics), 45k+ active agents, 100M+ monthly transactions. But every agent is operationally isolated.

When an agent fails mid-task — because an API rate-limits at 2am UTC, a budget is exceeded, a context window overflows, or a process crashes — **nothing standard happens**. The escrow sits in an ambiguous state. The human operator may or may not find out. Another agent does not automatically take over. The work is lost.

Twenty minutes later, a different agent — same task type, same API, same conditions — fails identically. The collective cost of this ignorance compounds as the agent economy scales.

**The failure disappears. Nothing learns.**

### 1.2 The Evidence

From builder feedback and published research:

- Builders report context loss, API incompatibilities, cost spikes from loops as their top operational pain
- Multi-agent system research (MAST taxonomy, 2025) identifies 14 distinct failure modes — but classifies them by symptom, not by what to do next
- "There is no equivalent of 'save game' for AI agent workflows. If something breaks, you're restarting from scratch." — documented builder complaint
- "The lack of a standardized failure framework with clear definitions makes identifying and classifying failures across different systems inconsistent." — MAST taxonomy paper
- 85% accuracy per agent action means a 10-step workflow only succeeds ~20% of the time end-to-end — failure handling is not optional, it is the protocol

### 1.3 What Is Missing

Every team building agents today has written their own failure handling. It is bespoke, incompatible, and invisible to the rest of the ecosystem. There is:

- No standard definition of what a failure is
- No standard protocol for what happens when one is detected
- No standard mechanism for task handoff to a fallback agent
- No standard escrow settlement rule for partial completion
- No shared record of what failed, why, and what worked instead

CAIRN is the protocol that fills this gap.

---

## 2. Protocol Overview

### 2.1 The Primary Output

**CAIRN is a standardized agent failure and recovery protocol.**

It defines the exact sequence of events that must occur when an agent fails mid-task — from detection, through classification, through fallback assignment, through settlement — without requiring any human intervention and without requiring trust between agents.

### 2.2 The Secondary Output

As a byproduct of the recovery protocol running, CAIRN accumulates an **execution intelligence layer** — a shared, queryable record of every failure, every recovery, and every successful completion across the ecosystem.

This is what makes CAIRN compound in value over time. The knowledge graph grows automatically. The more agents integrate CAIRN, the richer the intelligence layer becomes. Agents query it before starting tasks. The ecosystem gets smarter from every failure.

**The knowledge graph is the byproduct. The recovery protocol is the core.**

### 2.3 What CAIRN Is NOT

- **Not a new agent framework.** CAIRN wraps any existing framework — LangGraph, Olas SDK, AgentKit, custom builds.
- **Not a knowledge graph product.** Bonfires (the visualization layer) is a window into the intelligence layer, not the protocol itself.
- **Not a centralized service.** Every state transition is enforced by the CAIRN state machine contract. No server. No admin key. No human required.
- **Not a replacement for ERC-8183 or ERC-8004.** CAIRN integrates and extends both. It is an ERC-8183 Hook and an ERC-8004 reputation writer.
- **Not optional infrastructure.** The escrow condition makes record-writing mandatory — agents cannot receive payment without completing the protocol.

---

## 3. Design Philosophy

### 3.1 Why Recoverability, Not Symptom

Prior research identifies 14+ failure modes in multi-agent systems but most taxonomies describe surface symptoms ("step repetition") without prescribing what to do next. CAIRN's classification directly determines protocol behavior.

- **Liveness failures are almost always recoverable.** The agent stopped — not because the task is impossible, but because the agent crashed. A fallback can pick up exactly where it left off via the checkpoint list. Recovery score = HIGH.

- **Resource failures are partially recoverable.** The task may still be completable if the fallback operates more efficiently or if the remaining budget is sufficient. Recovery score = MEDIUM. Context depends on how much headroom remains.

- **Logic failures are rarely recoverable.** If the agent was reasoning incorrectly, a fallback with the same task spec will likely fail the same way. Assigning a fallback wastes more budget. Recovery score = LOW. Route to DISPUTED.

### 3.2 Resume, Not Restart

The core innovation that makes recovery meaningful. Without checkpoints, a fallback agent must restart the entire task — wasting the original agent's completed work and the budget spent on it.

Checkpoints solve this by committing verified work after each subtask. On recovery, the fallback agent reads the checkpoint list and resumes from the last verified output. No restart from zero. The fallback inherits exactly what the original completed.

### 3.3 Permissionless Enforcement

All enforce functions (`checkLiveness`, `checkBudget`, `checkDeadline`) are public. Anyone can call them. No trusted keeper required.

This makes the protocol permissionless — any agent in the ecosystem can enforce liveness on any task. The enforce function only succeeds if the condition is actually violated. False calls revert.

### 3.4 Escrow as Forcing Function

The escrow condition is the forcing function that bootstraps participation without relying on altruism. Agents cannot receive payment without completing the protocol — including writing the execution record.

Network effect:
```
More agents writing records
  → Richer intelligence layer
    → More accurate fallback selection
      → Higher recovery success rate
        → More agents integrating CAIRN
          → More agents writing records
```

The loop starts from day one.

---

## 4. Key Design Decisions

### 4.1 Checkpoint Protocol — Resume, Not Restart

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
  - next_subtask_index: 3                          // resume from here
  - remaining_budget: X
  - remaining_deadline: Y
→ Fallback reads CID_2 from IPFS → gets subtask 2 output
→ Fallback begins subtask 3 using subtask 2 output as input
```

**Schema validation:** The output schema for each subtask is declared by the operator at task init. CAIRN stores the schema hash. On checkpoint commit, CAIRN verifies the CID content matches the schema hash. This is deterministic — no AI, no oracle. Agents that attempt to commit fake checkpoints are caught at validation.

**Incentive alignment:** Agents are paid proportionally to their verified checkpoint count. More checkpoints written = more partial payment if failure occurs. This incentivizes frequent, honest checkpointing. It also means the original agent has a financial interest in writing checkpoints — not just the operator.

### 4.2 Task Type Taxonomy — The Routing Key

Every routing decision in CAIRN depends on `task_type`. The taxonomy must be:
- Specific enough to enable meaningful fallback matching
- General enough to accumulate sufficient signal per type
- Open enough to accommodate new agent capabilities

**Structure:**
```
task_type = {
  domain: "defi" | "data" | "governance" | "compute" | "social" | "storage",
  operation: string  // e.g., "price_fetch", "trade_execute", "vote_delegate"
}
```

**Serialized as:** `domain.operation` (e.g., `defi.price_fetch`)

**Registration:** Agents declare supported task types in their ERC-8004 identity card `services` array:
```json
{
  "cairn_task_types": ["defi.price_fetch", "defi.trade_execute"],
  "cairn_admission_stake": "0.01 ETH"
}
```

**Fallback matching precedence:**
1. Exact match on `domain.operation` + highest reputation + available stake
2. Domain match only (any operation in the same domain) + highest reputation
3. No match → DISPUTED immediately (no appropriate fallback in pool)

### 4.3 Adaptive Liveness Interval

A fixed heartbeat interval is incorrect. A 30-second API call and a 3-hour analysis task should not have the same liveness requirement.

**Rule:**
```
heartbeat_interval = operator_declared_value
subject to:
  min(heartbeat_interval) = 30 seconds (Base block time ≈ 2s → min = 15 blocks)
  max(heartbeat_interval) = task_deadline / 4
```

The interval is declared by the operator at task init and committed to the CAIRN contract. It cannot be changed during RUNNING. If the operator does not declare an interval, CAIRN uses the default:

```
default_interval = min(task_deadline / 10, 300 seconds)
```

This ensures at least 10 liveness signals per task by default, with a 5-minute cap per interval.

### 4.4 Fallback Pool Admission Control

Open registration creates a vulnerability: malicious or unreliable agents could register for all task types, accept recovery assignments, collect partial payment without completing work, and repeat.

**Two-gate admission:**

**Gate 1 — Reputation threshold:** Agent must have a minimum reputation score in ERC-8004 ReputationRegistry for the declared task_type. Threshold is configurable by CAIRN governance. Default: score ≥ 50 on a 0–100 scale where 0 is new and 100 is extensively attested.

**Gate 2 — Stake deposit:** Agent must deposit a stake proportional to the maximum escrow value it is eligible to take. Default formula:
```
min_stake = max_eligible_escrow × 0.1
```
If the fallback agent accepts a recovery assignment and fails without completing any checkpoints, the full stake is slashed and distributed to the operator. This creates a direct economic incentive for fallback agents to only accept assignments they are confident they can complete.

### 4.5 Arbiter Design — Dispute Resolution as Agent Service

The arbiter role in DISPUTED must be trustless, permissionless, and resistant to Sybil attacks — without a DAO and without centralization.

**CAIRN's solution:** The arbiter role is itself an agent service. Arbiter agents register in CAIRN with a stake. They read public execution records. They call `rule(taskId, outcome)`. They earn fees. The market for arbitration emerges naturally.

**Sybil resistance:** Arbiter registration requires a stake proportional to the maximum dispute value the arbiter is eligible to rule on:
```
min_arbiter_stake = max_ruleable_dispute_value × 0.2
```

A bad arbiter who rules incorrectly (detectable by the on-chain execution record evidence) loses stake. This makes collusion expensive at scale.

**Timeout mechanism:** If no arbiter rules within `dispute_timeout` blocks, the escrow auto-refunds to the operator. This prevents funds from being locked indefinitely. Default `dispute_timeout` = 7 days (in blocks). Configurable.

---

## 5. Execution Intelligence Layer

### 5.1 What It Is

The execution intelligence layer is the **secondary output** of CAIRN. It is not the core. It is what accumulates automatically as the recovery protocol runs — without human curation, without a central server, without any agent opting in separately (writing to the intelligence layer is mandatory for escrow settlement).

### 5.2 What Gets Written

**On FAILED** — Failure Record written to IPFS, CID emitted on-chain:
```json
{
  "record_type": "failure",
  "task_id": "0x...",
  "agent_id": "erc8004://base/0x...",
  "task_type": "defi.price_fetch",
  "failure_class": "RESOURCE",
  "failure_type": "RATE_LIMIT",
  "checkpoint_count_at_failure": 3,
  "cost_at_failure": "0.0023 ETH",
  "budget_remaining_pct": 0.42,
  "deadline_remaining_pct": 0.31,
  "recovery_score": 0.71,
  "block_number": 18492031,
  "timestamp": 1742000000,
  "api_endpoint": "api.coingecko.com",
  "error_code": "429"
}
```

**On RESOLVED** — Resolution Record written to IPFS, CID emitted on-chain:
```json
{
  "record_type": "resolution",
  "task_id": "0x...",
  "states_traversed": ["RUNNING", "FAILED", "RECOVERING", "RESOLVED"],
  "original_agent_id": "erc8004://base/0x...",
  "fallback_agent_id": "erc8004://base/0x...",
  "task_type": "defi.price_fetch",
  "total_cost": "0.0041 ETH",
  "total_duration_blocks": 847,
  "original_checkpoint_count": 3,
  "fallback_checkpoint_count": 2,
  "escrow_split": {
    "original_agent": "0.0024 ETH",
    "fallback_agent": "0.0016 ETH",
    "protocol_fee": "0.00002 ETH"
  },
  "failure_record_cid": "Qm...",
  "block_number": 18493012,
  "timestamp": 1742001700
}
```

### 5.3 What Agents Query (A2 — Pre-Task Intelligence)

Before confirming a task, CAIRN queries the intelligence layer by `task_type`:

| Query | What It Returns | How It Helps |
|---|---|---|
| Known failure patterns | List of failure types recorded for this task_type, sorted by frequency | Operator sees what has gone wrong before. Agent can pre-configure to avoid. |
| Cost distribution | P25, P50, P75, P95 of total cost per execution | Operator can set a realistic `budget_cap`. Prevents under-budgeting. |
| Recommended agent | Agents with highest success rate + reputation for this task_type | Starting with the best available agent reduces failure probability. |
| Known-bad conditions | Time windows or API conditions correlated with failures | Agent can avoid scheduling during high-risk windows. |
| Recovery success rate | % of failures that resolved via recovery for this task_type | Operator understands risk profile before committing. |

### 5.4 What Agents Query (A9 — Fallback Selection)

On recovery, CAIRN queries the intelligence layer for the best fallback:

```
Input: task_type, remaining_budget, remaining_deadline
Query: agents registered for task_type, sorted by:
  1. Success rate on this exact task_type (from Resolution Records)
  2. ERC-8004 reputation score
  3. Stake deposited (higher stake = more skin in game)
  4. Current availability (not already assigned to another task)
Filter: admission threshold (min rep score + active stake)
Output: ranked list of eligible fallback agents
```

### 5.5 The Bonfires Role

Bonfires is the **visualization and query interface** for the intelligence layer. It is:

- **Not** the storage layer (IPFS + The Graph handles storage and indexing)
- **Not** the protocol core (CairnTask.sol handles all state transitions)
- **Load-bearing** in A2 (failure pattern query) and A9 (fallback selection routing)
- **Valuable** as the interface humans use to inspect the health of the agent ecosystem

The BonfiresAdapter is a small event listener that watches for `TaskFailed` and `TaskResolved` events on-chain and writes the full record (fetched from IPFS) into a Bonfires data room. Bonfires then provides:

1. A queryable knowledge graph API (used by A2 and A9)
2. A visual data room that humans can inspect
3. A "hyperblog" of the agent ecosystem's failure and recovery history

The knowledge graph in Bonfires is built entirely by agent activity — no human writes to it.

### 5.6 Network Effects

The execution history cannot be forked. A competitor can copy the schema. They cannot copy the accumulated records.

Network effect:
```
More agents writing records
  → Richer intelligence layer
    → More accurate fallback selection
      → Higher recovery success rate
        → More agents integrating CAIRN
          → More agents writing records
```

The escrow condition is the forcing function that bootstraps this loop without relying on altruism. Agents cannot receive payment without writing the record. The loop starts from day one.

---

## 6. Economic Model

### 6.1 Escrow Split Rule

On RESOLVED, escrow is distributed proportionally to verified work:

```
original_agent_share = (original_checkpoint_count / total_checkpoint_count) × escrow_amount × (1 - protocol_fee)
fallback_agent_share = (fallback_checkpoint_count / total_checkpoint_count) × escrow_amount × (1 - protocol_fee)
protocol_fee = 0.5% (configurable by governance)
```

If no recovery occurred (original agent completed solo): 100% to original agent minus protocol fee.

### 6.2 Protocol Fee

- Default: 0.5% of escrow on settlement
- Collected on every RESOLVED state transition
- Configurable by governance (range: 0-5%)
- Funds protocol development and maintenance

### 6.3 Fallback Stake Requirements

| Parameter | Formula | Default |
|-----------|---------|---------|
| Minimum stake | `max_eligible_escrow × stake_pct` | 10% |
| Slash on failure | Full stake | 100% of stake |
| Slash recipient | Operator | - |

### 6.4 Arbiter Economics

| Parameter | Formula | Default |
|-----------|---------|---------|
| Minimum stake | `max_ruleable_dispute × stake_pct` | 15% |
| Ruling fee | `dispute_value × fee_pct` | 3% |
| Timeout | Blocks | 7 days (~302,400 blocks on Base) |

### 6.5 Recovery Score Formula

```
recovery_score = (failure_class_weight × 0.5) + (budget_remaining_pct × 0.3) + (deadline_remaining_pct × 0.2)
```

Where:
- `failure_class_weight`: Liveness = 0.9 | Resource = 0.5 | Logic = 0.1
- `budget_remaining_pct`: (budget_cap - cost_accrued) / budget_cap
- `deadline_remaining_pct`: (deadline - current_block) / (deadline - start_block)

Routing:
- `score ≥ 0.6` → RECOVERING
- `0.3 ≤ score < 0.6` → PARTIAL (attempt recovery with reduced budget)
- `score < 0.3` → DISPUTED

---

## 7. Governance

### 7.1 Configurable Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Protocol fee | 0.5% | 0-5% | Fee on escrow settlement |
| Fallback min reputation | 50/100 | 0-100 | Minimum rep score for fallback pool |
| Fallback min stake | 10% | 1-50% | Stake as % of max eligible escrow |
| Arbiter min stake | 15% | 5-50% | Stake as % of max ruleable dispute |
| Arbiter fee | 3% | 1-10% | Fee as % of dispute value |
| Arbiter timeout | 7 days | 1-30 days | Time for arbiter to rule |
| Recovery threshold | 0.6 | 0.3-0.9 | Score threshold for RECOVERING |

### 7.2 Governance Model

**Phase 1: Admin Key (Launch)**
- Single owner address controls all parameters
- Required for rapid iteration during early deployment
- Upgrade path defined before launch

**Phase 2: Multi-Sig**
- 3-of-5 multi-sig controls parameters
- 48-hour timelock for parameter changes
- Public proposal and review period

**Phase 3: Token Governance (Future)**
- If applicable, governance token enables community control
- Parameters changeable via on-chain voting
- Emergency multi-sig retained for security issues

### 7.3 Upgrade Path

- CairnTask.sol is designed to be non-upgradeable for security
- New versions deployed as new contracts
- Migration: new tasks use new version; in-flight tasks complete under original version
- No forced migration of existing tasks

### 7.4 Task Type Registry

**v1 (Launch):** Hardcoded task types:
- `defi.price_fetch`
- `defi.trade_execute`
- `data.report_generate`
- `governance.vote_delegate`
- `compute.model_inference`
- `storage.file_manage`

**v2 (Post-launch):** Open registry with governance approval:
1. Proposer calls `proposeTaskType(domain, operation, schemaURI)`
2. Governance review period (7 days)
3. Approval/rejection vote
4. On approval, task type is immutable

---

## 8. Future Work

### 8.1 Open Questions

**Task Type Registry**

The `task_type` taxonomy needs a canonical registry to prevent fragmentation. If any agent can declare any `task_type` string, the graph becomes ungroupable.

*Proposed resolution:* Deploy a `CairnTaskTypeRegistry` contract with governance-controlled registration.

**Checkpoint Schema Validation**

Schema validation must be deterministic and gas-efficient on-chain.

*Proposed resolution:* Schema hashes (keccak256 of JSON schema bytes) stored per subtask. Off-chain validators verify content. Full on-chain validation deferred to v2.

**Fallback Admission Thresholds**

What minimum reputation score and stake formula optimizes for quality without excluding new agents?

*Proposed resolution:* Start conservative (50/100 rep, 10% stake). Adjust based on observed behavior.

**Arbiter Stake Formula**

Arbiter stake must scale with dispute value to prevent Sybil attacks but not exclude participation.

*Proposed resolution:* 15% stake requirement, 3% fee. Evaluate after launch.

**Execution Record Schema Lock**

Schemas must be locked before BonfiresAdapter can write consistently. Schema changes break existing queries.

*Proposed resolution:* Version schemas (`failure-record-v1`). Migration is a governance event.

### 8.2 ERC Standardization

CAIRN is designed to become an Ethereum standard. The specification in [ERC-CAIRN.md](./ERC-CAIRN.md) follows the EIP-1 format.

**Working title:** `ERC-CAIRN: Agent Failure and Recovery Standard`

**Relationship to existing ERCs:**
- Extends ERC-8183 via the Hook mechanism — CAIRN is an ERC-8183 Hook
- Integrates ERC-8004 Identity Registry (agent IDs), Reputation Registry (outcome signals), and Validation Registry (checkpoint attestations)
- Compatible with ERC-7710 delegation framework for scoped permission transfer

---

## 9. References

1. MAST Taxonomy (2025) — Multi-Agent System Failure Modes
2. ERC-8183 — Agentic Commerce Standard
3. ERC-8004 — Trustless Agents Standard
4. ERC-7710 — Delegation Framework
5. Olas Network — Mech Marketplace

---

*CAIRN — Agent Failure and Recovery Protocol*
*Whitepaper v1.0*
*Agents learn together.*
