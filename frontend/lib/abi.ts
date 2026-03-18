export const cairnAbi = [
  {
    type: "constructor",
    inputs: [
      { name: "_owner", type: "address", internalType: "address" },
      { name: "_feeRecipient", type: "address", internalType: "address" }
    ],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "MIN_ESCROW",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "MIN_HEARTBEAT_INTERVAL",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "PROTOCOL_FEE_BPS",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "checkLiveness",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "commitCheckpoint",
    inputs: [
      { name: "taskId", type: "bytes32", internalType: "bytes32" },
      { name: "cid", type: "bytes32", internalType: "bytes32" }
    ],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "completeTask",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "feeRecipient",
    inputs: [],
    outputs: [{ name: "", type: "address", internalType: "address" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "getCheckpoints",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [{ name: "cids", type: "bytes32[]", internalType: "bytes32[]" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "getTask",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [
      { name: "state", type: "uint8", internalType: "enum ICairnTaskMVP.State" },
      { name: "operator", type: "address", internalType: "address" },
      { name: "primaryAgent", type: "address", internalType: "address" },
      { name: "fallbackAgent", type: "address", internalType: "address" },
      { name: "escrow", type: "uint256", internalType: "uint256" },
      { name: "primaryCheckpoints", type: "uint256", internalType: "uint256" },
      { name: "fallbackCheckpoints", type: "uint256", internalType: "uint256" },
      { name: "lastHeartbeat", type: "uint256", internalType: "uint256" },
      { name: "deadline", type: "uint256", internalType: "uint256" }
    ],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "heartbeat",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "isStale",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [{ name: "", type: "bool", internalType: "bool" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "minEscrow",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "pure"
  },
  {
    type: "function",
    name: "minHeartbeatInterval",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "pure"
  },
  {
    type: "function",
    name: "owner",
    inputs: [],
    outputs: [{ name: "", type: "address", internalType: "address" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "protocolFeeBps",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "pure"
  },
  {
    type: "function",
    name: "settle",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "submitTask",
    inputs: [
      { name: "primaryAgent", type: "address", internalType: "address" },
      { name: "fallbackAgent", type: "address", internalType: "address" },
      { name: "specHash", type: "bytes32", internalType: "bytes32" },
      { name: "heartbeatInterval", type: "uint256", internalType: "uint256" },
      { name: "deadline", type: "uint256", internalType: "uint256" }
    ],
    outputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    stateMutability: "payable"
  },
  // Events
  {
    type: "event",
    name: "CheckpointCommitted",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "index", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "cid", type: "bytes32", indexed: false, internalType: "bytes32" },
      { name: "agent", type: "address", indexed: false, internalType: "address" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "FallbackAssigned",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "fallbackAgent", type: "address", indexed: false, internalType: "address" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "HeartbeatReceived",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "timestamp", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskCompleted",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "completedBy", type: "address", indexed: false, internalType: "address" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskFailed",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "reason", type: "string", indexed: false, internalType: "string" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskResolved",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "primaryShare", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "fallbackShare", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "protocolFee", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskSubmitted",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "operator", type: "address", indexed: true, internalType: "address" },
      { name: "primaryAgent", type: "address", indexed: false, internalType: "address" },
      { name: "fallbackAgent", type: "address", indexed: false, internalType: "address" },
      { name: "escrow", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  // Errors
  { type: "error", name: "AlreadySettled", inputs: [] },
  { type: "error", name: "DeadlineExceeded", inputs: [] },
  { type: "error", name: "DeadlineNotReached", inputs: [] },
  {
    type: "error",
    name: "InsufficientEscrow",
    inputs: [
      { name: "required", type: "uint256", internalType: "uint256" },
      { name: "provided", type: "uint256", internalType: "uint256" }
    ]
  },
  { type: "error", name: "InvalidAddress", inputs: [] },
  { type: "error", name: "InvalidCID", inputs: [] },
  { type: "error", name: "InvalidDeadline", inputs: [] },
  {
    type: "error",
    name: "InvalidHeartbeatInterval",
    inputs: [
      { name: "minimum", type: "uint256", internalType: "uint256" },
      { name: "provided", type: "uint256", internalType: "uint256" }
    ]
  },
  {
    type: "error",
    name: "InvalidState",
    inputs: [
      { name: "expected", type: "uint8", internalType: "enum ICairnTaskMVP.State" },
      { name: "actual", type: "uint8", internalType: "enum ICairnTaskMVP.State" }
    ]
  },
  { type: "error", name: "NotStale", inputs: [] },
  { type: "error", name: "TaskNotFound", inputs: [] },
  { type: "error", name: "TransferFailed", inputs: [] },
  { type: "error", name: "Unauthorized", inputs: [] }
] as const;

// Contract address from deployment
export const CAIRN_CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CAIRN_CONTRACT_ADDRESS as `0x${string}` || '0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417';

// Task state enum matching contract
export enum TaskState {
  RUNNING = 0,
  FAILED = 1,
  RECOVERING = 2,
  RESOLVED = 3
}

// State display configuration (from docs/concepts.md)
export const stateConfig = {
  [TaskState.RUNNING]: {
    color: 'bg-cairn-running',
    label: 'In Progress',
    textColor: 'text-cairn-running',
    borderColor: 'border-cairn-running'
  },
  [TaskState.FAILED]: {
    color: 'bg-cairn-failed',
    label: 'Failed',
    textColor: 'text-cairn-failed',
    borderColor: 'border-cairn-failed'
  },
  [TaskState.RECOVERING]: {
    color: 'bg-cairn-recovering',
    label: 'Recovering',
    textColor: 'text-cairn-recovering',
    borderColor: 'border-cairn-recovering'
  },
  [TaskState.RESOLVED]: {
    color: 'bg-cairn-resolved',
    label: 'Completed',
    textColor: 'text-cairn-resolved',
    borderColor: 'border-cairn-resolved'
  },
} as const;
