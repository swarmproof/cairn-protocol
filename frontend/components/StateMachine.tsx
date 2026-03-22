'use client';

import { motion } from 'framer-motion';
import { ArrowRight, CheckCircle2, XCircle, RefreshCw, Play } from 'lucide-react';
import { TaskState, stateConfig } from '@/lib/abi';
import { cn } from '@/lib/utils';

interface StateMachineProps {
  currentState: TaskState;
  size?: 'sm' | 'md' | 'lg';
}

const states = [
  { state: TaskState.RUNNING, icon: Play, label: 'Running' },
  { state: TaskState.FAILED, icon: XCircle, label: 'Failed' },
  { state: TaskState.RECOVERING, icon: RefreshCw, label: 'Recovering' },
  { state: TaskState.RESOLVED, icon: CheckCircle2, label: 'Resolved' },
];

const stateColors = {
  [TaskState.IDLE]: 'border-stone-500 bg-stone-500/10 text-stone-400',
  [TaskState.RUNNING]: 'border-blue-500 bg-blue-500/10 text-blue-400',
  [TaskState.FAILED]: 'border-red-500 bg-red-500/10 text-red-400',
  [TaskState.RECOVERING]: 'border-amber-500 bg-amber-500/10 text-amber-400',
  [TaskState.DISPUTED]: 'border-purple-500 bg-purple-500/10 text-purple-400',
  [TaskState.RESOLVED]: 'border-green-500 bg-green-500/10 text-green-400',
};

const activeStateColors = {
  [TaskState.IDLE]: 'border-stone-500 bg-stone-500 text-white shadow-stone-500/50',
  [TaskState.RUNNING]: 'border-blue-500 bg-blue-500 text-white shadow-blue-500/50',
  [TaskState.FAILED]: 'border-red-500 bg-red-500 text-white shadow-red-500/50',
  [TaskState.RECOVERING]: 'border-amber-500 bg-amber-500 text-white shadow-amber-500/50',
  [TaskState.DISPUTED]: 'border-purple-500 bg-purple-500 text-white shadow-purple-500/50',
  [TaskState.RESOLVED]: 'border-green-500 bg-green-500 text-white shadow-green-500/50',
};

export function StateMachine({ currentState, size = 'md' }: StateMachineProps) {
  const sizeClasses = {
    sm: { node: 'w-20 h-10 text-xs', icon: 'h-3 w-3', gap: 'gap-2' },
    md: { node: 'w-28 h-12 text-sm', icon: 'h-4 w-4', gap: 'gap-4' },
    lg: { node: 'w-36 h-14 text-base', icon: 'h-5 w-5', gap: 'gap-6' },
  };

  const sizes = sizeClasses[size];

  return (
    <div className={cn('flex items-center justify-center', sizes.gap)}>
      {states.map((stateInfo, index) => {
        const Icon = stateInfo.icon;
        const isActive = currentState === stateInfo.state;
        const isPast = currentState > stateInfo.state;
        const isReachable =
          (currentState === TaskState.RUNNING && stateInfo.state !== TaskState.RECOVERING) ||
          (currentState === TaskState.FAILED && stateInfo.state === TaskState.RECOVERING) ||
          (currentState === TaskState.RECOVERING && stateInfo.state === TaskState.RESOLVED);

        return (
          <div key={stateInfo.state} className="flex items-center">
            <motion.div
              initial={{ scale: 0.9, opacity: 0.5 }}
              animate={{
                scale: isActive ? 1.05 : 1,
                opacity: isActive || isPast ? 1 : 0.5,
              }}
              transition={{ duration: 0.3 }}
              className={cn(
                'state-node border-2 rounded-lg flex items-center justify-center gap-2 transition-all duration-300',
                sizes.node,
                isActive
                  ? cn(activeStateColors[stateInfo.state], 'shadow-lg')
                  : stateColors[stateInfo.state]
              )}
            >
              <Icon className={cn(sizes.icon, isActive && 'animate-pulse')} />
              <span className="font-medium">{stateInfo.label}</span>
            </motion.div>

            {index < states.length - 1 && (
              <motion.div
                initial={{ opacity: 0.3 }}
                animate={{
                  opacity: isPast || (isActive && isReachable) ? 1 : 0.3,
                }}
                className={cn('mx-2', sizes.gap)}
              >
                <ArrowRight className={cn(
                  'text-muted-foreground',
                  sizes.icon,
                  (isPast || isActive) && 'text-primary'
                )} />
              </motion.div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Compact vertical state machine for cards
export function StateMachineCompact({ currentState }: { currentState: TaskState }) {
  return (
    <div className="flex items-center gap-1">
      {states.map((stateInfo, index) => {
        const isActive = currentState === stateInfo.state;
        const isPast = currentState > stateInfo.state;

        return (
          <div key={stateInfo.state} className="flex items-center">
            <div
              className={cn(
                'w-2 h-2 rounded-full transition-all',
                isActive
                  ? cn(activeStateColors[stateInfo.state].split(' ')[1], 'scale-125')
                  : isPast
                    ? 'bg-muted-foreground'
                    : 'bg-muted'
              )}
            />
            {index < states.length - 1 && (
              <div className={cn(
                'w-3 h-0.5 mx-0.5',
                isPast ? 'bg-muted-foreground' : 'bg-muted'
              )} />
            )}
          </div>
        );
      })}
    </div>
  );
}
