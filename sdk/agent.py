"""
CAIRN SDK Agent Wrapper

Wraps any agent with automatic checkpointing and heartbeat.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Protocol, runtime_checkable

from sdk.client import CairnClient
from sdk.checkpoint import CheckpointStore
from sdk.observer import CairnObserver
from sdk.types import Task, TaskState, CheckpointData
from sdk.exceptions import (
    CairnError,
    HeartbeatError,
    InvalidStateError,
    ContractError,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class AgentProtocol(Protocol):
    """Protocol that wrapped agents should implement."""

    async def execute_subtask(self, subtask: dict, context: dict) -> dict:
        """Execute a single subtask and return result."""
        ...


class CairnAgent:
    """
    Wraps any agent with CAIRN protocol integration.

    Provides:
    - Automatic checkpointing after each subtask
    - Background heartbeat thread
    - Graceful failure handling
    - Resume from checkpoint for fallback

    Example:
        class MyAgent:
            async def execute_subtask(self, subtask, context):
                return {"result": "done"}

        client = CairnClient(rpc_url, contract, private_key)
        ipfs = CheckpointStore(pinata_jwt)
        agent = CairnAgent(MyAgent(), client, ipfs)

        async with agent:
            result = await agent.execute(task_id, subtasks)
    """

    def __init__(
        self,
        agent: Any,
        client: CairnClient,
        ipfs: CheckpointStore,
        heartbeat_margin: float = 0.8,
    ):
        """
        Initialize CairnAgent wrapper.

        Args:
            agent: The agent to wrap (must have execute_subtask method)
            client: CairnClient for contract interaction
            ipfs: CheckpointStore for checkpoint storage
            heartbeat_margin: Send heartbeat at this fraction of interval (default 0.8)
        """
        self._agent = agent
        self._client = client
        self._ipfs = ipfs
        self._heartbeat_margin = heartbeat_margin

        # State
        self._active_task: Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._observers: list[CairnObserver] = []
        self._stopped = False

    def add_observer(self, observer: CairnObserver) -> None:
        """Add an observer for task lifecycle events."""
        self._observers.append(observer)

    def remove_observer(self, observer: CairnObserver) -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    async def __aenter__(self) -> "CairnAgent":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - cleanup."""
        await self.stop()

    async def stop(self) -> None:
        """Stop the agent and cleanup."""
        self._stopped = True
        await self._stop_heartbeat()
        await self._ipfs.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Main Execution
    # ─────────────────────────────────────────────────────────────────────────

    async def execute(
        self,
        task_id: str,
        subtasks: list[dict],
        context: dict | None = None,
    ) -> dict:
        """
        Execute a task with automatic checkpointing and heartbeat.

        Args:
            task_id: Task ID from contract
            subtasks: List of subtask definitions
            context: Optional shared context passed to agent

        Returns:
            Final result with all subtask outputs

        Raises:
            CairnError: On failure
        """
        context = context or {}

        # Load task from contract
        task = await self._client.get_task(task_id)
        self._active_task = task

        # Validate state
        if task.state != TaskState.RUNNING:
            raise InvalidStateError(
                "Task must be in RUNNING state to execute",
                task_id=task_id,
                current_state=str(task.state),
                expected_states=["RUNNING"],
            )

        # Notify observers
        await self._notify_task_submitted(task_id, task)

        # Start heartbeat
        await self._start_heartbeat(task_id, task.heartbeat_interval)

        try:
            results = []
            start_index = task.primary_checkpoints  # Resume from last checkpoint

            for i, subtask in enumerate(subtasks[start_index:], start=start_index):
                if self._stopped:
                    break

                logger.info(f"Executing subtask {i}/{len(subtasks)}")

                # Execute subtask
                result = await self._execute_subtask_safe(subtask, context, i)

                # Checkpoint
                cid = await self._checkpoint(task_id, i, result)
                results.append({"index": i, "result": result, "cid": cid})

                # Update context with result
                context[f"subtask_{i}_result"] = result

            return {
                "task_id": task_id,
                "completed": len(results),
                "total": len(subtasks),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            await self._notify_failed(task_id, str(e))
            raise

        finally:
            await self._stop_heartbeat()
            self._active_task = None

    async def resume(
        self,
        task_id: str,
        subtasks: list[dict],
        context: dict | None = None,
    ) -> dict:
        """
        Resume a task from checkpoint (for fallback agent).

        Args:
            task_id: Task ID from contract
            subtasks: Full list of subtask definitions
            context: Optional shared context

        Returns:
            Final result with all subtask outputs
        """
        context = context or {}

        # Load task from contract
        task = await self._client.get_task(task_id)
        self._active_task = task

        # Validate state
        if task.state != TaskState.RECOVERING:
            raise InvalidStateError(
                "Task must be in RECOVERING state to resume",
                task_id=task_id,
                current_state=str(task.state),
                expected_states=["RECOVERING"],
            )

        # Load existing checkpoints into context
        for i, cid in enumerate(task.checkpoint_cids):
            try:
                checkpoint_data = await self._ipfs.read(cid)
                context[f"subtask_{i}_result"] = checkpoint_data.get("data", {})
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {i}: {e}")

        # Start heartbeat
        await self._start_heartbeat(task_id, task.heartbeat_interval)

        try:
            results = []
            start_index = task.total_checkpoints  # Resume from last checkpoint

            logger.info(f"Resuming from checkpoint {start_index}")

            for i, subtask in enumerate(subtasks[start_index:], start=start_index):
                if self._stopped:
                    break

                logger.info(f"Executing subtask {i}/{len(subtasks)} (fallback)")

                # Execute subtask
                result = await self._execute_subtask_safe(subtask, context, i)

                # Checkpoint
                cid = await self._checkpoint(task_id, i, result)
                results.append({"index": i, "result": result, "cid": cid})

                # Update context
                context[f"subtask_{i}_result"] = result

            return {
                "task_id": task_id,
                "resumed_from": start_index,
                "completed": len(results),
                "total": len(subtasks),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Fallback execution failed: {e}")
            await self._notify_failed(task_id, str(e))
            raise

        finally:
            await self._stop_heartbeat()
            self._active_task = None

    # ─────────────────────────────────────────────────────────────────────────
    # Subtask Execution
    # ─────────────────────────────────────────────────────────────────────────

    async def _execute_subtask_safe(
        self,
        subtask: dict,
        context: dict,
        index: int,
    ) -> dict:
        """Execute subtask with error handling."""
        try:
            if hasattr(self._agent, "execute_subtask"):
                return await self._agent.execute_subtask(subtask, context)
            elif callable(self._agent):
                return await self._agent(subtask, context)
            else:
                raise CairnError(
                    "Agent must have execute_subtask method or be callable"
                )
        except Exception as e:
            logger.error(f"Subtask {index} failed: {e}")
            raise CairnError(f"Subtask {index} failed: {e}") from e

    # ─────────────────────────────────────────────────────────────────────────
    # Checkpointing
    # ─────────────────────────────────────────────────────────────────────────

    async def _checkpoint(
        self,
        task_id: str,
        subtask_index: int,
        data: dict,
    ) -> str:
        """Create and commit a checkpoint."""
        # Create checkpoint data
        checkpoint = CheckpointData(
            task_id=task_id,
            subtask_index=subtask_index,
            agent=self._client.address or "",
            timestamp=int(time.time()),
            data=data,
        )

        # Pin to IPFS
        cid = await self._ipfs.write(
            checkpoint.to_ipfs_payload(),
            name=f"checkpoint-{task_id[:8]}-{subtask_index}",
        )

        # Commit to contract
        await self._client.commit_checkpoint(task_id, cid)

        # Notify observers
        await self._notify_checkpoint(task_id, subtask_index, cid)

        logger.info(f"Checkpoint {subtask_index} committed: {cid}")
        return cid

    # ─────────────────────────────────────────────────────────────────────────
    # Heartbeat
    # ─────────────────────────────────────────────────────────────────────────

    async def _start_heartbeat(self, task_id: str, interval: int) -> None:
        """Start background heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            return

        async def heartbeat_loop():
            # Send heartbeat at margin of interval (e.g., 80% of interval)
            sleep_time = interval * self._heartbeat_margin

            while not self._stopped:
                try:
                    await asyncio.sleep(sleep_time)

                    if self._stopped:
                        break

                    await self._client.heartbeat(task_id)
                    await self._notify_heartbeat(task_id, int(time.time()))
                    logger.debug(f"Heartbeat sent for {task_id}")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Heartbeat failed: {e}")
                    # Continue trying - don't break the loop

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info(f"Heartbeat started (interval: {interval}s)")

    async def _stop_heartbeat(self) -> None:
        """Stop background heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Heartbeat stopped")

    # ─────────────────────────────────────────────────────────────────────────
    # Observer Notifications
    # ─────────────────────────────────────────────────────────────────────────

    async def _notify_task_submitted(self, task_id: str, task: Task) -> None:
        """Notify observers of task submission."""
        for observer in self._observers:
            try:
                await observer.on_task_submitted(task_id, task)
            except Exception as e:
                logger.warning(f"Observer notification failed: {e}")

    async def _notify_checkpoint(
        self, task_id: str, index: int, cid: str
    ) -> None:
        """Notify observers of checkpoint."""
        for observer in self._observers:
            try:
                await observer.on_checkpoint(task_id, index, cid)
            except Exception as e:
                logger.warning(f"Observer notification failed: {e}")

    async def _notify_heartbeat(self, task_id: str, timestamp: int) -> None:
        """Notify observers of heartbeat."""
        for observer in self._observers:
            try:
                await observer.on_heartbeat(task_id, timestamp)
            except Exception as e:
                logger.warning(f"Observer notification failed: {e}")

    async def _notify_failed(self, task_id: str, reason: str) -> None:
        """Notify observers of failure."""
        for observer in self._observers:
            try:
                await observer.on_failed(task_id, reason)
            except Exception as e:
                logger.warning(f"Observer notification failed: {e}")

    async def _notify_resolved(
        self, task_id: str, settlement: dict
    ) -> None:
        """Notify observers of resolution."""
        for observer in self._observers:
            try:
                await observer.on_resolved(task_id, settlement)
            except Exception as e:
                logger.warning(f"Observer notification failed: {e}")
