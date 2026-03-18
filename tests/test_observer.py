"""Tests for CAIRN SDK observers."""

import logging
import pytest
import httpx
import respx

from sdk.observer import (
    CairnObserver,
    LoggingObserver,
    WebhookObserver,
    CompositeObserver,
)
from sdk.types import Task, TaskState


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        task_id="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        state=TaskState.RUNNING,
        operator="0x1111111111111111111111111111111111111111",
        primary_agent="0x2222222222222222222222222222222222222222",
        fallback_agent="0x3333333333333333333333333333333333333333",
        escrow=10**18,
        heartbeat_interval=60,
        deadline=1700000000,
    )


class TestCairnObserver:
    """Tests for base CairnObserver."""

    @pytest.mark.asyncio
    async def test_default_methods_do_nothing(self, sample_task: Task):
        """Test that default observer methods don't raise errors."""
        observer = CairnObserver()

        # All these should complete without error
        await observer.on_task_submitted("0x1234", sample_task)
        await observer.on_checkpoint("0x1234", 0, "QmCid")
        await observer.on_heartbeat("0x1234", 1700000000)
        await observer.on_failed("0x1234", "Test failure")
        await observer.on_resolved("0x1234", {"primary_share": 10**18})


class TestLoggingObserver:
    """Tests for LoggingObserver."""

    @pytest.fixture
    def logger(self) -> logging.Logger:
        """Create test logger."""
        logger = logging.getLogger("test_cairn")
        logger.setLevel(logging.DEBUG)
        return logger

    @pytest.mark.asyncio
    async def test_on_task_submitted(
        self, logger: logging.Logger, sample_task: Task, caplog
    ):
        """Test task submission logging."""
        observer = LoggingObserver(logger=logger)

        with caplog.at_level(logging.INFO):
            await observer.on_task_submitted("0x1234", sample_task)

        assert "Task submitted" in caplog.text
        assert "RUNNING" in caplog.text

    @pytest.mark.asyncio
    async def test_on_checkpoint(self, logger: logging.Logger, caplog):
        """Test checkpoint logging."""
        observer = LoggingObserver(logger=logger)

        with caplog.at_level(logging.INFO):
            await observer.on_checkpoint("0x1234", 5, "QmTestCid123")

        assert "Checkpoint 5" in caplog.text
        assert "QmTestCid" in caplog.text

    @pytest.mark.asyncio
    async def test_on_heartbeat_uses_debug(self, logger: logging.Logger, caplog):
        """Test heartbeat uses DEBUG level."""
        observer = LoggingObserver(logger=logger)

        with caplog.at_level(logging.DEBUG):
            await observer.on_heartbeat("0x1234", 1700000000)

        assert "Heartbeat" in caplog.text

    @pytest.mark.asyncio
    async def test_on_failed(self, logger: logging.Logger, caplog):
        """Test failure logging."""
        observer = LoggingObserver(logger=logger)

        with caplog.at_level(logging.ERROR):
            await observer.on_failed("0x1234", "Connection timeout")

        assert "FAILED" in caplog.text
        assert "Connection timeout" in caplog.text

    @pytest.mark.asyncio
    async def test_on_resolved(self, logger: logging.Logger, caplog):
        """Test resolution logging."""
        observer = LoggingObserver(logger=logger)

        settlement = {
            "primary_share": 7 * 10**17,
            "fallback_share": 3 * 10**17,
        }

        with caplog.at_level(logging.INFO):
            await observer.on_resolved("0x1234", settlement)

        assert "RESOLVED" in caplog.text


class TestWebhookObserver:
    """Tests for WebhookObserver."""

    @pytest.fixture
    def webhook_url(self) -> str:
        """Sample webhook URL."""
        return "https://hooks.example.com/cairn"

    @respx.mock
    @pytest.mark.asyncio
    async def test_on_checkpoint_posts_event(
        self, webhook_url: str, sample_task: Task
    ):
        """Test checkpoint event is posted to webhook."""
        respx.post(webhook_url).mock(return_value=httpx.Response(200))

        observer = WebhookObserver(webhook_url=webhook_url)
        await observer.on_checkpoint("0x1234", 3, "QmCheckpointCid")

        assert respx.calls.call_count == 1

        # Verify request body
        request = respx.calls[0].request
        import json
        body = json.loads(request.content)

        assert body["event"] == "checkpoint"
        assert body["task_id"] == "0x1234"
        assert body["data"]["index"] == 3
        assert body["data"]["cid"] == "QmCheckpointCid"

    @respx.mock
    @pytest.mark.asyncio
    async def test_webhook_with_signature(self, webhook_url: str):
        """Test webhook includes HMAC signature when secret is provided."""
        respx.post(webhook_url).mock(return_value=httpx.Response(200))

        observer = WebhookObserver(
            webhook_url=webhook_url,
            secret="my-secret-key",
        )
        await observer.on_heartbeat("0x1234", 1700000000)

        request = respx.calls[0].request
        assert "X-Signature" in request.headers
        assert len(request.headers["X-Signature"]) == 64  # SHA256 hex

    @respx.mock
    @pytest.mark.asyncio
    async def test_webhook_retry_on_failure(self, webhook_url: str):
        """Test webhook retries on failure."""
        # First request fails, second succeeds
        respx.post(webhook_url).mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(500),
                httpx.Response(200),
            ]
        )

        observer = WebhookObserver(
            webhook_url=webhook_url,
            retry_count=2,
        )
        await observer.on_failed("0x1234", "Test error")

        assert respx.calls.call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_webhook_all_events(self, webhook_url: str, sample_task: Task):
        """Test all event types are posted correctly."""
        respx.post(webhook_url).mock(return_value=httpx.Response(200))

        observer = WebhookObserver(webhook_url=webhook_url)

        # Test all event types
        await observer.on_task_submitted("0x1234", sample_task)
        await observer.on_checkpoint("0x1234", 0, "QmCid")
        await observer.on_heartbeat("0x1234", 1700000000)
        await observer.on_failed("0x1234", "reason")
        await observer.on_resolved("0x1234", {"primary_share": 10**18})

        assert respx.calls.call_count == 5


class TestCompositeObserver:
    """Tests for CompositeObserver."""

    @pytest.mark.asyncio
    async def test_composite_delegates_to_all(self, sample_task: Task):
        """Test composite observer delegates to all observers."""
        # Create mock observers
        calls: list[str] = []

        class MockObserver(CairnObserver):
            def __init__(self, name: str):
                self.name = name

            async def on_checkpoint(self, task_id: str, index: int, cid: str):
                calls.append(f"{self.name}:checkpoint:{index}")

        observer1 = MockObserver("obs1")
        observer2 = MockObserver("obs2")

        composite = CompositeObserver([observer1, observer2])
        await composite.on_checkpoint("0x1234", 5, "QmCid")

        assert "obs1:checkpoint:5" in calls
        assert "obs2:checkpoint:5" in calls

    @pytest.mark.asyncio
    async def test_composite_add_remove(self, sample_task: Task):
        """Test adding and removing observers."""
        calls: list[str] = []

        class MockObserver(CairnObserver):
            def __init__(self, name: str):
                self.name = name

            async def on_heartbeat(self, task_id: str, timestamp: int):
                calls.append(self.name)

        obs1 = MockObserver("obs1")
        obs2 = MockObserver("obs2")

        composite = CompositeObserver([obs1])
        composite.add(obs2)

        await composite.on_heartbeat("0x1234", 1700000000)
        assert calls == ["obs1", "obs2"]

        calls.clear()
        composite.remove(obs1)

        await composite.on_heartbeat("0x1234", 1700000000)
        assert calls == ["obs2"]

    @pytest.mark.asyncio
    async def test_composite_handles_observer_errors(self, sample_task: Task):
        """Test composite continues if one observer fails."""
        calls: list[str] = []

        class FailingObserver(CairnObserver):
            async def on_failed(self, task_id: str, reason: str):
                raise RuntimeError("Observer error")

        class WorkingObserver(CairnObserver):
            async def on_failed(self, task_id: str, reason: str):
                calls.append("working")

        composite = CompositeObserver([
            FailingObserver(),
            WorkingObserver(),
        ])

        # Should not raise, and working observer should still be called
        await composite.on_failed("0x1234", "test")
        assert "working" in calls
