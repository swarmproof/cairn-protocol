// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

/// @title IFallbackPool - Reputation-gated, stake-secured fallback agent pool
/// @notice Manages registration, selection, and slashing of fallback agents
/// @dev Based on PRD-04 Section 2-3
///
/// Two-Gate Admission (PRD-04 Section 2.2):
///   1. Reputation >= 50 (from ERC-8004)
///   2. Stake >= 10% of max eligible escrow
///
/// Selection Algorithm (PRD-04 Section 2.4):
///   score = (success_rate × 0.4) + (reputation × 0.3) + (stake_ratio × 0.2) + (availability × 0.1)
///
/// Slashing Rules (PRD-04 Section 2.5):
///   - Accept + 0 checkpoints + fail → 100% stake to operator
///   - Accept + some checkpoints + fail → 50% stake to treasury
///   - Timeout without response → 25% stake to treasury
interface IFallbackPool {
    // ═══════════════════════════════════════════════════════════════
    // STRUCTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Fallback agent registration data
    struct FallbackAgent {
        bool registered;
        uint256 stake;
        bytes32[] supportedTaskTypes;
        uint256 reputation;
        uint256 activeTaskCount;
        uint256 maxConcurrentTasks;
        uint256 completedTasks;
        uint256 failedTasks;
        uint256 lastActive;
    }

    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    event AgentRegistered(address indexed agent, bytes32[] taskTypes, uint256 stake);
    event AgentDeregistered(address indexed agent, uint256 stakeReturned);
    event StakeAdded(address indexed agent, uint256 amount, uint256 newTotal);
    event StakeWithdrawn(address indexed agent, uint256 amount, uint256 newTotal);
    event FallbackActivated(bytes32 indexed taskId, address indexed fallbackAgent);
    event FallbackCompleted(bytes32 indexed taskId, address indexed fallbackAgent, bool success);
    event AgentSlashed(address indexed agent, uint256 amount, address recipient, string reason);

    // ═══════════════════════════════════════════════════════════════
    // ERRORS
    // ═══════════════════════════════════════════════════════════════

    error AlreadyRegistered();
    error NotRegistered();
    error InsufficientStake(uint256 required, uint256 provided);
    error InsufficientReputation(uint256 required, uint256 actual);
    error NoEligibleFallback();
    error ActiveRecoveriesPending();
    error NotCairnCore();
    error ZeroAddress();
    error InvalidTaskTypes();
    error AtMaxCapacity();

    // ═══════════════════════════════════════════════════════════════
    // REGISTRATION
    // ═══════════════════════════════════════════════════════════════

    /// @notice Register as a fallback agent
    /// @dev Requires stake > 0 and reputation >= minReputation
    /// @param taskTypes List of task types this agent can handle
    /// @param maxConcurrent Maximum concurrent recovery tasks
    function register(bytes32[] calldata taskTypes, uint256 maxConcurrent) external payable;

    /// @notice Add additional stake
    function addStake() external payable;

    /// @notice Withdraw stake (only if no active recoveries)
    /// @param amount Amount to withdraw
    function withdrawStake(uint256 amount) external;

    /// @notice Deregister from the pool (only if no active recoveries)
    function deregister() external;

    // ═══════════════════════════════════════════════════════════════
    // SELECTION (Called by CairnCore)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Select the best fallback agent for a task
    /// @dev Called by CairnCore during task submission
    /// @param taskType The task type identifier
    /// @param escrowAmount Task escrow (determines minimum stake)
    /// @return bestAgent Address of selected fallback (address(0) if none)
    function selectFallback(bytes32 taskType, uint256 escrowAmount) external view returns (address bestAgent);

    /// @notice Activate a fallback agent for recovery
    /// @dev Called by CairnCore when transitioning to RECOVERING
    /// @param taskId The task being recovered
    /// @param fallbackAgent The selected fallback agent
    function activateFallback(bytes32 taskId, address fallbackAgent) external;

    /// @notice Mark recovery task completed
    /// @dev Called by CairnCore on task completion/failure
    /// @param taskId The task ID
    /// @param fallbackAgent The fallback agent
    /// @param success Whether recovery succeeded
    /// @param checkpointsCommitted Number of checkpoints fallback committed
    function completeFallbackTask(
        bytes32 taskId,
        address fallbackAgent,
        bool success,
        uint256 checkpointsCommitted
    ) external;

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Get agent info
    function getAgent(address agent) external view returns (FallbackAgent memory);

    /// @notice Get minimum stake required for an escrow amount
    function getMinStake(uint256 escrowAmount) external view returns (uint256);

    /// @notice Get minimum reputation required
    function minReputation() external view returns (uint256);

    /// @notice Get minimum stake percentage
    function minStakePercent() external view returns (uint256);

    /// @notice Get CairnCore address
    function cairnCore() external view returns (address);

    /// @notice Get fee recipient for slashed funds
    function feeRecipient() external view returns (address);
}
