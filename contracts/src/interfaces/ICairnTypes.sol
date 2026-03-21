// SPDX-License-Identifier: BSL-1.1
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
    /// @dev Weights: LIVENESS=0.9, RESOURCE=0.5, LOGIC=0.1
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
        INVARIANT_VIOLATION
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

    /// @notice Intelligence hints for task execution (PRD-03)
    /// @dev Computed from historical data, helps agents prepare
    struct IntelligenceHint {
        uint256 successRate;        // Scaled by 1e18
        uint256 avgCheckpoints;     // Average checkpoints before completion
        uint256 commonFailureType;  // Most common failure (cast to FailureType)
        bytes32[] recentFailureCIDs; // Recent failure records for learning
    }
}
