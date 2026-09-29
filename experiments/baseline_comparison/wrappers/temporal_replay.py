"""Temporal: a workflow that runs the five steps as activities, executed against
Temporal's time-skipping test server (``WorkflowEnvironment.start_time_skipping``).

Each activity has ``RetryPolicy(maximum_attempts=3, backoff_coefficient=2.0)``;
completed activity results live in workflow history, so a retry re-runs only the
failed activity and earlier results are replayed from history, never
re-executed. Same worker (task queue) throughout.

Failure detection follows Temporal's server-side model: an error raised by the
activity is seen immediately; a crashed or hung worker is seen only when the
activity timeout fires (``HEARTBEAT_TIMEOUT_S`` on the virtual clock). Faults are
surfaced to Temporal as activity failures after that virtual delay; the worker
process is not actually killed. Retry backoff is accounted on the virtual clock
as Temporal's default 1 s initial interval doubling per attempt, while the real
``initial_interval`` is set to 1 ms so the run does not wait on wall-clock time.

If ``temporalio`` is missing or the test server cannot start (it is downloaded on
first use), or ``BENCH_FORCE_EMULATION`` is set, an in-process emulation of the
same history-replay + activity-retry semantics is used and the system is
labelled ``emulated``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional

from ..faults import InjectedFault, Supervisor
from ..harness import RunContext, System, SystemOutcome, execute_step, wait_detection
from ..task import N_STEPS, STEPS

MAX_ATTEMPTS = 3
INITIAL_INTERVAL_S = 1.0  # virtual
BACKOFF_COEFFICIENT = 2.0
TASK_QUEUE = "cairn-benchmark"
WORKER = "worker-1"

try:
    if os.environ.get("BENCH_FORCE_EMULATION"):
        raise ImportError("emulation forced")
    from temporalio import activity, workflow
    from temporalio.client import WorkflowFailureError
    from temporalio.common import RetryPolicy
    from temporalio.exceptions import ApplicationError
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import UnsandboxedWorkflowRunner, Worker

    TEMPORAL_IMPORTABLE = True
except ImportError:  # pragma: no cover
    TEMPORAL_IMPORTABLE = False

# Run contexts reachable from in-process activities, keyed by workflow run id.
_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _backoff(attempt: int) -> float:
    """Virtual delay before attempt ``attempt`` (1-based) of an activity."""
    if attempt <= 1:
        return 0.0
    return INITIAL_INTERVAL_S * BACKOFF_COEFFICIENT ** (attempt - 2)


if TEMPORAL_IMPORTABLE:

    @activity.defn(name="run_step")
    async def run_step_activity(run_key: str, index: int, context: Dict[str, Any]) -> Any:
        entry = _REGISTRY[run_key]
        rc: RunContext = entry["rc"]
        attempt = activity.info().attempt
        if attempt > 1:
            entry["retries"] += 1
            rc.clock.advance(_backoff(attempt))
        try:
            return execute_step(rc, index, context, WORKER)
        except InjectedFault as f:
            wait_detection(rc, f, Supervisor.REMOTE)
            raise ApplicationError(str(f), type=f.kind.value) from None

    @workflow.defn(name="ToyTaskWorkflow", sandboxed=False)
    class ToyTaskWorkflow:
        @workflow.run
        async def run(self, run_key: str, context: Dict[str, Any]) -> Any:
            ctx = dict(context)
            for step in STEPS:
                ctx[step.name] = await workflow.execute_activity(
                    run_step_activity,
                    args=[run_key, step.index, ctx],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(milliseconds=1),
                        backoff_coefficient=BACKOFF_COEFFICIENT,
                        maximum_attempts=MAX_ATTEMPTS,
                    ),
                )
            return ctx[STEPS[-1].name]


class TemporalSystem(System):
    name = "temporal"
    label = "Temporal (activities + history)"
    different_worker = False

    def __init__(self) -> None:
        self.mode = "real" if TEMPORAL_IMPORTABLE else "emulated"
        self.emulation_reason: Optional[str] = None if TEMPORAL_IMPORTABLE else "import failed"
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._env = None
        self._worker = None
        self._worker_task = None
        self.versions: Dict[str, str] = {}
        if TEMPORAL_IMPORTABLE:
            from importlib.metadata import version

            self.versions = {"temporalio": version("temporalio")}

    def open(self) -> None:
        if self.mode != "real":
            return
        # Each injected fault is an expected activity failure; keep the log quiet.
        logging.getLogger("temporalio").setLevel(logging.ERROR)
        self._loop = asyncio.new_event_loop()
        try:
            self._loop.run_until_complete(self._start())
        except Exception as e:  # pragma: no cover - network / binary download issues
            self.mode = "emulated"
            self.emulation_reason = f"test server failed to start: {type(e).__name__}"
            self._loop.close()
            self._loop = None

    async def _start(self) -> None:
        self._env = await asyncio.wait_for(WorkflowEnvironment.start_time_skipping(), 90)
        self._worker = Worker(
            self._env.client,
            task_queue=TASK_QUEUE,
            workflows=[ToyTaskWorkflow],
            activities=[run_step_activity],
            workflow_runner=UnsandboxedWorkflowRunner(),
        )
        self._worker_task = asyncio.ensure_future(self._worker.run())

    async def _stop(self) -> None:
        await self._worker.shutdown()
        await self._worker_task
        await self._env.shutdown()

    def close(self) -> None:
        if self._loop is not None:
            self._loop.run_until_complete(self._stop())
            self._loop.close()
            self._loop = None

    async def _execute(self, rc: RunContext) -> SystemOutcome:
        key = f"{rc.task_id}-{uuid.uuid4().hex[:8]}"
        _REGISTRY[key] = {"rc": rc, "retries": 0}
        try:
            out = await self._env.client.execute_workflow(
                ToyTaskWorkflow.run,
                args=[key, rc.initial_context()],
                id=key,
                task_queue=TASK_QUEUE,
            )
            return SystemOutcome(out, _REGISTRY[key]["retries"])
        except WorkflowFailureError:
            return SystemOutcome(None, _REGISTRY[key]["retries"])
        finally:
            _REGISTRY.pop(key, None)

    def _run_emulated(self, rc: RunContext) -> SystemOutcome:
        history: List[Any] = []  # completed activity results, replayed on retry
        ctx = rc.initial_context()
        retries = 0
        for i in range(N_STEPS):
            for attempt in range(1, MAX_ATTEMPTS + 1):
                if attempt > 1:
                    retries += 1
                    rc.clock.advance(_backoff(attempt))
                try:
                    out = execute_step(rc, i, ctx, WORKER)
                    break
                except InjectedFault as f:
                    wait_detection(rc, f, Supervisor.REMOTE)
            else:
                return SystemOutcome(None, retries)
            history.append(out)
            ctx[STEPS[i].name] = out
        return SystemOutcome(ctx[STEPS[-1].name], retries)

    def run(self, rc: RunContext) -> SystemOutcome:
        if self.mode == "real":
            if self._loop is None:
                self.open()
            if self.mode == "real":
                return self._loop.run_until_complete(self._execute(rc))
        return self._run_emulated(rc)
