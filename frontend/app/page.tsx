'use client';

import { useState, useEffect } from 'react';
import { useAccount, usePublicClient } from 'wagmi';
import { Header } from '@/components/Header';
import { TaskList } from '@/components/TaskList';
import { DemoControls } from '@/components/DemoControls';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cairnAbi, CAIRN_CONTRACT_ADDRESS, TaskState } from '@/lib/abi';
import { Task, useTaskEvents } from '@/hooks/useCairn';
import { Activity, CheckCircle, XCircle, RefreshCw, Coins } from 'lucide-react';
import { formatEth } from '@/lib/utils';
import { parseAbiItem } from 'viem';

export default function Dashboard() {
  const { address, isConnected } = useAccount();
  const publicClient = usePublicClient();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);

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
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container py-8">
        {/* Hero section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">CAIRN Protocol Dashboard</h1>
          <p className="text-muted-foreground">
            Agent failure & recovery protocol with checkpoint-based escrow settlement
          </p>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Activity className="h-4 w-4" />
                <span className="text-xs">Total Tasks</span>
              </div>
              <p className="text-2xl font-bold">{stats.total}</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-blue-400 mb-1">
                <Activity className="h-4 w-4" />
                <span className="text-xs">Running</span>
              </div>
              <p className="text-2xl font-bold">{stats.running}</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-amber-400 mb-1">
                <RefreshCw className="h-4 w-4" />
                <span className="text-xs">Recovering</span>
              </div>
              <p className="text-2xl font-bold">{stats.recovering}</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-green-400 mb-1">
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

        {/* Main content grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Task list */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Tasks</CardTitle>
              </CardHeader>
              <CardContent>
                <TaskList tasks={tasks} isLoading={isLoading} />
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Demo controls */}
            <DemoControls onTaskCreated={handleTaskCreated} />

            {/* Protocol info */}
            <Card>
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
                    className="text-blue-400 hover:underline text-xs"
                  >
                    View on Basescan →
                  </a>
                </div>
              </CardContent>
            </Card>

            {/* How it works */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">How It Works</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <p>
                  <strong className="text-foreground">1. Submit Task</strong>
                  <br />
                  Operator locks escrow, assigns primary & fallback agents
                </p>
                <p>
                  <strong className="text-foreground">2. Execute & Checkpoint</strong>
                  <br />
                  Agent commits progress to IPFS, sends heartbeats
                </p>
                <p>
                  <strong className="text-foreground">3. Failure Detection</strong>
                  <br />
                  Missed heartbeat triggers FAILED state
                </p>
                <p>
                  <strong className="text-foreground">4. Recovery</strong>
                  <br />
                  Fallback agent resumes from last checkpoint
                </p>
                <p>
                  <strong className="text-foreground">5. Settlement</strong>
                  <br />
                  Escrow split proportionally based on verified work
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
