# CAIRN v2 — Base Sepolia Deployment Runbook

Deploy-ready runbook for the v2 upgrade (PRD-04). **Deployment is performed by the
maintainer, not by automation.** This document is the hand-off from Phase 6:
everything below is prepared and tested; the steps here are the human actions to
put v2 on Base Sepolia.

> ⚠️ Testnet only. Do not deploy to mainnet before an external security audit
> (see `SECURITY.md`).

## What v2 changes vs the live v1

| Aspect | v1 (currently live) | v2 (this deployment) |
|---|---|---|
| Recovery formula | linear `0.5F+0.3B+0.2D` | multiplicative `F^0.80·B^0.35·D^0.15` (`RecoveryRouterV2`) |
| Routing | binary at 0.30 | three-tier FULL/REDUCED/DISPUTED at 0.40/0.35 |
| Arbiter stake | 15% | 20% of dispute value |
| Checkpoints | no schema enforcement | `commitCheckpointBatch` reverts on `schemaHash != specHash` |
| Legacy MVP | active | freeze via `CairnTaskMVP.freeze()` |

## Pre-flight

- [ ] `main` green: `cd contracts && forge test` → 375 passing
- [ ] Coverage gate: `forge coverage` → deployed-core contracts ≥95% lines
- [ ] `contracts/.env` set: `DEPLOYER_PRIVATE_KEY`, `ADMIN_ADDRESS`, `FEE_RECIPIENT_ADDRESS`, `BASE_SEPOLIA_RPC_URL`, `BASESCAN_API_KEY`
- [ ] Deployer funded with Base Sepolia ETH
- [ ] **Governance admin (H-7):** for anything beyond throwaway testing, `ADMIN_ADDRESS`
      MUST be a **multisig (Gnosis Safe) or `TimelockController`**, not a single EOA.
      `CairnGovernance.execute()` is an unrestricted, immediate privileged call (it can
      swap module contracts and redirect fees), so the admin *is* the security boundary —
      a compromised single EOA is total protocol compromise. If you must bootstrap with an
      EOA, hand off immediately afterward via the two-step `transferAdmin` → `acceptAdmin`
      (the new admin calls `acceptAdmin`, proving control before it takes effect).

## 1. Deploy the v2 stack

```bash
cd contracts
forge script script/DeployV2.s.sol:DeployCairnV2 \
  --rpc-url "$BASE_SEPOLIA_RPC_URL" \
  --broadcast --verify --etherscan-api-key "$BASESCAN_API_KEY"
```

This deploys CairnGovernance, RecoveryRouterV2, FallbackPool, ArbiterRegistry, and
CairnCore, and wires `cairnCore` into the router/pool/registry. Record the five
addresses from the console summary (also in `broadcast/DeployV2.s.sol/84532/run-latest.json`).

## 2. Activate v2 routing (governance)

Three-tier routing ships **off by default** (`threeTierRoutingEnabled == false`), so a
fresh deploy behaves like v1 binary routing until governance flips it.

`setThreeTierRouting` is `onlyGovernance` — it requires `msg.sender == address(governance)`,
so it **cannot** be called from an EOA directly. Route it through `CairnGovernance.execute`,
which the admin (`ADMIN_ADDRESS`) is authorized to call:

```bash
# admin sends: governance.execute(cairnCore, setThreeTierRouting(true))
cast send <CairnGovernance> "execute(address,bytes)" \
  <CairnCore> $(cast calldata "setThreeTierRouting(bool)" true) \
  --rpc-url base_sepolia --private-key <ADMIN_PRIVATE_KEY>
```

- The admin key that signs this must correspond to `ADMIN_ADDRESS` (the `CairnGovernance`
  admin set at deploy). This is a maintainer action, not automation.
- Arbiter stake (20%) and checkpoint schema validation are **already active** in the v2
  bytecode — no governance call needed.
- Optional (same `execute` pattern): `setReducedScopeCap(bps)` to tune the reduced-scope
  fallback cap (default 5000 = 50%), and `pause()`/`unpause()`.

Confirm: `cast call <CairnCore> "threeTierRoutingEnabled()(bool)" --rpc-url base_sepolia` → `true`.

## 3. Freeze the legacy MVP (optional, when ready)

Once the deployed `CairnTaskMVP` has no in-flight tasks:

```
CairnTaskMVP.freeze()   // onlyOwner — blocks new submitTask; existing tasks still settle
```

## 4. Post-deploy verification

- [ ] All 5 contracts show **Verified** source on `sepolia.basescan.org`
- [ ] `cast code <addr>` returns bytecode for each
- [ ] `threeTierRoutingEnabled()` → `true`
- [ ] Smoke test: submit → start → `commitCheckpointBatch(..., specHash)` → complete on a tiny escrow
- [ ] A checkpoint with a wrong `schemaHash` reverts (`InvalidCheckpointSchema`)

## 5. Record the deployment

- [ ] Update the README "Deployed Contracts (Base Sepolia)" table with the new v2 addresses
- [ ] Update `contracts/.env` `CAIRN_CONTRACT_ADDRESS`
- [ ] Update the frontend contract addresses + the SDK/CLI (note: `commitCheckpointBatch`
      now takes a `schemaHash` argument — SDK v2 must pass it)
- [ ] Mark PRD-04 Phase 6 deploy task complete in `PRDs/PRD-04-V2-UPGRADE/STATUS.md`

## Rollback

The v1 contracts remain live and independent; if v2 shows problems, integrations can
continue pointing at the v1 addresses. v2's `setThreeTierRouting(false)` also reverts
routing to binary behavior without redeploying.
