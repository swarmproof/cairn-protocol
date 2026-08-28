'use client';

import { useEffect, useState } from 'react';
import { usePublicClient } from 'wagmi';
import { parseAbiItem } from 'viem';
import { CAIRN_CONTRACT_ADDRESS, cairnAbi, TaskState } from '@/lib/abi';
import { formatEth } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface Stats {
  totalCairns: number;
  recoveryRate: number | null; // null until there is data to compute it honestly
  totalEscrow: bigint;
}

export function LiveStats() {
  const publicClient = usePublicClient();
  const [stats, setStats] = useState<Stats>({
    totalCairns: 0,
    recoveryRate: null,
    totalEscrow: BigInt(0),
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isLiveData, setIsLiveData] = useState(false);

  useEffect(() => {
    async function fetchStats() {
      if (!publicClient) {
        setIsLoading(false);
        return;
      }

      try {
        // CairnCore emits TaskCreated (not TaskSubmitted).
        const createdLogs = await publicClient.getLogs({
          address: CAIRN_CONTRACT_ADDRESS,
          event: parseAbiItem(
            'event TaskCreated(bytes32 indexed taskId, bytes32 indexed taskType, address indexed operator, address primaryAgent, address fallbackAgent, uint256 escrow, uint256 deadline)'
          ),
          fromBlock: 'earliest',
          toBlock: 'latest',
        });

        const tasks = await Promise.all(
          createdLogs.map(async (log) => {
            const taskId = log.args.taskId as `0x${string}`;
            const result = await publicClient.readContract({
              address: CAIRN_CONTRACT_ADDRESS,
              abi: cairnAbi,
              functionName: 'getTask',
              args: [taskId],
            });
            return {
              state: result.state as TaskState,
              escrow: result.escrowAmount as bigint,
            };
          })
        );

        const failedTasks = tasks.filter(
          (t) =>
            t.state === TaskState.FAILED ||
            t.state === TaskState.RECOVERING ||
            t.state === TaskState.RESOLVED
        ).length;
        const resolvedTasks = tasks.filter((t) => t.state === TaskState.RESOLVED).length;
        const totalEscrow = tasks.reduce((sum, t) => sum + t.escrow, BigInt(0));

        setIsLiveData(true);
        setStats({
          totalCairns: failedTasks,
          // Only meaningful once at least one task has failed; otherwise unknown.
          recoveryRate: failedTasks > 0 ? Math.round((resolvedTasks / failedTasks) * 1000) / 10 : null,
          totalEscrow,
        });
      } catch (error) {
        // On error, show an honest empty state — never fabricated numbers.
        console.error('Error fetching stats:', error);
        setIsLiveData(false);
        setStats({ totalCairns: 0, recoveryRate: null, totalEscrow: BigInt(0) });
      } finally {
        setIsLoading(false);
      }
    }

    fetchStats();
  }, [publicClient]);

  const dash = '—';
  const statItems = [
    {
      value: isLiveData ? stats.totalCairns.toString() : dash,
      label: 'Cairns',
      sublabel: '(total)',
    },
    {
      value: isLiveData && stats.recoveryRate !== null ? `${stats.recoveryRate}%` : dash,
      label: 'Recovery',
      sublabel: 'Rate',
    },
    {
      value: isLiveData ? `${formatEth(stats.totalEscrow)} ETH` : dash,
      label: 'Escrow',
      sublabel: '(total)',
    },
  ];

  return (
    <section className="py-12 border-y bg-muted/30">
      <div className="container">
        <div className="grid grid-cols-3 gap-6 max-w-2xl mx-auto">
          {statItems.map((item, index) => (
            <div
              key={index}
              className={cn(
                'text-center p-4 rounded-xl bg-background/50 border transition-all',
                isLoading && 'animate-pulse'
              )}
            >
              <div className="text-3xl md:text-4xl font-bold mb-1">
                {isLoading ? dash : item.value}
              </div>
              <div className="text-sm text-muted-foreground mb-1">
                {item.label}
                <br />
                <span className="text-xs">{item.sublabel}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-center gap-2 mt-6 text-sm text-muted-foreground">
          <span
            className={cn(
              'w-2 h-2 rounded-full animate-pulse',
              isLiveData && stats.totalCairns > 0 ? 'bg-green-500' : 'bg-yellow-500'
            )}
          />
          {isLiveData && stats.totalCairns > 0
            ? 'Live from Base Sepolia'
            : 'No tasks on-chain yet (Base Sepolia)'}
        </div>
      </div>
    </section>
  );
}
