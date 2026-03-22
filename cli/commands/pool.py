"""
Pool Commands

Commands for fallback pool management.
Note: MVP version uses direct fallback assignment, not pools.
"""

import click
from rich.panel import Panel

from cli.config import Config
from cli.utils import (
    async_command,
    handle_errors,
    print_warning,
    print_info,
    console,
)


@click.group()
def pool():
    """Fallback pool management commands."""
    pass


@pool.command()
@click.option("--type", "pool_type", help="Filter by task type")
@handle_errors
@async_command
async def list(pool_type: str):
    """List available fallback pools (future feature)."""
    print_warning("Fallback pools will be implemented in PRD-04 (Fallback Ecosystem).")
    print_info("For MVP, fallback agents are directly assigned per-task.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"Fallback pools will support:\n"
        f"• Task-type-specific agent pools\n"
        f"• Automatic fallback selection\n"
        f"• Pool-based incentive mechanisms\n"
        f"• Pool performance metrics\n\n"
        f"Filter: {pool_type or 'all types'}",
        title="Fallback Pools (Future)",
        border_style="yellow",
    ))


@pool.command()
@handle_errors
@async_command
async def stats():
    """Show fallback pool statistics (future feature)."""
    print_warning("Pool statistics will be implemented in PRD-04 (Fallback Ecosystem).")
    print_info("For MVP, use 'cairn task status' to see task-specific fallback usage.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"Pool statistics will include:\n"
        f"• Total agents per pool\n"
        f"• Recovery success rates\n"
        f"• Average recovery time\n"
        f"• Pool utilization metrics",
        title="Pool Statistics (Future)",
        border_style="yellow",
    ))
