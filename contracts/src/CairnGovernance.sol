// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity 0.8.24;

import {IGovernance} from "./interfaces/IGovernance.sol";

/// @title CairnGovernance - Protocol governance with timelock
/// @author CAIRN Protocol
/// @notice Manages protocol parameters with timelock protection
/// @dev Based on PRD-06 Section 3
///
/// Governance Phases:
///   1. Launch: Single admin key. For production this admin SHOULD be a
///      TimelockController / multisig (Safe), set at deploy — the two-step
///      transferAdmin/acceptAdmin handoff exists for exactly this. `execute()`
///      itself imposes no delay, so the timelock/multisig admin is the enforcement
///      point for privileged calls (H-7).
///   2. Multi-sig / timelock admin (external)
///   3. Token governance (future)
///
/// @dev PARAMETER STORE STATUS (H-7): the timelocked parameter store below
///      (proposeParameter/executeProposal + `getParameter`) is NOT yet read by the
///      protocol contracts, which currently use compile-time `constant` values.
///      Changing a parameter here therefore does NOT change on-chain behavior. It is
///      retained as forward-looking governance scaffolding; wiring consumers to read
///      these values (or making the constants formally immutable and removing this
///      store) is a tracked follow-up. Do not rely on it to tune live parameters.
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

    /// @notice Proposed next admin (H-7: two-step transfer prevents an
    ///         irrecoverable transfer to a wrong/dead address).
    address public pendingAdmin;

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

    /// @notice Emitted when a two-step admin transfer is initiated (H-7)
    event AdminTransferStarted(address indexed currentAdmin, address indexed pendingAdmin);

    /// @notice Caller is not the pending admin
    error NotPendingAdmin();

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
    /// @notice Begin an admin transfer (H-7). The new admin must call
    ///         acceptAdmin() to take effect, so a wrong/dead address cannot
    ///         irrecoverably capture governance. Enables safely handing admin to
    ///         a TimelockController / multisig (the recommended production admin).
    function transferAdmin(address newAdmin) external override onlyAdmin {
        if (newAdmin == address(0)) revert ZeroAddress();
        pendingAdmin = newAdmin;
        emit AdminTransferStarted(admin, newAdmin);
    }

    /// @notice Complete an admin transfer; callable only by the pending admin,
    ///         proving the new address is live and controllable.
    function acceptAdmin() external {
        if (msg.sender != pendingAdmin) revert NotPendingAdmin();
        address oldAdmin = admin;
        admin = pendingAdmin;
        pendingAdmin = address(0);
        emit AdminTransferred(oldAdmin, admin);
    }

    // ═══════════════════════════════════════════════════════════════
    // EXECUTOR
    // ═══════════════════════════════════════════════════════════════

    /// @notice Emitted when governance relays a call to another contract.
    event Executed(address indexed target, bytes data, bytes result);

    /// @notice Relay an admin-authorized call to another contract so that this
    ///         governance contract is `msg.sender`. Required to reach the
    ///         `onlyGovernance` functions on CairnCore (e.g. `setThreeTierRouting`,
    ///         `setContracts`, `pause`), which check `msg.sender == address(governance)`.
    /// @dev Immediate `onlyAdmin` execution. For mainnet, route sensitive calls
    ///      through the 48h parameter timelock or a multisig admin. Reverts bubble
    ///      up the target's revert reason.
    /// @param target The contract to call (e.g. CairnCore).
    /// @param data ABI-encoded calldata for the target function.
    /// @return result The target's return data.
    function execute(address target, bytes calldata data)
        external
        onlyAdmin
        returns (bytes memory result)
    {
        if (target == address(0)) revert ZeroAddress();

        (bool ok, bytes memory ret) = target.call(data);
        if (!ok) {
            // Bubble up the target's revert reason.
            assembly {
                revert(add(ret, 0x20), mload(ret))
            }
        }

        emit Executed(target, data, ret);
        return ret;
    }
}
