// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {RecoveryRouter} from "../src/RecoveryRouter.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {IERC8004} from "../src/interfaces/IERC8004.sol";
import {IERC7710} from "../src/interfaces/IERC7710.sol";
import {IERC8183} from "../src/interfaces/IERC8183.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";
import {ICairnCore} from "../src/interfaces/ICairnCore.sol";
import {MockERC8004} from "./mocks/MockERC8004.sol";

/// @title ERC Integration Tests
/// @notice Tests ERC-8004, ERC-7710, and ERC-8183 integrations
contract ERCIntegrationTest is Test {
    CairnCore public core;
    FallbackPool public pool;
    RecoveryRouter public router;
    ArbiterRegistry public registry;
    CairnGovernance public governance;
    MockERC8004 public reputationRegistry;

    address public feeRecipient = makeAddr("feeRecipient");
    address public operator = makeAddr("operator");
    address public primaryAgent = makeAddr("primaryAgent");
    address public fallbackAgent = makeAddr("fallbackAgent");

    bytes32 public taskType = keccak256("solidity.audit");

    function setUp() public {
        // Deploy mock reputation registry
        reputationRegistry = new MockERC8004();

        // Deploy governance
        governance = new CairnGovernance(address(this));

        // Deploy core protocol
        core = new CairnCore(
            feeRecipient,
            address(0), // router set later
            address(0), // pool set later
            address(0), // registry set later
            address(governance)
        );

        router = new RecoveryRouter(address(core));
        pool = new FallbackPool(address(core), feeRecipient, address(reputationRegistry), address(0), address(0));
        registry = new ArbiterRegistry(address(core), address(governance), feeRecipient);

        // Wire contracts
        vm.prank(address(governance));
        core.setContracts(address(router), address(pool), address(registry));

        // Fund accounts
        vm.deal(operator, 100 ether);
        vm.deal(primaryAgent, 10 ether);
        vm.deal(fallbackAgent, 10 ether);
    }

    // ═══════════════════════════════════════════════════════════════
    // ERC-8004 REPUTATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_ERC8004_DefaultReputation() public view {
        // Default reputation should be 70
        uint256 rep = reputationRegistry.getReputation(fallbackAgent);
        assertEq(rep, 70);
    }

    function test_ERC8004_CustomReputation() public {
        // Set custom reputation
        reputationRegistry.setReputation(fallbackAgent, 85);
        assertEq(reputationRegistry.getReputation(fallbackAgent), 85);
    }

    function test_ERC8004_BlocksLowReputation() public {
        // Set low reputation (below threshold of 50)
        reputationRegistry.setReputation(fallbackAgent, 30);

        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType;

        // Registration should fail
        vm.prank(fallbackAgent);
        vm.expectRevert();
        pool.register{value: 1 ether}(taskTypes, 3);
    }

    function test_ERC8004_AllowsHighReputation() public {
        // Set high reputation (above threshold)
        reputationRegistry.setReputation(fallbackAgent, 80);

        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType;

        // Registration should succeed
        vm.prank(fallbackAgent);
        pool.register{value: 1 ether}(taskTypes, 3);

        assertTrue(pool.getAgent(fallbackAgent).registered);
    }

    function test_ERC8004_ReportSuccess() public {
        // Report success increases reputation
        uint256 initialRep = reputationRegistry.getReputation(fallbackAgent);

        reputationRegistry.reportSuccess(fallbackAgent, taskType);

        uint256 newRep = reputationRegistry.getReputationForType(fallbackAgent, taskType);
        assertEq(newRep, initialRep + 1);
    }

    function test_ERC8004_ReportFailure() public {
        // Set initial reputation
        reputationRegistry.setReputation(fallbackAgent, 70);

        // Report failure with severity 5
        reputationRegistry.reportFailure(fallbackAgent, taskType, 5);

        uint256 newRep = reputationRegistry.getReputationForType(fallbackAgent, taskType);
        assertEq(newRep, 65); // 70 - 5
    }

    // ═══════════════════════════════════════════════════════════════
    // ERC-8183 HOOK TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_ERC8183_NoHookDoesNotRevert() public {
        // Submitting task without hook should work
        vm.prank(operator);
        bytes32 taskId = core.submitTask{value: 1 ether}(
            taskType,
            keccak256("spec"),
            primaryAgent,
            60,
            block.timestamp + 1 days
        );

        assertTrue(taskId != bytes32(0));
    }

    function test_FallbackPoolCanSetRegistries() public {
        // Test admin functions
        pool.setReputationRegistry(address(reputationRegistry));
        pool.setDelegationRegistry(address(0));

        assertEq(address(pool.reputationRegistry()), address(reputationRegistry));
    }

    function test_CairnCoreCanSetHook() public {
        // Test admin function
        vm.prank(address(governance));
        core.setEscrowHook(address(0));

        assertEq(address(core.escrowHook()), address(0));
    }

    // ═══════════════════════════════════════════════════════════════
    // INTEGRATION TEST
    // ═══════════════════════════════════════════════════════════════

    function test_Integration_FullFlow() public {
        // Set reputation for fallback agent
        reputationRegistry.setReputation(fallbackAgent, 80);

        // Register fallback agent
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType;

        vm.prank(fallbackAgent);
        pool.register{value: 1 ether}(taskTypes, 3);

        // Submit task (fallback auto-selected from pool)
        vm.prank(operator);
        bytes32 taskId = core.submitTask{value: 2 ether}(
            taskType,
            keccak256("audit-spec"),
            primaryAgent,
            60,
            block.timestamp + 1 days
        );

        // Verify task created
        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(task.operator, operator);
        assertEq(task.primaryAgent, primaryAgent);
        assertEq(task.fallbackAgent, fallbackAgent); // Auto-selected
        assertEq(task.escrowAmount, 2 ether);

        // Verify fallback agent was selected based on ERC-8004 reputation
        assertEq(task.fallbackAgent, fallbackAgent);
    }
}
