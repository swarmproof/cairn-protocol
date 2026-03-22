"""
Bonfires Client

Client wrapper for Bonfires API integration.
Based on Bonfires API: https://docs.bonfires.ai/
"""

import logging
from typing import Any, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from pipeline.config import PipelineConfig
from pipeline.records import FailureRecord, ResolutionRecord

logger = logging.getLogger(__name__)


class BonfiresError(Exception):
    """Base exception for Bonfires client errors."""

    pass


class BonfiresClient:
    """
    Client for interacting with Bonfires knowledge graph API.

    Bonfires is a decentralized knowledge graph for AI agents.
    API documentation: https://docs.bonfires.ai/

    Example:
        config = PipelineConfig.from_env()
        client = BonfiresClient(config)

        # Write failure record
        await client.write_record(
            record_type="failure",
            data=failure_record.to_bonfires_record(),
            cid="Qm..."
        )

        # Query agent history
        history = await client.get_agent_history("erc8004://base/0x...")
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize Bonfires client.

        Args:
            config: Pipeline configuration with API key
        """
        self._api_key = config.bonfires_api_key
        self._api_url = config.bonfires_api_url
        self._room = config.bonfires_room
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "BonfiresClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def write_record(
        self,
        record_type: str,
        data: dict[str, Any],
        cid: str,
        tags: Optional[list[str]] = None,
    ) -> str:
        """
        Write a record to Bonfires knowledge graph.

        Args:
            record_type: Type of record ("failure" or "resolution")
            data: Record data (output of to_bonfires_record())
            cid: IPFS CID where full record is stored
            tags: Optional tags for categorization

        Returns:
            Record ID assigned by Bonfires

        Raises:
            BonfiresError: If write fails
        """
        client = await self._get_client()

        payload = {
            "room": self._room,
            "record_type": record_type,
            "data": data,
            "ipfs_cid": cid,
            "tags": tags or [],
        }

        try:
            response = await client.post(
                f"{self._api_url}/records",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            record_id = result.get("record_id")

            if not record_id:
                raise BonfiresError("Bonfires response missing record_id")

            logger.info(f"Record written to Bonfires: {record_id} (CID: {cid})")
            return record_id

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except Exception:
                pass

            raise BonfiresError(
                f"Bonfires API error ({e.response.status_code}): {error_detail}"
            ) from e

        except httpx.TimeoutException as e:
            raise BonfiresError("Bonfires request timed out") from e

        except Exception as e:
            raise BonfiresError(f"Failed to write record: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def query_records(
        self,
        record_type: Optional[str] = None,
        task_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Query records from Bonfires.

        Args:
            record_type: Filter by record type ("failure" or "resolution")
            task_type: Filter by task type (e.g., "defi.price_fetch")
            agent_id: Filter by agent ID (ERC8004 format)
            limit: Maximum records to return
            offset: Pagination offset

        Returns:
            List of matching records

        Raises:
            BonfiresError: If query fails
        """
        client = await self._get_client()

        params = {
            "room": self._room,
            "limit": limit,
            "offset": offset,
        }

        if record_type:
            params["record_type"] = record_type
        if task_type:
            params["task_type"] = task_type
        if agent_id:
            params["agent_id"] = agent_id

        try:
            response = await client.get(
                f"{self._api_url}/records",
                params=params,
            )
            response.raise_for_status()

            result = response.json()
            records = result.get("records", [])

            logger.debug(f"Queried {len(records)} records from Bonfires")
            return records

        except httpx.HTTPStatusError as e:
            raise BonfiresError(
                f"Bonfires query failed ({e.response.status_code})"
            ) from e

        except Exception as e:
            raise BonfiresError(f"Failed to query records: {e}") from e

    async def get_agent_history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Get execution history for a specific agent.

        Args:
            agent_id: Agent identifier (ERC8004 format)
            limit: Maximum records to return

        Returns:
            Agent history with aggregated stats

        Raises:
            BonfiresError: If query fails
        """
        # Query all records for this agent
        records = await self.query_records(
            agent_id=agent_id,
            limit=limit,
        )

        # Aggregate statistics
        failures = [r for r in records if r.get("record_type") == "failure"]
        resolutions = [r for r in records if r.get("record_type") == "resolution"]

        successful_resolutions = [
            r for r in resolutions if r.get("recovery_successful", False)
        ]

        total_tasks = len(resolutions)
        successful_tasks = len(successful_resolutions)
        failed_tasks = len(failures)

        success_rate = (
            successful_tasks / total_tasks if total_tasks > 0 else 0.0
        )

        return {
            "agent_id": agent_id,
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": success_rate,
            "recent_failures": failures[:10],
            "recent_resolutions": resolutions[:10],
        }

    async def get_task_type_stats(
        self,
        task_type: str,
        lookback_hours: int = 24,
    ) -> dict[str, Any]:
        """
        Get statistics for a specific task type.

        Args:
            task_type: Task type to analyze (e.g., "defi.price_fetch")
            lookback_hours: Hours to look back (default 24)

        Returns:
            Task type statistics

        Raises:
            BonfiresError: If query fails
        """
        # Query records for this task type
        records = await self.query_records(
            task_type=task_type,
            limit=1000,
        )

        # Filter by time window
        import time

        cutoff_timestamp = int(time.time()) - (lookback_hours * 3600)
        recent_records = [
            r for r in records if r.get("timestamp", 0) >= cutoff_timestamp
        ]

        # Aggregate stats
        failures = [r for r in recent_records if r.get("record_type") == "failure"]
        resolutions = [
            r for r in recent_records if r.get("record_type") == "resolution"
        ]

        total_tasks = len(resolutions)
        successful = [r for r in resolutions if r.get("recovery_successful", True)]
        success_rate = len(successful) / total_tasks if total_tasks > 0 else 0.0

        # Failure pattern analysis
        failure_types: dict[str, int] = {}
        for failure in failures:
            failure_type = failure.get("failure_type", "UNKNOWN")
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1

        # Cost analysis
        costs = [
            float(r.get("total_cost", "0")) for r in resolutions if "total_cost" in r
        ]
        avg_cost = sum(costs) / len(costs) if costs else 0.0

        # Duration analysis
        durations = [r.get("duration_blocks", 0) for r in resolutions]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "task_type": task_type,
            "lookback_hours": lookback_hours,
            "total_tasks": total_tasks,
            "success_rate": success_rate,
            "avg_cost_eth": avg_cost,
            "avg_duration_blocks": int(avg_duration),
            "failure_patterns": [
                {"failure_type": ft, "count": count}
                for ft, count in failure_types.items()
            ],
        }

    async def health_check(self) -> bool:
        """
        Check if Bonfires API is healthy.

        Returns:
            True if API is reachable and responding

        Raises:
            BonfiresError: If health check fails
        """
        client = await self._get_client()

        try:
            response = await client.get(f"{self._api_url}/health")
            response.raise_for_status()
            logger.debug("Bonfires health check passed")
            return True

        except Exception as e:
            raise BonfiresError(f"Bonfires health check failed: {e}") from e
