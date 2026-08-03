// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {RecoveryRouter} from "../src/RecoveryRouter.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {ICairnCore} from "../src/interfaces/ICairnCore.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";
import {IERC8183} from "../src/interfaces/IERC8183.sol";

/// @notice Minimal ERC-8183 hook that records that each callback fired.
contract MockEscrowHook is IERC8183 {
    bool public submitted;
    bool public checkpointed;
    bool public completed;
    bool public settled;

    function onTaskSubmitted(bytes32, address, uint256) external { submitted = true; }
    function onCheckpoint(bytes32, bytes32) external { checkpointed = true; }
    function onTaskCompleted(bytes32, bool) external { completed = true; }
    function onSettlement(bytes32, uint256, uint256) external { settled = true; }
}

/// @title CairnCore coverage top-ups (PRD-04 Phase 6)
/// @notice Exercises the ERC-8183 hook path, the timeout-refund path, and the
///         intelligence-with-history path to bring CairnCore over the 95% gate.
contract CairnCoreCoverageTest is Test {
    CairnCore core;
    RecoveryRouter router;
    FallbackPool pool;
    ArbiterRegistry registry;
    CairnGovernance governance;
    MockEscrowHook hook;

    address admin = makeAddr("admin");
    address feeRecipient = makeAddr("feeRecipient");
    address operator = makeAddr("operator");
    address primaryAgent = makeAddr("primaryAgent");
    address fallbackAgent = makeAddr("fallbackAgent");

    bytes32 specHash = keccak256("task spec");
    bytes32 taskType = keccak256("defi.swap");

    function setUp() public {
        governance = new CairnGovernance(admin);
        core = new CairnCore(feeRecipient, address(0), address(0), address(0), address(governance));
        router = new RecoveryRouter(address(core));
        pool = new FallbackPool(address(core), feeRecipient, address(0), address(0), address(0));
        registry = new ArbiterRegistry(address(core), address(governance), feeRecipient);
        hook = new MockEscrowHook();

        vm.prank(address(governance));
        core.setContracts(address(router), address(pool), address(registry));

        vm.deal(operator, 100 ether);
        vm.deal(address(core), 10 ether);

        bytes32[] memory tt = new bytes32[](1);
        tt[0] = taskType;
        vm.deal(fallbackAgent, 2 ether);
        vm.prank(fallbackAgent);
        pool.register{value: 1 ether}(tt, 5);
    }

    function _submitStart(bytes32 tType) internal returns (bytes32 taskId) {
        vm.prank(operator);
        taskId = core.submitTask{value: 0.1 ether}(
            tType, specHash, primaryAgent, 60, block.timestamp + 1 hours
        );
        vm.prank(primaryAgent);
        core.startTask(taskId);
    }

    // ─── ERC-8183 hook path ───────────────────────────────────────

    function test_EscrowHook_FiresAcrossLifecycle() public {
        vm.prank(address(governance));
        core.setEscrowHook(address(hook));

        bytes32 taskId = _submitStart(taskType);
        assertTrue(hook.submitted(), "onTaskSubmitted");

        vm.prank(primaryAgent);
        core.commitCheckpointBatch(taskId, 1, keccak256("r"), keccak256("c"), specHash);
        assertTrue(hook.checkpointed(), "onCheckpoint");

        vm.prank(primaryAgent);
        core.completeTask(taskId);
        assertTrue(hook.completed(), "onTaskCompleted");
    }

    // ─── timeout-refund path (no fallback → DISPUTED → refund) ─────

    function test_TimeoutRefund_ReturnsEscrowToOperator() public {
        vm.prank(address(governance));
        core.setEscrowHook(address(hook));

        // Unregistered task type → no fallback selected → routes to DISPUTED
        bytes32 taskId = _submitStart(keccak256("no.fallback"));
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);
        assertEq(uint8(core.getTask(taskId).state), uint8(ICairnTypes.TaskState.DISPUTED));

        uint256 opBefore = operator.balance;
        vm.warp(block.timestamp + 7 days + 1);
        core.resolveDisputeTimeout(taskId);

        assertEq(uint8(core.getTask(taskId).state), uint8(ICairnTypes.TaskState.RESOLVED));
        assertEq(operator.balance - opBefore, 0.1 ether, "full escrow refunded");
        assertTrue(hook.settled(), "onSettlement fired on refund");
    }

    // ─── intelligence with history ────────────────────────────────

    function test_Intelligence_WithResolvedHistory() public {
        // First task of the type: submit, run, complete → RESOLVED SUCCESS
        bytes32 t1 = _submitStart(taskType);
        vm.prank(primaryAgent);
        core.commitCheckpointBatch(t1, 1, keccak256("r"), keccak256("c"), specHash);
        vm.prank(primaryAgent);
        core.completeTask(t1);

        // Second task of the same type: startTask now queries non-empty history
        bytes32 t2 = _submitStart(taskType);
        assertEq(uint8(core.getTask(t2).state), uint8(ICairnTypes.TaskState.RUNNING));

        // History view is populated
        assertGe(core.getTaskTypeHistory(taskType).length, 2);
    }

    // ─── commit in a terminal state reverts ───────────────────────

    function test_CommitCheckpoint_RevertsAfterResolved() public {
        bytes32 taskId = _submitStart(taskType);
        vm.prank(primaryAgent);
        core.completeTask(taskId); // → RESOLVED

        vm.prank(primaryAgent);
        vm.expectRevert();
        core.commitCheckpointBatch(taskId, 1, keccak256("r"), keccak256("c"), specHash);
    }
}
