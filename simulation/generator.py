"""Generate synthetic task-failure events for Monte Carlo simulation."""

import numpy as np
from dataclasses import dataclass
from simulation.config import FAILURE_CLASSES, FAILURE_CLASS_DISTRIBUTION, TASK_TYPES


@dataclass
class TaskFailureEvent:
    task_type: str
    total_subtasks: int
    failure_subtask: int
    failure_class: str
    budget_remaining: float
    deadline_remaining: float
    fallback_skill: float

    @property
    def remaining_subtasks(self) -> int:
        return self.total_subtasks - self.failure_subtask


def generate_events(n: int, rng: np.random.Generator) -> list[TaskFailureEvent]:
    """Generate n synthetic task-failure events."""

    # Task types: uniform across 5 types
    task_types = rng.choice(TASK_TYPES, size=n)

    # Total subtasks: Poisson(lambda=8) + 2, clipped to [2, 50]
    total_subtasks = np.clip(rng.poisson(lam=8, size=n) + 2, 2, 50)

    # Failure point: uniform within task
    failure_subtasks = np.array([rng.integers(1, ts + 1) for ts in total_subtasks])

    # Failure class: weighted sampling
    classes = list(FAILURE_CLASS_DISTRIBUTION.keys())
    probs = list(FAILURE_CLASS_DISTRIBUTION.values())
    failure_classes = rng.choice(classes, size=n, p=probs)

    # Progress ratio (how far through the task)
    progress = failure_subtasks / total_subtasks

    # Budget remaining: correlated with progress + noise
    budget_remaining = np.clip(1.0 - progress + rng.normal(0, 0.05, size=n), 0.0, 1.0)

    # Deadline remaining: correlated with progress + noise
    deadline_remaining = np.clip(1.0 - progress + rng.normal(0, 0.03, size=n), 0.0, 1.0)

    # Fallback skill: Beta(5, 2) shifted to [0.5, 1.0] (admission gate filters low skill)
    raw_skill = rng.beta(5, 2, size=n)
    fallback_skill = 0.5 + 0.5 * raw_skill  # maps [0,1] → [0.5, 1.0]

    events = []
    for i in range(n):
        events.append(TaskFailureEvent(
            task_type=task_types[i],
            total_subtasks=int(total_subtasks[i]),
            failure_subtask=int(failure_subtasks[i]),
            failure_class=failure_classes[i],
            budget_remaining=float(budget_remaining[i]),
            deadline_remaining=float(deadline_remaining[i]),
            fallback_skill=float(fallback_skill[i]),
        ))
    return events


def generate_events_vectorized(n: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Generate n events as numpy arrays for fast vectorized computation."""

    total_subtasks = np.clip(rng.poisson(lam=8, size=n) + 2, 2, 50).astype(float)
    failure_subtasks = np.array([rng.integers(1, int(ts) + 1) for ts in total_subtasks], dtype=float)

    classes = list(FAILURE_CLASS_DISTRIBUTION.keys())
    probs = list(FAILURE_CLASS_DISTRIBUTION.values())
    failure_classes = rng.choice(classes, size=n, p=probs)

    progress = failure_subtasks / total_subtasks
    budget_remaining = np.clip(1.0 - progress + rng.normal(0, 0.05, size=n), 0.0, 1.0)
    deadline_remaining = np.clip(1.0 - progress + rng.normal(0, 0.03, size=n), 0.0, 1.0)

    raw_skill = rng.beta(5, 2, size=n)
    fallback_skill = 0.5 + 0.5 * raw_skill

    remaining_subtasks = total_subtasks - failure_subtasks

    return {
        "failure_class": failure_classes,
        "budget_remaining": budget_remaining,
        "deadline_remaining": deadline_remaining,
        "fallback_skill": fallback_skill,
        "remaining_subtasks": remaining_subtasks,
        "task_type": rng.choice(TASK_TYPES, size=n),
    }
