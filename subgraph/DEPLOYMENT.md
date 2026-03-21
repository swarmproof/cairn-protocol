# CAIRN Protocol Subgraph - Deployment Guide

This guide walks through deploying the CAIRN Protocol subgraph to The Graph network.

## Prerequisites

- Node.js 16+ installed
- The Graph CLI installed globally: `npm install -g @graphprotocol/graph-cli`
- CairnCore contract deployed on Base Sepolia
- Contract ABI available at `../contracts/out/CairnCore.sol/CairnCore.json`

## Deployment Steps

### 1. Initial Setup

```bash
# Navigate to subgraph directory
cd subgraph

# Install dependencies
npm install

# Extract ABI from compiled contract
node scripts/extract-abi.js
```

This should create `abis/CairnCore.json` with the contract ABI.

### 2. Verify Configuration

Check `subgraph.yaml` has correct values:

```yaml
source:
  address: "0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640"  # CairnCore contract
  startBlock: 17741070  # Deployment block
```

**Important**: Update `startBlock` to the actual deployment block to optimize indexing speed.

To find the deployment block:
```bash
# From contracts directory
cat broadcast/Deploy.s.sol/84532/run-latest.json | jq '.receipts[0].blockNumber'
```

### 3. Generate Types

```bash
npm run codegen
```

This generates TypeScript types from:
- `schema.graphql` → Entity types
- `abis/CairnCore.json` → Event types

Expected output:
```
  Generate types for data source templates
  Generate types for data sources
  Write types to generated/schema.ts
  Write types to generated/CairnCore/CairnCore.ts
```

### 4. Build

```bash
npm run build
```

Expected output:
```
  Compile data source: CairnCore => build/CairnCore/CairnCore.wasm
  Add file to IPFS: build/schema.graphql
  Add file to IPFS: build/CairnCore/CairnCore.wasm
```

### 5. Deploy to The Graph Studio

#### 5.1 Create Subgraph

1. Go to [https://thegraph.com/studio/](https://thegraph.com/studio/)
2. Connect your wallet
3. Click "Create a Subgraph"
4. Name it: `cairn-protocol` (or `cairn-protocol-sepolia` for testnet)
5. Select "base-sepolia" network

#### 5.2 Get Deploy Key

1. In the subgraph dashboard, click "Settings"
2. Copy the "Deploy Key"

#### 5.3 Authenticate

```bash
graph auth --studio <YOUR_DEPLOY_KEY>
```

#### 5.4 Deploy

```bash
npm run deploy
```

Or specify version:
```bash
graph deploy --studio cairn-protocol --version-label v0.1.0
```

### 6. Verify Deployment

After deployment, The Graph Studio will:
1. Upload your subgraph to IPFS
2. Begin syncing from `startBlock`
3. Index all historical events
4. Make your subgraph queryable

Check the dashboard for:
- ✅ **Syncing Status**: Should show "Synced" when complete
- ✅ **Current Block**: Should match chain head
- ✅ **Entities**: Should show Task, Agent, etc. counts

### 7. Test Queries

In The Graph Studio playground, test a simple query:

```graphql
{
  protocol(id: "0xb65596b21d670b6c670106c3e3c7e5fff8e3a640") {
    totalTasksCreated
    totalTasksResolved
    overallSuccessRate
  }
}
```

If you get data back, your subgraph is working!

## Local Development Deployment

For testing during development:

### 1. Start Local Graph Node

```bash
# Clone graph-node repo
git clone https://github.com/graphprotocol/graph-node
cd graph-node/docker

# Configure for Base Sepolia
# Edit docker-compose.yml to add Base Sepolia RPC

# Start services
docker-compose up
```

### 2. Deploy Locally

```bash
# Create subgraph
npm run create-local

# Deploy
npm run deploy-local
```

Query endpoint: `http://localhost:8000/subgraphs/name/cairn-protocol`

## Updating After Contract Changes

If CairnCore is redeployed or events change:

### 1. Update Configuration

```yaml
# subgraph.yaml
source:
  address: "0x<NEW_ADDRESS>"
  startBlock: <NEW_BLOCK>
```

### 2. Re-extract ABI

```bash
node scripts/extract-abi.js
```

### 3. Rebuild and Redeploy

```bash
npm run codegen
npm run build
npm run deploy -- --version-label v0.2.0
```

## Troubleshooting

### "Failed to extract ABI"

**Solution**: Ensure contract is compiled:
```bash
cd ../contracts
forge build
cd ../subgraph
node scripts/extract-abi.js
```

### "Network not supported"

**Solution**: The Graph Studio must support `base-sepolia`. If not available:
- Use local graph node with custom RPC
- Or deploy to Base mainnet when ready

### "Indexing failed"

**Possible causes**:
1. **Wrong start block**: Set to actual deployment block
2. **Contract address mismatch**: Verify address in `subgraph.yaml`
3. **Event signature mismatch**: Re-extract ABI after contract changes

Check logs in The Graph Studio for specific error.

### "Entity not found"

If queries return null:
- Check that events have been emitted (use block explorer)
- Verify subgraph has synced past those blocks
- Ensure entity IDs match what you're querying

## Performance Optimization

### Start Block

Set `startBlock` to deployment block (not 0) to speed up initial sync:

```bash
# Get deployment block
cast block-number --rpc-url $BASE_SEPOLIA_RPC

# Or from deployment receipt
cat ../contracts/broadcast/Deploy.s.sol/84532/run-latest.json | jq '.receipts[0].blockNumber'
```

### Indexing Speed

First sync may take:
- **1-5 minutes** for recent deployment (< 1000 blocks)
- **10-30 minutes** for older deployment (> 10000 blocks)

Monitor in The Graph Studio dashboard.

## Production Checklist

Before deploying to mainnet:

- [ ] Contract audited and deployed to Base mainnet
- [ ] `subgraph.yaml` network changed to `base`
- [ ] Start block set to mainnet deployment block
- [ ] ABI extracted from mainnet deployment
- [ ] Test queries validated on testnet subgraph
- [ ] Version labeled with semantic versioning
- [ ] Subgraph published (not just deployed)

## Publishing

After successful deployment and testing:

1. In The Graph Studio, click "Publish"
2. This makes your subgraph publicly discoverable
3. Users can query at: `https://api.studio.thegraph.com/query/<SUBGRAPH_ID>/cairn-protocol/<VERSION>`

## Cost Considerations

- **The Graph Studio**: Free for development/testing
- **Decentralized Network**: Requires GRT tokens for queries
- **Self-hosted**: Free but requires infrastructure

For CAIRN's MVP, The Graph Studio is sufficient.

## Support Resources

- [The Graph Discord](https://discord.gg/graphprotocol)
- [Documentation](https://thegraph.com/docs/)
- [GitHub Issues](https://github.com/graphprotocol/graph-node/issues)

## Next Steps

After successful deployment:

1. Integrate subgraph queries into frontend
2. Build analytics dashboard using query API
3. Set up monitoring/alerts for indexing health
4. Plan migration to decentralized network (for mainnet)
