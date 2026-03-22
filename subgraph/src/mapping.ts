/**
 * CAIRN Protocol - The Graph Mappings
 *
 * Handles all CairnCore events and builds execution intelligence data
 * for failure pattern analysis and agent performance tracking.
 *
 * Based on PRD-03: Execution Intelligence Layer
 */

import { BigInt, BigDecimal, Bytes } from "@graphprotocol/graph-ts";
import {
  TaskCreated as TaskCreatedEvent,
  TaskStarted as TaskStartedEvent,
  TaskCompleted as TaskCompletedEvent,
  CheckpointBatchCommitted as CheckpointBatchCommittedEvent,
  Heartbeat as HeartbeatEvent,
  TaskFailed as TaskFailedEvent,
  RecoveryStarted as RecoveryStartedEvent,
  TaskDisputed as TaskDisputedEvent,
  TaskSettled as TaskSettledEvent,
} from "../generated/CairnCore/CairnCore";
import {
  Task,
  Agent,
  Checkpoint,
  FailurePattern,
  Protocol,
  DailyMetrics,
} from "../generated/schema";

// ═══════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════

const ZERO_BI = BigInt.fromI32(0);
const ONE_BI = BigInt.fromI32(1);
const ZERO_BD = BigDecimal.fromString("0");
const ONE_BD = BigDecimal.fromString("1");
const SECONDS_PER_DAY = BigInt.fromI32(86400);

// ═══════════════════════════════════════════════════════════════
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════

function getOrCreateAgent(address: Bytes): Agent {
  let agent = Agent.load(address);
  if (agent == null) {
    agent = new Agent(address);
    agent.totalTasksCreated = ZERO_BI;
    agent.totalTasksStarted = ZERO_BI;
    agent.totalTasksCompleted = ZERO_BI;
    agent.totalTasksFailed = ZERO_BI;
    agent.totalTasksRecovered = ZERO_BI;
    agent.totalEarned = ZERO_BI;
    agent.totalPrimaryEarned = ZERO_BI;
    agent.totalFallbackEarned = ZERO_BI;
    agent.successRate = ZERO_BD;
    agent.averageCheckpoints = ZERO_BD;
    agent.averageRecoveryScore = ZERO_BD;
    agent.save();
  }
  return agent;
}

function getOrCreateProtocol(contractAddress: Bytes): Protocol {
  let protocol = Protocol.load(contractAddress);
  if (protocol == null) {
    protocol = new Protocol(contractAddress);
    protocol.totalTasksCreated = ZERO_BI;
    protocol.totalTasksResolved = ZERO_BI;
    protocol.totalEscrowLocked = ZERO_BI;
    protocol.idleTasks = ZERO_BI;
    protocol.runningTasks = ZERO_BI;
    protocol.failedTasks = ZERO_BI;
    protocol.recoveringTasks = ZERO_BI;
    protocol.disputedTasks = ZERO_BI;
    protocol.resolvedTasks = ZERO_BI;
    protocol.totalFeesCollected = ZERO_BI;
    protocol.totalPrimaryPaid = ZERO_BI;
    protocol.totalFallbackPaid = ZERO_BI;
    protocol.overallSuccessRate = ZERO_BD;
    protocol.avgTaskDuration = ZERO_BI;
    protocol.avgCheckpointsPerTask = ZERO_BD;
    protocol.save();
  }
  return protocol;
}

function getOrCreateDailyMetrics(timestamp: BigInt): DailyMetrics {
  let dayStart = timestamp.div(SECONDS_PER_DAY).times(SECONDS_PER_DAY);
  let id = Bytes.fromI32(dayStart.toI32());

  let metrics = DailyMetrics.load(id);
  if (metrics == null) {
    metrics = new DailyMetrics(id);
    metrics.date = dayStart;
    metrics.tasksCreated = ZERO_BI;
    metrics.tasksCompleted = ZERO_BI;
    metrics.tasksFailed = ZERO_BI;
    metrics.tasksRecovered = ZERO_BI;
    metrics.escrowLocked = ZERO_BI;
    metrics.escrowSettled = ZERO_BI;
    metrics.feesCollected = ZERO_BI;
    metrics.avgRecoveryScore = ZERO_BD;
    metrics.successRate = ZERO_BD;
    metrics.save();
  }
  return metrics;
}

function getOrCreateFailurePattern(taskType: Bytes, failureClass: string): FailurePattern {
  let id = taskType.concatI32(failureClass.charCodeAt(0));
  let pattern = FailurePattern.load(id);

  if (pattern == null) {
    pattern = new FailurePattern(id);
    pattern.taskType = taskType;
    pattern.failureClass = failureClass;
    pattern.occurrenceCount = ZERO_BI;
    pattern.totalRecoveryScore = ZERO_BI;
    pattern.avgRecoveryScore = ZERO_BD;
    pattern.heartbeatMissCount = ZERO_BI;
    pattern.networkPartitionCount = ZERO_BI;
    pattern.rateLimitCount = ZERO_BI;
    pattern.gasExhaustedCount = ZERO_BI;
    pattern.validationFailedCount = ZERO_BI;
    pattern.schemaInvalidCount = ZERO_BI;
    pattern.totalAttempted = ZERO_BI;
    pattern.totalRecovered = ZERO_BI;
    pattern.recoveryRate = ZERO_BD;
    pattern.save();
  }
  return pattern;
}

function updateStateCounters(protocol: Protocol, oldState: string, newState: string): void {
  // Decrement old state
  if (oldState == "IDLE") protocol.idleTasks = protocol.idleTasks.minus(ONE_BI);
  else if (oldState == "RUNNING") protocol.runningTasks = protocol.runningTasks.minus(ONE_BI);
  else if (oldState == "FAILED") protocol.failedTasks = protocol.failedTasks.minus(ONE_BI);
  else if (oldState == "RECOVERING") protocol.recoveringTasks = protocol.recoveringTasks.minus(ONE_BI);
  else if (oldState == "DISPUTED") protocol.disputedTasks = protocol.disputedTasks.minus(ONE_BI);

  // Increment new state
  if (newState == "IDLE") protocol.idleTasks = protocol.idleTasks.plus(ONE_BI);
  else if (newState == "RUNNING") protocol.runningTasks = protocol.runningTasks.plus(ONE_BI);
  else if (newState == "FAILED") protocol.failedTasks = protocol.failedTasks.plus(ONE_BI);
  else if (newState == "RECOVERING") protocol.recoveringTasks = protocol.recoveringTasks.plus(ONE_BI);
  else if (newState == "DISPUTED") protocol.disputedTasks = protocol.disputedTasks.plus(ONE_BI);
  else if (newState == "RESOLVED") protocol.resolvedTasks = protocol.resolvedTasks.plus(ONE_BI);
}

function mapFailureClass(classEnum: i32): string {
  if (classEnum == 0) return "LIVENESS";
  if (classEnum == 1) return "RESOURCE";
  if (classEnum == 2) return "LOGIC";
  return "LIVENESS"; // Default
}

function mapFailureType(typeEnum: i32): string {
  if (typeEnum == 0) return "HEARTBEAT_MISS";
  if (typeEnum == 1) return "NETWORK_PARTITION";
  if (typeEnum == 2) return "NODE_CRASH";
  if (typeEnum == 3) return "RATE_LIMIT";
  if (typeEnum == 4) return "GAS_EXHAUSTED";
  if (typeEnum == 5) return "UPSTREAM_TIMEOUT";
  if (typeEnum == 6) return "VALIDATION_FAILED";
  if (typeEnum == 7) return "SCHEMA_MISMATCH";
  if (typeEnum == 8) return "INVARIANT_VIOLATION";
  return "HEARTBEAT_MISS"; // Default
}

function mapResolutionType(typeEnum: i32): string {
  if (typeEnum == 0) return "SUCCESS";
  if (typeEnum == 1) return "RECOVERY";
  if (typeEnum == 2) return "ARBITER_RULING";
  if (typeEnum == 3) return "TIMEOUT_REFUND";
  return "SUCCESS"; // Default
}

// ═══════════════════════════════════════════════════════════════
// EVENT HANDLERS
// ═══════════════════════════════════════════════════════════════

export function handleTaskCreated(event: TaskCreatedEvent): void {
  let task = new Task(event.params.taskId);

  // Basic info
  task.taskType = event.params.taskType;
  task.specHash = Bytes.empty(); // Not in event, would need to query contract
  task.operator = event.params.operator;
  task.currentAgent = event.params.primaryAgent;

  // Agents
  let primaryAgent = getOrCreateAgent(event.params.primaryAgent);
  primaryAgent.totalTasksCreated = primaryAgent.totalTasksCreated.plus(ONE_BI);
  let existingFirstTask = primaryAgent.firstTaskAt;
  if (existingFirstTask === null) {
    primaryAgent.firstTaskAt = event.block.timestamp;
  } else if (existingFirstTask.gt(event.block.timestamp)) {
    primaryAgent.firstTaskAt = event.block.timestamp;
  }
  primaryAgent.lastTaskAt = event.block.timestamp;
  primaryAgent.save();

  task.primaryAgent = event.params.primaryAgent;

  if (event.params.fallbackAgent.notEqual(Bytes.fromHexString("0x0000000000000000000000000000000000000000"))) {
    let fallbackAgent = getOrCreateAgent(event.params.fallbackAgent);
    fallbackAgent.save();
    task.fallbackAgent = event.params.fallbackAgent;
  }

  // State
  task.state = "IDLE";
  task.createdAt = event.block.timestamp;
  task.deadline = event.params.deadline;

  // Escrow
  task.escrowAmount = event.params.escrow;
  task.settledPrimary = ZERO_BI;
  task.settledFallback = ZERO_BI;

  // Heartbeat (will be set when task starts)
  task.heartbeatInterval = ZERO_BI;

  // Checkpoints
  task.checkpointCount = ZERO_BI;
  task.primaryCheckpoints = ZERO_BI;
  task.fallbackCheckpoints = ZERO_BI;

  task.save();

  // Update protocol
  let protocol = getOrCreateProtocol(event.address);
  protocol.totalTasksCreated = protocol.totalTasksCreated.plus(ONE_BI);
  protocol.totalEscrowLocked = protocol.totalEscrowLocked.plus(event.params.escrow);
  updateStateCounters(protocol, "", "IDLE");
  protocol.save();

  // Update daily metrics
  let daily = getOrCreateDailyMetrics(event.block.timestamp);
  daily.tasksCreated = daily.tasksCreated.plus(ONE_BI);
  daily.escrowLocked = daily.escrowLocked.plus(event.params.escrow);
  daily.save();
}

export function handleTaskStarted(event: TaskStartedEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  let oldState = task.state;
  task.state = "RUNNING";
  task.startedAt = event.block.timestamp;
  task.lastHeartbeat = event.block.timestamp;

  // Store intelligence hints from event
  task.successRate = event.params.successRate;
  task.avgCheckpoints = event.params.avgCheckpoints;

  task.save();

  // Update agent
  let agent = getOrCreateAgent(event.params.agent);
  agent.totalTasksStarted = agent.totalTasksStarted.plus(ONE_BI);
  agent.lastTaskAt = event.block.timestamp;
  agent.save();

  // Update protocol
  let protocol = getOrCreateProtocol(event.address);
  updateStateCounters(protocol, oldState, "RUNNING");
  protocol.save();
}

export function handleTaskCompleted(event: TaskCompletedEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  let oldState = task.state;
  task.state = "RESOLVED";
  task.resolutionType = task.currentAgent.equals(task.primaryAgent) ? "SUCCESS" : "RECOVERY";

  task.save();

  // Update agent
  let agent = getOrCreateAgent(event.params.agent);
  agent.totalTasksCompleted = agent.totalTasksCompleted.plus(ONE_BI);

  // Update success rate
  let totalTasks = agent.totalTasksCompleted.plus(agent.totalTasksFailed);
  if (totalTasks.gt(ZERO_BI)) {
    agent.successRate = agent.totalTasksCompleted.toBigDecimal().div(totalTasks.toBigDecimal());
  }

  // Update average checkpoints
  if (agent.totalTasksCompleted.gt(ZERO_BI)) {
    let currentTotal = agent.averageCheckpoints.times(agent.totalTasksCompleted.minus(ONE_BI).toBigDecimal());
    let newTotal = currentTotal.plus(event.params.checkpointCount.toBigDecimal());
    agent.averageCheckpoints = newTotal.div(agent.totalTasksCompleted.toBigDecimal());
  }

  agent.lastTaskAt = event.block.timestamp;
  agent.save();

  // Update protocol
  let protocol = getOrCreateProtocol(event.address);
  updateStateCounters(protocol, oldState, "RESOLVED");
  protocol.save();

  // Update daily metrics
  let daily = getOrCreateDailyMetrics(event.block.timestamp);
  daily.tasksCompleted = daily.tasksCompleted.plus(ONE_BI);
  daily.save();
}

export function handleCheckpointBatchCommitted(event: CheckpointBatchCommittedEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  // Update task checkpoint counters
  let batchSize = event.params.batchEndIndex.minus(event.params.batchStartIndex).plus(ONE_BI);
  task.checkpointCount = task.checkpointCount.plus(batchSize);
  task.latestCheckpointCID = event.params.latestCID;
  task.lastHeartbeat = event.block.timestamp; // Checkpoint acts as heartbeat

  // Track who committed these checkpoints
  if (event.params.agent.equals(task.primaryAgent)) {
    task.primaryCheckpoints = task.primaryCheckpoints.plus(batchSize);
  } else {
    let fallback = task.fallbackAgent;
    if (fallback !== null) {
      if (event.params.agent.equals(fallback)) {
        task.fallbackCheckpoints = task.fallbackCheckpoints.plus(batchSize);
      }
    }
  }

  task.save();

  // Create individual checkpoint entities for the batch
  // Note: We don't have individual CIDs here, only the latest one
  // In a real implementation, you'd need to reconstruct from Merkle tree or store differently
  // For now, we'll create a single checkpoint entity for the batch
  let checkpointId = event.params.taskId
    .concatI32(event.params.batchStartIndex.toI32())
    .concatI32(0); // leafIndex 0 for batch summary

  let checkpoint = new Checkpoint(checkpointId);
  checkpoint.task = event.params.taskId;
  checkpoint.agent = event.params.agent;
  checkpoint.cid = event.params.latestCID;
  checkpoint.batchIndex = event.params.batchStartIndex;
  checkpoint.leafIndex = ZERO_BI;
  checkpoint.merkleRoot = event.params.merkleRoot;
  checkpoint.timestamp = event.block.timestamp;
  checkpoint.save();
}

export function handleHeartbeat(event: HeartbeatEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  task.lastHeartbeat = event.params.timestamp;
  task.save();

  // Update agent
  let agent = getOrCreateAgent(event.params.agent);
  agent.lastHeartbeat = event.params.timestamp;
  agent.save();
}

export function handleTaskFailed(event: TaskFailedEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  let oldState = task.state;
  task.state = "FAILED";
  task.failureClass = mapFailureClass(event.params.failureClass);
  task.failureType = mapFailureType(event.params.failureType);
  task.failureRecordCID = event.params.failureRecordCID;
  task.recoveryScore = event.params.recoveryScore;

  task.save();

  // Update agent
  let agent = getOrCreateAgent(event.params.agent);
  agent.totalTasksFailed = agent.totalTasksFailed.plus(ONE_BI);

  // Update average recovery score
  if (agent.totalTasksFailed.gt(ZERO_BI)) {
    let currentTotal = agent.averageRecoveryScore.times(agent.totalTasksFailed.minus(ONE_BI).toBigDecimal());
    let newTotal = currentTotal.plus(event.params.recoveryScore.toBigDecimal().div(BigDecimal.fromString("1000000000000000000")));
    agent.averageRecoveryScore = newTotal.div(agent.totalTasksFailed.toBigDecimal());
  }

  agent.save();

  // Update failure pattern
  let pattern = getOrCreateFailurePattern(task.taskType, task.failureClass!);
  pattern.occurrenceCount = pattern.occurrenceCount.plus(ONE_BI);
  pattern.totalRecoveryScore = pattern.totalRecoveryScore.plus(event.params.recoveryScore);
  pattern.avgRecoveryScore = pattern.totalRecoveryScore.toBigDecimal().div(pattern.occurrenceCount.toBigDecimal()).div(BigDecimal.fromString("1000000000000000000"));

  // Update specific failure type counter
  let failureType = task.failureType!;
  if (failureType == "HEARTBEAT_MISS") pattern.heartbeatMissCount = pattern.heartbeatMissCount.plus(ONE_BI);
  else if (failureType == "NETWORK_PARTITION") pattern.networkPartitionCount = pattern.networkPartitionCount.plus(ONE_BI);
  else if (failureType == "RATE_LIMIT") pattern.rateLimitCount = pattern.rateLimitCount.plus(ONE_BI);
  else if (failureType == "GAS_EXHAUSTED") pattern.gasExhaustedCount = pattern.gasExhaustedCount.plus(ONE_BI);
  else if (failureType == "VALIDATION_FAILED") pattern.validationFailedCount = pattern.validationFailedCount.plus(ONE_BI);
  else if (failureType == "SCHEMA_MISMATCH") pattern.schemaInvalidCount = pattern.schemaInvalidCount.plus(ONE_BI);

  pattern.totalAttempted = pattern.totalAttempted.plus(ONE_BI);
  pattern.lastOccurrence = event.block.timestamp;

  let existingFirst = pattern.firstOccurrence;
  if (existingFirst === null) {
    pattern.firstOccurrence = event.block.timestamp;
  } else if (existingFirst.gt(event.block.timestamp)) {
    pattern.firstOccurrence = event.block.timestamp;
  }

  pattern.save();

  // Update protocol
  let protocol = getOrCreateProtocol(event.address);
  updateStateCounters(protocol, oldState, "FAILED");
  protocol.save();

  // Update daily metrics
  let daily = getOrCreateDailyMetrics(event.block.timestamp);
  daily.tasksFailed = daily.tasksFailed.plus(ONE_BI);

  // Update avg recovery score
  let totalFailed = daily.tasksFailed;
  if (totalFailed.gt(ZERO_BI)) {
    let currentTotal = daily.avgRecoveryScore.times(totalFailed.minus(ONE_BI).toBigDecimal());
    let newTotal = currentTotal.plus(event.params.recoveryScore.toBigDecimal().div(BigDecimal.fromString("1000000000000000000")));
    daily.avgRecoveryScore = newTotal.div(totalFailed.toBigDecimal());
  }

  daily.save();
}

export function handleRecoveryStarted(event: RecoveryStartedEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  let oldState = task.state;
  task.state = "RECOVERING";
  task.currentAgent = event.params.fallbackAgent;

  task.save();

  // Update fallback agent stats
  let agent = getOrCreateAgent(event.params.fallbackAgent);
  agent.totalTasksStarted = agent.totalTasksStarted.plus(ONE_BI);
  agent.lastTaskAt = event.block.timestamp;
  agent.save();

  // Update protocol
  let protocol = getOrCreateProtocol(event.address);
  updateStateCounters(protocol, oldState, "RECOVERING");
  protocol.save();
}

export function handleTaskDisputed(event: TaskDisputedEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  let oldState = task.state;
  task.state = "DISPUTED";

  task.save();

  // Update protocol
  let protocol = getOrCreateProtocol(event.address);
  updateStateCounters(protocol, oldState, "DISPUTED");
  protocol.save();
}

export function handleTaskSettled(event: TaskSettledEvent): void {
  let task = Task.load(event.params.taskId);
  if (task == null) return;

  task.settledPrimary = event.params.primaryPayout;
  task.settledFallback = event.params.fallbackPayout;
  task.resolutionType = mapResolutionType(event.params.resolutionType);

  task.save();

  // Update primary agent earnings
  if (event.params.primaryPayout.gt(ZERO_BI)) {
    let primaryAgent = getOrCreateAgent(task.primaryAgent);
    primaryAgent.totalEarned = primaryAgent.totalEarned.plus(event.params.primaryPayout);
    primaryAgent.totalPrimaryEarned = primaryAgent.totalPrimaryEarned.plus(event.params.primaryPayout);
    primaryAgent.save();
  }

  // Update fallback agent earnings
  let fallbackAddr = task.fallbackAgent;
  if (event.params.fallbackPayout.gt(ZERO_BI)) {
    if (fallbackAddr !== null) {
      let fallbackAgent = getOrCreateAgent(fallbackAddr);
      fallbackAgent.totalEarned = fallbackAgent.totalEarned.plus(event.params.fallbackPayout);
      fallbackAgent.totalFallbackEarned = fallbackAgent.totalFallbackEarned.plus(event.params.fallbackPayout);

      // Track recovery success
      if (task.resolutionType == "RECOVERY") {
        fallbackAgent.totalTasksRecovered = fallbackAgent.totalTasksRecovered.plus(ONE_BI);
      }

      fallbackAgent.save();

      // Update failure pattern recovery stats
      let failClass = task.failureClass;
      if (failClass !== null) {
        let pattern = getOrCreateFailurePattern(task.taskType, failClass);
        pattern.totalRecovered = pattern.totalRecovered.plus(ONE_BI);

        if (pattern.totalAttempted.gt(ZERO_BI)) {
          pattern.recoveryRate = pattern.totalRecovered.toBigDecimal().div(pattern.totalAttempted.toBigDecimal());
        }

        pattern.save();
      }
    }
  }

  // Update protocol
  let protocol = getOrCreateProtocol(event.address);
  protocol.totalTasksResolved = protocol.totalTasksResolved.plus(ONE_BI);
  protocol.totalEscrowLocked = protocol.totalEscrowLocked.minus(task.escrowAmount);
  protocol.totalFeesCollected = protocol.totalFeesCollected.plus(event.params.protocolFee);
  protocol.totalPrimaryPaid = protocol.totalPrimaryPaid.plus(event.params.primaryPayout);
  protocol.totalFallbackPaid = protocol.totalFallbackPaid.plus(event.params.fallbackPayout);

  // Update overall success rate
  if (protocol.totalTasksResolved.gt(ZERO_BI)) {
    protocol.overallSuccessRate = protocol.resolvedTasks.toBigDecimal().div(protocol.totalTasksResolved.toBigDecimal());
  }

  protocol.save();

  // Update daily metrics
  let daily = getOrCreateDailyMetrics(event.block.timestamp);
  daily.escrowSettled = daily.escrowSettled.plus(task.escrowAmount);
  daily.feesCollected = daily.feesCollected.plus(event.params.protocolFee);

  if (task.resolutionType == "RECOVERY") {
    daily.tasksRecovered = daily.tasksRecovered.plus(ONE_BI);
  }

  // Update daily success rate
  let totalSettled = daily.tasksCompleted.plus(daily.tasksFailed);
  if (totalSettled.gt(ZERO_BI)) {
    daily.successRate = daily.tasksCompleted.toBigDecimal().div(totalSettled.toBigDecimal());
  }

  daily.save();
}
