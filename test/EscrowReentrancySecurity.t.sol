// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../contracts/src/EscrowReentrancyExtensions.sol";

contract MockEscrowTransfer is EscrowReentrancyExtensions {
    function executeTransfer(address recipient, uint256 amount) external payable {
        safeTransferETH(recipient, amount);
    }
}

contract EscrowReentrancySecurityTest is Test {
    MockEscrowTransfer mockEscrow;

    function setUp() public {
        mockEscrow = new MockEscrowTransfer();
    }

    function testSafeETHTransferSuccess() public {
        address recipient = address(0x123);
        vm.deal(address(mockEscrow), 1 ether);
        mockEscrow.executeTransfer(recipient, 1 ether);
        assertEq(recipient.balance, 1 ether);
    }
}
