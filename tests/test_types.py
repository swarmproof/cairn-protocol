"""Tests for CAIRN SDK types."""

import pytest
from sdk.types import (
    Task,
    TaskState,
    TaskSpec,
    CheckpointData,
    SettlementInfo,
)


class TestTaskState:
    """Tests for TaskState enum."""

    def test_state_values(self):
        """Test state enum values match contract."""
        assert TaskState.RUNNING == 0
        assert TaskState.FAILED == 1
        assert TaskState.RECOVERING == 2
        assert TaskState.RESOLVED == 3

    def test_state_str(self):
        """Test state string representation."""
        assert str(TaskState.RUNNING) == "RUNNING"
        assert str(TaskState.FAILED) == "FAILED"


class TestTask:
    """Tests for Task model."""

    @pytest.fixture
    def sample_task(self) -> Task:
        """Create a sample task."""
        return Task(
            task_id="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            state=TaskState.RUNNING,
            operator="0x1111111111111111111111111111111111111111",
            primary_agent="0x2222222222222222222222222222222222222222",
            fallback_agent="0x3333333333333333333333333333333333333333",
            escrow=10**18,
            heartbeat_interval=60,
            deadline=1700000000,
            primary_checkpoints=3,
            fallback_checkpoints=2,
            last_heartbeat=1699999900,
            checkpoint_cids=["Qm123", "Qm456", "Qm789"],
            task_cid="QmTaskSpec",
        )

    def test_task_creation(self, sample_task: Task):
        """Test task model creation."""
        assert sample_task.state == TaskState.RUNNING
        assert sample_task.escrow == 10**18
        assert len(sample_task.checkpoint_cids) == 3

    def test_is_active(self, sample_task: Task):
        """Test is_active property."""
        assert sample_task.is_active is True

        failed_task = sample_task.model_copy(update={"state": TaskState.FAILED})
        assert failed_task.is_active is False

        recovering_task = sample_task.model_copy(update={"state": TaskState.RECOVERING})
        assert recovering_task.is_active is True

    def test_is_terminal(self, sample_task: Task):
        """Test is_terminal property."""
        assert sample_task.is_terminal is False

        resolved_task = sample_task.model_copy(update={"state": TaskState.RESOLVED})
        assert resolved_task.is_terminal is True

    def test_total_checkpoints(self, sample_task: Task):
        """Test total_checkpoints property."""
        assert sample_task.total_checkpoints == 5  # 3 + 2

    def test_task_immutable(self, sample_task: Task):
        """Test that Task is immutable (frozen)."""
        with pytest.raises(Exception):  # pydantic.ValidationError or AttributeError
            sample_task.state = TaskState.FAILED


class TestCheckpointData:
    """Tests for CheckpointData model."""

    def test_checkpoint_creation(self):
        """Test checkpoint data creation."""
        checkpoint = CheckpointData(
            task_id="0x1234",
            subtask_index=0,
            agent="0x5555",
            timestamp=1700000000,
            data={"result": "success"},
        )

        assert checkpoint.subtask_index == 0
        assert checkpoint.data["result"] == "success"

    def test_to_ipfs_payload(self):
        """Test IPFS payload conversion."""
        checkpoint = CheckpointData(
            task_id="0x1234",
            subtask_index=2,
            agent="0x5555",
            timestamp=1700000000,
            data={"key": "value"},
            metadata={"extra": "info"},
        )

        payload = checkpoint.to_ipfs_payload()

        assert payload["task_id"] == "0x1234"
        assert payload["subtask_index"] == 2
        assert payload["version"] == "1.0"
        assert payload["data"]["key"] == "value"
        assert payload["metadata"]["extra"] == "info"


class TestSettlementInfo:
    """Tests for SettlementInfo model."""

    def test_settlement_creation(self):
        """Test settlement info creation."""
        settlement = SettlementInfo(
            task_id="0x1234",
            primary_agent="0x2222",
            fallback_agent="0x3333",
            primary_share=7 * 10**17,  # 0.7 ETH
            fallback_share=3 * 10**17,  # 0.3 ETH
            protocol_fee=5 * 10**15,    # 0.005 ETH
            primary_checkpoints=7,
            fallback_checkpoints=3,
            resolved_at=1700000000,
        )

        assert settlement.primary_share == 7 * 10**17
        assert settlement.fallback_share == 3 * 10**17

    def test_total_escrow(self):
        """Test total_escrow property."""
        settlement = SettlementInfo(
            task_id="0x1234",
            primary_agent="0x2222",
            fallback_agent="0x3333",
            primary_share=10**18,
            fallback_share=5 * 10**17,
            protocol_fee=25 * 10**15,
            primary_checkpoints=5,
            fallback_checkpoints=5,
            resolved_at=1700000000,
        )

        expected_total = 10**18 + 5 * 10**17 + 25 * 10**15
        assert settlement.total_escrow == expected_total


class TestTaskSpec:
    """Tests for TaskSpec model."""

    def test_task_spec_creation(self):
        """Test task spec creation."""
        spec = TaskSpec(
            description="Rebalance portfolio",
            subtasks=[
                {"action": "fetch_prices"},
                {"action": "calculate_weights"},
                {"action": "execute_trades"},
            ],
            output_schema={"type": "object"},
            metadata={"priority": "high"},
        )

        assert len(spec.subtasks) == 3
        assert spec.metadata["priority"] == "high"
