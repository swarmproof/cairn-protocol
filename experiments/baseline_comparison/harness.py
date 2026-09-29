"""Benchmark harness: virtual clock, cost meter, step executor and metric computation.

Every system executes task steps through :func:`execute_step`, which advances a
per-run virtual clock, charges a budget-capped cost meter, consults the fault
injector, and records a trace. Metrics are computed from that trace, so every
system is measured the same way.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .faults import (
    FAULT_ORDER,
    PROFILES,
    PROGRESS_POINTS,
    FaultInjector,
    FaultKind,
    FiredEvent,
    InjectedFault,
    Supervisor,
    detection_latency,
    ground_truth_recoverable,
)
from .task import STEPS, TOTAL_COST, compute_step, initial_context, reference_output

# ── Economic / timing parameters (virtual units) ──────────────────────────────
ESCROW = 2.0 * TOTAL_COST  # 20 cost units; also the hard budget for every system
CREATED_AT = 0.0
DEADLINE = 30.0  # CAIRN task deadline == success window
SUCCESS_WINDOW_S = 30.0
PROCESS_RESTART_S = 0.5  # same-worker process restart
TX_LATENCY_S = 2.0  # one Base block for the failure / routing transaction
FALLBACK_STARTUP_S = 1.0  # fallback worker starts and loads the last checkpoint


class VirtualClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def advance(self, dt: float) -> None:
        if dt < 0:
            raise ValueError("time does not run backwards")
        self.now = round(self.now + dt, 9)


class CostMeter:
    """Accrued resource cost with a hard budget shared by all workers of a task."""

    def __init__(self, budget: float) -> None:
        self.budget = budget
        self.accrued = 0.0

    @property
    def exhausted(self) -> bool:
        return self.accrued >= self.budget

    def charge(self, amount: float) -> None:
        self.accrued = round(self.accrued + amount, 9)


@dataclass
class StepExec:
    index: int
    worker: str
    start: float
    end: float
    ok: bool


@dataclass
class RunContext:
    task_id: str
    injector: FaultInjector
    escrow: float = ESCROW  # CAIRN escrow; also the hard cost budget for every system
    clock: VirtualClock = field(default_factory=VirtualClock)
    meter: CostMeter = field(init=False)
    trace: List[StepExec] = field(default_factory=list)
    committed_checkpoints: int = 0  # maintained by checkpointing systems

    def __post_init__(self) -> None:
        self.meter = CostMeter(self.escrow)

    def initial_context(self) -> Dict[str, Any]:
        return initial_context(self.task_id)


def execute_step(rc: RunContext, index: int, context: Dict[str, Any], worker: str) -> Any:
    """Run one step on the virtual clock. Raises InjectedFault when a fault fires."""
    step = STEPS[index]
    t0 = rc.clock.now
    if rc.meter.exhausted or rc.meter.accrued + step.cost > rc.meter.budget:
        rc.injector.record(FiredEvent(index, worker, t0, rc.committed_checkpoints, refused=True))
        rc.trace.append(StepExec(index, worker, t0, t0, False))
        raise InjectedFault(FaultKind.BUDGET_EXHAUSTION, index, refused=True)
    if rc.injector.should_fire(index):
        kind = rc.injector.kind
        p = PROFILES[kind]
        elapsed = step.duration * p.elapsed_fraction + p.fixed_elapsed
        if kind is FaultKind.BUDGET_EXHAUSTION:
            charge = rc.meter.budget - rc.meter.accrued  # runaway spends the rest
        else:
            charge = step.cost * p.cost_fraction
        rc.clock.advance(elapsed)
        rc.meter.charge(charge)
        rc.injector.record(FiredEvent(index, worker, rc.clock.now, rc.committed_checkpoints))
        rc.trace.append(StepExec(index, worker, t0, rc.clock.now, False))
        raise InjectedFault(kind, index)
    output = compute_step(index, copy.deepcopy(context))
    rc.clock.advance(step.duration)
    rc.meter.charge(step.cost)
    rc.trace.append(StepExec(index, worker, t0, rc.clock.now, True))
    return output


def wait_detection(rc: RunContext, fault: InjectedFault, supervisor: Supervisor) -> None:
    rc.clock.advance(detection_latency(fault.kind, supervisor, fault.refused))


@dataclass
class SystemOutcome:
    """What a system wrapper returns; the harness derives every metric from it."""

    output: Optional[Any]
    recovery_attempts: int
    disputed: Optional[bool] = None  # CAIRN only
    settlement: Optional[Dict[str, float]] = None  # CAIRN only
    decisions: List[Dict[str, Any]] = field(default_factory=list)  # CAIRN only


class System:
    name: str = ""
    label: str = ""
    mode: str = "real"  # real | emulated | model
    different_worker: Optional[bool] = False  # design property, not a measurement
    uses_escrow: bool = False

    def open(self) -> None:  # optional per-benchmark setup
        pass

    def close(self) -> None:
        pass

    def run(self, rc: RunContext) -> SystemOutcome:
        raise NotImplementedError


def _r(x: Optional[float], nd: int = 4) -> Optional[float]:
    return None if x is None else round(float(x), nd)


def evaluate(system: System, rc: RunContext, outcome: SystemOutcome) -> Dict[str, Any]:
    kind = rc.injector.kind
    point = rc.injector.point
    ref = reference_output(rc.task_id)
    finished = rc.clock.now
    success = outcome.output == ref and finished <= SUCCESS_WINDOW_S
    attempted = outcome.recovery_attempts > 0
    recoverable = ground_truth_recoverable(kind) if kind is not None else None
    fault_time = rc.injector.first_fault_time

    execs: Dict[int, int] = {}
    for e in rc.trace:
        execs[e.index] = execs.get(e.index, 0) + 1
    if kind is not None and success:
        reused = sum(1 for i in range(point) if execs.get(i, 0) == 1)
        work_preserved = reused / point
    elif kind is not None:
        work_preserved = 0.0
    else:
        work_preserved = None

    if success:
        operator_loss = 0.0
    elif system.uses_escrow and outcome.settlement is not None:
        operator_loss = rc.escrow - outcome.settlement["operator_refund"]
    else:
        operator_loss = rc.meter.accrued

    fired = [e for e in rc.injector.fired if not e.refused]
    return {
        "system": system.name,
        "fault": kind.value if kind is not None else "none",
        "point": point if kind is not None else 0,
        "recoverable_ground_truth": recoverable,
        "success": success,
        "recovery_attempted": attempted,
        "recovery_attempts": outcome.recovery_attempts,
        "false_recovery": bool(kind is not None and attempted and not success),
        "missed_recovery": bool(kind is not None and recoverable and not attempted),
        "work_preserved": _r(work_preserved),
        "time_to_recovery": _r(finished - fault_time) if (success and fault_time is not None) else None,
        "completion_time": _r(finished),
        "resource_cost": _r(rc.meter.accrued),
        "step_executions": len(rc.trace),
        "disputed": outcome.disputed,
        "operator_loss": _r(operator_loss),
        "settlement": outcome.settlement,
        "decisions": outcome.decisions,
        "fault_fired_at_step": fired[0].step_index if fired else None,
        "checkpoints_before_fault": fired[0].checkpoints_before if fired else None,
        "workers": sorted({e.worker for e in rc.trace}),
    }


def run_one(
    system: System, kind: Optional[FaultKind], point: int, escrow: float = ESCROW
) -> Dict[str, Any]:
    task_id = f"task-{kind.value if kind else 'none'}-p{point}"
    rc = RunContext(task_id=task_id, injector=FaultInjector(kind, point), escrow=escrow)
    outcome = system.run(rc)
    return evaluate(system, rc, outcome)


def run_benchmark(systems: List[System]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for system in systems:
        system.open()
        try:
            rows.append(run_one(system, None, 0))  # no-fault control
            for kind in FAULT_ORDER:
                for point in PROGRESS_POINTS:
                    rows.append(run_one(system, kind, point))
        finally:
            system.close()
    return rows
