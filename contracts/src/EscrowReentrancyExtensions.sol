// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

abstract contract EscrowReentrancyExtensions {
    error TransferFailed(address recipient, uint256 amount);

    function safeTransferETH(address recipient, uint256 amount) internal {
        if (amount == 0) return;
        (bool success, ) = recipient.call{value: amount}("");
        if (!success) {
            revert TransferFailed(recipient, amount);
        }
    }
}
