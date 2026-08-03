# Spawn Prompt: SDK-Dev

> CAIRN MVP Python SDK Development

## CONTEXT

You are implementing the Python SDK for CAIRN protocol MVP, enabling agents to integrate with the protocol.

**PRD Location**: `/PRDs/PRD-01-MVP-HACKATHON.md`
**Target Repo**: `cairn-protocol`
**Your Tasks**: 9-14 (SDK Development phase)
**Depends On**: Contract deployed (Task 8)

**Read First** (understand existing patterns):
- PRD Section 5.2 (Python SDK Interface)
- PRD Section 2.2 (Checkpoint Protocol flow)
- `docs/integration.md` — Quick start patterns, error handling, best practices
- `docs/observer.md` — Observer component specification
- web3.py documentation: https://web3py.readthedocs.io/
- Pinata API docs: https://docs.pinata.cloud/

## SCOPE

**Directory Structure to Create**:
```
cairn-protocol/
├── sdk/
│   ├── __init__.py
│   ├── client.py          # CairnClient class
│   ├── agent.py           # CairnAgent wrapper
│   ├── checkpoint.py      # CheckpointStore (IPFS)
│   ├── observer.py        # CairnObserver base + implementations
│   ├── types.py           # Data classes
│   └── exceptions.py      # Custom exceptions
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_agent.py
│   ├── test_checkpoint.py
│   └── test_observer.py
├── pyproject.toml         # Package config
├── requirements.txt       # Dependencies
└── README.md              # SDK documentation
```

## YOUR TASKS

### Task 9: Setup Python Package
**Files**: `pyproject.toml`, `requirements.txt`, `sdk/__init__.py`
**Acceptance**:
- [ ] Package installable via `pip install -e .`
- [ ] Dependencies: web3, requests, pydantic
- [ ] Python 3.11+ required
- [ ] Exports: `CairnClient`, `CairnAgent`, `CheckpointStore`, `CairnObserver`, `Task`

### Task 10: Implement CheckpointStore
**Files**: `sdk/checkpoint.py`
**Acceptance**:
- [ ] `write(data: dict) -> str` pins JSON to Pinata, returns CID
- [ ] `read(cid: str) -> dict` fetches from IPFS gateway
- [ ] Retry logic: 3 attempts with exponential backoff
- [ ] Gateway fallback: pinata → ipfs.io → dweb.link
- [ ] Timeout: 10 seconds per request

**Interface**:
```python
class CheckpointStore:
    def __init__(self, pinata_jwt: str):
        ...

    async def write(self, data: dict) -> str:
        """Write checkpoint, return CID."""

    async def read(self, cid: str) -> dict:
        """Read checkpoint data."""
```

### Task 11: Implement CairnClient
**Files**: `sdk/client.py`, `sdk/types.py`
**Acceptance**:
- [ ] Connects to Base Sepolia via RPC URL
- [ ] Loads contract ABI (embed or load from file)
- [ ] `submit_task()` sends transaction, returns task_id
- [ ] `get_task()` reads task state
- [ ] `get_checkpoints()` returns CID list
- [ ] Event listening for `TaskFailed`, `FallbackAssigned`

**Interface**:
```python
@dataclass
class Task:
    task_id: str
    state: str
    operator: str
    primary_agent: str
    fallback_agent: str
    escrow: int
    primary_checkpoints: int
    fallback_checkpoints: int
    last_heartbeat: int
    deadline: int
    checkpoint_cids: List[str]

class CairnClient:
    def __init__(self, rpc_url: str, contract_address: str, private_key: str):
        ...

    async def submit_task(
        self,
        primary_agent: str,
        fallback_agent: str,
        spec: dict,
        heartbeat_interval: int,
        deadline: int,
        escrow: int
    ) -> str:
        """Submit task, return task_id."""

    async def get_task(self, task_id: str) -> Task:
        """Get task details."""
```

### Task 12: Implement CairnAgent Wrapper
**Files**: `sdk/agent.py`
**Acceptance**:
- [ ] Wraps any agent with CAIRN protocol
- [ ] Auto-checkpoints after each subtask
- [ ] Background heartbeat thread
- [ ] `execute()` for primary agent
- [ ] `resume()` for fallback agent
- [ ] Graceful shutdown on failure

**Interface**:
```python
class CairnAgent:
    def __init__(
        self,
        agent: Any,
        client: CairnClient,
        ipfs: CheckpointStore
    ):
        ...

    async def execute(self, task_id: str, subtasks: List[dict]) -> dict:
        """Execute task with automatic checkpointing and heartbeat."""

    async def resume(self, task_id: str, from_checkpoint: int) -> dict:
        """Resume task from checkpoint (for fallback)."""
```

### Task 12b: Implement CairnObserver
**Files**: `sdk/observer.py`
**Acceptance**:
- [ ] `CairnObserver` base class with event subscription pattern
- [ ] `on_task_submitted`, `on_checkpoint`, `on_heartbeat`, `on_failed`, `on_resolved` hooks
- [ ] `WebhookObserver` implementation (posts events to URL)
- [ ] `LoggingObserver` implementation (logs to stdout/file)
- [ ] Easy subscription: `agent.add_observer(observer)`

**Interface** (see `docs/observer.md` for full spec):
```python
class CairnObserver(ABC):
    """Base observer for task lifecycle events."""

    async def on_task_submitted(self, task_id: str, task: Task) -> None: ...
    async def on_checkpoint(self, task_id: str, index: int, cid: str) -> None: ...
    async def on_heartbeat(self, task_id: str, timestamp: int) -> None: ...
    async def on_failed(self, task_id: str, reason: str) -> None: ...
    async def on_resolved(self, task_id: str, settlement: dict) -> None: ...

class WebhookObserver(CairnObserver):
    def __init__(self, webhook_url: str, secret: str = None): ...

class LoggingObserver(CairnObserver):
    def __init__(self, logger: logging.Logger = None): ...
```

### Task 13: Write SDK Tests
**Files**: `tests/test_*.py`
**Acceptance**:
- [ ] Unit tests for CheckpointStore (mock Pinata)
- [ ] Unit tests for CairnClient (mock web3)
- [ ] Unit tests for CairnObserver (mock events)
- [ ] Integration test with local contract (if available)
- [ ] Test error handling and retries
- [ ] Coverage > 85%

### Task 14: Package and Document
**Files**: `README.md`, docstrings
**Acceptance**:
- [ ] README with installation instructions
- [ ] Quick start example (5 lines to integrate)
- [ ] API reference for all public classes
- [ ] Environment variables documented (PINATA_JWT, RPC_URL, etc.)

## BOUNDARIES

**Do NOT**:
- Add features not in PRD-01 (no recovery scoring queries)
- Block on contract interactions (use async/await)
- Store private keys in code (use environment variables)
- Add CLI interface (frontend handles user interaction)

**Do**:
- Use async/await throughout (asyncio compatible)
- Use pydantic for data validation
- Add type hints to all functions
- Log important events (checkpoint, heartbeat, failure)
- Handle network errors gracefully

## SUCCESS CRITERIA

1. **Installs**: `pip install -e .` succeeds
2. **Tests**: `pytest` passes, coverage > 85%
3. **Works**: Can submit task, checkpoint, settle via SDK
4. **Documented**: README covers all use cases

## PATTERNS TO FOLLOW

**Async Context Manager for Heartbeat**:
```python
class CairnAgent:
    async def __aenter__(self):
        self._start_heartbeat()
        return self

    async def __aexit__(self, *args):
        self._stop_heartbeat()
```

**Retry with Backoff**:
```python
async def _retry(self, fn, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            return await fn()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

**Environment Config**:
```python
import os

class Config:
    RPC_URL = os.getenv("CAIRN_RPC_URL", "https://sepolia.base.org")
    CONTRACT = os.getenv("CAIRN_CONTRACT")
    PINATA_JWT = os.getenv("PINATA_JWT")
```

## HANDOFF

When complete, update `PRD-01-STATUS.md`:
- Mark tasks 9-14 as ✅
- Note any API changes from PRD
- Unblock Frontend-Dev (tasks 15-22)

Notify: "SDK ready. Install with `pip install -e ./sdk`. See README for usage."
