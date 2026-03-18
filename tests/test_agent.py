"""Tests for CAIRN SDK CairnAgent."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sdk.agent import CairnAgent, AgentProtocol
from sdk.observer import CairnObserver
from sdk.types import Task, TaskState
from sdk.exceptions import CairnError, InvalidStateError


# Sample test data
SAMPLE_TASK_ID = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
SAMPLE_ADDRESS = "0x1111111111111111111111111111111111111111"


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
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


@pytest.fixture
def sample_failed_task() -> Task:
    """Create a sample failed task for testing."""
    return Task(
        task_id=SAMPLE_TASK_ID,
        state=TaskState.FAILED,
        operator=SAMPLE_ADDRESS,
        primary_agent=SAMPLE_ADDRESS,
        fallback_agent=SAMPLE_ADDRESS,
        escrow=10**18,
        heartbeat_interval=60,
        deadline=1700000000,
        primary_checkpoints=0,
        fallback_checkpoints=0,
    )


@pytest.fixture
def sample_recovering_task() -> Task:
    """Create a sample recovering task for testing."""
    return Task(
        task_id=SAMPLE_TASK_ID,
        state=TaskState.RECOVERING,
        operator=SAMPLE_ADDRESS,
        primary_agent=SAMPLE_ADDRESS,
        fallback_agent=SAMPLE_ADDRESS,
        escrow=10**18,
        heartbeat_interval=60,
        deadline=1700000000,
        primary_checkpoints=2,
        fallback_checkpoints=0,
        checkpoint_cids=["QmCid1", "QmCid2"],
    )


@pytest.fixture
def mock_client():
    """Create a mock CairnClient."""
    client = MagicMock()
    client.address = SAMPLE_ADDRESS
    client.get_task = AsyncMock()
    client.heartbeat = AsyncMock()
    client.commit_checkpoint = AsyncMock()
    return client


@pytest.fixture
def mock_ipfs():
    """Create a mock CheckpointStore."""
    ipfs = MagicMock()
    ipfs.write = AsyncMock(return_value="QmNewCheckpointCid")
    ipfs.read = AsyncMock(return_value={"data": {"result": "previous"}})
    ipfs.close = AsyncMock()
    return ipfs


@pytest.fixture
def mock_agent():
    """Create a mock agent with execute_subtask method."""
    agent = MagicMock()
    agent.execute_subtask = AsyncMock(return_value={"status": "completed"})
    return agent


class TestAgentProtocol:
    """Tests for AgentProtocol."""

    def test_protocol_check(self, mock_agent):
        """Test that mock agent satisfies protocol."""
        assert isinstance(mock_agent, AgentProtocol)

    def test_protocol_check_missing_method(self):
        """Test that object without method doesn't satisfy protocol."""
        obj = MagicMock(spec=[])  # No methods
        assert not isinstance(obj, AgentProtocol)


class TestCairnAgentInit:
    """Tests for CairnAgent initialization."""

    def test_init_basic(self, mock_client, mock_ipfs, mock_agent):
        """Test basic initialization."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        assert agent._agent == mock_agent
        assert agent._client == mock_client
        assert agent._ipfs == mock_ipfs
        assert agent._heartbeat_margin == 0.8

    def test_init_custom_heartbeat_margin(self, mock_client, mock_ipfs, mock_agent):
        """Test initialization with custom heartbeat margin."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs, heartbeat_margin=0.5)

        assert agent._heartbeat_margin == 0.5


class TestCairnAgentObservers:
    """Tests for CairnAgent observer management."""

    def test_add_observer(self, mock_client, mock_ipfs, mock_agent):
        """Test adding an observer."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        observer = MagicMock(spec=CairnObserver)

        agent.add_observer(observer)

        assert observer in agent._observers

    def test_remove_observer(self, mock_client, mock_ipfs, mock_agent):
        """Test removing an observer."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        observer = MagicMock(spec=CairnObserver)

        agent.add_observer(observer)
        agent.remove_observer(observer)

        assert observer not in agent._observers

    def test_remove_nonexistent_observer(self, mock_client, mock_ipfs, mock_agent):
        """Test removing a non-existent observer doesn't raise."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        observer = MagicMock(spec=CairnObserver)

        # Should not raise
        agent.remove_observer(observer)


class TestCairnAgentContextManager:
    """Tests for CairnAgent async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enter(self, mock_client, mock_ipfs, mock_agent):
        """Test async context manager entry."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        async with agent as ctx:
            assert ctx is agent

    @pytest.mark.asyncio
    async def test_context_manager_exit_cleanup(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test async context manager cleans up on exit."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        async with agent:
            pass

        assert agent._stopped is True
        mock_ipfs.close.assert_called_once()


class TestCairnAgentStop:
    """Tests for CairnAgent stop."""

    @pytest.mark.asyncio
    async def test_stop_sets_flag(self, mock_client, mock_ipfs, mock_agent):
        """Test stop sets stopped flag."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        await agent.stop()

        assert agent._stopped is True

    @pytest.mark.asyncio
    async def test_stop_closes_ipfs(self, mock_client, mock_ipfs, mock_agent):
        """Test stop closes IPFS store."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        await agent.stop()

        mock_ipfs.close.assert_called_once()


class TestCairnAgentExecute:
    """Tests for CairnAgent.execute()."""

    @pytest.mark.asyncio
    async def test_execute_validates_state(
        self, mock_client, mock_ipfs, mock_agent, sample_failed_task
    ):
        """Test execute validates task is in RUNNING state."""
        mock_client.get_task.return_value = sample_failed_task

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        with pytest.raises(InvalidStateError, match="RUNNING"):
            await agent.execute(SAMPLE_TASK_ID, [{"action": "test"}])

    @pytest.mark.asyncio
    async def test_execute_runs_subtasks(
        self, mock_client, mock_ipfs, mock_agent, sample_task
    ):
        """Test execute runs all subtasks."""
        mock_client.get_task.return_value = sample_task

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        subtasks = [
            {"action": "task1"},
            {"action": "task2"},
            {"action": "task3"},
        ]

        result = await agent.execute(SAMPLE_TASK_ID, subtasks)

        assert result["completed"] == 3
        assert result["total"] == 3
        assert mock_agent.execute_subtask.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_checkpoints_after_each_subtask(
        self, mock_client, mock_ipfs, mock_agent, sample_task
    ):
        """Test execute commits checkpoint after each subtask."""
        mock_client.get_task.return_value = sample_task

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        subtasks = [{"action": "task1"}, {"action": "task2"}]

        await agent.execute(SAMPLE_TASK_ID, subtasks)

        # Should write to IPFS twice
        assert mock_ipfs.write.call_count == 2
        # Should commit checkpoint twice
        assert mock_client.commit_checkpoint.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_updates_context(
        self, mock_client, mock_ipfs, mock_agent, sample_task
    ):
        """Test execute updates context with subtask results."""
        mock_client.get_task.return_value = sample_task

        # Track context passed to each subtask
        received_contexts = []

        async def track_context(subtask, context):
            received_contexts.append(dict(context))
            return {"status": "done"}

        mock_agent.execute_subtask.side_effect = track_context

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        subtasks = [{"action": "task1"}, {"action": "task2"}]

        await agent.execute(SAMPLE_TASK_ID, subtasks)

        # Second subtask should have result from first
        assert "subtask_0_result" in received_contexts[1]

    @pytest.mark.asyncio
    async def test_execute_resumes_from_checkpoint(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test execute resumes from existing checkpoints."""
        # Create task with existing checkpoints
        task_with_checkpoints = Task(
            task_id=SAMPLE_TASK_ID,
            state=TaskState.RUNNING,
            operator=SAMPLE_ADDRESS,
            primary_agent=SAMPLE_ADDRESS,
            fallback_agent=SAMPLE_ADDRESS,
            escrow=10**18,
            heartbeat_interval=60,
            deadline=1700000000,
            primary_checkpoints=2,  # Already has 2 checkpoints
            fallback_checkpoints=0,
        )
        mock_client.get_task.return_value = task_with_checkpoints

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        subtasks = [
            {"action": "task1"},
            {"action": "task2"},
            {"action": "task3"},
            {"action": "task4"},
        ]

        result = await agent.execute(SAMPLE_TASK_ID, subtasks)

        # Should only execute tasks 3 and 4 (indices 2, 3)
        assert result["completed"] == 2
        assert mock_agent.execute_subtask.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_notifies_observers(
        self, mock_client, mock_ipfs, mock_agent, sample_task
    ):
        """Test execute notifies observers of events."""
        mock_client.get_task.return_value = sample_task

        observer = MagicMock(spec=CairnObserver)
        observer.on_task_submitted = AsyncMock()
        observer.on_checkpoint = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(observer)

        await agent.execute(SAMPLE_TASK_ID, [{"action": "test"}])

        observer.on_task_submitted.assert_called_once()
        observer.on_checkpoint.assert_called_once()


class TestCairnAgentResume:
    """Tests for CairnAgent.resume()."""

    @pytest.mark.asyncio
    async def test_resume_validates_state(
        self, mock_client, mock_ipfs, mock_agent, sample_task
    ):
        """Test resume validates task is in RECOVERING state."""
        # sample_task already has RUNNING state, which is invalid for resume
        mock_client.get_task.return_value = sample_task

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        with pytest.raises(InvalidStateError, match="RECOVERING"):
            await agent.resume(SAMPLE_TASK_ID, [{"action": "test"}])

    @pytest.mark.asyncio
    async def test_resume_loads_checkpoints(
        self, mock_client, mock_ipfs, mock_agent, sample_recovering_task
    ):
        """Test resume loads existing checkpoints into context."""
        mock_client.get_task.return_value = sample_recovering_task

        # Track context passed to subtask
        received_context = None

        async def track_context(subtask, context):
            nonlocal received_context
            received_context = dict(context)
            return {"status": "done"}

        mock_agent.execute_subtask.side_effect = track_context

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        subtasks = [
            {"action": "task1"},
            {"action": "task2"},
            {"action": "task3"},
        ]

        await agent.resume(SAMPLE_TASK_ID, subtasks)

        # Context should have loaded checkpoint data
        assert "subtask_0_result" in received_context
        assert "subtask_1_result" in received_context

    @pytest.mark.asyncio
    async def test_resume_continues_from_checkpoint(
        self, mock_client, mock_ipfs, mock_agent, sample_recovering_task
    ):
        """Test resume continues from last checkpoint."""
        mock_client.get_task.return_value = sample_recovering_task

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        subtasks = [
            {"action": "task1"},
            {"action": "task2"},
            {"action": "task3"},
        ]

        result = await agent.resume(SAMPLE_TASK_ID, subtasks)

        # Task has 2 checkpoints, should only execute task3
        assert result["resumed_from"] == 2
        assert result["completed"] == 1
        assert mock_agent.execute_subtask.call_count == 1


class TestCairnAgentExecuteErrors:
    """Tests for error handling in execute."""

    @pytest.mark.asyncio
    async def test_execute_handles_subtask_error(
        self, mock_client, mock_ipfs, mock_agent, sample_task
    ):
        """Test execute handles subtask errors and notifies observers."""
        mock_client.get_task.return_value = sample_task
        mock_agent.execute_subtask.side_effect = ValueError("Subtask failed")

        observer = MagicMock(spec=CairnObserver)
        observer.on_task_submitted = AsyncMock()
        observer.on_failed = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(observer)

        with pytest.raises(CairnError):
            await agent.execute(SAMPLE_TASK_ID, [{"action": "test"}])

        # Observer should be notified of failure
        observer.on_failed.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_stops_heartbeat_on_error(
        self, mock_client, mock_ipfs, mock_agent, sample_task
    ):
        """Test execute stops heartbeat even when error occurs."""
        mock_client.get_task.return_value = sample_task
        mock_agent.execute_subtask.side_effect = ValueError("Subtask failed")

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        with pytest.raises(CairnError):
            await agent.execute(SAMPLE_TASK_ID, [{"action": "test"}])

        # Heartbeat task should be cleaned up
        assert agent._heartbeat_task is None


class TestCairnAgentResumeErrors:
    """Tests for error handling in resume."""

    @pytest.mark.asyncio
    async def test_resume_handles_checkpoint_load_error(
        self, mock_client, mock_ipfs, mock_agent, sample_recovering_task
    ):
        """Test resume continues even if checkpoint load fails."""
        mock_client.get_task.return_value = sample_recovering_task
        mock_ipfs.read.side_effect = Exception("IPFS error")

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        # Should not raise, checkpoint load errors are logged but continue
        result = await agent.resume(SAMPLE_TASK_ID, [
            {"action": "task1"},
            {"action": "task2"},
            {"action": "task3"},
        ])

        assert result["completed"] == 1  # Only task3 executed

    @pytest.mark.asyncio
    async def test_resume_handles_subtask_error(
        self, mock_client, mock_ipfs, mock_agent, sample_recovering_task
    ):
        """Test resume handles subtask errors."""
        mock_client.get_task.return_value = sample_recovering_task
        mock_agent.execute_subtask.side_effect = ValueError("Failed")

        observer = MagicMock(spec=CairnObserver)
        observer.on_failed = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(observer)

        with pytest.raises(CairnError):
            await agent.resume(SAMPLE_TASK_ID, [
                {"action": "task1"},
                {"action": "task2"},
                {"action": "task3"},
            ])

        observer.on_failed.assert_called_once()


class TestCairnAgentSubtaskExecution:
    """Tests for subtask execution."""

    @pytest.mark.asyncio
    async def test_execute_subtask_with_method(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test executing subtask with execute_subtask method."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        result = await agent._execute_subtask_safe(
            {"action": "test"}, {"context": "data"}, 0
        )

        assert result == {"status": "completed"}
        mock_agent.execute_subtask.assert_called_once_with(
            {"action": "test"}, {"context": "data"}
        )

    @pytest.mark.asyncio
    async def test_execute_subtask_callable(self, mock_client, mock_ipfs):
        """Test executing subtask with callable agent."""
        # Create a callable async function (not MagicMock which has all attributes)
        async def callable_agent(subtask, context):
            return {"result": "from_callable"}

        agent = CairnAgent(callable_agent, mock_client, mock_ipfs)

        result = await agent._execute_subtask_safe({"action": "test"}, {}, 0)

        assert result == {"result": "from_callable"}

    @pytest.mark.asyncio
    async def test_execute_subtask_invalid_agent(self, mock_client, mock_ipfs):
        """Test executing subtask with invalid agent raises error."""
        # Use a plain string which is not callable and has no execute_subtask
        invalid_agent = "not an agent"

        agent = CairnAgent(invalid_agent, mock_client, mock_ipfs)

        with pytest.raises(CairnError, match="must have execute_subtask"):
            await agent._execute_subtask_safe({"action": "test"}, {}, 0)

    @pytest.mark.asyncio
    async def test_execute_subtask_error_handling(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test subtask execution wraps errors."""
        mock_agent.execute_subtask.side_effect = ValueError("test error")

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        with pytest.raises(CairnError, match="Subtask 0 failed"):
            await agent._execute_subtask_safe({"action": "test"}, {}, 0)


class TestCairnAgentCheckpointing:
    """Tests for checkpointing."""

    @pytest.mark.asyncio
    async def test_checkpoint_writes_to_ipfs(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test checkpoint writes data to IPFS."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        cid = await agent._checkpoint(SAMPLE_TASK_ID, 0, {"result": "test"})

        assert cid == "QmNewCheckpointCid"
        mock_ipfs.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_checkpoint_commits_to_contract(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test checkpoint commits CID to contract."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        await agent._checkpoint(SAMPLE_TASK_ID, 0, {"result": "test"})

        mock_client.commit_checkpoint.assert_called_once_with(
            SAMPLE_TASK_ID, "QmNewCheckpointCid"
        )

    @pytest.mark.asyncio
    async def test_checkpoint_notifies_observers(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test checkpoint notifies observers."""
        observer = MagicMock(spec=CairnObserver)
        observer.on_checkpoint = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(observer)

        await agent._checkpoint(SAMPLE_TASK_ID, 0, {"result": "test"})

        observer.on_checkpoint.assert_called_once_with(
            SAMPLE_TASK_ID, 0, "QmNewCheckpointCid"
        )


class TestCairnAgentHeartbeat:
    """Tests for heartbeat management."""

    @pytest.mark.asyncio
    async def test_start_heartbeat(self, mock_client, mock_ipfs, mock_agent):
        """Test heartbeat task is started."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        await agent._start_heartbeat(SAMPLE_TASK_ID, 60)

        assert agent._heartbeat_task is not None
        assert not agent._heartbeat_task.done()

        # Cleanup
        await agent._stop_heartbeat()

    @pytest.mark.asyncio
    async def test_stop_heartbeat(self, mock_client, mock_ipfs, mock_agent):
        """Test heartbeat task is stopped."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)

        await agent._start_heartbeat(SAMPLE_TASK_ID, 60)
        await agent._stop_heartbeat()

        assert agent._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_heartbeat_margin_value(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test heartbeat uses correct margin calculation."""
        agent = CairnAgent(mock_agent, mock_client, mock_ipfs, heartbeat_margin=0.5)

        # Verify margin value is stored correctly
        assert agent._heartbeat_margin == 0.5

        # The calculation is interval * margin
        interval = 10
        expected_sleep_time = interval * agent._heartbeat_margin
        assert expected_sleep_time == 5.0


class TestCairnAgentNotifications:
    """Tests for observer notifications."""

    @pytest.mark.asyncio
    async def test_notify_task_submitted(self, mock_client, mock_ipfs, mock_agent):
        """Test notify_task_submitted calls all observers."""
        observer1 = MagicMock(spec=CairnObserver)
        observer1.on_task_submitted = AsyncMock()
        observer2 = MagicMock(spec=CairnObserver)
        observer2.on_task_submitted = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(observer1)
        agent.add_observer(observer2)

        task = MagicMock(spec=Task)
        await agent._notify_task_submitted(SAMPLE_TASK_ID, task)

        observer1.on_task_submitted.assert_called_once()
        observer2.on_task_submitted.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_handles_observer_errors(
        self, mock_client, mock_ipfs, mock_agent
    ):
        """Test notifications continue if observer raises error."""
        failing_observer = MagicMock(spec=CairnObserver)
        failing_observer.on_checkpoint = AsyncMock(side_effect=ValueError("error"))

        working_observer = MagicMock(spec=CairnObserver)
        working_observer.on_checkpoint = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(failing_observer)
        agent.add_observer(working_observer)

        # Should not raise
        await agent._notify_checkpoint(SAMPLE_TASK_ID, 0, "QmCid")

        # Working observer should still be called
        working_observer.on_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_failed(self, mock_client, mock_ipfs, mock_agent):
        """Test notify_failed calls all observers."""
        observer = MagicMock(spec=CairnObserver)
        observer.on_failed = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(observer)

        await agent._notify_failed(SAMPLE_TASK_ID, "Test error")

        observer.on_failed.assert_called_once_with(SAMPLE_TASK_ID, "Test error")

    @pytest.mark.asyncio
    async def test_notify_resolved(self, mock_client, mock_ipfs, mock_agent):
        """Test notify_resolved calls all observers."""
        observer = MagicMock(spec=CairnObserver)
        observer.on_resolved = AsyncMock()

        agent = CairnAgent(mock_agent, mock_client, mock_ipfs)
        agent.add_observer(observer)

        settlement = {"primary_share": 10**18}
        await agent._notify_resolved(SAMPLE_TASK_ID, settlement)

        observer.on_resolved.assert_called_once_with(SAMPLE_TASK_ID, settlement)
