'use client';

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { motion, useSpring, useTransform, SpringOptions } from 'framer-motion';
import { cn } from '@/lib/utils';

interface GlowCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  glowColor?: string;
  glowSize?: number;
  className?: string;
}

export function GlowCard({
  children,
  glowColor = 'rgba(59, 130, 246, 0.5)',
  glowSize = 200,
  className,
  ...props
}: GlowCardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  const springOptions: SpringOptions = { bounce: 0, duration: 0.3 };
  const mouseX = useSpring(0, springOptions);
  const mouseY = useSpring(0, springOptions);

  const glowLeft = useTransform(mouseX, (x) => `${x - glowSize / 2}px`);
  const glowTop = useTransform(mouseY, (y) => `${y - glowSize / 2}px`);

  const handleMouseMove = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (!containerRef.current) return;
      const { left, top } = containerRef.current.getBoundingClientRect();
      mouseX.set(event.clientX - left);
      mouseY.set(event.clientY - top);
    },
    [mouseX, mouseY]
  );

  return (
    <div
      ref={containerRef}
      className={cn('relative overflow-hidden rounded-xl', className)}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      {...props}
    >
      <motion.div
        className="pointer-events-none absolute rounded-full blur-xl transition-opacity duration-300"
        style={{
          width: glowSize,
          height: glowSize,
          left: glowLeft,
          top: glowTop,
          background: `radial-gradient(circle, ${glowColor}, transparent 70%)`,
          opacity: isHovered ? 1 : 0,
        }}
      />
      {children}
    </div>
  );
}
