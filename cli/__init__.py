"""
CAIRN CLI - Command Line Interface

A comprehensive CLI tool for interacting with the CAIRN Protocol.
"""

from cli.main import cli, main
from cli.config import Config

__version__ = "0.1.0"
__all__ = ["cli", "main", "Config"]
