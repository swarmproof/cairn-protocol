<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a0a0f,50:1a1a2e,100:00CED1&height=180&section=header&text=CAIRN%20Protocol&fontSize=52&fontColor=ffffff&animation=fadeIn&fontAlignY=42&desc=Agent%20Failure%20%26%20Recovery%20Protocol&descAlignY=62&descSize=16&descColor=7FFFD4" width="100%"/>

<p>
  <img src="https://img.shields.io/badge/Status-Live%20on%20Base%20Sepolia-00CED1?style=flat-square&logo=ethereum&logoColor=white"/>
  <img src="https://img.shields.io/badge/Contracts-6%20Deployed-008B8B?style=flat-square"/>
  <img src="https://img.shields.io/badge/Tests-315%20%7C%2098.95%25%20coverage-00CED1?style=flat-square"/>
  <img src="https://img.shields.io/badge/Chain%20ID-84532-0052FF?style=flat-square&logo=coinbase&logoColor=white"/>
  <img src="https://img.shields.io/badge/ERC-CAIRN%20Proposal-008B8B?style=flat-square"/>
</p>

<p>
  <a href="https://cairn-protocol-iona-78423aa1.vercel.app"><img src="https://img.shields.io/badge/🌐%20Live%20Demo-Frontend-00CED1?style=flat-square"/></a>
  <a href="./WHITEPAPER.md"><img src="https://img.shields.io/badge/📄%20Whitepaper-Read-008B8B?style=flat-square"/></a>
  <a href="./ERC-CAIRN.md"><img src="https://img.shields.io/badge/📋%20ERC%20Spec-Draft-20B2AA?style=flat-square"/></a>
  <a href="./docs/architecture.md"><img src="https://img.shields.io/badge/🏗️%20Architecture-Docs-008B8B?style=flat-square"/></a>
  <a href="https://thegraph.com/studio/subgraph/cairn"><img src="https://img.shields.io/badge/📊%20Subgraph-The%20Graph-6748fe?style=flat-square"/></a>
</p>

<br/>

> **One line:** CAIRN turns every agent failure into a lesson every other agent inherits —
> enforced by escrow, validated by attestation, owned by no one.
>
> **Three words:** Agents learn together.

<br/>

</div>

---

## The Problem

**Agent workflows fail 80% of the time.** At 85% success per action, a 10-step workflow completes only ~20% of the time. When failures happen today:

| What Happens | Cost |
|--------------|------|
| Work is lost | Restart from zero — all progress gone |
| Escrow locks | Funds stuck in ambiguous state for hours/days |
| No one learns | Same failure repeats across the ecosystem |
| Human intervention required | 2am pages, manual debugging, delayed resolution |

**The ecosystem is bleeding value.** Every silent failure is money lost, time wasted, and a lesson unlearned.

### The Cost of Doing Nothing

```
Monthly failure cost = failures × avg_escrow × (1 - recovery_rate) + restart_cost + opportunity_cost

Example (single operator):
- 20 failures/month × $50 avg escrow × 100% loss rate = $1,000 direct loss
- 20 restarts × $15 gas (duplicate work)              =   $300 gas waste
- 20 failures × 4 hours delay × $50/hour opportunity  = $4,000 opportunity cost
─────────────────────────────────────────────────────────────────────────────
  Total: ~$5,300/month lost to unrecovered failures
```

---

## A Real Failure: Before and After

**Scenario:** DeFi rebalancing agent on Base · $12,000 across 3 pools · 2:47am UTC, Saturday

<table>
<tr>
<td width="50%" valign="top">

### ❌ Without CAIRN

| Step | Action | Result |
|------|--------|--------|
| 1 | Price fetch | ✅ success |
| 2 | Approve token A | ✅ success |
| 3 | Swap on DEX | ❌ rate limit (429) |

Agent stopped. No heartbeat for 45 minutes.
Escrow: $45 locked in ambiguous state.
Operator notified: 7:15am (+4.5h).
Resolution: manual restart from scratch.
Approvals (step 2) must be re-done.

**Total cost: $57 + 4.5 hours**

</td>
<td width="50%" valign="top">

### ✅ With CAIRN

| Time | Event |
|------|-------|
| 2:47am | Agent fails (rate limit) |
| 2:52am | CAIRN detects (liveness timeout) |
| 2:52am | Classified: RESOURCE · score 0.74 |
| 2:53am | Fallback assigned from pool |
| 2:53am | Fallback reads checkpoint 2, resumes |
| 3:08am | Task completed by fallback |
| 3:08am | Escrow split: original 66% / fallback 33% |

Work preserved. Escrow settled proportionally.
Zero human intervention.

**Total delay: 21 minutes**

</td>
</tr>
</table>

---

## Why Now

| Signal | Status |
|--------|--------|
| **ERC-8183 is live** | Agent escrow infrastructure shipped March 2026 |
| **600+ agents on Olas** | Real fallback pool available today |
| **$479M aGDP** | Real money flowing through agent transactions |
| **80% workflow failure rate** | At 85% per-action success, most multi-step tasks fail |

The infrastructure is ready. The problem is severe. The gap is real.

---

## The Cairn Metaphor

Travelers in wilderness stack stones — **cairns** — to mark where they have been, which paths are safe, and which lead nowhere. Each cairn is left by one traveler but read by every traveler who comes after. No traveler owns the cairn network. Every traveler benefits from it.

CAIRN applies this to agents. Every failure leaves a cairn — an execution record that marks this exact task type, this exact failure mode, this exact cost. Every future agent reads the cairns before setting out. The ecosystem navigates by accumulated failure intelligence, not blind optimism.

---

## What CAIRN Is

**A standardized agent failure and recovery protocol.**

It defines the exact sequence of events that must occur when an agent fails mid-task — from detection, through classification, through fallback assignment, through settlement — without requiring any human intervention and without requiring trust between agents.

### The Protocol in One Paragraph

An operator initiates a task with a budget, deadline, and task type. Before the task starts, CAIRN queries the execution intelligence layer for known failure patterns on this task type and recommends the best-fit agent. The agent runs. It emits liveness signals. It writes checkpoints after each subtask. If it fails — for any reason — CAIRN detects it automatically, classifies the failure, computes a recovery score, and either assigns a fallback agent (who resumes from the last checkpoint) or routes to dispute. On resolution, escrow splits proportionally between the original and fallback agents based on verified work done. The execution record is written. The intelligence layer grows. The next agent inherits the lesson.

### Secondary Output: Execution Intelligence

As a byproduct of the recovery protocol running, CAIRN accumulates an **execution intelligence layer** — a shared, queryable record of every failure, every recovery, and every successful completion across the ecosystem. The knowledge graph grows automatically. The more agents integrate CAIRN, the richer the intelligence layer becomes.

**The knowledge graph is the byproduct. The recovery protocol is the core.**

---

## What CAIRN is NOT

| ❌ Not This | ✅ Instead |
|-------------|-----------|
| A new agent framework | Wraps any framework — LangGraph, Olas SDK, AgentKit, custom builds |
| A knowledge graph product | Bonfires is a window into the intelligence layer, not the protocol |
| A centralized service | Every state transition enforced on-chain. No server. No admin key |
| A replacement for ERC-8183/8004 | Integrates and extends both as a Hook and reputation writer |
| Optional infrastructure | Escrow-enforced — agents can't get paid without completing the protocol |

---

## The Six-State Machine

Every task moves through exactly one of these states. No silent failures. No ambiguous states. Every transition is enforced on-chain.

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
                    │   ┌─────────┐                           │
                    │   │  IDLE   │  ← task created           │
                    │   └────┬────┘                           │
                    │        │ startTask()                    │
                    │        ▼                                │
                    │   ┌─────────┐  heartbeat ───────────────┤
                    │   │ RUNNING │  checkpoint               │
                    │   └────┬────┘                           │
                    │        │ failure detected               │
                    │        ▼                                │
                    │   ┌─────────┐                           │
                    │   │ FAILED  │                           │
                    │   └────┬────┘                           │
                    │  score ≥ 0.3        score < 0.3         │
                    │        │                  │             │
                    │        ▼                  ▼             │
                    │  ┌───────────┐     ┌──────────┐         │
                    │  │RECOVERING │     │ DISPUTED │         │
                    │  └─────┬─────┘     └────┬─────┘         │
                    │        │ completes      │ arbiter       │
                    │        └───────┬────────┘               │
                    │                ▼                        │
                    │         ┌──────────┐                    │
                    │         │ RESOLVED │ ← terminal         │
                    │         └──────────┘                    │
                    └─────────────────────────────────────────┘
```

| State | Description |
|-------|-------------|
| **IDLE** | Task created, intelligence queried, agent recommended |
| **RUNNING** | Agent executing, heartbeats active, checkpoints committed |
| **FAILED** | Liveness / budget / deadline violation detected automatically |
| **RECOVERING** | Fallback assigned, resumes from last valid checkpoint |
| **DISPUTED** | Low recovery score, arbiter intervention required |
| **RESOLVED** | Escrow settled, reputation updated, record written (terminal) |

---

## Three-Class Failure Taxonomy

| Class | Trigger | Weight | Default Path |
|-------|---------|--------|--------------|
| **LIVENESS** | Heartbeat missed beyond `heartbeat_interval` | 0.9 (high) | RECOVERING |
| **RESOURCE** | Budget exceeded or deadline passed | 0.5 (medium) | RECOVERING |
| **LOGIC** | Invalid checkpoint, schema violation, disputed output | 0.1 (low) | DISPUTED |

**Recovery Score Formula:**
```
recovery_score = (failure_class_weight × 0.5) + (budget_remaining_pct × 0.3) + (deadline_remaining_pct × 0.2)
```

---

## The 14-Action Protocol

<details open>
<summary><b>Phase 1 — Initialization (A1–A3)</b></summary>
<br/>

**A1** · Operator submits task spec: `task_type`, `budget_cap`, `deadline`, `heartbeat_interval`, output schemas per subtask.

**A2** · Protocol queries execution intelligence layer by `task_type` → known failure patterns, real cost distribution, recommended agent (highest success rate + reputation), known-bad time windows.

**A3** · Operator confirms. Locks escrow. Pre-authorizes CAIRN for fallback sub-delegation (ERC-7710 caveat). State → `RUNNING`.

</details>

<details>
<summary><b>Phase 2 — Running (A4–A6)</b></summary>
<br/>

**A4** · Agent completes subtask N. Writes output to IPFS. Calls `commitCheckpoint(taskId, N, CID, cost)`. Protocol validates CID against declared schema.

**A5** · Agent emits liveness ping: `heartbeat(taskId)`. Resets liveness timer every `heartbeat_interval`.

**A6** · Protocol enforces (permissionless — anyone can call): `checkLiveness()` · `checkBudget()` · `checkDeadline()`.

</details>

<details>
<summary><b>Phase 3 — Failed (A7–A8)</b></summary>
<br/>

**A7** · Protocol classifies failure type (LIVENESS / RESOURCE / LOGIC). Computes `recovery_score`. Writes Failure Record to IPFS. Emits `TaskFailed(taskId, recordCID, recoveryScore)`.

**A8** · Routes: `score ≥ 0.3` → RECOVERING. `score < 0.3` → DISPUTED.

</details>

<details>
<summary><b>Phase 4 — Recovering (A9–A11)</b></summary>
<br/>

**A9** · Queries execution intelligence for best fallback: `task_type` match + reputation + availability.

**A10** · Transfers state to fallback: checkpoint CID list, `next_subtask_index`, remaining budget, remaining deadline, scoped permissions.

**A11** · Fallback reads checkpoint list from IPFS, resumes from `next_subtask_index`. New liveness clock starts. Continues A4/A5/A6 cycle.

</details>

<details>
<summary><b>Phase 5 — Resolved (A12)</b></summary>
<br/>

**A12** · Computes escrow split by verified checkpoint count. Releases escrow. Writes Resolution Record to IPFS. Emits `TaskResolved`. Writes positive reputation signal to ERC-8004. State → RESOLVED (terminal).

</details>

<details>
<summary><b>Phase 6 — Disputed (A13–A14)</b></summary>
<br/>

**A13** · Holds escrow. Writes negative reputation to ERC-8004. Exposes Failure Record CID publicly. Starts `arbiter_timeout` clock.

**A14** · Registered arbiter reads Failure Record, calls `rule(taskId, outcome)`. Arbiter fee deducted from escrow. If timeout expires: auto-refund operator. Either path → RESOLVED.

</details>

---

## Architecture

Four layers. Only the **CAIRN Protocol Layer** is new code. Everything else integrates live existing infrastructure.

```
┌──────────────────────────────────────────────────────────────┐
│ ACTORS                                                        │
│ Operator · Primary Agent · Fallback Pool · Arbiter            │
└─────────────────────────────┬────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────┐
│ CAIRN PROTOCOL LAYER                    ← only new code       │
│ CairnCore · RecoveryRouter · FallbackPool · ArbiterRegistry   │
└─────────────────────────────┬────────────────────────────────┘
                              │ integrates with
┌─────────────────────────────▼────────────────────────────────┐
│ ETHEREUM STANDARDS LAYER                ← existing live infra │
│ ERC-8183 (escrow) · ERC-8004 (identity) · ERC-7710 (delegation)│
│ Olas Mech Marketplace                                         │
└─────────────────────────────┬────────────────────────────────┘
                              │ writes to / reads from
┌─────────────────────────────▼────────────────────────────────┐
│ EXECUTION INTELLIGENCE LAYER            ← grows automatically │
│ IPFS execution records · Bonfires graph · The Graph indexer   │
└─────────────────────────────┬────────────────────────────────┘
                              │ deployed on
┌─────────────────────────────▼────────────────────────────────┐
│ BASE SEPOLIA                                                  │
│ ~2s block time · low gas · AgentKit native · ERC-8183 live    │
└──────────────────────────────────────────────────────────────┘
```

---

## Standards Integration

CAIRN is a **compositor** of existing primitives, not a replacement.

| Standard | What It Provides | CAIRN's Role |
|----------|------------------|--------------|
| **ERC-8183** | Standardized escrow for agent jobs with lifecycle hooks | Registers as lifecycle hook — intercepts failures, controls settlement |
| **ERC-8004** | On-chain agent identity and reputation registry | Writes success/failure signals to reputation scores post-resolution |
| **ERC-7710** | Scoped permission delegation with caveats | Enables pre-authorized fallback assignment without new signatures |
| **Olas Mech** | 600+ registered agents with staking | Live fallback pool — CAIRN queries for best-fit backup agents |

---

## Quick Start

```bash
pip install cairn-sdk

# or clone locally
git clone https://github.com/MarouaBoud/cairn-protocol
cd cairn-protocol && pip install -e ./sdk
```

```python
from cairn_sdk import CairnClient, CairnAgent
import os

client = CairnClient(
    rpc_url="https://sepolia.base.org",
    contract_address="0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640",  # CairnCore
    private_key=os.environ["PRIVATE_KEY"]
)

# Submit a task with checkpoint protocol
task = await client.submit_task(
    task_type="defi.rebalance",
    budget_cap=0.05,           # ETH
    deadline=3600,             # seconds
    heartbeat_interval=60
)

# Checkpoint after each subtask
await agent.checkpoint(task.id, subtask_n=1, output_cid="Qm...")

# Heartbeat to signal liveness
await agent.heartbeat(task.id)
```

📚 **Full guides:** [Integration](./docs/integration.md) · [SDK Quickstart](./sdk/QUICKSTART.md) · [CLI Reference](./cli/README.md)

---

## Deployed Contracts — Base Sepolia

| Contract | Address | Description |
|----------|---------|-------------|
| **CairnCore** | [`0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640`](https://sepolia.basescan.org/address/0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640) | Main entry point — 6-state machine, full task lifecycle |
| CairnGovernance | [`0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f`](https://sepolia.basescan.org/address/0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f) | Protocol parameters, admin controls |
| RecoveryRouter | [`0xE52703946cb44c12A6A38A41f638BA2D7197a84d`](https://sepolia.basescan.org/address/0xE52703946cb44c12A6A38A41f638BA2D7197a84d) | Failure classification, recovery scoring |
| FallbackPool | [`0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0`](https://sepolia.basescan.org/address/0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0) | Agent registration, selection algorithm |
| ArbiterRegistry | [`0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68`](https://sepolia.basescan.org/address/0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68) | Dispute resolution, appeals |
| CairnTaskMVP *(legacy)* | [`0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417`](https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417) | Simplified 4-state MVP — use CairnCore for production |

All contracts use **UUPS proxy pattern** (OpenZeppelin 5.x). Upgradeable without redeployment.

### Live Resources

| Resource | URL |
|----------|-----|
| **Frontend** | [cairn-protocol-iona-78423aa1.vercel.app](https://cairn-protocol-iona-78423aa1.vercel.app) |
| **Subgraph** | [The Graph Studio](https://thegraph.com/studio/subgraph/cairn) |
| **Query Endpoint** | `https://api.studio.thegraph.com/query/1744842/cairn/v1.0.0` |

---

## Protocol Status

| Property | Value |
|----------|-------|
| **Version** | 1.0 |
| **Network** | Base Sepolia (Chain ID: 84532) |
| **ERC Dependencies** | ERC-8183 · ERC-8004 · ERC-7710 |

### Implementation Progress — Synthesis Hackathon 2026

| Component | Status | Notes |
|-----------|--------|-------|
| PRD-00 Vision | ✅ Complete | Full protocol specification |
| PRD-01 MVP | ✅ Complete | Hackathon submission |
| Smart Contracts | ✅ Deployed | **315 tests · 98.95% coverage** |
| Deployment | ✅ Live | Base Sepolia — 6 contracts |
| SDK (Python) | ✅ Complete | CairnClient · CairnAgent · CheckpointStore · Observers |
| CLI Tool | ✅ Complete | submit-task · heartbeat · checkpoint · monitor · recover |
| Subgraph | ✅ Deployed | The Graph Studio indexing |
| Upgradeable | ✅ Complete | UUPS proxy pattern (OpenZeppelin 5.x) |
| Frontend | ✅ Deployed | Next.js 14 · wagmi · real-time events |
| PRD-07 Optimization | ✅ Complete | **Merkle checkpoint batching (89-99% gas savings)** |

See [`PRDs/README.md`](./PRDs/README.md) for full roadmap.

---

## Repository Structure

```
cairn-protocol/
├── contracts/           # Solidity — 6 deployed contracts, UUPS proxies
│   ├── src/            # Core: CairnCore, RecoveryRouter, FallbackPool, ArbiterRegistry
│   └── test/           # 315 tests · 98.95% coverage
├── sdk/                 # Python SDK — CairnClient, CairnAgent, CheckpointStore
├── cli/                 # CLI tool — task management, monitoring
├── subgraph/            # The Graph — indexes all CAIRN events
├── frontend/            # Next.js 14 dashboard — live on Vercel
├── pipeline/            # Off-chain recovery orchestration
├── docs/                # Technical documentation
├── PRDs/                # Product requirements documents
├── ERC-CAIRN.md         # ERC proposal (CC0 licensed)
├── WHITEPAPER.md        # Protocol philosophy and economics
├── SECURITY.md          # Threat model and mitigations
└── CHANGELOG.md         # Version history
```

---

## Documentation

### Core Documents

| Document | Description |
|----------|-------------|
| [Whitepaper](./WHITEPAPER.md) | Why CAIRN exists — problem, philosophy, economics |
| [ERC Specification](./ERC-CAIRN.md) | Technical standard in EIP format |
| [Security](./SECURITY.md) | Security model, attack vectors, mitigations |

### Technical Documentation

| Document | Description |
|----------|-------------|
| [Concepts](./docs/concepts.md) | Failure taxonomy, state machine, glossary |
| [Architecture](./docs/architecture.md) | System design, 4-layer stack, protocol flow |
| [Contracts](./docs/contracts.md) | Interfaces, schemas, component reference |
| [Integration](./docs/integration.md) | Checkpoint protocol, fallback pool, SDK guides |
| [Standards](./docs/standards.md) | ERC-8183, ERC-8004, ERC-7710, Olas integration |
| [Execution Intelligence](./docs/execution-intelligence.md) | Knowledge graph, queries, network effects |
| [Observer](./docs/observer.md) | Failure cost visibility layer |
| [Multi-Sig Governance](./docs/MULTI_SIG_GOVERNANCE.md) | Gnosis Safe setup, parameter management |
| [Olas Integration](./docs/olas-integration.md) | Mech marketplace adapter |

### Quick Navigation

| Goal | Path |
|------|------|
| **Understand CAIRN** | [Whitepaper](./WHITEPAPER.md) → [Concepts](./docs/concepts.md) |
| **Technical Spec** | [ERC-CAIRN](./ERC-CAIRN.md) → [Contracts](./docs/contracts.md) |
| **Build with CAIRN** | [Integration](./docs/integration.md) → [SDK Quickstart](./sdk/QUICKSTART.md) |
| **Security** | [Security Model](./SECURITY.md) |

---

## Hackathon Submission — Synthesis 2026

**Tracks:** Protocol Labs: Agents With Receipts • Let the Agent Cook

### What Makes CAIRN Different

| # | Differentiator |
|---|----------------|
| 1 | **Not a framework** — Wraps any agent SDK (LangGraph, Olas, AgentKit) |
| 2 | **Escrow-enforced** — Agents can't get paid without completing the protocol |
| 3 | **Automatic recovery** — No human intervention needed for fallback assignment |
| 4 | **Network effects** — Every failure teaches every future agent |

### Track Requirements: "Agents With Receipts"

| Requirement | Implementation |
|-------------|----------------|
| **Execution Records** | Every task creates on-chain record with checkpoints, heartbeats, settlement |
| **Failure Classification** | RecoveryRouter classifies (TIMEOUT, REVERTED, RESOURCE, LOGIC, UNKNOWN) |
| **Recovery Scoring** | Computed recovery probability before fallback assignment |
| **Settlement Receipts** | Proportional escrow splits with on-chain verification |
| **Collective Intelligence** | Bonfires integration writes failure patterns to knowledge graph |

### Agent Metadata

| File | Description |
|------|-------------|
| [`.synthesis/agent.json`](./.synthesis/agent.json) | Agent identity, team structure, deployment info |
| [`.synthesis/agent_log.json`](./.synthesis/agent_log.json) | Chronological build log |
| [`.synthesis/CONVERSATION_LOG.md`](./.synthesis/CONVERSATION_LOG.md) | Session summaries and decision log |

---

## License

This project uses a **multi-license structure** to balance openness, protection, and ecosystem compatibility.

| Component | License | Rationale |
|-----------|---------|-----------|
| [ERC-CAIRN.md](./ERC-CAIRN.md) | CC0-1.0 | ERC standards must be unencumbered |
| [WHITEPAPER.md](./WHITEPAPER.md) | All Rights Reserved | IP protection with citation rights |
| [contracts/](./contracts/) | GPL-3.0-or-later | Copyleft — forks must remain open source |
| [sdk/](./sdk/), [cli/](./cli/) | Apache-2.0 | Permissive + patent grant for integrators |
| [subgraph/](./subgraph/) | MIT | Simplest, no friction |
| [frontend/](./frontend/) | AGPL-3.0-or-later | SaaS providers must share modifications |
| [docs/](./docs/) | CC BY 4.0 | Freely shareable with attribution |

See [LICENSE](./LICENSE) for full details.

---

## Author

<p>
Built by <strong>Maroua Boudoukha</strong> · ML/AI Engineer · Web3 Builder
</p>

<p>
  <a href="https://linkedin.com/in/maroua-boudoukha"><img src="https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin"/></a>
  <a href="mailto:maroua@maroua-boudoukha.com"><img src="https://img.shields.io/badge/Email-Contact-00CED1?style=flat-square&logo=gmail&logoColor=white"/></a>
  <a href="https://github.com/MarouaBoud"><img src="https://img.shields.io/badge/GitHub-Follow-181717?style=flat-square&logo=github"/></a>
</p>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00CED1,100:0a0a0f&height=80&section=footer" width="100%"/>
