# PRD-01: CAIRN MVP — Status Tracker

> Last Updated: 2026-03-18

## Current Phase

- [x] **Phase 0**: PRD Written & Approved
- [x] **Phase 1**: Contract Development ✅ (87% - awaiting deployment)
- [ ] **Phase 2**: SDK Development (Days 4-5)
- [ ] **Phase 3**: Frontend & Demo (Days 6-8)
- [ ] **Phase 4**: Integration & Polish (Days 9-10)
- [ ] **Phase 5**: Submission

## Pipeline Checklist

| Stage | Status | Notes |
|-------|--------|-------|
| PRD Approved | ✅ | Ready for execution |
| Contract Complete | ✅ | 49 tests, 98.95% coverage |
| Contract Audited | ✅ | PRD compliance verified |
| Contract Deployed | ✅ | `0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417` |
| SDK Complete | 🔵 | Ready to start |
| Frontend Complete | ⏳ | Blocked by SDK |
| E2E Tests Pass | ⏳ | Blocked by frontend |
| Demo Rehearsed | ⏳ | Blocked by E2E |
| Submitted | ⏳ | Target: March 23 |

## Active Teammates

| Teammate | Assigned To | Status | Current Task |
|----------|-------------|--------|--------------|
| Contract-Dev | Tasks 1-6 | ✅ Complete | Awaiting deployment |
| SDK-Dev | Tasks 9-14 | ⏸️ Waiting | Blocked by deployment |
| Frontend-Dev | Tasks 15-22 | ⏸️ Waiting | Blocked by SDK |
| Integration | Tasks 23-26 | ⏸️ Waiting | Blocked by All |

## Task Breakdown

### Phase 1: Contract Development

| # | Task | Owner | Status | Completed | Notes |
|---|------|-------|--------|-----------|-------|
| 1 | Setup Foundry project | Contract-Dev | ✅ | 2026-03-18 | Dependencies installed |
| 2 | Implement state machine | Contract-Dev | ✅ | 2026-03-18 | 4 states |
| 3 | Implement checkpoint storage | Contract-Dev | ✅ | 2026-03-18 | CID array |
| 4 | Implement heartbeat system | Contract-Dev | ✅ | 2026-03-18 | Permissionless liveness |
| 5 | Implement settlement | Contract-Dev | ✅ | 2026-03-18 | Proportional split |
| 6 | Write unit tests | Contract-Dev | ✅ | 2026-03-18 | 49 tests, 98.95% coverage |
| 7 | Deploy to Base Sepolia | Agent | ✅ | 2026-03-18 | `0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417` |
| 8 | Verify on Basescan | Agent | ✅ | 2026-03-18 | [Verified](https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417) |

### Phase 2: SDK Development

| # | Task | Branch | Status | Notes |
|---|------|--------|--------|-------|
| 9 | Setup Python package | `claude/sdk-core` | ⏳ | Needs contract address |
| 10 | Implement CheckpointStore | `claude/sdk-core` | ⏳ | With Bonfires |
| 11 | Implement CairnClient | `claude/sdk-core` | ⏳ | |
| 12 | Implement CairnAgent wrapper | `claude/sdk-core` | ⏳ | |
| 13 | Write SDK tests | `claude/sdk-core` | ⏳ | |
| 14 | Package and document | `claude/sdk-core` | ⏳ | |

### Phase 3: Frontend & Demo

| # | Task | Branch | Status | Notes |
|---|------|--------|--------|-------|
| 15 | Setup Next.js + wagmi | `claude/frontend` | ⏳ | Needs Phase 2 |
| 16 | Task list component | `claude/frontend` | ⏳ | |
| 17 | Task detail component | `claude/frontend` | ⏳ | |
| 18 | State machine visualization | `claude/frontend` | ⏳ | |
| 19 | Demo control panel | `claude/frontend` | ⏳ | |
| 20 | Checkpoint viewer | `claude/frontend` | ⏳ | |
| 21 | Settlement display | `claude/frontend` | ⏳ | |
| 22 | Deploy to Vercel | `claude/frontend` | ⏳ | |

### Phase 4: Integration & Polish

| # | Task | Branch | Status | Notes |
|---|------|--------|--------|-------|
| 23 | E2E happy path test | `claude/integration` | ⏳ | |
| 24 | E2E recovery path test | `claude/integration` | ⏳ | |
| 25 | Demo script rehearsal | `claude/integration` | ⏳ | |
| 26 | Record backup video | `claude/integration` | ⏳ | |

## Blockers

| # | Blocker | Impact | Owner | Resolution | Status |
|---|---------|--------|-------|------------|--------|
| 1 | Contract deployment | SDK blocked | USER | Deploy to Base Sepolia | ⏳ Pending |

## Deliverables Completed

| Artifact | Path | Status |
|----------|------|--------|
| Interface | `contracts/src/interfaces/ICairnTaskMVP.sol` | ✅ |
| Contract | `contracts/src/CairnTaskMVP.sol` | ✅ Audited |
| Tests | `contracts/test/CairnTaskMVP.t.sol` | ✅ 49 tests |
| Deploy Script | `contracts/script/Deploy.s.sol` | ✅ |
| PRD-07 | `PRDs/PRD-07-CHECKPOINT-OPTIMIZATION/` | ✅ Planned |

## Gas Report (from audit)

| Operation | Gas | PRD Target | Status |
|-----------|-----|------------|--------|
| submitTask | 225,558 | < 200,000 | ⚠️ Slightly over |
| commitCheckpoint | 66,991 | < 60,000 | ⚠️ Slightly over |
| heartbeat | 35,105 | < 30,000 | ⚠️ Slightly over |
| settle | 106,466 | < 100,000 | ⚠️ Slightly over |

*Note: Gas slightly over targets, documented in audit. PRD-07 addresses optimization.*

## Timeline

```
March 2026
═══════════════════════════════════════════════════════════════
     13  14  15  16  17  18  19  20  21  22  23
                         ▼
                       TODAY
     ├───────────────────┤
     │   Contract Dev    │  ← ✅ COMPLETE (awaiting deploy)
                         ├───────────┤
                         │  SDK Dev  │  ← NEXT
                                     ├───────────────┤
                                     │   Frontend    │
                                                     ├─────┤
                                                     │Integ│
                                                           ▼
                                                       SUBMIT
```

## Next Steps

1. **USER**: Deploy contract to Base Sepolia
2. **USER**: Provide contract address
3. **Agent**: Spawn SDK-Dev with Bonfires integration
4. Continue Phase 2

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete |
| 🟢 | In Progress |
| 🔵 | Ready to Start |
| ⏸️ | Blocked / Waiting |
| ⏳ | Not Started |
