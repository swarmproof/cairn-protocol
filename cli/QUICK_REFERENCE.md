# CAIRN CLI - Quick Reference

## Installation

```bash
pip install -e .
cairn --version
```

## Configuration

Create `contracts/.env`:
```bash
CAIRN_CONTRACT_ADDRESS=0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417
RPC_URL=https://sepolia.base.org
PRIVATE_KEY=0x...      # For write operations
PINATA_JWT=...         # For checkpoints
```

## Commands

### Task Commands

```bash
# Submit task
cairn task submit \
  --primary-agent 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0 \
  --fallback-agent 0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199 \
  --task-cid QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG \
  --escrow 0.1 \
  [--heartbeat-interval 60] \
  [--deadline <timestamp>]

# Check status
cairn task status <task_id>

# Send heartbeat
cairn task heartbeat <task_id>

# Commit checkpoint
cairn task checkpoint <task_id> --cid <checkpoint_cid>

# Fail task (liveness check)
cairn task fail <task_id>

# Recover failed task
cairn task recover <task_id>

# Settle task
cairn task settle <task_id>
```

### Admin Commands

```bash
# View protocol info
cairn admin info
```

### Future Commands (Placeholders)

```bash
# Agent (PRD-05)
cairn agent register --stake 1.0 --types "code,test"
cairn agent status <address>
cairn agent withdraw

# Pool (PRD-04)
cairn pool list [--type <type>]
cairn pool stats

# Intel (PRD-03)
cairn intel query <task_type>
cairn intel patterns [--type <type>]
cairn intel agent-history <address>
```

## Common Workflows

### Complete Task Lifecycle

```bash
# 1. Submit
TASK_ID=$(cairn task submit ... | grep "Task ID" | awk '{print $3}')

# 2. Monitor
watch -n 10 "cairn task status $TASK_ID"

# 3. Heartbeat (agent loop)
while true; do
  cairn task heartbeat $TASK_ID
  sleep 60
done

# 4. Checkpoint (after subtask)
cairn task checkpoint $TASK_ID --cid QmCheckpoint1...

# 5. Settle (when complete)
cairn task settle $TASK_ID
```

### Recovery Workflow

```bash
# 1. Fail task (if no heartbeat)
cairn task fail $TASK_ID

# 2. Initiate recovery
cairn task recover $TASK_ID

# 3. Fallback agent takes over
cairn task heartbeat $TASK_ID  # From fallback agent
cairn task checkpoint $TASK_ID --cid QmFallback...

# 4. Settle recovered task
cairn task settle $TASK_ID
```

## Output Examples

### Task Status
```
╭─── Task Status ───────────────────────────────────────╮
│ Task ID: 0xabc...                                     │
│ State: RUNNING                                        │
│ Escrow: 0.100000 ETH                                  │
│ Primary Checkpoints: 3                                │
│ Fallback Checkpoints: 0                               │
╰───────────────────────────────────────────────────────╯
```

### Settlement
```
╭─── ✓ Task Settled ────────────────────────────────────╮
│ Primary Share: 0.095000 ETH                           │
│ Protocol Fee: 0.005000 ETH                            │
╰───────────────────────────────────────────────────────╯
```

## Error Handling

```bash
# Missing config
✗ Configuration Error: CAIRN_CONTRACT_ADDRESS required

# Task not found
✗ CAIRN Error: Task not found: 0xabc...

# Network error
✗ Network Error: Failed to connect to RPC
```

## Tips

1. **Check connection**: `cairn admin info`
2. **Get help**: `cairn <command> --help`
3. **JSON output**: Pipe to `jq` for scripting
4. **Verbose errors**: Set `PYTHONVERBOSE=1`
5. **Test mode**: Use Base Sepolia testnet

## Links

- **Documentation**: `cli/README.md`
- **Installation**: `INSTALLATION.md`
- **Examples**: `examples/cli_usage.sh`
- **BaseScan**: https://sepolia.basescan.org
- **Faucet**: https://www.coinbase.com/faucets/base-ethereum-sepolia-faucet
