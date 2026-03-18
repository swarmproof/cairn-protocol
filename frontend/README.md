# CAIRN Protocol Frontend

Demo dashboard for the CAIRN Protocol — Agent failure & recovery with checkpoint-based escrow settlement.

## Features

- **Task Dashboard**: View all tasks with real-time state updates
- **State Machine Visualization**: Visual representation of task lifecycle
- **Checkpoint Viewer**: Inspect IPFS-stored checkpoints
- **Settlement Display**: See escrow distribution calculations
- **Demo Controls**: Interactive controls for testing the protocol

## Tech Stack

- **Next.js 14** with App Router
- **wagmi v2** + **viem** for Ethereum interactions
- **RainbowKit** for wallet connection
- **Tailwind CSS** for styling
- **Framer Motion** for animations

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm (recommended) or npm
- A wallet with Base Sepolia ETH

### Installation

```bash
# Install dependencies
pnpm install

# Copy environment file
cp .env.local.example .env.local

# Edit .env.local with your values
# - NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID: Get from cloud.walletconnect.com
```

### Development

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
pnpm build
pnpm start
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | WalletConnect Cloud project ID | Yes |
| `NEXT_PUBLIC_CAIRN_CONTRACT_ADDRESS` | Deployed contract address | No (defaults to Base Sepolia deployment) |
| `NEXT_PUBLIC_DEMO_MODE` | Enable demo controls | No (defaults to true) |
| `NEXT_PUBLIC_IPFS_GATEWAY` | IPFS gateway URL | No (defaults to Pinata) |

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx       # Root layout with providers
│   ├── page.tsx         # Dashboard home
│   ├── providers.tsx    # wagmi/RainbowKit providers
│   ├── globals.css      # Global styles
│   └── task/
│       └── [id]/
│           └── page.tsx # Task detail page
├── components/
│   ├── ui/              # Base UI components (shadcn-style)
│   ├── Header.tsx       # Navigation header
│   ├── TaskList.tsx     # Task listing component
│   ├── TaskDetail.tsx   # Full task view
│   ├── StateMachine.tsx # State visualization
│   ├── StateBadge.tsx   # State indicator badges
│   ├── Checkpoints.tsx  # Checkpoint viewer
│   ├── Settlement.tsx   # Settlement display
│   └── DemoControls.tsx # Demo interaction panel
├── hooks/
│   └── useCairn.ts      # Contract interaction hooks
├── lib/
│   ├── abi.ts           # Contract ABI and types
│   ├── utils.ts         # Utility functions
│   └── wagmi.ts         # wagmi configuration
└── public/
```

## Contract Interaction

The frontend interacts with the deployed CairnTaskMVP contract on Base Sepolia:

- **Address**: `0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417`
- **Basescan**: [View Contract](https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417)

### Supported Actions

| Action | Description |
|--------|-------------|
| Submit Task | Create new task with escrow |
| Heartbeat | Send liveness signal |
| Commit Checkpoint | Save progress to IPFS |
| Check Liveness | Trigger failure if stale |
| Complete Task | Mark task as done |
| Settle | Distribute escrow |

## Demo Mode

When `NEXT_PUBLIC_DEMO_MODE=true`, the dashboard shows interactive controls for:

1. **Creating tasks** with test escrow
2. **Sending heartbeats** to keep tasks alive
3. **Committing checkpoints** to simulate progress
4. **Triggering failures** by detecting stale heartbeats
5. **Completing and settling** tasks

This enables judges and testers to experience the full protocol flow without running agents.

## License

BUSL-1.1 — See main repository LICENSE file.
