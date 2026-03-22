"""
Tests for CLI Utilities
"""

import pytest
from datetime import datetime
from cli.utils import (
    format_address,
    format_wei,
    format_timestamp,
    format_state,
    format_cid,
)
from sdk.types import TaskState


def test_format_address_full():
    """Test full address formatting."""
    address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
    result = format_address(address, short=False)
    assert result == address


def test_format_address_short():
    """Test short address formatting."""
    address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
    result = format_address(address, short=True)
    assert result == "0x742d...bEb0"
    assert len(result) == 13  # 6 + 3 + 4


def test_format_address_empty():
    """Test empty address formatting."""
    assert format_address("") == "N/A"
    assert format_address(None) == "N/A"


def test_format_wei():
    """Test wei to ETH formatting."""
    # 1 ETH
    assert format_wei(10**18) == "1.000000 ETH"

    # 0.1 ETH
    assert format_wei(10**17) == "0.100000 ETH"

    # 0 ETH
    assert format_wei(0) == "0.000000 ETH"

    # Small amount
    assert format_wei(123456789) == "0.000000 ETH"  # Less than 1 microETH


def test_format_timestamp():
    """Test timestamp formatting."""
    # Known timestamp: 2024-01-01 00:00:00 UTC
    timestamp = 1704067200
    result = format_timestamp(timestamp)
    assert "2024-01-01" in result or "2023-12-31" in result  # Account for timezone

    # Zero timestamp
    assert format_timestamp(0) == "N/A"


def test_format_state():
    """Test task state formatting with colors."""
    states = [
        TaskState.RUNNING,
        TaskState.FAILED,
        TaskState.RECOVERING,
        TaskState.RESOLVED,
    ]

    for state in states:
        result = format_state(state)
        assert str(state) in str(result)
        assert result.style is not None  # Has color


def test_format_cid_full():
    """Test full CID formatting."""
    cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
    result = format_cid(cid, short=False)
    assert result == cid


def test_format_cid_short():
    """Test short CID formatting."""
    cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
    result = format_cid(cid, short=True)
    assert result == "QmYwAPJz...PbdG"
    assert len(result) == 15  # 8 + 3 + 4


def test_format_cid_empty():
    """Test empty CID formatting."""
    assert format_cid("") == "N/A"
    assert format_cid(None) == "N/A"


def test_format_cid_short_string():
    """Test CID shorter than threshold."""
    cid = "Qm123"
    result = format_cid(cid, short=True)
    assert result == cid  # Too short to truncate
