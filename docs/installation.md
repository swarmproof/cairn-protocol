# CAIRN Protocol - Installation Guide

Complete installation guide for the CAIRN Protocol SDK and CLI.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git
- Access to Base Sepolia RPC endpoint

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/cairn-protocol/cairn.git
cd cairn
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3. Install CAIRN

```bash
# Install in development mode (includes SDK + CLI)
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### 4. Verify Installation

```bash
# Check CLI is installed
cairn --version
# Expected output: cairn, version 0.1.0

# Check help
cairn --help
```

### 5. Configure Environment

Create `contracts/.env` file:

```bash
# Required
CAIRN_CONTRACT_ADDRESS=0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417

# Optional (defaults to Base Sepolia)
RPC_URL=https://sepolia.base.org

# Required for write operations (submitting tasks, heartbeats, etc.)
PRIVATE_KEY=0x...

# Required for checkpoint operations
PINATA_JWT=...
```

**Security Note**: Never commit `.env` files to version control!

### 6. Test Installation

```bash
# View protocol info (read-only, no private key needed)
cairn admin info

# Expected output:
# ╭─── CAIRN Protocol Information ───╮
# │ Contract Address: 0x2eF...       │
# │ Chain ID: 84532                  │
# │ ...                              │
# ╰──────────────────────────────────╯
```

## Development Setup

### Install Development Tools

```bash
# Install with all dev dependencies
pip install -e ".[dev]"

# Verify dev tools
black --version
ruff --version
pytest --version
mypy --version
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sdk --cov=cli --cov-report=html

# Run specific test file
pytest tests/test_cli_config.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Type checking
mypy sdk/ cli/
```

## SDK Usage

### Python SDK

```python
import asyncio
from sdk import CairnClient

async def main():
    client = CairnClient(
        rpc_url="https://sepolia.base.org",
        contract_address="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417",
        private_key="0x...",  # Optional for read operations
    )

    # Check connection
    connected = await client.is_connected()
    print(f"Connected: {connected}")

    # Get protocol info
    fee = await client.get_protocol_fee()
    print(f"Protocol fee: {fee} basis points")

asyncio.run(main())
```

### CLI Usage

See `cli/README.md` for comprehensive CLI documentation.

```bash
# Submit task
cairn task submit \
  --primary-agent 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0 \
  --fallback-agent 0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199 \
  --task-cid QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG \
  --escrow 0.1

# Check task status
cairn task status 0xabc123...

# View all commands
cairn --help
```

## Troubleshooting

### ImportError: No module named 'sdk'

**Solution**: Install the package in development mode:
```bash
pip install -e .
```

### Command 'cairn' not found

**Solution**: Ensure package is installed and virtual environment is activated:
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall
pip install -e .

# Verify
which cairn
```

### Connection errors

**Solution**: Check RPC URL and network connectivity:
```bash
# Test RPC endpoint
curl -X POST https://sepolia.base.org \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'

# Verify contract address
cairn admin info
```

### Transaction failures

**Solution**: Check account balance and gas:
```bash
# Check balance (requires cast from Foundry)
cast balance $YOUR_ADDRESS --rpc-url https://sepolia.base.org

# Get Base Sepolia testnet ETH
# Visit: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet
```

### PRIVATE_KEY errors

**Solution**: Verify environment variable is set correctly:
```bash
# Check if variable is set
echo $PRIVATE_KEY

# Or check .env file
cat contracts/.env | grep PRIVATE_KEY

# Reload environment
source contracts/.env
```

## Updating

### Update from Git

```bash
# Pull latest changes
git pull origin main

# Reinstall dependencies
pip install -e ".[dev]"

# Run tests to verify
pytest
```

### Update Dependencies

```bash
# Update all dependencies
pip install --upgrade -e ".[dev]"

# Or update specific package
pip install --upgrade web3
```

## Uninstallation

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv

# Or uninstall package only
pip uninstall cairn-protocol
```

## Production Deployment

### Install from PyPI (when published)

```bash
pip install cairn-protocol
```

### Docker Deployment (Future)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir cairn-protocol

CMD ["cairn", "admin", "info"]
```

## Getting Help

- **Documentation**: https://docs.cairnprotocol.com
- **Issues**: https://github.com/cairn-protocol/cairn/issues
- **Discord**: https://discord.gg/cairn-protocol

## Next Steps

1. Read `cli/README.md` for CLI usage guide
2. Review `examples/cli_usage.sh` for common workflows
3. Check `sdk/` directory for SDK documentation
4. Join our Discord for support

## License

MIT License - see LICENSE file for details
