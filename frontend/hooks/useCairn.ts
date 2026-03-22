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
    state: data.state as TaskState,
    operator: data.operator,
    primaryAgent: data.primaryAgent,
    fallbackAgent: data.fallbackAgent,
    escrow: data.escrowAmount,
    primaryCheckpoints: data.primaryCheckpoints,
    fallbackCheckpoints: data.fallbackCheckpoints,
    lastHeartbeat: data.lastHeartbeat,
    deadline: data.deadline,
  } : undefined;

  return { task, isLoading, error, refetch };
}

// Hook to get checkpoint batch roots for a task
export function useCheckpoints(taskId: `0x${string}` | undefined) {
  const { data, isLoading, error, refetch } = useReadContract({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    functionName: 'getBatchRoots',
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

// Hook to detect failure (trigger failure check)
export function useDetectFailure() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const detectFailure = async (taskId: `0x${string}`) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'detectFailure',
      args: [taskId],
    });
  };

  return { detectFailure, isPending, error };
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

// Note: Settlement happens automatically in CairnCore when task is completed
// The completeTask function handles both completion and settlement

// Hook to commit checkpoint batch
// Note: The contract uses batch commits with Merkle roots for gas efficiency
export function useCommitCheckpoint() {
  const { writeContractAsync, isPending, error } = useWriteContract();

  const commitCheckpoint = async (
    taskId: `0x${string}`,
    count: bigint,
    merkleRoot: `0x${string}`,
    latestCID: `0x${string}`
  ) => {
    return writeContractAsync({
      address: CAIRN_CONTRACT_ADDRESS,
      abi: cairnAbi,
      functionName: 'commitCheckpointBatch',
      args: [taskId, count, merkleRoot, latestCID],
    });
  };

  return { commitCheckpoint, isPending, error };
}

// Hook to watch task events for real-time updates
export function useTaskEvents(taskId?: `0x${string}`) {
  const queryClient = useQueryClient();

  // Watch TaskCreated events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'TaskCreated',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch TaskStarted events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'TaskStarted',
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

  // Watch TaskCompleted events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'TaskCompleted',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch TaskSettled events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'TaskSettled',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch CheckpointBatchCommitted events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'CheckpointBatchCommitted',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch Heartbeat events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'Heartbeat',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });

  // Watch RecoveryStarted events
  useWatchContractEvent({
    address: CAIRN_CONTRACT_ADDRESS,
    abi: cairnAbi,
    eventName: 'RecoveryStarted',
    onLogs: () => {
      queryClient.invalidateQueries({ queryKey: ['readContract'] });
    },
  });
}
