"""
End-to-End tests for CAIRN SDK.

Tests the full workflow against the deployed contract on Base Sepolia.
These tests require environment variables to be set:
- CAIRN_RPC_URL: Base Sepolia RPC URL
- CAIRN_CONTRACT: Deployed contract address
- PRIVATE_KEY: Wallet private key (with testnet ETH)
- PINATA_JWT: Pinata API JWT

Run with: pytest tests/test_e2e.py -v --run-e2e
"""

import asyncio
import os
import time
import pytest

from sdk.client import CairnClient
from sdk.checkpoint import CheckpointStore
from sdk.agent import CairnAgent
from sdk.observer import LoggingObserver
from sdk.types import TaskState
from sdk.exceptions import ContractError, TaskNotFoundError


# Skip all E2E tests if env vars not set or --run-e2e not passed
def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")


@pytest.fixture(scope="module")
def e2e_enabled():
    """Check if E2E tests should run."""
    required_vars = ["CAIRN_RPC_URL", "CAIRN_CONTRACT", "PRIVATE_KEY", "PINATA_JWT"]
    missing = [v for v in required_vars if not os.getenv(v)]

    if missing:
        pytest.skip(f"E2E tests require env vars: {missing}")

    return True


@pytest.fixture(scope="module")
def cairn_client(e2e_enabled):
    """Create a real CairnClient connected to Base Sepolia."""
    return CairnClient(
        rpc_url=os.getenv("CAIRN_RPC_URL", "https://sepolia.base.org"),
        contract_address=os.getenv("CAIRN_CONTRACT", "0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417"),
        private_key=os.getenv("PRIVATE_KEY"),
    )


@pytest.fixture(scope="module")
def checkpoint_store(e2e_enabled):
    """Create a real CheckpointStore connected to Pinata."""
    return CheckpointStore(pinata_jwt=os.getenv("PINATA_JWT"))


@pytest.fixture
def test_agent():
    """Create a simple test agent."""
    class SimpleAgent:
        def __init__(self):
            self.executed = []

        async def execute_subtask(self, subtask: dict, context: dict) -> dict:
            self.executed.append(subtask)
            await asyncio.sleep(0.1)  # Simulate work
            return {
                "status": "completed",
                "action": subtask.get("action"),
                "timestamp": int(time.time()),
            }

    return SimpleAgent()


@pytest.mark.e2e
class TestE2EConnection:
    """Test basic connectivity to external services."""

    @pytest.mark.asyncio
    async def test_client_connects_to_rpc(self, cairn_client):
        """Test CairnClient can connect to Base Sepolia RPC."""
        is_connected = await cairn_client.is_connected()
        assert is_connected is True

    @pytest.mark.asyncio
    async def test_client_gets_chain_id(self, cairn_client):
        """Test CairnClient can get chain ID."""
        chain_id = await cairn_client.get_chain_id()
        assert chain_id == 84532  # Base Sepolia

    @pytest.mark.asyncio
    async def test_client_reads_protocol_fee(self, cairn_client):
        """Test CairnClient can read contract state."""
        fee = await cairn_client.get_protocol_fee()
        assert fee == 50  # 0.5% = 50 bps

    @pytest.mark.asyncio
    async def test_client_reads_min_escrow(self, cairn_client):
        """Test CairnClient can read min escrow."""
        min_escrow = await cairn_client.get_min_escrow()
        assert min_escrow == 10**15  # 0.001 ETH

    @pytest.mark.asyncio
    async def test_checkpoint_store_write_read(self, checkpoint_store):
        """Test CheckpointStore can write and read from IPFS."""
        async with checkpoint_store:
            test_data = {
                "test": "e2e",
                "timestamp": int(time.time()),
                "value": 42,
            }

            # Write to IPFS
            cid = await checkpoint_store.write(test_data, name="e2e-test")
            assert cid.startswith("Qm") or cid.startswith("bafy")

            # Read back
            read_data = await checkpoint_store.read(cid)
            assert read_data["test"] == "e2e"
            assert read_data["value"] == 42


@pytest.mark.e2e
class TestE2ETaskNotFound:
    """Test error handling for non-existent tasks."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, cairn_client):
        """Test getting a task that doesn't exist."""
        fake_task_id = "0x" + "0" * 64

        with pytest.raises(TaskNotFoundError):
            await cairn_client.get_task(fake_task_id)


@pytest.mark.e2e
class TestE2EFullWorkflow:
    """
    Test full task lifecycle.

    WARNING: These tests cost gas and modify on-chain state.
    Only run with dedicated test wallets.
    """

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Costs gas - enable manually for full E2E testing")
    async def test_submit_task_and_checkpoint(
        self, cairn_client, checkpoint_store, test_agent
    ):
        """
        Test full workflow: submit task, checkpoint, settle.

        This test:
        1. Submits a new task to the contract
        2. Executes subtasks with checkpointing
        3. Verifies checkpoints are stored on IPFS
        4. Verifies checkpoints are committed on-chain
        """
        async with checkpoint_store:
            # Create CAIRN agent
            agent = CairnAgent(test_agent, cairn_client, checkpoint_store)
            agent.add_observer(LoggingObserver())

            # Submit task (costs gas)
            task_id = await cairn_client.submit_task(
                primary_agent=cairn_client.address,
                fallback_agent=cairn_client.address,  # Self as fallback for test
                task_cid="QmE2ETestTaskSpec",
                heartbeat_interval=60,
                deadline=int(time.time()) + 3600,  # 1 hour
                escrow=10**16,  # 0.01 ETH
            )

            assert task_id.startswith("0x")

            # Verify task exists
            task = await cairn_client.get_task(task_id)
            assert task.state == TaskState.RUNNING
            assert task.primary_checkpoints == 0

            # Execute with checkpointing
            subtasks = [
                {"action": "step1"},
                {"action": "step2"},
            ]

            async with agent:
                result = await agent.execute(task_id, subtasks)

            assert result["completed"] == 2

            # Verify checkpoints on-chain
            updated_task = await cairn_client.get_task(task_id)
            assert updated_task.primary_checkpoints == 2
            assert len(updated_task.checkpoint_cids) == 2

            # Verify checkpoints on IPFS
            for cid in updated_task.checkpoint_cids:
                data = await checkpoint_store.read(cid)
                assert "task_id" in data
                assert "subtask_index" in data


@pytest.mark.e2e
class TestE2EAgentIntegration:
    """Test CairnAgent with real services (read-only operations)."""

    @pytest.mark.asyncio
    async def test_agent_context_manager(
        self, cairn_client, checkpoint_store, test_agent
    ):
        """Test CairnAgent async context manager lifecycle."""
        async with checkpoint_store:
            agent = CairnAgent(test_agent, cairn_client, checkpoint_store)

            async with agent:
                # Agent should be ready
                assert agent._stopped is False

            # After exit, agent should be stopped
            assert agent._stopped is True

    @pytest.mark.asyncio
    async def test_agent_observer_registration(
        self, cairn_client, checkpoint_store, test_agent
    ):
        """Test observer registration and removal."""
        async with checkpoint_store:
            agent = CairnAgent(test_agent, cairn_client, checkpoint_store)
            observer = LoggingObserver()

            # Add observer
            agent.add_observer(observer)
            assert observer in agent._observers

            # Remove observer
            agent.remove_observer(observer)
            assert observer not in agent._observers


# Pytest hook to add --run-e2e option
def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests against deployed contract",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-e2e"):
        skip_e2e = pytest.mark.skip(reason="Need --run-e2e option to run")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)
