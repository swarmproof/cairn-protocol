"""Deterministic five-step toy task (no network, no wall-clock dependence).

    1 fetch_prices   (mocked, seeded)       1.0 s   3 cost units
    2 compute_stats                          1.0 s   2 cost units
    3 format_report  (canonical JSON)        0.5 s   1 cost unit
    4 sign_report    (sha256)                0.5 s   1 cost unit
    5 submit_report  (mock receipt)          1.0 s   3 cost units

Durations are *virtual* seconds consumed on the benchmark's virtual clock. Every
step is a pure function of the task seed and the outputs of earlier steps, so the
final receipt is byte-identical no matter which worker, process or framework
executes which step.
"""

from __future__ import annotations

import hashlib
import json
import random
import statistics
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

TASK_SEED = 42
N_PRICES = 16


@dataclass(frozen=True)
class Step:
    index: int  # 0-based
    name: str
    duration: float  # virtual seconds
    cost: int  # cost units


def _fetch_prices(ctx: Dict[str, Any]) -> List[float]:
    rng = random.Random(ctx["seed"])
    price = 100.0
    out = []
    for _ in range(N_PRICES):
        price *= 1.0 + rng.uniform(-0.02, 0.02)
        out.append(round(price, 4))
    return out


def _compute_stats(ctx: Dict[str, Any]) -> Dict[str, float]:
    prices = ctx["fetch_prices"]
    return {
        "n": len(prices),
        "mean": round(statistics.fmean(prices), 6),
        "stdev": round(statistics.pstdev(prices), 6),
        "min": min(prices),
        "max": max(prices),
        "last": prices[-1],
    }


def _format_report(ctx: Dict[str, Any]) -> str:
    report = {"task_id": ctx["task_id"], "asset": "TOY/USD", "stats": ctx["compute_stats"]}
    return json.dumps(report, sort_keys=True, separators=(",", ":"))


def _sign_report(ctx: Dict[str, Any]) -> str:
    return hashlib.sha256(ctx["format_report"].encode("utf-8")).hexdigest()


def _submit_report(ctx: Dict[str, Any]) -> Dict[str, str]:
    receipt = hashlib.sha256((ctx["task_id"] + ":" + ctx["sign_report"]).encode()).hexdigest()
    return {"status": "accepted", "receipt_id": receipt[:16], "signature": ctx["sign_report"]}


STEPS: Tuple[Step, ...] = (
    Step(0, "fetch_prices", 1.0, 3),
    Step(1, "compute_stats", 1.0, 2),
    Step(2, "format_report", 0.5, 1),
    Step(3, "sign_report", 0.5, 1),
    Step(4, "submit_report", 1.0, 3),
)

_FUNCS: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "fetch_prices": _fetch_prices,
    "compute_stats": _compute_stats,
    "format_report": _format_report,
    "sign_report": _sign_report,
    "submit_report": _submit_report,
}

N_STEPS = len(STEPS)
TOTAL_DURATION = sum(s.duration for s in STEPS)  # 4.0 virtual s
TOTAL_COST = sum(s.cost for s in STEPS)  # 10 cost units


def initial_context(task_id: str, seed: int = TASK_SEED) -> Dict[str, Any]:
    return {"task_id": task_id, "seed": seed}


def compute_step(index: int, ctx: Dict[str, Any]) -> Any:
    """Pure step function: output of step ``index`` given the context so far."""
    return _FUNCS[STEPS[index].name](ctx)


def reference_output(task_id: str, seed: int = TASK_SEED) -> Dict[str, str]:
    """Final output of an undisturbed run; the success criterion compares to this."""
    ctx = initial_context(task_id, seed)
    for step in STEPS:
        ctx[step.name] = compute_step(step.index, ctx)
    return ctx[STEPS[-1].name]
