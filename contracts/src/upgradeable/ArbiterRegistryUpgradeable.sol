// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {IArbiterRegistry} from "../interfaces/IArbiterRegistry.sol";
import {ICairnTypes} from "../interfaces/ICairnTypes.sol";
import {Initializable} from "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import {UUPSUpgradeable} from "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {OwnableUpgradeable} from "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";

/// @title ArbiterRegistryUpgradeable - UUPS Upgradeable dispute resolution
/// @author CAIRN Protocol
/// @notice Manages arbiter registration, rulings, and appeals (Upgradeable)
/// @dev Based on PRD-05, implements UUPS proxy pattern from PRD-06
///
/// Economics:
///   - Arbiter fee: 3% of dispute escrow
///   - Min stake: 15% of max ruleable dispute
///
/// Slashing:
///   - Ruling overturned → 50% stake slashed
///
/// Dispute Lifecycle:
///   DISPUTED → (7 days) → Arbiter rules OR Timeout
///   After ruling → (48h appeal window) → RESOLVED
contract ArbiterRegistryUpgradeable is
    IArbiterRegistry,
    Initializable,
    UUPSUpgradeable,
    ReentrancyGuard,
    OwnableUpgradeable
{
    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS (PRD-05 Section 3.4)
    // ═══════════════════════════════════════════════════════════════

    /// @notice Arbiter fee in basis points (3%)
    uint256 public constant override arbiterFeeBps = 300;

    /// @notice Appeal window duration (48 hours)
    uint256 public constant override appealWindow = 48 hours;

    /// @notice Max allowed overturn rate (20%)
    uint256 public constant override maxOverturnRate = 20;

    /// @notice Minimum arbiter stake (0.15 ETH default)
    uint256 public constant override minArbiterStake = 0.15 ether;

    /// @notice Percentage precision
    uint256 private constant PRECISION = 100;

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Registered arbiters
    mapping(address => Arbiter) private _arbiters;

    /// @notice List of all arbiter addresses
    address[] private _arbiterList;

    /// @notice Stored rulings by task ID
    mapping(bytes32 => StoredRuling) private _rulings;

    /// @notice CairnCore contract address
    address public cairnCore;

    /// @notice Governance address for appeals
    address public governance;

    /// @notice Fee recipient for slashed funds
    address public feeRecipient;

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
    /// @param _governance Governance contract address
    /// @param _feeRecipient Fee recipient address
    /// @param _owner Initial owner address
    function initialize(
        address _cairnCore,
        address _governance,
        address _feeRecipient,
        address _owner
    ) external initializer {
        if (_governance == address(0)) revert ZeroAddress();
        if (_feeRecipient == address(0)) revert ZeroAddress();

        __Ownable_init(_owner);

        cairnCore = _cairnCore;
        governance = _governance;
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

    modifier onlyGovernance() {
        if (msg.sender != governance) revert NotGovernance();
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // REGISTRATION (PRD-05 Section 3.1)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IArbiterRegistry
    function registerArbiter(bytes32[] calldata domains) external payable override {
        if (_arbiters[msg.sender].registered) revert AlreadyRegistered();
        if (msg.value < minArbiterStake) {
            revert InsufficientStake(minArbiterStake, msg.value);
        }
        if (domains.length == 0) revert ZeroAddress(); // Reusing error for "no domains"

        _arbiters[msg.sender] = Arbiter({
            registered: true,
            stake: msg.value,
            expertiseDomains: domains,
            rulingCount: 0,
            overturnedCount: 0,
            earnings: 0,
            lastActive: block.timestamp
        });

        _arbiterList.push(msg.sender);

        emit ArbiterRegistered(msg.sender, domains, msg.value);
    }

    /// @inheritdoc IArbiterRegistry
    function addStake() external payable override {
        Arbiter storage arbiter = _arbiters[msg.sender];
        if (!arbiter.registered) revert NotRegistered();

        arbiter.stake += msg.value;
        emit StakeAdded(msg.sender, msg.value, arbiter.stake);
    }

    /// @inheritdoc IArbiterRegistry
    function withdrawStake(uint256 amount) external override nonReentrant {
        Arbiter storage arbiter = _arbiters[msg.sender];
        if (!arbiter.registered) revert NotRegistered();
        if (arbiter.stake < amount) {
            revert InsufficientStake(amount, arbiter.stake);
        }
        // Ensure minimum stake maintained
        if (arbiter.stake - amount < minArbiterStake && amount != arbiter.stake) {
            revert InsufficientStake(minArbiterStake, arbiter.stake - amount);
        }

        arbiter.stake -= amount;

        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
    }

    /// @inheritdoc IArbiterRegistry
    function deregisterArbiter() external override nonReentrant {
        Arbiter storage arbiter = _arbiters[msg.sender];
        if (!arbiter.registered) revert NotRegistered();

        uint256 stakeToReturn = arbiter.stake;

        // Remove from list
        _removeFromList(msg.sender);

        // Clear data
        delete _arbiters[msg.sender];

        // Return stake
        if (stakeToReturn > 0) {
            (bool success, ) = msg.sender.call{value: stakeToReturn}("");
            require(success, "Transfer failed");
        }

        emit ArbiterDeregistered(msg.sender, stakeToReturn);
    }

    // ═══════════════════════════════════════════════════════════════
    // RULING (PRD-05 Section 3.3)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IArbiterRegistry
    function rule(bytes32 taskId, ICairnTypes.Ruling calldata ruling) external override {
        // This is a convenience function - actual execution goes through CairnCore
        // Arbiters call CairnCore.resolveDispute() which then calls executeRuling()
        revert("Use CairnCore.resolveDispute()");
    }

    /// @inheritdoc IArbiterRegistry
    function executeRuling(
        bytes32 taskId,
        ICairnTypes.Ruling calldata ruling,
        address arbiter,
        uint256 escrowAmount,
        address primaryAgent,
        address fallbackAgent,
        bytes32 taskType
    ) external override onlyCairnCore returns (uint256 arbiterFee) {
        // Validate arbiter eligibility
        if (!isEligible(arbiter, escrowAmount, primaryAgent, fallbackAgent, taskType)) {
            revert NotEligibleForDispute();
        }

        // Check not already ruled
        if (_rulings[taskId].arbiter != address(0)) {
            revert AlreadyRuled();
        }

        // Calculate arbiter fee
        arbiterFee = (escrowAmount * arbiterFeeBps) / 10000;

        // Store ruling
        _rulings[taskId] = StoredRuling({
            arbiter: arbiter,
            outcome: ruling.outcome,
            agentShare: ruling.agentShare,
            rationaleCID: ruling.rationaleCID,
            timestamp: block.timestamp,
            appealed: false,
            overturned: false
        });

        // Update arbiter stats
        Arbiter storage arbiterData = _arbiters[arbiter];
        arbiterData.rulingCount++;
        arbiterData.earnings += arbiterFee;
        arbiterData.lastActive = block.timestamp;

        // Pay arbiter fee
        (bool success, ) = arbiter.call{value: arbiterFee}("");
        require(success, "Arbiter fee transfer failed");

        emit DisputeRuled(
            taskId,
            arbiter,
            ruling.outcome,
            ruling.agentShare,
            arbiterFee
        );

        return arbiterFee;
    }

    // ═══════════════════════════════════════════════════════════════
    // APPEALS (PRD-05 Section 3.5)
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IArbiterRegistry
    function overturnRuling(bytes32 taskId, ICairnTypes.Ruling calldata newRuling)
        external
        override
        onlyGovernance
        nonReentrant
    {
        StoredRuling storage storedRuling = _rulings[taskId];

        if (storedRuling.arbiter == address(0)) revert DisputeNotFound();
        if (storedRuling.overturned) revert AlreadyRuled();

        // Check within appeal window
        if (block.timestamp > storedRuling.timestamp + appealWindow) {
            revert AppealWindowExpired();
        }

        address originalArbiter = storedRuling.arbiter;
        Arbiter storage arbiterData = _arbiters[originalArbiter];

        // Slash 50% of stake
        uint256 slashAmount = arbiterData.stake / 2;
        arbiterData.stake -= slashAmount;
        arbiterData.overturnedCount++;

        // Mark as overturned
        storedRuling.overturned = true;

        // Update ruling
        storedRuling.outcome = newRuling.outcome;
        storedRuling.agentShare = newRuling.agentShare;
        storedRuling.rationaleCID = newRuling.rationaleCID;

        // Send slashed funds to fee recipient
        (bool success, ) = feeRecipient.call{value: slashAmount}("");
        require(success, "Slash transfer failed");

        emit RulingOverturned(
            taskId,
            originalArbiter,
            slashAmount,
            newRuling.outcome
        );
    }

    // ═══════════════════════════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IArbiterRegistry
    function getArbiter(address arbiter) external view override returns (Arbiter memory) {
        return _arbiters[arbiter];
    }

    /// @inheritdoc IArbiterRegistry
    function getRuling(bytes32 taskId) external view override returns (StoredRuling memory) {
        return _rulings[taskId];
    }

    /// @inheritdoc IArbiterRegistry
    function isEligible(
        address arbiter,
        uint256 escrowAmount,
        address primaryAgent,
        address fallbackAgent,
        bytes32 taskType
    ) public view override returns (bool) {
        Arbiter storage a = _arbiters[arbiter];

        // Must be registered
        if (!a.registered) return false;

        // Must have adequate stake (15% of dispute value)
        uint256 requiredStake = (escrowAmount * 15) / PRECISION;
        if (requiredStake < minArbiterStake) requiredStake = minArbiterStake;
        if (a.stake < requiredStake) return false;

        // Must not have high overturn rate
        if (a.rulingCount >= 10) {
            uint256 overturnRate = (a.overturnedCount * PRECISION) / a.rulingCount;
            if (overturnRate > maxOverturnRate) return false;
        }

        // Must not be the agent in question (conflict of interest)
        if (arbiter == primaryAgent || arbiter == fallbackAgent) return false;

        // Domain expertise check (simplified: check first domain)
        // In production, implement proper domain matching
        bool hasDomainMatch = false;
        bytes32 taskDomain = _extractDomain(taskType);
        for (uint256 i = 0; i < a.expertiseDomains.length; i++) {
            if (a.expertiseDomains[i] == taskDomain || a.expertiseDomains[i] == taskType) {
                hasDomainMatch = true;
                break;
            }
        }
        // For now, don't require domain match (too restrictive for early adoption)
        // if (!hasDomainMatch) return false;

        return true;
    }

    /// @notice Get all registered arbiters
    function getAllArbiters() external view returns (address[] memory) {
        return _arbiterList;
    }

    /// @notice Check if appeal window is active for a ruling
    function isAppealWindowActive(bytes32 taskId) external view returns (bool) {
        StoredRuling storage ruling = _rulings[taskId];
        if (ruling.arbiter == address(0)) return false;
        if (ruling.overturned) return false;
        return block.timestamp <= ruling.timestamp + appealWindow;
    }

    // ═══════════════════════════════════════════════════════════════
    // INTERNAL FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /// @notice Extract domain from task type (first part before .)
    function _extractDomain(bytes32 taskType) internal pure returns (bytes32) {
        // Simple extraction: return the task type as-is
        // In production, parse "domain.operation" format
        return taskType;
    }

    /// @notice Remove arbiter from list
    function _removeFromList(address arbiter) internal {
        for (uint256 i = 0; i < _arbiterList.length; i++) {
            if (_arbiterList[i] == arbiter) {
                _arbiterList[i] = _arbiterList[_arbiterList.length - 1];
                _arbiterList.pop();
                break;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN
    // ═══════════════════════════════════════════════════════════════

    /// @notice Update CairnCore address
    function setCairnCore(address _cairnCore) external onlyOwner {
        cairnCore = _cairnCore;
    }

    /// @notice Update governance address
    function setGovernance(address _governance) external onlyOwner {
        if (_governance == address(0)) revert ZeroAddress();
        governance = _governance;
    }

    /// @notice Update fee recipient
    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        if (_feeRecipient == address(0)) revert ZeroAddress();
        feeRecipient = _feeRecipient;
    }

    /// @notice Receive ETH for arbiter fees
    receive() external payable {}
}
