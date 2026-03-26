// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {IFallbackPool} from "../interfaces/IFallbackPool.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/// @title FallbackPoolUpgradeable - UUPS Upgradeable fallback agent pool
/// @author CAIRN Protocol
/// @notice Manages registration, selection, and slashing of fallback agents (Upgradeable)
/// @dev Based on PRD-04 Sections 2-3, implements UUPS proxy pattern from PRD-06
///
/// Two-Gate Admission:
///   1. Reputation >= 50 (from ERC-8004, mocked for now)
///   2. Stake >= 10% of max eligible escrow
///
/// Selection Algorithm:
///   score = (success_rate × 0.4) + (reputation × 0.3) + (stake_ratio × 0.2) + (availability × 0.1)
///
/// Slashing Rules:
///   - Accept + 0 checkpoints + fail → 100% stake to operator
///   - Accept + some checkpoints + fail → 50% stake to treasury
///   - Timeout without response → 25% stake to treasury
contract FallbackPoolUpgradeable is
    IFallbackPool,
    Initializable,
    UUPSUpgradeable,
    ReentrancyGuard,
    OwnableUpgradeable
{
    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS (PRD-04 Section 2.2)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Minimum reputation to join pool (50/100)
    uint256 public constant override minReputation = 50;

    /// @notice Minimum stake as percentage of escrow (10%)
    uint256 public constant override minStakePercent = 10;

    /// @notice Max allowed failure rate before auto-slash (30%)
    uint256 public constant MAX_FAILURE_RATE = 30;

    /// @notice Precision for percentage calculations
    uint256 private constant PRECISION = 100;

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Registered fallback agents
    mapping(address => FallbackAgent) private _agents;

    /// @notice List of all registered agent addresses
    address[] private _agentList;

    /// @notice Agents registered for each task type
    mapping(bytes32 => address[]) private _taskTypeAgents;

    /// @notice CairnCore contract address
    address public override cairnCore;

    /// @notice Fee recipient for slashed funds
    address public override feeRecipient;

    /// @notice Mocked reputation scores (replace with ERC-8004 in production)
    mapping(address => uint256) private _mockReputations;

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
    /// @param _feeRecipient Fee recipient address
    /// @param _owner Initial owner address
    function initialize(
        address _cairnCore,
        address _feeRecipient,
        address _owner
    ) external initializer {
        if (_feeRecipient == address(0)) revert ZeroAddress();

        __Ownable_init(_owner);

        cairnCore = _cairnCore;
        feeRecipient = _feeRecipient;
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
        if (msg.sender != cairnCore) revert NotCairnCore();
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // REGISTRATION (PRD-04 Section 2.2)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IFallbackPool
    function register(bytes32[] calldata taskTypes, uint256 maxConcurrent) external payable override {
        if (_agents[msg.sender].registered) revert AlreadyRegistered();
        if (msg.value == 0) revert InsufficientStake(1, 0);
        if (taskTypes.length == 0) revert InvalidTaskTypes();

        // Check reputation (mocked - replace with ERC-8004)
        uint256 reputation = _getReputation(msg.sender);
        if (reputation < minReputation) {
            revert InsufficientReputation(minReputation, reputation);
        }

        // Create agent record
        _agents[msg.sender] = FallbackAgent({
            registered: true,
            stake: msg.value,
            supportedTaskTypes: taskTypes,
            reputation: reputation,
            activeTaskCount: 0,
            maxConcurrentTasks: maxConcurrent,
            completedTasks: 0,
            failedTasks: 0,
            lastActive: block.timestamp
        });

        // Register for each task type
        for (uint256 i = 0; i < taskTypes.length; i++) {
            _taskTypeAgents[taskTypes[i]].push(msg.sender);
        }

        _agentList.push(msg.sender);

        emit AgentRegistered(msg.sender, taskTypes, msg.value);
    }

    /// @inheritdoc IFallbackPool
    function addStake() external payable override {
        FallbackAgent storage agent = _agents[msg.sender];
        if (!agent.registered) revert NotRegistered();

        agent.stake += msg.value;
        emit StakeAdded(msg.sender, msg.value, agent.stake);
    }

    /// @inheritdoc IFallbackPool
    function withdrawStake(uint256 amount) external override nonReentrant {
        FallbackAgent storage agent = _agents[msg.sender];
        if (!agent.registered) revert NotRegistered();
        if (agent.activeTaskCount > 0) revert ActiveRecoveriesPending();
        if (agent.stake < amount) revert InsufficientStake(amount, agent.stake);

        agent.stake -= amount;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        emit StakeWithdrawn(msg.sender, amount, agent.stake);
    }

    /// @inheritdoc IFallbackPool
    function deregister() external override nonReentrant {
        FallbackAgent storage agent = _agents[msg.sender];
        if (!agent.registered) revert NotRegistered();
        if (agent.activeTaskCount > 0) revert ActiveRecoveriesPending();

        uint256 stakeToReturn = agent.stake;

        // Remove from task type mappings
        bytes32[] memory taskTypes = agent.supportedTaskTypes;
        for (uint256 i = 0; i < taskTypes.length; i++) {
            _removeFromTaskType(taskTypes[i], msg.sender);
        }

        // Remove from agent list
        _removeFromAgentList(msg.sender);

        // Clear agent data
        delete _agents[msg.sender];

        // Return stake
        if (stakeToReturn > 0) {
            (bool success, ) = msg.sender.call{value: stakeToReturn}("");
            require(success, "Transfer failed");
        }

        emit AgentDeregistered(msg.sender, stakeToReturn);
    }

    // ═══════════════════════════════════════════════════════════════
    // SELECTION (PRD-04 Section 2.4)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IFallbackPool
    function selectFallback(bytes32 taskType, uint256 escrowAmount)
        external
        view
        override
        returns (address bestAgent)
    {
        address[] storage candidates = _taskTypeAgents[taskType];

        if (candidates.length == 0) {
            return address(0);
        }

        uint256 bestScore;
        uint256 requiredStake = getMinStake(escrowAmount);

        for (uint256 i = 0; i < candidates.length; i++) {
            address candidate = candidates[i];
            FallbackAgent storage agent = _agents[candidate];

            // Skip if disqualified
            if (!_isEligible(agent, requiredStake)) continue;

            // Calculate selection score
            uint256 score = _calculateScore(agent, escrowAmount);

            if (score > bestScore) {
                bestScore = score;
                bestAgent = candidate;
            }
        }

        return bestAgent;
    }

    /// @inheritdoc IFallbackPool
    function activateFallback(bytes32 taskId, address fallbackAgent)
        external
        override
        onlyCairnCore
    {
        FallbackAgent storage agent = _agents[fallbackAgent];
        if (!agent.registered) revert NotRegistered();
        if (agent.activeTaskCount >= agent.maxConcurrentTasks) revert AtMaxCapacity();

        agent.activeTaskCount++;
        agent.lastActive = block.timestamp;

        emit FallbackActivated(taskId, fallbackAgent);
    }

    /// @inheritdoc IFallbackPool
    function completeFallbackTask(
        bytes32 taskId,
        address fallbackAgent,
        bool success,
        uint256 checkpointsCommitted
    ) external override onlyCairnCore nonReentrant {
        FallbackAgent storage agent = _agents[fallbackAgent];
        if (!agent.registered) revert NotRegistered();

        agent.activeTaskCount--;
        agent.lastActive = block.timestamp;

        if (success) {
            agent.completedTasks++;
        } else {
            agent.failedTasks++;
            // Slash based on checkpoints (PRD-04 Section 2.5)
            _handleFailure(fallbackAgent, checkpointsCommitted, taskId);
        }

        emit FallbackCompleted(taskId, fallbackAgent, success);
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IFallbackPool
    function getAgent(address agent) external view override returns (FallbackAgent memory) {
        return _agents[agent];
    }

    /// @inheritdoc IFallbackPool
    function getMinStake(uint256 escrowAmount) public pure override returns (uint256) {
        return (escrowAmount * minStakePercent) / PRECISION;
    }

    /// @notice Get all registered agents
    function getAllAgents() external view returns (address[] memory) {
        return _agentList;
    }

    /// @notice Get agents for a task type
    function getTaskTypeAgents(bytes32 taskType) external view returns (address[] memory) {
        return _taskTypeAgents[taskType];
    }

    // ═══════════════════════════════════════════════════════════════
    // INTERNAL FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Check if agent is eligible for selection
    function _isEligible(FallbackAgent storage agent, uint256 requiredStake)
        internal
        view
        returns (bool)
    {
        // Must have enough stake
        if (agent.stake < requiredStake) return false;

        // Must not be at max capacity
        if (agent.activeTaskCount >= agent.maxConcurrentTasks) return false;

        // Must meet reputation threshold
        if (agent.reputation < minReputation) return false;

        return true;
    }

    /// @notice Calculate selection score (PRD-04 Section 2.4)
    /// @dev score = (success × 0.4) + (reputation × 0.3) + (stake × 0.2) + (availability × 0.1)
    function _calculateScore(FallbackAgent storage agent, uint256 escrowAmount)
        internal
        view
        returns (uint256)
    {
        uint256 totalTasks = agent.completedTasks + agent.failedTasks;

        // Success rate (40%)
        uint256 successRate;
        if (totalTasks > 0) {
            successRate = (agent.completedTasks * PRECISION) / totalTasks;
        } else {
            successRate = 50; // Default 50% for new agents
        }
        uint256 successScore = successRate * 40 / PRECISION;

        // Reputation (30%)
        uint256 reputationScore = agent.reputation * 30 / PRECISION;

        // Stake ratio (20%) - capped at 2x required
        uint256 requiredStake = getMinStake(escrowAmount);
        uint256 stakeRatio = requiredStake > 0
            ? (agent.stake * PRECISION) / requiredStake
            : PRECISION;
        if (stakeRatio > 200) stakeRatio = 200; // Cap at 2x
        uint256 stakeScore = stakeRatio * 20 / PRECISION;

        // Availability (10%)
        uint256 utilization = agent.maxConcurrentTasks > 0
            ? (agent.activeTaskCount * PRECISION) / agent.maxConcurrentTasks
            : 0;
        uint256 availabilityScore = (PRECISION - utilization) * 10 / PRECISION;

        return successScore + reputationScore + stakeScore + availabilityScore;
    }

    /// @notice Handle fallback failure and slashing (PRD-04 Section 2.5)
    function _handleFailure(
        address fallbackAgent,
        uint256 checkpointsCommitted,
        bytes32 taskId
    ) internal {
        FallbackAgent storage agent = _agents[fallbackAgent];

        // Check failure rate
        uint256 totalTasks = agent.completedTasks + agent.failedTasks;
        if (totalTasks > 5) {
            uint256 failureRate = (agent.failedTasks * PRECISION) / totalTasks;
            if (failureRate > MAX_FAILURE_RATE) {
                // Auto-slash 10% for high failure rate
                uint256 slashAmount = agent.stake / 10;
                _slash(fallbackAgent, slashAmount, feeRecipient, "High failure rate");
            }
        }

        // Slash based on checkpoints committed (PRD-04 Section 2.5)
        if (checkpointsCommitted == 0) {
            // Complete failure: 100% slash (up to reasonable limit)
            uint256 slashAmount = agent.stake > 0 ? agent.stake / 4 : 0;
            _slash(fallbackAgent, slashAmount, feeRecipient, "Zero checkpoints failure");
        }
        // Note: For partial failure (some checkpoints), we don't auto-slash
        // This is handled by the arbiter if disputed
    }

    /// @notice Execute slashing
    function _slash(
        address agent,
        uint256 amount,
        address recipient,
        string memory reason
    ) internal {
        FallbackAgent storage agentData = _agents[agent];

        uint256 slashAmount = amount > agentData.stake ? agentData.stake : amount;
        if (slashAmount == 0) return;

        agentData.stake -= slashAmount;

        (bool success, ) = recipient.call{value: slashAmount}("");
        require(success, "Slash transfer failed");

        emit AgentSlashed(agent, slashAmount, recipient, reason);
    }

    /// @notice Get agent reputation (mock - replace with ERC-8004)
    function _getReputation(address agent) internal view returns (uint256) {
        uint256 mockRep = _mockReputations[agent];
        // Default to 70 for testing if not set
        return mockRep > 0 ? mockRep : 70;
    }

    /// @notice Remove agent from task type list
    function _removeFromTaskType(bytes32 taskType, address agent) internal {
        address[] storage list = _taskTypeAgents[taskType];
        for (uint256 i = 0; i < list.length; i++) {
            if (list[i] == agent) {
                list[i] = list[list.length - 1];
                list.pop();
                break;
            }
        }
    }

    /// @notice Remove agent from main list
    function _removeFromAgentList(address agent) internal {
        for (uint256 i = 0; i < _agentList.length; i++) {
            if (_agentList[i] == agent) {
                _agentList[i] = _agentList[_agentList.length - 1];
                _agentList.pop();
                break;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN (for testing)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Set mock reputation for testing
    function setMockReputation(address agent, uint256 reputation) external onlyOwner {
        // In production, remove this and use ERC-8004
        _mockReputations[agent] = reputation;
    }

    /// @notice Update CairnCore address
    function setCairnCore(address _cairnCore) external onlyOwner {
        cairnCore = _cairnCore;
    }

    /// @notice Update fee recipient
    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        if (_feeRecipient == address(0)) revert ZeroAddress();
        feeRecipient = _feeRecipient;
    }
}
