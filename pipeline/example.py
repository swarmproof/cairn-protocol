"""
CAIRN Pipeline Example Usage

This script demonstrates how to run the Bonfires data pipeline.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.config import PipelineConfig
from pipeline.bonfires import BonfiresClient, BonfiresError
from pipeline.adapter import BonfiresAdapter
from pipeline.listener import EventListener
from pipeline.patterns import PatternDetector
from sdk.checkpoint import CheckpointStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_pipeline():
    """
    Run the complete Bonfires pipeline.

    This will:
    1. Connect to Base Sepolia RPC
    2. Listen for TaskFailed and TaskResolved events
    3. Create structured records
    4. Pin records to IPFS
    5. Index records in Bonfires
    6. Detect patterns in real-time
    """
    logger.info("🚀 Starting CAIRN Pipeline - Bonfires Integration")

    try:
        # Load configuration from environment
        logger.info("Loading configuration from environment...")
        config = PipelineConfig.from_env()
        config.validate()

        logger.info(f"✅ Configuration loaded:")
        logger.info(f"   Contract: {config.contract_address}")
        logger.info(f"   RPC: {config.rpc_url}")
        logger.info(f"   Bonfires Bonfire ID: {config.bonfires_bonfire_id}")
        logger.info(f"   Poll Interval: {config.poll_interval}s")

    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("Please check your .env file has all required variables:")
        logger.error("  - BONFIRES_API_KEY")
        logger.error("  - CAIRN_CONTRACT_ADDRESS")
        logger.error("  - PINATA_JWT")
        return

    # Initialize clients
    logger.info("Initializing clients...")

    ipfs = CheckpointStore(config.pinata_jwt)
    bonfires = BonfiresClient(config)

    # Create pattern detector with custom thresholds
    pattern_detector = PatternDetector(
        min_samples=10,  # Need at least 10 samples
        confidence_threshold=0.7,  # 70% confidence minimum
    )

    adapter = BonfiresAdapter(bonfires, ipfs, pattern_detector)
    listener = EventListener(config, adapter)

    logger.info("✅ All clients initialized")

    # Health checks
    logger.info("Running health checks...")

    try:
        await bonfires.health_check()
        logger.info("✅ Bonfires API is healthy")
    except BonfiresError as e:
        logger.error(f"❌ Bonfires health check failed: {e}")
        return

    health = await listener.health_check()
    if health["connected"]:
        logger.info(f"✅ Connected to chain ID {health['chain_id']}")
        logger.info(f"   Current block: {health['current_block']}")
    else:
        logger.error("❌ Failed to connect to RPC")
        return

    # Start listening
    logger.info("Starting event listener...")
    logger.info("Press Ctrl+C to stop\n")

    try:
        await listener.start()

    except KeyboardInterrupt:
        logger.info("\n⏸️  Stopping listener...")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

    finally:
        # Cleanup
        logger.info("Cleaning up...")
        await listener.stop()
        await ipfs.close()
        await bonfires.close()

        # Show final statistics
        stats = adapter.get_statistics()
        logger.info("\n📊 Final Statistics:")
        logger.info(f"   Total records processed: {stats['total_records']}")
        logger.info(f"   Failures: {stats['failure_count']}")
        logger.info(f"   Resolutions: {stats['resolution_count']}")
        logger.info(f"   Success rate: {stats['success_rate']:.1%}")

        logger.info("\n✅ Pipeline stopped cleanly")


async def query_example():
    """
    Example of querying intelligence from Bonfires.

    This demonstrates how agents can query historical data
    before starting a new task.
    """
    logger.info("🔍 Querying Intelligence Example")

    config = PipelineConfig.from_env()
    bonfires = BonfiresClient(config)

    try:
        # Example 1: Get task type statistics
        task_type = "defi.price_fetch"
        logger.info(f"\n📈 Getting stats for task type: {task_type}")

        stats = await bonfires.get_task_type_stats(task_type, lookback_hours=24)

        logger.info(f"   Total tasks (24h): {stats['total_tasks']}")
        logger.info(f"   Success rate: {stats['success_rate']:.1%}")
        logger.info(f"   Average cost: {stats['avg_cost_eth']} ETH")
        logger.info(f"   Average duration: {stats['avg_duration_blocks']} blocks")

        if stats["failure_patterns"]:
            logger.info("   Failure patterns:")
            for pattern in stats["failure_patterns"]:
                logger.info(f"      - {pattern['failure_type']}: {pattern['count']} occurrences")

        # Example 2: Get agent history
        # Replace with actual agent ID
        agent_id = "erc8004://base/0x1234567890123456789012345678901234567890"
        logger.info(f"\n👤 Getting history for agent: {agent_id[:30]}...")

        history = await bonfires.get_agent_history(agent_id, limit=50)

        logger.info(f"   Total tasks: {history['total_tasks']}")
        logger.info(f"   Successful: {history['successful_tasks']}")
        logger.info(f"   Failed: {history['failed_tasks']}")
        logger.info(f"   Success rate: {history['success_rate']:.1%}")

        # Example 3: Query specific records
        logger.info(f"\n📋 Querying recent failure records...")

        failures = await bonfires.query_records(
            record_type="failure",
            task_type=task_type,
            limit=10,
        )

        logger.info(f"   Found {len(failures)} failure records")
        for i, failure in enumerate(failures[:3], 1):
            logger.info(f"   {i}. Task: {failure.get('task_id', '')[:16]}...")
            logger.info(f"      Failure class: {failure.get('failure_class')}")
            logger.info(f"      Recovery score: {failure.get('recovery_score', 0):.2f}")

    except BonfiresError as e:
        logger.error(f"❌ Query failed: {e}")

    finally:
        await bonfires.close()

    logger.info("\n✅ Query example complete")


async def pattern_detection_example():
    """
    Example of pattern detection on collected records.
    """
    logger.info("🔬 Pattern Detection Example")

    config = PipelineConfig.from_env()
    bonfires = BonfiresClient(config)

    try:
        # Query recent records
        logger.info("Fetching recent records...")
        records = await bonfires.query_records(limit=100)

        logger.info(f"Found {len(records)} records")

        # Run pattern detection
        detector = PatternDetector(min_samples=10, confidence_threshold=0.6)

        for record in records:
            detector.add_record(record)

        logger.info("Running pattern detection...")
        patterns = detector.detect_patterns()

        logger.info(f"\n🎯 Detected {len(patterns)} patterns:\n")

        for pattern in patterns:
            severity_emoji = {
                "LOW": "ℹ️",
                "MEDIUM": "⚠️",
                "HIGH": "🔴",
                "CRITICAL": "🚨",
            }
            emoji = severity_emoji.get(pattern.severity.value, "📊")

            logger.info(f"{emoji} [{pattern.pattern_type.value}] {pattern.severity.value}")
            logger.info(f"   {pattern.description}")
            logger.info(f"   Confidence: {pattern.confidence:.1%}")
            logger.info(f"   Data: {pattern.data}\n")

    except BonfiresError as e:
        logger.error(f"❌ Pattern detection failed: {e}")

    finally:
        await bonfires.close()

    logger.info("✅ Pattern detection example complete")


async def main():
    """
    Main entry point.

    Choose which example to run based on command-line argument.
    """
    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "query":
            await query_example()
        elif mode == "patterns":
            await pattern_detection_example()
        elif mode == "pipeline":
            await run_pipeline()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python example.py [pipeline|query|patterns]")
            return
    else:
        # Default: run pipeline
        await run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
