# Olas Mech Marketplace Integration for CAIRN Protocol

**Status**: Implementation Complete
**PRD Reference**: PRD-04 Section 2.7
**Date**: 2026-03-21

## Overview

This document describes the Olas Mech Marketplace adapter implementation for CAIRN Protocol, enabling CAIRN to query and utilize Olas Mechs as external fallback agents.

## Architecture

### Component Hierarchy

```
FallbackPool (Enhanced)
    │
    ├── Internal Agent Pool (Existing)
    │   └── Registered CAIRN fallback agents
    │
    └── OlasMechAdapter (New)
        └── IOlasMech Registry (Gnosis Chain)
            └── 600+ Olas Mech agents
```

### Data Flow

```
1. Task needs fallback
   └─> FallbackPool.selectFallback(taskType, escrow)

2. Query internal pool
   └─> Evaluate registered CAIRN agents
   └─> Calculate selection score

3. Query Olas pool (via adapter)
   └─> OlasMechAdapter.queryAvailableMechs(taskType)
   └─> Map CAIRN task type → Olas capability
   └─> Filter by reputation & active status
   └─> Return eligible Olas mechs

4. Select best agent
   └─> Compare internal vs Olas scores
   └─> Return highest-scoring agent
```

## Implementation Details

### 1. Interface: IOlasMech.sol

**Location**: `/contracts/src/interfaces/IOlasMech.sol`

Defines the interface for interacting with the Olas Mech Registry on Gnosis Chain.

**Key Functions**:
- `getMech(uint256 serviceId)` - Get detailed mech information
- `getMechsByCapability(bytes32 capability)` - Query mechs by capability
- `isMechActive(uint256 serviceId)` - Check if mech is active
- `getMechAddress(uint256 serviceId)` - Get mech contract address
- `getMechPrice(uint256 serviceId)` - Get price per request

**MechInfo Struct**:
```solidity
struct MechInfo {
    address mechAddress;        // Contract address of the mech
    uint256 serviceId;          // Service ID in Olas registry
    bytes32[] capabilities;     // Task capabilities
    uint256 pricePerRequest;    // Cost per request (wei)
    bool active;                // Currently accepting requests
    uint256 requestsCompleted;  // Total successful requests
    uint256 requestsFailed;     // Total failed requests
}
```

### 2. Adapter: OlasMechAdapter.sol

**Location**: `/contracts/src/adapters/OlasMechAdapter.sol`

Bridges CAIRN task types with Olas Mech capabilities.

**Core Functionality**:

#### Task Type Mapping
Maps CAIRN's hierarchical task taxonomy to Olas service types:

```solidity
cairnToOlasCapability[keccak256("defi.price_fetch")] = keccak256("price_oracle");
cairnToOlasCapability[keccak256("defi.trade_execute")] = keccak256("trading_bot");
cairnToOlasCapability[keccak256("data.report_generate")] = keccak256("data_analyst");
```

**Default Mappings**:
| CAIRN Task Type | Olas Capability |
|-----------------|-----------------|
| `defi.price_fetch` | `price_oracle` |
| `defi.trade_execute` | `trading_bot` |
| `defi.liquidity_provide` | `liquidity_manager` |
| `data.report_generate` | `data_analyst` |
| `data.scrape_website` | `web_scraper` |
| `governance.vote_delegate` | `governance_agent` |
| `compute.model_inference` | `ai_inference` |

#### Eligibility Filtering
Olas mechs must meet criteria to be considered:
- **Active**: `isMechActive(serviceId) == true`
- **Reputation**: Success rate ≥ 70% (configurable)
  - Success rate = `requestsCompleted / (requestsCompleted + requestsFailed)`
- **Mapped**: Task type has valid Olas capability mapping

#### Admin Functions
- `mapTaskType(cairnType, olasCapability)` - Create new mappings
- `unmapTaskType(cairnType)` - Remove mappings
- `setMinReputation(newMin)` - Update reputation threshold
- `setEnabled(bool)` - Enable/disable Olas integration

### 3. Enhanced FallbackPool

**Location**: `/contracts/src/FallbackPool.sol`

Updated to integrate Olas Mech adapter into fallback selection.

**Changes**:

1. **New State Variable**:
```solidity
OlasMechAdapter public olasMechAdapter;
```

2. **Updated Constructor**:
```solidity
constructor(
    address _cairnCore,
    address _feeRecipient,
    address _reputationRegistry,
    address _delegationRegistry,
    address _olasMechAdapter  // New parameter
)
```

3. **Enhanced selectFallback()**:
```solidity
function selectFallback(bytes32 taskType, uint256 escrowAmount)
    external view returns (address bestAgent)
{
    // Step 1: Evaluate internal pool
    for (candidates in internalPool) {
        score = calculateScore(agent);
        if (score > bestScore) {
            bestScore = score;
            bestAgent = agent;
        }
    }

    // Step 2: Query Olas mechs (if adapter configured)
    if (olasMechAdapter != address(0)) {
        address[] memory olasMechs = olasMechAdapter.queryAvailableMechs(taskType);

        // Olas mechs get base score of 75 (assumed good reputation)
        for (olasMechs) {
            if (75 > bestScore) {
                bestScore = 75;
                bestAgent = olasMech;
            }
        }
    }

    return bestAgent;
}
```

4. **Admin Function**:
```solidity
function setOlasMechAdapter(address _olasMechAdapter) external {
    // Update or disable Olas integration
    olasMechAdapter = OlasMechAdapter(_olasMechAdapter);
}
```

### 4. Python SDK: olas.py

**Location**: `/sdk/cairn/olas.py`

Python client for querying and interacting with Olas Mechs.

**Key Classes**:

#### `MechInfo` Dataclass
```python
@dataclass
class MechInfo:
    mech_address: Address
    service_id: int
    capabilities: List[bytes]
    price_per_request: int
    active: bool
    requests_completed: int
    requests_failed: int

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
```

#### `OlasMechClient` Class
```python
class OlasMechClient:
    def __init__(self, rpc_url: str, registry_address: str):
        """Initialize client for Olas Mech Registry"""

    async def get_available_mechs(
        self, capability: str, min_reputation: float = 70.0
    ) -> List[MechInfo]:
        """Query available mechs for a capability"""

    async def get_mech_info(self, service_id: int) -> MechInfo:
        """Get detailed mech information"""

    async def is_mech_active(self, service_id: int) -> bool:
        """Check if mech is active"""

    @staticmethod
    def map_cairn_to_olas_capability(cairn_task_type: str) -> str:
        """Map CAIRN task type to Olas capability"""
```

**Usage Example**:
```python
from cairn.olas import OlasMechClient

# Initialize client for Gnosis Chain
client = OlasMechClient(
    rpc_url="https://gnosis-rpc.publicnode.com",
    registry_address="0x9338b5153AE39BB89f50468E608eD9d764B755fD"
)

# Query available price oracle mechs
mechs = await client.get_available_mechs("price_oracle", min_reputation=70.0)

for mech in mechs:
    print(f"Mech {mech.service_id}: {mech.success_rate:.1f}% success rate")
```

## Testing

### Solidity Tests

#### `OlasMechAdapter.t.sol`
Tests adapter functionality in isolation with mock registry.

**Test Coverage**:
- ✅ Default mappings initialized correctly
- ✅ Admin can map/unmap task types
- ✅ Query returns eligible mechs
- ✅ Inactive mechs filtered out
- ✅ Low reputation mechs filtered out
- ✅ Eligibility checks work correctly
- ✅ Admin functions require authorization
- ✅ Adapter can be enabled/disabled

#### `FallbackPoolOlas.t.sol`
Integration tests for FallbackPool with Olas adapter.

**Test Coverage**:
- ✅ Internal agents preferred over Olas (when eligible)
- ✅ Falls back to Olas when no internal agents
- ✅ Falls back to Olas when internal agents ineligible
- ✅ Combines internal + Olas pools for selection
- ✅ Handles Olas query failures gracefully
- ✅ Adapter can be updated or disabled

### Python Tests

#### `test_olas.py`
Unit tests for OlasMechClient SDK.

**Test Coverage**:
- ✅ Client initialization and connection
- ✅ Get mech information
- ✅ Query available mechs by capability
- ✅ Filter inactive mechs
- ✅ Filter low reputation mechs
- ✅ CAIRN to Olas capability mapping
- ✅ Success rate calculation
- ✅ Error handling for individual mech failures

**Run Tests**:
```bash
# Solidity tests
forge test --match-contract OlasMechAdapter
forge test --match-contract FallbackPoolOlas

# Python tests
pytest sdk/tests/test_olas.py -v
```

## Deployment

### Prerequisites
1. Olas Mech Registry deployed on Gnosis Chain: `0x9338b5153AE39BB89f50468E608eD9d764B755fD`
2. FallbackPool deployed on Base Sepolia
3. Admin account for adapter management

### Deployment Steps

1. **Deploy OlasMechAdapter**:
```solidity
OlasMechAdapter adapter = new OlasMechAdapter(
    olasMechRegistryAddress,  // Gnosis: 0x9338b5153AE39BB89f50468E608eD9d764B755fD
    adminAddress
);
```

2. **Update FallbackPool**:
```solidity
fallbackPool.setOlasMechAdapter(address(adapter));
```

3. **Configure Mappings** (optional - defaults already set):
```solidity
adapter.mapTaskType(
    keccak256("custom.task"),
    keccak256("custom_capability")
);
```

4. **Verify Integration**:
```solidity
address[] memory mechs = adapter.queryAvailableMechs(keccak256("defi.price_fetch"));
require(mechs.length > 0, "No Olas mechs found");
```

## Configuration

### Task Type Mappings

Admins can add custom mappings:

```solidity
// Add new mapping
adapter.mapTaskType(
    keccak256("nft.mint"),
    keccak256("nft_minter")
);

// Remove mapping
adapter.unmapTaskType(keccak256("nft.mint"));
```

### Reputation Threshold

Default: 70% success rate

```solidity
// Increase to 80%
adapter.setMinReputation(80);
```

### Enable/Disable Integration

```solidity
// Disable Olas integration
adapter.setEnabled(false);

// Re-enable
adapter.setEnabled(true);
```

## Security Considerations

### 1. Cross-Chain Risk
- Olas Registry is on Gnosis Chain
- CAIRN is on Base
- **Mitigation**: Adapter queries are read-only, no cross-chain execution

### 2. Centralization Risk
- Adapter has single admin
- **Mitigation**: Use multi-sig or DAO for admin in production

### 3. Oracle Risk
- Reputation data comes from Olas Registry
- **Mitigation**:
  - Minimum reputation threshold (70%)
  - Internal pool always evaluated first
  - Graceful fallback if Olas query fails

### 4. Gas Costs
- Querying Olas adds gas overhead
- **Mitigation**:
  - View function (no gas for selection)
  - Try/catch to prevent reverts
  - Can be disabled via `setEnabled(false)`

## Performance

### Gas Costs (Estimated)

| Operation | Gas Cost |
|-----------|----------|
| `queryAvailableMechs()` (3 mechs) | ~80,000 |
| `selectFallback()` (with Olas) | ~120,000 |
| `selectFallback()` (without Olas) | ~100,000 |
| `mapTaskType()` | ~50,000 |

### Query Latency

- **Gnosis RPC call**: ~100-500ms
- **Filtering logic**: ~1-10ms
- **Total**: ~100-500ms additional latency

## Olas Mech Marketplace Info

- **Gnosis Registry**: `0x9338b5153AE39BB89f50468E608eD9d764B755fD`
- **Documentation**: https://docs.autonolas.network/
- **Marketplace**: https://marketplace.olas.network/gnosis/ai-agents
- **Total Mechs**: 600+ active agents
- **Supported Chains**: Gnosis, Base, Polygon, Optimism

## Future Enhancements

1. **Dynamic Scoring**: Use actual Olas reputation data instead of fixed score
2. **Price Consideration**: Factor in `pricePerRequest` for selection
3. **Multi-Chain**: Support Olas mechs on Base, Polygon, Optimism
4. **Caching**: Cache Olas queries to reduce latency
5. **Monitoring**: Track Olas mech performance in CAIRN tasks

## References

- [Olas Documentation](https://docs.autonolas.network/)
- [Mech Client GitHub](https://github.com/valory-xyz/mech-client)
- [AI Registry Mech Contracts](https://github.com/valory-xyz/ai-registry-mech)
- [PRD-04: Fallback Ecosystem](/PRDs/PRD-04-FALLBACK-ECOSYSTEM/PRD.md)

## Sources

Implementation based on:
- [Olas Developer Documentation](https://docs.olas.network/)
- [Mech Marketplace](https://marketplace.olas.network/gnosis/ai-agents)
- [Olas GitHub (valory-xyz)](https://github.com/valory-xyz)
- [Code4rena 2026 Olas Audit](https://github.com/code-423n4/2026-01-olas)

---

*This documentation is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: CAIRN Protocol.*
