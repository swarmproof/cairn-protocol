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
| CI green | `forge test` red on main (nightly Foundry double-prank); fixed + pinned to stable | ✅ | #56 |
| Frontend↔contract ABI/events | `LiveStats` event `TaskSubmitted`→`TaskCreated`; `getTask` tuple + `submitTask`/`commitCheckpointBatch` ABI + callers aligned to v2 | ✅ | #55, #57 |
| Delete demo fallback numbers | Removed error-fallback `156/98.7/12.4`, trends, `avgRecoveryTime`; hero `47` + fake insights; intelligence `129` + always-same detail pane + dead time-filter | ✅ | #55, #59 |
| Remove false claims | `pip install cairn-sdk`/`npm i @cairn/sdk`, `cairn.protocol` host, "production ready"/"verified"/"95% coverage", Discord-no-URL, `MarouaBoud`→`swarmproof` | ✅ | #58 |
| Unify license → AGPL-3.0 | Site/README/footer standardized to AGPL-3.0 | ✅ | #54 |
| Pipeline event names | Pipeline listens for `TaskResolved` (Core emits `TaskSettled`/`TaskCompleted`); address fixed in #60, event names remain | ☐ | — |

## P1 — One true story (docs/paper consistency)

| Item | Detail | Status | PR |
|------|--------|--------|----|
| Propagate the honest sentence | README/CHANGELOG/CLAUDE.md aligned to v2-is-live + sim-validated | ✅ | #60 |
| Paper drift: slashing §7.3 | Documented in Implementation Status (code = 50/25/+10 treasury; supersedes 100%-to-operator; §7.5 derivations flagged for re-derivation) | ✅ | #61 |
| Paper drift: governance §8 | Documented in Implementation Status (param store advisory; multisig admin) | ✅ | #61 |
| Implementation Status section | Added (authoritative) to the whitepaper | ✅ | #61 |
| Spec↔code name map | Added to the Implementation Status section | ✅ | #61 |
| Standardize test count | 339/375 → 408 (README, runbook) | ✅ | #60 |
| Fix stale addresses/URLs | pipeline Core `0xB655…`→`0x9917…`; subgraph startBlock; cite URLs `MarouaBoud`→`swarmproof` | ✅ | #60 |

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
| Close #41/#42 | Reentrancy + dispute-timeout — resolved (H-1 #46 / M-1 #48) | ✅ | closed |
| Close #43/#44 | Stub "fixes" — superseded by #46/#48 | ✅ | closed |
| M-11 (Olas) | Distinct Olas activation path (selection returns unregistered mech) | ⏸ | — |
| H-5 follow-up | Bind checkpoint count to Merkle leaf count (cap shipped in #46) | ⏸ | — |
| H-7 follow-up | Wire param store into consumers or remove it (advisory doc shipped in #51) | ⏸ | — |
| Redeploy to Sepolia | Ship audited contracts (#46–#52) to testnet; re-point frontend/subgraph | ☐ | — |

---

## Completed audit remediation (context)

3 Critical + 7 High + 8 Medium fixed across PRs #46–#51 (H-5/H-7 mitigated with tracked
follow-ups). See `docs/audit/SECURITY-AUDIT.md`. Full suite: 408 passing.
