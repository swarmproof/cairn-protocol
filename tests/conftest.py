"""
Pytest configuration and shared fixtures for CAIRN SDK tests.
"""

import pytest

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def sample_task_id() -> str:
    """Sample task ID for testing."""
    return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


@pytest.fixture
def sample_address() -> str:
    """Sample Ethereum address for testing."""
    return "0x1111111111111111111111111111111111111111"


@pytest.fixture
def sample_cid() -> str:
    """Sample IPFS CID for testing."""
    return "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
