"""
Pytest configuration for CAIRN SDK tests.
"""

import os
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires PINATA_JWT)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture
def pinata_jwt():
    """Get Pinata JWT from environment."""
    jwt = os.getenv("PINATA_JWT")
    if not jwt:
        pytest.skip("PINATA_JWT not set - skipping integration test")
    return jwt


@pytest.fixture
def sample_checkpoint_data():
    """Sample checkpoint data for testing."""
    return {
        "task_id": "test-task-123",
        "subtask_index": 0,
        "agent": "0x1234567890123456789012345678901234567890",
        "timestamp": 1710000000,
        "data": {
            "result": "success",
            "metrics": {
                "duration_ms": 1234,
                "gas_used": 50000,
            },
        },
    }
