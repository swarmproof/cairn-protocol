// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {IRecoveryRouter} from "../interfaces/IRecoveryRouter.sol";
import {IRecoveryRouterV2} from "../interfaces/IRecoveryRouterV2.sol";
import {ICairnTypes} from "../interfaces/ICairnTypes.sol";
import {FailureTaxonomy} from "../libraries/FailureTaxonomy.sol";
import {MultiplicativeRecoveryScore as Score} from "../libraries/MultiplicativeRecoveryScore.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/// @title RecoveryRouterV2Upgradeable - UUPS variant of RecoveryRouterV2
/// @author CAIRN Protocol
/// @notice Same behaviour as RecoveryRouterV2 (multiplicative score r = F^0.80 × B^0.35 × D^0.15,
///         evidence-based classification, three-tier routing), deployable behind an ERC-1967
///         proxy. Scoring and classification come from the same libraries as RecoveryRouterV2.
/// @dev Owner-authorized upgrades. Append new state before __gap and shrink the gap.
contract RecoveryRouterV2Upgradeable is
    IRecoveryRouter,
    IRecoveryRouterV2,
    Initializable,
    UUPSUpgradeable,
    OwnableUpgradeable
{
    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS
    // ═══════════════════════════════════════════════════════════════

    uint256 public constant PRECISION = Score.PRECISION;
    uint256 public constant B_EXPONENT = Score.B_EXPONENT;
    uint256 public constant D_EXPONENT = Score.D_EXPONENT;
    uint256 public constant F_POW_LIVENESS = Score.F_POW_LIVENESS;
    uint256 public constant F_POW_RESOURCE = Score.F_POW_RESOURCE;
    uint256 public constant F_POW_LOGIC = Score.F_POW_LOGIC;

    /// @notice Default upper threshold — score ≥ this routes to RECOVERING (full)
    uint256 public constant DEFAULT_UPPER_THRESHOLD = 0.40e18;

    /// @notice Default lower threshold — score ≥ this and < upper routes to REDUCED
    uint256 public constant DEFAULT_LOWER_THRESHOLD = 0.35e18;

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Address authorized to call classifyAndScore (CairnCore)
    address public cairnCore;

    /// @inheritdoc IRecoveryRouterV2
    uint256 public override upperThreshold;

    /// @inheritdoc IRecoveryRouterV2
    uint256 public override lowerThreshold;

    /// @notice Counter for failure records (used in record identifiers)
    uint256 private _failureRecordNonce;

    /// @dev Storage gap for future state (4 slots used above)
    uint256[46] private __gap;

    // ═══════════════════════════════════════════════════════════════
    // ERRORS / EVENTS (parity with RecoveryRouterV2)
    // ═══════════════════════════════════════════════════════════════

    error InvalidThresholdOrder();
    error InvalidThresholdRange();
    error InputOutOfRange();
    error ZeroAddress();

    event CairnCoreUpdated(address indexed cairnCore);
    event ThresholdsUpdated(uint256 upper, uint256 lower);

    // ═══════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /// @notice Initialize the proxy
    /// @param _cairnCore CairnCore address (may be zero and set later via setCairnCore)
    /// @param _owner Initial owner (upgrade + parameter authority)
    function initialize(address _cairnCore, address _owner) external initializer {
        __Ownable_init(_owner);
        cairnCore = _cairnCore;
        upperThreshold = DEFAULT_UPPER_THRESHOLD;
        lowerThreshold = DEFAULT_LOWER_THRESHOLD;
    }

    /// @dev Only the owner may upgrade the implementation
    function _authorizeUpgrade(address) internal override onlyOwner {}

    modifier onlyCairnCore() {
        if (msg.sender != cairnCore) revert NotAuthorized();
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // IRecoveryRouter
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IRecoveryRouter
    function classifyAndScore(bytes32 taskId, ICairnTypes.FailureEvidence calldata evidence)
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

        recoveryScore = Score.score(
            failureClass,
            FailureTaxonomy.budgetRemaining(evidence.escrowAmount, evidence.costAccrued),
            FailureTaxonomy.deadlineRemaining(evidence.createdAt, evidence.deadline)
        );

        _failureRecordNonce++;
        failureRecordCID = keccak256(
            abi.encodePacked(
                taskId, failureClass, failureType, recoveryScore, block.timestamp, _failureRecordNonce
            )
        );
        emit FailureRecordCreated(taskId, failureRecordCID, failureClass, failureType, block.timestamp);
        emit FailureClassified(taskId, failureClass, failureType, recoveryScore, failureRecordCID);
    }

    /// @inheritdoc IRecoveryRouter
    function computeRecoveryScore(
        ICairnTypes.FailureClass failureClass,
        uint256 budgetRemaining,
        uint256 deadlineRemaining
    ) external pure override returns (uint256) {
        return Score.score(failureClass, budgetRemaining, deadlineRemaining);
    }

    /// @inheritdoc IRecoveryRouter
    function getClassWeight(ICairnTypes.FailureClass failureClass)
        external
        pure
        override
        returns (uint256)
    {
        return Score.classWeight(failureClass);
    }

    /// @inheritdoc IRecoveryRouter
    /// @dev Returns the lower threshold for binary-routing callers.
    function recoveryThreshold() external view override returns (uint256) {
        return lowerThreshold;
    }

    // ═══════════════════════════════════════════════════════════════
    // IRecoveryRouterV2
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IRecoveryRouterV2
    function routingTier(uint256 score) external view override returns (uint8 tier) {
        if (score >= upperThreshold) return 2;
        if (score >= lowerThreshold) return 1;
        return 0;
    }

    // ═══════════════════════════════════════════════════════════════
    // GOVERNANCE
    // ═══════════════════════════════════════════════════════════════

    function setCairnCore(address _cairnCore) external onlyOwner {
        if (_cairnCore == address(0)) revert ZeroAddress();
        cairnCore = _cairnCore;
        emit CairnCoreUpdated(_cairnCore);
    }

    /// @notice Update both thresholds atomically (lower ≤ upper, both in [0.1, 0.9])
    function setThresholds(uint256 _upper, uint256 _lower) external onlyOwner {
        if (_upper < _lower) revert InvalidThresholdOrder();
        if (_upper < 0.1e18 || _upper > 0.9e18) revert InvalidThresholdRange();
        if (_lower < 0.1e18 || _lower > 0.9e18) revert InvalidThresholdRange();
        upperThreshold = _upper;
        lowerThreshold = _lower;
        emit ThresholdsUpdated(_upper, _lower);
    }
}
