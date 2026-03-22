"""
CAIRN CLI - Command Line Interface for CAIRN Protocol

Main entry point for the CLI tool.
"""

import click
from rich.console import Console

from cli.commands import task, agent, pool, intel, admin

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="cairn")
@click.pass_context
def cli(ctx):
    """
    CAIRN Protocol CLI - Agent Failure and Recovery Protocol

    A command-line tool for interacting with CAIRN smart contracts,
    managing tasks, and monitoring agent execution.

    Examples:

        # Submit a new task
        cairn task submit --primary-agent 0x123... --fallback-agent 0x456... \\
                          --task-cid QmABC... --escrow 0.1

        # Check task status
        cairn task status 0xabc123...

        # Send heartbeat
        cairn task heartbeat 0xabc123...

        # Commit checkpoint
        cairn task checkpoint 0xabc123... --cid QmXYZ...

        # Settle task
        cairn task settle 0xabc123...

        # View protocol info
        cairn admin info

    Configuration:
        Set environment variables in contracts/.env:
        - CAIRN_CONTRACT_ADDRESS (required)
        - RPC_URL (default: https://sepolia.base.org)
        - PRIVATE_KEY (required for write operations)
        - PINATA_JWT (required for checkpoint operations)

    For more information: https://github.com/cairn-protocol/cairn
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


# Add command groups
cli.add_command(task)
cli.add_command(agent)
cli.add_command(pool)
cli.add_command(intel)
cli.add_command(admin)


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise SystemExit(130)
    except Exception as e:
        console.print(f"[red]Fatal error:[/red] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
