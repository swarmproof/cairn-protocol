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
        contract_address="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417",
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

Interacts with the CairnTaskMVP smart contract.

```python
from sdk import CairnClient

client = CairnClient(
    rpc_url="https://sepolia.base.org",
    contract_address="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417",
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

Stores checkpoints on IPFS via Pinata.

```python
from sdk import CheckpointStore

async with CheckpointStore(pinata_jwt="eyJ...") as store:
    # Write checkpoint
    cid = await store.write({
        "subtask": 0,
        "result": {"status": "success"},
        "timestamp": int(time.time()),
    })

    # Read checkpoint
    data = await store.read(cid)

    # Check if exists
    exists = await store.exists(cid)
```

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
| `CAIRN_CONTRACT` | CairnTaskMVP address | Yes |
| `PRIVATE_KEY` | Wallet private key | Yes (for writes) |
| `PINATA_JWT` | Pinata API JWT | Yes |

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

```bash
cd sdk
pip install -e ".[dev]"
pytest -v
pytest --cov=sdk --cov-report=html
```

## Contract Address

**Base Sepolia**: `0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417`

[View on Basescan](https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417)

## License

BSL-1.1 — See [LICENSE](../LICENSE)
