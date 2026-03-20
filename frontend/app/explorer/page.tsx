'use client';

import { useState, useEffect } from 'react';
import { useAccount, usePublicClient } from 'wagmi';
import { TaskList } from '@/components/TaskList';
import { DemoControls } from '@/components/DemoControls';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cairnAbi, CAIRN_CONTRACT_ADDRESS, TaskState } from '@/lib/abi';
import { Task, useTaskEvents } from '@/hooks/useCairn';
import { Activity, CheckCircle, RefreshCw, Coins, Search, Filter } from 'lucide-react';
import { formatEth } from '@/lib/utils';
import { parseAbiItem } from 'viem';
import { Spotlight } from '@/components/ui/spotlight';
import { BorderBeam } from '@/components/ui/border-beam';

export default function ExplorerPage() {
  const { address, isConnected } = useAccount();
  const publicClient = usePublicClient();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [stateFilter, setStateFilter] = useState<TaskState | 'all'>('all');

  // Watch for real-time events
  useTaskEvents();

  // Fetch tasks from events
  useEffect(() => {
    async function fetchTasks() {
      if (!publicClient) return;

      setIsLoading(true);
      try {
        // Get TaskSubmitted events
        const logs = await publicClient.getLogs({
          address: CAIRN_CONTRACT_ADDRESS,
          event: parseAbiItem('event TaskSubmitted(bytes32 indexed taskId, address indexed operator, address primaryAgent, address fallbackAgent, uint256 escrow)'),
          fromBlock: 'earliest',
          toBlock: 'latest',
        });

        // Fetch task details for each event
        const taskPromises = logs.map(async (log) => {
          const taskId = log.args.taskId as `0x${string}`;
          const result = await publicClient.readContract({
            address: CAIRN_CONTRACT_ADDRESS,
            abi: cairnAbi,
            functionName: 'getTask',
            args: [taskId],
          });

          return {
            taskId,
            state: result[0] as TaskState,
            operator: result[1],
            primaryAgent: result[2],
            fallbackAgent: result[3],
            escrow: result[4],
            primaryCheckpoints: result[5],
            fallbackCheckpoints: result[6],
            lastHeartbeat: result[7],
            deadline: result[8],
          } as Task;
        });

        const fetchedTasks = await Promise.all(taskPromises);
        // Sort by most recent first (reverse order of events)
        setTasks(fetchedTasks.reverse());
      } catch (error) {
        console.error('Error fetching tasks:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchTasks();
  }, [publicClient]);

  const handleTaskCreated = () => {
    // Refetch tasks after a new one is created
    setTimeout(() => {
      window.location.reload();
    }, 2000);
  };

  // Filter tasks by state
  const filteredTasks = stateFilter === 'all'
    ? tasks
    : tasks.filter(t => t.state === stateFilter);

  // Calculate stats
  const stats = {
    total: tasks.length,
    running: tasks.filter(t => t.state === TaskState.RUNNING).length,
    failed: tasks.filter(t => t.state === TaskState.FAILED).length,
    recovering: tasks.filter(t => t.state === TaskState.RECOVERING).length,
    resolved: tasks.filter(t => t.state === TaskState.RESOLVED).length,
    totalEscrow: tasks.reduce((sum, t) => sum + t.escrow, BigInt(0)),
  };

  return (
    <div className="container py-8">
      {/* Page Header with Spotlight */}
      <div className="relative mb-8 p-6 rounded-2xl bg-black/[0.96] border border-slate-800 overflow-hidden">
        <Spotlight className="-top-40 left-0 md:left-20 md:-top-20" fill="rgba(217, 119, 6, 0.12)" />
        <div className="relative z-10">
          <h1 className="text-3xl font-bold mb-2 text-white">Task Explorer</h1>
          <p className="text-slate-400">
            Monitor live tasks and interact with the CAIRN Protocol on Base Sepolia
          </p>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <Card className="cursor-pointer hover:border-primary/50 transition-colors" onClick={() => setStateFilter('all')}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Activity className="h-4 w-4" />
              <span className="text-xs">Total Tasks</span>
            </div>
            <p className="text-2xl font-bold">{stats.total}</p>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-amber-500/50 transition-colors" onClick={() => setStateFilter(TaskState.RUNNING)}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-amber-400 mb-1">
              <Activity className="h-4 w-4 animate-pulse" />
              <span className="text-xs">Running</span>
            </div>
            <p className="text-2xl font-bold">{stats.running}</p>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-amber-500/50 transition-colors" onClick={() => setStateFilter(TaskState.RECOVERING)}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-amber-400 mb-1">
              <RefreshCw className="h-4 w-4" />
              <span className="text-xs">Recovering</span>
            </div>
            <p className="text-2xl font-bold">{stats.recovering}</p>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-stone-500/50 transition-colors" onClick={() => setStateFilter(TaskState.RESOLVED)}>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-stone-400 mb-1">
              <CheckCircle className="h-4 w-4" />
              <span className="text-xs">Resolved</span>
            </div>
            <p className="text-2xl font-bold">{stats.resolved}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Coins className="h-4 w-4" />
              <span className="text-xs">Total Escrow</span>
            </div>
            <p className="text-2xl font-bold">{formatEth(stats.totalEscrow)} ETH</p>
          </CardContent>
        </Card>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <span className="text-sm text-muted-foreground flex items-center gap-1">
          <Filter className="h-4 w-4" />
          Filter:
        </span>
        {['all', TaskState.RUNNING, TaskState.FAILED, TaskState.RECOVERING, TaskState.RESOLVED].map((state) => (
          <button
            key={state.toString()}
            onClick={() => setStateFilter(state as TaskState | 'all')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              stateFilter === state
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {state === 'all' ? 'All' :
             state === TaskState.RUNNING ? 'Running' :
             state === TaskState.FAILED ? 'Failed' :
             state === TaskState.RECOVERING ? 'Recovering' : 'Resolved'}
          </button>
        ))}
      </div>

      {/* Main content grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Task list */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Tasks</CardTitle>
                <span className="text-sm text-muted-foreground">
                  {filteredTasks.length} {stateFilter === 'all' ? 'total' : ''} task{filteredTasks.length !== 1 ? 's' : ''}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <TaskList tasks={filteredTasks} isLoading={isLoading} />
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Demo controls */}
          <DemoControls onTaskCreated={handleTaskCreated} />

          {/* Protocol info */}
          <Card className="relative overflow-hidden">
            <BorderBeam size={100} duration={12} colorFrom="#d97706" colorTo="#f59e0b" />
            <CardHeader>
              <CardTitle className="text-lg">Protocol Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Contract</span>
                <code className="text-xs">
                  {CAIRN_CONTRACT_ADDRESS.slice(0, 6)}...{CAIRN_CONTRACT_ADDRESS.slice(-4)}
                </code>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Network</span>
                <span>Base Sepolia</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Protocol Fee</span>
                <span>0.5%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Min Escrow</span>
                <span>0.001 ETH</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Min Heartbeat</span>
                <span>30 seconds</span>
              </div>
              <div className="pt-3 border-t">
                <a
                  href={`https://sepolia.basescan.org/address/${CAIRN_CONTRACT_ADDRESS}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-amber-400 hover:underline text-xs"
                >
                  View on Basescan →
                </a>
              </div>
            </CardContent>
          </Card>

          {/* State Machine Guide */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">State Machine</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-muted-foreground" />
                <span><strong>IDLE</strong> → Task created, not started</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                <span><strong>RUNNING</strong> → Agent actively executing</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                <span><strong>FAILED</strong> → Heartbeat missed</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span><strong>RECOVERING</strong> → Fallback agent active</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-stone-500" />
                <span><strong>DISPUTED</strong> → Arbiter reviewing</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-stone-400" />
                <span><strong>RESOLVED</strong> → Settled & complete</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
