"""
Task Commands

Commands for task lifecycle management.
"""

import time
from typing import Optional

import click
from rich.table import Table
from rich.panel import Panel
from web3 import Web3

from cli.config import Config
from cli.utils import (
    async_command,
    handle_errors,
    print_success,
    print_error,
    print_info,
    print_warning,
    print_json,
    format_address,
    format_wei,
    format_timestamp,
    format_state,
    format_cid,
    with_progress,
    console,
)
from sdk import CairnClient, CheckpointStore
from sdk.types import TaskState


@click.group()
def task():
    """Task lifecycle management commands."""
    pass


@task.command()
@click.option("--primary-agent", required=True, help="Primary agent address")
@click.option("--fallback-agent", required=True, help="Fallback agent address")
@click.option("--task-cid", required=True, help="IPFS CID of task specification")
@click.option("--escrow", required=True, type=float, help="Escrow amount in ETH")
@click.option("--heartbeat-interval", default=60, type=int, help="Heartbeat interval in seconds")
@click.option("--deadline", type=int, help="Task deadline as Unix timestamp (default: 24h from now)")
@handle_errors
@async_command
async def submit(
    primary_agent: str,
    fallback_agent: str,
    task_cid: str,
    escrow: float,
    heartbeat_interval: int,
    deadline: Optional[int],
):
    """Submit a new task to CAIRN protocol."""
    config = Config.from_env()
    config.validate_write_operations()

    # Convert ETH to wei
    escrow_wei = int(escrow * 10**18)

    # Default deadline to 24 hours from now
    if deadline is None:
        deadline = int(time.time()) + 86400

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
        private_key=config.private_key,
    )

    # Validate connection
    with with_progress("Connecting to network...") as progress:
        task_id = progress.add_task("connect", total=None)
        connected = await client.is_connected()
        if not connected:
            print_error("Failed to connect to RPC endpoint")
            return

    # Submit task
    print_info(f"Submitting task to {config.contract_address}")
    print_info(f"Primary: {format_address(primary_agent, short=True)}")
    print_info(f"Fallback: {format_address(fallback_agent, short=True)}")
    print_info(f"Escrow: {format_wei(escrow_wei)}")
    print_info(f"Deadline: {format_timestamp(deadline)}")

    with with_progress("Submitting task...") as progress:
        task_id = progress.add_task("submit", total=None)
        result_task_id = await client.submit_task(
            primary_agent=primary_agent,
            fallback_agent=fallback_agent,
            task_cid=task_cid,
            heartbeat_interval=heartbeat_interval,
            deadline=deadline,
            escrow=escrow_wei,
        )

    print_success(f"Task submitted successfully!")
    console.print(Panel(
        f"[cyan]Task ID:[/cyan] {result_task_id}\n"
        f"[cyan]View on BaseScan:[/cyan] https://sepolia.basescan.org/tx/{result_task_id}",
        title="✓ Task Created",
        border_style="green",
    ))


@task.command()
@click.argument("task_id")
@handle_errors
@async_command
async def status(task_id: str):
    """Get detailed status of a task."""
    config = Config.from_env()

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
    )

    with with_progress("Fetching task status...") as progress:
        task_obj = progress.add_task("fetch", total=None)
        task_data = await client.get_task(task_id)

    # Create status panel
    status_content = f"""[cyan]Task ID:[/cyan] {task_data.task_id}
[cyan]State:[/cyan] {format_state(task_data.state)}
[cyan]Operator:[/cyan] {task_data.operator}
[cyan]Primary Agent:[/cyan] {task_data.primary_agent}
[cyan]Fallback Agent:[/cyan] {task_data.fallback_agent}
[cyan]Escrow:[/cyan] {format_wei(task_data.escrow)}
[cyan]Heartbeat Interval:[/cyan] {task_data.heartbeat_interval}s
[cyan]Deadline:[/cyan] {format_timestamp(task_data.deadline)}
[cyan]Last Heartbeat:[/cyan] {format_timestamp(task_data.last_heartbeat)}
[cyan]Primary Checkpoints:[/cyan] {task_data.primary_checkpoints}
[cyan]Fallback Checkpoints:[/cyan] {task_data.fallback_checkpoints}
[cyan]Total Checkpoints:[/cyan] {task_data.total_checkpoints}
[cyan]Task CID:[/cyan] {format_cid(task_data.task_cid, short=False)}
"""

    console.print(Panel(status_content, title="Task Status", border_style="cyan"))

    # Show checkpoints if any
    if task_data.checkpoint_cids:
        console.print("\n[bold]Checkpoints:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", justify="right")
        table.add_column("CID", style="cyan")
        table.add_column("IPFS URL", style="dim")

        for i, cid in enumerate(task_data.checkpoint_cids):
            table.add_row(
                str(i + 1),
                format_cid(cid, short=True),
                f"https://gateway.pinata.cloud/ipfs/{cid}",
            )

        console.print(table)


@task.command()
@click.option("--operator", help="Filter by operator address")
@click.option("--agent", help="Filter by agent address (primary or fallback)")
@click.option("--state", type=click.Choice(["running", "failed", "recovering", "resolved"]), help="Filter by state")
@click.option("--limit", default=10, type=int, help="Maximum number of tasks to display")
@handle_errors
@async_command
async def list(operator: Optional[str], agent: Optional[str], state: Optional[str], limit: int):
    """List tasks with optional filters."""
    config = Config.from_env()

    print_warning("Note: Full task listing requires event indexing or archive node access.")
    print_info("This command shows basic task enumeration. For production, use a subgraph or indexer.")

    # For MVP, we'll just show how to query a specific task
    # In production, you'd use events or a subgraph
    print_info("Example: Use 'cairn task status <task_id>' to view specific tasks.")


@task.command()
@click.argument("task_id")
@click.option("--cid", required=True, help="IPFS CID of checkpoint data")
@handle_errors
@async_command
async def checkpoint(task_id: str, cid: str):
    """Commit a checkpoint for a task."""
    config = Config.from_env()
    config.validate_write_operations()

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
        private_key=config.private_key,
    )

    print_info(f"Committing checkpoint for task: {format_address(task_id, short=True)}")
    print_info(f"Checkpoint CID: {cid}")

    with with_progress("Committing checkpoint...") as progress:
        task_obj = progress.add_task("checkpoint", total=None)
        receipt = await client.commit_checkpoint(task_id, cid)

    print_success("Checkpoint committed successfully!")
    console.print(Panel(
        f"[cyan]Task ID:[/cyan] {task_id}\n"
        f"[cyan]Checkpoint CID:[/cyan] {cid}\n"
        f"[cyan]Transaction:[/cyan] {receipt['transactionHash'].hex()}\n"
        f"[cyan]Gas Used:[/cyan] {receipt['gasUsed']}",
        title="✓ Checkpoint Committed",
        border_style="green",
    ))


@task.command()
@click.argument("task_id")
@handle_errors
@async_command
async def heartbeat(task_id: str):
    """Send a heartbeat for a task."""
    config = Config.from_env()
    config.validate_write_operations()

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
        private_key=config.private_key,
    )

    print_info(f"Sending heartbeat for task: {format_address(task_id, short=True)}")

    with with_progress("Sending heartbeat...") as progress:
        task_obj = progress.add_task("heartbeat", total=None)
        receipt = await client.heartbeat(task_id)

    print_success("Heartbeat sent successfully!")
    console.print(Panel(
        f"[cyan]Task ID:[/cyan] {task_id}\n"
        f"[cyan]Transaction:[/cyan] {receipt['transactionHash'].hex()}\n"
        f"[cyan]Gas Used:[/cyan] {receipt['gasUsed']}",
        title="✓ Heartbeat Sent",
        border_style="green",
    ))


@task.command()
@click.argument("task_id")
@handle_errors
@async_command
async def fail(task_id: str):
    """Fail a task (permissionless liveness check)."""
    config = Config.from_env()
    config.validate_write_operations()

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
        private_key=config.private_key,
    )

    print_info(f"Failing task: {format_address(task_id, short=True)}")

    with with_progress("Failing task...") as progress:
        task_obj = progress.add_task("fail", total=None)
        receipt = await client.fail_task(task_id)

    print_success("Task failed successfully!")
    console.print(Panel(
        f"[cyan]Task ID:[/cyan] {task_id}\n"
        f"[cyan]Transaction:[/cyan] {receipt['transactionHash'].hex()}",
        title="✓ Task Failed",
        border_style="yellow",
    ))


@task.command()
@click.argument("task_id")
@handle_errors
@async_command
async def recover(task_id: str):
    """Initiate recovery for a failed task."""
    config = Config.from_env()
    config.validate_write_operations()

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
        private_key=config.private_key,
    )

    print_info(f"Initiating recovery for task: {format_address(task_id, short=True)}")

    with with_progress("Recovering task...") as progress:
        task_obj = progress.add_task("recover", total=None)
        receipt = await client.recover_task(task_id)

    print_success("Recovery initiated successfully!")
    console.print(Panel(
        f"[cyan]Task ID:[/cyan] {task_id}\n"
        f"[cyan]Transaction:[/cyan] {receipt['transactionHash'].hex()}",
        title="✓ Recovery Initiated",
        border_style="green",
    ))


@task.command()
@click.argument("task_id")
@handle_errors
@async_command
async def settle(task_id: str):
    """Settle a task and distribute escrow."""
    config = Config.from_env()
    config.validate_write_operations()

    client = CairnClient(
        rpc_url=config.rpc_url,
        contract_address=config.contract_address,
        private_key=config.private_key,
    )

    print_info(f"Settling task: {format_address(task_id, short=True)}")

    with with_progress("Settling task...") as progress:
        task_obj = progress.add_task("settle", total=None)
        settlement = await client.settle(task_id)

    print_success("Task settled successfully!")

    settlement_content = f"""[cyan]Task ID:[/cyan] {settlement.task_id}
[cyan]Primary Agent:[/cyan] {settlement.primary_agent}
[cyan]Fallback Agent:[/cyan] {settlement.fallback_agent}
[cyan]Primary Share:[/cyan] {format_wei(settlement.primary_share)}
[cyan]Fallback Share:[/cyan] {format_wei(settlement.fallback_share)}
[cyan]Protocol Fee:[/cyan] {format_wei(settlement.protocol_fee)}
[cyan]Primary Checkpoints:[/cyan] {settlement.primary_checkpoints}
[cyan]Fallback Checkpoints:[/cyan] {settlement.fallback_checkpoints}
[cyan]Total Escrow:[/cyan] {format_wei(settlement.total_escrow)}
"""

    console.print(Panel(
        settlement_content,
        title="✓ Task Settled",
        border_style="green",
    ))
