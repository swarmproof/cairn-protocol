// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {OlasMechAdapter} from "../src/adapters/OlasMechAdapter.sol";
import {IOlasMech} from "../src/interfaces/IOlasMech.sol";

/// @title OlasMechAdapterTest - Tests for Olas Mech Marketplace adapter
/// @notice Tests capability mapping, mech querying, and eligibility checks
contract OlasMechAdapterTest is Test {
    OlasMechAdapter public adapter;
    MockOlasMechRegistry public mockRegistry;

    address public admin = address(0x1);
    address public user = address(0x2);

    // Task type identifiers
    bytes32 public constant PRICE_FETCH = keccak256("defi.price_fetch");
    bytes32 public constant TRADE_EXECUTE = keccak256("defi.trade_execute");
    bytes32 public constant REPORT_GENERATE = keccak256("data.report_generate");

    // Olas capability identifiers
    bytes32 public constant PRICE_ORACLE = keccak256("price_oracle");
    bytes32 public constant TRADING_BOT = keccak256("trading_bot");
    bytes32 public constant DATA_ANALYST = keccak256("data_analyst");

    function setUp() public {
        // Deploy mock registry
        mockRegistry = new MockOlasMechRegistry();

        // Deploy adapter
        adapter = new OlasMechAdapter(address(mockRegistry), admin);

        // Setup test mechs in registry
        _setupMockMechs();
    }

    // ═══════════════════════════════════════════════════════════════
    // MAPPING TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_defaultMappings() public view {
        // Check default mappings are initialized
        assertEq(
            adapter.cairnToOlasCapability(PRICE_FETCH),
            PRICE_ORACLE,
            "Price fetch mapping incorrect"
        );
        assertEq(
            adapter.cairnToOlasCapability(TRADE_EXECUTE),
            TRADING_BOT,
            "Trade execute mapping incorrect"
        );
        assertEq(
            adapter.cairnToOlasCapability(REPORT_GENERATE),
            DATA_ANALYST,
            "Report generate mapping incorrect"
        );
    }

    function test_mapTaskType() public {
        bytes32 customTask = keccak256("custom.task");
        bytes32 customCapability = keccak256("custom_capability");

        vm.prank(admin);
        adapter.mapTaskType(customTask, customCapability);

        assertEq(
            adapter.cairnToOlasCapability(customTask),
            customCapability,
            "Custom mapping not set"
        );
    }

    function test_mapTaskType_revertsForNonAdmin() public {
        bytes32 customTask = keccak256("custom.task");
        bytes32 customCapability = keccak256("custom_capability");

        vm.prank(user);
        vm.expectRevert(OlasMechAdapter.OnlyAdmin.selector);
        adapter.mapTaskType(customTask, customCapability);
    }

    function test_unmapTaskType() public {
        vm.prank(admin);
        adapter.unmapTaskType(PRICE_FETCH);

        assertEq(
            adapter.cairnToOlasCapability(PRICE_FETCH),
            bytes32(0),
            "Mapping not removed"
        );
    }

    // ═══════════════════════════════════════════════════════════════
    // QUERY TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_queryAvailableMechs() public view {
        address[] memory mechs = adapter.queryAvailableMechs(PRICE_FETCH);

        assertGt(mechs.length, 0, "No mechs found");
        assertEq(mechs[0], address(0x100), "Incorrect mech address");
    }

    function test_queryAvailableMechs_filtersInactiveMechs() public {
        // Deactivate a mech
        mockRegistry.setMechActive(2, false);

        address[] memory mechs = adapter.queryAvailableMechs(TRADE_EXECUTE);

        // Should not include inactive mech
        for (uint256 i = 0; i < mechs.length; i++) {
            assertTrue(mechs[i] != address(0x200), "Inactive mech included");
        }
    }

    function test_queryAvailableMechs_filtersLowReputation() public {
        // Set a mech with low reputation
        mockRegistry.setMechReputation(3, 10, 90); // 10% success rate

        address[] memory mechs = adapter.queryAvailableMechs(REPORT_GENERATE);

        // Should not include low reputation mech
        for (uint256 i = 0; i < mechs.length; i++) {
            assertTrue(mechs[i] != address(0x300), "Low reputation mech included");
        }
    }

    function test_queryAvailableMechs_emptyForUnmappedTask() public view {
        bytes32 unmappedTask = keccak256("unmapped.task");
        address[] memory mechs = adapter.queryAvailableMechs(unmappedTask);

        assertEq(mechs.length, 0, "Should return empty for unmapped task");
    }

    // ═══════════════════════════════════════════════════════════════
    // ELIGIBILITY TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_isOlasMechEligible_trueForActiveMech() public view {
        bool eligible = adapter.isOlasMechEligible(address(0x100), PRICE_FETCH);
        assertTrue(eligible, "Active mech should be eligible");
    }

    function test_isOlasMechEligible_falseForInactiveMech() public {
        mockRegistry.setMechActive(1, false);

        bool eligible = adapter.isOlasMechEligible(address(0x100), PRICE_FETCH);
        assertFalse(eligible, "Inactive mech should not be eligible");
    }

    function test_isOlasMechEligible_falseForLowReputation() public {
        // Set mech with 50% success rate (below 70% threshold)
        mockRegistry.setMechReputation(1, 50, 50);

        bool eligible = adapter.isOlasMechEligible(address(0x100), PRICE_FETCH);
        assertFalse(eligible, "Low reputation mech should not be eligible");
    }

    function test_isOlasMechEligible_falseForUnmappedTask() public view {
        bytes32 unmappedTask = keccak256("unmapped.task");
        bool eligible = adapter.isOlasMechEligible(address(0x100), unmappedTask);
        assertFalse(eligible, "Should not be eligible for unmapped task");
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_setMinReputation() public {
        vm.prank(admin);
        adapter.setMinReputation(80);

        assertEq(adapter.minOlasReputation(), 80, "Min reputation not updated");
    }

    function test_setMinReputation_revertsForInvalidValue() public {
        vm.prank(admin);
        vm.expectRevert(OlasMechAdapter.InvalidReputation.selector);
        adapter.setMinReputation(101);
    }

    function test_setEnabled() public {
        vm.prank(admin);
        adapter.setEnabled(false);

        assertFalse(adapter.enabled(), "Adapter should be disabled");
    }

    function test_queryAvailableMechs_revertsWhenDisabled() public {
        vm.prank(admin);
        adapter.setEnabled(false);

        vm.expectRevert(OlasMechAdapter.AdapterDisabled.selector);
        adapter.queryAvailableMechs(PRICE_FETCH);
    }

    // ═══════════════════════════════════════════════════════════════
    // HELPER FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    function _setupMockMechs() internal {
        // Mech 1: Price Oracle (good reputation)
        mockRegistry.addMech(
            1,
            address(0x100),
            PRICE_ORACLE,
            0.01 ether,
            true,
            85,
            15
        );

        // Mech 2: Trading Bot (good reputation)
        mockRegistry.addMech(
            2,
            address(0x200),
            TRADING_BOT,
            0.02 ether,
            true,
            90,
            10
        );

        // Mech 3: Data Analyst (good reputation)
        mockRegistry.addMech(
            3,
            address(0x300),
            DATA_ANALYST,
            0.015 ether,
            true,
            80,
            20
        );
    }
}

// ═══════════════════════════════════════════════════════════════
// MOCK OLAS MECH REGISTRY
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
    uint256[] public allServiceIds;

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
        allServiceIds.push(serviceId);
    }

    function setMechActive(uint256 serviceId, bool active) external {
        mechs[serviceId].active = active;
    }

    function setMechReputation(
        uint256 serviceId,
        uint256 completed,
        uint256 failed
    ) external {
        mechs[serviceId].requestsCompleted = completed;
        mechs[serviceId].requestsFailed = failed;
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
