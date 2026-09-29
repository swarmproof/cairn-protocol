// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {ICairnTypes} from "./ICairnTypes.sol";

/// @title IRecoveryRouter - Failure classification and recovery scoring
/// @notice Classifies a failure from its recorded evidence and computes a recovery score
///         from the failure class F, remaining budget B, and remaining deadline D.
/// @dev The scoring formula and class weights are implementation-specific
///      (RecoveryRouter: linear; RecoveryRouterV2: multiplicative). Classification and the
///      B/D inputs are shared across implementations via FailureTaxonomy.
///      B = (escrow - costAccrued) / escrow, where costAccrued is agent-reported.
///      D = (deadline - now) / (deadline - createdAt).
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

    /// @notice Classify a failure from its evidence and compute the recovery score
    /// @dev Called by CairnCore on detectFailure (heartbeat timeout / deadline expiry) or
    ///      reportFailure (agent report).
    /// @param taskId The failing task's ID
    /// @param evidence The recorded failure evidence and score inputs
    /// @return failureClass The failure class derived from the evidence
    /// @return failureType Specific failure within the class
    /// @return recoveryScore Recovery score (0-1e18 scale)
    /// @return failureRecordCID Identifier of the failure record
    function classifyAndScore(
        bytes32 taskId,
        ICairnTypes.FailureEvidence calldata evidence
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
