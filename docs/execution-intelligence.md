# Execution Intelligence Layer

> The knowledge graph that accumulates automatically as CAIRN runs — failure patterns, cost distributions, recovery signals.

---

## Table of Contents

1. [What It Is](#what-it-is)
2. [What Gets Written](#what-gets-written)
3. [Pre-Task Intelligence Queries](#pre-task-intelligence-queries)
4. [Fallback Selection Queries](#fallback-selection-queries)
5. [The Bonfires Role](#the-bonfires-role)
6. [Network Effects](#network-effects)

---

## What It Is

The execution intelligence layer is the **secondary output** of CAIRN. It is not the core. It is what accumulates automatically as the recovery protocol runs — without human curation, without a central server, without any agent opting in separately (writing to the intelligence layer is mandatory for escrow settlement).

---

## What Gets Written

### On FAILED — Failure Record

Written to IPFS, CID emitted on-chain:

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

### On RESOLVED — Resolution Record

Written to IPFS, CID emitted on-chain:

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

---

## Pre-Task Intelligence Queries

Before confirming a task (A2), CAIRN queries the intelligence layer by `task_type`:

| Query | What It Returns | How It Helps |
|-------|-----------------|--------------|
| **Known failure patterns** | List of failure types recorded for this task_type, sorted by frequency | Operator sees what has gone wrong before. Agent can pre-configure to avoid. |
| **Cost distribution** | P25, P50, P75, P95 of total cost per execution | Operator can set a realistic `budget_cap`. Prevents under-budgeting. |
| **Recommended agent** | Agents with highest success rate + reputation for this task_type | Starting with the best available agent reduces failure probability. |
| **Known-bad conditions** | Time windows or API conditions correlated with failures | Agent can avoid scheduling during high-risk windows. |
| **Recovery success rate** | % of failures that resolved via recovery for this task_type | Operator understands risk profile before committing. |

### Example Query Response

```json
{
  "task_type": "defi.price_fetch",
  "failure_patterns": [
    {"type": "RATE_LIMIT", "count": 12, "api": "api.coingecko.com"},
    {"type": "HEARTBEAT_MISSED", "count": 3},
    {"type": "CONTEXT_OVERFLOW", "count": 1}
  ],
  "cost_distribution": {
    "p25": "0.0015 ETH",
    "p50": "0.0028 ETH",
    "p75": "0.0041 ETH",
    "p95": "0.0067 ETH"
  },
  "recommended_agent": "erc8004://base/0x1234...5678",
  "success_rate": 0.87,
  "recovery_success_rate": 0.92,
  "known_bad_windows": [
    {"hour_utc": 0, "failure_rate": 0.34},
    {"hour_utc": 12, "failure_rate": 0.28}
  ]
}
```

---

## Fallback Selection Queries

On recovery (A9), CAIRN queries the intelligence layer for the best fallback:

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

### Fallback Selection Criteria

| Priority | Criterion | Weight |
|----------|-----------|--------|
| 1 | Success rate on exact `task_type` | 40% |
| 2 | ERC-8004 reputation score | 30% |
| 3 | Stake deposited | 20% |
| 4 | Current availability | 10% |

---

## The Bonfires Role

Bonfires is the **visualization and query interface** for the intelligence layer. It is:

- **Not** the storage layer (IPFS + The Graph handles storage and indexing)
- **Not** the protocol core (CairnTask.sol handles all state transitions)
- **Load-bearing** in A2 (failure pattern query) and A9 (fallback selection routing)
- **Valuable** as the interface humans use to inspect the health of the agent ecosystem

### BonfiresAdapter

The BonfiresAdapter is a small event listener that watches for `TaskFailed` and `TaskResolved` events on-chain and writes the full record (fetched from IPFS) into a Bonfires data room.

Bonfires then provides:

1. **Queryable knowledge graph API** (used by A2 and A9)
2. **Visual data room** that humans can inspect
3. **"Hyperblog"** of the agent ecosystem's failure and recovery history

The knowledge graph in Bonfires is built entirely by agent activity — no human writes to it. This is the inversion of Bonfires' typical use case (human contributors) and the novel integration angle.

---

## Network Effects

The execution history cannot be forked. A competitor can copy the schema. They cannot copy the accumulated records.

### The Compounding Loop

```
More agents writing records
  → Richer intelligence layer
    → More accurate fallback selection
      → Higher recovery success rate
        → More agents integrating CAIRN
          → More agents writing records
```

### The Forcing Function

The escrow condition is the forcing function that bootstraps this loop without relying on altruism. Agents cannot receive payment without writing the record. The loop starts from day one.

### The Moat

| Aspect | Copyable? | Notes |
|--------|-----------|-------|
| Protocol code | Yes | Open source |
| Schema definitions | Yes | Public |
| Execution history | **No** | Accumulated over time |
| Agent reputation | **No** | Built through attestations |
| Network density | **No** | More agents = more value |

---

## Storage Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CairnTask     │     │      IPFS       │     │   The Graph     │
│   (on-chain)    │────►│   (off-chain)   │◄────│   (indexer)     │
│                 │     │                 │     │                 │
│ • State machine │     │ • Full records  │     │ • Event index   │
│ • CID pointers  │     │ • Checkpoints   │     │ • Fast queries  │
│ • Events        │     │ • Schemas       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                                               │
         │                                               │
         ▼                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Bonfires                                  │
│                                                                  │
│  • Knowledge graph API (for agents)                              │
│  • Visual data room (for humans)                                 │
│  • Pattern detection                                             │
│  • Fallback recommendations                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

*See also: [Concepts](./concepts.md) · [Architecture](./architecture.md) · [Integration](./integration.md)*

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
