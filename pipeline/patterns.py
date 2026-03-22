"""
Pattern Detection

Analyzes failure/resolution records to detect patterns and anomalies.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of patterns that can be detected."""

    TIME_BASED = "TIME_BASED"
    TASK_TYPE = "TASK_TYPE"
    AGENT_PERFORMANCE = "AGENT_PERFORMANCE"
    FAILURE_CORRELATION = "FAILURE_CORRELATION"
    COST_ANOMALY = "COST_ANOMALY"


class Severity(str, Enum):
    """Pattern severity levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Pattern:
    """Detected pattern with metadata."""

    pattern_type: PatternType
    severity: Severity
    description: str
    confidence: float  # 0.0 to 1.0
    data: dict[str, Any]
    timestamp: int


class PatternDetector:
    """
    Detects patterns in failure and resolution data.

    Example:
        detector = PatternDetector()

        # Add records
        for record in records:
            detector.add_record(record)

        # Detect patterns
        patterns = detector.detect_patterns()
        for pattern in patterns:
            print(f"{pattern.pattern_type}: {pattern.description}")
    """

    def __init__(
        self,
        min_samples: int = 10,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize pattern detector.

        Args:
            min_samples: Minimum samples required to detect patterns
            confidence_threshold: Minimum confidence to report pattern
        """
        self._min_samples = min_samples
        self._confidence_threshold = confidence_threshold
        self._records: list[dict[str, Any]] = []

    def add_record(self, record: dict[str, Any]) -> None:
        """Add a record for analysis."""
        self._records.append(record)

    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()

    def detect_patterns(self) -> list[Pattern]:
        """
        Detect all patterns in collected records.

        Returns:
            List of detected patterns above confidence threshold
        """
        if len(self._records) < self._min_samples:
            logger.debug(
                f"Insufficient samples for pattern detection: {len(self._records)} < {self._min_samples}"
            )
            return []

        patterns = []

        # Run all detection algorithms
        patterns.extend(self._detect_time_patterns())
        patterns.extend(self._detect_task_type_patterns())
        patterns.extend(self._detect_agent_patterns())
        patterns.extend(self._detect_failure_correlations())
        patterns.extend(self._detect_cost_anomalies())

        # Filter by confidence
        filtered = [p for p in patterns if p.confidence >= self._confidence_threshold]

        logger.info(f"Detected {len(filtered)} patterns (from {len(patterns)} candidates)")
        return filtered

    def _detect_time_patterns(self) -> list[Pattern]:
        """Detect time-based failure patterns."""
        patterns = []

        # Get failure records
        failures = [r for r in self._records if r.get("record_type") == "failure"]

        if len(failures) < self._min_samples:
            return patterns

        # Group by hour of day
        hourly_counts: dict[int, int] = defaultdict(int)
        for failure in failures:
            timestamp = failure.get("timestamp", 0)
            hour = datetime.utcfromtimestamp(timestamp).hour
            hourly_counts[hour] += 1

        # Calculate variance
        counts = list(hourly_counts.values())
        if not counts:
            return patterns

        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        std_dev = variance**0.5

        # Detect peak hours (> mean + 1.5 * std_dev)
        threshold = mean + 1.5 * std_dev
        peak_hours = [hour for hour, count in hourly_counts.items() if count > threshold]

        if peak_hours:
            total_failures = len(failures)
            peak_failures = sum(hourly_counts[h] for h in peak_hours)
            confidence = peak_failures / total_failures

            patterns.append(
                Pattern(
                    pattern_type=PatternType.TIME_BASED,
                    severity=Severity.HIGH if confidence > 0.3 else Severity.MEDIUM,
                    description=f"Peak failure hours detected: {sorted(peak_hours)} UTC",
                    confidence=confidence,
                    data={
                        "peak_hours": sorted(peak_hours),
                        "hourly_distribution": dict(hourly_counts),
                        "mean": mean,
                        "std_dev": std_dev,
                    },
                    timestamp=int(datetime.utcnow().timestamp()),
                )
            )

        return patterns

    def _detect_task_type_patterns(self) -> list[Pattern]:
        """Detect task type failure patterns."""
        patterns = []

        # Group by task type
        task_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "failures": 0}
        )

        for record in self._records:
            task_type = record.get("task_type", "unknown")
            task_stats[task_type]["total"] += 1

            if record.get("record_type") == "failure":
                task_stats[task_type]["failures"] += 1

        # Calculate failure rates
        for task_type, stats in task_stats.items():
            if stats["total"] < self._min_samples:
                continue

            failure_rate = stats["failures"] / stats["total"]

            # Report high failure rates
            if failure_rate > 0.3:  # > 30% failure rate
                severity = Severity.CRITICAL if failure_rate > 0.5 else Severity.HIGH

                patterns.append(
                    Pattern(
                        pattern_type=PatternType.TASK_TYPE,
                        severity=severity,
                        description=f"High failure rate for {task_type}: {failure_rate:.1%}",
                        confidence=min(failure_rate * 1.5, 1.0),
                        data={
                            "task_type": task_type,
                            "failure_rate": failure_rate,
                            "total_tasks": stats["total"],
                            "failures": stats["failures"],
                        },
                        timestamp=int(datetime.utcnow().timestamp()),
                    )
                )

        return patterns

    def _detect_agent_patterns(self) -> list[Pattern]:
        """Detect agent performance patterns."""
        patterns = []

        # Group by agent
        agent_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "successful": 0, "failed": 0}
        )

        for record in self._records:
            if record.get("record_type") == "resolution":
                agent_id = record.get("metadata", {}).get("original_agent", {}).get("id")
                if not agent_id:
                    continue

                agent_stats[agent_id]["total"] += 1

                if record.get("recovery_successful", False):
                    agent_stats[agent_id]["successful"] += 1
                else:
                    agent_stats[agent_id]["failed"] += 1

        # Identify top and bottom performers
        for agent_id, stats in agent_stats.items():
            if stats["total"] < self._min_samples:
                continue

            success_rate = stats["successful"] / stats["total"]

            # Report exceptional performers
            if success_rate > 0.95:
                patterns.append(
                    Pattern(
                        pattern_type=PatternType.AGENT_PERFORMANCE,
                        severity=Severity.LOW,
                        description=f"High-performing agent detected: {agent_id[:20]}... ({success_rate:.1%} success)",
                        confidence=success_rate,
                        data={
                            "agent_id": agent_id,
                            "success_rate": success_rate,
                            "total_tasks": stats["total"],
                            "successful": stats["successful"],
                        },
                        timestamp=int(datetime.utcnow().timestamp()),
                    )
                )

            # Report poor performers
            elif success_rate < 0.5:
                patterns.append(
                    Pattern(
                        pattern_type=PatternType.AGENT_PERFORMANCE,
                        severity=Severity.HIGH,
                        description=f"Low-performing agent detected: {agent_id[:20]}... ({success_rate:.1%} success)",
                        confidence=1.0 - success_rate,
                        data={
                            "agent_id": agent_id,
                            "success_rate": success_rate,
                            "total_tasks": stats["total"],
                            "failed": stats["failed"],
                        },
                        timestamp=int(datetime.utcnow().timestamp()),
                    )
                )

        return patterns

    def _detect_failure_correlations(self) -> list[Pattern]:
        """Detect correlated failure types."""
        patterns = []

        # Get failures
        failures = [r for r in self._records if r.get("record_type") == "failure"]

        if len(failures) < self._min_samples:
            return patterns

        # Count failure types
        failure_type_counts: dict[str, int] = defaultdict(int)
        for failure in failures:
            failure_type = failure.get("failure_type", "UNKNOWN")
            failure_type_counts[failure_type] += 1

        # Find dominant failure types (> 20% of failures)
        total_failures = len(failures)
        for failure_type, count in failure_type_counts.items():
            frequency = count / total_failures

            if frequency > 0.2:  # > 20% of all failures
                severity = Severity.HIGH if frequency > 0.4 else Severity.MEDIUM

                patterns.append(
                    Pattern(
                        pattern_type=PatternType.FAILURE_CORRELATION,
                        severity=severity,
                        description=f"Dominant failure type: {failure_type} ({frequency:.1%} of failures)",
                        confidence=frequency,
                        data={
                            "failure_type": failure_type,
                            "frequency": frequency,
                            "count": count,
                            "total_failures": total_failures,
                        },
                        timestamp=int(datetime.utcnow().timestamp()),
                    )
                )

        return patterns

    def _detect_cost_anomalies(self) -> list[Pattern]:
        """Detect cost anomalies."""
        patterns = []

        # Get resolution records with costs
        resolutions = [
            r
            for r in self._records
            if r.get("record_type") == "resolution" and "total_cost" in r
        ]

        if len(resolutions) < self._min_samples:
            return patterns

        # Calculate cost statistics
        costs = [float(r.get("total_cost", "0")) for r in resolutions]
        mean_cost = sum(costs) / len(costs)
        variance = sum((x - mean_cost) ** 2 for x in costs) / len(costs)
        std_dev = variance**0.5

        # Detect outliers (> mean + 2 * std_dev)
        threshold = mean_cost + 2 * std_dev
        high_cost_tasks = [r for r, c in zip(resolutions, costs) if c > threshold]

        if high_cost_tasks:
            confidence = len(high_cost_tasks) / len(resolutions)

            patterns.append(
                Pattern(
                    pattern_type=PatternType.COST_ANOMALY,
                    severity=Severity.MEDIUM,
                    description=f"{len(high_cost_tasks)} tasks with abnormally high costs detected",
                    confidence=confidence,
                    data={
                        "mean_cost": mean_cost,
                        "std_dev": std_dev,
                        "threshold": threshold,
                        "anomaly_count": len(high_cost_tasks),
                        "sample_task_ids": [
                            t.get("task_id", "")[:16] + "..."
                            for t in high_cost_tasks[:5]
                        ],
                    },
                    timestamp=int(datetime.utcnow().timestamp()),
                )
            )

        return patterns

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary statistics for current records.

        Returns:
            Summary statistics dictionary
        """
        total_records = len(self._records)
        failures = [r for r in self._records if r.get("record_type") == "failure"]
        resolutions = [r for r in self._records if r.get("record_type") == "resolution"]

        successful_resolutions = [
            r for r in resolutions if r.get("recovery_successful", False)
        ]

        return {
            "total_records": total_records,
            "failure_count": len(failures),
            "resolution_count": len(resolutions),
            "success_rate": (
                len(successful_resolutions) / len(resolutions)
                if resolutions
                else 0.0
            ),
            "ready_for_detection": total_records >= self._min_samples,
        }
