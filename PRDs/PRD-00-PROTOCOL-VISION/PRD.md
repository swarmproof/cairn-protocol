# PRD-00: CAIRN Protocol Vision

> The Complete Specification — North Star Reference

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-00 |
| **Title** | CAIRN Protocol Full Vision |
| **Status** | Reference Document |
| **Author** | CAIRN Team |
| **Created** | March 2026 |
| **Type** | Vision / Reference |

---

## 1. Executive Summary

### 1.1 One-Liner

**CAIRN** is a standardized agent failure and recovery protocol that turns every agent failure into a lesson every other agent inherits.

### 1.2 The Problem

Agent workflows fail **80% of the time**. At 85% per-action success, a 10-step task completes only ~20% of the time. Today:

- **No standard failure handling** — Each team writes bespoke, incompatible recovery logic
- **Failures disappear** — No shared record, ecosystem cannot learn
- **Money bleeds away** — Locked escrow, wasted gas, opportunity cost

### 1.3 The Solution

CAIRN provides:

1. **Standardized Recovery** — Deterministic failure → classification → fallback → settlement
2. **Execution Intelligence** — Shared, queryable record of every failure and resolution
3. **Economic Alignment** — Escrow forces participation; agents paid by verified work

### 1.4 Tagline

> "Agents learn together."

---

## 2. Goals & Non-Goals

### 2.1 Goals

| Priority | Goal |
|----------|------|
| P0 | Enable automatic recovery when agents fail mid-task |
| P0 | Preserve work through checkpoints (resume, not restart) |
| P0 | Fair settlement based on verified contribution |
| P1 | Build ecosystem intelligence from failure records |
| P1 | Permissionless enforcement (no trusted keeper) |
| P2 | Support any agent framework (framework-agnostic) |
| P2 | Minimize integration burden (<5 min for basic setup) |

### 2.2 Non-Goals

| Non-Goal | Reason |
|----------|--------|
| Replace agent frameworks | CAIRN wraps, not replaces |
| AI-powered failure classification | Deterministic rules, not ML |
| Centralized failure database | IPFS + The Graph, not our server |
| Mandatory for all agents | Opt-in via escrow |

---

## 3. Repository Structure

### 3.1 Full Codebase Layout

```
cairn-protocol/
│
├── contracts/                      # Solidity smart contracts (Foundry)
│   ├── src/
│   │   ├── CairnCore.sol           # Main contract: state machine, checkpoints, settlement
│   │   ├── CairnHook.sol           # ERC-8183 lifecycle hook implementation
│   │   ├── RecoveryRouter.sol      # Failure classification & recovery scoring
│   │   ├── FallbackPool.sol        # Fallback agent registration & selection
│   │   ├── ArbiterRegistry.sol     # Dispute resolution & ruling mechanics
│   │   ├── CairnGovernance.sol     # Parameter management & upgrades
│   │   ├── interfaces/
│   │   │   ├── ICairnCore.sol
│   │   │   ├── ICairnHook.sol
│   │   │   ├── IRecoveryRouter.sol
│   │   │   ├── IFallbackPool.sol
│   │   │   ├── IArbiterRegistry.sol
│   │   │   ├── IERC8183.sol        # Job escrow standard
│   │   │   ├── IERC8004.sol        # Agent identity standard
│   │   │   └── IERC7710.sol        # Scoped delegation standard
│   │   ├── libraries/
│   │   │   ├── FailureClassifier.sol
│   │   │   ├── RecoveryScorer.sol
│   │   │   └── CheckpointValidator.sol
│   │   └── adapters/
│   │       └── OlasMechAdapter.sol # Olas Mech Marketplace integration
│   ├── test/
│   │   ├── CairnCore.t.sol
│   │   ├── RecoveryRouter.t.sol
│   │   ├── FallbackPool.t.sol
│   │   ├── ArbiterRegistry.t.sol
│   │   ├── integration/
│   │   │   ├── FullProtocol.t.sol
│   │   │   └── E2ERecovery.t.sol
│   │   └── fuzz/
│   │       └── CairnCoreFuzz.t.sol
│   ├── script/
│   │   ├── Deploy.s.sol
│   │   ├── DeployTestnet.s.sol
│   │   └── UpgradeProxy.s.sol
│   ├── foundry.toml
│   └── remappings.txt
│
├── backend/                        # Backend API & services
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry
│   │   ├── config.py               # Environment configuration
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── intelligence.py     # /intelligence/* endpoints
│   │   │   ├── tasks.py            # /tasks/* endpoints
│   │   │   ├── agents.py           # /agents/* endpoints
│   │   │   ├── fallbacks.py        # /fallbacks/* endpoints
│   │   │   └── health.py           # /health endpoint
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── intelligence.py     # Pre-task intelligence queries
│   │   │   ├── fallback_ranker.py  # Fallback selection algorithm
│   │   │   ├── record_writer.py    # IPFS record writing
│   │   │   └── graph_client.py     # The Graph queries
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py
│   │   │   ├── agent.py
│   │   │   ├── failure.py
│   │   │   └── resolution.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py             # API key / JWT validation
│   │       └── rate_limit.py       # Rate limiting
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── event_listener.py       # On-chain event listener
│   │   ├── record_processor.py     # Process & store failure records
│   │   └── pattern_detector.py     # Detect failure patterns
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_intelligence.py
│   │   ├── test_fallback_ranker.py
│   │   └── test_integration.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── sdk/                            # Python SDK for CAIRN integration
│   ├── cairn/
│   │   ├── __init__.py
│   │   ├── client.py               # CairnClient main class
│   │   ├── agent.py                # CairnAgent wrapper
│   │   ├── pool.py                 # FallbackPool interactions
│   │   ├── arbiter.py              # ArbiterRegistry interactions
│   │   ├── intelligence.py         # Intelligence API client
│   │   ├── types.py                # Type definitions
│   │   ├── exceptions.py           # Custom exceptions
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── ipfs.py             # IPFS client wrapper
│   │       ├── checkpoint.py       # Checkpoint helpers
│   │       └── heartbeat.py        # Heartbeat thread
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_client.py
│   │   ├── test_agent.py
│   │   └── test_integration.py
│   ├── examples/
│   │   ├── simple_agent.py
│   │   ├── fallback_registration.py
│   │   └── arbiter_agent.py
│   ├── pyproject.toml
│   └── README.md
│
├── cli/                            # Command-line interface
│   ├── cairn_cli/
│   │   ├── __init__.py
│   │   ├── main.py                 # Click/Typer CLI entry
│   │   ├── commands/
│   │   │   ├── __init__.py
│   │   │   ├── intel.py            # cairn intel <task_type>
│   │   │   ├── submit.py           # cairn submit --type --agent --escrow
│   │   │   ├── status.py           # cairn status <task_id>
│   │   │   ├── fallback.py         # cairn fallback register|list|withdraw
│   │   │   ├── arbiter.py          # cairn arbiter register|rule|appeal
│   │   │   └── config.py           # cairn config set|get
│   │   └── utils.py
│   ├── tests/
│   │   └── test_commands.py
│   ├── pyproject.toml
│   └── README.md
│
├── indexer/                        # The Graph subgraph
│   ├── subgraph.yaml
│   ├── schema.graphql
│   ├── src/
│   │   ├── cairn-core.ts           # CairnCore event handlers
│   │   ├── fallback-pool.ts        # FallbackPool event handlers
│   │   ├── arbiter-registry.ts     # ArbiterRegistry event handlers
│   │   └── utils.ts
│   ├── tests/
│   │   └── cairn-core.test.ts
│   ├── package.json
│   └── tsconfig.json
│
├── frontend/                       # Dashboard (Optional - for demo)
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Dashboard home
│   │   │   ├── tasks/
│   │   │   │   └── [id]/page.tsx   # Task detail view
│   │   │   ├── agents/
│   │   │   │   └── page.tsx        # Agent list
│   │   │   └── intelligence/
│   │   │       └── page.tsx        # Intelligence explorer
│   │   ├── components/
│   │   │   ├── TaskCard.tsx
│   │   │   ├── StateTimeline.tsx
│   │   │   ├── CheckpointList.tsx
│   │   │   └── FallbackRanking.tsx
│   │   └── lib/
│   │       ├── cairn-client.ts
│   │       └── graph-client.ts
│   ├── package.json
│   ├── next.config.js
│   └── tailwind.config.js
│
├── infra/                          # Infrastructure & deployment
│   ├── docker/
│   │   ├── docker-compose.yml      # Local development
│   │   ├── docker-compose.prod.yml # Production
│   │   └── Dockerfile.api
│   ├── kubernetes/
│   │   ├── api-deployment.yaml
│   │   ├── worker-deployment.yaml
│   │   └── ingress.yaml
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── scripts/
│       ├── deploy-testnet.sh
│       ├── deploy-mainnet.sh
│       └── verify-contracts.sh
│
├── docs/                           # Documentation
│   ├── architecture.md
│   ├── integration-guide.md
│   ├── api-reference.md
│   ├── sdk-reference.md
│   ├── operator-guide.md
│   ├── fallback-guide.md
│   ├── arbiter-guide.md
│   └── images/
│       ├── state-machine.png
│       ├── architecture.png
│       └── recovery-flow.png
│
├── PRDs/                           # Product Requirements Documents
│   ├── README.md
│   ├── PRD-00-PROTOCOL-VISION/
│   ├── PRD-01-MVP-HACKATHON/
│   ├── PRD-02-CORE-RECOVERY/
│   ├── PRD-03-EXECUTION-INTELLIGENCE/
│   ├── PRD-04-FALLBACK-ECOSYSTEM/
│   ├── PRD-05-ARBITER-NETWORK/
│   └── PRD-06-FULL-INTEGRATION/
│
├── .github/
│   └── workflows/
│       ├── contracts.yml           # Foundry test + coverage
│       ├── backend.yml             # Python tests
│       ├── sdk.yml                 # SDK tests + publish
│       └── deploy.yml              # Deployment pipeline
│
├── CAIRN_PROTOCOL_SPEC.md
├── ERC-CAIRN.md
├── WHITEPAPER_V2.md
├── README.md
├── LICENSE
└── SECURITY.md
```

### 3.2 Component Mapping

| Component | Location | Language | Purpose |
|-----------|----------|----------|---------|
| Core Contracts | `contracts/src/` | Solidity | On-chain state machine, escrow, enforcement |
| Backend API | `backend/api/` | Python (FastAPI) | Intelligence queries, off-chain coordination |
| Event Workers | `backend/workers/` | Python | Event processing, pattern detection |
| Python SDK | `sdk/cairn/` | Python | Agent integration, checkpoint management |
| CLI Tool | `cli/cairn_cli/` | Python (Click) | Developer & operator commands |
| Subgraph | `indexer/` | TypeScript | On-chain event indexing |
| Dashboard | `frontend/` | TypeScript (Next.js) | Operator UI, task monitoring |
| Infrastructure | `infra/` | Docker/K8s/Terraform | Deployment & orchestration |

---

## 4. System Architecture

### 4.1 Four-Layer Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: EXECUTION INTELLIGENCE                                              │
│ ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│ │    IPFS     │───►│  The Graph  │───►│ Backend API │───►│     SDK     │    │
│ │  (records)  │    │  (indexer)  │    │  (queries)  │    │  (client)   │    │
│ └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│ LAYER 3: ETHEREUM STANDARDS                                                  │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐              │
│ │    ERC-8183      │ │    ERC-8004      │ │    ERC-7710      │              │
│ │  (Job Escrow)    │ │ (Agent Identity) │ │ (Delegation)     │              │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘              │
├─────────────────────────────────────────────────────────────────────────────┤
│ LAYER 2: CAIRN PROTOCOL (ON-CHAIN)                                           │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │  CairnCore   │ │ Recovery     │ │ Fallback     │ │  Arbiter     │         │
│ │  (state)     │ │ Router       │ │ Pool         │ │  Registry    │         │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
│                           │                                                  │
│                    ┌──────────────┐                                         │
│                    │  Governance  │                                         │
│                    └──────────────┘                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ LAYER 1: ACTORS                                                              │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │   Operator   │ │ Primary Agent│ │ Fallback Pool│ │   Arbiters   │         │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Deployment Architecture (Production)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION DEPLOYMENT                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         EXTERNAL SERVICES                            │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐        │   │
│  │  │   Base    │  │   IPFS    │  │ The Graph │  │   Olas    │        │   │
│  │  │ Mainnet   │  │  Gateway  │  │  Hosted   │  │   Mech    │        │   │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘        │   │
│  └────────┼──────────────┼──────────────┼──────────────┼───────────────┘   │
│           │              │              │              │                    │
│           ▼              ▼              ▼              ▼                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CAIRN INFRASTRUCTURE                         │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                        KUBERNETES CLUSTER                      │  │   │
│  │  │                                                                │  │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │  │   │
│  │  │  │   API Pod   │  │ Worker Pod  │  │  Redis Pod  │            │  │   │
│  │  │  │  (FastAPI)  │  │  (Celery)   │  │  (Cache)    │            │  │   │
│  │  │  │  replicas:3 │  │  replicas:2 │  │  replicas:1 │            │  │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘            │  │   │
│  │  │         │                │                │                    │  │   │
│  │  │         └────────────────┼────────────────┘                    │  │   │
│  │  │                          │                                     │  │   │
│  │  │                   ┌──────┴──────┐                              │  │   │
│  │  │                   │  PostgreSQL │                              │  │   │
│  │  │                   │  (metadata) │                              │  │   │
│  │  │                   └─────────────┘                              │  │   │
│  │  │                                                                │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                         MONITORING                             │  │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │  │   │
│  │  │  │ Prometheus  │  │   Grafana   │  │   Sentry    │            │  │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘            │  │   │
│  │  └────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Data Flow

```
                                  CAIRN DATA FLOW

┌─────────────┐                                              ┌─────────────┐
│   Operator  │                                              │    Agent    │
└──────┬──────┘                                              └──────┬──────┘
       │                                                            │
       │ 1. Submit Task                                            │
       ▼                                                            │
┌─────────────────┐     2. Query Intelligence     ┌─────────────────┐
│  Backend API    │◄──────────────────────────────│    The Graph    │
│  /intelligence  │                               │    (indexer)    │
└────────┬────────┘                               └────────┬────────┘
         │                                                  │
         │ 3. Return patterns, costs, recommended agent    │
         ▼                                                  │
┌─────────────────┐                                        │
│   CairnCore     │◄───────────────────────────────────────┘
│   (on-chain)    │         (events indexed)
└────────┬────────┘
         │
         │ 4. Task RUNNING
         ▼
┌─────────────────┐     5. Checkpoint CID      ┌─────────────────┐
│      Agent      │ ─────────────────────────► │      IPFS       │
│   (executing)   │                            │    (storage)    │
└────────┬────────┘                            └─────────────────┘
         │
         │ 6. heartbeat() / commitCheckpoint()
         ▼
┌─────────────────┐
│   CairnCore     │
│   (validate)    │
└────────┬────────┘
         │
    [FAILURE]
         │
         ▼
┌─────────────────┐     7. Write Failure Record  ┌─────────────────┐
│ RecoveryRouter  │ ─────────────────────────────►│      IPFS       │
│ (classify/score)│                              └─────────────────┘
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
 ≥0.3       <0.3
    │         │
    ▼         ▼
RECOVERING  DISPUTED
    │         │
    ▼         │
┌─────────────┐   │
│FallbackPool │   │
│  (select)   │   │
└──────┬──────┘   │
       │          │
       ▼          ▼
┌─────────────┐  ┌─────────────┐
│  Fallback   │  │   Arbiter   │
│   Agent     │  │   Registry  │
└──────┬──────┘  └──────┬──────┘
       │                │
       └───────┬────────┘
               │
               ▼
        ┌─────────────┐
        │  RESOLVED   │
        │  (settle)   │
        └──────┬──────┘
               │
               ▼
┌─────────────────┐    8. Write Resolution Record  ┌─────────────────┐
│   CairnCore     │ ──────────────────────────────►│      IPFS       │
│   (escrow)      │                                └────────┬────────┘
└─────────────────┘                                         │
                                                            │ 9. Index
                                                            ▼
                                                   ┌─────────────────┐
                                                   │    The Graph    │
                                                   └─────────────────┘
```

---

## 5. Smart Contracts

### 5.1 Contract Summary

| Contract | LOC (est) | Purpose | Gas (key ops) |
|----------|-----------|---------|---------------|
| CairnCore.sol | ~400 | State machine, checkpoints, heartbeat, settlement | submitTask: 200k, checkpoint: 60k |
| CairnHook.sol | ~80 | ERC-8183 lifecycle hook interface | N/A (callback) |
| RecoveryRouter.sol | ~150 | Failure classification, recovery scoring | classify: 30k |
| FallbackPool.sol | ~200 | Agent registration, selection, slashing | register: 80k, select: 50k |
| ArbiterRegistry.sol | ~150 | Dispute registration, ruling, appeals | rule: 100k |
| CairnGovernance.sol | ~100 | Parameter management, timelock, upgrades | updateParam: 25k |

**Total: ~1,080 LOC** (manageable audit scope)

### 5.2 CairnCore Interface

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ICairnCore {
    // ========== ENUMS ==========
    enum State { IDLE, RUNNING, FAILED, RECOVERING, DISPUTED, RESOLVED }
    enum FailureClass { LIVENESS, RESOURCE, LOGIC }
    enum FailureType {
        HEARTBEAT_MISS, PROCESS_CRASH, NETWORK_TIMEOUT,      // LIVENESS
        BUDGET_EXCEEDED, DEADLINE_EXCEEDED, RATE_LIMIT,      // RESOURCE
        STEP_LOOP, WRONG_TOOL, HALLUCINATION, SPEC_MISMATCH  // LOGIC
    }

    // ========== STRUCTS ==========
    struct TaskSpec {
        string taskType;           // e.g., "defi.price_fetch"
        bytes32 specHash;          // Hash of full spec (stored off-chain)
        uint256 budgetCap;         // Max cost in wei
        uint256 deadline;          // Block number
        uint256 heartbeatInterval; // Seconds
        uint8 expectedCheckpoints; // Expected subtask count
    }

    struct Task {
        bytes32 id;
        State state;
        address operator;
        address primaryAgent;
        address fallbackAgent;
        uint256 escrow;
        uint256 costAccrued;
        uint256 startBlock;
        uint256 deadline;
        uint256 lastHeartbeat;
        uint256 heartbeatInterval;
        bytes32[] checkpointCIDs;
        uint8 primaryCheckpoints;
        uint8 fallbackCheckpoints;
    }

    struct Checkpoint {
        bytes32 cid;           // IPFS CID
        uint256 cost;          // Cost of this subtask
        uint256 blockNumber;
        bool validated;
    }

    // ========== EVENTS ==========
    event TaskSubmitted(bytes32 indexed taskId, address indexed operator, string taskType);
    event TaskConfirmed(bytes32 indexed taskId, address indexed agent, uint256 escrow);
    event CheckpointCommitted(bytes32 indexed taskId, uint8 index, bytes32 cid, uint256 cost);
    event HeartbeatReceived(bytes32 indexed taskId, uint256 blockNumber);
    event TaskFailed(bytes32 indexed taskId, FailureClass class, FailureType failureType, uint256 recoveryScore);
    event FallbackAssigned(bytes32 indexed taskId, address indexed fallback, uint8 resumeFromIndex);
    event TaskResolved(bytes32 indexed taskId, uint256 primaryShare, uint256 fallbackShare, uint256 protocolFee);
    event TaskDisputed(bytes32 indexed taskId, bytes32 failureRecordCID);

    // ========== CORE FUNCTIONS ==========
    function submitTask(TaskSpec calldata spec) external returns (bytes32 taskId);
    function confirmTask(bytes32 taskId, address agent) external payable;
    function commitCheckpoint(bytes32 taskId, uint8 index, bytes32 cid, uint256 cost) external;
    function heartbeat(bytes32 taskId) external;

    // ========== ENFORCEMENT (PUBLIC) ==========
    function checkLiveness(bytes32 taskId) external;
    function checkBudget(bytes32 taskId) external;
    function checkDeadline(bytes32 taskId) external;

    // ========== RECOVERY ==========
    function assignFallback(bytes32 taskId, address fallbackAgent) external;
    function resolveTask(bytes32 taskId) external;

    // ========== DISPUTE ==========
    function escalateToDispute(bytes32 taskId, bytes32 failureRecordCID) external;

    // ========== VIEWS ==========
    function getTask(bytes32 taskId) external view returns (Task memory);
    function getCheckpoints(bytes32 taskId) external view returns (Checkpoint[] memory);
    function getRecoveryScore(bytes32 taskId) external view returns (uint256);
}
```

### 5.3 RecoveryRouter Interface

```solidity
interface IRecoveryRouter {
    struct FailureRecord {
        bytes32 taskId;
        FailureClass class;
        FailureType failureType;
        uint256 recoveryScore;
        uint256 budgetRemainingPct;    // 0-100
        uint256 deadlineRemainingPct;  // 0-100
        uint8 checkpointCountAtFailure;
        bytes32 failureRecordCID;      // IPFS CID
    }

    function classifyFailure(bytes32 taskId, FailureType failureType) external returns (FailureClass);
    function computeRecoveryScore(bytes32 taskId) external view returns (uint256);
    function shouldRecover(bytes32 taskId) external view returns (bool);
    function writeFailureRecord(bytes32 taskId) external returns (bytes32 cid);
}
```

### 5.4 FallbackPool Interface

```solidity
interface IFallbackPool {
    struct FallbackAgent {
        bool registered;
        string[] taskTypes;
        uint256 stake;
        uint256 successCount;
        uint256 failureCount;
        uint256 lastActive;
    }

    event AgentRegistered(address indexed agent, string[] taskTypes, uint256 stake);
    event AgentSelected(bytes32 indexed taskId, address indexed agent);
    event AgentSlashed(address indexed agent, uint256 amount, string reason);

    function register(string[] calldata taskTypes) external payable;
    function depositStake() external payable;
    function withdrawStake(uint256 amount) external;
    function selectFallback(bytes32 taskId, string calldata taskType, uint256 escrowValue) external returns (address);
    function slashAgent(address agent, uint256 amount, string calldata reason) external;
    function getAgent(address agent) external view returns (FallbackAgent memory);
    function getEligibleAgents(string calldata taskType, uint256 minStake) external view returns (address[] memory);
}
```

### 5.5 ArbiterRegistry Interface

```solidity
interface IArbiterRegistry {
    enum DisputeOutcome { REFUND_OPERATOR, PAY_AGENT, SPLIT }

    struct Arbiter {
        bool registered;
        uint256 stake;
        string[] expertiseDomains;
        uint256 rulingCount;
        uint256 overturnedCount;
        uint256 earnings;
    }

    struct Ruling {
        DisputeOutcome outcome;
        uint256 agentShare;    // Only for SPLIT (0-100)
        string rationale;      // IPFS CID
    }

    event ArbiterRegistered(address indexed arbiter, string[] domains, uint256 stake);
    event DisputeRuled(bytes32 indexed taskId, address indexed arbiter, DisputeOutcome outcome);
    event RulingAppealed(bytes32 indexed taskId, address indexed appellant);
    event RulingOverturned(bytes32 indexed taskId, address indexed originalArbiter, uint256 slashAmount);

    function registerArbiter(string[] calldata domains) external payable;
    function rule(bytes32 taskId, Ruling calldata ruling) external;
    function appeal(bytes32 taskId) external payable;
    function overturnRuling(bytes32 taskId, Ruling calldata newRuling) external; // onlyGovernance
    function getArbiter(address arbiter) external view returns (Arbiter memory);
}
```

---

## 6. Backend API

### 6.1 API Overview

| Base URL | Description |
|----------|-------------|
| `https://api.cairn.network/v1` | Production API |
| `https://api-testnet.cairn.network/v1` | Testnet API |

### 6.2 Endpoints

#### Intelligence Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/intelligence/{task_type}` | Get pre-task intelligence |
| GET | `/intelligence/{task_type}/patterns` | Get failure patterns |
| GET | `/intelligence/{task_type}/costs` | Get cost distribution |
| GET | `/intelligence/{task_type}/agents` | Get recommended agents |

#### Task Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks/{task_id}` | Get task details |
| GET | `/tasks/{task_id}/checkpoints` | Get task checkpoints |
| GET | `/tasks/{task_id}/timeline` | Get state transitions |
| GET | `/tasks` | List tasks (with filters) |

#### Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents/{address}` | Get agent details |
| GET | `/agents/{address}/history` | Get agent task history |
| GET | `/agents/{address}/reputation` | Get reputation breakdown |

#### Fallback Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fallbacks` | List fallback agents |
| GET | `/fallbacks/rank/{task_type}` | Get ranked fallbacks for task type |

### 6.3 Response Schemas

#### TaskIntelligence

```json
{
  "task_type": "defi.price_fetch",
  "success_rate": 0.82,
  "avg_cost_eth": "0.0035",
  "cost_percentiles": {
    "p25": "0.0020",
    "p50": "0.0032",
    "p75": "0.0045",
    "p95": "0.0078"
  },
  "avg_duration_blocks": 120,
  "failure_patterns": [
    {
      "type": "RATE_LIMIT",
      "frequency": 0.35,
      "common_apis": ["api.coingecko.com"],
      "mitigation": "Use multiple data sources"
    }
  ],
  "recommended_agents": [
    {
      "address": "0x...",
      "reputation": 85,
      "success_rate": 0.94,
      "avg_cost": "0.0028"
    }
  ],
  "known_risks": [
    {
      "description": "High failure rate 00:00-02:00 UTC",
      "severity": "medium"
    }
  ],
  "sample_size": 1247,
  "last_updated": "2026-03-17T12:00:00Z"
}
```

#### Task

```json
{
  "id": "0x...",
  "state": "RUNNING",
  "task_type": "defi.price_fetch",
  "operator": "0x...",
  "primary_agent": "0x...",
  "fallback_agent": null,
  "escrow_eth": "0.05",
  "cost_accrued_eth": "0.012",
  "start_block": 18492000,
  "deadline": 18493000,
  "last_heartbeat": 18492850,
  "checkpoints": [
    {
      "index": 0,
      "cid": "Qm...",
      "cost_eth": "0.004",
      "validated": true,
      "block": 18492200
    }
  ],
  "created_at": "2026-03-17T10:00:00Z",
  "updated_at": "2026-03-17T10:30:00Z"
}
```

---

## 7. Python SDK

### 7.1 Installation

```bash
pip install cairn-sdk
```

> **Production Agent Requirements:** Real autonomous agents require additional infrastructure beyond the SDK: wallet with gas funding, IPFS write access, background heartbeat capability, and event listening for task assignments. See `/docs/real-agent-integration.md` for complete production requirements, framework compatibility (Olas, LangChain, AutoGen), and deployment patterns.

### 7.2 CairnClient

```python
from cairn import CairnClient, TaskSpec

# Initialize
client = CairnClient(
    rpc_url="https://base-mainnet.g.alchemy.com/v2/...",
    api_url="https://api.cairn.network/v1",
    private_key="0x...",  # Optional: for signing transactions
)

# Query intelligence
intel = await client.get_intelligence("defi.price_fetch")
print(f"Success rate: {intel.success_rate}")
print(f"Recommended agent: {intel.recommended_agents[0].address}")

# Submit task
task = await client.submit_task(
    TaskSpec(
        task_type="defi.price_fetch",
        spec={"pairs": ["ETH/USDC"], "sources": ["uniswap"]},
        budget_cap=0.05,      # ETH
        deadline_blocks=1000,
        heartbeat_interval=60,
        expected_checkpoints=5,
    ),
    agent=intel.recommended_agents[0].address,
    escrow=0.05,  # ETH
)

# Monitor
result = await client.wait_for_resolution(task.id, timeout=3600)
print(f"Final state: {result.state}")
print(f"Primary paid: {result.primary_share} ETH")
```

### 7.3 CairnAgent Wrapper

```python
from cairn import CairnAgent, Checkpoint

class MyPriceFetchAgent(CairnAgent):
    """Example agent with automatic CAIRN integration."""

    task_types = ["defi.price_fetch"]

    async def execute_subtask(self, index: int, input_data: dict) -> Checkpoint:
        """Execute a single subtask and return checkpoint."""
        # Your agent logic here
        pair = input_data.get("pair", "ETH/USDC")
        price = await self.fetch_price(pair)

        return Checkpoint(
            index=index,
            output={"pair": pair, "price": price},
            cost=0.001,  # Estimated cost
        )

    async def fetch_price(self, pair: str) -> float:
        # Implementation
        pass

# Usage
agent = MyPriceFetchAgent(
    contract_address="0x...",
    private_key="0x...",
    heartbeat_interval=60,
)

# Agent automatically handles:
# - Heartbeat emission
# - Checkpoint commits to IPFS + on-chain
# - Failure detection and reporting
await agent.run()
```

### 7.4 FallbackPool Client

```python
from cairn import FallbackPool

pool = FallbackPool(client)

# Register as fallback
await pool.register(
    task_types=["defi.price_fetch", "defi.trade_execute"],
    stake=1.0,  # ETH
)

# Query eligible fallbacks
fallbacks = await pool.get_eligible("defi.price_fetch", escrow=0.1)
for f in fallbacks:
    print(f"{f.address}: reputation={f.reputation}, stake={f.stake}")

# Withdraw stake (if no active recoveries)
await pool.withdraw_stake(0.5)
```

### 7.5 Arbiter Client

```python
from cairn import ArbiterRegistry, Ruling, DisputeOutcome

registry = ArbiterRegistry(client)

# Register as arbiter
await registry.register(
    domains=["defi"],
    stake=2.0,  # ETH
)

# Monitor disputes
async for dispute in registry.watch_disputes(domains=["defi"]):
    evidence = await registry.get_evidence(dispute.task_id)

    # Analyze and rule
    ruling = Ruling(
        outcome=DisputeOutcome.PAY_AGENT,
        agent_share=70,  # 70% to agent
        rationale="External API failure, not agent fault",
    )
    await registry.submit_ruling(dispute.task_id, ruling)
```

---

## 8. CLI Tool

### 8.1 Installation

```bash
pip install cairn-cli
```

### 8.2 Commands

```bash
# Configuration
cairn config set rpc-url https://base-mainnet.g.alchemy.com/v2/...
cairn config set api-url https://api.cairn.network/v1
cairn config set private-key 0x...  # Stored encrypted

# Intelligence queries
cairn intel defi.price_fetch
cairn intel defi.price_fetch --format json
cairn intel defi.price_fetch --patterns
cairn intel defi.price_fetch --costs

# Task operations
cairn submit --type defi.price_fetch --agent 0x... --escrow 0.05 --spec spec.json
cairn status 0x<task_id>
cairn status 0x<task_id> --watch
cairn checkpoints 0x<task_id>

# Fallback operations
cairn fallback register --types "defi.price_fetch,defi.trade_execute" --stake 1.0
cairn fallback list
cairn fallback withdraw 0.5

# Arbiter operations
cairn arbiter register --domains "defi" --stake 2.0
cairn arbiter disputes --domain defi
cairn arbiter rule 0x<task_id> --outcome PAY_AGENT --share 70 --rationale "..."
cairn arbiter appeal 0x<task_id> --stake 0.1

# Agent operations
cairn agent info 0x...
cairn agent history 0x...
```

### 8.3 Example Output

```bash
$ cairn intel defi.price_fetch

╔══════════════════════════════════════════════════════════════════╗
║                    CAIRN Intelligence Report                      ║
║                      defi.price_fetch                             ║
╠══════════════════════════════════════════════════════════════════╣
║ Success Rate:     82.3%                                           ║
║ Sample Size:      1,247 tasks                                     ║
║ Avg Cost:         0.0035 ETH                                      ║
║ Avg Duration:     120 blocks (~4 min)                             ║
╠══════════════════════════════════════════════════════════════════╣
║ TOP FAILURE PATTERNS                                              ║
║ ┌────────────────┬───────────┬──────────────────────────────────┐║
║ │ Type           │ Frequency │ Common APIs                      │║
║ ├────────────────┼───────────┼──────────────────────────────────┤║
║ │ RATE_LIMIT     │ 35%       │ api.coingecko.com               │║
║ │ NETWORK_TIMEOUT│ 22%       │ api.binance.com                 │║
║ │ SPEC_MISMATCH  │ 8%        │ —                                │║
║ └────────────────┴───────────┴──────────────────────────────────┘║
╠══════════════════════════════════════════════════════════════════╣
║ RECOMMENDED AGENTS                                                ║
║ 1. 0x1234...abcd  Rep: 92  Success: 96%  Avg: 0.0028 ETH        ║
║ 2. 0x5678...efgh  Rep: 87  Success: 91%  Avg: 0.0032 ETH        ║
║ 3. 0x9abc...ijkl  Rep: 81  Success: 88%  Avg: 0.0030 ETH        ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 9. State Machine

### 9.1 States

| State | Description | Terminal |
|-------|-------------|----------|
| `IDLE` | Task submitted, awaiting confirmation | No |
| `RUNNING` | Agent executing, checkpointing, heartbeating | No |
| `FAILED` | Failure detected, pending classification | No |
| `RECOVERING` | Fallback agent assigned, resuming work | No |
| `DISPUTED` | Low recoverability, arbiter deciding | No |
| `RESOLVED` | Task complete, escrow settled | Yes |

### 9.2 Transition Diagram

```
IDLE
  │ [operator confirms, escrow locked]
  ▼
RUNNING ─────────────────────────────┐
  │                                   │
  │ [success]                         │ [failure detected]
  ▼                                   ▼
RESOLVED ◄───────────────────────── FAILED
  ▲                                   │
  │                                   ├── [score ≥ 0.3] ──► RECOVERING
  │                                   │                         │
  │                                   │                         ├─[success]──► RESOLVED
  │                                   │                         │
  │                                   │                         └─[failure]──► DISPUTED
  │                                   │
  │                                   └── [score < 0.3] ──► DISPUTED
  │                                                             │
  │                                                             ├─[arbiter rules]──► RESOLVED
  │                                                             │
  └─────────────────────────────────────────[timeout 7d]────────┘
                                                 (auto-refund)
```

### 9.3 Transition Rules

| From | To | Trigger | Condition |
|------|----|---------|-----------|
| IDLE | RUNNING | `confirmTask()` | Escrow deposited |
| RUNNING | RESOLVED | `resolveTask()` | All checkpoints complete |
| RUNNING | FAILED | `checkLiveness()` | Heartbeat missed |
| RUNNING | FAILED | `checkBudget()` | Budget exceeded |
| RUNNING | FAILED | `checkDeadline()` | Deadline passed |
| FAILED | RECOVERING | `assignFallback()` | Recovery score ≥ 0.3 |
| FAILED | DISPUTED | `escalateToDispute()` | Recovery score < 0.3 |
| RECOVERING | RESOLVED | `resolveTask()` | Fallback completes |
| RECOVERING | DISPUTED | `escalateToDispute()` | Fallback fails |
| DISPUTED | RESOLVED | `rule()` | Arbiter rules |
| DISPUTED | RESOLVED | timeout | 7 days, auto-refund |

**All `check*` functions are public.** No trusted keeper required.

---

## 10. Failure Taxonomy

### 10.1 Three Classes (By Recoverability)

| Class | Weight | Examples | Action |
|-------|--------|----------|--------|
| **LIVENESS** | 0.9 | Heartbeat miss, process crash, network partition | Assign fallback |
| **RESOURCE** | 0.5 | Budget cap, deadline exceeded, rate limit | Attempt recovery with remaining |
| **LOGIC** | 0.1 | Step loop, wrong tool, hallucination, spec mismatch | Route to dispute |

### 10.2 Failure Types

| Type | Class | Description |
|------|-------|-------------|
| `HEARTBEAT_MISS` | LIVENESS | No heartbeat within interval |
| `PROCESS_CRASH` | LIVENESS | Agent reported process termination |
| `NETWORK_TIMEOUT` | LIVENESS | Network partition detected |
| `BUDGET_EXCEEDED` | RESOURCE | Cost accrued > budget cap |
| `DEADLINE_EXCEEDED` | RESOURCE | Current block > deadline |
| `RATE_LIMIT` | RESOURCE | External API rate limited |
| `CONTEXT_OVERFLOW` | RESOURCE | LLM context exhausted |
| `STEP_LOOP` | LOGIC | Agent stuck in loop |
| `WRONG_TOOL` | LOGIC | Tool call doesn't match task |
| `HALLUCINATION` | LOGIC | Output doesn't match reality |
| `SPEC_MISMATCH` | LOGIC | Output schema doesn't match spec |

### 10.3 Classification Rules

```python
def classify_failure(event: FailureEvent) -> FailureClass:
    if event.type in [HEARTBEAT_MISS, PROCESS_CRASH, NETWORK_TIMEOUT]:
        return LIVENESS  # weight: 0.9

    if event.type in [BUDGET_EXCEEDED, DEADLINE_EXCEEDED, RATE_LIMIT, CONTEXT_OVERFLOW]:
        return RESOURCE  # weight: 0.5

    if event.type in [STEP_LOOP, WRONG_TOOL, HALLUCINATION, SPEC_MISMATCH]:
        return LOGIC  # weight: 0.1

    return LOGIC  # conservative default
```

**No AI. Pure rules.**

---

## 11. Recovery Score

### 11.1 Formula

```
recovery_score = (failure_class_weight × 0.5)
               + (budget_remaining_pct × 0.3)
               + (deadline_remaining_pct × 0.2)
```

### 11.2 Variables

| Variable | Calculation |
|----------|-------------|
| `failure_class_weight` | LIVENESS=0.9, RESOURCE=0.5, LOGIC=0.1 |
| `budget_remaining_pct` | `(budget_cap - cost_accrued) / budget_cap` |
| `deadline_remaining_pct` | `(deadline - current_block) / (deadline - start_block)` |

### 11.3 Routing Thresholds

| Score Range | Route To | Rationale |
|-------------|----------|-----------|
| ≥ 0.6 | RECOVERING | High confidence in recovery |
| 0.3 – 0.6 | RECOVERING (reduced scope) | Attempt with constraints |
| < 0.3 | DISPUTED | Arbiter needed |

### 11.4 Examples

| Scenario | Class | Budget | Deadline | Score | Route |
|----------|-------|--------|----------|-------|-------|
| Early heartbeat miss | LIVENESS (0.9) | 80% | 90% | 0.69 | RECOVERING |
| Late rate limit | RESOURCE (0.5) | 30% | 20% | 0.38 | RECOVERING (reduced) |
| Logic failure near deadline | LOGIC (0.1) | 50% | 10% | 0.22 | DISPUTED |

---

## 12. Checkpoint Protocol

### 12.1 Why Checkpoints

Without checkpoints, fallback restarts from zero — wasting original agent's work and budget.

### 12.2 Checkpoint Schema

```json
{
  "task_id": "0x...",
  "index": 2,
  "subtask": {
    "description": "Fetch ETH/USDC price from Uniswap",
    "expected_output_schema": {
      "type": "object",
      "properties": {
        "pair": { "type": "string" },
        "price": { "type": "number" },
        "source": { "type": "string" }
      }
    }
  },
  "output": {
    "pair": "ETH/USDC",
    "price": 3245.67,
    "source": "uniswap_v3"
  },
  "cost_wei": "4000000000000000",
  "agent": "0x...",
  "block_number": 18492500,
  "timestamp": 1742000500
}
```

### 12.3 Write Flow

```
1. Agent completes subtask N
2. Agent writes output to IPFS → receives CID
3. Agent calls commitCheckpoint(taskId, N, CID, cost)
4. CAIRN validates CID against declared schema for subtask N
5. Valid: CID stored, cost recorded
   Invalid: rejected, agent retries
```

### 12.4 Read Flow (on RECOVERING)

```
1. Fallback receives: checkpoint CID list, next subtask index, remaining budget/deadline
2. Fallback reads last CID from IPFS → retrieves subtask output
3. Fallback begins next subtask using previous output as input
4. No restart. No waste.
```

### 12.5 Incentive Alignment

Agents paid proportionally to verified checkpoint count → financial interest in frequent, honest checkpointing.

---

## 13. Escrow Settlement

### 13.1 Settlement Formula

On RESOLVED:

```
total_checkpoints = primary_checkpoints + fallback_checkpoints
protocol_fee_amount = escrow × protocol_fee_percent

original_share = (primary_checkpoints / total_checkpoints) × (escrow - protocol_fee_amount)
fallback_share = (fallback_checkpoints / total_checkpoints) × (escrow - protocol_fee_amount)
```

### 13.2 Examples

| Scenario | Primary CPs | Fallback CPs | Original | Fallback | Protocol (0.5%) |
|----------|-------------|--------------|----------|----------|-----------------|
| Solo completion | 5 | 0 | 99.5% | 0% | 0.5% |
| Recovery (3+2) | 3 | 2 | 59.7% | 39.8% | 0.5% |
| Late failure (4+1) | 4 | 1 | 79.6% | 19.9% | 0.5% |

---

## 14. Liveness Signal

### 14.1 Heartbeat Bounds

```
min(interval) = 30 seconds (~15 Base blocks)
max(interval) = task_deadline / 4
default = min(task_deadline / 10, 300 seconds)
```

### 14.2 Enforcement

```solidity
function checkLiveness(bytes32 taskId) external {
    Task storage task = tasks[taskId];
    require(task.state == State.RUNNING, "Not running");
    require(block.timestamp > task.lastHeartbeat + task.heartbeatInterval, "Not stale");

    _transitionTo(taskId, State.FAILED, FailureType.HEARTBEAT_MISS);
    emit TaskFailed(taskId, FailureClass.LIVENESS, FailureType.HEARTBEAT_MISS, _computeRecoveryScore(taskId));
}
```

**Anyone can call.** No trusted keeper.

---

## 15. Fallback Pool

### 15.1 Admission Gates

**Gate 1 — Reputation Threshold:**
```
Agent must have min reputation score in ERC-8004 ReputationRegistry
Default: score ≥ 50/100
```

**Gate 2 — Stake Deposit:**
```
min_stake = max_eligible_escrow × 0.1 (10%)
```

### 15.2 Matching Rules

```
1. Exact match on domain.operation + highest reputation + available stake
2. Domain match only + highest reputation (if no exact match)
3. No match → DISPUTED immediately
```

### 15.3 Selection Algorithm

```python
def select_fallback(task_type: str, escrow_value: int) -> Address:
    eligible = get_eligible_agents(task_type, min_stake=escrow_value * 0.1)

    if not eligible:
        return None  # Route to DISPUTED

    # Rank by weighted score
    ranked = sorted(eligible, key=lambda a: (
        a.success_rate * 0.4 +
        a.reputation * 0.3 +
        (a.stake / escrow_value) * 0.2 +
        a.availability * 0.1
    ), reverse=True)

    return ranked[0].address
```

### 15.4 Slashing

| Scenario | Slash Amount |
|----------|--------------|
| Fallback accepts but completes 0 checkpoints | 100% of stake |
| Fallback completes some checkpoints then fails | 50% of stake |
| Fallback times out without attempting | 25% of stake |

---

## 16. Arbiter Design

### 16.1 Role

Arbiters are **themselves agent services**. Registered with stake. Read public records. Call `rule(taskId, outcome)`. Earn fees.

### 16.2 Economics

```
min_arbiter_stake = max_ruleable_dispute_value × 0.20 (20%)
arbiter_fee = dispute_escrow_value × 0.03 (3%)
appeal_window = 48 hours
dispute_timeout = 7 days
```

### 16.3 Ruling Outcomes

| Outcome | Description | Escrow Distribution |
|---------|-------------|---------------------|
| REFUND_OPERATOR | Agent at fault | 100% to operator |
| PAY_AGENT | External failure, agent not at fault | Checkpoint-proportional to agent(s) |
| SPLIT | Shared fault | Custom split (arbiter decides %) |

### 16.4 Evidence Package

```json
{
  "dispute_id": "0x...",
  "task_spec": {
    "task_type": "defi.trade_execute",
    "description": "Execute swap on Uniswap",
    "expected_output_schema": { "..." }
  },
  "failure_record": {
    "cid": "Qm...",
    "failure_class": "LOGIC",
    "failure_type": "SPEC_MISMATCH",
    "recovery_score": 0.17
  },
  "checkpoints": [
    { "index": 0, "cid": "Qm...", "validated": true },
    { "index": 1, "cid": "Qm...", "validated": true },
    { "index": 2, "cid": "Qm...", "validated": false, "error": "Output schema mismatch" }
  ],
  "agent_history": {
    "reputation": 65,
    "success_rate": 0.78,
    "similar_failures": 2
  },
  "operator_notes": "Agent output was garbage at step 3"
}
```

### 16.5 Sybil Resistance

Bad ruling → lose 50% of stake. Collusion becomes prohibitively expensive at scale:

```
Collusion cost = stake_required × number_of_disputes × 0.5 (if caught)
```

### 16.6 Timeout

7 days (in Base blocks). No ruling → auto-refund operator.

---

## 17. Task Types

### 17.1 Hierarchical Taxonomy

```
domain.operation

Examples:
- defi.price_fetch
- defi.trade_execute
- defi.liquidity_provide
- data.report_generate
- data.sentiment_analyze
- governance.vote_delegate
- governance.proposal_create
- compute.model_inference
- compute.data_transform
- storage.file_manage
- storage.ipfs_pin
```

### 17.2 Registry

Task types declared in agent's ERC-8004 identity card. Reputation tracked per task type.

```solidity
// ERC-8004 Identity
{
  "agent": "0x...",
  "task_types": ["defi.price_fetch", "defi.trade_execute"],
  "reputation": {
    "defi.price_fetch": 85,
    "defi.trade_execute": 72
  }
}
```

---

## 18. Execution Intelligence

### 18.1 Failure Record Schema

```json
{
  "record_type": "failure",
  "task_id": "0x...",
  "agent_id": "erc8004://base/0x...",
  "task_type": "defi.price_fetch",
  "failure_class": "RESOURCE",
  "failure_type": "RATE_LIMIT",
  "checkpoint_count_at_failure": 3,
  "cost_at_failure_wei": "2300000000000000",
  "budget_remaining_pct": 42,
  "deadline_remaining_pct": 31,
  "recovery_score": 71,
  "block_number": 18492031,
  "timestamp": 1742000000,
  "context": {
    "api_endpoint": "api.coingecko.com",
    "error_code": "429",
    "error_message": "Too many requests"
  }
}
```

### 18.2 Resolution Record Schema

```json
{
  "record_type": "resolution",
  "task_id": "0x...",
  "states_traversed": ["IDLE", "RUNNING", "FAILED", "RECOVERING", "RESOLVED"],
  "original_agent_id": "erc8004://base/0x...",
  "fallback_agent_id": "erc8004://base/0x...",
  "task_type": "defi.price_fetch",
  "total_cost_wei": "4100000000000000",
  "total_duration_blocks": 847,
  "original_checkpoint_count": 3,
  "fallback_checkpoint_count": 2,
  "escrow_split": {
    "original_agent_wei": "2400000000000000",
    "fallback_agent_wei": "1600000000000000",
    "protocol_fee_wei": "20000000000000"
  },
  "failure_record_cid": "Qm...",
  "resolution_cid": "Qm...",
  "block_number": 18493012,
  "timestamp": 1742001700
}
```

### 18.3 Query Capabilities

**Pre-Task:**
- Known failure patterns (sorted by frequency)
- Cost distribution (P25, P50, P75, P95)
- Recommended agent (highest success + reputation)
- Known-bad conditions (time windows, APIs)

**Fallback Selection:**
- Success rate on task_type (40% weight)
- ERC-8004 reputation (30% weight)
- Stake deposited (20% weight)
- Current availability (10% weight)

---

## 19. ERC Integrations

### 19.1 ERC-8183 (Job Escrow)

| Feature | CAIRN Usage |
|---------|-------------|
| Task spec submission | `submitTask()` creates ERC-8183 job |
| Escrow locking | `confirmTask()` locks funds |
| Lifecycle hooks | CairnHook implements `onJobCreated`, `onJobCompleted` |
| Escrow release | `resolveTask()` triggers settlement |

### 19.2 ERC-8004 (Agent Identity)

| Feature | CAIRN Usage |
|---------|-------------|
| Agent registration | Agents register identity before participating |
| Task type declaration | Agents declare supported task types |
| Reputation tracking | Success/failure updates reputation per task type |
| Attestations | CAIRN writes resolution attestations |

### 19.3 ERC-7710 (Scoped Delegation)

| Feature | CAIRN Usage |
|---------|-------------|
| Operator → CAIRN | Operator pre-authorizes CAIRN to manage task |
| CAIRN → Fallback | CAIRN sub-delegates to fallback agent |
| Caveat scoping | Delegation limited to specific task ID |
| Revocation | On task resolution, delegations revoked |

### 19.4 Olas Mech Marketplace

| Feature | CAIRN Usage |
|---------|-------------|
| Agent discovery | Query available mechs for fallback pool |
| Stake integration | Mech stake counts toward CAIRN requirements |
| Reputation bridging | Olas reputation maps to ERC-8004 |

---

## 20. Security Constraints

### 20.1 Access Control

| Function | Caller | Validation |
|----------|--------|------------|
| `submitTask` | Anyone | Valid spec |
| `confirmTask` | Operator only | `msg.value >= escrow` |
| `commitCheckpoint` | Assigned agent only | Valid CID, correct index |
| `heartbeat` | Assigned agent only | Task is RUNNING |
| `checkLiveness/Budget/Deadline` | Anyone | Violation condition met |
| `assignFallback` | Protocol only | Score ≥ 0.3 |
| `rule` | Registered arbiter | Valid dispute, domain match |
| `updateParameter` | Governance (timelock) | Within range |

### 20.2 Rate Limiting (API)

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/intelligence/*` | 100 req | per minute |
| `/tasks/*` | 60 req | per minute |
| `/agents/*` | 60 req | per minute |
| `/fallbacks/*` | 30 req | per minute |

### 20.3 Input Validation

| Input | Validation |
|-------|------------|
| Task spec | Schema validation, max size 10KB |
| Checkpoint CID | Valid IPFS CID format, content exists |
| Heartbeat interval | Within bounds (30s - deadline/4) |
| Stake amount | Above minimum threshold |
| Ruling rationale | Valid IPFS CID |

### 20.4 Attack Vectors & Mitigations

| Vector | Mitigation |
|--------|------------|
| Checkpoint manipulation | Schema validation, slashing |
| Heartbeat spam | Min interval enforcement |
| Fallback griefing | Stake requirement, slashing |
| Arbiter collusion | High stake, appeals, governance override |
| Flash loan governance | Timelock (48h) |
| Escrow reentrancy | ReentrancyGuard, CEI pattern |
| Front-running | Commit-reveal for high-value disputes (future) |

---

## 21. Performance Constraints

### 21.1 On-Chain

| Operation | Gas Target | Actual (est) |
|-----------|------------|--------------|
| `submitTask` | < 200,000 | ~180,000 |
| `confirmTask` | < 100,000 | ~85,000 |
| `commitCheckpoint` | < 60,000 | ~55,000 |
| `heartbeat` | < 30,000 | ~25,000 |
| `resolveTask` | < 150,000 | ~140,000 |
| `rule` | < 100,000 | ~90,000 |

### 21.2 API Latency

| Endpoint | P50 Target | P95 Target |
|----------|------------|------------|
| `/intelligence/{task_type}` | < 100ms | < 500ms |
| `/tasks/{task_id}` | < 50ms | < 200ms |
| `/fallbacks/rank/{task_type}` | < 200ms | < 800ms |

### 21.3 Throughput

| Metric | Target |
|--------|--------|
| Tasks/day | 10,000+ |
| Checkpoints/second | 100+ |
| API requests/second | 500+ |

---

## 22. Observability

### 22.1 Metrics (Prometheus)

```
# Protocol health
cairn_tasks_total{state="RESOLVED"}
cairn_tasks_total{state="DISPUTED"}
cairn_recovery_success_rate
cairn_recovery_duration_seconds{quantile="0.5"}
cairn_recovery_duration_seconds{quantile="0.95"}

# Pool health
cairn_fallback_pool_size
cairn_fallback_pool_utilization
cairn_arbiter_count

# API health
cairn_api_requests_total{endpoint="/intelligence", status="200"}
cairn_api_latency_seconds{endpoint="/intelligence", quantile="0.95"}

# Economic
cairn_escrow_locked_eth
cairn_protocol_fees_eth
cairn_slashing_total_eth
```

### 22.2 Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| Pipeline stall | Zero tasks processed in 30min | Critical |
| High dispute rate | > 20% tasks disputed in 1h | Critical |
| API latency spike | P95 > 2s for 5min | Warning |
| Fallback pool depleted | < 3 eligible agents | Warning |
| Recovery success drop | < 80% in 1h | Warning |

### 22.3 Logging

```python
# Structured logging format
{
  "timestamp": "2026-03-17T12:00:00Z",
  "level": "INFO",
  "service": "cairn-api",
  "event": "task_submitted",
  "task_id": "0x...",
  "task_type": "defi.price_fetch",
  "operator": "0x...",
  "escrow_eth": "0.05"
}
```

---

## 23. Governance

### 23.1 Phases

| Phase | Control | Timing |
|-------|---------|--------|
| 1 | Single admin key | Launch |
| 2 | 3-of-5 multi-sig + 48h timelock | Month 1 |
| 3 | Token governance | Future |

### 23.2 Configurable Parameters

| Parameter | Default | Range | Governance Level |
|-----------|---------|-------|------------------|
| Protocol fee | 0.5% | 0-5% | Multi-sig |
| Fallback min reputation | 50 | 0-100 | Multi-sig |
| Fallback min stake % | 10% | 1-50% | Multi-sig |
| Arbiter min stake % | 20% | 5-50% | Multi-sig |
| Arbiter fee | 3% | 1-10% | Multi-sig |
| Dispute timeout | 7 days | 1-30 days | Multi-sig |
| Appeal window | 48 hours | 24-72 hours | Multi-sig |
| Recovery threshold | 0.3 | 0.1-0.9 | Multi-sig |
| Heartbeat min interval | 30s | 10-300s | Admin |

### 23.3 Upgrade Path

**Proxy Pattern:** UUPS (Universal Upgradeable Proxy Standard)

**Upgrade Process:**
1. Deploy new implementation
2. Governance proposes upgrade
3. 48-hour timelock
4. Execution

---

## 24. Testing Strategy

### 24.1 Test Categories

| Category | Coverage Target | Tools |
|----------|-----------------|-------|
| Contract unit tests | > 95% | Foundry |
| Contract integration tests | > 80% | Foundry |
| Contract fuzz tests | All external functions | Foundry |
| Contract invariant tests | Key state invariants | Foundry |
| API unit tests | > 90% | pytest |
| API integration tests | > 80% | pytest |
| SDK tests | > 90% | pytest |
| E2E tests | Critical paths | pytest + Foundry |

### 24.2 Key Invariants

```solidity
// Total escrowed = sum of all active task escrows
invariant totalEscrowedMatchesTasks();

// Task state transitions are valid (no skipping states)
invariant validStateTransitions();

// Checkpoints are monotonically increasing per task
invariant checkpointsMonotonic();

// Settlement never exceeds escrow
invariant settlementNeverExceedsEscrow();

// Slashing never exceeds stake
invariant slashingNeverExceedsStake();
```

### 24.3 E2E Scenarios

| Scenario | Steps | Expected |
|----------|-------|----------|
| Happy path | Submit → 5 checkpoints → settle | Primary paid 99.5% |
| Recovery path | Submit → 3 checkpoints → fail → fallback → 2 checkpoints → settle | Split 60/40 |
| Dispute path | Submit → logic fail → arbiter rules REFUND | Operator refunded |
| Timeout path | Submit → fail → DISPUTED → 7 days → auto-refund | Operator refunded |

---

## 25. Success Metrics

### 25.1 Protocol Health

| Metric | Target |
|--------|--------|
| Recovery success rate (LIVENESS) | > 90% |
| Recovery success rate (RESOURCE) | > 70% |
| Median recovery time | < 30 min |
| Fallback pool utilization | > 20% |
| Dispute rate | < 10% |
| Arbiter ruling time (median) | < 24 hours |

### 25.2 Ecosystem Growth (Year 1)

| Metric | Target |
|--------|--------|
| Integrated agents | 100+ |
| Tasks processed | 10,000+ |
| Recorded failures | 5,000+ |
| Active fallback agents | 20+ |
| Registered arbiters | 5+ |
| Escrow volume (cumulative) | 100+ ETH |

---

## 26. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fallback pool insufficient | Medium | High | Partner with Olas, bootstrap incentives |
| Checkpoint manipulation | Low | High | Schema validation, slashing |
| Arbiter collusion | Low | Medium | High stake requirements, timeout fallback |
| Adoption friction | Medium | Medium | <5 min integration, SDK/wrapper |
| Gas price spikes | Medium | Low | Optimize contracts, batch operations |
| IPFS availability | Low | Medium | Multiple pinning services, fallback |
| The Graph downtime | Low | Medium | Local caching, fallback queries |

---

## 27. Appendix

### 27.1 Glossary

| Term | Definition |
|------|------------|
| **Agent** | Autonomous software that executes tasks |
| **Checkpoint** | Verified subtask output stored on IPFS, referenced on-chain |
| **Escrow** | Funds locked until task resolution |
| **Fallback** | Agent that takes over a failed task |
| **Heartbeat** | Periodic liveness signal from executing agent |
| **Operator** | Entity that submits tasks and pays escrow |
| **Recovery Score** | 0-1 score determining if task should attempt recovery |
| **Settlement** | Distribution of escrow based on verified work |

### 27.2 Related Documents

- `/WHITEPAPER_V2.md` — Protocol specification, philosophy, economics, simulation results
- `/CAIRN_PROTOCOL_SPEC.md` — Technical specification
- `/ERC-CAIRN.md` — EIP format
- `/docs/` — Detailed component docs
- `/docs/real-agent-integration.md` — **Production agent requirements** (wallet, gas, IPFS, framework compatibility)

### 27.3 Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | March 2026 | Initial draft |
| 0.2 | March 2026 | Added repository structure, backend API, SDK specs |

---

*This is the North Star. All other PRDs are milestones toward this vision.*
