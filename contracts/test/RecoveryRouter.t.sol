// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {RecoveryRouter} from "../src/RecoveryRouter.sol";
import {IRecoveryRouter} from "../src/interfaces/IRecoveryRouter.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";

/// @title RecoveryRouter Tests
/// @notice Comprehensive tests for failure classification and recovery scoring
/// @dev Based on PRD-02 Sections 2.1-2.2
contract RecoveryRouterTest is Test {
    RecoveryRouter public router;

    address public cairnCore = makeAddr("cairnCore");
    address public randomUser = makeAddr("randomUser");

    uint256 public constant PRECISION = 1e18;

    function setUp() public {
        router = new RecoveryRouter(cairnCore);
    }

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Constructor() public view {
        assertEq(router.cairnCore(), cairnCore);
        assertEq(router.recoveryThreshold(), 0.3e18);
    }

    function test_ConstructorInitializesClassWeights() public view {
        // PRD-02 class weights
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.LIVENESS), 0.9e18);
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.RESOURCE), 0.5e18);
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.LOGIC), 0.1e18);
    }

    // ═══════════════════════════════════════════════════════════════
    // CLASSIFY AND SCORE TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_ClassifyAndScoreZeroCheckpoints() public {
        bytes32 taskId = keccak256("task1");
        uint256 escrow = 1 ether;
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp + 1 hours;
        uint256 checkpointCount = 0;

        vm.prank(cairnCore);
        (
            ICairnTypes.FailureClass failureClass,
            ICairnTypes.FailureType failureType,
            uint256 recoveryScore,
            bytes32 failureRecordCID
        ) = router.classifyAndScore(taskId, escrow, createdAt, deadline, checkpointCount);

        // Zero checkpoints = LIVENESS failure (agent never started)
        assertEq(uint8(failureClass), uint8(ICairnTypes.FailureClass.LIVENESS));
        assertEq(uint8(failureType), uint8(ICairnTypes.FailureType.HEARTBEAT_MISS));
        assertTrue(recoveryScore > 0);
        assertTrue(failureRecordCID != bytes32(0));
    }

    function test_ClassifyAndScoreFewCheckpoints() public {
        bytes32 taskId = keccak256("task2");
        uint256 escrow = 1 ether;
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp + 1 hours;
        uint256 checkpointCount = 2; // < 3 = RESOURCE

        vm.prank(cairnCore);
        (
            ICairnTypes.FailureClass failureClass,
            ICairnTypes.FailureType failureType,
            ,
        ) = router.classifyAndScore(taskId, escrow, createdAt, deadline, checkpointCount);

        // Few checkpoints = RESOURCE failure (early failure)
        assertEq(uint8(failureClass), uint8(ICairnTypes.FailureClass.RESOURCE));
        assertEq(uint8(failureType), uint8(ICairnTypes.FailureType.UPSTREAM_TIMEOUT));
    }

    function test_ClassifyAndScoreManyCheckpoints() public {
        bytes32 taskId = keccak256("task3");
        uint256 escrow = 1 ether;
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp + 1 hours;
        uint256 checkpointCount = 5; // >= 3 = LIVENESS (default)

        vm.prank(cairnCore);
        (
            ICairnTypes.FailureClass failureClass,
            ICairnTypes.FailureType failureType,
            ,
        ) = router.classifyAndScore(taskId, escrow, createdAt, deadline, checkpointCount);

        // Many checkpoints then fail = LIVENESS (default conservative)
        assertEq(uint8(failureClass), uint8(ICairnTypes.FailureClass.LIVENESS));
        assertEq(uint8(failureType), uint8(ICairnTypes.FailureType.HEARTBEAT_MISS));
    }

    function test_ClassifyAndScoreEmitsEvent() public {
        bytes32 taskId = keccak256("task4");
        uint256 escrow = 1 ether;
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp + 1 hours;
        uint256 checkpointCount = 0;

        vm.prank(cairnCore);
        vm.expectEmit(true, false, false, false);
        emit IRecoveryRouter.FailureClassified(
            taskId,
            ICairnTypes.FailureClass.LIVENESS,
            ICairnTypes.FailureType.HEARTBEAT_MISS,
            0, // score is computed
            bytes32(0) // CID is generated
        );
        router.classifyAndScore(taskId, escrow, createdAt, deadline, checkpointCount);
    }

    function test_RevertClassifyAndScoreNotCairnCore() public {
        vm.prank(randomUser);
        vm.expectRevert(IRecoveryRouter.NotAuthorized.selector);
        router.classifyAndScore(
            keccak256("task"),
            1 ether,
            block.timestamp,
            block.timestamp + 1 hours,
            0
        );
    }

    // ═══════════════════════════════════════════════════════════════
    // RECOVERY SCORE COMPUTATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_ComputeRecoveryScoreLivenessFullBudgetFullDeadline() public view {
        // LIVENESS = 0.9 weight
        // Full budget = 1.0
        // Full deadline = 1.0
        // score = (0.9 × 0.5) + (1.0 × 0.3) + (1.0 × 0.2) = 0.45 + 0.30 + 0.20 = 0.95
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS,
            PRECISION, // Full budget
            PRECISION  // Full deadline
        );

        // Expected: 0.95e18
        assertEq(score, 0.95e18);
    }

    function test_ComputeRecoveryScoreResourceHalfBudgetHalfDeadline() public view {
        // RESOURCE = 0.5 weight
        // Half budget = 0.5
        // Half deadline = 0.5
        // score = (0.5 × 0.5) + (0.5 × 0.3) + (0.5 × 0.2) = 0.25 + 0.15 + 0.10 = 0.50
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.RESOURCE,
            PRECISION / 2,
            PRECISION / 2
        );

        assertEq(score, 0.5e18);
    }

    function test_ComputeRecoveryScoreLogicNoBudgetNoDeadline() public view {
        // LOGIC = 0.1 weight
        // No budget = 0
        // No deadline = 0
        // score = (0.1 × 0.5) + (0 × 0.3) + (0 × 0.2) = 0.05
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LOGIC,
            0,
            0
        );

        assertEq(score, 0.05e18);
    }

    function test_ComputeRecoveryScoreLogicFullParams() public view {
        // LOGIC = 0.1 weight
        // Full budget = 1.0
        // Full deadline = 1.0
        // score = (0.1 × 0.5) + (1.0 × 0.3) + (1.0 × 0.2) = 0.05 + 0.30 + 0.20 = 0.55
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LOGIC,
            PRECISION,
            PRECISION
        );

        assertEq(score, 0.55e18);
    }

    function test_RecoveryScoreAboveThresholdRouteToRecovery() public view {
        // LIVENESS with full params = 0.95 > 0.3 threshold
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS,
            PRECISION,
            PRECISION
        );

        assertTrue(score >= router.recoveryThreshold());
    }

    function test_RecoveryScoreBelowThresholdRouteToDispute() public view {
        // LOGIC with no budget/deadline = 0.05 < 0.3 threshold
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LOGIC,
            0,
            0
        );

        assertTrue(score < router.recoveryThreshold());
    }

    // ═══════════════════════════════════════════════════════════════
    // DEADLINE REMAINING TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_DeadlineRemainingFullTime() public {
        bytes32 taskId = keccak256("deadline_test_1");
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp + 1 hours;

        // At creation, full deadline remaining
        vm.prank(cairnCore);
        (,, uint256 score,) = router.classifyAndScore(taskId, 1 ether, createdAt, deadline, 0);

        // With LIVENESS and full budget, score should be high
        assertTrue(score > 0.9e18);
    }

    function test_DeadlineRemainingHalfTime() public {
        bytes32 taskId = keccak256("deadline_test_2");
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp + 1 hours;

        // Warp to halfway
        vm.warp(block.timestamp + 30 minutes);

        vm.prank(cairnCore);
        (,, uint256 score,) = router.classifyAndScore(taskId, 1 ether, createdAt, deadline, 0);

        // Score should be lower than full deadline
        // LIVENESS × 0.5 + budget × 0.3 + 0.5 deadline × 0.2 = 0.45 + 0.30 + 0.10 = 0.85
        assertEq(score, 0.85e18);
    }

    function test_DeadlineRemainingExpired() public {
        bytes32 taskId = keccak256("deadline_test_3");
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp + 1 hours;

        // Warp past deadline
        vm.warp(block.timestamp + 2 hours);

        vm.prank(cairnCore);
        (,, uint256 score,) = router.classifyAndScore(taskId, 1 ether, createdAt, deadline, 0);

        // Deadline component should be 0
        // LIVENESS × 0.5 + budget × 0.3 + 0 deadline × 0.2 = 0.45 + 0.30 + 0 = 0.75
        assertEq(score, 0.75e18);
    }

    // ═══════════════════════════════════════════════════════════════
    // FAILURE RECORD CID TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_UniqueFailureRecordCIDs() public {
        bytes32 taskId1 = keccak256("task_cid_1");
        bytes32 taskId2 = keccak256("task_cid_2");

        vm.startPrank(cairnCore);
        (,,, bytes32 cid1) = router.classifyAndScore(taskId1, 1 ether, block.timestamp, block.timestamp + 1 hours, 0);
        (,,, bytes32 cid2) = router.classifyAndScore(taskId2, 1 ether, block.timestamp, block.timestamp + 1 hours, 0);
        vm.stopPrank();

        // CIDs should be unique
        assertTrue(cid1 != cid2);
    }

    function test_FailureRecordCIDEmitsEvent() public {
        bytes32 taskId = keccak256("task_cid_event");

        vm.prank(cairnCore);
        vm.expectEmit(true, false, false, false);
        emit IRecoveryRouter.FailureRecordCreated(
            taskId,
            bytes32(0), // CID generated
            ICairnTypes.FailureClass.LIVENESS,
            ICairnTypes.FailureType.HEARTBEAT_MISS,
            block.timestamp
        );
        router.classifyAndScore(taskId, 1 ether, block.timestamp, block.timestamp + 1 hours, 0);
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_GetClassWeight() public view {
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.LIVENESS), 0.9e18);
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.RESOURCE), 0.5e18);
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.LOGIC), 0.1e18);
    }

    function test_RecoveryThreshold() public view {
        assertEq(router.recoveryThreshold(), 0.3e18);
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_SetCairnCore() public {
        address newCairnCore = makeAddr("newCairnCore");
        router.setCairnCore(newCairnCore);
        assertEq(router.cairnCore(), newCairnCore);
    }

    function test_SetRecoveryThreshold() public {
        uint256 newThreshold = 0.5e18;
        router.setRecoveryThreshold(newThreshold);
        assertEq(router.recoveryThreshold(), newThreshold);
    }

    function test_RevertSetRecoveryThresholdTooLow() public {
        vm.expectRevert("Invalid threshold");
        router.setRecoveryThreshold(0.05e18);
    }

    function test_RevertSetRecoveryThresholdTooHigh() public {
        vm.expectRevert("Invalid threshold");
        router.setRecoveryThreshold(0.95e18);
    }

    function test_SetRecoveryThresholdBoundaries() public {
        // Valid: 0.1e18 - 0.9e18
        router.setRecoveryThreshold(0.1e18);
        assertEq(router.recoveryThreshold(), 0.1e18);

        router.setRecoveryThreshold(0.9e18);
        assertEq(router.recoveryThreshold(), 0.9e18);
    }

    // ═══════════════════════════════════════════════════════════════
    // EDGE CASES
    // ═══════════════════════════════════════════════════════════════

    function test_ZeroDurationDeadline() public {
        bytes32 taskId = keccak256("zero_duration");
        uint256 createdAt = block.timestamp;
        uint256 deadline = block.timestamp; // Same as creation = 0 duration

        vm.prank(cairnCore);
        (,, uint256 score,) = router.classifyAndScore(taskId, 1 ether, createdAt, deadline, 0);

        // Score should still compute (deadline component = 0)
        // LIVENESS × 0.5 + budget × 0.3 + 0 = 0.75
        assertEq(score, 0.75e18);
    }

    function test_ZeroEscrowAmount() public {
        bytes32 taskId = keccak256("zero_escrow");

        vm.prank(cairnCore);
        (,, uint256 score,) = router.classifyAndScore(taskId, 0, block.timestamp, block.timestamp + 1 hours, 0);

        // Budget remaining = 0 (no escrow)
        // LIVENESS × 0.5 + 0 × 0.3 + deadline × 0.2 = 0.45 + 0 + 0.20 = 0.65
        assertEq(score, 0.65e18);
    }

    function test_ConsistentClassificationForSameParams() public {
        bytes32 taskId1 = keccak256("consistent_1");
        bytes32 taskId2 = keccak256("consistent_2");

        vm.startPrank(cairnCore);
        (
            ICairnTypes.FailureClass class1,
            ICairnTypes.FailureType type1,
            ,
        ) = router.classifyAndScore(taskId1, 1 ether, block.timestamp, block.timestamp + 1 hours, 5);

        (
            ICairnTypes.FailureClass class2,
            ICairnTypes.FailureType type2,
            ,
        ) = router.classifyAndScore(taskId2, 1 ether, block.timestamp, block.timestamp + 1 hours, 5);
        vm.stopPrank();

        // Same checkpoint count should yield same classification
        assertEq(uint8(class1), uint8(class2));
        assertEq(uint8(type1), uint8(type2));
    }

    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_WeightConstants() public view {
        assertEq(router.FAILURE_CLASS_WEIGHT(), 0.5e18);
        assertEq(router.BUDGET_WEIGHT(), 0.3e18);
        assertEq(router.DEADLINE_WEIGHT(), 0.2e18);
        assertEq(router.PRECISION(), 1e18);
        assertEq(router.DEFAULT_THRESHOLD(), 0.3e18);
    }

    function test_WeightsSumToOne() public view {
        uint256 totalWeight = router.FAILURE_CLASS_WEIGHT() + router.BUDGET_WEIGHT() + router.DEADLINE_WEIGHT();
        assertEq(totalWeight, 1e18);
    }
}
