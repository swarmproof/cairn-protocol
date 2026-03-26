# CAIRN Protocol Multi-Sig Governance Setup

## Overview

The CAIRN Protocol uses a progressive governance model:

| Phase | Controller | Description |
|-------|-----------|-------------|
| **1. Launch** | Single EOA | Initial deployment (current) |
| **2. Multi-sig** | Gnosis Safe | Require M-of-N signatures |
| **3. Token** | DAO | Future token governance |

## Current Deployment

| Contract | Address | Admin |
|----------|---------|-------|
| CairnGovernance | `0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f` | Deployer |
| CairnCore | `0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640` | Governance |
| RecoveryRouter | `0xE52703946cb44c12A6A38A41f638BA2D7197a84d` | CairnCore |
| FallbackPool | `0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0` | CairnCore |
| ArbiterRegistry | `0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68` | CairnCore |

## Setting Up Multi-Sig Governance

### Step 1: Create Gnosis Safe on Base Sepolia

1. Go to [Safe App](https://app.safe.global/)
2. Connect wallet to **Base Sepolia**
3. Click "Create Safe"
4. Add signers (recommended: 2-of-3 or 3-of-5)
5. Set threshold (e.g., 2 signatures required)
6. Deploy the Safe

### Step 2: Transfer Admin to Safe

Execute this from the current admin wallet:

```solidity
// Using cast (Foundry)
cast send 0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f \
  "transferAdmin(address)" \
  <SAFE_ADDRESS> \
  --rpc-url https://sepolia.base.org \
  --private-key $DEPLOYER_PRIVATE_KEY
```

Or via script:

```solidity
// script/TransferToMultisig.s.sol
pragma solidity 0.8.24;

import "forge-std/Script.sol";
import "../src/CairnGovernance.sol";

contract TransferToMultisig is Script {
    function run() external {
        address safe = vm.envAddress("SAFE_ADDRESS");
        address governance = 0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f;

        vm.startBroadcast();
        CairnGovernance(governance).transferAdmin(safe);
        vm.stopBroadcast();
    }
}
```

### Step 3: Verify Transfer

```bash
cast call 0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f "admin()" --rpc-url https://sepolia.base.org
```

## Multi-Sig Operations

### Proposing Parameter Changes

All governance actions require multi-sig approval:

1. **Create Transaction** in Safe UI
2. **Target**: `0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f` (Governance)
3. **Function**: `proposeParameter(bytes32 key, uint256 value)`
4. **Wait for Signatures**: M-of-N signers approve
5. **Execute**: Submit to blockchain
6. **Timelock**: Wait 48 hours
7. **Execute Proposal**: Call `executeProposal(bytes32 key)`

### Available Parameters

| Key | Current | Range | Description |
|-----|---------|-------|-------------|
| `PROTOCOL_FEE_BPS` | 50 (0.5%) | 0-500 | Protocol fee |
| `ARBITER_FEE_BPS` | 300 (3%) | 100-1000 | Arbiter fee |
| `MIN_REPUTATION` | 50 | 0-100 | Min reputation score |
| `MIN_STAKE_PERCENT` | 10 | 1-50 | Min agent stake % |
| `MIN_ARBITER_STAKE_PERCENT` | 15 | 5-50 | Min arbiter stake % |
| `RECOVERY_THRESHOLD` | 0.3e18 | 0.1-0.9e18 | Recovery threshold |
| `DISPUTE_TIMEOUT` | 7 days | 1-30 days | Dispute timeout |
| `APPEAL_WINDOW` | 48 hours | 24-72 hours | Appeal window |
| `MIN_HEARTBEAT_INTERVAL` | 30 | 10-300 | Min heartbeat (sec) |

### Emergency Controls

**Emergency Pause** (immediate, no timelock):
```solidity
function emergencyPause(string calldata reason) external onlyAdmin
```

**Emergency Unpause**:
```solidity
function emergencyUnpause() external onlyAdmin
```

## Security Considerations

1. **Timelock**: All parameter changes have 48-hour delay
2. **Range Validation**: Parameters validated against predefined ranges
3. **Multi-sig**: Requires M-of-N signatures for any action
4. **Separation**: Governance controls parameters, not direct contract state

## Recommended Safe Configuration

For testnet (Base Sepolia):
- **Signers**: 2-3 team members
- **Threshold**: 2-of-3

For mainnet (future):
- **Signers**: 5-7 trusted parties
- **Threshold**: 3-of-5 or 4-of-7
- **Hardware wallets**: Required for all signers

## Verification Commands

```bash
# Check current admin
cast call 0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f "admin()" --rpc-url https://sepolia.base.org

# Check if paused
cast call 0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f "isPaused()" --rpc-url https://sepolia.base.org

# Get parameter value
cast call 0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f \
  "getParameter(bytes32)" \
  $(cast keccak "PROTOCOL_FEE_BPS") \
  --rpc-url https://sepolia.base.org
```

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
