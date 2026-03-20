'use client';

import { cn } from '@/lib/utils';
import { ReactNode } from 'react';

interface AnimatedGradientTextProps {
  children: ReactNode;
  className?: string;
}

export function AnimatedGradientText({ children, className }: AnimatedGradientTextProps) {
  return (
    <span
      className={cn(
        'inline animate-gradient bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 bg-[length:var(--bg-size)_100%] bg-clip-text text-transparent',
        className
      )}
      style={{ '--bg-size': '400%' } as React.CSSProperties}
    >
      {children}
    </span>
  );
}
