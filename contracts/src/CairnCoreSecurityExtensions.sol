// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library CairnCoreSecurityExtensions {
    error DisputeTimeoutNotReached();

    function validateDisputeTimeout(uint256 disputedAt, uint256 disputeTimeout) internal view {
        if (disputedAt == 0 || block.timestamp < disputedAt + disputeTimeout) {
            revert DisputeTimeoutNotReached();
        }
    }
}
