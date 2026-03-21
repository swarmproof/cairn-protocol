# Bonfires Pipeline - Quick Start Guide

Get the CAIRN Bonfires pipeline running in 5 minutes.

## Prerequisites

- Python 3.10+
- Access to Bonfires API (API key)
- Pinata account (for IPFS)
- Base Sepolia RPC access

## Step 1: Install Dependencies

```bash
cd cairn-protocol
pip install -r sdk/requirements.txt
pip install -r pipeline/requirements.txt
```

## Step 2: Configure Environment

Create `.env` file in project root:

```env
# Bonfires API
BONFIRES_API_KEY=your_bonfires_api_key_here

# CAIRN Contract (Base Sepolia)
CAIRN_CONTRACT_ADDRESS=0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417

# IPFS (Pinata)
PINATA_JWT=your_pinata_jwt_here

# Optional - defaults provided
RPC_URL=https://sepolia.base.org
START_BLOCK=0
POLL_INTERVAL=5
```

### Get Your API Keys

1. **Bonfires API Key**: Visit [Bonfires Dashboard](https://bonfires.ai/) and create an API key
2. **Pinata JWT**: Go to [Pinata Developers](https://app.pinata.cloud/developers/api-keys) and create a new API key

## Step 3: Test Configuration

```bash
cd pipeline
python -c "from config import PipelineConfig; config = PipelineConfig.from_env(); config.validate(); print('✅ Configuration valid')"
```

## Step 4: Run the Pipeline

```bash
python example.py pipeline
```

You should see:

```
🚀 Starting CAIRN Pipeline - Bonfires Integration
Loading configuration from environment...
✅ Configuration loaded:
   Contract: 0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417
   RPC: https://sepolia.base.org
   Bonfires Room: cairn-failures
   Poll Interval: 5s
Initializing clients...
✅ All clients initialized
Running health checks...
✅ Bonfires API is healthy
✅ Connected to chain ID 84532
   Current block: 12345678
Starting event listener...
Press Ctrl+C to stop
```

## Step 5: Test Pattern Detection (Optional)

In a separate terminal, query intelligence:

```bash
python example.py query
```

Or run pattern detection:

```bash
python example.py patterns
```

## Usage Examples

### Query Task Type Statistics

```python
from pipeline.config import PipelineConfig
from pipeline.bonfires import BonfiresClient
import asyncio

async def main():
    config = PipelineConfig.from_env()
    async with BonfiresClient(config) as client:
        stats = await client.get_task_type_stats("defi.price_fetch")
        print(f"Success rate: {stats['success_rate']:.1%}")
        print(f"Average cost: {stats['avg_cost_eth']} ETH")

asyncio.run(main())
```

### Query Agent History

```python
async def main():
    config = PipelineConfig.from_env()
    async with BonfiresClient(config) as client:
        history = await client.get_agent_history(
            "erc8004://base/0x1234567890123456789012345678901234567890"
        )
        print(f"Total tasks: {history['total_tasks']}")
        print(f"Success rate: {history['success_rate']:.1%}")

asyncio.run(main())
```

## Running Tests

```bash
# All tests
pytest pipeline/tests/ -v

# Specific test file
pytest pipeline/tests/test_records.py -v

# With coverage
pytest pipeline/tests/ --cov=pipeline --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### "BONFIRES_API_KEY environment variable is required"

**Solution**: Ensure `.env` file exists in project root with valid `BONFIRES_API_KEY`.

### "Failed to connect to RPC"

**Solutions**:
1. Check `RPC_URL` is correct
2. Try public Base Sepolia RPC: `https://sepolia.base.org`
3. Verify network connectivity

### "Pinata request timed out"

**Solutions**:
1. Verify `PINATA_JWT` is valid
2. Create new JWT at https://app.pinata.cloud/developers/api-keys
3. Check PINATA_JWT has write permissions

### "Bonfires API error (401)"

**Solution**: Verify your `BONFIRES_API_KEY` is active and has correct permissions.

### No events detected

**Possible causes**:
1. No tasks have been submitted to the contract yet
2. `START_BLOCK` is set after all events occurred
3. Contract address is incorrect

**Solutions**:
1. Submit a test task using the SDK
2. Set `START_BLOCK=0` to scan from genesis
3. Verify contract address matches deployed contract

## Production Deployment

For production, run the pipeline as a system service:

### Using systemd (Linux)

Create `/etc/systemd/system/cairn-pipeline.service`:

```ini
[Unit]
Description=CAIRN Bonfires Pipeline
After=network.target

[Service]
Type=simple
User=cairn
WorkingDirectory=/opt/cairn-protocol
Environment="PATH=/opt/cairn-protocol/venv/bin"
ExecStart=/opt/cairn-protocol/venv/bin/python pipeline/example.py pipeline
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable cairn-pipeline
sudo systemctl start cairn-pipeline
sudo systemctl status cairn-pipeline
```

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install -r sdk/requirements.txt && \
    pip install -r pipeline/requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["python", "pipeline/example.py", "pipeline"]
```

Build and run:

```bash
docker build -t cairn-pipeline .
docker run --env-file .env cairn-pipeline
```

## Monitoring

The pipeline logs to stdout. Capture logs using:

```bash
# Write to file
python example.py pipeline > pipeline.log 2>&1

# With log rotation
python example.py pipeline | rotatelogs pipeline-%Y-%m-%d.log 86400
```

## Next Steps

1. ✅ Pipeline running and processing events
2. 📊 Check Bonfires dashboard for indexed records
3. 🔍 Query intelligence before submitting tasks
4. 📈 Monitor pattern detection alerts
5. 🚀 Integrate intelligence queries into your agents

## Support

- **Documentation**: See [README.md](README.md) for full details
- **Issues**: Open issues on GitHub
- **PRD**: See [PRD-03](../PRDs/PRD-03-EXECUTION-INTELLIGENCE/PRD.md) for specifications

---

**Built for CAIRN Protocol - Synthesis Hackathon 2026**
