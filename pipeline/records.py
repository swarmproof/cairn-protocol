"""
Failure and Resolution Record Schemas

Pydantic models for failure/resolution records stored in Bonfires.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class FailureClass(str, Enum):
    """Failure classification types."""

    LIVENESS = "LIVENESS"
    RESOURCE = "RESOURCE"
    EXECUTION = "EXECUTION"
    DEADLINE = "DEADLINE"


class FailureType(str, Enum):
    """Specific failure types."""

    # Liveness failures
    HEARTBEAT_TIMEOUT = "HEARTBEAT_TIMEOUT"
    AGENT_CRASHED = "AGENT_CRASHED"

    # Resource failures
    RATE_LIMIT = "RATE_LIMIT"
    API_UNAVAILABLE = "API_UNAVAILABLE"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # Execution failures
    LOGIC_ERROR = "LOGIC_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"

    # Deadline failures
    TIMEOUT = "TIMEOUT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class FailureRecord(BaseModel):
    """
    Failure record stored on IPFS and indexed in Bonfires.

    Based on PRD-03 Section 3.1 schema.
    """

    # Record metadata
    record_type: str = Field(default="failure", frozen=True)
    version: str = Field(default="1.0", frozen=True)

    # Task identification
    task_id: str = Field(..., description="Unique task identifier (bytes32 hex)")
    agent_id: str = Field(..., description="Agent ERC8004 identifier")
    task_type: str = Field(..., description="Task type classification (e.g., defi.price_fetch)")

    # Failure classification
    failure_class: FailureClass = Field(..., description="High-level failure classification")
    failure_type: FailureType = Field(..., description="Specific failure type")
    failure_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional failure context (API endpoints, error codes, etc.)",
    )

    # Task progress
    checkpoint_count_at_failure: int = Field(..., ge=0, description="Checkpoints completed before failure")
    total_checkpoints_expected: int = Field(..., ge=0, description="Total expected checkpoints")

    # Resource metrics
    cost_at_failure: str = Field(..., description="Cost incurred before failure (in ETH)")
    cost_unit: str = Field(default="ETH", frozen=True)
    budget_remaining_pct: float = Field(..., ge=0.0, le=1.0, description="Remaining budget percentage")
    deadline_remaining_pct: float = Field(..., ge=0.0, le=1.0, description="Remaining deadline percentage")

    # Recovery metadata
    recovery_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Recovery likelihood score (0-1)",
    )

    # Blockchain metadata
    block_number: int = Field(..., ge=0, description="Block number when failure occurred")
    timestamp: int = Field(..., ge=0, description="Unix timestamp of failure")

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task_id is a valid hex string."""
        if not v.startswith("0x"):
            raise ValueError("task_id must start with 0x")
        if len(v) != 66:  # 0x + 64 hex chars for bytes32
            raise ValueError("task_id must be 66 characters (0x + 64 hex)")
        return v

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Validate agent_id follows ERC8004 format."""
        if not v.startswith("erc8004://"):
            raise ValueError("agent_id must follow ERC8004 format: erc8004://chain/address")
        return v

    def to_ipfs_payload(self) -> dict[str, Any]:
        """Convert to IPFS-ready JSON payload."""
        return self.model_dump(mode="json")

    def to_bonfires_record(self) -> dict[str, Any]:
        """Convert to Bonfires indexing format."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "failure_class": self.failure_class.value,
            "failure_type": self.failure_type.value,
            "checkpoint_count": self.checkpoint_count_at_failure,
            "recovery_score": self.recovery_score,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "metadata": {
                "failure_details": self.failure_details,
                "budget_remaining": self.budget_remaining_pct,
                "deadline_remaining": self.deadline_remaining_pct,
            },
        }


class ResolutionType(str, Enum):
    """Resolution types."""

    SUCCESS = "SUCCESS"
    FALLBACK_SUCCESS = "FALLBACK_SUCCESS"
    FALLBACK_FAILURE = "FALLBACK_FAILURE"
    OPERATOR_CANCEL = "OPERATOR_CANCEL"


class AgentResolutionInfo(BaseModel):
    """Agent-specific resolution information."""

    id: str = Field(..., description="Agent ERC8004 identifier")
    checkpoint_count: int = Field(..., ge=0, description="Checkpoints committed by this agent")
    cost: str = Field(..., description="Cost incurred by this agent (in ETH)")
    payout: str = Field(..., description="Payout received by this agent (in ETH)")


class ResolutionRecord(BaseModel):
    """
    Resolution record stored on IPFS and indexed in Bonfires.

    Based on PRD-03 Section 3.2 schema.
    """

    # Record metadata
    record_type: str = Field(default="resolution", frozen=True)
    version: str = Field(default="1.0", frozen=True)

    # Task identification
    task_id: str = Field(..., description="Unique task identifier (bytes32 hex)")

    # State transitions
    states_traversed: list[str] = Field(
        ...,
        description="States traversed during task lifecycle",
    )

    # Recovery information
    recovery_attempted: bool = Field(..., description="Whether recovery was attempted")
    recovery_successful: bool = Field(..., description="Whether recovery succeeded")

    # Agent information
    original_agent: AgentResolutionInfo = Field(..., description="Original (primary) agent info")
    fallback_agent: Optional[AgentResolutionInfo] = Field(
        None,
        description="Fallback agent info (if recovery was attempted)",
    )

    # Task metadata
    task_type: str = Field(..., description="Task type classification")

    # Cost metrics
    total_cost: str = Field(..., description="Total cost (primary + fallback)")
    total_duration_blocks: int = Field(..., ge=0, description="Total duration in blocks")
    escrow_total: str = Field(..., description="Total escrow amount")
    protocol_fee: str = Field(..., description="Protocol fee deducted")

    # Linked records
    failure_record_cid: Optional[str] = Field(
        None,
        description="IPFS CID of linked failure record",
    )

    # Blockchain metadata
    block_number: int = Field(..., ge=0, description="Block number when resolved")
    timestamp: int = Field(..., ge=0, description="Unix timestamp of resolution")

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task_id is a valid hex string."""
        if not v.startswith("0x"):
            raise ValueError("task_id must start with 0x")
        if len(v) != 66:
            raise ValueError("task_id must be 66 characters (0x + 64 hex)")
        return v

    def to_ipfs_payload(self) -> dict[str, Any]:
        """Convert to IPFS-ready JSON payload."""
        return self.model_dump(mode="json")

    def to_bonfires_record(self) -> dict[str, Any]:
        """Convert to Bonfires indexing format."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "recovery_attempted": self.recovery_attempted,
            "recovery_successful": self.recovery_successful,
            "total_cost": self.total_cost,
            "duration_blocks": self.total_duration_blocks,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "metadata": {
                "states_traversed": self.states_traversed,
                "original_agent": self.original_agent.model_dump(),
                "fallback_agent": self.fallback_agent.model_dump() if self.fallback_agent else None,
                "escrow_total": self.escrow_total,
                "protocol_fee": self.protocol_fee,
                "failure_record_cid": self.failure_record_cid,
            },
        }
