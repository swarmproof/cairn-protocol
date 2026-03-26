# CAIRN Architecture

> High-level system architecture, protocol flow diagrams, and component interactions.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Protocol Layers](#protocol-layers)
3. [Low-Level Protocol Flow](#low-level-protocol-flow)
4. [Full Action Sequence](#full-action-sequence)

---

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              ACTORS                                            │
│                                                                                │
│  ┌──────────┐  ┌───────────────┐  ┌────────────────┐  ┌────────┐  ┌───────┐  │
│  │ Operator │  │ Primary Agent │  │  Fallback Pool  │  │Arbiter │  │Watcher│  │
│  │initiates │  │ executes task │  │registered agents│  │ agents │  │ bots  │  │
│  └──────────┘  └───────────────┘  └────────────────┘  └────────┘  └───────┘  │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │ interact with
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                          CAIRN PROTOCOL LAYER                                  │
│                                                                                │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  CairnTask.sol  │  │CairnHook.sol │  │RecoveryOrch. │  │  SlashModule  │  │
│  │  State machine  │  │ERC-8183 hook │  │Fallback sel. │  │ Rep. slashing │  │
│  │  + enforcement  │  │  interface   │  │   logic      │  │               │  │
│  └─────────────────┘  └──────────────┘  └──────────────┘  └───────────────┘  │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │ integrates with
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                        ETHEREUM STANDARDS LAYER                                │
│                                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │  ERC-8183    │  │  ERC-8004    │  │  ERC-7710    │  │  Olas Mech Mkt   │ │
│  │  Job escrow  │  │  Identity    │  │  Delegation  │  │  Fallback agents  │ │
│  │  + hooks     │  │  Reputation  │  │  framework   │  │  (live registry)  │ │
│  │  (live)      │  │  (live)      │  │  (live)      │  │                   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────────────┘ │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │ writes to / reads from
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                      EXECUTION INTELLIGENCE LAYER                              │
│                                                                                │
│  ┌────────────────────┐  ┌───────────────────┐  ┌────────────────────────┐   │
│  │   IPFS / Records   │  │  Bonfires Graph   │  │  The Graph Subgraph    │   │
│  │  Full exec records │  │  Visualize+query  │  │  Index onchain events  │   │
│  │  (content-address) │  │  API for agents   │  │  (TaskFailed/Resolved) │   │
│  └────────────────────┘  └───────────────────┘  └────────────────────────┘   │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │ deployed on
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                           BASE (deployment chain)                              │
│  CairnTask.sol · CairnHook.sol · ERC-8004 registries · ERC-8183 factory       │
│  ~2s block time · low gas · AgentKit native · ERC-8004/8183 already deployed  │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Protocol Layers

### Why These Four Layers

**Actors** — the humans and agents that interact with the protocol. CAIRN does not care about the actor's framework or language. Any actor that can call a contract function can integrate CAIRN.

**CAIRN Protocol Layer** — the only new code built. Four components, all deployable in 7 days. Everything else is a call to an existing system.

**Ethereum Standards Layer** — four live standards that CAIRN integrates rather than reinvents. This is the key architectural decision: CAIRN is a *compositor* of existing primitives, not a replacement.

**Execution Intelligence Layer** — what accumulates automatically as the protocol runs. No human curation. No central server. Records are written on-chain events, stored on IPFS, indexed by The Graph, visualized by Bonfires.

---

## Low-Level Protocol Flow

```
ACTORS:    Operator          CairnTask         ERC-8183         ERC-8004    Intelligence
           ─────────         ─────────         ────────         ────────    ───────────

── INIT ──────────────────────────────────────────────────────────────────────────────────

A2:        ──────────────────────────────────────────────────────────────────► query(task_type)
           ◄──────────────────────────────────────────────────────────────── failure_patterns
                                                                              cost_estimate
                                                                              recommended_agent

A3:        startTask(spec)──►                  createJob(...)──►
           lockEscrow()──────────────────────►
           preDelegate(CAIRN, caveat)──────────────────────────────────────► ERC-7710 set

── RUNNING ───────────────────────────────────────────────────────────────────────────────

A4:                          commitCheckpoint(taskId, N, CID, cost)
                             ← validate CID vs schema →
                             ← store CID, update cost_accrued →

A5:                          heartbeat(taskId)
                             ← reset last_heartbeat →

A6:        [anyone]          checkLiveness(taskId)  [public, permissionless]
           [anyone]          checkBudget(taskId)    [public, permissionless]
           [anyone]          checkDeadline(taskId)  [public, permissionless]

── FAILED ────────────────────────────────────────────────────────────────────────────────

A7:                          → classify(failure_type)
                             → compute(recovery_score)
                             → write FailureRecord to IPFS ──────────────────► store CID
                             → emit TaskFailed(taskId, recordCID, score)
                             ← BonfiresAdapter indexes record ◄──────────────── event

A8:        score≥0.3 ─────────────────────────────────────────────────────► [RECOVERING]
           score<0.3 ─────────────────────────────────────────────────────► [DISPUTED]

── RECOVERING ────────────────────────────────────────────────────────────────────────────

A9:                                                                           query(task_type)
                                                                              → Bonfires + Olas
                             ◄──────────────────────────────────────────── fallback_agent_id

A10:                         → transfer(checkpoint_cid_list, remaining_budget,
                                        remaining_deadline, delegation_caveat)
                             → ERC-7710 sub-delegate ──────────────────────► to fallback

A11:       [fallback reads IPFS → resumes from last CID → continues A4/A5/A6 cycle]

── RESOLVED ──────────────────────────────────────────────────────────────────────────────

A12:                         → compute escrow_split(checkpoint_counts)
                                                        complete(jobId)──────►
                             ← ERC-8183 releases funds ◄───────────────────
                             → write positive rep ──────────────────────────► ReputationRegistry
                             → write ResolutionRecord to IPFS ──────────────► store CID
                             → emit TaskResolved(taskId, recordCID)
                             ← BonfiresAdapter indexes record ◄──────────────── event

── DISPUTED ──────────────────────────────────────────────────────────────────────────────

A13:                         → hold escrow
                             → write negative rep ───────────────────────────► ReputationRegistry
                             → expose FailureRecord CID publicly
                             → emit TaskDisputed(taskId, recordCID, timeout)
                             ← BonfiresAdapter indexes record ◄──────────────── event

A14:       [arbiter]         rule(taskId, outcome)
                             → distribute escrow per ruling + arbiter fee
                             → emit TaskResolved(taskId, recordCID)
           [OR timeout]      → auto-refund operator
                             → emit TaskRefunded(taskId)
```

---

## Full Action Sequence

14 actions across 6 phases. Stack-agnostic — described as protocol operations, not implementation details.

### Phase 1: Initialization

| Action | Actor | Description |
|--------|-------|-------------|
| **A1** | Operator submits | Submit task spec: task_type (domain.operation), budget_cap, deadline, output_format per subtask, description, heartbeat_interval (optional) |
| **A2** | Protocol queries intelligence | Query execution intelligence layer by task_type: → known failure patterns, → real cost distribution from prior executions, → recommended agent (highest success rate + reputation), → known-bad time windows or API conditions |
| **A3** | Operator confirms | Reviews A2 output. Confirms task. Locks escrow. Pre-authorizes CAIRN for fallback sub-delegation (ERC-7710 caveat: allowed actions + budget cap + allowed fallback pool). State → RUNNING. |

### Phase 2: Running

| Action | Actor | Description |
|--------|-------|-------------|
| **A4** | Agent checkpoints | Completes subtask N. Writes output to IPFS. Receives CID. Calls commitCheckpoint(taskId, N, CID, cost). Protocol validates CID against declared schema. Valid: stored. Invalid: rejected, agent must retry. |
| **A5** | Agent heartbeats | Emits liveness ping: heartbeat(taskId). Resets liveness timer. Must occur every heartbeat_interval time units. |
| **A6** | Protocol enforces | Enforce functions (public, anyone can call): checkLiveness(taskId) — fires FAILED if heartbeat missed. checkBudget(taskId) — fires FAILED if budget_cap hit. checkDeadline(taskId) — fires FAILED if deadline passed. |

### Phase 3: Failed

| Action | Actor | Description |
|--------|-------|-------------|
| **A7** | Protocol classifies | Classifies failure type (liveness / resource / logic). Computes recovery_score using formula. Writes Failure Record to IPFS. Stores CID on-chain. Emits TaskFailed(taskId, recordCID, recoveryScore). Escrow held. |
| **A8** | Protocol routes | Routes based on recovery_score: score ≥ 0.3 → A9 (RECOVERING path). score < 0.3 → A13 (DISPUTED path) |

### Phase 4: Recovering

| Action | Actor | Description |
|--------|-------|-------------|
| **A9** | Protocol selects fallback | Queries execution intelligence layer for best fallback agent: task_type match + reputation score + availability + admission threshold check. Returns ranked list. Selects top available agent. |
| **A10** | Protocol transfers state | Transfers task state to fallback agent: → checkpoint_cid_list (all validated outputs), → next_subtask_index (where to resume), → remaining_budget, → remaining_deadline, → scoped permissions (pre-authorized caveat from A3) |
| **A11** | Fallback agent resumes | Reads checkpoint_cid_list from A10. Fetches last validated output from IPFS. Begins executing from next_subtask_index. New liveness clock starts. Continues A4/A5/A6 cycle with remaining budget. |

### Phase 5: Resolved

| Action | Actor | Description |
|--------|-------|-------------|
| **A12** | Protocol settles | Computes escrow split by verified checkpoint count. Releases escrow to original agent and/or fallback. Writes Resolution Record to IPFS. Stores CID on-chain. Emits TaskResolved(taskId, recordCID). Writes positive reputation signal to ERC-8004 ReputationRegistry for all completing agents. State → RESOLVED (terminal). |

### Phase 6: Disputed

| Action | Actor | Description |
|--------|-------|-------------|
| **A13** | Protocol opens dispute | Holds escrow — funds do not move. Writes negative reputation signal to ERC-8004 ReputationRegistry for failing agent. Exposes Failure Record CID publicly. Starts arbiter_timeout clock. Emits TaskDisputed(taskId, recordCID, arbiterTimeout). |
| **A14** | Arbiter rules or timeout fires | Registered arbiter reads Failure Record from IPFS. Evaluates evidence. Calls rule(taskId, outcome) within arbiter_timeout window. Arbiter fee deducted from escrow. If timeout expires with no arbiter: auto-refund operator. Either path → RESOLVED (terminal). |

---

*See also: [Concepts](./concepts.md) · [Integration](./integration.md) · [Contracts](./contracts.md)*

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
