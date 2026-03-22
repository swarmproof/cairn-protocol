// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title IERC7710 - Scoped Delegation Interface
/// @notice Standard interface for time-boxed, scope-limited delegation
/// @dev See https://eips.ethereum.org/EIPS/eip-7710
///
/// Purpose: Allows operators to delegate agent selection authority to
/// third-party services or governance contracts with granular control.
///
/// Integration: FallbackPool checks delegation before allowing registration
/// on behalf of an agent owner.
interface IERC7710 {
    // ═══════════════════════════════════════════════════════════════
    // STRUCTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Delegation record
    struct Delegation {
        address delegatee;      // Who can act on behalf of delegator
        bytes32 scope;          // What actions are delegated (e.g., "fallback.register")
        uint256 expiry;         // When delegation expires (0 = permanent)
        bool active;            // Can be revoked early
    }

    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Emitted when a new delegation is created
    event DelegationCreated(
        bytes32 indexed delegationId,
        address indexed delegator,
        address indexed delegatee,
        bytes32 scope,
        uint256 expiry
    );

    /// @notice Emitted when a delegation is revoked
    event DelegationRevoked(
        bytes32 indexed delegationId,
        address indexed delegator,
        address indexed delegatee
    );

    // ═══════════════════════════════════════════════════════════════
    // DELEGATION MANAGEMENT
    // ═══════════════════════════════════════════════════════════════

    /// @notice Create a new scoped delegation
    /// @param to Address being granted delegation
    /// @param scope Action scope (e.g., keccak256("fallback.register"))
    /// @param duration Duration in seconds (0 = permanent)
    /// @return delegationId Unique delegation identifier
    function delegate(address to, bytes32 scope, uint256 duration)
        external
        returns (bytes32 delegationId);

    /// @notice Revoke an existing delegation
    /// @param delegationId The delegation to revoke
    function revoke(bytes32 delegationId) external;

    // ═══════════════════════════════════════════════════════════════
    // DELEGATION QUERIES
    // ═══════════════════════════════════════════════════════════════

    /// @notice Check if an actor can perform an action in a scope
    /// @param actor The address attempting to act
    /// @param scope The action scope being checked
    /// @return authorized True if actor has active delegation for scope
    function canAct(address actor, bytes32 scope) external view returns (bool authorized);

    /// @notice Get delegation details
    /// @param delegationId The delegation ID
    /// @return delegation The delegation record
    function getDelegation(bytes32 delegationId)
        external
        view
        returns (Delegation memory delegation);
}
