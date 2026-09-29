"""One module per recovery system under comparison."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..harness import RunContext, System, execute_step
from ..schema import Checkpoint, CheckpointStore
from ..task import N_STEPS, STEPS


def run_steps(
    rc: RunContext,
    start: int,
    context: Dict[str, Any],
    worker: str,
    store: Optional[CheckpointStore] = None,
    on_commit: Optional[Callable[[int], None]] = None,
) -> Dict[str, Any]:
    """Execute steps ``start..N-1`` in order, checkpointing after each if a store is given."""
    for i in range(start, N_STEPS):
        out = execute_step(rc, i, context, worker)
        context[STEPS[i].name] = out
        if store is not None:
            store.commit(Checkpoint(rc.task_id, i, out, dict(context)))
            rc.committed_checkpoints = store.count(rc.task_id)
            if on_commit is not None:
                on_commit(i)
    return context


def all_systems() -> List[System]:
    from .cairn import CairnSystem
    from .langgraph_sqlite import LangGraphSystem
    from .naive_restart import NaiveRestartSystem
    from .oracle import OracleSystem
    from .same_agent_retry import SameAgentRetrySystem
    from .temporal_replay import TemporalSystem

    return [
        NaiveRestartSystem(),
        SameAgentRetrySystem(),
        LangGraphSystem(),
        TemporalSystem(),
        CairnSystem(),
        OracleSystem(),
    ]
