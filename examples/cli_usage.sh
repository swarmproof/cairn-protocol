#!/bin/bash
# CAIRN CLI Usage Examples
#
# This script demonstrates common CLI workflows.
# Make sure to set environment variables in contracts/.env before running.

set -e

echo "=== CAIRN CLI Usage Examples ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PRIMARY_AGENT="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
FALLBACK_AGENT="0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199"
TASK_CID="QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
ESCROW="0.1"
HEARTBEAT_INTERVAL=60
DEADLINE=$(($(date +%s) + 86400))  # 24 hours from now

echo -e "${BLUE}1. Check Protocol Information${NC}"
cairn admin info
echo ""

echo -e "${BLUE}2. Submit a New Task${NC}"
echo -e "${YELLOW}Command:${NC} cairn task submit \\"
echo "  --primary-agent $PRIMARY_AGENT \\"
echo "  --fallback-agent $FALLBACK_AGENT \\"
echo "  --task-cid $TASK_CID \\"
echo "  --escrow $ESCROW \\"
echo "  --heartbeat-interval $HEARTBEAT_INTERVAL \\"
echo "  --deadline $DEADLINE"
echo ""

# Uncomment to actually submit:
# TASK_ID=$(cairn task submit \
#   --primary-agent "$PRIMARY_AGENT" \
#   --fallback-agent "$FALLBACK_AGENT" \
#   --task-cid "$TASK_CID" \
#   --escrow "$ESCROW" \
#   --heartbeat-interval "$HEARTBEAT_INTERVAL" \
#   --deadline "$DEADLINE" | grep "Task ID" | cut -d: -f2 | tr -d ' ')
# echo "Created Task ID: $TASK_ID"

# For demo purposes, use a placeholder
TASK_ID="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
echo -e "${GREEN}(Using placeholder Task ID for demo)${NC}"
echo ""

echo -e "${BLUE}3. Check Task Status${NC}"
echo -e "${YELLOW}Command:${NC} cairn task status $TASK_ID"
# cairn task status "$TASK_ID"
echo ""

echo -e "${BLUE}4. Send Heartbeat (Primary Agent)${NC}"
echo -e "${YELLOW}Command:${NC} cairn task heartbeat $TASK_ID"
# cairn task heartbeat "$TASK_ID"
echo ""

echo -e "${BLUE}5. Commit Checkpoint (Primary Agent)${NC}"
CHECKPOINT_CID="QmCheckpoint1234567890abcdef1234567890abcdef123"
echo -e "${YELLOW}Command:${NC} cairn task checkpoint $TASK_ID --cid $CHECKPOINT_CID"
# cairn task checkpoint "$TASK_ID" --cid "$CHECKPOINT_CID"
echo ""

echo -e "${BLUE}6. Commit Multiple Checkpoints${NC}"
for i in {1..3}; do
    CID="QmCheckpoint${i}abcdef1234567890abcdef1234567890"
    echo -e "${YELLOW}Checkpoint $i:${NC} cairn task checkpoint $TASK_ID --cid $CID"
    # cairn task checkpoint "$TASK_ID" --cid "$CID"
done
echo ""

echo -e "${BLUE}7. Check Updated Task Status${NC}"
echo -e "${YELLOW}Command:${NC} cairn task status $TASK_ID"
# cairn task status "$TASK_ID"
echo ""

echo -e "${BLUE}8. Settle Task (After Completion)${NC}"
echo -e "${YELLOW}Command:${NC} cairn task settle $TASK_ID"
# cairn task settle "$TASK_ID"
echo ""

echo -e "${BLUE}9. Failure Recovery Workflow${NC}"
echo -e "${YELLOW}Scenario:${NC} Task fails, needs recovery"
echo ""
echo -e "${YELLOW}Step 1 - Fail Task:${NC} cairn task fail $TASK_ID"
# cairn task fail "$TASK_ID"
echo ""
echo -e "${YELLOW}Step 2 - Initiate Recovery:${NC} cairn task recover $TASK_ID"
# cairn task recover "$TASK_ID"
echo ""
echo -e "${YELLOW}Step 3 - Fallback Agent Sends Heartbeat:${NC} cairn task heartbeat $TASK_ID"
# cairn task heartbeat "$TASK_ID"
echo ""
echo -e "${YELLOW}Step 4 - Fallback Agent Commits Checkpoints:${NC}"
for i in {1..2}; do
    CID="QmFallbackCheckpoint${i}abcdef123456789"
    echo "  cairn task checkpoint $TASK_ID --cid $CID"
done
# cairn task checkpoint "$TASK_ID" --cid "QmFallbackCheckpoint1..."
# cairn task checkpoint "$TASK_ID" --cid "QmFallbackCheckpoint2..."
echo ""
echo -e "${YELLOW}Step 5 - Settle Recovered Task:${NC} cairn task settle $TASK_ID"
# cairn task settle "$TASK_ID"
echo ""

echo -e "${BLUE}10. Advanced Usage - Scripting${NC}"
echo -e "${YELLOW}Example:${NC} Monitor task until deadline"
cat << 'EOF'
#!/bin/bash
TASK_ID="0x..."
while true; do
    STATUS=$(cairn task status $TASK_ID --json | jq -r '.state')
    if [[ "$STATUS" == "RESOLVED" ]] || [[ "$STATUS" == "FAILED" ]]; then
        echo "Task completed with status: $STATUS"
        break
    fi
    echo "Task still running..."
    sleep 60
done
EOF
echo ""

echo -e "${GREEN}=== CLI Examples Complete ===${NC}"
echo ""
echo -e "${BLUE}To run these commands:${NC}"
echo "1. Set environment variables in contracts/.env"
echo "2. Uncomment the command lines in this script"
echo "3. Run: bash examples/cli_usage.sh"
echo ""
echo -e "${BLUE}For help on any command:${NC}"
echo "  cairn --help"
echo "  cairn task --help"
echo "  cairn task submit --help"
