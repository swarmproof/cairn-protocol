"""
Tests for failure and resolution record schemas.
"""

import pytest
import time
from pipeline.records import (
    FailureRecord,
    ResolutionRecord,
    FailureClass,
    FailureType,
    AgentResolutionInfo,
)


class TestFailureRecord:
    """Tests for FailureRecord."""

    def test_create_valid_failure_record(self):
        """Test creating a valid failure record."""
        record = FailureRecord(
            task_id="0x" + "a" * 64,
            agent_id="erc8004://base/0x1234567890123456789012345678901234567890",
            task_type="defi.price_fetch",
            failure_class=FailureClass.RESOURCE,
            failure_type=FailureType.RATE_LIMIT,
            failure_details={"http_status": 429, "api": "coingecko"},
            checkpoint_count_at_failure=3,
            total_checkpoints_expected=5,
            cost_at_failure="0.0023",
            budget_remaining_pct=0.42,
            deadline_remaining_pct=0.31,
            recovery_score=0.71,
            block_number=18492031,
            timestamp=int(time.time()),
        )

        assert record.record_type == "failure"
        assert record.version == "1.0"
        assert record.failure_class == FailureClass.RESOURCE
        assert record.failure_type == FailureType.RATE_LIMIT
        assert record.checkpoint_count_at_failure == 3

    def test_invalid_task_id_format(self):
        """Test that invalid task_id format raises error."""
        with pytest.raises(ValueError, match="task_id must start with 0x"):
            FailureRecord(
                task_id="invalid",
                agent_id="erc8004://base/0x1234567890123456789012345678901234567890",
                task_type="test",
                failure_class=FailureClass.LIVENESS,
                failure_type=FailureType.HEARTBEAT_TIMEOUT,
                checkpoint_count_at_failure=0,
                total_checkpoints_expected=5,
                cost_at_failure="0.001",
                budget_remaining_pct=1.0,
                deadline_remaining_pct=1.0,
                recovery_score=0.5,
                block_number=1,
                timestamp=int(time.time()),
            )

    def test_invalid_agent_id_format(self):
        """Test that invalid agent_id format raises error."""
        with pytest.raises(ValueError, match="agent_id must follow ERC8004 format"):
            FailureRecord(
                task_id="0x" + "a" * 64,
                agent_id="invalid-agent-id",
                task_type="test",
                failure_class=FailureClass.LIVENESS,
                failure_type=FailureType.HEARTBEAT_TIMEOUT,
                checkpoint_count_at_failure=0,
                total_checkpoints_expected=5,
                cost_at_failure="0.001",
                budget_remaining_pct=1.0,
                deadline_remaining_pct=1.0,
                recovery_score=0.5,
                block_number=1,
                timestamp=int(time.time()),
            )

    def test_to_ipfs_payload(self):
        """Test converting to IPFS payload."""
        record = FailureRecord(
            task_id="0x" + "a" * 64,
            agent_id="erc8004://base/0x1234567890123456789012345678901234567890",
            task_type="test",
            failure_class=FailureClass.RESOURCE,
            failure_type=FailureType.RATE_LIMIT,
            checkpoint_count_at_failure=3,
            total_checkpoints_expected=5,
            cost_at_failure="0.001",
            budget_remaining_pct=0.5,
            deadline_remaining_pct=0.5,
            recovery_score=0.7,
            block_number=100,
            timestamp=int(time.time()),
        )

        payload = record.to_ipfs_payload()

        assert payload["record_type"] == "failure"
        assert payload["task_id"] == "0x" + "a" * 64
        assert payload["failure_class"] == "RESOURCE"

    def test_to_bonfires_record(self):
        """Test converting to Bonfires format."""
        record = FailureRecord(
            task_id="0x" + "a" * 64,
            agent_id="erc8004://base/0x1234567890123456789012345678901234567890",
            task_type="test",
            failure_class=FailureClass.EXECUTION,
            failure_type=FailureType.LOGIC_ERROR,
            checkpoint_count_at_failure=2,
            total_checkpoints_expected=5,
            cost_at_failure="0.001",
            budget_remaining_pct=0.6,
            deadline_remaining_pct=0.4,
            recovery_score=0.8,
            block_number=200,
            timestamp=int(time.time()),
        )

        bonfires_data = record.to_bonfires_record()

        assert bonfires_data["task_id"] == "0x" + "a" * 64
        assert bonfires_data["failure_class"] == "EXECUTION"
        assert bonfires_data["checkpoint_count"] == 2
        assert "metadata" in bonfires_data


class TestResolutionRecord:
    """Tests for ResolutionRecord."""

    def test_create_valid_resolution_record(self):
        """Test creating a valid resolution record."""
        record = ResolutionRecord(
            task_id="0x" + "b" * 64,
            states_traversed=["RUNNING", "FAILED", "RECOVERING", "RESOLVED"],
            recovery_attempted=True,
            recovery_successful=True,
            original_agent=AgentResolutionInfo(
                id="erc8004://base/0x1111111111111111111111111111111111111111",
                checkpoint_count=3,
                cost="0.0023",
                payout="0.0024",
            ),
            fallback_agent=AgentResolutionInfo(
                id="erc8004://base/0x2222222222222222222222222222222222222222",
                checkpoint_count=2,
                cost="0.0018",
                payout="0.0016",
            ),
            task_type="defi.price_fetch",
            total_cost="0.0041",
            total_duration_blocks=847,
            escrow_total="0.01",
            protocol_fee="0.00005",
            block_number=18493012,
            timestamp=int(time.time()),
        )

        assert record.record_type == "resolution"
        assert record.recovery_attempted is True
        assert record.recovery_successful is True
        assert len(record.states_traversed) == 4

    def test_resolution_without_fallback(self):
        """Test resolution record without fallback agent."""
        record = ResolutionRecord(
            task_id="0x" + "c" * 64,
            states_traversed=["RUNNING", "RESOLVED"],
            recovery_attempted=False,
            recovery_successful=False,
            original_agent=AgentResolutionInfo(
                id="erc8004://base/0x1111111111111111111111111111111111111111",
                checkpoint_count=5,
                cost="0.005",
                payout="0.005",
            ),
            fallback_agent=None,
            task_type="test",
            total_cost="0.005",
            total_duration_blocks=100,
            escrow_total="0.006",
            protocol_fee="0.0001",
            block_number=1000,
            timestamp=int(time.time()),
        )

        assert record.fallback_agent is None
        assert record.recovery_attempted is False

    def test_to_bonfires_record_with_fallback(self):
        """Test converting to Bonfires format with fallback."""
        record = ResolutionRecord(
            task_id="0x" + "d" * 64,
            states_traversed=["RUNNING", "FAILED", "RECOVERING", "RESOLVED"],
            recovery_attempted=True,
            recovery_successful=True,
            original_agent=AgentResolutionInfo(
                id="erc8004://base/0x1111111111111111111111111111111111111111",
                checkpoint_count=3,
                cost="0.003",
                payout="0.003",
            ),
            fallback_agent=AgentResolutionInfo(
                id="erc8004://base/0x2222222222222222222222222222222222222222",
                checkpoint_count=2,
                cost="0.002",
                payout="0.002",
            ),
            task_type="test",
            total_cost="0.005",
            total_duration_blocks=500,
            escrow_total="0.006",
            protocol_fee="0.0001",
            failure_record_cid="QmTest123",
            block_number=2000,
            timestamp=int(time.time()),
        )

        bonfires_data = record.to_bonfires_record()

        assert bonfires_data["recovery_attempted"] is True
        assert bonfires_data["recovery_successful"] is True
        assert bonfires_data["metadata"]["fallback_agent"] is not None
        assert bonfires_data["metadata"]["failure_record_cid"] == "QmTest123"
