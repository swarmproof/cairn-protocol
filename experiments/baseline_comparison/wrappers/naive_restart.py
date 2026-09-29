"""Naive restart: no checkpoints; on any failure the same worker restarts the task
from step 1 after a process restart, up to ``MAX_RESTARTS`` times."""

from __future__ import annotations

from ..faults import InjectedFault, Supervisor
from ..harness import PROCESS_RESTART_S, RunContext, System, SystemOutcome, wait_detection
from ..task import STEPS
from . import run_steps

MAX_RESTARTS = 2


class NaiveRestartSystem(System):
    name = "naive_restart"
    label = "Naive restart"
    mode = "model"
    different_worker = False

    def run(self, rc: RunContext) -> SystemOutcome:
        restarts = 0
        while True:
            try:
                ctx = run_steps(rc, 0, rc.initial_context(), "worker-1")
                return SystemOutcome(ctx[STEPS[-1].name], restarts)
            except InjectedFault as f:
                wait_detection(rc, f, Supervisor.LOCAL)
                if restarts >= MAX_RESTARTS:
                    return SystemOutcome(None, restarts)
                restarts += 1
                rc.clock.advance(PROCESS_RESTART_S)
