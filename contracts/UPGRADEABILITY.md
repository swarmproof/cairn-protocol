# CAIRN Protocol - UUPS Upgradeability Guide

> **PRD-06 Implementation**: Complete guide to CAIRN's upgradeable contract architecture

## Overview

All CAIRN Protocol contracts implement the **UUPS (Universal Upgradeable Proxy Standard)** pattern using OpenZeppelin's battle-tested upgradeable contracts library. This allows the protocol to evolve while preserving user funds and state.

### Why UUPS?

- **Gas Efficient**: Upgrade logic lives in implementation, not proxy
- **Secure**: Upgrade authorization built into each contract
- **Clean**: Single proxy pattern, no admin/implementation slot confusion
- **Battle-Tested**: OpenZeppelin standard used by major protocols

## Architecture

### Contract Structure

```
┌─────────────────────────────────────────────┐
│           User / Frontend                    │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         ERC1967Proxy (Immutable)             │
│  • Delegates all calls to implementation     │
│  • Stores implementation address            │
│  • Never changes after deployment           │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│   CairnCoreUpgradeable (Implementation)      │
│  • Contains all logic                        │
│  • Can be replaced via upgrade              │
│  • Inherits: Initializable, UUPSUpgradeable │
└─────────────────────────────────────────────┘
```

### Upgradeable Contracts

| Contract | Proxy | Implementation | Owner |
|----------|-------|----------------|-------|
| CairnCore | ERC1967Proxy | CairnCoreUpgradeable | Governance |
| FallbackPool | ERC1967Proxy | FallbackPoolUpgradeable | Admin/Multisig |
| ArbiterRegistry | ERC1967Proxy | ArbiterRegistryUpgradeable | Admin/Multisig |
| RecoveryRouter | ERC1967Proxy | RecoveryRouterUpgradeable | Admin/Multisig |

**Non-Upgradeable:**
- `CairnGovernance` - Governance logic should be immutable for security

## Deployment

### Initial Deployment

```bash
# Set environment variables
export PRIVATE_KEY="0x..."
export FEE_RECIPIENT="0x..."
export BASE_SEPOLIA_RPC_URL="https://..."

# Deploy all contracts
forge script script/DeployUpgradeable.s.sol:DeployUpgradeable \
  --rpc-url $BASE_SEPOLIA_RPC_URL \
  --broadcast \
  --verify

# Deployment addresses saved to:
# ./deployments/{chainId}-upgradeable.json
```

### Deployment Order

1. **CairnGovernance** (non-upgradeable)
2. **RecoveryRouter** (implementation + proxy)
3. **FallbackPool** (implementation + proxy)
4. **ArbiterRegistry** (implementation + proxy)
5. **CairnCore** (implementation + proxy)
6. **Configure references** (setCairnCore on each)

### Deployment Verification

```solidity
// Verify proxy points to implementation
address implementation = getImplementation(proxyAddress);
console.log("Implementation:", implementation);

// Verify initialization
CairnCoreUpgradeable core = CairnCoreUpgradeable(proxyAddress);
assert(core.feeRecipient() == expectedFeeRecipient);
assert(address(core.governance()) == expectedGovernance);
```

## Upgrades

### Upgrade Process (48-Hour Timelock)

Per PRD-06 Section 3.4, all upgrades require:
1. **Proposal** - Deploy new implementation
2. **Timelock** - 48-hour waiting period
3. **Execution** - Call `upgradeToAndCall()`

```bash
# Step 1: Deploy new implementation
export UPGRADE_CONTRACT="CairnCore"
export PROXY_ADDRESS="0x..." # From deployment JSON

forge script script/Upgrade.s.sol:Upgrade \
  --rpc-url $BASE_SEPOLIA_RPC_URL \
  --broadcast

# Step 2: Wait 48 hours (via governance timelock)

# Step 3: Execute upgrade (via governance)
# This happens automatically if using TimelockController
```

### Manual Upgrade (Testing Only)

```solidity
// Deploy new implementation
CairnCoreUpgradeable newImpl = new CairnCoreUpgradeable();

// Upgrade (only governance can call this)
CairnCoreUpgradeable(proxyAddress).upgradeToAndCall(
    address(newImpl),
    "" // Optional initialization data
);
```

### Upgrade Authorization

```solidity
// CairnCoreUpgradeable.sol
function _authorizeUpgrade(address newImplementation)
    internal
    override
    onlyGovernance
{}
```

Only the **governance contract** can authorize upgrades to CairnCore. This prevents:
- Unauthorized upgrades by malicious actors
- Accidental upgrades by admins
- Rug pulls by single key holders

## Storage Layout Safety

### ⚠️ CRITICAL RULES

1. **NEVER change the order of existing storage variables**
2. **NEVER change the type of existing storage variables**
3. **NEVER remove storage variables**
4. **ALWAYS add new variables at the end**
5. **ALWAYS use storage gaps (`__gap`) for future upgrades**

### Example: Safe Storage Evolution

```solidity
// V1
contract CairnCoreUpgradeable {
    mapping(bytes32 => Task) private _tasks;
    address public feeRecipient;
    uint256 public totalEscrowLocked;

    uint256[50] private __gap; // Reserve space for future variables
}

// V2 - SAFE ✅
contract CairnCoreUpgradeable {
    mapping(bytes32 => Task) private _tasks;      // Same position
    address public feeRecipient;                   // Same position
    uint256 public totalEscrowLocked;              // Same position

    // New variables at the end
    uint256 public newVariable;

    uint256[49] private __gap; // Reduced by 1
}

// V2 - UNSAFE ❌
contract CairnCoreUpgradeable {
    uint256 public newVariable;                    // DON'T DO THIS!
    mapping(bytes32 => Task) private _tasks;       // Position changed
    address public feeRecipient;                   // Position changed
}
```

### Storage Gap Usage

Each upgradeable contract reserves 50 storage slots:

```solidity
uint256[50] private __gap;
```

**Purpose**: Allow adding up to 50 new state variables in future upgrades without breaking existing storage layout.

**Rule**: When adding N new variables, reduce gap by N:
```solidity
// Added 3 new variables
uint256 public var1;
uint256 public var2;
address public var3;
uint256[47] private __gap; // Was 50, now 47
```

## Testing Upgrades

### Test Suite Structure

```
contracts/test/upgrades/
├── CairnCoreUpgrade.t.sol        # CairnCore upgrade tests
├── FallbackPoolUpgrade.t.sol      # FallbackPool upgrade tests
├── ArbiterRegistryUpgrade.t.sol   # ArbiterRegistry upgrade tests
└── RecoveryRouterUpgrade.t.sol    # RecoveryRouter upgrade tests
```

### Run Upgrade Tests

```bash
# Run all upgrade tests
forge test --match-path "test/upgrades/*.sol" -vv

# Run specific contract upgrade tests
forge test --match-path "test/upgrades/CairnCoreUpgrade.t.sol" -vvv

# Test with gas reporting
forge test --match-path "test/upgrades/*.sol" --gas-report
```

### Test Coverage Requirements

Per PRD-06 Section 4.3:

| Test Category | Coverage Target |
|--------------|-----------------|
| State preservation | 100% |
| Authorization checks | 100% |
| Functionality post-upgrade | >95% |
| Multiple upgrade cycles | 100% |

### Example Test

```solidity
function test_StatePreservedAfterUpgrade() public {
    // Submit task before upgrade
    bytes32 taskId = cairnCore.submitTask{value: 0.01 ether}(...);

    // Verify state before
    uint256 escrowBefore = cairnCore.totalEscrowLocked();

    // Perform upgrade
    CairnCoreUpgradeable newImpl = new CairnCoreUpgradeable();
    cairnCore.upgradeToAndCall(address(newImpl), "");

    // Verify state after
    assertEq(cairnCore.totalEscrowLocked(), escrowBefore);

    // Verify task data intact
    ICairnCore.Task memory task = cairnCore.getTask(taskId);
    assertEq(task.escrowAmount, 0.01 ether);
}
```

## Security Considerations

### Upgrade Authorization

```solidity
// ✅ SECURE: Only governance can upgrade
function _authorizeUpgrade(address) internal override onlyGovernance {}

// ❌ INSECURE: Anyone can upgrade
function _authorizeUpgrade(address) internal override {}

// ❌ INSECURE: Single admin can upgrade
function _authorizeUpgrade(address) internal override onlyOwner {}
```

### Initialization Safety

```solidity
// ✅ Disable initializers in implementation constructor
/// @custom:oz-upgrades-unsafe-allow constructor
constructor() {
    _disableInitializers();
}

// ✅ Use initializer modifier
function initialize(...) external initializer {
    __UUPSUpgradeable_init();
    __ReentrancyGuard_init();
    // ...
}
```

### Selfdestruct Protection

**NEVER use `selfdestruct` in upgradeable contracts**. It can brick the proxy permanently.

```solidity
// ❌ DON'T DO THIS
function emergencyExit() external onlyOwner {
    selfdestruct(payable(owner())); // NEVER DO THIS
}
```

## Governance Integration

### Timelock Flow

```
1. Admin proposes upgrade
   ↓
2. Deploy new implementation
   ↓
3. Queue upgrade in TimelockController
   ↓
4. Wait 48 hours (PRD-06 requirement)
   ↓
5. Execute upgrade
   ↓
6. New implementation active
```

### Example: Propose Upgrade via Governance

```solidity
// 1. Deploy new implementation
address newImpl = address(new CairnCoreUpgradeable());

// 2. Encode upgrade call
bytes memory upgradeData = abi.encodeCall(
    UUPSUpgradeable.upgradeToAndCall,
    (newImpl, "")
);

// 3. Schedule via timelock
timelock.schedule(
    proxyAddress,      // target
    0,                 // value
    upgradeData,       // data
    bytes32(0),        // predecessor
    bytes32(0),        // salt
    48 hours           // delay
);

// 4. After 48 hours, execute
timelock.execute(
    proxyAddress,
    0,
    upgradeData,
    bytes32(0),
    bytes32(0)
);
```

## Emergency Procedures

### Emergency Pause

If a critical bug is found before upgrade can be deployed:

```solidity
// Governance can pause the protocol
cairnCore.pause();

// All state-changing functions will revert
// Users can still read data
```

### Rollback (Not Recommended)

UUPS doesn't support rollback by default. Instead:

1. **Fix the bug** in a new implementation
2. **Deploy** the fixed version
3. **Upgrade** to the fixed implementation

**Never** try to "rollback" to old implementation - state may be corrupted.

## Tools & Commands

### Get Current Implementation

```bash
# Using cast
cast implementation <PROXY_ADDRESS> --rpc-url $RPC_URL

# Output: 0x... (current implementation address)
```

### Verify Upgrade

```bash
# Verify implementation on Etherscan/Basescan
forge verify-contract <IMPLEMENTATION_ADDRESS> \
  src/upgradeable/CairnCoreUpgradeable.sol:CairnCoreUpgradeable \
  --chain base-sepolia
```

### Storage Layout Analysis

```bash
# Generate storage layout report
forge inspect CairnCoreUpgradeable storage-layout --pretty
```

## Checklist: Before Mainnet Upgrade

- [ ] New implementation deployed and verified
- [ ] Storage layout validated (no conflicts)
- [ ] Unit tests pass (>95% coverage)
- [ ] Upgrade tests pass (100% state preservation)
- [ ] Fuzz tests pass
- [ ] Gas report reviewed (no major increases)
- [ ] Audit complete (if significant changes)
- [ ] Governance proposal created
- [ ] Timelock configured (48 hours)
- [ ] Emergency pause plan ready
- [ ] Monitoring alerts configured

## References

- [OpenZeppelin UUPS Docs](https://docs.openzeppelin.com/contracts/4.x/api/proxy#UUPSUpgradeable)
- [EIP-1822: UUPS Standard](https://eips.ethereum.org/EIPS/eip-1822)
- [EIP-1967: Proxy Storage Slots](https://eips.ethereum.org/EIPS/eip-1967)
- [CAIRN PRD-06](../PRDs/PRD-06-FULL-INTEGRATION/PRD.md)

## Support

For upgrade-related questions:
- Discord: `#dev-upgrades`
- GitHub Issues: Tag with `upgrade` label
- Email: security@cairn.io (for critical issues)

---

**Remember**: With great power comes great responsibility. Upgrades are powerful but dangerous. Always test thoroughly before mainnet deployment.
