# CAIRN Protocol — PRD Roadmap

> From Hackathon MVP to Full Protocol

## Overview

This folder contains the Product Requirements Documents (PRDs) for CAIRN protocol, structured as a progressive build from a hackathon-ready MVP to the complete protocol vision. Each PRD is a folder containing the main PRD document, status tracker, and spawn prompts for agent team execution.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           CAIRN PRD PROGRESSION                                │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   PRD-00 ────────────────────────────────────────────────────────────────►   │
│   PROTOCOL VISION (North Star - What we're building toward)                  │
│                                                                               │
│   ════════════════════════════════════════════════════════════════════════   │
│                                                                               │
│   PRD-01          PRD-02          PRD-03          PRD-04          PRD-05     │
│   ┌─────┐        ┌─────┐        ┌─────┐        ┌─────┐        ┌─────┐       │
│   │ MVP │───────►│CORE │───────►│INTEL│───────►│POOL │───────►│ARBIT│       │
│   │     │        │RECOV│        │LAYER│        │     │        │     │       │
│   └─────┘        └─────┘        └─────┘        └─────┘        └─────┘       │
│   Hackathon      Recovery       Execution      Fallback       Arbiter       │
│   2 weeks        Scoring        Intelligence   Ecosystem      Network       │
│                                                                               │
│   ════════════════════════════════════════════════════════════════════════   │
│                                                                               │
│                    PRD-06                         PRD-07                      │
│               FULL INTEGRATION              GAS OPTIMIZATION                  │
│             (Protocol Complete)           (Production Scaling)                │
│                      │                            │                           │
│                      └────────────┬───────────────┘                           │
│                                   ▼                                           │
│                           PRODUCTION READY                                    │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## PRD Index

| PRD | Name | Scope | Timeline | Status |
|-----|------|-------|----------|--------|
| [PRD-00](./PRD-00-PROTOCOL-VISION/PRD.md) | Protocol Vision | Full CAIRN specification | Reference | 📋 Draft |
| [PRD-01](./PRD-01-MVP-HACKATHON/PRD.md) | MVP Hackathon | Synthesis-ready demo | 1 weeks | 🚧 In Progress |
| [PRD-02](./PRD-02-CORE-RECOVERY/PRD.md) | Core Recovery | Enhanced recovery scoring | +2 weeks | ⏳ Planned |
| [PRD-03](./PRD-03-EXECUTION-INTELLIGENCE/PRD.md) | Execution Intelligence | Knowledge graph layer | +3 weeks | ⏳ Planned |
| [PRD-04](./PRD-04-FALLBACK-ECOSYSTEM/PRD.md) | Fallback Ecosystem | Full pool + reputation | +3 weeks | ⏳ Planned |
| [PRD-05](./PRD-05-ARBITER-NETWORK/PRD.md) | Arbiter Network | Dispute resolution | +2 weeks | ⏳ Planned |
| [PRD-06](./PRD-06-FULL-INTEGRATION/PRD.md) | Full Integration | Complete protocol | +2 weeks | ⏳ Planned |
| [PRD-07](./PRD-07-CHECKPOINT-OPTIMIZATION/PRD.md) | Checkpoint Optimization | Gas-efficient Merkle batching | +2 weeks | ⏳ Planned |

---

## Folder Structure

Each PRD is organized as a folder with spawn prompts for agent team execution:

```
PRDs/
├── README.md                              # This file
│
├── PRD-00-PROTOCOL-VISION/
│   └── PRD.md                             # Full protocol reference
│
├── PRD-01-MVP-HACKATHON/
│   ├── PRD.md                             # Synthesis hackathon MVP
│   ├── STATUS.md                          # Pipeline tracking
│   ├── spawn-contract-dev.md              # Contract development agent
│   ├── spawn-sdk-dev.md                   # SDK development agent
│   ├── spawn-frontend-dev.md              # Frontend development agent
│   └── spawn-integration.md               # Integration testing agent
│
├── PRD-02-CORE-RECOVERY/
│   ├── PRD.md                             # Recovery scoring & routing
│   ├── STATUS.md                          # Pipeline tracking
│   ├── spawn-recovery-contract.md         # Contract agent
│   └── spawn-recovery-sdk.md              # SDK agent
│
├── PRD-03-EXECUTION-INTELLIGENCE/
│   ├── PRD.md                             # Knowledge graph layer
│   ├── STATUS.md                          # Pipeline tracking
│   ├── spawn-intel-infra.md               # Infrastructure agent
│   ├── spawn-intel-pipeline.md            # Pipeline agent
│   └── spawn-intel-api.md                 # API agent
│
├── PRD-04-FALLBACK-ECOSYSTEM/
│   ├── PRD.md                             # Fallback pool & reputation
│   ├── STATUS.md                          # Pipeline tracking
│   ├── spawn-pool-erc.md                  # ERC integration agent
│   ├── spawn-pool-contract.md             # Contract agent
│   ├── spawn-pool-sdk.md                  # SDK agent
│   └── spawn-agent-onboarding.md          # Agent SDK & framework integrations
│
├── PRD-05-ARBITER-NETWORK/
│   ├── PRD.md                             # Dispute resolution
│   ├── STATUS.md                          # Pipeline tracking
│   ├── spawn-arbiter-contract.md          # Contract agent
│   └── spawn-arbiter-sdk.md               # SDK agent
│
├── PRD-06-FULL-INTEGRATION/
│   ├── PRD.md                             # Complete protocol
│   ├── STATUS.md                          # Pipeline tracking
│   ├── spawn-governance.md                # Governance agent
│   ├── spawn-integration.md               # Integration agent
│   └── spawn-deployment.md                # Deployment agent
│
├── PRD-07-CHECKPOINT-OPTIMIZATION/
│   ├── PRD.md                             # Gas-efficient Merkle batching
│   ├── STATUS.md                          # Pipeline tracking
│   ├── spawn-contract-v2.md               # Contract V2 development
│   ├── spawn-sdk-v2.md                    # SDK V2 development
│   └── spawn-migration.md                 # V1 to V2 migration
│
└── assets/                                # Diagrams, mockups
    ├── state-machine.png
    ├── architecture.png
    └── demo-flow.png
```

---

## Synthesis Hackathon Alignment

**Event:** SYNTHESIS (March 4-23, 2026)
**Building Period:** March 13-23 (~10 days)
**Feedback Phase:** March 18 (judging agents advise projects)

### Track Alignment

| Synthesis Theme | CAIRN Feature | PRD Coverage |
|-----------------|---------------|--------------|
| **Agents that pay** | Escrow settlement, proportional payment by checkpoints | PRD-01 (core), PRD-02 (enhanced) |
| **Agents that trust** | ERC-8004 identity, reputation attestations, stake deposits | PRD-01 (basic), PRD-04 (full) |
| **Agents that cooperate** | Fallback recovery, checkpoint handoff, shared learning | PRD-01 (demo), PRD-03 (intelligence) |
| **Agents that keep secrets** | ERC-7710 scoped delegation, minimal permission exposure | PRD-02 (integration) |

### Key Sponsors to Target

| Sponsor | Relevance | Integration Point |
|---------|-----------|-------------------|
| **Base** | Deployment chain | Primary network |
| **Olas** | Fallback pool (600+ agents) | Mech Marketplace |
| **Virtuals Protocol** | ERC-8183 co-author | Job escrow standard |
| **MetaMask** | ERC-7710 author | Scoped delegation |
| **Protocol Labs / Filecoin** | IPFS storage | Checkpoint & record storage |

---

## MVP Strategy (PRD-01)

### What We're Proving

The hackathon MVP must demonstrate the **core value loop**:

```
Agent fails → CAIRN detects → Fallback recovers → Work preserved → Payment fair
```

### MVP Scope (Must Have)

1. **State Machine** — RUNNING → FAILED → RECOVERING → RESOLVED
2. **Checkpoint Protocol** — Write/read subtask outputs to IPFS
3. **Heartbeat Detection** — Liveness monitoring with public enforcement
4. **Simple Recovery** — Route to available fallback (no scoring yet)
5. **Escrow Settlement** — Split payment by checkpoint count

### MVP Deferred (Post-Hackathon)

- Full recovery scoring formula
- Execution intelligence queries
- Reputation-gated fallback pool
- Arbiter dispute resolution
- ERC-7710 sub-delegation
- Governance & multi-sig

### Demo Scenario

**"The 2:47am Recovery"** — Live demonstration:
1. DeFi agent starts 5-step rebalancing task
2. Agent fails at step 3 (simulated rate limit)
3. CAIRN detects failure via heartbeat miss
4. Fallback agent assigned, receives checkpoint state
5. Fallback completes steps 4-5
6. Escrow splits: 60% original (3 checkpoints) / 40% fallback (2 checkpoints)

---

## Progressive Build Path

### Phase 1: MVP (PRD-01) — Hackathon
**Goal:** Prove the concept works end-to-end
- Minimal viable contracts (~200 LOC)
- Single-agent fallback (hardcoded)
- Manual failure injection for demo
- Basic IPFS checkpoints

### Phase 2: Core Recovery (PRD-02) — Post-Hackathon
**Goal:** Intelligent failure routing
- Failure classification (LIVENESS/RESOURCE/LOGIC)
- Recovery score calculation
- Deterministic routing thresholds
- ERC-7710 delegation integration

### Phase 3: Execution Intelligence (PRD-03) — Month 2
**Goal:** Ecosystem learns from every task
- Structured failure/resolution records
- IPFS → The Graph → Bonfires pipeline
- Pre-task intelligence queries
- Pattern detection (rate limits, time windows)

### Phase 4: Fallback Ecosystem (PRD-04) — Month 2-3
**Goal:** Open, trustworthy fallback pool
- ERC-8004 reputation integration
- Task-type matching
- Stake requirements & slashing
- Multi-fallback ranking

### Phase 5: Arbiter Network (PRD-05) — Month 3
**Goal:** Decentralized dispute resolution
- Arbiter registration & staking
- DISPUTED state handling
- Ruling mechanics & fees
- Timeout auto-refund

### Phase 6: Full Integration (PRD-06) — Month 3-4
**Goal:** Production-ready protocol
- Full ERC-CAIRN standard compliance
- Governance (multi-sig → token)
- Security audit preparation
- Mainnet deployment

---

## Success Metrics

### Hackathon (PRD-01)
- [ ] End-to-end demo working
- [ ] Judges understand value proposition
- [ ] At least 1 sponsor integration highlighted
- [ ] Codebase clean enough for post-hackathon development

### Post-Hackathon (PRD-02-06)
- [ ] 10+ agents integrated in first month
- [ ] 100+ recorded failures in knowledge graph
- [ ] 90%+ recovery success rate for LIVENESS failures
- [ ] 3+ fallback agents in active pool
- [ ] 1+ arbiter registered and operational

---

## Protocol Vision Coverage Matrix

This matrix shows how every section of PRD-00 (Protocol Vision) maps to implementation PRDs, ensuring complete coverage.

### Core Protocol Components

| PRD-00 Section | Component | PRD Coverage | Notes |
|----------------|-----------|--------------|-------|
| §2.1 | State Machine (6 states) | PRD-01 (4-state MVP) → PRD-05 (DISPUTED) | MVP simplifies to 4 states |
| §2.2 | Checkpoint Protocol | PRD-01 | Core from day one |
| §2.3 | Recovery Score Formula | PRD-02 | Post-hackathon enhancement |
| §3.1 | ERC-8183 Job Escrow | PRD-01 | Core integration |
| §3.2 | ERC-8004 Identity | PRD-04 | Reputation-gated fallback |
| §3.3 | ERC-7710 Delegation | PRD-02 | Permission scoping |

### Failure & Recovery

| PRD-00 Section | Component | PRD Coverage | Notes |
|----------------|-----------|--------------|-------|
| §4.1 | Failure Classification | PRD-02 | LIVENESS/RESOURCE/LOGIC |
| §4.2 | Failure Detection | PRD-01 (heartbeat) → PRD-02 (full) | Heartbeat in MVP |
| §4.3 | Routing Algorithm | PRD-02 | Score-based routing |
| §5.1 | Fallback Selection | PRD-04 | Pool matching |
| §5.2 | Reputation System | PRD-04 | ERC-8004 attestations |
| §5.3 | Stake/Slashing | PRD-04 | Economic security |

### Execution Intelligence

| PRD-00 Section | Component | PRD Coverage | Notes |
|----------------|-----------|--------------|-------|
| §6.1 | Failure Records | PRD-03 | IPFS structured storage |
| §6.2 | Knowledge Graph | PRD-03 | The Graph + Bonfires |
| §6.3 | Pre-task Queries | PRD-03 | Intelligence API |
| §6.4 | Pattern Detection | PRD-03 | Rate limits, time windows |

### Dispute Resolution

| PRD-00 Section | Component | PRD Coverage | Notes |
|----------------|-----------|--------------|-------|
| §7.1 | DISPUTED State | PRD-05 | 6th state activation |
| §7.2 | Arbiter Registration | PRD-05 | Staking requirements |
| §7.3 | Ruling Mechanics | PRD-05 | Multi-arbiter consensus |
| §7.4 | Fee Distribution | PRD-05 | Arbiter incentives |

### Production Operations

| PRD-00 Section | Component | PRD Coverage | Notes |
|----------------|-----------|--------------|-------|
| §8.1 | Agent Requirements | PRD-04 (§10) | Wallet, gas, IPFS, events |
| §8.2 | Framework Integrations | PRD-04 (§10) | Olas, LangChain, etc. |
| §8.3 | Monitoring | PRD-04 (§10) | Prometheus, health checks |
| §8.4 | Gas Management | PRD-04 (§10) | Balance monitoring |

### Governance & Deployment

| PRD-00 Section | Component | PRD Coverage | Notes |
|----------------|-----------|--------------|-------|
| §9.1 | Parameter Governance | PRD-06 | Multi-sig → token |
| §9.2 | Fee Structure | PRD-06 | Protocol sustainability |
| §9.3 | Upgrade Path | PRD-06 | Proxy patterns |
| §10.1 | Base Deployment | PRD-06 | Mainnet launch |
| §10.2 | CLI Tools | PRD-06 | `cairn` CLI |
| §10.3 | Security Audit | PRD-06 | Pre-mainnet |

### Coverage Summary

```
PRD-01 (MVP)         → Basic state machine, checkpoints, heartbeat, escrow
PRD-02 (Recovery)    → Failure classification, recovery scoring, delegation
PRD-03 (Intel)       → Knowledge graph, pattern detection, intelligence API
PRD-04 (Ecosystem)   → Fallback pool, reputation, stake/slash, agent SDK
PRD-05 (Arbiter)     → Dispute resolution, arbiter network, rulings
PRD-06 (Integration) → Governance, CLI, security, mainnet deployment
PRD-07 (Optimization)→ Merkle batching, gas efficiency, production scaling
```

**Full Protocol = PRD-01 + PRD-02 + PRD-03 + PRD-04 + PRD-05 + PRD-06 + PRD-07**

Each PRD builds on the previous, with no gaps in the vision coverage.

---

## PRD Coherence & Dependencies

The PRDs form a coherent system where each builds on the previous:

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    PRD DEPENDENCY GRAPH                 │
                    └─────────────────────────────────────────────────────────┘

     PRD-01 ─────────────────┬─────────────────┬─────────────────┐
     (MVP)                   │                 │                 │
       │                     │                 │                 │
       │ contracts           │ state machine   │ checkpoints     │
       │ SDK core            │ heartbeat       │ IPFS            │
       ▼                     ▼                 ▼                 ▼
     PRD-02 ───────────────PRD-03 ───────────PRD-04 ───────────PRD-05
     (Recovery)            (Intel)           (Pool)            (Arbiter)
       │                     │                 │                 │
       │ scoring formula     │ failure records │ reputation      │ DISPUTED state
       │ failure classes     │ knowledge graph │ stake/slash     │ arbitration
       │ routing logic       │ patterns        │ agent SDK       │ rulings
       │                     │                 │                 │
       └──────────────┬──────┴─────────────────┴─────────────────┘
                      │
                      ▼
                  PRD-06
              (Integration)
                    │
                    │ governance, CLI, security, mainnet
                    │
                    ▼
            FULL PROTOCOL
```

### Cross-PRD Data Flows

| From | To | Data Flow |
|------|----|-----------||PRD-01 | PRD-02 | Checkpoint CIDs → Recovery scoring inputs |
| PRD-01 | PRD-03 | Task events → Failure record storage |
| PRD-01 | PRD-07 | Checkpoint storage → Merkle optimization |
| PRD-02 | PRD-03 | Failure classifications → Knowledge graph |
| PRD-02 | PRD-04 | Recovery scores → Fallback selection |
| PRD-03 | PRD-02 | Historical patterns → Score adjustments |
| PRD-03 | PRD-04 | Task-type matching → Pool queries |
| PRD-03 | PRD-07 | Event indexing → Batch verification |
| PRD-04 | PRD-05 | Stake balances → Dispute eligibility |
| PRD-05 | PRD-04 | Rulings → Reputation updates |
| PRD-07 | PRD-06 | Optimized contracts → Production deployment |

### Shared Components

These components span multiple PRDs:

| Component | PRDs | Evolution |
|-----------|------|-----------|
| **CairnClient** | 01 → 02 → 04 → 07 | Basic → scoring methods → pool methods → batched |
| **Task struct** | 01 → 02 → 05 → 07 | 4 states → failure class → DISPUTED → Merkle roots |
| **Checkpoint CID** | 01 → 02 → 03 → 07 | Storage → scoring → intelligence → Merkle batching |
| **Agent identity** | 01 → 04 | EOA → ERC-8004 reputation |
| **Escrow** | 01 → 02 → 05 | Basic → proportional → disputed |
| **Gas efficiency** | 01 → 07 | Per-CID storage → Merkle batching (95% reduction) |

---

## Agent Team Execution

Each PRD folder contains **spawn prompts** for agent team execution. These are focused prompts that can be given to AI coding agents to execute specific phases of the PRD.

### Spawn Prompt Structure

```markdown
# Spawn Prompt: [Team]-[Role]

## CONTEXT
- PRD location, target repo, dependencies

## SCOPE
- Directory structure to create/modify

## YOUR TASKS
- Numbered tasks matching STATUS.md

## SUCCESS CRITERIA
- Verifiable completion criteria

## HANDOFF
- What to update, who to notify
```

### Parallelism

Within each PRD, teams can work in parallel where dependencies allow:
- **PRD-01**: Contract → SDK → Frontend (sequential), Integration (parallel after all)
- **PRD-04**: ERC → Contract → SDK (sequential)
- **PRD-06**: Governance → Integration → Deployment (sequential)

---

## Next Steps

1. **Finalize PRD-01** — Lock MVP scope for hackathon
2. **Build during March 13-23** — Focus on demo-ability
3. **Get feedback March 18** — Incorporate judge/agent advice
4. **Post-hackathon** — Continue with PRD-02+

---

## Production Agent Readiness

The protocol is designed for **production autonomous agents** from day one. While the hackathon MVP uses controlled agents for demo reliability, all protocol interactions (contracts, IPFS, events) work with real autonomous agents.

**Key Resources:**
- `/docs/real-agent-integration.md` — Production agent requirements
- `/docs/integration.md` — Quick start integration guide
- `/docs/observer.md` — Monitoring and observability

**Supported Frameworks:** Olas SDK, LangChain, LangGraph, AutoGen, CrewAI, custom Python

---

*Last updated: March 2026*
