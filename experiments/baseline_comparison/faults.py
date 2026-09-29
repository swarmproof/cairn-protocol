"""Fault catalogue, ground truth, detection latencies and the fault injector.

A fault at *progress point p* (p in 1..4) fires during step index p (0-based),
i.e. after steps 1..p have completed and p checkpoints exist.

Transient faults (crash, hang, 429, upstream timeout) fire on the first execution
of the faulted step only; any later execution of that step, by any worker,
succeeds. Deterministic faults (schema mismatch, verifier rejection) fire on
every execution of the faulted step, by any worker. Budget exhaustion is a
runaway step that drives accrued cost up to the budget (= escrow); once the budget
is spent the shared cost meter refuses every further step for every worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .task import STEPS

PROGRESS_POINTS: Tuple[int, ...] = (1, 2, 3, 4)

# ── Detection constants (virtual seconds) ──────────────────────────────────────
PROCESS_EXIT_DETECT_S = 0.5  # a local supervisor observes the process exit
STEP_TIMEOUT_S = 3.0  # no-progress timeout used by every supervisor
HEARTBEAT_TIMEOUT_S = 3.0  # remote liveness timeout (CAIRN heartbeat, Temporal activity)


class FaultKind(str, Enum):
    CRASH = "process_crash"
    HANG = "hang"
    RATE_LIMIT = "rate_limit_429"
    UPSTREAM_TIMEOUT = "upstream_timeout"
    BUDGET_EXHAUSTION = "budget_exhaustion"
    SCHEMA_MISMATCH = "schema_mismatch"
    VERIFIER_REJECTION = "verifier_rejection"


FAULT_ORDER: Tuple[FaultKind, ...] = tuple(FaultKind)


class Supervisor(str, Enum):
    """How a system notices a failure."""

    LOCAL = "local"  # in-process / host supervisor: sees exceptions and process exits
    REMOTE = "remote"  # only sees missed heartbeats / activity timeouts and reports


@dataclass(frozen=True)
class FaultProfile:
    kind: FaultKind
    transient: bool
    recoverable: bool  # ground truth: resuming from the last checkpoint succeeds
    cairn_evidence: str  # HEARTBEAT_TIMEOUT or AGENT_REPORT
    cairn_report_type: Optional[str]  # FailureType for AGENT_REPORT evidence
    elapsed_fraction: float  # share of the step's duration consumed before failing
    fixed_elapsed: float  # extra virtual seconds before the failure surfaces
    cost_fraction: float  # share of the step's cost charged to the failed attempt
    silent: bool  # no error surfaces; must be detected by timeout / heartbeat
    process_exit: bool  # the worker process dies (in-memory state lost)


PROFILES: Dict[FaultKind, FaultProfile] = {
    FaultKind.CRASH: FaultProfile(
        FaultKind.CRASH, True, True, "HEARTBEAT_TIMEOUT", None, 0.5, 0.0, 0.5, True, True
    ),
    FaultKind.HANG: FaultProfile(
        FaultKind.HANG, True, True, "HEARTBEAT_TIMEOUT", None, 0.0, 0.0, 1.0, True, False
    ),
    FaultKind.RATE_LIMIT: FaultProfile(
        FaultKind.RATE_LIMIT, True, True, "AGENT_REPORT", "RATE_LIMIT", 0.0, 0.1, 0.0, False, False
    ),
    FaultKind.UPSTREAM_TIMEOUT: FaultProfile(
        FaultKind.UPSTREAM_TIMEOUT,
        True,
        True,
        "AGENT_REPORT",
        "UPSTREAM_TIMEOUT",
        0.0,
        2.0,
        1.0,
        False,
        False,
    ),
    FaultKind.BUDGET_EXHAUSTION: FaultProfile(
        FaultKind.BUDGET_EXHAUSTION,
        False,
        False,
        "HEARTBEAT_TIMEOUT",
        None,
        1.0,
        0.0,
        0.0,  # the runaway charge is the remaining budget, applied separately
        True,
        False,
    ),
    FaultKind.SCHEMA_MISMATCH: FaultProfile(
        FaultKind.SCHEMA_MISMATCH,
        False,
        False,
        "AGENT_REPORT",
        "SCHEMA_MISMATCH",
        0.0,
        0.0,
        0.0,
        False,
        False,
    ),
    FaultKind.VERIFIER_REJECTION: FaultProfile(
        FaultKind.VERIFIER_REJECTION,
        False,
        False,
        "AGENT_REPORT",
        "VALIDATION_FAILED",
        1.0,
        0.0,
        1.0,
        False,
        False,
    ),
}


def ground_truth_recoverable(kind: FaultKind) -> bool:
    return PROFILES[kind].recoverable


def detection_latency(kind: FaultKind, supervisor: Supervisor, refused: bool = False) -> float:
    """Virtual seconds between the failure moment and the supervisor noticing it."""
    if refused:  # the cost meter rejected the step up front: an immediate error
        return 0.0
    p = PROFILES[kind]
    if not p.silent:
        return 0.0
    if p.process_exit and supervisor is Supervisor.LOCAL:
        return PROCESS_EXIT_DETECT_S
    return STEP_TIMEOUT_S if supervisor is Supervisor.LOCAL else HEARTBEAT_TIMEOUT_S


class InjectedFault(Exception):
    """Raised by the step executor when a fault fires (or the budget is spent)."""

    def __init__(self, kind: FaultKind, step_index: int, refused: bool = False) -> None:
        super().__init__(f"{kind.value} at step {step_index}")
        self.kind = kind
        self.step_index = step_index
        self.refused = refused  # True: cost meter refused the step (budget already spent)

    @property
    def process_exit(self) -> bool:
        return PROFILES[self.kind].process_exit and not self.refused


@dataclass
class FiredEvent:
    step_index: int
    worker: str
    time: float  # virtual time the failure occurred
    checkpoints_before: int
    refused: bool = False


@dataclass
class FaultInjector:
    kind: Optional[FaultKind]
    point: int = 0  # progress point; the fault fires in step index == point
    fired: List[FiredEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind is not None and self.point not in PROGRESS_POINTS:
            raise ValueError(f"progress point must be one of {PROGRESS_POINTS}")

    @property
    def profile(self) -> Optional[FaultProfile]:
        return PROFILES[self.kind] if self.kind is not None else None

    def should_fire(self, step_index: int) -> bool:
        if self.kind is None or step_index != self.point:
            return False
        p = PROFILES[self.kind]
        if p.transient or self.kind is FaultKind.BUDGET_EXHAUSTION:
            return not any(not e.refused for e in self.fired)
        return True  # deterministic faults fire on every execution

    def record(self, event: FiredEvent) -> None:
        self.fired.append(event)

    @property
    def first_fault_time(self) -> Optional[float]:
        for e in self.fired:
            if not e.refused:
                return e.time
        return None


def fault_step(point: int):
    return STEPS[point]
