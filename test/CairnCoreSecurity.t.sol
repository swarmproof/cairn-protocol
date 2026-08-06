// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../contracts/src/CairnCoreSecurityExtensions.sol";

contract CairnCoreSecurityTest is Test {
    function testDisputeTimeoutFromDisputedAt() public {
        uint256 disputedAt = 1000;
        uint256 disputeTimeout = 7 days;

        vm.warp(disputedAt + disputeTimeout - 1);
        vm.expectRevert(CairnCoreSecurityExtensions.DisputeTimeoutNotReached.selector);
        CairnCoreSecurityExtensions.validateDisputeTimeout(disputedAt, disputeTimeout);

        vm.warp(disputedAt + disputeTimeout);
        CairnCoreSecurityExtensions.validateDisputeTimeout(disputedAt, disputeTimeout);
    }
}
