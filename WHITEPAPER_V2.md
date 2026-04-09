# CAIRN Protocol Whitepaper

## Agent Failure and Recovery Protocol

### Version 2.0 — April 2026

> **Copyright 2026 Maroua BOUDOUKHA. All rights reserved.**
>
> This document may be cited for academic and research purposes with proper attribution:
> BOUDOUKHA, M. (2026). *CAIRN Protocol: Agent Failure and Recovery Protocol*. Whitepaper v2.0, April 2026.
>
> Redistribution or commercial use requires written permission from the author.
>
> **Contact:** github.com/MarouaBoud

---

## Abstract

AI agent task completion rates remain at approximately 50% across popular frameworks, yet no standardized protocol exists for failure detection, classification, and recovery in the on-chain agent economy. We present CAIRN, the first protocol to classify agent failures by **recoverability** rather than symptom, enabling deterministic routing to checkpoint-based recovery or dispute resolution.

CAIRN defines a 6-state machine with three-tier recovery routing, enforced by smart contracts: when an agent fails mid-task, the protocol detects the failure via missed heartbeats or resource exhaustion, classifies it into one of three recoverability classes (LIVENESS, RESOURCE, LOGIC), computes a recovery score, and routes the task to either a qualified fallback agent who resumes from the last IPFS-committed checkpoint, or to dispute resolution. Escrow is settled proportionally to verified work. We prove escrow safety, termination, and state determinism, and show that honest checkpointing is the dominant strategy under realistic economic parameters.

Our key insight is that **economic enforcement** — escrow-conditioned record writing — bootstraps a collective intelligence layer without requiring altruistic participation. Every failure becomes a queryable record. Every recovery teaches the next agent. The accumulated execution history creates a network effect that cannot be forked.

CAIRN integrates three Ethereum standards: ERC-8004 for agent identity and reputation, ERC-8183 for job escrow lifecycle, and ERC-7710 for scoped delegation. It is deployed on Base and composable with existing agent frameworks (LangGraph, Olas, CrewAI, AutoGen) and emerging coordination protocols (Google A2A, Anthropic MCP).

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Protocol Specification](#2-protocol-specification)
3. [Design Philosophy](#3-design-philosophy)
4. [Key Design Decisions](#4-key-design-decisions)
5. [Execution Intelligence Layer](#5-execution-intelligence-layer)
6. [Economic Model](#6-economic-model)
7. [Security Model](#7-security-model)
8. [Governance](#8-governance)
9. [Related Work](#9-related-work)
10. [Future Work](#10-future-work)
11. [References](#11-references)

---

## 1. Introduction

### 1.1 The Problem

The Ethereum agentic economy generates significant economic activity — over 10 million agent-to-agent transactions on the Olas network alone [5], 85,000+ registered agent identities via ERC-8004 across 18 EVM chains [14], and growing on-chain commerce via ERC-8183 [15]. But every agent is operationally isolated.

When an agent fails mid-task — because an API rate-limits, a budget is exceeded, a context window overflows, or a process crashes — **nothing standard happens**. The escrow sits in an ambiguous state. The human operator may or may not discover the failure. Another agent does not automatically take over. Completed work is lost.

Twenty minutes later, a different agent — same task type, same API, same conditions — fails identically. The collective cost compounds as the agent economy scales.

### 1.2 The Evidence

Published research establishes agent failure as a systemic problem, not an edge case:

- Multi-agent benchmarks show an **average task completion rate of approximately 50%** across popular frameworks including AutoGPT, MetaGPT, and ChatDev [3]. At 85% per-action accuracy, a 10-step workflow succeeds only ~20% of the time (0.85^10 = 0.197).

- The MAST taxonomy identifies **14 distinct failure modes** across 1,600+ annotated traces from 7 multi-agent frameworks [1]. However, MAST classifies failures by symptom (step repetition, incorrect tool selection) — not by what recovery action to take.

- Research on AI agent reliability finds that **predictability is the weakest dimension** of current agents — agents cannot reliably determine when they are wrong [2]. This validates the need for external failure detection infrastructure rather than relying on agent self-diagnosis.

- A systematic survey of 317 publications on autonomous agents and blockchains identifies **missing interface layers and verifiable policy enforcement** as key gaps [6] — precisely the gaps CAIRN addresses.

- ISO/IEC TR 5469 notes that "highly autonomous systems likely fall into a risk category where current methods are insufficient to adequately mitigate reliability-related risks" [7].

### 1.3 What Is Missing

Every team building agents has written bespoke, incompatible failure handling. There is:

- No standard definition of what an agent failure is
- No standard protocol for what happens when one is detected
- No standard mechanism for task handoff to a fallback agent
- No standard escrow settlement rule for partial completion
- No shared record of what failed, why, and what worked instead

CAIRN fills this gap.

---

## 2. Protocol Specification

### 2.1 Overview

CAIRN is a standardized agent failure and recovery protocol. It defines the exact sequence of events that occur when an agent fails mid-task — from detection, through classification, through fallback assignment, through settlement — without requiring human intervention and without requiring trust between agents.

As a byproduct, CAIRN accumulates an **execution intelligence layer**: a shared, queryable record of every failure, recovery, and completion across the ecosystem. The intelligence layer grows automatically because record-writing is mandatory for escrow settlement.

**Formal Definition.** A CAIRN task is a tuple *T* = (*id*, *σ*, *A*<sub>p</sub>, *A*<sub>f</sub>, *E*, *δ*, *H*, *c*<sub>p</sub>, *c*<sub>f</sub>, *κ*, *t*<sub>0</sub>) where:

| Symbol | Type | Description |
|--------|------|-------------|
| *id* | bytes32 | Unique task identifier: keccak256(operator, nonce, block.timestamp) |
| *σ* | enum | Current state ∈ {IDLE, RUNNING, FAILED, RECOVERING, DISPUTED, RESOLVED} |
| *A*<sub>p</sub>, *A*<sub>f</sub> | address | Primary and fallback agent addresses |
| *E* | uint256 | Escrow amount in wei, *E* ≥ *E*<sub>min</sub> = 10<sup>15</sup> (0.001 ETH) |
| *δ* | uint256 | Deadline as block timestamp |
| *H* | uint256 | Heartbeat interval in seconds, 30 ≤ *H* ≤ *δ*/4 |
| *c*<sub>p</sub>, *c*<sub>f</sub> | uint256 | Checkpoint counts for primary and fallback agents |
| *κ* | uint256 | Cost accrued in wei |
| *t*<sub>0</sub> | uint256 | Task start block timestamp |

### 2.2 State Machine

Six states. Every transition is deterministic. No human is required to trigger any state change.

```
                    ┌──────────────────────────────────────────────────┐
                    │               CAIRN State Machine                │
                    └──────────────────────────────────────────────────┘

    ┌──────┐  confirm   ┌─────────┐   task done   ┌──────────┐
    │      │ ─────────► │         │ ─────────────► │          │
    │ IDLE │            │ RUNNING │                │ RESOLVED │ (terminal)
    │      │            │         │                │          │
    └──────┘            └────┬────┘                └────▲─────┘
                             │                          │
                    fault    │                          │ complete
                  detected   │                          │
                             ▼                          │
                        ┌─────────┐   score ≥ 0.3  ┌───┴──────┐
                        │         │ ──────────────► │          │
                        │ FAILED  │   (≥0.6 full   │RECOVERING│
                        │         │ ◄──0.3-0.6──── │ (full or │
                        └────┬────┘  reduced scope) │ reduced) │
                             │       or fallback    └──────────┘
                      score  │       fails
                      < 0.3  │
                             ▼
                        ┌──────────┐  arbiter   ┌──────────┐
                        │          │ ──────────► │          │
                        │ DISPUTED │             │ RESOLVED │ (terminal)
                        │          │  timeout    │          │
                        └──────────┘ ──────────► └──────────┘
                                      refund
```

**State Definitions:**

| State | Entry Trigger | Actions | Exit Conditions |
|-------|---------------|---------|-----------------|
| **IDLE** | Operator submits task | Query intelligence layer; lock escrow; pre-authorize delegation | Operator confirms → RUNNING |
| **RUNNING** | Operator confirmation | Agent executes subtasks; writes checkpoints; emits heartbeats | Success → RESOLVED; Fault → FAILED |
| **FAILED** | Liveness miss, budget hit, or deadline exceeded | Classify failure; compute recovery score; write failure record | Score ≥ 0.3 → RECOVERING (full or reduced scope); Score < 0.3 → DISPUTED |
| **RECOVERING** | Recovery score ≥ 0.3 | Select fallback; transfer checkpoint state; fallback resumes (full or reduced scope) | Success → RESOLVED; Failure → DISPUTED |
| **DISPUTED** | Score < 0.3 or fallback failure | Hold escrow; expose evidence; start arbiter timeout | Arbiter ruling → RESOLVED; Timeout → auto-refund |
| **RESOLVED** | Completion or ruling | Settle escrow proportionally; write resolution record; update reputation | Terminal |

### 2.2.1 Formal Properties

**Transition Function.** The state transition function *τ*: *S* × *Event* → *S* is defined as:

| Current State | Event | Condition | Next State |
|---------------|-------|-----------|------------|
| IDLE | Confirm | Operator signs confirmation | RUNNING |
| RUNNING | Complete | All subtasks verified | RESOLVED |
| RUNNING | HeartbeatMiss | block.timestamp > lastHeartbeat + *H* | FAILED |
| RUNNING | BudgetExceeded | *κ* ≥ *E* | FAILED |
| RUNNING | DeadlineExceeded | block.timestamp ≥ *δ* | FAILED |
| FAILED | RecoveryRoute | *r* ≥ 0.3 | RECOVERING |
| FAILED | RecoveryRoute | *r* < 0.3 | DISPUTED |
| RECOVERING | Complete | Fallback completes remaining subtasks | RESOLVED |
| RECOVERING | FallbackFailed | Fallback fails or deadline exceeded | DISPUTED |
| DISPUTED | ArbiterRuling | Arbiter submits valid ruling | RESOLVED |
| DISPUTED | Timeout | block.timestamp ≥ *t*<sub>dispute</sub> + *D*<sub>timeout</sub> | RESOLVED (refund) |

All (*σ*, *event*) pairs not listed above are undefined; the transaction reverts.

**Theorem 1 (Escrow Safety).** *For any task T, escrow E is not distributed until σ = RESOLVED.*

*Proof.* The settlement function `settle(taskId)` contains the precondition `require(task.state == RESOLVED)`. No other function in the protocol transfers escrow from the task's balance. By Theorem 3 (Irreversibility), once a task leaves RESOLVED... it cannot — RESOLVED is terminal with no outgoing transitions. Therefore, escrow *E* remains locked in all non-terminal states. ∎

**Theorem 2 (Termination).** *Every task T reaches σ = RESOLVED within at most δ − t₀ + D<sub>timeout</sub> seconds.*

*Proof.* We show each non-terminal state has a bounded exit:
- **IDLE**: Operator confirms or deadline passes. Bounded by *δ* − *t*<sub>0</sub>.
- **RUNNING**: Either completes (→ RESOLVED) or a fault triggers (heartbeat miss at *t* > lastHeartbeat + *H*, or deadline *δ* reached). Maximum duration: *δ* − *t*<sub>0</sub>.
- **FAILED**: Recovery score *r* is computed as a pure function of on-chain state. Routing is immediate within the same transaction. Duration: 0.
- **RECOVERING**: Fallback either completes (→ RESOLVED) or fails (→ DISPUTED). Bounded by remaining deadline: *δ* − *t*<sub>current</sub>.
- **DISPUTED**: Arbiter rules (→ RESOLVED) or timeout expires (→ RESOLVED with auto-refund). Bounded by *D*<sub>timeout</sub> (default 604,800 seconds = 7 days).

Total maximum: (*δ* − *t*<sub>0</sub>) + 0 + (*δ* − *t*<sub>fail</sub>) + *D*<sub>timeout</sub> ≤ (*δ* − *t*<sub>0</sub>) + *D*<sub>timeout</sub>. ∎

**Theorem 3 (Irreversibility).** *State transitions are monotonic: once a task leaves state σ, it never returns to σ.*

*Proof.* The transition function *τ* defines a directed acyclic graph over states: IDLE → RUNNING → {FAILED, RESOLVED}; FAILED → {RECOVERING, DISPUTED}; RECOVERING → {RESOLVED, DISPUTED}; DISPUTED → RESOLVED. No edge returns to a previously visited state. Each transition executes atomically within a single transaction, writing the new state to contract storage before function return. ∎

**Theorem 4 (Determinism).** *For any task T in state σ and event e, τ(σ, e) produces at most one successor state.*

*Proof.* The only branching transition is *τ*(FAILED, RecoveryRoute(*r*)), which depends on the recovery score *r*. Since *r* is computed as a pure function of on-chain state (Equation 1 in Section 6.4), and the threshold comparisons (*r* ≥ 0.6, 0.3 ≤ *r* < 0.6, *r* < 0.3) partition ℝ into disjoint intervals, exactly one branch is taken. All other transitions in the table map to a unique successor. ∎

### 2.3 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CAIRN Protocol Architecture                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Operator / Agent Frameworks                                       │
│   (LangGraph, Olas SDK, CrewAI, AutoGen, custom)                    │
│         │                                                           │
│         ▼                                                           │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │                    CairnCore (Hub)                         │     │
│   │  Task lifecycle · Checkpoint batching · Heartbeat          │     │
│   │  Escrow settlement · Permissionless enforcement            │     │
│   ├───────────┬───────────┬───────────┬──────────────────────┤     │
│   │ Recovery  │ Fallback  │ Arbiter   │ Governance            │     │
│   │ Router    │ Pool      │ Registry  │                       │     │
│   │           │           │           │ Timelock proposals     │     │
│   │ Classify  │ Select    │ Dispute   │ Parameter control      │     │
│   │ Score     │ Rank      │ Ruling    │ Upgrade authorization  │     │
│   │ Route     │ Slash     │ Appeal    │                       │     │
│   └─────┬─────┴─────┬─────┴─────┬─────┴──────────────────────┘     │
│         │           │           │                                   │
│   ┌─────▼─────┐ ┌───▼──────┐ ┌─▼───────────┐                      │
│   │ ERC-8183  │ │ ERC-8004 │ │  ERC-7710   │                      │
│   │ Job       │ │ Identity │ │  Delegation  │                      │
│   │ Escrow    │ │ + Reputa-│ │  (scoped    │                      │
│   │ Hooks     │ │ tion     │ │  permission) │                      │
│   └───────────┘ └──────────┘ └─────────────┘                      │
│         │           │                                               │
│   ┌─────▼───────────▼──────────────────────────────────────────┐   │
│   │              Execution Intelligence Layer                   │   │
│   │  IPFS (checkpoint + record storage)                         │   │
│   │  The Graph (event indexing + aggregation)                   │   │
│   │  Knowledge graph (pattern detection + queries)              │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   Optional Integration:                                             │
│   ┌──────────────┐  ┌──────────────┐                               │
│   │ Olas Mech    │  │ OlasMech     │                               │
│   │ Marketplace  │  │ Adapter      │                               │
│   │ (600+ agents)│  │ (fallback    │                               │
│   │              │  │  bridge)     │                               │
│   └──────────────┘  └──────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.4 Worked Example: The 2:47am Recovery

A DeFi operator submits a 5-step portfolio rebalancing task with 0.01 ETH escrow, a 30-minute deadline, and a 60-second heartbeat interval.

| Time | Event | State |
|------|-------|-------|
| T+0s | Operator submits task; escrow locked | **IDLE** |
| T+5s | Operator confirms; agent begins execution | **RUNNING** |
| T+30s | Agent completes step 1 → writes checkpoint CID to IPFS → commits on-chain | RUNNING |
| T+65s | Agent completes step 2 → checkpoint 2 committed | RUNNING |
| T+95s | Agent completes step 3 → checkpoint 3 committed | RUNNING |
| T+120s | Agent calls CoinGecko API → HTTP 429 (rate limit) → agent process crashes | RUNNING |
| T+185s | Heartbeat missed (120s + 65s > 60s interval) → anyone calls `checkLiveness` | **FAILED** |
| T+186s | RecoveryRouter classifies: **LIVENESS** (0.9 weight); budget 85% remaining; deadline 88% remaining | FAILED |
| T+186s | Recovery score = (0.9 × 0.5) + (0.85 × 0.3) + (0.88 × 0.2) = **0.45 + 0.255 + 0.176 = 0.881** | FAILED |
| T+186s | Score 0.881 ≥ 0.6 → route to RECOVERING | **RECOVERING** |
| T+190s | FallbackPool selects highest-reputation agent for `defi.trade_execute` | RECOVERING |
| T+195s | Fallback reads checkpoints 1-3 from IPFS; resumes at step 4 | RECOVERING |
| T+230s | Fallback completes step 4 → checkpoint 4 committed | RECOVERING |
| T+270s | Fallback completes step 5 → task complete | **RESOLVED** |
| T+271s | Settlement: primary gets 60% (3/5 checkpoints), fallback gets 40% (2/5), minus 0.5% protocol fee | RESOLVED |

**Result without CAIRN:** Operator discovers failure 4+ hours later. Full restart. Original agent paid $0.

**Result with CAIRN:** Automatic detection in 65 seconds. Fallback resumes from step 4. Original agent paid $0.006 for verified work. Total recovery time: ~85 seconds.

### 2.5 Comparative Analysis: Recovery vs. Restart

The value of checkpoint-based recovery scales with task length and failure point. The later a task fails, the more work is preserved:

| Task Profile | Steps | Failure Point | CAIRN Detection | Restart Detection | CAIRN Recovered Work | Restart Recovered Work | CAIRN Settlement Time | Restart Settlement |
|---|---|---|---|---|---|---|---|---|
| Simple API call | 3 | Step 2 | ~65s (heartbeat) | ~4h (manual) | 66% (2/3 steps) | 0% | ~90s total | Full re-execution |
| DeFi rebalance | 5 | Step 3 | ~65s | ~4h | 60% (3/5 steps) | 0% | ~85s total | Full re-execution |
| Data pipeline | 10 | Step 7 | ~65s | ~4h | 70% (7/10 steps) | 0% | ~70s total | Full re-execution |
| Long analysis | 20 | Step 15 | ~65s | ~4h | 75% (15/20 steps) | 0% | ~65s total | Full re-execution |
| Complex pipeline | 50 | Step 42 | ~65s | ~4h | 84% (42/50 steps) | 0% | ~60s total | Full re-execution |

**Key insight:** With restart, failure cost is proportional to total task length (all work is lost). With CAIRN, failure cost is proportional to *remaining* work only (completed checkpoints are preserved). For a 50-step task failing at step 42, CAIRN preserves 84% of completed work and only re-executes the remaining 16%.

**Economic comparison** (0.01 ETH escrow, 0.5% protocol fee):

| Task Profile | Steps | Failure at | Original Agent (CAIRN) | Original Agent (Restart) | Wasted Gas (CAIRN) | Wasted Gas (Restart) |
|---|---|---|---|---|---|---|
| DeFi rebalance | 5 | Step 3 | 0.00597 ETH (60%) | 0 ETH | Steps 1-3: $0 | Steps 1-3: ~$0.003 |
| Data pipeline | 10 | Step 7 | 0.00697 ETH (70%) | 0 ETH | Steps 1-7: $0 | Steps 1-7: ~$0.006 |
| Complex pipeline | 50 | Step 42 | 0.00836 ETH (84%) | 0 ETH | Steps 1-42: $0 | Steps 1-42: ~$0.035 |

With CAIRN, the original agent is compensated for verified work. Without CAIRN, 100% of work and payment is lost on any failure.

### 2.6 What CAIRN Is NOT

- **Not a new agent framework.** CAIRN wraps any existing framework — LangGraph, Olas SDK, AgentKit, CrewAI, custom builds.
- **Not a replacement for A2A or MCP.** Google's A2A protocol [12] handles agent discovery and communication. Anthropic's MCP [13] connects agents to tools. CAIRN handles what happens when those agents fail mid-task: detection, recovery, and settlement. These are complementary layers.
- **Not a replacement for ERC-8183.** Virtuals' Agent Commerce Protocol implements ERC-8183 for the job lifecycle happy path (job creation → completion → payment). CAIRN handles the unhappy path (failure → classification → recovery → settlement). They compose.
- **Not a centralized service.** Every state transition is enforced by the CAIRN state machine contract. No server. No admin key. No human required.
- **Not optional infrastructure.** The escrow condition makes record-writing mandatory — agents cannot receive payment without completing the protocol.

---

## 3. Design Philosophy

### 3.1 Classify by Recoverability, Not Symptom

Prior research identifies 14+ failure modes in multi-agent systems [1], but existing taxonomies describe surface symptoms ("step repetition," "wrong tool selected") without prescribing what to do next. CAIRN's classification directly determines protocol behavior:

**LIVENESS failures** (weight: 0.9) — the agent stopped responding. A heartbeat was missed, a process crashed, or a network partition occurred. These are almost always recoverable: the task is not impossible, the agent simply died. A fallback can resume from the last checkpoint immediately.

**RESOURCE failures** (weight: 0.5) — the agent exhausted a resource. Budget exceeded, deadline hit, API rate-limited, or context window overflowed. These are partially recoverable: success depends on whether sufficient budget and deadline remain for the fallback.

**LOGIC failures** (weight: 0.1) — the agent reasoned incorrectly. Step repetition loops, hallucinated outputs, or specification mismatches. These are rarely recoverable: a fallback with the same task specification will likely fail the same way. Route to dispute.

This mapping is analogous to the foundational distinction between **crash faults** and **Byzantine faults** in distributed systems [8]. A crashed agent needs a different recovery path than an agent producing wrong outputs. CAIRN operationalizes this insight for the AI agent domain.

### 3.2 Resume, Not Restart

Without checkpoints, a fallback agent must restart the entire task — wasting the original agent's completed work and the budget spent on it. Checkpoints commit verified work after each subtask. On recovery, the fallback reads the checkpoint list and resumes from the last verified output. No restart from zero.

The theoretical foundation for this approach is the Chandy-Lamport algorithm for distributed snapshots [8], which proves that consistent global state can be reconstructed from local checkpoints in a distributed system. CAIRN adapts this: agents independently checkpoint after each subtask (independent timing), but checkpoints are schema-validated and IPFS-stored (coordinated verification) — a quasi-synchronous model.

### 3.3 Permissionless Enforcement

All enforcement functions (`checkLiveness`, `checkBudget`, `checkDeadline`) are public. Anyone can call them. No trusted keeper is required.

The enforcement function only succeeds if the condition is actually violated. False calls revert with no state change and no gas refund for the caller. This makes the protocol permissionless — any participant can enforce liveness on any task, removing the dependency on centralized keeper networks.

### 3.4 Escrow as Forcing Function

The escrow condition bootstraps participation without relying on altruism. Agents cannot receive payment without completing the protocol — including writing the execution record. This creates a compounding network effect:

```
More agents writing records → Richer intelligence layer
  → More accurate fallback selection → Higher recovery success rate
    → More agents integrating CAIRN → More agents writing records
```

The loop starts from day one because the economic incentive is immediate.

### 3.5 Why On-Chain

A legitimate question: why does agent failure recovery require a blockchain? The answer is structural, not ideological.

**Escrow requires trustless settlement.** CAIRN distributes escrow proportionally to verified checkpoints from two agents who do not trust each other (the primary and fallback). A centralized coordinator could modify checkpoint counts or settlement calculations. On-chain settlement removes this trust dependency — the escrow split is computed by an immutable function visible to all parties.

**Permissionless enforcement requires public state.** Any participant can call `checkLiveness` to trigger failure detection. This is only possible when the enforcement function, the last heartbeat timestamp, and the heartbeat interval are all publicly readable on-chain. A centralized system could restrict who is allowed to report failures.

**Record immutability requires append-only storage.** The execution intelligence layer's value depends on records being tamper-proof. If a centralized operator could modify failure records (e.g., deleting records that make a preferred agent look bad), the intelligence layer loses integrity. On-chain events are immutable.

**What does NOT need to be on-chain:**
- Checkpoint data content → IPFS (content-addressed, verifiable off-chain)
- Intelligence queries → The Graph / knowledge graph (off-chain indexing)
- Pattern detection → Off-chain analytics pipeline
- Agent framework integration → SDK wraps any framework locally

CAIRN places the minimum viable state on-chain (task state, escrow, checkpoint counts, heartbeat timestamps) and keeps everything else off-chain. This minimizes gas costs while preserving the trust properties that motivate blockchain use.

---

## 4. Key Design Decisions

### 4.1 Checkpoint Protocol

**Write flow:**
```
Agent completes subtask N
→ Agent writes output to IPFS → receives content-addressed CID
→ Agent calls commitCheckpointBatch(taskId, count, merkleRoot, latestCID)
→ CAIRN stores Merkle root and latest CID, increments checkpoint count
→ Event: CheckpointBatchCommitted(taskId, count, merkleRoot)
```

**Recovery read flow:**
```
Fallback agent receives task state:
  - checkpoint CIDs: [CID_0, CID_1, CID_2]  (from events/IPFS)
  - next subtask index: 3                     (resume here)
  - remaining budget, remaining deadline
→ Fallback reads CID_2 from IPFS → subtask 2 output
→ Fallback begins subtask 3 using subtask 2 output as input
```

Checkpoints use **Merkle tree batching** for gas efficiency: multiple checkpoint CIDs are batched off-chain, and only the Merkle root is committed on-chain. Individual checkpoints can be verified via Merkle proof when needed (e.g., during dispute). This reduces gas costs by approximately 95% for tasks with many checkpoints compared to per-CID storage [see Section 6.5].

**Incentive alignment:** Agents are paid proportionally to verified checkpoint count. More checkpoints written means more partial payment on failure. This incentivizes frequent, honest checkpointing — the original agent has a direct financial interest in making their work resumable.

### 4.1.1 Checkpoint Portability

A checkpoint's value depends on whether a different agent — potentially running a different framework — can meaningfully resume from it. We define portability formally:

**Definition (Semantic Portability).** A checkpoint *C*<sub>i</sub> for subtask *i* is *semantically portable* from framework *F*<sub>1</sub> to framework *F*<sub>2</sub> if and only if an agent running *F*<sub>2</sub> can produce a correct output for subtask *i+1* given only *C*<sub>i</sub> and the task specification *S*, without access to *F*<sub>1</sub>'s internal state.

Portability depends on the checkpoint's **context completeness** — whether the checkpoint contains all information needed to continue the task:

| Portability Class | Description | Context Requirement | Examples |
|---|---|---|---|
| **Fully portable** | Checkpoint output is self-contained | Output is the complete result of subtask *i*; no implicit state needed | Data fetches, API calls, file transformations, on-chain reads |
| **Portable with context** | Checkpoint output is complete when combined with explicit metadata | Output plus metadata fields (e.g., accumulated state, configuration) | Multi-step computations, stateful API sessions, paginated queries |
| **Framework-dependent** | Checkpoint requires internal framework state to interpret | Implicit reasoning chain, model context window, conversation history | Chain-of-thought reasoning, multi-turn dialogue, planning with backtracking |

CAIRN's checkpoint schema targets the first two classes by requiring explicit context serialization:

```json
{
  "task_id": "0x...",
  "subtask_index": 3,
  "output": { ... },
  "context": {
    "accumulated_state": { ... },
    "dependencies": ["subtask_0_cid", "subtask_1_cid", "subtask_2_cid"],
    "metadata": { ... }
  },
  "schema_version": "1.0"
}
```

The `context` field is the portability mechanism: any agent can reconstruct the necessary state by reading the output and context fields, without needing the original agent's internal representation. For framework-dependent tasks (reasoning chains with implicit state), operators should decompose the task into subtasks whose outputs are self-contained — effectively converting framework-dependent checkpoints into the "portable with context" class.

### 4.2 Task Type Taxonomy

Every routing decision depends on `task_type`. The taxonomy is hierarchical:

```
task_type = domain.operation
```

Examples: `defi.price_fetch`, `defi.trade_execute`, `data.report_generate`, `governance.vote_delegate`, `compute.model_inference`.

Agents declare supported task types in their ERC-8004 identity record. Fallback matching follows a precedence order: (1) exact match on `domain.operation` with highest reputation and available stake; (2) domain-level match with highest reputation; (3) no match → DISPUTED immediately.

### 4.3 Adaptive Liveness Interval

A fixed heartbeat interval is incorrect for all task types. A 30-second API call and a 3-hour analysis task require different liveness requirements.

```
heartbeat_interval = operator_declared_value
subject to:
  min = 30 seconds (Base block time ≈ 2s → 15 blocks)
  max = task_deadline / 4
  default = min(task_deadline / 10, 300 seconds)
```

This ensures at least 10 liveness signals per task by default, with a 5-minute cap per interval.

### 4.4 Fallback Pool Admission Control

Open registration creates a vulnerability: malicious or unreliable agents could register broadly, accept recovery assignments, and collect partial payment without completing work.

**Two-gate admission:**

**Gate 1 — Reputation:** Minimum ERC-8004 reputation score for the declared task type. Default threshold: score ≥ 50 on a 0-100 scale.

**Gate 2 — Stake:** Deposit proportional to maximum eligible escrow. Default: `min_stake = max_eligible_escrow × 0.1`. If the fallback agent fails without completing any checkpoints, the full stake is slashed and distributed to the operator.

**Optional: Olas Mech Marketplace integration.** When no internal fallback is available, CAIRN queries the Olas Mech Marketplace [5] for eligible agents by task capability, filtered by minimum reputation (85% success rate). This extends the fallback pool to 600+ external agents without requiring separate registration.

### 4.5 Arbiter Design

The arbiter role is itself an agent service. Arbiter agents register in CAIRN with a stake proportional to the maximum dispute value they can rule on (`min_arbiter_stake = max_dispute_value × 0.2`). They read public execution records, submit rulings, and earn fees (3% of dispute value).

Sybil resistance is economic: incorrect rulings (detectable via on-chain evidence) result in stake slashing. The stake at risk (20%) exceeds the fee earned (3%), making collusion uneconomical.

A commit-reveal scheme prevents front-running of dispute rulings. If no arbiter rules within the timeout (default 7 days), escrow auto-refunds to the operator.

---

## 5. Execution Intelligence Layer

### 5.1 What Gets Written

Record-writing is mandatory for escrow settlement — not optional.

**On FAILED — Failure Record (IPFS):**
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
  "timestamp": 1742000000
}
```

**On RESOLVED — Resolution Record (IPFS):**
```json
{
  "record_type": "resolution",
  "task_id": "0x...",
  "states_traversed": ["RUNNING", "FAILED", "RECOVERING", "RESOLVED"],
  "task_type": "defi.price_fetch",
  "total_cost": "0.0041 ETH",
  "original_checkpoint_count": 3,
  "fallback_checkpoint_count": 2,
  "escrow_split": {
    "original_agent": "0.006 ETH",
    "fallback_agent": "0.004 ETH",
    "protocol_fee": "0.00005 ETH"
  }
}
```

### 5.2 What Agents Query

**Pre-task intelligence (Phase 1 — Initialization):**

| Query | Returns | Purpose |
|-------|---------|---------|
| Failure patterns by task type | Ranked failure types with frequency | Operator assesses risk before committing escrow |
| Cost distribution | P25/P50/P75/P95 total cost | Operator sets realistic budget cap |
| Agent success rates | Agents ranked by success rate for task type | Select best-fit primary agent |
| Known-bad conditions | Time windows or APIs correlated with failures | Avoid scheduling during high-risk windows |

**Fallback selection intelligence (on FAILED → RECOVERING):**
```
Input:  task_type, remaining_budget, remaining_deadline
Query:  Eligible agents sorted by:
        1. Success rate on this task_type
        2. ERC-8004 reputation score
        3. Stake deposited
        4. Current availability
Filter: Admission threshold (min reputation + active stake)
Output: Ranked list of eligible fallback agents
```

### 5.3 Network Effects

The execution history cannot be forked. A competitor can copy the protocol code. They cannot copy the accumulated records — the failure patterns, the agent performance data, the cost distributions. This creates a defensible network effect where each new agent failure makes the protocol more valuable for every future agent.

**Quantitative model.** The intelligence layer's utility for a given task type *τ* is a function of the number of recorded failure and resolution events *n*<sub>τ</sub>:

```
Pattern confidence:     P(τ, n) = 1 − e^{−n/k}
Fallback accuracy:      F(τ, n) = F_0 + (F_max − F_0) × (1 − e^{−n/m})
```

Where:
- *k* = minimum records for 63% pattern confidence (estimated: *k* ≈ 30 per task type, based on standard statistical power analysis for detecting failure rates above 10% with 80% power)
- *F*<sub>0</sub> = baseline fallback success rate without intelligence (random selection from pool)
- *F*<sub>max</sub> = maximum fallback success rate with full intelligence
- *m* = records needed for 63% of maximum improvement (estimated: *m* ≈ 100 per task type)

**Minimum viable intelligence thresholds:**

| Records per Task Type | Pattern Confidence | Practical Utility |
|---|---|---|
| *n* = 10 | 28% | Preliminary signals; not actionable |
| *n* = 30 | 63% | Dominant failure type identifiable |
| *n* = 100 | 96% | Reliable failure pattern distribution; fallback ranking meaningful |
| *n* = 300 | >99.99% | Statistical significance for time-based and agent-specific patterns |

These estimates follow from the exponential model: at *n* = *k*, confidence is 1 − *e*<sup>−1</sup> ≈ 0.63. The model predicts diminishing returns — the first 100 records per task type provide the majority of intelligence value, making the cold-start problem bounded rather than open-ended.

**Cold-start bootstrap:** With 6 initial task types and the empirical 50% failure rate [3], 100 tasks per type produces ~50 failure records per type — sufficient for 81% pattern confidence. At 10 tasks per day across the protocol, minimum viable intelligence is reached in approximately 60 days.

---

## 6. Economic Model

### 6.1 Escrow Split Rule

On RESOLVED, escrow is distributed proportionally to verified work:

```
protocol_fee      = escrow × fee_bps / 10000
distributable     = escrow - protocol_fee
original_share    = distributable × (original_checkpoints / total_checkpoints)
fallback_share    = distributable × (fallback_checkpoints / total_checkpoints)
```

If no recovery occurred (original agent completed solo): 100% of distributable to original agent.

### 6.2 Protocol Fee

- Default: 50 basis points (0.5%) of escrow on settlement
- Collected on every RESOLVED state transition
- Configurable by governance (range: 0-500 bps)

### 6.3 Stake Requirements

| Role | Min Stake | Slash Condition | Slash Amount |
|------|-----------|-----------------|-------------|
| Fallback agent | 10% of max eligible escrow | Fails without completing any checkpoints | 100% of stake |
| Arbiter | 20% of max ruleable dispute | Incorrect ruling (detectable via evidence) | 50% of stake |

### 6.4 Recovery Score Formula

**Equation 1:**
```
r = w_f × F + w_b × B + w_d × D
```

Where *r* is the recovery score, expanded as:
```
r = (0.5 × failure_class_weight) + (0.3 × budget_remaining_pct) + (0.2 × deadline_remaining_pct)
```

Where:
- `failure_class_weight`: LIVENESS = 0.9, RESOURCE = 0.5, LOGIC = 0.1
- `budget_remaining_pct`: (budget_cap - cost_accrued) / budget_cap
- `deadline_remaining_pct`: (deadline - current_block) / (deadline - start_block)

**Three-tier routing:**
- Score ≥ 0.6 → **RECOVERING** (high confidence — automatic fallback, full remaining budget)
- 0.3 ≤ Score < 0.6 → **RECOVERING (reduced scope)** (attempt with constraints — fallback receives capped budget)
- Score < 0.3 → **DISPUTED** (requires arbiter resolution)

The three-tier model enables graduated recovery: high-confidence failures get full resources, medium-confidence failures get a constrained attempt before escalating to dispute, and low-confidence failures go directly to arbitration.

**Weight rationale:** The failure class contributes 50% of the score because the nature of the failure is the strongest predictor of recovery success — a LIVENESS failure (agent crashed) is fundamentally different from a LOGIC failure (agent reasoning incorrectly), regardless of remaining budget or time. Budget contributes 30% because resource availability is the next constraint — even a recoverable failure type cannot be resolved without sufficient remaining budget. Deadline contributes 20% because time pressure is real but secondary — an agent can often complete remaining work faster if the failure type is favorable and budget exists.

The upper threshold of 0.6 requires either a LIVENESS failure with any resource headroom, or a RESOURCE failure with substantial headroom. The lower threshold of 0.3 catches RESOURCE failures with minimal headroom — worth attempting but with reduced budget allocation. LOGIC failures (0.1 weight) almost never reach 0.3 — which is correct, since they rarely benefit from retry. All thresholds are governance-adjustable parameters (see Section 8).

### 6.5 Gas Costs

All operations are designed for Base L2, where gas is inexpensive:

| Operation | Gas Cost | Cost @ 0.01 gwei (Base L2) | Cost @ $2,500/ETH |
|-----------|----------|---------------------------|-------------------|
| `submitTask` | ~180,000 | 1.8 × 10⁻⁶ ETH | $0.0045 |
| `commitCheckpointBatch` (1 checkpoint) | ~80,000 | 8.0 × 10⁻⁷ ETH | $0.0020 |
| `commitCheckpointBatch` (10 checkpoints) | ~100,000 | 1.0 × 10⁻⁶ ETH | $0.0025 |
| `heartbeat` | ~45,000 | 4.5 × 10⁻⁷ ETH | $0.0011 |
| `settle` (escrow distribution) | ~140,000 | 1.4 × 10⁻⁶ ETH | $0.0035 |

Merkle batching reduces checkpoint gas by ~95% compared to per-CID storage. A 50-checkpoint task costs approximately 100,000 gas total for checkpoints (one batch) versus 3,350,000 gas without batching.

---

## 7. Security Model

### 7.1 Design Principles

| Principle | Implementation |
|-----------|---------------|
| No trusted keepers | All enforce functions public; anyone can trigger failure detection |
| Escrow as commitment | Record-writing mandatory for payment release |
| Stake-based accountability | Fallback agents and arbiters stake capital proportional to exposure |
| Deterministic scoring | Recovery score is a pure function of on-chain state — no oracle, no AI |
| Permissionless enforcement | False enforcement calls revert; caller pays gas; no economic benefit to attacker |

### 7.2 Threat Model

CAIRN assumes:
- The underlying blockchain (Base/Ethereum) is secure
- IPFS content remains available for the task duration plus dispute period (ensured via pinning services)
- ERC-8004 reputation scores are accurate (CAIRN inherits ERC-8004's security model)
- Operators submit accurate task specifications (agents can query specs before accepting)
- Block time is consistent (~2s on Base)

### 7.3 Attack Vectors and Mitigations

| Attack | Severity | Mitigation |
|--------|----------|------------|
| **Checkpoint gaming** — Agent commits fake checkpoints to inflate payment | High | Schema validation via hash; off-chain content verification; reputation decay for invalid submissions |
| **Liveness griefing** — Attacker calls `checkLiveness` to force premature failure | Low | Only succeeds if heartbeat interval actually elapsed; false calls revert; attacker pays gas |
| **Fallback Sybil** — Attacker registers many agents to capture recovery assignments | Medium | Reputation gate (min 50) + stake requirement (10%); 100% slash on zero-checkpoint failure |
| **Arbiter collusion** — Arbiter rules in favor of colluding agent | Medium | Stake (20%) > fee (3%); incorrect rulings slashed; commit-reveal prevents front-running |
| **Recovery score manipulation** — Agent times failure for desired routing | Low | All score inputs on-chain; agent cannot control failure classification retroactively |
| **Intelligence poisoning** — False failure records to mislead future agents | Medium | Records auto-written by protocol, not by agents; content matches on-chain state |

### 7.4 Protocol Invariants

These properties hold at all times:

1. **Escrow safety.** Escrow is not released until `state == RESOLVED`.
2. **Deterministic scoring.** Same on-chain inputs produce the same recovery score. No external dependencies.
3. **Checkpoint immutability.** Committed checkpoint CIDs cannot be modified or deleted.
4. **State irreversibility.** No backward state transitions. `IDLE → RUNNING → {FAILED, RESOLVED}; FAILED → {RECOVERING, DISPUTED}; RECOVERING → {RESOLVED, DISPUTED}; DISPUTED → RESOLVED; RESOLVED → terminal`.
5. **Fee ordering.** Protocol fee is deducted before agent payment calculation.
6. **Liveness enforcement.** `checkLiveness` only succeeds if the heartbeat interval has actually elapsed.

### 7.5 Incentive Analysis

We analyze three strategic games within CAIRN: the checkpoint commitment game, the fallback acceptance game, and the arbiter ruling game.

#### Game 1: Checkpoint Commitment

**Proposition 1 (Checkpoint Dominance).** *For a task with escrow E, n subtasks, empirical failure probability p<sub>f</sub>, and per-checkpoint gas cost g, honest checkpointing is the dominant strategy when p<sub>f</sub> × E × (1 − f) / n > g, where f is the protocol fee rate.*

*Proof.* Agent *A* executes task *T* with *n* subtasks. At each subtask *i*, *A* chooses action *a*<sub>i</sub> ∈ {commit, skip}. Let *c* = number of committed checkpoints. Let *g* = gas cost per checkpoint on Base L2 ≈ 8 × 10⁻⁷ ETH (80,000 gas × 0.01 gwei).

The expected marginal value of one additional checkpoint:

```
ΔV = (1 − p_f) × (−g) + p_f × [E(1 − f)/n − g]
   = p_f × E(1 − f)/n − g
```

In case of success (probability 1 − *p*<sub>f</sub>), an extra checkpoint costs *g* but provides no additional payment. In case of failure (probability *p*<sub>f</sub>), an extra checkpoint increases the agent's share by *E*(1 − *f*)/*n* at cost *g*.

Checkpointing is dominant when Δ*V* > 0. Evaluating with protocol parameters (*f* = 0.005, *g* = 8 × 10⁻⁷ ETH) and the empirical failure rate *p*<sub>f</sub> = 0.5 from [3]:

| Subtasks (*n*) | Min Escrow (*E*) | Δ*V* | Dominant? |
|---|---|---|---|
| 5 | 0.001 ETH | 9.87 × 10⁻⁵ | Yes (Δ*V* ≫ *g*) |
| 10 | 0.001 ETH | 4.90 × 10⁻⁵ | Yes |
| 50 | 0.001 ETH | 9.15 × 10⁻⁶ | Yes |
| 100 | 0.001 ETH | 4.17 × 10⁻⁶ | Yes |
| 500 | 0.001 ETH | 1.95 × 10⁻⁷ | Marginal (Δ*V* ≈ 0.24*g*) |

The condition holds for all realistic task configurations (n ≤ 100 at minimum escrow, or any escrow ≥ 0.01 ETH at any *n*). The boundary escrow for dominance is *E*<sub>min</sub> = (*g* × *n*) / (*p*<sub>f</sub> × (1 − *f*)) — for *n* = 100: *E*<sub>min</sub> ≈ 1.6 × 10⁻⁴ ETH, well below the protocol minimum of 10⁻³ ETH.

**Faking checkpoints** is strictly dominated: invalid CIDs are rejected by schema hash validation (the schema hash is committed at task initialization and cannot be changed). Repeated invalid submissions trigger reputation decay below the fallback pool admission threshold. ∎

#### Game 2: Fallback Acceptance

**Proposition 2 (Rational Fallback Acceptance).** *A fallback agent with success rate s<sub>τ</sub> for task type τ should accept a recovery assignment when the expected payoff exceeds zero:*

```
s_τ × E_r × (c_f / c_total) × (1 − f) > (1 − s_τ) × p_0 × stake
```

*where E<sub>r</sub> is remaining escrow, c<sub>f</sub>/c<sub>total</sub> is the fallback's expected checkpoint share, and p<sub>0</sub> is the probability of zero-checkpoint failure (triggering 100% slash).*

This self-selection mechanism is beneficial: agents with low success rates for a given task type will rationally decline recovery assignments, ensuring only capable agents accept. The admission gates (reputation ≥ 50, stake ≥ 10%) further filter the pool so that only agents with demonstrated competence are eligible.

#### Game 3: Arbiter Ruling

**Proposition 3 (Arbiter Honesty).** *For an arbiter with stake s = 0.2V (where V is the dispute value), fee φ = 0.03V, and detection probability p<sub>d</sub> for incorrect rulings, honest ruling is the rational strategy when:*

```
bribe < φ + p_d × 0.5s = 0.03V + p_d × 0.1V
```

*Proof.* The arbiter chooses between honest and dishonest ruling:
- **Honest payoff:** +*φ* = +0.03*V*
- **Dishonest payoff:** +bribe − *p*<sub>d</sub> × 0.5*s* = bribe − *p*<sub>d</sub> × 0.1*V*

For dishonesty to be rational, the bribe must exceed the honest fee plus the expected penalty: bribe > 0.03*V* + *p*<sub>d</sub> × 0.1*V*.

The detection probability *p*<sub>d</sub> is high in CAIRN because all evidence is on-chain: checkpoint CIDs, failure records, heartbeat timestamps, and cost accruals are publicly verifiable. With *p*<sub>d</sub> ≥ 0.8 (conservative — most disputes have clear on-chain evidence), the minimum bribe is 0.03*V* + 0.08*V* = 0.11*V*.

**Multi-dispute analysis:** An arbiter who colludes in *k* disputes has cumulative detection probability 1 − (1 − *p*<sub>d</sub>)<sup>k</sup>. At *p*<sub>d</sub> = 0.8: a single dispute has 80% detection risk; two disputes have 96%; three disputes have 99.2%. This makes sustained collusion economically irrational — the expected losses from detection compound exponentially while the gains are linear.

The commit-reveal scheme provides an additional layer: the arbiter commits a hash of their ruling before knowing which agents are involved (preventing pre-arrangement), and must reveal within 24 hours or forfeit their eligibility. ∎

---

## 8. Governance

### 8.1 Configurable Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Protocol fee | 50 bps | 0-500 bps | Fee on escrow settlement |
| Fallback min reputation | 50/100 | 0-100 | Min ERC-8004 reputation for fallback pool |
| Fallback min stake | 10% | 1-50% | Stake as % of max eligible escrow |
| Arbiter min stake | 20% | 5-50% | Stake as % of max ruleable dispute |
| Arbiter fee | 3% | 1-10% | Fee as % of dispute value |
| Arbiter timeout | 7 days | 1-30 days | Time for arbiter to rule before auto-refund |
| Recovery threshold (upper) | 0.6 | 0.1-0.9 | Score threshold for full-scope RECOVERING |
| Recovery threshold (lower) | 0.3 | 0.1-0.9 | Score threshold for reduced-scope RECOVERING vs DISPUTED |

### 8.2 Governance Model

**Current: Multi-sig with timelock.** A 3-of-5 multi-sig controls parameter changes with a 48-hour timelock. All proposals are public. This provides rapid iteration capability while maintaining review periods.

**Future: Token governance (if applicable).** Parameters changeable via on-chain voting. Emergency multi-sig retained for security issues.

### 8.3 Upgrade Path

CAIRN contracts implement the **UUPS (Universal Upgradeable Proxy Standard)** pattern. The proxy is immutable; the implementation contract can be replaced via governance-authorized upgrade. This allows the protocol to evolve (new features, bug fixes) while preserving user funds and task state across versions.

All upgrades require governance approval via the timelock. In-flight tasks are not affected — they complete under the implementation version active when they were created.

---

## 9. Related Work

### 9.1 Agent Frameworks with Failure Handling

| Solution | Checkpointing | Cross-Agent Handoff | Escrow Settlement | Failure Intelligence |
|----------|:---:|:---:|:---:|:---:|
| LangGraph | Yes (proprietary) | No | No | No |
| Temporal.io | Yes | No (same worker) | No | No |
| Kubernetes | No (container-level) | No | No | No |
| LangSmith | No (observability only) | No | No | No |
| Manual restart | No | No | No | No |
| **CAIRN** | **Yes (portable)** | **Yes** | **Yes** | **Yes** |

**LangGraph** provides state persistence via `SqliteSaver`/`PostgresSaver`, but checkpoints are framework-locked — a LangGraph checkpoint cannot be read by a CrewAI agent or an Olas mech. No automatic fallback assignment, no escrow settlement, no cross-ecosystem intelligence. CAIRN wraps LangGraph: agents write CAIRN-format checkpoints (portable via IPFS), and any CAIRN-compatible agent can resume on failure.

**Temporal.io** provides production-grade workflow orchestration with deterministic replay. However, recovery is within the same worker pool — no cross-organization fallback. No escrow integration. No on-chain settlement. Temporal is excellent for internal automation; CAIRN is for autonomous agents with on-chain economics.

**Kubernetes** operates at the container level (is the pod running?) while CAIRN operates at the task level (did step 3 complete? can step 4 be recovered?). These are orthogonal. Use both.

### 9.2 On-Chain Agent Coordination

**ERC-8183 / Agent Commerce Protocol (ACP).** Defines the job lifecycle (Open → Funded → Submitted → Terminal) and escrow mechanism. Live on Arbitrum via Virtuals Protocol [15]. CAIRN extends ERC-8183 as a Hook — when an ERC-8183 job fails, CAIRN provides the failure classification, fallback routing, and proportional settlement that ERC-8183 does not define.

**ERC-8004 (Trustless Agents).** Provides agent identity and reputation registries. Live on Ethereum mainnet since January 2026, with 85,000+ registered agents across 18+ EVM chains [14]. CAIRN reads reputation scores for fallback pool admission and writes outcome signals (success/failure attestations) after task completion.

**ERC-7710 (Delegation Framework).** Enables scoped permission transfer. CAIRN uses ERC-7710 for pre-authorized fallback delegation: the operator grants CAIRN permission to sub-delegate task authority to a fallback agent at recovery time, without requiring a new operator signature.

**ERC-8211 (Smart Batching).** Enables AI agents to execute complex DeFi operations in a single batched transaction [16]. Composable with CAIRN: checkpoints can wrap ERC-8211 batched executions.

### 9.3 Off-Chain Coordination Protocols

**Google A2A (Agent-to-Agent Protocol).** Under the Linux Foundation with 50+ enterprise partners [12]. Handles agent discovery via Agent Cards, task delegation, and collaboration via context sharing. A2A is the off-chain communication layer; CAIRN is the on-chain settlement and recovery layer. A2A tells agents what to do; CAIRN guarantees what happens when it fails.

**Anthropic MCP (Model Context Protocol).** Connects agents to tools and data sources [13]. Adopted by OpenAI, Microsoft, Google, Amazon. MCP provides the tool access; CAIRN provides the fault tolerance. When an MCP tool call fails mid-task, CAIRN's checkpoint system preserves completed work and the fallback mechanism ensures completion.

### 9.4 Academic Foundations

CAIRN builds on established theory:

- **Distributed checkpointing.** The Chandy-Lamport algorithm [8] proves that consistent global state can be reconstructed from local checkpoints. CAIRN adapts this for AI agent semantics with IPFS-stored, schema-validated checkpoints.

- **Mechanism design.** Staking and slashing mechanisms are proven at $400B+ scale in Ethereum Proof-of-Stake [9]. CAIRN applies the same principle: stake capital to participate, lose it for misbehavior.

- **Multi-agent failure analysis.** The MAST taxonomy [1] provides the most comprehensive classification of multi-agent failure modes to date. CAIRN's contribution is to add the recoverability dimension — classifying failures by what action to take, not by what went wrong.

---

## 10. Future Work

### 10.1 Open Research Questions

**Checkpoint semantic portability.** CAIRN's checkpoint format is portable across frameworks (schema-validated IPFS CIDs), and Section 4.1.1 establishes that fully portable and portable-with-context checkpoints cover the majority of practical task types (data fetches, API calls, multi-step computations, stateful queries). However, for complex reasoning chains with implicit context (chain-of-thought, multi-turn dialogue), semantic portability remains unproven. Empirical study of checkpoint portability across LangGraph, CrewAI, and Olas agent architectures is planned.

**Recovery score calibration.** The current weights (*w*<sub>f</sub> = 0.5, *w*<sub>b</sub> = 0.3, *w*<sub>d</sub> = 0.2) and class weights (*F*<sub>LIVENESS</sub> = 0.9, *F*<sub>RESOURCE</sub> = 0.5, *F*<sub>LOGIC</sub> = 0.1) are based on domain reasoning and the boundary analysis in Section 6.4, not empirical data. A Monte Carlo simulation across synthetic task distributions is planned to validate that these weights maximize the F1 score for recovery routing decisions — minimizing both false positives (attempting recovery that fails) and false negatives (sending recoverable tasks to dispute). As CAIRN accumulates execution records, the weights will be validated against observed recovery success rates and adjusted via governance.

**Multi-agent recovery chains.** The current protocol supports one fallback. Future versions could support multiple sequential fallbacks, with each contributing checkpoints and earning proportional payment. The mechanism design for chains longer than two agents requires additional analysis.

### 10.2 Protocol Extensions

**ERC standardization.** CAIRN is designed to become an Ethereum standard. The specification in [ERC-CAIRN.md](./ERC-CAIRN.md) follows the EIP-1 format. Working title: `ERC-CAIRN: Agent Failure and Recovery Standard`.

**CAIRN MCP Server.** Exposing checkpoint, recovery, and intelligence query as MCP tools would enable any MCP-connected agent to participate in CAIRN without framework-specific integration.

**Cross-chain support.** CAIRN is currently deployed on Base. Cross-chain fallback (e.g., a Base task recovered by an Olas agent on Gnosis) requires cross-chain messaging and is planned for a future protocol version.

**Privacy-preserving intelligence.** Currently, all failure records are public. Future versions may use zero-knowledge proofs to enable agents to query failure patterns without revealing their specific execution data.

---

## 11. References

[1] M. Cemri, M. Z. Pan, S. Yang, et al., "Why Do Multi-Agent LLM Systems Fail?", *NeurIPS 2025 Datasets and Benchmarks Track (Spotlight)*, arXiv:2503.13657, 2025.

[2] S. Rabanser, S. Kapoor, et al., "Towards a Science of AI Agent Reliability", arXiv:2602.16666, February 2026.

[3] "Exploring Autonomous Agents: A Closer Look at Why They Fail", *ASE 2025 NIER Track*, arXiv:2508.13143, August 2025.

[4] "Blockchain-Enhanced Incentive-Compatible Mechanisms for Multi-Agent Reinforcement Learning Systems", *Nature Scientific Reports*, November 2025.

[5] Olas Network, "Mech Marketplace", https://olas.network/mech-marketplace. Over 10 million agent-to-agent transactions as of 2026.

[6] "Autonomous Agents on Blockchains: A Systematic Survey", arXiv:2601.04583, January 2026. Survey of 317 publications identifying missing interface layers and verifiable policy enforcement as key gaps.

[7] ISO/IEC TR 5469, "Artificial Intelligence — Functional Safety and AI Systems", International Organization for Standardization.

[8] K. M. Chandy and L. Lamport, "Distributed Snapshots: Determining Global States of Distributed Systems", *ACM Transactions on Computer Systems*, 3(1):63-75, 1985.

[9] V. Buterin, D. Ryan, et al., "Ethereum Proof-of-Stake Consensus Specifications", Ethereum Foundation, 2020-2026. https://github.com/ethereum/consensus-specs. Staking/slashing mechanism securing $400B+ in staked value across 1M+ validators.

[10] "AI Agents Meet Blockchain: A Survey", *MDPI Future Internet*, 17(2):57, February 2025. Introduces Proof-of-Thought and Proof-of-Compute concepts.

[11] IETF Draft, "Task-Oriented Multi-Agent Recovery Framework for Converged Networks", 2026.

[12] Google, "Agent2Agent Protocol (A2A)", Linux Foundation, v0.3, 2025-2026. https://github.com/google/A2A

[13] Anthropic, "Model Context Protocol (MCP)", 2025-2026. https://modelcontextprotocol.io

[14] ERC-8004: Trustless Agents Standard. Live on Ethereum mainnet since January 29, 2026. 85,000+ registered agents across 18+ EVM chains. EIP: https://eips.ethereum.org/EIPS/eip-8004

[15] ERC-8183: Agentic Commerce Standard. Draft status, March 2026. Agent Commerce Protocol (ACP) live on Arbitrum via Virtuals Protocol. EIP: https://eips.ethereum.org/EIPS/eip-8183

[16] ERC-8211: Smart Batching for DeFi Agents. Proposed by Biconomy, 2026. EIP: https://eips.ethereum.org/EIPS/eip-8211

[17] ERC-7710: Smart Contract Delegation. Draft status. Used by MetaMask Delegation Toolkit. EIP: https://eips.ethereum.org/EIPS/eip-7710

---

*CAIRN — Agent Failure and Recovery Protocol*
*Whitepaper v2.0 — April 2026*
*Agents learn together.*
