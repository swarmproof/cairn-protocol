"""
CAIRN SDK Exceptions

Custom exception hierarchy for CAIRN protocol errors.
"""


class CairnError(Exception):
    """Base exception for all CAIRN SDK errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ContractError(CairnError):
    """Error interacting with the CAIRN smart contract."""

    def __init__(
        self,
        message: str,
        tx_hash: str | None = None,
        revert_reason: str | None = None,
    ):
        details = {}
        if tx_hash:
            details["tx_hash"] = tx_hash
        if revert_reason:
            details["revert_reason"] = revert_reason
        super().__init__(message, details)
        self.tx_hash = tx_hash
        self.revert_reason = revert_reason


class CheckpointError(CairnError):
    """Error reading or writing checkpoints to IPFS."""

    def __init__(
        self,
        message: str,
        cid: str | None = None,
        gateway: str | None = None,
    ):
        details = {}
        if cid:
            details["cid"] = cid
        if gateway:
            details["gateway"] = gateway
        super().__init__(message, details)
        self.cid = cid
        self.gateway = gateway


class HeartbeatError(CairnError):
    """Error sending heartbeat to contract."""

    def __init__(
        self,
        message: str,
        task_id: str | None = None,
        last_heartbeat: int | None = None,
    ):
        details = {}
        if task_id:
            details["task_id"] = task_id
        if last_heartbeat:
            details["last_heartbeat"] = last_heartbeat
        super().__init__(message, details)
        self.task_id = task_id
        self.last_heartbeat = last_heartbeat


class TaskNotFoundError(CairnError):
    """Task ID does not exist in contract."""

    def __init__(self, task_id: str):
        super().__init__(f"Task not found: {task_id}", {"task_id": task_id})
        self.task_id = task_id


class InvalidStateError(CairnError):
    """Operation not allowed in current task state."""

    def __init__(
        self,
        message: str,
        task_id: str,
        current_state: str,
        expected_states: list[str] | None = None,
    ):
        details = {
            "task_id": task_id,
            "current_state": current_state,
        }
        if expected_states:
            details["expected_states"] = expected_states
        super().__init__(message, details)
        self.task_id = task_id
        self.current_state = current_state
        self.expected_states = expected_states or []


class TimeoutError(CairnError):
    """Operation timed out."""

    def __init__(self, message: str, timeout_seconds: float):
        super().__init__(message, {"timeout_seconds": timeout_seconds})
        self.timeout_seconds = timeout_seconds


class NetworkError(CairnError):
    """Network-related error (RPC, IPFS gateway, etc.)."""

    def __init__(self, message: str, url: str | None = None):
        details = {}
        if url:
            details["url"] = url
        super().__init__(message, details)
        self.url = url
