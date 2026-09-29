"""LangGraph: a five-node ``StateGraph`` compiled with ``SqliteSaver``.

LangGraph checkpoints the graph state after every completed node (superstep).
On failure the supervisor re-invokes the graph on the same ``thread_id`` with
``None`` input, which resumes from the last persisted state and re-runs only the
failed node. A process crash is modelled by discarding the compiled graph and
its SQLite connection and building fresh ones on the same database file, so the
resume reads state from disk only. Same worker throughout; up to
``MAX_RESUMES`` resumes; no node-level RetryPolicy.

If ``langgraph`` / ``langgraph-checkpoint-sqlite`` are not importable (or
``BENCH_FORCE_EMULATION`` is set) an in-process emulation of the same
persisted-superstep resume semantics is used and the system is labelled
``emulated``.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import warnings
from typing import Any, Dict, Optional

from ..faults import InjectedFault, Supervisor
from ..harness import PROCESS_RESTART_S, RunContext, System, SystemOutcome, execute_step, wait_detection
from ..task import N_STEPS, STEPS

MAX_RESUMES = 2
WORKER = "worker-1"

try:
    if os.environ.get("BENCH_FORCE_EMULATION"):
        raise ImportError("emulation forced")
    with warnings.catch_warnings():
        import langchain_core  # noqa: F401  (installs its own warning filters on import)

        warnings.simplefilter("ignore")
        from typing_extensions import TypedDict

        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph.graph import END, START, StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the dependency
    LANGGRAPH_AVAILABLE = False


def _versions() -> Dict[str, str]:
    if not LANGGRAPH_AVAILABLE:
        return {}
    from importlib.metadata import version

    return {
        "langgraph": version("langgraph"),
        "langgraph-checkpoint-sqlite": version("langgraph-checkpoint-sqlite"),
    }


if LANGGRAPH_AVAILABLE:

    class _State(TypedDict, total=False):
        task_id: str
        seed: int
        fetch_prices: Any
        compute_stats: Any
        format_report: Any
        sign_report: Any
        submit_report: Any


class LangGraphSystem(System):
    name = "langgraph"
    label = "LangGraph + SqliteSaver"
    different_worker = False

    def __init__(self) -> None:
        self.mode = "real" if LANGGRAPH_AVAILABLE else "emulated"
        self.versions = _versions()
        self._tmp: Optional[str] = None

    def open(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="bench_lg_")

    def close(self) -> None:
        if self._tmp:
            shutil.rmtree(self._tmp, ignore_errors=True)
            self._tmp = None

    # ── real ──────────────────────────────────────────────────────────────
    def _build(self, rc: RunContext, db_path: str):
        g = StateGraph(_State)
        prev = START
        for step in STEPS:

            def node(state, _i=step.index, _name=step.name):
                return {_name: execute_step(rc, _i, dict(state), WORKER)}

            g.add_node(step.name, node)
            g.add_edge(prev, step.name)
            prev = step.name
        g.add_edge(prev, END)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return g.compile(checkpointer=SqliteSaver(conn)), conn

    def _run_real(self, rc: RunContext) -> SystemOutcome:
        if self._tmp is None:
            self.open()
        db_path = os.path.join(self._tmp, f"{rc.task_id}.sqlite")
        if os.path.exists(db_path):
            os.remove(db_path)
        cfg = {"configurable": {"thread_id": rc.task_id}}
        app, conn = self._build(rc, db_path)
        resumes = 0
        payload: Optional[Dict[str, Any]] = rc.initial_context()
        try:
            while True:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        final = app.invoke(payload, cfg)
                    return SystemOutcome(final[STEPS[-1].name], resumes)
                except InjectedFault as f:
                    wait_detection(rc, f, Supervisor.LOCAL)
                    if resumes >= MAX_RESUMES:
                        return SystemOutcome(None, resumes)
                    resumes += 1
                    payload = None  # resume from the persisted checkpoint
                    if f.process_exit:
                        conn.close()
                        rc.clock.advance(PROCESS_RESTART_S)
                        app, conn = self._build(rc, db_path)
        finally:
            conn.close()

    # ── emulated: persisted state after each completed node ───────────────
    def _run_emulated(self, rc: RunContext) -> SystemOutcome:
        persisted: Dict[str, Any] = dict(rc.initial_context())
        done = 0
        resumes = 0
        while True:
            state = dict(persisted)  # a (re)started process reads persisted state
            try:
                for i in range(done, N_STEPS):
                    state[STEPS[i].name] = execute_step(rc, i, state, WORKER)
                    persisted, done = dict(state), i + 1
                return SystemOutcome(state[STEPS[-1].name], resumes)
            except InjectedFault as f:
                wait_detection(rc, f, Supervisor.LOCAL)
                if resumes >= MAX_RESUMES:
                    return SystemOutcome(None, resumes)
                resumes += 1
                if f.process_exit:
                    rc.clock.advance(PROCESS_RESTART_S)

    def run(self, rc: RunContext) -> SystemOutcome:
        return self._run_real(rc) if self.mode == "real" else self._run_emulated(rc)
