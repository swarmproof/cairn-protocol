# Spawn Prompt: Contract-Dev

> CAIRN MVP Smart Contract Development

## CONTEXT

You are implementing the core smart contracts for CAIRN protocol MVP.

**PRD Location**: `/PRDs/PRD-01-MVP-HACKATHON.md`
**Target Repo**: `cairn-protocol`
**Your Tasks**: 1-8 (Contract Development phase)

**Read First** (understand existing patterns):
- OpenZeppelin ReentrancyGuard: `@openzeppelin/contracts/utils/ReentrancyGuard.sol`
- OpenZeppelin Ownable: `@openzeppelin/contracts/access/Ownable.sol`
- Foundry test patterns: https://book.getfoundry.sh/forge/tests

## SCOPE

**Directory Structure to Create**:
```
cairn-protocol/
├── contracts/
│   └── src/
│       ├── CairnTaskMVP.sol      # Main contract (you create)
│       └── interfaces/
│           └── ICairnTaskMVP.sol  # Interface (you create)
├── test/
│   └── CairnTaskMVP.t.sol        # Tests (you create)
├── script/
│   └── Deploy.s.sol               # Deployment script (you create)
├── foundry.toml                   # Config (you create)
└── remappings.txt                 # Dependencies (you create)
```

## YOUR TASKS

### Task 1: Setup Foundry Project
**Files**: `foundry.toml`, `remappings.txt`
**Acceptance**:
- [ ] `forge build` succeeds
- [ ] OpenZeppelin contracts installed via `forge install`
- [ ] Remappings configured for OZ imports

### Task 2: Implement State Machine
**Files**: `contracts/src/CairnTaskMVP.sol`
**Acceptance**:
- [ ] `State` enum: RUNNING, FAILED, RECOVERING, RESOLVED
- [ ] `Task` struct with all fields per PRD Section 2.1
- [ ] `submitTask()` creates task in RUNNING state
- [ ] State transitions enforced via modifiers
- [ ] Events emitted for all transitions

### Task 3: Implement Checkpoint Storage
**Files**: `contracts/src/CairnTaskMVP.sol`
**Acceptance**:
- [ ] `commitCheckpoint(taskId, cid)` stores CID
- [ ] Sequential index enforcement (no gaps)
- [ ] Tracks `primaryCheckpoints` vs `fallbackCheckpoints`
- [ ] `CheckpointCommitted` event emitted
- [ ] Only assigned agent can checkpoint

### Task 4: Implement Heartbeat System
**Files**: `contracts/src/CairnTaskMVP.sol`
**Acceptance**:
- [ ] `heartbeat(taskId)` updates `lastHeartbeat`
- [ ] `checkLiveness(taskId)` public function
- [ ] Triggers FAILED if `block.timestamp > lastHeartbeat + interval`
- [ ] Min interval enforced (30 seconds)
- [ ] `HeartbeatReceived` and `TaskFailed` events

### Task 5: Implement Settlement
**Files**: `contracts/src/CairnTaskMVP.sol`
**Acceptance**:
- [ ] `settle(taskId)` calculates proportional shares
- [ ] Protocol fee: 0.5% (50 bps)
- [ ] Uses `call{value:}` for ETH transfers (not `transfer()`)
- [ ] ReentrancyGuard applied
- [ ] `TaskResolved` event with all amounts

### Task 6: Write Unit Tests
**Files**: `test/CairnTaskMVP.t.sol`
**Acceptance**:
- [ ] Test happy path: submit → checkpoints → complete → settle
- [ ] Test recovery path: submit → checkpoints → fail → fallback → settle
- [ ] Test access control: unauthorized calls revert
- [ ] Test edge cases: zero checkpoints, stale heartbeat, double settle
- [ ] Coverage > 95%

### Task 7: Deploy to Base Sepolia
**Files**: `script/Deploy.s.sol`
**Acceptance**:
- [ ] Deployment script works with `forge script`
- [ ] Contract deployed to Base Sepolia
- [ ] Contract address saved to `.env` or deployment log
- [ ] Initial parameters set correctly

### Task 8: Verify on Basescan
**Manual task**
**Acceptance**:
- [ ] Contract verified on Basescan
- [ ] Source code readable on explorer
- [ ] ABI available for SDK

## BOUNDARIES

**Do NOT**:
- Add features not in PRD-01 (no recovery scoring, no DISPUTED state)
- Use `transfer()` or `send()` for ETH — use `call{value:}`
- Store large data on-chain — only 32-byte CIDs
- Add governance or upgradeability (MVP is simple)
- Change the interface signatures from PRD Section 5.1

**Do**:
- Use custom errors instead of require strings (gas savings)
- Follow CEI pattern (Checks-Effects-Interactions)
- Emit events for every state change
- Add natspec comments for public functions
- Use Solidity 0.8.20+ for built-in overflow checks

## SUCCESS CRITERIA

1. **Builds**: `forge build` passes with no warnings
2. **Tests**: `forge test` passes, coverage > 95%
3. **Deploys**: Contract live on Base Sepolia
4. **Verified**: Source verified on Basescan
5. **Interface**: Matches PRD Section 5.1 exactly

## PATTERNS TO FOLLOW

**State Machine Pattern**:
```solidity
modifier inState(bytes32 taskId, State expected) {
    require(tasks[taskId].state == expected, InvalidState());
    _;
}

function checkLiveness(bytes32 taskId) external inState(taskId, State.RUNNING) {
    // ...
}
```

**Custom Errors**:
```solidity
error InvalidState();
error Unauthorized();
error InsufficientEscrow(uint256 required, uint256 provided);
error NotStale();
```

**Safe ETH Transfer**:
```solidity
(bool success, ) = recipient.call{value: amount}("");
require(success, TransferFailed());
```

## HANDOFF

When complete, update `PRD-01-STATUS.md`:
- Mark tasks 1-8 as ✅
- Add contract address to notes
- Unblock SDK-Dev (tasks 9-14)

Notify: "Contract deployed at [address] on Base Sepolia. SDK can proceed."
