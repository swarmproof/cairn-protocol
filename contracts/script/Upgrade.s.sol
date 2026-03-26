// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {CairnCoreUpgradeable} from "../src/upgradeable/CairnCoreUpgradeable.sol";
import {FallbackPoolUpgradeable} from "../src/upgradeable/FallbackPoolUpgradeable.sol";
import {ArbiterRegistryUpgradeable} from "../src/upgradeable/ArbiterRegistryUpgradeable.sol";
import {RecoveryRouterUpgradeable} from "../src/upgradeable/RecoveryRouterUpgradeable.sol";

/// @title Upgrade
/// @notice Upgrade CAIRN contracts to new implementations
/// @dev Based on PRD-06 Section 3.4 - UUPS upgrade pattern
contract Upgrade is Script {
    enum ContractType {
        CairnCore,
        FallbackPool,
        ArbiterRegistry,
        RecoveryRouter
    }

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        // Get contract type from environment
        string memory contractTypeStr = vm.envString("UPGRADE_CONTRACT");
        ContractType contractType = _parseContractType(contractTypeStr);

        // Get proxy address from environment
        address proxyAddress = vm.envAddress("PROXY_ADDRESS");

        console2.log("==============================================");
        console2.log("CAIRN Protocol - Contract Upgrade");
        console2.log("==============================================");
        console2.log("Upgrader:", deployer);
        console2.log("Contract:", contractTypeStr);
        console2.log("Proxy Address:", proxyAddress);
        console2.log("Chain ID:", block.chainid);
        console2.log("==============================================");

        vm.startBroadcast(deployerPrivateKey);

        address newImplementation;

        // Deploy new implementation
        if (contractType == ContractType.CairnCore) {
            console2.log("\nDeploying new CairnCore implementation...");
            newImplementation = address(new CairnCoreUpgradeable());
        } else if (contractType == ContractType.FallbackPool) {
            console2.log("\nDeploying new FallbackPool implementation...");
            newImplementation = address(new FallbackPoolUpgradeable());
        } else if (contractType == ContractType.ArbiterRegistry) {
            console2.log("\nDeploying new ArbiterRegistry implementation...");
            newImplementation = address(new ArbiterRegistryUpgradeable());
        } else if (contractType == ContractType.RecoveryRouter) {
            console2.log("\nDeploying new RecoveryRouter implementation...");
            newImplementation = address(new RecoveryRouterUpgradeable());
        }

        console2.log("New implementation:", newImplementation);

        // Perform upgrade
        console2.log("\nUpgrading proxy...");
        UUPSUpgradeable(proxyAddress).upgradeToAndCall(newImplementation, "");
        console2.log("Upgrade successful!");

        vm.stopBroadcast();

        console2.log("\n==============================================");
        console2.log("UPGRADE SUMMARY");
        console2.log("==============================================");
        console2.log("Contract:", contractTypeStr);
        console2.log("Proxy:", proxyAddress);
        console2.log("New Implementation:", newImplementation);
        console2.log("==============================================");
    }

    function _parseContractType(string memory contractTypeStr) internal pure returns (ContractType) {
        bytes32 hash = keccak256(bytes(contractTypeStr));

        if (hash == keccak256("CairnCore")) {
            return ContractType.CairnCore;
        } else if (hash == keccak256("FallbackPool")) {
            return ContractType.FallbackPool;
        } else if (hash == keccak256("ArbiterRegistry")) {
            return ContractType.ArbiterRegistry;
        } else if (hash == keccak256("RecoveryRouter")) {
            return ContractType.RecoveryRouter;
        }

        revert("Invalid contract type");
    }
}
