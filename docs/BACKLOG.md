# CAIRN — Launch Readiness Backlog

Living tracker for the work between "audited code" and "honest, publishable launch".
Grouped by theme; each item notes status and the PR that resolves it.

**Status:** ☐ open · ◑ in progress · ✅ done · ⏸ deferred (needs a decision)

Guiding principle (honesty-first): the public surface must tell **one true story** —
*v2 is live on Base Sepolia; zero tasks so far; the recovery formula is validated in
simulation, not in production recoveries* — before anything is published or launched.

---

## P0 — Correctness & honesty (stop active harm)

| Item | Detail | Status | PR |
|------|--------|--------|----|
| Frontend↔contract ABI/events | `LiveStats` listens for non-existent `TaskSubmitted`; `submitTask`/`commitCheckpointBatch` ABI predate deployed Core; `Task` tuple missing v2 fields; pipeline listens for `TaskResolved` + stale Core `0xB655…` | ☐ | — |
| Delete demo fallback numbers | Hardcoded `156/98.7%/12.4 ETH` on RPC error, hero `47`, intelligence `129`, `avgRecoveryTime=21`, fake trends | ☐ | — |
| Remove false claims | `pip install cairn-sdk` (404), `npm i @cairn/sdk` (nonexistent), dead subgraph endpoint, "production ready", "verified", "no admin key", "95% coverage", Discord w/o URL, `cairn.protocol`/`docs.cairnprotocol.com` dead hosts | ☐ | — |
| Unify license → AGPL-3.0 | Site says MPL-2.0, README says BUSL-1.1, package.json says AGPL. Standardize app to AGPL-3.0; footer link → org repo | ☐ | — |

## P1 — One true story (docs/paper consistency)

| Item | Detail | Status | PR |
|------|--------|--------|----|
| Propagate the honest sentence | README, CHANGELOG, WHITEPAPER abstract/§6.4/§10.3, PRD-04 STATUS, arXiv comments all state v2-is-live + sim-validated | ☐ | — |
| Paper drift: slashing §7.3 | Paper says 100% to operator; code (#50) is 50/25/+10 to treasury | ☐ | — |
| Paper drift: governance §8 | Paper says timelock params; code (#51) has an advisory param store + constants | ☐ | — |
| Implementation Status section | Add a single canonical status section to the paper | ☐ | — |
| Spec↔code name map | `checkLiveness`→`detectFailure`, `commitCheckpoint`→`commitCheckpointBatch`, `settle`→internal, `confirmTask`→`startTask` | ☐ | — |
| Standardize test count | Docs cite 381/339/375/401; actual is 408 | ☐ | — |
| Fix stale addresses/URLs | pipeline README Core `0xB655…`, subgraph `DEPLOYMENT.md` startBlock, cite URL `MarouaBoud`→`swarmproof` | ☐ | — |

## P2 — Bigger (needs design/product decisions)

| Item | Detail | Status | PR |
|------|--------|--------|----|
| Site redesign | Real cairn visualization (stones/trail), amber/stone palette, drop Magic UI/emoji-robot/Spline, real whitepaper link | ⏸ | — |
| Publish SDK (or keep claims removed) | No JS SDK exists; Python SDK is 0.1.0 alpha with ABI mismatch, not on PyPI | ⏸ | — |
| arXiv publish | License decision (All Rights Reserved vs non-exclusive distribution), reconcile 2 drifted paper copies, ERC-CAIRN reframed as draft | ⏸ | — |
| Machine-checked proofs | Paper theorems are prose; optional formalization | ⏸ | — |

## Housekeeping

| Item | Detail | Status | PR |
|------|--------|--------|----|
| Close #41/#42 | Reentrancy + dispute-timeout — resolved (M-1/H-1) | ☐ | — |
| Close #43/#44 | Stub "fixes" — superseded by #46/#48 | ☐ | — |
| M-11 (Olas) | Distinct Olas activation path (selection returns unregistered mech) | ⏸ | — |
| H-5 follow-up | Bind checkpoint count to Merkle leaf count (cap shipped in #46) | ⏸ | — |
| H-7 follow-up | Wire param store into consumers or remove it (advisory doc shipped in #51) | ⏸ | — |
| Redeploy to Sepolia | Ship audited contracts (#46–#52) to testnet; re-point frontend/subgraph | ☐ | — |

---

## Completed audit remediation (context)

3 Critical + 7 High + 8 Medium fixed across PRs #46–#51 (H-5/H-7 mitigated with tracked
follow-ups). See `docs/audit/SECURITY-AUDIT.md`. Full suite: 408 passing.
