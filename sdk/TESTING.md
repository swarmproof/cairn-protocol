# CAIRN SDK - Testing Guide

Comprehensive testing guide for the CAIRN SDK with real IPFS integration.

## Test Structure

```
sdk/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Pytest configuration & fixtures
│   └── test_checkpoint_integration.py # Integration tests (real API)
├── verify_integration.py              # Quick verification script
├── examples/
│   └── checkpoint_example.py          # Runnable examples
└── pytest.ini                         # Pytest settings
```

## Test Types

### 1. Integration Tests (Real API)

Tests that use **real Pinata API** and **real IPFS**.

**Location**: `tests/test_checkpoint_integration.py`

**Requirements**:
- `PINATA_JWT` environment variable
- Internet connection
- Pinata account with API access

**What they test**:
- Real Pinata API writes
- Real IPFS gateway reads
- Network error handling
- Retry logic
- Gateway fallback
- Concurrent operations

**Run**:
```bash
# All integration tests
pytest -v -m integration

# Specific test
pytest -v tests/test_checkpoint_integration.py::test_write_and_read

# Skip slow tests
pytest -v -m "integration and not slow"
```

### 2. Verification Script

Quick sanity check that everything works.

**Location**: `verify_integration.py`

**What it tests**:
- SDK imports
- Environment setup
- Basic write/read flow
- Data integrity
- Cleanup (unpin)

**Run**:
```bash
python verify_integration.py
```

**Expected output**:
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

### 3. Example Scripts

Practical examples that demonstrate usage.

**Location**: `examples/checkpoint_example.py`

**What they demonstrate**:
- Basic operations
- Multi-step workflows
- Error handling patterns
- Resume from checkpoint
- Concurrent operations

**Run**:
```bash
python -m sdk.examples.checkpoint_example
```

## Installation

### Minimal (runtime only)

```bash
pip install -r requirements.txt
```

### Full (with dev tools)

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

**Dev dependencies include**:
- pytest (testing framework)
- pytest-asyncio (async test support)
- pytest-cov (coverage reporting)
- black (code formatting)
- ruff (linting)
- mypy (type checking)

## Running Tests

### Quick Start

```bash
# Setup
export PINATA_JWT="eyJ..."  # Or add to .env

# Run verification
python verify_integration.py

# Run integration tests
pytest -v -m integration

# Run examples
python -m sdk.examples.checkpoint_example
```

### All Test Commands

```bash
# ──────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────

# All integration tests
pytest -v -m integration

# Specific test file
pytest -v tests/test_checkpoint_integration.py

# Specific test
pytest -v tests/test_checkpoint_integration.py::test_write_and_read

# Exclude slow tests
pytest -v -m "integration and not slow"

# Only slow tests
pytest -v -m "integration and slow"

# ──────────────────────────────────────────────────────
# Coverage
# ──────────────────────────────────────────────────────

# Generate coverage report
pytest --cov=sdk --cov-report=html -m integration

# View coverage
open htmlcov/index.html

# Terminal coverage
pytest --cov=sdk --cov-report=term -m integration

# Minimum coverage threshold (fail if below 80%)
pytest --cov=sdk --cov-fail-under=80 -m integration

# ──────────────────────────────────────────────────────
# Verification & Examples
# ──────────────────────────────────────────────────────

# Quick verification
python verify_integration.py

# All examples
python -m sdk.examples.checkpoint_example

# ──────────────────────────────────────────────────────
# Code Quality
# ──────────────────────────────────────────────────────

# Format code
black sdk/ tests/ examples/

# Lint code
ruff check sdk/ tests/ examples/

# Type check
mypy sdk/
```

## Test Markers

Pytest markers defined in `pytest.ini`:

| Marker | Description | Usage |
|--------|-------------|-------|
| `integration` | Real API calls required | `pytest -m integration` |
| `slow` | Takes >5 seconds | `pytest -m slow` |
| `unit` | Fast, mocked tests | `pytest -m unit` |

**Examples**:
```bash
# Only integration tests
pytest -m integration

# Integration but not slow
pytest -m "integration and not slow"

# Everything except integration
pytest -m "not integration"
```

## Test Fixtures

Defined in `tests/conftest.py`:

### `pinata_jwt`

Returns `PINATA_JWT` from environment or skips test.

```python
@pytest.mark.integration
async def test_something(pinata_jwt):
    store = CheckpointStore(pinata_jwt=pinata_jwt)
    # ...
```

### `sample_checkpoint_data`

Returns sample checkpoint data for testing.

```python
async def test_something(sample_checkpoint_data):
    cid = await store.write(sample_checkpoint_data)
    # ...
```

## Integration Test Details

### Test Coverage

| Test | What It Tests | Duration |
|------|---------------|----------|
| `test_checkpoint_store_init_from_env` | Auto-load JWT from env | <1s |
| `test_checkpoint_store_init_explicit` | Explicit JWT parameter | <1s |
| `test_checkpoint_store_init_missing` | Error on missing JWT | <1s |
| `test_write_and_read` | Full write/read cycle | ~5s |
| `test_read_nonexistent_cid` | Error handling | ~2s |
| `test_gateway_fallback` | Multiple gateways | ~5s |
| `test_exists_check` | CID existence | ~5s |
| `test_unpin` | Unpin operation | ~3s |
| `test_context_manager` | Async cleanup | <1s |
| `test_concurrent_writes` | Concurrent pins | ~10s |
| `test_large_checkpoint_data` | Large payloads | ~10s |

**Total runtime**: ~45 seconds (with slow tests)

### Test Isolation

Each test:
1. Creates new CheckpointStore instance
2. Writes to Pinata (creates real pins)
3. Reads from IPFS
4. Cleans up (unpins) after completion

**No shared state** between tests - each is independent.

### IPFS Propagation

Tests account for IPFS propagation delay:

```python
# Write
cid = await store.write(data)

# Wait for propagation
await asyncio.sleep(3)

# Read
data = await store.read(cid)
```

Typical delays:
- Pinata write: 500ms - 2s
- IPFS propagation: 2s - 5s
- Gateway read: 200ms - 1s

## Environment Setup

### Required Variables

```bash
# .env file
PINATA_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Load Environment

**Option 1**: Export directly
```bash
export PINATA_JWT="eyJ..."
pytest -v -m integration
```

**Option 2**: Use .env file
```bash
# Load from .env
export $(cat .env | grep PINATA_JWT | xargs)
pytest -v -m integration
```

**Option 3**: python-dotenv (recommended for examples)
```python
from dotenv import load_dotenv
load_dotenv()

# Now os.getenv("PINATA_JWT") works
```

## Troubleshooting Tests

### Issue: Tests Skip

**Error**: `PINATA_JWT not set - skipping integration test`

**Solution**:
```bash
# Check if set
echo $PINATA_JWT

# If not set
export PINATA_JWT="eyJ..."

# Or add to .env
echo "PINATA_JWT=eyJ..." >> .env
```

### Issue: Tests Fail with Network Error

**Error**: `All IPFS gateways failed`

**Causes**:
1. No internet connection
2. IPFS gateways down
3. Pinata API issues

**Solution**:
```bash
# Check internet
ping ipfs.io

# Check Pinata status
curl https://api.pinata.cloud/data/testAuthentication \
  -H "Authorization: Bearer $PINATA_JWT"

# Retry tests
pytest -v -m integration --maxfail=1
```

### Issue: Tests Slow

**Error**: Tests take >1 minute

**Cause**: IPFS propagation delays

**Solution**:
```bash
# Skip slow tests
pytest -v -m "integration and not slow"

# Run in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -v -m integration -n 4
```

### Issue: Cleanup Fails

**Error**: Pins not unpinned after test

**Solution**:
```bash
# Manual cleanup via Pinata dashboard
# Or via API:
curl -X DELETE https://api.pinata.cloud/pinning/unpin/CID \
  -H "Authorization: Bearer $PINATA_JWT"
```

## Best Practices

### 1. Always Clean Up

```python
@pytest.mark.integration
async def test_something():
    async with CheckpointStore() as store:
        cid = await store.write(data)
        try:
            # Test code...
        finally:
            await store.unpin(cid)  # Always cleanup
```

### 2. Wait for Propagation

```python
cid = await store.write(data)
await asyncio.sleep(3)  # Wait for IPFS
data = await store.read(cid)
```

### 3. Use Fixtures

```python
@pytest.mark.integration
async def test_something(sample_checkpoint_data):
    # Use provided fixture instead of hardcoding
    cid = await store.write(sample_checkpoint_data)
```

### 4. Handle Network Errors

```python
from sdk.exceptions import CheckpointError

try:
    data = await store.read(cid)
except CheckpointError:
    pytest.fail("Should have succeeded")
```

### 5. Test Concurrency

```python
tasks = [store.write(data) for _ in range(5)]
cids = await asyncio.gather(*tasks)
# Verify all succeeded
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run integration tests
        env:
          PINATA_JWT: ${{ secrets.PINATA_JWT }}
        run: |
          pytest -v -m integration --cov=sdk --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Secrets Setup

1. Go to repository Settings > Secrets
2. Add `PINATA_JWT` secret
3. Never commit JWT to git!

## Performance Benchmarks

### Expected Performance

| Operation | Expected | Acceptable | Too Slow |
|-----------|----------|------------|----------|
| Write | 500ms - 2s | < 5s | > 10s |
| Read (first) | 1s - 3s | < 10s | > 30s |
| Read (cached) | 200ms - 500ms | < 2s | > 5s |
| Exists | 100ms - 500ms | < 2s | > 5s |
| Unpin | 200ms - 500ms | < 3s | > 10s |

### Benchmark Tests

```python
import time

async def benchmark_write():
    start = time.time()
    cid = await store.write(data)
    duration = time.time() - start
    assert duration < 5.0, f"Write too slow: {duration}s"
```

## Coverage Goals

| Module | Target | Current |
|--------|--------|---------|
| checkpoint.py | 95%+ | ✅ |
| agent.py | 90%+ | ⏳ |
| client.py | 90%+ | ⏳ |
| exceptions.py | 100% | ✅ |

**Check coverage**:
```bash
pytest --cov=sdk --cov-report=term
```

## Summary

✅ **Integration tests** - Real API, comprehensive coverage
✅ **Verification script** - Quick sanity check
✅ **Examples** - Practical demonstrations
✅ **Fixtures** - Reusable test data
✅ **Markers** - Organized test categories
✅ **Documentation** - Clear testing guide

**Run all checks**:
```bash
# 1. Verify
python verify_integration.py

# 2. Test
pytest -v -m integration

# 3. Examples
python -m sdk.examples.checkpoint_example

# 4. Coverage
pytest --cov=sdk --cov-report=html
```

Ready to test! 🧪
