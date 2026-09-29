// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {IRecoveryRouter} from "./interfaces/IRecoveryRouter.sol";
import {ICairnTypes} from "./interfaces/ICairnTypes.sol";
import {FailureTaxonomy} from "./libraries/FailureTaxonomy.sol";
import {MultiplicativeRecoveryScore as Score} from "./libraries/MultiplicativeRecoveryScore.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title RecoveryRouterV2 - Multiplicative recovery scoring (CAIRN v2)
/// @author CAIRN Protocol
/// @notice Implements the simulation-validated multiplicative recovery formula
///         from WHITEPAPER_V2 Section 6.4 and PRD-04.
///
/// Recovery Score Formula (v2):
///     r = F^0.80 × B^0.35 × D^0.15
///
/// Where:
///     F = failure_class_weight ∈ {0.70 (LIVENESS), 0.30 (RESOURCE), 0.00 (LOGIC)}
///     B = (escrow − costAccrued) / escrow ∈ [0, 1]   (costAccrued is agent-reported)
///     D = (deadline − now) / (deadline − createdAt) ∈ [0, 1]
///
/// The failure class is derived from the recorded failure evidence (FailureTaxonomy).
///
/// Three-tier routing (v2 thresholds):
///     r ≥ 0.40                  → RECOVERING (full scope)
///     0.35 ≤ r < 0.40           → RECOVERING (reduced scope)
///     r < 0.35                  → DISPUTED
///
/// The IRecoveryRouter interface is preserved so this contract is
/// drop-in for governance migration via setRecoveryRouter() in CairnCore.
/// The legacy recoveryThreshold() returns the lower (0.35) threshold so
/// v1 callers that only check a single threshold continue to behave
/// correctly (they skip the FULL/REDUCED distinction but make the same
/// recover/dispute decision the lower threshold would yield).
contract RecoveryRouterV2 is IRecoveryRouter, Ownable {
    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS — fixed-point exponents and lookup values (v2)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Precision scale (1e18 = 100% in UD60x18)
    uint256 public constant PRECISION = Score.PRECISION;

    /// @notice Budget exponent b = 0.35 in UD60x18
    uint256 public constant B_EXPONENT = Score.B_EXPONENT;

    /// @notice Deadline exponent c = 0.15 in UD60x18
    uint256 public constant D_EXPONENT = Score.D_EXPONENT;

    /// @notice Pre-computed F^0.80 lookup for LIVENESS class weight 0.70
    /// @dev 0.70^0.80 = 0.751758646650045568 (verified to 18 decimals)
    uint256 public constant F_POW_LIVENESS = Score.F_POW_LIVENESS;

    /// @notice Pre-computed F^0.80 lookup for RESOURCE class weight 0.30
    /// @dev 0.30^0.80 = 0.381677890961817600 (verified to 18 decimals)
    uint256 public constant F_POW_RESOURCE = Score.F_POW_RESOURCE;

    /// @notice Pre-computed F^0.80 lookup for LOGIC class weight 0.00
    /// @dev 0.00^0.80 = 0; LOGIC always routes to DISPUTED (r = 0)
    uint256 public constant F_POW_LOGIC = Score.F_POW_LOGIC;

    /// @notice Upper threshold — score ≥ this routes to RECOVERING (full)
    uint256 public constant DEFAULT_UPPER_THRESHOLD = 0.40e18;

    /// @notice Lower threshold — score ≥ this and < upper routes to REDUCED
    uint256 public constant DEFAULT_LOWER_THRESHOLD = 0.35e18;

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Address authorized to call classifyAndScore (CairnCore)
    address public cairnCore;

    /// @notice Upper routing threshold (governance-adjustable)
    uint256 public upperThreshold;

    /// @notice Lower routing threshold (governance-adjustable)
    uint256 public lowerThreshold;

    /// @notice Counter for failure records (used in CID generation)
    uint256 private _failureRecordNonce;

    // ═══════════════════════════════════════════════════════════════
    // CUSTOM ERRORS (in addition to those in IRecoveryRouter)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Thresholds violate ordering invariant (lower must be ≤ upper)
    error InvalidThresholdOrder();

    /// @notice Threshold value is outside the [0.1, 0.9] permitted range
    error InvalidThresholdRange();

    /// @notice Input scaled fixed-point value exceeds 1e18 (raised by the score library;
    ///         declared here so the selector is part of this contract's ABI)
    error InputOutOfRange();

    /// @notice Zero address supplied where a contract address is required
    error ZeroAddress();

    event CairnCoreUpdated(address indexed cairnCore);
    event ThresholdsUpdated(uint256 upper, uint256 lower);

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════

    constructor(address _cairnCore) Ownable(msg.sender) {
        cairnCore = _cairnCore;
        upperThreshold = DEFAULT_UPPER_THRESHOLD;
        lowerThreshold = DEFAULT_LOWER_THRESHOLD;
    }

    // ═══════════════════════════════════════════════════════════════
    // MODIFIERS
    // ═══════════════════════════════════════════════════════════════

    modifier onlyCairnCore() {
        if (msg.sender != cairnCore) revert NotAuthorized();
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // CORE FUNCTIONS — IRecoveryRouter
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IRecoveryRouter
    function classifyAndScore(
        bytes32 taskId,
        ICairnTypes.FailureEvidence calldata evidence
    )
        external
        override
        onlyCairnCore
        returns (
            ICairnTypes.FailureClass failureClass,
            ICairnTypes.FailureType failureType,
            uint256 recoveryScore,
            bytes32 failureRecordCID
        )
    {
        (failureClass, failureType) = FailureTaxonomy.classify(evidence);

        uint256 budgetRemaining =
            FailureTaxonomy.budgetRemaining(evidence.escrowAmount, evidence.costAccrued);
        uint256 deadlineRemaining =
            FailureTaxonomy.deadlineRemaining(evidence.createdAt, evidence.deadline);

        recoveryScore = _computeScore(failureClass, budgetRemaining, deadlineRemaining);

        failureRecordCID = _createFailureRecord(taskId, failureClass, failureType, recoveryScore);

        emit FailureClassified(
            taskId, failureClass, failureType, recoveryScore, failureRecordCID
        );

        return (failureClass, failureType, recoveryScore, failureRecordCID);
    }

    /// @inheritdoc IRecoveryRouter
    function computeRecoveryScore(
        ICairnTypes.FailureClass failureClass,
        uint256 budgetRemaining,
        uint256 deadlineRemaining
    )
        external
        view
        override
        returns (uint256 score)
    {
        return _computeScore(failureClass, budgetRemaining, deadlineRemaining);
    }

    /// @inheritdoc IRecoveryRouter
    /// @dev v2 returns the *raw* class weight F (0.70/0.30/0.00) rather than
    ///      its 0.80-power, to match the semantic the interface promised in v1.
    function getClassWeight(ICairnTypes.FailureClass failureClass)
        external
        pure
        override
        returns (uint256)
    {
        return Score.classWeight(failureClass);
    }

    /// @inheritdoc IRecoveryRouter
    /// @dev Returns the lower threshold so binary-routing v1 callers fall back
    ///      to the recover/dispute boundary. Three-tier-aware callers should
    ///      use upperThreshold() and lowerThreshold() directly.
    function recoveryThreshold() external view override returns (uint256) {
        return lowerThreshold;
    }

    // ═══════════════════════════════════════════════════════════════
    // V2-ONLY VIEW FUNCTIONS (three-tier routing support)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Classify a score into a routing tier
    /// @return tier 2 = FULL (r ≥ upper), 1 = REDUCED (lower ≤ r < upper), 0 = DISPUTED
    function routingTier(uint256 score) external view returns (uint8 tier) {
        if (score >= upperThreshold) return 2;
        if (score >= lowerThreshold) return 1;
        return 0;
    }

    // ═══════════════════════════════════════════════════════════════
    // INTERNAL — formula
    // ═══════════════════════════════════════════════════════════════

    function _computeScore(
        ICairnTypes.FailureClass failureClass,
        uint256 budgetRemaining,
        uint256 deadlineRemaining
    )
        internal
        pure
        returns (uint256)
    {
        return Score.score(failureClass, budgetRemaining, deadlineRemaining);
    }

    // ═══════════════════════════════════════════════════════════════
    // INTERNAL — helpers
    // ═══════════════════════════════════════════════════════════════

    function _createFailureRecord(
        bytes32 taskId,
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 recoveryScore
    )
        internal
        returns (bytes32)
    {
        _failureRecordNonce++;
        bytes32 recordHash = keccak256(
            abi.encodePacked(
                taskId,
                failureClass,
                failureType,
                recoveryScore,
                block.timestamp,
                _failureRecordNonce
            )
        );
        emit FailureRecordCreated(
            taskId, recordHash, failureClass, failureType, block.timestamp
        );
        return recordHash;
    }

    // ═══════════════════════════════════════════════════════════════
    // GOVERNANCE
    // ═══════════════════════════════════════════════════════════════

    /// @dev Gated by owner (transfer to governance/multisig post-deploy).
    function setCairnCore(address _cairnCore) external onlyOwner {
        if (_cairnCore == address(0)) revert ZeroAddress();
        cairnCore = _cairnCore;
        emit CairnCoreUpdated(_cairnCore);
    }

    /// @notice Update both thresholds atomically (must respect ordering)
    /// @dev Gated by owner (transfer to governance/multisig post-deploy).
    function setThresholds(uint256 _upper, uint256 _lower) external onlyOwner {
        if (_upper < _lower) revert InvalidThresholdOrder();
        if (_upper < 0.1e18 || _upper > 0.9e18) revert InvalidThresholdRange();
        if (_lower < 0.1e18 || _lower > 0.9e18) revert InvalidThresholdRange();
        upperThreshold = _upper;
        lowerThreshold = _lower;
        emit ThresholdsUpdated(_upper, _lower);
    }
}
