"""
CAIRN SDK CheckpointStore

IPFS checkpoint storage with Pinata pinning service.
"""

import json
import logging
import os
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from sdk.exceptions import CheckpointError, NetworkError

logger = logging.getLogger(__name__)

# IPFS gateways for reading (fallback order)
IPFS_GATEWAYS = [
    "https://gateway.pinata.cloud/ipfs/",
    "https://ipfs.io/ipfs/",
    "https://dweb.link/ipfs/",
    "https://cloudflare-ipfs.com/ipfs/",
]

# Pinata API endpoints
PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
PINATA_UNPIN_URL = "https://api.pinata.cloud/pinning/unpin/"

# Timeouts
REQUEST_TIMEOUT = 10.0  # seconds


class CheckpointStore:
    """
    IPFS checkpoint storage using Pinata for pinning.

    Example:
        # Auto-load from environment
        store = CheckpointStore()

        # Or provide explicitly
        store = CheckpointStore(pinata_jwt="your_jwt_token")

        # Write checkpoint
        cid = await store.write({"subtask": 0, "result": "success"})

        # Read checkpoint
        data = await store.read(cid)
    """

    def __init__(self, pinata_jwt: str | None = None):
        """
        Initialize CheckpointStore.

        Args:
            pinata_jwt: Pinata JWT token for authentication.
                        If not provided, will try to load from PINATA_JWT env var.
                        Get from https://app.pinata.cloud/developers/api-keys

        Raises:
            CheckpointError: If JWT is not provided and not found in environment
        """
        jwt = pinata_jwt or os.getenv("PINATA_JWT")

        if not jwt:
            raise CheckpointError(
                "PINATA_JWT is required. Either pass pinata_jwt parameter or set PINATA_JWT environment variable."
            )

        self._jwt = jwt
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "CheckpointStore":
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
    async def write(self, data: dict[str, Any], name: str | None = None) -> str:
        """
        Write checkpoint data to IPFS via Pinata.

        Args:
            data: Checkpoint data to store (must be JSON-serializable)
            name: Optional name for the pin (for Pinata dashboard)

        Returns:
            CID (Content Identifier) of the pinned content

        Raises:
            CheckpointError: If pinning fails after retries
        """
        client = await self._get_client()

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self._jwt}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "pinataContent": data,
        }

        if name:
            payload["pinataMetadata"] = {"name": name}

        try:
            response = await client.post(
                PINATA_PIN_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            cid = result.get("IpfsHash")

            if not cid:
                raise CheckpointError("Pinata response missing IpfsHash")

            logger.info(f"Checkpoint pinned: {cid}")
            return cid

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except Exception:
                pass

            raise CheckpointError(
                f"Pinata API error: {e.response.status_code}",
                gateway="pinata",
            ) from e

        except httpx.TimeoutException as e:
            raise CheckpointError(
                "Pinata request timed out",
                gateway="pinata",
            ) from e

        except Exception as e:
            raise CheckpointError(f"Failed to write checkpoint: {e}") from e

    async def read(self, cid: str) -> dict[str, Any]:
        """
        Read checkpoint data from IPFS.

        Tries multiple gateways with fallback.

        Args:
            cid: Content Identifier to fetch

        Returns:
            Checkpoint data as dictionary

        Raises:
            CheckpointError: If all gateways fail
        """
        if not cid:
            raise ValueError("CID is required")

        client = await self._get_client()
        last_error: Exception | None = None

        for gateway in IPFS_GATEWAYS:
            url = f"{gateway}{cid}"

            try:
                response = await self._fetch_with_retry(client, url)
                data = response.json()
                logger.debug(f"Checkpoint fetched from {gateway}")
                return data

            except Exception as e:
                logger.warning(f"Gateway {gateway} failed: {e}")
                last_error = e
                continue

        raise CheckpointError(
            f"All IPFS gateways failed for CID: {cid}",
            cid=cid,
        ) from last_error

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def _fetch_with_retry(
        self, client: httpx.AsyncClient, url: str
    ) -> httpx.Response:
        """Fetch URL with retry logic."""
        response = await client.get(url)
        response.raise_for_status()
        return response

    async def unpin(self, cid: str) -> bool:
        """
        Unpin content from Pinata.

        Args:
            cid: Content Identifier to unpin

        Returns:
            True if unpinned successfully

        Raises:
            CheckpointError: If unpin fails
        """
        client = await self._get_client()

        headers = {
            "Authorization": f"Bearer {self._jwt}",
        }

        try:
            response = await client.delete(
                f"{PINATA_UNPIN_URL}{cid}",
                headers=headers,
            )
            response.raise_for_status()
            logger.info(f"Checkpoint unpinned: {cid}")
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Already unpinned
                return True
            raise CheckpointError(
                f"Failed to unpin: {e.response.status_code}",
                cid=cid,
            ) from e

    async def exists(self, cid: str) -> bool:
        """
        Check if CID exists on IPFS.

        Args:
            cid: Content Identifier to check

        Returns:
            True if content exists
        """
        client = await self._get_client()

        for gateway in IPFS_GATEWAYS[:2]:  # Only try first 2 gateways
            url = f"{gateway}{cid}"
            try:
                response = await client.head(url, timeout=5.0)
                if response.status_code == 200:
                    return True
            except Exception:
                continue

        return False
