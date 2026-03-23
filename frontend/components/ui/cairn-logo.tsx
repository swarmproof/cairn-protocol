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
      {/* 3D Isometric Cairn Stack Icon */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn(animated && 'group')}
      >
        {/* Bottom block - largest */}
        <g className={cn(animated && 'group-hover:translate-y-[-1px] transition-transform')}>
          {/* Top face */}
          <path
            d="M24 32 L36 26 L24 20 L12 26 Z"
            className={cn(
              'fill-cyan-400',
              animated && 'group-hover:fill-cyan-300 transition-colors'
            )}
          />
          {/* Right face */}
          <path
            d="M24 32 L36 26 L36 34 L24 40 Z"
            className={cn(
              'fill-cyan-600',
              animated && 'group-hover:fill-cyan-500 transition-colors'
            )}
          />
          {/* Left face */}
          <path
            d="M24 32 L12 26 L12 34 L24 40 Z"
            className={cn(
              'fill-cyan-500',
              animated && 'group-hover:fill-cyan-400 transition-colors'
            )}
          />
        </g>

        {/* Middle block */}
        <g className={cn(animated && 'group-hover:translate-y-[-2px] transition-transform delay-75')}>
          {/* Top face */}
          <path
            d="M24 22 L32 18 L24 14 L16 18 Z"
            className={cn(
              'fill-cyan-400',
              animated && 'group-hover:fill-cyan-300 transition-colors delay-75'
            )}
          />
          {/* Right face */}
          <path
            d="M24 22 L32 18 L32 24 L24 28 Z"
            className={cn(
              'fill-cyan-600',
              animated && 'group-hover:fill-cyan-500 transition-colors delay-75'
            )}
          />
          {/* Left face */}
          <path
            d="M24 22 L16 18 L16 24 L24 28 Z"
            className={cn(
              'fill-cyan-500',
              animated && 'group-hover:fill-cyan-400 transition-colors delay-75'
            )}
          />
        </g>

        {/* Top block - smallest */}
        <g className={cn(animated && 'group-hover:translate-y-[-3px] transition-transform delay-150')}>
          {/* Top face */}
          <path
            d="M24 12 L28 10 L24 8 L20 10 Z"
            className={cn(
              'fill-cyan-300',
              animated && 'group-hover:fill-cyan-200 transition-colors delay-150'
            )}
          />
          {/* Right face */}
          <path
            d="M24 12 L28 10 L28 14 L24 16 Z"
            className={cn(
              'fill-cyan-500',
              animated && 'group-hover:fill-cyan-400 transition-colors delay-150'
            )}
          />
          {/* Left face */}
          <path
            d="M24 12 L20 10 L20 14 L24 16 Z"
            className={cn(
              'fill-cyan-400',
              animated && 'group-hover:fill-cyan-300 transition-colors delay-150'
            )}
          />
        </g>
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
      {/* Bottom block */}
      <path d="M24 32 L36 26 L24 20 L12 26 Z" className="fill-cyan-400" />
      <path d="M24 32 L36 26 L36 34 L24 40 Z" className="fill-cyan-600" />
      <path d="M24 32 L12 26 L12 34 L24 40 Z" className="fill-cyan-500" />

      {/* Middle block */}
      <path d="M24 22 L32 18 L24 14 L16 18 Z" className="fill-cyan-400" />
      <path d="M24 22 L32 18 L32 24 L24 28 Z" className="fill-cyan-600" />
      <path d="M24 22 L16 18 L16 24 L24 28 Z" className="fill-cyan-500" />

      {/* Top block */}
      <path d="M24 12 L28 10 L24 8 L20 10 Z" className="fill-cyan-300" />
      <path d="M24 12 L28 10 L28 14 L24 16 Z" className="fill-cyan-500" />
      <path d="M24 12 L20 10 L20 14 L24 16 Z" className="fill-cyan-400" />
    </svg>
  );
}
