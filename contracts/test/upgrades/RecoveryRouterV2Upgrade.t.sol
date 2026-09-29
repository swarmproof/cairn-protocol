// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import {RecoveryRouterV2Upgradeable} from "../../src/upgradeable/RecoveryRouterV2Upgradeable.sol";
import {RecoveryRouterV2} from "../../src/RecoveryRouterV2.sol";
import {CairnCore} from "../../src/CairnCore.sol";
import {FallbackPool} from "../../src/FallbackPool.sol";
import {ArbiterRegistry} from "../../src/ArbiterRegistry.sol";
import {CairnGovernance} from "../../src/CairnGovernance.sol";
import {IRecoveryRouter} from "../../src/interfaces/IRecoveryRouter.sol";
import {ICairnCore} from "../../src/interfaces/ICairnCore.sol";
import {ICairnTypes} from "../../src/interfaces/ICairnTypes.sol";

/// @dev Second implementation used to exercise upgrades.
contract RecoveryRouterV2UpgradeableV2Mock is RecoveryRouterV2Upgradeable {
    function version() external pure returns (uint256) {
        return 2;
    }
}

/// @title RecoveryRouterV2Upgradeable (AC-08)
/// @notice UUPS mechanics, behavioural parity with RecoveryRouterV2, and CairnCore wiring.
contract RecoveryRouterV2UpgradeTest is Test {
    RecoveryRouterV2Upgradeable public router;
    RecoveryRouterV2 public baseline;

    address public owner = makeAddr("owner");
    address public core = makeAddr("core");
    address public stranger = makeAddr("stranger");

    function setUp() public {
        RecoveryRouterV2Upgradeable impl = new RecoveryRouterV2Upgradeable();
        ERC1967Proxy proxy = new ERC1967Proxy(
            address(impl), abi.encodeCall(RecoveryRouterV2Upgradeable.initialize, (core, owner))
        );
        router = RecoveryRouterV2Upgradeable(address(proxy));
        baseline = new RecoveryRouterV2(core);
    }

    function _ev(ICairnTypes.FailureEvidenceSource src, ICairnTypes.FailureType t, uint256 cost)
        internal
        view
        returns (ICairnTypes.FailureEvidence memory)
    {
        return ICairnTypes.FailureEvidence({
            source: src,
            reportedType: t,
            evidenceCID: bytes32(0),
            escrowAmount: 1 ether,
            costAccrued: cost,
            createdAt: block.timestamp,
            deadline: block.timestamp + 1 hours,
            checkpointCount: 0
        });
    }

    // ═══════════════════════════════════════════════════════════════
    // initialization
    // ═══════════════════════════════════════════════════════════════

    function test_Initialize_SetsState() public view {
        assertEq(router.owner(), owner);
        assertEq(router.cairnCore(), core);
        assertEq(router.upperThreshold(), 0.40e18);
        assertEq(router.lowerThreshold(), 0.35e18);
        assertEq(router.recoveryThreshold(), 0.35e18);
    }

    function test_Reinitialize_Reverts() public {
        vm.expectRevert(Initializable.InvalidInitialization.selector);
        router.initialize(core, stranger);
    }

    function test_Implementation_CannotBeInitialized() public {
        RecoveryRouterV2Upgradeable impl = new RecoveryRouterV2Upgradeable();
        vm.expectRevert(Initializable.InvalidInitialization.selector);
        impl.initialize(core, owner);
    }

    // ═══════════════════════════════════════════════════════════════
    // upgrades
    // ═══════════════════════════════════════════════════════════════

    function test_Upgrade_ByOwner_PreservesState() public {
        vm.prank(owner);
        router.setThresholds(0.5e18, 0.45e18);

        RecoveryRouterV2UpgradeableV2Mock next = new RecoveryRouterV2UpgradeableV2Mock();
        vm.prank(owner);
        router.upgradeToAndCall(address(next), "");

        assertEq(RecoveryRouterV2UpgradeableV2Mock(address(router)).version(), 2);
        assertEq(router.upperThreshold(), 0.5e18);
        assertEq(router.lowerThreshold(), 0.45e18);
        assertEq(router.cairnCore(), core);
        assertEq(router.owner(), owner);
    }

    function test_Upgrade_ByNonOwner_Reverts() public {
        RecoveryRouterV2UpgradeableV2Mock next = new RecoveryRouterV2UpgradeableV2Mock();
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(OwnableUpgradeable.OwnableUnauthorizedAccount.selector, stranger));
        router.upgradeToAndCall(address(next), "");
    }

    // ═══════════════════════════════════════════════════════════════
    // parity with RecoveryRouterV2
    // ═══════════════════════════════════════════════════════════════

    function test_Constants_MatchBaseline() public view {
        assertEq(router.B_EXPONENT(), baseline.B_EXPONENT());
        assertEq(router.D_EXPONENT(), baseline.D_EXPONENT());
        assertEq(router.F_POW_LIVENESS(), baseline.F_POW_LIVENESS());
        assertEq(router.F_POW_RESOURCE(), baseline.F_POW_RESOURCE());
        assertEq(router.F_POW_LOGIC(), baseline.F_POW_LOGIC());
    }

    function testFuzz_ComputeScore_MatchesBaseline(uint8 cls, uint256 b, uint256 d) public view {
        ICairnTypes.FailureClass fc = ICairnTypes.FailureClass(bound(cls, 0, 2));
        b = bound(b, 0, 1e18);
        d = bound(d, 0, 1e18);
        assertEq(router.computeRecoveryScore(fc, b, d), baseline.computeRecoveryScore(fc, b, d));
    }

    function test_ClassWeight_MatchesBaseline() public view {
        for (uint8 i = 0; i < 3; i++) {
            ICairnTypes.FailureClass fc = ICairnTypes.FailureClass(i);
            assertEq(router.getClassWeight(fc), baseline.getClassWeight(fc));
        }
    }

    function testFuzz_ClassifyAndScore_MatchesBaseline(uint8 src, uint8 t, uint256 cost) public {
        ICairnTypes.FailureEvidence memory ev = _ev(
            ICairnTypes.FailureEvidenceSource(bound(src, 0, 2)),
            ICairnTypes.FailureType(bound(t, 0, 10)),
            bound(cost, 0, 2 ether)
        );
        vm.startPrank(core);
        (ICairnTypes.FailureClass c1, ICairnTypes.FailureType t1, uint256 s1,) =
            router.classifyAndScore(keccak256("x"), ev);
        (ICairnTypes.FailureClass c2, ICairnTypes.FailureType t2, uint256 s2,) =
            baseline.classifyAndScore(keccak256("x"), ev);
        vm.stopPrank();
        assertEq(uint8(c1), uint8(c2));
        assertEq(uint8(t1), uint8(t2));
        assertEq(s1, s2);
    }

    function testFuzz_RoutingTier_MatchesBaseline(uint256 score) public view {
        score = bound(score, 0, 1e18);
        assertEq(router.routingTier(score), baseline.routingTier(score));
    }

    function test_ComputeScore_OutOfRange_Reverts() public {
        vm.expectRevert(RecoveryRouterV2Upgradeable.InputOutOfRange.selector);
        router.computeRecoveryScore(ICairnTypes.FailureClass.LIVENESS, 1e18 + 1, 1e18);
    }

    // ═══════════════════════════════════════════════════════════════
    // access control and parameters
    // ═══════════════════════════════════════════════════════════════

    function test_ClassifyAndScore_NotCore_Reverts() public {
        vm.expectRevert(IRecoveryRouter.NotAuthorized.selector);
        router.classifyAndScore(
            keccak256("x"),
            _ev(ICairnTypes.FailureEvidenceSource.HEARTBEAT_TIMEOUT, ICairnTypes.FailureType.HEARTBEAT_MISS, 0)
        );
    }

    function test_SetThresholds_Validation() public {
        vm.startPrank(owner);
        vm.expectRevert(RecoveryRouterV2Upgradeable.InvalidThresholdOrder.selector);
        router.setThresholds(0.3e18, 0.4e18);
        vm.expectRevert(RecoveryRouterV2Upgradeable.InvalidThresholdRange.selector);
        router.setThresholds(0.95e18, 0.4e18);
        vm.expectRevert(RecoveryRouterV2Upgradeable.InvalidThresholdRange.selector);
        router.setThresholds(0.5e18, 0.05e18);
        vm.stopPrank();

        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(OwnableUpgradeable.OwnableUnauthorizedAccount.selector, stranger));
        router.setThresholds(0.5e18, 0.4e18);
    }

    function test_SetCairnCore() public {
        vm.prank(owner);
        vm.expectRevert(RecoveryRouterV2Upgradeable.ZeroAddress.selector);
        router.setCairnCore(address(0));

        address next = makeAddr("nextCore");
        vm.prank(owner);
        router.setCairnCore(next);
        assertEq(router.cairnCore(), next);
    }

    // ═══════════════════════════════════════════════════════════════
    // wired into CairnCore
    // ═══════════════════════════════════════════════════════════════

    function test_WiredIntoCairnCore_ThreeTierRouting() public {
        address admin = makeAddr("admin");
        address feeRecipient = makeAddr("fee");
        address operator = makeAddr("operator");
        address primary = makeAddr("primary");
        address fallbackAgent = makeAddr("fallback");
        bytes32 taskType = keccak256("t");
        bytes32 spec = keccak256("s");

        CairnGovernance gov = new CairnGovernance(admin);
        CairnCore c = new CairnCore(feeRecipient, address(0), address(0), address(0), address(gov));
        FallbackPool pool = new FallbackPool(address(c), feeRecipient, address(0), address(0), address(0));
        ArbiterRegistry reg = new ArbiterRegistry(address(c), address(gov), feeRecipient);
        vm.prank(owner);
        router.setCairnCore(address(c));

        vm.startPrank(address(gov));
        c.setContracts(address(router), address(pool), address(reg));
        c.setThreeTierRouting(true);
        vm.stopPrank();

        vm.deal(fallbackAgent, 10 ether);
        bytes32[] memory types = new bytes32[](1);
        types[0] = taskType;
        vm.prank(fallbackAgent);
        pool.register{ value: 1 ether }(types, 5);

        vm.deal(operator, 10 ether);
        vm.prank(operator);
        bytes32 taskId = c.submitTask{ value: 0.1 ether }(taskType, spec, primary, 60, block.timestamp + 1 hours);
        vm.prank(primary);
        c.startTask(taskId);
        vm.warp(block.timestamp + 121);
        c.detectFailure(taskId);

        ICairnCore.Task memory task = c.getTask(taskId);
        assertEq(uint8(task.state), uint8(ICairnTypes.TaskState.RECOVERING));
        assertEq(uint8(task.recoveryScope), uint8(ICairnTypes.RecoveryScope.FULL));
        assertEq(task.currentAgent, fallbackAgent);
    }
}
