# CAIRN Proof of Concept Scope

> Synthesis Hackathon 2026 — 7-day build plan

---

## What Gets Built (7 days)

### Day 1–2: CairnTask.sol + CairnHook.sol

**Scope:**
- Full state machine implementation
- All enforce functions (public, permissionless)
- Checkpoint commit + schema validation
- Recovery score computation
- Escrow split logic
- Event emission for all transitions
- Integration with ERC-8183 via hook

**Deliverable:** Deploy to Base Sepolia testnet → Base mainnet before submission

---

### Day 3: CairnAgent Wrapper (Python / LangGraph)

**Scope:**
- Six LangGraph nodes: `pre_task_query`, `start_task`, `heartbeat_loop`, `commit_checkpoint`, `report_cost`, `handle_failure`
- Wraps Lagartha (existing OpenClaw agent on EC2)
- Connects to deployed CairnTask contract
- Calls Bonfires API in `pre_task_query`

**Deliverable:** Working Python wrapper that makes any LangGraph agent CAIRN-compatible

---

### Day 4: RecoveryOrchestrator (Python)

**Scope:**
- Event listener for `TaskFailed` events with `score ≥ 0.6`
- Queries Bonfires API for fallback agent by task_type
- Queries Olas Mech Marketplace for agent availability
- Calls `assignFallback()` on CairnTask contract

**Deliverable:** Autonomous recovery orchestration without human intervention

---

### Day 5: BonfiresAdapter (Python)

**Scope:**
- Event listener for `TaskFailed` and `TaskResolved` events
- Fetches full record from IPFS using emitted CID
- Writes structured record to Bonfires data room via API
- Seeds graph with Lagartha's prior execution history (genesis records)

**Deliverable:** Live intelligence layer that grows automatically

---

### Day 6: Integration Testing

**Test scenarios:**
- Full lifecycle test: RUNNING → FAILED → RECOVERING → RESOLVED
- Full lifecycle test: RUNNING → FAILED → DISPUTED → auto-refund
- Heartbeat interval validation
- Checkpoint schema validation (valid + invalid CID rejection)
- Escrow split verification
- Bonfires graph query verification (A2 returns correct patterns)

**Deliverable:** All critical paths verified end-to-end

---

### Day 7: Demo Preparation + Submission

**Scope:**
- Seed Bonfires graph with prior execution records from Lagartha on EC2
- Record demo script (beats timed to 3 minutes)
- Write submission document with contract addresses + demo video

**Deliverable:** Complete submission package

---

## What Does NOT Get Built (already live)

| Component | Status | Location |
|-----------|--------|----------|
| ERC-8004 Identity Registry | Live on Base mainnet | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| ERC-8004 Reputation Registry | Live on Base mainnet | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |
| ERC-8183 job factory | Live (draft March 2026) | Deployed on Base |
| ERC-7710 delegation framework | Live (MetaMask Smart Accounts Kit) | Integrated via SDK |
| Olas Mech Marketplace | Live | `olas.network/mech-marketplace` |
| Bonfires API | Live | `app.bonfires.ai` |
| IPFS | Live | Use Pinata or similar |

---

## PoC Simplifications

The PoC makes these simplifications that would need to be addressed in production:

| Simplification | PoC Approach | Production Approach |
|----------------|--------------|---------------------|
| **Schema validation** | keccak256 hash comparison | Full JSON schema validation |
| **Arbiter** | Not implemented; DISPUTED → auto-refund | Full arbiter agent pool |
| **Task type registry** | Hardcoded to 6 types | Open registry with registration |
| **Fallback pool** | Olas Mech only | Any registered agent meeting criteria |
| **The Graph subgraph** | Bonfires direct | The Graph indexes all events |

---

## Component Effort Estimates

| Component | Lines of Code | Complexity |
|-----------|---------------|------------|
| CairnTask.sol | ~250 | High |
| CairnHook.sol | ~80 | Medium |
| RecoveryOrchestrator | ~150 | Medium |
| CairnAgent wrapper | ~200 | Medium |
| BonfiresAdapter | ~100 | Low |
| **Total** | **~780** | — |

---

## Success Criteria

The PoC is successful if:

1. **Full lifecycle demo** — RUNNING → FAILED → RECOVERING → RESOLVED works end-to-end
2. **Permissionless enforcement** — Anyone can call `checkLiveness()` and trigger failure
3. **Checkpoint resumption** — Fallback agent reads CIDs and resumes from correct subtask
4. **Escrow split** — Original and fallback agents paid proportionally
5. **Intelligence accumulation** — Bonfires graph shows new records after execution
6. **Pre-task query** — A2 returns failure patterns from graph before task starts

---

*Synthesis Hackathon 2026*
