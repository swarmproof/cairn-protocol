// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {CairnCoreUpgradeable} from "../../src/upgradeable/CairnCoreUpgradeable.sol";
import {FallbackPoolUpgradeable} from "../../src/upgradeable/FallbackPoolUpgradeable.sol";
import {ArbiterRegistryUpgradeable} from "../../src/upgradeable/ArbiterRegistryUpgradeable.sol";
import {RecoveryRouterUpgradeable} from "../../src/upgradeable/RecoveryRouterUpgradeable.sol";
import {CairnGovernance} from "../../src/CairnGovernance.sol";
import {ICairnTypes} from "../../src/interfaces/ICairnTypes.sol";
import {ICairnCore} from "../../src/interfaces/ICairnCore.sol";

/// @title CairnCoreUpgradeTest
/// @notice Tests for UUPS upgradeability of CairnCore
/// @dev Verifies: deployment, upgrade, state preservation, authorization
contract CairnCoreUpgradeTest is Test {
    // Contracts
    CairnCoreUpgradeable public cairnCore;
    FallbackPoolUpgradeable public fallbackPool;
    ArbiterRegistryUpgradeable public arbiterRegistry;
    RecoveryRouterUpgradeable public recoveryRouter;
    CairnGovernance public governance;

    // Proxies
    address public cairnCoreProxy;
    address public fallbackPoolProxy;
    address public arbiterRegistryProxy;
    address public recoveryRouterProxy;

    // Actors
    address public admin = makeAddr("admin");
    address public operator = makeAddr("operator");
    address public primaryAgent = makeAddr("primaryAgent");
    address public fallbackAgent = makeAddr("fallbackAgent");
    address public feeRecipient = makeAddr("feeRecipient");

    // Test data
    bytes32 public constant TASK_TYPE = keccak256("test.task");
    bytes32 public constant SPEC_HASH = keccak256("spec");

    function setUp() public {
        vm.startPrank(admin);

        // 1. Deploy governance
        governance = new CairnGovernance(admin);

        // 2. Deploy RecoveryRouter
        RecoveryRouterUpgradeable recoveryRouterImpl = new RecoveryRouterUpgradeable();
        ERC1967Proxy recoveryProxy = new ERC1967Proxy(
            address(recoveryRouterImpl),
            abi.encodeCall(RecoveryRouterUpgradeable.initialize, (address(0), admin))
        );
        recoveryRouterProxy = address(recoveryProxy);
        recoveryRouter = RecoveryRouterUpgradeable(recoveryRouterProxy);

        // 3. Deploy FallbackPool
        FallbackPoolUpgradeable fallbackPoolImpl = new FallbackPoolUpgradeable();
        ERC1967Proxy fallbackProxy = new ERC1967Proxy(
            address(fallbackPoolImpl),
            abi.encodeCall(FallbackPoolUpgradeable.initialize, (address(0), feeRecipient, admin))
        );
        fallbackPoolProxy = address(fallbackProxy);
        fallbackPool = FallbackPoolUpgradeable(fallbackPoolProxy);

        // 4. Deploy ArbiterRegistry
        ArbiterRegistryUpgradeable arbiterRegistryImpl = new ArbiterRegistryUpgradeable();
        ERC1967Proxy arbiterProxy = new ERC1967Proxy(
            address(arbiterRegistryImpl),
            abi.encodeCall(
                ArbiterRegistryUpgradeable.initialize,
                (address(0), address(governance), feeRecipient, admin)
            )
        );
        arbiterRegistryProxy = address(arbiterProxy);
        arbiterRegistry = ArbiterRegistryUpgradeable(payable(arbiterRegistryProxy));

        // 5. Deploy CairnCore
        CairnCoreUpgradeable cairnCoreImpl = new CairnCoreUpgradeable();
        ERC1967Proxy coreProxy = new ERC1967Proxy(
            address(cairnCoreImpl),
            abi.encodeCall(
                CairnCoreUpgradeable.initialize,
                (
                    feeRecipient,
                    address(recoveryRouter),
                    address(fallbackPool),
                    address(arbiterRegistry),
                    address(governance)
                )
            )
        );
        cairnCoreProxy = address(coreProxy);
        cairnCore = CairnCoreUpgradeable(payable(cairnCoreProxy));

        // 6. Configure contract references
        recoveryRouter.setCairnCore(address(cairnCore));
        fallbackPool.setCairnCore(address(cairnCore));
        arbiterRegistry.setCairnCore(address(cairnCore));

        vm.stopPrank();

        // Fund test accounts
        vm.deal(operator, 100 ether);
        vm.deal(fallbackAgent, 10 ether);
    }

    function test_InitialDeployment() public view {
        // Verify proxy addresses
        assertTrue(cairnCoreProxy != address(0));
        assertTrue(fallbackPoolProxy != address(0));
        assertTrue(arbiterRegistryProxy != address(0));
        assertTrue(recoveryRouterProxy != address(0));

        // Verify initialization
        assertEq(cairnCore.feeRecipient(), feeRecipient);
        assertEq(address(cairnCore.governance()), address(governance));
        assertEq(address(cairnCore.recoveryRouter()), address(recoveryRouter));
        assertEq(address(cairnCore.fallbackPool()), address(fallbackPool));
        assertEq(address(cairnCore.arbiterRegistry()), address(arbiterRegistry));

        // Verify constants
        assertEq(cairnCore.protocolFeeBps(), 50);
        assertEq(cairnCore.minEscrow(), 0.001 ether);
        assertEq(cairnCore.minHeartbeatInterval(), 30);
        assertEq(cairnCore.recoveryThreshold(), 0.3e18);
        assertEq(cairnCore.disputeTimeout(), 7 days);
    }

    function test_UpgradeToV2() public {
        // Create some state before upgrade
        vm.prank(operator);
        bytes32 taskId = cairnCore.submitTask{value: 0.01 ether}(
            TASK_TYPE,
            SPEC_HASH,
            primaryAgent,
            60, // 1 minute heartbeat
            block.timestamp + 1 days
        );

        // Verify initial state
        ICairnCore.Task memory task = cairnCore.getTask(taskId);
        assertEq(task.operator, operator);
        assertEq(task.primaryAgent, primaryAgent);
        assertEq(task.escrowAmount, 0.01 ether);
        assertEq(uint256(task.state), uint256(ICairnTypes.TaskState.IDLE));

        // Deploy new implementation
        vm.prank(admin);
        CairnCoreUpgradeable newImpl = new CairnCoreUpgradeable();

        // Upgrade (only governance can upgrade)
        vm.prank(address(governance));
        cairnCore.upgradeToAndCall(address(newImpl), "");

        // Verify state preserved after upgrade
        ICairnCore.Task memory taskAfter = cairnCore.getTask(taskId);
        assertEq(taskAfter.operator, operator);
        assertEq(taskAfter.primaryAgent, primaryAgent);
        assertEq(taskAfter.escrowAmount, 0.01 ether);
        assertEq(uint256(taskAfter.state), uint256(ICairnTypes.TaskState.IDLE));

        // Verify constants still correct
        assertEq(cairnCore.protocolFeeBps(), 50);
        assertEq(cairnCore.minEscrow(), 0.001 ether);
    }

    function test_StatePreservedAfterUpgrade() public {
        // Submit multiple tasks
        vm.startPrank(operator);

        bytes32 task1 = cairnCore.submitTask{value: 0.01 ether}(
            TASK_TYPE,
            SPEC_HASH,
            primaryAgent,
            60,
            block.timestamp + 1 days
        );

        bytes32 task2 = cairnCore.submitTask{value: 0.02 ether}(
            keccak256("another.task"),
            keccak256("spec2"),
            fallbackAgent,
            120,
            block.timestamp + 2 days
        );

        vm.stopPrank();

        // Start first task
        vm.prank(primaryAgent);
        cairnCore.startTask(task1);

        // Verify states before upgrade
        assertEq(cairnCore.totalTasksCreated(), 2);
        assertEq(cairnCore.totalEscrowLocked(), 0.03 ether);
        ICairnCore.Task memory task1Before = cairnCore.getTask(task1);
        assertEq(uint256(task1Before.state), uint256(ICairnTypes.TaskState.RUNNING));

        // Perform upgrade
        vm.startPrank(admin);
        CairnCoreUpgradeable newImpl = new CairnCoreUpgradeable();
        vm.stopPrank();

        vm.prank(address(governance));
        cairnCore.upgradeToAndCall(address(newImpl), "");

        // Verify all state preserved
        assertEq(cairnCore.totalTasksCreated(), 2);
        assertEq(cairnCore.totalEscrowLocked(), 0.03 ether);

        ICairnCore.Task memory task1After = cairnCore.getTask(task1);
        assertEq(uint256(task1After.state), uint256(ICairnTypes.TaskState.RUNNING));
        assertEq(task1After.operator, operator);
        assertEq(task1After.escrowAmount, 0.01 ether);

        ICairnCore.Task memory task2After = cairnCore.getTask(task2);
        assertEq(uint256(task2After.state), uint256(ICairnTypes.TaskState.IDLE));
        assertEq(task2After.escrowAmount, 0.02 ether);
    }

    function test_OnlyGovernanceCanUpgrade() public {
        CairnCoreUpgradeable newImpl = new CairnCoreUpgradeable();

        // Operator cannot upgrade
        vm.prank(operator);
        vm.expectRevert();
        cairnCore.upgradeToAndCall(address(newImpl), "");

        // Admin cannot upgrade
        vm.prank(admin);
        vm.expectRevert();
        cairnCore.upgradeToAndCall(address(newImpl), "");

        // Governance can upgrade
        vm.prank(address(governance));
        cairnCore.upgradeToAndCall(address(newImpl), "");
    }

    function test_CannotReinitialize() public {
        // Attempt to call initialize again should fail
        vm.expectRevert();
        cairnCore.initialize(
            feeRecipient,
            address(recoveryRouter),
            address(fallbackPool),
            address(arbiterRegistry),
            address(governance)
        );
    }

    function test_FunctionalityAfterUpgrade() public {
        // Upgrade
        vm.startPrank(admin);
        CairnCoreUpgradeable newImpl = new CairnCoreUpgradeable();
        vm.stopPrank();

        vm.prank(address(governance));
        cairnCore.upgradeToAndCall(address(newImpl), "");

        // Test full task lifecycle after upgrade
        vm.prank(operator);
        bytes32 taskId = cairnCore.submitTask{value: 0.01 ether}(
            TASK_TYPE,
            SPEC_HASH,
            primaryAgent,
            60,
            block.timestamp + 1 days
        );

        // Start task
        vm.prank(primaryAgent);
        cairnCore.startTask(taskId);

        // Commit checkpoint
        bytes32[] memory checkpoints = new bytes32[](1);
        checkpoints[0] = keccak256("checkpoint1");
        bytes32 merkleRoot = keccak256(abi.encodePacked(checkpoints[0]));

        vm.prank(primaryAgent);
        cairnCore.commitCheckpointBatch(taskId, 1, merkleRoot, checkpoints[0]);

        // Complete task
        vm.prank(primaryAgent);
        cairnCore.completeTask(taskId);

        // Verify settlement
        ICairnCore.Task memory task = cairnCore.getTask(taskId);
        assertEq(uint256(task.state), uint256(ICairnTypes.TaskState.RESOLVED));
        assertEq(uint256(task.resolutionType), uint256(ICairnTypes.ResolutionType.SUCCESS));
        assertTrue(task.settledPrimary > 0);
    }

    function test_MultipleUpgrades() public {
        // First upgrade
        vm.startPrank(admin);
        CairnCoreUpgradeable impl2 = new CairnCoreUpgradeable();
        vm.stopPrank();

        vm.prank(address(governance));
        cairnCore.upgradeToAndCall(address(impl2), "");

        // Submit task after first upgrade
        vm.prank(operator);
        bytes32 taskId = cairnCore.submitTask{value: 0.01 ether}(
            TASK_TYPE,
            SPEC_HASH,
            primaryAgent,
            60,
            block.timestamp + 1 days
        );

        // Second upgrade
        vm.startPrank(admin);
        CairnCoreUpgradeable impl3 = new CairnCoreUpgradeable();
        vm.stopPrank();

        vm.prank(address(governance));
        cairnCore.upgradeToAndCall(address(impl3), "");

        // Verify task still exists
        ICairnCore.Task memory task = cairnCore.getTask(taskId);
        assertEq(task.operator, operator);
        assertEq(task.escrowAmount, 0.01 ether);
    }

    function test_PauseAfterUpgrade() public {
        // Upgrade
        vm.startPrank(admin);
        CairnCoreUpgradeable newImpl = new CairnCoreUpgradeable();
        vm.stopPrank();

        vm.prank(address(governance));
        cairnCore.upgradeToAndCall(address(newImpl), "");

        // Pause via governance
        vm.prank(address(governance));
        cairnCore.pause();

        // Cannot submit task when paused
        vm.prank(operator);
        vm.expectRevert();
        cairnCore.submitTask{value: 0.01 ether}(
            TASK_TYPE,
            SPEC_HASH,
            primaryAgent,
            60,
            block.timestamp + 1 days
        );

        // Unpause
        vm.prank(address(governance));
        cairnCore.unpause();

        // Can submit task after unpause
        vm.prank(operator);
        bytes32 taskId = cairnCore.submitTask{value: 0.01 ether}(
            TASK_TYPE,
            SPEC_HASH,
            primaryAgent,
            60,
            block.timestamp + 1 days
        );

        assertTrue(taskId != bytes32(0));
    }
}
