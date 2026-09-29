"""Aggregation, markdown tables and figures for the baseline-comparison benchmark."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .faults import FAULT_ORDER, PROGRESS_POINTS, FaultKind, ground_truth_recoverable

RECOVERABLE = [k.value for k in FAULT_ORDER if ground_truth_recoverable(k)]
FAULTS = [k.value for k in FAULT_ORDER]

FAULT_LABEL = {
    FaultKind.CRASH.value: "crash",
    FaultKind.HANG.value: "hang",
    FaultKind.RATE_LIMIT.value: "429",
    FaultKind.UPSTREAM_TIMEOUT.value: "upstream t/o",
    FaultKind.BUDGET_EXHAUSTION.value: "budget",
    FaultKind.SCHEMA_MISMATCH.value: "schema",
    FaultKind.VERIFIER_REJECTION.value: "verifier",
}


def _mean(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 4) if xs else None


def faulted(rows: List[Dict[str, Any]], system: Optional[str] = None) -> List[Dict[str, Any]]:
    return [r for r in rows if r["fault"] != "none" and (system is None or r["system"] == system)]


def aggregate(rows: List[Dict[str, Any]], systems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in systems:
        rs = faulted(rows, s["name"])
        rec = [r for r in rs if r["recoverable_ground_truth"]]
        ok = [r for r in rs if r["success"]]
        cairn_like = s["name"] == "cairn"
        out.append(
            {
                "system": s["name"],
                "runs": len(rs),
                "recovered": len(ok),
                "success_rate": round(len(ok) / len(rs), 4),
                "success_rate_recoverable": round(sum(r["success"] for r in rec) / len(rec), 4),
                "work_preserved_recoverable_mean": _mean([r["work_preserved"] for r in rec]),
                "work_preserved_recovered_mean": _mean([r["work_preserved"] for r in ok]),
                "time_to_recovery_mean": _mean([r["time_to_recovery"] for r in ok]),
                "resource_cost_total": round(sum(r["resource_cost"] for r in rs), 4),
                "resource_cost_recovered_mean": _mean([r["resource_cost"] for r in ok]),
                "step_executions_total": sum(r["step_executions"] for r in rs),
                "false_recoveries": sum(r["false_recovery"] for r in rs),
                "missed_recoveries": sum(r["missed_recovery"] for r in rs),
                "disputes": sum(bool(r["disputed"]) for r in rs) if cairn_like else None,
                "dispute_rate": (
                    round(sum(bool(r["disputed"]) for r in rs) / len(rs), 4) if cairn_like else None
                ),
                "resource_cost_unrecovered_total": round(
                    sum(r["resource_cost"] for r in rs if not r["success"]), 4
                ),
                "operator_loss_total": round(sum(r["operator_loss"] for r in rs), 4),
                "different_worker": s["different_worker"],
                "mode": s["mode"],
            }
        )
    return out


def per_fault_success(rows: List[Dict[str, Any]], systems: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    table: Dict[str, Dict[str, int]] = {}
    for s in systems:
        table[s["name"]] = {
            f: sum(r["success"] for r in faulted(rows, s["name"]) if r["fault"] == f) for f in FAULTS
        }
    return table


def cairn_routing(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in faulted(rows, "cairn"):
        d = r["decisions"][0]
        out.append(
            {
                "fault": r["fault"],
                "point": r["point"],
                "evidence": d["evidence"],
                "class": d["class"],
                "type": d["type"],
                "B": d["B"],
                "D": d["D"],
                "r": d["r"],
                "tier": d["tier"],
                "recovered": r["success"],
                "settlement": r["settlement"],
            }
        )
    return out


def outcome_code(r: Dict[str, Any]) -> str:
    if r["success"]:
        return "R"  # recovered
    if r["false_recovery"]:
        return "F"  # recovery attempted and failed
    if r["missed_recovery"]:
        return "M"  # recoverable, not attempted / not permitted
    return "A"  # not recoverable, not attempted


# ── markdown ─────────────────────────────────────────────────────────────────


def _fmt(x: Any, pct: bool = False) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if pct:
        return f"{100 * x:.1f}%"
    if isinstance(x, float):
        return f"{x:.2f}"
    return str(x)


def md_aggregate(agg: List[Dict[str, Any]], labels: Dict[str, str]) -> str:
    head = (
        "| System | Mode | Recovered (of 28) | Success, recoverable faults (of 16) | "
        "Work preserved, recoverable faults | Mean time-to-recovery (s) | "
        "Total resource cost | Resource cost on unrecovered runs | False recoveries | "
        "Missed recoveries | Disputes | Operator loss | Recovery by different worker |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for a in agg:
        lines.append(
            f"| {labels[a['system']]} | {a['mode']} | {a['recovered']} | "
            f"{round(a['success_rate_recoverable'] * 16)} ({_fmt(a['success_rate_recoverable'], True)}) | "
            f"{_fmt(a['work_preserved_recoverable_mean'], True)} | {_fmt(a['time_to_recovery_mean'])} | "
            f"{_fmt(a['resource_cost_total'])} | {_fmt(a['resource_cost_unrecovered_total'])} | "
            f"{a['false_recoveries']} | {a['missed_recoveries']} | "
            f"{_fmt(a['disputes'])} | {_fmt(a['operator_loss_total'])} | "
            f"{'n/a' if a['different_worker'] is None else _fmt(a['different_worker'])} |"
        )
    return head + "\n".join(lines) + "\n"


def md_per_fault(table: Dict[str, Dict[str, int]], labels: Dict[str, str]) -> str:
    head = "| System | " + " | ".join(FAULT_LABEL[f] for f in FAULTS) + " |\n"
    head += "|---|" + "---|" * len(FAULTS) + "\n"
    lines = [
        f"| {labels[s]} | " + " | ".join(f"{t[f]}/4" for f in FAULTS) + " |" for s, t in table.items()
    ]
    return head + "\n".join(lines) + "\n"


def md_matrix(rows: List[Dict[str, Any]], labels: Dict[str, str], systems: List[str]) -> str:
    cols = [(f, p) for f in FAULTS for p in PROGRESS_POINTS]
    head = "| System | " + " | ".join(f"{FAULT_LABEL[f]} p{p}" for f, p in cols) + " |\n"
    head += "|---|" + "---|" * len(cols) + "\n"
    idx = {(r["system"], r["fault"], r["point"]): r for r in faulted(rows)}
    lines = [
        f"| {labels[s]} | " + " | ".join(outcome_code(idx[(s, f, p)]) for f, p in cols) + " |"
        for s in systems
    ]
    return head + "\n".join(lines) + "\n"


def md_metric_by_point(
    rows: List[Dict[str, Any]], labels: Dict[str, str], systems: List[str], key: str, faults: List[str]
) -> str:
    cols = [(f, p) for f in faults for p in PROGRESS_POINTS]
    head = "| System | " + " | ".join(f"{FAULT_LABEL[f]} p{p}" for f, p in cols) + " |\n"
    head += "|---|" + "---|" * len(cols) + "\n"
    idx = {(r["system"], r["fault"], r["point"]): r for r in faulted(rows)}
    lines = []
    for s in systems:
        cells = []
        for f, p in cols:
            v = idx[(s, f, p)][key]
            if key == "work_preserved":
                cells.append(f"{round(100 * v)}%")
            else:
                cells.append("-" if v is None else f"{v:g}")
        lines.append(f"| {labels[s]} | " + " | ".join(cells) + " |")
    return head + "\n".join(lines) + "\n"


def md_cairn_routing(routing: List[Dict[str, Any]]) -> str:
    head = (
        "| Fault | Point | Evidence | Class / type | B | D | r | Tier | Recovered | "
        "Primary | Fallback | Operator refund | Protocol fee |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for x in routing:
        st = x["settlement"]
        lines.append(
            f"| {FAULT_LABEL[x['fault']]} | {x['point']} | {x['evidence']} | "
            f"{x['class']} / {x['type']} | {x['B']:.4f} | {x['D']:.4f} | {x['r']:.4f} | "
            f"{x['tier']} | {_fmt(x['recovered'])} | {st['primary']:.3f} | {st['fallback']:.3f} | "
            f"{st['operator_refund']:.3f} | {st['protocol_fee']:.3f} |"
        )
    return head + "\n".join(lines) + "\n"


def md_sensitivity(sens: List[Dict[str, Any]]) -> str:
    faults = sorted({s["fault"] for s in sens}, key=FAULTS.index)
    mults = sorted({s["escrow_multiple"] for s in sens})
    cols = [(f, p) for f in faults for p in PROGRESS_POINTS]
    head = "| Escrow / no-failure cost | " + " | ".join(f"{FAULT_LABEL[f]} p{p}" for f, p in cols)
    head += " |\n|---|" + "---|" * len(cols) + "\n"
    idx = {(s["escrow_multiple"], s["fault"], s["point"]): s for s in sens}
    lines = []
    for m in mults:
        cells = [f"{idx[(m, f, p)]['tier']} ({idx[(m, f, p)]['r']:.3f})" for f, p in cols]
        lines.append(f"| {m:g}x | " + " | ".join(cells) + " |")
    return head + "\n".join(lines) + "\n"


# ── figures ──────────────────────────────────────────────────────────────────

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
STATUS = {"R": "#0ca30c", "F": "#d03b3b", "M": "#ec835a", "A": "#d9d8d2"}
STATUS_TEXT = {"R": "#ffffff", "F": "#ffffff", "M": TEXT, "A": TEXT}
OUTCOME_NAME = {
    "R": "R  recovered (correct output within 30 s)",
    "F": "F  false recovery (attempted, failed)",
    "M": "M  missed recovery (recoverable, not attempted)",
    "A": "A  abstained (not recoverable, not attempted)",
}


def _setup_mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "svg.hashsalt": "cairn-baseline-benchmark",
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "text.color": TEXT,
            "axes.labelcolor": TEXT_2,
            "xtick.color": TEXT_2,
            "ytick.color": TEXT,
            "axes.edgecolor": SURFACE,
        }
    )
    return plt


def _save(fig, out_dir: str, stem: str) -> List[str]:
    paths = []
    for ext, meta in (("png", {"Software": None}), ("svg", {"Date": None, "Creator": None})):
        p = os.path.join(out_dir, f"{stem}.{ext}")
        fig.savefig(p, dpi=200, bbox_inches="tight", metadata=meta)
        paths.append(p)
    return paths


def _cells(ax, n_rows: int, n_cols: int, color_of, text_of, text_color_of) -> None:
    from matplotlib.patches import Rectangle

    gap = 0.06  # surface gap between cells
    for i in range(n_rows):
        for j in range(n_cols):
            ax.add_patch(
                Rectangle(
                    (j + gap / 2, i + gap / 2),
                    1 - gap,
                    1 - gap,
                    facecolor=color_of(i, j),
                    edgecolor="none",
                )
            )
            ax.text(j + 0.5, i + 0.5, text_of(i, j), ha="center", va="center",
                    fontsize=7.5, color=text_color_of(i, j))
    ax.set_xlim(0, n_cols)
    ax.set_ylim(n_rows, 0)
    ax.tick_params(length=0)


def _group_labels(ax, faults: List[str], y: float) -> None:
    for k, f in enumerate(faults):
        x0 = k * len(PROGRESS_POINTS)
        ax.text(x0 + len(PROGRESS_POINTS) / 2, y, FAULT_LABEL[f], ha="center", va="bottom",
                fontsize=8.5, color=TEXT)
        if k:
            ax.axvline(x0, color=SURFACE, linewidth=3)


def fig_work_preserved(rows, labels, systems, out_dir) -> List[str]:
    plt = _setup_mpl()
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("blue", ["#eef4fb", "#2a78d6", "#123f7a"])
    cols = [(f, p) for f in RECOVERABLE for p in PROGRESS_POINTS]
    idx = {(r["system"], r["fault"], r["point"]): r for r in faulted(rows)}
    val = [[idx[(s, f, p)]["work_preserved"] for f, p in cols] for s in systems]

    fig, ax = plt.subplots(figsize=(9.2, 3.2))
    _cells(
        ax,
        len(systems),
        len(cols),
        lambda i, j: cmap(0.08 + 0.72 * val[i][j]),
        lambda i, j: f"{round(100 * val[i][j])}",
        lambda i, j: "#ffffff" if val[i][j] >= 0.5 else TEXT,
    )
    ax.set_yticks([i + 0.5 for i in range(len(systems))])
    ax.set_yticklabels([labels[s] for s in systems])
    ax.set_xticks([j + 0.5 for j in range(len(cols))])
    ax.set_xticklabels([f"p{p}" for _, p in cols])
    _group_labels(ax, RECOVERABLE, -0.25)
    ax.set_xlabel("progress point p (fault fires after p of 5 steps have completed)")
    fig.suptitle(
        "Work preserved (%) on faults where resuming from the last checkpoint succeeds",
        x=0.01, ha="left", fontsize=10.5, y=1.04,
    )
    ax.set_title(
        "Share of the p pre-fault steps reused, not re-executed, in the correct final output; "
        "0 when not recovered",
        loc="left", fontsize=8, color=TEXT_2, pad=18,
    )
    paths = _save(fig, out_dir, "fig17_work_preserved")
    plt.close(fig)
    return paths


def fig_outcome_matrix(rows, labels, systems, out_dir) -> List[str]:
    plt = _setup_mpl()
    from matplotlib.patches import Patch

    cols = [(f, p) for f in FAULTS for p in PROGRESS_POINTS]
    idx = {(r["system"], r["fault"], r["point"]): r for r in faulted(rows)}
    code = [[outcome_code(idx[(s, f, p)]) for f, p in cols] for s in systems]

    fig, ax = plt.subplots(figsize=(12.5, 3.4))
    _cells(
        ax,
        len(systems),
        len(cols),
        lambda i, j: STATUS[code[i][j]],
        lambda i, j: code[i][j],
        lambda i, j: STATUS_TEXT[code[i][j]],
    )
    ax.set_yticks([i + 0.5 for i in range(len(systems))])
    ax.set_yticklabels([labels[s] for s in systems])
    ax.set_xticks([j + 0.5 for j in range(len(cols))])
    ax.set_xticklabels([f"p{p}" for _, p in cols], fontsize=7)
    _group_labels(ax, FAULTS, -0.25)
    n_rec = len(RECOVERABLE) * len(PROGRESS_POINTS)
    ax.axvline(n_rec, color=TEXT_2, linewidth=1.0, linestyle=(0, (2, 2)))
    ax.text(n_rec / 2, len(systems) + 0.55, "ground truth: resuming succeeds", ha="center",
            va="top", fontsize=8, color=TEXT_2)
    ax.text(n_rec + (len(cols) - n_rec) / 2, len(systems) + 0.55,
            "ground truth: resuming fails", ha="center", va="top", fontsize=8, color=TEXT_2)
    handles = [Patch(facecolor=STATUS[c], label=OUTCOME_NAME[c]) for c in "RFMA"]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, -0.28), ncol=4,
              frameon=False, fontsize=8, handlelength=1.2)
    fig.suptitle("Outcome per system, fault and progress point", x=0.01, ha="left",
                 fontsize=10.5, y=1.04)
    ax.set_title("CAIRN's M and A cells are routed to dispute", loc="left", fontsize=8,
                 color=TEXT_2, pad=18)
    paths = _save(fig, out_dir, "fig18_outcome_matrix")
    plt.close(fig)
    return paths
