// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {RecoveryRouter} from "../src/RecoveryRouter.sol";
import {RecoveryRouterV2} from "../src/RecoveryRouterV2.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {ICairnCore} from "../src/interfaces/ICairnCore.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";
import {FailureTaxonomy} from "../src/libraries/FailureTaxonomy.sol";

/// @dev Exposes the internal library for direct testing.
contract FailureTaxonomyHarness {
    function classOf(ICairnTypes.FailureType t) external pure returns (ICairnTypes.FailureClass) {
        return FailureTaxonomy.classOf(t);
    }

    function isMechanicalOnly(ICairnTypes.FailureType t) external pure returns (bool) {
        return FailureTaxonomy.isMechanicalOnly(t);
    }

    function classify(ICairnTypes.FailureEvidence calldata ev)
        external
        pure
        returns (ICairnTypes.FailureClass, ICairnTypes.FailureType)
    {
        return FailureTaxonomy.classify(ev);
    }

    function budgetRemaining(uint256 escrow, uint256 cost) external pure returns (uint256) {
        return FailureTaxonomy.budgetRemaining(escrow, cost);
    }

    function deadlineRemaining(uint256 createdAt, uint256 deadline) external view returns (uint256) {
        return FailureTaxonomy.deadlineRemaining(createdAt, deadline);
    }
}

/// @title Failure evidence, reported cost (B), and deadline detection
/// @notice Covers PRD-06: evidence-derived failure classes, the budget input
///         B = (escrow - costAccrued) / escrow, agent failure reports, and deadline
///         expiry as mechanical failure evidence.
contract FailureEvidenceTest is Test {
    CairnCore public core;
    RecoveryRouterV2 public router;
    FallbackPool public pool;
    ArbiterRegistry public registry;
    CairnGovernance public governance;
    FailureTaxonomyHarness public tax;

    address public admin = makeAddr("admin");
    address public feeRecipient = makeAddr("feeRecipient");
    address public operator = makeAddr("operator");
    address public primaryAgent = makeAddr("primaryAgent");
    address public fallbackAgent = makeAddr("fallbackAgent");
    address public stranger = makeAddr("stranger");

    bytes32 public specHash = keccak256("task spec");
    bytes32 public taskType = keccak256("defi.swap");
    bytes32 public constant EVIDENCE = keccak256("evidence");

    uint256 constant ESCROW = 0.1 ether;
    uint256 constant HEARTBEAT = 60;
    uint256 constant DURATION = 1 hours;

    function setUp() public {
        governance = new CairnGovernance(admin);
        core = new CairnCore(feeRecipient, address(0), address(0), address(0), address(governance));
        router = new RecoveryRouterV2(address(core));
        pool = new FallbackPool(address(core), feeRecipient, address(0), address(0), address(0));
        registry = new ArbiterRegistry(address(core), address(governance), feeRecipient);
        tax = new FailureTaxonomyHarness();

        vm.startPrank(address(governance));
        core.setContracts(address(router), address(pool), address(registry));
        core.setThreeTierRouting(true);
        vm.stopPrank();

        vm.deal(operator, 100 ether);
        vm.deal(fallbackAgent, 10 ether);

        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType;
        vm.prank(fallbackAgent);
        pool.register{ value: 1 ether }(taskTypes, 5);
    }

    // ─── helpers ─────────────────────────────────────────────────

    function _submitAndStart() internal returns (bytes32 taskId) {
        vm.prank(operator);
        taskId = core.submitTask{ value: ESCROW }(
            taskType, specHash, primaryAgent, HEARTBEAT, block.timestamp + DURATION
        );
        vm.prank(primaryAgent);
        core.startTask(taskId);
    }

    function _ev(ICairnTypes.FailureEvidenceSource source, ICairnTypes.FailureType t, uint256 cost)
        internal
        view
        returns (ICairnTypes.FailureEvidence memory)
    {
        return ICairnTypes.FailureEvidence({
            source: source,
            reportedType: t,
            evidenceCID: bytes32(0),
            escrowAmount: 1 ether,
            costAccrued: cost,
            createdAt: block.timestamp,
            deadline: block.timestamp + DURATION,
            checkpointCount: 0
        });
    }

    // ═══════════════════════════════════════════════════════════════
    // TAXONOMY
    // ═══════════════════════════════════════════════════════════════

    function test_ClassOf_AllTypes() public view {
        ICairnTypes.FailureClass L = ICairnTypes.FailureClass.LIVENESS;
        ICairnTypes.FailureClass R = ICairnTypes.FailureClass.RESOURCE;
        ICairnTypes.FailureClass G = ICairnTypes.FailureClass.LOGIC;
        ICairnTypes.FailureClass[11] memory expected = [L, L, L, R, R, R, G, G, G, R, R];
        for (uint8 i = 0; i < 11; i++) {
            assertEq(uint8(tax.classOf(ICairnTypes.FailureType(i))), uint8(expected[i]));
        }
    }

    function test_MechanicalOnlyTypes() public view {
        for (uint8 i = 0; i < 11; i++) {
            ICairnTypes.FailureType t = ICairnTypes.FailureType(i);
            bool expected = t == ICairnTypes.FailureType.HEARTBEAT_MISS ||
                t == ICairnTypes.FailureType.DEADLINE_EXCEEDED;
            assertEq(tax.isMechanicalOnly(t), expected);
        }
    }

    function test_Classify_HeartbeatTimeout_IsLiveness() public view {
        (ICairnTypes.FailureClass c, ICairnTypes.FailureType t) = tax.classify(
            _ev(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT, ICairnTypes.FailureType.HEARTBEAT_MISS, 0)
        );
        assertEq(uint8(c), uint8(ICairnTypes.FailureClass.LIVENESS));
        assertEq(uint8(t), uint8(ICairnTypes.FailureType.HEARTBEAT_MISS));
    }

    function test_Classify_HeartbeatTimeoutWithBudgetExhausted_IsResource() public view {
        (ICairnTypes.FailureClass c, ICairnTypes.FailureType t) = tax.classify(
            _ev(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT, ICairnTypes.FailureType.HEARTBEAT_MISS, 1 ether)
        );
        assertEq(uint8(c), uint8(ICairnTypes.FailureClass.RESOURCE));
        assertEq(uint8(t), uint8(ICairnTypes.FailureType.BUDGET_EXHAUSTED));
    }

    function test_Classify_DeadlineExpired_IsResourceDeadlineExceeded() public view {
        (ICairnTypes.FailureClass c, ICairnTypes.FailureType t) = tax.classify(
            _ev(ICairnTypes.FailureEvidenceSource.DEADLINE_EXPIRED, ICairnTypes.FailureType.HEARTBEAT_MISS, 0)
        );
        assertEq(uint8(c), uint8(ICairnTypes.FailureClass.RESOURCE));
        assertEq(uint8(t), uint8(ICairnTypes.FailureType.DEADLINE_EXCEEDED));
    }

    function test_Classify_AgentReport_UsesReportedType() public view {
        (ICairnTypes.FailureClass c, ICairnTypes.FailureType t) = tax.classify(
            _ev(ICairnTypes.FailureEvidenceSource.AGENT_REPORT, ICairnTypes.FailureType.SCHEMA_MISMATCH, 0)
        );
        assertEq(uint8(c), uint8(ICairnTypes.FailureClass.LOGIC));
        assertEq(uint8(t), uint8(ICairnTypes.FailureType.SCHEMA_MISMATCH));
    }

    // ═══════════════════════════════════════════════════════════════
    // B — remaining budget
    // ═══════════════════════════════════════════════════════════════

    function test_BudgetRemaining_Values() public view {
        assertEq(tax.budgetRemaining(1 ether, 0), 1e18);
        assertEq(tax.budgetRemaining(1 ether, 0.25 ether), 0.75e18);
        assertEq(tax.budgetRemaining(1 ether, 1 ether), 0);
        assertEq(tax.budgetRemaining(1 ether, 2 ether), 0);
        assertEq(tax.budgetRemaining(0, 0), 0);
    }

    /// B is the exact floor of (escrow - cost) / escrow on the 1e18 scale, bounded by 1e18,
    /// and non-increasing in cost.
    function testFuzz_BudgetRemaining_Exact(uint128 escrow, uint128 cost, uint128 extra) public view {
        uint256 b = tax.budgetRemaining(escrow, cost);
        assertLe(b, 1e18);
        uint256 expected = (escrow == 0 || cost >= escrow)
            ? 0
            : ((uint256(escrow) - cost) * 1e18) / escrow;
        assertEq(b, expected);
        assertLe(tax.budgetRemaining(escrow, uint256(cost) + extra), b);
    }

    function test_DeadlineRemaining_Values() public {
        uint256 t0 = block.timestamp;
        assertEq(tax.deadlineRemaining(t0, t0 + 100), 1e18);
        vm.warp(t0 + 25);
        assertEq(tax.deadlineRemaining(t0, t0 + 100), 0.75e18);
        vm.warp(t0 + 100);
        assertEq(tax.deadlineRemaining(t0, t0 + 100), 0);
        assertEq(tax.deadlineRemaining(t0 + 100, t0 + 100), 0);
    }

    /// B now changes the v2 score: half the budget consumed lowers r by 0.5^0.35.
    function test_RouterV2_ScoreUsesReportedCost() public {
        vm.startPrank(address(core));
        (,, uint256 full,) = router.classifyAndScore(
            keccak256("a"),
            _ev(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT, ICairnTypes.FailureType.HEARTBEAT_MISS, 0)
        );
        (,, uint256 half,) = router.classifyAndScore(
            keccak256("b"),
            _ev(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT, ICairnTypes.FailureType.HEARTBEAT_MISS, 0.5 ether)
        );
        vm.stopPrank();

        assertEq(full, router.computeRecoveryScore(ICairnTypes.FailureClass.LIVENESS, 1e18, 1e18));
        assertEq(half, router.computeRecoveryScore(ICairnTypes.FailureClass.LIVENESS, 0.5e18, 1e18));
        assertLt(half, full);
    }

    function test_RouterV1_ScoreUsesReportedCost() public {
        RecoveryRouter v1 = new RecoveryRouter(address(this));
        (,, uint256 full,) = v1.classifyAndScore(
            keccak256("a"),
            _ev(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT, ICairnTypes.FailureType.HEARTBEAT_MISS, 0)
        );
        (,, uint256 half,) = v1.classifyAndScore(
            keccak256("b"),
            _ev(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT, ICairnTypes.FailureType.HEARTBEAT_MISS, 0.5 ether)
        );
        assertEq(half, v1.computeRecoveryScore(ICairnTypes.FailureClass.LIVENESS, 0.5e18, 1e18));
        assertLt(half, full);
    }

    // ═══════════════════════════════════════════════════════════════
    // reportCost
    // ═══════════════════════════════════════════════════════════════

    function test_ReportCost_StoresAndEmits() public {
        bytes32 taskId = _submitAndStart();
        vm.expectEmit(true, true, false, true);
        emit ICairnCore.CostReported(taskId, primaryAgent, 0.02 ether);
        vm.prank(primaryAgent);
        core.reportCost(taskId, 0.02 ether);
        assertEq(core.getTask(taskId).costAccrued, 0.02 ether);
    }

    function test_ReportCost_ClampedToEscrow() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(primaryAgent);
        core.reportCost(taskId, 5 ether);
        assertEq(core.getTask(taskId).costAccrued, ESCROW);
    }

    function test_ReportCost_NonMonotonic_Reverts() public {
        bytes32 taskId = _submitAndStart();
        vm.startPrank(primaryAgent);
        core.reportCost(taskId, 0.03 ether);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.CostNotMonotonic.selector, 0.01 ether, 0.03 ether));
        core.reportCost(taskId, 0.01 ether);
        core.reportCost(taskId, 0.03 ether); // equal is allowed
        vm.stopPrank();
    }

    function test_ReportCost_NotCurrentAgent_Reverts() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.NotAuthorized.selector, stranger, primaryAgent));
        core.reportCost(taskId, 1);
    }

    function test_ReportCost_NotActive_Reverts() public {
        vm.prank(operator);
        bytes32 taskId = core.submitTask{ value: ESCROW }(
            taskType, specHash, primaryAgent, HEARTBEAT, block.timestamp + DURATION
        );
        vm.prank(primaryAgent);
        vm.expectRevert(
            abi.encodeWithSelector(
                ICairnCore.InvalidState.selector, ICairnTypes.TaskState.IDLE, ICairnTypes.TaskState.RUNNING
            )
        );
        core.reportCost(taskId, 1);
    }

    function test_ReportCost_WhenPaused_Reverts() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(address(governance));
        core.pause();
        vm.prank(primaryAgent);
        vm.expectRevert();
        core.reportCost(taskId, 1);
    }

    /// The score CairnCore stores uses the reported cost and the current deadline fraction.
    function test_DetectFailure_ScoreReflectsReportedCost() public {
        bytes32 taskId = _submitAndStart();
        ICairnCore.Task memory t0 = core.getTask(taskId);
        vm.prank(primaryAgent);
        core.reportCost(taskId, ESCROW / 2);

        vm.warp(block.timestamp + 2 * HEARTBEAT + 1);
        core.detectFailure(taskId);

        uint256 d = tax.deadlineRemaining(t0.createdAt, t0.deadline);
        uint256 expected = router.computeRecoveryScore(ICairnTypes.FailureClass.LIVENESS, 0.5e18, d);
        ICairnCore.Task memory t = core.getTask(taskId);
        assertEq(t.recoveryScore, expected);
        assertEq(uint8(t.failureEvidenceSource), uint8(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT));
    }

    function test_DetectFailure_BudgetExhausted_IsResource() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(primaryAgent);
        core.reportCost(taskId, ESCROW);
        vm.warp(block.timestamp + 2 * HEARTBEAT + 1);
        core.detectFailure(taskId);

        ICairnCore.Task memory t = core.getTask(taskId);
        assertEq(uint8(t.failureClass), uint8(ICairnTypes.FailureClass.RESOURCE));
        assertEq(uint8(t.failureType), uint8(ICairnTypes.FailureType.BUDGET_EXHAUSTED));
        assertEq(t.recoveryScore, 0); // B = 0
        assertEq(uint8(t.state), uint8(ICairnTypes.TaskState.DISPUTED));
    }

    // ═══════════════════════════════════════════════════════════════
    // reportFailure
    // ═══════════════════════════════════════════════════════════════

    function test_ReportFailure_Logic_RoutesToDispute() public {
        bytes32 taskId = _submitAndStart();

        vm.expectEmit(true, false, false, true);
        emit ICairnCore.FailureEvidenceRecorded(
            taskId,
            ICairnTypes.FailureEvidenceSource.AGENT_REPORT,
            ICairnTypes.FailureType.VALIDATION_FAILED,
            EVIDENCE
        );
        vm.prank(primaryAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.VALIDATION_FAILED, EVIDENCE);

        ICairnCore.Task memory t = core.getTask(taskId);
        assertEq(uint8(t.failureClass), uint8(ICairnTypes.FailureClass.LOGIC));
        assertEq(t.recoveryScore, 0);
        assertEq(uint8(t.state), uint8(ICairnTypes.TaskState.DISPUTED));
        assertEq(uint8(t.failureEvidenceSource), uint8(ICairnTypes.FailureEvidenceSource.AGENT_REPORT));
        assertEq(t.failureEvidenceCID, EVIDENCE);
    }

    function test_ReportFailure_Liveness_RoutesToFullRecovery() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(primaryAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.NODE_CRASH, EVIDENCE);

        ICairnCore.Task memory t = core.getTask(taskId);
        assertEq(uint8(t.state), uint8(ICairnTypes.TaskState.RECOVERING));
        assertEq(uint8(t.recoveryScope), uint8(ICairnTypes.RecoveryScope.FULL));
        assertEq(t.currentAgent, fallbackAgent);
    }

    /// No heartbeat timeout is needed: the report routes immediately.
    function test_ReportFailure_DoesNotWaitForStaleness() public {
        bytes32 taskId = _submitAndStart();
        assertFalse(core.isStale(taskId));
        vm.prank(primaryAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.RATE_LIMIT, EVIDENCE);
        assertTrue(core.getTask(taskId).state != ICairnTypes.TaskState.RUNNING);
    }

    function test_ReportFailure_MechanicalOnlyTypes_Revert() public {
        bytes32 taskId = _submitAndStart();
        vm.startPrank(primaryAgent);
        vm.expectRevert(
            abi.encodeWithSelector(ICairnCore.InvalidFailureReport.selector, ICairnTypes.FailureType.HEARTBEAT_MISS)
        );
        core.reportFailure(taskId, ICairnTypes.FailureType.HEARTBEAT_MISS, EVIDENCE);
        vm.expectRevert(
            abi.encodeWithSelector(ICairnCore.InvalidFailureReport.selector, ICairnTypes.FailureType.DEADLINE_EXCEEDED)
        );
        core.reportFailure(taskId, ICairnTypes.FailureType.DEADLINE_EXCEEDED, EVIDENCE);
        vm.stopPrank();
    }

    function test_ReportFailure_NotCurrentAgent_Reverts() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(operator);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.NotAuthorized.selector, operator, primaryAgent));
        core.reportFailure(taskId, ICairnTypes.FailureType.VALIDATION_FAILED, EVIDENCE);
    }

    function test_ReportFailure_NotActive_Reverts() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(primaryAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.VALIDATION_FAILED, EVIDENCE); // → DISPUTED
        vm.prank(primaryAgent);
        vm.expectRevert(
            abi.encodeWithSelector(
                ICairnCore.InvalidState.selector, ICairnTypes.TaskState.DISPUTED, ICairnTypes.TaskState.RUNNING
            )
        );
        core.reportFailure(taskId, ICairnTypes.FailureType.RATE_LIMIT, EVIDENCE);
    }

    function test_ReportFailure_WhenPaused_Reverts() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(address(governance));
        core.pause();
        vm.prank(primaryAgent);
        vm.expectRevert();
        core.reportFailure(taskId, ICairnTypes.FailureType.RATE_LIMIT, EVIDENCE);
    }

    /// A fallback reporting failure during recovery goes to dispute (one recovery attempt, H-3).
    function test_ReportFailure_ByFallbackDuringRecovery_Disputes() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(primaryAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.NODE_CRASH, EVIDENCE);
        assertEq(core.getTask(taskId).currentAgent, fallbackAgent);

        vm.prank(fallbackAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.UPSTREAM_TIMEOUT, EVIDENCE);
        assertEq(uint8(core.getTask(taskId).state), uint8(ICairnTypes.TaskState.DISPUTED));
    }

    // ═══════════════════════════════════════════════════════════════
    // detectFailure — deadline expiry
    // ═══════════════════════════════════════════════════════════════

    /// An agent that keeps heart-beating past the deadline can still be failed.
    function test_DetectFailure_PastDeadlineWhileHeartbeating() public {
        bytes32 taskId = _submitAndStart();
        uint256 deadline = core.getTask(taskId).deadline;

        // Heartbeat right up to (and past) the deadline so the task is never stale
        while (block.timestamp <= deadline + HEARTBEAT) {
            vm.warp(block.timestamp + HEARTBEAT);
            vm.prank(primaryAgent);
            core.heartbeat(taskId);
        }
        assertFalse(core.isStale(taskId));

        vm.expectEmit(true, false, false, true);
        emit ICairnCore.FailureEvidenceRecorded(
            taskId,
            ICairnTypes.FailureEvidenceSource.DEADLINE_EXPIRED,
            ICairnTypes.FailureType.DEADLINE_EXCEEDED,
            bytes32(0)
        );
        vm.prank(stranger);
        core.detectFailure(taskId);

        ICairnCore.Task memory t = core.getTask(taskId);
        assertEq(uint8(t.state), uint8(ICairnTypes.TaskState.DISPUTED));
        assertEq(uint8(t.failureType), uint8(ICairnTypes.FailureType.DEADLINE_EXCEEDED));
        assertEq(uint8(t.failureEvidenceSource), uint8(ICairnTypes.FailureEvidenceSource.DEADLINE_EXPIRED));
        assertEq(t.recoveryScore, 0);
    }

    function test_DetectFailure_NeitherStaleNorPastDeadline_Reverts() public {
        bytes32 taskId = _submitAndStart();
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.TaskNotStale.selector, taskId));
        core.detectFailure(taskId);
    }

    function test_DetectFailure_IdleTaskPastDeadline_Reverts() public {
        vm.prank(operator);
        bytes32 taskId = core.submitTask{ value: ESCROW }(
            taskType, specHash, primaryAgent, HEARTBEAT, block.timestamp + DURATION
        );
        vm.warp(block.timestamp + DURATION + 1);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.TaskNotStale.selector, taskId));
        core.detectFailure(taskId);
    }

    /// The fallback reports cost during recovery; cost is cumulative across both agents.
    function test_ReportCost_ByFallbackDuringRecovery() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(primaryAgent);
        core.reportCost(taskId, 0.01 ether);
        vm.prank(primaryAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.NODE_CRASH, EVIDENCE);

        vm.prank(primaryAgent);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.NotAuthorized.selector, primaryAgent, fallbackAgent));
        core.reportCost(taskId, 0.02 ether);

        vm.prank(fallbackAgent);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.CostNotMonotonic.selector, 0.005 ether, 0.01 ether));
        core.reportCost(taskId, 0.005 ether);

        vm.prank(fallbackAgent);
        core.reportCost(taskId, 0.03 ether);
        assertEq(core.getTask(taskId).costAccrued, 0.03 ether);
    }

    /// A fallback heart-beating past the deadline is failed through deadline evidence.
    function test_DetectFailure_PastDeadlineDuringRecovery() public {
        bytes32 taskId = _submitAndStart();
        vm.prank(primaryAgent);
        core.reportFailure(taskId, ICairnTypes.FailureType.NODE_CRASH, EVIDENCE);
        uint256 deadline = core.getTask(taskId).deadline;
        while (block.timestamp <= deadline + HEARTBEAT) {
            vm.warp(block.timestamp + HEARTBEAT);
            vm.prank(fallbackAgent);
            core.heartbeat(taskId);
        }
        core.detectFailure(taskId);
        ICairnCore.Task memory t = core.getTask(taskId);
        assertEq(uint8(t.state), uint8(ICairnTypes.TaskState.DISPUTED));
        assertEq(uint8(t.failureEvidenceSource), uint8(ICairnTypes.FailureEvidenceSource.DEADLINE_EXPIRED));
    }
}
