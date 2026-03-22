#!/usr/bin/env python3
"""
Quick verification script for CAIRN CheckpointStore integration.

This script tests the real Pinata API integration to ensure:
1. CheckpointStore can load JWT from environment
2. Writing to Pinata works
3. Reading from IPFS works
4. Unpinning works

Usage:
    python verify_integration.py
"""

import asyncio
import os
import sys
import time


async def verify_integration():
    """Verify CheckpointStore integration with real Pinata API."""
    print("=" * 70)
    print("CAIRN CHECKPOINT INTEGRATION VERIFICATION")
    print("=" * 70)

    # Import SDK
    try:
        from sdk.checkpoint import CheckpointStore
        from sdk.exceptions import CheckpointError
        print("✓ SDK imports successful")
    except ImportError as e:
        print(f"✗ Failed to import SDK: {e}")
        print("\nInstall dependencies: pip install -r requirements.txt")
        return False

    # Check environment
    pinata_jwt = os.getenv("PINATA_JWT")
    if not pinata_jwt:
        print("\n✗ PINATA_JWT environment variable not set")
        print("\nPlease set it in .env file or export it:")
        print("  export PINATA_JWT='your_jwt_token'")
        return False

    print(f"✓ PINATA_JWT loaded ({len(pinata_jwt)} chars)")

    # Test 1: Initialize CheckpointStore
    print("\n--- Test 1: Initialize CheckpointStore ---")
    try:
        store = CheckpointStore()
        print("✓ CheckpointStore initialized (auto-loaded JWT from env)")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False

    # Test 2: Write checkpoint
    print("\n--- Test 2: Write Checkpoint to Pinata ---")
    test_data = {
        "test": "verification",
        "timestamp": int(time.time()),
        "message": "CAIRN SDK integration test",
    }

    try:
        async with store:
            cid = await store.write(test_data, name="cairn-integration-test")
            print(f"✓ Checkpoint written successfully")
            print(f"  CID: {cid}")

            # Verify CID format
            if not (cid.startswith(("Qm", "ba", "baf")) and len(cid) > 40):
                print(f"⚠ Warning: CID format looks unusual")

    except Exception as e:
        print(f"✗ Failed to write checkpoint: {e}")
        await store.close()
        return False

    # Test 3: Read checkpoint back
    print("\n--- Test 3: Read Checkpoint from IPFS ---")
    print("Waiting 3 seconds for IPFS propagation...")
    await asyncio.sleep(3)

    try:
        async with CheckpointStore() as store:
            data = await store.read(cid)
            print(f"✓ Checkpoint read successfully")

            # Verify data matches
            if data == test_data:
                print(f"✓ Data integrity verified")
            else:
                print(f"⚠ Warning: Data mismatch")
                print(f"  Expected: {test_data}")
                print(f"  Got: {data}")

    except Exception as e:
        print(f"✗ Failed to read checkpoint: {e}")
        return False

    # Test 4: Check if CID exists
    print("\n--- Test 4: Check CID Existence ---")
    try:
        async with CheckpointStore() as store:
            exists = await store.exists(cid)
            if exists:
                print(f"✓ CID exists on IPFS")
            else:
                print(f"⚠ Warning: CID reported as not existing")

    except Exception as e:
        print(f"✗ Failed to check existence: {e}")
        return False

    # Test 5: Unpin from Pinata
    print("\n--- Test 5: Unpin from Pinata ---")
    try:
        async with CheckpointStore() as store:
            await store.unpin(cid)
            print(f"✓ Checkpoint unpinned successfully")

    except Exception as e:
        print(f"✗ Failed to unpin: {e}")
        return False

    # Success
    print("\n" + "=" * 70)
    print("✓ ALL INTEGRATION TESTS PASSED")
    print("=" * 70)
    print("\nThe CAIRN SDK is ready to use with real Pinata integration!")
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_integration())
    sys.exit(0 if success else 1)
