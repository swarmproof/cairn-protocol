// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {IRecoveryRouter} from "./interfaces/IRecoveryRouter.sol";
import {ICairnTypes} from "./interfaces/ICairnTypes.sol";

/// @title RecoveryRouter - Failure classification and recovery scoring
/// @author CAIRN Protocol
/// @notice Classifies agent failures and computes recovery likelihood
/// @dev Based on PRD-02 Sections 2.1-2.2
///
/// Recovery Score Formula:
///   score = (failure_class_weight × 0.5) + (budget_remaining × 0.3) + (deadline_remaining × 0.2)
///
/// Class Weights (recovery potential):
///   - LIVENESS: 0.9 (just restart - high recovery)
///   - RESOURCE: 0.5 (may need different approach - medium)
///   - LOGIC: 0.1 (likely to repeat - low recovery)
///
/// Routing Decision:
///   - score >= 0.3 → RECOVERING (fallback assigned)
///   - score < 0.3 → DISPUTED (arbiter needed)
contract RecoveryRouter is IRecoveryRouter {
    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS (PRD-02 Section 2.2)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Weight multiplier for failure class component
    uint256 public constant FAILURE_CLASS_WEIGHT = 0.5e18;

    /// @notice Weight multiplier for budget remaining component
    uint256 public constant BUDGET_WEIGHT = 0.3e18;

    /// @notice Weight multiplier for deadline remaining component
    uint256 public constant DEADLINE_WEIGHT = 0.2e18;

    /// @notice Precision scale (1e18 = 100%)
    uint256 public constant PRECISION = 1e18;

    /// @notice Default recovery threshold (30%)
    uint256 public constant DEFAULT_THRESHOLD = 0.3e18;

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Recovery potential by failure class (PRD-02 Section 2.1)
    mapping(ICairnTypes.FailureClass => uint256) public classRecoveryPotential;

    /// @notice Address authorized to call classifyAndScore (CairnCore)
    address public cairnCore;

    /// @notice Recovery threshold (configurable via governance)
    uint256 public override recoveryThreshold;

    /// @notice Counter for failure records (used in CID generation)
    uint256 private _failureRecordNonce;

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════

    constructor(address _cairnCore) {
        cairnCore = _cairnCore;
        recoveryThreshold = DEFAULT_THRESHOLD;

        // Initialize class weights (PRD-02 Section 2.1)
        // LIVENESS: High recovery - just restart
        classRecoveryPotential[ICairnTypes.FailureClass.LIVENESS] = 0.9e18;
        // RESOURCE: Medium recovery - may need different approach
        classRecoveryPotential[ICairnTypes.FailureClass.RESOURCE] = 0.5e18;
        // LOGIC: Low recovery - likely to repeat
        classRecoveryPotential[ICairnTypes.FailureClass.LOGIC] = 0.1e18;
    }

    // ═══════════════════════════════════════════════════════════════
    // MODIFIERS
    // ═══════════════════════════════════════════════════════════════

    modifier onlyCairnCore() {
        if (msg.sender != cairnCore) revert NotAuthorized();
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // CORE FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IRecoveryRouter
    function classifyAndScore(
        bytes32 taskId,
        uint256 escrowAmount,
        uint256 createdAt,
        uint256 deadline,
        uint256 checkpointCount
    ) external override onlyCairnCore returns (
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 recoveryScore,
        bytes32 failureRecordCID
    ) {
        // Classify the failure (default: heartbeat miss = LIVENESS)
        // More sophisticated classification would analyze checkpoint content
        (failureClass, failureType) = _classifyFailure(checkpointCount);

        // Compute budget remaining (full budget if no settlement yet)
        uint256 budgetRemaining = escrowAmount > 0 ? PRECISION : 0;

        // Compute deadline remaining
        uint256 deadlineRemaining = _computeDeadlineRemaining(createdAt, deadline);

        // Compute recovery score
        recoveryScore = _computeScore(failureClass, budgetRemaining, deadlineRemaining);

        // Create failure record (hash as CID placeholder)
        failureRecordCID = _createFailureRecord(
            taskId,
            failureClass,
            failureType,
            recoveryScore
        );

        emit FailureClassified(
            taskId,
            failureClass,
            failureType,
            recoveryScore,
            failureRecordCID
        );

        return (failureClass, failureType, recoveryScore, failureRecordCID);
    }

    /// @inheritdoc IRecoveryRouter
    function computeRecoveryScore(
        ICairnTypes.FailureClass failureClass,
        uint256 budgetRemaining,
        uint256 deadlineRemaining
    ) external view override returns (uint256 score) {
        return _computeScore(failureClass, budgetRemaining, deadlineRemaining);
    }

    /// @inheritdoc IRecoveryRouter
    function getClassWeight(ICairnTypes.FailureClass failureClass) external view override returns (uint256) {
        return classRecoveryPotential[failureClass];
    }

    // ═══════════════════════════════════════════════════════════════
    // INTERNAL FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Classify failure based on available data
    /// @dev Default: heartbeat miss = LIVENESS (most common case)
    /// @param checkpointCount Number of checkpoints completed
    function _classifyFailure(uint256 checkpointCount)
        internal
        pure
        returns (ICairnTypes.FailureClass, ICairnTypes.FailureType)
    {
        // Simple heuristic (PRD-02 Section 2.1):
        // - 0 checkpoints: likely LIVENESS (agent never responded)
        // - Some checkpoints: could be RESOURCE or LOGIC
        //
        // More sophisticated classification would analyze:
        // - Checkpoint content for schema mismatches (LOGIC)
        // - Error messages for rate limits (RESOURCE)
        // - Time between checkpoints for patterns

        if (checkpointCount == 0) {
            // Agent never started or crashed immediately
            return (ICairnTypes.FailureClass.LIVENESS, ICairnTypes.FailureType.HEARTBEAT_MISS);
        } else if (checkpointCount < 3) {
            // Early failure, possibly resource issue
            return (ICairnTypes.FailureClass.RESOURCE, ICairnTypes.FailureType.UPSTREAM_TIMEOUT);
        } else {
            // Made progress then failed, could be logic error
            // But default to LIVENESS (heartbeat miss) for conservative scoring
            return (ICairnTypes.FailureClass.LIVENESS, ICairnTypes.FailureType.HEARTBEAT_MISS);
        }
    }

    /// @notice Compute deadline remaining percentage
    /// @param createdAt Task creation timestamp
    /// @param deadline Task deadline timestamp
    /// @return remaining Percentage remaining (0-1e18)
    function _computeDeadlineRemaining(uint256 createdAt, uint256 deadline)
        internal
        view
        returns (uint256 remaining)
    {
        if (block.timestamp >= deadline) {
            return 0;
        }

        uint256 totalDuration = deadline - createdAt;
        if (totalDuration == 0) {
            return 0;
        }

        uint256 elapsed = block.timestamp - createdAt;
        uint256 timeRemaining = totalDuration - elapsed;

        return (timeRemaining * PRECISION) / totalDuration;
    }

    /// @notice Compute recovery score using PRD-02 formula
    /// @dev score = (class_weight × 0.5) + (budget × 0.3) + (deadline × 0.2)
    function _computeScore(
        ICairnTypes.FailureClass failureClass,
        uint256 budgetRemaining,
        uint256 deadlineRemaining
    ) internal view returns (uint256) {
        // Get class recovery potential
        uint256 classPotential = classRecoveryPotential[failureClass];

        // Calculate each component
        // failure_class_weight × 0.5
        uint256 classScore = (classPotential * FAILURE_CLASS_WEIGHT) / PRECISION;

        // budget_remaining × 0.3
        uint256 budgetScore = (budgetRemaining * BUDGET_WEIGHT) / PRECISION;

        // deadline_remaining × 0.2
        uint256 deadlineScore = (deadlineRemaining * DEADLINE_WEIGHT) / PRECISION;

        return classScore + budgetScore + deadlineScore;
    }

    /// @notice Create a failure record hash (placeholder for IPFS CID)
    /// @dev In production, this would write to IPFS and return the actual CID
    function _createFailureRecord(
        bytes32 taskId,
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 recoveryScore
    ) internal returns (bytes32) {
        _failureRecordNonce++;

        bytes32 recordHash = keccak256(abi.encodePacked(
            taskId,
            failureClass,
            failureType,
            recoveryScore,
            block.timestamp,
            _failureRecordNonce
        ));

        emit FailureRecordCreated(
            taskId,
            recordHash,
            failureClass,
            failureType,
            block.timestamp
        );

        return recordHash;
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN (for testing/upgrades)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Update CairnCore address (for upgrades)
    /// @dev Should be called via governance in production
    function setCairnCore(address _cairnCore) external {
        // In production, add onlyGovernance modifier
        cairnCore = _cairnCore;
    }

    /// @notice Update recovery threshold
    /// @dev Should be called via governance in production
    function setRecoveryThreshold(uint256 _threshold) external {
        // In production, add onlyGovernance modifier
        require(_threshold >= 0.1e18 && _threshold <= 0.9e18, "Invalid threshold");
        recoveryThreshold = _threshold;
    }
}
