"""
CLI Utilities

Helper functions for formatting output, handling errors, and
common operations.
"""

import asyncio
import functools
import sys
from typing import Any, Callable, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.text import Text
import json

from sdk.exceptions import CairnError
from sdk.types import TaskState

console = Console()


def format_address(address: str, short: bool = False) -> str:
    """
    Format an Ethereum address.

    Args:
        address: Ethereum address
        short: If True, show only first 6 and last 4 chars

    Returns:
        Formatted address
    """
    if not address:
        return "N/A"
    if short:
        return f"{address[:6]}...{address[-4:]}"
    return address


def format_wei(wei: int) -> str:
    """
    Format wei amount to ETH with proper decimals.

    Args:
        wei: Amount in wei

    Returns:
        Formatted ETH amount
    """
    eth = wei / 10**18
    return f"{eth:.6f} ETH"


def format_timestamp(timestamp: int) -> str:
    """
    Format Unix timestamp to human-readable format.

    Args:
        timestamp: Unix timestamp

    Returns:
        Formatted timestamp string
    """
    if timestamp == 0:
        return "N/A"
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_state(state: TaskState) -> Text:
    """
    Format task state with color.

    Args:
        state: Task state

    Returns:
        Rich Text with color
    """
    colors = {
        TaskState.RUNNING: "green",
        TaskState.FAILED: "red",
        TaskState.RECOVERING: "yellow",
        TaskState.RESOLVED: "blue",
    }
    return Text(str(state), style=colors.get(state, "white"))


def format_cid(cid: str, short: bool = True) -> str:
    """
    Format IPFS CID.

    Args:
        cid: IPFS CID
        short: If True, show only first 8 and last 4 chars

    Returns:
        Formatted CID
    """
    if not cid:
        return "N/A"
    if short and len(cid) > 12:
        return f"{cid[:8]}...{cid[-4:]}"
    return cid


def print_json(data: Any) -> None:
    """
    Print JSON data with syntax highlighting.

    Args:
        data: Data to print as JSON
    """
    json_str = json.dumps(data, indent=2, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[red]✗[/red] {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")


def create_task_table(tasks: list[dict]) -> Table:
    """
    Create a Rich table for displaying tasks.

    Args:
        tasks: List of task dictionaries

    Returns:
        Rich Table
    """
    table = Table(title="CAIRN Tasks", show_header=True, header_style="bold magenta")

    table.add_column("Task ID", style="cyan", no_wrap=True)
    table.add_column("State", style="white")
    table.add_column("Operator", style="dim")
    table.add_column("Primary Agent", style="dim")
    table.add_column("Escrow", justify="right")
    table.add_column("Checkpoints", justify="right")
    table.add_column("Deadline", style="yellow")

    for task in tasks:
        table.add_row(
            format_address(task["task_id"], short=True),
            format_state(TaskState(task["state"])),
            format_address(task["operator"], short=True),
            format_address(task["primary_agent"], short=True),
            format_wei(task["escrow"]),
            f"{task['primary_checkpoints']}/{task['fallback_checkpoints']}",
            format_timestamp(task["deadline"]),
        )

    return table


def async_command(func: Callable) -> Callable:
    """
    Decorator to run async functions in Click commands.

    Args:
        func: Async function to wrap

    Returns:
        Wrapped function that runs in asyncio event loop
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in CLI commands.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CairnError as e:
            print_error(f"CAIRN Error: {e}")
            if e.details:
                print_info(f"Details: {e.details}")
            sys.exit(1)
        except ValueError as e:
            print_error(f"Configuration Error: {e}")
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected Error: {e}")
            import traceback
            console.print_exception(show_locals=False)
            sys.exit(1)
    return wrapper


def with_progress(description: str) -> Any:
    """
    Context manager for showing progress spinner.

    Args:
        description: Progress description

    Returns:
        Progress context manager
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )


def confirm(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if confirmed, False otherwise
    """
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = console.input(f"[yellow]?[/yellow] {message}{suffix}")

    if not response:
        return default

    return response.lower() in ("y", "yes")
