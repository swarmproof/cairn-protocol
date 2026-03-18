"""
CAIRN SDK Observers

Observer pattern for task lifecycle events.
"""

import hashlib
import hmac
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from sdk.types import Task

logger = logging.getLogger(__name__)


class CairnObserver(ABC):
    """
    Base observer for task lifecycle events.

    Implement this class to receive notifications about task progress.

    Example:
        class MyObserver(CairnObserver):
            async def on_checkpoint(self, task_id, index, cid):
                print(f"Checkpoint {index} committed!")

        agent.add_observer(MyObserver())
    """

    async def on_task_submitted(self, task_id: str, task: Task) -> None:
        """Called when a task starts execution."""
        pass

    async def on_checkpoint(self, task_id: str, index: int, cid: str) -> None:
        """Called when a checkpoint is committed."""
        pass

    async def on_heartbeat(self, task_id: str, timestamp: int) -> None:
        """Called when a heartbeat is sent."""
        pass

    async def on_failed(self, task_id: str, reason: str) -> None:
        """Called when task execution fails."""
        pass

    async def on_resolved(self, task_id: str, settlement: dict) -> None:
        """Called when task is resolved and settled."""
        pass


class LoggingObserver(CairnObserver):
    """
    Observer that logs all events.

    Example:
        import logging
        logging.basicConfig(level=logging.INFO)

        agent.add_observer(LoggingObserver())
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
        level: int = logging.INFO,
    ):
        """
        Initialize LoggingObserver.

        Args:
            logger: Logger instance (uses module logger if not provided)
            level: Logging level for events
        """
        self._logger = logger or logging.getLogger("cairn.observer")
        self._level = level

    async def on_task_submitted(self, task_id: str, task: Task) -> None:
        """Log task submission."""
        self._logger.log(
            self._level,
            f"[CAIRN] Task submitted: {task_id[:16]}... "
            f"| State: {task.state} "
            f"| Escrow: {task.escrow / 10**18:.4f} ETH",
        )

    async def on_checkpoint(self, task_id: str, index: int, cid: str) -> None:
        """Log checkpoint commit."""
        self._logger.log(
            self._level,
            f"[CAIRN] Checkpoint {index} committed: {cid[:16]}... "
            f"| Task: {task_id[:16]}...",
        )

    async def on_heartbeat(self, task_id: str, timestamp: int) -> None:
        """Log heartbeat."""
        self._logger.log(
            logging.DEBUG,  # Heartbeats are verbose, use DEBUG
            f"[CAIRN] Heartbeat: {task_id[:16]}... | Time: {timestamp}",
        )

    async def on_failed(self, task_id: str, reason: str) -> None:
        """Log failure."""
        self._logger.log(
            logging.ERROR,
            f"[CAIRN] Task FAILED: {task_id[:16]}... | Reason: {reason}",
        )

    async def on_resolved(self, task_id: str, settlement: dict) -> None:
        """Log resolution."""
        primary_share = settlement.get("primary_share", 0) / 10**18
        fallback_share = settlement.get("fallback_share", 0) / 10**18

        self._logger.log(
            self._level,
            f"[CAIRN] Task RESOLVED: {task_id[:16]}... "
            f"| Primary: {primary_share:.4f} ETH "
            f"| Fallback: {fallback_share:.4f} ETH",
        )


class WebhookObserver(CairnObserver):
    """
    Observer that posts events to a webhook URL.

    Useful for integrating with Slack, Discord, or custom backends.

    Example:
        observer = WebhookObserver(
            webhook_url="https://hooks.slack.com/...",
            secret="my-secret-key",  # For HMAC signature
        )
        agent.add_observer(observer)

    The webhook receives JSON payloads:
        {
            "event": "checkpoint",
            "task_id": "0x...",
            "data": {...},
            "timestamp": 1234567890
        }

    If a secret is provided, the payload includes an X-Signature header
    with HMAC-SHA256 signature.
    """

    def __init__(
        self,
        webhook_url: str,
        secret: str | None = None,
        timeout: float = 5.0,
        retry_count: int = 2,
    ):
        """
        Initialize WebhookObserver.

        Args:
            webhook_url: URL to POST events to
            secret: Optional secret for HMAC signature
            timeout: Request timeout in seconds
            retry_count: Number of retries on failure
        """
        self._url = webhook_url
        self._secret = secret.encode() if secret else None
        self._timeout = timeout
        self._retry_count = retry_count
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _post_event(
        self,
        event: str,
        task_id: str,
        data: dict[str, Any],
    ) -> None:
        """Post event to webhook."""
        payload = {
            "event": event,
            "task_id": task_id,
            "data": data,
            "timestamp": int(time.time()),
        }

        headers = {"Content-Type": "application/json"}

        # Add HMAC signature if secret is set
        if self._secret:
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            signature = hmac.new(
                self._secret, payload_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-Signature"] = signature

        client = await self._get_client()

        for attempt in range(self._retry_count + 1):
            try:
                response = await client.post(
                    self._url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return

            except Exception as e:
                if attempt == self._retry_count:
                    logger.warning(f"Webhook failed after {self._retry_count} retries: {e}")
                else:
                    logger.debug(f"Webhook attempt {attempt + 1} failed: {e}")

    async def on_task_submitted(self, task_id: str, task: Task) -> None:
        """Post task submission event."""
        await self._post_event("task_submitted", task_id, {
            "state": str(task.state),
            "operator": task.operator,
            "primary_agent": task.primary_agent,
            "fallback_agent": task.fallback_agent,
            "escrow_wei": task.escrow,
            "deadline": task.deadline,
        })

    async def on_checkpoint(self, task_id: str, index: int, cid: str) -> None:
        """Post checkpoint event."""
        await self._post_event("checkpoint", task_id, {
            "index": index,
            "cid": cid,
        })

    async def on_heartbeat(self, task_id: str, timestamp: int) -> None:
        """Post heartbeat event."""
        await self._post_event("heartbeat", task_id, {
            "timestamp": timestamp,
        })

    async def on_failed(self, task_id: str, reason: str) -> None:
        """Post failure event."""
        await self._post_event("failed", task_id, {
            "reason": reason,
        })

    async def on_resolved(self, task_id: str, settlement: dict) -> None:
        """Post resolution event."""
        await self._post_event("resolved", task_id, settlement)


class CompositeObserver(CairnObserver):
    """
    Observer that delegates to multiple observers.

    Example:
        composite = CompositeObserver([
            LoggingObserver(),
            WebhookObserver(url),
        ])
        agent.add_observer(composite)
    """

    def __init__(self, observers: list[CairnObserver]):
        """
        Initialize CompositeObserver.

        Args:
            observers: List of observers to delegate to
        """
        self._observers = observers

    def add(self, observer: CairnObserver) -> None:
        """Add an observer."""
        self._observers.append(observer)

    def remove(self, observer: CairnObserver) -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    async def on_task_submitted(self, task_id: str, task: Task) -> None:
        """Delegate to all observers."""
        for observer in self._observers:
            try:
                await observer.on_task_submitted(task_id, task)
            except Exception as e:
                logger.warning(f"Observer error: {e}")

    async def on_checkpoint(self, task_id: str, index: int, cid: str) -> None:
        """Delegate to all observers."""
        for observer in self._observers:
            try:
                await observer.on_checkpoint(task_id, index, cid)
            except Exception as e:
                logger.warning(f"Observer error: {e}")

    async def on_heartbeat(self, task_id: str, timestamp: int) -> None:
        """Delegate to all observers."""
        for observer in self._observers:
            try:
                await observer.on_heartbeat(task_id, timestamp)
            except Exception as e:
                logger.warning(f"Observer error: {e}")

    async def on_failed(self, task_id: str, reason: str) -> None:
        """Delegate to all observers."""
        for observer in self._observers:
            try:
                await observer.on_failed(task_id, reason)
            except Exception as e:
                logger.warning(f"Observer error: {e}")

    async def on_resolved(self, task_id: str, settlement: dict) -> None:
        """Delegate to all observers."""
        for observer in self._observers:
            try:
                await observer.on_resolved(task_id, settlement)
            except Exception as e:
                logger.warning(f"Observer error: {e}")
