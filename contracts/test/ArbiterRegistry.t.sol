// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";
import {IArbiterRegistry} from "../src/interfaces/IArbiterRegistry.sol";
import {ICairnTypes} from "../src/interfaces/ICairnTypes.sol";

/// @title ArbiterRegistry Tests
/// @notice Comprehensive tests for dispute resolution and arbiter management
/// @dev Based on PRD-05
contract ArbiterRegistryTest is Test {
    ArbiterRegistry public registry;

    address public cairnCore = makeAddr("cairnCore");
    address public governance = makeAddr("governance");
    address public feeRecipient = makeAddr("feeRecipient");
    address public arbiter1 = makeAddr("arbiter1");
    address public arbiter2 = makeAddr("arbiter2");
    address public primaryAgent = makeAddr("primaryAgent");
    address public fallbackAgent = makeAddr("fallbackAgent");
    address public randomUser = makeAddr("randomUser");

    bytes32 public taskType = keccak256("defi.swap");

    uint256 public constant ARBITER_FEE_BPS = 300; // 3%
    uint256 public constant APPEAL_WINDOW = 48 hours;
    uint256 public constant MIN_ARBITER_STAKE = 0.15 ether;

    function setUp() public {
        registry = new ArbiterRegistry(cairnCore, governance, feeRecipient);

        // Fund arbiters
        vm.deal(arbiter1, 10 ether);
        vm.deal(arbiter2, 10 ether);
        vm.deal(cairnCore, 10 ether);

        // Fund the registry contract to pay arbiter fees
        vm.deal(address(registry), 10 ether);
    }

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Constructor() public view {
        assertEq(registry.cairnCore(), cairnCore);
        assertEq(registry.governance(), governance);
        assertEq(registry.feeRecipient(), feeRecipient);
        assertEq(registry.arbiterFeeBps(), ARBITER_FEE_BPS);
        assertEq(registry.appealWindow(), APPEAL_WINDOW);
        assertEq(registry.minArbiterStake(), MIN_ARBITER_STAKE);
    }

    function test_ConstructorAllowsZeroCairnCore() public {
        // Zero cairnCore is allowed for initial deployment (set via setCairnCore later)
        ArbiterRegistry reg = new ArbiterRegistry(address(0), governance, feeRecipient);
        assertEq(reg.cairnCore(), address(0));

        // Can set cairnCore since it's address(0)
        reg.setCairnCore(cairnCore);
        assertEq(reg.cairnCore(), cairnCore);
    }

    function test_RevertConstructorZeroGovernance() public {
        vm.expectRevert(IArbiterRegistry.ZeroAddress.selector);
        new ArbiterRegistry(cairnCore, address(0), feeRecipient);
    }

    function test_RevertConstructorZeroFeeRecipient() public {
        vm.expectRevert(IArbiterRegistry.ZeroAddress.selector);
        new ArbiterRegistry(cairnCore, governance, address(0));
    }

    // ═══════════════════════════════════════════════════════════════
    // REGISTRATION TESTS (PRD-05 Section 3.1)
    // ═══════════════════════════════════════════════════════════════

    function test_RegisterArbiter() public {
        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;

        vm.prank(arbiter1);
        registry.registerArbiter{value: 0.2 ether}(domains);

        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);
        assertTrue(arbiter.registered);
        assertEq(arbiter.stake, 0.2 ether);
        assertEq(arbiter.rulingCount, 0);
        assertEq(arbiter.overturnedCount, 0);
        assertEq(arbiter.earnings, 0);
    }

    function test_RegisterArbiterEmitsEvent() public {
        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;

        vm.prank(arbiter1);
        vm.expectEmit(true, false, false, true);
        emit IArbiterRegistry.ArbiterRegistered(arbiter1, domains, 0.2 ether);
        registry.registerArbiter{value: 0.2 ether}(domains);
    }

    function test_RevertRegisterArbiterAlreadyRegistered() public {
        _registerArbiter(arbiter1, 0.2 ether);

        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;

        vm.prank(arbiter1);
        vm.expectRevert(IArbiterRegistry.AlreadyRegistered.selector);
        registry.registerArbiter{value: 0.2 ether}(domains);
    }

    function test_RevertRegisterArbiterInsufficientStake() public {
        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;

        vm.prank(arbiter1);
        vm.expectRevert(abi.encodeWithSelector(
            IArbiterRegistry.InsufficientStake.selector,
            MIN_ARBITER_STAKE,
            0.1 ether
        ));
        registry.registerArbiter{value: 0.1 ether}(domains);
    }

    function test_RevertRegisterArbiterNoDomains() public {
        bytes32[] memory domains = new bytes32[](0);

        vm.prank(arbiter1);
        vm.expectRevert(IArbiterRegistry.ZeroAddress.selector);
        registry.registerArbiter{value: 0.2 ether}(domains);
    }

    function test_RegisterArbiterMultipleDomains() public {
        bytes32[] memory domains = new bytes32[](3);
        domains[0] = keccak256("defi.swap");
        domains[1] = keccak256("defi.lend");
        domains[2] = keccak256("nft.mint");

        vm.prank(arbiter1);
        registry.registerArbiter{value: 0.5 ether}(domains);

        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);
        assertEq(arbiter.expertiseDomains.length, 3);
    }

    // ═══════════════════════════════════════════════════════════════
    // STAKE MANAGEMENT TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_AddStake() public {
        _registerArbiter(arbiter1, 0.2 ether);

        vm.prank(arbiter1);
        registry.addStake{value: 0.3 ether}();

        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);
        assertEq(arbiter.stake, 0.5 ether);
    }

    function test_AddStakeEmitsEvent() public {
        _registerArbiter(arbiter1, 0.2 ether);

        vm.prank(arbiter1);
        vm.expectEmit(true, false, false, true);
        emit IArbiterRegistry.StakeAdded(arbiter1, 0.3 ether, 0.5 ether);
        registry.addStake{value: 0.3 ether}();
    }

    function test_RevertAddStakeNotRegistered() public {
        vm.prank(arbiter1);
        vm.expectRevert(IArbiterRegistry.NotRegistered.selector);
        registry.addStake{value: 0.3 ether}();
    }

    function test_WithdrawStake() public {
        _registerArbiter(arbiter1, 0.5 ether);

        uint256 balanceBefore = arbiter1.balance;

        vm.prank(arbiter1);
        registry.withdrawStake(0.3 ether);

        uint256 balanceAfter = arbiter1.balance;
        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);

        assertEq(arbiter.stake, 0.2 ether);
        assertEq(balanceAfter - balanceBefore, 0.3 ether);
    }

    function test_RevertWithdrawStakeNotRegistered() public {
        vm.prank(arbiter1);
        vm.expectRevert(IArbiterRegistry.NotRegistered.selector);
        registry.withdrawStake(0.1 ether);
    }

    function test_RevertWithdrawStakeInsufficientBalance() public {
        _registerArbiter(arbiter1, 0.2 ether);

        vm.prank(arbiter1);
        vm.expectRevert(abi.encodeWithSelector(
            IArbiterRegistry.InsufficientStake.selector,
            0.5 ether,
            0.2 ether
        ));
        registry.withdrawStake(0.5 ether);
    }

    function test_RevertWithdrawStakeBelowMinimum() public {
        _registerArbiter(arbiter1, 0.2 ether);

        // Try to withdraw leaving less than minimum
        vm.prank(arbiter1);
        vm.expectRevert(abi.encodeWithSelector(
            IArbiterRegistry.InsufficientStake.selector,
            MIN_ARBITER_STAKE,
            0.1 ether
        ));
        registry.withdrawStake(0.1 ether);
    }

    function test_WithdrawEntireStake() public {
        _registerArbiter(arbiter1, 0.2 ether);

        vm.prank(arbiter1);
        registry.withdrawStake(0.2 ether);

        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);
        assertEq(arbiter.stake, 0);
    }

    // ═══════════════════════════════════════════════════════════════
    // DEREGISTRATION TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_DeregisterArbiter() public {
        _registerArbiter(arbiter1, 0.5 ether);

        uint256 balanceBefore = arbiter1.balance;

        vm.prank(arbiter1);
        registry.deregisterArbiter();

        uint256 balanceAfter = arbiter1.balance;
        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);

        assertFalse(arbiter.registered);
        assertEq(balanceAfter - balanceBefore, 0.5 ether);
    }

    function test_DeregisterArbiterEmitsEvent() public {
        _registerArbiter(arbiter1, 0.5 ether);

        vm.prank(arbiter1);
        vm.expectEmit(true, false, false, true);
        emit IArbiterRegistry.ArbiterDeregistered(arbiter1, 0.5 ether);
        registry.deregisterArbiter();
    }

    function test_RevertDeregisterArbiterNotRegistered() public {
        vm.prank(arbiter1);
        vm.expectRevert(IArbiterRegistry.NotRegistered.selector);
        registry.deregisterArbiter();
    }

    // ═══════════════════════════════════════════════════════════════
    // RULING TESTS (PRD-05 Section 3.3)
    // ═══════════════════════════════════════════════════════════════

    function test_ExecuteRuling() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        uint256 escrowAmount = 1 ether;

        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.SPLIT,
            agentShare: 60, // 60%
            rationaleCID: keccak256("rationale")
        });

        uint256 arbiterBalanceBefore = arbiter1.balance;

        vm.prank(cairnCore);
        uint256 arbiterFee = registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            escrowAmount,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        // Arbiter fee = 3% of escrow
        assertEq(arbiterFee, 0.03 ether);
        assertEq(arbiter1.balance - arbiterBalanceBefore, 0.03 ether);

        // Check ruling was stored
        IArbiterRegistry.StoredRuling memory storedRuling = registry.getRuling(taskId);
        assertEq(storedRuling.arbiter, arbiter1);
        assertEq(uint8(storedRuling.outcome), uint8(ICairnTypes.RulingOutcome.SPLIT));
        assertEq(storedRuling.agentShare, 60);
        assertFalse(storedRuling.appealed);
        assertFalse(storedRuling.overturned);

        // Check arbiter stats
        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);
        assertEq(arbiter.rulingCount, 1);
        assertEq(arbiter.earnings, 0.03 ether);
    }

    function test_ExecuteRulingEmitsEvent() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(cairnCore);
        vm.expectEmit(true, true, false, true);
        emit IArbiterRegistry.DisputeRuled(
            taskId,
            arbiter1,
            ICairnTypes.RulingOutcome.PAY_AGENT,
            100,
            0.03 ether
        );
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );
    }

    function test_RevertExecuteRulingNotCairnCore() public {
        _registerArbiter(arbiter1, 1 ether);

        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(randomUser);
        vm.expectRevert(IArbiterRegistry.NotCairnCore.selector);
        registry.executeRuling(
            keccak256("task1"),
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );
    }

    function test_RevertExecuteRulingNotEligible() public {
        // Don't register arbiter

        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(cairnCore);
        vm.expectRevert(IArbiterRegistry.NotEligibleForDispute.selector);
        registry.executeRuling(
            keccak256("task1"),
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );
    }

    function test_RevertExecuteRulingAlreadyRuled() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("rationale")
        });

        // First ruling
        vm.prank(cairnCore);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        // Try second ruling on same task
        vm.prank(cairnCore);
        vm.expectRevert(IArbiterRegistry.AlreadyRuled.selector);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );
    }

    function test_RevertRuleDirectly() public {
        _registerArbiter(arbiter1, 1 ether);

        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(arbiter1);
        vm.expectRevert("Use CairnCore.resolveDispute()");
        registry.rule(keccak256("task1"), ruling);
    }

    // ═══════════════════════════════════════════════════════════════
    // APPEALS TESTS (PRD-05 Section 3.5)
    // ═══════════════════════════════════════════════════════════════

    function test_OverturnRuling() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.SPLIT,
            agentShare: 60,
            rationaleCID: keccak256("rationale")
        });

        // Execute ruling
        vm.prank(cairnCore);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        uint256 feeRecipientBefore = feeRecipient.balance;

        // Governance overturns
        ICairnTypes.Ruling memory newRuling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("new_rationale")
        });

        vm.prank(governance);
        registry.overturnRuling(taskId, newRuling);

        // Check slash (50% of stake)
        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);
        assertEq(arbiter.stake, 0.5 ether); // 1 ether - 0.5 ether slash
        assertEq(arbiter.overturnedCount, 1);

        // Check fee recipient received slashed funds
        assertEq(feeRecipient.balance - feeRecipientBefore, 0.5 ether);

        // Check ruling was updated
        IArbiterRegistry.StoredRuling memory storedRuling = registry.getRuling(taskId);
        assertTrue(storedRuling.overturned);
        assertEq(uint8(storedRuling.outcome), uint8(ICairnTypes.RulingOutcome.PAY_AGENT));
        assertEq(storedRuling.agentShare, 100);
    }

    function test_OverturnRulingEmitsEvent() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.SPLIT,
            agentShare: 60,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(cairnCore);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        ICairnTypes.Ruling memory newRuling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("new_rationale")
        });

        vm.prank(governance);
        vm.expectEmit(true, true, false, true);
        emit IArbiterRegistry.RulingOverturned(
            taskId,
            arbiter1,
            0.5 ether,
            ICairnTypes.RulingOutcome.PAY_AGENT
        );
        registry.overturnRuling(taskId, newRuling);
    }

    function test_RevertOverturnRulingNotGovernance() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.SPLIT,
            agentShare: 60,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(cairnCore);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        vm.prank(randomUser);
        vm.expectRevert(IArbiterRegistry.NotGovernance.selector);
        registry.overturnRuling(taskId, ruling);
    }

    function test_RevertOverturnRulingNotFound() public {
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(governance);
        vm.expectRevert(IArbiterRegistry.DisputeNotFound.selector);
        registry.overturnRuling(keccak256("nonexistent"), ruling);
    }

    function test_RevertOverturnRulingAlreadyOverturned() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.SPLIT,
            agentShare: 60,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(cairnCore);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        ICairnTypes.Ruling memory newRuling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("new_rationale")
        });

        // First overturn
        vm.prank(governance);
        registry.overturnRuling(taskId, newRuling);

        // Second overturn should fail
        vm.prank(governance);
        vm.expectRevert(IArbiterRegistry.AlreadyRuled.selector);
        registry.overturnRuling(taskId, newRuling);
    }

    function test_RevertOverturnRulingAfterAppealWindow() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.SPLIT,
            agentShare: 60,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(cairnCore);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        // Warp past appeal window
        vm.warp(block.timestamp + APPEAL_WINDOW + 1);

        vm.prank(governance);
        vm.expectRevert(IArbiterRegistry.AppealWindowExpired.selector);
        registry.overturnRuling(taskId, ruling);
    }

    // ═══════════════════════════════════════════════════════════════
    // ELIGIBILITY TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_IsEligibleRegistered() public {
        _registerArbiter(arbiter1, 1 ether);

        bool eligible = registry.isEligible(
            arbiter1,
            1 ether, // escrow
            primaryAgent,
            fallbackAgent,
            taskType
        );

        assertTrue(eligible);
    }

    function test_IsEligibleNotRegistered() public view {
        bool eligible = registry.isEligible(
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        assertFalse(eligible);
    }

    function test_IsEligibleInsufficientStake() public {
        _registerArbiter(arbiter1, MIN_ARBITER_STAKE);

        // Escrow = 10 ether requires 1.5 ether stake (15%)
        bool eligible = registry.isEligible(
            arbiter1,
            10 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        assertFalse(eligible);
    }

    function test_IsEligibleConflictOfInterest() public {
        _registerArbiter(arbiter1, 1 ether);

        // Arbiter is the primary agent
        bool eligible = registry.isEligible(
            arbiter1,
            1 ether,
            arbiter1, // conflict
            fallbackAgent,
            taskType
        );

        assertFalse(eligible);
    }

    function test_IsEligibleHighOverturnRate() public {
        _registerArbiter(arbiter1, 1 ether);

        // First, execute ALL 10 rulings
        bytes32[] memory taskIds = new bytes32[](10);
        for (uint256 i = 0; i < 10; i++) {
            taskIds[i] = keccak256(abi.encode("task", i));
            ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
                outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
                agentShare: 100,
                rationaleCID: keccak256("rationale")
            });

            vm.prank(cairnCore);
            registry.executeRuling(
                taskIds[i],
                ruling,
                arbiter1,
                1 ether,
                primaryAgent,
                fallbackAgent,
                taskType
            );
        }

        // Then overturn 3 of them (30% > 20% max)
        for (uint256 i = 0; i < 3; i++) {
            ICairnTypes.Ruling memory newRuling = ICairnTypes.Ruling({
                outcome: ICairnTypes.RulingOutcome.REFUND_OPERATOR,
                agentShare: 0,
                rationaleCID: keccak256("new_rationale")
            });

            vm.prank(governance);
            registry.overturnRuling(taskIds[i], newRuling);
        }

        // With 30% overturn rate, should be ineligible
        bool eligible = registry.isEligible(
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        assertFalse(eligible);
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_GetAllArbiters() public {
        _registerArbiter(arbiter1, 0.5 ether);
        _registerArbiter(arbiter2, 0.5 ether);

        address[] memory arbiters = registry.getAllArbiters();
        assertEq(arbiters.length, 2);
    }

    function test_IsAppealWindowActive() public {
        _registerArbiter(arbiter1, 1 ether);

        bytes32 taskId = keccak256("task1");
        ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
            outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
            agentShare: 100,
            rationaleCID: keccak256("rationale")
        });

        vm.prank(cairnCore);
        registry.executeRuling(
            taskId,
            ruling,
            arbiter1,
            1 ether,
            primaryAgent,
            fallbackAgent,
            taskType
        );

        assertTrue(registry.isAppealWindowActive(taskId));

        // Warp past window
        vm.warp(block.timestamp + APPEAL_WINDOW + 1);
        assertFalse(registry.isAppealWindowActive(taskId));
    }

    function test_IsAppealWindowActiveNoRuling() public view {
        assertFalse(registry.isAppealWindowActive(keccak256("nonexistent")));
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_SetCairnCore() public {
        address newCairnCore = makeAddr("newCairnCore");

        vm.prank(governance);
        registry.setCairnCore(newCairnCore);

        assertEq(registry.cairnCore(), newCairnCore);
    }

    function test_RevertSetCairnCoreNotGovernance() public {
        vm.prank(randomUser);
        vm.expectRevert(IArbiterRegistry.NotGovernance.selector);
        registry.setCairnCore(makeAddr("newCairnCore"));
    }

    function test_SetGovernance() public {
        address newGovernance = makeAddr("newGovernance");

        vm.prank(governance);
        registry.setGovernance(newGovernance);

        assertEq(registry.governance(), newGovernance);
    }

    // ═══════════════════════════════════════════════════════════════
    // EDGE CASES
    // ═══════════════════════════════════════════════════════════════

    function test_ReceiveETH() public {
        // Contract should accept ETH for arbiter fees
        (bool success,) = address(registry).call{value: 1 ether}("");
        assertTrue(success);
    }

    function test_MultipleRulingsFromSameArbiter() public {
        _registerArbiter(arbiter1, 1 ether);

        for (uint256 i = 0; i < 5; i++) {
            bytes32 taskId = keccak256(abi.encode("task", i));
            ICairnTypes.Ruling memory ruling = ICairnTypes.Ruling({
                outcome: ICairnTypes.RulingOutcome.PAY_AGENT,
                agentShare: 100,
                rationaleCID: keccak256("rationale")
            });

            vm.prank(cairnCore);
            registry.executeRuling(
                taskId,
                ruling,
                arbiter1,
                1 ether,
                primaryAgent,
                fallbackAgent,
                taskType
            );
        }

        IArbiterRegistry.Arbiter memory arbiter = registry.getArbiter(arbiter1);
        assertEq(arbiter.rulingCount, 5);
        assertEq(arbiter.earnings, 0.15 ether); // 5 × 0.03
    }

    // ═══════════════════════════════════════════════════════════════
    // HELPERS
    // ═══════════════════════════════════════════════════════════════

    function _registerArbiter(address arbiter, uint256 stake) internal {
        bytes32[] memory domains = new bytes32[](1);
        domains[0] = taskType;

        vm.prank(arbiter);
        registry.registerArbiter{value: stake}(domains);
    }
}
