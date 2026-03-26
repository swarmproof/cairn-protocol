// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {OlasMechAdapter} from "../src/adapters/OlasMechAdapter.sol";
import {IOlasMech} from "../src/interfaces/IOlasMech.sol";

/// @title FallbackPoolOlasTest - Integration tests for FallbackPool with Olas Mech adapter
/// @notice Tests that FallbackPool correctly integrates with Olas Mech Marketplace
contract FallbackPoolOlasTest is Test {
    FallbackPool public pool;
    OlasMechAdapter public adapter;
    MockOlasMechRegistry public mockRegistry;

    address public cairnCore = address(0x1);
    address public feeRecipient = address(0x2);
    address public admin = address(0x3);
    address public agent1 = address(0x4);
    address public agent2 = address(0x5);

    // ERC-8004 and ERC-7710 mocks (zero addresses for now)
    address public mockERC8004 = address(0);
    address public mockERC7710 = address(0);

    // Task types
    bytes32 public constant PRICE_FETCH = keccak256("defi.price_fetch");
    bytes32 public constant TRADE_EXECUTE = keccak256("defi.trade_execute");

    // Olas capabilities
    bytes32 public constant PRICE_ORACLE = keccak256("price_oracle");
    bytes32 public constant TRADING_BOT = keccak256("trading_bot");

    function setUp() public {
        // Deploy mock Olas registry
        mockRegistry = new MockOlasMechRegistry();

        // Deploy Olas adapter
        adapter = new OlasMechAdapter(address(mockRegistry), admin);

        // Deploy FallbackPool with Olas integration
        pool = new FallbackPool(
            cairnCore,
            feeRecipient,
            mockERC8004,
            mockERC7710,
            address(adapter)
        );

        // Setup mock Olas mechs
        _setupMockMechs();
    }

    // ═══════════════════════════════════════════════════════════════
    // INTEGRATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_selectFallback_prefersInternalPool() public {
        // Register internal agent with high score
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = PRICE_FETCH;

        vm.deal(agent1, 10 ether);
        vm.prank(agent1);
        pool.register{value: 1 ether}(taskTypes, 5);

        // Mark agent as successful
        vm.prank(cairnCore);
        pool.activateFallback(bytes32(uint256(1)), agent1);
        vm.prank(cairnCore);
        pool.completeFallbackTask(bytes32(uint256(1)), agent1, true, 5);

        // Select fallback
        address selected = pool.selectFallback(PRICE_FETCH, 1 ether);

        // Should select internal agent over Olas
        assertEq(selected, agent1, "Should prefer internal agent with good track record");
    }

    function test_selectFallback_fallsBackToOlas_whenNoInternalAgents() public {
        // No internal agents registered for this task type
        address selected = pool.selectFallback(PRICE_FETCH, 0.1 ether);

        // Should select Olas mech
        assertEq(selected, address(0x100), "Should select Olas mech when no internal agents");
    }

    function test_selectFallback_fallsBackToOlas_whenInternalAgentsIneligible() public {
        // Register internal agent but with insufficient stake
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = PRICE_FETCH;

        vm.deal(agent1, 10 ether);
        vm.prank(agent1);
        pool.register{value: 0.01 ether}(taskTypes, 5); // Very low stake

        // Select fallback with high escrow (requires 10% stake)
        address selected = pool.selectFallback(PRICE_FETCH, 10 ether);

        // Should select Olas mech because internal agent has insufficient stake
        assertEq(selected, address(0x100), "Should fall back to Olas when internal agent ineligible");
    }

    function test_selectFallback_combinesInternalAndOlasPools() public {
        // Register internal agent with low score
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = TRADE_EXECUTE;

        vm.deal(agent2, 10 ether);
        vm.prank(agent2);
        pool.register{value: 0.2 ether}(taskTypes, 5);

        // Mark agent as having some failures
        vm.prank(cairnCore);
        pool.activateFallback(bytes32(uint256(2)), agent2);
        vm.prank(cairnCore);
        pool.completeFallbackTask(bytes32(uint256(2)), agent2, false, 0);

        // Select fallback
        address selected = pool.selectFallback(TRADE_EXECUTE, 1 ether);

        // Should select Olas mech (score 75) over failed internal agent
        assertEq(
            selected,
            address(0x200),
            "Should prefer high-reputation Olas mech over failed internal agent"
        );
    }

    function test_selectFallback_returnsZeroAddress_whenNoEligibleFallbacks() public {
        bytes32 unmappedTask = keccak256("unmapped.task");

        address selected = pool.selectFallback(unmappedTask, 1 ether);

        assertEq(selected, address(0), "Should return zero address when no fallbacks available");
    }

    // ═══════════════════════════════════════════════════════════════
    // ADAPTER CONFIGURATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_setOlasMechAdapter_updatesAdapter() public {
        // Deploy new adapter
        OlasMechAdapter newAdapter = new OlasMechAdapter(address(mockRegistry), admin);

        // Update adapter (no access control in current implementation)
        pool.setOlasMechAdapter(address(newAdapter));

        assertEq(
            address(pool.olasMechAdapter()),
            address(newAdapter),
            "Adapter not updated"
        );
    }

    function test_setOlasMechAdapter_canDisableOlas() public {
        // Disable Olas integration
        pool.setOlasMechAdapter(address(0));

        // Should have no Olas adapter
        assertEq(address(pool.olasMechAdapter()), address(0), "Adapter should be zero");

        // Fallback selection should only use internal pool
        address selected = pool.selectFallback(PRICE_FETCH, 0.1 ether);
        assertEq(selected, address(0), "Should return zero when no internal agents and Olas disabled");
    }

    function test_selectFallback_handlesOlasQueryFailure() public {
        // Disable Olas adapter to simulate failure
        vm.prank(admin);
        adapter.setEnabled(false);

        // Should not revert, just return best internal agent (or zero)
        address selected = pool.selectFallback(PRICE_FETCH, 0.1 ether);

        // With no internal agents and Olas disabled, should return zero
        assertEq(selected, address(0), "Should handle Olas failure gracefully");
    }

    // ═══════════════════════════════════════════════════════════════
    // HELPER FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    function _setupMockMechs() internal {
        // Mech 1: Price Oracle (excellent reputation: 85%)
        mockRegistry.addMech(
            1,
            address(0x100),
            PRICE_ORACLE,
            0.01 ether,
            true,
            85,
            15
        );

        // Mech 2: Trading Bot (excellent reputation: 90%)
        mockRegistry.addMech(
            2,
            address(0x200),
            TRADING_BOT,
            0.02 ether,
            true,
            90,
            10
        );
    }
}

// ═══════════════════════════════════════════════════════════════
// MOCK OLAS MECH REGISTRY (same as OlasMechAdapter tests)
// ═══════════════════════════════════════════════════════════════

contract MockOlasMechRegistry is IOlasMech {
    struct Mech {
        address mechAddress;
        uint256 serviceId;
        bytes32 capability;
        uint256 pricePerRequest;
        bool active;
        uint256 requestsCompleted;
        uint256 requestsFailed;
    }

    mapping(uint256 => Mech) public mechs;
    mapping(bytes32 => uint256[]) public capabilityToServiceIds;

    function addMech(
        uint256 serviceId,
        address mechAddress,
        bytes32 capability,
        uint256 price,
        bool active,
        uint256 completed,
        uint256 failed
    ) external {
        mechs[serviceId] = Mech({
            mechAddress: mechAddress,
            serviceId: serviceId,
            capability: capability,
            pricePerRequest: price,
            active: active,
            requestsCompleted: completed,
            requestsFailed: failed
        });

        capabilityToServiceIds[capability].push(serviceId);
    }

    // IOlasMech interface implementation
    function getMech(uint256 serviceId) external view override returns (MechInfo memory) {
        Mech storage mech = mechs[serviceId];

        bytes32[] memory capabilities = new bytes32[](1);
        capabilities[0] = mech.capability;

        return MechInfo({
            mechAddress: mech.mechAddress,
            serviceId: mech.serviceId,
            capabilities: capabilities,
            pricePerRequest: mech.pricePerRequest,
            active: mech.active,
            requestsCompleted: mech.requestsCompleted,
            requestsFailed: mech.requestsFailed
        });
    }

    function getMechsByCapability(bytes32 capability)
        external
        view
        override
        returns (uint256[] memory serviceIds)
    {
        return capabilityToServiceIds[capability];
    }

    function isMechActive(uint256 serviceId) external view override returns (bool) {
        return mechs[serviceId].active;
    }

    function getMechAddress(uint256 serviceId) external view override returns (address) {
        return mechs[serviceId].mechAddress;
    }

    function getMechPrice(uint256 serviceId) external view override returns (uint256) {
        return mechs[serviceId].pricePerRequest;
    }
}
