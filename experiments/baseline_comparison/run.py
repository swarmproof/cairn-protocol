"""Run the baseline-comparison benchmark.

    python3 -m experiments.baseline_comparison.run [--no-figures] [--out DIR] [--tables]

Writes ``results.json`` (deterministic: no timestamps, paths or wall-clock values)
and ``figures/fig17_work_preserved.{png,svg}``, ``figures/fig18_outcome_matrix.{png,svg}``.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from typing import Any, Dict, List

from . import analyze
from .faults import (
    HEARTBEAT_TIMEOUT_S,
    PROCESS_EXIT_DETECT_S,
    PROFILES,
    PROGRESS_POINTS,
    STEP_TIMEOUT_S,
    FaultKind,
)
from .harness import (
    CREATED_AT,
    DEADLINE,
    ESCROW,
    FALLBACK_STARTUP_S,
    PROCESS_RESTART_S,
    SUCCESS_WINDOW_S,
    TX_LATENCY_S,
    run_benchmark,
    run_one,
)
from .task import STEPS, TOTAL_COST, TOTAL_DURATION
from .wrappers import all_systems
from .wrappers.cairn import CairnSystem

HERE = os.path.dirname(os.path.abspath(__file__))
SENSITIVITY_MULTIPLES = (1.5, 2.0, 3.0, 5.0, 10.0, 100.0)
SENSITIVITY_FAULTS = (FaultKind.RATE_LIMIT, FaultKind.UPSTREAM_TIMEOUT)


def escrow_sensitivity() -> List[Dict[str, Any]]:
    """CAIRN tier for the RESOURCE-class transient faults as escrow varies."""
    sys_ = CairnSystem()
    out = []
    for m in SENSITIVITY_MULTIPLES:
        for kind in SENSITIVITY_FAULTS:
            for p in PROGRESS_POINTS:
                row = run_one(sys_, kind, p, escrow=m * TOTAL_COST)
                d = row["decisions"][0]
                out.append(
                    {
                        "escrow_multiple": m,
                        "fault": kind.value,
                        "point": p,
                        "B": d["B"],
                        "D": d["D"],
                        "r": d["r"],
                        "tier": d["tier"],
                        "recovered": row["success"],
                    }
                )
    return out


def build_results() -> Dict[str, Any]:
    systems = all_systems()
    rows = run_benchmark(systems)
    sys_meta = []
    versions: Dict[str, str] = {}
    for s in systems:
        sys_meta.append(
            {
                "name": s.name,
                "label": s.label,
                "mode": s.mode,
                "emulation_reason": getattr(s, "emulation_reason", None),
                "different_worker": s.different_worker,
            }
        )
        versions.update(getattr(s, "versions", {}) or {})
    labels = {s["name"]: s["label"] for s in sys_meta}
    agg = analyze.aggregate(rows, sys_meta)
    return {
        "setup": {
            "steps": [
                {"index": st.index, "name": st.name, "duration_s": st.duration, "cost": st.cost}
                for st in STEPS
            ],
            "no_failure_duration_s": TOTAL_DURATION,
            "no_failure_cost": TOTAL_COST,
            "escrow_and_budget": ESCROW,
            "created_at": CREATED_AT,
            "deadline_s": DEADLINE,
            "success_window_s": SUCCESS_WINDOW_S,
            "progress_points": list(PROGRESS_POINTS),
            "process_exit_detect_s": PROCESS_EXIT_DETECT_S,
            "step_timeout_s": STEP_TIMEOUT_S,
            "heartbeat_timeout_s": HEARTBEAT_TIMEOUT_S,
            "process_restart_s": PROCESS_RESTART_S,
            "cairn_tx_latency_s": TX_LATENCY_S,
            "cairn_fallback_startup_s": FALLBACK_STARTUP_S,
            "faults": [
                {
                    "fault": k.value,
                    "transient": p.transient,
                    "recoverable_ground_truth": p.recoverable,
                    "cairn_evidence": p.cairn_evidence,
                    "cairn_report_type": p.cairn_report_type,
                    "silent": p.silent,
                    "process_exit": p.process_exit,
                }
                for k, p in PROFILES.items()
            ],
        },
        "systems": sys_meta,
        "framework_versions": versions,
        "aggregate": agg,
        "per_fault_success": analyze.per_fault_success(rows, sys_meta),
        "cairn_routing": analyze.cairn_routing(rows),
        "cairn_escrow_sensitivity": escrow_sensitivity(),
        "runs": rows,
        "_labels": labels,
    }


def dumps(results: Dict[str, Any]) -> str:
    public = {k: v for k, v in results.items() if not k.startswith("_")}
    return json.dumps(public, indent=1, sort_keys=True) + "\n"


def tables(results: Dict[str, Any]) -> str:
    labels = results["_labels"]
    names = [s["name"] for s in results["systems"]]
    rows = results["runs"]
    parts = [
        "## Aggregate\n\n" + analyze.md_aggregate(results["aggregate"], labels),
        "## Successes per fault (of 4 progress points)\n\n"
        + analyze.md_per_fault(results["per_fault_success"], labels),
        "## Outcome matrix\n\n" + analyze.md_matrix(rows, labels, names),
        "## Work preserved\n\n"
        + analyze.md_metric_by_point(rows, labels, names, "work_preserved", analyze.RECOVERABLE),
        "## Time to recovery (s)\n\n"
        + analyze.md_metric_by_point(rows, labels, names, "time_to_recovery", analyze.RECOVERABLE),
        "## Resource cost (all faults)\n\n"
        + analyze.md_metric_by_point(rows, labels, names, "resource_cost", analyze.FAULTS),
        "## CAIRN routing and settlement\n\n" + analyze.md_cairn_routing(results["cairn_routing"]),
        "## CAIRN escrow sensitivity\n\n" + analyze.md_sensitivity(results["cairn_escrow_sensitivity"]),
    ]
    return "\n".join(parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=HERE, help="directory for results.json and figures/")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--tables", action="store_true", help="print all markdown tables")
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    results = build_results()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "results.json"), "w") as fh:
        fh.write(dumps(results))
    if not args.no_figures:
        fig_dir = os.path.join(args.out, "figures")
        os.makedirs(fig_dir, exist_ok=True)
        names = [s["name"] for s in results["systems"]]
        analyze.fig_work_preserved(results["runs"], results["_labels"], names, fig_dir)
        analyze.fig_outcome_matrix(results["runs"], results["_labels"], names, fig_dir)
    wall = time.perf_counter() - t0

    modes = ", ".join(f"{s['name']}={s['mode']}" for s in results["systems"])
    print(f"python {platform.python_version()}; systems: {modes}")
    print(f"framework versions: {results['framework_versions']}")
    print(tables(results) if args.tables else analyze.md_aggregate(results["aggregate"], results["_labels"]))
    print(f"wall time: {wall:.2f} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
