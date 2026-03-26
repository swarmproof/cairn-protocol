// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import "forge-std/Script.sol";
import "../src/CairnGovernance.sol";

/// @title Transfer Governance to Multi-sig
/// @notice Transfers CairnGovernance admin to a Gnosis Safe multi-sig
/// @dev Run after deploying Safe: forge script TransferToMultisig --rpc-url $RPC_URL --broadcast
contract TransferToMultisig is Script {
    // Deployed CairnGovernance on Base Sepolia
    address constant GOVERNANCE = 0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f;

    function run() external {
        // Read Safe address from environment
        address safe = vm.envAddress("SAFE_ADDRESS");
        require(safe != address(0), "SAFE_ADDRESS not set");

        // Verify current admin
        CairnGovernance governance = CairnGovernance(GOVERNANCE);
        address currentAdmin = governance.admin();
        console.log("Current admin:", currentAdmin);
        console.log("New admin (Safe):", safe);

        // Transfer admin
        vm.startBroadcast();
        governance.transferAdmin(safe);
        vm.stopBroadcast();

        // Verify transfer
        address newAdmin = governance.admin();
        require(newAdmin == safe, "Transfer failed");
        console.log("Admin transferred successfully to:", newAdmin);
    }
}
