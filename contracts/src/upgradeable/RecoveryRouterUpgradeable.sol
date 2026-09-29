// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {IRecoveryRouter} from "../interfaces/IRecoveryRouter.sol";
import {ICairnTypes} from "../interfaces/ICairnTypes.sol";
import {FailureTaxonomy} from "../libraries/FailureTaxonomy.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/// @title RecoveryRouterUpgradeable - UUPS Upgradeable failure classification
/// @author CAIRN Protocol
/// @notice Classifies agent failures and computes recovery likelihood (Upgradeable)
/// @dev Based on PRD-02 Sections 2.1-2.2, implements UUPS proxy pattern from PRD-06
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
contract RecoveryRouterUpgradeable is
    IRecoveryRouter,
    Initializable,
    UUPSUpgradeable,
    OwnableUpgradeable
{
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

    /// @dev Storage gap to allow for future variable additions
    uint256[50] private __gap;

    // ═══════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /// @notice Initialize the contract
    /// @param _cairnCore CairnCore contract address
    /// @param _owner Initial owner address
    function initialize(address _cairnCore, address _owner) external initializer {
        __Ownable_init(_owner);

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
    // UPGRADE AUTHORIZATION
    // ═══════════════════════════════════════════════════════════════

    /// @notice Authorize upgrade (only owner can upgrade)
    /// @dev Required by UUPS pattern
    /// @param newImplementation Address of the new implementation
    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}

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
        ICairnTypes.FailureEvidence calldata evidence
    ) external override onlyCairnCore returns (
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 recoveryScore,
        bytes32 failureRecordCID
    ) {
        // Classify from the recorded evidence (FailureTaxonomy); progress does not affect class
        (failureClass, failureType) = FailureTaxonomy.classify(evidence);

        // B = fraction of escrow not yet consumed by reported cost; D = time remaining
        uint256 budgetRemaining =
            FailureTaxonomy.budgetRemaining(evidence.escrowAmount, evidence.costAccrued);
        uint256 deadlineRemaining =
            FailureTaxonomy.deadlineRemaining(evidence.createdAt, evidence.deadline);

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
    // ADMIN (for upgrades)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Update CairnCore address (for upgrades)
    function setCairnCore(address _cairnCore) external onlyOwner {
        cairnCore = _cairnCore;
    }

    /// @notice Update recovery threshold
    function setRecoveryThreshold(uint256 _threshold) external onlyOwner {
        require(_threshold >= 0.1e18 && _threshold <= 0.9e18, "Invalid threshold");
        recoveryThreshold = _threshold;
    }

    /// @notice Update class recovery potential
    function setClassRecoveryPotential(ICairnTypes.FailureClass failureClass, uint256 potential) external onlyOwner {
        require(potential <= PRECISION, "Invalid potential");
        classRecoveryPotential[failureClass] = potential;
    }
}
