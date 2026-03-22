// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title IERC8004 - Agent Reputation Registry Interface
/// @notice Standard interface for querying and updating agent reputation scores
/// @dev See https://eips.ethereum.org/EIPS/eip-8004
///
/// Purpose: Provides a decentralized reputation system for autonomous agents
/// across different domains and task types.
///
/// Integration: FallbackPool uses this to enforce the 50/100 reputation gate
/// during agent registration and eligibility checks.
interface IERC8004 {
    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Emitted when an agent's reputation changes
    event ReputationUpdated(
        address indexed agent,
        bytes32 indexed taskType,
        uint256 newReputation,
        uint256 oldReputation
    );

    // ═══════════════════════════════════════════════════════════════
    // REPUTATION QUERIES
    // ═══════════════════════════════════════════════════════════════

    /// @notice Get global reputation score for an agent
    /// @param agent The agent address
    /// @return reputation Score from 0-100 (scaled to 100)
    function getReputation(address agent) external view returns (uint256 reputation);

    /// @notice Get reputation score for a specific task type
    /// @param agent The agent address
    /// @param taskType The task type identifier (e.g., keccak256("solidity.audit"))
    /// @return reputation Score from 0-100 for this task type
    function getReputationForType(address agent, bytes32 taskType)
        external
        view
        returns (uint256 reputation);

    /// @notice Get all task types an agent has reputation in
    /// @param agent The agent address
    /// @return taskTypes Array of task type identifiers
    function getTaskTypes(address agent) external view returns (bytes32[] memory taskTypes);

    // ═══════════════════════════════════════════════════════════════
    // REPUTATION REPORTING
    // ═══════════════════════════════════════════════════════════════

    /// @notice Report successful task completion (increases reputation)
    /// @dev Only authorized reporters (like CairnCore) can call this
    /// @param agent The agent who succeeded
    /// @param taskType The task type completed
    function reportSuccess(address agent, bytes32 taskType) external;

    /// @notice Report task failure (decreases reputation)
    /// @dev Only authorized reporters (like CairnCore) can call this
    /// @param agent The agent who failed
    /// @param taskType The task type failed
    /// @param severity Failure severity (0=minor, 10=critical)
    function reportFailure(address agent, bytes32 taskType, uint8 severity) external;
}
