"""
Event Listener

Listens for CairnCore contract events on Base Sepolia and routes them to BonfiresAdapter.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.types import EventData

from pipeline.adapter import BonfiresAdapter
from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class EventListener:
    """
    Event listener for CAIRN Protocol contract events.

    Connects to Base Sepolia RPC, subscribes to TaskFailed and TaskResolved events,
    and routes them to BonfiresAdapter for processing.

    Example:
        config = PipelineConfig.from_env()
        adapter = BonfiresAdapter(bonfires, ipfs)
        listener = EventListener(config, adapter)

        # Start listening (blocking)
        await listener.start()
    """

    def __init__(
        self,
        config: PipelineConfig,
        adapter: BonfiresAdapter,
        abi: Optional[list[dict[str, Any]]] = None,
    ):
        """
        Initialize event listener.

        Args:
            config: Pipeline configuration
            adapter: BonfiresAdapter to route events to
            abi: Contract ABI (loads from SDK if not provided)
        """
        self._config = config
        self._adapter = adapter
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # Initialize Web3
        self._w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(config.rpc_url))

        # Load ABI
        if abi is None:
            from pathlib import Path
            import json

            abi_path = Path(__file__).parent.parent / "sdk" / "abi.json"
            with open(abi_path) as f:
                abi = json.load(f)

        # Initialize contract
        self._contract: AsyncContract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(config.contract_address),
            abi=abi,
        )

        logger.info(
            f"EventListener initialized for contract {config.contract_address} "
            f"on {config.rpc_url}"
        )

    async def start(self) -> None:
        """
        Start listening for events.

        This is a blocking call that runs until stop() is called.
        """
        if self._running:
            logger.warning("EventListener already running")
            return

        self._running = True
        logger.info("Starting event listener...")

        # Check connection
        is_connected = await self._w3.is_connected()
        if not is_connected:
            raise RuntimeError(f"Failed to connect to RPC: {self._config.rpc_url}")

        chain_id = await self._w3.eth.chain_id
        logger.info(f"Connected to chain ID: {chain_id}")

        # Get starting block
        if self._config.start_block > 0:
            from_block = self._config.start_block
        else:
            from_block = await self._w3.eth.block_number
            logger.info(f"Starting from current block: {from_block}")

        # Create event filters
        task_failed_filter = await self._contract.events.TaskFailed.create_filter(
            from_block=from_block
        )
        task_resolved_filter = await self._contract.events.TaskResolved.create_filter(
            from_block=from_block
        )

        logger.info("Event filters created, listening for events...")

        try:
            # Poll for events
            while self._running:
                # Check TaskFailed events
                failed_entries = await task_failed_filter.get_new_entries()
                for entry in failed_entries:
                    await self._handle_task_failed(entry)

                # Check TaskResolved events
                resolved_entries = await task_resolved_filter.get_new_entries()
                for entry in resolved_entries:
                    await self._handle_task_resolved(entry)

                # Run pattern detection periodically
                if len(failed_entries) > 0 or len(resolved_entries) > 0:
                    self._run_pattern_detection()

                # Wait before next poll
                await asyncio.sleep(self._config.poll_interval)

        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
        except Exception as e:
            logger.error(f"Event listener error: {e}")
            raise
        finally:
            self._running = False
            logger.info("Event listener stopped")

    async def stop(self) -> None:
        """Stop the event listener."""
        if not self._running:
            return

        logger.info("Stopping event listener...")
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

    async def _handle_task_failed(self, event: EventData) -> None:
        """
        Handle TaskFailed event.

        Args:
            event: Web3 EventData object
        """
        try:
            args = event["args"]
            block = await self._w3.eth.get_block(event["blockNumber"])

            event_data = {
                "task_id": args["taskId"],
                "agent": args.get("agent", ""),
                "failure_class": args.get("failureClass", 0),
                "checkpoint_count": args.get("checkpointCount", 0),
                "block_number": event["blockNumber"],
                "timestamp": block["timestamp"],
                "transaction_hash": event["transactionHash"].hex(),
            }

            logger.info(
                f"TaskFailed event: task={event_data['task_id'].hex()[:16]}... "
                f"block={event_data['block_number']}"
            )

            # Route to adapter
            cid = await self._adapter.on_task_failed(event_data)
            logger.info(f"Failure record created: {cid}")

        except Exception as e:
            logger.error(f"Failed to handle TaskFailed event: {e}")
            # Continue processing other events

    async def _handle_task_resolved(self, event: EventData) -> None:
        """
        Handle TaskResolved event.

        Args:
            event: Web3 EventData object
        """
        try:
            args = event["args"]
            block = await self._w3.eth.get_block(event["blockNumber"])

            event_data = {
                "task_id": args["taskId"],
                "primary_agent": args.get("primaryAgent", ""),
                "fallback_agent": args.get("fallbackAgent", ""),
                "primary_checkpoints": args.get("primaryCheckpoints", 0),
                "fallback_checkpoints": args.get("fallbackCheckpoints", 0),
                "primary_payout": args.get("primaryPayout", 0),
                "fallback_payout": args.get("fallbackPayout", 0),
                "protocol_fee": args.get("protocolFee", 0),
                "block_number": event["blockNumber"],
                "timestamp": block["timestamp"],
                "transaction_hash": event["transactionHash"].hex(),
            }

            logger.info(
                f"TaskResolved event: task={event_data['task_id'].hex()[:16]}... "
                f"block={event_data['block_number']}"
            )

            # Route to adapter
            cid = await self._adapter.on_task_resolved(event_data)
            logger.info(f"Resolution record created: {cid}")

        except Exception as e:
            logger.error(f"Failed to handle TaskResolved event: {e}")
            # Continue processing other events

    def _run_pattern_detection(self) -> None:
        """Run pattern detection (non-blocking)."""
        try:
            patterns = self._adapter.run_pattern_detection()
            if patterns:
                logger.info(f"Detected {len(patterns)} patterns")
        except Exception as e:
            logger.warning(f"Pattern detection failed: {e}")

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status dictionary
        """
        try:
            is_connected = await self._w3.is_connected()
            current_block = await self._w3.eth.block_number
            chain_id = await self._w3.eth.chain_id

            stats = self._adapter.get_statistics()

            return {
                "running": self._running,
                "connected": is_connected,
                "chain_id": chain_id,
                "current_block": current_block,
                "contract": self._config.contract_address,
                "statistics": stats,
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "running": self._running,
                "connected": False,
                "error": str(e),
            }

    async def __aenter__(self) -> "EventListener":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.stop()
