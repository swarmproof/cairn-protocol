"""Tests for CAIRN SDK CairnClient."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from web3.types import TxReceipt

from sdk.client import CairnClient, _load_abi
from sdk.types import Task, TaskState, SettlementInfo
from sdk.exceptions import ContractError, TaskNotFoundError


# Sample test data
SAMPLE_TASK_ID = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
SAMPLE_ADDRESS = "0x1111111111111111111111111111111111111111"
SAMPLE_RPC_URL = "https://sepolia.base.org"
SAMPLE_CONTRACT_ADDRESS = "0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417"
SAMPLE_PRIVATE_KEY = "0x" + "a" * 64


class TestLoadAbi:
    """Tests for ABI loading."""

    def test_load_abi_success(self):
        """Test ABI loads successfully."""
        abi = _load_abi()
        assert isinstance(abi, list)
        assert len(abi) > 0

    def test_load_abi_has_required_functions(self):
        """Test ABI contains required functions."""
        abi = _load_abi()
        function_names = [item.get("name") for item in abi if item.get("type") == "function"]

        required_functions = [
            "submitTask",
            "heartbeat",
            "commitCheckpoint",
            "checkLiveness",
            "settle",
            "getTask",
            "getCheckpoints",
        ]

        for func in required_functions:
            assert func in function_names, f"Missing function: {func}"


class TestCairnClientInit:
    """Tests for CairnClient initialization."""

    @patch("sdk.client.AsyncWeb3")
    def test_init_with_private_key(self, mock_web3_class):
        """Test initialization with private key."""
        mock_w3 = MagicMock()
        mock_w3.to_checksum_address.return_value = SAMPLE_CONTRACT_ADDRESS
        mock_w3.eth.contract.return_value = MagicMock()
        mock_w3.eth.account.from_key.return_value = MagicMock(address=SAMPLE_ADDRESS)
        mock_web3_class.return_value = mock_w3
        mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

        client = CairnClient(
            rpc_url=SAMPLE_RPC_URL,
            contract_address=SAMPLE_CONTRACT_ADDRESS,
            private_key=SAMPLE_PRIVATE_KEY,
        )

        assert client.contract_address == SAMPLE_CONTRACT_ADDRESS
        assert client.address == SAMPLE_ADDRESS

    @patch("sdk.client.AsyncWeb3")
    def test_init_without_private_key(self, mock_web3_class):
        """Test initialization without private key (read-only)."""
        mock_w3 = MagicMock()
        mock_w3.to_checksum_address.return_value = SAMPLE_CONTRACT_ADDRESS
        mock_w3.eth.contract.return_value = MagicMock()
        mock_web3_class.return_value = mock_w3
        mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

        client = CairnClient(
            rpc_url=SAMPLE_RPC_URL,
            contract_address=SAMPLE_CONTRACT_ADDRESS,
        )

        assert client.address is None
        assert client.contract_address == SAMPLE_CONTRACT_ADDRESS


class TestCairnClientReadMethods:
    """Tests for CairnClient read methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing."""
        with patch("sdk.client.AsyncWeb3") as mock_web3_class:
            mock_w3 = MagicMock()
            mock_w3.to_checksum_address.return_value = SAMPLE_CONTRACT_ADDRESS
            mock_contract = MagicMock()
            mock_w3.eth.contract.return_value = mock_contract
            mock_web3_class.return_value = mock_w3
            mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

            client = CairnClient(
                rpc_url=SAMPLE_RPC_URL,
                contract_address=SAMPLE_CONTRACT_ADDRESS,
            )
            client._contract = mock_contract
            client._w3 = mock_w3
            yield client

    @pytest.mark.asyncio
    async def test_is_connected_true(self, mock_client):
        """Test is_connected returns True when connected."""
        mock_client._w3.is_connected = AsyncMock(return_value=True)

        result = await mock_client.is_connected()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_connected_false_on_exception(self, mock_client):
        """Test is_connected returns False on exception."""
        mock_client._w3.is_connected = AsyncMock(side_effect=Exception("Connection error"))

        result = await mock_client.is_connected()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_chain_id(self, mock_client):
        """Test get_chain_id returns chain ID."""
        # chain_id is an awaitable property in AsyncWeb3
        mock_client._w3.eth.chain_id = asyncio.coroutine(lambda: 84532)()

        result = await mock_client.get_chain_id()

        assert result == 84532

    @pytest.mark.asyncio
    async def test_get_task_success(self, mock_client):
        """Test get_task returns task data."""
        # Mock contract call response
        mock_result = (
            0,  # state (RUNNING)
            SAMPLE_ADDRESS,  # operator
            SAMPLE_ADDRESS,  # primary_agent
            SAMPLE_ADDRESS,  # fallback_agent
            10**18,  # escrow
            60,  # heartbeat_interval
            1700000000,  # deadline
            2,  # primary_checkpoints
            0,  # fallback_checkpoints
            1699999900,  # last_heartbeat
            "QmTaskCid",  # task_cid
        )

        mock_client._contract.functions.getTask.return_value.call = AsyncMock(return_value=mock_result)
        mock_client._contract.functions.getCheckpoints.return_value.call = AsyncMock(return_value=["QmCid1", "QmCid2"])

        task = await mock_client.get_task(SAMPLE_TASK_ID)

        assert task.task_id == SAMPLE_TASK_ID
        assert task.state == TaskState.RUNNING
        assert task.escrow == 10**18
        assert len(task.checkpoint_cids) == 2

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, mock_client):
        """Test get_task raises TaskNotFoundError for non-existent task."""
        mock_result = (
            0,  # state
            "0x0000000000000000000000000000000000000000",  # zero address = not found
            "0x0000000000000000000000000000000000000000",
            "0x0000000000000000000000000000000000000000",
            0, 0, 0, 0, 0, 0, "",
        )

        mock_client._contract.functions.getTask.return_value.call = AsyncMock(return_value=mock_result)

        with pytest.raises(TaskNotFoundError):
            await mock_client.get_task(SAMPLE_TASK_ID)

    @pytest.mark.asyncio
    async def test_get_checkpoints(self, mock_client):
        """Test get_checkpoints returns list of CIDs."""
        mock_client._contract.functions.getCheckpoints.return_value.call = AsyncMock(
            return_value=["QmCid1", "QmCid2", "QmCid3"]
        )

        cids = await mock_client.get_checkpoints(SAMPLE_TASK_ID)

        assert cids == ["QmCid1", "QmCid2", "QmCid3"]

    @pytest.mark.asyncio
    async def test_get_protocol_fee(self, mock_client):
        """Test get_protocol_fee returns fee in basis points."""
        mock_client._contract.functions.protocolFeeBps.return_value.call = AsyncMock(return_value=250)

        fee = await mock_client.get_protocol_fee()

        assert fee == 250  # 2.5%

    @pytest.mark.asyncio
    async def test_get_min_escrow(self, mock_client):
        """Test get_min_escrow returns minimum escrow."""
        mock_client._contract.functions.minEscrow.return_value.call = AsyncMock(return_value=10**16)

        min_escrow = await mock_client.get_min_escrow()

        assert min_escrow == 10**16  # 0.01 ETH

    @pytest.mark.asyncio
    async def test_get_min_heartbeat_interval(self, mock_client):
        """Test get_min_heartbeat_interval returns interval."""
        mock_client._contract.functions.minHeartbeatInterval.return_value.call = AsyncMock(return_value=30)

        interval = await mock_client.get_min_heartbeat_interval()

        assert interval == 30


class TestCairnClientWriteMethods:
    """Tests for CairnClient write methods."""

    @pytest.fixture
    def mock_client_with_signer(self):
        """Create a mock client with signer for write operations."""
        with patch("sdk.client.AsyncWeb3") as mock_web3_class:
            mock_w3 = MagicMock()
            mock_w3.to_checksum_address.return_value = SAMPLE_CONTRACT_ADDRESS
            mock_contract = MagicMock()
            mock_w3.eth.contract.return_value = mock_contract

            mock_account = MagicMock()
            mock_account.address = SAMPLE_ADDRESS
            mock_account.sign_transaction.return_value = MagicMock(
                raw_transaction=b"raw_tx_bytes"
            )
            mock_w3.eth.account.from_key.return_value = mock_account

            mock_web3_class.return_value = mock_w3
            mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

            client = CairnClient(
                rpc_url=SAMPLE_RPC_URL,
                contract_address=SAMPLE_CONTRACT_ADDRESS,
                private_key=SAMPLE_PRIVATE_KEY,
            )
            client._contract = mock_contract
            client._w3 = mock_w3
            client._account = mock_account
            yield client

    @pytest.mark.asyncio
    async def test_require_signer_without_key(self):
        """Test write operations fail without private key."""
        with patch("sdk.client.AsyncWeb3") as mock_web3_class:
            mock_w3 = MagicMock()
            mock_w3.to_checksum_address.return_value = SAMPLE_CONTRACT_ADDRESS
            mock_w3.eth.contract.return_value = MagicMock()
            mock_web3_class.return_value = mock_w3
            mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

            client = CairnClient(
                rpc_url=SAMPLE_RPC_URL,
                contract_address=SAMPLE_CONTRACT_ADDRESS,
            )

            with pytest.raises(ContractError, match="Private key required"):
                await client.heartbeat(SAMPLE_TASK_ID)

    @pytest.mark.asyncio
    async def test_heartbeat_success(self, mock_client_with_signer):
        """Test heartbeat sends transaction successfully."""
        client = mock_client_with_signer

        # Mock transaction flow
        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.heartbeat.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")
        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 1, "blockNumber": 100}
        )

        receipt = await client.heartbeat(SAMPLE_TASK_ID)

        assert receipt["status"] == 1

    @pytest.mark.asyncio
    async def test_heartbeat_reverted(self, mock_client_with_signer):
        """Test heartbeat raises error on revert."""
        client = mock_client_with_signer

        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.heartbeat.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")
        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 0, "blockNumber": 100}  # status=0 means reverted
        )

        with pytest.raises(ContractError, match="reverted"):
            await client.heartbeat(SAMPLE_TASK_ID)

    @pytest.mark.asyncio
    async def test_commit_checkpoint_success(self, mock_client_with_signer):
        """Test commit_checkpoint sends transaction successfully."""
        client = mock_client_with_signer

        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.commitCheckpoint.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")
        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 1, "blockNumber": 100}
        )

        receipt = await client.commit_checkpoint(SAMPLE_TASK_ID, "QmTestCid")

        assert receipt["status"] == 1

    @pytest.mark.asyncio
    async def test_fail_task_success(self, mock_client_with_signer):
        """Test fail_task sends transaction successfully."""
        client = mock_client_with_signer

        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.failTask.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")
        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 1, "blockNumber": 100}
        )

        receipt = await client.fail_task(SAMPLE_TASK_ID)

        assert receipt["status"] == 1

    @pytest.mark.asyncio
    async def test_recover_task_success(self, mock_client_with_signer):
        """Test recover_task sends transaction successfully."""
        client = mock_client_with_signer

        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.recoverTask.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")
        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 1, "blockNumber": 100}
        )

        receipt = await client.recover_task(SAMPLE_TASK_ID)

        assert receipt["status"] == 1


class TestCairnClientSubmitAndSettle:
    """Tests for CairnClient submit_task and settle methods."""

    @pytest.fixture
    def mock_client_with_signer(self):
        """Create a mock client with signer for write operations."""
        with patch("sdk.client.AsyncWeb3") as mock_web3_class:
            mock_w3 = MagicMock()
            mock_w3.to_checksum_address.side_effect = lambda x: x
            mock_contract = MagicMock()
            mock_w3.eth.contract.return_value = mock_contract

            mock_account = MagicMock()
            mock_account.address = SAMPLE_ADDRESS
            mock_account.sign_transaction.return_value = MagicMock(
                raw_transaction=b"raw_tx_bytes"
            )
            mock_w3.eth.account.from_key.return_value = mock_account

            mock_web3_class.return_value = mock_w3
            mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

            client = CairnClient(
                rpc_url=SAMPLE_RPC_URL,
                contract_address=SAMPLE_CONTRACT_ADDRESS,
                private_key=SAMPLE_PRIVATE_KEY,
            )
            client._contract = mock_contract
            client._w3 = mock_w3
            client._account = mock_account
            yield client

    @pytest.mark.asyncio
    async def test_submit_task_success(self, mock_client_with_signer):
        """Test submit_task sends transaction and returns task_id."""
        client = mock_client_with_signer

        # Mock transaction flow
        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.submitTask.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1, "value": 10**17}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")

        # Mock receipt with TaskSubmitted event
        task_id_bytes = bytes.fromhex(SAMPLE_TASK_ID.replace("0x", ""))
        mock_event = MagicMock()
        mock_event.__getitem__ = lambda self, key: {"taskId": task_id_bytes} if key == "args" else None
        client._contract.events.TaskSubmitted.return_value.process_log.return_value = mock_event

        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 1, "logs": [{}], "blockNumber": 100}
        )

        task_id = await client.submit_task(
            primary_agent=SAMPLE_ADDRESS,
            fallback_agent=SAMPLE_ADDRESS,
            task_cid="QmTaskCid",
            heartbeat_interval=60,
            deadline=1700000000,
            escrow=10**17,
        )

        assert task_id == SAMPLE_TASK_ID

    @pytest.mark.asyncio
    async def test_settle_success(self, mock_client_with_signer):
        """Test settle sends transaction and returns settlement info."""
        client = mock_client_with_signer

        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.settle.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")

        # Mock receipt with TaskSettled event
        mock_event = {
            "args": {
                "primaryAgent": SAMPLE_ADDRESS,
                "fallbackAgent": SAMPLE_ADDRESS,
                "primaryShare": 7 * 10**17,
                "fallbackShare": 3 * 10**17,
                "protocolFee": 25 * 10**15,
                "primaryCheckpoints": 5,
                "fallbackCheckpoints": 2,
            }
        }
        client._contract.events.TaskSettled.return_value.process_log.return_value = mock_event

        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 1, "logs": [{}], "blockNumber": 100}
        )

        settlement = await client.settle(SAMPLE_TASK_ID)

        assert settlement.task_id == SAMPLE_TASK_ID
        assert settlement.primary_share == 7 * 10**17

    @pytest.mark.asyncio
    async def test_submit_task_reverted(self, mock_client_with_signer):
        """Test submit_task raises error on revert."""
        client = mock_client_with_signer

        client._w3.eth.get_transaction_count = AsyncMock(return_value=1)
        client._contract.functions.submitTask.return_value.build_transaction = AsyncMock(
            return_value={"nonce": 1}
        )
        client._w3.eth.send_raw_transaction = AsyncMock(return_value=b"tx_hash")
        client._w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 0, "logs": [], "blockNumber": 100}
        )

        with pytest.raises(ContractError, match="reverted"):
            await client.submit_task(
                primary_agent=SAMPLE_ADDRESS,
                fallback_agent=SAMPLE_ADDRESS,
                task_cid="QmTaskCid",
                heartbeat_interval=60,
                deadline=1700000000,
                escrow=10**17,
            )


class TestCairnClientHelpers:
    """Tests for CairnClient helper methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client for testing."""
        with patch("sdk.client.AsyncWeb3") as mock_web3_class:
            mock_w3 = MagicMock()
            mock_w3.to_checksum_address.return_value = SAMPLE_CONTRACT_ADDRESS
            mock_contract = MagicMock()
            mock_w3.eth.contract.return_value = mock_contract
            mock_web3_class.return_value = mock_w3
            mock_web3_class.AsyncHTTPProvider.return_value = MagicMock()

            client = CairnClient(
                rpc_url=SAMPLE_RPC_URL,
                contract_address=SAMPLE_CONTRACT_ADDRESS,
            )
            client._contract = mock_contract
            yield client

    def test_extract_task_id_from_receipt(self, mock_client):
        """Test extracting task_id from receipt logs."""
        task_id_bytes = bytes.fromhex(SAMPLE_TASK_ID.replace("0x", ""))

        # Mock event processing
        mock_event = MagicMock()
        mock_event.__getitem__ = lambda self, key: {"taskId": task_id_bytes} if key == "args" else None
        mock_client._contract.events.TaskSubmitted.return_value.process_log.return_value = mock_event

        receipt = {"logs": [{"topics": [], "data": ""}]}

        result = mock_client._extract_task_id_from_receipt(receipt)

        assert result == SAMPLE_TASK_ID

    def test_extract_task_id_not_found(self, mock_client):
        """Test extracting task_id raises error when not found."""
        mock_client._contract.events.TaskSubmitted.return_value.process_log.side_effect = Exception("No event")

        receipt = {"logs": []}

        with pytest.raises(ContractError, match="not found"):
            mock_client._extract_task_id_from_receipt(receipt)

    def test_extract_settlement_from_receipt(self, mock_client):
        """Test extracting settlement info from receipt."""
        mock_event = {
            "args": {
                "primaryAgent": SAMPLE_ADDRESS,
                "fallbackAgent": SAMPLE_ADDRESS,
                "primaryShare": 7 * 10**17,
                "fallbackShare": 3 * 10**17,
                "protocolFee": 25 * 10**15,
                "primaryCheckpoints": 5,
                "fallbackCheckpoints": 2,
            }
        }
        mock_client._contract.events.TaskSettled.return_value.process_log.return_value = mock_event

        receipt = {"logs": [{"topics": [], "data": ""}], "blockNumber": 100}

        settlement = mock_client._extract_settlement_from_receipt(receipt, SAMPLE_TASK_ID)

        assert settlement.task_id == SAMPLE_TASK_ID
        assert settlement.primary_share == 7 * 10**17
        assert settlement.fallback_share == 3 * 10**17

    def test_extract_settlement_fallback(self, mock_client):
        """Test extracting settlement returns minimal info when event not found."""
        mock_client._contract.events.TaskSettled.return_value.process_log.side_effect = Exception("No event")

        receipt = {"logs": [], "blockNumber": 100}

        settlement = mock_client._extract_settlement_from_receipt(receipt, SAMPLE_TASK_ID)

        assert settlement.task_id == SAMPLE_TASK_ID
        assert settlement.primary_share == 0
        assert settlement.resolved_at == 100
