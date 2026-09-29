// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {ICairnTypes} from "../interfaces/ICairnTypes.sol";

/// @title FailureTaxonomy - Evidence-based failure classification and score inputs
/// @author CAIRN Protocol
/// @notice Shared by every recovery router so classification and the budget/deadline
///         inputs are computed identically regardless of the scoring formula.
/// @dev Classification uses only the recorded failure evidence. Checkpoint progress does
///      not influence the failure class.
library FailureTaxonomy {
    /// @notice Precision scale (1e18 = 100%)
    uint256 internal constant PRECISION = 1e18;

    /// @notice Map a failure type to its failure class
    function classOf(ICairnTypes.FailureType t) internal pure returns (ICairnTypes.FailureClass) {
        if (
            t == ICairnTypes.FailureType.HEARTBEAT_MISS ||
            t == ICairnTypes.FailureType.NETWORK_PARTITION ||
            t == ICairnTypes.FailureType.NODE_CRASH
        ) {
            return ICairnTypes.FailureClass.LIVENESS;
        }
        if (
            t == ICairnTypes.FailureType.VALIDATION_FAILED ||
            t == ICairnTypes.FailureType.SCHEMA_MISMATCH ||
            t == ICairnTypes.FailureType.INVARIANT_VIOLATION
        ) {
            return ICairnTypes.FailureClass.LOGIC;
        }
        // RATE_LIMIT, GAS_EXHAUSTED, UPSTREAM_TIMEOUT, BUDGET_EXHAUSTED, DEADLINE_EXCEEDED
        return ICairnTypes.FailureClass.RESOURCE;
    }

    /// @notice Whether a failure type can only be established mechanically on-chain
    /// @dev These types cannot be self-reported: a report would assert mechanical evidence
    ///      that the contract checks itself.
    function isMechanicalOnly(ICairnTypes.FailureType t) internal pure returns (bool) {
        return t == ICairnTypes.FailureType.HEARTBEAT_MISS ||
            t == ICairnTypes.FailureType.DEADLINE_EXCEEDED;
    }

    /// @notice Derive the failure class and type from the recorded evidence
    /// @dev DEADLINE_EXPIRED → RESOURCE/DEADLINE_EXCEEDED.
    ///      AGENT_REPORT → the reported type and its class.
    ///      HEARTBEAT_TIMEOUT → RESOURCE/BUDGET_EXHAUSTED if reported cost reached the escrow,
    ///      otherwise LIVENESS/HEARTBEAT_MISS.
    function classify(ICairnTypes.FailureEvidence calldata ev)
        internal
        pure
        returns (ICairnTypes.FailureClass, ICairnTypes.FailureType)
    {
        if (ev.source == ICairnTypes.FailureEvidenceSource.DEADLINE_EXPIRED) {
            return (ICairnTypes.FailureClass.RESOURCE, ICairnTypes.FailureType.DEADLINE_EXCEEDED);
        }
        if (ev.source == ICairnTypes.FailureEvidenceSource.AGENT_REPORT) {
            return (classOf(ev.reportedType), ev.reportedType);
        }
        if (ev.escrowAmount > 0 && ev.costAccrued >= ev.escrowAmount) {
            return (ICairnTypes.FailureClass.RESOURCE, ICairnTypes.FailureType.BUDGET_EXHAUSTED);
        }
        return (ICairnTypes.FailureClass.LIVENESS, ICairnTypes.FailureType.HEARTBEAT_MISS);
    }

    /// @notice Fraction of the task budget (its escrow) not yet consumed by reported cost
    /// @return B on the 0-1e18 scale; 0 if there is no escrow
    function budgetRemaining(uint256 escrowAmount, uint256 costAccrued)
        internal
        pure
        returns (uint256)
    {
        if (escrowAmount == 0 || costAccrued >= escrowAmount) return 0;
        return ((escrowAmount - costAccrued) * PRECISION) / escrowAmount;
    }

    /// @notice Fraction of the task's lifetime remaining before its deadline
    /// @return D on the 0-1e18 scale; 0 at or after the deadline
    function deadlineRemaining(uint256 createdAt, uint256 deadline)
        internal
        view
        returns (uint256)
    {
        if (block.timestamp >= deadline) return 0;
        uint256 totalDuration = deadline - createdAt;
        if (totalDuration == 0) return 0;
        uint256 timeRemaining = deadline - block.timestamp;
        return (timeRemaining * PRECISION) / totalDuration;
    }
}
