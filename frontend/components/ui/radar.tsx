'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import React from 'react';

export const Circle = ({ className, children, idx, ...rest }: any) => {
  return (
    <motion.div
      {...rest}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: idx * 0.1, duration: 0.2 }}
      className={cn(
        'absolute inset-0 left-1/2 top-1/2 h-10 w-10 -translate-x-1/2 -translate-y-1/2 transform rounded-full border border-neutral-200',
        className
      )}
    />
  );
};

export const Radar = ({ className }: { className?: string }) => {
  const circles = new Array(8).fill(1);
  return (
    <div
      className={cn(
        'relative flex h-20 w-20 items-center justify-center rounded-full',
        className
      )}
    >
      <style>{`
        @keyframes radar-spin {
          from { transform: rotate(20deg); }
          to   { transform: rotate(380deg); }
        }
        .animate-radar-spin {
          animation: radar-spin 10s linear infinite;
        }
      `}</style>
      {/* Rotating sweep line */}
      <div
        style={{ transformOrigin: 'right center' }}
        className="animate-radar-spin absolute right-1/2 top-1/2 z-40 flex h-[5px] w-[400px] items-end justify-center overflow-hidden bg-transparent"
      >
        <div className="relative z-40 h-[1px] w-full bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
      </div>
      {/* Concentric circles */}
      {circles.map((_, idx) => (
        <Circle
          style={{
            height: `${(idx + 1) * 5}rem`,
            width: `${(idx + 1) * 5}rem`,
            border: `1px solid rgba(16, 185, 129, ${0.3 - idx * 0.03})`,
          }}
          key={`circle-${idx}`}
          idx={idx}
        />
      ))}
    </div>
  );
};

export const IconContainer = ({
  icon,
  text,
  delay,
  className,
}: {
  icon?: React.ReactNode;
  text?: string;
  delay?: number;
  className?: string;
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2, delay: delay ?? 0 }}
      className={cn('relative z-50 flex flex-col items-center justify-center space-y-2', className)}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-700 bg-slate-900/80 shadow-inner backdrop-blur-sm">
        {icon || (
          <svg className="h-8 w-8 text-slate-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </div>
      <div className="hidden rounded-md px-2 py-1 md:block">
        <div className="text-center text-xs font-medium text-slate-400">{text || 'Agent'}</div>
      </div>
    </motion.div>
  );
};
