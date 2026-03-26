<div align="center">

<img src="./.synthesis/cover.png" alt="CAIRN Protocol - Agent Failure and Recovery Protocol" width="100%"/>

<p>
  <img src="https://img.shields.io/badge/Status-Live%20on%20Base%20Sepolia-00CED1?style=flat-square&logo=ethereum&logoColor=white"/>
  <img src="https://github.com/MarouaBoud/cairn-protocol/actions/workflows/tests.yml/badge.svg" alt="Tests"/>
  <img src="https://img.shields.io/badge/Contracts-6%20Deployed-008B8B?style=flat-square"/>
  <img src="https://img.shields.io/badge/Tests-315%20%7C%2098.95%25%20coverage-00CED1?style=flat-square"/>
  <img src="https://img.shields.io/badge/Chain%20ID-84532-0052FF?style=flat-square&logo=coinbase&logoColor=white"/>
  <img src="https://img.shields.io/badge/ERC-CAIRN%20Proposal-008B8B?style=flat-square"/>
</p>

<p>
  <a href="https://cairn-protocol-iona-78423aa1.vercel.app"><img src="https://img.shields.io/badge/Live%20Demo-Frontend-00CED1?style=flat-square"/></a>
  <a href="./WHITEPAPER.md"><img src="https://img.shields.io/badge/Whitepaper-Read-008B8B?style=flat-square"/></a>
  <a href="./ERC-CAIRN.md"><img src="https://img.shields.io/badge/ERC%20Spec-Draft-20B2AA?style=flat-square"/></a>
  <a href="./docs/architecture.md"><img src="https://img.shields.io/badge/Architecture-Docs-008B8B?style=flat-square"/></a>
  <a href="https://thegraph.com/studio/subgraph/cairn"><img src="https://img.shields.io/badge/Subgraph-The%20Graph-6748fe?style=flat-square"/></a>
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

**→ Evaluating the protocol?** [Whitepaper](./WHITEPAPER.md) → [ERC Spec](./ERC-CAIRN.md)
**→ Integrating CAIRN?** [Quick Start](#quick-start) → [Integration Guide](./docs/integration.md)
**→ Auditing contracts?** [Contracts](#deployed-contracts-base-sepolia) → [Security](./SECURITY.md)
**→ Hackathon judges?** [Submission](#hackathon-submission--synthesis-2026) → [Live Demo](https://cairn-protocol-iona-78423aa1.vercel.app)

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
| **600+ agents on Olas** | Real fallback pool available today |
| **$479M aGDP** | Real money flowing through agent transactions |
| **80% workflow failure rate** | At 85% per-action success, most multi-step tasks fail |


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
                    │  score ≥ 0.6        score < 0.6         │
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

Routing: `score ≥ 0.6` → RECOVERING | `score < 0.6` → DISPUTED

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

**A8** · Routes: `score ≥ 0.6` → RECOVERING. `score < 0.6` → DISPUTED.

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

## AI Agent Skill Endpoint

CAIRN exposes machine-readable endpoints for AI agents to fetch integration instructions:

```bash
# Quick integration guide (5-minute setup)
curl -s https://cairn-protocol-iona-78423aa1.vercel.app/skill.md

# Full protocol documentation
curl -s https://cairn-protocol-iona-78423aa1.vercel.app/cairn.md
```

These endpoints return markdown that AI agents can parse to integrate CAIRN into their workflows automatically.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Whitepaper](./WHITEPAPER.md) | Why CAIRN exists — problem, philosophy, economics |
| [ERC Specification](./ERC-CAIRN.md) | Technical standard (EIP format) |
| [Security](./SECURITY.md) | Security model, attack vectors, mitigations |
| [Changelog](./CHANGELOG.md) | Version history |

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
| Version | 1.0 |
| Status | **Live on Base Sepolia** |
| Network | Base Sepolia (Chain ID: 84532) |
| ERC Dependencies | ERC-8183, ERC-8004, ERC-7710 |

### Implementation Progress (Synthesis Hackathon 2026)

| Component | Status | Notes |
|-----------|--------|-------|
| PRD-00 Vision | ✅ Complete | Full protocol specification |
| PRD-01 MVP | ✅ Complete | Hackathon submission |
| Smart Contracts | ✅ Deployed | 315 tests, 98.95% coverage |
| Deployment | ✅ Live | Base Sepolia (6 contracts) |
| SDK (Python) | ✅ Complete | CairnClient, CairnAgent, CheckpointStore, Observers |
| CLI Tool | ✅ Complete | submit-task, heartbeat, checkpoint, monitor, recover |
| Subgraph | ✅ Deployed | The Graph Studio indexing |
| Upgradeable | ✅ Complete | UUPS proxy pattern (OpenZeppelin 5.x) |
| Frontend | ✅ Deployed | Next.js 14, wagmi |
| PRD-07 Optimization | ✅ Complete | Merkle checkpoint batching — significant gas reduction |

See [`PRDs/README.md`](./PRDs/README.md) for full roadmap.

### Deployed Contracts (Base Sepolia)

| Contract | Address | Description |
|----------|---------|-------------|
| **CairnCore** | [`0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640`](https://sepolia.basescan.org/address/0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640) | Main entry point — 6-state machine, task lifecycle |
| CairnGovernance | [`0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f`](https://sepolia.basescan.org/address/0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f) | Protocol parameters, admin controls |
| RecoveryRouter | [`0xE52703946cb44c12A6A38A41f638BA2D7197a84d`](https://sepolia.basescan.org/address/0xE52703946cb44c12A6A38A41f638BA2D7197a84d) | Failure classification, recovery scoring |
| FallbackPool | [`0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0`](https://sepolia.basescan.org/address/0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0) | Agent registration, selection algorithm |
| ArbiterRegistry | [`0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68`](https://sepolia.basescan.org/address/0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68) | Dispute resolution, appeals |
| CairnTaskMVP *(legacy)* | [`0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417`](https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417) | Legacy MVP (4-state) — use CairnCore for production |

All contracts use **UUPS proxy pattern** (OpenZeppelin 5.x). Upgradeable without redeployment.

### Live Demo

| Resource | URL |
|----------|-----|
| **Frontend** | [cairn-protocol-iona-78423aa1.vercel.app](https://cairn-protocol-iona-78423aa1.vercel.app) |
| **Subgraph** | [The Graph Studio](https://thegraph.com/studio/subgraph/cairn) |
| **Query Endpoint** | `https://api.studio.thegraph.com/query/1744842/cairn/v1.0.0` |

---

## Quick Links

- **Understand CAIRN:** [Whitepaper](./WHITEPAPER.md) → [Concepts](./docs/concepts.md)
- **Technical Spec:** [ERC-CAIRN](./ERC-CAIRN.md) → [Contracts](./docs/contracts.md)
- **Build with CAIRN:** [Integration Guide](./docs/integration.md)
- **Security:** [Security Model](./SECURITY.md)

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

<details>
<summary><b>Hackathon Submission — Synthesis 2026</b></summary>
<br/>

**Tracks:** Protocol Labs: Agents With Receipts • Let the Agent Cook

### Onchain Artifacts

| Artifact | Value |
|----------|-------|
| **Chain** | Base Sepolia (Chain ID: 84532) |
| **Contracts** | 6 deployed — see [Deployed Contracts](#deployed-contracts-base-sepolia) above |
| **Deployment Tx** | [`0xeeee5fc6...`](https://sepolia.basescan.org/tx/0xeeee5fc6281d95e14b8362ba950407b83818b31ba04813489dd5a0120cea825b) |
| **Test Coverage** | 98.95% (315 tests) |

### Agent Metadata

| File | Description |
|------|-------------|
| [`.synthesis/agent.json`](./.synthesis/agent.json) | Agent identity, team structure, deployment info |
| [`.synthesis/agent_log.json`](./.synthesis/agent_log.json) | Chronological build log |
| [`.synthesis/CONVERSATION_LOG.md`](./.synthesis/CONVERSATION_LOG.md) | Session summaries and decision log |

### Track Requirements: "Agents With Receipts"

CAIRN implements the complete agent receipts pattern:

| Requirement | Implementation |
|-------------|----------------|
| **Execution Records** | Every task creates on-chain record with checkpoints, heartbeats, settlement |
| **Failure Classification** | RecoveryRouter classifies failures (TIMEOUT, REVERTED, RESOURCE, LOGIC, UNKNOWN) |
| **Recovery Scoring** | Computed recovery probability before fallback assignment |
| **Settlement Receipts** | Proportional escrow splits with on-chain verification |
| **Collective Intelligence** | Bonfires integration writes failure patterns to knowledge graph |

### What Makes CAIRN Different

| # | Differentiator |
|---|----------------|
| 1 | **Not a framework** — Wraps any agent SDK (LangGraph, Olas, AgentKit) |
| 2 | **Escrow-enforced** — Agents can't get paid without completing the protocol |
| 3 | **Automatic recovery** — No human intervention needed for fallback assignment |
| 4 | **Network effects** — Every failure teaches every future agent |

### Repository Structure

```
cairn-protocol/
├── contracts/          # Solidity smart contracts (Foundry)
│   ├── src/           # Core contracts (CairnCore, RecoveryRouter, FallbackPool)
│   └── test/          # 315 tests, 98.95% coverage
├── sdk/               # Python SDK (CairnClient, CairnAgent, CheckpointStore)
├── cli/               # CLI tool — task management, monitoring
├── frontend/          # Next.js 14 dashboard
├── pipeline/          # Off-chain event listener
├── subgraph/          # The Graph indexer
├── PRDs/              # Product requirements documents
└── docs/              # Technical documentation
```

</details>

---

## License

See [LICENSE](./LICENSE) for details.

| Component | License |
|-----------|---------|
| [ERC-CAIRN.md](./ERC-CAIRN.md) | CC0-1.0 |
| [WHITEPAPER.md](./WHITEPAPER.md) | All Rights Reserved |
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
