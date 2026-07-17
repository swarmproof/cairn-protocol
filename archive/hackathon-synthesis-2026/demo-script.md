# CAIRN Demo Script

> 3-minute demo for Synthesis Hackathon 2026

---

## Setup (before demo starts)

- CairnTask.sol deployed on Base Sepolia
- Bonfires data room seeded with 12 prior execution records from Lagartha's EC2 history:
  - 4 records: `defi.price_fetch` — 2 successes, 1 RATE_LIMIT failure, 1 HEARTBEAT_MISSED failure
  - 4 records: `data.report_generate` — 3 successes, 1 CONTEXT_OVERFLOW failure
  - 4 records: `defi.trade_execute` — 2 successes, 2 BUDGET_HIT failures
- Two terminal windows open: agent terminal + enforce terminal
- Bonfires graph visible on screen (showing seeded records)

---

## Beat by Beat

### 0:00 — The Broken World (30 seconds)

**Script:**

> "Every agent team has written their own failure handling. Here is what Lagartha does without CAIRN."

**Action:**
- Run Lagartha without CairnAgent wrapper on a `defi.price_fetch` task
- Hit the CoinGecko rate limit
- Lagartha crashes silently

**Show:**
- No record written
- No escrow settlement
- No fallback
- Nothing learned

**Closing line:**

> "The failure disappeared. Twenty minutes later, any other agent will hit the same wall."

---

### 0:30 — CAIRN Deployed. Same Task. (20 seconds)

**Script:**

> "Now with CAIRN. Same task. Watch what changes."

**Action:**
- Run Lagartha with the CairnAgent wrapper
- Show A2 firing: the `pre_task_query` hits Bonfires

**Show:**
- The graph already has a RATE_LIMIT record for `defi.price_fetch`
- Terminal shows warning: "Known failure pattern: RATE_LIMIT at api.coingecko.com — 1 prior occurrence."
- Lagartha starting the task
- State = RUNNING
- Heartbeat clock ticking
- First checkpoint committed (CID visible on-chain)

---

### 1:00 — The Failure (30 seconds)

**Script:**

> "Rate limit hits. Lagartha misses her heartbeat."

**Action:**
- In the enforce terminal: `checkLiveness(taskId)`
- Called from a separate address — anyone can call this, no trusted keeper required

**Show:**
- State transition fires on-chain: RUNNING → FAILED
- `TaskFailed` event emitted
- CID of Failure Record appears in terminal
- Bonfires adapter picks up the event
- New node appears in the Bonfires graph

**Key stat to highlight:**

> "Recovery score: 0.74. Score is HIGH — this is a liveness failure, 42% budget remaining, 31% deadline remaining. Recovery path fires."

---

### 1:30 — Autonomous Recovery (40 seconds)

**Script:**

> "No human told CAIRN to recover. The score triggered it automatically."

**Action:**
- RecoveryOrchestrator: queries Bonfires for best `defi.price_fetch` fallback agent
- Olas Mech Marketplace returns available agent
- `assignFallback(taskId, fallbackAgentId)` called
- State = RECOVERING

**Show:**
- Task state transferred
- Checkpoint CID list passed to fallback
- Fallback reads the last committed output from IPFS
- Fallback resumes from subtask 3 (not from zero)
- New heartbeat clock starts for fallback
- Fallback completes subtasks 3 and 4

---

### 2:10 — Resolution (30 seconds)

**Script:**

> "Fallback completes. CAIRN settles."

**Show:**
- State: RECOVERING → RESOLVED
- Escrow split: Lagartha (3 subtasks) gets 60%, Fallback (2 subtasks) gets 40% minus protocol fee
- Both agents paid automatically
- ERC-8004 reputation updated for both
- Resolution Record written
- New node appears in Bonfires graph — the complete execution path visible

---

### 2:40 — The Lesson Inherited (20 seconds)

**Script:**

> "Same task type. New agent. No human intervention."

**Action:**
- Run the same `defi.price_fetch` task again with a third agent

**Show:**
- A2 query: Bonfires now returns the full failure pattern + the successful recovery path
- The new agent configures to use the Olas Mech Marketplace API endpoint that succeeded
- It completes without hitting the rate limit

**Closing line:**

> "The graph learned. The next agent inherited the lesson. That is CAIRN."

---

### 3:00 — End.

---

## Visual Checklist

| Time | Visual on Screen |
|------|------------------|
| 0:00 | Terminal: Lagartha crash, no output |
| 0:30 | Terminal: CAIRN warning + checkpoint commit |
| 1:00 | Terminal: enforce call + Bonfires graph update |
| 1:30 | Terminal: fallback assignment + state transfer |
| 2:10 | Terminal: escrow split + graph update |
| 2:40 | Terminal: new agent query + successful completion |

---

## Key Messages to Land

1. **Permissionless enforcement** — Anyone can call `checkLiveness()`. No trusted keeper.
2. **Resume, not restart** — Fallback reads checkpoints, resumes from subtask 3.
3. **Automatic settlement** — Escrow splits proportionally. No human required.
4. **Intelligence accumulates** — Graph grows with every execution.
5. **Lessons inherited** — Future agents query the graph before starting.

---

*Synthesis Hackathon 2026*
