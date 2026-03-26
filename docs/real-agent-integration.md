# Real Agent Integration

> Production requirements for autonomous agents integrating with CAIRN Protocol.

---

## Overview

CAIRN is designed for **production autonomous agents**, not just demos. While hackathon demonstrations may use controlled agents for reliability, the protocol architecture assumes fully autonomous agents operating without human intervention.

This document specifies the requirements, patterns, and considerations for real agent integration.

---

## Agent Requirements

### Minimum Capabilities

| Capability | Requirement | Why |
|------------|-------------|-----|
| **Wallet Management** | Agent controls its own EOA | Sign transactions, receive payments |
| **Transaction Sending** | Can send txs to Base (L2) | Heartbeat, checkpoint, settlement |
| **IPFS Write Access** | Can pin JSON to IPFS | Checkpoint storage |
| **Event Listening** | Can subscribe to contract events | Receive task assignments, detect state changes |
| **Background Tasks** | Can run concurrent operations | Heartbeat loop parallel to execution |
| **Graceful Shutdown** | Can handle SIGTERM/SIGINT | Clean exit, final checkpoint |

### Technical Specifications

```yaml
# Minimum agent configuration
agent:
  wallet:
    type: EOA  # Not contract wallet (for gas simplicity)
    funding: 0.01 ETH minimum  # Gas for ~100 transactions

  network:
    chain_id: 8453  # Base mainnet (84532 for Sepolia)
    rpc_url: "https://mainnet.base.org"
    backup_rpc: "https://base.publicnode.com"

  ipfs:
    provider: "pinata"  # or "web3.storage", "infura"
    gateway_fallbacks:
      - "https://gateway.pinata.cloud/ipfs/"
      - "https://ipfs.io/ipfs/"
      - "https://dweb.link/ipfs/"

  heartbeat:
    interval_seconds: 60  # Must match task configuration
    retry_attempts: 3
    priority_fee_gwei: 0.1  # Ensure tx lands

  checkpoint:
    max_size_bytes: 1048576  # 1MB per checkpoint
    compression: true  # gzip before pinning
    schema_validation: true  # Validate before commit
```

---

## Integration Patterns

### Pattern 1: Wrapper Integration (Recommended)

Wrap any existing agent framework with CAIRN capabilities:

```python
from cairn import CairnAgent, CairnClient, CheckpointStore

# Your existing agent (LangChain, Olas, custom, etc.)
my_agent = YourAgentFramework(...)

# CAIRN wrapper adds protocol compliance
cairn_agent = CairnAgent(
    agent=my_agent,
    client=CairnClient(
        rpc_url=os.getenv("RPC_URL"),
        contract_address=os.getenv("CAIRN_CONTRACT"),
        private_key=os.getenv("AGENT_PRIVATE_KEY")
    ),
    ipfs=CheckpointStore(
        pinata_jwt=os.getenv("PINATA_JWT")
    ),
    config={
        "heartbeat_interval": 60,
        "checkpoint_after_each_subtask": True,
        "auto_retry_failed_checkpoints": True
    }
)

# Execute with full CAIRN protection
result = await cairn_agent.execute(task_id, subtasks)
```

**How it works:**
1. `CairnAgent` intercepts subtask completion
2. Automatically commits checkpoint to IPFS + contract
3. Runs heartbeat loop in background
4. Handles graceful failure reporting

### Pattern 2: Native Integration

Build CAIRN compliance directly into agent logic:

```python
class CairnNativeAgent:
    """Agent with built-in CAIRN protocol support."""

    def __init__(self, cairn_client: CairnClient, ipfs: CheckpointStore):
        self.cairn = cairn_client
        self.ipfs = ipfs
        self._heartbeat_task = None
        self._current_task_id = None

    async def accept_task(self, task_id: str) -> bool:
        """Called when assigned as primary or fallback."""
        task = await self.cairn.get_task(task_id)

        # Validate we can handle this task
        if not self._can_execute(task.spec):
            return False

        self._current_task_id = task_id
        return True

    async def execute(self, task_id: str, subtasks: list) -> dict:
        """Execute task with CAIRN protocol compliance."""

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(task_id)
        )

        results = []
        try:
            for i, subtask in enumerate(subtasks):
                # Execute subtask
                result = await self._execute_subtask(subtask)
                results.append(result)

                # Checkpoint after each subtask
                checkpoint_data = {
                    "subtask_index": i,
                    "output": result,
                    "timestamp": int(time.time()),
                    "agent_id": self.cairn.address
                }
                cid = await self.ipfs.write(checkpoint_data)
                await self.cairn.commit_checkpoint(task_id, cid)

            # Complete task
            await self.cairn.complete_task(task_id)
            return {"success": True, "results": results}

        except Exception as e:
            # Report failure (contract will route appropriately)
            await self.cairn.report_failure(task_id, str(e))
            raise
        finally:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()

    async def resume(self, task_id: str, from_checkpoint: int) -> dict:
        """Resume task from checkpoint (fallback role)."""

        # Fetch checkpoint data
        task = await self.cairn.get_task(task_id)
        checkpoints = task.checkpoint_cids

        # Read last checkpoint
        last_output = await self.ipfs.read(checkpoints[-1])

        # Continue from next subtask
        remaining_subtasks = task.spec["subtasks"][from_checkpoint:]
        return await self.execute(task_id, remaining_subtasks)

    async def _heartbeat_loop(self, task_id: str):
        """Emit liveness signals at configured interval."""
        while True:
            try:
                await self.cairn.heartbeat(task_id)
            except Exception as e:
                # Log but don't crash - next iteration will retry
                logger.warning(f"Heartbeat failed: {e}")
            await asyncio.sleep(60)

    async def _execute_subtask(self, subtask: dict) -> dict:
        """Override in subclass with actual execution logic."""
        raise NotImplementedError
```

### Pattern 3: Event-Driven Fallback Agent

Agent that listens for recovery assignments:

```python
class FallbackListenerAgent:
    """Agent that monitors for recovery opportunities."""

    def __init__(self, cairn_client: CairnClient, task_types: list[str]):
        self.cairn = cairn_client
        self.supported_types = task_types
        self._running = False

    async def start_listening(self):
        """Subscribe to FallbackAssigned events."""
        self._running = True

        async for event in self.cairn.subscribe("FallbackAssigned"):
            if not self._running:
                break

            task_id = event["taskId"]
            assigned_to = event["fallbackAgent"]

            # Check if we're the assigned fallback
            if assigned_to.lower() == self.cairn.address.lower():
                await self._handle_assignment(task_id, event)

    async def _handle_assignment(self, task_id: str, event: dict):
        """Handle incoming recovery assignment."""

        task = await self.cairn.get_task(task_id)

        # Verify we can handle this task type
        if task.task_type not in self.supported_types:
            logger.warning(f"Assigned task type {task.task_type} not supported")
            return  # Don't accept - will timeout to DISPUTED

        # Read checkpoints from primary agent
        checkpoint_cids = event["checkpointCIDs"]
        last_checkpoint_index = len(checkpoint_cids) - 1

        # Resume execution
        try:
            await self.resume(task_id, last_checkpoint_index + 1)
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            # Task will route to DISPUTED
```

---

## Fallback Pool Registration

### Registration Process

```python
async def register_as_fallback(
    cairn: CairnClient,
    task_types: list[str],
    stake_amount: int,  # wei
    max_escrow: int     # Maximum escrow value willing to handle
):
    """Register agent in the fallback pool."""

    # 1. Verify reputation meets threshold (PRD-04)
    reputation = await cairn.get_reputation(cairn.address)
    if reputation < 50:
        raise ValueError(f"Reputation {reputation} below threshold 50")

    # 2. Deposit stake
    tx = await cairn.deposit_stake(stake_amount)
    await tx.wait()

    # 3. Register supported task types
    tx = await cairn.register_fallback(
        task_types=task_types,
        max_escrow=max_escrow
    )
    await tx.wait()

    # 4. Start listening for assignments
    await FallbackListenerAgent(cairn, task_types).start_listening()
```

### Stake Requirements

```
min_stake = max_eligible_escrow × 0.1

Example:
- Agent wants to handle tasks up to 1 ETH escrow
- Minimum stake = 0.1 ETH
- If agent accepts and fails with 0 checkpoints → 100% stake slashed
```

---

## Production Considerations

### 1. Gas Management

```python
class GasManager:
    """Ensure agent always has gas for critical operations."""

    MINIMUM_BALANCE = Web3.to_wei(0.005, "ether")  # ~50 transactions
    HEARTBEAT_GAS = 30_000
    CHECKPOINT_GAS = 60_000

    async def check_balance(self, address: str) -> bool:
        balance = await self.web3.eth.get_balance(address)
        return balance >= self.MINIMUM_BALANCE

    async def estimate_remaining_operations(self, address: str) -> int:
        balance = await self.web3.eth.get_balance(address)
        gas_price = await self.web3.eth.gas_price
        return balance // (self.HEARTBEAT_GAS * gas_price)
```

**Auto-refuel pattern:**
```python
if await gas_manager.estimate_remaining_operations(agent.address) < 20:
    # Notify operator or auto-refuel from treasury
    await notify_low_gas(agent.address)
```

### 2. Checkpoint Reliability

```python
class ReliableCheckpointStore:
    """Checkpoint store with retry and fallback logic."""

    GATEWAYS = [
        "https://gateway.pinata.cloud/ipfs/",
        "https://ipfs.io/ipfs/",
        "https://dweb.link/ipfs/",
        "https://cloudflare-ipfs.com/ipfs/"
    ]

    async def write(self, data: dict, retries: int = 3) -> str:
        """Write with automatic retry."""
        last_error = None
        for attempt in range(retries):
            try:
                return await self._pin_to_pinata(data)
            except Exception as e:
                last_error = e
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        raise last_error

    async def read(self, cid: str) -> dict:
        """Read with gateway fallback."""
        for gateway in self.GATEWAYS:
            try:
                return await self._fetch_from_gateway(gateway, cid)
            except Exception:
                continue
        raise IPFSUnavailableError(f"All gateways failed for {cid}")
```

### 3. Heartbeat Resilience

```python
class ResilientHeartbeat:
    """Heartbeat with multiple fallback strategies."""

    async def send_heartbeat(self, task_id: str):
        """Send heartbeat with priority fee boost on retry."""

        for attempt in range(3):
            try:
                # Increase priority fee with each retry
                priority_fee = Web3.to_wei(0.1 * (attempt + 1), "gwei")

                tx = await self.cairn.heartbeat(
                    task_id,
                    max_priority_fee_per_gas=priority_fee
                )
                await tx.wait(timeout=30)
                return True

            except TransactionTimeout:
                logger.warning(f"Heartbeat attempt {attempt + 1} timed out")
                continue

        # All attempts failed - agent should gracefully shut down
        logger.error("Failed to send heartbeat after 3 attempts")
        return False
```

### 4. Graceful Shutdown

```python
import signal

class GracefulAgent:
    """Agent with proper shutdown handling."""

    def __init__(self):
        self._shutdown_requested = False
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        logger.info("Shutdown signal received")
        self._shutdown_requested = True

    async def execute_with_shutdown_check(self, task_id: str, subtasks: list):
        """Execute subtasks with shutdown awareness."""

        for i, subtask in enumerate(subtasks):
            if self._shutdown_requested:
                # Commit final checkpoint before exit
                await self._commit_final_checkpoint(task_id, i)
                logger.info(f"Graceful shutdown at subtask {i}")
                raise GracefulShutdownError()

            result = await self._execute_subtask(subtask)
            await self._commit_checkpoint(task_id, i, result)
```

### 5. Multi-Chain Support (Future)

```python
class MultiChainAgent:
    """Agent supporting multiple CAIRN deployments."""

    DEPLOYMENTS = {
        8453: "0x...",   # Base mainnet
        84532: "0x...",  # Base Sepolia
        42161: "0x...",  # Arbitrum
        10: "0x...",     # Optimism
    }

    def __init__(self, chain_id: int):
        self.chain_id = chain_id
        self.contract_address = self.DEPLOYMENTS[chain_id]
```

---

## Agent Frameworks Compatibility

### Supported Frameworks

| Framework | Integration Method | Notes |
|-----------|-------------------|-------|
| **Olas SDK** | Wrapper | Native sponsor alignment |
| **LangChain** | Wrapper | Most common, easy setup |
| **LangGraph** | Node injection | Add CAIRN nodes to graph |
| **AutoGen** | Wrapper | Multi-agent support |
| **CrewAI** | Wrapper | Task-based agents |
| **Custom Python** | Native | Full control |

### Olas Integration Example

```python
from olas_sdk import MechService
from cairn import CairnAgent

# Olas Mech service
mech = MechService(
    service_id="my_service",
    chain_id=8453
)

# Wrap with CAIRN
cairn_mech = CairnAgent(
    agent=mech,
    client=CairnClient(...),
    ipfs=CheckpointStore(...)
)

# Register in both Olas Mech Marketplace AND CAIRN Fallback Pool
await cairn_mech.register_fallback(
    task_types=["defi.price_fetch"],
    stake=Web3.to_wei(0.1, "ether")
)
```

---

## Testing Real Agents

### Local Testing Setup

```bash
# 1. Start local Anvil node (Base fork)
anvil --fork-url https://mainnet.base.org --port 8545

# 2. Deploy CAIRN contracts locally
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# 3. Start local IPFS node
ipfs daemon

# 4. Run agent tests
pytest tests/integration/test_real_agent.py -v
```

### Integration Test Example

```python
@pytest.mark.integration
async def test_real_agent_recovery_flow():
    """Test full recovery flow with real agent processes."""

    # Start primary agent
    primary = spawn_agent("primary", task_types=["defi.price_fetch"])

    # Start fallback agent
    fallback = spawn_agent("fallback", task_types=["defi.price_fetch"])

    # Submit task
    task_id = await submit_task(
        primary_agent=primary.address,
        fallback_agent=fallback.address,
        escrow=Web3.to_wei(0.1, "ether")
    )

    # Wait for primary to checkpoint
    await wait_for_checkpoints(task_id, count=3, timeout=60)

    # Kill primary (simulate crash)
    primary.terminate()

    # Wait for liveness check to trigger
    await wait_for_state(task_id, "FAILED", timeout=120)

    # Wait for fallback to complete
    await wait_for_state(task_id, "RESOLVED", timeout=120)

    # Verify settlement
    settlement = await get_settlement(task_id)
    assert settlement.primary_share > 0  # Got paid for 3 checkpoints
    assert settlement.fallback_share > 0  # Got paid for remaining work
```

---

## Monitoring & Observability

### Agent Health Metrics

```python
from prometheus_client import Counter, Gauge, Histogram

# Metrics to export
HEARTBEATS_SENT = Counter("cairn_heartbeats_total", "Heartbeats sent")
HEARTBEAT_FAILURES = Counter("cairn_heartbeat_failures_total", "Failed heartbeats")
CHECKPOINTS_COMMITTED = Counter("cairn_checkpoints_total", "Checkpoints committed")
TASK_DURATION = Histogram("cairn_task_duration_seconds", "Task execution time")
ACTIVE_TASKS = Gauge("cairn_active_tasks", "Currently executing tasks")
GAS_BALANCE = Gauge("cairn_gas_balance_wei", "Agent gas balance")
```

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: cairn_agent
    rules:
      - alert: AgentLowGas
        expr: cairn_gas_balance_wei < 5000000000000000  # < 0.005 ETH
        for: 5m
        labels:
          severity: warning

      - alert: HeartbeatFailureSpike
        expr: rate(cairn_heartbeat_failures_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical

      - alert: NoCheckpointsCommitted
        expr: rate(cairn_checkpoints_total[10m]) == 0
        for: 10m
        labels:
          severity: warning
```

---

*See also: [Integration Guide](./integration.md) · [Observer](./observer.md) · [Concepts](./concepts.md)*

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
