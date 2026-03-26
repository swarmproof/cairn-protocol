// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {CairnTaskMVP} from "../src/CairnTaskMVP.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {RecoveryRouter} from "../src/RecoveryRouter.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";

/// @title DeployCAIRN
/// @notice Full protocol deployment script for CAIRN to Base Sepolia
/// @dev Deploys all contracts in correct order and wires them together
///
/// Deployment Order (handles circular dependencies):
///   1. CairnGovernance (admin)
///   2. RecoveryRouter (cairnCore=0, set later)
///   3. FallbackPool (cairnCore=0, feeRecipient)
///   4. ArbiterRegistry (cairnCore=0, governance, feeRecipient)
///   5. CairnCore (feeRecipient, recoveryRouter, fallbackPool, arbiterRegistry, governance)
///   6. Wire: setCairnCore() on RecoveryRouter, FallbackPool, ArbiterRegistry
///
/// Environment Variables:
///   DEPLOYER_PRIVATE_KEY - Private key for deployment
///   OWNER_ADDRESS - Admin/owner address
///   FEE_RECIPIENT_ADDRESS - Protocol fee recipient
contract DeployCAIRN is Script {
    // Deployed contract addresses
    CairnGovernance public governance;
    RecoveryRouter public recoveryRouter;
    FallbackPool public fallbackPool;
    ArbiterRegistry public arbiterRegistry;
    CairnCore public cairnCore;

    function run() external {
        // Load environment variables
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address admin = vm.envAddress("OWNER_ADDRESS");
        address feeRecipient = vm.envAddress("FEE_RECIPIENT_ADDRESS");

        console.log("===============================================");
        console.log("   CAIRN Protocol Full Deployment");
        console.log("===============================================");
        console.log("Deployer:", vm.addr(deployerPrivateKey));
        console.log("Admin:", admin);
        console.log("Fee Recipient:", feeRecipient);
        console.log("");

        vm.startBroadcast(deployerPrivateKey);

        // ═══════════════════════════════════════════════════════════════
        // PHASE 1: Deploy all contracts
        // ═══════════════════════════════════════════════════════════════

        console.log("[1/6] Deploying CairnGovernance...");
        governance = new CairnGovernance(admin);
        console.log("  -> CairnGovernance:", address(governance));

        console.log("[2/6] Deploying RecoveryRouter...");
        recoveryRouter = new RecoveryRouter(address(0)); // Set cairnCore later
        console.log("  -> RecoveryRouter:", address(recoveryRouter));

        console.log("[3/6] Deploying FallbackPool...");
        // Deploy without ERC registries for now (can be set via setReputationRegistry later)
        fallbackPool = new FallbackPool(address(0), feeRecipient, address(0), address(0), address(0));
        console.log("  -> FallbackPool:", address(fallbackPool));

        console.log("[4/6] Deploying ArbiterRegistry...");
        arbiterRegistry = new ArbiterRegistry(
            address(0), // Set cairnCore later
            address(governance),
            feeRecipient
        );
        console.log("  -> ArbiterRegistry:", address(arbiterRegistry));

        console.log("[5/6] Deploying CairnCore...");
        cairnCore = new CairnCore(
            feeRecipient,
            address(recoveryRouter),
            address(fallbackPool),
            address(arbiterRegistry),
            address(governance)
        );
        console.log("  -> CairnCore:", address(cairnCore));

        // ═══════════════════════════════════════════════════════════════
        // PHASE 2: Wire contracts together
        // ═══════════════════════════════════════════════════════════════

        console.log("[6/6] Wiring contracts...");

        recoveryRouter.setCairnCore(address(cairnCore));
        console.log("  -> RecoveryRouter.cairnCore set");

        fallbackPool.setCairnCore(address(cairnCore));
        console.log("  -> FallbackPool.cairnCore set");

        arbiterRegistry.setCairnCore(address(cairnCore));
        console.log("  -> ArbiterRegistry.cairnCore set");

        vm.stopBroadcast();

        // ═══════════════════════════════════════════════════════════════
        // Summary
        // ═══════════════════════════════════════════════════════════════

        console.log("");
        console.log("===============================================");
        console.log("   Deployment Complete!");
        console.log("===============================================");
        console.log("");
        console.log("Contract Addresses:");
        console.log("  CairnGovernance:", address(governance));
        console.log("  RecoveryRouter:", address(recoveryRouter));
        console.log("  FallbackPool:", address(fallbackPool));
        console.log("  ArbiterRegistry:", address(arbiterRegistry));
        console.log("  CairnCore:", address(cairnCore));
        console.log("");
        console.log("Protocol Parameters:");
        console.log("  Protocol Fee (bps):", governance.getParameter(governance.PROTOCOL_FEE_BPS()));
        console.log("  Arbiter Fee (bps):", governance.getParameter(governance.ARBITER_FEE_BPS()));
        console.log("  Min Reputation:", governance.getParameter(governance.MIN_REPUTATION()));
        console.log("  Min Stake (%):", governance.getParameter(governance.MIN_STAKE_PERCENT()));
        console.log("");
        console.log("Next Steps:");
        console.log("  1. Verify contracts on BaseScan");
        console.log("  2. Update frontend with contract addresses");
        console.log("  3. Register fallback agents via FallbackPool.register()");
        console.log("  4. Register arbiters via ArbiterRegistry.registerArbiter()");
        console.log("===============================================");
    }
}

/// @title DeployMVP
/// @notice Simplified MVP deployment (CairnTaskMVP only)
/// @dev Use this for quick testing without full protocol
contract DeployMVP is Script {
    function run() external {
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
