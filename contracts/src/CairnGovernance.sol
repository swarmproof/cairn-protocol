// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import {IGovernance} from "./interfaces/IGovernance.sol";

/// @title CairnGovernance - Protocol governance with timelock
/// @author CAIRN Protocol
/// @notice Manages protocol parameters with timelock protection
/// @dev Based on PRD-06 Section 3
///
/// Governance Phases:
///   1. Launch: Single admin key (this contract)
///   2. Multi-sig: Transfer admin to multi-sig (external)
///   3. Token: Token governance (future)
///
/// All parameter changes go through a 48-hour timelock.
contract CairnGovernance is IGovernance {
    // ═══════════════════════════════════════════════════════════════
    // CONSTANTS - Parameter Keys
    // ═══════════════════════════════════════════════════════════════

    bytes32 public constant override PROTOCOL_FEE_BPS = keccak256("PROTOCOL_FEE_BPS");
    bytes32 public constant override ARBITER_FEE_BPS = keccak256("ARBITER_FEE_BPS");
    bytes32 public constant override MIN_REPUTATION = keccak256("MIN_REPUTATION");
    bytes32 public constant override MIN_STAKE_PERCENT = keccak256("MIN_STAKE_PERCENT");
    bytes32 public constant override MIN_ARBITER_STAKE_PERCENT = keccak256("MIN_ARBITER_STAKE_PERCENT");
    bytes32 public constant override RECOVERY_THRESHOLD = keccak256("RECOVERY_THRESHOLD");
    bytes32 public constant override DISPUTE_TIMEOUT = keccak256("DISPUTE_TIMEOUT");
    bytes32 public constant override APPEAL_WINDOW = keccak256("APPEAL_WINDOW");
    bytes32 public constant override MIN_HEARTBEAT_INTERVAL = keccak256("MIN_HEARTBEAT_INTERVAL");

    // ═══════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════

    /// @notice Current admin address
    address public override admin;

    /// @notice Timelock duration for parameter changes (48 hours)
    uint256 public constant override timelockDuration = 48 hours;

    /// @notice Protocol pause state
    bool public override isPaused;

    /// @notice Current parameter values
    mapping(bytes32 => uint256) private _parameters;

    /// @notice Pending parameter proposals
    struct Proposal {
        uint256 value;
        uint256 executeAfter;
        bool exists;
    }
    mapping(bytes32 => Proposal) private _proposals;

    /// @notice Parameter validation ranges
    struct Range {
        uint256 min;
        uint256 max;
    }
    mapping(bytes32 => Range) private _ranges;

    // ═══════════════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════

    constructor(address _admin) {
        if (_admin == address(0)) revert ZeroAddress();
        admin = _admin;

        // Initialize default values (PRD-06 Section 3.2)
        _parameters[PROTOCOL_FEE_BPS] = 50;           // 0.5%
        _parameters[ARBITER_FEE_BPS] = 300;           // 3%
        _parameters[MIN_REPUTATION] = 50;              // 50/100
        _parameters[MIN_STAKE_PERCENT] = 10;           // 10%
        _parameters[MIN_ARBITER_STAKE_PERCENT] = 15;   // 15%
        _parameters[RECOVERY_THRESHOLD] = 0.3e18;      // 30%
        _parameters[DISPUTE_TIMEOUT] = 7 days;
        _parameters[APPEAL_WINDOW] = 48 hours;
        _parameters[MIN_HEARTBEAT_INTERVAL] = 30;      // 30 seconds

        // Set validation ranges
        _ranges[PROTOCOL_FEE_BPS] = Range(0, 500);           // 0-5%
        _ranges[ARBITER_FEE_BPS] = Range(100, 1000);         // 1-10%
        _ranges[MIN_REPUTATION] = Range(0, 100);
        _ranges[MIN_STAKE_PERCENT] = Range(1, 50);
        _ranges[MIN_ARBITER_STAKE_PERCENT] = Range(5, 50);
        _ranges[RECOVERY_THRESHOLD] = Range(0.1e18, 0.9e18);
        _ranges[DISPUTE_TIMEOUT] = Range(1 days, 30 days);
        _ranges[APPEAL_WINDOW] = Range(24 hours, 72 hours);
        _ranges[MIN_HEARTBEAT_INTERVAL] = Range(10, 300);
    }

    // ═══════════════════════════════════════════════════════════════
    // MODIFIERS
    // ═══════════════════════════════════════════════════════════════

    modifier onlyAdmin() {
        if (msg.sender != admin) revert NotAdmin();
        _;
    }

    // ═══════════════════════════════════════════════════════════════
    // PARAMETER MANAGEMENT
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IGovernance
    function proposeParameter(bytes32 key, uint256 value) external override onlyAdmin {
        Range memory range = _ranges[key];

        // Validate range (skip validation if range not set)
        if (range.max > 0 && (value < range.min || value > range.max)) {
            revert ValueOutOfRange(key, value, range.min, range.max);
        }

        _proposals[key] = Proposal({
            value: value,
            executeAfter: block.timestamp + timelockDuration,
            exists: true
        });

        emit ParameterProposed(key, value, block.timestamp + timelockDuration);
    }

    /// @inheritdoc IGovernance
    function executeProposal(bytes32 key) external override onlyAdmin {
        Proposal storage proposal = _proposals[key];

        if (!proposal.exists) revert ProposalNotFound();
        if (block.timestamp < proposal.executeAfter) {
            revert TimelockNotExpired(proposal.executeAfter - block.timestamp);
        }

        uint256 oldValue = _parameters[key];
        uint256 newValue = proposal.value;

        _parameters[key] = newValue;
        delete _proposals[key];

        emit ParameterUpdated(key, oldValue, newValue);
    }

    /// @inheritdoc IGovernance
    function cancelProposal(bytes32 key) external override onlyAdmin {
        if (!_proposals[key].exists) revert ProposalNotFound();
        delete _proposals[key];
    }

    /// @inheritdoc IGovernance
    function getParameter(bytes32 key) external view override returns (uint256) {
        return _parameters[key];
    }

    /// @inheritdoc IGovernance
    function getProposal(bytes32 key) external view override returns (uint256 newValue, uint256 executeAfter) {
        Proposal storage proposal = _proposals[key];
        if (!proposal.exists) revert ProposalNotFound();
        return (proposal.value, proposal.executeAfter);
    }

    // ═══════════════════════════════════════════════════════════════
    // EMERGENCY CONTROLS
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IGovernance
    function emergencyPause(string calldata reason) external override onlyAdmin {
        isPaused = true;
        emit EmergencyPaused(msg.sender, reason);
    }

    /// @inheritdoc IGovernance
    function emergencyUnpause() external override onlyAdmin {
        isPaused = false;
        emit EmergencyUnpaused(msg.sender);
    }

    // ═══════════════════════════════════════════════════════════════
    // ADMIN
    // ═══════════════════════════════════════════════════════════════

    /// @inheritdoc IGovernance
    function transferAdmin(address newAdmin) external override onlyAdmin {
        if (newAdmin == address(0)) revert ZeroAddress();

        address oldAdmin = admin;
        admin = newAdmin;

        emit AdminTransferred(oldAdmin, newAdmin);
    }
}
