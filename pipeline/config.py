"""
Pipeline Configuration

Loads environment variables for Bonfires integration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for Bonfires pipeline."""

    # Bonfires API
    bonfires_api_key: str
    bonfires_api_url: str = "https://tnt-v2.api.bonfires.ai"
    bonfires_bonfire_id: str = "cairn-protocol"

    # RPC Configuration
    rpc_url: str = "https://sepolia.base.org"
    contract_address: str = ""

    # IPFS Configuration
    pinata_jwt: str = ""

    # Event Listener
    start_block: int = 0
    poll_interval: int = 5  # seconds

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """
        Load configuration from environment variables.

        Returns:
            PipelineConfig instance

        Raises:
            ValueError: If required variables are missing
        """
        bonfires_api_key = os.getenv("BONFIRES_API_KEY")
        if not bonfires_api_key:
            raise ValueError("BONFIRES_API_KEY environment variable is required")

        contract_address = os.getenv("CAIRN_CONTRACT_ADDRESS", "")
        if not contract_address:
            raise ValueError("CAIRN_CONTRACT_ADDRESS environment variable is required")

        pinata_jwt = os.getenv("PINATA_JWT", "")
        if not pinata_jwt:
            raise ValueError("PINATA_JWT environment variable is required")

        return cls(
            bonfires_api_key=bonfires_api_key,
            bonfires_api_url=os.getenv("BONFIRES_API_URL", "https://tnt-v2.api.bonfires.ai"),
            bonfires_bonfire_id=os.getenv("BONFIRES_BONFIRE_ID", "cairn-protocol"),
            rpc_url=os.getenv("RPC_URL", "https://sepolia.base.org"),
            contract_address=contract_address,
            pinata_jwt=pinata_jwt,
            start_block=int(os.getenv("START_BLOCK", "0")),
            poll_interval=int(os.getenv("POLL_INTERVAL", "5")),
        )

    def validate(self) -> None:
        """
        Validate configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.bonfires_api_key:
            raise ValueError("bonfires_api_key is required")
        if not self.contract_address:
            raise ValueError("contract_address is required")
        if not self.pinata_jwt:
            raise ValueError("pinata_jwt is required")
        if self.poll_interval < 1:
            raise ValueError("poll_interval must be >= 1")
