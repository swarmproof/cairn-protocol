"""Off-chain mirror of CAIRN's v2 failure classification, recovery scoring,
three-tier routing and settlement (CairnCore + RecoveryRouterV2).

Classification (evidence -> class / type):
    DEADLINE_EXPIRED      -> RESOURCE / DEADLINE_EXCEEDED
    AGENT_REPORT(type)    -> class of that type
    HEARTBEAT_TIMEOUT     -> RESOURCE / BUDGET_EXHAUSTED  if costAccrued >= escrow
                             LIVENESS / HEARTBEAT_MISS    otherwise
Checkpoint count never affects the class.

Score:   r = F^0.80 * B^0.35 * D^0.15
    F = 0.70 LIVENESS, 0.30 RESOURCE, 0.00 LOGIC
    B = (escrow - cost) / escrow, 0 when cost >= escrow
    D = (deadline - now) / (deadline - createdAt), 0 at/after the deadline

Routing: r >= 0.40 FULL; 0.35 <= r < 0.40 REDUCED; r < 0.35 DISPUTED.
    Past the deadline -> DISPUTED. At most one fallback attempt; a failure of the
    fallback -> DISPUTED.

Settlement: distributable = escrow * 0.995 (50 bps protocol fee), split between
primary and fallback in proportion to checkpoints committed. REDUCED caps the
fallback at 50% of distributable and refunds the excess to the operator. A dispute
with no arbiter ruling resolves by timeout with the full escrow refunded to the
operator.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FailureClass(str, Enum):
    LIVENESS = "LIVENESS"
    RESOURCE = "RESOURCE"
    LOGIC = "LOGIC"


FAILURE_TYPES = {
    FailureClass.LIVENESS: ("HEARTBEAT_MISS", "NETWORK_PARTITION", "NODE_CRASH"),
    FailureClass.LOGIC: ("VALIDATION_FAILED", "SCHEMA_MISMATCH", "INVARIANT_VIOLATION"),
    FailureClass.RESOURCE: (
        "RATE_LIMIT",
        "GAS_EXHAUSTED",
        "UPSTREAM_TIMEOUT",
        "BUDGET_EXHAUSTED",
        "DEADLINE_EXCEEDED",
    ),
}
TYPE_TO_CLASS = {t: c for c, ts in FAILURE_TYPES.items() for t in ts}

EVIDENCE_TYPES = ("HEARTBEAT_TIMEOUT", "AGENT_REPORT", "DEADLINE_EXPIRED")

CLASS_WEIGHT = {
    FailureClass.LIVENESS: 0.70,
    FailureClass.RESOURCE: 0.30,
    FailureClass.LOGIC: 0.00,
}
F_EXPONENT = 0.80
B_EXPONENT = 0.35
D_EXPONENT = 0.15

UPPER_THRESHOLD = 0.40
LOWER_THRESHOLD = 0.35

PROTOCOL_FEE_BPS = 50
REDUCED_SCOPE_CAP_BPS = 5000
MAX_FALLBACK_ATTEMPTS = 1


class Tier(str, Enum):
    FULL = "FULL"
    REDUCED = "REDUCED"
    DISPUTED = "DISPUTED"


def classify(
    evidence: str,
    report_type: Optional[str] = None,
    cost_accrued: float = 0.0,
    escrow: float = 0.0,
    checkpoint_count: int = 0,  # accepted and ignored: count never changes the class
) -> tuple:
    """Return (FailureClass, failure_type) for a piece of evidence."""
    if evidence == "DEADLINE_EXPIRED":
        return FailureClass.RESOURCE, "DEADLINE_EXCEEDED"
    if evidence == "AGENT_REPORT":
        if report_type not in TYPE_TO_CLASS:
            raise ValueError(f"unknown failure type {report_type!r}")
        return TYPE_TO_CLASS[report_type], report_type
    if evidence == "HEARTBEAT_TIMEOUT":
        if cost_accrued >= escrow:
            return FailureClass.RESOURCE, "BUDGET_EXHAUSTED"
        return FailureClass.LIVENESS, "HEARTBEAT_MISS"
    raise ValueError(f"unknown evidence {evidence!r}")


def budget_factor(escrow: float, cost_accrued: float) -> float:
    if escrow <= 0 or cost_accrued >= escrow:
        return 0.0
    return (escrow - cost_accrued) / escrow


def deadline_factor(deadline: float, now: float, created_at: float) -> float:
    if now >= deadline or deadline <= created_at:
        return 0.0
    return (deadline - now) / (deadline - created_at)


def recovery_score(failure_class: FailureClass, b: float, d: float) -> float:
    f = CLASS_WEIGHT[failure_class]
    if f == 0.0 or b <= 0.0 or d <= 0.0:
        return 0.0
    return (f**F_EXPONENT) * (b**B_EXPONENT) * (d**D_EXPONENT)


def route(score: float, now: float, deadline: float) -> Tier:
    if now >= deadline:
        return Tier.DISPUTED
    if score >= UPPER_THRESHOLD:
        return Tier.FULL
    if score >= LOWER_THRESHOLD:
        return Tier.REDUCED
    return Tier.DISPUTED


@dataclass(frozen=True)
class Decision:
    failure_class: FailureClass
    failure_type: str
    b: float
    d: float
    score: float
    tier: Tier


def decide(
    evidence: str,
    report_type: Optional[str],
    cost_accrued: float,
    escrow: float,
    now: float,
    created_at: float,
    deadline: float,
    fallback_attempts_so_far: int = 0,
    checkpoint_count: int = 0,
) -> Decision:
    cls, ftype = classify(evidence, report_type, cost_accrued, escrow, checkpoint_count)
    b = budget_factor(escrow, cost_accrued)
    d = deadline_factor(deadline, now, created_at)
    r = recovery_score(cls, b, d)
    tier = route(r, now, deadline)
    if fallback_attempts_so_far >= MAX_FALLBACK_ATTEMPTS:
        tier = Tier.DISPUTED
    return Decision(cls, ftype, b, d, r, tier)


@dataclass(frozen=True)
class Settlement:
    primary: float
    fallback: float
    operator_refund: float
    protocol_fee: float

    def as_dict(self) -> dict:
        return {
            "primary": round(self.primary, 6),
            "fallback": round(self.fallback, 6),
            "operator_refund": round(self.operator_refund, 6),
            "protocol_fee": round(self.protocol_fee, 6),
        }


def settle_resolved(
    escrow: float,
    primary_checkpoints: int,
    fallback_checkpoints: int,
    tier: Optional[Tier],
    completed_by_primary: bool = False,
) -> Settlement:
    fee = escrow * PROTOCOL_FEE_BPS / 10000
    distributable = escrow - fee
    total = primary_checkpoints + fallback_checkpoints
    if total > 0:
        primary = distributable * primary_checkpoints / total
        fallback = distributable - primary
    elif completed_by_primary:
        primary, fallback = distributable, 0.0
    else:
        primary, fallback = 0.0, distributable
    refund = 0.0
    if tier is Tier.REDUCED:
        cap = distributable * REDUCED_SCOPE_CAP_BPS / 10000
        if fallback > cap:
            refund = fallback - cap
            fallback = cap
    return Settlement(primary, fallback, refund, fee)


def settle_dispute_timeout(escrow: float) -> Settlement:
    return Settlement(0.0, 0.0, escrow, 0.0)
