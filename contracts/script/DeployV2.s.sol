// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {CairnCore} from "../src/CairnCore.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";
import {RecoveryRouterV2} from "../src/RecoveryRouterV2.sol";
import {FallbackPool} from "../src/FallbackPool.sol";
import {ArbiterRegistry} from "../src/ArbiterRegistry.sol";

/// @title DeployCairnV2
/// @notice Deploys the CAIRN v2 stack with the multiplicative RecoveryRouterV2
///         (three-tier routing) and 20% arbiter stake + checkpoint schema
///         validation baked into the contracts (PRD-04).
/// @dev Deploy-time actions only. Enabling three-tier routing
///      (`CairnCore.setThreeTierRouting(true)`) is `onlyGovernance` and is
///      performed AFTER deployment via the governance path — see
///      docs/v2-deployment-runbook.md. USER runs this script; agents never deploy.
///
/// Required env:
///   DEPLOYER_PRIVATE_KEY, ADMIN_ADDRESS, FEE_RECIPIENT_ADDRESS
contract DeployCairnV2 is Script {
    CairnGovernance public governance;
    RecoveryRouterV2 public recoveryRouter;
    FallbackPool public fallbackPool;
    ArbiterRegistry public arbiterRegistry;
    CairnCore public cairnCore;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address admin = vm.envAddress("ADMIN_ADDRESS");
        address feeRecipient = vm.envAddress("FEE_RECIPIENT_ADDRESS");

        console.log("===============================================");
        console.log("   CAIRN v2 Deployment (RecoveryRouterV2)");
        console.log("===============================================");
        console.log("Deployer:", vm.addr(deployerPrivateKey));
        console.log("Admin:", admin);
        console.log("Fee Recipient:", feeRecipient);
        console.log("");

        vm.startBroadcast(deployerPrivateKey);

        console.log("[1/6] Deploying CairnGovernance...");
        governance = new CairnGovernance(admin);
        console.log("  -> CairnGovernance:", address(governance));

        console.log("[2/6] Deploying RecoveryRouterV2...");
        recoveryRouter = new RecoveryRouterV2(address(0)); // cairnCore set below
        console.log("  -> RecoveryRouterV2:", address(recoveryRouter));

        console.log("[3/6] Deploying FallbackPool...");
        fallbackPool = new FallbackPool(address(0), feeRecipient, address(0), address(0), address(0));
        console.log("  -> FallbackPool:", address(fallbackPool));

        console.log("[4/6] Deploying ArbiterRegistry (20% stake)...");
        arbiterRegistry = new ArbiterRegistry(address(0), address(governance), feeRecipient);
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

        console.log("[6/6] Wiring contracts...");
        recoveryRouter.setCairnCore(address(cairnCore));
        fallbackPool.setCairnCore(address(cairnCore));
        arbiterRegistry.setCairnCore(address(cairnCore));

        vm.stopBroadcast();

        console.log("");
        console.log("=============== Deployed (v2) ===============");
        console.log("  CairnGovernance:  ", address(governance));
        console.log("  RecoveryRouterV2: ", address(recoveryRouter));
        console.log("  FallbackPool:     ", address(fallbackPool));
        console.log("  ArbiterRegistry:  ", address(arbiterRegistry));
        console.log("  CairnCore:        ", address(cairnCore));
        console.log("");
        console.log("POST-DEPLOY (governance, see docs/v2-deployment-runbook.md):");
        console.log("  * CairnCore.setThreeTierRouting(true)  <- activates v2 routing");
        console.log("  * Verify all 5 contracts on BaseScan");
        console.log("  * Update README 'Deployed Contracts' + frontend addresses");
        console.log("=============================================");
    }
}
