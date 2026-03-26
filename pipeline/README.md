# CAIRN Pipeline - Bonfires Integration

> **Knowledge Graph Data Pipeline for Execution Intelligence**

This pipeline listens for CAIRN Protocol contract events on Base Sepolia, creates structured failure/resolution records, pins them to IPFS, and indexes them in Bonfires knowledge graph for pattern detection and intelligence queries.

## Overview

The pipeline implements **PRD-03: Execution Intelligence Layer** which transforms every task failure and resolution into queryable knowledge that future agents can learn from.

### Data Flow

```
CairnCore Contract (Base Sepolia)
    ↓ (TaskFailed, TaskResolved events)
EventListener
    ↓ (event data)
BonfiresAdapter
    ├─→ Create FailureRecord/ResolutionRecord (Pydantic)
    ├─→ Pin to IPFS (Pinata)
    └─→ Index in Bonfires (knowledge graph)
         ↓
PatternDetector
    ├─→ Time-based patterns
    ├─→ Task type failure rates
    ├─→ Agent performance metrics
    └─→ Cost anomalies
```

## Components

### 1. **config.py** - Configuration Management
Loads environment variables for Bonfires API, RPC endpoints, and IPFS.

```python
from pipeline.config import PipelineConfig

config = PipelineConfig.from_env()
config.validate()
```

**Required Environment Variables:**
- `BONFIRES_API_KEY` - Bonfires API authentication key
- `CAIRN_CONTRACT_ADDRESS` - Deployed CairnCore contract address
- `PINATA_JWT` - Pinata JWT for IPFS pinning
- `RPC_URL` - Base Sepolia RPC endpoint (optional, defaults to public RPC)

### 2. **records.py** - Data Schemas
Pydantic models for type-safe failure and resolution records.

**FailureRecord Schema:**
```python
{
  "record_type": "failure",
  "version": "1.0",
  "task_id": "0x...",
  "agent_id": "erc8004://base/0x...",
  "task_type": "defi.price_fetch",
  "failure_class": "RESOURCE",
  "failure_type": "RATE_LIMIT",
  "failure_details": {"http_status": 429},
  "checkpoint_count_at_failure": 3,
  "total_checkpoints_expected": 5,
  "cost_at_failure": "0.0023",
  "recovery_score": 0.71,
  "block_number": 18492031,
  "timestamp": 1742000000
}
```

**ResolutionRecord Schema:**
```python
{
  "record_type": "resolution",
  "version": "1.0",
  "task_id": "0x...",
  "states_traversed": ["RUNNING", "FAILED", "RECOVERING", "RESOLVED"],
  "recovery_attempted": true,
  "recovery_successful": true,
  "original_agent": {...},
  "fallback_agent": {...},
  "total_cost": "0.0041",
  "total_duration_blocks": 847,
  "block_number": 18493012,
  "timestamp": 1742001700
}
```

### 3. **bonfires.py** - Bonfires Client
HTTP client for Bonfires knowledge graph API with retry logic.

**Methods:**
- `write_record(record_type, data, cid, tags)` - Write record to Bonfires
- `query_records(record_type, task_type, agent_id)` - Query records
- `get_agent_history(agent_id)` - Get agent execution history
- `get_task_type_stats(task_type)` - Get task type statistics
- `health_check()` - Check API health

### 4. **adapter.py** - BonfiresAdapter
Event handler that processes on-chain events and writes records.

**Event Handlers:**
- `on_task_failed(event)` - Creates FailureRecord, pins to IPFS, indexes in Bonfires
- `on_task_resolved(event)` - Creates ResolutionRecord with payout distribution
- `on_pattern_detected(pattern)` - Logs detected patterns

### 5. **patterns.py** - PatternDetector
Analyzes records to detect failure patterns and anomalies.

**Pattern Types:**
- **TIME_BASED** - Peak failure hours (e.g., "14:00-16:00 UTC has 40% of failures")
- **TASK_TYPE** - Task type failure rates (e.g., "defi.swap fails 45% of time")
- **AGENT_PERFORMANCE** - Agent success/failure rates
- **FAILURE_CORRELATION** - Dominant failure types (e.g., "RATE_LIMIT is 30% of failures")
- **COST_ANOMALY** - Tasks with abnormal costs

### 6. **listener.py** - EventListener
Web3 event listener that subscribes to contract events and routes to adapter.

**Events Listened:**
- `TaskFailed(bytes32 taskId, address agent, uint8 failureClass, uint256 checkpointCount)`
- `TaskResolved(bytes32 taskId, address primaryAgent, address fallbackAgent, ...)`

## Installation

```bash
# Install dependencies
cd pipeline
pip install -r requirements.txt

# Or use the main SDK requirements
cd ..
pip install -r sdk/requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
# Bonfires API
BONFIRES_API_KEY=your_bonfires_api_key_here
BONFIRES_API_URL=https://api.bonfires.ai/v1
BONFIRES_ROOM=cairn-failures

# Contract & RPC
CAIRN_CONTRACT_ADDRESS=0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640  # CairnCore (production)
RPC_URL=https://sepolia.base.org

# IPFS
PINATA_JWT=your_pinata_jwt_here

# Event Listener
START_BLOCK=0  # Or specific block number to start from
POLL_INTERVAL=5  # Poll every 5 seconds
```

## Usage

### Running the Pipeline

```python
import asyncio
from pipeline.config import PipelineConfig
from pipeline.bonfires import BonfiresClient
from pipeline.adapter import BonfiresAdapter
from pipeline.listener import EventListener
from sdk.checkpoint import CheckpointStore

async def main():
    # Load configuration
    config = PipelineConfig.from_env()
    config.validate()

    # Initialize clients
    ipfs = CheckpointStore(config.pinata_jwt)
    bonfires = BonfiresClient(config)
    adapter = BonfiresAdapter(bonfires, ipfs)
    listener = EventListener(config, adapter)

    # Health checks
    await bonfires.health_check()
    health = await listener.health_check()
    print(f"Listener status: {health}")

    # Start listening (blocking)
    try:
        await listener.start()
    except KeyboardInterrupt:
        print("Stopping listener...")
        await listener.stop()
    finally:
        await ipfs.close()
        await bonfires.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Querying Intelligence

```python
from pipeline.bonfires import BonfiresClient
from pipeline.config import PipelineConfig

async def query_intelligence():
    config = PipelineConfig.from_env()
    bonfires = BonfiresClient(config)

    # Get agent history
    agent_id = "erc8004://base/0x1234..."
    history = await bonfires.get_agent_history(agent_id)
    print(f"Agent success rate: {history['success_rate']:.1%}")

    # Get task type statistics
    stats = await bonfires.get_task_type_stats("defi.price_fetch", lookback_hours=24)
    print(f"Task type success rate: {stats['success_rate']:.1%}")
    print(f"Average cost: {stats['avg_cost_eth']} ETH")
    print(f"Failure patterns: {stats['failure_patterns']}")

    await bonfires.close()
```

### Pattern Detection

```python
from pipeline.patterns import PatternDetector, Severity

detector = PatternDetector(min_samples=10, confidence_threshold=0.7)

# Add records (from Bonfires query or event stream)
for record in records:
    detector.add_record(record)

# Detect patterns
patterns = detector.detect_patterns()

for pattern in patterns:
    if pattern.severity in (Severity.HIGH, Severity.CRITICAL):
        print(f"⚠️ {pattern.description}")
        print(f"   Confidence: {pattern.confidence:.1%}")
        print(f"   Data: {pattern.data}")

# Get summary
summary = detector.get_summary()
print(f"Total records: {summary['total_records']}")
print(f"Success rate: {summary['success_rate']:.1%}")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest pipeline/tests/ -v

# Run with coverage
pytest pipeline/tests/ --cov=pipeline --cov-report=html

# Run specific test file
pytest pipeline/tests/test_records.py -v
```

## Architecture Decisions

### Why Bonfires?
Bonfires provides a decentralized knowledge graph specifically designed for AI agents to share execution history and learnings. It offers:
- Decentralized storage and indexing
- Queryable knowledge graph
- Built for agent-to-agent knowledge transfer

### Why IPFS for Records?
IPFS provides:
- Immutable record storage
- Content-addressed retrieval
- Decentralized availability
- Automatic deduplication

### Why Pattern Detection?
Real-time pattern detection enables:
- Proactive alerting for recurring issues
- Cost optimization insights
- Agent performance benchmarking
- Task type risk assessment

## Performance

### Latency Targets (PRD-03 Section 12)
- **Intelligence query**: < 500ms P95
- **Record write**: < 5s (event → IPFS → indexed)
- **Pattern detection**: < 10s (batch job)
- **The Graph sync lag**: < 30 blocks

### Scalability (PRD-03 Section 12.2)
- **Month 1**: 1,000 records, < 200ms queries, 100MB storage
- **Month 6**: 50,000 records, < 500ms queries, 5GB storage
- **Year 1**: 500,000 records, < 1s queries, 50GB storage

## Security

### Data Privacy (PRD-03 Section 11.1)
- Task IDs and agent addresses are public (already on-chain)
- Checkpoint content CIDs are public, content is on IPFS
- Failure details are aggregated only for intelligence queries
- No API credentials or sensitive data in records

### API Security
- API key authentication for Bonfires
- Rate limiting: 100 requests/min per agent
- CID verification for data integrity

## Monitoring

The pipeline logs:
- ✅ Event processing (TaskFailed, TaskResolved)
- ✅ IPFS pinning success/failure
- ✅ Bonfires indexing status
- ⚠️ Pattern detection alerts
- 🔴 Error conditions

Use standard logging configuration:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Troubleshooting

### "BONFIRES_API_KEY environment variable is required"
Ensure `.env` file exists with valid `BONFIRES_API_KEY`.

### "Failed to connect to RPC"
Check `RPC_URL` is correct and accessible. Try public Base Sepolia RPC:
```
RPC_URL=https://sepolia.base.org
```

### "Pinata request timed out"
Check `PINATA_JWT` is valid. Get a new key from https://app.pinata.cloud/developers/api-keys

### Slow pattern detection
Reduce `min_samples` or increase `confidence_threshold` in PatternDetector constructor.

## Contributing

See main project [CLAUDE.md](../CLAUDE.md) for contribution guidelines.

## License

MPL-2.0 — see main project LICENSE file.

---

**Built with**:
- Python 3.10+
- Pydantic 2.x
- httpx (async HTTP)
- web3.py (Ethereum interaction)
- tenacity (retry logic)

**For**: CAIRN Protocol - Synthesis Hackathon 2026
