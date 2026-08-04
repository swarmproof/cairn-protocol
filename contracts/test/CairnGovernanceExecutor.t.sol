// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {ICairnCore} from "../src/interfaces/ICairnCore.sol";
import {IGovernance} from "../src/interfaces/IGovernance.sol";

/// @title CairnGovernance.execute — governance → CairnCore activation path
/// @notice Proves that CairnCore's onlyGovernance functions are reachable ON-CHAIN
///         (msg.sender == address(governance)) via the executor, WITHOUT vm.prank.
///         This is the path used to activate v2 three-tier routing after deploy.
contract CairnGovernanceExecutorTest is Test {
    CairnGovernance governance;
    CairnCore core;

    address admin = makeAddr("admin");
    address feeRecipient = makeAddr("feeRecipient");
    address stranger = makeAddr("stranger");

    function setUp() public {
        governance = new CairnGovernance(admin);
        // Router/pool/registry not needed for the governance-gated setters under test.
        core = new CairnCore(feeRecipient, address(0), address(0), address(0), address(governance));
    }

    /// The real v2 activation call, exercised through governance (no prank).
    function test_Execute_ActivatesThreeTierRouting() public {
        assertFalse(core.threeTierRoutingEnabled());

        vm.prank(admin); // admin drives governance; governance is msg.sender to core
        governance.execute(
            address(core),
            abi.encodeCall(CairnCore.setThreeTierRouting, (true))
        );

        assertTrue(core.threeTierRoutingEnabled(), "three-tier routing activated on-chain");
    }

    /// Executor reaches other onlyGovernance functions too (e.g. pause).
    function test_Execute_CanPauseCore() public {
        vm.prank(admin);
        governance.execute(address(core), abi.encodeCall(CairnCore.pause, ()));
        assertTrue(core.paused());
    }

    function test_Execute_OnlyAdmin() public {
        vm.prank(stranger);
        vm.expectRevert(IGovernance.NotAdmin.selector);
        governance.execute(address(core), abi.encodeCall(CairnCore.setThreeTierRouting, (true)));
    }

    function test_Execute_RevertZeroTarget() public {
        vm.prank(admin);
        vm.expectRevert(IGovernance.ZeroAddress.selector);
        governance.execute(address(0), abi.encodeCall(CairnCore.setThreeTierRouting, (true)));
    }

    /// A reverting target call bubbles up the target's revert reason.
    function test_Execute_BubblesTargetRevert() public {
        vm.prank(admin);
        vm.expectRevert(abi.encodeWithSelector(ICairnCore.InvalidReducedScopeCap.selector, 20001));
        governance.execute(
            address(core),
            abi.encodeCall(CairnCore.setReducedScopeCap, (20001))
        );
    }

    /// Sanity: without the executor the gate is closed to the admin EOA directly.
    function test_DirectEoaCall_IsRejected() public {
        vm.prank(admin);
        vm.expectRevert(); // NotAuthorized(admin, address(governance))
        core.setThreeTierRouting(true);
    }
}
