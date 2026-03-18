// SPDX-License-Identifier: BSL-1.1
pragma solidity 0.8.24;

interface ICairnTaskMVP {
    enum State { RUNNING, FAILED, RECOVERING, RESOLVED }

    event TaskSubmitted(bytes32 indexed taskId, address indexed operator, address primaryAgent, address fallbackAgent, uint256 escrow);
    event CheckpointCommitted(bytes32 indexed taskId, uint256 index, bytes32 cid, address agent);
    event HeartbeatReceived(bytes32 indexed taskId, uint256 timestamp);
    event TaskFailed(bytes32 indexed taskId, string reason);
    event FallbackAssigned(bytes32 indexed taskId, address fallbackAgent);
    event TaskCompleted(bytes32 indexed taskId, address completedBy);
    event TaskResolved(bytes32 indexed taskId, uint256 primaryShare, uint256 fallbackShare, uint256 protocolFee);

    error InsufficientEscrow(uint256 required, uint256 provided);
    error InvalidAddress();
    error InvalidDeadline();
    error InvalidHeartbeatInterval(uint256 minimum, uint256 provided);
    error InvalidCID();
    error CheckpointGap(uint256 expected, uint256 provided);
    error Unauthorized();
    error InvalidState(State expected, State actual);
    error NotStale();
    error AlreadySettled();
    error TaskNotFound();
    error TransferFailed();
    error DeadlineExceeded();
    error DeadlineNotReached();

    function submitTask(address primaryAgent, address fallbackAgent, bytes32 specHash, uint256 heartbeatInterval, uint256 deadline) external payable returns (bytes32 taskId);
    function commitCheckpoint(bytes32 taskId, bytes32 cid) external;
    function heartbeat(bytes32 taskId) external;
    function checkLiveness(bytes32 taskId) external;
    function completeTask(bytes32 taskId) external;
    function settle(bytes32 taskId) external;
    function getTask(bytes32 taskId) external view returns (State state, address operator, address primaryAgent, address fallbackAgent, uint256 escrow, uint256 primaryCheckpoints, uint256 fallbackCheckpoints, uint256 lastHeartbeat, uint256 deadline);
    function getCheckpoints(bytes32 taskId) external view returns (bytes32[] memory cids);
    function isStale(bytes32 taskId) external view returns (bool);
    function protocolFeeBps() external view returns (uint256);
    function minEscrow() external view returns (uint256);
    function minHeartbeatInterval() external view returns (uint256);
}
