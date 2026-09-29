import pytest

from experiments.baseline_comparison import cairn_model as m
from experiments.baseline_comparison.cairn_model import FailureClass, Tier


def test_worked_values():
    assert m.recovery_score(FailureClass.LIVENESS, 1.0, 1.0) == pytest.approx(0.7518, abs=5e-5)
    assert m.recovery_score(FailureClass.RESOURCE, 1.0, 1.0) == pytest.approx(0.3817, abs=5e-5)
    assert m.recovery_score(FailureClass.LOGIC, 1.0, 1.0) == 0.0


def test_matches_contract_lookup_constants():
    # RecoveryRouterV2 pre-computed F^0.80 lookups
    assert 0.70**0.80 == pytest.approx(0.751758646650045568, rel=1e-12)
    assert 0.30**0.80 == pytest.approx(0.381677890961817600, rel=1e-12)


@pytest.mark.parametrize(
    "rtype,cls",
    [
        ("HEARTBEAT_MISS", FailureClass.LIVENESS),
        ("NETWORK_PARTITION", FailureClass.LIVENESS),
        ("NODE_CRASH", FailureClass.LIVENESS),
        ("VALIDATION_FAILED", FailureClass.LOGIC),
        ("SCHEMA_MISMATCH", FailureClass.LOGIC),
        ("INVARIANT_VIOLATION", FailureClass.LOGIC),
        ("RATE_LIMIT", FailureClass.RESOURCE),
        ("GAS_EXHAUSTED", FailureClass.RESOURCE),
        ("UPSTREAM_TIMEOUT", FailureClass.RESOURCE),
        ("BUDGET_EXHAUSTED", FailureClass.RESOURCE),
        ("DEADLINE_EXCEEDED", FailureClass.RESOURCE),
    ],
)
def test_agent_report_class(rtype, cls):
    assert m.classify("AGENT_REPORT", rtype) == (cls, rtype)


def test_heartbeat_and_deadline_evidence():
    assert m.classify("HEARTBEAT_TIMEOUT", cost_accrued=5, escrow=20) == (
        FailureClass.LIVENESS,
        "HEARTBEAT_MISS",
    )
    assert m.classify("HEARTBEAT_TIMEOUT", cost_accrued=20, escrow=20) == (
        FailureClass.RESOURCE,
        "BUDGET_EXHAUSTED",
    )
    assert m.classify("DEADLINE_EXPIRED") == (FailureClass.RESOURCE, "DEADLINE_EXCEEDED")


def test_checkpoint_count_does_not_affect_class():
    for n in (0, 1, 4, 100):
        assert m.classify("HEARTBEAT_TIMEOUT", None, 1, 20, checkpoint_count=n)[0] is (
            FailureClass.LIVENESS
        )
        assert m.classify("AGENT_REPORT", "SCHEMA_MISMATCH", checkpoint_count=n)[0] is (
            FailureClass.LOGIC
        )


def test_unknown_inputs_rejected():
    with pytest.raises(ValueError):
        m.classify("GOSSIP")
    with pytest.raises(ValueError):
        m.classify("AGENT_REPORT", "NOT_A_TYPE")


def test_factors():
    assert m.budget_factor(20, 5) == pytest.approx(0.75)
    assert m.budget_factor(20, 20) == 0.0
    assert m.budget_factor(20, 25) == 0.0
    assert m.deadline_factor(30, 3, 0) == pytest.approx(0.9)
    assert m.deadline_factor(30, 30, 0) == 0.0
    assert m.deadline_factor(30, 31, 0) == 0.0


def test_routing_thresholds():
    assert m.route(0.40, 0, 30) is Tier.FULL
    assert m.route(0.3999, 0, 30) is Tier.REDUCED
    assert m.route(0.35, 0, 30) is Tier.REDUCED
    assert m.route(0.3499, 0, 30) is Tier.DISPUTED
    assert m.route(0.99, 30, 30) is Tier.DISPUTED  # past deadline


def test_decide_one_fallback_attempt():
    first = m.decide("HEARTBEAT_TIMEOUT", None, 0, 20, 1, 0, 30)
    assert first.tier is Tier.FULL
    second = m.decide("HEARTBEAT_TIMEOUT", None, 0, 20, 1, 0, 30, fallback_attempts_so_far=1)
    assert second.tier is Tier.DISPUTED


def test_resource_at_full_budget_and_time_is_reduced():
    d = m.decide("AGENT_REPORT", "RATE_LIMIT", 0, 20, 0, 0, 30)
    assert d.score == pytest.approx(0.3817, abs=5e-5)
    assert d.tier is Tier.REDUCED


def test_settlement_full_and_reduced():
    s = m.settle_resolved(20, 2, 3, Tier.FULL)
    assert s.protocol_fee == pytest.approx(0.1)
    assert s.primary == pytest.approx(19.9 * 2 / 5)
    assert s.fallback == pytest.approx(19.9 * 3 / 5)
    assert s.operator_refund == 0.0
    r = m.settle_resolved(20, 1, 4, Tier.REDUCED)
    assert r.fallback == pytest.approx(19.9 * 0.5)
    assert r.operator_refund == pytest.approx(19.9 * 4 / 5 - 19.9 * 0.5)
    total = r.primary + r.fallback + r.operator_refund + r.protocol_fee
    assert total == pytest.approx(20)


def test_dispute_timeout_refunds_operator():
    s = m.settle_dispute_timeout(20)
    assert (s.primary, s.fallback, s.operator_refund, s.protocol_fee) == (0, 0, 20, 0)
