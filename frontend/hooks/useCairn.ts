'use client';

import { useReadContract, useWriteContract, useWatchContractEvent, useAccount } from 'wagmi';
import { useQueryClient } from '@tanstack/react-query';
import { cairnAbi, CAIRN_CONTRACT_ADDRESS, TaskState } from '@/lib/abi';
import { parseEther } from 'viem';

// Types
export interface Task {
  taskId: `0x${string}`;
  state: TaskState;
  operator: `0x${string}`;
  primaryAgent: `0x${string}`;
  fallbackAgent: `0x${string}`;
  escrow: bigint;
  primaryCheckpoints: bigint;
  fallbackCheckpoints: bigint;
  lastHeartbeat: bigint;
  deadline: bigint;
}

// Hook to read a single task
export function useTask(taskId: `0x${string}` | undefined) {
  const { data, isLoading, error, refetch } = useReadContract({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    functionName: 'getTask',
    args: taskId ? [taskId] : undefined,
    query: {
      enabled: !!taskId,
    },
  });

  const task: Task | undefined = data ? {
    taskId: taskId!,
    state: data[0] as TaskState,
    operator: data[1],
    primaryAgent: data[2],
    fallbackAgent: data[3],
    escrow: data[4],
    primaryCheckpoints: data[5],
    fallbackCheckpoints: data[6],
    lastHeartbeat: data[7],
    deadline: data[8],
  } : undefined;

  return { task, isLoading, error, refetch };
}

// Hook to get checkpoints for a task
export function useCheckpoints(taskId: `0x${string}` | undefined) {
  const { data, isLoading, error, refetch } = useReadContract({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    functionName: 'getCheckpoints',
    args: taskId ? [taskId] : undefined,
    query: {
      enabled: !!taskId,
    },
  });

  return { checkpoints: data as `0x${string}`[] | undefined, isLoading, error, refetch };
}

// Hook to check if task is stale
export function useIsStale(taskId: `0x${string}` | undefined) {
  const { data, isLoading, refetch } = useReadContract({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    functionName: 'isStale',
    args: taskId ? [taskId] : undefined,
    query: {
      enabled: !!taskId,
      refetchInterval: 5000, // Check every 5 seconds
    },
  });

  return { isStale: data as boolean | undefined, isLoading, refetch };
}

// Hook to submit a new task
export function useSubmitTask() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const submitTask = async (
    primaryAgent: `0x${string}`,
    fallbackAgent: `0x${string}`,
    specHash: `0x${string}`,
    heartbeatInterval: bigint,
    deadline: bigint,
    escrowEth: string
  ) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'submitTask',
      args: [primaryAgent, fallbackAgent, specHash, heartbeatInterval, deadline],
      value: parseEther(escrowEth),
    });
  };

  return { submitTask, isPending, error };
}

// Hook to send heartbeat
export function useHeartbeat() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const heartbeat = async (taskId: `0x${string}`) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'heartbeat',
      args: [taskId],
    });
  };

  return { heartbeat, isPending, error };
}

// Hook to check liveness (trigger failure)
export function useCheckLiveness() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const checkLiveness = async (taskId: `0x${string}`) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'checkLiveness',
      args: [taskId],
    });
  };

  return { checkLiveness, isPending, error };
}

// Hook to complete task
export function useCompleteTask() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const completeTask = async (taskId: `0x${string}`) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'completeTask',
      args: [taskId],
    });
  };

  return { completeTask, isPending, error };
}

// Hook to settle task
export function useSettle() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const settle = async (taskId: `0x${string}`) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'settle',
      args: [taskId],
    });
  };

  return { settle, isPending, error };
}

// Hook to commit checkpoint
export function useCommitCheckpoint() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const commitCheckpoint = async (taskId: `0x${string}`, cid: `0x${string}`) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'commitCheckpoint',
      args: [taskId, cid],
    });
  };

  return { commitCheckpoint, isPending, error };
}

// Hook to watch task events for real-time updates
export function useTaskEvents(taskId?: `0x${string}`) {
  const queryClient = useQueryClient();

  // Watch TaskSubmitted events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'TaskSubmitted',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch TaskFailed events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'TaskFailed',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch TaskResolved events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'TaskResolved',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch CheckpointCommitted events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'CheckpointCommitted',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch HeartbeatReceived events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'HeartbeatReceived',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });
}
