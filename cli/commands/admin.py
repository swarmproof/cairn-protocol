"""
Admin Commands

Commands for protocol administration.
Note: MVP version has minimal admin features.
"""

import click
from rich.panel import Panel

from cli.config import Config
from cli.utils import (
    async_command,
    handle_errors,
    print_warning,
    print_info,
    print_success,
    console,
    format_wei,
)
from sdk import CairnClient


@click.group()
def admin():
    """Protocol administration commands."""
    pass


@admin.command()
@handle_errors
@async_command
async def pause():
    """Pause the protocol (future feature)."""
    print_warning("Protocol pausing will be implemented in PRD-02 (Core Recovery) with governance.")
    print_info("MVP does not include pausable functionality.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"Protocol pause will support:\n"
        f"• Emergency pause mechanism\n"
        f"• Governance-based unpause\n"
        f"• Granular pause controls",
        title="Protocol Pause (Future)",
        border_style="yellow",
    ))


@admin.command()
@handle_errors
@async_command
async def unpause():
    """Unpause the protocol (future feature)."""
    print_warning("Protocol unpausing will be implemented in PRD-02 (Core Recovery) with governance.")
    print_info("MVP does not include pausable functionality.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"Protocol unpause will require:\n"
        f"• Governance approval\n"
        f"• Multi-sig confirmation\n"
        f"• Safety checks",
        title="Protocol Unpause (Future)",
        border_style="yellow",
    ))


@admin.command()
@click.argument("param")
@click.argument("value")
@handle_errors
@async_command
async def set_param(param: str, value: str):
    """Set protocol parameter (future feature)."""
    print_warning("Parameter governance will be implemented in PRD-02 (Core Recovery).")
    print_info("MVP has fixed parameters set in constructor.")

    console.print(Panel(
        f"[yellow]Coming Soon[/yellow]\n\n"
        f"Protocol parameters that will be governable:\n"
        f"• Protocol fee (basis points)\n"
        f"• Minimum escrow\n"
        f"• Minimum heartbeat interval\n"
        f"• Recovery timeout\n\n"
        f"Requested: {param} = {value}",
        title="Parameter Governance (Future)",
        border_style="yellow",
    ))


@admin.command()
@handle_errors
@async_command
async def info():
    """Show protocol information and parameters."""
    config = Config.from_env()

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
    )

    print_info("Fetching protocol information...")

    # Get protocol parameters
    protocol_fee = await client.get_protocol_fee()
    min_escrow = await client.get_min_escrow()
    min_heartbeat = await client.get_min_heartbeat_interval()
    chain_id = await client.get_chain_id()

    info_content = f"""[cyan]Contract Address:[/cyan] {config.contract_address}
[cyan]Chain ID:[/cyan] {chain_id}
[cyan]RPC URL:[/cyan] {config.rpc_url}

[bold]Protocol Parameters:[/bold]
[cyan]Protocol Fee:[/cyan] {protocol_fee / 100}% ({protocol_fee} basis points)
[cyan]Min Escrow:[/cyan] {format_wei(min_escrow)}
[cyan]Min Heartbeat Interval:[/cyan] {min_heartbeat} seconds

[bold]Network Links:[/bold]
[cyan]BaseScan:[/cyan] https://sepolia.basescan.org/address/{config.contract_address}
"""

    console.print(Panel(
        info_content,
        title="CAIRN Protocol Information",
        border_style="cyan",
    ))

    print_success("Protocol is operational")
