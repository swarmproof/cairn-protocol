"""Tests for CAIRN SDK CheckpointStore."""

import pytest
import httpx
import respx

from sdk.checkpoint import CheckpointStore, IPFS_GATEWAYS
from sdk.exceptions import CheckpointError


@pytest.fixture
def pinata_jwt() -> str:
    """Sample Pinata JWT for testing."""
    return "test_jwt_token_12345"


@pytest.fixture
def checkpoint_store(pinata_jwt: str) -> CheckpointStore:
    """Create CheckpointStore instance."""
    return CheckpointStore(pinata_jwt=pinata_jwt)


class TestCheckpointStoreInit:
    """Tests for CheckpointStore initialization."""

    def test_init_with_jwt(self, pinata_jwt: str):
        """Test initialization with JWT."""
        store = CheckpointStore(pinata_jwt=pinata_jwt)
        assert store._jwt == pinata_jwt

    def test_init_without_jwt(self):
        """Test initialization without JWT raises error."""
        with pytest.raises(ValueError, match="pinata_jwt is required"):
            CheckpointStore(pinata_jwt="")

        with pytest.raises(ValueError):
            CheckpointStore(pinata_jwt=None)  # type: ignore


class TestCheckpointStoreWrite:
    """Tests for CheckpointStore.write()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_write_success(self, checkpoint_store: CheckpointStore):
        """Test successful checkpoint write."""
        # Mock Pinata API response
        respx.post("https://api.pinata.cloud/pinning/pinJSONToIPFS").mock(
            return_value=httpx.Response(
                200,
                json={"IpfsHash": "QmTestCid123456789"},
            )
        )

        data = {"subtask": 0, "result": "success"}
        cid = await checkpoint_store.write(data)

        assert cid == "QmTestCid123456789"

    @respx.mock
    @pytest.mark.asyncio
    async def test_write_with_name(self, checkpoint_store: CheckpointStore):
        """Test checkpoint write with custom name."""
        respx.post("https://api.pinata.cloud/pinning/pinJSONToIPFS").mock(
            return_value=httpx.Response(
                200,
                json={"IpfsHash": "QmNamedCid"},
            )
        )

        cid = await checkpoint_store.write(
            {"data": "test"},
            name="checkpoint-task-0",
        )

        assert cid == "QmNamedCid"

    @respx.mock
    @pytest.mark.asyncio
    async def test_write_api_error(self, checkpoint_store: CheckpointStore):
        """Test checkpoint write with API error."""
        respx.post("https://api.pinata.cloud/pinning/pinJSONToIPFS").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )

        with pytest.raises(CheckpointError, match="Pinata API error"):
            await checkpoint_store.write({"data": "test"})

    @respx.mock
    @pytest.mark.asyncio
    async def test_write_missing_hash(self, checkpoint_store: CheckpointStore):
        """Test checkpoint write with missing IpfsHash in response."""
        respx.post("https://api.pinata.cloud/pinning/pinJSONToIPFS").mock(
            return_value=httpx.Response(200, json={})
        )

        with pytest.raises(CheckpointError, match="missing IpfsHash"):
            await checkpoint_store.write({"data": "test"})


class TestCheckpointStoreRead:
    """Tests for CheckpointStore.read()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_read_success(self, checkpoint_store: CheckpointStore):
        """Test successful checkpoint read."""
        cid = "QmTestCid123"
        expected_data = {"subtask": 0, "result": "success"}

        # Mock first gateway
        respx.get(f"{IPFS_GATEWAYS[0]}{cid}").mock(
            return_value=httpx.Response(200, json=expected_data)
        )

        data = await checkpoint_store.read(cid)
        assert data == expected_data

    @respx.mock
    @pytest.mark.asyncio
    async def test_read_fallback_gateway(self, checkpoint_store: CheckpointStore):
        """Test checkpoint read with gateway fallback."""
        cid = "QmTestCid456"
        expected_data = {"data": "from_fallback"}

        # First gateway fails
        respx.get(f"{IPFS_GATEWAYS[0]}{cid}").mock(
            return_value=httpx.Response(500)
        )

        # Second gateway succeeds
        respx.get(f"{IPFS_GATEWAYS[1]}{cid}").mock(
            return_value=httpx.Response(200, json=expected_data)
        )

        data = await checkpoint_store.read(cid)
        assert data == expected_data

    @respx.mock
    @pytest.mark.asyncio
    async def test_read_all_gateways_fail(self, checkpoint_store: CheckpointStore):
        """Test checkpoint read when all gateways fail."""
        cid = "QmFailingCid"

        # All gateways fail
        for gateway in IPFS_GATEWAYS:
            respx.get(f"{gateway}{cid}").mock(
                return_value=httpx.Response(500)
            )

        with pytest.raises(CheckpointError, match="All IPFS gateways failed"):
            await checkpoint_store.read(cid)

    @pytest.mark.asyncio
    async def test_read_empty_cid(self, checkpoint_store: CheckpointStore):
        """Test checkpoint read with empty CID."""
        with pytest.raises(ValueError, match="CID is required"):
            await checkpoint_store.read("")


class TestCheckpointStoreUnpin:
    """Tests for CheckpointStore.unpin()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_unpin_success(self, checkpoint_store: CheckpointStore):
        """Test successful unpin."""
        cid = "QmToPinCid"

        respx.delete(f"https://api.pinata.cloud/pinning/unpin/{cid}").mock(
            return_value=httpx.Response(200)
        )

        result = await checkpoint_store.unpin(cid)
        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_unpin_already_unpinned(self, checkpoint_store: CheckpointStore):
        """Test unpin when already unpinned (404)."""
        cid = "QmAlreadyUnpinned"

        respx.delete(f"https://api.pinata.cloud/pinning/unpin/{cid}").mock(
            return_value=httpx.Response(404)
        )

        result = await checkpoint_store.unpin(cid)
        assert result is True  # 404 is considered success


class TestCheckpointStoreExists:
    """Tests for CheckpointStore.exists()."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_exists_true(self, checkpoint_store: CheckpointStore):
        """Test exists returns True when CID exists."""
        cid = "QmExistingCid"

        respx.head(f"{IPFS_GATEWAYS[0]}{cid}").mock(
            return_value=httpx.Response(200)
        )

        result = await checkpoint_store.exists(cid)
        assert result is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_exists_false(self, checkpoint_store: CheckpointStore):
        """Test exists returns False when CID doesn't exist."""
        cid = "QmNonExistentCid"

        # Both gateways return 404
        respx.head(f"{IPFS_GATEWAYS[0]}{cid}").mock(
            return_value=httpx.Response(404)
        )
        respx.head(f"{IPFS_GATEWAYS[1]}{cid}").mock(
            return_value=httpx.Response(404)
        )

        result = await checkpoint_store.exists(cid)
        assert result is False


class TestCheckpointStoreContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager(self, pinata_jwt: str):
        """Test async context manager."""
        async with CheckpointStore(pinata_jwt=pinata_jwt) as store:
            assert store._jwt == pinata_jwt

        # Client should be closed after context exit
        assert store._client is None or store._client.is_closed
