# CAIRN CLI

Command-line interface for interacting with CAIRN Protocol - an Agent Failure and Recovery Protocol.

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/cairn-protocol/cairn.git
cd cairn

# Install in development mode
pip install -e .

# Verify installation
cairn --help
```

### Production Install

```bash
pip install cairn-protocol
```

## Configuration

Set environment variables in `contracts/.env`:

```bash
# Required
CAIRN_CONTRACT_ADDRESS=0x...

# Optional (defaults shown)
RPC_URL=https://sepolia.base.org

# Required for write operations
PRIVATE_KEY=0x...

# Required for checkpoint operations
PINATA_JWT=...

# Required for intelligence features (future)
BONFIRES_API_KEY=...
```

## Usage

### Task Management

#### Submit a Task

```bash
cairn task submit \
  --primary-agent 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0 \
  --fallback-agent 0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199 \
  --task-cid QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG \
  --escrow 0.1 \
  --heartbeat-interval 60 \
  --deadline 1735689600
```

#### Check Task Status

```bash
cairn task status 0xabc123...
```

Example output:

```
╭─── Task Status ───────────────────────────────────────╮
│ Task ID: 0xabc123...                                  │
│ State: RUNNING                                        │
│ Operator: 0x123...                                    │
│ Primary Agent: 0x742...                               │
│ Fallback Agent: 0x862...                              │
│ Escrow: 0.100000 ETH                                  │
│ Heartbeat Interval: 60s                               │
│ Deadline: 2024-12-31 12:00:00                         │
│ Last Heartbeat: 2024-12-30 10:30:00                   │
│ Primary Checkpoints: 3                                │
│ Fallback Checkpoints: 0                               │
│ Total Checkpoints: 3                                  │
│ Task CID: QmYwAP...                                   │
╰───────────────────────────────────────────────────────╯

Checkpoints:
┏━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ # ┃ CID          ┃ IPFS URL                         ┃
┡━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1 │ QmXYZ...abc  │ https://gateway.pinata.cloud/... │
│ 2 │ QmABC...xyz  │ https://gateway.pinata.cloud/... │
│ 3 │ QmDEF...123  │ https://gateway.pinata.cloud/... │
└───┴──────────────┴──────────────────────────────────┘
```

#### Send Heartbeat

```bash
cairn task heartbeat 0xabc123...
```

#### Commit Checkpoint

```bash
cairn task checkpoint 0xabc123... --cid QmCheckpointHash...
```

#### Fail Task (Liveness Check)

```bash
cairn task fail 0xabc123...
```

#### Recover Failed Task

```bash
cairn task recover 0xabc123...
```

#### Settle Task

```bash
cairn task settle 0xabc123...
```

Example output:

```
╭─── ✓ Task Settled ────────────────────────────────────╮
│ Task ID: 0xabc123...                                  │
│ Primary Agent: 0x742...                               │
│ Fallback Agent: 0x862...                              │
│ Primary Share: 0.095000 ETH                           │
│ Fallback Share: 0.000000 ETH                          │
│ Protocol Fee: 0.005000 ETH                            │
│ Primary Checkpoints: 5                                │
│ Fallback Checkpoints: 0                               │
│ Total Escrow: 0.100000 ETH                            │
╰───────────────────────────────────────────────────────╯
```

### Agent Management (Future Features)

```bash
# Register as agent (PRD-05)
cairn agent register --stake 1.0 --types "code,test,deploy"

# Check agent status (PRD-05)
cairn agent status 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0

# Withdraw stake (PRD-05)
cairn agent withdraw
```

### Pool Management (Future Features)

```bash
# List fallback pools (PRD-04)
cairn pool list --type code

# Show pool statistics (PRD-04)
cairn pool stats
```

### Intelligence Queries (Future Features)

```bash
# Query execution patterns (PRD-03)
cairn intel query code-generation

# List execution patterns (PRD-03)
cairn intel patterns --type deployment

# Get agent history (PRD-03)
cairn intel agent-history 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
```

### Protocol Administration

```bash
# View protocol information
cairn admin info

# Pause protocol (PRD-02 - future)
cairn admin pause

# Unpause protocol (PRD-02 - future)
cairn admin unpause

# Set protocol parameter (PRD-02 - future)
cairn admin set-param protocol_fee 500
```

## Features

### Current (MVP)

- ✅ Task submission and management
- ✅ Heartbeat monitoring
- ✅ Checkpoint commitment
- ✅ Task failure and recovery
- ✅ Settlement and escrow distribution
- ✅ Protocol information display
- ✅ Rich formatted output with colors and tables
- ✅ Progress indicators for transactions
- ✅ Comprehensive error handling

### Coming Soon

- 🔜 Agent registration and staking (PRD-05)
- 🔜 Fallback pool management (PRD-04)
- 🔜 Execution intelligence queries (PRD-03)
- 🔜 Protocol governance commands (PRD-02)
- 🔜 Task listing and filtering via events/subgraph
- 🔜 WebSocket event subscriptions
- 🔜 Batch operations

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=cli --cov-report=html
```

### Code Quality

```bash
# Format code
black cli/ sdk/

# Lint code
ruff check cli/ sdk/

# Type checking
mypy cli/ sdk/
```

## Examples

### Complete Task Lifecycle

```bash
# 1. Submit task
TASK_ID=$(cairn task submit \
  --primary-agent 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0 \
  --fallback-agent 0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199 \
  --task-cid QmTaskSpec... \
  --escrow 0.1 | grep "Task ID" | cut -d: -f2 | tr -d ' ')

# 2. Monitor status
cairn task status $TASK_ID

# 3. Send heartbeats (agent)
cairn task heartbeat $TASK_ID

# 4. Commit checkpoints (agent)
cairn task checkpoint $TASK_ID --cid QmCheckpoint1...
cairn task checkpoint $TASK_ID --cid QmCheckpoint2...

# 5. Settle task (operator)
cairn task settle $TASK_ID
```

### Error Handling

The CLI provides clear error messages and suggestions:

```bash
$ cairn task submit --primary-agent 0xInvalid...
✗ Configuration Error: Invalid address format
ℹ Details: Address must be a valid Ethereum address (0x...)
```

### JSON Output

For programmatic usage, pipe to `jq`:

```bash
cairn task status $TASK_ID --json | jq '.escrow'
```

## Troubleshooting

### Connection Issues

```bash
# Check network connection
curl -X POST $RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'

# Verify contract address
cairn admin info
```

### Transaction Failures

```bash
# Check balance
cast balance $YOUR_ADDRESS --rpc-url $RPC_URL

# Estimate gas
cast estimate --rpc-url $RPC_URL \
  --to $CAIRN_CONTRACT_ADDRESS \
  --value 0.1ether \
  --sig "submitTask(address,address,string,uint256,uint256)" \
  $PRIMARY $FALLBACK "QmCID" 60 $DEADLINE
```

### Environment Variables

```bash
# List all required variables
env | grep -E "(CAIRN|RPC|PRIVATE|PINATA)"

# Reload environment
source contracts/.env
cairn admin info
```

## Security

- **Private Keys**: Never commit `.env` files or expose private keys
- **RPC URLs**: Use secure, authenticated RPC endpoints for production
- **Pinata JWT**: Keep your Pinata JWT secret and rotate regularly
- **Permissions**: The CLI requires write access only for state-changing operations

## Support

- Documentation: https://docs.cairnprotocol.com
- Issues: https://github.com/cairn-protocol/cairn/issues
- Discord: https://discord.gg/cairn-protocol

## License

MIT License - see LICENSE file for details
