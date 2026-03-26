'use client';

import { useState, useEffect, useCallback } from 'react';

// Subgraph endpoint (from README)
const SUBGRAPH_ENDPOINT = 'https://api.studio.thegraph.com/query/1744842/cairn/v1.0.0';

// Types based on subgraph schema
export interface ProtocolStats {
  totalTasksCreated: bigint;
  totalTasksResolved: bigint;
  totalEscrowLocked: bigint;
  runningTasks: bigint;
  failedTasks: bigint;
  resolvedTasks: bigint;
  overallSuccessRate: number;
  avgCheckpointsPerTask: number;
}

export interface FailurePattern {
  id: string;
  taskType: string;
  failureClass: 'LIVENESS' | 'RESOURCE' | 'EXECUTION' | 'DEADLINE';
  occurrenceCount: bigint;
  avgRecoveryScore: number;
  recoveryRate: number;
  heartbeatMissCount: bigint;
  networkPartitionCount: bigint;
  rateLimitCount: bigint;
  gasExhaustedCount: bigint;
  validationFailedCount: bigint;
  lastOccurrence: bigint;
}

export interface TaskTypeStats {
  id: string;
  name: string;
  cairnCount: number;
  successRate: number;
  recentActivity: string;
  topFailure: string;
}

// GraphQL queries
const PROTOCOL_STATS_QUERY = `
  query GetProtocolStats {
    protocols(first: 1) {
      id
      totalTasksCreated
      totalTasksResolved
      totalEscrowLocked
      runningTasks
      failedTasks
      resolvedTasks
      overallSuccessRate
      avgCheckpointsPerTask
    }
  }
`;

const FAILURE_PATTERNS_QUERY = `
  query GetFailurePatterns {
    failurePatterns(first: 50, orderBy: occurrenceCount, orderDirection: desc) {
      id
      taskType
      failureClass
      occurrenceCount
      avgRecoveryScore
      recoveryRate
      heartbeatMissCount
      networkPartitionCount
      rateLimitCount
      gasExhaustedCount
      validationFailedCount
      lastOccurrence
    }
  }
`;

const DAILY_METRICS_QUERY = `
  query GetDailyMetrics($days: Int!) {
    dailyMetricss(first: $days, orderBy: date, orderDirection: desc) {
      id
      date
      tasksCreated
      tasksCompleted
      tasksFailed
      tasksRecovered
      successRate
      avgRecoveryScore
    }
  }
`;

// Fetch helper with error handling
async function fetchSubgraph<T>(query: string, variables?: Record<string, unknown>): Promise<T | null> {
  try {
    const response = await fetch(SUBGRAPH_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, variables }),
    });

    if (!response.ok) {
      console.error('Subgraph request failed:', response.status);
      return null;
    }

    const result = await response.json();

    if (result.errors) {
      console.error('Subgraph query errors:', result.errors);
      return null;
    }

    return result.data;
  } catch (error) {
    console.error('Failed to fetch from subgraph:', error);
    return null;
  }
}

// Hook to get protocol stats
export function useProtocolStats() {
  const [data, setData] = useState<ProtocolStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const result = await fetchSubgraph<{ protocols: Array<{
      totalTasksCreated: string;
      totalTasksResolved: string;
      totalEscrowLocked: string;
      runningTasks: string;
      failedTasks: string;
      resolvedTasks: string;
      overallSuccessRate: string;
      avgCheckpointsPerTask: string;
    }> }>(PROTOCOL_STATS_QUERY);

    if (result?.protocols?.[0]) {
      const p = result.protocols[0];
      setData({
        totalTasksCreated: BigInt(p.totalTasksCreated || '0'),
        totalTasksResolved: BigInt(p.totalTasksResolved || '0'),
        totalEscrowLocked: BigInt(p.totalEscrowLocked || '0'),
        runningTasks: BigInt(p.runningTasks || '0'),
        failedTasks: BigInt(p.failedTasks || '0'),
        resolvedTasks: BigInt(p.resolvedTasks || '0'),
        overallSuccessRate: parseFloat(p.overallSuccessRate || '0'),
        avgCheckpointsPerTask: parseFloat(p.avgCheckpointsPerTask || '0'),
      });
    } else {
      setError(new Error('No protocol data available'));
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

// Hook to get failure patterns
export function useFailurePatterns() {
  const [data, setData] = useState<FailurePattern[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const result = await fetchSubgraph<{ failurePatterns: Array<{
      id: string;
      taskType: string;
      failureClass: string;
      occurrenceCount: string;
      avgRecoveryScore: string;
      recoveryRate: string;
      heartbeatMissCount: string;
      networkPartitionCount: string;
      rateLimitCount: string;
      gasExhaustedCount: string;
      validationFailedCount: string;
      lastOccurrence: string;
    }> }>(FAILURE_PATTERNS_QUERY);

    if (result?.failurePatterns) {
      setData(result.failurePatterns.map(fp => ({
        id: fp.id,
        taskType: fp.taskType,
        failureClass: fp.failureClass as FailurePattern['failureClass'],
        occurrenceCount: BigInt(fp.occurrenceCount || '0'),
        avgRecoveryScore: parseFloat(fp.avgRecoveryScore || '0'),
        recoveryRate: parseFloat(fp.recoveryRate || '0'),
        heartbeatMissCount: BigInt(fp.heartbeatMissCount || '0'),
        networkPartitionCount: BigInt(fp.networkPartitionCount || '0'),
        rateLimitCount: BigInt(fp.rateLimitCount || '0'),
        gasExhaustedCount: BigInt(fp.gasExhaustedCount || '0'),
        validationFailedCount: BigInt(fp.validationFailedCount || '0'),
        lastOccurrence: BigInt(fp.lastOccurrence || '0'),
      })));
    } else {
      setError(new Error('No failure pattern data available'));
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

// Hook to get task type statistics (aggregated from failure patterns)
export function useTaskTypeStats() {
  const [data, setData] = useState<TaskTypeStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    // Fetch both protocol stats and failure patterns
    const [protocolResult, patternsResult] = await Promise.all([
      fetchSubgraph<{ protocols: Array<{ totalTasksCreated: string; overallSuccessRate: string }> }>(PROTOCOL_STATS_QUERY),
      fetchSubgraph<{ failurePatterns: Array<{
        id: string;
        taskType: string;
        failureClass: string;
        occurrenceCount: string;
        recoveryRate: string;
      }> }>(FAILURE_PATTERNS_QUERY),
    ]);

    // Aggregate by task type
    const taskTypeMap = new Map<string, {
      cairnCount: number;
      successRate: number;
      failures: { type: string; count: number }[];
    }>();

    if (patternsResult?.failurePatterns) {
      for (const fp of patternsResult.failurePatterns) {
        const taskType = decodeTaskType(fp.taskType);
        const existing = taskTypeMap.get(taskType) || {
          cairnCount: 0,
          successRate: parseFloat(fp.recoveryRate || '0') * 100,
          failures: []
        };

        existing.cairnCount += parseInt(fp.occurrenceCount || '0', 10);
        existing.failures.push({
          type: fp.failureClass,
          count: parseInt(fp.occurrenceCount || '0', 10),
        });

        taskTypeMap.set(taskType, existing);
      }
    }

    // Convert to array and sort by cairn count
    const stats: TaskTypeStats[] = Array.from(taskTypeMap.entries())
      .map(([name, data]) => {
        // Find top failure
        const topFailure = data.failures.sort((a, b) => b.count - a.count)[0];
        const totalFailures = data.failures.reduce((sum, f) => sum + f.count, 0);
        const topFailurePercent = topFailure
          ? Math.round((topFailure.count / totalFailures) * 100)
          : 0;

        return {
          id: name,
          name,
          cairnCount: data.cairnCount,
          successRate: Math.round(data.successRate),
          recentActivity: 'Live data', // Would need timestamp comparison
          topFailure: topFailure
            ? `${topFailure.type} (${topFailurePercent}%)`
            : 'N/A',
        };
      })
      .sort((a, b) => b.cairnCount - a.cairnCount);

    if (stats.length > 0) {
      setData(stats);
    } else {
      // No data from subgraph - return empty (will trigger fallback UI)
      setData([]);
      setError(new Error('No task type data available from subgraph'));
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, isLoading, error, refetch };
}

// Helper to decode bytes32 task type to string
function decodeTaskType(taskTypeHex: string): string {
  if (!taskTypeHex || taskTypeHex === '0x') return 'unknown';

  try {
    // Remove 0x prefix and trailing zeros
    const hex = taskTypeHex.replace('0x', '').replace(/0+$/, '');

    // Convert hex to string
    let result = '';
    for (let i = 0; i < hex.length; i += 2) {
      const charCode = parseInt(hex.substr(i, 2), 16);
      if (charCode > 0) {
        result += String.fromCharCode(charCode);
      }
    }

    return result || 'unknown';
  } catch {
    return taskTypeHex.slice(0, 10) + '...';
  }
}
