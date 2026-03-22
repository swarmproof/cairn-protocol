"""
Tests for CLI Configuration
"""

import os
import pytest
from pathlib import Path
from cli.config import Config


def test_config_from_env(monkeypatch):
    """Test configuration loading from environment variables."""
    monkeypatch.setenv("CAIRN_CONTRACT_ADDRESS", "0x1234567890123456789012345678901234567890")
    monkeypatch.setenv("RPC_URL", "https://base-sepolia.example.com")
    monkeypatch.setenv("PRIVATE_KEY", "0xabcdef1234567890")
    monkeypatch.setenv("PINATA_JWT", "test_jwt_token")

    config = Config.from_env()

    assert config.contract_address == "0x1234567890123456789012345678901234567890"
    assert config.rpc_url == "https://base-sepolia.example.com"
    assert config.private_key == "0xabcdef1234567890"
    assert config.pinata_jwt == "test_jwt_token"
    assert config.chain_id == 84532  # Base Sepolia


def test_config_missing_contract_address(monkeypatch, tmp_path):
    """Test that missing contract address raises error."""
    # Clear all relevant env vars to ensure clean state
    for key in ["CAIRN_CONTRACT_ADDRESS", "RPC_URL", "PRIVATE_KEY", "PINATA_JWT"]:
        monkeypatch.delenv(key, raising=False)

    # Use non-existent env file to prevent loading from actual .env
    fake_env = tmp_path / ".env"

    with pytest.raises(ValueError, match="CAIRN_CONTRACT_ADDRESS"):
        Config.from_env(env_file=fake_env)


def test_config_defaults(monkeypatch):
    """Test default values when optional vars not set."""
    monkeypatch.setenv("CAIRN_CONTRACT_ADDRESS", "0x1234567890123456789012345678901234567890")
    monkeypatch.delenv("RPC_URL", raising=False)
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.delenv("PINATA_JWT", raising=False)

    config = Config.from_env()

    assert config.rpc_url == "https://sepolia.base.org"
    assert config.private_key is None
    assert config.pinata_jwt is None


def test_config_validate_write_operations(monkeypatch):
    """Test validation for write operations."""
    monkeypatch.setenv("CAIRN_CONTRACT_ADDRESS", "0x1234567890123456789012345678901234567890")
    monkeypatch.delenv("PRIVATE_KEY", raising=False)

    config = Config.from_env()

    with pytest.raises(ValueError, match="PRIVATE_KEY"):
        config.validate_write_operations()


def test_config_validate_write_operations_success(monkeypatch):
    """Test successful validation for write operations."""
    monkeypatch.setenv("CAIRN_CONTRACT_ADDRESS", "0x1234567890123456789012345678901234567890")
    monkeypatch.setenv("PRIVATE_KEY", "0xabc123")

    config = Config.from_env()
    config.validate_write_operations()  # Should not raise


def test_config_validate_checkpoint_operations(monkeypatch):
    """Test validation for checkpoint operations."""
    monkeypatch.setenv("CAIRN_CONTRACT_ADDRESS", "0x1234567890123456789012345678901234567890")
    monkeypatch.delenv("PINATA_JWT", raising=False)

    config = Config.from_env()

    with pytest.raises(ValueError, match="PINATA_JWT"):
        config.validate_checkpoint_operations()


def test_config_validate_checkpoint_operations_success(monkeypatch):
    """Test successful validation for checkpoint operations."""
    monkeypatch.setenv("CAIRN_CONTRACT_ADDRESS", "0x1234567890123456789012345678901234567890")
    monkeypatch.setenv("PINATA_JWT", "test_jwt")

    config = Config.from_env()
    config.validate_checkpoint_operations()  # Should not raise


def test_config_chain_id_detection(monkeypatch):
    """Test chain ID detection from RPC URL."""
    monkeypatch.setenv("CAIRN_CONTRACT_ADDRESS", "0x1234567890123456789012345678901234567890")

    # Test Base Mainnet
    monkeypatch.setenv("RPC_URL", "https://mainnet.base.org")
    config = Config.from_env()
    assert config.chain_id == 8453

    # Test Base Sepolia (default)
    monkeypatch.setenv("RPC_URL", "https://sepolia.base.org")
    config = Config.from_env()
    assert config.chain_id == 84532

    # Test other network (defaults to Sepolia)
    monkeypatch.setenv("RPC_URL", "https://custom.rpc.com")
    config = Config.from_env()
    assert config.chain_id == 84532
