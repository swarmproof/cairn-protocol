// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import { Script, console } from "forge-std/Script.sol";
import { CairnTaskMVP } from "../src/CairnTaskMVP.sol";

/// @title Deploy
/// @notice Deployment script for CairnTaskMVP to Base Sepolia
contract Deploy is Script {
    function run() external {
        // Load environment variables
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address owner = vm.envAddress("OWNER_ADDRESS");
        address feeRecipient = vm.envAddress("FEE_RECIPIENT_ADDRESS");

        console.log("=== CairnTaskMVP Deployment ===");
        console.log("Deployer:", vm.addr(deployerPrivateKey));
        console.log("Owner:", owner);
        console.log("Fee Recipient:", feeRecipient);

        vm.startBroadcast(deployerPrivateKey);

        CairnTaskMVP cairn = new CairnTaskMVP(owner, feeRecipient);

        vm.stopBroadcast();

        console.log("=== Deployment Complete ===");
        console.log("CairnTaskMVP deployed at:", address(cairn));
        console.log("Protocol Fee (bps):", cairn.protocolFeeBps());
        console.log("Min Escrow (wei):", cairn.minEscrow());
        console.log("Min Heartbeat (sec):", cairn.minHeartbeatInterval());
    }
}
