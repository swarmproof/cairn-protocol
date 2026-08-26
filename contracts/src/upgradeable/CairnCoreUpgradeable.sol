// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {ICairnCore} from "../interfaces/ICairnCore.sol";
import {ICairnTypes} from "../interfaces/ICairnTypes.sol";
import {IRecoveryRouter} from "../interfaces/IRecoveryRouter.sol";
import {IFallbackPool} from "../interfaces/IFallbackPool.sol";
import {IArbiterRegistry} from "../interfaces/IArbiterRegistry.sol";
import {IGovernance} from "../interfaces/IGovernance.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {PausableUpgradeable} from "@openzeppelin/contracts-upgradeable/utils/PausableUpgradeable.sol";
import {MerkleProof} from "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/// @title CairnCoreUpgradeable - UUPS Upgradeable Main CAIRN Protocol Contract
/// @author CAIRN Protocol
/// @notice Manages the complete task lifecycle with failure recovery (Upgradeable)
/// @dev Based on PRD-01 through PRD-07, implements UUPS proxy pattern from PRD-06
///
/// State Machine (6 states):
///   IDLE → RUNNING → FAILED → RECOVERING/DISPUTED → RESOLVED
///
/// Key Features:
///   - Auto-selected fallback from pool (NOT pre-declared)
///   - Merkle checkpoint batching for gas efficiency
///   - Intelligent failure routing based on recovery score
///   - Arbiter dispute resolution for contested failures
///   - UUPS upgradeable with governance-controlled authorization
contract CairnCoreUpgradeable is
    ICairnCore,
    Initializable,
    UUPSUpgradeable,
    ReentrancyGuard,
    PausableUpgradeable
{
    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Protocol fee in basis points (0.5%)
    uint256 public constant override protocolFeeBps = 50;

    /// @notice Minimum escrow amount
    uint256 public constant override minEscrow = 0.001 ether;

    /// @notice Minimum heartbeat interval (30 seconds)
    uint256 public constant override minHeartbeatInterval = 30;

    /// @notice Recovery threshold (30%) - scores below this go to DISPUTED
    uint256 public constant override recoveryThreshold = 0.3e18;

    /// @notice Dispute timeout (7 days)
    uint256 public constant override disputeTimeout = 7 days;

    /// @notice Upper bound on a single checkpoint batch's self-reported size (H-5)
    uint256 public constant MAX_CHECKPOINTS_PER_BATCH = 1000;

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice All tasks by ID
    mapping(bytes32 => Task) private _tasks;

    /// @notice Merkle batch roots per task
    mapping(bytes32 => bytes32[]) private _batchRoots;

    /// @notice Merkle batch sizes per task
    mapping(bytes32 => uint256[]) private _batchSizes;

    /// @notice Task IDs by agent
    mapping(address => bytes32[]) private _agentTasks;

    /// @notice Task history by type (for intelligence)
    mapping(bytes32 => bytes32[]) private _taskTypeHistory;

    /// @notice External contract references
    IRecoveryRouter public recoveryRouter;
    IFallbackPool public fallbackPool;
    IArbiterRegistry public arbiterRegistry;
    IGovernance public governance;

    /// @notice Protocol state
    address public override feeRecipient;
    uint256 public override totalEscrowLocked;
    uint256 public override totalTasksCreated;
    uint256 public override totalTasksResolved;

    /// @notice Operator nonces for task ID generation
    mapping(address => uint256) private _operatorNonces;

    /// @notice Amounts owed to recipients whose push payout failed (M-1: pull
    ///         fallback so one reverting recipient can't block a settlement).
    mapping(address => uint256) public pendingWithdrawals;

    /// @dev Storage gap to allow for future variable additions.
    ///      Reduced by 1 when pendingWithdrawals was appended (storage-safe).
    uint256[49] private __gap;

    // ═══════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    /// @notice Initialize the contract
    /// @param _feeRecipient Address to receive protocol fees
    /// @param _recoveryRouter RecoveryRouter contract address
    /// @param _fallbackPool FallbackPool contract address
    /// @param _arbiterRegistry ArbiterRegistry contract address
    /// @param _governance Governance contract address
    function initialize(
        address _feeRecipient,
        address _recoveryRouter,
        address _fallbackPool,
        address _arbiterRegistry,
        address _governance
    ) external initializer {
        // M-10: a zero governance address would permanently brick upgrades
        // (_authorizeUpgrade is onlyGovernance) and all governance actions.
        if (_feeRecipient == address(0) || _governance == address(0)) revert ZeroAddress();

        __Pausable_init();

        feeRecipient = _feeRecipient;
        recoveryRouter = IRecoveryRouter(_recoveryRouter);
        fallbackPool = IFallbackPool(_fallbackPool);
        arbiterRegistry = IArbiterRegistry(_arbiterRegistry);
        governance = IGovernance(_governance);
    }

    // ═══════════════════════════════════════════════════════════════
    // UPGRADE AUTHORIZATION
    // ═══════════════════════════════════════════════════════════════

    /// @notice Authorize upgrade (only governance can upgrade)
    /// @dev Required by UUPS pattern
    /// @param newImplementation Address of the new implementation
    function _authorizeUpgrade(address newImplementation) internal override onlyGovernance {}

    // ═══════════════════════════════════════════════════════════════
    // MODIFIERS
    // ═══════════════════════════════════════════════════════════════

    modifier onlyCurrentAgent(bytes32 taskId) {
        if (msg.sender != _tasks[taskId].currentAgent) {
            revert NotAuthorized(msg.sender, _tasks[taskId].currentAgent);
        }
        _;
    }

    modifier onlyGovernance() {
        if (msg.sender != address(governance)) {
            revert NotAuthorized(msg.sender, address(governance));
        }
        _;
    }

    modifier taskExists(bytes32 taskId) {
        if (_tasks[taskId].operator == address(0)) {
            revert TaskNotFound(taskId);
        }
        _;
    }

    modifier inState(bytes32 taskId, ICairnTypes.TaskState expected) {
        if (_tasks[taskId].state != expected) {
            revert InvalidState(_tasks[taskId].state, expected);
        }
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // TASK LIFECYCLE
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc ICairnCore
    function submitTask(
        bytes32 taskType,
        bytes32 specHash,
        address primaryAgent,
        uint256 heartbeatInterval,
        uint256 deadline
    ) external payable override nonReentrant whenNotPaused returns (bytes32 taskId) {
        // Validation
        if (msg.value < minEscrow) {
            revert InsufficientEscrow(msg.value, minEscrow);
        }
        if (heartbeatInterval < minHeartbeatInterval) {
            revert InvalidHeartbeatInterval(heartbeatInterval, minHeartbeatInterval);
        }
        if (primaryAgent == address(0)) revert ZeroAddress();
        if (deadline <= block.timestamp) {
            revert DeadlineExceeded(bytes32(0), deadline);
        }

        // Generate task ID
        uint256 nonce = _operatorNonces[msg.sender]++;
        taskId = keccak256(abi.encodePacked(
            msg.sender,
            primaryAgent,
            taskType,
            block.timestamp,
            nonce
        ));

        // Auto-select fallback from pool (PRD-04) — NOT pre-declared
        address selectedFallback;
        if (address(fallbackPool) != address(0)) {
            selectedFallback = fallbackPool.selectFallback(taskType, msg.value);
        }

        // Create task
        Task storage task = _tasks[taskId];
        task.id = taskId;
        task.taskType = taskType;
        task.specHash = specHash;
        task.operator = msg.sender;
        task.primaryAgent = primaryAgent;
        task.fallbackAgent = selectedFallback;
        task.currentAgent = primaryAgent;
        task.state = ICairnTypes.TaskState.IDLE;
        task.createdAt = block.timestamp;
        task.deadline = deadline;
        task.escrowAmount = msg.value;
        task.heartbeatInterval = heartbeatInterval;

        // Update state
        _agentTasks[primaryAgent].push(taskId);
        _taskTypeHistory[taskType].push(taskId);
        totalEscrowLocked += msg.value;
        totalTasksCreated++;

        emit TaskCreated(
            taskId,
            taskType,
            msg.sender,
            primaryAgent,
            selectedFallback,
            msg.value,
            deadline
        );
    }

    /// @inheritdoc ICairnCore
    function startTask(bytes32 taskId)
        external
        override
        taskExists(taskId)
        onlyCurrentAgent(taskId)
        inState(taskId, ICairnTypes.TaskState.IDLE)
    {
        Task storage task = _tasks[taskId];

        // Query intelligence for hints (PRD-03)
        ICairnTypes.IntelligenceHint memory hint = _queryIntelligence(task.taskType);

        task.state = ICairnTypes.TaskState.RUNNING;
        task.startedAt = block.timestamp;
        task.lastHeartbeat = block.timestamp;

        emit TaskStarted(taskId, msg.sender, hint.successRate, hint.avgCheckpoints);
    }

    /// @inheritdoc ICairnCore
    function heartbeat(bytes32 taskId)
        external
        override
        taskExists(taskId)
        onlyCurrentAgent(taskId)
    {
        Task storage task = _tasks[taskId];

        // Can heartbeat in RUNNING or RECOVERING
        if (task.state != ICairnTypes.TaskState.RUNNING &&
            task.state != ICairnTypes.TaskState.RECOVERING) {
            revert InvalidState(task.state, ICairnTypes.TaskState.RUNNING);
        }

        // Enforce minimum interval (prevent spam)
        if (block.timestamp < task.lastHeartbeat + minHeartbeatInterval) {
            revert HeartbeatTooFrequent(task.lastHeartbeat, minHeartbeatInterval);
        }

        task.lastHeartbeat = block.timestamp;
        emit Heartbeat(taskId, msg.sender, block.timestamp);
    }

    /// @inheritdoc ICairnCore
    function commitCheckpointBatch(
        bytes32 taskId,
        uint256 count,
        bytes32 merkleRoot,
        bytes32 latestCID,
        bytes32 schemaHash
    ) external override taskExists(taskId) onlyCurrentAgent(taskId) whenNotPaused {
        Task storage task = _tasks[taskId];

        // Can checkpoint in RUNNING or RECOVERING
        if (task.state != ICairnTypes.TaskState.RUNNING &&
            task.state != ICairnTypes.TaskState.RECOVERING) {
            revert InvalidState(task.state, ICairnTypes.TaskState.RUNNING);
        }

        // PRD-04 Phase 3: enforce the committed schema against the task's specHash
        if (schemaHash != task.specHash) {
            revert InvalidCheckpointSchema(schemaHash, task.specHash);
        }

        // H-5: bound the self-reported batch size. The escrow split is weighted by
        // checkpoint counts, so an unbounded count lets an agent capture the whole
        // payout. This caps per-batch inflation; binding count to the Merkle tree's
        // leaf count is tracked as a follow-up hardening item.
        if (count == 0 || count > MAX_CHECKPOINTS_PER_BATCH) {
            revert InvalidCheckpointCount(count, MAX_CHECKPOINTS_PER_BATCH);
        }

        uint256 batchStart = task.checkpointCount;

        // Track who committed these checkpoints
        if (msg.sender == task.primaryAgent) {
            task.primaryCheckpoints += count;
        } else {
            task.fallbackCheckpoints += count;
        }

        task.checkpointCount += count;
        task.latestCheckpointCID = latestCID;
        task.lastHeartbeat = block.timestamp; // Checkpoint acts as heartbeat

        _batchRoots[taskId].push(merkleRoot);
        _batchSizes[taskId].push(count);

        emit CheckpointBatchCommitted(
            taskId,
            msg.sender,
            batchStart,
            task.checkpointCount - 1,
            merkleRoot,
            latestCID
        );
    }

    /// @inheritdoc ICairnCore
    function completeTask(bytes32 taskId)
        external
        override
        taskExists(taskId)
        onlyCurrentAgent(taskId)
        nonReentrant
        whenNotPaused
    {
        Task storage task = _tasks[taskId];

        // Can complete from RUNNING or RECOVERING
        if (task.state != ICairnTypes.TaskState.RUNNING &&
            task.state != ICairnTypes.TaskState.RECOVERING) {
            revert InvalidState(task.state, ICairnTypes.TaskState.RUNNING);
        }

        // Check deadline
        if (block.timestamp > task.deadline) {
            revert DeadlineExceeded(taskId, task.deadline);
        }

        task.state = ICairnTypes.TaskState.RESOLVED;
        task.resolutionType = ICairnTypes.ResolutionType.SUCCESS;

        // H-3: notify the fallback pool of a successful recovery (releases the
        // fallback's activeTaskCount). No-op if the primary completed directly.
        _releaseFallback(task, taskId, true);

        emit TaskCompleted(taskId, msg.sender, task.checkpointCount);

        _settleEscrow(taskId);
    }

    // ═══════════════════════════════════════════════════════════════
    // FAILURE DETECTION & RECOVERY (PRD-02)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc ICairnCore
    function isStale(bytes32 taskId) public view override taskExists(taskId) returns (bool) {
        Task storage task = _tasks[taskId];
        if (task.state != ICairnTypes.TaskState.RUNNING &&
            task.state != ICairnTypes.TaskState.RECOVERING) {
            return false;
        }

        // Stale if heartbeat missed by 2x interval
        return block.timestamp > task.lastHeartbeat + (task.heartbeatInterval * 2);
    }

    /// @inheritdoc ICairnCore
    function detectFailure(bytes32 taskId)
        external
        override
        taskExists(taskId)
        nonReentrant
        whenNotPaused
    {
        Task storage task = _tasks[taskId];

        if (!isStale(taskId)) revert TaskNotStale(taskId);

        // Classify failure via RecoveryRouter (PRD-02)
        (
            ICairnTypes.FailureClass failureClass,
            ICairnTypes.FailureType failureType,
            uint256 recoveryScore,
            bytes32 failureRecordCID
        ) = recoveryRouter.classifyAndScore(
            taskId,
            task.escrowAmount,
            task.createdAt,
            task.deadline,
            task.checkpointCount
        );

        // Store failure data
        task.failureClass = failureClass;
        task.failureType = failureType;
        task.recoveryScore = recoveryScore;
        task.failureRecordCID = failureRecordCID;
        task.state = ICairnTypes.TaskState.FAILED;

        emit TaskFailed(
            taskId,
            task.currentAgent,
            failureClass,
            failureType,
            recoveryScore,
            failureRecordCID
        );

        // Route based on recovery score
        _routeFailedTask(taskId);
    }

    /// @notice Route failed task to RECOVERING or DISPUTED
    function _routeFailedTask(bytes32 taskId) internal {
        Task storage task = _tasks[taskId];

        // H-4: a task already past its deadline can never be completed by a
        // recovering fallback (completeTask reverts past the deadline), which
        // would trap the escrow in an unresolvable RECOVERING loop. Route it
        // straight to dispute so it can reach timeout refund / arbitration.
        if (block.timestamp > task.deadline) {
            _enterDispute(task, taskId);
            return;
        }

        // H-3: allow only one fallback recovery attempt. If a fallback was already
        // activated and the task failed again, release it and move to dispute
        // rather than re-activating (which would double-count and never resolve).
        if (task.fallbackActivated) {
            _enterDispute(task, taskId);
            return;
        }

        if (task.recoveryScore >= recoveryThreshold) {
            // High recovery score → automatic fallback
            if (task.fallbackAgent != address(0)) {
                task.state = ICairnTypes.TaskState.RECOVERING;
                task.currentAgent = task.fallbackAgent;

                // Notify fallback pool
                if (address(fallbackPool) != address(0)) {
                    task.fallbackActivated = true;
                    fallbackPool.activateFallback(taskId, task.fallbackAgent);
                }

                emit RecoveryStarted(
                    taskId,
                    task.fallbackAgent,
                    task.checkpointCount
                );
            } else {
                // No fallback available → dispute
                _enterDispute(task, taskId);
            }
        } else {
            // Low recovery score → dispute required
            _enterDispute(task, taskId);
        }
    }

    /// @notice Enter DISPUTED state
    function _enterDispute(Task storage task, bytes32 taskId) internal {
        task.state = ICairnTypes.TaskState.DISPUTED;
        // H-1: anchor the timeout window to dispute onset, not task creation.
        task.disputedAt = block.timestamp;

        // H-3: release an active fallback as a failed recovery so its stake is
        // freed (activeTaskCount decremented) and slashing runs. No-op if no
        // fallback was activated (task disputed without a recovery attempt).
        _releaseFallback(task, taskId, false);

        emit TaskDisputed(
            taskId,
            task.recoveryScore,
            task.disputedAt + disputeTimeout
        );
    }

    /// @notice Notify the fallback pool exactly once when an active fallback
    ///         recovery terminates (H-3), decrementing its activeTaskCount and
    ///         triggering slashing on failure.
    function _releaseFallback(Task storage task, bytes32 taskId, bool success) internal {
        if (!task.fallbackActivated) return;
        task.fallbackActivated = false;
        if (address(fallbackPool) != address(0)) {
            fallbackPool.completeFallbackTask(
                taskId,
                task.fallbackAgent,
                success,
                task.fallbackCheckpoints
            );
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // DISPUTE RESOLUTION (PRD-05)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc ICairnCore
    function resolveDispute(bytes32 taskId, ICairnTypes.Ruling calldata ruling)
        external
        override
        taskExists(taskId)
        inState(taskId, ICairnTypes.TaskState.DISPUTED)
        nonReentrant
        whenNotPaused
    {
        Task storage task = _tasks[taskId];

        // CR-3: the operator must not arbitrate their own dispute (conflict of
        // interest — the registry already excludes the primary/fallback agents).
        if (msg.sender == task.operator) revert ArbiterIsOperator();

        // Execute ruling via arbiter registry
        uint256 arbiterFee = arbiterRegistry.executeRuling(
            taskId,
            ruling,
            msg.sender,
            task.escrowAmount,
            task.primaryAgent,
            task.fallbackAgent,
            task.taskType
        );

        task.state = ICairnTypes.TaskState.RESOLVED;
        task.resolutionType = ICairnTypes.ResolutionType.ARBITER_RULING;

        // Settle based on ruling
        _settleDispute(taskId, ruling, arbiterFee, msg.sender);
    }

    /// @inheritdoc ICairnCore
    function resolveDisputeTimeout(bytes32 taskId)
        external
        override
        taskExists(taskId)
        inState(taskId, ICairnTypes.TaskState.DISPUTED)
        nonReentrant
        whenNotPaused
    {
        Task storage task = _tasks[taskId];

        // Check timeout has passed (H-1: measured from dispute onset)
        if (block.timestamp < task.disputedAt + disputeTimeout) {
            revert DisputeTimeoutNotReached();
        }

        // Auto-refund to operator on timeout
        task.state = ICairnTypes.TaskState.RESOLVED;
        task.resolutionType = ICairnTypes.ResolutionType.TIMEOUT_REFUND;

        _refundOperator(taskId);
    }

    // ═══════════════════════════════════════════════════════════════
    // MERKLE VERIFICATION (PRD-07)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc ICairnCore
    function verifyCheckpoint(
        bytes32 taskId,
        bytes32 cid,
        uint256 batchIndex,
        uint256 leafIndex,
        bytes32[] calldata proof
    ) external view override taskExists(taskId) returns (bool) {
        bytes32[] storage roots = _batchRoots[taskId];

        if (batchIndex >= roots.length) {
            return false;
        }

        bytes32 leaf = keccak256(abi.encodePacked(cid, leafIndex));
        return MerkleProof.verify(proof, roots[batchIndex], leaf);
    }

    /// @inheritdoc ICairnCore
    function getBatchRoots(bytes32 taskId)
        external
        view
        override
        taskExists(taskId)
        returns (bytes32[] memory)
    {
        return _batchRoots[taskId];
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc ICairnCore
    function getTask(bytes32 taskId)
        external
        view
        override
        taskExists(taskId)
        returns (Task memory)
    {
        return _tasks[taskId];
    }

    /// @notice Get task IDs for an agent
    function getAgentTasks(address agent) external view returns (bytes32[] memory) {
        return _agentTasks[agent];
    }

    /// @notice Get task history for a type
    function getTaskTypeHistory(bytes32 taskType) external view returns (bytes32[] memory) {
        return _taskTypeHistory[taskType];
    }

    // ═══════════════════════════════════════════════════════════════
    // SETTLEMENT
    // ═══════════════════════════════════════════════════════════════

    /// @notice Emitted when a push payout failed and was credited for later pull
    event PayoutDeferred(address indexed to, uint256 amount);
    /// @notice Emitted when a deferred payout is withdrawn
    event Withdrawn(address indexed to, uint256 amount);
    /// @notice No deferred balance to withdraw
    error NothingToWithdraw();

    /// @notice Pay `to` `amount`, falling back to a claimable balance if the push
    ///         transfer fails (M-1: prevents a reverting recipient from blocking
    ///         the whole settlement / locking escrow).
    function _payout(address to, uint256 amount) internal {
        if (amount == 0) return;
        (bool ok, ) = to.call{value: amount}("");
        if (!ok) {
            pendingWithdrawals[to] += amount;
            emit PayoutDeferred(to, amount);
        }
    }

    /// @notice Withdraw a payout that was deferred because its push transfer failed.
    function withdraw() external nonReentrant {
        uint256 amount = pendingWithdrawals[msg.sender];
        if (amount == 0) revert NothingToWithdraw();
        pendingWithdrawals[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "Withdraw failed");
        emit Withdrawn(msg.sender, amount);
    }

    /// @notice Calculate and distribute escrow for successful task
    function _settleEscrow(bytes32 taskId) internal {
        Task storage task = _tasks[taskId];

        uint256 escrow = task.escrowAmount;
        uint256 protocolFee = (escrow * protocolFeeBps) / 10000;
        uint256 distributable = escrow - protocolFee;

        // Calculate split based on checkpoints
        uint256 primaryCheckpoints = task.primaryCheckpoints;
        uint256 fallbackCheckpoints = task.fallbackCheckpoints;
        uint256 totalCheckpoints = primaryCheckpoints + fallbackCheckpoints;

        uint256 primaryPayout;
        uint256 fallbackPayout;

        if (totalCheckpoints > 0) {
            primaryPayout = (distributable * primaryCheckpoints) / totalCheckpoints;
            fallbackPayout = distributable - primaryPayout;
        } else {
            // No checkpoints: full payout to completing agent
            if (task.currentAgent == task.primaryAgent) {
                primaryPayout = distributable;
            } else {
                fallbackPayout = distributable;
            }
        }

        // Store settlement amounts
        task.settledPrimary = primaryPayout;
        task.settledFallback = fallbackPayout;

        // Transfer funds (M-1: push with pull fallback)
        _payout(task.primaryAgent, primaryPayout);
        _payout(task.fallbackAgent, fallbackPayout);
        _payout(feeRecipient, protocolFee);

        // Update state
        totalEscrowLocked -= escrow;
        totalTasksResolved++;

        emit TaskSettled(
            taskId,
            task.resolutionType,
            primaryPayout,
            fallbackPayout,
            protocolFee
        );
    }

    /// @notice Settle based on arbiter ruling
    function _settleDispute(
        bytes32 taskId,
        ICairnTypes.Ruling calldata ruling,
        uint256 arbiterFee,
        address arbiter
    ) internal {
        Task storage task = _tasks[taskId];

        uint256 escrow = task.escrowAmount;
        uint256 protocolFee = (escrow * protocolFeeBps) / 10000;
        uint256 distributable = escrow - protocolFee - arbiterFee;

        uint256 primaryPayout;
        uint256 fallbackPayout;
        uint256 operatorRefund;

        if (ruling.outcome == ICairnTypes.RulingOutcome.REFUND_OPERATOR) {
            operatorRefund = distributable;
        } else if (ruling.outcome == ICairnTypes.RulingOutcome.PAY_AGENT) {
            // Pay proportionally based on checkpoints
            uint256 total = task.primaryCheckpoints + task.fallbackCheckpoints;
            if (total > 0) {
                primaryPayout = (distributable * task.primaryCheckpoints) / total;
                fallbackPayout = distributable - primaryPayout;
            } else {
                primaryPayout = distributable;
            }
        } else {
            // SPLIT: agentShare% goes to the agents, split by checkpoint
            // contribution; the remainder is refunded to the operator.
            // M-3: bound agentShare (prevents underflow-revert griefing) and pay
            // the fallback its share instead of sending everything to the primary.
            if (ruling.agentShare > 100) revert InvalidAgentShare(ruling.agentShare);
            uint256 agentTotal = (distributable * ruling.agentShare) / 100;
            operatorRefund = distributable - agentTotal;
            uint256 total = task.primaryCheckpoints + task.fallbackCheckpoints;
            if (total > 0) {
                primaryPayout = (agentTotal * task.primaryCheckpoints) / total;
                fallbackPayout = agentTotal - primaryPayout;
            } else {
                primaryPayout = agentTotal;
            }
        }

        // Store settlement
        task.settledPrimary = primaryPayout;
        task.settledFallback = fallbackPayout;

        // Transfer funds (M-1: push with pull fallback)
        _payout(task.primaryAgent, primaryPayout);
        _payout(task.fallbackAgent, fallbackPayout);
        _payout(task.operator, operatorRefund);
        _payout(feeRecipient, protocolFee);
        // H-2: pay the arbiter their fee out of escrow (previously subtracted
        // from distributable but never transferred → ETH stranded in Core).
        _payout(arbiter, arbiterFee);

        totalEscrowLocked -= escrow;
        totalTasksResolved++;

        emit TaskSettled(
            taskId,
            task.resolutionType,
            primaryPayout,
            fallbackPayout,
            protocolFee
        );
    }

    /// @notice Refund operator (for timeout)
    function _refundOperator(bytes32 taskId) internal {
        Task storage task = _tasks[taskId];

        uint256 escrow = task.escrowAmount;

        _payout(task.operator, escrow); // M-1: push with pull fallback

        totalEscrowLocked -= escrow;
        totalTasksResolved++;

        emit TaskSettled(taskId, task.resolutionType, 0, 0, 0);
    }

    // ═══════════════════════════════════════════════════════════════
    // INTELLIGENCE LAYER (PRD-03)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Query intelligence for a task type
    function _queryIntelligence(bytes32 taskType)
        internal
        view
        returns (ICairnTypes.IntelligenceHint memory hint)
    {
        bytes32[] storage history = _taskTypeHistory[taskType];
        uint256 historyLen = history.length;

        if (historyLen == 0) {
            return hint; // No history
        }

        // Calculate on-chain hints (basic)
        uint256 successCount;
        uint256 totalCheckpoints;
        uint256 sampleStart = historyLen > 5 ? historyLen - 5 : 0;

        for (uint256 i = sampleStart; i < historyLen; i++) {
            Task storage t = _tasks[history[i]];
            if (t.state == ICairnTypes.TaskState.RESOLVED &&
                t.resolutionType == ICairnTypes.ResolutionType.SUCCESS) {
                successCount++;
            }
            totalCheckpoints += t.checkpointCount;
        }

        uint256 sampleSize = historyLen - sampleStart;
        hint.successRate = (successCount * 1e18) / sampleSize;
        hint.avgCheckpoints = totalCheckpoints / sampleSize;

        return hint;
    }

    // ═══════════════════════════════════════════════════════════════
    // GOVERNANCE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Pause the protocol (emergency)
    function pause() external onlyGovernance {
        _pause();
    }

    /// @notice Unpause the protocol
    function unpause() external onlyGovernance {
        _unpause();
    }

    /// @notice Update external contract references
    function setContracts(
        address _recoveryRouter,
        address _fallbackPool,
        address _arbiterRegistry
    ) external onlyGovernance {
        // M-10: router and registry are required for failure handling / disputes;
        // the fallback pool is intentionally optional (zero disables auto-fallback).
        if (_recoveryRouter == address(0) || _arbiterRegistry == address(0)) revert ZeroAddress();
        recoveryRouter = IRecoveryRouter(_recoveryRouter);
        fallbackPool = IFallbackPool(_fallbackPool);
        arbiterRegistry = IArbiterRegistry(_arbiterRegistry);
    }

    /// @notice Update fee recipient
    function setFeeRecipient(address _feeRecipient) external onlyGovernance {
        if (_feeRecipient == address(0)) revert ZeroAddress();
        feeRecipient = _feeRecipient;
    }

    /// @notice Receive ETH (for arbiter fee refunds)
    receive() external payable {}
}
