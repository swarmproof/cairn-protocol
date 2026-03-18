"""
Integration tests for CAIRN SDK.

Tests components working together without external dependencies.
Uses mocked external services but real internal component interactions.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sdk.agent import CairnAgent
from sdk.client import CairnClient
from sdk.checkpoint import CheckpointStore
from sdk.observer import LoggingObserver, CompositeObserver, CairnObserver
from sdk.types import Task, TaskState, CheckpointData
from sdk.exceptions import CairnError, InvalidStateError


# Test data
SAMPLE_TASK_ID = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
SAMPLE_ADDRESS = "0x1111111111111111111111111111111111111111"


class TestAgentClientIntegration:
    """Test CairnAgent and CairnClient working together."""

    @pytest.fixture
    def mock_web3(self):
        """Mock Web3 for client."""
        with patch("sdk.client.AsyncWeb3") as mock_web3_class:
            mock_w3 = MagicMock()
            mock_w3.to_checksum_address.side_effect = lambda x: x
            mock_contract = MagicMock()
            mock_w3.eth.contract.return_value = mock_contract

            mock_account = MagicMock()
            mock_account.address = SAMPLE_ADDRESS
            mock_account.sign_transaction.return_value = MagicMock(
                raw_transaction=b"raw_tx"
            )
            mock_w3.eth.account.from_key.return_value = mock_account
            mock_w3.eth.get_transaction_count = AsyncMock(return_value=1)
            mock_w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")
            mock_w3.eth.wait_for_transaction_receipt = AsyncMock(
                return_value={"status": 1, "logs": [], "blockNumber": 100}
            )

            mock_web3_class.return_value = mock_w3
            mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

            yield mock_w3, mock_contract

    @pytest.fixture
    def real_client(self, mock_web3):
        """Create a real CairnClient with mocked Web3."""
        mock_w3, mock_contract = mock_web3
        client = CairnClient(
            rpc_url="https://sepolia.base.org",
            contract_address="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417",
            private_key="0x" + "a" * 64,
        )
        client._w3 = mock_w3
        client._contract = mock_contract
        client._account = mock_w3.eth.account.from_key("0x" + "a" * 64)
        return client

    @pytest.fixture
    def mock_ipfs(self):
        """Mock CheckpointStore."""
        store = MagicMock(spec=CheckpointStore)
        store.write = AsyncMock(return_value="QmTestCheckpointCid")
        store.read = AsyncMock(return_value={"data": {"result": "previous"}})
        store.close = AsyncMock()
        return store

    @pytest.fixture
    def sample_agent(self):
        """Create a sample agent implementation."""
        class TestAgent:
            def __init__(self):
                self.executed = []

            async def execute_subtask(self, subtask: dict, context: dict) -> dict:
                self.executed.append(subtask)
                return {"status": "completed", "action": subtask.get("action")}

        return TestAgent()

    @pytest.mark.asyncio
    async def test_full_execute_flow(
        self, real_client, mock_ipfs, sample_agent, mock_web3
    ):
        """Test CairnAgent executing through CairnClient."""
        mock_w3, mock_contract = mock_web3

        # Setup task response
        task = Task(
            task_id=SAMPLE_TASK_ID,
            state=TaskState.RUNNING,
            operator=SAMPLE_ADDRESS,
            primary_agent=SAMPLE_ADDRESS,
            fallback_agent=SAMPLE_ADDRESS,
            escrow=10**18,
            heartbeat_interval=60,
            deadline=1700000000,
            primary_checkpoints=0,
            fallback_checkpoints=0,
        )

        mock_contract.functions.getTask.return_value.call = AsyncMock(
            return_value=(
                0,  # state
                SAMPLE_ADDRESS,
                SAMPLE_ADDRESS,
                SAMPLE_ADDRESS,
                10**18,
                60,
                1700000000,
                0,
                0,
                1699999900,
                "QmTaskCid",
            )
        )
        mock_contract.functions.getCheckpoints.return_value.call = AsyncMock(
            return_value=[]
        )
        mock_contract.functions.heartbeat.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        mock_contract.functions.commitCheckpoint.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )

        # Create agent with real components
        agent = CairnAgent(sample_agent, real_client, mock_ipfs)

        subtasks = [
            {"action": "fetch_data"},
            {"action": "process_data"},
            {"action": "store_result"},
        ]

        result = await agent.execute(SAMPLE_TASK_ID, subtasks)

        # Verify execution
        assert result["completed"] == 3
        assert result["total"] == 3
        assert len(sample_agent.executed) == 3

        # Verify checkpoints were written
        assert mock_ipfs.write.call_count == 3

        # Verify checkpoints were committed to contract
        assert mock_contract.functions.commitCheckpoint.call_count == 3

    @pytest.mark.asyncio
    async def test_agent_with_multiple_observers(
        self, real_client, mock_ipfs, sample_agent, mock_web3
    ):
        """Test CairnAgent notifying multiple observers."""
        mock_w3, mock_contract = mock_web3

        # Setup mocks
        mock_contract.functions.getTask.return_value.call = AsyncMock(
            return_value=(
                0, SAMPLE_ADDRESS, SAMPLE_ADDRESS, SAMPLE_ADDRESS,
                10**18, 60, 1700000000, 0, 0, 1699999900, "QmTaskCid",
            )
        )
        mock_contract.functions.getCheckpoints.return_value.call = AsyncMock(return_value=[])
        mock_contract.functions.heartbeat.return_value.build_transaction = AsyncMock(return_value={"nonce": 1})
        mock_contract.functions.commitCheckpoint.return_value.build_transaction = AsyncMock(return_value={"nonce": 1})

        # Create observers
        observer1_events = []
        observer2_events = []

        class TrackingObserver(CairnObserver):
            def __init__(self, events_list):
                self.events = events_list

            async def on_task_submitted(self, task_id, task):
                self.events.append(("submitted", task_id))

            async def on_checkpoint(self, task_id, index, cid):
                self.events.append(("checkpoint", task_id, index))

        agent = CairnAgent(sample_agent, real_client, mock_ipfs)
        agent.add_observer(TrackingObserver(observer1_events))
        agent.add_observer(TrackingObserver(observer2_events))

        await agent.execute(SAMPLE_TASK_ID, [{"action": "test"}])

        # Both observers should receive events
        assert ("submitted", SAMPLE_TASK_ID) in observer1_events
        assert ("submitted", SAMPLE_TASK_ID) in observer2_events
        assert ("checkpoint", SAMPLE_TASK_ID, 0) in observer1_events
        assert ("checkpoint", SAMPLE_TASK_ID, 0) in observer2_events


class TestCheckpointClientIntegration:
    """Test CheckpointStore data flowing through CairnClient."""

    @pytest.mark.asyncio
    async def test_checkpoint_data_format(self):
        """Test checkpoint data is correctly formatted for IPFS."""
        checkpoint = CheckpointData(
            task_id=SAMPLE_TASK_ID,
            subtask_index=0,
            agent=SAMPLE_ADDRESS,
            timestamp=1700000000,
            data={"result": "success", "output": "test"},
        )

        payload = checkpoint.to_ipfs_payload()

        assert payload["task_id"] == SAMPLE_TASK_ID
        assert payload["subtask_index"] == 0
        assert payload["agent"] == SAMPLE_ADDRESS
        assert payload["data"]["result"] == "success"


class TestObserverCompositionIntegration:
    """Test observer composition patterns."""

    @pytest.mark.asyncio
    async def test_composite_with_logging_observer(self, caplog):
        """Test CompositeObserver with LoggingObserver."""
        import logging

        logger = logging.getLogger("test_integration")
        logger.setLevel(logging.DEBUG)

        logging_observer = LoggingObserver(logger=logger)
        composite = CompositeObserver([logging_observer])

        task = Task(
            task_id=SAMPLE_TASK_ID,
            state=TaskState.RUNNING,
            operator=SAMPLE_ADDRESS,
            primary_agent=SAMPLE_ADDRESS,
            fallback_agent=SAMPLE_ADDRESS,
            escrow=10**18,
            heartbeat_interval=60,
            deadline=1700000000,
        )

        with caplog.at_level(logging.INFO):
            await composite.on_task_submitted(SAMPLE_TASK_ID, task)
            await composite.on_checkpoint(SAMPLE_TASK_ID, 0, "QmCid")

        assert "Task submitted" in caplog.text
        assert "Checkpoint 0" in caplog.text

    @pytest.mark.asyncio
    async def test_observer_error_isolation(self):
        """Test that one observer failing doesn't affect others."""
        events = []

        class FailingObserver(CairnObserver):
            async def on_checkpoint(self, task_id, index, cid):
                raise RuntimeError("Observer crashed!")

        class WorkingObserver(CairnObserver):
            async def on_checkpoint(self, task_id, index, cid):
                events.append(("checkpoint", index))

        composite = CompositeObserver([
            FailingObserver(),
            WorkingObserver(),
        ])

        # Should not raise
        await composite.on_checkpoint(SAMPLE_TASK_ID, 5, "QmCid")

        # Working observer should still receive event
        assert ("checkpoint", 5) in events


class TestContextPropagationIntegration:
    """Test context propagation between subtasks."""

    @pytest.fixture
    def mock_components(self):
        """Create mocked components for testing."""
        with patch("sdk.client.AsyncWeb3") as mock_web3_class:
            mock_w3 = MagicMock()
            mock_w3.to_checksum_address.side_effect = lambda x: x
            mock_contract = MagicMock()
            mock_w3.eth.contract.return_value = mock_contract

            mock_account = MagicMock()
            mock_account.address = SAMPLE_ADDRESS
            mock_account.sign_transaction.return_value = MagicMock(raw_transaction=b"tx")
            mock_w3.eth.account.from_key.return_value = mock_account
            mock_w3.eth.get_transaction_count = AsyncMock(return_value=1)
            mock_w3.eth.send_raw_transaction = AsyncMock(return_value=b"hash")
            mock_w3.eth.wait_for_transaction_receipt = AsyncMock(
                return_value={"status": 1, "logs": [], "blockNumber": 100}
            )

            mock_web3_class.return_value = mock_w3
            mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

            mock_contract.functions.getTask.return_value.call = AsyncMock(
                return_value=(0, SAMPLE_ADDRESS, SAMPLE_ADDRESS, SAMPLE_ADDRESS,
                              10**18, 60, 1700000000, 0, 0, 1699999900, "QmCid")
            )
            mock_contract.functions.getCheckpoints.return_value.call = AsyncMock(return_value=[])
            mock_contract.functions.heartbeat.return_value.build_transaction = AsyncMock(return_value={"nonce": 1})
            mock_contract.functions.commitCheckpoint.return_value.build_transaction = AsyncMock(return_value={"nonce": 1})

            client = CairnClient(
                rpc_url="https://sepolia.base.org",
                contract_address="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417",
                private_key="0x" + "a" * 64,
            )
            client._w3 = mock_w3
            client._contract = mock_contract
            client._account = mock_account

            ipfs = MagicMock(spec=CheckpointStore)
            ipfs.write = AsyncMock(return_value="QmCid")
            ipfs.close = AsyncMock()

            yield client, ipfs

    @pytest.mark.asyncio
    async def test_context_passed_between_subtasks(self, mock_components):
        """Test that results from previous subtasks are available in context."""
        client, ipfs = mock_components
        received_contexts = []

        class ContextTrackingAgent:
            async def execute_subtask(self, subtask: dict, context: dict) -> dict:
                received_contexts.append(dict(context))
                return {"value": subtask.get("step", 0) * 10}

        agent = CairnAgent(ContextTrackingAgent(), client, ipfs)

        subtasks = [
            {"step": 1},
            {"step": 2},
            {"step": 3},
        ]

        await agent.execute(SAMPLE_TASK_ID, subtasks)

        # First subtask has empty context
        assert "subtask_0_result" not in received_contexts[0]

        # Second subtask has first result
        assert received_contexts[1].get("subtask_0_result") == {"value": 10}

        # Third subtask has first and second results
        assert received_contexts[2].get("subtask_0_result") == {"value": 10}
        assert received_contexts[2].get("subtask_1_result") == {"value": 20}
