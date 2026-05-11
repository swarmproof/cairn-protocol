# CAIRN Protocol Whitepaper

## Agent Failure and Recovery Protocol

### Version 2.0 — April 2026

> **Author:** Maroua Boudoukha
> **Affiliation:** Independent Researcher
> **Contact:** github.com/MarouaBoud
>
> **Copyright 2026 Maroua BOUDOUKHA. All rights reserved.**
>
> This document may be cited for academic and research purposes with proper attribution:
> BOUDOUKHA, M. (2026). *CAIRN Protocol: Agent Failure and Recovery Protocol*. Whitepaper v2.0, April 2026.
>
> Redistribution or commercial use requires written permission from the author.

---

## Abstract

AI agent task completion rates remain at approximately 50% across popular frameworks, yet no standardized protocol exists for failure detection, classification, and recovery in the on-chain agent economy. We present CAIRN, the **first on-chain agent protocol** to classify agent failures by **recoverability** rather than symptom — adapting the classical crash-vs-Byzantine distinction from distributed systems [8] to the AI agent domain — enabling deterministic routing to checkpoint-based recovery or dispute resolution.

CAIRN defines a 6-state machine with three-tier recovery routing, enforced by smart contracts: when an agent fails mid-task, the protocol detects the failure via missed heartbeats or resource exhaustion, classifies it into one of three recoverability classes (LIVENESS, RESOURCE, LOGIC), computes a multiplicative recovery score *r* = *F*<sup>0.80</sup> × *B*<sup>0.35</sup> × *D*<sup>0.15</sup>, and routes the task to either a qualified fallback agent who resumes from the last IPFS-committed checkpoint, or to dispute resolution. The formula is **calibrated and validated via Monte Carlo simulation** against a ground-truth model derived from published failure-mode distributions [1][2][3]: across 100,000 synthetic task-failure events and 16 experiments, the multiplicative formula achieves 23.46% misrouting against that ground truth — within 0.93pp of the Bayes-optimal minimum (22.53%) attainable for the same model — and reduces wasted-recovery false positives by 65% versus a linear baseline. We are explicit that this is near-optimality *against the calibrated model*, not against measured production data, which does not yet exist; the staged calibration roadmap (Section 10.1) replaces the synthetic ground truth with observed outcomes as testnet and mainnet data accumulate. Escrow is settled proportionally to verified work. We prove escrow safety, termination, and state determinism, and show that honest checkpointing is the dominant strategy under realistic economic parameters.

Our key insight is that **economic enforcement** — escrow-conditioned record writing — bootstraps a collective intelligence layer without requiring altruistic participation. Every failure becomes a queryable record. Every recovery teaches the next agent. The accumulated execution history grows with task throughput and is openly queryable across the ecosystem.

CAIRN integrates three Ethereum standards: ERC-8004 for agent identity and reputation, ERC-8183 for job escrow lifecycle, and ERC-7710 for scoped delegation. It is deployed on Base and composable with existing agent frameworks (LangGraph, Olas, CrewAI, AutoGen) and emerging coordination protocols (Google A2A, Anthropic MCP). All simulation code, results, and figures are reproducible from `simulation/` in the CAIRN repository via `python3 -m simulation.run_eq4` (seed=42); see reference [18].

> **Note on protocol versions.** This paper specifies CAIRN **v2**, the simulation-validated protocol described throughout. The current testnet deployment (**v1**) uses an interim linear recovery score (Equation 1 of Section 10.1) with binary routing, reflecting the protocol's state prior to the calibration work reported here. The multiplicative formula, three-tier routing, and refined stake/threshold parameters described in Sections 2.2.1, 6.4, and 7.5 are the v2 specification, intended for adoption through the governance upgrade path outlined in Section 8.3. Sections marked *"v2 specification"* describe the target protocol; *"v1 deployment"* references describe what is live on testnet. This paper exists to motivate and document the v1 → v2 transition.

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

The Ethereum agentic economy generates significant economic activity — over 10 million agent-to-agent transactions on the Olas network alone [5], ~49,000 registered agent identities via ERC-8004 across 30+ EVM chains (as of February 2026) [14], and growing on-chain commerce via ERC-8183 [15]. But every agent is operationally isolated.

When an agent fails mid-task — because an API rate-limits, a budget is exceeded, a context window overflows, or a process crashes — **nothing standard happens**. The escrow sits in an ambiguous state. The operator who submitted the task — whether a human, another agent, a DAO multisig, or an autonomous smart contract — has no standardized way to detect the failure or trigger a recovery; the failure is discovered (if at all) only when the principal happens to poll the task. Another agent does not automatically take over. Completed work is lost.

Twenty minutes later, a different agent — same task type, same API, same conditions — fails identically. The collective cost compounds as the agent economy scales.

### 1.2 The Evidence

Published research establishes agent failure as a systemic problem, not an edge case:

- Multi-agent benchmarks show an **average task completion rate of approximately 50%** across popular frameworks including TaskWeaver, MetaGPT, and AutoGen [3]. The compounding effect is structural: *even if* single-step accuracy were 85% (well above current measured agent reliability per [2]), a 10-step workflow would succeed only ~20% of the time (0.85<sup>10</sup> = 0.197). Real production accuracy is lower, and the 50% headline rate is the empirical consequence.

- The MAST taxonomy identifies **14 distinct failure modes** across 1,600+ annotated traces from 7 multi-agent frameworks [1]. However, MAST classifies failures by symptom (step repetition, incorrect tool selection) — not by what recovery action to take.

- Research on AI agent reliability finds that **consistency remains weak across all models** — outcome consistency is the most persistently low dimension, and agents cannot reliably determine when they are wrong [2]. This validates the need for external failure detection infrastructure rather than relying on agent self-diagnosis.

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

CAIRN is a standardized agent failure and recovery protocol. It defines the exact sequence of events that occur when an agent fails mid-task — from detection, through classification, through fallback assignment, through settlement — **without any human-in-the-loop after task submission**, and without requiring trust between agents.

**Definition (Operator).** Throughout this paper, an *operator* is the Ethereum address that submits a task and posts its escrow — an EOA, an agent, a smart contract, or a DAO multisig; CAIRN is agnostic to which. The "no human required" property is therefore precise: **no human signature, intervention, or polling is required at any point between task submission and final settlement**. Failure detection, classification, recovery routing, fallback execution, dispute initiation, and escrow distribution all proceed via permissionless on-chain enforcement (Section 3.3) regardless of who or what submitted the task.

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

Six states. Every transition is deterministic. After the operator submits the task, **no human signature or human intervention is required to trigger any state change** — every transition fires from on-chain conditions evaluated by permissionless enforcement functions (Section 3.3) that any address may call.

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
                        ┌─────────┐  score ≥ 0.35  ┌───┴──────┐
                        │         │ ──────────────► │          │
                        │ FAILED  │  (≥0.40 full   │RECOVERING│
                        │         │ ◄─0.35-0.40─── │ (full or │
                        └────┬────┘  reduced scope) │ reduced) │
                             │       or fallback    └──────────┘
                      score  │       fails
                     < 0.35  │
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
| **FAILED** | Liveness miss, budget hit, or deadline exceeded | Classify failure; compute recovery score; write failure record | Score ≥ 0.35 → RECOVERING (full or reduced scope); Score < 0.35 → DISPUTED |
| **RECOVERING** | Recovery score ≥ 0.35 | Select fallback; transfer checkpoint state; fallback resumes (full or reduced scope) | Success → RESOLVED; Failure → DISPUTED |
| **DISPUTED** | Score < 0.35 or fallback failure | Hold escrow; expose evidence; start arbiter timeout | Arbiter ruling → RESOLVED; Timeout → auto-refund |
| **RESOLVED** | Completion or ruling | Settle escrow proportionally; write resolution record; update reputation | Terminal |

### 2.2.1 Formal Properties

**Transition Function.** The state transition function *τ*: *S* × *Event* → *S* is defined as:

| Current State | Event | Condition | Next State |
|---------------|-------|-----------|------------|
| IDLE | Confirm | Operator address calls `confirmTask` (signs via wallet, contract call, or multisig) | RUNNING |
| RUNNING | Complete | All subtasks verified | RESOLVED |
| RUNNING | HeartbeatMiss | block.timestamp > lastHeartbeat + *H* | FAILED |
| RUNNING | BudgetExceeded | *κ* ≥ *E* | FAILED |
| RUNNING | DeadlineExceeded | block.timestamp ≥ *δ* | FAILED |
| FAILED | RecoveryRoute | *r* ≥ 0.35 | RECOVERING |
| FAILED | RecoveryRoute | *r* < 0.35 | DISPUTED |
| RECOVERING | Complete | Fallback completes remaining subtasks | RESOLVED |
| RECOVERING | FallbackFailed | Fallback fails or deadline exceeded | DISPUTED |
| DISPUTED | ArbiterRuling | Arbiter submits valid ruling | RESOLVED |
| DISPUTED | Timeout | block.timestamp ≥ *t*<sub>dispute</sub> + *D*<sub>timeout</sub> | RESOLVED (refund) |

All (*σ*, *event*) pairs not listed above are undefined; the transaction reverts.

**Theorem 1 (Escrow Safety).** *For any task T, escrow E is not distributed until σ = RESOLVED.*

*Proof.* The settlement function `settle(taskId)` contains the precondition `require(task.state == RESOLVED)`. No other function in the protocol transfers escrow from the task's balance. The transition table in Section 2.2 has no outgoing edges from RESOLVED, so RESOLVED is terminal. Therefore, escrow *E* remains locked in all non-terminal states and is released only via `settle()` at σ = RESOLVED. ∎

**Theorem 2 (Termination).** *Every task T reaches σ = RESOLVED within at most δ − t₀ + D<sub>timeout</sub> seconds.*

*Proof.* We show each non-terminal state has a bounded exit:
- **IDLE**: Operator confirms or deadline passes. Bounded by *δ* − *t*<sub>0</sub>.
- **RUNNING**: Either completes (→ RESOLVED) or a fault triggers (heartbeat miss at *t* > lastHeartbeat + *H*, or deadline *δ* reached). Maximum duration: *δ* − *t*<sub>0</sub>.
- **FAILED**: Recovery score *r* is computed as a pure function of on-chain state. Routing is immediate within the same transaction. Duration: 0.
- **RECOVERING**: Fallback either completes (→ RESOLVED) or fails (→ DISPUTED). Bounded by remaining deadline: *δ* − *t*<sub>current</sub>.
- **DISPUTED**: Arbiter rules (→ RESOLVED) or timeout expires (→ RESOLVED with auto-refund). Bounded by *D*<sub>timeout</sub> (default 604,800 seconds = 7 days).

RUNNING and RECOVERING share the same time window [*t*<sub>0</sub>, *δ*] — RECOVERING begins at *t*<sub>fail</sub> ≥ *t*<sub>0</sub> and can only consume time up to *δ*, so the two intervals are not additive. The worst-case path therefore takes at most (*δ* − *t*<sub>0</sub>) seconds before DISPUTED is entered, plus at most *D*<sub>timeout</sub> seconds in DISPUTED. Total upper bound: (*δ* − *t*<sub>0</sub>) + *D*<sub>timeout</sub>. ∎

**Theorem 3 (Irreversibility).** *State transitions are monotonic: once a task leaves state σ, it never returns to σ.*

*Proof.* The transition function *τ* defines a directed acyclic graph over states: IDLE → RUNNING → {FAILED, RESOLVED}; FAILED → {RECOVERING, DISPUTED}; RECOVERING → {RESOLVED, DISPUTED}; DISPUTED → RESOLVED. No edge returns to a previously visited state. Each transition executes atomically within a single transaction, writing the new state to contract storage before function return. ∎

**Theorem 4 (Determinism).** *For any task T in state σ and event e, τ(σ, e) produces at most one successor state.*

*Proof.* The only branching transition is *τ*(FAILED, RecoveryRoute(*r*)), which depends on the recovery score *r*. Since *r* is computed as a pure function of on-chain state (Equation 1 in Section 6.4), and the v2 threshold comparisons (*r* ≥ 0.40, 0.35 ≤ *r* < 0.40, *r* < 0.35) partition ℝ into disjoint intervals, exactly one branch is taken. (In v1, the two-tier partition at *r* ≥ 0.30 / *r* < 0.30 is a degenerate case of the same proof; the determinism property holds in both versions.) All other transitions in the table map to a unique successor. ∎

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
│   │ (~2000 mechs)│  │ (fallback    │                               │
│   │              │  │  bridge)     │                               │
│   └──────────────┘  └──────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.4 Worked Example: The 2:47am Recovery

A DeFi portfolio-management agent (acting as the operator — its own wallet posts the escrow on behalf of an end user it serves) submits a 5-step portfolio rebalancing task to a worker agent with 0.01 ETH escrow, a 30-minute deadline, and a 60-second heartbeat interval. The operator role here is filled by an agent, not a human; the example would proceed identically if the operator were a human user, a DAO treasury contract, or any other principal.

| Time | Event | State |
|------|-------|-------|
| T+0s | Operator submits task; escrow locked | **IDLE** |
| T+5s | Operator confirms; agent begins execution | **RUNNING** |
| T+30s | Agent completes step 1 → writes checkpoint CID to IPFS → commits on-chain | RUNNING |
| T+65s | Agent completes step 2 → checkpoint 2 committed | RUNNING |
| T+95s | Agent completes step 3 → checkpoint 3 committed | RUNNING |
| T+120s | Agent calls CoinGecko API → HTTP 429 (rate limit) → agent process crashes | RUNNING |
| T+185s | Heartbeat missed (120s + 65s > 60s interval) → anyone calls `checkLiveness` | **FAILED** |
| T+186s | RecoveryRouter classifies: **LIVENESS** (*F* = 0.70); budget 85% remaining; deadline 88% remaining | FAILED |
| T+186s | Recovery score = *F*^0.80 × *B*^0.35 × *D*^0.15 = 0.70^0.80 × 0.85^0.35 × 0.88^0.15 = **0.752 × 0.945 × 0.981 = 0.697** | FAILED |
| T+186s | Score 0.697 ≥ 0.40 → route to RECOVERING (full scope) | **RECOVERING** |
| T+190s | FallbackPool selects highest-reputation agent for `defi.trade_execute` | RECOVERING |
| T+195s | Fallback reads checkpoints 1-3 from IPFS; resumes at step 4 | RECOVERING |
| T+230s | Fallback completes step 4 → checkpoint 4 committed | RECOVERING |
| T+270s | Fallback completes step 5 → task complete | **RESOLVED** |
| T+271s | Settlement: primary gets 60% (3/5 checkpoints), fallback gets 40% (2/5), minus 0.5% protocol fee | RESOLVED |

**Result without CAIRN:** The operator (agent or human) discovers the failure only on its next polling cycle — typically 4+ hours later for a human, or whenever the next health-check fires for an automated principal. Full restart. Original agent paid 0.

**Result with CAIRN:** Automatic detection in 65 seconds. Fallback resumes from step 4. Original agent paid 0.006 ETH for verified work (60% × 0.01 ETH escrow, minus 0.5% protocol fee). Total recovery time: ~85 seconds.

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
- **Not a centralized service.** Every state transition is enforced by the CAIRN state machine contract. No server. No admin key. No human-in-the-loop after task submission (the operator who submits the task may be a human, an agent, a DAO, or a contract — see Section 2.1).
- **Not optional infrastructure.** The escrow condition makes record-writing mandatory — agents cannot receive payment without completing the protocol.

---

## 3. Design Philosophy

### 3.1 Classify by Recoverability, Not Symptom

Prior research identifies 14+ failure modes in multi-agent systems [1], but existing taxonomies describe surface symptoms ("step repetition," "wrong tool selected") without prescribing what to do next. CAIRN's classification directly determines protocol behavior:

**LIVENESS failures** (*F* = 0.70) — the agent stopped responding. A heartbeat was missed, a process crashed, or a network partition occurred. These are almost always recoverable (~92% base rate): the task is not impossible, the agent simply died. A fallback can resume from the last checkpoint immediately.

**RESOURCE failures** (*F* = 0.30) — the agent exhausted a resource. Budget exceeded, deadline hit, API rate-limited, or context window overflowed. These are partially recoverable (~48% base rate): success depends on whether sufficient budget and deadline remain for the fallback.

**LOGIC failures** (*F* = 0.00) — the agent reasoned incorrectly. Step repetition loops, hallucinated outputs, or specification mismatches. These are rarely recoverable (~8% base rate): a fallback with the same task specification will likely fail the same way. Setting *F* = 0.00 routes all LOGIC failures directly to dispute.

This mapping is analogous to the foundational distinction between **crash faults** and **Byzantine faults** in distributed systems [8]. A crashed agent needs a different recovery path than an agent producing wrong outputs. CAIRN operationalizes this insight for the AI agent domain.

**Sub-class modulation.** Within each class, the failure type provides additional signal that the fallback agent uses for off-chain strategy selection (e.g., retry with different API key vs. reduced context vs. alternative model), though it does not affect the on-chain recovery score. The separation is deliberate: the score determines *whether* to attempt recovery (an on-chain decision requiring determinism), while the failure type informs *how* to attempt recovery (an off-chain decision that benefits from richness).

| Failure Class | Failure Types | On-Chain Score Impact | Off-Chain Strategy Impact |
|---|---|---|---|
| LIVENESS | HEARTBEAT_MISS, PROCESS_CRASH, NETWORK_PARTITION | Same (*F* = 0.70) | Fallback uses same approach vs. different node |
| RESOURCE | BUDGET_EXCEEDED, DEADLINE_HIT, RATE_LIMIT, CONTEXT_OVERFLOW | Same (*F* = 0.30) | Fallback uses different API key vs. smaller context vs. reduced scope |
| LOGIC | HALLUCINATION, SPEC_MISMATCH, STEP_LOOP, WRONG_TOOL | Same (*F* = 0.00) | N/A (routes to dispute) |

Future protocol versions may introduce sub-class weights if production data reveals that within-class recovery rate variance exceeds between-class variance for specific failure types.

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

> **Scope.** CAIRN's recovery guarantees apply *fully* to structured-pipeline tasks (data fetches, API calls, multi-step computations, stateful queries — see "Fully portable" and "Portable with context" rows below) and *partially* to reasoning-heavy tasks (chain-of-thought, planning with backtracking — "Framework-dependent"). For the framework-dependent class, only output-level checkpoints are portable; the fallback resumes the next subtask from the output of the previous one, losing any implicit reasoning state. The 23.46% misrouting result and the §6.6 economic analysis are calibrated for the first two classes, which we estimate cover ~80-90% of current on-chain agent workloads based on the task-type distribution observed in Olas and Virtuals deployments. Reasoning-heavy workloads receive degraded recovery rather than no recovery; quantifying the exact degradation requires empirical study, which is reserved for v3 (Section 10.1, open research questions).

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

### 4.1.3 Data Availability

**Checkpoint availability.** CAIRN requires checkpoint data availability for two windows: (1) the task duration (for fallback resumption) and (2) the dispute period (for arbiter evidence). Availability is ensured via:

- **Protocol-level pinning:** The CAIRN SDK pins all checkpoint CIDs to a configurable pinning service (default: Pinata) on commit. The protocol fee (Section 6.2) covers pinning costs for the task duration plus dispute period.
- **Operator-level redundancy:** Operators may specify additional pinning services at task submission.
- **Availability fallback:** If a checkpoint CID is unretrievable during recovery, the fallback resumes from the last available checkpoint (potentially losing work between the last available and the actual last checkpoint). If no checkpoints are retrievable, the task routes to DISPUTED.

Future versions may integrate Filecoin storage deals for cryptographic availability guarantees, or EIP-4844 blob storage for short-lived checkpoint data.

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

This ensures at least 10 liveness signals per task by default, with a 5-minute cap per interval. The v1 `isStale(taskId)` check triggers failure detection only after **two** consecutive missed intervals (i.e., `block.timestamp > lastHeartbeat + 2 × heartbeatInterval`), which widens the effective liveness window to absorb transient RPC or sequencer hiccups without false-positive failure detection. A single late heartbeat does not fail the task; two consecutive misses do.

**Progress detection.** Heartbeats confirm the agent process is alive but not that it is making progress. A stuck agent (infinite loop, hung API call) continues to heartbeat while producing no checkpoints. CAIRN detects this via a progress timeout: if no new checkpoint is committed within `max(heartbeat_interval × 4, expected_subtask_duration)`, the protocol considers the agent stalled. The operator can configure `expected_subtask_duration` at task submission (default: `deadline / total_expected_subtasks`).

Stalled agents are treated as RESOURCE failures (the agent has consumed time without producing output). The progress timeout is enforced by a public `checkProgress(taskId)` function analogous to `checkLiveness`.

**Gameability bound.** An adversarial worker emitting heartbeats while producing no useful work is bounded by the *tighter* of the two timeouts. Specifically: between any two consecutive checkpoints, an agent can stall for at most `max(4 × heartbeat_interval, expected_subtask_duration)` before `checkProgress` fires. With the default `heartbeat_interval = min(deadline / 10, 300s)` and the default `expected_subtask_duration = deadline / n_subtasks`, the worst-case stall window per subtask is the larger of:
- `4 × deadline / 10 = 0.4 × deadline` (heartbeat-bound)
- `deadline / n_subtasks` (subtask-bound)

For a typical task with `n_subtasks ≥ 5`, the subtask bound is tighter, capping stall time at ≤ 20% of deadline per subtask. For a task with very few subtasks (`n ≤ 3`), the heartbeat bound dominates and an adversarial worker can extract up to ~24% of deadline cost-free (slightly under the `4× heartbeat_interval` threshold). Operators submitting low-subtask tasks should set `expected_subtask_duration` explicitly rather than relying on the default; setting it to `1.5 × heartbeat_interval` reduces the gameable window to ~6% of deadline. This trade-off — tighter progress windows reduce gameability but increase false-positive stall detections on legitimately variable subtasks — is left to operator configuration rather than fixed by the protocol.

### 4.4 Fallback Pool Admission Control

Open registration creates a vulnerability: malicious or unreliable agents could register broadly, accept recovery assignments, and collect partial payment without completing work.

**Two-gate admission:**

**Gate 1 — Reputation:** Minimum ERC-8004 reputation score for the declared task type. Default threshold: score ≥ 50 on a 0-100 scale.

**Gate 2 — Stake:** Deposit proportional to maximum eligible escrow. Default: `min_stake = max_eligible_escrow × 0.1`. If the fallback agent fails without completing any checkpoints, the full stake is slashed and distributed to the operator.

**Optional: Olas Mech Marketplace integration.** When no internal fallback is available, CAIRN queries the Olas Mech Marketplace [5] for eligible agents by task capability, filtered by minimum reputation (85% success rate). This could extend the fallback pool to Olas's ~2,000 deployed mechs (≈500 active daily), subject to integration of CAIRN's checkpoint schema with the Olas execution model.

### 4.5 Arbiter Design

The arbiter role is itself an agent service. Arbiter agents register in CAIRN with a stake proportional to the maximum dispute value they can rule on (`min_arbiter_stake = max_dispute_value × 0.2`). They read public execution records, submit rulings, and earn fees (3% of dispute value).

Sybil resistance is economic: incorrect rulings (detectable via on-chain evidence) result in stake slashing. The stake at risk (20%) exceeds the fee earned (3%), making collusion uneconomical *for disputes where detectability holds* — see Section 7.5 Proposition 3 for the formal analysis and the explicit acknowledgment that detection probability is high for LIVENESS and RESOURCE disputes (on-chain evidence) but materially lower for LOGIC disputes (where "incorrect" is a reasoning judgment). The v2 specification ships single-tier arbitration with this caveat; an appeals layer (in the style of Kleros [19]) is reserved for v3.

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
  "failure_class": "LIVENESS",
  "failure_type": "HEARTBEAT_MISS",
  "checkpoint_count_at_failure": 3,
  "cost_at_failure": "0.0023 ETH",
  "budget_remaining_pct": 0.42,
  "deadline_remaining_pct": 0.31,
  "recovery_score": 0.47,
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

The execution history is on-chain and publicly indexable, growing with task throughput. As more agents complete tasks under CAIRN, the failure patterns, agent performance data, and cost distributions accumulate into a richer signal for every future routing and fallback-selection decision. Each new agent failure makes the protocol more valuable for every future agent.

**Quantitative model.** The intelligence layer's utility for a given task type *τ* is a function of the number of recorded failure and resolution events *n*<sub>τ</sub>:

```
Pattern confidence:     P(τ, n) = 1 − e^{−n/k}
Fallback accuracy:      F(τ, n) = F_0 + (F_max − F_0) × (1 − e^{−n/m})
```

Where:
- *k* = minimum records for 63% pattern confidence (estimated: *k* ≈ 30 per task type). The value *k* ≈ 30 follows from the sample size formula for a one-proportion *z*-test: *n* = (*z*<sub>α/2</sub>)² × *p*(1−*p*) / *d*², where *p* = 0.5 (failure rate), *d* = 0.10 (precision), *α* = 0.05 → *n* = 1.96² × 0.25 / 0.01 ≈ 96 total records. With a 45% LIVENESS proportion, we need ~96 × 0.45 ≈ 43 LIVENESS records — or roughly 30 records per class when amortized across the three classes.
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

**Cold-start bootstrap.** The initial 6 task types are `defi.price_fetch`, `defi.trade_execute`, `data.report_generate`, `governance.vote_delegate`, `compute.model_inference`, and a reserved `generic.*` catch-all. Using the simulation's 50% failure rate (base literature value [3], modulated downward to 36.8% observed in Section 10.1 once complexity and skill factors apply): at a protocol-wide throughput of **10 tasks/day**, 100 tasks per task type (≈ 60 days of operation) produces ~50 failure records per type — sufficient for 81% pattern confidence (1 − e<sup>−50/30</sup>). Reaching *k* = 30 records per type (63% confidence) takes ~36 days at this rate. When decomposed per failure class, the LOGIC path saturates last (~180 days to *k* = 30 LOGIC records per type), but this does not block protocol utility: LOGIC's recovery score is 0 by construction (Section 6.4), so it routes to dispute without needing pattern confidence for the recover/dispute decision. For the per-type aggregate decision (recover vs. dispute), minimum viable intelligence is reached in ~60 days.

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
- Configurable in the v2 upgradeable implementation (range: 0-500 bps); the v1 testnet contract declares `protocolFeeBps` as `constant`, so fee changes on v1 require a code redeployment rather than a parameter set.

### 6.3 Stake Requirements

| Role | Min Stake (v2) | Slash Condition | Slash Amount |
|------|----------------|-----------------|-------------|
| Fallback agent | 10% of max eligible escrow | Fails without completing any checkpoints | 100% of stake |
| Arbiter | 20% of max ruleable dispute | Incorrect ruling (detectable via evidence) | 50% of stake |

**Derivation of the 10% fallback stake.** The minimum stake must satisfy two simultaneous constraints. First, it must make zero-checkpoint failure *economically irrational* for any agent whose ex-ante success rate exceeds the admission floor — i.e., the expected loss from staking exceeds the expected gain from an unjustified acceptance. Combining the fallback acceptance condition (Proposition 2 in §7.5) with the slash mechanism: a fallback with success rate *s* faces expected gain `s · E_r · (c_f/c_total) · (1−f) − (1−s) · p_0 · stake`. For the admission floor *s* = 0.5 (reputation gate), zero-checkpoint failure probability *p*<sub>0</sub> ≈ 0.3 (empirical estimate from the simulation ground truth where failures cluster early), and the typical case `(c_f/c_total) ≈ 0.4` (fallback takes ~40% of work on recovery), the break-even stake is approximately `0.5 × 0.4 × E_r / (0.5 × 0.3) ≈ 1.33 × E_r`. Since `E_r ≤ E`, a stake of 10-15% of *maximum eligible escrow* across the agent's task portfolio satisfies this break-even with margin. Second, the stake must be small enough that capable agents will actually post it — 10% is large enough to deter Sybils but small enough that a reputable fallback can serve many tasks without locking excessive capital. Empirically, 10% is the floor used by similar staked-fallback designs (e.g., Olas's mech registration); CAIRN inherits this convention.

**Derivation of the 20% arbiter stake.** The arbiter stake must dominate the arbiter fee by a factor large enough to make collusion uneconomical. With fee φ = 3% of dispute value and slash amount 50% of stake on detection, the no-collusion condition is `bribe < φ + p_d × (slash/2 × stake) = 0.03V + p_d × stake/2`. Setting `stake = 0.20V` and `p_d = 0.8` (high-detection regime, on-chain evidence) yields `bribe < 0.03V + 0.08V = 0.11V` — the minimum bribe must exceed 11% of dispute value. For the LOGIC-dispute regime where *p*<sub>d</sub> ≈ 0.4, the same stake yields `bribe < 0.05V`, which is the residual structural risk discussed in §7.5 and §10.3. A higher stake (e.g., 30%) would tighten the LOGIC-dispute bound but at the cost of arbiter participation — 20% is the compromise that keeps arbiter capital cost roughly equal to ~6-7× the per-dispute fee, which we judge is the lowest acceptable risk-to-reward ratio that still attracts professional arbiters. The v1 testnet uses 15% pending the v2 upgrade.

The v1 testnet deployment currently enforces a **15% arbiter stake** (plus a 0.15 ETH absolute floor) rather than 20%. The v2 upgrade raises the ratio to 20% to strengthen the incentive analysis in Section 7.5. Under v1 parameters, the Proposition 3 inequality becomes `bribe < 0.03V + p_d × 0.075V`; the qualitative conclusion (honest ruling rational under realistic detection probabilities) is preserved, but the margin is tighter.

### 6.4 Recovery Score Formula *(v2 specification)*

**v2 formula (simulation-validated, this paper's headline result):**
```
r = F^a × B^b × D^c
```

Where *r* is the recovery score, expanded with default parameters as:
```
r = F^0.80 × B^0.35 × D^0.15
```

Where:
- *F* = `failure_class_weight`: LIVENESS = 0.70, RESOURCE = 0.30, LOGIC = 0.00
- *B* = `budget_remaining_pct`: (budget_cap - cost_accrued) / budget_cap
- *D* = `deadline_remaining_pct`: (deadline - current_block) / (deadline - start_block)
- (*a*, *b*, *c*) = governance-adjustable exponents; default (0.80, 0.35, 0.15)

**Three-tier routing (v2):**
- Score ≥ 0.40 → **RECOVERING** (high confidence — automatic fallback, full remaining budget)
- 0.35 ≤ Score < 0.40 → **RECOVERING (reduced scope)** (attempt with constraints — fallback receives capped budget)
- Score < 0.35 → **DISPUTED** (requires arbiter resolution)

> **v1 interim formula (current testnet deployment).** The v1 contract on Base Sepolia implements the pre-calibration linear formula `r = 0.5·F + 0.3·B + 0.2·D` with class weights (0.90, 0.50, 0.10) and a single binary threshold at 0.30 — the 47.56%-misrouting baseline called "Eq1-current" in Section 10.1. The calibration work in this paper motivates the v2 upgrade path: replace the linear formula with the multiplicative formula above, move class weights to (0.70, 0.30, 0.00), and introduce the three-tier threshold band (0.40 / 0.35). The migration is governance-gated and does not require a state-breaking upgrade, because the score formula is already isolated behind the `IRecoveryRouter` interface in the v1 contract architecture.

The three-tier model enables graduated recovery: high-confidence failures get full resources, medium-confidence failures get a constrained attempt before escalating to dispute, and low-confidence failures go directly to arbitration.

**Why multiplicative.** The formula uses a product rather than a weighted sum because recovery success depends on *all* factors being adequate simultaneously. If budget is zero, recovery is impossible regardless of failure type or deadline. If the failure is a LOGIC error (*F* = 0.00), no amount of budget or time helps. The multiplicative structure captures this "any-factor-kills-it" dynamic: when any input approaches zero, the score approaches zero — matching empirical recovery dynamics.

This design choice is empirically validated. Monte Carlo simulation across 100,000 synthetic task-failure events per run (seed=42, reproducible via `python3 -m simulation.run_eq4`) systematically compared four formula structures across 16 experiments: (1) linear weighted sum — optimal 33.81% misrouting (Run 1, 362 grid points); (2) piecewise-linear with *B*×*D* interaction — 33.17% (Run 2); (3) 5-variable linear with complexity and skill inputs — 32.78% (Run 3); and (4) multiplicative — **23.46%** (Run 4, 2,646 grid points). The first three formulas converge to a ~33% misrouting floor — a structural ceiling intrinsic to additive formulas, confirmed across 3,008 configurations. The multiplicative formula breaks through to 23.46%, within **0.93 percentage points of the Bayes-optimal theoretical minimum (22.53%)** — capturing 96% of achievable improvement. A hybrid α-sweep (11 ratios from α=0.0 pure multiplicative to α=1.0 pure linear) confirms that pure multiplicative is strictly optimal: misrouting increases monotonically with α (23.46% at α=0, 24.57% at α=0.1, 26.27% at α=0.5, 35.07% at α=1.0). Cross-task-type leave-one-out validation shows 23.39% ± 0.36% across five task types — best generalization of any formula tested. Most importantly, the confusion matrix pivots: **FULL-tier false positives drop from 22.3% (Eq1 linear) to 7.9% (Eq4 multiplicative) — a 65% reduction in wasted recovery attempts.** Full methodology, per-experiment findings, and confusion matrices are documented in Section 10.1; raw results in `simulation/RESULTS_EQ4.md`.

**Exponent rationale.** The failure class exponent *a* = 0.80 makes *F* the dominant factor: a LIVENESS failure (*F* = 0.70) produces *F*^0.80 ≈ 0.752, while a RESOURCE failure (*F* = 0.30) produces *F*^0.80 ≈ 0.382 — roughly a 2× separation (precise ratio 1.97). The sub-linear exponent provides diminishing returns above *F* = 0.5, preventing the class signal from overwhelming resource signals. The budget exponent *b* = 0.35 assigns moderate influence: 50% budget remaining yields *B*^0.35 = 0.79, while 10% yields *B*^0.35 = 0.47 — a meaningful but not catastrophic penalty. The deadline exponent *c* = 0.15 assigns the least weight: in the multiplicative context, deadline contributes through the product interaction (low deadline × low budget is catastrophic) more than through its individual exponent. All exponents are governance-adjustable parameters (see Section 8).

**Class weight rationale.** LIVENESS failures (agent crashes, API timeouts) have the highest base recovery rate (~92% when resources are available), justifying *F*<sub>LIVENESS</sub> = 0.70. RESOURCE failures (budget exhaustion, context overflow) are partially recoverable (~48%), justifying *F*<sub>RESOURCE</sub> = 0.30. LOGIC failures (reasoning errors, hallucinations, spec mismatches) have ~8% base recovery rate — a different agent retrying the same reasoning task rarely succeeds. Setting *F*<sub>LOGIC</sub> = 0.00 routes all LOGIC failures directly to dispute, which is the economically correct decision: the expected value of a recovery attempt (8% × escrow saved) is less than the expected cost (92% × wasted fallback budget).

**Threshold rationale.** The Bayes-optimal three-tier sweep (Exp 13) identified `(upper, lower) = (0.50, 0.45)` as the threshold pair that minimises overall misrouting against the ground-truth probability *p*. CAIRN ships `(0.40, 0.35)` instead. The deviation is deliberate, not an error:

- **Asymmetric cost.** The Bayes-optimal objective treats false positives and false negatives symmetrically — every misroute counts equally. In production economics they do not. A false positive (recovery attempted that fails) wastes ~50% of the remaining escrow plus the fallback agent's gas and reputation; a false negative (recoverable task disputed) costs the operator only the 3% arbiter fee plus a 7-day delay. Section 6.6 quantifies the asymmetry: at *E* = 0.01 ETH, a FULL-tier FP costs ~10× more than an FN. The Bayes-optimal threshold treats these as equivalent; CAIRN's lower thresholds shift the routing band toward the *cheaper* error mode (more FNs, fewer FPs), which the §6.6 confusion matrix confirms (Eq4 FULL-FP drops to 7.9% vs Bayes's 9.2%, FN rises to 12.2% vs Bayes's 13.0%).
- **Coverage objective.** The narrow band `[0.35, 0.40)` is small by design: the multiplicative formula's primary value is the binary recover/dispute decision, not the FULL/REDUCED distinction. Setting both thresholds near the Bayes-optimal *lower* boundary (0.45) maximises the set of tasks routed to *some* recovery attempt rather than to immediate dispute, which is the operator-friendly bias.
- **Headroom check.** Worked example: LIVENESS at *B*=0.85, *D*=0.88 yields *r* = 0.697, comfortably above 0.40. RESOURCE failures span 0.25-0.45 depending on resources, sitting exactly in the discriminating band. LOGIC failures score 0 regardless.

All thresholds are governance-adjustable parameters (Section 8) — an operator population with different cost ratios can move toward (0.50, 0.45) for symmetric-cost optimisation, or further down for even more aggressive recovery bias.

**Solidity implementation.** The multiplicative formula requires fixed-point exponentiation. Since only three failure class weights exist (0.70, 0.30, 0.00), the *F*^*a* term is implemented as a lookup (3 pre-computed values), eliminating the most expensive `pow` call. The remaining *B*^*b* and *D*^*c* terms use PRBMath's `pow` function (~3,000 gas each) or a binned lookup table for further gas savings. Total cost: ~2,500-6,200 gas depending on implementation — negligible on Base L2 (see Section 6.5).

### 6.5 Gas Costs

All operations are designed for Base L2, where gas is inexpensive. The `recoveryScore` and `classifyAndScore` rows below are **measured** values from `forge test --gas-report` against the v2 reference implementation `RecoveryRouterV2.sol` (24-test suite, 339 tests overall passing on this branch); the remaining rows are design-target estimates pending a full v2 system benchmark. The raw report is committed at `contracts/gas-report-v2-router.txt`.

| Operation | Gas | Cost @ 0.01 gwei Base L2 | Cost @ $2,500/ETH | Source |
|-----------|-----|--------------------------|-------------------|--------|
| `submitTask` | ~180,000 (estimate) | 1.8 × 10⁻⁶ ETH | $0.0045 | design target |
| `commitCheckpointBatch` (1 checkpoint, v2) | ~80,000 (estimate) | 8.0 × 10⁻⁷ ETH | $0.0020 | design target |
| `commitCheckpointBatch` (10 checkpoints, v2) | ~100,000 (estimate) | 1.0 × 10⁻⁶ ETH | $0.0025 | design target |
| `heartbeat` | ~45,000 (estimate) | 4.5 × 10⁻⁷ ETH | $0.0011 | design target |
| `settle` (escrow distribution) | ~140,000 (estimate) | 1.4 × 10⁻⁶ ETH | $0.0035 | design target |
| `RecoveryRouterV2.computeRecoveryScore` (full multiplicative path) | **19,935 max / 5,748 avg / 524 min** (measured) | 2.0 × 10⁻⁷ ETH max | $0.00050 max | measured |
| `RecoveryRouterV2.classifyAndScore` (called from CairnCore on failure) | **53,680 max / 39,017 avg / 24,354 min** (measured) | 5.4 × 10⁻⁷ ETH max | $0.00134 max | measured |
| `RecoveryRouterV2` deployment cost | 1,224,782 (measured) | 1.2 × 10⁻⁵ ETH | $0.031 | measured |

The 0.01 gwei assumption reflects typical post-Dencun Base L2 gas prices; actual L2 execution gas has ranged from below 0.001 gwei (low congestion) to approximately 0.1 gwei (high congestion) per BaseScan. Base transactions also carry an L1 publication fee (~1-5% of total cost at typical congestion) that is not included in the table above and can dominate at very low L2 gas prices. Dollar figures should therefore be read as order-of-magnitude estimates, not contractual guarantees.

The measured v2 `computeRecoveryScore` average of **5,748 gas** is *better* than the design-target estimate (~6,200 gas) used in earlier drafts. The maximum observed (~20,000 gas) corresponds to the full multiplicative path with two PRBMath UD60x18 `pow` calls; the median (~1,348 gas) is dominated by short-circuit paths (LOGIC class returning 0, or zero-budget early termination — see `_computeScore` in `RecoveryRouterV2.sol`). The minimum (524 gas) is the LOGIC short-circuit alone. The pre-computed *F*^0.80 lookup (0.7518 for LIVENESS, 0.3817 for RESOURCE, 0 for LOGIC, all at 18-decimal fixed-point precision) eliminates one PRBMath `pow` call per score; the remaining two `pow` calls (for *B*^0.35 and *D*^0.15) account for most of the gas.

PRBMath UD60x18 v4.1.1 is integrated in v2 (`@prb/math/UD60x18.sol`); v1 has no fixed-point math dependency.

Merkle batching in the v2 `commitCheckpointBatch(taskId, count, merkleRoot, latestCID)` function reduces checkpoint gas by approximately 95% compared to per-CID storage. A 50-checkpoint task is expected to cost approximately 100,000 gas for a single batch commit versus an estimated 3,350,000 gas for 50 sequential commits at ~67,000 gas each (linear extrapolation; to be validated by benchmark). The v1 MVP contract uses a simpler non-batched `commitCheckpoint(taskId, cid)` and does not realize this reduction; batching is a v2 feature.

### 6.6 Economic Impact of Misrouting

The multiplicative formula's 23.46% misrouting rate (Section 6.4, Run 4 / Exp 14) has a concrete economic cost derived from the Run 4 confusion matrix (Section 10.1, Experiment 14). All percentages in this section are **joint probabilities** P(Routed = *x* ∧ Outcome = *y*) expressed over the full event population — *not* conditional rates such as P(Failed | Routed to Recover). The joint-probability basis is what matters for aggregate cost; the conditional FP/FN rates (31.10% / 19.09% for Eq4) appear elsewhere in the simulation outputs and reflect a different denominator.

| Error Type | Rate (Eq4) | Rate (Eq1 Linear) | Cost per Error | Cost per 1,000 Tasks (Eq4) |
|---|---|---|---|---|
| False positive — FULL tier (full budget wasted) | 7.9% | 22.3% | ~50% of remaining escrow | 79 × 0.50 × *E*<sub>rem</sub> |
| False positive — REDUCED tier (capped budget wasted) | 5.4% | 3.8% | ~25% of remaining escrow | 54 × 0.25 × *E*<sub>rem</sub> |
| False negative — DISPUTED-but-recoverable | 12.2% | 7.7% | Arbiter fee (3% of escrow) + 7-day delay | 122 × 0.03 × *E* |

At an average escrow *E* = 0.01 ETH with 50% remaining-budget *E*<sub>rem</sub> = 0.005 ETH at failure (so per 1,000 tasks, each percentage-point of joint probability corresponds to 10 events):

- FULL-tier FP: 79 × 0.50 × 0.005 ETH = **0.198 ETH / 1,000 tasks**
- REDUCED-tier FP: 54 × 0.25 × 0.005 ETH = **0.068 ETH / 1,000 tasks**
- FN (arbiter fee only, delay cost not monetized): 122 × 0.03 × 0.01 ETH = **0.037 ETH / 1,000 tasks**
- **Total Eq4 misrouting cost: ~0.303 ETH / 1,000 tasks (~$758 at $2,500/ETH, i.e., ~$0.76 per task).**

**Versus the current Eq1 formula (v1 testnet deployment).** Applying the same cost model to the Run 1 Eq1-current confusion matrix (RESULTS.md §9: FULL+Failed 13.1%, REDUCED+Failed 34.0%, DISPUTED+Succeeded 0.5%):

- FULL-tier FP: 131 × 0.50 × 0.005 ETH = 0.3275 ETH / 1,000 tasks
- REDUCED-tier FP: 340 × 0.25 × 0.005 ETH = 0.4250 ETH / 1,000 tasks
- FN: 5 × 0.03 × 0.01 ETH = 0.0015 ETH / 1,000 tasks
- **Total Eq1 misrouting cost: ~0.754 ETH / 1,000 tasks (~$1,885).**

The multiplicative v2 formula therefore saves **~0.451 ETH / 1,000 tasks (~$1,128)**, a **60% reduction** in misrouting cost. The residual 0.93pp gap above the Bayes-optimal floor (22.53%) bounds the maximum further savings from calibration at roughly 0.012 ETH / 1,000 tasks (~$30) — essentially exhausted.

Relative to deployed escrow capital (10 ETH of escrow across 1,000 tasks at *E* = 0.01): Eq4 misrouting costs **~3.0% of escrow value**; Eq1-current costs ~7.5%. Eq4 reduces the friction on deployed escrow by ~2.5× — an acceptable overhead for permissionless, trustless automated recovery.

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

**L2 sequencer trust dependency.** Base is operated by a single centralised sequencer (Coinbase, as of April 2026). For a protocol that markets "trustless" recovery, this dependency requires explicit treatment:

- **Liveness:** if the Coinbase sequencer is offline or refuses to include CAIRN transactions, the entire protocol pauses — `checkLiveness`, `commitCheckpointBatch`, `settle`, and arbiter rulings cannot execute. This is a censorship/availability risk shared with every Base-deployed protocol. The mitigation Base provides today is a "force inclusion" escape hatch through L1, but it adds latency (hours-to-days, depending on Base's exact bridge cadence) that exceeds CAIRN's heartbeat intervals; force-included transactions would arrive too late to prevent stale failures.
- **Ordering:** the sequencer chooses the in-block order of transactions. For CAIRN this matters in two cases: (i) a worker agent submitting a just-in-time `heartbeat` racing against an enforcer's `checkLiveness`, and (ii) a fallback agent committing checkpoints racing against the deadline. In both cases the sequencer can pick a winner. The atomicity of CAIRN's failure path (detection → classification → routing in one transaction) limits the MEV surface to ordering only — there is no mid-transaction state insertion — but ordering alone is sufficient to extract value in adversarial scenarios.
- **Honesty assumption:** CAIRN implicitly assumes the sequencer is not actively collaborating with one party to a dispute. This assumption is weaker than the underlying L1 trust model and is the principal residual trust dependency in v2. Base's roadmap toward decentralised sequencing (planned via the Optimism Superchain stack) will reduce this dependency over time; until then, CAIRN inherits the same trust assumption as every other Base-deployed application.
- **Migration mitigation:** the protocol is portable to any EVM L2 with comparable gas economics. A future deployment to a chain with decentralised sequencing (e.g., a future iteration of the OP Stack with shared sequencing, or an Arbitrum Nitro chain with permissionless validators) would remove the single-sequencer dependency without protocol changes.

### 7.3 Attack Vectors and Mitigations

| Attack | Severity | Mitigation |
|--------|----------|------------|
| **Checkpoint gaming** — Agent commits fake checkpoints to inflate payment | High | v2: schema hash validation on commit (the `specHash` stored at task initialization is matched against each checkpoint payload); off-chain content verification; reputation decay for invalid submissions. (v1 stores `specHash` but does not enforce per-checkpoint validation — the v2 upgrade activates this check.) |
| **Liveness griefing** — Attacker calls `checkLiveness` to force premature failure | Low | Only succeeds if heartbeat interval actually elapsed; false calls revert; attacker pays gas |
| **Fallback Sybil** — Attacker registers many agents to capture recovery assignments | Medium | Reputation gate (min 50) + stake requirement (10%); 100% slash on zero-checkpoint failure |
| **Arbiter collusion** — Arbiter rules in favor of colluding agent | Medium | Stake (20%) > fee (3%); incorrect rulings slashed; commit-reveal prevents front-running |
| **Recovery score manipulation** — Agent times failure for desired routing | Low | All score inputs on-chain; agent cannot control failure classification retroactively |
| **Intelligence poisoning** — False failure records to mislead future agents | Medium | Records auto-written by protocol, not by agents; content matches on-chain state |
| **Sequencer reordering (MEV)** — Block builder reorders `checkLiveness` and a just-in-time `heartbeat` to extract value | Low | Atomic detection → classification → routing within a single tx; MEV surface limited to ordering, not mid-tx state insertion; heartbeat interval must actually have elapsed for enforcement to succeed |

### 7.4 Protocol Invariants

These properties hold at all times:

1. **Escrow safety.** Escrow is not released until `state == RESOLVED`.
2. **Deterministic scoring.** Same on-chain inputs produce the same recovery score. No external dependencies.
3. **Checkpoint immutability.** Committed checkpoint CIDs cannot be modified or deleted.
4. **State irreversibility.** No backward state transitions. The DAG is `IDLE → RUNNING → {FAILED, RESOLVED}; FAILED → {RECOVERING, DISPUTED}; RECOVERING → {RESOLVED, DISPUTED}; DISPUTED → RESOLVED; RESOLVED → terminal`. The `RECOVERING → DISPUTED` edge exists in the v2 specification as a direct transition when the fallback agent itself fails (FallbackFailed event in §2.2.1, triggered by missed heartbeat or deadline exceeded during the fallback phase). In v1, this transition is reached *indirectly* via the fallback's failure re-entering the FAILED state and then being re-routed; v2 surfaces it as a direct edge to make the state graph match the formal model in this paper. The reachable state set is identical in both versions; v2 changes only the path, not the destinations.
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

**Faking checkpoints** is strictly dominated under v2: invalid CIDs are rejected by schema hash validation (the `specHash` committed at task initialization and matched against each checkpoint payload). Under v1 (where per-checkpoint validation is not yet enforced), the equilibrium is preserved by reputation decay alone — repeated invalid submissions push agents below the fallback pool admission threshold (Section 4.4). The v2 upgrade hardens this from an economic disincentive into an on-chain invariant. ∎

#### Game 2: Fallback Acceptance

**Proposition 2 (Rational Fallback Acceptance).** *A fallback agent with success rate s<sub>τ</sub> for task type τ should accept a recovery assignment when the expected payoff exceeds zero:*

```
s_τ × E_r × (c_f / c_total) × (1 − f) > (1 − s_τ) × p_0 × stake
```

*where E<sub>r</sub> is remaining escrow, c<sub>f</sub>/c<sub>total</sub> is the fallback's expected checkpoint share, and p<sub>0</sub> is the probability of zero-checkpoint failure (triggering 100% slash).*

*Proof.* A fallback agent accepting an assignment faces a binary outcome:
- With probability *s*<sub>τ</sub> (success), the fallback earns its share of remaining escrow after the protocol fee: gain = *E*<sub>r</sub> × (*c*<sub>f</sub> / *c*<sub>total</sub>) × (1 − *f*).
- With probability (1 − *s*<sub>τ</sub>) (failure), the fallback either (i) completes at least one checkpoint and earns partial payment without stake loss, or (ii) fails without any checkpoint and is slashed 100% of stake.

Let *p*<sub>0</sub> denote the conditional probability of zero-checkpoint failure given failure — the sole slash trigger. Expected payoff:

```
E[payoff] = s_τ · E_r · (c_f / c_total) · (1 − f)  −  (1 − s_τ) · p_0 · stake
```

Acceptance is rational when E[payoff] > 0, yielding the stated inequality. Three remarks: (a) at *s*<sub>τ</sub> = 1 the condition reduces to a trivially positive gain, recovering the intuition that a perfectly competent fallback always accepts; (b) the fallback's own gas cost *g* and opportunity cost are absorbed into *E*<sub>r</sub> for brevity (subtract them from the left side to obtain the stricter form); (c) the admission gates (reputation ≥ 50, stake ≥ 10%) enforce a lower bound on *s*<sub>τ</sub> by construction, so low-competence agents never reach the decision. ∎

This self-selection mechanism is beneficial: agents with low success rates for a given task type will rationally decline recovery assignments, ensuring only capable agents accept.

#### Game 3: Arbiter Ruling

**Proposition 3 (Arbiter Honesty).** *For an arbiter with stake s = 0.2V (where V is the dispute value), fee φ = 0.03V, and detection probability p<sub>d</sub> for incorrect rulings, honest ruling is the rational strategy when:*

```
bribe < φ + p_d × 0.5s = 0.03V + p_d × 0.1V
```

*Proof.* The arbiter chooses between honest and dishonest ruling:
- **Honest payoff:** +*φ* = +0.03*V*
- **Dishonest payoff:** +bribe − *p*<sub>d</sub> × 0.5*s* = bribe − *p*<sub>d</sub> × 0.1*V*

For dishonesty to be rational, the bribe must exceed the honest fee plus the expected penalty: bribe > 0.03*V* + *p*<sub>d</sub> × 0.1*V*.

The detection probability *p*<sub>d</sub> varies sharply by dispute type, and this is the central weakness of the analysis. For **LIVENESS** disputes (was a heartbeat actually missed?) and **RESOURCE** disputes (was the budget actually exhausted?), all evidence is on-chain — heartbeat timestamps, cost accruals, deadline blocks are publicly verifiable — so *p*<sub>d</sub> ≥ 0.8 is conservative. With *p*<sub>d</sub> = 0.8 the minimum bribe is 0.03*V* + 0.08*V* = 0.11*V*.

**Multi-dispute analysis:** For LIVENESS/RESOURCE classes, an arbiter who colludes in *k* disputes has cumulative detection probability 1 − (1 − *p*<sub>d</sub>)<sup>k</sup>. At *p*<sub>d</sub> = 0.8: a single dispute has 80% detection risk; two disputes have 96%; three disputes have 99.2%. Sustained collusion is therefore economically irrational for these classes — expected losses compound exponentially while gains are linear.

**The arbiter-recursion problem.** Proposition 3's economic guarantee breaks down for **LOGIC** disputes ("did the agent hallucinate?", "did the output match the specification?"). Arbiters are themselves agents reasoning about reasoning errors; the dispute being judged and the judge are drawn from the same population. Whether a ruling is "incorrect" is not always detectable from on-chain evidence — for genuine LOGIC disputes the detection signal is itself an inference about reasoning quality, not a comparison against a timestamp. We estimate *p*<sub>d</sub> for the hardest LOGIC cases at 0.3-0.5 rather than 0.8, which raises the minimum bribe to roughly 0.045*V*-0.08*V* — still meaningful, but a much narrower margin than the on-chain-evidenced classes.

This is the same structural problem encountered by Kleros and other on-chain dispute-resolution protocols [19]: a sufficiently capable adversary can craft a dispute where the "correct" answer is genuinely contestable, and detection requires either (a) an appeals layer that defers to ever-larger juries with diminishing returns, or (b) an external ground-truth oracle that re-introduces a trust assumption. CAIRN inherits this limitation. The mitigations the protocol does provide — high reputation gates for arbiter admission, commit-reveal to prevent pre-arrangement, multi-dispute compounding for repeat offenders — bound the worst case but do not eliminate it. Section 10.3 lists this as a known limitation; the v2 specification ships **single-tier arbitration**, and a future appeals layer (multi-juror with bonded escalation, in the Kleros style) is reserved for protocol v3.

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
| Recovery threshold (upper) | 0.40 | 0.1-0.9 | Score threshold for full-scope RECOVERING |
| Recovery threshold (lower) | 0.35 | 0.1-0.9 | Score threshold for reduced-scope RECOVERING vs DISPUTED |
| Recovery exponent *a* | 0.80 | 0.1-2.0 | Exponent for failure class weight in Equation 1 |
| Recovery exponent *b* | 0.35 | 0.1-2.0 | Exponent for budget remaining in Equation 1 |
| Recovery exponent *c* | 0.15 | 0.1-2.0 | Exponent for deadline remaining in Equation 1 |
| *F*<sub>LIVENESS</sub> | 0.70 | 0-1.0 | Failure class weight for LIVENESS failures |
| *F*<sub>RESOURCE</sub> | 0.30 | 0-1.0 | Failure class weight for RESOURCE failures |
| *F*<sub>LOGIC</sub> | 0.00 | 0-1.0 | Failure class weight for LOGIC failures |

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

**ERC-8004 (Trustless Agents).** Provides agent identity and reputation registries. Live on Ethereum mainnet since January 29, 2026, with ~49,000 registered agents across 30+ EVM chains as of February 2026 [14]. CAIRN reads reputation scores for fallback pool admission and writes outcome signals (success/failure attestations) after task completion.

**ERC-7710 (Delegation Framework).** Enables scoped permission transfer. CAIRN uses ERC-7710 for pre-authorized fallback delegation: the operator grants CAIRN permission to sub-delegate task authority to a fallback agent at recovery time, without requiring a new operator signature.

**ERC-8211 (Smart Batching).** Enables AI agents to execute complex DeFi operations in a single batched transaction [16]. Composable with CAIRN: checkpoints can wrap ERC-8211 batched executions.

### 9.3 Off-Chain Coordination Protocols

**Google A2A (Agent-to-Agent Protocol).** Donated to the Linux Foundation (June 2025) with 100+ industry partners [12]. Handles agent discovery via Agent Cards, task delegation, and collaboration via context sharing. A2A is the off-chain communication layer; CAIRN is the on-chain settlement and recovery layer. A2A tells agents what to do; CAIRN guarantees what happens when it fails.

**Anthropic MCP (Model Context Protocol).** Connects agents to tools and data sources [13]. Adopted by OpenAI, Microsoft, Google, Amazon. MCP provides the tool access; CAIRN provides the fault tolerance. When an MCP tool call fails mid-task, CAIRN's checkpoint system preserves completed work and the fallback mechanism ensures completion.

### 9.4 Academic Foundations

CAIRN builds on established theory:

- **Distributed checkpointing.** The Chandy-Lamport algorithm [8] proves that consistent global state can be reconstructed from local checkpoints. CAIRN adapts this for AI agent semantics with IPFS-stored, schema-validated checkpoints.

- **Mechanism design.** Staking and slashing mechanisms are proven at over $100 billion in staked value in Ethereum Proof-of-Stake [9]. CAIRN applies the same principle: stake capital to participate, lose it for misbehavior.

- **Multi-agent failure analysis.** The MAST taxonomy [1] provides the most comprehensive classification of multi-agent failure modes to date. CAIRN's contribution is to add the recoverability dimension — classifying failures by what action to take, not by what went wrong.

---

## 10. Future Work

### 10.1 Open Research Questions

**Checkpoint semantic portability.** CAIRN's checkpoint format is portable across frameworks (schema-validated IPFS CIDs), and Section 4.1.1 establishes that fully portable and portable-with-context checkpoints cover the majority of practical task types (data fetches, API calls, multi-step computations, stateful queries). However, for complex reasoning chains with implicit context (chain-of-thought, multi-turn dialogue), semantic portability remains unproven. Empirical study of checkpoint portability across LangGraph, CrewAI, and Olas agent architectures is planned.

**Recovery score calibration — empirical validation.** The recovery score formula (Section 6.4) has been validated via a Monte Carlo simulation suite of 100,000 synthetic task-failure events per run, seed=42, fully reproducible (Reference [18]). The simulation compared four formula structures across **16 experiments organized into 4 runs**. Run 1 evaluated 362 configurations (55 weight vectors + 245 class-weight vectors + 62 threshold pairs, sequential grid refinement); Run 4 evaluated 2,646 multiplicative-formula configurations; Runs 2-3 used staged grid refinement within the extended parameter space (counts emit to `stdout` at runtime).

*Run summary.* Each run tested a distinct formula hypothesis:

| Run | Formula | Structure | Variables | Misrouting Rate |
|-----|---------|-----------|-----------|----------------|
| 1 | *r* = *w*<sub>f</sub>*F* + *w*<sub>b</sub>*B* + *w*<sub>d</sub>*D* | Linear | 3 (*F*, *B*, *D*) | 47.56% (current) → **33.81%** (optimized) |
| 2 | Run 1 + piecewise cliffs + *w*<sub>int</sub>·*B*·*D* interaction | Linear + non-linear | 3 + 4 cliff params + 1 interaction | **33.17%** |
| 3 | Run 1 + *w*<sub>c</sub>·*C* (complexity) + *w*<sub>s</sub>·*S* (fallback skill) | Linear | 5 (adds *C*, *S*) | **32.78%** |
| **4** | ***r* = *F*^*a* × *B*^*b* × *D*^*c*** | **Multiplicative** | **3 (*F*, *B*, *D*)** | **23.46%** |
| — | Bayes-optimal three-tier (thresholds 0.50/0.45) | Perfect oracle (ground-truth *p*) | — | 22.53% |

Runs 1-3 exhaustively proved that any additive formula — regardless of non-linear terms or additional variables — converges to a ~33% misrouting structural ceiling. The **"93/4/3 rule"** emerged: 93% of achievable improvement comes from weight tuning within the linear formula, 4% from non-linear terms, and 3% from adding variables. The ceiling exists because additive formulas cannot express the "any-factor-kills-it" dynamic: in reality, zero budget means zero recovery chance regardless of failure type, but a sum always produces a positive value from the remaining terms.

Run 4 changed the formula structure to multiplicative. The result — 23.46% misrouting — captures 96% of the theoretically achievable improvement and lies within 0.93 percentage points of the Bayes-optimal three-tier baseline (22.53%). The binary Bayes-optimal floor is 22.52%, confirming that the 22.5% irreducible noise is intrinsic to the stochastic ground truth rather than to the three-tier structure.

*Experiment catalog.* Each experiment answered a distinct calibration question:

| Exp | Run | Name | Method | Key Finding | Delta |
|-----|-----|------|--------|-------------|-------|
| 1 | 1 | Weight optimization | Grid search over 55 *(w<sub>f</sub>, w<sub>b</sub>, w<sub>d</sub>)* simplex points | Current weights rank #31/55; deadline should dominate (*w<sub>d</sub>* ≥ 0.40) | −5.35pp |
| 2 | 1 | Class weight optimization | Grid search over 245 *(F<sub>L</sub>, F<sub>R</sub>, F<sub>Log</sub>)* combinations | *F*<sub>LOGIC</sub> → 0.00 routes 8%-base-rate failures to dispute; current ranks #161/245 | −4.43pp |
| 3 | 1 | Threshold optimization | Grid search over 62 (upper, lower) pairs | Optimal band 0.45/0.40 is 6× tighter than current 0.60/0.30 | −3.97pp |
| 4 | 1 | Weight sensitivity | ±5/10/15/20% perturbation on each weight | *w<sub>f</sub>* most sensitive (+4.56pp at +20%); stable within ±10% | — |
| 5 | 1 | Cross-task LOO-CV | Leave-one-type-out across 5 task types | 37.65% ± 0.68% — generalizes across domains | — |
| 6 | 2 | Piecewise + interaction grid | Staged grid over (*w*, *b*<sub>crit</sub>, *d*<sub>crit</sub>, penalties, *w*<sub>int</sub>) | Optimal: *b*<sub>crit</sub>=0.10, *d*<sub>crit</sub>=0.05, *w*<sub>int</sub>=0.25 | −0.64pp |
| 7 | 2 | Ablation: cliff vs interaction | Compare cliff-only, interaction-only, combined | Cliffs contribute **−0.01pp** (inert); interaction contributes **−0.63pp** | — |
| 8 | 2 | Eq2 sensitivity | ±20% perturbation on 8 Eq2 parameters | All 4 piecewise parameters have **zero sensitivity** — structurally inert | — |
| 9 | 3 | 5-variable weight optimization | Grid search with *w<sub>c</sub>*, *w<sub>s</sub>* added | Optimizer assigns minimum (0.05) to both new variables; at Eq1 thresholds the 5-var weight change alone produces 34.98% (+1.17pp vs Eq1-opt). Improvement arrives only when re-tuned thresholds (Exp 10) are applied. | +1.17pp at Eq1 thresholds |
| 10 | 3 | 5-variable threshold optimization | Threshold grid for Eq3 scores | Optimal: upper=0.50, lower=0.45 — tighter than Eq1's 0.45/0.40 | −1.00pp |
| 11 | 3 | Variable ablation | Solo complexity, solo skill, both | Solo: −0.86pp (complexity), −0.87pp (skill); combined: −0.55pp (**subadditive** — linear sum cannot capture the multiplicative *C*·*S* ground-truth interaction) | — |
| 12 | 3 | 5-var cross-task LOO-CV | Leave-one-type-out on Eq3 | 32.37% ± 0.36% — generalizes; confirms ~33% ceiling is structural, not data-specific | — |
| 13 | 4 | Bayes-optimal baseline | Route using ground-truth *p* directly | Binary floor 22.52%; three-tier floor 22.53% — any formula ≤25% is near-optimal | — |
| 14 | 4 | Multiplicative grid search | 2,646 Phase-A configs (9×7×7 exponent triples × 6 coarse threshold pairs) + 53 Phase-B threshold refinements at best exponents | Optimal: (0.80, 0.35, 0.15), thresholds 0.40/0.35 | −10.35pp vs Eq1 |
| 15 | 4 | Hybrid α-sweep | *r* = α·Eq1 + (1−α)·Eq4 at 11 α values | Monotonic: α=0.0 best (23.46%), α=1.0 worst (35.07%) — every increment of linear component strictly degrades routing | — |
| 16 | 4 | Multiplicative cross-task LOO-CV | Leave-one-type-out on Eq4 | 23.39% ± 0.36% — best generalization of any run | — |

*Ground-truth model validation.* Before any optimization, the synthetic ground truth was validated against published literature [1][2][3]. The model is calibrated — not invented — from prior empirical studies:

| Check | Expected (from literature) | Observed (simulation) | Deviation |
|---|---|---|---|
| LIVENESS class frequency | ~45% | 44.96% | 0.04pp |
| RESOURCE class frequency | ~35% | 34.87% | 0.13pp |
| LOGIC class frequency | ~20% | 20.17% | 0.17pp |
| LIVENESS recovery at high resources | ~92% | 71.4% | Base rate × complexity/skill factors |
| RESOURCE recovery at high resources | ~48% | 37.9% | Same modulation |
| LOGIC recovery at high resources | ~8% | 5.4% | Same modulation |
| Overall recovery rate | ~50% [3] | 36.8% | Complexity/skill factors pull rate below base |

Class frequencies match literature to within 0.17pp. Recovery rates are proportionally scaled down by the complexity and skill factors, which model real-world subtask length and fallback competence variance — factors absent from the base-rate literature but necessary for realistic routing simulation.

*Formula-level comparison (Eq1 optimized vs Eq4 multiplicative).* The confusion matrices reveal where the multiplicative formula wins:

| Routing Cell | Eq1 Linear | Eq4 Multiplicative | Bayes Optimal | Meaning |
|---|---|---|---|---|
| FULL + Succeeded | 26.1% | 21.8% | 23.0% | Correctly routed to full recovery |
| **FULL + Failed** | **22.3%** | **7.9%** | **9.2%** | **False positive — wasted recovery** |
| REDUCED + Succeeded | 3.3% | 3.2% | 0.4% | Correctly routed to reduced recovery |
| REDUCED + Failed | 3.8% | 5.4% | 0.1% | False positive in reduced tier |
| **DISPUTED + Succeeded** | **7.7%** | **12.2%** | **13.0%** | **False negative — missed recovery** |
| DISPUTED + Failed | 36.7% | 51.5% | 53.3% | Correctly disputed |

The headline result: **FULL-tier false positives drop from 22.3% to 7.9% — a 65% reduction**. The multiplicative formula is far more selective about which tasks receive full recovery resources. The trade-off is a rise in disputed-but-recoverable cases (7.7% → 12.2%), which is the correct direction: a failed recovery wastes the fallback's budget and time, while a disputed-recoverable task merely delays resolution with the arbiter fee as overhead (see Section 6.6 for economic cost). The Eq4 matrix is strikingly close to the Bayes-optimal matrix, confirming the formula captures nearly all information extractable from the three on-chain inputs.

*Cross-task-type generalization (LOO-CV).* The per-task-type leave-one-out results confirm the formula is not over-fit to any single domain:

| Held-out Task Type | Run 1 (Eq1) | Run 4 (Eq4) | Eq4 Improvement |
|---|---|---|---|
| `defi.price_fetch` | 37.90% | 23.96% | −13.94pp |
| `defi.trade_execute` | 38.23% | 23.32% | −14.91pp |
| `data.report_generate` | 36.63% | 22.83% | −13.80pp |
| `governance.vote_delegate` | 38.39% | 23.39% | −15.00pp |
| `compute.model_inference` | 37.10% | 23.44% | −13.66pp |
| **Mean ± std** | **37.65% ± 0.68%** | **23.39% ± 0.36%** | **−14.26pp ± 0.54pp** |

Both formulas generalize (std well below the 3pp threshold), but Eq4 generalizes twice as tightly (0.36% vs 0.68%). `compute.model_inference` is the worst case for Eq4 (23.44%) — still 9pp below the Eq1 best case. The reported standard deviations use the population formula (divisor *N*, consistent with NumPy's default in `results_eq4.json`); the sample-std form (divisor *N*−1) yields 0.40% for Eq4 and 0.76% for Eq1. The *N*-divisor convention is retained here to match the raw simulation output.

*Ground-truth model specification.* The simulation uses base recovery rates from the MAST taxonomy [1] and agent reliability literature [2][3]: LIVENESS 92%, RESOURCE 48%, LOGIC 8%. The recovery probability for any single task-failure event is:

```
p = base × σ(15·(B − 0.15)) × σ(20·(D − 0.10)) × 1/(1 + 0.02·n_remaining) × (0.4 + 0.6·skill)
```

where σ is the logistic function, *B* and *D* are budget and deadline remaining, *n_remaining* is the count of remaining subtasks, and *skill* ∈ [0, 1] is the fallback agent's drawn skill score. The steeper deadline sigmoid (slope 20 vs budget's 15) reflects the sharper empirical cliff around deadline exhaustion. Skill is gated by the fallback's ERC-8004 reputation: higher-reputation fallbacks sample from a distribution biased toward 1.0. The source of truth is `simulation/recovery.py`; the stochastic event generator and all 16 experiment scripts live in `simulation/`, with results in `RESULTS.md` (Run 1), `RESULTS_EQ2.md` (Run 2), `RESULTS_EQ3.md` (Run 3), `RESULTS_EQ4.md` (Run 4).

**Remaining calibration work.** The simulation uses synthetic failure distributions. As CAIRN accumulates real execution records, the exponents (*a*, *b*, *c*), class weights, and thresholds should be re-validated against observed recovery outcomes via Bayesian posterior inference (MCMC) and adjusted via governance. The staged calibration roadmap: **(Stage 1)** Monte Carlo with synthetic data — **complete** (this section); **(Stage 2)** Bayesian posterior update once testnet produces ≥ *k* = 30 records per class per task type (~ 60 days post-launch at 10 tasks/day, per Section 5.3) — **planned**; **(Stage 3)** full MCMC re-calibration at mainnet with per-type posteriors — **planned**. At each stage the exponents are updated via governance parameter change, not a code redeployment.

**Multi-agent recovery chains.** The current protocol supports one fallback. Future versions could support multiple sequential fallbacks, with each contributing checkpoints and earning proportional payment. The mechanism design for chains longer than two agents requires additional analysis.

### 10.2 Protocol Extensions

**ERC standardization.** CAIRN is designed to become an Ethereum standard. The specification in [ERC-CAIRN.md](./ERC-CAIRN.md) follows the EIP-1 format. Working title: `ERC-CAIRN: Agent Failure and Recovery Standard`.

**CAIRN MCP Server.** Exposing checkpoint, recovery, and intelligence query as MCP tools would enable any MCP-connected agent to participate in CAIRN without framework-specific integration.

**Cross-chain support.** CAIRN is currently deployed on Base. Cross-chain fallback (e.g., a Base task recovered by an Olas agent on Gnosis) requires cross-chain messaging and is planned for a future protocol version.

**Privacy-preserving intelligence.** Currently, all failure records are public. Future versions may use zero-knowledge proofs to enable agents to query failure patterns without revealing their specific execution data.

### 10.3 Limitations

CAIRN's current design makes explicit trade-offs. We state them here to bound the claims made elsewhere in this paper.

**Checkpoint portability boundary.** CAIRN's full checkpoint portability covers structured pipeline tasks (approximately 90% of current on-chain agent workloads). Reasoning-heavy tasks (chain-of-thought, planning with backtracking) operate in degraded mode where only output-level checkpoints are portable. See Section 4.1.1.

**Recovery score accuracy.** The multiplicative formula achieves 23.46% misrouting against the synthetic ground truth — 0.93pp from the Bayes-optimal floor of 22.53% (96% of achievable improvement captured). The ground truth is calibrated to published class frequencies to within 0.17pp (LIVENESS/RESOURCE/LOGIC at 44.96% / 34.87% / 20.17% vs. literature targets 45% / 35% / 20%), but the recovery *rates* within each class have not been validated against empirical recovery outcomes because no such dataset yet exists. The staged calibration roadmap (Section 10.1) replaces the synthetic ground truth with observed outcomes as testnet and mainnet data accumulate; parameter updates happen via governance, not redeployment.

**Single-fallback architecture.** CAIRN supports one fallback attempt per failure. If the fallback also fails, the task goes to dispute. Multi-fallback chains are deferred to a future version.

**On-chain classification limits.** Failure classification is high-confidence for LIVENESS (heartbeat miss) and RESOURCE (budget/deadline exceeded) triggers, but LOGIC failures require agent self-reporting or external verification — a weaker signal. See the LOGIC class definition in Section 3.1 and the `detectFailure` permissionless-enforcement discussion in Section 3.3.

**L2 dependency.** CAIRN is economically viable on Base L2 but not on Ethereum mainnet (gas costs would be 100-1000× higher). This creates a dependency on the L2's sequencer availability and ordering guarantees.

**Arbiter recursion.** Arbiters are themselves agents reasoning about reasoning errors. Proposition 3 (Section 7.5) establishes that honest ruling is rational when the detection probability *p*<sub>d</sub> for incorrect rulings is high — which holds for LIVENESS and RESOURCE disputes (on-chain evidence) but not necessarily for LOGIC disputes ("did the agent hallucinate?"), where detection is itself a reasoning inference. CAIRN inherits the structural limitation common to all on-chain arbitration protocols [19]: a sufficiently adversarial LOGIC dispute can have a genuinely contestable answer, and the protocol cannot fully economically deter collusion in that regime. Mitigations (reputation gates, commit-reveal, multi-dispute compounding) bound the worst case; a Kleros-style multi-juror appeals layer is reserved for protocol v3.

**Arbiter depth.** Relatedly, the current arbiter mechanism is single-tier with no appeals. High-value disputes may require additional dispute resolution infrastructure in future versions.

**v1 / v2 specification gap.** The v1 testnet contract implements the pre-calibration linear recovery formula (see Section 6.4 note), 15% arbiter stake, binary routing at threshold 0.30, a non-batched `commitCheckpoint` signature in the MVP variant, and no on-chain schema-hash enforcement. The v2 specification described throughout this paper — multiplicative formula, three-tier routing at 0.40/0.35, 20% arbiter stake, batched `commitCheckpointBatch`, PRBMath-based or lookup-based fixed-point exponentiation, and per-checkpoint schema validation — is the target protocol that the simulation work motivates. The migration path is governance-gated via the `IRecoveryRouter` interface; it does not require a state-breaking upgrade of deployed tasks. Gas figures (Section 6.5) are design-target estimates for v2; the `forge test --gas-report` against the v2 reference implementation will be published alongside the v2 testnet deployment. Readers evaluating this paper should treat deployed-behaviour claims as pertaining to v2 unless explicitly annotated "v1."

---

## 11. References

[1] M. Cemri, M. Z. Pan, S. Yang, et al., "Why Do Multi-Agent LLM Systems Fail?", *NeurIPS 2025 Datasets and Benchmarks Track*, arXiv:2503.13657, 2025.

[2] S. Rabanser, S. Kapoor, P. Kirgis, K. Liu, S. Utpala, A. Narayanan, "Towards a Science of AI Agent Reliability", arXiv:2602.16666, February 2026.

[3] R. Lu, Y. Li, Y. Huo, "Exploring Autonomous Agents: A Closer Look at Why They Fail", *ASE 2025 NIER Track*, arXiv:2508.13143, August 2025.

[4] "Blockchain-Enhanced Incentive-Compatible Mechanisms for Multi-Agent Reinforcement Learning Systems", *Nature Scientific Reports*, November 2025. DOI: 10.1038/s41598-025-20247-8.

[5] Olas Network, "Mech Marketplace", https://olas.network/mech-marketplace. Over 10 million agent-to-agent transactions as of 2026; approximately 2,000 agents deployed, ~500 active daily.

[6] S. Alqithami, "Autonomous Agents on Blockchains: Standards, Execution Models, and Trust Boundaries", arXiv:2601.04583, January 2026. Systematic survey of 317 publications identifying missing interface layers and verifiable policy enforcement as key gaps.

[7] ISO/IEC TR 5469:2024, "Artificial Intelligence — Functional Safety and AI Systems", International Organization for Standardization, 2024.

[8] K. M. Chandy and L. Lamport, "Distributed Snapshots: Determining Global States of Distributed Systems", *ACM Transactions on Computer Systems*, 3(1):63-75, 1985.

[9] V. Buterin, D. Ryan, et al., "Ethereum Proof-of-Stake Consensus Specifications", Ethereum Foundation, 2020-2026. https://github.com/ethereum/consensus-specs. Staking/slashing mechanism securing over $100 billion in staked value across 1M+ validators as of early 2026.

[10] "AI Agents Meet Blockchain: A Survey", *MDPI Future Internet*, 17(2):57, February 2025. Introduces the Proof-of-Thought concept.

[11] IETF Draft, "Task-Oriented Multi-Agent Recovery Framework for High-Reliability in Converged Mobile Networks", `draft-yue-anima-agent-recovery-networks-00`, 2026.

[12] Google, "Agent2Agent Protocol (A2A)", donated to Linux Foundation June 2025; v0.3 released July 2025. https://github.com/a2aproject/A2A

[13] Anthropic, "Model Context Protocol (MCP)", 2024-2026; donated to Linux Foundation Agentic AI Foundation December 2025. https://modelcontextprotocol.io

[14] M. De Rossi, D. Crapis, J. Ellis, E. Reppel, "ERC-8004: Trustless Agents Standard." EIP in Draft status; mainnet-deployed since January 29, 2026. ~49,000 registered agents across 30+ EVM chains as of February 2026. EIP: https://eips.ethereum.org/EIPS/eip-8004

[15] D. Crapis, B. Lim, T. Weixiong, C. Zuhwa, "ERC-8183: Agentic Commerce Standard." EIP in Draft status, created February 25, 2026. Agent Commerce Protocol (ACP) deployed on Arbitrum via Virtuals Protocol. EIP: https://eips.ethereum.org/EIPS/eip-8183

[16] Biconomy, "ERC-8211: Smart Batching — Runtime-Resolved Parameters and Predicate-Gated Execution for Smart Accounts." Proposed April 2026; discussion draft on Ethereum Magicians (no canonical EIP page at time of writing). Discussion: https://ethereum-magicians.org/t/erc-8211-smart-batching/28135

[17] R. McPeck, D. Finlay, R. Dawson, D. Chiang, "ERC-7710: Smart Contract Delegation." EIP in Draft status, created May 20, 2024. Used by the MetaMask Delegation Toolkit. EIP: https://eips.ethereum.org/EIPS/eip-7710

[18] CAIRN Recovery Score Calibration Simulation, April 2026. Monte Carlo validation across 100,000 synthetic task-failure events per run, 4 formula structures (linear, piecewise + interaction, 5-variable linear, multiplicative), 16 experiments (Exp 1-5 weight/class/threshold/sensitivity/LOO-CV for Eq1; Exp 6-8 for Eq2; Exp 9-12 for Eq3; Exp 13-16 Bayes-optimal baseline, multiplicative grid, hybrid α-sweep, and cross-task LOO-CV for Eq4). Run 1: 362 grid points (55 weight + 245 class-weight + 62 threshold), runtime ~3 seconds. Run 2: staged grid over 8 Eq2 parameters, runtime ~31 seconds. Run 3: staged grid over 5 linear weights + thresholds. Run 4: 2,646 multiplicative-formula grid points + hybrid α-sweep, runtime ~14 seconds. Reproducible: `python3 -m simulation.run` (Run 1), `run_eq2` (Run 2), `run_eq3` (Run 3), `run_eq4` (Run 4); seed=42, deterministic on any NumPy ≥1.20 installation. Source: `simulation/` in the CAIRN repository. Results: `simulation/RESULTS.md`, `RESULTS_EQ2.md`, `RESULTS_EQ3.md`, `RESULTS_EQ4.md`. Figures: `simulation/figures/fig1` through `fig16`.

[19] C. Lesaege, F. Ast, W. George, "Kleros: A Decentralized Court System for the Internet", Kleros Yellowpaper, v1.0.7, 2019. https://kleros.io/yellowpaper.pdf. Pioneers the bonded-juror-with-Schelling-point design for on-chain dispute resolution, including multi-round appeals with quadratically increasing juror pools. Cited in this paper as the canonical prior work on the arbiter-recursion problem (Section 4.5, Section 7.5, Section 10.3).

---

*CAIRN — Agent Failure and Recovery Protocol*
*Whitepaper v2.0 — April 2026*
*Agents learn together.*
