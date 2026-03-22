"""
Tests for Olas Mech Marketplace integration

Tests the OlasMechClient SDK for querying and interacting with Olas mechs.
Uses mock Web3 provider to avoid actual network calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from web3 import Web3
from eth_typing import HexStr

import sys
sys.path.insert(0, '/Users/maroua/Projects/personal/ventures-studio/Git-repos/ai-agents/cairn-protocol/sdk')

from cairn.olas import OlasMechClient, MechInfo


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_web3():
    """Mock Web3 instance with test data"""
    mock = MagicMock()
    mock.is_connected.return_value = True
    mock.eth.chain_id = 100  # Gnosis Chain
    mock.eth.block_number = 1000000
    return mock


@pytest.fixture
def mock_registry_contract():
    """Mock Olas Mech registry contract"""
    mock = MagicMock()

    # Mock getMech response
    def mock_get_mech(service_id):
        mechs = {
            1: (
                "0x0000000000000000000000000000000000000100",  # mechAddress
                1,  # serviceId
                [Web3.keccak(text="price_oracle")],  # capabilities
                10000000000000000,  # pricePerRequest (0.01 ETH)
                True,  # active
                85,  # requestsCompleted
                15,  # requestsFailed
            ),
            2: (
                "0x0000000000000000000000000000000000000200",
                2,
                [Web3.keccak(text="trading_bot")],
                20000000000000000,
                True,
                90,
                10,
            ),
            3: (
                "0x0000000000000000000000000000000000000300",
                3,
                [Web3.keccak(text="data_analyst")],
                15000000000000000,
                False,  # inactive
                50,
                50,
            ),
        }
        result = MagicMock()
        result.call.return_value = mechs.get(service_id)
        return result

    # Mock getMechsByCapability response
    def mock_get_mechs_by_capability(capability):
        mappings = {
            Web3.keccak(text="price_oracle"): [1],
            Web3.keccak(text="trading_bot"): [2],
            Web3.keccak(text="data_analyst"): [3],
        }
        result = MagicMock()
        result.call.return_value = mappings.get(capability, [])
        return result

    # Mock isMechActive response
    def mock_is_mech_active(service_id):
        active_mechs = {1: True, 2: True, 3: False}
        result = MagicMock()
        result.call.return_value = active_mechs.get(service_id, False)
        return result

    # Mock getMechAddress response
    def mock_get_mech_address(service_id):
        addresses = {
            1: "0x0000000000000000000000000000000000000100",
            2: "0x0000000000000000000000000000000000000200",
            3: "0x0000000000000000000000000000000000000300",
        }
        result = MagicMock()
        result.call.return_value = addresses.get(service_id)
        return result

    # Mock getMechPrice response
    def mock_get_mech_price(service_id):
        prices = {1: 10000000000000000, 2: 20000000000000000, 3: 15000000000000000}
        result = MagicMock()
        result.call.return_value = prices.get(service_id, 0)
        return result

    mock.functions.getMech = mock_get_mech
    mock.functions.getMechsByCapability = mock_get_mechs_by_capability
    mock.functions.isMechActive = mock_is_mech_active
    mock.functions.getMechAddress = mock_get_mech_address
    mock.functions.getMechPrice = mock_get_mech_price

    return mock


@pytest.fixture
def client(mock_web3, mock_registry_contract):
    """OlasMechClient instance with mocked dependencies"""
    with patch("cairn.olas.Web3") as mock_web3_class:
        mock_web3_class.return_value = mock_web3
        mock_web3_class.to_checksum_address = Web3.to_checksum_address
        mock_web3_class.keccak = Web3.keccak
        mock_web3_class.to_wei = Web3.to_wei

        with patch.object(mock_web3.eth, "contract", return_value=mock_registry_contract):
            client = OlasMechClient(
                rpc_url="https://gnosis-rpc.publicnode.com",
                registry_address="0x9338b5153AE39BB89f50468E608eD9d764B755fD",
            )
            client.registry = mock_registry_contract
            return client


# ═══════════════════════════════════════════════════════════════
# CONNECTION TESTS
# ═══════════════════════════════════════════════════════════════

def test_client_initialization(client, mock_web3):
    """Test client initializes correctly"""
    assert client.web3 == mock_web3
    assert client.registry_address == Web3.to_checksum_address(
        "0x9338b5153AE39BB89f50468E608eD9d764B755fD"
    )


def test_connection_info(client):
    """Test get_connection_info returns correct data"""
    info = client.get_connection_info()

    assert info["connected"] is True
    assert info["chain_id"] == 100
    assert info["block_number"] == 1000000


# ═══════════════════════════════════════════════════════════════
# QUERY TESTS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_mech_info(client):
    """Test fetching mech information"""
    mech_info = await client.get_mech_info(1)

    assert mech_info.service_id == 1
    assert mech_info.mech_address == Web3.to_checksum_address(
        "0x0000000000000000000000000000000000000100"
    )
    assert mech_info.active is True
    assert mech_info.requests_completed == 85
    assert mech_info.requests_failed == 15
    assert mech_info.success_rate == 85.0


@pytest.mark.asyncio
async def test_get_available_mechs(client):
    """Test querying available mechs by capability"""
    mechs = await client.get_available_mechs("price_oracle", min_reputation=70.0)

    assert len(mechs) == 1
    assert mechs[0].service_id == 1
    assert mechs[0].success_rate >= 70.0
    assert mechs[0].active is True


@pytest.mark.asyncio
async def test_get_available_mechs_filters_inactive(client):
    """Test that inactive mechs are filtered out"""
    mechs = await client.get_available_mechs("data_analyst", min_reputation=0.0)

    # Mech 3 is inactive, should be filtered
    assert len(mechs) == 0


@pytest.mark.asyncio
async def test_get_available_mechs_filters_low_reputation(client):
    """Test that low reputation mechs are filtered out"""
    # Mech 3 has 50% success rate
    mechs = await client.get_available_mechs("data_analyst", min_reputation=60.0)

    assert len(mechs) == 0


@pytest.mark.asyncio
async def test_is_mech_active(client):
    """Test checking mech active status"""
    assert await client.is_mech_active(1) is True
    assert await client.is_mech_active(2) is True
    assert await client.is_mech_active(3) is False


@pytest.mark.asyncio
async def test_get_mech_address(client):
    """Test getting mech address by service ID"""
    address = await client.get_mech_address(1)

    assert address == Web3.to_checksum_address("0x0000000000000000000000000000000000000100")


@pytest.mark.asyncio
async def test_get_mech_price(client):
    """Test getting mech price"""
    price = await client.get_mech_price(1)

    assert price == 10000000000000000  # 0.01 ETH in wei


# ═══════════════════════════════════════════════════════════════
# CAPABILITY MAPPING TESTS
# ═══════════════════════════════════════════════════════════════

def test_map_cairn_to_olas_capability():
    """Test CAIRN to Olas capability mapping"""
    assert OlasMechClient.map_cairn_to_olas_capability("defi.price_fetch") == "price_oracle"
    assert OlasMechClient.map_cairn_to_olas_capability("defi.trade_execute") == "trading_bot"
    assert (
        OlasMechClient.map_cairn_to_olas_capability("data.report_generate") == "data_analyst"
    )
    assert OlasMechClient.map_cairn_to_olas_capability("unknown.task") == "general"


# ═══════════════════════════════════════════════════════════════
# MECH INFO TESTS
# ═══════════════════════════════════════════════════════════════

def test_mech_info_success_rate_calculation():
    """Test MechInfo success rate calculation"""
    # 85% success rate
    mech = MechInfo(
        mech_address=Web3.to_checksum_address("0x0000000000000000000000000000000000000100"),
        service_id=1,
        capabilities=[],
        price_per_request=0,
        active=True,
        requests_completed=85,
        requests_failed=15,
    )

    assert mech.success_rate == 85.0


def test_mech_info_success_rate_zero_requests():
    """Test MechInfo success rate when no requests"""
    mech = MechInfo(
        mech_address=Web3.to_checksum_address("0x0000000000000000000000000000000000000100"),
        service_id=1,
        capabilities=[],
        price_per_request=0,
        active=True,
        requests_completed=0,
        requests_failed=0,
    )

    assert mech.success_rate == 0.0


# ═══════════════════════════════════════════════════════════════
# SERVICE REQUEST TESTS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_request_mech_service_placeholder(client):
    """Test request_mech_service placeholder implementation"""
    # This is a placeholder - should return mock tx hash
    tx_hash = await client.request_mech_service(
        mech_id=1,
        task_data=b"test_data",
        from_address=Web3.to_checksum_address("0x0000000000000000000000000000000000001234"),
    )

    assert isinstance(tx_hash, str)
    assert tx_hash.startswith("0x")


@pytest.mark.asyncio
async def test_request_mech_service_raises_for_inactive_mech(client):
    """Test request_mech_service raises error for inactive mech"""
    with pytest.raises(ValueError, match="not active"):
        await client.request_mech_service(
            mech_id=3,  # Inactive mech
            task_data=b"test_data",
            from_address=Web3.to_checksum_address(
                "0x0000000000000000000000000000000000001234"
            ),
        )


# ═══════════════════════════════════════════════════════════════
# ERROR HANDLING TESTS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_available_mechs_handles_load_failure(client):
    """Test that get_available_mechs handles individual mech load failures gracefully"""

    # Mock getMech to raise exception for one mech
    def mock_get_mech_with_error(service_id):
        if service_id == 1:
            raise Exception("Network error")
        return client.registry.functions.getMech(service_id)

    client.registry.functions.getMech = mock_get_mech_with_error

    # Should not raise, just skip the failing mech
    mechs = await client.get_available_mechs("price_oracle")

    # Should handle the error gracefully
    assert isinstance(mechs, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
