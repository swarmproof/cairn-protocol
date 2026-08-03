// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {RecoveryRouterV2} from "../src/RecoveryRouterV2.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {ICairnCore} from "../src/interfaces/ICairnCore.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";

/// @title CairnCore three-tier routing tests (PRD-04 Phase 2)
/// @notice Verifies FAILED → RECOVERING(FULL) / RECOVERING(REDUCED) / DISPUTED
///         routing via RecoveryRouterV2.routingTier(), the reduced-scope escrow
///         cap in settlement, and the governance toggles.
///
/// Scoring (RecoveryRouterV2, B = 1 since escrow > 0):
///   r = F^0.80 × D^0.15
///   - 0 checkpoints  → LIVENESS (F=0.70), F^0.80 ≈ 0.752 → FULL for normal D
///   - 1-2 checkpoints→ RESOURCE (F=0.30), F^0.80 ≈ 0.382 → REDUCED at high D,
///                       DISPUTED once the deadline is mostly elapsed
contract CairnCoreThreeTierTest is Test {
    CairnCore public core;
    RecoveryRouterV2 public router;
    FallbackPool public pool;
    ArbiterRegistry public registry;
    CairnGovernance public governance;

    address public admin = makeAddr("admin");
    address public feeRecipient = makeAddr("feeRecipient");
    address public operator = makeAddr("operator");
    address public primaryAgent = makeAddr("primaryAgent");
    address public fallbackAgent = makeAddr("fallbackAgent");

    bytes32 public specHash = keccak256("task spec");
    bytes32 public taskType = keccak256("defi.swap");

    uint256 constant ESCROW = 0.1 ether;
    uint256 constant FEE_BPS = 50;

    function setUp() public {
        governance = new CairnGovernance(admin);
        core = new CairnCore(feeRecipient, address(0), address(0), address(0), address(governance));

        // Wire the v2 router (implements routingTier) instead of the v1 router
        router = new RecoveryRouterV2(address(core));
        pool = new FallbackPool(address(core), feeRecipient, address(0), address(0), address(0));
        registry = new ArbiterRegistry(address(core), address(governance), feeRecipient);

        vm.startPrank(address(governance));
        core.setContracts(address(router), address(pool), address(registry));
        core.setThreeTierRouting(true); // enable v2 three-tier routing
        vm.stopPrank();

        vm.deal(operator, 100 ether);
        vm.deal(fallbackAgent, 10 ether);
        vm.deal(address(core), 10 ether);

        bytes32[] memory taskTypes = new bytes32[](1);
        taskTypes[0] = taskType;
        vm.prank(fallbackAgent);
        pool.register{ value: 1 ether }(taskTypes, 5);
    }

    // ─── helpers
    // ──────────────────────────────────────────────────

    function _submitAndStart() internal returns (bytes32 taskId) {
        uint256 deadline = block.timestamp + 1 hours;
        vm.prank(operator);
        taskId = core.submitTask{ value: ESCROW }(taskType, specHash, primaryAgent, 60, deadline);
        vm.prank(primaryAgent);
        core.startTask(taskId);
    }

    function _commit(bytes32 taskId, address who, uint256 count) internal {
        vm.prank(who);
        core.commitCheckpointBatch(taskId, count, keccak256("root"), keccak256("cid"), specHash);
    }

    // ═══════════════════════════════════════════════════════════════
    // ROUTING — three tiers
    // ═══════════════════════════════════════════════════════════════

    /// FULL: 0 checkpoints (LIVENESS), fresh deadline → r ≈ 0.75 ≥ 0.40
    function test_FullScope_ZeroCheckpoints() public {
        bytes32 taskId = _submitAndStart();
        vm.warp(block.timestamp + 121); // stale (2× 60s)

        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RECOVERING));
        assertEq(uint8(task.recoveryScope), uint8(ICairnTypes.RecoveryScope.FULL));
        assertEq(task.currentAgent, fallbackAgent);
        assertGe(task.recoveryScore, 0.4e18);
    }

    /// REDUCED: 1 checkpoint (RESOURCE), fresh deadline → 0.35 ≤ r < 0.40
    function test_ReducedScope_ResourceClass() public {
        bytes32 taskId = _submitAndStart();
        _commit(taskId, primaryAgent, 1); // 1 checkpoint → RESOURCE class
        vm.warp(block.timestamp + 121);

        vm.expectEmit(true, false, false, true);
        emit ICairnCore.RecoveryScopeAssigned(taskId, ICairnTypes.RecoveryScope.REDUCED);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RECOVERING));
        assertEq(uint8(task.recoveryScope), uint8(ICairnTypes.RecoveryScope.REDUCED));
        assertGe(task.recoveryScore, 0.35e18);
        assertLt(task.recoveryScore, 0.4e18);
    }

    /// DISPUTED: 1 checkpoint (RESOURCE), deadline mostly elapsed → r < 0.35
    function test_Disputed_LowScore() public {
        bytes32 taskId = _submitAndStart();
        _commit(taskId, primaryAgent, 1);
        vm.warp(block.timestamp + 2400); // ~40 min elapsed of the 1h deadline

        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.DISPUTED));
        assertLt(task.recoveryScore, 0.35e18);
    }

    /// A qualifying score with no fallback available still routes to DISPUTED.
    function test_NoFallback_Disputed() public {
        // Fresh core with an unregistered task type → selectFallback returns 0
        bytes32 lonelyType = keccak256("no.fallback.type");
        uint256 deadline = block.timestamp + 1 hours;
        vm.prank(operator);
        bytes32 taskId =
            core.submitTask{ value: ESCROW }(lonelyType, specHash, primaryAgent, 60, deadline);
        vm.prank(primaryAgent);
        core.startTask(taskId);
        vm.warp(block.timestamp + 121);

        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(task.fallbackAgent, address(0));
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.DISPUTED));
    }

    // ═══════════════════════════════════════════════════════════════
    // SETTLEMENT — reduced-scope cap
    // ═══════════════════════════════════════════════════════════════

    /// Reduced-scope recovery caps the fallback at 50% of distributable and
    /// refunds the remainder to the operator.
    function test_ReducedScope_SettlementCapsFallbackAt50pct() public {
        bytes32 taskId = _submitAndStart();
        _commit(taskId, primaryAgent, 1); // primary: 1 checkpoint → REDUCED route
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory failed = core.getTask(taskId);
        assertEq(uint8(failed.recoveryScope), uint8(ICairnTypes.RecoveryScope.REDUCED));

        // Fallback does the majority of the work (3 of 4 checkpoints → 75% pre-cap)
        _commit(taskId, fallbackAgent, 3);

        uint256 opBefore = operator.balance;
        vm.prank(fallbackAgent);
        core.completeTask(taskId);

        uint256 distributable = ESCROW - (ESCROW * FEE_BPS) / 10_000; // 0.0995 ether
        uint256 expectedPrimary = (distributable * 1) / 4; // 25%
        uint256 cap = distributable / 2; // 50%
        uint256 expectedRefund = (distributable * 3) / 4 - cap; // 75% - 50% = 25%

        ICairnCore.Task memory settled = core.getTask(taskId);
        assertEq(settled.settledPrimary, expectedPrimary, "primary 25%");
        assertEq(settled.settledFallback, cap, "fallback capped at 50%");
        assertEq(operator.balance - opBefore, expectedRefund, "operator refunded excess 25%");
    }

    /// FULL-scope recovery does NOT cap: fallback keeps its full proportional share.
    function test_FullScope_NoSettlementCap() public {
        bytes32 taskId = _submitAndStart();
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId); // 0 checkpoints → FULL

        _commit(taskId, fallbackAgent, 3); // fallback does all work
        uint256 opBefore = operator.balance;
        vm.prank(fallbackAgent);
        core.completeTask(taskId);

        uint256 distributable = ESCROW - (ESCROW * FEE_BPS) / 10_000;
        ICairnCore.Task memory settled = core.getTask(taskId);
        assertEq(settled.settledFallback, distributable, "fallback gets 100% (no cap)");
        assertEq(operator.balance - opBefore, 0, "no operator refund on full scope");
    }

    // ═══════════════════════════════════════════════════════════════
    // GOVERNANCE toggles
    // ═══════════════════════════════════════════════════════════════

    function test_SetThreeTierRouting_OnlyGovernance() public {
        vm.expectRevert();
        core.setThreeTierRouting(false);

        vm.prank(address(governance));
        core.setThreeTierRouting(false);
        assertFalse(core.threeTierRoutingEnabled());
    }

    function test_SetReducedScopeCap_Governance() public {
        vm.prank(address(governance));
        core.setReducedScopeCap(3000);
        assertEq(core.reducedScopeCapBps(), 3000);
    }

    function test_SetReducedScopeCap_RevertOverMax() public {
        vm.prank(address(governance));
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.InvalidReducedScopeCap.selector, 10_001));
        core.setReducedScopeCap(10_001);
    }

    function test_SetReducedScopeCap_OnlyGovernance() public {
        vm.expectRevert();
        core.setReducedScopeCap(3000);
    }

    /// Sanity: with the flag OFF, a RESOURCE score (~0.38 > v1 0.30 threshold)
    /// routes to RECOVERING with default FULL scope (v1 binary behavior).
    function test_FlagOff_UsesV1BinaryRouting() public {
        vm.prank(address(governance));
        core.setThreeTierRouting(false);

        bytes32 taskId = _submitAndStart();
        _commit(taskId, primaryAgent, 1);
        vm.warp(block.timestamp + 121);
        core.detectFailure(taskId);

        ICairnCore.Task memory task = core.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RECOVERING));
        // v1 path never assigns REDUCED — scope stays default FULL
        assertEq(uint8(task.recoveryScope), uint8(ICairnTypes.RecoveryScope.FULL));
    }
}
