// CairnCore ABI - Full Protocol (6-state machine)
export const cairnAbi = [
  {
    type: "constructor",
    inputs: [
      { name: "_feeRecipient", type: "address", internalType: "address" },
      { name: "_recoveryRouter", type: "address", internalType: "address" },
      { name: "_fallbackPool", type: "address", internalType: "address" },
      { name: "_arbiterRegistry", type: "address", internalType: "address" },
      { name: "_governance", type: "address", internalType: "address" }
    ],
    stateMutability: "nonpayable"
  },
  { type: "receive", stateMutability: "payable" },
  // View functions
  {
    type: "function",
    name: "arbiterRegistry",
    inputs: [],
    outputs: [{ name: "", type: "address", internalType: "contract IArbiterRegistry" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "disputeTimeout",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "fallbackPool",
    inputs: [],
    outputs: [{ name: "", type: "address", internalType: "contract IFallbackPool" }],
    stateMutability: "view"
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
    name: "getAgentTasks",
    inputs: [{ name: "agent", type: "address", internalType: "address" }],
    outputs: [{ name: "", type: "bytes32[]", internalType: "bytes32[]" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "getBatchRoots",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [{ name: "", type: "bytes32[]", internalType: "bytes32[]" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "getTask",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [
      {
        name: "",
        type: "tuple",
        internalType: "struct ICairnCore.Task",
        components: [
          { name: "id", type: "bytes32", internalType: "bytes32" },
          { name: "taskType", type: "bytes32", internalType: "bytes32" },
          { name: "specHash", type: "bytes32", internalType: "bytes32" },
          { name: "operator", type: "address", internalType: "address" },
          { name: "primaryAgent", type: "address", internalType: "address" },
          { name: "fallbackAgent", type: "address", internalType: "address" },
          { name: "currentAgent", type: "address", internalType: "address" },
          { name: "state", type: "uint8", internalType: "enum ICairnTypes.TaskState" },
          { name: "createdAt", type: "uint256", internalType: "uint256" },
          { name: "startedAt", type: "uint256", internalType: "uint256" },
          { name: "deadline", type: "uint256", internalType: "uint256" },
          { name: "escrowAmount", type: "uint256", internalType: "uint256" },
          { name: "settledPrimary", type: "uint256", internalType: "uint256" },
          { name: "settledFallback", type: "uint256", internalType: "uint256" },
          { name: "heartbeatInterval", type: "uint256", internalType: "uint256" },
          { name: "lastHeartbeat", type: "uint256", internalType: "uint256" },
          { name: "checkpointCount", type: "uint256", internalType: "uint256" },
          { name: "primaryCheckpoints", type: "uint256", internalType: "uint256" },
          { name: "fallbackCheckpoints", type: "uint256", internalType: "uint256" },
          { name: "latestCheckpointCID", type: "bytes32", internalType: "bytes32" },
          { name: "failureClass", type: "uint8", internalType: "enum ICairnTypes.FailureClass" },
          { name: "failureType", type: "uint8", internalType: "enum ICairnTypes.FailureType" },
          { name: "failureRecordCID", type: "bytes32", internalType: "bytes32" },
          { name: "recoveryScore", type: "uint256", internalType: "uint256" },
          { name: "resolutionType", type: "uint8", internalType: "enum ICairnTypes.ResolutionType" },
          { name: "resolutionRecordCID", type: "bytes32", internalType: "bytes32" }
        ]
      }
    ],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "getTaskTypeHistory",
    inputs: [{ name: "taskType", type: "bytes32", internalType: "bytes32" }],
    outputs: [{ name: "", type: "bytes32[]", internalType: "bytes32[]" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "governance",
    inputs: [],
    outputs: [{ name: "", type: "address", internalType: "contract IGovernance" }],
    stateMutability: "view"
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
    stateMutability: "view"
  },
  {
    type: "function",
    name: "minHeartbeatInterval",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "paused",
    inputs: [],
    outputs: [{ name: "", type: "bool", internalType: "bool" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "protocolFeeBps",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "recoveryRouter",
    inputs: [],
    outputs: [{ name: "", type: "address", internalType: "contract IRecoveryRouter" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "recoveryThreshold",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "totalEscrowLocked",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "totalTasksCreated",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "totalTasksResolved",
    inputs: [],
    outputs: [{ name: "", type: "uint256", internalType: "uint256" }],
    stateMutability: "view"
  },
  {
    type: "function",
    name: "verifyCheckpoint",
    inputs: [
      { name: "taskId", type: "bytes32", internalType: "bytes32" },
      { name: "cid", type: "bytes32", internalType: "bytes32" },
      { name: "batchIndex", type: "uint256", internalType: "uint256" },
      { name: "leafIndex", type: "uint256", internalType: "uint256" },
      { name: "proof", type: "bytes32[]", internalType: "bytes32[]" }
    ],
    outputs: [{ name: "", type: "bool", internalType: "bool" }],
    stateMutability: "view"
  },
  // Write functions
  {
    type: "function",
    name: "commitCheckpointBatch",
    inputs: [
      { name: "taskId", type: "bytes32", internalType: "bytes32" },
      { name: "count", type: "uint256", internalType: "uint256" },
      { name: "merkleRoot", type: "bytes32", internalType: "bytes32" },
      { name: "latestCID", type: "bytes32", internalType: "bytes32" }
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
    name: "detectFailure",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [],
    stateMutability: "nonpayable"
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
    name: "pause",
    inputs: [],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "resolveDispute",
    inputs: [
      { name: "taskId", type: "bytes32", internalType: "bytes32" },
      {
        name: "ruling",
        type: "tuple",
        internalType: "struct ICairnTypes.Ruling",
        components: [
          { name: "outcome", type: "uint8", internalType: "enum ICairnTypes.RulingOutcome" },
          { name: "agentShare", type: "uint256", internalType: "uint256" },
          { name: "rationaleCID", type: "bytes32", internalType: "bytes32" }
        ]
      }
    ],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "resolveDisputeTimeout",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "setContracts",
    inputs: [
      { name: "_recoveryRouter", type: "address", internalType: "address" },
      { name: "_fallbackPool", type: "address", internalType: "address" },
      { name: "_arbiterRegistry", type: "address", internalType: "address" }
    ],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "setFeeRecipient",
    inputs: [{ name: "_feeRecipient", type: "address", internalType: "address" }],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "startTask",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    outputs: [],
    stateMutability: "nonpayable"
  },
  {
    type: "function",
    name: "submitTask",
    inputs: [
      { name: "taskType", type: "bytes32", internalType: "bytes32" },
      { name: "specHash", type: "bytes32", internalType: "bytes32" },
      { name: "primaryAgent", type: "address", internalType: "address" },
      { name: "heartbeatInterval", type: "uint256", internalType: "uint256" },
      { name: "deadline", type: "uint256", internalType: "uint256" }
    ],
    outputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }],
    stateMutability: "payable"
  },
  {
    type: "function",
    name: "unpause",
    inputs: [],
    outputs: [],
    stateMutability: "nonpayable"
  },
  // Events
  {
    type: "event",
    name: "CheckpointBatchCommitted",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "agent", type: "address", indexed: true, internalType: "address" },
      { name: "batchStartIndex", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "batchEndIndex", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "merkleRoot", type: "bytes32", indexed: false, internalType: "bytes32" },
      { name: "latestCID", type: "bytes32", indexed: false, internalType: "bytes32" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "Heartbeat",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "agent", type: "address", indexed: true, internalType: "address" },
      { name: "timestamp", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "Paused",
    inputs: [{ name: "account", type: "address", indexed: false, internalType: "address" }],
    anonymous: false
  },
  {
    type: "event",
    name: "RecoveryStarted",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "fallbackAgent", type: "address", indexed: true, internalType: "address" },
      { name: "resumeFromCheckpoint", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskCompleted",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "agent", type: "address", indexed: true, internalType: "address" },
      { name: "checkpointCount", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskCreated",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "taskType", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "operator", type: "address", indexed: true, internalType: "address" },
      { name: "primaryAgent", type: "address", indexed: false, internalType: "address" },
      { name: "fallbackAgent", type: "address", indexed: false, internalType: "address" },
      { name: "escrow", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "deadline", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskDisputed",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "recoveryScore", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "disputeDeadline", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskFailed",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "agent", type: "address", indexed: true, internalType: "address" },
      { name: "failureClass", type: "uint8", indexed: false, internalType: "enum ICairnTypes.FailureClass" },
      { name: "failureType", type: "uint8", indexed: false, internalType: "enum ICairnTypes.FailureType" },
      { name: "recoveryScore", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "failureRecordCID", type: "bytes32", indexed: false, internalType: "bytes32" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskSettled",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "resolutionType", type: "uint8", indexed: false, internalType: "enum ICairnTypes.ResolutionType" },
      { name: "primaryPayout", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "fallbackPayout", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "protocolFee", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "TaskStarted",
    inputs: [
      { name: "taskId", type: "bytes32", indexed: true, internalType: "bytes32" },
      { name: "agent", type: "address", indexed: true, internalType: "address" },
      { name: "successRate", type: "uint256", indexed: false, internalType: "uint256" },
      { name: "avgCheckpoints", type: "uint256", indexed: false, internalType: "uint256" }
    ],
    anonymous: false
  },
  {
    type: "event",
    name: "Unpaused",
    inputs: [{ name: "account", type: "address", indexed: false, internalType: "address" }],
    anonymous: false
  },
  // Errors
  {
    type: "error",
    name: "DeadlineExceeded",
    inputs: [
      { name: "taskId", type: "bytes32", internalType: "bytes32" },
      { name: "deadline", type: "uint256", internalType: "uint256" }
    ]
  },
  { type: "error", name: "DisputeTimeoutNotReached", inputs: [] },
  { type: "error", name: "EnforcedPause", inputs: [] },
  { type: "error", name: "ExpectedPause", inputs: [] },
  {
    type: "error",
    name: "HeartbeatTooFrequent",
    inputs: [
      { name: "lastHeartbeat", type: "uint256", internalType: "uint256" },
      { name: "minInterval", type: "uint256", internalType: "uint256" }
    ]
  },
  {
    type: "error",
    name: "InsufficientEscrow",
    inputs: [
      { name: "provided", type: "uint256", internalType: "uint256" },
      { name: "minimum", type: "uint256", internalType: "uint256" }
    ]
  },
  {
    type: "error",
    name: "InvalidHeartbeatInterval",
    inputs: [
      { name: "provided", type: "uint256", internalType: "uint256" },
      { name: "minimum", type: "uint256", internalType: "uint256" }
    ]
  },
  { type: "error", name: "InvalidMerkleProof", inputs: [] },
  {
    type: "error",
    name: "InvalidState",
    inputs: [
      { name: "current", type: "uint8", internalType: "enum ICairnTypes.TaskState" },
      { name: "expected", type: "uint8", internalType: "enum ICairnTypes.TaskState" }
    ]
  },
  {
    type: "error",
    name: "NotAuthorized",
    inputs: [
      { name: "caller", type: "address", internalType: "address" },
      { name: "expected", type: "address", internalType: "address" }
    ]
  },
  { type: "error", name: "ReentrancyGuardReentrantCall", inputs: [] },
  {
    type: "error",
    name: "TaskNotFound",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }]
  },
  {
    type: "error",
    name: "TaskNotStale",
    inputs: [{ name: "taskId", type: "bytes32", internalType: "bytes32" }]
  },
  { type: "error", name: "ZeroAddress", inputs: [] }
] as const;

// Contract addresses - Full Protocol on Base Sepolia
export const CAIRN_CORE_ADDRESS = '0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640' as const;
export const CAIRN_GOVERNANCE_ADDRESS = '0x7A09567e0348889Cc14264bEcf08F8d72Dc6987f' as const;
export const RECOVERY_ROUTER_ADDRESS = '0xE52703946cb44c12A6A38A41f638BA2D7197a84d' as const;
export const FALLBACK_POOL_ADDRESS = '0x4dCeA24eaD4026987d97a205598c1Ee1CE1649B0' as const;
export const ARBITER_REGISTRY_ADDRESS = '0xfb50F4F778F166ADd684E0eFe7aD5133CE34aE68' as const;

// Legacy MVP contract (for backwards compatibility)
export const CAIRN_MVP_ADDRESS = '0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417' as const;

// Default contract address (use CairnCore for full protocol)
export const CAIRN_CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CAIRN_CONTRACT_ADDRESS as `0x${string}` || CAIRN_CORE_ADDRESS;

// Task state enum - 6 states for full protocol
export enum TaskState {
  IDLE = 0,       // Task submitted, awaiting start
  RUNNING = 1,    // Agent executing, heartbeats active
  FAILED = 2,     // Failure detected, recovery pending
  RECOVERING = 3, // Fallback agent assigned, executing
  DISPUTED = 4,   // Under arbiter review
  RESOLVED = 5    // Settlement complete
}

// Failure class enum
export enum FailureClass {
  NONE = 0,
  LIVENESS = 1,   // Agent stopped responding
  RESOURCE = 2,   // External dependency failed
  LOGIC = 3       // Agent-side bug
}

// Resolution type enum
export enum ResolutionType {
  NONE = 0,
  SUCCESS = 1,      // Task completed normally
  RECOVERY = 2,     // Completed by fallback
  ARBITRATION = 3,  // Resolved by arbiter
  TIMEOUT = 4       // Dispute timeout
}

// State display configuration for 6-state machine
export const stateConfig = {
  [TaskState.IDLE]: {
    color: 'bg-stone-500',
    label: 'Pending',
    textColor: 'text-stone-500',
    borderColor: 'border-stone-500'
  },
  [TaskState.RUNNING]: {
    color: 'bg-amber-500',
    label: 'Running',
    textColor: 'text-amber-500',
    borderColor: 'border-amber-500'
  },
  [TaskState.FAILED]: {
    color: 'bg-red-500',
    label: 'Failed',
    textColor: 'text-red-500',
    borderColor: 'border-red-500'
  },
  [TaskState.RECOVERING]: {
    color: 'bg-orange-500',
    label: 'Recovering',
    textColor: 'text-orange-500',
    borderColor: 'border-orange-500'
  },
  [TaskState.DISPUTED]: {
    color: 'bg-purple-500',
    label: 'Disputed',
    textColor: 'text-purple-500',
    borderColor: 'border-purple-500'
  },
  [TaskState.RESOLVED]: {
    color: 'bg-green-500',
    label: 'Resolved',
    textColor: 'text-green-500',
    borderColor: 'border-green-500'
  },
} as const;
