// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

/// @title IGovernance - Protocol governance interface
/// @notice Manages protocol parameters with timelock
/// @dev Based on PRD-06 Section 3
///
/// Governance Phases (PRD-06 Section 3.1):
///   1. Launch: Single admin key
///   2. Multi-sig: 3-of-5 + 48h timelock
///   3. Token: Token governance (future)
///
/// Configurable Parameters (PRD-06 Section 3.2):
///   - Protocol fee: 0.5% (0-5%)
///   - Fallback min reputation: 50 (0-100)
///   - Fallback min stake %: 10% (1-50%)
///   - Arbiter min stake %: 15% (5-50%)
///   - Arbiter fee: 3% (1-10%)
///   - Dispute timeout: 7 days (1-30 days)
///   - Appeal window: 48 hours (24-72 hours)
///   - Recovery threshold: 0.3 (0.1-0.9)
interface IGovernance {
    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    event ParameterUpdated(bytes32 indexed key, uint256 oldValue, uint256 newValue);
    event ParameterProposed(bytes32 indexed key, uint256 newValue, uint256 executeAfter);
    event EmergencyPaused(address indexed by, string reason);
    event EmergencyUnpaused(address indexed by);
    event AdminTransferred(address indexed oldAdmin, address indexed newAdmin);

    // ═══════════════════════════════════════════════════════════════
    // ERRORS
    // ═══════════════════════════════════════════════════════════════

    error NotAdmin();
    error TimelockNotExpired(uint256 remaining);
    error ValueOutOfRange(bytes32 key, uint256 value, uint256 min, uint256 max);
    error ProposalNotFound();
    error ZeroAddress();

    // ═══════════════════════════════════════════════════════════════
    // PARAMETER KEYS
    // ═══════════════════════════════════════════════════════════════

    // Fee parameters
    function PROTOCOL_FEE_BPS() external view returns (bytes32);
    function ARBITER_FEE_BPS() external view returns (bytes32);

    // Threshold parameters
    function MIN_REPUTATION() external view returns (bytes32);
    function MIN_STAKE_PERCENT() external view returns (bytes32);
    function MIN_ARBITER_STAKE_PERCENT() external view returns (bytes32);
    function RECOVERY_THRESHOLD() external view returns (bytes32);

    // Timing parameters
    function DISPUTE_TIMEOUT() external view returns (bytes32);
    function APPEAL_WINDOW() external view returns (bytes32);
    function MIN_HEARTBEAT_INTERVAL() external view returns (bytes32);

    // ═══════════════════════════════════════════════════════════════
    // PARAMETER MANAGEMENT
    // ═══════════════════════════════════════════════════════════════

    /// @notice Propose a parameter change (starts timelock)
    /// @param key Parameter key
    /// @param value New value
    function proposeParameter(bytes32 key, uint256 value) external;

    /// @notice Execute a proposed parameter change (after timelock)
    /// @param key Parameter key
    function executeProposal(bytes32 key) external;

    /// @notice Cancel a pending proposal
    /// @param key Parameter key
    function cancelProposal(bytes32 key) external;

    /// @notice Get current parameter value
    /// @param key Parameter key
    /// @return value Current value
    function getParameter(bytes32 key) external view returns (uint256 value);

    /// @notice Get pending proposal for a parameter
    /// @param key Parameter key
    /// @return newValue Proposed value
    /// @return executeAfter When proposal can be executed
    function getProposal(bytes32 key) external view returns (uint256 newValue, uint256 executeAfter);

    // ═══════════════════════════════════════════════════════════════
    // EMERGENCY CONTROLS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Emergency pause all protocol operations
    /// @param reason Reason for pause (logged)
    function emergencyPause(string calldata reason) external;

    /// @notice Resume protocol operations
    function emergencyUnpause() external;

    // ═══════════════════════════════════════════════════════════════
    // ADMIN
    // ═══════════════════════════════════════════════════════════════

    /// @notice Transfer admin role
    /// @param newAdmin New admin address
    function transferAdmin(address newAdmin) external;

    /// @notice Get current admin
    function admin() external view returns (address);

    /// @notice Get timelock duration
    function timelockDuration() external view returns (uint256);

    /// @notice Check if protocol is paused
    function isPaused() external view returns (bool);
}
