// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {ICairnTypes} from "./ICairnTypes.sol";

/// @title IArbiterRegistry - Decentralized dispute resolution
/// @notice Manages arbiter registration, rulings, and appeals
/// @dev Based on PRD-05
///
/// Economics (PRD-05 Section 3.4):
///   - Arbiter fee: 3% of dispute escrow
///   - Min stake: 15% of max ruleable dispute
///
/// Slashing (PRD-05 Section 3.5):
///   - Ruling overturned → 50% stake slashed
///
/// Dispute Lifecycle (PRD-05 Section 3.2):
///   DISPUTED → (7 days) → Arbiter rules OR Timeout
///   After ruling → (48h appeal window) → RESOLVED
interface IArbiterRegistry {
    // ═══════════════════════════════════════════════════════════════
    // STRUCTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Arbiter registration data
    struct Arbiter {
        bool registered;
        uint256 stake;
        bytes32[] expertiseDomains;
        uint256 rulingCount;
        uint256 overturnedCount;
        uint256 earnings;
        uint256 lastActive;
    }

    /// @notice Stored ruling data
    struct StoredRuling {
        address arbiter;
        ICairnTypes.RulingOutcome outcome;
        uint256 agentShare;
        bytes32 rationaleCID;
        uint256 timestamp;
        bool appealed;
        bool overturned;
    }

    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    event ArbiterRegistered(address indexed arbiter, bytes32[] domains, uint256 stake);
    event ArbiterDeregistered(address indexed arbiter, uint256 stakeReturned);
    event StakeAdded(address indexed arbiter, uint256 amount, uint256 newTotal);
    event DisputeRuled(
        bytes32 indexed taskId,
        address indexed arbiter,
        ICairnTypes.RulingOutcome outcome,
        uint256 agentShare,
        uint256 arbiterFee
    );
    event RulingAppealed(bytes32 indexed taskId, address indexed appellant);
    event RulingOverturned(
        bytes32 indexed taskId,
        address indexed originalArbiter,
        uint256 slashAmount,
        ICairnTypes.RulingOutcome newOutcome
    );

    // ═══════════════════════════════════════════════════════════════
    // ERRORS
    // ═══════════════════════════════════════════════════════════════

    error AlreadyRegistered();
    error NotRegistered();
    error InsufficientStake(uint256 required, uint256 provided);
    error NotEligibleForDispute();
    error DisputeNotFound();
    error AlreadyRuled();
    error NotCairnCore();
    error NotGovernance();
    error AppealWindowExpired();
    error AppealWindowActive();
    error ConflictOfInterest();
    error HighOverturnRate();
    error ZeroAddress();

    // ═══════════════════════════════════════════════════════════════
    // REGISTRATION
    // ═══════════════════════════════════════════════════════════════

    /// @notice Register as an arbiter
    /// @dev Requires stake >= minArbiterStake
    /// @param domains Expertise domains this arbiter can rule on
    function registerArbiter(bytes32[] calldata domains) external payable;

    /// @notice Add additional stake
    function addStake() external payable;

    /// @notice Withdraw stake (after cooldown, no active disputes)
    /// @param amount Amount to withdraw
    function withdrawStake(uint256 amount) external;

    /// @notice Deregister as arbiter
    function deregisterArbiter() external;

    // ═══════════════════════════════════════════════════════════════
    // RULING (First eligible arbiter wins)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Submit a ruling for a disputed task
    /// @dev First-come-first-served among eligible arbiters
    /// @param taskId The disputed task
    /// @param ruling The ruling decision
    function rule(bytes32 taskId, ICairnTypes.Ruling calldata ruling) external;

    /// @notice Execute a ruling (called by CairnCore)
    /// @dev Validates arbiter eligibility and applies ruling
    /// @param taskId The task ID
    /// @param ruling The ruling to apply
    /// @param arbiter The arbiter submitting the ruling
    /// @param escrowAmount Task escrow for fee calculation
    /// @param primaryAgent Primary agent address (conflict check)
    /// @param fallbackAgent Fallback agent address (conflict check)
    /// @param taskType Task type for domain matching
    function executeRuling(
        bytes32 taskId,
        ICairnTypes.Ruling calldata ruling,
        address arbiter,
        uint256 escrowAmount,
        address primaryAgent,
        address fallbackAgent,
        bytes32 taskType
    ) external returns (uint256 arbiterFee);

    // ═══════════════════════════════════════════════════════════════
    // APPEALS (Governance only)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Overturn a ruling (governance only)
    /// @dev Slashes original arbiter 50% stake
    /// @param taskId The task with ruling to overturn
    /// @param newRuling The corrected ruling
    function overturnRuling(bytes32 taskId, ICairnTypes.Ruling calldata newRuling) external;

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Get arbiter info
    function getArbiter(address arbiter) external view returns (Arbiter memory);

    /// @notice Get stored ruling for a task
    function getRuling(bytes32 taskId) external view returns (StoredRuling memory);

    /// @notice Check if arbiter is eligible for a dispute
    function isEligible(
        address arbiter,
        uint256 escrowAmount,
        address primaryAgent,
        address fallbackAgent,
        bytes32 taskType
    ) external view returns (bool);

    /// @notice Get minimum arbiter stake
    function minArbiterStake() external view returns (uint256);

    /// @notice Get arbiter fee percentage (basis points)
    function arbiterFeeBps() external view returns (uint256);

    /// @notice Get appeal window duration
    function appealWindow() external view returns (uint256);

    /// @notice Get max allowed overturn rate (percentage)
    function maxOverturnRate() external view returns (uint256);
}
