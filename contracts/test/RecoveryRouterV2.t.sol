// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {RecoveryRouterV2} from "../src/RecoveryRouterV2.sol";
import {IRecoveryRouter} from "../src/interfaces/IRecoveryRouter.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";

/// @title RecoveryRouterV2 unit tests
/// @notice Verifies the simulation-validated multiplicative formula
///         r = F^0.80 × B^0.35 × D^0.15 per WHITEPAPER_V2 §6.4 and §2.4.
contract RecoveryRouterV2Test is Test {
    RecoveryRouterV2 public router;
    address public cairnCore = address(0xC0FFEE);

    // ─── Tolerances ─────────────────────────────────────────────
    // PRBMath pow(B, 0.35) and pow(D, 0.15) carry rounding error of
    // up to ~1e-7 in the raw output (it uses log/exp internally).
    // We assert closeness to ~1e-3 in the final UD60x18 score.
    uint256 constant TOL = 1e15; // 0.001 in UD60x18

    function setUp() public {
        router = new RecoveryRouterV2(cairnCore);
    }

    // ═══════════════════════════════════════════════════════════════
    // 1. CONSTANTS — verify the F^0.80 lookup table
    // ═══════════════════════════════════════════════════════════════

    function test_FPowLookup_LivenessConstant() public {
        // 0.70^0.80 = 0.7517586466500457
        // Constant stored at 18-decimal precision.
        assertEq(router.F_POW_LIVENESS(), 751_758_646_650_045_568);
    }

    function test_FPowLookup_ResourceConstant() public {
        // 0.30^0.80 = 0.3816778909618176
        assertEq(router.F_POW_RESOURCE(), 381_677_890_961_817_600);
    }

    function test_FPowLookup_LogicConstant() public {
        assertEq(router.F_POW_LOGIC(), 0);
    }

    function test_DefaultThresholds() public {
        assertEq(router.upperThreshold(), 0.40e18);
        assertEq(router.lowerThreshold(), 0.35e18);
    }

    function test_LegacyRecoveryThresholdReturnsLower() public {
        // v1-compat: recoveryThreshold() returns the recover/dispute boundary,
        // i.e. the lower threshold of the v2 three-tier band.
        assertEq(router.recoveryThreshold(), router.lowerThreshold());
    }

    // ═══════════════════════════════════════════════════════════════
    // 2. WORKED EXAMPLE — WHITEPAPER §2.4
    //    r(F=0.70, B=0.85, D=0.88) ≈ 0.6967  (paper rounds to 0.697)
    // ═══════════════════════════════════════════════════════════════

    function test_WorkedExample_2_47amRecovery() public {
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS,
            0.85e18, // budget remaining
            0.88e18 // deadline remaining
        );

        // Expected: 0.6967 ± tolerance
        assertApproxEqAbs(score, 0.6967e18, TOL);
        // Should comfortably exceed upperThreshold → routes to FULL
        assertGt(score, router.upperThreshold());
    }

    // ═══════════════════════════════════════════════════════════════
    // 3. CLASS SEPARATION — F^0.80 dominates the recover/dispute decision
    // ═══════════════════════════════════════════════════════════════

    function test_LivenessAtFullResources_ScoresFullTier() public {
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 1e18, 1e18
        );
        // F=0.70, B=D=1 → r = F^0.80 × 1 × 1 = 0.7518
        assertApproxEqAbs(score, 751_758_646_650_045_568, TOL);
        assertEq(router.routingTier(score), 2); // FULL
    }

    function test_ResourceAtFullResources_ScoresReducedOrDisputeBoundary() public {
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.RESOURCE, 1e18, 1e18
        );
        // F=0.30, B=D=1 → r = F^0.80 = 0.3817
        assertApproxEqAbs(score, 381_677_890_961_817_600, TOL);
        // 0.3817 > 0.35 (lower) but < 0.40 (upper) → REDUCED tier
        assertEq(router.routingTier(score), 1);
    }

    function test_LogicAlwaysScoresZero_RoutesToDispute() public {
        // LOGIC short-circuits to 0 regardless of B, D
        uint256 atFull = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LOGIC, 1e18, 1e18
        );
        assertEq(atFull, 0);

        uint256 atZero = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LOGIC, 0, 0
        );
        assertEq(atZero, 0);

        assertEq(router.routingTier(atFull), 0); // DISPUTED
    }

    // ═══════════════════════════════════════════════════════════════
    // 4. ANY-FACTOR-KILLS-IT — multiplicative structure dynamic
    // ═══════════════════════════════════════════════════════════════

    function test_ZeroBudget_ScoresZero_EvenForLiveness() public {
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 0, 1e18
        );
        // pow(0, anything > 0) = 0 in PRBMath → r = 0
        assertEq(score, 0);
        assertEq(router.routingTier(score), 0);
    }

    function test_ZeroDeadline_ScoresZero_EvenForLiveness() public {
        uint256 score = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 1e18, 0
        );
        assertEq(score, 0);
        assertEq(router.routingTier(score), 0);
    }

    // ═══════════════════════════════════════════════════════════════
    // 5. THREE-TIER BAND BOUNDARIES
    // ═══════════════════════════════════════════════════════════════

    function test_RoutingTier_AboveUpper_IsFull() public {
        assertEq(router.routingTier(0.50e18), 2);
        assertEq(router.routingTier(0.40e18), 2); // boundary inclusive
        assertEq(router.routingTier(1e18), 2);
    }

    function test_RoutingTier_BetweenLowerAndUpper_IsReduced() public {
        assertEq(router.routingTier(0.39e18), 1);
        assertEq(router.routingTier(0.35e18), 1); // boundary inclusive
        assertEq(router.routingTier(0.36e18), 1);
    }

    function test_RoutingTier_BelowLower_IsDisputed() public {
        assertEq(router.routingTier(0.34e18), 0);
        assertEq(router.routingTier(0.10e18), 0);
        assertEq(router.routingTier(0), 0);
    }

    // ═══════════════════════════════════════════════════════════════
    // 6. INPUT VALIDATION
    // ═══════════════════════════════════════════════════════════════

    function test_OverflowBudget_Reverts() public {
        vm.expectRevert(RecoveryRouterV2.InputOutOfRange.selector);
        router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 2e18, 1e18
        );
    }

    function test_OverflowDeadline_Reverts() public {
        vm.expectRevert(RecoveryRouterV2.InputOutOfRange.selector);
        router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 1e18, 2e18
        );
    }

    // ═══════════════════════════════════════════════════════════════
    // 7. ACCESS CONTROL
    // ═══════════════════════════════════════════════════════════════

    function test_ClassifyAndScore_NotCairnCore_Reverts() public {
        vm.expectRevert(IRecoveryRouter.NotAuthorized.selector);
        router.classifyAndScore(bytes32(uint256(1)), 1 ether, 1, 100, 0);
    }

    // ═══════════════════════════════════════════════════════════════
    // 8. GOVERNANCE THRESHOLD UPDATES
    // ═══════════════════════════════════════════════════════════════

    function test_SetThresholds_Valid_Updates() public {
        router.setThresholds(0.50e18, 0.45e18);
        assertEq(router.upperThreshold(), 0.50e18);
        assertEq(router.lowerThreshold(), 0.45e18);
    }

    function test_SetThresholds_LowerExceedsUpper_Reverts() public {
        vm.expectRevert(RecoveryRouterV2.InvalidThresholdOrder.selector);
        router.setThresholds(0.30e18, 0.35e18);
    }

    function test_SetThresholds_OutOfRange_Reverts() public {
        vm.expectRevert(RecoveryRouterV2.InvalidThresholdRange.selector);
        router.setThresholds(0.99e18, 0.01e18);
    }

    // ═══════════════════════════════════════════════════════════════
    // 9. CLASSIFY-AND-SCORE INTEGRATION (caller = cairnCore)
    // ═══════════════════════════════════════════════════════════════

    function test_ClassifyAndScore_FromCairnCore_LivenessHappyPath() public {
        vm.prank(cairnCore);
        (
            ICairnTypes.FailureClass failureClass,
            ,
            uint256 score,
            bytes32 cid
        ) = router.classifyAndScore(
            bytes32(uint256(1)),
            1 ether,
            block.timestamp,
            block.timestamp + 1000,
            0 // 0 checkpoints → LIVENESS classification
        );

        assertEq(uint8(failureClass), uint8(ICairnTypes.FailureClass.LIVENESS));
        assertGt(score, router.upperThreshold()); // fresh task, full resources
        assertTrue(cid != bytes32(0));
    }

    // ═══════════════════════════════════════════════════════════════
    // 10. MONOTONICITY — sanity that score grows in each input
    // ═══════════════════════════════════════════════════════════════

    function test_Monotonic_InBudget() public {
        uint256 low = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 0.30e18, 1e18
        );
        uint256 high = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 0.90e18, 1e18
        );
        assertGt(high, low);
    }

    function test_Monotonic_InDeadline() public {
        uint256 low = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 1e18, 0.30e18
        );
        uint256 high = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 1e18, 0.90e18
        );
        assertGt(high, low);
    }

    function test_LivenessExceedsResourceAtSameResources() public {
        uint256 liveness = router.computeRecoveryScore(
            ICairnTypes.FailureClass.LIVENESS, 0.50e18, 0.50e18
        );
        uint256 resource = router.computeRecoveryScore(
            ICairnTypes.FailureClass.RESOURCE, 0.50e18, 0.50e18
        );
        assertGt(liveness, resource);
        // Specifically: ratio ≈ 1.97 per WHITEPAPER §6.4
        // We just assert the ordering (avoids PRBMath rounding flakiness).
    }

    // ═══════════════════════════════════════════════════════════════
    // COVERAGE: class weights, classification, admin
    // ═══════════════════════════════════════════════════════════════

    function test_GetClassWeight_AllClasses() public view {
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.LIVENESS), 0.70e18);
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.RESOURCE), 0.30e18);
        assertEq(router.getClassWeight(ICairnTypes.FailureClass.LOGIC), 0);
    }

    /// checkpointCount >= 3 classifies as LIVENESS (late-stage failure).
    function test_ClassifyAndScore_ManyCheckpoints_IsLiveness() public {
        vm.prank(cairnCore);
        (ICairnTypes.FailureClass fc, ICairnTypes.FailureType ft,,) =
            router.classifyAndScore(keccak256("t"), 1 ether, block.timestamp, block.timestamp + 1 hours, 5);
        assertEq(uint8(fc), uint8(ICairnTypes.FailureClass.LIVENESS));
        assertEq(uint8(ft), uint8(ICairnTypes.FailureType.HEARTBEAT_MISS));
    }

    /// 1-2 checkpoints classify as RESOURCE.
    function test_ClassifyAndScore_FewCheckpoints_IsResource() public {
        vm.prank(cairnCore);
        (ICairnTypes.FailureClass fc,,,) =
            router.classifyAndScore(keccak256("t"), 1 ether, block.timestamp, block.timestamp + 1 hours, 2);
        assertEq(uint8(fc), uint8(ICairnTypes.FailureClass.RESOURCE));
    }

    function test_SetCairnCore() public {
        address newCore = address(0xBEEF);
        router.setCairnCore(newCore);
        assertEq(router.cairnCore(), newCore);
    }
}
