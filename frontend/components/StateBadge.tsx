'use client';

import { Badge } from '@/components/ui/badge';
import { TaskState, stateConfig } from '@/lib/abi';

interface StateBadgeProps {
  state: TaskState;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
}

const stateVariant = {
  [TaskState.RUNNING]: 'running',
  [TaskState.FAILED]: 'failed',
  [TaskState.RECOVERING]: 'recovering',
  [TaskState.RESOLVED]: 'resolved',
} as const;

export function StateBadge({ state, size = 'md', pulse = false }: StateBadgeProps) {
  const config = stateConfig[state];
  const variant = stateVariant[state];

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-0.5',
    lg: 'text-base px-3 py-1',
  };

  return (
    <Badge
      variant={variant}
      className={`
        ${sizeClasses[size]}
        ${pulse && state === TaskState.RUNNING ? 'animate-pulse-slow' : ''}
      `}
    >
      {config.label}
    </Badge>
  );
}
