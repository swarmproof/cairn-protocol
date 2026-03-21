"""
CAIRN Checkpoint Example

Demonstrates how to use CAIRN checkpoints with IPFS/Pinata.

Usage:
    # Set PINATA_JWT in .env or environment
    python -m sdk.examples.checkpoint_example

Requirements:
    - PINATA_JWT environment variable set
    - Install dependencies: pip install -r requirements.txt
"""

import asyncio
import time
import os
from datetime import datetime

from sdk.checkpoint import CheckpointStore
from sdk.exceptions import CheckpointError


async def example_basic_write_read():
    """Example 1: Basic write and read operation."""
    print("\n=== Example 1: Basic Write & Read ===")

    async with CheckpointStore() as store:
        # Prepare checkpoint data
        checkpoint = {
            "task_id": "example-task-001",
            "subtask_index": 0,
            "agent": "0x1234567890123456789012345678901234567890",
            "timestamp": int(time.time()),
            "data": {
                "step": "initialize",
                "result": "success",
                "metrics": {
                    "duration_ms": 125,
                    "memory_mb": 45.2,
                },
            },
        }

        # Write to IPFS
        print(f"Writing checkpoint to IPFS...")
        cid = await store.write(checkpoint, name="example-checkpoint-basic")
        print(f"✓ Checkpoint written: {cid}")

        # Wait for IPFS propagation
        print("Waiting for IPFS propagation...")
        await asyncio.sleep(3)

        # Read back from IPFS
        print(f"Reading checkpoint from IPFS...")
        data = await store.read(cid)
        print(f"✓ Checkpoint read successfully")
        print(f"  Task ID: {data['task_id']}")
        print(f"  Result: {data['data']['result']}")

        # Cleanup
        print(f"Unpinning checkpoint...")
        await store.unpin(cid)
        print(f"✓ Checkpoint unpinned")


async def example_multi_step_task():
    """Example 2: Multi-step task with sequential checkpoints."""
    print("\n=== Example 2: Multi-Step Task ===")

    async with CheckpointStore() as store:
        task_id = f"task-{int(time.time())}"
        checkpoints = []

        # Simulate a multi-step task
        steps = [
            {"name": "data_fetch", "duration": 234},
            {"name": "data_process", "duration": 567},
            {"name": "model_inference", "duration": 1234},
            {"name": "result_format", "duration": 89},
        ]

        print(f"Task ID: {task_id}")

        for i, step in enumerate(steps):
            print(f"\nStep {i+1}/{len(steps)}: {step['name']}")

            # Create checkpoint for this step
            checkpoint = {
                "task_id": task_id,
                "subtask_index": i,
                "agent": "0x1234567890123456789012345678901234567890",
                "timestamp": int(time.time()),
                "data": {
                    "step_name": step["name"],
                    "status": "completed",
                    "duration_ms": step["duration"],
                },
            }

            # Write checkpoint
            cid = await store.write(checkpoint, name=f"{task_id}-step-{i}")
            print(f"  ✓ Checkpoint: {cid}")
            checkpoints.append(cid)

        # Wait for propagation
        await asyncio.sleep(3)

        # Verify all checkpoints
        print(f"\nVerifying {len(checkpoints)} checkpoints...")
        for i, cid in enumerate(checkpoints):
            data = await store.read(cid)
            print(f"  ✓ Step {i}: {data['data']['step_name']} - {data['data']['status']}")

        # Cleanup all checkpoints
        print(f"\nCleaning up...")
        for cid in checkpoints:
            await store.unpin(cid)
        print(f"✓ All checkpoints unpinned")


async def example_error_handling():
    """Example 3: Error handling and recovery."""
    print("\n=== Example 3: Error Handling ===")

    async with CheckpointStore() as store:
        # Test 1: Reading non-existent CID
        print("Test 1: Reading non-existent CID...")
        try:
            fake_cid = "QmTzQ1JRkWErMnqLiM7dNLKkxQXQTsVGUeGiJcPKLUKRj9"
            await store.read(fake_cid)
            print("  ✗ Should have failed!")
        except CheckpointError as e:
            print(f"  ✓ Correctly caught error: {e}")

        # Test 2: Check if CID exists
        print("\nTest 2: Checking CID existence...")
        valid_checkpoint = {"test": "data", "timestamp": int(time.time())}
        cid = await store.write(valid_checkpoint, name="existence-test")
        await asyncio.sleep(2)

        exists = await store.exists(cid)
        print(f"  ✓ CID {cid[:16]}... exists: {exists}")

        fake_exists = await store.exists("QmTzQ1JRkWErMnqLiM7dNLKkxQXQTsVGUeGiJcPKLUKRj9")
        print(f"  ✓ Fake CID exists: {fake_exists}")

        # Cleanup
        await store.unpin(cid)


async def example_resume_from_checkpoint():
    """Example 4: Resume task from checkpoint (fallback scenario)."""
    print("\n=== Example 4: Resume from Checkpoint ===")

    async with CheckpointStore() as store:
        task_id = f"resumable-task-{int(time.time())}"

        # Simulate primary agent completing 2 out of 4 steps
        print("Primary agent executing steps 0-1...")
        checkpoint_cids = []

        for i in range(2):
            checkpoint = {
                "task_id": task_id,
                "subtask_index": i,
                "agent": "primary_agent",
                "timestamp": int(time.time()),
                "data": {"step": i, "completed": True},
            }
            cid = await store.write(checkpoint, name=f"{task_id}-primary-{i}")
            checkpoint_cids.append(cid)
            print(f"  ✓ Step {i} checkpoint: {cid}")

        # Wait for propagation
        await asyncio.sleep(2)

        # Simulate primary agent failing
        print("\n⚠ Primary agent failed!")

        # Fallback agent resumes from checkpoint
        print("\nFallback agent loading checkpoints...")
        context = {}
        for i, cid in enumerate(checkpoint_cids):
            data = await store.read(cid)
            context[f"step_{i}"] = data["data"]
            print(f"  ✓ Loaded step {i} state: {data['data']}")

        # Fallback agent completes remaining steps
        print("\nFallback agent completing steps 2-3...")
        for i in range(2, 4):
            checkpoint = {
                "task_id": task_id,
                "subtask_index": i,
                "agent": "fallback_agent",
                "timestamp": int(time.time()),
                "data": {
                    "step": i,
                    "completed": True,
                    "resumed_from": 2,
                },
            }
            cid = await store.write(checkpoint, name=f"{task_id}-fallback-{i}")
            checkpoint_cids.append(cid)
            print(f"  ✓ Step {i} checkpoint: {cid}")

        print(f"\n✓ Task completed with {len(checkpoint_cids)} total checkpoints")

        # Cleanup
        print("\nCleaning up...")
        for cid in checkpoint_cids:
            await store.unpin(cid)


async def example_concurrent_operations():
    """Example 5: Concurrent checkpoint operations."""
    print("\n=== Example 5: Concurrent Operations ===")

    async with CheckpointStore() as store:
        # Simulate multiple agents writing checkpoints concurrently
        print("Creating 5 concurrent checkpoints...")

        tasks = []
        for i in range(5):
            checkpoint = {
                "task_id": f"concurrent-task-{i}",
                "subtask_index": 0,
                "agent": f"agent_{i}",
                "timestamp": int(time.time()),
                "data": {"agent_id": i, "status": "completed"},
            }
            task = store.write(checkpoint, name=f"concurrent-{i}")
            tasks.append(task)

        # Execute all writes concurrently
        cids = await asyncio.gather(*tasks)
        print(f"✓ Created {len(cids)} checkpoints concurrently")

        for i, cid in enumerate(cids):
            print(f"  Agent {i}: {cid}")

        # Wait for propagation
        await asyncio.sleep(3)

        # Verify all checkpoints
        print("\nVerifying all checkpoints...")
        for i, cid in enumerate(cids):
            data = await store.read(cid)
            print(f"  ✓ Agent {data['data']['agent_id']}: {data['data']['status']}")

        # Cleanup
        print("\nCleaning up...")
        for cid in cids:
            await store.unpin(cid)


async def main():
    """Run all examples."""
    print("=" * 70)
    print("CAIRN CHECKPOINT EXAMPLES")
    print("=" * 70)

    # Verify PINATA_JWT is set
    if not os.getenv("PINATA_JWT"):
        print("\n❌ ERROR: PINATA_JWT environment variable not set")
        print("Please set it in .env file or export it:")
        print("  export PINATA_JWT='your_jwt_token_here'")
        return

    print(f"\nStarted at: {datetime.now().isoformat()}")

    try:
        # Run all examples
        await example_basic_write_read()
        await example_multi_step_task()
        await example_error_handling()
        await example_resume_from_checkpoint()
        await example_concurrent_operations()

        print("\n" + "=" * 70)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)

    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        raise


if __name__ == "__main__":
    asyncio.run(main())
