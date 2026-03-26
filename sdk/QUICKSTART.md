# CAIRN SDK - Quick Start Guide

Get started with CAIRN checkpoints in 5 minutes.

## Prerequisites

- Python 3.10+
- Pinata account with API key ([get free account](https://app.pinata.cloud/developers/api-keys))
- Base Sepolia RPC URL (e.g., `https://sepolia.base.org`)

## Step 1: Setup Environment

```bash
# Clone repository
git clone <repo-url>
cd cairn-protocol/sdk

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp ../.env.example ../.env
```

## Step 2: Configure Environment

Edit `.env` file:

```bash
# Required for CheckpointStore
PINATA_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Required for CairnClient
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
CAIRN_CONTRACT_ADDRESS=0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640  # CairnCore (production)

# Required for agent operations (testnet keys only!)
PRIMARY_AGENT_PRIVATE_KEY=0x...
```

**Get your Pinata JWT**:
1. Go to https://app.pinata.cloud/developers/api-keys
2. Create new API key
3. Copy JWT token
4. Paste into `.env`

## Step 3: Verify Integration

```bash
# Quick verification
python verify_integration.py
```

Expected output:
```
✓ SDK imports successful
✓ PINATA_JWT loaded
✓ CheckpointStore initialized
✓ Checkpoint written successfully
✓ Checkpoint read successfully
✓ Data integrity verified
✓ CID exists on IPFS
✓ Checkpoint unpinned successfully

✓ ALL INTEGRATION TESTS PASSED
```

## Step 4: Run Examples

```bash
# Run all examples
python -m sdk.examples.checkpoint_example
```

This demonstrates:
- Basic write/read
- Multi-step tasks
- Error handling
- Resume from checkpoint
- Concurrent operations

## Step 5: Write Your Agent

### Simple Agent

```python
# my_agent.py
import asyncio
from sdk import CairnClient, CairnAgent, CheckpointStore

class SimpleAgent:
    """Agent that processes data in steps."""

    async def execute_subtask(self, subtask: dict, context: dict) -> dict:
        """Execute one subtask."""
        step_name = subtask["name"]
        print(f"Processing: {step_name}")

        # Your agent logic here
        result = {"step": step_name, "status": "completed"}

        return result


async def main():
    # Initialize CAIRN components
    client = CairnClient(
        rpc_url="https://sepolia.base.org",
        contract_address="0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640",  # CairnCore
        private_key="0x...",  # Your agent's private key
    )

    store = CheckpointStore()  # Auto-loads PINATA_JWT

    # Wrap your agent
    agent = CairnAgent(SimpleAgent(), client, store)

    # Execute task
    async with agent:
        result = await agent.execute(
            task_id="your-task-id",
            subtasks=[
                {"name": "fetch_data"},
                {"name": "process_data"},
                {"name": "store_result"},
            ],
        )

        print(f"✓ Completed {result['completed']}/{result['total']} subtasks")


if __name__ == "__main__":
    asyncio.run(main())
```

### Run Your Agent

```bash
python my_agent.py
```

## Step 6: Test Your Agent (Optional)

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run integration tests
pytest -v -m integration

# Run with coverage
pytest --cov=sdk --cov-report=html -m integration
```

## Common Commands

```bash
# Verify setup
python verify_integration.py

# Run examples
python -m sdk.examples.checkpoint_example

# Run tests
pytest -v -m integration

# Install dev tools
pip install -r requirements-dev.txt

# Generate coverage report
pytest --cov=sdk --cov-report=html
```

## Troubleshooting

### Error: "PINATA_JWT is required"

**Solution**: Set environment variable

```bash
export PINATA_JWT="eyJ..."
# Or add to .env file
```

### Error: "All IPFS gateways failed"

**Cause**: Network issue or CID doesn't exist yet

**Solution**:
```python
# Wait for IPFS propagation after write
cid = await store.write(data)
await asyncio.sleep(2-3)  # Wait 2-3 seconds
data = await store.read(cid)
```

### Error: "Pinata API error: 401"

**Cause**: Invalid or expired JWT

**Solution**: Get new JWT from Pinata dashboard

## Next Steps

1. ✅ Read [IPFS_INTEGRATION.md](./IPFS_INTEGRATION.md) for detailed guide
2. ✅ Review [examples/](./examples/) for advanced patterns
3. ✅ Check [README.md](./README.md) for full API reference
4. ✅ See [INTEGRATION_SUMMARY.md](./INTEGRATION_SUMMARY.md) for implementation details

## Key Concepts

### Checkpoint Flow

```
1. Agent executes subtask
2. CairnAgent calls checkpoint()
3. CheckpointStore.write() pins to Pinata
4. Returns CID
5. CairnAgent commits CID to contract
6. Repeat for each subtask
```

### Fallback/Recovery Flow

```
1. Primary agent fails mid-task
2. Contract triggers recovery
3. Fallback agent reads checkpoints from IPFS
4. Fallback resumes from last checkpoint
5. Completes remaining subtasks
6. Contract settles payment
```

## Resources

- [CAIRN Protocol Documentation](../README.md)
- [Pinata Documentation](https://docs.pinata.cloud/)
- [IPFS Documentation](https://docs.ipfs.tech/)
- [Base Sepolia Explorer](https://sepolia.basescan.org/)

## Support

Need help?
1. Check [IPFS_INTEGRATION.md](./IPFS_INTEGRATION.md)
2. Run verification: `python verify_integration.py`
3. Review examples: `python -m sdk.examples.checkpoint_example`
4. Check integration tests: `pytest -v -m integration`

Happy building! 🚀
