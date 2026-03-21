"""
Agent Commands

Commands for agent registration and management.
Note: MVP version uses simple task assignment, not full registry.
"""

import click
from rich.panel import Panel

from cli.config import Config
from cli.utils import (
    async_command,
    handle_errors,
    print_success,
    print_info,
    print_warning,
    console,
)


@click.group()
def agent():
    """Agent registration and management commands."""
    pass


@agent.command()
@click.option("--stake", required=True, type=float, help="Stake amount in ETH")
@click.option("--types", required=True, help="Comma-separated task types (e.g., 'code,test,deploy')")
@handle_errors
@async_command
async def register(stake: float, types: str):
    """Register as an agent (future feature)."""
    print_warning("Agent registration will be implemented in PRD-05 (Arbiter Network).")
    print_info("For MVP, agents are directly assigned in task submission.")
    print_info("Use 'cairn task submit --primary-agent <address>' to assign tasks.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"The agent registry will support:\n"
        f"• Staking mechanism for agent reputation\n"
        f"• Task type specialization\n"
        f"• Automated agent selection\n"
        f"• Performance-based ranking\n\n"
        f"Requested stake: {stake} ETH\n"
        f"Requested types: {types}",
        title="Agent Registration (Future)",
        border_style="yellow",
    ))


@agent.command()
@click.argument("address")
@handle_errors
@async_command
async def status(address: str):
    """Get agent status and statistics (future feature)."""
    print_warning("Agent status tracking will be implemented in PRD-05 (Arbiter Network).")
    print_info("For MVP, use 'cairn task status <task_id>' to check task-specific agent status.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"Agent status will include:\n"
        f"• Total tasks completed\n"
        f"• Success rate and reputation\n"
        f"• Active tasks\n"
        f"• Staked amount\n"
        f"• Task type specializations\n\n"
        f"Address: {address}",
        title="Agent Status (Future)",
        border_style="yellow",
    ))


@agent.command()
@handle_errors
@async_command
async def withdraw():
    """Withdraw stake (future feature)."""
    print_warning("Agent stake withdrawal will be implemented in PRD-05 (Arbiter Network).")
    print_info("For MVP, escrow is settled directly per-task via 'cairn task settle'.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"Stake withdrawal will support:\n"
        f"• Unstaking with cooldown period\n"
        f"• Partial withdrawals\n"
        f"• Slash protection during cooldown",
        title="Stake Withdrawal (Future)",
        border_style="yellow",
    ))
