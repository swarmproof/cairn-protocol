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

### ⚠️ v1 (deployed) vs v2 (spec) — do not conflate

The contracts **deployed on Base Sepolia implement the interim linear** recovery
formula `r = 0.5·F + 0.3·B + 0.2·D` with a single 0.30 routing threshold. The
whitepaper/README describe the **v2 multiplicative** formula `r = F^0.80 · B^0.35
· D^0.15` with three-tier routing — that lives only in `RecoveryRouterV2.sol`
(not deployed) and migrates via governance through the `IRecoveryRouter`
interface. When code and docs disagree on the formula, this is why. See
`PRDs/PRD-04-V2-UPGRADE/PRD.md`.

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
- Spawning the next agent phase

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
5. Update `.synthesis/agent_log.json` with audit results

### 1.3 Post-Deployment Checklist

After deployment completes:
```
[ ] .synthesis/agent_log.json
    - Add "contract_deployed" entry with address, chain, gas
    - Add "contract_verified" entry if verified
    - Update "deployment" object with full details
    - Update "deliverables" statuses to "deployed"
    - Update "team_status" to unblock next phase
    - Set "next_step" to next action

[ ] .synthesis/agent.json
    - Add deployment info to Contract-Dev role
    - Update Contract-Dev status to "completed"
    - Update SDK-Dev status to "ready"
    - Add contract_address at root level

[ ] .planning/AGENT_LOG.md
    - Add deployment entry with timestamp

[ ] contracts/.env
    - Add CAIRN_CONTRACT_ADDRESS

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
[ ] Hackathon logs updated (.synthesis/agent_log.json)
```

### 2.3 Test Requirements

Every feature MUST have:
- Unit tests for all public functions
- Revert tests for all error conditions
- Integration tests for multi-step workflows
- Edge case tests per PRD section 2.8

---

## 3. HACKATHON LOGGING (REQUIRED)

This project is submitted to **Synthesis Hackathon 2026** and will be **judged by AI agents**.

> ⚠️ **CRITICAL REMINDER**: `.synthesis/agent_log.json` is the SOURCE OF TRUTH for judges.
>
> **ALWAYS update it IMMEDIATELY after**: deployments, audits, phase completions, errors.
>
> The markdown log (`.planning/AGENT_LOG.md`) is for humans. The JSON log is for judges.
>
> 🔒 **NEVER LOG SECRETS**: No private keys, API keys, passwords, or sensitive credentials in ANY log file.

### 3.1 Mandatory Log Updates

Update `.synthesis/agent_log.json` after:
- Branch created/merged
- Feature implemented
- Tests passed/failed
- **Audit completed** (with full results)
- Build completed
- Deployment done
- PR created/merged
- Any error or blocker

### 3.2 Log Entry Format

```json
{
  "timestamp": "ISO-8601",
  "phase": "contract-dev|sdk-dev|frontend-dev|integration",
  "action": "what_was_done",
  "status": "completed|in_progress|failed",
  "details": { "relevant": "metadata" }
}
```

> 🔒 **SECURITY**: Never include private keys, API keys, or secrets in log entries.
> Safe: `"address": "0x..."`, `"tx_hash": "0x..."`, `"chain_id": 84532`
> FORBIDDEN: `"private_key": "..."`, `"api_key": "..."`, `"password": "..."`

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

## 5. AGENT TEAM COORDINATION

### 5.1 Team Structure

```
Lead (Orchestrator)
├── Contract-Dev    → Phase 1: Tasks 1-8
├── SDK-Dev         → Phase 2: Tasks 9-14 (blocked by Contract-Dev)
├── Frontend-Dev    → Phase 3: Tasks 15-22 (blocked by SDK-Dev)
└── Integration     → Phase 4: Tasks 23-26 (blocked by all above)
```

### 5.2 Phase Handoff Protocol

When completing a phase:
1. **Complete audit** with full checklist
2. Update **BOTH** log files:
   - `.synthesis/agent_log.json` ← SOURCE OF TRUTH (for judges)
   - `.synthesis/agent.json` ← Team status & deployment info
   - `.planning/AGENT_LOG.md` ← Human-readable history
3. Update `team_status` to unblock next agent
4. Document any deviations from PRD
5. List dependencies for next phase

### 5.3 Spawning Rules

Before spawning a teammate agent:
1. Verify previous phase audit is COMPLETE
2. Verify dependencies are met (e.g., contract deployed)
3. Include full context in spawn prompt
4. Reference relevant PRD spawn file

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
   [ ] Update .synthesis/agent_log.json with audit results

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
   [ ] Update team_status in agent_log.json
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
docs(synthesis): add hackathon logs with deployment status
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
- NEVER log sensitive data in ANY file including:
  - `.synthesis/agent_log.json`
  - `.synthesis/agent.json`
  - `.planning/AGENT_LOG.md`
  - Any STATUS.md or documentation
- Only USER handles deployment credentials

**Safe to log**: Contract addresses, tx hashes, block numbers, gas amounts, public addresses
**NEVER log**: Private keys, API keys, passwords, mnemonics, secrets

---

## 8. CONTEXT FILES

### Read in Order for Session Recovery

1. `.planning/SESSION_CONTEXT.md` — Full rules and current state
2. `.synthesis/agent_log.json` — Action history for judges
3. `.planning/mvp/STATUS.md` — Task tracking
4. `/PRDs/PRD-01-MVP-HACKATHON/PRD.md` — Full requirements

### Quick Reference

| What | Where |
|------|-------|
| Full Context | `.planning/SESSION_CONTEXT.md` |
| Hackathon Logs | `.synthesis/agent_log.json` |
| Agent Metadata | `.synthesis/agent.json` |
| Task Status | `.planning/mvp/STATUS.md` |
| PRD | `/PRDs/PRD-01-MVP-HACKATHON/PRD.md` |
| Contract Spawn | `/PRDs/PRD-01-MVP-HACKATHON/spawn-contract-dev.md` |
| SDK Spawn | `/PRDs/PRD-01-MVP-HACKATHON/spawn-sdk-dev.md` |
| Frontend Spawn | `/PRDs/PRD-01-MVP-HACKATHON/spawn-frontend-dev.md` |

---

## 9. CODE STANDARDS

- **Solidity**: 0.8.24+, custom errors, CEI pattern, natspec
- **Python**: 3.10+, type hints, async/await
- **Frontend**: Next.js 14, wagmi 2.x, TypeScript

---

## 10. SESSION RECOVERY

If session fails:
1. Read `.planning/SESSION_CONTEXT.md`
2. Check `.synthesis/agent_log.json` for last action
3. Update logs with recovery entry
4. Continue from last completed task
5. **Re-run audit** if mid-feature

---

**REMEMBER**: These validation rules exist because this project will be judged by AI agents. Clean audits, PRD compliance, and proper logging are REQUIREMENTS, not suggestions.
