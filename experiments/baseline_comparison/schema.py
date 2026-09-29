"""Checkpoint schema shared by every checkpointing system in the benchmark.

A checkpoint is written after each completed subtask:

    {task_id, subtask_index, output, context, schema_version}

``subtask_index`` is the 0-based index of the step that produced ``output``;
``context`` holds every step output produced so far, keyed by step name, so a
worker that has never seen the task can resume from the checkpoint alone.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

REQUIRED_FIELDS = ("task_id", "subtask_index", "output", "context", "schema_version")


class CheckpointSchemaError(ValueError):
    """A checkpoint does not match the schema."""


@dataclass(frozen=True)
class Checkpoint:
    task_id: str
    subtask_index: int
    output: Any
    context: Dict[str, Any]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        validate(data)
        return cls(
            task_id=data["task_id"],
            subtask_index=data["subtask_index"],
            output=copy.deepcopy(data["output"]),
            context=copy.deepcopy(data["context"]),
            schema_version=data["schema_version"],
        )


def validate(data: Dict[str, Any]) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise CheckpointSchemaError(f"missing fields: {missing}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise CheckpointSchemaError(f"unsupported schema_version {data['schema_version']}")
    if not isinstance(data["subtask_index"], int) or data["subtask_index"] < 0:
        raise CheckpointSchemaError("subtask_index must be a non-negative int")
    if not isinstance(data["context"], dict):
        raise CheckpointSchemaError("context must be an object")


class CheckpointStore:
    """Append-only checkpoint log keyed by task (stands in for IPFS + on-chain CIDs)."""

    def __init__(self) -> None:
        self._log: Dict[str, List[str]] = {}

    def commit(self, checkpoint: Checkpoint) -> int:
        """Store a checkpoint; returns the number of checkpoints now committed."""
        validate(checkpoint.to_dict())
        self._log.setdefault(checkpoint.task_id, []).append(checkpoint.to_json())
        return len(self._log[checkpoint.task_id])

    def latest(self, task_id: str) -> Optional[Checkpoint]:
        entries = self._log.get(task_id)
        if not entries:
            return None
        return Checkpoint.from_dict(json.loads(entries[-1]))

    def count(self, task_id: str) -> int:
        return len(self._log.get(task_id, []))
