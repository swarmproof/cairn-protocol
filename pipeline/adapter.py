"""
Bonfires Adapter

Event listener and adapter for CAIRN Protocol -> Bonfires integration.
Handles TaskFailed and TaskResolved events, creates records, pins to IPFS, indexes in Bonfires.
"""

import logging
import time
from typing import Any, Optional

from sdk.checkpoint import CheckpointStore
from pipeline.bonfires import BonfiresClient, BonfiresError
from pipeline.config import PipelineConfig
from pipeline.patterns import PatternDetector, Pattern
from pipeline.records import (
    FailureRecord,
    ResolutionRecord,
    FailureClass,
    FailureType,
    AgentResolutionInfo,
)

logger = logging.getLogger(__name__)


class BonfiresAdapter:
    """
    Adapter for writing CAIRN events to Bonfires knowledge graph.

    Listens for on-chain events and:
    1. Creates structured FailureRecord or ResolutionRecord
    2. Pins record to IPFS via Pinata
    3. Indexes record in Bonfires for querying
    4. Detects patterns and logs alerts

    Example:
        config = PipelineConfig.from_env()
        ipfs = CheckpointStore(config.pinata_jwt)
        bonfires = BonfiresClient(config)
        adapter = BonfiresAdapter(bonfires, ipfs)

        # Handle event
        await adapter.on_task_failed(task_failed_event)
    """

    def __init__(
        self,
        bonfires: BonfiresClient,
        ipfs: CheckpointStore,
        pattern_detector: Optional[PatternDetector] = None,
    ):
        """
        Initialize Bonfires adapter.

        Args:
            bonfires: Bonfires client for indexing
            ipfs: IPFS client for pinning records
            pattern_detector: Optional pattern detector for analysis
        """
        self._bonfires = bonfires
        self._ipfs = ipfs
        self._detector = pattern_detector or PatternDetector()

    async def on_task_failed(self, event: dict[str, Any]) -> str:
        """
        Handle TaskFailed event.

        Creates a FailureRecord, pins to IPFS, and indexes in Bonfires.

        Args:
            event: TaskFailed event data with fields:
                - task_id: bytes32 task identifier
                - agent: address
                - failure_class: FailureClass enum
                - checkpoint_count: int
                - block_number: int
                - timestamp: int
                - task_type: str (optional)
                - failure_details: dict (optional)

        Returns:
            IPFS CID of the failure record

        Raises:
            BonfiresError: If indexing fails
        """
        task_id = event.get("task_id", "")
        if not task_id.startswith("0x"):
            task_id = f"0x{task_id.hex()}" if hasattr(task_id, "hex") else task_id

        # Extract event data
        agent_address = event.get("agent", "")
        failure_class_value = event.get("failure_class", 0)
        checkpoint_count = event.get("checkpoint_count", 0)
        block_number = event.get("block_number", 0)
        timestamp = event.get("timestamp", int(time.time()))

        # Additional context (may come from off-chain indexer)
        task_type = event.get("task_type", "unknown")
        failure_details = event.get("failure_details", {})
        total_checkpoints = event.get("total_checkpoints_expected", 10)
        cost_at_failure = event.get("cost_at_failure", "0.001")
        budget_remaining_pct = event.get("budget_remaining_pct", 0.5)
        deadline_remaining_pct = event.get("deadline_remaining_pct", 0.3)

        # Map failure class enum to our types
        failure_class = self._map_failure_class(failure_class_value)
        failure_type = self._infer_failure_type(failure_class, failure_details)

        # Calculate recovery score
        recovery_score = self._calculate_recovery_score(
            checkpoint_count=checkpoint_count,
            total_checkpoints=total_checkpoints,
            budget_remaining=budget_remaining_pct,
            deadline_remaining=deadline_remaining_pct,
        )

        # Create agent ID in ERC8004 format
        agent_id = f"erc8004://base/{agent_address}"

        # Build failure record
        try:
            failure_record = FailureRecord(
                task_id=task_id,
                agent_id=agent_id,
                task_type=task_type,
                failure_class=failure_class,
                failure_type=failure_type,
                failure_details=failure_details,
                checkpoint_count_at_failure=checkpoint_count,
                total_checkpoints_expected=total_checkpoints,
                cost_at_failure=cost_at_failure,
                budget_remaining_pct=budget_remaining_pct,
                deadline_remaining_pct=deadline_remaining_pct,
                recovery_score=recovery_score,
                block_number=block_number,
                timestamp=timestamp,
            )

            # Pin to IPFS
            ipfs_payload = failure_record.to_ipfs_payload()
            cid = await self._ipfs.write(
                ipfs_payload,
                name=f"failure-{task_id[:16]}",
            )

            logger.info(f"Failure record pinned to IPFS: {cid}")

            # Index in Bonfires
            bonfires_data = failure_record.to_bonfires_record()
            record_id = await self._bonfires.write_record(
                record_type="failure",
                data=bonfires_data,
                cid=cid,
                tags=[task_type, failure_class.value, failure_type.value],
            )

            logger.info(f"Failure record indexed in Bonfires: {record_id}")

            # Add to pattern detector
            self._detector.add_record({**bonfires_data, "record_type": "failure"})

            return cid

        except Exception as e:
            logger.error(f"Failed to process TaskFailed event: {e}")
            raise BonfiresError(f"Failed to process failure event: {e}") from e

    async def on_task_resolved(self, event: dict[str, Any]) -> str:
        """
        Handle TaskResolved event.

        Creates a ResolutionRecord, pins to IPFS, and indexes in Bonfires.

        Args:
            event: TaskResolved event data with fields:
                - task_id: bytes32
                - primary_agent: address
                - fallback_agent: address (or zero address)
                - primary_checkpoints: int
                - fallback_checkpoints: int
                - primary_payout: wei
                - fallback_payout: wei
                - protocol_fee: wei
                - block_number: int
                - timestamp: int
                - task_type: str (optional)
                - failure_record_cid: str (optional)

        Returns:
            IPFS CID of the resolution record

        Raises:
            BonfiresError: If indexing fails
        """
        task_id = event.get("task_id", "")
        if not task_id.startswith("0x"):
            task_id = f"0x{task_id.hex()}" if hasattr(task_id, "hex") else task_id

        # Extract event data
        primary_agent_addr = event.get("primary_agent", "")
        fallback_agent_addr = event.get("fallback_agent", "")
        primary_checkpoints = event.get("primary_checkpoints", 0)
        fallback_checkpoints = event.get("fallback_checkpoints", 0)
        primary_payout_wei = event.get("primary_payout", 0)
        fallback_payout_wei = event.get("fallback_payout", 0)
        protocol_fee_wei = event.get("protocol_fee", 0)
        block_number = event.get("block_number", 0)
        timestamp = event.get("timestamp", int(time.time()))

        # Additional context
        task_type = event.get("task_type", "unknown")
        failure_record_cid = event.get("failure_record_cid")
        start_block = event.get("start_block", block_number)
        states_traversed = event.get("states_traversed", ["RUNNING", "RESOLVED"])

        # Determine if recovery was attempted
        zero_address = "0x0000000000000000000000000000000000000000"
        recovery_attempted = (
            fallback_agent_addr != zero_address and fallback_checkpoints > 0
        )
        recovery_successful = recovery_attempted and fallback_payout_wei > 0

        # Convert wei to ETH
        def wei_to_eth(wei: int) -> str:
            return f"{wei / 10**18:.6f}"

        primary_cost = wei_to_eth(primary_payout_wei)
        fallback_cost = wei_to_eth(fallback_payout_wei)
        total_cost = wei_to_eth(primary_payout_wei + fallback_payout_wei)
        escrow_total = wei_to_eth(
            primary_payout_wei + fallback_payout_wei + protocol_fee_wei
        )
        protocol_fee = wei_to_eth(protocol_fee_wei)

        # Build agent info
        original_agent = AgentResolutionInfo(
            id=f"erc8004://base/{primary_agent_addr}",
            checkpoint_count=primary_checkpoints,
            cost=primary_cost,
            payout=primary_cost,
        )

        fallback_agent_info = None
        if recovery_attempted:
            fallback_agent_info = AgentResolutionInfo(
                id=f"erc8004://base/{fallback_agent_addr}",
                checkpoint_count=fallback_checkpoints,
                cost=fallback_cost,
                payout=fallback_cost,
            )

        # Calculate duration
        duration_blocks = block_number - start_block

        try:
            # Build resolution record
            resolution_record = ResolutionRecord(
                task_id=task_id,
                states_traversed=states_traversed,
                recovery_attempted=recovery_attempted,
                recovery_successful=recovery_successful,
                original_agent=original_agent,
                fallback_agent=fallback_agent_info,
                task_type=task_type,
                total_cost=total_cost,
                total_duration_blocks=duration_blocks,
                escrow_total=escrow_total,
                protocol_fee=protocol_fee,
                failure_record_cid=failure_record_cid,
                block_number=block_number,
                timestamp=timestamp,
            )

            # Pin to IPFS
            ipfs_payload = resolution_record.to_ipfs_payload()
            cid = await self._ipfs.write(
                ipfs_payload,
                name=f"resolution-{task_id[:16]}",
            )

            logger.info(f"Resolution record pinned to IPFS: {cid}")

            # Index in Bonfires
            bonfires_data = resolution_record.to_bonfires_record()
            record_id = await self._bonfires.write_record(
                record_type="resolution",
                data=bonfires_data,
                cid=cid,
                tags=[task_type, "resolved", "recovery" if recovery_attempted else "direct"],
            )

            logger.info(f"Resolution record indexed in Bonfires: {record_id}")

            # Add to pattern detector
            self._detector.add_record({**bonfires_data, "record_type": "resolution"})

            return cid

        except Exception as e:
            logger.error(f"Failed to process TaskResolved event: {e}")
            raise BonfiresError(f"Failed to process resolution event: {e}") from e

    async def on_pattern_detected(self, pattern: Pattern) -> None:
        """
        Handle detected pattern.

        Logs pattern and could trigger alerts/notifications.

        Args:
            pattern: Detected pattern
        """
        severity_emoji = {
            "LOW": "ℹ️",
            "MEDIUM": "⚠️",
            "HIGH": "🔴",
            "CRITICAL": "🚨",
        }

        emoji = severity_emoji.get(pattern.severity.value, "📊")

        logger.warning(
            f"{emoji} PATTERN DETECTED [{pattern.pattern_type.value}] "
            f"Severity: {pattern.severity.value} | "
            f"Confidence: {pattern.confidence:.1%} | "
            f"{pattern.description}"
        )

        # Could send to webhook, alerting service, etc.
        # For now, just log

    def run_pattern_detection(self) -> list[Pattern]:
        """
        Run pattern detection on collected records.

        Returns:
            List of detected patterns

        Raises:
            Exception: If pattern detection fails
        """
        try:
            patterns = self._detector.detect_patterns()

            for pattern in patterns:
                # Async safe - just log synchronously here
                logger.info(f"Pattern detected: {pattern.description}")

            return patterns

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            raise

    def get_statistics(self) -> dict[str, Any]:
        """
        Get adapter statistics.

        Returns:
            Statistics dictionary with record counts and detection readiness
        """
        return self._detector.get_summary()

    # ─────────────────────────────────────────────────────────────────────────
    # Helper Methods
    # ─────────────────────────────────────────────────────────────────────────

    def _map_failure_class(self, value: int) -> FailureClass:
        """Map on-chain failure class enum to FailureClass."""
        mapping = {
            0: FailureClass.LIVENESS,
            1: FailureClass.RESOURCE,
            2: FailureClass.EXECUTION,
            3: FailureClass.DEADLINE,
        }
        return mapping.get(value, FailureClass.EXECUTION)

    def _infer_failure_type(
        self,
        failure_class: FailureClass,
        details: dict[str, Any],
    ) -> FailureType:
        """Infer specific failure type from class and details."""
        # Check details for hints
        http_status = details.get("http_status")
        error_code = details.get("error_code")

        if failure_class == FailureClass.LIVENESS:
            if "crashed" in str(details).lower():
                return FailureType.AGENT_CRASHED
            return FailureType.HEARTBEAT_TIMEOUT

        elif failure_class == FailureClass.RESOURCE:
            if http_status == 429:
                return FailureType.RATE_LIMIT
            if http_status in (502, 503, 504):
                return FailureType.API_UNAVAILABLE
            if "quota" in str(details).lower():
                return FailureType.QUOTA_EXCEEDED
            if "funds" in str(details).lower():
                return FailureType.INSUFFICIENT_FUNDS
            return FailureType.API_UNAVAILABLE

        elif failure_class == FailureClass.EXECUTION:
            if "validation" in str(details).lower() or "invalid" in str(details).lower():
                return FailureType.INVALID_INPUT
            if "dependency" in str(details).lower():
                return FailureType.DEPENDENCY_FAILURE
            return FailureType.LOGIC_ERROR

        elif failure_class == FailureClass.DEADLINE:
            if "budget" in str(details).lower():
                return FailureType.BUDGET_EXCEEDED
            return FailureType.TIMEOUT

        return FailureType.LOGIC_ERROR

    def _calculate_recovery_score(
        self,
        checkpoint_count: int,
        total_checkpoints: int,
        budget_remaining: float,
        deadline_remaining: float,
    ) -> float:
        """
        Calculate recovery likelihood score (0-1).

        Factors:
        - Progress made (checkpoints completed)
        - Budget remaining
        - Deadline remaining

        Returns:
            Recovery score between 0.0 and 1.0
        """
        if total_checkpoints == 0:
            progress_score = 0.0
        else:
            progress_score = checkpoint_count / total_checkpoints

        # Weighted average: progress (40%), budget (30%), deadline (30%)
        recovery_score = (
            progress_score * 0.4 + budget_remaining * 0.3 + deadline_remaining * 0.3
        )

        return min(max(recovery_score, 0.0), 1.0)
