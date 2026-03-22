"""
Tests for pattern detection.
"""

import pytest
import time
from datetime import datetime
from pipeline.patterns import PatternDetector, PatternType, Severity


class TestPatternDetector:
    """Tests for PatternDetector."""

    def test_insufficient_samples(self):
        """Test that insufficient samples returns empty patterns."""
        detector = PatternDetector(min_samples=10)

        # Add only 5 samples
        for i in range(5):
            detector.add_record({
                "record_type": "failure",
                "task_type": "test",
                "timestamp": int(time.time()),
            })

        patterns = detector.detect_patterns()
        assert len(patterns) == 0

    def test_time_pattern_detection(self):
        """Test detection of time-based failure patterns."""
        detector = PatternDetector(min_samples=10, confidence_threshold=0.1)

        # Create concentrated failures at hour 14
        from datetime import timezone
        base_time = int(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp())

        # 30 failures at hour 14
        for i in range(30):
            detector.add_record({
                "record_type": "failure",
                "task_type": "test",
                "timestamp": base_time + (14 * 3600) + (i * 60),
            })

        # 5 failures at other hours
        for hour in [2, 4, 6, 8, 10]:
            detector.add_record({
                "record_type": "failure",
                "task_type": "test",
                "timestamp": base_time + (hour * 3600),
            })

        patterns = detector.detect_patterns()

        # Should detect peak at hour 14
        time_patterns = [p for p in patterns if p.pattern_type == PatternType.TIME_BASED]
        assert len(time_patterns) > 0
        assert 14 in time_patterns[0].data["peak_hours"]

    def test_task_type_pattern_detection(self):
        """Test detection of task type failure patterns."""
        detector = PatternDetector(min_samples=10, confidence_threshold=0.2)

        # Task type with high failure rate
        for i in range(20):
            detector.add_record({
                "record_type": "failure",
                "task_type": "risky_task",
                "timestamp": int(time.time()),
            })

        # Add some successes
        for i in range(5):
            detector.add_record({
                "record_type": "resolution",
                "task_type": "risky_task",
                "recovery_successful": True,
                "timestamp": int(time.time()),
            })

        patterns = detector.detect_patterns()

        # Should detect high failure rate
        task_patterns = [p for p in patterns if p.pattern_type == PatternType.TASK_TYPE]
        assert len(task_patterns) > 0
        assert task_patterns[0].data["task_type"] == "risky_task"
        assert task_patterns[0].data["failure_rate"] > 0.3

    def test_agent_performance_detection(self):
        """Test detection of agent performance patterns."""
        detector = PatternDetector(min_samples=10, confidence_threshold=0.5)

        # High-performing agent
        good_agent = "erc8004://base/0x1111111111111111111111111111111111111111"
        for i in range(20):
            detector.add_record({
                "record_type": "resolution",
                "task_type": "test",
                "recovery_successful": True,
                "metadata": {
                    "original_agent": {"id": good_agent},
                },
                "timestamp": int(time.time()),
            })

        # Low-performing agent
        bad_agent = "erc8004://base/0x2222222222222222222222222222222222222222"
        for i in range(15):
            detector.add_record({
                "record_type": "resolution",
                "task_type": "test",
                "recovery_successful": False,
                "metadata": {
                    "original_agent": {"id": bad_agent},
                },
                "timestamp": int(time.time()),
            })

        for i in range(5):
            detector.add_record({
                "record_type": "resolution",
                "task_type": "test",
                "recovery_successful": True,
                "metadata": {
                    "original_agent": {"id": bad_agent},
                },
                "timestamp": int(time.time()),
            })

        patterns = detector.detect_patterns()

        agent_patterns = [
            p for p in patterns if p.pattern_type == PatternType.AGENT_PERFORMANCE
        ]
        assert len(agent_patterns) >= 1  # At least high performer or low performer

    def test_failure_correlation_detection(self):
        """Test detection of correlated failure types."""
        detector = PatternDetector(min_samples=10, confidence_threshold=0.15)

        # Dominant failure type: RATE_LIMIT
        for i in range(25):
            detector.add_record({
                "record_type": "failure",
                "failure_type": "RATE_LIMIT",
                "task_type": "test",
                "timestamp": int(time.time()),
            })

        # Other failure types
        for failure_type in ["TIMEOUT", "LOGIC_ERROR"]:
            for i in range(3):
                detector.add_record({
                    "record_type": "failure",
                    "failure_type": failure_type,
                    "task_type": "test",
                    "timestamp": int(time.time()),
                })

        patterns = detector.detect_patterns()

        correlation_patterns = [
            p for p in patterns if p.pattern_type == PatternType.FAILURE_CORRELATION
        ]
        assert len(correlation_patterns) > 0
        assert correlation_patterns[0].data["failure_type"] == "RATE_LIMIT"

    def test_cost_anomaly_detection(self):
        """Test detection of cost anomalies."""
        detector = PatternDetector(min_samples=10, confidence_threshold=0.05)

        # Normal costs: 0.001 - 0.003 ETH
        for i in range(30):
            detector.add_record({
                "record_type": "resolution",
                "task_type": "test",
                "total_cost": "0.002",
                "timestamp": int(time.time()),
            })

        # Anomalous high costs
        for i in range(3):
            detector.add_record({
                "record_type": "resolution",
                "task_type": "test",
                "total_cost": "0.050",  # 25x higher
                "timestamp": int(time.time()),
            })

        patterns = detector.detect_patterns()

        cost_patterns = [p for p in patterns if p.pattern_type == PatternType.COST_ANOMALY]
        assert len(cost_patterns) > 0

    def test_get_summary(self):
        """Test getting summary statistics."""
        detector = PatternDetector(min_samples=10)

        # Add records
        for i in range(15):
            detector.add_record({
                "record_type": "failure",
                "task_type": "test",
                "timestamp": int(time.time()),
            })

        for i in range(10):
            detector.add_record({
                "record_type": "resolution",
                "task_type": "test",
                "recovery_successful": True,
                "timestamp": int(time.time()),
            })

        summary = detector.get_summary()

        assert summary["total_records"] == 25
        assert summary["failure_count"] == 15
        assert summary["resolution_count"] == 10
        assert summary["success_rate"] == 1.0  # All resolutions successful
        assert summary["ready_for_detection"] is True

    def test_clear_records(self):
        """Test clearing records."""
        detector = PatternDetector()

        # Add records
        for i in range(5):
            detector.add_record({"record_type": "failure"})

        summary = detector.get_summary()
        assert summary["total_records"] == 5

        # Clear
        detector.clear()

        summary = detector.get_summary()
        assert summary["total_records"] == 0
