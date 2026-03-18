// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import { Test, console } from "forge-std/Test.sol";
import { CairnTaskMVP } from "../src/CairnTaskMVP.sol";
import { ICairnTaskMVP } from "../src/interfaces/ICairnTaskMVP.sol";

contract CairnTaskMVPTest is Test {
    CairnTaskMVP public cairn;

    address public owner = makeAddr("owner");
    address public feeRecipient = makeAddr("feeRecipient");
    address public operator = makeAddr("operator");
    address public primaryAgent = makeAddr("primaryAgent");
    address public fallbackAgent = makeAddr("fallbackAgent");
    address public randomUser = makeAddr("randomUser");

    uint256 public constant MIN_ESCROW = 0.001 ether;
    uint256 public constant MIN_HEARTBEAT = 30;
    uint256 public constant PROTOCOL_FEE_BPS = 50;

    bytes32 public specHash = keccak256("task spec");
    bytes32 public cid1 = keccak256("checkpoint1");
    bytes32 public cid2 = keccak256("checkpoint2");
    bytes32 public cid3 = keccak256("checkpoint3");

    function setUp() public {
        cairn = new CairnTaskMVP(owner, feeRecipient);
        vm.deal(operator, 10 ether);
        vm.deal(primaryAgent, 1 ether);
        vm.deal(fallbackAgent, 1 ether);
    }

    // ============ Helper Functions ============

    function _submitTask() internal returns (bytes32) {
        uint256 deadline = block.timestamp + 1 hours;
        vm.prank(operator);
        return cairn.submitTask{value: 0.1 ether}(primaryAgent, fallbackAgent, specHash, 60, deadline);
    }

    function _submitTaskWithParams(uint256 escrow, uint256 heartbeat, uint256 deadlineOffset) internal returns (bytes32) {
        uint256 deadline = block.timestamp + deadlineOffset;
        vm.prank(operator);
        return cairn.submitTask{value: escrow}(primaryAgent, fallbackAgent, specHash, heartbeat, deadline);
    }

    // ============ Constructor Tests ============

    function test_Constructor() public view {
        assertEq(cairn.owner(), owner);
        assertEq(cairn.feeRecipient(), feeRecipient);
    }

    function test_RevertConstructorZeroFeeRecipient() public {
        vm.expectRevert(ICairnTaskMVP.InvalidAddress.selector);
        new CairnTaskMVP(owner, address(0));
    }

    // ============ submitTask Tests ============

    function test_SubmitTask() public {
        bytes32 taskId = _submitTask();
        
        (ICairnTaskMVP.State state, address op, address primary, address fallback_, uint256 escrow, uint256 primaryCp, uint256 fallbackCp, uint256 lastHb, uint256 deadline) = cairn.getTask(taskId);
        
        assertEq(uint8(state), uint8(ICairnTaskMVP.State.RUNNING));
        assertEq(op, operator);
        assertEq(primary, primaryAgent);
        assertEq(fallback_, fallbackAgent);
        assertEq(escrow, 0.1 ether);
        assertEq(primaryCp, 0);
        assertEq(fallbackCp, 0);
        assertEq(lastHb, block.timestamp);
        assertEq(deadline, block.timestamp + 1 hours);
    }

    function test_SubmitTaskEmitsEvent() public {
        uint256 deadline = block.timestamp + 1 hours;
        vm.prank(operator);
        vm.expectEmit(false, true, false, true);
        emit ICairnTaskMVP.TaskSubmitted(bytes32(0), operator, primaryAgent, fallbackAgent, 0.1 ether);
        cairn.submitTask{value: 0.1 ether}(primaryAgent, fallbackAgent, specHash, 60, deadline);
    }

    function test_RevertSubmitTaskZeroPrimaryAgent() public {
        vm.prank(operator);
        vm.expectRevert(ICairnTaskMVP.InvalidAddress.selector);
        cairn.submitTask{value: 0.1 ether}(address(0), fallbackAgent, specHash, 60, block.timestamp + 1 hours);
    }

    function test_RevertSubmitTaskZeroFallbackAgent() public {
        vm.prank(operator);
        vm.expectRevert(ICairnTaskMVP.InvalidAddress.selector);
        cairn.submitTask{value: 0.1 ether}(primaryAgent, address(0), specHash, 60, block.timestamp + 1 hours);
    }

    function test_RevertSubmitTaskInsufficientEscrow() public {
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(ICairnTaskMVP.InsufficientEscrow.selector, MIN_ESCROW, 0.0001 ether));
        cairn.submitTask{value: 0.0001 ether}(primaryAgent, fallbackAgent, specHash, 60, block.timestamp + 1 hours);
    }

    function test_RevertSubmitTaskInvalidHeartbeat() public {
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(ICairnTaskMVP.InvalidHeartbeatInterval.selector, MIN_HEARTBEAT, 10));
        cairn.submitTask{value: 0.1 ether}(primaryAgent, fallbackAgent, specHash, 10, block.timestamp + 1 hours);
    }

    function test_RevertSubmitTaskInvalidDeadline() public {
        vm.prank(operator);
        vm.expectRevert(ICairnTaskMVP.InvalidDeadline.selector);
        cairn.submitTask{value: 0.1 ether}(primaryAgent, fallbackAgent, specHash, 60, block.timestamp - 1);
    }

    function test_SubmitTaskMinimumEscrow() public {
        bytes32 taskId = _submitTaskWithParams(MIN_ESCROW, 30, 1 hours);
        (,,,, uint256 escrow,,,,) = cairn.getTask(taskId);
        assertEq(escrow, MIN_ESCROW);
    }

    // ============ commitCheckpoint Tests ============

    function test_CommitCheckpoint() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        
        bytes32[] memory cids = cairn.getCheckpoints(taskId);
        assertEq(cids.length, 1);
        assertEq(cids[0], cid1);
        
        (,,,,,uint256 primaryCp,,,) = cairn.getTask(taskId);
        assertEq(primaryCp, 1);
    }

    function test_CommitMultipleCheckpoints() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid2);
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid3);
        
        bytes32[] memory cids = cairn.getCheckpoints(taskId);
        assertEq(cids.length, 3);
        
        (,,,,,uint256 primaryCp,,,) = cairn.getTask(taskId);
        assertEq(primaryCp, 3);
    }

    function test_CommitCheckpointEmitsEvent() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        vm.expectEmit(true, false, false, true);
        emit ICairnTaskMVP.CheckpointCommitted(taskId, 0, cid1, primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
    }

    function test_RevertCommitCheckpointUnauthorized() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(randomUser);
        vm.expectRevert(ICairnTaskMVP.Unauthorized.selector);
        cairn.commitCheckpoint(taskId, cid1);
    }

    function test_RevertCommitCheckpointInvalidCID() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        vm.expectRevert(ICairnTaskMVP.InvalidCID.selector);
        cairn.commitCheckpoint(taskId, bytes32(0));
    }

    function test_RevertCommitCheckpointTaskNotFound() public {
        vm.prank(primaryAgent);
        vm.expectRevert(ICairnTaskMVP.TaskNotFound.selector);
        cairn.commitCheckpoint(bytes32(uint256(123)), cid1);
    }

    function test_RevertCommitCheckpointAfterDeadline() public {
        bytes32 taskId = _submitTask();
        
        vm.warp(block.timestamp + 2 hours);
        
        vm.prank(primaryAgent);
        vm.expectRevert(ICairnTaskMVP.DeadlineExceeded.selector);
        cairn.commitCheckpoint(taskId, cid1);
    }

    // ============ heartbeat Tests ============

    function test_Heartbeat() public {
        bytes32 taskId = _submitTask();
        
        uint256 initialHb = block.timestamp;
        vm.warp(block.timestamp + 30);
        
        vm.prank(primaryAgent);
        cairn.heartbeat(taskId);
        
        (,,,,,,,uint256 lastHb,) = cairn.getTask(taskId);
        assertEq(lastHb, initialHb + 30);
    }

    function test_HeartbeatEmitsEvent() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        vm.expectEmit(true, false, false, true);
        emit ICairnTaskMVP.HeartbeatReceived(taskId, block.timestamp);
        cairn.heartbeat(taskId);
    }

    function test_RevertHeartbeatUnauthorized() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(fallbackAgent);
        vm.expectRevert(ICairnTaskMVP.Unauthorized.selector);
        cairn.heartbeat(taskId);
    }

    function test_RevertHeartbeatAfterDeadline() public {
        bytes32 taskId = _submitTask();
        
        vm.warp(block.timestamp + 2 hours);
        
        vm.prank(primaryAgent);
        vm.expectRevert(ICairnTaskMVP.DeadlineExceeded.selector);
        cairn.heartbeat(taskId);
    }

    // ============ checkLiveness Tests ============

    function test_CheckLiveness() public {
        bytes32 taskId = _submitTask();
        
        // Warp past heartbeat interval
        vm.warp(block.timestamp + 61);
        
        cairn.checkLiveness(taskId);
        
        (ICairnTaskMVP.State state,,,,,,,, ) = cairn.getTask(taskId);
        assertEq(uint8(state), uint8(ICairnTaskMVP.State.RECOVERING));
    }

    function test_CheckLivenessEmitsEvents() public {
        bytes32 taskId = _submitTask();
        
        vm.warp(block.timestamp + 61);
        
        vm.expectEmit(true, false, false, true);
        emit ICairnTaskMVP.TaskFailed(taskId, "HEARTBEAT_MISS");
        vm.expectEmit(true, false, false, true);
        emit ICairnTaskMVP.FallbackAssigned(taskId, fallbackAgent);
        cairn.checkLiveness(taskId);
    }

    function test_RevertCheckLivenessNotStale() public {
        bytes32 taskId = _submitTask();
        
        vm.expectRevert(ICairnTaskMVP.NotStale.selector);
        cairn.checkLiveness(taskId);
    }

    function test_RevertCheckLivenessWrongState() public {
        bytes32 taskId = _submitTask();
        
        // First trigger failure
        vm.warp(block.timestamp + 61);
        cairn.checkLiveness(taskId);
        
        // Try again - should fail as state is RECOVERING
        vm.warp(block.timestamp + 61);
        vm.expectRevert(abi.encodeWithSelector(ICairnTaskMVP.InvalidState.selector, ICairnTaskMVP.State.RUNNING, ICairnTaskMVP.State.RECOVERING));
        cairn.checkLiveness(taskId);
    }

    function test_IsStale() public {
        bytes32 taskId = _submitTask();
        
        assertFalse(cairn.isStale(taskId));
        
        vm.warp(block.timestamp + 61);
        assertTrue(cairn.isStale(taskId));
    }

    // ============ completeTask Tests ============

    function test_CompleteTask() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        
        vm.prank(primaryAgent);
        cairn.completeTask(taskId);
        
        (ICairnTaskMVP.State state,,,,,,,, ) = cairn.getTask(taskId);
        assertEq(uint8(state), uint8(ICairnTaskMVP.State.RESOLVED));
    }

    function test_CompleteTaskEmitsEvent() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        vm.expectEmit(true, false, false, true);
        emit ICairnTaskMVP.TaskCompleted(taskId, primaryAgent);
        cairn.completeTask(taskId);
    }

    function test_RevertCompleteTaskUnauthorized() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(fallbackAgent);
        vm.expectRevert(ICairnTaskMVP.Unauthorized.selector);
        cairn.completeTask(taskId);
    }

    function test_RevertCompleteTaskAfterDeadline() public {
        bytes32 taskId = _submitTask();
        
        vm.warp(block.timestamp + 2 hours);
        
        vm.prank(primaryAgent);
        vm.expectRevert(ICairnTaskMVP.DeadlineExceeded.selector);
        cairn.completeTask(taskId);
    }

    // ============ settle Tests ============

    function test_SettleHappyPath() public {
        bytes32 taskId = _submitTask();
        
        // Primary commits 5 checkpoints and completes
        for (uint i = 0; i < 5; i++) {
            vm.prank(primaryAgent);
            cairn.commitCheckpoint(taskId, keccak256(abi.encode("cp", i)));
        }
        
        vm.prank(primaryAgent);
        cairn.completeTask(taskId);
        
        uint256 primaryBalanceBefore = primaryAgent.balance;
        uint256 feeRecipientBalanceBefore = feeRecipient.balance;
        
        cairn.settle(taskId);
        
        // Primary gets 99.5%
        uint256 escrow = 0.1 ether;
        uint256 fee = (escrow * PROTOCOL_FEE_BPS) / 10000;
        uint256 primaryExpected = escrow - fee;
        
        assertEq(primaryAgent.balance - primaryBalanceBefore, primaryExpected);
        assertEq(feeRecipient.balance - feeRecipientBalanceBefore, fee);
    }

    function test_SettleRecoveryPath() public {
        bytes32 taskId = _submitTask();
        
        // Primary commits 3 checkpoints
        for (uint i = 0; i < 3; i++) {
            vm.prank(primaryAgent);
            cairn.commitCheckpoint(taskId, keccak256(abi.encode("cp", i)));
        }
        
        // Primary fails (heartbeat miss)
        vm.warp(block.timestamp + 61);
        cairn.checkLiveness(taskId);
        
        // Fallback commits 2 checkpoints and completes
        for (uint i = 3; i < 5; i++) {
            vm.prank(fallbackAgent);
            cairn.commitCheckpoint(taskId, keccak256(abi.encode("cp", i)));
        }
        
        vm.prank(fallbackAgent);
        cairn.completeTask(taskId);
        
        uint256 primaryBalanceBefore = primaryAgent.balance;
        uint256 fallbackBalanceBefore = fallbackAgent.balance;
        uint256 feeRecipientBalanceBefore = feeRecipient.balance;
        
        cairn.settle(taskId);
        
        // Calculate expected shares (3/5 = 60% primary, 2/5 = 40% fallback)
        uint256 escrow = 0.1 ether;
        uint256 fee = (escrow * PROTOCOL_FEE_BPS) / 10000;
        uint256 distributable = escrow - fee;
        uint256 primaryExpected = (distributable * 3) / 5;
        uint256 fallbackExpected = distributable - primaryExpected;
        
        assertEq(primaryAgent.balance - primaryBalanceBefore, primaryExpected);
        assertEq(fallbackAgent.balance - fallbackBalanceBefore, fallbackExpected);
        assertEq(feeRecipient.balance - feeRecipientBalanceBefore, fee);
    }

    function test_SettleZeroCheckpointsRefund() public {
        bytes32 taskId = _submitTask();
        
        // Warp past deadline
        vm.warp(block.timestamp + 2 hours);
        
        uint256 operatorBalanceBefore = operator.balance;
        
        cairn.settle(taskId);
        
        // Full refund to operator
        assertEq(operator.balance - operatorBalanceBefore, 0.1 ether);
    }

    function test_SettleEmitsEvent() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        vm.prank(primaryAgent);
        cairn.completeTask(taskId);
        
        uint256 escrow = 0.1 ether;
        uint256 fee = (escrow * PROTOCOL_FEE_BPS) / 10000;
        uint256 primaryShare = escrow - fee;
        
        vm.expectEmit(true, false, false, true);
        emit ICairnTaskMVP.TaskResolved(taskId, primaryShare, 0, fee);
        cairn.settle(taskId);
    }

    function test_RevertSettleAlreadySettled() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        cairn.completeTask(taskId);
        cairn.settle(taskId);
        
        vm.expectRevert(ICairnTaskMVP.AlreadySettled.selector);
        cairn.settle(taskId);
    }

    function test_RevertSettleNotResolvedNotDeadline() public {
        bytes32 taskId = _submitTask();
        
        vm.expectRevert(abi.encodeWithSelector(ICairnTaskMVP.InvalidState.selector, ICairnTaskMVP.State.RESOLVED, ICairnTaskMVP.State.RUNNING));
        cairn.settle(taskId);
    }

    function test_SettleAfterDeadlineAutoResolves() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        
        // Warp past deadline without completing
        vm.warp(block.timestamp + 2 hours);
        
        cairn.settle(taskId);
        
        (ICairnTaskMVP.State state,,,,,,,, ) = cairn.getTask(taskId);
        assertEq(uint8(state), uint8(ICairnTaskMVP.State.RESOLVED));
    }

    // ============ View Function Tests ============

    function test_ProtocolFeeBps() public view {
        assertEq(cairn.protocolFeeBps(), PROTOCOL_FEE_BPS);
    }

    function test_MinEscrow() public view {
        assertEq(cairn.minEscrow(), MIN_ESCROW);
    }

    function test_MinHeartbeatInterval() public view {
        assertEq(cairn.minHeartbeatInterval(), MIN_HEARTBEAT);
    }

    // ============ Admin Function Tests ============

    function test_SetFeeRecipient() public {
        address newFeeRecipient = makeAddr("newFeeRecipient");
        
        vm.prank(owner);
        cairn.setFeeRecipient(newFeeRecipient);
        
        assertEq(cairn.feeRecipient(), newFeeRecipient);
    }

    function test_RevertSetFeeRecipientNotOwner() public {
        vm.prank(randomUser);
        vm.expectRevert();
        cairn.setFeeRecipient(makeAddr("newFeeRecipient"));
    }

    function test_RevertSetFeeRecipientZeroAddress() public {
        vm.prank(owner);
        vm.expectRevert(ICairnTaskMVP.InvalidAddress.selector);
        cairn.setFeeRecipient(address(0));
    }

    // ============ Recovery Flow E2E Tests ============

    function test_FullRecoveryFlow() public {
        // 1. Operator submits task
        bytes32 taskId = _submitTask();
        
        // 2. Primary works on task (3 checkpoints)
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        vm.warp(block.timestamp + 30);
        vm.prank(primaryAgent);
        cairn.heartbeat(taskId);
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid2);
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid3);
        
        // 3. Primary fails (heartbeat miss)
        vm.warp(block.timestamp + 61);
        cairn.checkLiveness(taskId);
        
        // 4. Fallback picks up (2 checkpoints)
        vm.prank(fallbackAgent);
        cairn.commitCheckpoint(taskId, keccak256("checkpoint4"));
        vm.warp(block.timestamp + 30);
        vm.prank(fallbackAgent);
        cairn.heartbeat(taskId);
        vm.prank(fallbackAgent);
        cairn.commitCheckpoint(taskId, keccak256("checkpoint5"));
        
        // 5. Fallback completes task
        vm.prank(fallbackAgent);
        cairn.completeTask(taskId);
        
        // 6. Settlement
        (,,,,,uint256 primaryCp, uint256 fallbackCp,,) = cairn.getTask(taskId);
        assertEq(primaryCp, 3);
        assertEq(fallbackCp, 2);
        
        uint256 primaryBalanceBefore = primaryAgent.balance;
        uint256 fallbackBalanceBefore = fallbackAgent.balance;
        
        cairn.settle(taskId);
        
        // Verify 60/40 split (minus protocol fee)
        uint256 escrow = 0.1 ether;
        uint256 fee = (escrow * PROTOCOL_FEE_BPS) / 10000;
        uint256 distributable = escrow - fee;
        
        assertEq(primaryAgent.balance - primaryBalanceBefore, (distributable * 3) / 5);
        assertEq(fallbackAgent.balance - fallbackBalanceBefore, distributable - (distributable * 3) / 5);
    }

    // ============ Edge Case Tests ============

    function test_HeartbeatExactlyAtInterval() public {
        bytes32 taskId = _submitTask();
        
        // Warp exactly to interval boundary
        vm.warp(block.timestamp + 60);
        
        // Should not be stale yet (need to exceed interval)
        assertFalse(cairn.isStale(taskId));
        
        // Heartbeat should work
        vm.prank(primaryAgent);
        cairn.heartbeat(taskId);
    }

    function test_CheckpointUpdatesHeartbeat() public {
        bytes32 taskId = _submitTask();
        
        uint256 initialTime = block.timestamp;
        vm.warp(block.timestamp + 30);
        
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        
        (,,,,,,,uint256 lastHb,) = cairn.getTask(taskId);
        assertEq(lastHb, initialTime + 30);
    }

    function test_FallbackCannotActBeforeAssignment() public {
        bytes32 taskId = _submitTask();
        
        // Fallback tries to checkpoint before being assigned
        vm.prank(fallbackAgent);
        vm.expectRevert(ICairnTaskMVP.Unauthorized.selector);
        cairn.commitCheckpoint(taskId, cid1);
    }

    function test_PrimaryCannotActAfterFailure() public {
        bytes32 taskId = _submitTask();
        
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId, cid1);
        
        // Trigger failure
        vm.warp(block.timestamp + 61);
        cairn.checkLiveness(taskId);
        
        // Primary tries to checkpoint after failure
        vm.prank(primaryAgent);
        vm.expectRevert(ICairnTaskMVP.Unauthorized.selector);
        cairn.commitCheckpoint(taskId, cid2);
    }

    function test_MultipleTasksIndependent() public {
        bytes32 taskId1 = _submitTask();
        bytes32 taskId2 = _submitTask();
        
        // Work on task 1
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId1, cid1);
        
        // Work on task 2
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId2, cid2);
        vm.prank(primaryAgent);
        cairn.commitCheckpoint(taskId2, cid3);
        
        // Verify independence
        (,,,,,uint256 cp1,,,) = cairn.getTask(taskId1);
        (,,,,,uint256 cp2,,,) = cairn.getTask(taskId2);
        
        assertEq(cp1, 1);
        assertEq(cp2, 2);
    }
}
