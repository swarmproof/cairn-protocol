# CAIRN Observer

> Failure cost visibility layer — see the problem before solving it.

---

## Overview

CAIRN Observer is a lightweight monitoring component that surfaces failure costs to agent operators. It operates independently of the full CAIRN recovery protocol, providing visibility into agent failures without requiring protocol integration.

**Purpose:** Operators cannot adopt recovery infrastructure if they do not perceive the problem. Observer quantifies the cost of agent failures, creating awareness that drives protocol adoption.

**Relationship to CAIRN Protocol:**
- Observer is the **visibility layer** (shows the pain)
- CAIRN Protocol is the **recovery layer** (solves the pain)
- Observer can operate standalone or as a gateway to full CAIRN integration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       CAIRN Observer                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │   Indexer    │───►│   Analyzer   │───►│  Dashboard   │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│          │                   │                    │              │
│          ▼                   ▼                    ▼              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│   │ Transaction  │    │ Failure Cost │    │   Operator   │     │
│   │   Stream     │    │  Calculator  │    │   Reports    │     │
│   └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
         │                                           │
         ▼                                           ▼
┌─────────────────┐                       ┌─────────────────┐
│  Base / Olas    │                       │    Operator     │
│  Agent Txns     │                       │    Interface    │
└─────────────────┘                       └─────────────────┘
```

---

## Components

### 1. Indexer

Monitors on-chain agent activity and identifies failure patterns.

**Data Sources:**
- ERC-8183 escrow contract events
- ERC-8004 agent registry transactions
- Olas Mech Marketplace service calls
- Known agent contract addresses

**Indexed Events:**

| Event Type | Source | Indicates |
|------------|--------|-----------|
| `EscrowLocked` | ERC-8183 | Task initiated |
| `EscrowReleased` | ERC-8183 | Task completed successfully |
| `EscrowDisputed` | ERC-8183 | Task failed, funds contested |
| `EscrowExpired` | ERC-8183 | Task timed out, no resolution |
| `ServiceRequest` | Olas Mech | Agent job requested |
| `ServiceDelivered` | Olas Mech | Agent job completed |
| `ServiceFailed` | Olas Mech | Agent job failed |

### 2. Analyzer

Processes indexed data to identify failure patterns and calculate costs.

**Failure Detection Heuristics:**

| Pattern | Detection Method | Confidence |
|---------|------------------|------------|
| **Stuck Escrow** | `EscrowLocked` with no `Released`/`Disputed` after N blocks | HIGH |
| **Repeated Retries** | Multiple `ServiceRequest` for same task type within time window | MEDIUM |
| **Timeout** | `EscrowExpired` event | HIGH |
| **Partial Completion** | `ServiceDelivered` followed by new `ServiceRequest` for same task | MEDIUM |
| **Silent Failure** | `ServiceRequest` with no subsequent `Delivered` or `Failed` | MEDIUM |

**Cost Calculation:**

```
failure_cost = escrow_locked_value
             + gas_spent_on_failed_attempts
             + opportunity_cost(lock_duration)
             + restart_cost(if_restarted)
```

Where:
- `escrow_locked_value`: Funds inaccessible during failure state
- `gas_spent_on_failed_attempts`: Sum of gas for failed transactions
- `opportunity_cost`: `lock_duration_hours × operator_hourly_rate` (configurable)
- `restart_cost`: Gas for duplicate work if task was restarted

### 3. Dashboard

Presents failure cost data to operators.

**Views:**

| View | Content |
|------|---------|
| **Summary** | Total failure cost (24h / 7d / 30d), failure count, avg resolution time |
| **By Agent** | Failure breakdown per agent address |
| **By Task Type** | Failure breakdown per task category |
| **Timeline** | Chronological failure events with cost attribution |
| **Comparison** | Estimated savings with CAIRN recovery enabled |

**Key Metrics:**

| Metric | Calculation | Display |
|--------|-------------|---------|
| **Total Failure Cost** | Sum of all `failure_cost` in period | `$X,XXX lost` |
| **Avg Time to Resolution** | Mean time from failure to resolution | `X.X hours` |
| **Recovery Rate** | `successful_recoveries / total_failures` | `X%` |
| **Escrow Lock Duration** | Mean time funds held in failed state | `X.X hours` |
| **Projected CAIRN Savings** | `failure_cost × estimated_recovery_rate × checkpoint_value_preserved` | `$X,XXX recoverable` |

---

## Data Schema

### FailureEvent

```json
{
  "event_id": "0x...",
  "timestamp": 1742000000,
  "block_number": 18492031,
  "failure_type": "STUCK_ESCROW | TIMEOUT | RETRY_LOOP | SILENT",
  "agent_address": "0x...",
  "operator_address": "0x...",
  "task_type": "defi.price_fetch",
  "escrow_value_wei": "50000000000000000",
  "gas_spent_wei": "2500000000000000",
  "lock_duration_blocks": 1800,
  "resolution": "MANUAL_RESTART | ABANDONED | DISPUTED | RECOVERED",
  "resolution_timestamp": 1742010000,
  "calculated_cost": {
    "escrow_locked": "0.05 ETH",
    "gas_wasted": "0.0025 ETH",
    "opportunity": "0.02 ETH",
    "total": "0.0725 ETH"
  }
}
```

### OperatorReport

```json
{
  "operator_address": "0x...",
  "report_period": {
    "start": 1740000000,
    "end": 1742000000
  },
  "summary": {
    "total_tasks": 150,
    "successful_tasks": 120,
    "failed_tasks": 30,
    "failure_rate": 0.20,
    "total_failure_cost_eth": 2.175,
    "avg_resolution_time_hours": 4.2
  },
  "breakdown_by_type": {
    "STUCK_ESCROW": { "count": 12, "cost_eth": 0.87 },
    "TIMEOUT": { "count": 10, "cost_eth": 0.75 },
    "RETRY_LOOP": { "count": 5, "cost_eth": 0.35 },
    "SILENT": { "count": 3, "cost_eth": 0.205 }
  },
  "cairn_projection": {
    "estimated_recovery_rate": 0.70,
    "estimated_checkpoint_preservation": 0.60,
    "projected_savings_eth": 0.914
  }
}
```

---

## Integration Points

### Standalone Mode

Observer operates independently, requiring no changes to existing agent infrastructure.

**Requirements:**
- RPC access to Base (or target chain)
- List of agent contract addresses to monitor
- Optional: Operator address mapping for attribution

**Deployment:**
```bash
cairn-observer start \
  --rpc https://base.publicnode.com \
  --agents 0x...,0x...,0x... \
  --port 8080
```

### CAIRN Protocol Integration

When used alongside the full CAIRN Protocol, Observer provides:

1. **Pre-integration baseline:** Quantify failure costs before CAIRN adoption
2. **Post-integration comparison:** Show improvement after CAIRN enabled
3. **Continuous monitoring:** Ongoing visibility into ecosystem health

**Data Flow:**

```
Observer (visibility) ──► Operator sees costs ──► Adopts CAIRN Protocol
                                                         │
                                                         ▼
                                             CAIRN Protocol (recovery)
                                                         │
                                                         ▼
                                              Observer shows improvement
```

---

## API

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/summary` | GET | Aggregate failure metrics |
| `/api/v1/failures` | GET | List failure events (paginated) |
| `/api/v1/failures/{id}` | GET | Single failure event detail |
| `/api/v1/operators/{address}/report` | GET | Operator-specific report |
| `/api/v1/agents/{address}/failures` | GET | Agent-specific failures |
| `/api/v1/projection` | GET | CAIRN adoption savings projection |

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | timestamp | Start of time range |
| `to` | timestamp | End of time range |
| `type` | string | Filter by failure type |
| `min_cost` | number | Minimum cost threshold (wei) |
| `limit` | number | Results per page |
| `offset` | number | Pagination offset |

### Example Response

```bash
GET /api/v1/summary?from=1740000000&to=1742000000
```

```json
{
  "period": {
    "from": 1740000000,
    "to": 1742000000,
    "duration_hours": 555.56
  },
  "totals": {
    "tasks_monitored": 1250,
    "failures_detected": 287,
    "failure_rate": 0.2296,
    "total_cost_eth": 21.48,
    "total_cost_usd": 69812.00
  },
  "by_type": {
    "STUCK_ESCROW": { "count": 115, "pct": 0.40, "cost_eth": 8.59 },
    "TIMEOUT": { "count": 98, "pct": 0.34, "cost_eth": 7.33 },
    "RETRY_LOOP": { "count": 45, "pct": 0.16, "cost_eth": 3.37 },
    "SILENT": { "count": 29, "pct": 0.10, "cost_eth": 2.19 }
  },
  "cairn_projection": {
    "recoverable_failures": 201,
    "projected_recovery_rate": 0.70,
    "projected_savings_eth": 9.03,
    "projected_savings_usd": 29347.50
  }
}
```

---

## Implementation Phases

### Phase 1: MVP

**Scope:**
- Monitor 3-5 known agent contracts on Base
- Detect 2 failure types: stuck escrow, timeout
- Basic dashboard with cost summary
- Manual agent address configuration

**Deliverables:**
- Indexer service (Node.js / Python)
- PostgreSQL schema for failure events
- Simple web dashboard (React)
- REST API for data access

### Phase 2: Expanded Detection

**Scope:**
- All 4 failure types (stuck, timeout, retry, silent)
- Automatic agent discovery via ERC-8004 registry
- Operator-specific reports and alerts
- Email/webhook notifications

### Phase 3: CAIRN Integration

**Scope:**
- Pre/post CAIRN comparison views
- Real-time savings tracking
- Integration with CAIRN Protocol dashboard
- Ecosystem-wide metrics aggregation

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| **Data accuracy** | Multiple confirmation blocks before indexing; cross-reference multiple sources |
| **Operator privacy** | Aggregated views by default; operator-specific data requires authentication |
| **Cost manipulation** | Gas prices from on-chain data only; no external oracles for cost calculation |
| **Indexer availability** | Stateless design; can rebuild from chain data; no single point of failure |

---

## Configuration

```yaml
# observer.config.yaml
indexer:
  rpc_url: "https://base.publicnode.com"
  start_block: 18000000  # or "latest"
  confirmation_blocks: 12
  poll_interval_ms: 2000

agents:
  # Manually specified agent contracts
  addresses:
    - "0x..."
    - "0x..."
  # Or discover via registry
  discovery:
    enabled: true
    registry: "0x..."  # ERC-8004 registry address

analyzer:
  opportunity_cost_rate_usd_per_hour: 50
  stuck_escrow_threshold_blocks: 1800  # ~1 hour on Base
  retry_window_blocks: 300  # ~10 minutes

dashboard:
  port: 8080
  auth:
    enabled: false  # MVP: no auth
```

---

*See also: [Architecture](./architecture.md) · [Integration](./integration.md) · [Execution Intelligence](./execution-intelligence.md)*

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
