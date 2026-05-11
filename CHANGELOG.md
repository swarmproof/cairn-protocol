# Changelog

All notable changes to the CAIRN Protocol will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-04 (Whitepaper v2.0)

### Changed — Protocol Specification

- **Recovery score formula** replaced with a multiplicative form: `r = F^0.80 × B^0.35 × D^0.15`. The v1 linear form `0.5·F + 0.3·B + 0.2·D` had a structural ~33% misrouting ceiling that no parameter tuning could break; the multiplicative form achieves 23.46% misrouting on the calibrated ground-truth model, within 0.93pp of the Bayes-optimal floor. See WHITEPAPER_V2.md §6.4 and `simulation/RESULTS_EQ4.md`.
- **Failure class weights** changed: LIVENESS 0.90→0.70, RESOURCE 0.50→0.30, LOGIC 0.10→0.00. Setting LOGIC to 0 routes all LOGIC failures directly to dispute (economically correct given the 8% empirical base recovery rate).
- **Routing thresholds** changed from a single binary boundary at 0.30 to a three-tier band: `r ≥ 0.40` → RECOVERING (full scope); `0.35 ≤ r < 0.40` → RECOVERING (reduced scope, capped budget); `r < 0.35` → DISPUTED.
- **Arbiter stake** raised from 15% to 20% of dispute value (50% slash on detection).
- **Checkpoint commit** signature changed to `commitCheckpointBatch(taskId, count, merkleRoot, latestCID)` with on-commit `specHash` validation.

### Added

- Monte Carlo calibration suite (4 runs, 16 experiments, 100,000 events each; deterministic seed=42) in `simulation/`. Documented in WHITEPAPER_V2.md §10.1 and `simulation/RESULTS_EQ4.md`.
- `RecoveryRouterV2.sol` reference implementation (24 unit tests passing, measured gas avg 5,748 / max 19,935).
- `PRDs/PRD-04-V2-UPGRADE/` — six-phase migration plan from v1 testnet to v2 contracts.
- `PUBLICATION/arxiv/` — submission-ready arXiv bundle (`.tex`, figures, metadata) for the v2.0 whitepaper.

### Documented (not yet deployed)

- The v2 spec is the **target protocol**. The Base Sepolia testnet currently runs v1; v2 ships via governance-gated migration through the `IRecoveryRouter` interface (no state-breaking redeployment).

---

## [Unreleased]

### Added
- Initial protocol specification
- Documentation structure

---

## [1.0.0] - 2026-03-16

### Added

#### Protocol Core
- Six-state failure and recovery state machine (IDLE, RUNNING, FAILED, RECOVERING, RESOLVED, DISPUTED)
- Three-class failure taxonomy (LIVENESS, RESOURCE, LOGIC)
- Deterministic recovery score algorithm
- Checkpoint-based task resumption protocol
- Permissionless enforcement functions (checkLiveness, checkBudget, checkDeadline)

#### Smart Contracts
- `CairnTask.sol` — Core state machine contract (~250 lines)
- `CairnHook.sol` — ERC-8183 hook implementation (~80 lines)
- `ICairnTask` interface
- `ICairnHook` interface

#### Standards Integration
- ERC-8183 integration via Hook interface
- ERC-8004 integration for identity and reputation
- ERC-7710 integration for caveat-enforced delegation

#### Execution Intelligence Layer
- Failure Record schema (v1)
- Resolution Record schema (v1)
- IPFS storage for execution records
- On-chain event emission for indexing

#### Documentation
- Protocol whitepaper
- ERC specification (EIP format)
- Security model documentation
- Architecture documentation
- Integration guides

### Standards

- Follows EIP-1 specification format
- Implements ERC-8183 Hook interface
- Compatible with ERC-8004 registries
- Compatible with ERC-7710 delegation

### Security

- Checkpoint schema validation
- Two-gate fallback admission (reputation + stake)
- Stake-based arbiter accountability
- Permissionless enforcement (no trusted keepers)

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-03-16 | Initial release |

---

## Upgrade Policy

- CairnTask.sol is non-upgradeable by design
- New versions are deployed as new contracts
- In-flight tasks complete under their original version
- No forced migration of existing tasks

## Migration Guides

Migration guides will be added here when new versions are released.

---

*CAIRN Protocol Changelog*
