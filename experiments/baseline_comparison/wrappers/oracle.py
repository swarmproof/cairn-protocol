"""Oracle: knows the ground truth. On a failure it resumes from the last checkpoint
with zero detection and restart latency exactly when resuming would succeed, and
does nothing otherwise. It bounds every other system; it is not implementable."""

from __future__ import annotations

from ..faults import InjectedFault, ground_truth_recoverable
from ..harness import RunContext, System, SystemOutcome
from ..schema import CheckpointStore
from ..task import STEPS
from . import run_steps


class OracleSystem(System):
    name = "oracle"
    label = "Oracle"
    mode = "model"
    different_worker = None  # not applicable

    def run(self, rc: RunContext) -> SystemOutcome:
        store = CheckpointStore()
        try:
            ctx = run_steps(rc, 0, rc.initial_context(), "worker-1", store)
            return SystemOutcome(ctx[STEPS[-1].name], 0)
        except InjectedFault as f:
            if not ground_truth_recoverable(f.kind):
                return SystemOutcome(None, 0)
        cp = store.latest(rc.task_id)
        start = cp.subtask_index + 1 if cp else 0
        ctx = dict(cp.context) if cp else rc.initial_context()
        try:
            ctx = run_steps(rc, start, ctx, "worker-1", store)
            return SystemOutcome(ctx[STEPS[-1].name], 1)
        except InjectedFault:
            return SystemOutcome(None, 1)
