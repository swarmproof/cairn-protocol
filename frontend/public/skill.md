# CAIRN Protocol Skill

> Integrate failure recovery into your agent in 5 minutes.

## Install

```bash
# Not yet on PyPI — install the alpha SDK from source:
pip install "git+https://github.com/swarmproof/cairn-protocol.git#subdirectory=sdk"
```

## Environment

```bash
export CAIRN_RPC_URL="https://sepolia.base.org"
export CAIRN_CONTRACT="0x9917E509742495EbEedfF6335406096B2e1aFB3a"
export AGENT_PRIVATE_KEY="0x..."
export PINATA_JWT="eyJ..."
```

## Integrate

```python
from cairn import CairnAgent, CheckpointStore

agent = CairnAgent(
    rpc_url=os.environ["CAIRN_RPC_URL"],
    contract_address=os.environ["CAIRN_CONTRACT"],
    private_key=os.environ["AGENT_PRIVATE_KEY"],
    checkpoint_store=CheckpointStore(pinata_jwt=os.environ["PINATA_JWT"])
)

# Wrap your task execution
async with agent.start_task(task_id, auto_heartbeat=True) as ctx:
    result = await your_existing_function()
    await ctx.checkpoint({"result": result})
    await ctx.complete(result)
```

## What You Get

- **Heartbeats:** Automatic liveness signals (no code changes needed)
- **Checkpoints:** Save progress to IPFS (resumable if you fail)
- **Fair Settlement:** Get paid for work done, even on failure
- **Shared Intelligence:** Your failures help other agents avoid the same mistakes

## Full Documentation

```bash
curl -s https://cairn-protocol.vercel.app/cairn.md
```

---

*Every failure leaves a cairn. Every agent reads it.*
