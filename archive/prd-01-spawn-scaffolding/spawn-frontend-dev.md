# Spawn Prompt: Frontend-Dev

> CAIRN MVP Demo Frontend Development

## CONTEXT

You are implementing the demo frontend for CAIRN protocol MVP — a visual dashboard that shows the protocol in action for hackathon judges.

**PRD Location**: `/PRDs/PRD-01-MVP-HACKATHON.md`
**Target Repo**: `cairn-protocol`
**Your Tasks**: 15-22 (Frontend & Demo phase)
**Depends On**: SDK ready (Task 14)

**Read First** (understand existing patterns):
- PRD Section 2.7 (User Workflows)
- PRD Appendix A (Demo Script)
- `docs/concepts.md` — Glossary, state labels, failure class labels, recovery score display conventions
- wagmi docs: https://wagmi.sh/
- shadcn/ui: https://ui.shadcn.com/

## SCOPE

**Directory Structure to Create**:
```
cairn-protocol/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Dashboard
│   │   └── task/
│   │       └── [id]/
│   │           └── page.tsx   # Task detail
│   ├── components/
│   │   ├── TaskList.tsx
│   │   ├── TaskDetail.tsx
│   │   ├── StateMachine.tsx   # Visual state diagram
│   │   ├── Checkpoints.tsx
│   │   ├── Settlement.tsx
│   │   ├── DemoControls.tsx   # Inject failure, etc.
│   │   └── ui/                # shadcn components
│   ├── lib/
│   │   ├── cairn.ts           # Contract interaction
│   │   └── utils.ts
│   ├── hooks/
│   │   └── useCairn.ts
│   ├── package.json
│   ├── next.config.js
│   └── tailwind.config.js
```

## YOUR TASKS

### Task 15: Setup Next.js + wagmi
**Files**: `frontend/`, `package.json`, configs
**Acceptance**:
- [ ] Next.js 14 with App Router
- [ ] wagmi + viem configured for Base Sepolia
- [ ] RainbowKit for wallet connection
- [ ] Tailwind CSS + shadcn/ui installed
- [ ] `npm run dev` starts successfully

### Task 16: Task List Component
**Files**: `components/TaskList.tsx`
**Acceptance**:
- [ ] Lists all tasks from contract
- [ ] Shows: task ID (truncated), state, escrow, agent addresses
- [ ] Color-coded state badges (green=RESOLVED, red=FAILED, yellow=RECOVERING)
- [ ] Click to navigate to task detail
- [ ] Real-time updates via event subscription

### Task 17: Task Detail Component
**Files**: `components/TaskDetail.tsx`, `app/task/[id]/page.tsx`
**Acceptance**:
- [ ] Shows full task information
- [ ] Embeds StateMachine, Checkpoints, Settlement components
- [ ] Real-time state updates
- [ ] Shows timeline of events

### Task 18: State Machine Visualization
**Files**: `components/StateMachine.tsx`
**Acceptance**:
- [ ] Visual diagram of 4 states
- [ ] Current state highlighted
- [ ] Animated transitions
- [ ] Shows which transitions are possible from current state

**Design**:
```
┌─────────┐    ┌────────┐    ┌────────────┐    ┌──────────┐
│ RUNNING │───►│ FAILED │───►│ RECOVERING │───►│ RESOLVED │
└─────────┘    └────────┘    └────────────┘    └──────────┘
     │                                               ▲
     └───────────────────────────────────────────────┘
```

### Task 19: Demo Control Panel
**Files**: `components/DemoControls.tsx`
**Acceptance**:
- [ ] "Submit Task" button (opens modal with params)
- [ ] "Inject Failure" button (stops heartbeat simulation)
- [ ] "Trigger Recovery" button (calls checkLiveness)
- [ ] "Settle" button (calls settle)
- [ ] Only visible in demo mode (env flag)

### Task 20: Checkpoint Viewer
**Files**: `components/Checkpoints.tsx`
**Acceptance**:
- [ ] Lists all checkpoints with index, CID, agent
- [ ] Shows which agent committed each checkpoint
- [ ] Click to view checkpoint content (fetch from IPFS)
- [ ] Visual indicator: primary vs fallback checkpoints

### Task 21: Settlement Display
**Files**: `components/Settlement.tsx`
**Acceptance**:
- [ ] Shows escrow amount
- [ ] Pie chart or bar showing split (primary vs fallback vs protocol)
- [ ] Actual ETH amounts displayed
- [ ] Transaction hash link to Basescan

### Task 22: Deploy to Vercel
**Files**: CI/CD config, environment
**Acceptance**:
- [ ] Deployed to Vercel
- [ ] Environment variables configured
- [ ] Working on custom domain or vercel.app subdomain
- [ ] Production build optimized

## BOUNDARIES

**Do NOT**:
- Build a full admin panel (this is a demo dashboard)
- Add user authentication (wallet connection is enough)
- Support multiple networks (Base Sepolia only)
- Over-engineer — this is a 2-day build

**Do**:
- Prioritize visual clarity for judges
- Make the demo flow obvious and guided
- Use animations to show state transitions
- Handle loading and error states gracefully
- Mobile-responsive (judges may view on phone)

## SUCCESS CRITERIA

1. **Runs**: `npm run dev` works, no errors
2. **Connects**: Wallet connects to Base Sepolia
3. **Shows**: Tasks list and detail pages work
4. **Demo**: Full demo script executable via UI
5. **Deploys**: Live on Vercel

## PATTERNS TO FOLLOW

**wagmi Hook Pattern**:
```typescript
import { useContractRead, useContractWrite } from 'wagmi'
import { cairnAbi } from '@/lib/abi'

export function useTask(taskId: string) {
  const { data, isLoading } = useContractRead({
    address: CAIRN_ADDRESS,
    abi: cairnAbi,
    functionName: 'getTask',
    args: [taskId],
  })

  return { task: data, isLoading }
}
```

**State Badge Component** (see `docs/concepts.md` for display labels):
```typescript
// Use display labels from docs/concepts.md Glossary
const stateConfig = {
  RUNNING: { color: 'bg-blue-500', label: 'In Progress' },
  FAILED: { color: 'bg-red-500', label: 'Failed' },
  RECOVERING: { color: 'bg-yellow-500', label: 'Recovering' },
  RESOLVED: { color: 'bg-green-500', label: 'Completed' },
}

function StateBadge({ state }: { state: string }) {
  const config = stateConfig[state]
  return (
    <span className={`px-2 py-1 rounded text-white ${config.color}`}>
      {config.label}
    </span>
  )
}
```

**Real-time Events**:
```typescript
useContractEvent({
  address: CAIRN_ADDRESS,
  abi: cairnAbi,
  eventName: 'TaskFailed',
  listener(log) {
    // Update UI when task fails
    refetchTasks()
  },
})
```

## HANDOFF

When complete, update `PRD-01-STATUS.md`:
- Mark tasks 15-22 as ✅
- Add Vercel URL
- Unblock Integration (tasks 23-26)

Notify: "Frontend deployed at [URL]. Ready for E2E testing."
