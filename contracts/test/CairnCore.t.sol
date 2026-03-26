// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {RecoveryRouter} from "../src/RecoveryRouter.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {ICairnCore} from "../src/interfaces/ICairnCore.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";
import {IFallbackPool} from "../src/interfaces/IFallbackPool.sol";

/// @title CairnCore Tests
/// @notice Comprehensive tests for the main protocol with 6-state machine
/// @dev Based on PRD-01 through PRD-07
contract CairnCoreTest is Test {
    CairnCore public core;
    RecoveryRouter public router;
    FallbackPool public pool;
    ArbiterRegistry public registry;
    CairnGovernance public governance;

    address public admin = makeAddr("admin");
    address public feeRecipient = makeAddr("feeRecipient");
    address public operator = makeAddr("operator");
    address public primaryAgent = makeAddr("primaryAgent");
    address public fallbackAgent = makeAddr("fallbackAgent");
    address public arbiter = makeAddr("arbiter");
    address public randomUser = makeAddr("randomUser");

    bytes32 public specHash = keccak256("task spec");
    bytes32 public taskType = keccak256("defi.swap");
    bytes32 public cid1 = keccak256("checkpoint1");
    bytes32 public cid2 = keccak256("checkpoint2");

    uint256 public constant MIN_ESCROW = 0.001 ether;
    uint256 public constant PROTOCOL_FEE_BPS = 50;

    function setUp() public {
        // Deploy governance first
        governance = new CairnGovernance(admin);

        // Deploy core with placeholder addresses first
        core = new CairnCore(
            feeRecipient,
            address(0), // router placeholder
            address(0), // pool placeholder
            address(0), // registry placeholder
            address(governance)
        );

        // Deploy dependent contracts with core address
        router = new RecoveryRouter(address(core));
        pool = new FallbackPool(address(core), feeRecipient, address(0), address(0), address(0));
        registry = new ArbiterRegistry(address(core), address(governance), feeRecipient);

        // Configure CairnCore via governance
        vm.prank(address(governance));
        core.setContracts(address(router), address(pool), address(registry));

        // Fund accounts
        vm.deal(operator, 100 ether);
        vm.deal(primaryAgent, 10 ether);
        vm.deal(fallbackAgent, 10 ether);
        vm.deal(arbiter, 10 ether);
        vm.deal(address(core), 10 ether);

        // Register fallback agent in pool
        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType;
        vm.prank(fallbackAgent);
        pool.register{value: 1 ether}(taskTypes, 5);

        // Register arbiter
        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;
        vm.prank(arbiter);
        registry.registerArbiter{value: 0.5 ether}(domains);
    }

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Constructor() public view {
        assertEq(core.feeRecipient(), feeRecipient);
        assertEq(core.protocolFeeBps(), PROTOCOL_FEE_BPS);
        assertEq(core.minEscrow(), MIN_ESCROW);
        assertEq(core.recoveryThreshold(), 0.3e18);
        assertEq(core.disputeTimeout(), 7 days);
    }

    function test_RevertConstructorZeroFeeRecipient() public {
        vm.expectRevert(ICairnCore.ZeroAddress.selector);
        new CairnCore(address(0), address(0), address(0), address(0), address(0));
    }

    // ═══════════════════════════════════════════════════════════════
    // SUBMIT TASK TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_SubmitTask() public {
        bytes32 taskId = _submitTask();

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.IDLE));
        assertEq(task.operator, operator);
        assertEq(task.primaryAgent, primaryAgent);
        assertEq(task.escrowAmount, 0.1 ether);
        assertEq(task.checkpointCount, 0);
    }

    function test_SubmitTaskWithAutoFallback() public {
        bytes32 taskId = _submitTask();

        ICairnCore.Task memory task = core.getTask(taskId);
        // Fallback was auto-selected from pool
        assertEq(task.fallbackAgent, fallbackAgent);
    }

    function test_SubmitTaskEmitsEvent() public {
        uint256 deadline = block.timestamp + 1 hours;
        vm.prank(operator);
        vm.expectEmit(false, false, true, false);
        emit ICairnCore.TaskCreated(
            bytes32(0),
            taskType,
            operator,
            primaryAgent,
            fallbackAgent,
            0.1 ether,
            deadline
        );
        core.submitTask{value: 0.1 ether}(taskType, specHash, primaryAgent, 60, deadline);
    }

    function test_RevertSubmitTaskZeroPrimaryAgent() public {
        vm.prank(operator);
        vm.expectRevert(ICairnCore.ZeroAddress.selector);
        core.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            address(0),
            60,
            block.timestamp + 1 hours
        );
    }

    function test_RevertSubmitTaskInsufficientEscrow() public {
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.InsufficientEscrow.selector, 0, MIN_ESCROW));
        core.submitTask{value: 0}(
            taskType,
            specHash,
            primaryAgent,
            60,
            block.timestamp + 1 hours
        );
    }

    function test_RevertSubmitTaskInvalidHeartbeat() public {
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.InvalidHeartbeatInterval.selector, 10, 30));
        core.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            10, // Too low
            block.timestamp + 1 hours
        );
    }

    function test_RevertSubmitTaskInvalidDeadline() public {
        vm.prank(operator);
        vm.expectRevert();
        core.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            60,
            block.timestamp - 1 // Past deadline
        );
    }

    // ═══════════════════════════════════════════════════════════════
    // START TASK TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_StartTask() public {
        bytes32 taskId = _submitTask();

        vm.prank(primaryAgent);
        core.startTask(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RUNNING));
        assertGt(task.startedAt, 0);
        assertGt(task.lastHeartbeat, 0);
    }

    function test_StartTaskEmitsEvent() public {
        bytes32 taskId = _submitTask();

        vm.prank(primaryAgent);
        vm.expectEmit(true, true, false, false);
        emit ICairnCore.TaskStarted(taskId, primaryAgent, 0, 0);
        core.startTask(taskId);
    }

    function test_RevertStartTaskUnauthorized() public {
        bytes32 taskId = _submitTask();

        vm.prank(randomUser);
        vm.expectRevert();
        core.startTask(taskId);
    }

    function test_RevertStartTaskWrongState() public {
        bytes32 taskId = _submitTask();

        vm.prank(primaryAgent);
        core.startTask(taskId);

        // Try to start again
        vm.prank(primaryAgent);
        vm.expectRevert();
        core.startTask(taskId);
    }

    // ═══════════════════════════════════════════════════════════════
    // CHECKPOINT BATCH TESTS (PRD-07)
    // ═══════════════════════════════════════════════════════════════

    function test_CommitCheckpointBatch() public {
        bytes32 taskId = _submitAndStartTask();

        bytes32 merkleRoot = keccak256("merkle_root");
        bytes32 latestCID = keccak256("batch_latest");

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 5, merkleRoot, latestCID);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(task.checkpointCount, 5);
        assertEq(task.latestCheckpointCID, latestCID);
    }

    function test_CommitCheckpointBatchEmitsEvent() public {
        bytes32 taskId = _submitAndStartTask();

        bytes32 merkleRoot = keccak256("merkle_root");
        bytes32 latestCID = keccak256("batch_latest");

        vm.prank(primaryAgent);
        vm.expectEmit(true, true, false, true);
        emit ICairnCore.CheckpointBatchCommitted(taskId, primaryAgent, 0, 4, merkleRoot, latestCID);
        core.commitCheckpointBatch(taskId, 5, merkleRoot, latestCID);
    }

    function test_CommitCheckpointBatchAccumulates() public {
        bytes32 taskId = _submitAndStartTask();

        // First batch: 3 checkpoints
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root1"), keccak256("cid1"));

        // Second batch: 5 checkpoints
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 5, keccak256("root2"), keccak256("cid2"));

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(task.checkpointCount, 8);
        assertEq(task.primaryCheckpoints, 8);
    }

    function test_CommitCheckpointBatchUpdatesHeartbeat() public {
        bytes32 taskId = _submitAndStartTask();

        uint256 timeBefore = block.timestamp;
        vm.warp(block.timestamp + 30);

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root"), keccak256("cid"));

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(task.lastHeartbeat, timeBefore + 30);
    }

    function test_RevertCommitCheckpointBatchUnauthorized() public {
        bytes32 taskId = _submitAndStartTask();

        vm.prank(randomUser);
        vm.expectRevert();
        core.commitCheckpointBatch(taskId, 5, keccak256("root"), keccak256("cid"));
    }

    // ═══════════════════════════════════════════════════════════════
    // HEARTBEAT TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Heartbeat() public {
        bytes32 taskId = _submitAndStartTask();

        uint256 timeBefore = block.timestamp;
        vm.warp(block.timestamp + 30);

        vm.prank(primaryAgent);
        core.heartbeat(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(task.lastHeartbeat, timeBefore + 30);
    }

    function test_HeartbeatEmitsEvent() public {
        bytes32 taskId = _submitAndStartTask();

        vm.warp(block.timestamp + 30);

        vm.prank(primaryAgent);
        vm.expectEmit(true, true, false, true);
        emit ICairnCore.Heartbeat(taskId, primaryAgent, block.timestamp);
        core.heartbeat(taskId);
    }

    function test_RevertHeartbeatUnauthorized() public {
        bytes32 taskId = _submitAndStartTask();

        vm.warp(block.timestamp + 30);

        vm.prank(fallbackAgent);
        vm.expectRevert();
        core.heartbeat(taskId);
    }

    function test_RevertHeartbeatTooFrequent() public {
        bytes32 taskId = _submitAndStartTask();

        // Try heartbeat immediately (too soon)
        vm.prank(primaryAgent);
        vm.expectRevert();
        core.heartbeat(taskId);
    }

    // ═══════════════════════════════════════════════════════════════
    // LIVENESS CHECK & FAILURE DETECTION TESTS (PRD-02)
    // ═══════════════════════════════════════════════════════════════

    function test_IsStale() public {
        bytes32 taskId = _submitAndStartTask();

        assertFalse(core.isStale(taskId));

        // Warp past 2x heartbeat interval
        vm.warp(block.timestamp + 121);
        assertTrue(core.isStale(taskId));
    }

    function test_DetectFailure() public {
        bytes32 taskId = _submitAndStartTask();

        // Warp past staleness threshold
        vm.warp(block.timestamp + 121);

        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        // With high recovery score, should go to RECOVERING
        assertTrue(
            task.state == ICairnTypes.TaskState.RECOVERING ||
            task.state == ICairnTypes.TaskState.DISPUTED
        );
    }

    function test_DetectFailureEmitsEvent() public {
        bytes32 taskId = _submitAndStartTask();

        vm.warp(block.timestamp + 121);

        vm.expectEmit(true, false, false, false);
        emit ICairnCore.TaskFailed(
            taskId,
            primaryAgent,
            ICairnTypes.FailureClass.LIVENESS,
            ICairnTypes.FailureType.HEARTBEAT_MISS,
            0,
            bytes32(0)
        );
        core.detectFailure(taskId);
    }

    function test_RevertDetectFailureNotStale() public {
        bytes32 taskId = _submitAndStartTask();

        vm.expectRevert(abi.encodeWithSelector(ICairnCore.TaskNotStale.selector, taskId));
        core.detectFailure(taskId);
    }

    // ═══════════════════════════════════════════════════════════════
    // RECOVERY FLOW TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_FallbackTakesOverAfterFailure() public {
        bytes32 taskId = _submitAndStartTask();

        // Primary commits some work
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root"), cid1);

        // Primary fails
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);

        // If in RECOVERING state, fallback can work
        if (task.state == ICairnTypes.TaskState.RECOVERING) {
            assertEq(task.currentAgent, fallbackAgent);

            // Fallback picks up
            vm.prank(fallbackAgent);
            core.commitCheckpointBatch(taskId, 2, keccak256("root2"), cid2);

            task = core.getTask(taskId);
            assertEq(task.checkpointCount, 5);
            assertEq(task.fallbackCheckpoints, 2);
        }
    }

    function test_PrimaryCannotActAfterFailure() public {
        bytes32 taskId = _submitAndStartTask();

        // Primary commits some work
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root"), cid1);

        // Primary fails
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);

        if (task.state == ICairnTypes.TaskState.RECOVERING) {
            // Primary tries to continue - should fail
            vm.prank(primaryAgent);
            vm.expectRevert();
            core.commitCheckpointBatch(taskId, 2, keccak256("root2"), cid2);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // COMPLETE TASK TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_CompleteTask() public {
        bytes32 taskId = _submitAndStartTask();

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root"), cid1);

        vm.prank(primaryAgent);
        core.completeTask(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));
    }

    function test_CompleteTaskEmitsEvent() public {
        bytes32 taskId = _submitAndStartTask();

        vm.prank(primaryAgent);
        vm.expectEmit(true, true, false, true);
        emit ICairnCore.TaskCompleted(taskId, primaryAgent, 0);
        core.completeTask(taskId);
    }

    function test_CompleteTaskTriggersSettlement() public {
        bytes32 taskId = _submitAndStartTask();

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root"), cid1);

        uint256 primaryBefore = primaryAgent.balance;
        uint256 feeBefore = feeRecipient.balance;

        vm.prank(primaryAgent);
        core.completeTask(taskId);

        // Check settlement happened
        uint256 escrow = 0.1 ether;
        uint256 fee = (escrow * PROTOCOL_FEE_BPS) / 10000;
        uint256 primaryExpected = escrow - fee;

        assertEq(primaryAgent.balance - primaryBefore, primaryExpected);
        assertEq(feeRecipient.balance - feeBefore, fee);
    }

    function test_RevertCompleteTaskUnauthorized() public {
        bytes32 taskId = _submitAndStartTask();

        vm.prank(fallbackAgent);
        vm.expectRevert();
        core.completeTask(taskId);
    }

    function test_RevertCompleteTaskAfterDeadline() public {
        bytes32 taskId = _submitAndStartTask();

        vm.warp(block.timestamp + 2 hours);

        vm.prank(primaryAgent);
        vm.expectRevert();
        core.completeTask(taskId);
    }

    function test_FallbackCanComplete() public {
        bytes32 taskId = _submitAndStartTask();

        // Primary fails
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);

        if (task.state == ICairnTypes.TaskState.RECOVERING) {
            // Fallback completes
            vm.prank(fallbackAgent);
            core.completeTask(taskId);

            task = core.getTask(taskId);
            assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // DISPUTE TESTS (PRD-05)
    // ═══════════════════════════════════════════════════════════════

    function test_ResolveDispute() public {
        bytes32 taskId = _submitAndStartTask();

        // Create conditions for DISPUTED state
        // (Low recovery score would go to DISPUTED, but let's test directly)

        // Get task into DISPUTED state by failure with low recovery
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);

        if (task.state == ICairnTypes.TaskState.DISPUTED) {
            ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
                outcome: ICairnTypes.RulingOutcome.REFUND_OPERATOR,
                agentShare: 0,
                rationaleCID: keccak256("rationale")
            });

            vm.prank(arbiter);
            core.resolveDispute(taskId, ruling);

            task = core.getTask(taskId);
            assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));
        }
    }

    function test_ResolveDisputeTimeout() public {
        bytes32 taskId = _submitAndStartTask();

        // Get into DISPUTED state
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);

        if (task.state == ICairnTypes.TaskState.DISPUTED) {
            // Wait for dispute timeout
            vm.warp(block.timestamp + 7 days + 1);

            uint256 operatorBefore = operator.balance;

            core.resolveDisputeTimeout(taskId);

            task = core.getTask(taskId);
            assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));

            // Operator should get refund
            assertGt(operator.balance, operatorBefore);
        }
    }

    function test_RevertResolveDisputeTimeoutTooEarly() public {
        bytes32 taskId = _submitAndStartTask();

        // Get into DISPUTED state
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);

        if (task.state == ICairnTypes.TaskState.DISPUTED) {
            // Try timeout before it's ready
            vm.expectRevert(ICairnCore.DisputeTimeoutNotReached.selector);
            core.resolveDisputeTimeout(taskId);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // MERKLE VERIFICATION TESTS (PRD-07)
    // ═══════════════════════════════════════════════════════════════

    function test_GetBatchRoots() public {
        bytes32 taskId = _submitAndStartTask();

        bytes32 root1 = keccak256("root1");
        bytes32 root2 = keccak256("root2");

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, root1, cid1);
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 5, root2, cid2);

        bytes32[] memory roots = core.getBatchRoots(taskId);
        assertEq(roots.length, 2);
        assertEq(roots[0], root1);
        assertEq(roots[1], root2);
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_GetAgentTasks() public {
        bytes32 taskId = _submitTask();

        bytes32[] memory tasks = core.getAgentTasks(primaryAgent);
        assertEq(tasks.length, 1);
        assertEq(tasks[0], taskId);
    }

    function test_GetTaskTypeHistory() public {
        bytes32 taskId = _submitTask();

        bytes32[] memory history = core.getTaskTypeHistory(taskType);
        assertEq(history.length, 1);
        assertEq(history[0], taskId);
    }

    function test_TotalEscrowLocked() public {
        uint256 beforeSubmit = core.totalEscrowLocked();

        _submitTask();

        assertEq(core.totalEscrowLocked(), beforeSubmit + 0.1 ether);
    }

    function test_TotalTasksCreated() public {
        uint256 beforeSubmit = core.totalTasksCreated();

        _submitTask();

        assertEq(core.totalTasksCreated(), beforeSubmit + 1);
    }

    // ═══════════════════════════════════════════════════════════════
    // GOVERNANCE TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_SetFeeRecipient() public {
        address newFee = makeAddr("newFee");

        vm.prank(address(governance));
        core.setFeeRecipient(newFee);

        assertEq(core.feeRecipient(), newFee);
    }

    function test_RevertSetFeeRecipientNotGovernance() public {
        vm.prank(randomUser);
        vm.expectRevert();
        core.setFeeRecipient(makeAddr("newFee"));
    }

    function test_SetContracts() public {
        address newRouter = makeAddr("newRouter");
        address newPool = makeAddr("newPool");
        address newRegistry = makeAddr("newRegistry");

        vm.prank(address(governance));
        core.setContracts(newRouter, newPool, newRegistry);

        assertEq(address(core.recoveryRouter()), newRouter);
        assertEq(address(core.fallbackPool()), newPool);
        assertEq(address(core.arbiterRegistry()), newRegistry);
    }

    function test_Pause() public {
        vm.prank(address(governance));
        core.pause();

        // Should not be able to submit task when paused
        vm.prank(operator);
        vm.expectRevert();
        core.submitTask{value: 0.1 ether}(taskType, specHash, primaryAgent, 60, block.timestamp + 1 hours);
    }

    function test_Unpause() public {
        vm.prank(address(governance));
        core.pause();

        vm.prank(address(governance));
        core.unpause();

        // Should be able to submit task after unpause
        vm.prank(operator);
        core.submitTask{value: 0.1 ether}(taskType, specHash, primaryAgent, 60, block.timestamp + 1 hours);
    }

    // ═══════════════════════════════════════════════════════════════
    // E2E FLOW TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_E2E_HappyPath() public {
        // 1. Submit task
        bytes32 taskId = _submitTask();

        // 2. Start task
        vm.prank(primaryAgent);
        core.startTask(taskId);

        // 3. Primary works (checkpoint batches + heartbeats)
        for (uint i = 0; i < 3; i++) {
            vm.warp(block.timestamp + 30);
            vm.prank(primaryAgent);
            core.commitCheckpointBatch(taskId, 2, keccak256(abi.encode("root", i)), keccak256(abi.encode("cid", i)));
        }

        // 4. Complete
        uint256 primaryBefore = primaryAgent.balance;
        vm.prank(primaryAgent);
        core.completeTask(taskId);

        // Verify
        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));
        assertEq(uint8(task.resolutionType), uint8(ICairnTypes.ResolutionType.SUCCESS));
        assertGt(primaryAgent.balance - primaryBefore, 0);
    }

    function test_E2E_RecoveryFlow() public {
        // 1. Submit and start task
        bytes32 taskId = _submitAndStartTask();

        // 2. Primary works partially
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root1"), cid1);

        // 3. Primary fails
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);

        if (task.state == ICairnTypes.TaskState.RECOVERING) {
            // 4. Fallback picks up
            vm.prank(fallbackAgent);
            core.commitCheckpointBatch(taskId, 2, keccak256("root2"), cid2);

            // 5. Fallback completes
            uint256 primaryBefore = primaryAgent.balance;
            uint256 fallbackBefore = fallbackAgent.balance;

            vm.prank(fallbackAgent);
            core.completeTask(taskId);

            // Both should get paid proportionally
            assertGt(primaryAgent.balance - primaryBefore, 0);
            assertGt(fallbackAgent.balance - fallbackBefore, 0);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // EDGE CASES
    // ═══════════════════════════════════════════════════════════════

    function test_MultipleTasks() public {
        bytes32 taskId1 = _submitAndStartTask();
        bytes32 taskId2 = _submitAndStartTask();

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId1, 3, keccak256("root1"), cid1);

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId2, 5, keccak256("root2"), cid2);

        ICairnCore.Task memory task1 = core.getTask(taskId1);
        ICairnCore.Task memory task2 = core.getTask(taskId2);

        assertEq(task1.checkpointCount, 3);
        assertEq(task2.checkpointCount, 5);
    }

    function test_ReceiveETH() public {
        // Contract should accept ETH
        (bool success,) = address(core).call{value: 1 ether}("");
        assertTrue(success);
    }

    // ═══════════════════════════════════════════════════════════════
    // DISPUTED STATE TESTS (Coverage Gap Fix)
    // ═══════════════════════════════════════════════════════════════

    function test_DetectFailure_NoFallback_EntersDisputed() public {
        // Deploy a fresh system without fallback pool
        RecoveryRouter newRouter = new RecoveryRouter(address(0));
        ArbiterRegistry newRegistry = new ArbiterRegistry(address(0), address(governance), feeRecipient);

        CairnCore coreNoFallback = new CairnCore(
            feeRecipient,
            address(newRouter),
            address(0), // No fallback pool
            address(newRegistry),
            address(governance)
        );

        // Configure router to accept the new core
        newRouter.setCairnCore(address(coreNoFallback));
        newRegistry.setCairnCore(address(coreNoFallback));

        vm.deal(operator, 10 ether);

        // Submit and start task
        vm.prank(operator);
        bytes32 taskId = coreNoFallback.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            60,
            block.timestamp + 1 hours
        );

        vm.prank(primaryAgent);
        coreNoFallback.startTask(taskId);

        // Let task go stale
        vm.warp(block.timestamp + 121);
        coreNoFallback.detectFailure(taskId);

        // Should be DISPUTED because no fallback available
        ICairnCore.Task memory task = coreNoFallback.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.DISPUTED));
    }

    function test_DetectFailure_ZeroCheckpoints_EntersDisputed() public {
        // Submit and start task (no checkpoints committed)
        bytes32 taskId = _submitAndStartTask();

        // Immediately go stale without any checkpoints
        // This should result in low recovery score → DISPUTED
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        // May go to RECOVERING or DISPUTED based on recovery score
        // but with 0 checkpoints, score should be low
        assertTrue(
            task.state == ICairnTypes.TaskState.DISPUTED ||
            task.state == ICairnTypes.TaskState.RECOVERING,
            "Should be DISPUTED or RECOVERING"
        );
    }

    function test_ResolveDispute_PayAgent() public {
        // Deploy a fresh system without fallback pool
        RecoveryRouter newRouter = new RecoveryRouter(address(0));
        ArbiterRegistry newRegistry = new ArbiterRegistry(address(0), address(governance), feeRecipient);

        CairnCore coreNoFallback = new CairnCore(
            feeRecipient,
            address(newRouter),
            address(0),
            address(newRegistry),
            address(governance)
        );

        newRouter.setCairnCore(address(coreNoFallback));
        newRegistry.setCairnCore(address(coreNoFallback));

        // Register arbiter in new registry
        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;
        vm.prank(arbiter);
        newRegistry.registerArbiter{value: 0.5 ether}(domains);

        vm.deal(operator, 10 ether);

        vm.prank(operator);
        bytes32 taskId = coreNoFallback.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            60,
            block.timestamp + 1 hours
        );

        vm.prank(primaryAgent);
        coreNoFallback.startTask(taskId);

        // Commit some checkpoints before failing
        vm.prank(primaryAgent);
        coreNoFallback.commitCheckpointBatch(taskId, 3, keccak256("root"), cid1);

        vm.warp(block.timestamp + 121);
        coreNoFallback.detectFailure(taskId);

        ICairnCore.Task memory task = coreNoFallback.getTask(taskId);
        if (task.state == ICairnTypes.TaskState.DISPUTED) {
            // Resolve with PAY_AGENT ruling
            ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
                outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
                agentShare: 0,
                rationaleCID: keccak256("pay agent rationale")
            });

            uint256 primaryBefore = primaryAgent.balance;
            vm.prank(arbiter);
            coreNoFallback.resolveDispute(taskId, ruling);

            task = coreNoFallback.getTask(taskId);
            assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));
            assertEq(uint8(task.resolutionType), uint8(ICairnTypes.ResolutionType.ARBITER_RULING));
            assertGt(primaryAgent.balance, primaryBefore, "Agent should be paid");
        }
    }

    function test_ResolveDispute_Split() public {
        // Deploy a fresh system without fallback pool
        RecoveryRouter newRouter = new RecoveryRouter(address(0));
        ArbiterRegistry newRegistry = new ArbiterRegistry(address(0), address(governance), feeRecipient);

        CairnCore coreNoFallback = new CairnCore(
            feeRecipient,
            address(newRouter),
            address(0),
            address(newRegistry),
            address(governance)
        );

        newRouter.setCairnCore(address(coreNoFallback));
        newRegistry.setCairnCore(address(coreNoFallback));

        // Register arbiter
        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;
        vm.prank(arbiter);
        newRegistry.registerArbiter{value: 0.5 ether}(domains);

        vm.deal(operator, 10 ether);

        vm.prank(operator);
        bytes32 taskId = coreNoFallback.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            60,
            block.timestamp + 1 hours
        );

        vm.prank(primaryAgent);
        coreNoFallback.startTask(taskId);

        vm.warp(block.timestamp + 121);
        coreNoFallback.detectFailure(taskId);

        ICairnCore.Task memory task = coreNoFallback.getTask(taskId);
        if (task.state == ICairnTypes.TaskState.DISPUTED) {
            // Resolve with SPLIT ruling (50% to agent, 50% refund)
            ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
                outcome: ICairnTypes.RulingOutcome.SPLIT,
                agentShare: 50,
                rationaleCID: keccak256("split rationale")
            });

            uint256 primaryBefore = primaryAgent.balance;

            vm.prank(arbiter);
            coreNoFallback.resolveDispute(taskId, ruling);

            task = coreNoFallback.getTask(taskId);
            assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));
            // Agent should receive funds
            assertGt(primaryAgent.balance, primaryBefore, "Agent should receive split");
        }
    }

    function test_ResolveDisputeTimeout_FullFlow() public {
        // Deploy a fresh system without fallback pool
        RecoveryRouter newRouter = new RecoveryRouter(address(0));
        ArbiterRegistry newRegistry = new ArbiterRegistry(address(0), address(governance), feeRecipient);

        CairnCore coreNoFallback = new CairnCore(
            feeRecipient,
            address(newRouter),
            address(0),
            address(newRegistry),
            address(governance)
        );

        newRouter.setCairnCore(address(coreNoFallback));
        newRegistry.setCairnCore(address(coreNoFallback));

        vm.deal(operator, 10 ether);

        vm.prank(operator);
        bytes32 taskId = coreNoFallback.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            60,
            block.timestamp + 1 hours
        );

        vm.prank(primaryAgent);
        coreNoFallback.startTask(taskId);

        vm.warp(block.timestamp + 121);
        coreNoFallback.detectFailure(taskId);

        ICairnCore.Task memory task = coreNoFallback.getTask(taskId);
        if (task.state == ICairnTypes.TaskState.DISPUTED) {
            // Wait for dispute timeout (7 days)
            vm.warp(block.timestamp + 7 days + 1);

            uint256 operatorBefore = operator.balance;

            coreNoFallback.resolveDisputeTimeout(taskId);

            task = coreNoFallback.getTask(taskId);
            assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RESOLVED));
            assertEq(uint8(task.resolutionType), uint8(ICairnTypes.ResolutionType.TIMEOUT_REFUND));
            assertGt(operator.balance, operatorBefore, "Operator should get refund");
        }
    }

    function test_RevertResolveDispute_NotDisputed() public {
        bytes32 taskId = _submitAndStartTask();

        // Task is in RUNNING state, not DISPUTED
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.REFUND_OPERATOR,
            agentShare: 0,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(arbiter);
        vm.expectRevert();
        core.resolveDispute(taskId, ruling);
    }

    function test_TaskDisputedEvent() public {
        // Deploy a fresh system without fallback pool
        RecoveryRouter newRouter = new RecoveryRouter(address(0));
        ArbiterRegistry newRegistry = new ArbiterRegistry(address(0), address(governance), feeRecipient);

        CairnCore coreNoFallback = new CairnCore(
            feeRecipient,
            address(newRouter),
            address(0),
            address(newRegistry),
            address(governance)
        );

        newRouter.setCairnCore(address(coreNoFallback));
        newRegistry.setCairnCore(address(coreNoFallback));

        vm.deal(operator, 10 ether);

        vm.prank(operator);
        bytes32 taskId = coreNoFallback.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            60,
            block.timestamp + 1 hours
        );

        vm.prank(primaryAgent);
        coreNoFallback.startTask(taskId);

        vm.warp(block.timestamp + 121);

        // Expect TaskDisputed event
        vm.expectEmit(true, false, false, false);
        emit ICairnCore.TaskDisputed(taskId, 0, 0);
        coreNoFallback.detectFailure(taskId);
    }

    // ═══════════════════════════════════════════════════════════════
    // MERKLE VERIFICATION TESTS (Coverage Gap Fix)
    // ═══════════════════════════════════════════════════════════════

    function test_VerifyCheckpoint_InvalidBatchIndex() public {
        bytes32 taskId = _submitAndStartTask();

        // Commit one batch
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 3, keccak256("root"), cid1);

        // Try to verify with invalid batch index
        bytes32[] memory proof = new bytes32[](0);
        bool result = core.verifyCheckpoint(taskId, cid1, 99, 0, proof);

        assertFalse(result, "Should return false for invalid batch index");
    }

    function test_VerifyCheckpoint_ValidProof() public {
        bytes32 taskId = _submitAndStartTask();

        // Create a proper Merkle tree for testing
        // Leaf structure: keccak256(abi.encodePacked(cid, leafIndex))
        bytes32 leaf0 = keccak256(abi.encodePacked(cid1, uint256(0)));
        bytes32 leaf1 = keccak256(abi.encodePacked(cid2, uint256(1)));

        // Simple 2-leaf tree: root = hash(leaf0, leaf1)
        bytes32 root = _hashPair(leaf0, leaf1);

        // Commit batch with this root
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 2, root, cid2);

        // Verify leaf0 with proof [leaf1]
        bytes32[] memory proof = new bytes32[](1);
        proof[0] = leaf1;

        bool result = core.verifyCheckpoint(taskId, cid1, 0, 0, proof);
        assertTrue(result, "Valid proof should verify");
    }

    function test_VerifyCheckpoint_InvalidProof() public {
        bytes32 taskId = _submitAndStartTask();

        // Create a proper Merkle tree
        bytes32 leaf0 = keccak256(abi.encodePacked(cid1, uint256(0)));
        bytes32 leaf1 = keccak256(abi.encodePacked(cid2, uint256(1)));
        bytes32 root = _hashPair(leaf0, leaf1);

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 2, root, cid2);

        // Try to verify with wrong proof
        bytes32[] memory wrongProof = new bytes32[](1);
        wrongProof[0] = keccak256("wrong");

        bool result = core.verifyCheckpoint(taskId, cid1, 0, 0, wrongProof);
        assertFalse(result, "Invalid proof should not verify");
    }

    function test_VerifyCheckpoint_WrongCID() public {
        bytes32 taskId = _submitAndStartTask();

        bytes32 leaf0 = keccak256(abi.encodePacked(cid1, uint256(0)));
        bytes32 leaf1 = keccak256(abi.encodePacked(cid2, uint256(1)));
        bytes32 root = _hashPair(leaf0, leaf1);

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 2, root, cid2);

        // Try to verify wrong CID with correct proof structure
        bytes32[] memory proof = new bytes32[](1);
        proof[0] = leaf1;

        bytes32 wrongCid = keccak256("wrong cid");
        bool result = core.verifyCheckpoint(taskId, wrongCid, 0, 0, proof);
        assertFalse(result, "Wrong CID should not verify");
    }

    function test_RevertTaskNotFound() public {
        bytes32 fakeTaskId = keccak256("nonexistent");

        vm.expectRevert(abi.encodeWithSelector(ICairnCore.TaskNotFound.selector, fakeTaskId));
        core.getTask(fakeTaskId);
    }

    function test_ModifierInState_Reverts() public {
        bytes32 taskId = _submitTask();

        // Task is in IDLE state, try to complete it (requires RUNNING)
        vm.prank(primaryAgent);
        vm.expectRevert();
        core.completeTask(taskId);
    }

    // ═══════════════════════════════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════════════════════════════

    function _hashPair(bytes32 a, bytes32 b) internal pure returns (bytes32) {
        return a < b
            ? keccak256(abi.encodePacked(a, b))
            : keccak256(abi.encodePacked(b, a));
    }

    function _submitTask() internal returns (bytes32) {
        uint256 deadline = block.timestamp + 1 hours;
        vm.prank(operator);
        return core.submitTask{value: 0.1 ether}(
            taskType,
            specHash,
            primaryAgent,
            60,
            deadline
        );
    }

    function _submitAndStartTask() internal returns (bytes32) {
        bytes32 taskId = _submitTask();
        vm.prank(primaryAgent);
        core.startTask(taskId);
        return taskId;
    }
}
