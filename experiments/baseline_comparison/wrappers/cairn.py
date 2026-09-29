"""CAIRN: primary agent checkpoints every step; on failure the evidence is
classified and scored by the v2 decision model (``cairn_model``); FULL / REDUCED
routes assign a *different* worker (the fallback) that resumes from the last
committed checkpoint; DISPUTED ends automated recovery. At most one fallback.

Timing: silent failures are detected by heartbeat timeout; agent-reported ones
immediately. The failure/routing transaction takes one block (TX_LATENCY_S); the
fallback then starts and loads the checkpoint (FALLBACK_STARTUP_S). The score is
evaluated at the block in which the failure transaction lands.

Disputes are settled on the timeout path (no arbiter ruling): the full escrow is
refunded to the operator. On-chain, that path requires the 7-day dispute timeout,
which is outside the benchmark's 30 s success window either way.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .. import cairn_model as cm
from ..faults import PROFILES, InjectedFault, Supervisor
from ..harness import (
    CREATED_AT,
    DEADLINE,
    FALLBACK_STARTUP_S,
    TX_LATENCY_S,
    RunContext,
    System,
    SystemOutcome,
    wait_detection,
)
from ..schema import CheckpointStore
from ..task import STEPS
from . import run_steps

PRIMARY = "primary-agent"
FALLBACK = "fallback-agent"


def _evidence(fault: InjectedFault):
    if fault.refused:  # the meter refused the step: the budget is gone
        return "HEARTBEAT_TIMEOUT", None
    p = PROFILES[fault.kind]
    return p.cairn_evidence, p.cairn_report_type


class CairnSystem(System):
    name = "cairn"
    label = "CAIRN"
    mode = "model"  # off-chain mirror of the contract decision rules
    different_worker = True
    uses_escrow = True

    def _decide(self, rc: RunContext, fault: InjectedFault, fallbacks: int) -> cm.Decision:
        evidence, rtype = _evidence(fault)
        wait_detection(rc, fault, Supervisor.REMOTE)
        rc.clock.advance(TX_LATENCY_S)
        return cm.decide(
            evidence,
            rtype,
            rc.meter.accrued,
            rc.escrow,
            rc.clock.now,
            CREATED_AT,
            DEADLINE,
            fallback_attempts_so_far=fallbacks,
            checkpoint_count=rc.committed_checkpoints,
        )

    @staticmethod
    def _log(decision: cm.Decision, rc: RunContext, evidence: str, who: str) -> Dict[str, Any]:
        return {
            "failed_worker": who,
            "evidence": evidence,
            "class": decision.failure_class.value,
            "type": decision.failure_type,
            "B": round(decision.b, 4),
            "D": round(decision.d, 4),
            "r": round(decision.score, 4),
            "tier": decision.tier.value,
            "decided_at": round(rc.clock.now, 4),
            "cost_at_decision": round(rc.meter.accrued, 4),
        }

    def run(self, rc: RunContext) -> SystemOutcome:
        store = CheckpointStore()
        decisions: List[Dict[str, Any]] = []
        try:
            ctx = run_steps(rc, 0, rc.initial_context(), PRIMARY, store)
            s = cm.settle_resolved(rc.escrow, store.count(rc.task_id), 0, None, True)
            return SystemOutcome(ctx[STEPS[-1].name], 0, False, s.as_dict(), decisions)
        except InjectedFault as f:
            primary_cps = store.count(rc.task_id)
            d = self._decide(rc, f, fallbacks=0)
            decisions.append(self._log(d, rc, _evidence(f)[0], PRIMARY))
        if d.tier is cm.Tier.DISPUTED:
            s = cm.settle_dispute_timeout(rc.escrow)
            return SystemOutcome(None, 0, True, s.as_dict(), decisions)

        tier = d.tier
        rc.clock.advance(FALLBACK_STARTUP_S)
        cp = store.latest(rc.task_id)
        start = cp.subtask_index + 1 if cp else 0
        ctx = dict(cp.context) if cp else rc.initial_context()
        try:
            ctx = run_steps(rc, start, ctx, FALLBACK, store)
        except InjectedFault as f2:
            d2 = self._decide(rc, f2, fallbacks=1)
            decisions.append(self._log(d2, rc, _evidence(f2)[0], FALLBACK))
            s = cm.settle_dispute_timeout(rc.escrow)
            return SystemOutcome(None, 1, True, s.as_dict(), decisions)
        fallback_cps = store.count(rc.task_id) - primary_cps
        s = cm.settle_resolved(rc.escrow, primary_cps, fallback_cps, tier)
        return SystemOutcome(ctx[STEPS[-1].name], 1, False, s.as_dict(), decisions)
