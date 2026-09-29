import json
import os
import subprocess
import sys

import pytest

from experiments.baseline_comparison import run as bench
from experiments.baseline_comparison.faults import (
    FAULT_ORDER,
    PROGRESS_POINTS,
    FaultInjector,
    FaultKind,
    InjectedFault,
)
from experiments.baseline_comparison.harness import RunContext, execute_step, run_one
from experiments.baseline_comparison.task import STEPS, TOTAL_COST, reference_output
from experiments.baseline_comparison.wrappers.cairn import CairnSystem
from experiments.baseline_comparison.wrappers.naive_restart import NaiveRestartSystem

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="module")
def results():
    return bench.build_results()


def test_determinism_across_two_runs(results):
    assert bench.dumps(results) == bench.dumps(bench.build_results())


def test_committed_results_match_a_fresh_run(results):
    path = os.path.join(os.path.dirname(bench.__file__), "results.json")
    with open(path) as fh:
        committed = json.load(fh)
    fresh = json.loads(bench.dumps(results))
    if any(s["mode"] == "emulated" for s in fresh["systems"]):
        pytest.skip("a framework is emulated in this environment; committed results use real ones")
    assert fresh == committed


def test_reference_output_is_stable():
    a = reference_output("task-x")
    assert a == reference_output("task-x")
    assert a["status"] == "accepted" and len(a["receipt_id"]) == 16


@pytest.mark.parametrize("kind", list(FAULT_ORDER))
@pytest.mark.parametrize("point", list(PROGRESS_POINTS))
def test_each_fault_fires_at_intended_point(kind, point):
    rc = RunContext(task_id="t", injector=FaultInjector(kind, point))
    ctx = rc.initial_context()
    for i in range(point):
        ctx[STEPS[i].name] = execute_step(rc, i, ctx, "w")
    assert rc.injector.fired == []
    with pytest.raises(InjectedFault) as exc:
        execute_step(rc, point, ctx, "w")
    assert exc.value.kind is kind and exc.value.step_index == point
    assert [e.step_index for e in rc.injector.fired] == [point]


@pytest.mark.parametrize("kind", list(FAULT_ORDER))
@pytest.mark.parametrize("point", list(PROGRESS_POINTS))
def test_fault_fires_after_point_checkpoints_in_cairn(kind, point):
    row = run_one(CairnSystem(), kind, point)
    assert row["fault_fired_at_step"] == point
    assert row["checkpoints_before_fault"] == point


def test_transient_fires_once_deterministic_fires_every_time():
    for kind, expected in ((FaultKind.CRASH, False), (FaultKind.SCHEMA_MISMATCH, True)):
        inj = FaultInjector(kind, 2)
        rc = RunContext(task_id="t", injector=inj)
        ctx = rc.initial_context()
        for i in range(2):
            ctx[STEPS[i].name] = execute_step(rc, i, ctx, "w")
        with pytest.raises(InjectedFault):
            execute_step(rc, 2, ctx, "w")
        if expected:
            with pytest.raises(InjectedFault):
                execute_step(rc, 2, ctx, "other-worker")
        else:
            execute_step(rc, 2, ctx, "other-worker")


def test_budget_exhaustion_blocks_every_worker():
    rc = RunContext(task_id="t", injector=FaultInjector(FaultKind.BUDGET_EXHAUSTION, 1))
    ctx = rc.initial_context()
    ctx[STEPS[0].name] = execute_step(rc, 0, ctx, "w")
    with pytest.raises(InjectedFault):
        execute_step(rc, 1, ctx, "w")
    assert rc.meter.accrued == rc.escrow
    with pytest.raises(InjectedFault) as exc:
        execute_step(rc, 1, ctx, "fallback")
    assert exc.value.refused


def test_naive_restart_preserves_zero_work(results):
    rows = [r for r in results["runs"] if r["system"] == "naive_restart" and r["fault"] != "none"]
    assert len(rows) == len(FAULT_ORDER) * len(PROGRESS_POINTS)
    assert all(r["work_preserved"] == 0.0 for r in rows)
    ok = [r for r in rows if r["success"]]
    assert ok and all(r["resource_cost"] > TOTAL_COST for r in ok)


def test_naive_restart_reexecutes_every_pre_fault_step():
    row = run_one(NaiveRestartSystem(), FaultKind.CRASH, 3)
    assert row["success"] and row["work_preserved"] == 0.0


def test_no_fault_control_runs_are_clean(results):
    for r in results["runs"]:
        if r["fault"] == "none":
            assert r["success"] and r["resource_cost"] == TOTAL_COST and r["completion_time"] == 4.0


def test_oracle_bounds_every_system(results):
    succ = {a["system"]: a["recovered"] for a in results["aggregate"]}
    assert all(v <= succ["oracle"] for v in succ.values())
    oracle = next(a for a in results["aggregate"] if a["system"] == "oracle")
    assert oracle["false_recoveries"] == 0 and oracle["missed_recoveries"] == 0


def test_only_cairn_uses_a_different_worker(results):
    for r in results["runs"]:
        if r["system"] == "cairn" and r["recovery_attempted"]:
            assert r["workers"] == ["fallback-agent", "primary-agent"]
        elif r["system"] != "cairn":
            assert len(r["workers"]) <= 1


def test_emulations_match_real_frameworks(results):
    """The emulated fallbacks must reproduce the real frameworks' outcomes exactly."""
    if any(s["mode"] != "real" for s in results["systems"] if s["name"] in ("langgraph", "temporal")):
        pytest.skip("real frameworks unavailable")
    code = (
        "import json;from experiments.baseline_comparison import run as b;"
        "print(json.dumps([r for r in json.loads(b.dumps(b.build_results()))['runs']"
        " if r['system'] in ('langgraph','temporal')], sort_keys=True))"
    )
    env = dict(os.environ, BENCH_FORCE_EMULATION="1")
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
        timeout=120, check=True,
    ).stdout
    real = [r for r in json.loads(bench.dumps(results))["runs"] if r["system"] in ("langgraph", "temporal")]
    assert json.loads(out) == json.loads(json.dumps(real, sort_keys=True))
