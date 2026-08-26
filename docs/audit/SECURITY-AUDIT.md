# CAIRN Protocol — Security Audit & Remediation

Full-surface review of the protocol contracts (`CairnCore`, `FallbackPool`,
`ArbiterRegistry`, `RecoveryRouter`, `RecoveryRouterV2`, `CairnGovernance`, and their
UUPS-upgradeable variants), with every finding verified against source and remediated
across **both** the non-upgradeable and upgradeable contract lines.

**Status legend:** ✅ fixed · ◑ mitigated (residual follow-up) · ☐ tracked (follow-up)

## Summary

| ID | Severity | Area | Status | PR |
|----|----------|------|--------|----|
| CR-1 | Critical | FallbackPool admin setters had no access control | ✅ | #46 |
| CR-2 | Critical | Both routers' setters had no access control | ✅ | #46 |
| CR-3 | Critical | Operator could arbitrate/refund their own dispute | ✅ | #46 |
| H-1 | High | Dispute timeout anchored to `createdAt`, not dispute onset | ✅ | #46 |
| H-2 | High | Arbiter fee paid from stake pool + stranded in Core (insolvency) | ✅ | #46 |
| H-3 | High | `activeTaskCount` leak + dead slashing on failed recoveries | ✅ | #46 |
| H-4 | High | Post-deadline failure locked escrow in a RECOVERING loop | ✅ | #46 |
| H-5 | High | Self-reported checkpoint count captured the escrow split | ◑ | #46 |
| H-6 | High | Arbiter slash evadable by exiting during the appeal window | ✅ | #46 |
| H-7 | High | Governance: single-step admin; timelock bypass; dead params | ◑ | #46 |
| M-1 | Medium | Push-payment settlement could be blocked by a reverting recipient | ✅ | (this PR) |
| M-3 | Medium | SPLIT ruling: `agentShare` unbounded + fallback unpaid | ✅ | #47 |
| M-4 | Medium | Sybil gas-DoS of `selectFallback` (1-wei registration) | ✅ | #47 |
| M-5 | Medium | Pause only guarded `submitTask` | ✅ | #47 |
| M-7 | Medium | `activeTaskCount--` underflow could brick finalization | ✅ | #47 |
| M-8 | Medium | `setCairnCore` deploy-race stake drain | ✅ | #46 (via H-2) |
| M-10 | Medium | Missing zero-address validation (setContracts / initialize) | ✅ | #47 |
| M-9 | Medium | V2 router vs binary-path threshold mismatch | ✅ | (this PR) |
| M-2 | Medium | Appeals cosmetic — escrow settled before appeal window | ☐ | — |
| M-6 | Medium | Slashing recipient/amounts diverge from documented policy | ☐ | — |
| M-11 | Medium | Olas mech selected but not registered → activation reverts | ☐ | — |

Plus Low/Informational items (reputation gate default, recovery recorded as SUCCESS,
bare `receive()`, missing setter events, uncapped `maxConcurrentTasks`, zero-stake dust
edge, disabled domain check, dead `rule()`, settlement CEI ordering, floored-multiply
bias). Tracked for a hardening pass.

## Critical (all fixed — #46)

- **CR-1 / CR-2 — missing access control.** `FallbackPool` and both routers exposed
  admin setters (`setCairnCore`, threshold/registry setters) with no modifier — the
  `// In production, add onlyGovernance` placeholders were never actioned. An attacker
  could repoint `cairnCore` to brick `detectFailure` protocol-wide or slash/destroy all
  agent stakes. Gated behind `Ownable` (owner → transferable to governance) + zero-address
  checks + events.
- **CR-3 — self-dealing dispute resolution.** `resolveDispute` was permissionless and
  `isEligible` excluded the primary/fallback agents but not the operator, so an operator
  could arbitrate and refund their own dispute. Core now rejects `msg.sender == operator`.
  (A full arbiter-assignment/commit-reveal scheme remains a design follow-up; the economic
  deterrent is restored by H-6.)

## High (all fixed — #46)

- **H-1** — added `Task.disputedAt`, set on dispute entry; timeout gate + event now anchor
  to dispute onset rather than task creation.
- **H-2** — `executeRuling` no longer pays the arbiter from the registry's stake balance;
  Core pays the fee from escrow in `_settleDispute`. Removes the insolvency drain and the
  stranded-fee bug (and the M-8 deploy-race drain).
- **H-3** — added a `fallbackActivated` flag + symmetric `_releaseFallback` invoked on both
  success and failure, so a failed recovery releases the fallback's `activeTaskCount` and
  runs slashing. Recoveries are capped at one attempt (closes the re-detect/double-count loop).
- **H-4** — post-deadline failures route straight to `DISPUTED` (recoverable via timeout)
  instead of a RECOVERING loop that can never complete.
- **H-5 ◑** — per-batch checkpoint `count` bounded to `0 < count <= MAX_CHECKPOINTS_PER_BATCH`,
  defeating the documented `count=1e9` split-capture exploit. **Follow-up:** bind `count` to
  the committed Merkle tree's leaf count (full economic fix).
- **H-6** — added `Arbiter.stakeLockedUntil`; stake withdrawal/deregistration is blocked
  until the appeal window closes, so an overturn slash always lands.
- **H-7 ◑** — two-step admin transfer (`transferAdmin` + `acceptAdmin`) prevents an
  irrecoverable handoff and enables safely moving admin to a `TimelockController`/multisig.
  **Follow-up:** route `execute()` through that timelock/multisig (deployment invariant) and
  wire governance parameters into consumers (currently hardcoded constants).

## Medium — fixed

- **M-1** — settlement payouts use push-with-pull-fallback (`_payout` + `withdraw()`): a
  reverting recipient's share is credited as a claimable balance instead of reverting the
  whole settlement and locking escrow.
- **M-3** — bounded SPLIT `agentShare <= 100` and split the agent portion between
  primary/fallback by checkpoint contribution.
- **M-4** — `MIN_REGISTRATION_STAKE` (0.01 ETH) floor on fallback registration.
- **M-5** — `whenNotPaused` extended to all fund-moving / state-critical functions.
- **M-7** — guarded the `activeTaskCount` decrement against underflow.
- **M-10** — zero-address validation on `setContracts` (router/registry) and `initialize`
  (governance).
- **M-9** — Core's binary routing path now reads `recoveryRouter.recoveryThreshold()`
  instead of its local constant, so a wired V2 router's boundary is respected even when
  three-tier routing has not been enabled (no `[0.30, 0.35)` misroute).

## Medium — tracked (follow-up)

- **M-2** — settlement happens in the same tx as the ruling, so `overturnRuling` can punish
  an arbiter but cannot claw back distributed escrow. Requires holding escrow until the
  appeal window closes, or a re-settlement/clawback path.
- **M-6** — zero-checkpoint failure slashes 25% to the treasury; the documented policy is
  100% to the affected operator, with partial-failure and timeout tiers. Needs the intended
  slashing matrix confirmed.
- **M-9** — Core's binary routing path compares against its own `recoveryThreshold` constant
  while a wired V2 router's boundary is the lower threshold; a half-applied V2 migration
  misroutes scores in `[0.30, 0.35)`. Make Core read the router threshold or make the
  migration atomic.
- **M-11** — `selectFallback` can return an Olas mech not present in `_agents`, so
  `activateFallback` reverts. A conservative "only select registered mechs" guard was
  tried but effectively disables Olas selection entirely (mechs are external and never
  registered as `_agents`). The correct fix is a distinct Olas activation/slash path that
  does not assume pool registration — a design change tracked here rather than a one-line guard.

## Verified clean (do not "fix" incorrectly)

- Upgradeable line: `_disableInitializers()` in all constructors, `initializer`-guarded
  `initialize`, `_authorizeUpgrade` gated (`onlyGovernance`/`onlyOwner`), consistent
  `__gap` — no re-initialization or unprotected-upgrade seizure vector.
- Non-upgradeable `ReentrancyGuard` behind proxies is safe (OZ 5.x ERC-7201 namespaced slot).
- No PRB-Math domain-error DoS in the V2 recovery formula on the production input range.
- `classifyAndScore` is not griefable (onlyCairnCore + bounded inputs).

## Test coverage

`forge test` in `contracts/` — full suite green after each remediation (401 → 406 as
regression tests were added). Every fixed finding has a dedicated regression test asserting
the specific exploit is closed.
