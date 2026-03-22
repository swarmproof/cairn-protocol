// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {ERC1967Proxy} from "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";
import {CairnCoreUpgradeable} from "../src/upgradeable/CairnCoreUpgradeable.sol";
import {FallbackPoolUpgradeable} from "../src/upgradeable/FallbackPoolUpgradeable.sol";
import {ArbiterRegistryUpgradeable} from "../src/upgradeable/ArbiterRegistryUpgradeable.sol";
import {RecoveryRouterUpgradeable} from "../src/upgradeable/RecoveryRouterUpgradeable.sol";
import {CairnGovernance} from "../src/CairnGovernance.sol";

/// @title DeployUpgradeable
/// @notice Deploy all CAIRN contracts behind UUPS proxies
/// @dev Based on PRD-06 Section 3.4
contract DeployUpgradeable is Script {
    // Deployment addresses
    address public governance;
    address public recoveryRouter;
    address public fallbackPool;
    address public arbiterRegistry;
    address public cairnCore;

    // Implementation addresses
    address public cairnCoreImpl;
    address public fallbackPoolImpl;
    address public arbiterRegistryImpl;
    address public recoveryRouterImpl;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        address feeRecipient = vm.envOr("FEE_RECIPIENT", deployer);

        console2.log("==============================================");
        console2.log("CAIRN Protocol - Upgradeable Deployment");
        console2.log("==============================================");
        console2.log("Deployer:", deployer);
        console2.log("Fee Recipient:", feeRecipient);
        console2.log("Chain ID:", block.chainid);
        console2.log("==============================================");

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy Governance (non-upgradeable)
        console2.log("\n1. Deploying CairnGovernance...");
        governance = address(new CairnGovernance(deployer));
        console2.log("   CairnGovernance:", governance);

        // 2. Deploy RecoveryRouter implementation
        console2.log("\n2. Deploying RecoveryRouter implementation...");
        recoveryRouterImpl = address(new RecoveryRouterUpgradeable());
        console2.log("   RecoveryRouter implementation:", recoveryRouterImpl);

        // 3. Deploy RecoveryRouter proxy
        console2.log("\n3. Deploying RecoveryRouter proxy...");
        bytes memory recoveryRouterInitData = abi.encodeCall(
            RecoveryRouterUpgradeable.initialize,
            (address(0), deployer) // cairnCore = 0 initially, will be set later
        );
        ERC1967Proxy recoveryRouterProxy = new ERC1967Proxy(
            recoveryRouterImpl,
            recoveryRouterInitData
        );
        recoveryRouter = address(recoveryRouterProxy);
        console2.log("   RecoveryRouter proxy:", recoveryRouter);

        // 4. Deploy FallbackPool implementation
        console2.log("\n4. Deploying FallbackPool implementation...");
        fallbackPoolImpl = address(new FallbackPoolUpgradeable());
        console2.log("   FallbackPool implementation:", fallbackPoolImpl);

        // 5. Deploy FallbackPool proxy
        console2.log("\n5. Deploying FallbackPool proxy...");
        bytes memory fallbackPoolInitData = abi.encodeCall(
            FallbackPoolUpgradeable.initialize,
            (address(0), feeRecipient, deployer) // cairnCore = 0 initially
        );
        ERC1967Proxy fallbackPoolProxy = new ERC1967Proxy(
            fallbackPoolImpl,
            fallbackPoolInitData
        );
        fallbackPool = address(fallbackPoolProxy);
        console2.log("   FallbackPool proxy:", fallbackPool);

        // 6. Deploy ArbiterRegistry implementation
        console2.log("\n6. Deploying ArbiterRegistry implementation...");
        arbiterRegistryImpl = address(new ArbiterRegistryUpgradeable());
        console2.log("   ArbiterRegistry implementation:", arbiterRegistryImpl);

        // 7. Deploy ArbiterRegistry proxy
        console2.log("\n7. Deploying ArbiterRegistry proxy...");
        bytes memory arbiterRegistryInitData = abi.encodeCall(
            ArbiterRegistryUpgradeable.initialize,
            (address(0), governance, feeRecipient, deployer) // cairnCore = 0 initially
        );
        ERC1967Proxy arbiterRegistryProxy = new ERC1967Proxy(
            arbiterRegistryImpl,
            arbiterRegistryInitData
        );
        arbiterRegistry = address(arbiterRegistryProxy);
        console2.log("   ArbiterRegistry proxy:", arbiterRegistry);

        // 8. Deploy CairnCore implementation
        console2.log("\n8. Deploying CairnCore implementation...");
        cairnCoreImpl = address(new CairnCoreUpgradeable());
        console2.log("   CairnCore implementation:", cairnCoreImpl);

        // 9. Deploy CairnCore proxy
        console2.log("\n9. Deploying CairnCore proxy...");
        bytes memory cairnCoreInitData = abi.encodeCall(
            CairnCoreUpgradeable.initialize,
            (feeRecipient, recoveryRouter, fallbackPool, arbiterRegistry, governance)
        );
        ERC1967Proxy cairnCoreProxy = new ERC1967Proxy(
            cairnCoreImpl,
            cairnCoreInitData
        );
        cairnCore = address(cairnCoreProxy);
        console2.log("   CairnCore proxy:", cairnCore);

        // 10. Set CairnCore addresses in other contracts
        console2.log("\n10. Configuring contract references...");
        RecoveryRouterUpgradeable(recoveryRouter).setCairnCore(cairnCore);
        FallbackPoolUpgradeable(fallbackPool).setCairnCore(cairnCore);
        ArbiterRegistryUpgradeable(payable(arbiterRegistry)).setCairnCore(cairnCore);
        console2.log("   All contract references configured");

        vm.stopBroadcast();

        // Print deployment summary
        console2.log("\n==============================================");
        console2.log("DEPLOYMENT SUMMARY");
        console2.log("==============================================");
        console2.log("CairnGovernance:", governance);
        console2.log("");
        console2.log("RecoveryRouter Proxy:", recoveryRouter);
        console2.log("RecoveryRouter Implementation:", recoveryRouterImpl);
        console2.log("");
        console2.log("FallbackPool Proxy:", fallbackPool);
        console2.log("FallbackPool Implementation:", fallbackPoolImpl);
        console2.log("");
        console2.log("ArbiterRegistry Proxy:", arbiterRegistry);
        console2.log("ArbiterRegistry Implementation:", arbiterRegistryImpl);
        console2.log("");
        console2.log("CairnCore Proxy:", cairnCore);
        console2.log("CairnCore Implementation:", cairnCoreImpl);
        console2.log("==============================================");

        // Save deployment addresses to a file
        _saveDeployment();
    }

    function _saveDeployment() internal {
        string memory obj = "deployment";

        vm.serializeAddress(obj, "governance", governance);
        vm.serializeAddress(obj, "recoveryRouter", recoveryRouter);
        vm.serializeAddress(obj, "recoveryRouterImpl", recoveryRouterImpl);
        vm.serializeAddress(obj, "fallbackPool", fallbackPool);
        vm.serializeAddress(obj, "fallbackPoolImpl", fallbackPoolImpl);
        vm.serializeAddress(obj, "arbiterRegistry", arbiterRegistry);
        vm.serializeAddress(obj, "arbiterRegistryImpl", arbiterRegistryImpl);
        vm.serializeAddress(obj, "cairnCore", cairnCore);
        string memory finalJson = vm.serializeAddress(obj, "cairnCoreImpl", cairnCoreImpl);

        string memory path = string.concat(
            "./deployments/",
            vm.toString(block.chainid),
            "-upgradeable.json"
        );
        vm.writeJson(finalJson, path);
        console2.log("\nDeployment addresses saved to:", path);
    }
}
