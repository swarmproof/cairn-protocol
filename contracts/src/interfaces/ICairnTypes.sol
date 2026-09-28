// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

/// @title ICairnTypes - Shared types for CAIRN Protocol
/// @notice Defines enums and structs used across all CAIRN contracts
/// @dev Based on PRD-02 (failure taxonomy), PRD-06 (6-state machine)
interface ICairnTypes {
    // ═══════════════════════════════════════════════════════════════
    // ENUMS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Task lifecycle states (PRD-06: 6-state machine)
    /// @dev IDLE → RUNNING → FAILED/COMPLETED → RECOVERING/DISPUTED → RESOLVED
    enum TaskState {
        IDLE,       // Task created but not started
        RUNNING,    // Agent executing, heartbeats active
        FAILED,     // Failure detected, awaiting classification
        RECOVERING, // Recovery score >= threshold, fallback assigned
        DISPUTED,   // Recovery score < threshold, arbiter needed
        RESOLVED    // Terminal state: escrow settled
    }

    /// @notice Failure classification (PRD-02: 3-class taxonomy)
    /// @dev The class is derived from recorded failure evidence (see FailureTaxonomy);
    ///      class weights are defined by the wired recovery router.
    enum FailureClass {
        LIVENESS,   // Agent stopped responding (high recovery potential)
        RESOURCE,   // External resource limit hit (medium recovery)
        LOGIC       // Agent reasoning error (low recovery potential)
    }

    /// @notice Specific failure types within each class (PRD-02)
    enum FailureType {
        // LIVENESS failures (external, high recovery)
        HEARTBEAT_MISS,
        NETWORK_PARTITION,
        NODE_CRASH,
        // RESOURCE failures (external, medium recovery)
        RATE_LIMIT,
        GAS_EXHAUSTED,
        UPSTREAM_TIMEOUT,
        // LOGIC failures (internal, low recovery)
        VALIDATION_FAILED,
        SCHEMA_MISMATCH,
        INVARIANT_VIOLATION,
        // RESOURCE failures appended after the original set (ordinals above unchanged)
        BUDGET_EXHAUSTED,  // reported cost reached the task's escrow
        DEADLINE_EXCEEDED  // task deadline passed before completion (mechanical only)
    }

    /// @notice Where the evidence for a failure came from
    /// @dev HEARTBEAT_TIMEOUT and DEADLINE_EXPIRED are mechanically verifiable on-chain.
    ///      AGENT_REPORT is attested by the current agent and is not verified on-chain.
    enum FailureEvidenceSource {
        HEARTBEAT_TIMEOUT, // heartbeat missed by more than 2x the interval
        DEADLINE_EXPIRED,  // block.timestamp passed the task deadline
        AGENT_REPORT       // current agent declared a failure type with an evidence CID
    }

    /// @notice How a task was resolved (PRD-06)
    enum ResolutionType {
        SUCCESS,         // Task completed successfully
        RECOVERY,        // Fallback completed after primary failed
        ARBITER_RULING,  // Arbiter resolved dispute
        TIMEOUT_REFUND   // Dispute timed out, operator refunded
    }

    /// @notice Arbiter ruling outcomes (PRD-05)
    enum RulingOutcome {
        REFUND_OPERATOR, // Full refund to operator
        PAY_AGENT,       // Pay agent proportionally
        SPLIT            // Custom split between operator/agent
    }

    /// @notice Recovery scope tier for the RECOVERING state (PRD-04 three-tier routing)
    /// @dev FULL: recovery score >= upper threshold (fallback gets full checkpoint-proportional
    ///      share). REDUCED: lower <= score < upper — fallback attempts with a capped budget, so
    ///      its escrow share is capped and the remainder returns to the operator (WHITEPAPER_V2
    ///      Section 6.4). Default value (0) is FULL, so tasks routed under v1 binary routing are
    ///      unaffected.
    enum RecoveryScope {
        FULL,   // Full-scope recovery (default)
        REDUCED // Reduced-scope recovery: fallback payout capped
    }

    // ═══════════════════════════════════════════════════════════════
    // STRUCTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Arbiter ruling details (PRD-05)
    /// @param outcome The ruling decision
    /// @param agentShare For SPLIT outcome: percentage to agent (0-100)
    /// @param rationaleCID IPFS CID of detailed rationale
    struct Ruling {
        RulingOutcome outcome;
        uint256 agentShare;
        bytes32 rationaleCID;
    }

    /// @notice Inputs the recovery router classifies and scores a failure from
    /// @param source Where the failure evidence came from
    /// @param reportedType Failure type declared by the agent (AGENT_REPORT only)
    /// @param evidenceCID Content identifier of the agent's evidence (zero for mechanical sources)
    /// @param escrowAmount Task escrow; the budget against which cost is measured
    /// @param costAccrued Cumulative execution cost reported by the task's agents (wei, <= escrow)
    /// @param createdAt Task creation timestamp
    /// @param deadline Task deadline timestamp
    /// @param checkpointCount Checkpoints committed so far (recorded; not used for classification)
    struct FailureEvidence {
        FailureEvidenceSource source;
        FailureType reportedType;
        bytes32 evidenceCID;
        uint256 escrowAmount;
        uint256 costAccrued;
        uint256 createdAt;
        uint256 deadline;
        uint256 checkpointCount;
    }

    /// @notice Intelligence hints for task execution (PRD-03)
    /// @dev Computed from historical data, helps agents prepare
    struct IntelligenceHint {
        uint256 successRate;        // Scaled by 1e18
        uint256 avgCheckpoints;     // Average checkpoints before completion
        uint256 commonFailureType;  // Most common failure (cast to FailureType)
        bytes32[] recentFailureCIDs; // Recent failure records for learning
    }
}
