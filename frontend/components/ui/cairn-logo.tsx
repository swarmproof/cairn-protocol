'use client';

import { cn } from '@/lib/utils';

interface CairnLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'full' | 'icon';
  animated?: boolean;
}

const sizes = {
  sm: { icon: 24, text: 'text-lg' },
  md: { icon: 32, text: 'text-xl' },
  lg: { icon: 40, text: 'text-2xl' },
  xl: { icon: 56, text: 'text-3xl' },
};

export function CairnLogo({
  className,
  size = 'md',
  variant = 'full',
  animated = false
}: CairnLogoProps) {
  const { icon: iconSize, text: textSize } = sizes[size];

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Cairn Stone Stack Icon */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn(animated && 'group')}
      >
        {/* Base stone - largest */}
        <ellipse
          cx="24"
          cy="40"
          rx="14"
          ry="5"
          className={cn(
            'fill-slate-600',
            animated && 'group-hover:fill-slate-500 transition-colors'
          )}
        />
        {/* Middle stone */}
        <ellipse
          cx="24"
          cy="32"
          rx="10"
          ry="4"
          className={cn(
            'fill-slate-500',
            animated && 'group-hover:fill-slate-400 transition-colors delay-75'
          )}
        />
        {/* Upper middle stone */}
        <ellipse
          cx="24"
          cy="25"
          rx="7"
          ry="3"
          className={cn(
            'fill-slate-400',
            animated && 'group-hover:fill-slate-300 transition-colors delay-100'
          )}
        />
        {/* Top stone with glow */}
        <ellipse
          cx="24"
          cy="19"
          rx="5"
          ry="2.5"
          className={cn(
            'fill-emerald-500',
            animated && 'group-hover:fill-emerald-400 transition-colors delay-150'
          )}
        />
        {/* Glow effect on top stone */}
        <ellipse
          cx="24"
          cy="19"
          rx="5"
          ry="2.5"
          className="fill-emerald-400/30"
          filter="url(#glow)"
        />
        {/* Pulse indicator */}
        <circle
          cx="24"
          cy="12"
          r="2"
          className={cn(
            'fill-emerald-400',
            animated && 'animate-pulse'
          )}
        />
        {/* Signal waves */}
        <path
          d="M18 8 Q24 4 30 8"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          className="text-emerald-500/60"
          fill="none"
        />
        <path
          d="M20 5 Q24 2 28 5"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          className="text-emerald-400/40"
          fill="none"
        />
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      {/* Text logo */}
      {variant === 'full' && (
        <span className={cn(
          'font-bold tracking-tight',
          textSize
        )}>
          <span className="text-slate-100">CAIRN</span>
        </span>
      )}
    </div>
  );
}

// Compact icon-only version for favicons and small spaces
export function CairnIcon({
  className,
  size = 24,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <ellipse cx="24" cy="40" rx="14" ry="5" className="fill-slate-600" />
      <ellipse cx="24" cy="32" rx="10" ry="4" className="fill-slate-500" />
      <ellipse cx="24" cy="25" rx="7" ry="3" className="fill-slate-400" />
      <ellipse cx="24" cy="19" rx="5" ry="2.5" className="fill-emerald-500" />
      <circle cx="24" cy="12" r="2" className="fill-emerald-400" />
      <path
        d="M18 8 Q24 4 30 8"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        className="text-emerald-500/60"
        fill="none"
      />
    </svg>
  );
}
