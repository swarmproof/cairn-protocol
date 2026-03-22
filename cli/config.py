"""
CLI Configuration Management

Loads configuration from environment variables and provides
validation and defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """CAIRN CLI configuration."""

    rpc_url: str
    contract_address: str
    private_key: Optional[str]
    pinata_jwt: Optional[str]
    bonfires_api_key: Optional[str]
    chain_id: int

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> "Config":
        """
        Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file

        Returns:
            Config instance

        Raises:
            ValueError: If required config is missing
        """
        # Load .env if provided or default location exists
        if env_file:
            load_dotenv(env_file)
        else:
            # Try loading from contracts/.env by default
            default_env = Path.cwd() / "contracts" / ".env"
            if default_env.exists():
                load_dotenv(default_env)

        # Required fields
        rpc_url = os.getenv("RPC_URL", "https://sepolia.base.org")
        contract_address = os.getenv("CAIRN_CONTRACT_ADDRESS")

        if not contract_address:
            raise ValueError(
                "CAIRN_CONTRACT_ADDRESS environment variable required. "
                "Set it in contracts/.env or export it."
            )

        # Optional fields
        private_key = os.getenv("PRIVATE_KEY")
        pinata_jwt = os.getenv("PINATA_JWT")
        bonfires_api_key = os.getenv("BONFIRES_API_KEY")

        # Derive chain ID from RPC URL
        chain_id = 84532  # Base Sepolia default
        if "mainnet" in rpc_url.lower():
            chain_id = 8453  # Base Mainnet

        return cls(
            rpc_url=rpc_url,
            contract_address=contract_address,
            private_key=private_key,
            pinata_jwt=pinata_jwt,
            bonfires_api_key=bonfires_api_key,
            chain_id=chain_id,
        )

    def validate_write_operations(self) -> None:
        """
        Validate config for write operations.

        Raises:
            ValueError: If private key is missing
        """
        if not self.private_key:
            raise ValueError(
                "PRIVATE_KEY environment variable required for write operations. "
                "Export it or add to contracts/.env"
            )

    def validate_checkpoint_operations(self) -> None:
        """
        Validate config for checkpoint operations.

        Raises:
            ValueError: If Pinata JWT is missing
        """
        if not self.pinata_jwt:
            raise ValueError(
                "PINATA_JWT environment variable required for checkpoint operations. "
                "Get one from https://pinata.cloud and export it."
            )
