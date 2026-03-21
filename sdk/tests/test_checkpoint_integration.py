"""
Integration tests for CheckpointStore with real Pinata API.

These tests use the real Pinata API and require PINATA_JWT environment variable.
Run with: pytest -m integration
"""

import pytest
import asyncio
import time
from sdk.checkpoint import CheckpointStore
from sdk.exceptions import CheckpointError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_store_init_from_env():
    """Test that CheckpointStore can auto-load JWT from environment."""
    store = CheckpointStore()
    assert store._jwt is not None
    await store.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_store_init_explicit(pinata_jwt):
    """Test that CheckpointStore accepts explicit JWT."""
    store = CheckpointStore(pinata_jwt=pinata_jwt)
    assert store._jwt == pinata_jwt
    await store.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_checkpoint_store_init_missing():
    """Test that CheckpointStore raises error when JWT is missing."""
    import os
    old_jwt = os.environ.pop("PINATA_JWT", None)

    try:
        with pytest.raises(CheckpointError, match="PINATA_JWT is required"):
            CheckpointStore()
    finally:
        if old_jwt:
            os.environ["PINATA_JWT"] = old_jwt


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_write_and_read(sample_checkpoint_data):
    """Test writing checkpoint to Pinata and reading it back."""
    async with CheckpointStore() as store:
        # Write checkpoint
        cid = await store.write(
            sample_checkpoint_data,
            name=f"test-checkpoint-{int(time.time())}",
        )

        # Verify CID format (should start with Qm or ba for CIDv0/v1)
        assert cid.startswith(("Qm", "ba", "baf"))
        assert len(cid) > 40  # CIDs are typically 46+ chars

        # Read checkpoint back
        # Note: IPFS propagation can take a moment, so we retry
        for attempt in range(5):
            try:
                data = await store.read(cid)
                break
            except CheckpointError:
                if attempt < 4:
                    await asyncio.sleep(2)  # Wait for IPFS propagation
                else:
                    raise

        # Verify data matches
        assert data == sample_checkpoint_data
        assert data["task_id"] == "test-task-123"
        assert data["subtask_index"] == 0
        assert data["data"]["result"] == "success"

        # Cleanup - unpin from Pinata
        await store.unpin(cid)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_nonexistent_cid():
    """Test reading a non-existent CID fails gracefully."""
    async with CheckpointStore() as store:
        # Use a valid-looking but non-existent CID
        fake_cid = "QmTzQ1JRkWErMnqLiM7dNLKkxQXQTsVGUeGiJcPKLUKRj9"

        with pytest.raises(CheckpointError, match="All IPFS gateways failed"):
            await store.read(fake_cid)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_gateway_fallback(sample_checkpoint_data):
    """Test that gateway fallback works when primary gateway fails."""
    async with CheckpointStore() as store:
        # Write checkpoint
        cid = await store.write(sample_checkpoint_data)

        # Wait for propagation
        await asyncio.sleep(3)

        # Read should work even if first gateway is slow
        # (we can't easily simulate gateway failure in integration test,
        # but we verify the multi-gateway read works)
        data = await store.read(cid)
        assert data == sample_checkpoint_data

        # Cleanup
        await store.unpin(cid)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_exists_check(sample_checkpoint_data):
    """Test checking if CID exists on IPFS."""
    async with CheckpointStore() as store:
        # Write checkpoint
        cid = await store.write(sample_checkpoint_data)

        # Wait for propagation
        await asyncio.sleep(3)

        # Check existence
        exists = await store.exists(cid)
        assert exists is True

        # Check non-existent CID
        fake_cid = "QmTzQ1JRkWErMnqLiM7dNLKkxQXQTsVGUeGiJcPKLUKRj9"
        exists = await store.exists(fake_cid)
        assert exists is False

        # Cleanup
        await store.unpin(cid)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_unpin(sample_checkpoint_data):
    """Test unpinning content from Pinata."""
    async with CheckpointStore() as store:
        # Write checkpoint
        cid = await store.write(sample_checkpoint_data)

        # Unpin
        result = await store.unpin(cid)
        assert result is True

        # Unpin again (should succeed - idempotent)
        result = await store.unpin(cid)
        assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager properly closes HTTP client."""
    store = CheckpointStore()

    # Client should be created on first use
    assert store._client is None

    async with store:
        # Make a request to create client
        await store._get_client()
        assert store._client is not None
        assert not store._client.is_closed

    # After context exit, client should be closed
    assert store._client is None or store._client.is_closed


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_concurrent_writes(sample_checkpoint_data):
    """Test concurrent checkpoint writes work correctly."""
    async with CheckpointStore() as store:
        # Create multiple checkpoints concurrently
        tasks = []
        for i in range(3):
            data = {**sample_checkpoint_data, "subtask_index": i}
            task = store.write(data, name=f"concurrent-test-{i}")
            tasks.append(task)

        # Wait for all writes
        cids = await asyncio.gather(*tasks)

        # Verify all CIDs are unique
        assert len(cids) == len(set(cids))

        # Wait for propagation
        await asyncio.sleep(3)

        # Verify all can be read back
        for i, cid in enumerate(cids):
            data = await store.read(cid)
            assert data["subtask_index"] == i

        # Cleanup
        for cid in cids:
            await store.unpin(cid)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_large_checkpoint_data():
    """Test writing and reading large checkpoint data."""
    async with CheckpointStore() as store:
        # Create large checkpoint (but within reasonable limits)
        large_data = {
            "task_id": "large-test",
            "subtask_index": 0,
            "data": {
                "large_array": list(range(10000)),
                "nested": {
                    f"key_{i}": f"value_{i}" * 10
                    for i in range(100)
                },
            },
        }

        # Write
        cid = await store.write(large_data, name="large-checkpoint-test")

        # Wait for propagation
        await asyncio.sleep(5)

        # Read back
        data = await store.read(cid)
        assert data == large_data
        assert len(data["data"]["large_array"]) == 10000

        # Cleanup
        await store.unpin(cid)
