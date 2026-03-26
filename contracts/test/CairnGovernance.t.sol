// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {IGovernance} from "../src/interfaces/IGovernance.sol";

/// @title CairnGovernance Tests
/// @notice Comprehensive tests for governance with 48-hour timelock
/// @dev Based on PRD-06 Section 3
contract CairnGovernanceTest is Test {
    CairnGovernance public governance;

    address public admin = makeAddr("admin");
    address public randomUser = makeAddr("randomUser");
    address public newAdmin = makeAddr("newAdmin");

    uint256 public constant TIMELOCK = 48 hours;

    function setUp() public {
        governance = new CairnGovernance(admin);
    }

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_Constructor() public view {
        assertEq(governance.admin(), admin);
        assertFalse(governance.isPaused());
        assertEq(governance.timelockDuration(), TIMELOCK);
    }

    function test_ConstructorInitializesDefaultParameters() public view {
        // PRD-06 default values
        assertEq(governance.getParameter(governance.PROTOCOL_FEE_BPS()), 50);
        assertEq(governance.getParameter(governance.ARBITER_FEE_BPS()), 300);
        assertEq(governance.getParameter(governance.MIN_REPUTATION()), 50);
        assertEq(governance.getParameter(governance.MIN_STAKE_PERCENT()), 10);
        assertEq(governance.getParameter(governance.MIN_ARBITER_STAKE_PERCENT()), 15);
        assertEq(governance.getParameter(governance.RECOVERY_THRESHOLD()), 0.3e18);
        assertEq(governance.getParameter(governance.DISPUTE_TIMEOUT()), 7 days);
        assertEq(governance.getParameter(governance.APPEAL_WINDOW()), 48 hours);
        assertEq(governance.getParameter(governance.MIN_HEARTBEAT_INTERVAL()), 30);
    }

    function test_RevertConstructorZeroAdmin() public {
        vm.expectRevert(IGovernance.ZeroAddress.selector);
        new CairnGovernance(address(0));
    }

    // ═══════════════════════════════════════════════════════════════
    // PROPOSE PARAMETER TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_ProposeParameter() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        uint256 newValue = 100; // 1%

        vm.prank(admin);
        governance.proposeParameter(key, newValue);

        (uint256 value, uint256 executeAfter) = governance.getProposal(key);
        assertEq(value, newValue);
        assertEq(executeAfter, block.timestamp + TIMELOCK);
    }

    function test_ProposeParameterEmitsEvent() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        uint256 newValue = 100;

        vm.prank(admin);
        vm.expectEmit(true, false, false, true);
        emit IGovernance.ParameterProposed(key, newValue, block.timestamp + TIMELOCK);
        governance.proposeParameter(key, newValue);
    }

    function test_RevertProposeParameterNotAdmin() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        vm.prank(randomUser);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.proposeParameter(key, 100);
    }

    function test_RevertProposeParameterOutOfRange() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        // Max is 500 (5%)
        uint256 invalidValue = 600;

        vm.prank(admin);
        vm.expectRevert(abi.encodeWithSelector(
            IGovernance.ValueOutOfRange.selector,
            key,
            invalidValue,
            0,
            500
        ));
        governance.proposeParameter(key, invalidValue);
    }

    function test_ProposeParameterBoundaryValues() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        // Test min boundary (0)
        vm.prank(admin);
        governance.proposeParameter(key, 0);

        // Test max boundary (500)
        vm.prank(admin);
        governance.proposeParameter(key, 500);

        (uint256 value,) = governance.getProposal(key);
        assertEq(value, 500);
    }

    // ═══════════════════════════════════════════════════════════════
    // EXECUTE PROPOSAL TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_ExecuteProposal() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        uint256 newValue = 100;

        // Propose
        vm.prank(admin);
        governance.proposeParameter(key, newValue);

        // Warp past timelock
        vm.warp(block.timestamp + TIMELOCK + 1);

        // Execute
        uint256 oldValue = governance.getParameter(key);
        vm.prank(admin);
        governance.executeProposal(key);

        assertEq(governance.getParameter(key), newValue);
        assertNotEq(governance.getParameter(key), oldValue);
    }

    function test_ExecuteProposalEmitsEvent() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        uint256 newValue = 100;
        uint256 oldValue = governance.getParameter(key);

        vm.prank(admin);
        governance.proposeParameter(key, newValue);
        vm.warp(block.timestamp + TIMELOCK + 1);

        vm.prank(admin);
        vm.expectEmit(true, false, false, true);
        emit IGovernance.ParameterUpdated(key, oldValue, newValue);
        governance.executeProposal(key);
    }

    function test_RevertExecuteProposalNotAdmin() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        vm.prank(admin);
        governance.proposeParameter(key, 100);
        vm.warp(block.timestamp + TIMELOCK + 1);

        vm.prank(randomUser);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.executeProposal(key);
    }

    function test_RevertExecuteProposalNotFound() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        vm.prank(admin);
        vm.expectRevert(IGovernance.ProposalNotFound.selector);
        governance.executeProposal(key);
    }

    function test_RevertExecuteProposalTimelockNotExpired() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        vm.prank(admin);
        governance.proposeParameter(key, 100);

        // Try to execute before timelock expires
        vm.warp(block.timestamp + TIMELOCK - 1);

        vm.prank(admin);
        vm.expectRevert(abi.encodeWithSelector(
            IGovernance.TimelockNotExpired.selector,
            1 // 1 second remaining
        ));
        governance.executeProposal(key);
    }

    function test_ExecuteProposalExactlyAtTimelock() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        vm.prank(admin);
        governance.proposeParameter(key, 100);

        // Warp exactly to timelock
        vm.warp(block.timestamp + TIMELOCK);

        vm.prank(admin);
        governance.executeProposal(key);

        assertEq(governance.getParameter(key), 100);
    }

    // ═══════════════════════════════════════════════════════════════
    // CANCEL PROPOSAL TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_CancelProposal() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        vm.prank(admin);
        governance.proposeParameter(key, 100);

        vm.prank(admin);
        governance.cancelProposal(key);

        // Should revert when trying to get canceled proposal
        vm.expectRevert(IGovernance.ProposalNotFound.selector);
        governance.getProposal(key);
    }

    function test_RevertCancelProposalNotAdmin() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        vm.prank(admin);
        governance.proposeParameter(key, 100);

        vm.prank(randomUser);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.cancelProposal(key);
    }

    function test_RevertCancelProposalNotFound() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();
        vm.prank(admin);
        vm.expectRevert(IGovernance.ProposalNotFound.selector);
        governance.cancelProposal(key);
    }

    // ═══════════════════════════════════════════════════════════════
    // EMERGENCY CONTROLS TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_EmergencyPause() public {
        assertFalse(governance.isPaused());

        vm.prank(admin);
        governance.emergencyPause("Security issue");

        assertTrue(governance.isPaused());
    }

    function test_EmergencyPauseEmitsEvent() public {
        vm.prank(admin);
        vm.expectEmit(true, false, false, true);
        emit IGovernance.EmergencyPaused(admin, "Security issue");
        governance.emergencyPause("Security issue");
    }

    function test_EmergencyUnpause() public {
        vm.prank(admin);
        governance.emergencyPause("Security issue");
        assertTrue(governance.isPaused());

        vm.prank(admin);
        governance.emergencyUnpause();
        assertFalse(governance.isPaused());
    }

    function test_EmergencyUnpauseEmitsEvent() public {
        vm.prank(admin);
        governance.emergencyPause("Security issue");

        vm.prank(admin);
        vm.expectEmit(true, false, false, false);
        emit IGovernance.EmergencyUnpaused(admin);
        governance.emergencyUnpause();
    }

    function test_RevertEmergencyPauseNotAdmin() public {
        vm.prank(randomUser);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.emergencyPause("Not allowed");
    }

    function test_RevertEmergencyUnpauseNotAdmin() public {
        vm.prank(admin);
        governance.emergencyPause("Security issue");

        vm.prank(randomUser);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.emergencyUnpause();
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN TRANSFER TESTS
    // ═══════════════════════════════════════════════════════════════

    function test_TransferAdmin() public {
        vm.prank(admin);
        governance.transferAdmin(newAdmin);

        assertEq(governance.admin(), newAdmin);
    }

    function test_TransferAdminEmitsEvent() public {
        vm.prank(admin);
        vm.expectEmit(true, true, false, false);
        emit IGovernance.AdminTransferred(admin, newAdmin);
        governance.transferAdmin(newAdmin);
    }

    function test_RevertTransferAdminNotAdmin() public {
        vm.prank(randomUser);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.transferAdmin(newAdmin);
    }

    function test_RevertTransferAdminZeroAddress() public {
        vm.prank(admin);
        vm.expectRevert(IGovernance.ZeroAddress.selector);
        governance.transferAdmin(address(0));
    }

    function test_NewAdminCanActAfterTransfer() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        vm.prank(admin);
        governance.transferAdmin(newAdmin);

        // New admin can propose
        vm.prank(newAdmin);
        governance.proposeParameter(key, 100);

        // Old admin cannot
        vm.prank(admin);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.proposeParameter(key, 200);
    }

    // ═══════════════════════════════════════════════════════════════
    // PARAMETER VALIDATION TESTS (All Parameters)
    // ═══════════════════════════════════════════════════════════════

    function test_ArbiterFeeBpsRange() public {
        bytes32 key = governance.ARBITER_FEE_BPS();

        // Valid: 100-1000 (1%-10%)
        vm.prank(admin);
        governance.proposeParameter(key, 100);

        vm.prank(admin);
        governance.proposeParameter(key, 1000);

        // Invalid: below 100
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 50);

        // Invalid: above 1000
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 1100);
    }

    function test_MinReputationRange() public {
        bytes32 key = governance.MIN_REPUTATION();

        // Valid: 0-100
        vm.prank(admin);
        governance.proposeParameter(key, 0);

        vm.prank(admin);
        governance.proposeParameter(key, 100);

        // Invalid: above 100
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 101);
    }

    function test_RecoveryThresholdRange() public {
        bytes32 key = governance.RECOVERY_THRESHOLD();

        // Valid: 0.1e18 - 0.9e18
        vm.prank(admin);
        governance.proposeParameter(key, 0.1e18);

        vm.prank(admin);
        governance.proposeParameter(key, 0.9e18);

        // Invalid: below 0.1e18
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 0.05e18);

        // Invalid: above 0.9e18
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 0.95e18);
    }

    function test_DisputeTimeoutRange() public {
        bytes32 key = governance.DISPUTE_TIMEOUT();

        // Valid: 1 day - 30 days
        vm.prank(admin);
        governance.proposeParameter(key, 1 days);

        vm.prank(admin);
        governance.proposeParameter(key, 30 days);

        // Invalid: below 1 day
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 12 hours);

        // Invalid: above 30 days
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 31 days);
    }

    function test_AppealWindowRange() public {
        bytes32 key = governance.APPEAL_WINDOW();

        // Valid: 24 hours - 72 hours
        vm.prank(admin);
        governance.proposeParameter(key, 24 hours);

        vm.prank(admin);
        governance.proposeParameter(key, 72 hours);

        // Invalid: below 24 hours
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 12 hours);

        // Invalid: above 72 hours
        vm.prank(admin);
        vm.expectRevert();
        governance.proposeParameter(key, 96 hours);
    }

    // ═══════════════════════════════════════════════════════════════
    // EDGE CASES
    // ═══════════════════════════════════════════════════════════════

    function test_OverwriteExistingProposal() public {
        bytes32 key = governance.PROTOCOL_FEE_BPS();

        // First proposal
        vm.prank(admin);
        governance.proposeParameter(key, 100);

        // Overwrite with new proposal
        vm.prank(admin);
        governance.proposeParameter(key, 200);

        (uint256 value,) = governance.getProposal(key);
        assertEq(value, 200);
    }

    function test_MultipleParameterProposals() public {
        // Propose multiple parameters
        vm.startPrank(admin);
        governance.proposeParameter(governance.PROTOCOL_FEE_BPS(), 100);
        governance.proposeParameter(governance.ARBITER_FEE_BPS(), 500);
        governance.proposeParameter(governance.MIN_REPUTATION(), 60);
        vm.stopPrank();

        // Warp and execute all
        vm.warp(block.timestamp + TIMELOCK + 1);

        vm.startPrank(admin);
        governance.executeProposal(governance.PROTOCOL_FEE_BPS());
        governance.executeProposal(governance.ARBITER_FEE_BPS());
        governance.executeProposal(governance.MIN_REPUTATION());
        vm.stopPrank();

        assertEq(governance.getParameter(governance.PROTOCOL_FEE_BPS()), 100);
        assertEq(governance.getParameter(governance.ARBITER_FEE_BPS()), 500);
        assertEq(governance.getParameter(governance.MIN_REPUTATION()), 60);
    }

    function test_GetParameterConstants() public view {
        // Verify constant key values
        assertEq(governance.PROTOCOL_FEE_BPS(), keccak256("PROTOCOL_FEE_BPS"));
        assertEq(governance.ARBITER_FEE_BPS(), keccak256("ARBITER_FEE_BPS"));
        assertEq(governance.MIN_REPUTATION(), keccak256("MIN_REPUTATION"));
        assertEq(governance.MIN_STAKE_PERCENT(), keccak256("MIN_STAKE_PERCENT"));
        assertEq(governance.MIN_ARBITER_STAKE_PERCENT(), keccak256("MIN_ARBITER_STAKE_PERCENT"));
        assertEq(governance.RECOVERY_THRESHOLD(), keccak256("RECOVERY_THRESHOLD"));
        assertEq(governance.DISPUTE_TIMEOUT(), keccak256("DISPUTE_TIMEOUT"));
        assertEq(governance.APPEAL_WINDOW(), keccak256("APPEAL_WINDOW"));
        assertEq(governance.MIN_HEARTBEAT_INTERVAL(), keccak256("MIN_HEARTBEAT_INTERVAL"));
    }
}
