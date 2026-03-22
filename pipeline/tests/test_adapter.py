"""
Tests for BonfiresAdapter.
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from pipeline.adapter import BonfiresAdapter
from pipeline.records import FailureClass, FailureType


class TestBonfiresAdapter:
    """Tests for BonfiresAdapter."""

    @pytest.fixture
    def mock_bonfires(self):
        """Mock Bonfires client."""
        client = AsyncMock()
        client.write_failure_episode = AsyncMock(return_value="episode-uuid-failure-123")
        client.write_resolution_episode = AsyncMock(return_value="episode-uuid-resolution-456")
        return client

    @pytest.fixture
    def mock_ipfs(self):
        """Mock IPFS client."""
        client = AsyncMock()
        client.write = AsyncMock(return_value="QmTestCID123")
        return client

    @pytest.fixture
    def adapter(self, mock_bonfires, mock_ipfs):
        """Create adapter with mocks."""
        return BonfiresAdapter(mock_bonfires, mock_ipfs)

    @pytest.mark.asyncio
    async def test_on_task_failed(self, adapter, mock_ipfs, mock_bonfires):
        """Test handling TaskFailed event."""
        event = {
            "task_id": "0x" + "a" * 64,
            "agent": "0x1234567890123456789012345678901234567890",
            "failure_class": 1,  # RESOURCE
            "checkpoint_count": 3,
            "block_number": 100,
            "timestamp": int(time.time()),
            "task_type": "defi.price_fetch",
            "total_checkpoints_expected": 5,
        }

        cid = await adapter.on_task_failed(event)

        # Verify IPFS was called
        assert mock_ipfs.write.called
        call_args = mock_ipfs.write.call_args
        assert call_args[1]["name"].startswith("failure-")

        # Verify Bonfires episode was written
        assert mock_bonfires.write_failure_episode.called
        call_kwargs = mock_bonfires.write_failure_episode.call_args[1]
        assert call_kwargs["task_id"] == "0x" + "a" * 64
        assert call_kwargs["failure_class"] == "RESOURCE"
        assert call_kwargs["checkpoint_count"] == 3
        assert cid == "QmTestCID123"

    @pytest.mark.asyncio
    async def test_on_task_resolved_with_recovery(self, adapter, mock_ipfs, mock_bonfires):
        """Test handling TaskResolved event with recovery."""
        event = {
            "task_id": "0x" + "b" * 64,
            "primary_agent": "0x1111111111111111111111111111111111111111",
            "fallback_agent": "0x2222222222222222222222222222222222222222",
            "primary_checkpoints": 3,
            "fallback_checkpoints": 2,
            "primary_payout": 2_000_000_000_000_000,  # 0.002 ETH
            "fallback_payout": 1_500_000_000_000_000,  # 0.0015 ETH
            "protocol_fee": 100_000_000_000_000,  # 0.0001 ETH
            "block_number": 200,
            "timestamp": int(time.time()),
            "task_type": "defi.price_fetch",
        }

        cid = await adapter.on_task_resolved(event)

        # Verify IPFS was called
        assert mock_ipfs.write.called
        call_args = mock_ipfs.write.call_args
        assert call_args[1]["name"].startswith("resolution-")

        # Verify Bonfires resolution episode was written
        assert mock_bonfires.write_resolution_episode.called
        call_kwargs = mock_bonfires.write_resolution_episode.call_args[1]
        assert call_kwargs["task_id"] == "0x" + "b" * 64
        assert call_kwargs["recovery_attempted"] is True
        assert call_kwargs["original_checkpoints"] == 3
        assert call_kwargs["fallback_checkpoints"] == 2
        assert cid == "QmTestCID123"

    @pytest.mark.asyncio
    async def test_on_task_resolved_without_recovery(self, adapter, mock_ipfs, mock_bonfires):
        """Test handling TaskResolved event without recovery."""
        event = {
            "task_id": "0x" + "c" * 64,
            "primary_agent": "0x1111111111111111111111111111111111111111",
            "fallback_agent": "0x0000000000000000000000000000000000000000",  # Zero address
            "primary_checkpoints": 5,
            "fallback_checkpoints": 0,
            "primary_payout": 3_000_000_000_000_000,  # 0.003 ETH
            "fallback_payout": 0,
            "protocol_fee": 100_000_000_000_000,
            "block_number": 300,
            "timestamp": int(time.time()),
            "task_type": "defi.swap",
        }

        cid = await adapter.on_task_resolved(event)

        assert mock_ipfs.write.called
        # Verify Bonfires resolution episode was written without recovery
        assert mock_bonfires.write_resolution_episode.called
        call_kwargs = mock_bonfires.write_resolution_episode.call_args[1]
        assert call_kwargs["recovery_attempted"] is False
        assert call_kwargs["fallback_agent"] is None
        assert cid == "QmTestCID123"

    def test_map_failure_class(self, adapter):
        """Test mapping failure class enum."""
        assert adapter._map_failure_class(0) == FailureClass.LIVENESS
        assert adapter._map_failure_class(1) == FailureClass.RESOURCE
        assert adapter._map_failure_class(2) == FailureClass.EXECUTION
        assert adapter._map_failure_class(3) == FailureClass.DEADLINE

    def test_infer_failure_type_rate_limit(self, adapter):
        """Test inferring RATE_LIMIT failure type."""
        failure_type = adapter._infer_failure_type(
            FailureClass.RESOURCE,
            {"http_status": 429}
        )
        assert failure_type == FailureType.RATE_LIMIT

    def test_infer_failure_type_api_unavailable(self, adapter):
        """Test inferring API_UNAVAILABLE failure type."""
        failure_type = adapter._infer_failure_type(
            FailureClass.RESOURCE,
            {"http_status": 503}
        )
        assert failure_type == FailureType.API_UNAVAILABLE

    def test_calculate_recovery_score(self, adapter):
        """Test recovery score calculation."""
        # High recovery likelihood
        score = adapter._calculate_recovery_score(
            checkpoint_count=8,
            total_checkpoints=10,
            budget_remaining=0.8,
            deadline_remaining=0.7,
        )
        assert score > 0.7

        # Low recovery likelihood
        score = adapter._calculate_recovery_score(
            checkpoint_count=1,
            total_checkpoints=10,
            budget_remaining=0.1,
            deadline_remaining=0.05,
        )
        assert score < 0.3

    def test_get_statistics(self, adapter):
        """Test getting adapter statistics."""
        stats = adapter.get_statistics()

        assert "total_records" in stats
        assert "failure_count" in stats
        assert "resolution_count" in stats
        assert "ready_for_detection" in stats
