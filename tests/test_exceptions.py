"""Tests for CAIRN SDK exceptions."""

import pytest
from sdk.exceptions import (
    CairnError,
    ContractError,
    CheckpointError,
    HeartbeatError,
    TaskNotFoundError,
    InvalidStateError,
    NetworkError,
)


class TestCairnError:
    """Tests for base CairnError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = CairnError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with details."""
        error = CairnError("Failed", details={"code": 500, "reason": "timeout"})
        assert "Details:" in str(error)
        assert error.details["code"] == 500


class TestContractError:
    """Tests for ContractError."""

    def test_contract_error(self):
        """Test contract error creation."""
        error = ContractError(
            "Transaction failed",
            tx_hash="0xabc123",
            revert_reason="Insufficient funds",
        )

        assert error.tx_hash == "0xabc123"
        assert error.revert_reason == "Insufficient funds"
        assert "tx_hash" in error.details

    def test_contract_error_minimal(self):
        """Test contract error with minimal info."""
        error = ContractError("RPC error")
        assert error.tx_hash is None
        assert error.revert_reason is None


class TestCheckpointError:
    """Tests for CheckpointError."""

    def test_checkpoint_error(self):
        """Test checkpoint error creation."""
        error = CheckpointError(
            "Failed to fetch",
            cid="QmXyz123",
            gateway="ipfs.io",
        )

        assert error.cid == "QmXyz123"
        assert error.gateway == "ipfs.io"


class TestTaskNotFoundError:
    """Tests for TaskNotFoundError."""

    def test_task_not_found(self):
        """Test task not found error."""
        task_id = "0x1234567890abcdef"
        error = TaskNotFoundError(task_id)

        assert task_id in str(error)
        assert error.task_id == task_id
        assert error.details["task_id"] == task_id


class TestInvalidStateError:
    """Tests for InvalidStateError."""

    def test_invalid_state(self):
        """Test invalid state error."""
        error = InvalidStateError(
            "Cannot checkpoint in FAILED state",
            task_id="0x1234",
            current_state="FAILED",
            expected_states=["RUNNING", "RECOVERING"],
        )

        assert error.task_id == "0x1234"
        assert error.current_state == "FAILED"
        assert "RUNNING" in error.expected_states


class TestHeartbeatError:
    """Tests for HeartbeatError."""

    def test_heartbeat_error(self):
        """Test heartbeat error."""
        error = HeartbeatError(
            "Heartbeat timeout",
            task_id="0x5678",
            last_heartbeat=1700000000,
        )

        assert error.task_id == "0x5678"
        assert error.last_heartbeat == 1700000000


class TestNetworkError:
    """Tests for NetworkError."""

    def test_network_error(self):
        """Test network error."""
        error = NetworkError(
            "Connection refused",
            url="https://rpc.example.com",
        )

        assert error.url == "https://rpc.example.com"
        assert "url" in error.details
