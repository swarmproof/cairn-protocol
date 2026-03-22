"""
Olas Mech Marketplace Integration for CAIRN Protocol

This module provides a client for querying and interacting with Olas Mech agents
as fallback options within the CAIRN recovery system.

Based on PRD-04 Section 2.7: Olas Mech Marketplace Integration
"""

from dataclasses import dataclass
from typing import List, Optional
from web3 import Web3
from web3.contract import Contract
from eth_typing import Address, HexStr


# ═══════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class MechInfo:
    """Olas Mech agent information"""
    mech_address: Address
    service_id: int
    capabilities: List[bytes]
    price_per_request: int  # in wei
    active: bool
    requests_completed: int
    requests_failed: int

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.requests_completed + self.requests_failed
        if total == 0:
            return 0.0
        return (self.requests_completed / total) * 100


@dataclass
class MechRequest:
    """Olas Mech service request"""
    mech_address: Address
    service_id: int
    task_data: bytes
    payment: int  # in wei


# ═══════════════════════════════════════════════════════════════
# OLAS MECH CLIENT
# ═══════════════════════════════════════════════════════════════

class OlasMechClient:
    """
    Client for interacting with Olas Mech Marketplace.

    Provides methods to:
    - Query available mechs by capability
    - Get mech information
    - Request mech services
    - Monitor mech performance

    Usage:
        >>> client = OlasMechClient(
        ...     rpc_url="https://gnosis-rpc.publicnode.com",
        ...     registry_address="0x9338b5153AE39BB89f50468E608eD9d764B755fD"
        ... )
        >>> mechs = await client.get_available_mechs("price_oracle")
        >>> mech_info = await client.get_mech_info(mechs[0].service_id)
    """

    # Olas Mech Registry ABI (minimal interface)
    REGISTRY_ABI = [
        {
            "inputs": [{"name": "serviceId", "type": "uint256"}],
            "name": "getMech",
            "outputs": [
                {
                    "components": [
                        {"name": "mechAddress", "type": "address"},
                        {"name": "serviceId", "type": "uint256"},
                        {"name": "capabilities", "type": "bytes32[]"},
                        {"name": "pricePerRequest", "type": "uint256"},
                        {"name": "active", "type": "bool"},
                        {"name": "requestsCompleted", "type": "uint256"},
                        {"name": "requestsFailed", "type": "uint256"},
                    ],
                    "name": "",
                    "type": "tuple",
                }
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "capability", "type": "bytes32"}],
            "name": "getMechsByCapability",
            "outputs": [{"name": "serviceIds", "type": "uint256[]"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "serviceId", "type": "uint256"}],
            "name": "isMechActive",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "serviceId", "type": "uint256"}],
            "name": "getMechAddress",
            "outputs": [{"name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "serviceId", "type": "uint256"}],
            "name": "getMechPrice",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    def __init__(self, rpc_url: str, registry_address: str):
        """
        Initialize Olas Mech client.

        Args:
            rpc_url: RPC endpoint for the chain (e.g., Gnosis Chain)
            registry_address: Olas Mech Registry contract address
        """
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.web3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")

        self.registry_address = Web3.to_checksum_address(registry_address)
        self.registry: Contract = self.web3.eth.contract(
            address=self.registry_address, abi=self.REGISTRY_ABI
        )

    # ═══════════════════════════════════════════════════════════════
    # QUERY METHODS
    # ═══════════════════════════════════════════════════════════════

    async def get_available_mechs(
        self, capability: str, min_reputation: float = 70.0
    ) -> List[MechInfo]:
        """
        Get all available mechs for a specific capability.

        Args:
            capability: Capability identifier (e.g., "price_oracle")
            min_reputation: Minimum success rate percentage (default: 70%)

        Returns:
            List of MechInfo objects meeting criteria
        """
        # Convert capability string to bytes32
        capability_hash = Web3.keccak(text=capability)

        # Query registry for service IDs
        service_ids = self.registry.functions.getMechsByCapability(
            capability_hash
        ).call()

        # Fetch detailed info for each mech
        mechs = []
        for service_id in service_ids:
            try:
                mech_info = await self.get_mech_info(service_id)

                # Filter by reputation
                if mech_info.success_rate >= min_reputation and mech_info.active:
                    mechs.append(mech_info)
            except Exception as e:
                # Skip mechs that fail to load
                print(f"Warning: Failed to load mech {service_id}: {e}")
                continue

        return mechs

    async def get_mech_info(self, service_id: int) -> MechInfo:
        """
        Get detailed information about a specific mech.

        Args:
            service_id: Olas service ID

        Returns:
            MechInfo object with mech details
        """
        # Call registry contract
        mech_data = self.registry.functions.getMech(service_id).call()

        return MechInfo(
            mech_address=Web3.to_checksum_address(mech_data[0]),
            service_id=mech_data[1],
            capabilities=mech_data[2],
            price_per_request=mech_data[3],
            active=mech_data[4],
            requests_completed=mech_data[5],
            requests_failed=mech_data[6],
        )

    async def is_mech_active(self, service_id: int) -> bool:
        """
        Check if a mech is currently active.

        Args:
            service_id: Olas service ID

        Returns:
            True if mech is active, False otherwise
        """
        return self.registry.functions.isMechActive(service_id).call()

    async def get_mech_address(self, service_id: int) -> Address:
        """
        Get mech contract address by service ID.

        Args:
            service_id: Olas service ID

        Returns:
            Mech contract address
        """
        address = self.registry.functions.getMechAddress(service_id).call()
        return Web3.to_checksum_address(address)

    async def get_mech_price(self, service_id: int) -> int:
        """
        Get price per request for a mech.

        Args:
            service_id: Olas service ID

        Returns:
            Price in wei
        """
        return self.registry.functions.getMechPrice(service_id).call()

    # ═══════════════════════════════════════════════════════════════
    # SERVICE REQUEST METHODS
    # ═══════════════════════════════════════════════════════════════

    async def request_mech_service(
        self,
        mech_id: int,
        task_data: bytes,
        from_address: Address,
        private_key: Optional[str] = None,
    ) -> HexStr:
        """
        Request a service from an Olas Mech.

        Note: In production, this would interact with the Mech's contract
        directly to submit a request. This is a placeholder implementation.

        Args:
            mech_id: Olas service ID
            task_data: Encoded task data for the mech
            from_address: Sender address
            private_key: Private key for signing (optional)

        Returns:
            Transaction hash

        Raises:
            ValueError: If mech is not active or price not met
        """
        # Verify mech is active
        if not await self.is_mech_active(mech_id):
            raise ValueError(f"Mech {mech_id} is not active")

        # Get mech info
        mech_info = await self.get_mech_info(mech_id)

        # In production, this would:
        # 1. Build transaction to mech contract
        # 2. Include payment (mech_info.price_per_request)
        # 3. Submit task_data
        # 4. Return transaction hash

        # Placeholder implementation
        print(
            f"[PLACEHOLDER] Would request service from mech {mech_id} "
            f"at {mech_info.mech_address} with payment {mech_info.price_per_request} wei"
        )

        # Return mock transaction hash
        return HexStr("0x" + "0" * 64)

    # ═══════════════════════════════════════════════════════════════
    # CAPABILITY MAPPING
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def map_cairn_to_olas_capability(cairn_task_type: str) -> str:
        """
        Map CAIRN task type to Olas capability.

        Based on PRD-04 Section 2.7 default mappings.

        Args:
            cairn_task_type: CAIRN task type (e.g., "defi.price_fetch")

        Returns:
            Olas capability identifier
        """
        mapping = {
            # DeFi
            "defi.price_fetch": "price_oracle",
            "defi.trade_execute": "trading_bot",
            "defi.liquidity_provide": "liquidity_manager",
            # Data
            "data.report_generate": "data_analyst",
            "data.scrape_website": "web_scraper",
            # Governance
            "governance.vote_delegate": "governance_agent",
            # Compute
            "compute.model_inference": "ai_inference",
        }

        return mapping.get(cairn_task_type, "general")

    # ═══════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════

    def get_connection_info(self) -> dict:
        """Get connection information."""
        return {
            "connected": self.web3.is_connected(),
            "chain_id": self.web3.eth.chain_id if self.web3.is_connected() else None,
            "registry_address": self.registry_address,
            "block_number": (
                self.web3.eth.block_number if self.web3.is_connected() else None
            ),
        }


# ═══════════════════════════════════════════════════════════════
# EXAMPLE USAGE
# ═══════════════════════════════════════════════════════════════

async def example_usage():
    """Example usage of OlasMechClient."""

    # Initialize client for Gnosis Chain
    client = OlasMechClient(
        rpc_url="https://gnosis-rpc.publicnode.com",
        registry_address="0x9338b5153AE39BB89f50468E608eD9d764B755fD",
    )

    # Check connection
    print("Connection info:", client.get_connection_info())

    # Query available price oracle mechs
    price_mechs = await client.get_available_mechs("price_oracle", min_reputation=70.0)

    print(f"\nFound {len(price_mechs)} price oracle mechs:")
    for mech in price_mechs:
        print(f"  - Service ID {mech.service_id}")
        print(f"    Address: {mech.mech_address}")
        print(f"    Success Rate: {mech.success_rate:.1f}%")
        print(f"    Price: {mech.price_per_request} wei")

    # Get specific mech info
    if price_mechs:
        mech = price_mechs[0]
        is_active = await client.is_mech_active(mech.service_id)
        print(f"\nMech {mech.service_id} is active: {is_active}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
