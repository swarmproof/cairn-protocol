# CairnTaskMVP Deprecation & Migration

`CairnTaskMVP` is the original 4-state hackathon MVP contract. It is **superseded by
`CairnCore`** (the full 6-state protocol) and is being retired as part of the v1 → v2
upgrade (PRD-04 Phase 4). This note explains the freeze mechanism and how to migrate.

## What changes

`CairnTaskMVP` gains a one-way **freeze** switch:

- `freeze()` — owner-only, irreversible. Sets `frozen = true` and emits `MvpFrozen(timestamp)`.
- Once frozen, `submitTask` reverts with `MvpIsFrozen()` — **no new tasks** can be created.
- **Existing tasks are unaffected.** `heartbeat`, `commitCheckpoint`, `completeTask`, and
  `settle` continue to work so in-flight tasks finish and escrow settles normally.

Freezing is a governance/owner action taken at v2 activation; it is not automatic.

## Why deprecate rather than extend

Per PRD-04 §3.5, the MVP is frozen (Option A) rather than upgraded to the v2 checkpoint
API (Option B). The MVP lacks the v2 features — three-tier recovery routing, multiplicative
recovery scoring, and checkpoint schema validation — and adding them would fork the
checkpoint signature. Keeping the MVP frozen-but-settling avoids stranding any in-flight
escrow while steering all new work to `CairnCore`.

## Migrating from CairnTaskMVP to CairnCore

There is **no on-chain state migration** — the two contracts are independent. Migration is
operational:

| MVP (`CairnTaskMVP`) | Full protocol (`CairnCore`) |
|---|---|
| `submitTask(primary, fallback, specHash, hb, deadline)` — fallback pre-declared | `submitTask(taskType, specHash, primary, hb, deadline)` — fallback **auto-selected** from the pool |
| `commitCheckpoint(taskId, cid)` — one at a time | `commitCheckpointBatch(taskId, count, merkleRoot, latestCID, schemaHash)` — Merkle-batched + schema-validated |
| 4 states | 6 states (adds RECOVERING/DISPUTED with three-tier routing) |
| Binary recover/dispute | Multiplicative recovery score + FULL/REDUCED/DISPUTED routing |

**Recommended sequence:**
1. Stop submitting new tasks to the MVP; point integrations at the deployed `CairnCore` address.
2. Let any in-flight MVP tasks reach `RESOLVED` and settle.
3. Once the MVP has no active tasks, call `freeze()` to close it to new submissions.

Existing MVP task escrow is never locked by the freeze — only new submissions are blocked.
