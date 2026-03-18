"""
CAIRN SDK Client

Web3 client for interacting with the CairnTaskMVP contract.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.types import TxReceipt, Wei

from sdk.types import Task, TaskState, SettlementInfo
from sdk.exceptions import (
    ContractError,
    TaskNotFoundError,
    InvalidStateError,
    NetworkError,
)

logger = logging.getLogger(__name__)

# Load ABI from package
ABI_PATH = Path(__file__).parent / "abi.json"


def _load_abi() -> list[dict[str, Any]]:
    """Load contract ABI from file."""
    if not ABI_PATH.exists():
        raise FileNotFoundError(f"ABI file not found: {ABI_PATH}")
    with open(ABI_PATH) as f:
        return json.load(f)


class CairnClient:
    """
    Client for interacting with CairnTaskMVP contract.

    Example:
        client = CairnClient(
            rpc_url="https://sepolia.base.org",
            contract_address="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417",
            private_key=os.environ["PRIVATE_KEY"],
        )

        # Submit a task
        task_id = await client.submit_task(
            primary_agent="0x...",
            fallback_agent="0x...",
            task_cid="Qm...",
            heartbeat_interval=60,
            deadline=int(time.time()) + 3600,
            escrow=10**17,  # 0.1 ETH
        )

        # Get task state
        task = await client.get_task(task_id)
    """

    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        private_key: str | None = None,
    ):
        """
        Initialize CairnClient.

        Args:
            rpc_url: Base Sepolia RPC URL
            contract_address: Deployed CairnTaskMVP address
            private_key: Private key for signing transactions (optional for read-only)
        """
        self._rpc_url = rpc_url
        self._contract_address = contract_address
        self._private_key = private_key

        # Initialize Web3
        self._w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        self._abi = _load_abi()
        self._contract: AsyncContract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(contract_address),
            abi=self._abi,
        )

        # Account setup
        self._account = None
        if private_key:
            self._account = self._w3.eth.account.from_key(private_key)
            logger.info(f"Client initialized with account: {self._account.address}")

    @property
    def address(self) -> str | None:
        """Get the client's account address."""
        return self._account.address if self._account else None

    @property
    def contract_address(self) -> str:
        """Get the contract address."""
        return self._contract_address

    async def is_connected(self) -> bool:
        """Check if connected to RPC."""
        try:
            return await self._w3.is_connected()
        except Exception:
            return False

    async def get_chain_id(self) -> int:
        """Get the chain ID."""
        return await self._w3.eth.chain_id

    # ─────────────────────────────────────────────────────────────────────────
    # Write Methods
    # ─────────────────────────────────────────────────────────────────────────

    async def submit_task(
        self,
        primary_agent: str,
        fallback_agent: str,
        task_cid: str,
        heartbeat_interval: int,
        deadline: int,
        escrow: int,
    ) -> str:
        """
        Submit a new task to the contract.

        Args:
            primary_agent: Address of primary agent
            fallback_agent: Address of fallback agent
            task_cid: IPFS CID of task specification
            heartbeat_interval: Heartbeat interval in seconds
            deadline: Task deadline as Unix timestamp
            escrow: Escrow amount in wei

        Returns:
            Task ID (bytes32 hex string)

        Raises:
            ContractError: If transaction fails
        """
        self._require_signer()

        try:
            tx = await self._contract.functions.submitTask(
                self._w3.to_checksum_address(primary_agent),
                self._w3.to_checksum_address(fallback_agent),
                task_cid,
                heartbeat_interval,
                deadline,
            ).build_transaction({
                "from": self._account.address,
                "value": Wei(escrow),
                "nonce": await self._w3.eth.get_transaction_count(self._account.address),
                "gas": 300000,  # Estimate
            })

            signed = self._account.sign_transaction(tx)
            tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] != 1:
                raise ContractError(
                    "submitTask transaction reverted",
                    tx_hash=tx_hash.hex(),
                )

            # Extract task_id from TaskSubmitted event
            task_id = self._extract_task_id_from_receipt(receipt)
            logger.info(f"Task submitted: {task_id}")
            return task_id

        except ContractError:
            raise
        except Exception as e:
            raise ContractError(f"Failed to submit task: {e}") from e

    async def heartbeat(self, task_id: str) -> TxReceipt:
        """
        Send heartbeat for a task.

        Args:
            task_id: Task ID (bytes32 hex)

        Returns:
            Transaction receipt

        Raises:
            ContractError: If transaction fails
        """
        self._require_signer()

        try:
            task_id_bytes = bytes.fromhex(task_id.replace("0x", ""))

            tx = await self._contract.functions.heartbeat(
                task_id_bytes
            ).build_transaction({
                "from": self._account.address,
                "nonce": await self._w3.eth.get_transaction_count(self._account.address),
                "gas": 50000,
            })

            signed = self._account.sign_transaction(tx)
            tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] != 1:
                raise ContractError("heartbeat transaction reverted", tx_hash=tx_hash.hex())

            logger.debug(f"Heartbeat sent for task: {task_id}")
            return receipt

        except ContractError:
            raise
        except Exception as e:
            raise ContractError(f"Failed to send heartbeat: {e}") from e

    async def commit_checkpoint(
        self,
        task_id: str,
        cid: str,
    ) -> TxReceipt:
        """
        Commit a checkpoint for a task.

        Args:
            task_id: Task ID (bytes32 hex)
            cid: IPFS CID of checkpoint data

        Returns:
            Transaction receipt

        Raises:
            ContractError: If transaction fails
        """
        self._require_signer()

        try:
            task_id_bytes = bytes.fromhex(task_id.replace("0x", ""))

            tx = await self._contract.functions.commitCheckpoint(
                task_id_bytes,
                cid,
            ).build_transaction({
                "from": self._account.address,
                "nonce": await self._w3.eth.get_transaction_count(self._account.address),
                "gas": 100000,
            })

            signed = self._account.sign_transaction(tx)
            tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] != 1:
                raise ContractError("commitCheckpoint reverted", tx_hash=tx_hash.hex())

            logger.info(f"Checkpoint committed: {cid}")
            return receipt

        except ContractError:
            raise
        except Exception as e:
            raise ContractError(f"Failed to commit checkpoint: {e}") from e

    async def fail_task(self, task_id: str) -> TxReceipt:
        """
        Fail a task (permissionless liveness check).

        Args:
            task_id: Task ID (bytes32 hex)

        Returns:
            Transaction receipt
        """
        self._require_signer()

        try:
            task_id_bytes = bytes.fromhex(task_id.replace("0x", ""))

            tx = await self._contract.functions.failTask(
                task_id_bytes
            ).build_transaction({
                "from": self._account.address,
                "nonce": await self._w3.eth.get_transaction_count(self._account.address),
                "gas": 100000,
            })

            signed = self._account.sign_transaction(tx)
            tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] != 1:
                raise ContractError("failTask reverted", tx_hash=tx_hash.hex())

            logger.info(f"Task failed: {task_id}")
            return receipt

        except ContractError:
            raise
        except Exception as e:
            raise ContractError(f"Failed to fail task: {e}") from e

    async def recover_task(self, task_id: str) -> TxReceipt:
        """
        Initiate recovery for a failed task.

        Args:
            task_id: Task ID (bytes32 hex)

        Returns:
            Transaction receipt
        """
        self._require_signer()

        try:
            task_id_bytes = bytes.fromhex(task_id.replace("0x", ""))

            tx = await self._contract.functions.recoverTask(
                task_id_bytes
            ).build_transaction({
                "from": self._account.address,
                "nonce": await self._w3.eth.get_transaction_count(self._account.address),
                "gas": 100000,
            })

            signed = self._account.sign_transaction(tx)
            tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] != 1:
                raise ContractError("recoverTask reverted", tx_hash=tx_hash.hex())

            logger.info(f"Task recovery initiated: {task_id}")
            return receipt

        except ContractError:
            raise
        except Exception as e:
            raise ContractError(f"Failed to recover task: {e}") from e

    async def settle(self, task_id: str) -> SettlementInfo:
        """
        Settle a task and distribute escrow.

        Args:
            task_id: Task ID (bytes32 hex)

        Returns:
            Settlement information

        Raises:
            ContractError: If settlement fails
        """
        self._require_signer()

        try:
            task_id_bytes = bytes.fromhex(task_id.replace("0x", ""))

            tx = await self._contract.functions.settle(
                task_id_bytes
            ).build_transaction({
                "from": self._account.address,
                "nonce": await self._w3.eth.get_transaction_count(self._account.address),
                "gas": 150000,
            })

            signed = self._account.sign_transaction(tx)
            tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt["status"] != 1:
                raise ContractError("settle reverted", tx_hash=tx_hash.hex())

            # Extract settlement info from event
            settlement = self._extract_settlement_from_receipt(receipt, task_id)
            logger.info(f"Task settled: {task_id}")
            return settlement

        except ContractError:
            raise
        except Exception as e:
            raise ContractError(f"Failed to settle task: {e}") from e

    # ─────────────────────────────────────────────────────────────────────────
    # Read Methods
    # ─────────────────────────────────────────────────────────────────────────

    async def get_task(self, task_id: str) -> Task:
        """
        Get task details from contract.

        Args:
            task_id: Task ID (bytes32 hex)

        Returns:
            Task object with all details

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        try:
            task_id_bytes = bytes.fromhex(task_id.replace("0x", ""))
            result = await self._contract.functions.getTask(task_id_bytes).call()

            # Unpack tuple result
            (
                state,
                operator,
                primary_agent,
                fallback_agent,
                escrow,
                heartbeat_interval,
                deadline,
                primary_checkpoints,
                fallback_checkpoints,
                last_heartbeat,
                task_cid,
            ) = result

            # Check if task exists (operator is zero address if not)
            if operator == "0x0000000000000000000000000000000000000000":
                raise TaskNotFoundError(task_id)

            # Get checkpoint CIDs
            checkpoint_cids = await self.get_checkpoints(task_id)

            return Task(
                task_id=task_id,
                state=TaskState(state),
                operator=operator,
                primary_agent=primary_agent,
                fallback_agent=fallback_agent,
                escrow=escrow,
                heartbeat_interval=heartbeat_interval,
                deadline=deadline,
                primary_checkpoints=primary_checkpoints,
                fallback_checkpoints=fallback_checkpoints,
                last_heartbeat=last_heartbeat,
                checkpoint_cids=checkpoint_cids,
                task_cid=task_cid,
            )

        except TaskNotFoundError:
            raise
        except Exception as e:
            raise ContractError(f"Failed to get task: {e}") from e

    async def get_checkpoints(self, task_id: str) -> list[str]:
        """
        Get all checkpoint CIDs for a task.

        Args:
            task_id: Task ID (bytes32 hex)

        Returns:
            List of checkpoint CIDs
        """
        try:
            task_id_bytes = bytes.fromhex(task_id.replace("0x", ""))
            cids = await self._contract.functions.getCheckpoints(task_id_bytes).call()
            return list(cids)
        except Exception as e:
            raise ContractError(f"Failed to get checkpoints: {e}") from e

    async def get_protocol_fee(self) -> int:
        """Get protocol fee in basis points."""
        return await self._contract.functions.protocolFeeBps().call()

    async def get_min_escrow(self) -> int:
        """Get minimum escrow in wei."""
        return await self._contract.functions.minEscrow().call()

    async def get_min_heartbeat_interval(self) -> int:
        """Get minimum heartbeat interval in seconds."""
        return await self._contract.functions.minHeartbeatInterval().call()

    # ─────────────────────────────────────────────────────────────────────────
    # Event Subscription
    # ─────────────────────────────────────────────────────────────────────────

    async def watch_events(
        self,
        event_name: str,
        callback: Callable[[dict], None],
        from_block: int | str = "latest",
    ) -> None:
        """
        Watch for contract events.

        Args:
            event_name: Name of event to watch (e.g., "TaskSubmitted")
            callback: Function to call with event data
            from_block: Block to start watching from
        """
        event = getattr(self._contract.events, event_name)
        event_filter = await event.create_filter(from_block=from_block)

        while True:
            entries = await event_filter.get_new_entries()
            for entry in entries:
                callback(dict(entry))

    # ─────────────────────────────────────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _require_signer(self) -> None:
        """Ensure client has a signer for write operations."""
        if not self._account:
            raise ContractError("Private key required for write operations")

    def _extract_task_id_from_receipt(self, receipt: TxReceipt) -> str:
        """Extract task_id from TaskSubmitted event in receipt."""
        for log in receipt["logs"]:
            try:
                event = self._contract.events.TaskSubmitted().process_log(log)
                return "0x" + event["args"]["taskId"].hex()
            except Exception:
                continue
        raise ContractError("TaskSubmitted event not found in receipt")

    def _extract_settlement_from_receipt(
        self, receipt: TxReceipt, task_id: str
    ) -> SettlementInfo:
        """Extract settlement info from TaskSettled event."""
        for log in receipt["logs"]:
            try:
                event = self._contract.events.TaskSettled().process_log(log)
                args = event["args"]
                return SettlementInfo(
                    task_id=task_id,
                    primary_agent=args.get("primaryAgent", ""),
                    fallback_agent=args.get("fallbackAgent", ""),
                    primary_share=args.get("primaryShare", 0),
                    fallback_share=args.get("fallbackShare", 0),
                    protocol_fee=args.get("protocolFee", 0),
                    primary_checkpoints=args.get("primaryCheckpoints", 0),
                    fallback_checkpoints=args.get("fallbackCheckpoints", 0),
                    resolved_at=receipt["blockNumber"],
                )
            except Exception:
                continue

        # Return minimal settlement if event not found
        return SettlementInfo(
            task_id=task_id,
            primary_agent="",
            fallback_agent="",
            primary_share=0,
            fallback_share=0,
            protocol_fee=0,
            primary_checkpoints=0,
            fallback_checkpoints=0,
            resolved_at=receipt["blockNumber"],
        )
