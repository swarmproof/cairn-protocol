"""
Bonfires Client

Client wrapper for Bonfires Knowledge Graph API integration.
API: https://tnt-v2.api.bonfires.ai/docs
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

logger = logging.getLogger(__name__)


class BonfiresError(Exception):
    """Base exception for Bonfires client errors."""

    pass


class BonfiresClient:
    """
    Client for interacting with Bonfires Knowledge Graph API.

    Bonfires is a decentralized knowledge graph for AI agents.
    API: https://tnt-v2.api.bonfires.ai

    Endpoints:
        - POST /knowledge_graph/episode_update - Write episodes
        - POST /delve - Query knowledge graph
        - GET /healthz - Health check

    Example:
        config = PipelineConfig.from_env()
        client = BonfiresClient(config)

        # Write failure episode
        episode_id = await client.write_episode(
            summary="Task 0x1234 failed: HEARTBEAT_MISSED",
            content="Agent 0xABCD missed heartbeat...",
            attributes={"task_id": "0x1234", "failure_type": "LIVENESS"},
            labels=["CAIRN", "TaskFailed"]
        )

        # Query patterns
        results = await client.delve("failure patterns for defi tasks")
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize Bonfires client.

        Args:
            config: Pipeline configuration with API key and bonfire_id
        """
        self._api_key = config.bonfires_api_key
        self._api_url = config.bonfires_api_url.rstrip("/")
        self._bonfire_id = config.bonfires_bonfire_id
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
    async def write_episode(
        self,
        summary: str,
        content: str,
        attributes: dict[str, Any],
        labels: list[str],
        source: str = "cairn-protocol",
        source_description: str = "CAIRN Protocol Event",
        user_updates: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        """
        Write an episode to Bonfires knowledge graph.

        Args:
            summary: Short summary of the episode
            content: Full content/description
            attributes: Structured attributes (task_id, failure_type, etc.)
            labels: List of label names for categorization
            source: Source identifier (default: "cairn-protocol")
            source_description: Human-readable source description
            user_updates: Optional user/agent activity updates

        Returns:
            Episode UUID assigned by Bonfires

        Raises:
            BonfiresError: If write fails
        """
        client = await self._get_client()

        # Build episode payload per Bonfires API spec
        payload = {
            "bonfire_id": self._bonfire_id,
            "episode": {
                "summary": summary,
                "content": content,
                "source": source,
                "source_description": source_description,
                "attributes": attributes,
            },
            "labels": [{"label_name": label} for label in labels],
        }

        if user_updates:
            payload["user_updates"] = user_updates

        try:
            response = await client.post(
                f"{self._api_url}/knowledge_graph/episode_update",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            episode_uuid = result.get("episode_uuid") or result.get("uuid") or result.get("id")

            if not episode_uuid:
                # Some APIs return success without explicit ID
                episode_uuid = f"episode-{attributes.get('task_id', 'unknown')[:16]}"
                logger.warning(f"Bonfires response missing episode_uuid, using: {episode_uuid}")

            logger.info(f"Episode written to Bonfires: {episode_uuid}")
            return episode_uuid

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
            raise BonfiresError(f"Failed to write episode: {e}") from e

    async def write_failure_episode(
        self,
        task_id: str,
        agent_id: str,
        task_type: str,
        failure_class: str,
        failure_type: str,
        checkpoint_count: int,
        recovery_score: float,
        block_number: int,
        failure_details: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Write a TaskFailed episode to Bonfires.

        Args:
            task_id: Task identifier (hex string)
            agent_id: Agent identifier (ERC8004 format)
            task_type: Type of task (e.g., "defi.price_fetch")
            failure_class: Failure class (LIVENESS, RESOURCE, EXECUTION, DEADLINE)
            failure_type: Specific failure type
            checkpoint_count: Number of checkpoints completed
            recovery_score: Recovery likelihood (0-1)
            block_number: Block number when failure occurred
            failure_details: Additional failure context

        Returns:
            Episode UUID
        """
        summary = f"Task {task_id[:16]}... failed: {failure_type} after {checkpoint_count} checkpoints"
        content = (
            f"Agent {agent_id} executing task type '{task_type}' experienced {failure_class} failure. "
            f"Failure type: {failure_type}. Recovery score: {recovery_score:.2f}. "
            f"Checkpoints completed: {checkpoint_count}."
        )

        attributes = {
            "task_id": task_id,
            "agent_id": agent_id,
            "task_type": task_type,
            "failure_class": failure_class,
            "failure_type": failure_type,
            "checkpoint_count": checkpoint_count,
            "recovery_score": recovery_score,
            "block_number": block_number,
            "chain_id": 84532,  # Base Sepolia
        }

        if failure_details:
            attributes["failure_details"] = failure_details

        labels = ["CAIRN", "TaskFailed", task_type, failure_class]

        user_updates = [
            {
                "user_id": agent_id,
                "username": f"Agent {agent_id[:10]}...",
                "per_label": [{"label_name": "FailedTask", "activity": "primary_agent"}],
            }
        ]

        return await self.write_episode(
            summary=summary,
            content=content,
            attributes=attributes,
            labels=labels,
            source_description="CAIRN TaskFailed event",
            user_updates=user_updates,
        )

    async def write_resolution_episode(
        self,
        task_id: str,
        original_agent: str,
        fallback_agent: Optional[str],
        task_type: str,
        recovery_attempted: bool,
        recovery_successful: bool,
        original_checkpoints: int,
        fallback_checkpoints: int,
        total_cost_eth: str,
        original_payout_eth: str,
        fallback_payout_eth: str,
        block_number: int,
    ) -> str:
        """
        Write a TaskResolved episode to Bonfires.

        Args:
            task_id: Task identifier
            original_agent: Original agent ID
            fallback_agent: Fallback agent ID (if recovery attempted)
            task_type: Type of task
            recovery_attempted: Whether recovery was attempted
            recovery_successful: Whether recovery succeeded
            original_checkpoints: Checkpoints by original agent
            fallback_checkpoints: Checkpoints by fallback agent
            total_cost_eth: Total cost in ETH
            original_payout_eth: Payout to original agent
            fallback_payout_eth: Payout to fallback agent
            block_number: Block number of resolution

        Returns:
            Episode UUID
        """
        if recovery_attempted:
            if recovery_successful:
                summary = f"Task {task_id[:16]}... resolved: Recovery successful via fallback"
            else:
                summary = f"Task {task_id[:16]}... resolved: Recovery attempted but failed"
        else:
            summary = f"Task {task_id[:16]}... resolved: Direct completion"

        content = (
            f"Original agent completed {original_checkpoints} checkpoints. "
            f"{'Fallback agent completed ' + str(fallback_checkpoints) + ' checkpoints. ' if recovery_attempted else ''}"
            f"Settlement: {original_payout_eth} ETH to original"
            f"{', ' + fallback_payout_eth + ' ETH to fallback' if recovery_attempted else ''}."
        )

        attributes = {
            "task_id": task_id,
            "task_type": task_type,
            "original_agent": original_agent,
            "fallback_agent": fallback_agent or "",
            "recovery_attempted": recovery_attempted,
            "recovery_successful": recovery_successful,
            "original_checkpoints": original_checkpoints,
            "fallback_checkpoints": fallback_checkpoints,
            "total_cost_eth": total_cost_eth,
            "original_payout_eth": original_payout_eth,
            "fallback_payout_eth": fallback_payout_eth,
            "block_number": block_number,
            "chain_id": 84532,
        }

        labels = ["CAIRN", "TaskResolved", task_type]
        if recovery_attempted:
            labels.append("RecoverySuccess" if recovery_successful else "RecoveryFailed")

        return await self.write_episode(
            summary=summary,
            content=content,
            attributes=attributes,
            labels=labels,
            source_description="CAIRN TaskResolved event",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def delve(
        self,
        query: str,
        num_results: int = 10,
    ) -> dict[str, Any]:
        """
        Query the Bonfires knowledge graph using natural language.

        Args:
            query: Natural language query (e.g., "failure patterns for defi tasks")
            num_results: Maximum number of results

        Returns:
            Query results with episodes, entities, and graph_id

        Raises:
            BonfiresError: If query fails
        """
        client = await self._get_client()

        payload = {
            "query": query,
            "bonfire_id": self._bonfire_id,
            "num_results": num_results,
        }

        try:
            response = await client.post(
                f"{self._api_url}/delve",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()

            logger.debug(f"Delve query returned {len(result.get('episodes', []))} episodes")
            return {
                "episodes": result.get("episodes", []),
                "entities": result.get("entities", []),
                "graph_id": result.get("graph_id"),
                "query": query,
            }

        except httpx.HTTPStatusError as e:
            raise BonfiresError(
                f"Bonfires delve failed ({e.response.status_code})"
            ) from e

        except Exception as e:
            raise BonfiresError(f"Failed to query Bonfires: {e}") from e

    async def get_failure_patterns(
        self,
        task_type: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Get failure patterns for a specific task type.

        Args:
            task_type: Task type to analyze (e.g., "defi.price_fetch")
            limit: Maximum number of results

        Returns:
            Failure pattern analysis
        """
        query = f"failure patterns and common issues for {task_type} tasks in CAIRN protocol"
        return await self.delve(query, num_results=limit)

    async def get_agent_history(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get execution history for a specific agent.

        Args:
            agent_id: Agent identifier (ERC8004 format)
            limit: Maximum number of results

        Returns:
            Agent history with episodes
        """
        query = f"all task failures and resolutions for agent {agent_id}"
        results = await self.delve(query, num_results=limit)

        # Extract and categorize episodes
        episodes = results.get("episodes", [])
        failures = [e for e in episodes if "TaskFailed" in str(e.get("labels", []))]
        resolutions = [e for e in episodes if "TaskResolved" in str(e.get("labels", []))]

        return {
            "agent_id": agent_id,
            "total_episodes": len(episodes),
            "failures": len(failures),
            "resolutions": len(resolutions),
            "recent_episodes": episodes[:10],
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
            response = await client.get(f"{self._api_url}/healthz")
            response.raise_for_status()

            result = response.json()
            status = result.get("status", "unknown")

            if status == "ok":
                logger.debug("Bonfires health check passed")
                return True
            else:
                raise BonfiresError(f"Bonfires unhealthy: {status}")

        except httpx.HTTPStatusError as e:
            raise BonfiresError(f"Bonfires health check failed ({e.response.status_code})") from e

        except Exception as e:
            raise BonfiresError(f"Bonfires health check failed: {e}") from e


# Legacy compatibility - map old method names to new ones
BonfiresClient.write_record = BonfiresClient.write_episode  # type: ignore
BonfiresClient.query_records = BonfiresClient.delve  # type: ignore
