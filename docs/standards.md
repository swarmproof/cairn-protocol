# Standards Integration

> How CAIRN integrates with ERC-8183, ERC-8004, ERC-7710, and the Olas Mech Marketplace.

---

## Table of Contents

1. [Integration Philosophy](#integration-philosophy)
2. [ERC-8183: Job Escrow](#erc-8183-job-escrow)
3. [ERC-8004: Agent Identity & Reputation](#erc-8004-agent-identity--reputation)
4. [ERC-7710: Delegation Framework](#erc-7710-delegation-framework)
5. [Olas Mech Marketplace](#olas-mech-marketplace)
6. [Sponsor Integration Map](#sponsor-integration-map)

---

## Integration Philosophy

**Rule: CairnTask.sol is the only new thing built. Everything else is an integration call.**

CAIRN is a *compositor* of existing primitives, not a replacement. This architectural decision means:

- Lower development effort (leverage existing audited code)
- Better interoperability (use standards the ecosystem already knows)
- Clearer value proposition (CAIRN adds failure/recovery, not reinvents escrow)

---

## ERC-8183: Job Escrow

### Role in CAIRN

ERC-8183 handles the job lifecycle and escrow. CAIRN is an **ERC-8183 Hook** that adds failure detection and recovery.

### Integration Points

| CAIRN State | ERC-8183 Integration |
|-------------|----------------------|
| **IDLE → RUNNING** | `createJob()` called, escrow locked |
| **RUNNING** | Job in progress, hooks monitor state |
| **RESOLVED** | `complete()` called, escrow released |
| **DISPUTED** | `claimRefund()` on timeout |

### CairnHook.sol

```solidity
interface ICairnHook {
    function beforeFund(bytes32 jobId, bytes calldata params) external;
    function afterFund(bytes32 jobId, bytes calldata params) external;
    function beforeComplete(bytes32 jobId, bytes calldata params) external;
    function afterComplete(bytes32 jobId, bytes calldata params) external;
    function beforeReject(bytes32 jobId, bytes calldata params) external;
    function afterReject(bytes32 jobId, bytes calldata params) external;
}
```

### Configuration

CairnTask is set as the ERC-8183 job `evaluator`. This allows CAIRN to:

- Validate checkpoint submissions
- Compute escrow splits
- Trigger state transitions based on liveness/budget/deadline

---

## ERC-8004: Agent Identity & Reputation

### Role in CAIRN

ERC-8004 provides agent identity (who is this agent?) and reputation (how well do they perform?).

### Integration Points

| CAIRN Action | ERC-8004 Integration |
|--------------|----------------------|
| **A3: Task init** | Read agent identity from Identity Registry |
| **A9: Fallback selection** | Query reputation scores by task_type |
| **A12: Resolution** | Write positive reputation signal |
| **A13: Dispute** | Write negative reputation signal |

### Agent Registration

Agents declare their CAIRN capabilities in their ERC-8004 identity card:

```json
{
  "cairn_task_types": ["defi.price_fetch", "defi.trade_execute"],
  "cairn_admission_stake": "0.01 ETH"
}
```

### Reputation Signals

On **RESOLVED**:
```python
await reputation_registry.writeAttestation(
    agent_id=completing_agent,
    task_type=task.task_type,
    outcome="SUCCESS",
    context={"checkpoints": checkpoint_count, "cost": total_cost}
)
```

On **DISPUTED**:
```python
await reputation_registry.writeAttestation(
    agent_id=failing_agent,
    task_type=task.task_type,
    outcome="FAILURE",
    context={"failure_class": failure_class, "recovery_score": score}
)
```

### Deployed Addresses (Base Mainnet)

| Registry | Address |
|----------|---------|
| Identity Registry | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Reputation Registry | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |

---

## ERC-7710: Delegation Framework

### Role in CAIRN

ERC-7710 enables caveat-enforced delegation — the operator pre-authorizes CAIRN to sub-delegate permissions to a fallback agent without requiring a new signature at recovery time.

### Integration Points

| CAIRN Action | ERC-7710 Integration |
|--------------|----------------------|
| **A3: Task init** | Operator pre-authorizes CAIRN with scoped caveat |
| **A10: State transfer** | CAIRN sub-delegates to fallback agent |

### The Trust Model

```
Operator
    │
    │ pre-delegate (at task init)
    │ caveat: {allowed_actions, budget_cap, allowed_fallback_pool}
    ▼
  CAIRN
    │
    │ sub-delegate (at recovery, no new signature)
    │ inherited caveat scope
    ▼
Fallback Agent
```

This is critical: **no human is required at recovery time**. The delegation was set up at task initialization with explicit bounds. When failure occurs, CAIRN can immediately assign a fallback without waiting for operator approval.

### Caveat Structure

```typescript
interface CairnDelegationCaveat {
  // What actions the fallback can perform
  allowed_actions: string[];

  // Maximum budget the fallback can spend
  budget_cap: bigint;

  // Pool of agents eligible for fallback
  allowed_fallback_pool: address[];

  // Expiration (same as task deadline)
  expiry: number;
}
```

### Implementation

```python
# At task init (A3)
await erc7710.delegate(
    delegator=operator,
    delegatee=cairn_task_address,
    caveat={
        "allowed_actions": task_spec.allowed_actions,
        "budget_cap": task_spec.budget_cap,
        "allowed_fallback_pool": registered_fallback_agents,
        "expiry": task_spec.deadline
    }
)

# At recovery (A10) — no new signature required
await erc7710.subDelegate(
    original_delegation=delegation_id,
    new_delegatee=fallback_agent_address
)
```

---

## Olas Mech Marketplace

### Role in CAIRN

Olas Mech Marketplace provides the **live pool of fallback agents**. When CAIRN needs to assign a fallback, it queries Olas for available agents that support the task type.

### Integration Points

| CAIRN Action | Olas Integration |
|--------------|------------------|
| **A9: Fallback selection** | Query available agents by task_type |

### Query Flow

```python
async def select_fallback(task_type: str, remaining_budget: int) -> address:
    # 1. Query Olas for available agents
    available_agents = await olas_mech.getAgentsByTaskType(task_type)

    # 2. Filter by CAIRN admission criteria
    eligible_agents = [
        a for a in available_agents
        if a.reputation >= MIN_REPUTATION_THRESHOLD
        and a.stake >= remaining_budget * 0.1
    ]

    # 3. Sort by success rate (from Bonfires)
    success_rates = await bonfires.getSuccessRates(
        agents=eligible_agents,
        task_type=task_type
    )

    # 4. Return top agent
    return sorted(eligible_agents, key=lambda a: success_rates[a])[-1]
```

### Marketplace URL

Live at: `https://olas.network/mech-marketplace`

---

## Sponsor Integration Map

Visual map of how each sponsor integrates at each CAIRN state:

```
CairnTask.sol
│
├── RUNNING
│   ├── ERC-8183 (Virtuals/EF dAI) — job + escrow locked on startTask()
│   └── ERC-7710 (MetaMask) — delegation caveat pre-authorized by operator
│
├── FAILED
│   └── Bonfires — failure record written via BonfiresAdapter on TaskFailed event
│
├── RECOVERING
│   ├── Olas Mech Marketplace (Valory) — fallback agent pool queried
│   ├── Bonfires — success rate signal for fallback selection
│   └── ERC-7710 (MetaMask) — pre-authorized caveat sub-delegated to fallback
│
├── RESOLVED
│   ├── ERC-8183 (Virtuals/EF dAI) — complete() called, escrow released
│   ├── ERC-8004 (EF dAI) — positive reputation signal written
│   └── Bonfires — resolution record written via BonfiresAdapter
│
└── DISPUTED
    ├── ERC-8183 (Virtuals/EF dAI) — escrow held, claimRefund() on timeout
    ├── ERC-8004 (EF dAI) — negative reputation signal written
    └── Bonfires — dispute record written, exposed as arbitration evidence
```

### Why This Integration Works

Every sponsor integration is **load-bearing**:

| Remove | CAIRN Loses |
|--------|-------------|
| ERC-8183 | No escrow mechanism |
| ERC-8004 | No identity or reputation |
| ERC-7710 | No trustless permission transfer |
| Olas | No fallback agent pool |
| Bonfires | No intelligence layer |

The integrations are not decorative — they are structural.

---

*See also: [Concepts](./concepts.md) · [Architecture](./architecture.md) · [Integration](./integration.md) · [Contracts](./contracts.md)*

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
