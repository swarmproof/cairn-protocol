// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

import { ICairnTaskMVP } from "./interfaces/ICairnTaskMVP.sol";
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";

contract CairnTaskMVP is ICairnTaskMVP, ReentrancyGuard, Ownable {
    uint256 public constant PROTOCOL_FEE_BPS = 50;
    uint256 public constant MIN_ESCROW = 0.001 ether;
    uint256 public constant MIN_HEARTBEAT_INTERVAL = 30;

    struct Task {
        State state;
        address operator;
        address primaryAgent;
        address fallbackAgent;
        uint256 escrow;
        uint256 heartbeatInterval;
        uint256 lastHeartbeat;
        uint256 deadline;
        bytes32 specHash;
        bytes32[] checkpointCIDs;
        uint256 primaryCheckpoints;
        uint256 fallbackCheckpoints;
        bool settled;
    }

    mapping(bytes32 => Task) private tasks;
    mapping(address => uint256) private operatorNonces;
    address public feeRecipient;

    constructor(address _owner, address _feeRecipient) Ownable(_owner) {
        if (_feeRecipient == address(0)) revert InvalidAddress();
        feeRecipient = _feeRecipient;
    }

    modifier taskExists(bytes32 taskId) {
        if (tasks[taskId].operator == address(0)) revert TaskNotFound();
        _;
    }

    modifier onlyActiveAgent(bytes32 taskId) {
        Task storage task = tasks[taskId];
        if (task.state == State.RUNNING) {
            if (msg.sender != task.primaryAgent) revert Unauthorized();
        } else if (task.state == State.RECOVERING) {
            if (msg.sender != task.fallbackAgent) revert Unauthorized();
        } else {
            revert InvalidState(State.RUNNING, task.state);
        }
        _;
    }

    function submitTask(address primaryAgent, address fallbackAgent, bytes32 specHash, uint256 heartbeatInterval, uint256 deadline) external payable returns (bytes32 taskId) {
        if (primaryAgent == address(0) || fallbackAgent == address(0)) revert InvalidAddress();
        if (msg.value < MIN_ESCROW) revert InsufficientEscrow(MIN_ESCROW, msg.value);
        if (heartbeatInterval < MIN_HEARTBEAT_INTERVAL) revert InvalidHeartbeatInterval(MIN_HEARTBEAT_INTERVAL, heartbeatInterval);
        if (deadline <= block.timestamp) revert InvalidDeadline();

        uint256 nonce = operatorNonces[msg.sender]++;
        taskId = keccak256(abi.encodePacked(msg.sender, nonce, block.timestamp));

        Task storage task = tasks[taskId];
        task.state = State.RUNNING;
        task.operator = msg.sender;
        task.primaryAgent = primaryAgent;
        task.fallbackAgent = fallbackAgent;
        task.escrow = msg.value;
        task.heartbeatInterval = heartbeatInterval;
        task.lastHeartbeat = block.timestamp;
        task.deadline = deadline;
        task.specHash = specHash;

        emit TaskSubmitted(taskId, msg.sender, primaryAgent, fallbackAgent, msg.value);
    }

    function commitCheckpoint(bytes32 taskId, bytes32 cid) external taskExists(taskId) onlyActiveAgent(taskId) {
        Task storage task = tasks[taskId];
        if (block.timestamp > task.deadline) revert DeadlineExceeded();
        if (cid == bytes32(0)) revert InvalidCID();

        uint256 index = task.checkpointCIDs.length;
        task.checkpointCIDs.push(cid);
        if (msg.sender == task.primaryAgent) { task.primaryCheckpoints++; } else { task.fallbackCheckpoints++; }
        task.lastHeartbeat = block.timestamp;

        emit CheckpointCommitted(taskId, index, cid, msg.sender);
    }

    function heartbeat(bytes32 taskId) external taskExists(taskId) onlyActiveAgent(taskId) {
        Task storage task = tasks[taskId];
        if (block.timestamp > task.deadline) revert DeadlineExceeded();
        task.lastHeartbeat = block.timestamp;
        emit HeartbeatReceived(taskId, block.timestamp);
    }

    function checkLiveness(bytes32 taskId) external taskExists(taskId) {
        Task storage task = tasks[taskId];
        if (task.state != State.RUNNING) revert InvalidState(State.RUNNING, task.state);
        if (!_isStale(task)) revert NotStale();

        task.state = State.FAILED;
        emit TaskFailed(taskId, "HEARTBEAT_MISS");

        task.state = State.RECOVERING;
        task.lastHeartbeat = block.timestamp;
        emit FallbackAssigned(taskId, task.fallbackAgent);
    }

    function completeTask(bytes32 taskId) external taskExists(taskId) onlyActiveAgent(taskId) {
        Task storage task = tasks[taskId];
        if (block.timestamp > task.deadline) revert DeadlineExceeded();
        task.state = State.RESOLVED;
        emit TaskCompleted(taskId, msg.sender);
    }

    function settle(bytes32 taskId) external nonReentrant taskExists(taskId) {
        Task storage task = tasks[taskId];
        if (task.settled) revert AlreadySettled();
        if (task.state != State.RESOLVED && block.timestamp <= task.deadline) revert InvalidState(State.RESOLVED, task.state);
        if (task.state != State.RESOLVED) task.state = State.RESOLVED;

        task.settled = true;
        uint256 escrow = task.escrow;
        uint256 totalCheckpoints = task.primaryCheckpoints + task.fallbackCheckpoints;
        uint256 protocolFee; uint256 primaryShare; uint256 fallbackShare;

        if (totalCheckpoints == 0) {
            _safeTransfer(task.operator, escrow);
        } else {
            protocolFee = (escrow * PROTOCOL_FEE_BPS) / 10000;
            uint256 distributable = escrow - protocolFee;
            primaryShare = (distributable * task.primaryCheckpoints) / totalCheckpoints;
            fallbackShare = distributable - primaryShare;
            if (primaryShare > 0) _safeTransfer(task.primaryAgent, primaryShare);
            if (fallbackShare > 0) _safeTransfer(task.fallbackAgent, fallbackShare);
            if (protocolFee > 0) _safeTransfer(feeRecipient, protocolFee);
        }
        emit TaskResolved(taskId, primaryShare, fallbackShare, protocolFee);
    }

    function getTask(bytes32 taskId) external view taskExists(taskId) returns (State state, address operator, address primaryAgent, address fallbackAgent, uint256 escrow, uint256 primaryCheckpoints, uint256 fallbackCheckpoints, uint256 lastHeartbeat, uint256 deadline) {
        Task storage task = tasks[taskId];
        return (task.state, task.operator, task.primaryAgent, task.fallbackAgent, task.escrow, task.primaryCheckpoints, task.fallbackCheckpoints, task.lastHeartbeat, task.deadline);
    }

    function getCheckpoints(bytes32 taskId) external view taskExists(taskId) returns (bytes32[] memory cids) {
        return tasks[taskId].checkpointCIDs;
    }

    function isStale(bytes32 taskId) external view taskExists(taskId) returns (bool) {
        return _isStale(tasks[taskId]);
    }

    function protocolFeeBps() external pure returns (uint256) { return PROTOCOL_FEE_BPS; }
    function minEscrow() external pure returns (uint256) { return MIN_ESCROW; }
    function minHeartbeatInterval() external pure returns (uint256) { return MIN_HEARTBEAT_INTERVAL; }

    function setFeeRecipient(address _feeRecipient) external onlyOwner {
        if (_feeRecipient == address(0)) revert InvalidAddress();
        feeRecipient = _feeRecipient;
    }

    function _isStale(Task storage task) internal view returns (bool) {
        return block.timestamp > task.lastHeartbeat + task.heartbeatInterval;
    }

    function _safeTransfer(address to, uint256 amount) internal {
        (bool success, ) = to.call{ value: amount }("");
        if (!success) revert TransferFailed();
    }
}
