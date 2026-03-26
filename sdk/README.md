# CAIRN SDK

Python SDK for the CAIRN Protocol — Agent Failure and Recovery with checkpoint-based escrow settlement.

## Installation

```bash
# From the repository root
cd sdk
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from sdk import CairnClient, CairnAgent, CheckpointStore, LoggingObserver

async def main():
    # Initialize components
    client = CairnClient(
        rpc_url="https://sepolia.base.org",
        contract_address="0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640",  # CairnCore
        private_key=os.environ["PRIVATE_KEY"],
    )

    ipfs = CheckpointStore(pinata_jwt=os.environ["PINATA_JWT"])

    # Your agent implementation
    class MyAgent:
        async def execute_subtask(self, subtask: dict, context: dict) -> dict:
            # Do work...
            return {"status": "completed", "result": subtask["action"]}

    # Wrap with CAIRN
    agent = CairnAgent(MyAgent(), client, ipfs)
    agent.add_observer(LoggingObserver())

    async with agent:
        result = await agent.execute(
            task_id="0x...",
            subtasks=[
                {"action": "fetch_data"},
                {"action": "process_data"},
                {"action": "store_result"},
            ],
        )
        print(f"Completed {result['completed']} subtasks")

asyncio.run(main())
```

## Components

### CairnClient

Interacts with the CairnCore smart contract (production 6-state machine).

```python
from sdk import CairnClient

client = CairnClient(
    rpc_url="https://sepolia.base.org",
    contract_address="0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640",  # CairnCore
    private_key="0x...",  # Optional for read-only
)

# Submit a task
task_id = await client.submit_task(
    primary_agent="0x...",
    fallback_agent="0x...",
    task_cid="QmTaskSpec...",
    heartbeat_interval=60,
    deadline=int(time.time()) + 3600,
    escrow=10**17,  # 0.1 ETH
)

# Get task state
task = await client.get_task(task_id)
print(f"State: {task.state}, Checkpoints: {task.total_checkpoints}")

# Send heartbeat
await client.heartbeat(task_id)

# Commit checkpoint
await client.commit_checkpoint(task_id, "QmCheckpointCid...")

# Settle task
settlement = await client.settle(task_id)
print(f"Primary share: {settlement.primary_share / 10**18} ETH")
```

### CheckpointStore

Stores checkpoints on IPFS via Pinata with real API integration.

```python
from sdk import CheckpointStore

# Auto-loads from PINATA_JWT environment variable
async with CheckpointStore() as store:
    # Write checkpoint
    cid = await store.write({
        "subtask": 0,
        "result": {"status": "success"},
        "timestamp": int(time.time()),
    }, name="optional-name-for-pinata")

    # Read checkpoint (tries multiple IPFS gateways with fallback)
    data = await store.read(cid)

    # Check if exists
    exists = await store.exists(cid)

    # Unpin from Pinata
    await store.unpin(cid)
```

**Features**:
- Real Pinata API integration (not mocked)
- Automatic retry with exponential backoff
- Multiple IPFS gateway fallback for reads
- Auto-loads JWT from environment or accepts explicit parameter

### CairnAgent

Wraps your agent with automatic checkpointing and heartbeat.

```python
from sdk import CairnAgent

class MyAgent:
    async def execute_subtask(self, subtask: dict, context: dict) -> dict:
        # Access previous results via context
        prev_result = context.get("subtask_0_result")

        # Do your work...
        return {"output": "result"}

agent = CairnAgent(
    agent=MyAgent(),
    client=client,
    ipfs=checkpoint_store,
    heartbeat_margin=0.8,  # Send heartbeat at 80% of interval
)

async with agent:
    # Primary execution
    result = await agent.execute(task_id, subtasks)

    # Or resume as fallback
    result = await agent.resume(task_id, subtasks)
```

### Observers

Monitor task lifecycle events.

```python
from sdk import LoggingObserver, WebhookObserver, CairnObserver

# Built-in logging
agent.add_observer(LoggingObserver())

# Webhook notifications
agent.add_observer(WebhookObserver(
    webhook_url="https://hooks.slack.com/...",
    secret="optional-hmac-secret",
))

# Custom observer
class MyObserver(CairnObserver):
    async def on_checkpoint(self, task_id: str, index: int, cid: str):
        print(f"Checkpoint {index} committed!")

    async def on_failed(self, task_id: str, reason: str):
        send_alert(f"Task {task_id} failed: {reason}")

agent.add_observer(MyObserver())
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `CAIRN_RPC_URL` | Base Sepolia RPC URL | Yes |
| `CAIRN_CONTRACT` | CairnCore contract address | Yes |
| `PRIVATE_KEY` | Wallet private key | Yes (for writes) |
| `PINATA_JWT` | Pinata API JWT | Yes |

> ⚠️ **Security Warning**: Never commit private keys to version control. Use environment variables or a secure secrets manager. The `PRIVATE_KEY` grants full control over the associated wallet. For production, consider using hardware wallets, multi-sig, or key management services (e.g., AWS KMS, HashiCorp Vault).

## Error Handling

```python
from sdk.exceptions import (
    CairnError,           # Base error
    ContractError,        # Contract interaction failed
    CheckpointError,      # IPFS read/write failed
    TaskNotFoundError,    # Task doesn't exist
    InvalidStateError,    # Wrong task state for operation
)

try:
    await client.heartbeat(task_id)
except InvalidStateError as e:
    print(f"Task in {e.current_state}, expected {e.expected_states}")
except ContractError as e:
    print(f"TX failed: {e.revert_reason}")
```

## Testing

### Run Tests

```bash
cd sdk

# Install dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run all tests (unit + integration)
pytest -v

# Run only unit tests (fast, no external services needed)
pytest -v -m "not integration"

# Run integration tests (requires PINATA_JWT env var)
pytest -v -m integration

# Run with coverage
pytest --cov=sdk --cov-report=html
```

### Integration Tests

Integration tests use the **real Pinata API** and require:
- `PINATA_JWT` environment variable set (from `.env` file)
- Internet connection
- Pinata account with API access

**Note**: Integration tests will create and delete pins on Pinata during testing.

### Examples

See practical examples in `examples/`:

```bash
# Run checkpoint examples
python -m sdk.examples.checkpoint_example
```

Examples demonstrate:
- Basic write/read operations
- Multi-step tasks with sequential checkpoints
- Error handling and recovery
- Resume from checkpoint (fallback scenario)
- Concurrent checkpoint operations

## Contract Addresses

### CairnCore (Production)

**Base Sepolia**: `0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640`

[View on Basescan](https://sepolia.basescan.org/address/0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640)

### CairnTaskMVP (Legacy)

**Base Sepolia**: `0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417`

[View on Basescan](https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417)

> **Note**: Use CairnCore for all new integrations. CairnTaskMVP is retained for backwards compatibility.

## License

MPL-2.0 — See [LICENSE](../LICENSE)
