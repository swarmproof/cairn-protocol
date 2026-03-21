// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {ICairnTypes} from "./ICairnTypes.sol";

/// @title IRecoveryRouter - Failure classification and recovery scoring
/// @notice Classifies failures and computes recovery likelihood scores
/// @dev Based on PRD-02 Section 2.1-2.2
///
/// Recovery Score Formula (PRD-02):
///   score = (failure_class_weight × 0.5) + (budget_remaining × 0.3) + (deadline_remaining × 0.2)
///
/// Class Weights:
///   - LIVENESS: 0.9 (high recovery potential)
///   - RESOURCE: 0.5 (medium recovery potential)
///   - LOGIC: 0.1 (low recovery potential)
///
/// Routing:
///   - score >= 0.3 → RECOVERING (fallback assigned)
///   - score < 0.3 → DISPUTED (arbiter needed)
interface IRecoveryRouter {
    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Emitted when a failure is classified and scored
    event FailureClassified(
        bytes32 indexed taskId,
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 recoveryScore,
        bytes32 failureRecordCID
    );

    /// @notice Emitted when a failure record is written
    event FailureRecordCreated(
        bytes32 indexed taskId,
        bytes32 indexed recordCID,
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 timestamp
    );

    // ═══════════════════════════════════════════════════════════════
    // ERRORS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Caller is not authorized to classify failures
    error NotAuthorized();

    /// @notice Task data is invalid or incomplete
    error InvalidTaskData();

    // ═══════════════════════════════════════════════════════════════
    // CORE FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Classify a failure and compute recovery score
    /// @dev Called by CairnCore when a task fails (heartbeat miss)
    /// @param taskId The failing task's ID
    /// @param escrowAmount Task's escrowed funds
    /// @param createdAt Task creation timestamp
    /// @param deadline Task deadline timestamp
    /// @param checkpointCount Number of checkpoints completed
    /// @return failureClass The classified failure type
    /// @return failureType Specific failure within the class
    /// @return recoveryScore Recovery likelihood (0-1e18 scale)
    /// @return failureRecordCID IPFS CID of the failure record
    function classifyAndScore(
        bytes32 taskId,
        uint256 escrowAmount,
        uint256 createdAt,
        uint256 deadline,
        uint256 checkpointCount
    ) external returns (
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 recoveryScore,
        bytes32 failureRecordCID
    );

    /// @notice Compute recovery score for given parameters
    /// @dev View function for simulation/queries
    /// @param failureClass The failure classification
    /// @param budgetRemaining Percentage of budget remaining (0-1e18)
    /// @param deadlineRemaining Percentage of deadline remaining (0-1e18)
    /// @return score Recovery score (0-1e18)
    function computeRecoveryScore(
        ICairnTypes.FailureClass failureClass,
        uint256 budgetRemaining,
        uint256 deadlineRemaining
    ) external view returns (uint256 score);

    /// @notice Get the recovery weight for a failure class
    /// @param failureClass The failure classification
    /// @return weight Class weight (0-1e18 scale)
    function getClassWeight(ICairnTypes.FailureClass failureClass) external view returns (uint256 weight);

    /// @notice Get the recovery threshold
    /// @return threshold Score threshold for automatic recovery (0.3e18 default)
    function recoveryThreshold() external view returns (uint256 threshold);
}
