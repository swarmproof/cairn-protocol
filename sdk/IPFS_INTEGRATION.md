# CAIRN SDK - IPFS/Pinata Integration

This document describes the real IPFS/Pinata integration in the CAIRN SDK.

## Overview

The CAIRN SDK uses **real Pinata API integration** (not mocked) for checkpoint storage on IPFS. This provides:

- **Decentralized storage** - Checkpoints stored on IPFS, accessible via multiple gateways
- **Reliability** - Pinata ensures content is pinned and available
- **Resilience** - Automatic retry and gateway fallback for reads
- **Production-ready** - Real API calls with proper error handling

## Architecture

```
┌─────────────────┐
│  CairnAgent     │
│  (Agent Wrapper)│
└────────┬────────┘
         │
         ├─ execute_subtask()
         │
         └─► checkpoint() ────────┐
                                  │
                    ┌─────────────▼──────────────┐
                    │   CheckpointStore          │
                    │                            │
                    │  write() ──► Pinata API    │
                    │            (Pin JSON)      │
                    │                            │
                    │  read() ───► IPFS Gateways │
                    │            (Fallback)      │
                    │                            │
                    │  unpin() ─► Pinata API     │
                    │            (Unpin)         │
                    └────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  IPFS Network       │
                    │  - gateway.pinata   │
                    │  - ipfs.io          │
                    │  - dweb.link        │
                    │  - cloudflare-ipfs  │
                    └─────────────────────┘
```

## CheckpointStore Implementation

### Initialization

```python
from sdk.checkpoint import CheckpointStore

# Option 1: Auto-load from environment (recommended)
store = CheckpointStore()  # Reads PINATA_JWT from .env

# Option 2: Explicit JWT
store = CheckpointStore(pinata_jwt="eyJ...")
```

### Writing Checkpoints

```python
async with CheckpointStore() as store:
    checkpoint_data = {
        "task_id": "task-123",
        "subtask_index": 0,
        "agent": "0x1234...",
        "timestamp": 1710000000,
        "data": {"result": "success"}
    }

    # Write to Pinata (returns CID)
    cid = await store.write(
        checkpoint_data,
        name="task-123-checkpoint-0"  # Optional name for Pinata dashboard
    )
    # Returns: "QmXxx..." or "bafyxxx..."
```

**Write Process**:
1. Serialize data to JSON
2. POST to Pinata API with JWT auth
3. Retry up to 3 times with exponential backoff (1s, 2s, 4s)
4. Return IPFS CID (Content Identifier)

### Reading Checkpoints

```python
async with CheckpointStore() as store:
    # Read from IPFS (tries multiple gateways)
    data = await store.read(cid)
```

**Read Process** (Gateway Fallback):
1. Try `gateway.pinata.cloud` (fastest for pinned content)
2. If fails, try `ipfs.io`
3. If fails, try `dweb.link`
4. If fails, try `cloudflare-ipfs.com`
5. Each gateway has 3 retries with exponential backoff
6. Returns data if any gateway succeeds
7. Raises `CheckpointError` if all fail

### Checking Existence

```python
async with CheckpointStore() as store:
    exists = await store.exists(cid)  # Returns bool
```

Uses HEAD requests to first 2 gateways with short timeout (5s).

### Unpinning

```python
async with CheckpointStore() as store:
    await store.unpin(cid)  # Returns True
```

Removes pin from Pinata. Content may still be available on IPFS via other nodes.

## Error Handling

### CheckpointError

All checkpoint operations can raise `CheckpointError`:

```python
from sdk.exceptions import CheckpointError

try:
    cid = await store.write(data)
except CheckpointError as e:
    print(f"Error: {e.message}")
    print(f"Gateway: {e.gateway}")  # If applicable
    print(f"CID: {e.cid}")  # If applicable
```

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| "PINATA_JWT is required" | Missing env var | Set `PINATA_JWT` in `.env` |
| "Pinata API error: 401" | Invalid JWT | Get new JWT from Pinata dashboard |
| "Pinata request timed out" | Network issue | Retry will handle automatically |
| "All IPFS gateways failed" | CID doesn't exist or network down | Verify CID, check internet |

## Retry Logic

### Write Retries

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
)
```

- **Attempts**: 3
- **Wait**: 1s, 2s, 4s (exponential)
- **Retries on**: HTTP errors, timeouts
- **Max wait**: 10s

### Read Retries (per gateway)

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5)
)
```

- **Attempts**: 3 per gateway
- **Wait**: 1s, 2s, 4s
- **Total attempts**: 3 × 4 gateways = 12 max attempts

## Configuration

### Environment Variables

```bash
# Required
PINATA_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional (has defaults)
REQUEST_TIMEOUT=10.0  # HTTP timeout in seconds
```

### IPFS Gateways

Configured in `checkpoint.py`:

```python
IPFS_GATEWAYS = [
    "https://gateway.pinata.cloud/ipfs/",  # Primary (fastest for pinned)
    "https://ipfs.io/ipfs/",               # Public gateway
    "https://dweb.link/ipfs/",             # Public gateway
    "https://cloudflare-ipfs.com/ipfs/",   # Public gateway
]
```

Order matters - tries in sequence.

### Timeouts

```python
REQUEST_TIMEOUT = 10.0  # Default HTTP timeout (seconds)
```

For existence checks, uses shorter timeout (5s) to fail fast.

## Testing

### Unit Tests

Unit tests use mocked HTTP responses (not included yet - TOD if needed).

### Integration Tests

Integration tests use **real Pinata API**:

```bash
# Set environment
export PINATA_JWT="eyJ..."

# Run integration tests
cd sdk
pytest -v -m integration

# Run specific test
pytest -v tests/test_checkpoint_integration.py::test_write_and_read
```

**Note**: Integration tests will:
- Create real pins on Pinata
- Wait for IPFS propagation (2-5 seconds)
- Clean up (unpin) after each test
- Require internet connection

### Verification Script

Quick check that everything works:

```bash
cd sdk
python verify_integration.py
```

This runs:
1. Environment check (PINATA_JWT)
2. Write checkpoint
3. Read checkpoint
4. Verify data integrity
5. Check existence
6. Unpin checkpoint

## Examples

### Example 1: Basic Usage

See `examples/checkpoint_example.py` for complete examples.

```bash
python -m sdk.examples.checkpoint_example
```

### Example 2: With CairnAgent

```python
from sdk import CairnAgent, CairnClient, CheckpointStore

client = CairnClient(rpc_url, contract, private_key)
store = CheckpointStore()  # Auto-loads PINATA_JWT

agent = CairnAgent(MyAgent(), client, store)

async with agent:
    result = await agent.execute(task_id, subtasks)
    # Checkpoints automatically written to IPFS after each subtask
```

## Performance Characteristics

| Operation | Typical Latency | Max Retries | Total Timeout |
|-----------|----------------|-------------|---------------|
| Write (Pinata) | 500ms - 2s | 3 | ~30s |
| Read (single gateway) | 200ms - 1s | 3 | ~30s |
| Read (all gateways) | - | 12 | ~2 minutes |
| Exists check | 100ms - 500ms | 0 | 5s |
| Unpin | 200ms - 500ms | 0 | 10s |

**Notes**:
- Write times include network + Pinata processing
- First read after write may need 2-5s for IPFS propagation
- Subsequent reads are faster (cached on gateways)
- Exists check uses HEAD requests (no data transfer)

## Best Practices

### 1. Use Async Context Manager

```python
async with CheckpointStore() as store:
    cid = await store.write(data)
    # HTTP client automatically closed
```

### 2. Wait After Write Before Read

```python
cid = await store.write(data)
await asyncio.sleep(2)  # Allow IPFS propagation
data = await store.read(cid)
```

### 3. Handle Errors Gracefully

```python
from sdk.exceptions import CheckpointError

try:
    cid = await store.write(data)
except CheckpointError as e:
    logger.error(f"Checkpoint failed: {e}")
    # Fallback: store locally, retry later
```

### 4. Use Descriptive Names

```python
cid = await store.write(
    data,
    name=f"task-{task_id}-checkpoint-{index}"
)
# Easier to find in Pinata dashboard
```

### 5. Clean Up Test Pins

```python
# In tests
cid = await store.write(test_data)
try:
    # ... test code ...
finally:
    await store.unpin(cid)  # Always cleanup
```

## Troubleshooting

### Issue: "PINATA_JWT is required"

**Solution**: Set environment variable

```bash
export PINATA_JWT="eyJ..."
# Or add to .env file
```

### Issue: Write succeeds but read fails

**Cause**: IPFS propagation delay

**Solution**: Add delay before read

```python
cid = await store.write(data)
await asyncio.sleep(3)  # Wait for propagation
data = await store.read(cid)
```

### Issue: "All IPFS gateways failed"

**Causes**:
1. CID doesn't exist
2. Network connectivity issue
3. All gateways down (rare)

**Solution**:
```python
# Verify CID was written
exists = await store.exists(cid)
if not exists:
    # CID not available yet or doesn't exist
```

### Issue: Slow reads

**Cause**: Gateway latency

**Solution**: Content should cache on gateways. First read is slow, subsequent reads faster.

### Issue: Rate limiting

**Cause**: Too many requests to Pinata

**Solution**: Pinata free tier has generous limits. If hitting limits, consider:
- Batch operations
- Upgrade Pinata plan
- Add delays between operations

## Security Considerations

### JWT Protection

- **Never commit** `PINATA_JWT` to git
- Store in `.env` file (gitignored)
- Use environment variables in production
- Rotate JWT periodically

### Data Privacy

- Data pinned to IPFS is **public**
- Anyone with CID can read content
- Don't store sensitive data without encryption
- Consider encrypting checkpoint data before pinning

### Access Control

- JWT gives full Pinata account access
- Use scoped API keys when possible
- One JWT per environment (dev/staging/prod)

## API Reference

See [checkpoint.py](./checkpoint.py) for full implementation and docstrings.

### CheckpointStore

```python
class CheckpointStore:
    def __init__(self, pinata_jwt: str | None = None)
    async def write(self, data: dict, name: str | None = None) -> str
    async def read(self, cid: str) -> dict
    async def exists(self, cid: str) -> bool
    async def unpin(self, cid: str) -> bool
    async def close(self) -> None
```

## Resources

- [Pinata Documentation](https://docs.pinata.cloud/)
- [IPFS Documentation](https://docs.ipfs.tech/)
- [CAIRN Protocol](../README.md)
- [SDK Examples](./examples/)

## Support

For issues or questions:
1. Check this documentation
2. See examples in `examples/`
3. Run `verify_integration.py`
4. Check integration tests
5. Open an issue on GitHub
