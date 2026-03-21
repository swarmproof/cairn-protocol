'use client';

import { cn } from '@/lib/utils';

export type CairnStoneType = 'liveness' | 'resource' | 'logic' | 'success';

export interface CairnStoneConfig {
  color: string;
  bgColor: string;
  borderColor: string;
  symbol: string;
  label: string;
}

export const CAIRN_STONES: Record<CairnStoneType, CairnStoneConfig> = {
  liveness: {
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    symbol: '~~~',
    label: 'Heartbeat Miss',
  },
  resource: {
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/20',
    borderColor: 'border-orange-500/30',
    symbol: '⚠',
    label: 'API/Gas Failure',
  },
  logic: {
    color: 'text-red-500',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/30',
    symbol: '🐛',
    label: 'Code Error',
  },
  success: {
    color: 'text-green-500',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
    symbol: '✓',
    label: 'Recovery Success',
  },
};

interface CairnIconProps {
  type: CairnStoneType;
  size?: 'sm' | 'md' | 'lg';
  glow?: boolean;
  showLabel?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: 'w-6 h-6 text-xs',
  md: 'w-8 h-8 text-sm',
  lg: 'w-12 h-12 text-base',
};

export function CairnIcon({
  type,
  size = 'md',
  glow = false,
  showLabel = false,
  className,
}: CairnIconProps) {
  const stone = CAIRN_STONES[type];

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className={cn(
          'flex items-center justify-center rounded-lg border transition-all duration-300',
          stone.bgColor,
          stone.borderColor,
          stone.color,
          sizeClasses[size],
          glow && 'ring-2 ring-current ring-opacity-50 animate-pulse'
        )}
        title={stone.label}
      >
        <span>{stone.symbol}</span>
      </div>
      {showLabel && (
        <span className={cn('text-sm font-medium', stone.color)}>
          {stone.label}
        </span>
      )}
    </div>
  );
}

interface CairnStackProps {
  count: number;
  type?: CairnStoneType;
  maxDisplay?: number;
  className?: string;
}

export function CairnStack({
  count,
  type = 'resource',
  maxDisplay = 5,
  className,
}: CairnStackProps) {
  const displayCount = Math.min(count, maxDisplay);
  const isGlowing = count >= 21;
  const stone = CAIRN_STONES[type];

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <div className="flex flex-col-reverse items-center">
        {Array.from({ length: displayCount }).map((_, i) => (
          <div
            key={i}
            className={cn(
              'flex items-center justify-center rounded transition-all duration-300',
              stone.bgColor,
              stone.color,
              i === displayCount - 1 && isGlowing && 'animate-pulse ring-2 ring-current ring-opacity-50',
              // Stacking effect: each stone slightly smaller
              i === 0 ? 'w-10 h-3' : i === 1 ? 'w-9 h-3' : i === 2 ? 'w-8 h-3' : i === 3 ? 'w-7 h-3' : 'w-6 h-3',
              i !== 0 && '-mb-0.5'
            )}
            style={{ opacity: 0.6 + (i * 0.1) }}
          />
        ))}
      </div>
      <span className="text-xs text-muted-foreground font-medium">
        {count} cairn{count !== 1 ? 's' : ''}
      </span>
    </div>
  );
}

interface IntelligenceLevelProps {
  cairnCount: number;
}

export function IntelligenceLevel({ cairnCount }: IntelligenceLevelProps) {
  let level: 'new' | 'learning' | 'mature';
  let label: string;
  let color: string;

  if (cairnCount <= 5) {
    level = 'new';
    label = 'New task type';
    color = 'text-muted-foreground';
  } else if (cairnCount <= 20) {
    level = 'learning';
    label = 'Pattern recognition';
    color = 'text-blue-500';
  } else {
    level = 'mature';
    label = 'High intelligence';
    color = 'text-green-500';
  }

  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'w-2 h-2 rounded-full',
          level === 'new' && 'bg-muted-foreground',
          level === 'learning' && 'bg-blue-500',
          level === 'mature' && 'bg-green-500 animate-pulse'
        )}
      />
      <span className={cn('text-xs font-medium', color)}>{label}</span>
    </div>
  );
}
