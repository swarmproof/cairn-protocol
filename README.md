<div align="center">

<img src="./assets/cover.png" alt="CAIRN Protocol - Agent Failure and Recovery Protocol" width="100%"/>

<p>
  <img src="https://img.shields.io/badge/Status-Live_on_Base_Sepolia-00CED1?style=flat-square&logo=ethereum&logoColor=white" alt="Status"/>
  <img src="https://github.com/swarmproof/cairn-protocol/actions/workflows/tests.yml/badge.svg" alt="Tests"/>
  <img src="https://img.shields.io/badge/Contracts-5_Deployed-008B8B?style=flat-square" alt="Contracts"/>
  <img src="https://img.shields.io/badge/Tests-381_passing-00CED1?style=flat-square" alt="Tests"/>
  <img src="https://img.shields.io/badge/Chain_ID-84532-0052FF?style=flat-square&logo=coinbase&logoColor=white" alt="Chain ID"/>
  <img src="https://img.shields.io/badge/ERC-CAIRN_Proposal-008B8B?style=flat-square" alt="ERC"/>
</p>

<p>
  <a href="https://cairn-protocol.vercel.app"><img src="https://img.shields.io/badge/Live_Demo-Frontend-00CED1?style=flat-square" alt="Live Demo"/></a>
  <a href="./WHITEPAPER_V2.md"><img src="https://img.shields.io/badge/Whitepaper-v2.0-008B8B?style=flat-square" alt="Whitepaper"/></a>
  <a href="./ERC-CAIRN.md"><img src="https://img.shields.io/badge/ERC_Spec-Draft-20B2AA?style=flat-square" alt="ERC Spec"/></a>
  <a href="./docs/architecture.md"><img src="https://img.shields.io/badge/Architecture-Docs-008B8B?style=flat-square" alt="Architecture"/></a>
  <a href="https://thegraph.com/studio/subgraph/cairn"><img src="https://img.shields.io/badge/Subgraph-The_Graph-6748fe?style=flat-square" alt="Subgraph"/></a>
</p>

<br/>

> ⚠️ **Testnet only.** Deployed on Base Sepolia (Chain ID: 84532). Mainnet deployment pending security audit.

<br/>

> CAIRN turns every agent failure into a lesson every other agent inherits — enforced by escrow, validated by attestation, owned by no one.
>
> *Agents learn together.*

<br/>

</div>

---

**→ Evaluating the protocol?** [Whitepaper v2](./WHITEPAPER_V2.md) → [ERC Spec](./ERC-CAIRN.md)
**→ Integrating CAIRN?** [Quick Start](#quick-start) → [Integration Guide](./docs/integration.md)
**→ Auditing contracts?** [Contracts](#deployed-contracts-base-sepolia) → [Security](./SECURITY.md)
**→ Reproducing the simulation?** [`simulation/`](./simulation) → `python3 -m simulation.run_eq4` (seed=42)

---

## The Problem: Invisible Failures, Wasted Work

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
- 20 restarts × $15 gas (duplicate work) = $300 gas waste
- 20 failures × 4 hours avg delay × $50/hour opportunity = $4,000 opportunity cost
- Total: ~$5,300/month lost to unrecovered failures
```

---

## A Failure Story: What Happens Today

**Scenario:** DeFi rebalancing agent on Base
**Time:** 2:47am UTC, Saturday
**Task:** Rebalance $12,000 across 3 pools

<table>
<tr>
<td width="50%" valign="top">

### ❌ Without CAIRN

| Step | Action | Result |
|------|--------|--------|
| 1 | Price fetch | ✅ SUCCESS |
| 2 | Approve token A | ✅ SUCCESS |
| 3 | Swap on DEX | ❌ **FAILED** — rate limit (429) |

**What happened next:**
- Agent stopped. No heartbeat for 45 minutes.
- Escrow: $45 locked in ambiguous state
- Operator notified: 7:15am (4.5 hours later)
- Resolution: Manual restart from scratch
- Work lost: Approvals (Step 2) must be re-done

**Total cost:** $45 escrow delay + $12 gas + 4.5 hours

</td>
<td width="50%" valign="top">

### ✅ With CAIRN

| Time | Event |
|------|-------|
| 2:47am | Agent fails (rate limit) |
| 2:52am | CAIRN detects (liveness timeout) |
| 2:52am | Classified: RESOURCE failure, score: 0.74 |
| 2:53am | Fallback agent assigned from pool |
| 2:53am | Fallback reads checkpoints — approvals preserved |
| 3:08am | Task completed by fallback |
| 3:08am | Escrow split: Original 66% / Fallback 33% |

**Total delay: 21 minutes** (vs. 4.5 hours)
**Work preserved:** Yes (checkpoint 2)
**Escrow settled:** Fairly, proportional to verified work

</td>
</tr>
</table>

---

## Why Now

| Signal | Status |
|--------|--------|
| **ERC-8183 is live** | Agent escrow infrastructure shipped March 2026 |
| **~2,000 mechs deployed on Olas** | ~500 active daily — real fallback pool available today |
| **10M+ agent-to-agent transactions** | Real economic activity flowing through agent rails |
| **~50% multi-agent task completion rate** | Per Lu et al. 2025 across TaskWeaver, MetaGPT, AutoGen |


The infrastructure is ready. The problem is severe. The gap is real.

---

## The Cairn Metaphor

A cairn is a stack of stones left by travelers to mark the path — so the next traveler knows where to go, and where not to. Every agent failure leaves a cairn. Every future agent reads it.

Travelers in wilderness stack stones — cairns — to mark where they have been, which paths are safe, and which lead nowhere. Each cairn is left by one traveler but read by every traveler who comes after. No traveler owns the cairn network. Every traveler benefits from it.

CAIRN applies this to agents. Every failure leaves a cairn — an execution record that marks this exact task type, this exact failure mode, this exact cost. Every future agent reads the cairns before setting out. The ecosystem navigates by accumulated failure intelligence, not blind optimism.

---

## What is CAIRN?

**CAIRN is a standardized agent failure and recovery protocol.**

It defines the exact sequence of events that must occur when an agent fails mid-task — from detection, through classification, through fallback assignment, through settlement — without requiring any human intervention and without requiring trust between agents.

### The Protocol in One Paragraph

An operator initiates a task with a budget, deadline, and task type. Before the task starts, CAIRN queries the execution intelligence layer for known failure patterns on this task type and recommends the best-fit agent. The agent runs. It emits liveness signals. It writes checkpoints after each subtask. If it fails — for any reason — CAIRN detects it automatically, classifies the failure, computes a recovery score, and either assigns a fallback agent (who resumes from the last checkpoint) or routes to dispute. On resolution, escrow splits proportionally between the original and fallback agents based on verified work done. The execution record is written. The intelligence layer grows. The next agent inherits the lesson.

### Secondary Output: Execution Intelligence

As a byproduct of the recovery protocol running, CAIRN accumulates an **execution intelligence layer** — a shared, queryable record of every failure, every recovery, and every successful completion across the ecosystem.

This is what makes CAIRN compound in value over time. The knowledge graph grows automatically. The more agents integrate CAIRN, the richer the intelligence layer becomes. Agents query it before starting tasks. The ecosystem gets smarter from every failure.

**The knowledge graph is the byproduct. The recovery protocol is the core.**

---

## What CAIRN is NOT

- **Not a new agent framework.** CAIRN wraps any existing framework — LangGraph, Olas SDK, AgentKit, custom builds.
- **Not a knowledge graph product.** Bonfires (the visualization layer) is a window into the intelligence layer, not the protocol itself.
- **Not a centralized service.** Every state transition is enforced by the CAIRN state machine contract. No server. No admin key. No human required.
- **Not a replacement for ERC-8183 or ERC-8004.** CAIRN integrates and extends both. It is an ERC-8183 Hook and an ERC-8004 reputation writer.
- **Not optional infrastructure.** The escrow condition makes record-writing mandatory — agents cannot receive payment without completing the protocol.

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
                    │  score ≥ 0.35       score < 0.35        │
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

| Class | Trigger | Class weight *F* (v2) | Default Path |
|-------|---------|------------------------|--------------|
| **LIVENESS** | Heartbeat missed beyond `heartbeat_interval` | 0.70 (high recovery) | RECOVERING |
| **RESOURCE** | Budget exceeded or deadline passed | 0.30 (partial recovery) | RECOVERING / DISPUTED |
| **LOGIC** | Invalid checkpoint, schema violation, hallucination | 0.00 (no recovery) | DISPUTED |

**Recovery Score Formula (v2 — multiplicative):**
```
r = F^0.80 × B^0.35 × D^0.15
```

Routing: `r ≥ 0.40` → RECOVERING (full scope) | `0.35 ≤ r < 0.40` → RECOVERING (reduced scope) | `r < 0.35` → DISPUTED

The multiplicative form captures the "any-factor-kills-it" dynamic: if budget, deadline, or class recoverability approaches zero, the score collapses to zero — matching the ground-truth recovery dynamics. The formula was selected after Monte Carlo simulation across 100,000 task-failure events and 16 experiments comparing it against three linear alternatives; see [Whitepaper §6.4](./WHITEPAPER_V2.md) and [`simulation/RESULTS_EQ4.md`](./simulation/RESULTS_EQ4.md).

> **Deployment note.** The v2 multiplicative formula with three-tier routing is **deployed and activated** on Base Sepolia (`RecoveryRouterV2` + `CairnCore` with `threeTierRoutingEnabled`). The earlier v1 interim-linear deployment has been superseded. See [PRD-04](./PRDs/PRD-04-V2-UPGRADE/PRD.md) for the upgrade history.

---

## The 14-Action Protocol

<details open>
<summary><b>Phase 1 — Initialization (A1–A3)</b></summary>
<br/>

**A1** · Operator submits task spec: `task_type`, `budget_cap`, `deadline`, `heartbeat_interval`, output schemas per subtask.

**A2** · Protocol queries execution intelligence layer by `task_type` → known failure patterns, real cost distribution from prior executions, recommended agent (highest success rate + reputation), known-bad time windows.

**A3** · Operator confirms. Locks escrow. Pre-authorizes CAIRN for fallback sub-delegation (ERC-7710 caveat: allowed actions + budget cap + fallback pool). State → `RUNNING`.

</details>

<details>
<summary><b>Phase 2 — Running (A4–A6)</b></summary>
<br/>

**A4** · Agent completes subtask N. Writes output to IPFS. Calls `commitCheckpoint(taskId, N, CID, cost)`. Protocol validates CID against declared schema.

**A5** · Agent emits liveness ping: `heartbeat(taskId)`. Resets liveness timer every `heartbeat_interval`.

**A6** · Protocol enforces (public, permissionless — anyone can call): `checkLiveness()` · `checkBudget()` · `checkDeadline()`.

</details>

<details>
<summary><b>Phase 3 — Failed (A7–A8)</b></summary>
<br/>

**A7** · Protocol classifies failure type (LIVENESS / RESOURCE / LOGIC). Computes `recovery_score`. Writes Failure Record to IPFS. Emits `TaskFailed(taskId, recordCID, recoveryScore)`.

**A8** · Routes: `score ≥ 0.6` → RECOVERING (full). `0.3 ≤ score < 0.6` → RECOVERING (reduced). `score < 0.3` → DISPUTED.

</details>

<details>
<summary><b>Phase 4 — Recovering (A9–A11)</b></summary>
<br/>

**A9** · Queries execution intelligence for best fallback: `task_type` match + reputation + availability.

**A10** · Transfers state to fallback: checkpoint CID list, `next_subtask_index`, remaining budget, remaining deadline, scoped permissions (ERC-7710 pre-authorized caveat from A3).

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

**A13** · Holds escrow. Writes negative reputation to ERC-8004. Exposes Failure Record CID publicly. Starts `arbiter_timeout` clock. Emits `TaskDisputed(taskId, recordCID, arbiterTimeout)`.

**A14** · Registered arbiter reads Failure Record, calls `rule(taskId, outcome)`. Arbiter fee deducted from escrow. If timeout expires with no arbiter: auto-refund operator. Either path → RESOLVED.

</details>

---

## Architecture

Four layers. Only the CAIRN Protocol Layer is new code. Everything else integrates live existing infrastructure.

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
│ ERC-8183 (escrow + hooks) · ERC-8004 (identity + reputation)  │
│ ERC-7710 (delegation) · Olas Mech Marketplace                 │
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

## Quick Start

```bash
pip install cairn-sdk

# or clone locally
git clone https://github.com/swarmproof/cairn-protocol
cd cairn-protocol && pip install -e ./sdk
```

```python
from cairn_sdk import CairnClient, CairnAgent
import os

client = CairnClient(
    rpc_url="https://sepolia.base.org",
    contract_address="0x9917E509742495EbEedfF6335406096B2e1aFB3a",  # CairnCore (v2)
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

## AI Agent Skill Endpoint

CAIRN exposes machine-readable endpoints for AI agents to fetch integration instructions:

```bash
# Quick integration guide (5-minute setup)
curl -s https://cairn-protocol.vercel.app/skill.md

# Full protocol documentation
curl -s https://cairn-protocol.vercel.app/cairn.md
```

These endpoints return markdown that AI agents can parse to integrate CAIRN into their workflows automatically.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Whitepaper v2.0](./WHITEPAPER_V2.md) | The protocol specification — problem, mechanism, formal proofs, simulation-validated formula, economic model |
| [ERC Specification](./ERC-CAIRN.md) | Technical standard (EIP-1 format draft) |
| [Security](./SECURITY.md) | Security model, attack vectors, mitigations |
| [Changelog](./CHANGELOG.md) | Version history |
| [Simulation results](./simulation/) | Monte Carlo calibration (Runs 1-4, 16 experiments, 100k events each); see `RESULTS_EQ4.md` for the headline multiplicative-formula result |

### Technical Documentation

| Document | Description |
|----------|-------------|
| [Concepts](./docs/concepts.md) | Failure taxonomy, state machine, glossary |
| [Architecture](./docs/architecture.md) | System design, protocol flow diagrams |
| [Execution Intelligence](./docs/execution-intelligence.md) | Knowledge graph, queries, network effects |
| [Integration](./docs/integration.md) | Checkpoint protocol, fallback pool, guides |
| [Contracts](./docs/contracts.md) | Interfaces, schemas, component reference |
| [Standards](./docs/standards.md) | ERC-8183, ERC-8004, ERC-7710, Olas integration |
| [Observer](./docs/observer.md) | CAIRN Observer — failure cost visibility layer |
| [CLI Usage](./cli/CLI_IMPLEMENTATION.md) | Command-line tool for task management |
| [Multi-Sig Governance](./docs/MULTI_SIG_GOVERNANCE.md) | Gnosis Safe setup, parameter management |
| [Olas Integration](./docs/olas-integration.md) | Mech marketplace adapter, fallback pool |

---

## Protocol Status

| Property | Value |
|----------|-------|
| Specification | **v2** (this paper — multiplicative recovery score, three-tier routing) |
| Testnet deployment | **v2** (multiplicative, three-tier routing) — Live on Base Sepolia, Chain ID 84532 |
| Whitepaper | [v2.0 — April 2026](./WHITEPAPER_V2.md) |
| ERC Dependencies | ERC-8183, ERC-8004, ERC-7710 |
| v1 → v2 migration | Governance-gated via `IRecoveryRouter` interface; see [PRD-04](./PRDs/PRD-04-V2-UPGRADE/PRD.md) |

### Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Whitepaper v2.0 | ✅ Released | Formal protocol specification, proofs, simulation-validated formula |
| Smart contracts (v2) | ✅ Deployed | Live on Base Sepolia — 6 contracts, 408 tests passing |
| RecoveryRouterV2 (v2) | ✅ Implemented | 24 unit tests, gas measured (avg 5,748 / max 19,935) — ready for governance upgrade |
| Monte Carlo simulation | ✅ Complete | 4 runs, 16 experiments, 100k events each — see [`simulation/`](./simulation) |
| PRD-01 MVP | ✅ Complete | v1 protocol shipped |
| PRD-03 Recovery score calibration | ✅ Complete | Derived the v2 multiplicative formula and its parameters |
| PRD-04 v2 contract upgrade | ✅ Complete | Three-tier routing, 20% stake, schema validation deployed + activated on Base Sepolia |
| SDK (Python) | ✅ Complete | CairnClient, CairnAgent, CheckpointStore, Observers |
| CLI Tool | ✅ Complete | submit-task, heartbeat, checkpoint, monitor, recover |
| Subgraph | ✅ Deployed | The Graph Studio indexing |
| Upgradeability | 🟡 Variants ready | UUPS-upgradeable variants implemented (OpenZeppelin 5.x); the deployed set is non-upgradeable, pending the v2 governance upgrade |
| Frontend | ✅ Deployed | Next.js 14, wagmi |

See [`PRDs/README.md`](./PRDs/README.md) for the full roadmap.

### Deployed Contracts (Base Sepolia)

The **v2 protocol** (multiplicative recovery score, three-tier routing, 20% arbiter stake, checkpoint schema validation) is deployed and activated on Base Sepolia:

| Contract | Address | Description |
|----------|---------|-------------|
| **CairnCore** | [`0x9917E509742495EbEedfF6335406096B2e1aFB3a`](https://sepolia.basescan.org/address/0x9917E509742495EbEedfF6335406096B2e1aFB3a) | Main entry point — 6-state machine, task lifecycle |
| CairnGovernance | [`0xA14272Ab4B782Dc139B76Ea994117b924727221C`](https://sepolia.basescan.org/address/0xA14272Ab4B782Dc139B76Ea994117b924727221C) | Protocol parameters, admin executor |
| RecoveryRouterV2 | [`0x1481586D976454ad17CfB2E9a4176a0826Ec9A70`](https://sepolia.basescan.org/address/0x1481586D976454ad17CfB2E9a4176a0826Ec9A70) | Multiplicative recovery scoring, three-tier routing |
| FallbackPool | [`0x363a0812333aE98945bE4c9Cd17E97aD383C5D07`](https://sepolia.basescan.org/address/0x363a0812333aE98945bE4c9Cd17E97aD383C5D07) | Agent registration, selection algorithm |
| ArbiterRegistry | [`0x3AF10DDAd783Cf10d5CD938F641B8CB96e1F35eB`](https://sepolia.basescan.org/address/0x3AF10DDAd783Cf10d5CD938F641B8CB96e1F35eB) | Dispute resolution (20% arbiter stake) |

All five contracts are source-verified on BaseScan. The deployed contracts are the **non-upgradeable base implementations**; UUPS-upgradeable variants (OpenZeppelin 5.x) exist in `contracts/src/upgradeable/` but are not deployed. See [PRD-04](./PRDs/PRD-04-V2-UPGRADE/PRD.md).

### Live Demo

| Resource | URL |
|----------|-----|
| **Frontend** | [cairn-protocol.vercel.app](https://cairn-protocol.vercel.app) |
| **Subgraph** | [The Graph Studio](https://thegraph.com/studio/subgraph/cairn) |
| **Query Endpoint** | `https://api.studio.thegraph.com/query/1744842/cairn/v1.0.0` |

---

## Quick Links

- **Understand CAIRN:** [Whitepaper v2](./WHITEPAPER_V2.md) → [Concepts](./docs/concepts.md)
- **Technical Spec:** [ERC-CAIRN](./ERC-CAIRN.md) → [Contracts](./docs/contracts.md)
- **Build with CAIRN:** [Integration Guide](./docs/integration.md)
- **Security:** [Security Model](./SECURITY.md)
- **Reproduce the simulation:** `python3 -m simulation.run_eq4` (seed=42, deterministic on NumPy ≥1.20)

---

## Standards Integration

CAIRN integrates with existing Ethereum standards rather than replacing them:

| Standard | What It Provides | Role in CAIRN |
|----------|------------------|---------------|
| **ERC-8183** | Standardized escrow for agent jobs with lifecycle hooks | Holds payment until task completes; CAIRN registers as a lifecycle hook to intercept failures |
| **ERC-8004** | On-chain agent identity and reputation registry | Verifies agent identity; CAIRN writes success/failure signals to reputation scores |
| **ERC-7710** | Scoped permission delegation with caveats | Enables pre-authorized fallback assignment without requiring new signatures at recovery time |
| **Olas Mech Marketplace** | Registry of available agent services with staking | Provides the fallback agent pool; CAIRN queries for best-fit backup agents |

For detailed integration guidance, see [Standards Documentation](./docs/standards.md).

---

## Repository Structure

```
cairn-protocol/
├── contracts/          # Solidity smart contracts (Foundry)
│   ├── src/           # Core contracts (CairnCore, RecoveryRouter, RecoveryRouterV2, FallbackPool, ArbiterRegistry)
│   └── test/          # 408 tests passing
├── sdk/               # Python SDK (CairnClient, CairnAgent, CheckpointStore)
├── cli/               # CLI tool — task management, monitoring
├── frontend/          # Next.js 14 dashboard
├── pipeline/          # Off-chain event listener
├── subgraph/          # The Graph indexer
├── simulation/        # Monte Carlo recovery-score calibration (Runs 1-4, 16 experiments)
├── PRDs/              # Product requirements documents
├── docs/              # Technical documentation
├── PUBLICATION/       # arXiv submission bundle (whitepaper LaTeX, figures, metadata)
└── WHITEPAPER_V2.md   # Protocol specification
```

## What Makes CAIRN Different

| # | Differentiator |
|---|----------------|
| 1 | **Not a framework** — Wraps any agent SDK (LangGraph, Olas, AgentKit, CrewAI, AutoGen) |
| 2 | **Escrow-enforced** — Agents cannot get paid without completing the protocol's record-writing |
| 3 | **Automatic recovery** — No human-in-the-loop required between task submission and settlement |
| 4 | **Simulation-validated formula** — The v2 multiplicative recovery score is within 0.93pp of the Bayes-optimal floor on the calibrated ground-truth model |
| 5 | **Network effects** — Every failure becomes a queryable record; the intelligence layer grows with task throughput |

---

## License

See [LICENSE](./LICENSE) for details.

| Component | License |
|-----------|---------|
| [ERC-CAIRN.md](./ERC-CAIRN.md) | CC0-1.0 |
| [WHITEPAPER_V2.md](./WHITEPAPER_V2.md) | All Rights Reserved (see header copyright notice) |
| [contracts/](./contracts/) | GPL-3.0-or-later |
| [sdk/](./sdk/), [cli/](./cli/) | Apache-2.0 |
| [subgraph/](./subgraph/) | MIT |
| [frontend/](./frontend/) | AGPL-3.0-or-later |
| [docs/](./docs/) | CC BY 4.0 |

---

## Contributing

Contributions are welcome! Whether it's bug fixes, new features, documentation improvements, or ideas — we'd love your help.

See **[CONTRIBUTING.md](./CONTRIBUTING.md)** for:
- Development setup (Foundry, Python, Node.js)
- Code style guidelines
- Testing requirements
- Pull request process

By contributing, you agree to license your contributions under the same license as the component you're modifying.

---

## Cite this work

If you use CAIRN in your research, please cite the whitepaper:

```bibtex
@misc{boudoukha2026cairn,
  title  = {CAIRN: A Protocol for Agent Failure Detection, Classification, and Recovery in the On-Chain Agent Economy},
  author = {Boudoukha, Maroua},
  year   = {2026},
  note   = {Whitepaper v2.0. Reproducible simulation: python3 -m simulation.run\_eq4 (seed=42).},
  url    = {https://github.com/swarmproof/cairn-protocol}
}
```

An arXiv preprint will be linked here after submission acceptance.

---

## Author

<p>
Built by <strong>Maroua Boudoukha</strong> · ML/AI Engineer · Web3 Builder
</p>

<p>
  <a href="https://linkedin.com/in/maroua-boudoukha"><img src="https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin"/></a>
  <a href="mailto:maroua@maroua-boudoukha.com"><img src="https://img.shields.io/badge/Email-Contact-00CED1?style=flat-square&logo=gmail&logoColor=white"/></a>
  <a href="https://github.com/swarmproof"><img src="https://img.shields.io/badge/GitHub-Follow-181717?style=flat-square&logo=github"/></a>
</p>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:00CED1,100:0a0a0f&height=80&section=footer" width="100%"/>
