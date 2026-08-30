# CAIRN Protocol — Claude Code Instructions

> **CRITICAL**: These rules are MANDATORY for ALL agents and builds. No exceptions.
>
> Sections 0–10 below are the **governance/process charter** (audit gates, logging,
> deployment, git). The **Orientation** section immediately below is the practical
> map of the repo: how to build, test, and where the code lives. Read Orientation
> first when you start work; obey Sections 0–10 before you commit or deploy.

---

## Orientation — Build, Test & Architecture

### What this repo is

CAIRN is a **standardized agent failure-and-recovery protocol** on Base Sepolia
(Chain ID 84532). A task moves through a six-state machine (`IDLE → RUNNING →
FAILED → RECOVERING/DISPUTED → RESOLVED`); when an agent fails, the protocol
classifies the failure, scores recoverability, assigns a fallback agent that
resumes from the last checkpoint, and settles escrow proportionally. Deep
background lives in `README.md`, `WHITEPAPER_V2.md`, and `docs/`.

It is a **polyglot monorepo** — Solidity contracts, a Python SDK + CLI, a Next.js
frontend, a Graph subgraph, an off-chain event pipeline, and a Monte Carlo
simulation — each with its own toolchain.

### v1 vs v2 — v2 is live

**v2 is deployed and activated on Base Sepolia.** The live stack runs
`RecoveryRouterV2` (the **multiplicative** formula `r = F^0.80 · B^0.35 · D^0.15`
with three-tier routing) wired into `CairnCore` with `threeTierRoutingEnabled = true`.
The earlier **v1 interim-linear** router (`r = 0.5·F + 0.3·B + 0.2·D`, single 0.30
threshold) still exists in-repo (`RecoveryRouter.sol`) and behind the
`IRecoveryRouter` interface, but it is superseded. When older docs or comments
imply "v1 is what's deployed / v2 is only a spec", they are stale — v2 is live.
See `PRDs/PRD-04-V2-UPGRADE/PRD.md`.

> Note: the audited security fixes (PRs #46–#59) are on `main` but **not yet
> redeployed** — the currently-live addresses run the pre-audit code until the
> redeploy (see `docs/v2-deployment-runbook.md`).

### Component map

| Path | Stack | What it is |
|------|-------|-----------|
| `contracts/` | Solidity 0.8.24, Foundry | Protocol contracts + interfaces. Deps are **git submodules** (`lib/`). |
| `sdk/` | Python 3.10+ | `CairnClient`, `CairnAgent`, `CheckpointStore`, observers. Published as `cairn-sdk`. |
| `cli/` | Python 3.10+, Click | `cairn` command (`task`, `agent`, `pool`, `intel`, `admin` subcommands). Entry point `cli.main:main`. |
| `frontend/` | Next.js 14 (App Router), wagmi 2.x, TypeScript, **pnpm** | Dashboard. Live on Vercel. |
| `subgraph/` | The Graph, AssemblyScript, **pnpm** | Indexes on-chain events → execution intelligence. |
| `pipeline/` | Python | Off-chain event listener → IPFS records → Bonfires graph. |
| `simulation/` | Python, NumPy | Monte Carlo recovery-score calibration (derived the v2 formula). |
| `PRDs/` | — | Source-of-truth product specs. See Section 4 for the reference hierarchy. |

### Contracts (Foundry)

`contracts/` holds six core contracts — `CairnCore` (entry point, state machine),
`CairnGovernance`, `RecoveryRouter` (+ `RecoveryRouterV2`), `FallbackPool`,
`ArbiterRegistry` — plus `CairnTaskMVP` (legacy 4-state, do not extend),
`adapters/OlasMechAdapter.sol`, `interfaces/` (the API contracts, including the
external `IERC8183`/`IERC8004`/`IERC7710` standards CAIRN integrates), and
`upgradeable/` UUPS variants (OpenZeppelin 5.x proxy pattern).

```bash
# First checkout — submodules are REQUIRED (OZ, forge-std, OZ-upgradeable, prb-math)
git submodule update --init --recursive   # or: cd contracts && forge install

cd contracts
forge build --sizes                # compile + contract size check
forge test -vvv                    # full suite
forge test --match-test testSubmitTask   # single test by name
forge test --match-contract CairnCoreTest # single test contract
forge coverage                     # must be ≥95% (see Section 0)
forge test --gas-report            # gas analysis
forge fmt                          # formatter (config in foundry.toml)
```

> CI (`.github/workflows/tests.yml`) runs **only** `forge test` in `contracts/`
> with recursive submodules. Python/frontend/subgraph are not yet in CI — run
> their tests locally before committing.

### Python (SDK, CLI, pipeline, simulation)

Two `pyproject.toml` files exist: the **root** one (package `cairn-protocol`,
installs `sdk`+`cli`, provides the `cairn` script) and **`sdk/pyproject.toml`**
(the standalone `cairn-sdk` package, hatchling). Install for development:

```bash
pip install -e ".[dev]"     # root: SDK + CLI + dev tools (pytest, black, ruff, mypy)
pip install -e ./sdk        # or just the SDK
```

> **Local import gotcha:** in-repo the SDK is imported as `from sdk import
> CairnClient, CairnAgent, CheckpointStore` (see `sdk/__init__.py`). The README's
> `from cairn_sdk import ...` refers to the *published* package name — it will
> `ModuleNotFoundError` against a source checkout.

```bash
# Root pytest config (pyproject.toml) targets the top-level tests/ dir,
# covering sdk + cli, and writes HTML coverage to htmlcov/.
pytest                              # runs tests/ with coverage (per addopts)
pytest tests/test_client.py -v     # one file
pytest tests/test_client.py::test_submit_task   # one test
pytest sdk/tests/ -v               # the SDK's own test suite (separate dir)
python -m pytest pipeline/tests/   # pipeline tests

black . && ruff check . && mypy sdk cli   # format + lint + typecheck (line length 100)

# Reproduce the headline simulation result (deterministic, seed=42)
python3 -m simulation.run_eq4
```

### Frontend & subgraph (Node, pnpm)

```bash
cd frontend && pnpm install
pnpm dev            # local dev server
pnpm build          # production build
pnpm lint           # next lint / eslint

cd subgraph && pnpm install
pnpm codegen        # generate types from schema + ABIs (run after schema/ABI changes)
pnpm build
pnpm test           # matchstick-as unit tests
```

### Where to look first

- Protocol behavior / spec of a feature → `PRDs/PRD-XX-*/PRD.md` (see Section 4).
- Contract API shape → `contracts/src/interfaces/`.
- Current decisions / session state → `.planning/SESSION_CONTEXT.md`.
- Deployed addresses → `README.md` "Deployed Contracts" table.

---

## 0. MANDATORY VALIDATION GATE

### Before ANY Deployment or Feature Completion

**RULE**: Every feature MUST be audited against ALL project docs and requirements before:
- Marking a feature as complete
- Deploying to any network (testnet or mainnet)
- Creating a pull request

### Audit Checklist (REQUIRED)

```
[ ] PRD COMPLIANCE AUDIT
    - Read the relevant PRD (PRDs/PRD-XX-*/PRD.md)
    - Verify ALL sub-features (SF-XX) are implemented correctly
    - Verify ALL acceptance criteria (AC-XX) pass
    - Verify ALL edge cases (EC-XX) are handled
    - Verify ALL function signatures match PRD exactly
    - Verify ALL events match PRD definitions
    - Verify ALL errors match PRD definitions

[ ] SECURITY AUDIT
    - No reentrancy vulnerabilities (use ReentrancyGuard)
    - CEI pattern followed (Checks-Effects-Interactions)
    - Access control on all state-changing functions
    - No unchecked external calls
    - Input validation on all public functions
    - No hardcoded secrets or sensitive data

[ ] TEST COVERAGE AUDIT
    - Minimum 95% line coverage achieved
    - All happy paths tested
    - All revert conditions tested
    - All edge cases from PRD tested
    - Run: forge test -vvv && forge coverage

[ ] GAS ANALYSIS
    - Gas report generated: forge test --gas-report
    - Compare against PRD performance targets
    - Document any deviations with justification

[ ] DOCUMENTATION SYNC
    - Interface matches implementation
    - NatSpec comments accurate
    - README/docs updated if needed
```

### Audit Output Format

Every audit MUST produce a report containing:
- Total items checked
- Pass/Fail status for each category
- Security issues found (MUST be 0 for deployment)
- Warnings with justifications
- **Verdict**: `READY_FOR_DEPLOYMENT` or `BLOCKED`

### Audit Commands

```bash
# Full test suite
forge test -vvv

# Coverage report
forge coverage

# Gas report
forge test --gas-report

# Build with size check
forge build --sizes
```

---

## 1. DEPLOYMENT RULES

### 1.1 Who Deploys

| Network | Who Deploys | Agent Role |
|---------|-------------|------------|
| **Testnet** | USER ONLY | Prepare, audit, provide instructions |
| **Mainnet** | USER ONLY | NEVER deploy to mainnet |

### 1.2 Pre-Deployment Validation

Before giving deployment instructions:
1. Complete FULL audit checklist above
2. Run all tests: `forge test`
3. Run coverage: `forge coverage` (must be ≥95%)
4. Run gas report: `forge test --gas-report`

### 1.3 Post-Deployment Checklist

After deployment completes:
```
[ ] contracts/.env
    - Add CAIRN_CONTRACT_ADDRESS

[ ] README.md "Deployed Contracts" table
    - Add/update the address, chain, and BaseScan link

[ ] PRD STATUS.md files
    - Mark deployment tasks as complete
```

---

## 2. CODE QUALITY GATES

### 2.1 Never Work Around Bugs

- Fix bugs properly at the source
- No temporary fixes or hacks
- No "TODO: fix later" that skips validation
- If a test fails, fix the code or test - NEVER skip

### 2.2 Pre-Commit Checklist

Before ANY commit:
```
[ ] All existing tests pass
[ ] New tests written for new functionality
[ ] Code compiles without warnings
[ ] No security vulnerabilities introduced
[ ] Feature matches PRD specification
```

### 2.3 Test Requirements

Every feature MUST have:
- Unit tests for all public functions
- Revert tests for all error conditions
- Integration tests for multi-step workflows
- Edge case tests per PRD section 2.8

---

## 3. PROGRESS TRACKING

Progress is tracked through standard mechanisms — no external logging system:

- **Git history + PRs** are the durable record of what was done and why.
- **PRD `STATUS.md`** files track task completion within each PRD.
- **`.planning/`** (git-ignored, local only) holds in-flight session context.

There is no `.synthesis/` submission log anymore — the hackathon phase is over.
Do not recreate it.

---

## 4. DOCUMENTATION REFERENCE HIERARCHY

When implementing features, consult in this order:

1. **PRD** (`/PRDs/PRD-XX-*/PRD.md`) — Primary source of truth
2. **Interfaces** (`/contracts/src/interfaces/`) — API contracts
3. **SESSION_CONTEXT** (`.planning/SESSION_CONTEXT.md`) — Current decisions
4. **Existing code** — Follow established patterns

### Required PRD Sections to Verify

| PRD Section | What to Check |
|-------------|---------------|
| Section 2 | Features & Functionality (sub-features SF-XX) |
| Section 2.8 | Edge Cases (EC-XX) |
| Section 5 | API Contracts (function signatures) |
| Section 8 | Test Cases (acceptance criteria AC-XX) |
| Section 9 | Security Constraints |
| Section 10 | Performance targets |

---

## 5. SPAWNING SUBAGENTS

When delegating work to a subagent:
1. Verify any prerequisite work is complete and its audit has passed.
2. Verify dependencies are met (e.g., contract deployed before SDK work that needs the address).
3. Include full context in the spawn prompt — the relevant PRD, interfaces, and current state.

The layered dependency order still holds: contracts → SDK → CLI/frontend → integration.
Don't start work that depends on an unfinished layer.

---

## 6. GIT WORKFLOW

- Branch naming: `claude/feature-name`
- Only commit/push when feature is **fully implemented AND tested**
- **Progressive commits** - one logical change per commit, never batch multiple changes
- Keep `.planning/` local (never push)
- Don't push PRD-02 through PRD-07 until MVP complete

### 6.0 Co-Author Attribution (REQUIRED)

**ALL commits MUST include the following co-author:**

```
Co-Authored-By: Lagartha <ionanova22@gmail.com>
```

Example commit format:
```bash
git commit -m "feat(scope): description

Co-Authored-By: Lagartha <ionanova22@gmail.com>"
```

### 6.1 Phase Completion Workflow (MANDATORY)

> ⚠️ **CRITICAL**: NEVER move to the next phase/branch until this workflow is complete.

When a feature/phase is **fully implemented and tested** (unit, integration, E2E):

```
1. AUDIT
   [ ] Run audit against PRD requirements (Section 0 checklist)
   [ ] Verify docs are consistent with implementation

2. PUSH BRANCH
   [ ] Ensure all commits are progressive and atomic
   [ ] Push branch to remote: git push -u origin branch-name

3. CREATE PR
   [ ] Create PR with clear description
   [ ] Reference completed PRD tasks
   [ ] Include test coverage stats
   [ ] Link to relevant documentation

4. THEN (and only then) MOVE TO NEXT PHASE
   [ ] Create new branch for next phase
   [ ] Begin next phase work
```

**Why this matters**: PRs provide review checkpoints, audit trails, and enable rollback if issues are found later.

### 6.3 Progressive Commit Rule

**NEVER batch multiple unrelated changes into one commit.** Each commit should be:
- One logical unit of work
- Independently reviewable
- Atomic (can be reverted without breaking other changes)

Example of correct progressive commits:
```
feat(contracts): add deployment records for Base Sepolia
docs(rules): add validation gates and security rules
docs(prd-01): update status to Phase 1 complete
```

Example of INCORRECT batching:
```
feat: add deployment, logs, rules, and status updates  ❌ TOO BROAD
```

### No AI Attribution

- No "Generated with Claude" in commits
- No "Co-Authored-By: Claude" in PRs
- Write as human developer

---

## 7. SECURITY NON-NEGOTIABLES

### Smart Contract Security

- ALWAYS use ReentrancyGuard for ETH transfers
- ALWAYS use custom errors (not require strings)
- ALWAYS validate all inputs
- NEVER use `transfer()` - use `call{value:}()`
- NEVER store secrets in code or comments

### Key Management

- NEVER generate or store private keys
- NEVER commit .env files
- NEVER log sensitive data in ANY tracked file — code, comments, STATUS.md,
  documentation, or local `.planning/` notes
- Only USER handles deployment credentials

**Safe to log**: Contract addresses, tx hashes, block numbers, gas amounts, public addresses
**NEVER log**: Private keys, API keys, passwords, mnemonics, secrets

---

## 8. CONTEXT FILES

### Read in Order for Session Recovery

1. `.planning/SESSION_CONTEXT.md` — current decisions and in-flight state (local, git-ignored)
2. The relevant `PRDs/PRD-XX-*/PRD.md` and its `STATUS.md` — requirements and task status
3. `README.md` + `WHITEPAPER_V2.md` — protocol overview and spec
4. The **Orientation** section at the top of this file — build/test commands and layout

### Quick Reference

| What | Where |
|------|-------|
| Current session state | `.planning/SESSION_CONTEXT.md` (local) |
| Requirements | `PRDs/PRD-XX-*/PRD.md` |
| Task status | `PRDs/PRD-XX-*/STATUS.md` |
| Deployed addresses | `README.md` "Deployed Contracts" table |
| Contract API | `contracts/src/interfaces/` |

---

## 9. CODE STANDARDS

- **Solidity**: 0.8.24+, custom errors, CEI pattern, natspec
- **Python**: 3.10+, type hints, async/await
- **Frontend**: Next.js 14, wagmi 2.x, TypeScript

---

## 10. SESSION RECOVERY

If session fails:
1. Read `.planning/SESSION_CONTEXT.md` and the relevant PRD `STATUS.md`
2. Check `git log` and open PRs for the last completed work
3. Continue from the last completed task
4. **Re-run audit** if mid-feature

---

**REMEMBER**: These validation rules exist to keep CAIRN audit-clean and safe to deploy. Clean audits, PRD compliance, and progressive commits are REQUIREMENTS, not suggestions.
