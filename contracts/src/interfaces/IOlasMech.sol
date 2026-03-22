// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

/// @title IOlasMech - Interface for Olas Mech Marketplace integration
/// @notice Enables CAIRN to query and interact with Olas Mech agents
/// @dev Based on Olas Mech Marketplace contract structure
///      https://github.com/valory-xyz/ai-registry-mech
///
/// Olas Mech Registry on Gnosis: 0x9338b5153AE39BB89f50468E608eD9d764B755fD
interface IOlasMech {
    // ═══════════════════════════════════════════════════════════════
    // STRUCTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Mech agent information
    /// @dev Represents an Olas Mech service available for fallback
    struct MechInfo {
        address mechAddress;        // Contract address of the mech
        uint256 serviceId;          // Service ID in Olas registry
        bytes32[] capabilities;     // Task capabilities (mapped to CAIRN task types)
        uint256 pricePerRequest;    // Cost per request (in wei)
        bool active;                // Currently accepting requests
        uint256 requestsCompleted;  // Total successful requests
        uint256 requestsFailed;     // Total failed requests
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Get mech information by service ID
    /// @param serviceId The Olas service ID
    /// @return Mech information struct
    function getMech(uint256 serviceId) external view returns (MechInfo memory);

    /// @notice Get all mechs supporting a specific capability
    /// @param capability The task capability identifier
    /// @return serviceIds Array of service IDs matching the capability
    function getMechsByCapability(bytes32 capability) external view returns (uint256[] memory serviceIds);

    /// @notice Check if a mech is currently active
    /// @param serviceId The Olas service ID
    /// @return Whether the mech is active
    function isMechActive(uint256 serviceId) external view returns (bool);

    /// @notice Get mech contract address by service ID
    /// @param serviceId The Olas service ID
    /// @return Mech contract address
    function getMechAddress(uint256 serviceId) external view returns (address);

    /// @notice Get price per request for a mech
    /// @param serviceId The Olas service ID
    /// @return Price in wei
    function getMechPrice(uint256 serviceId) external view returns (uint256);
}
