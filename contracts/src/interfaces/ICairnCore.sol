// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {ICairnTypes} from "./ICairnTypes.sol";

/// @title ICairnCore - Main CAIRN Protocol interface
/// @notice Defines the complete task lifecycle with failure recovery
/// @dev Based on PRD-01 through PRD-07
///
/// State Machine (PRD-06: 6 states):
///   IDLE → RUNNING → FAILED → RECOVERING/DISPUTED → RESOLVED
///
/// Key Features:
///   - PRD-01: Task submission, checkpoints, heartbeat, settlement
///   - PRD-02: Failure classification, recovery scoring
///   - PRD-04: Auto-selected fallback from pool (NOT pre-declared)
///   - PRD-05: Arbiter dispute resolution
///   - PRD-07: Merkle checkpoint batching
interface ICairnCore {
    // ═══════════════════════════════════════════════════════════════
    // STRUCTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Complete task data structure
    struct Task {
        // Identity
        bytes32 id;
        bytes32 taskType;
        bytes32 specHash;

        // Participants
        address operator;
        address primaryAgent;
        address fallbackAgent;
        address currentAgent;

        // State
        ICairnTypes.TaskState state;
        uint256 createdAt;
        uint256 startedAt;
        uint256 deadline;

        // Escrow
        uint256 escrowAmount;
        uint256 settledPrimary;
        uint256 settledFallback;

        // Heartbeat
        uint256 heartbeatInterval;
        uint256 lastHeartbeat;

        // Checkpoints (PRD-07: Merkle batched)
        uint256 checkpointCount;
        uint256 primaryCheckpoints;
        uint256 fallbackCheckpoints;
        bytes32 latestCheckpointCID;

        // Failure (PRD-02)
        ICairnTypes.FailureClass failureClass;
        ICairnTypes.FailureType failureType;
        bytes32 failureRecordCID;
        uint256 recoveryScore;

        // Resolution
        ICairnTypes.ResolutionType resolutionType;
        bytes32 resolutionRecordCID;

        // Recovery routing tier (PRD-04 three-tier routing; appended for storage safety)
        ICairnTypes.RecoveryScope recoveryScope;

        // Dispute onset timestamp (H-1: timeout window anchors here, not createdAt;
        // appended for storage safety)
        uint256 disputedAt;

        // Whether a fallback recovery is currently active for this task (H-3:
        // ensures the fallback pool is notified exactly once on the terminal
        // transition, so activeTaskCount is released and slashing runs on failed
        // recoveries). Appended for storage safety.
        bool fallbackActivated;

        // Timestamp an arbiter ruling was recorded (M-2: escrow is held until the
        // appeal window elapses, then finalizeDispute settles the possibly-overturned
        // ruling). Zero means no ruling recorded yet. Appended for storage safety.
        uint256 disputeRuledAt;

        // Cumulative execution cost reported by the task's agents, in wei, clamped to
        // escrowAmount. Feeds the recovery score's budget input B. Appended for storage safety.
        uint256 costAccrued;

        // Evidence the failure was recorded from, and the agent's evidence CID (zero for
        // mechanical sources). Appended for storage safety.
        ICairnTypes.FailureEvidenceSource failureEvidenceSource;
        bytes32 failureEvidenceCID;
    }

    // ═══════════════════════════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════════════════════════

    // Lifecycle
    event TaskCreated(
        bytes32 indexed taskId,
        bytes32 indexed taskType,
        address indexed operator,
        address primaryAgent,
        address fallbackAgent,
        uint256 escrow,
        uint256 deadline
    );

    event TaskStarted(
        bytes32 indexed taskId,
        address indexed agent,
        uint256 successRate,
        uint256 avgCheckpoints
    );

    event TaskCompleted(
        bytes32 indexed taskId,
        address indexed agent,
        uint256 checkpointCount
    );

    // Checkpoints (PRD-07)
    event CheckpointBatchCommitted(
        bytes32 indexed taskId,
        address indexed agent,
        uint256 batchStartIndex,
        uint256 batchEndIndex,
        bytes32 merkleRoot,
        bytes32 latestCID
    );

    event Heartbeat(
        bytes32 indexed taskId,
        address indexed agent,
        uint256 timestamp
    );

    // Failure & Recovery (PRD-02)
    event TaskFailed(
        bytes32 indexed taskId,
        address indexed agent,
        ICairnTypes.FailureClass failureClass,
        ICairnTypes.FailureType failureType,
        uint256 recoveryScore,
        bytes32 failureRecordCID
    );

    event RecoveryStarted(
        bytes32 indexed taskId,
        address indexed fallbackAgent,
        uint256 resumeFromCheckpoint
    );

    /// @notice Emitted when a recovering task's scope tier is assigned (PRD-04 three-tier routing)
    event RecoveryScopeAssigned(
        bytes32 indexed taskId,
        ICairnTypes.RecoveryScope scope
    );

    event TaskDisputed(
        bytes32 indexed taskId,
        uint256 recoveryScore,
        uint256 disputeDeadline
    );

    // Failure evidence and cost
    event CostReported(bytes32 indexed taskId, address indexed agent, uint256 costAccrued);

    event FailureEvidenceRecorded(
        bytes32 indexed taskId,
        ICairnTypes.FailureEvidenceSource source,
        ICairnTypes.FailureType failureType,
        bytes32 evidenceCID
    );

    // Settlement
    event TaskSettled(
        bytes32 indexed taskId,
        ICairnTypes.ResolutionType resolutionType,
        uint256 primaryPayout,
        uint256 fallbackPayout,
        uint256 protocolFee
    );

    // ═══════════════════════════════════════════════════════════════
    // ERRORS
    // ═══════════════════════════════════════════════════════════════

    error TaskNotFound(bytes32 taskId);
    error InvalidState(ICairnTypes.TaskState current, ICairnTypes.TaskState expected);
    error NotAuthorized(address caller, address expected);
    error InsufficientEscrow(uint256 provided, uint256 minimum);
    error InvalidHeartbeatInterval(uint256 provided, uint256 minimum);
    error HeartbeatTooFrequent(uint256 lastHeartbeat, uint256 minInterval);
    error TaskNotStale(bytes32 taskId); // neither heartbeat-stale nor past the deadline
    error CostNotMonotonic(uint256 provided, uint256 current);
    error InvalidFailureReport(ICairnTypes.FailureType failureType);
    error DeadlineExceeded(bytes32 taskId, uint256 deadline);
    error InvalidMerkleProof();
    error DisputeTimeoutNotReached();
    error ZeroAddress();
    error InvalidReducedScopeCap(uint256 bps);
    error InvalidCheckpointSchema(bytes32 provided, bytes32 expected);
    error ArbiterIsOperator();
    error InvalidCheckpointCount(uint256 provided, uint256 max);
    error InvalidAgentShare(uint256 share);
    error DisputeAlreadyRuled();
    error DisputeNotRuled();
    error AppealWindowNotClosed();

    // ═══════════════════════════════════════════════════════════════
    // TASK LIFECYCLE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Submit a new task with escrow
    /// @dev Fallback is auto-selected from pool, NOT pre-declared
    /// @param taskType Domain.operation format identifier
    /// @param specHash Hash of task specification (stored off-chain)
    /// @param primaryAgent The agent to execute the task
    /// @param heartbeatInterval Required heartbeat frequency in seconds
    /// @param deadline Task must complete by this timestamp
    /// @return taskId The created task's unique identifier
    function submitTask(
        bytes32 taskType,
        bytes32 specHash,
        address primaryAgent,
        uint256 heartbeatInterval,
        uint256 deadline
    ) external payable returns (bytes32 taskId);

    /// @notice Agent starts executing the task
    /// @param taskId The task to start
    function startTask(bytes32 taskId) external;

    /// @notice Agent sends heartbeat to prove liveness
    /// @param taskId The task being executed
    function heartbeat(bytes32 taskId) external;

    /// @notice Commit a batch of checkpoints
    /// @dev The batch size is the number of CIDs supplied (1..MAX_CHECKPOINTS_PER_BATCH) and
    ///      the batch's Merkle root is computed on-chain from them: leaf i is
    ///      keccak256(abi.encodePacked(cids[i], i)), pairs are hashed with OpenZeppelin's
    ///      commutative keccak256, and an odd last node is promoted. The last CID becomes the
    ///      task's latest checkpoint CID. The contract commits to the CIDs; it does not verify
    ///      the content they reference.
    /// @param taskId The task being executed
    /// @param cids Checkpoint content identifiers, in order
    /// @param schemaHash Schema hash for this batch; must equal the task's specHash (PRD-04 Phase 3)
    function commitCheckpointBatch(
        bytes32 taskId,
        bytes32[] calldata cids,
        bytes32 schemaHash
    ) external;

    /// @notice Agent marks task as successfully completed
    /// @param taskId The task to complete
    function completeTask(bytes32 taskId) external;

    // ═══════════════════════════════════════════════════════════════
    // FAILURE DETECTION & RECOVERY (PRD-02)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Check if a task is stale (heartbeat missed)
    /// @param taskId The task to check
    /// @return stale True if heartbeat was missed
    function isStale(bytes32 taskId) external view returns (bool stale);

    /// @notice Record mechanically verifiable failure evidence and route the task
    /// @dev Permissionless. Succeeds when the task's deadline has passed (DEADLINE_EXPIRED,
    ///      takes precedence) or its heartbeat was missed by more than 2x the interval
    ///      (HEARTBEAT_TIMEOUT). Reverts TaskNotStale otherwise.
    /// @param taskId The task that may have failed
    function detectFailure(bytes32 taskId) external;

    /// @notice The current agent declares that its execution failed
    /// @dev Records AGENT_REPORT evidence (attested, not verified on-chain) and routes the
    ///      task without waiting for a heartbeat timeout. HEARTBEAT_MISS and
    ///      DEADLINE_EXCEEDED cannot be reported; they are established by detectFailure.
    /// @param taskId The task
    /// @param failureType The failure type the agent declares
    /// @param evidenceCID Content identifier of the agent's supporting evidence
    function reportFailure(
        bytes32 taskId,
        ICairnTypes.FailureType failureType,
        bytes32 evidenceCID
    ) external;

    /// @notice The current agent reports the task's cumulative execution cost
    /// @dev Attested by the agent, not verified on-chain. Must be non-decreasing; the stored
    ///      value is clamped to the task escrow (reaching it means the budget is exhausted).
    ///      Used as the recovery score's budget input B = (escrow - costAccrued) / escrow.
    ///      Settlement does not depend on it.
    /// @param taskId The task
    /// @param cumulativeCost Total cost consumed by the task so far, in wei
    function reportCost(bytes32 taskId, uint256 cumulativeCost) external;

    // ═══════════════════════════════════════════════════════════════
    // DISPUTE RESOLUTION (PRD-05)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Arbiter submits ruling for disputed task
    /// @param taskId The disputed task
    /// @param ruling The arbiter's ruling
    function resolveDispute(bytes32 taskId, ICairnTypes.Ruling calldata ruling) external;

    /// @notice Timeout resolution for disputed tasks
    /// @param taskId The disputed task
    function resolveDisputeTimeout(bytes32 taskId) external;

    /// @notice Settle a disputed task after its arbiter ruling's appeal window has
    ///         elapsed (M-2). Uses the current (possibly overturned) stored ruling.
    function finalizeDispute(bytes32 taskId) external;

    // ═══════════════════════════════════════════════════════════════
    // MERKLE VERIFICATION (PRD-07)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Verify a specific checkpoint was included in a batch
    /// @param taskId The task
    /// @param cid The checkpoint CID to verify
    /// @param batchIndex Which batch the checkpoint is in
    /// @param leafIndex Index within the batch
    /// @param proof Merkle proof
    /// @return valid True if checkpoint is verified
    function verifyCheckpoint(
        bytes32 taskId,
        bytes32 cid,
        uint256 batchIndex,
        uint256 leafIndex,
        bytes32[] calldata proof
    ) external view returns (bool valid);

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Get complete task data
    /// @param taskId The task ID
    /// @return task The task struct
    function getTask(bytes32 taskId) external view returns (Task memory task);

    /// @notice Get batch roots for a task
    /// @param taskId The task ID
    /// @return roots Array of Merkle roots
    function getBatchRoots(bytes32 taskId) external view returns (bytes32[] memory roots);

    /// @notice Get protocol fee in basis points
    function protocolFeeBps() external view returns (uint256);

    /// @notice Get minimum escrow amount
    function minEscrow() external view returns (uint256);

    /// @notice Get minimum heartbeat interval
    function minHeartbeatInterval() external view returns (uint256);

    /// @notice Get recovery threshold
    function recoveryThreshold() external view returns (uint256);

    /// @notice Get dispute timeout duration
    function disputeTimeout() external view returns (uint256);

    /// @notice Get fee recipient address
    function feeRecipient() external view returns (address);

    /// @notice Get total escrowed funds
    function totalEscrowLocked() external view returns (uint256);

    /// @notice Get total tasks created
    function totalTasksCreated() external view returns (uint256);

    /// @notice Get total tasks resolved
    function totalTasksResolved() external view returns (uint256);
}
