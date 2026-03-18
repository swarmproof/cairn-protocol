"""
CAIRN SDK Types

Pydantic models for type-safe data structures.
"""

from enum import IntEnum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class TaskState(IntEnum):
    """Task lifecycle states matching contract enum."""

    RUNNING = 0
    FAILED = 1
    RECOVERING = 2
    RESOLVED = 3

    def __str__(self) -> str:
        return self.name


class Task(BaseModel):
    """On-chain task representation."""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(..., description="Unique task identifier (bytes32 hex)")
    state: TaskState = Field(..., description="Current task state")
    operator: str = Field(..., description="Operator address who submitted the task")
    primary_agent: str = Field(..., description="Primary agent address")
    fallback_agent: str = Field(..., description="Fallback agent address")
    escrow: int = Field(..., description="Escrowed amount in wei")
    heartbeat_interval: int = Field(..., description="Required heartbeat interval in seconds")
    deadline: int = Field(..., description="Task deadline as Unix timestamp")
    primary_checkpoints: int = Field(0, description="Checkpoints committed by primary")
    fallback_checkpoints: int = Field(0, description="Checkpoints committed by fallback")
    last_heartbeat: int = Field(0, description="Last heartbeat timestamp")
    checkpoint_cids: list[str] = Field(default_factory=list, description="List of checkpoint CIDs")
    task_cid: str = Field("", description="Task specification CID")

    @property
    def is_active(self) -> bool:
        """Check if task is in an active state."""
        return self.state in (TaskState.RUNNING, TaskState.RECOVERING)

    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state in (TaskState.FAILED, TaskState.RESOLVED)

    @property
    def total_checkpoints(self) -> int:
        """Total checkpoints from both agents."""
        return self.primary_checkpoints + self.fallback_checkpoints


class TaskSpec(BaseModel):
    """Task specification for submission."""

    model_config = ConfigDict(frozen=True)

    description: str = Field(..., description="Human-readable task description")
    subtasks: list[dict[str, Any]] = Field(..., description="List of subtask definitions")
    output_schema: dict[str, Any] | None = Field(None, description="Expected output JSON schema")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CheckpointData(BaseModel):
    """Checkpoint data structure for IPFS storage."""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(..., description="Associated task ID")
    subtask_index: int = Field(..., description="Subtask index (0-based)")
    agent: str = Field(..., description="Agent address that created checkpoint")
    timestamp: int = Field(..., description="Creation timestamp")
    data: dict[str, Any] = Field(..., description="Subtask output data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def to_ipfs_payload(self) -> dict[str, Any]:
        """Convert to IPFS-ready payload."""
        return {
            "task_id": self.task_id,
            "subtask_index": self.subtask_index,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
            "version": "1.0",
        }


class SettlementInfo(BaseModel):
    """Settlement details after task resolution."""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(..., description="Settled task ID")
    primary_agent: str = Field(..., description="Primary agent address")
    fallback_agent: str = Field(..., description="Fallback agent address")
    primary_share: int = Field(..., description="Primary agent share in wei")
    fallback_share: int = Field(..., description="Fallback agent share in wei")
    protocol_fee: int = Field(..., description="Protocol fee in wei")
    primary_checkpoints: int = Field(..., description="Primary agent checkpoint count")
    fallback_checkpoints: int = Field(..., description="Fallback agent checkpoint count")
    resolved_at: int = Field(..., description="Resolution timestamp")

    @property
    def total_escrow(self) -> int:
        """Total escrow amount."""
        return self.primary_share + self.fallback_share + self.protocol_fee


class HeartbeatInfo(BaseModel):
    """Heartbeat event data."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    timestamp: int
    block_number: int


class FailureInfo(BaseModel):
    """Task failure event data."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    reason: str
    failed_at: int
    checkpoints_at_failure: int
