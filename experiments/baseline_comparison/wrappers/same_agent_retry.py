"""Same-agent retry: the worker keeps step outputs in memory and retries a failed
step up to ``MAX_RETRIES_PER_STEP`` times with exponential backoff (1 s, 2 s).

A process crash loses the in-memory state, so the worker restarts the whole task
(up to ``MAX_RESTARTS`` times). No persistent checkpoints."""

from __future__ import annotations

from ..faults import InjectedFault, Supervisor
from ..harness import PROCESS_RESTART_S, RunContext, System, SystemOutcome, execute_step, wait_detection
from ..task import N_STEPS, STEPS

MAX_RETRIES_PER_STEP = 2
MAX_RESTARTS = 2
BACKOFF_S = (1.0, 2.0)


class SameAgentRetrySystem(System):
    name = "same_agent_retry"
    label = "Same-agent retry"
    mode = "model"
    different_worker = False

    def run(self, rc: RunContext) -> SystemOutcome:
        attempts = 0
        restarts = 0
        ctx = rc.initial_context()
        i = 0
        retries_here = 0
        while i < N_STEPS:
            try:
                ctx[STEPS[i].name] = execute_step(rc, i, ctx, "worker-1")
                i += 1
                retries_here = 0
            except InjectedFault as f:
                wait_detection(rc, f, Supervisor.LOCAL)
                if f.process_exit:
                    if restarts >= MAX_RESTARTS:
                        return SystemOutcome(None, attempts)
                    restarts += 1
                    attempts += 1
                    rc.clock.advance(PROCESS_RESTART_S)
                    ctx, i, retries_here = rc.initial_context(), 0, 0
                    continue
                if retries_here >= MAX_RETRIES_PER_STEP:
                    return SystemOutcome(None, attempts)
                rc.clock.advance(BACKOFF_S[retries_here])
                retries_here += 1
                attempts += 1
        return SystemOutcome(ctx[STEPS[-1].name], attempts)
