"""
CAIRN SDK - Python SDK for CAIRN Protocol

Agent Failure and Recovery Protocol with checkpoint-based escrow settlement.

Example:
    from sdk import CairnClient, CairnAgent, CheckpointStore

    client = CairnClient(rpc_url, contract_address, private_key)
    ipfs = CheckpointStore(pinata_jwt)
    agent = CairnAgent(my_agent, client, ipfs)

    async with agent:
        result = await agent.execute(task_id, subtasks)
"""

from sdk.types import Task, TaskState, CheckpointData, SettlementInfo
from sdk.exceptions import (
    CairnError,
    ContractError,
    CheckpointError,
    HeartbeatError,
    TaskNotFoundError,
    InvalidStateError,
)
from sdk.checkpoint import CheckpointStore
from sdk.client import CairnClient
from sdk.agent import CairnAgent
from sdk.observer import CairnObserver, WebhookObserver, LoggingObserver

__version__ = "0.1.0"
__all__ = [
    # Core classes
    "CairnClient",
    "CairnAgent",
    "CheckpointStore",
    # Observers
    "CairnObserver",
    "WebhookObserver",
    "LoggingObserver",
    # Types
    "Task",
    "TaskState",
    "CheckpointData",
    "SettlementInfo",
    # Exceptions
    "CairnError",
    "ContractError",
    "CheckpointError",
    "HeartbeatError",
    "TaskNotFoundError",
    "InvalidStateError",
]
