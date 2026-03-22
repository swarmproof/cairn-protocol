# CAIRN Protocol Subgraph

The Graph indexing for CAIRN Protocol's execution intelligence layer. This subgraph indexes all task lifecycle events, failure patterns, and agent performance metrics for analytics and querying.

## 🏗️ Architecture

### Entities

- **Task**: Complete task lifecycle tracking with state machine (IDLE → RUNNING → FAILED/RECOVERING/DISPUTED → RESOLVED)
- **Agent**: Performance metrics, earnings, and reputation tracking
- **Checkpoint**: Individual checkpoint records with Merkle proof support
- **FailurePattern**: Aggregated failure analytics by task type and failure class
- **Protocol**: Global protocol metrics and counters
- **DailyMetrics**: Daily snapshots for time-series analysis

### Event Handlers

Handles all CairnCore events:
- `TaskCreated` - Task submission with escrow
- `TaskStarted` - Execution begins with intelligence hints
- `TaskCompleted` - Successful completion
- `CheckpointBatchCommitted` - Merkle-batched checkpoints (PRD-07)
- `Heartbeat` - Liveness proof
- `TaskFailed` - Failure detection with classification (PRD-02)
- `RecoveryStarted` - Fallback activation
- `TaskDisputed` - Arbiter needed
- `TaskSettled` - Final escrow settlement

## 🚀 Quick Start

### Prerequisites

```bash
npm install -g @graphprotocol/graph-cli
```

### Setup

1. **Extract ABI** (required before codegen):

```bash
cd subgraph
node scripts/extract-abi.js
```

This extracts the ABI from the compiled contract at `contracts/out/CairnCore.sol/CairnCore.json`.

2. **Install dependencies**:

```bash
npm install
```

3. **Generate types**:

```bash
npm run codegen
```

4. **Build**:

```bash
npm run build
```

### Deployment

#### The Graph Studio (Recommended)

1. Create a subgraph at [https://thegraph.com/studio/](https://thegraph.com/studio/)

2. Authenticate:

```bash
graph auth --studio <DEPLOY_KEY>
```

3. Deploy:

```bash
npm run deploy
```

#### Local Graph Node

1. Start local graph node (requires Docker):

```bash
# Clone graph-node repo
git clone https://github.com/graphprotocol/graph-node
cd graph-node/docker

# Start services
docker-compose up
```

2. Create and deploy:

```bash
npm run create-local
npm run deploy-local
```

## 📊 Example Queries

### Get Task with Full Details

```graphql
{
  task(id: "0x...") {
    id
    taskType
    operator
    primaryAgent {
      id
      totalTasksCompleted
      successRate
    }
    fallbackAgent {
      id
      totalTasksRecovered
    }
    state
    escrowAmount
    checkpointCount
    checkpoints {
      cid
      timestamp
    }
    failureClass
    failureType
    recoveryScore
    resolutionType
    settledPrimary
    settledFallback
  }
}
```

### Agent Performance Dashboard

```graphql
{
  agents(first: 10, orderBy: totalEarned, orderDirection: desc) {
    id
    totalTasksCompleted
    totalTasksFailed
    totalTasksRecovered
    successRate
    totalEarned
    averageCheckpoints
    averageRecoveryScore
  }
}
```

### Failure Pattern Analysis

```graphql
{
  failurePatterns(orderBy: occurrenceCount, orderDirection: desc) {
    taskType
    failureClass
    occurrenceCount
    avgRecoveryScore
    recoveryRate
    heartbeatMissCount
    rateLimitCount
    gasExhaustedCount
    validationFailedCount
  }
}
```

### Protocol Analytics

```graphql
{
  protocol(id: "0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640") {
    totalTasksCreated
    totalTasksResolved
    totalEscrowLocked
    runningTasks
    failedTasks
    recoveringTasks
    disputedTasks
    overallSuccessRate
    totalFeesCollected
    avgCheckpointsPerTask
  }
}
```

### Daily Time Series

```graphql
{
  dailyMetrics(first: 30, orderBy: date, orderDirection: desc) {
    date
    tasksCreated
    tasksCompleted
    tasksFailed
    tasksRecovered
    successRate
    avgRecoveryScore
    escrowLocked
    feesCollected
  }
}
```

### Tasks by State

```graphql
{
  runningTasks: tasks(where: { state: RUNNING }) {
    id
    taskType
    currentAgent
    lastHeartbeat
    deadline
  }

  failedTasks: tasks(where: { state: FAILED }) {
    id
    failureClass
    failureType
    recoveryScore
  }

  disputedTasks: tasks(where: { state: DISPUTED }) {
    id
    recoveryScore
    failureClass
  }
}
```

### Recent Checkpoints

```graphql
{
  checkpoints(first: 100, orderBy: timestamp, orderDirection: desc) {
    task {
      id
      taskType
    }
    agent
    cid
    timestamp
  }
}
```

## 🔧 Development

### Run Tests

```bash
npm test
```

### Local Development Workflow

1. Make changes to schema or mappings
2. Run `npm run codegen` to regenerate types
3. Run `npm run build` to verify compilation
4. Deploy to local graph node for testing

### Updating After Contract Changes

If the CairnCore contract is redeployed or updated:

1. Update the contract address in `subgraph.yaml`
2. Update the `startBlock` to the new deployment block
3. Re-extract ABI: `node scripts/extract-abi.js`
4. Rebuild and redeploy

## 📖 Schema Reference

### Enums

**TaskState**
- IDLE - Created but not started
- RUNNING - Actively executing
- FAILED - Failure detected
- RECOVERING - Fallback agent executing
- DISPUTED - Arbiter needed
- RESOLVED - Terminal state

**FailureClass** (PRD-02)
- LIVENESS - Agent unresponsive (high recovery potential)
- RESOURCE - External limits (medium recovery)
- LOGIC - Agent reasoning error (low recovery)

**FailureType**
- HEARTBEAT_MISS, NETWORK_PARTITION, NODE_CRASH
- RATE_LIMIT, GAS_EXHAUSTED, UPSTREAM_TIMEOUT
- VALIDATION_FAILED, SCHEMA_MISMATCH, INVARIANT_VIOLATION

**ResolutionType**
- SUCCESS - Completed normally
- RECOVERY - Fallback completed
- ARBITER_RULING - Dispute resolved
- TIMEOUT_REFUND - Dispute timed out

## 🌐 Network Configuration

### Base Sepolia (Current)

- Network: `base-sepolia`
- Chain ID: 84532
- Contract: `0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640`
- Start Block: ~17741070

To change networks, update `subgraph.yaml`:

```yaml
dataSources:
  - kind: ethereum
    name: CairnCore
    network: base-sepolia  # Change this
    source:
      address: "0x..."     # Update address
      startBlock: 12345    # Update start block
```

## 🔐 Security

- This subgraph is read-only and cannot modify blockchain state
- All data is publicly indexable from on-chain events
- No private keys or sensitive data are required

## 📝 License

BSL-1.1 (Business Source License)

## 🤝 Contributing

This subgraph is part of the CAIRN Protocol project. See main repository for contribution guidelines.

## 📚 Resources

- [The Graph Documentation](https://thegraph.com/docs/)
- [AssemblyScript API](https://thegraph.com/docs/en/developing/assemblyscript-api/)
- [CAIRN Protocol Docs](../../docs/)
- [PRD-03: Execution Intelligence](../../PRDs/PRD-03-EXECUTION-INTELLIGENCE/)
