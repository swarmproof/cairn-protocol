// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {IFallbackPool} from "../src/interfaces/IFallbackPool.sol";
import {RecoveryRouter} from "../src/RecoveryRouter.sol";
import {RecoveryRouterV2} from "../src/RecoveryRouterV2.sol";

/// @title Access-control regression tests for CR-1 / CR-2
/// @notice Proves the previously-unprotected admin setters on the non-upgradeable
///         FallbackPool and both routers now reject non-owner callers, closing the
///         privilege-takeover / protocol-brick vectors from the security audit.
contract SecurityAccessControlTest is Test {
    FallbackPool internal pool;
    RecoveryRouter internal routerV1;
    RecoveryRouterV2 internal routerV2;

    address internal feeRecipient = address(0xFEE);
    address internal attacker = address(0xBAD);
    address internal legitCore = address(0xC0DE);

    function setUp() public {
        // This contract is the deployer → owner of all three.
        pool = new FallbackPool(address(0), feeRecipient, address(0), address(0), address(0));
        routerV1 = new RecoveryRouter(address(0));
        routerV2 = new RecoveryRouterV2(address(0));
    }

    // ─── CR-1: FallbackPool ───────────────────────────────────────────

    function test_CR1_FallbackPool_SetCairnCore_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        pool.setCairnCore(attacker);
    }

    function test_CR1_FallbackPool_SetReputationRegistry_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        pool.setReputationRegistry(attacker);
    }

    function test_CR1_FallbackPool_SetDelegationRegistry_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        pool.setDelegationRegistry(attacker);
    }

    function test_CR1_FallbackPool_SetOlasMechAdapter_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        pool.setOlasMechAdapter(attacker);
    }

    function test_CR1_FallbackPool_OwnerCanSetCairnCore() public {
        pool.setCairnCore(legitCore);
        assertEq(pool.cairnCore(), legitCore);
    }

    function test_CR1_FallbackPool_SetCairnCore_RejectsZeroAddress() public {
        vm.expectRevert(IFallbackPool.ZeroAddress.selector);
        pool.setCairnCore(address(0));
    }

    // ─── CR-2: RecoveryRouter (v1) ────────────────────────────────────

    function test_CR2_RouterV1_SetCairnCore_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        routerV1.setCairnCore(attacker);
    }

    function test_CR2_RouterV1_SetRecoveryThreshold_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        routerV1.setRecoveryThreshold(0.5e18);
    }

    function test_CR2_RouterV1_OwnerCanSetCairnCore() public {
        routerV1.setCairnCore(legitCore);
        assertEq(routerV1.cairnCore(), legitCore);
    }

    // ─── CR-2: RecoveryRouterV2 ───────────────────────────────────────

    function test_CR2_RouterV2_SetCairnCore_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        routerV2.setCairnCore(attacker);
    }

    function test_CR2_RouterV2_SetThresholds_RevertsForNonOwner() public {
        vm.prank(attacker);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, attacker));
        routerV2.setThresholds(0.5e18, 0.4e18);
    }

    function test_CR2_RouterV2_OwnerCanSetThresholds() public {
        routerV2.setThresholds(0.5e18, 0.4e18);
        assertEq(routerV2.upperThreshold(), 0.5e18);
        assertEq(routerV2.lowerThreshold(), 0.4e18);
    }
}
