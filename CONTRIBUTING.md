# Contributing to CAIRN Protocol

Thank you for your interest in contributing to CAIRN! We welcome contributions of all kinds — bug fixes, new features, documentation improvements, and ideas.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [License](#license)

---

## Code of Conduct

Be respectful, inclusive, and constructive. We're building infrastructure for the agent ecosystem — let's do it collaboratively.

---

## Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes
4. **Make your changes** with tests
5. **Submit a Pull Request**

---

## Development Setup

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [Foundry](https://book.getfoundry.sh/) | Latest | Smart contract development |
| [Python](https://python.org/) | 3.10+ | SDK and CLI |
| [Node.js](https://nodejs.org/) | 18+ | Frontend and subgraph |
| [pnpm](https://pnpm.io/) | 8+ | Package management |

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/cairn-protocol.git
cd cairn-protocol

# Install contract dependencies
cd contracts && forge install && cd ..

# Install Python SDK/CLI
pip install -e ./sdk
pip install -e .  # CLI

# Install frontend dependencies
cd frontend && pnpm install && cd ..

# Install subgraph dependencies
cd subgraph && pnpm install && cd ..
```

### Environment Setup

```bash
# Copy example env files
cp contracts/.env.example contracts/.env
cp frontend/.env.example frontend/.env.local

# Add your test private key (NEVER use mainnet keys)
# Edit contracts/.env and add DEPLOYER_PRIVATE_KEY
```

---

## Project Structure

```
cairn-protocol/
├── contracts/          # Solidity smart contracts (Foundry)
│   ├── src/           # Core contracts
│   ├── test/          # Foundry tests
│   └── script/        # Deployment scripts
├── sdk/               # Python SDK
│   ├── cairn_sdk/     # Main package
│   └── tests/         # pytest tests
├── cli/               # CLI commands (in root)
├── frontend/          # Next.js 14 dashboard
├── subgraph/          # The Graph indexer
├── pipeline/          # Off-chain event listener
├── docs/              # Technical documentation
└── PRDs/              # Product requirements
```

---

## Making Changes

### Branch Naming

```
feature/short-description    # New features
fix/issue-description        # Bug fixes
docs/what-changed           # Documentation
refactor/component-name     # Code restructuring
```

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples:**
```
feat(contracts): add merkle checkpoint batching
fix(sdk): handle timeout in heartbeat loop
docs(readme): update deployment addresses
test(contracts): add dispute resolution edge cases
```

---

## Code Style

### Solidity (contracts/)

- **Version:** 0.8.24+
- **Formatter:** `forge fmt`
- **Patterns:**
  - Use custom errors (not `require` strings)
  - Follow CEI pattern (Checks-Effects-Interactions)
  - Use `ReentrancyGuard` for external calls with ETH
  - Add NatSpec comments for public functions

```solidity
// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity ^0.8.24;

/// @notice Brief description
/// @param taskId The task identifier
/// @return success Whether the operation succeeded
function example(uint256 taskId) external returns (bool success) {
    // Checks
    if (taskId == 0) revert InvalidTaskId();

    // Effects
    tasks[taskId].status = Status.Running;

    // Interactions
    emit TaskStarted(taskId);
    return true;
}
```

### Python (sdk/, cli/)

- **Version:** 3.10+
- **Formatter:** `black` + `isort`
- **Type hints:** Required for all public functions
- **Docstrings:** Google style

```python
async def submit_task(
    self,
    task_type: str,
    budget_cap: float,
    deadline: int,
) -> Task:
    """Submit a new task to the CAIRN protocol.

    Args:
        task_type: Category of task (e.g., "defi.rebalance")
        budget_cap: Maximum budget in ETH
        deadline: Seconds until task expires

    Returns:
        Task object with ID and status

    Raises:
        InsufficientFundsError: If wallet balance < budget_cap
    """
```

### TypeScript (frontend/, subgraph/)

- **Formatter:** Prettier
- **Linter:** ESLint
- **Framework:** Next.js 14 App Router, wagmi 2.x

---

## Testing

### Smart Contracts

```bash
cd contracts

# Run all tests
forge test

# Run with verbosity
forge test -vvv

# Run specific test
forge test --match-test testSubmitTask

# Coverage report (must be ≥95%)
forge coverage

# Gas report
forge test --gas-report
```

### Python SDK

```bash
# Run pytest
python -m pytest sdk/tests/ -v

# With coverage
python -m pytest sdk/tests/ --cov=cairn_sdk
```

### Frontend

```bash
cd frontend
pnpm test        # Unit tests
pnpm test:e2e    # E2E tests (if available)
```

---

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally (`forge test`, `pytest`)
- [ ] Code is formatted (`forge fmt`, `black`)
- [ ] No linting errors
- [ ] Coverage maintained (≥95% for contracts)
- [ ] Documentation updated if needed

### PR Template

```markdown
## Summary
Brief description of changes (1-3 sentences)

## Changes
- Change 1
- Change 2

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed

## Related Issues
Fixes #123 (if applicable)
```

### Review Process

1. Submit PR against `main` branch
2. Automated checks run (tests, linting)
3. Maintainer reviews code
4. Address feedback if any
5. Squash and merge when approved

---

## License

**Important:** By contributing, you agree to license your contributions under the same license as the component you're modifying.

| Component | License | What This Means |
|-----------|---------|-----------------|
| `contracts/` | GPL-3.0-or-later | Contributions must be GPL-3.0 compatible |
| `sdk/`, `cli/` | Apache-2.0 | You grant patent rights to users |
| `subgraph/` | MIT | Most permissive, minimal restrictions |
| `frontend/` | AGPL-3.0-or-later | Network use triggers copyleft |
| `docs/` | CC BY 4.0 | Attribution required |

See [LICENSE](./LICENSE) for full details.

---

## Questions?

- **Issues:** Open a [GitHub issue](https://github.com/MarouaBoud/cairn-protocol/issues)
- **Discussions:** Start a discussion in the repo
- **Contact:** Reach out to the maintainers

Thank you for contributing to CAIRN!
