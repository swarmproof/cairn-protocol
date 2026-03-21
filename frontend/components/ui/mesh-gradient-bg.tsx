'use client';

import { MeshGradient } from '@paper-design/shaders-react';

interface MeshGradientBgProps {
  /** Preset color themes */
  variant?: 'default' | 'warm' | 'cool' | 'subtle';
  /** Animation speed (0.1 - 2.0) */
  speed?: number;
  /** Additional className */
  className?: string;
}

// Cairn/Desert inspired color palettes - muted, sophisticated
const colorPresets = {
  default: ['#0a0a0a', '#1a1814', '#2d2a26', '#1f1d1a'],
  warm: ['#0a0908', '#1a1612', '#2e2620', '#1c1915'],
  cool: ['#080a0a', '#12181a', '#1e2628', '#141a1c'],
  subtle: ['#0c0c0c', '#161616', '#202020', '#141414'],
};

export function MeshGradientBg({
  variant = 'default',
  speed = 0.4,
  className = '',
}: MeshGradientBgProps) {
  return (
    <div className={`fixed inset-0 -z-10 ${className}`}>
      <MeshGradient
        className="w-full h-full"
        colors={colorPresets[variant]}
        speed={speed}
      />
      {/* Subtle overlay for depth */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/40 pointer-events-none" />
    </div>
  );
}

// Simpler static background for pages that don't need animation
export function DesertGradientBg({ className = '' }: { className?: string }) {
  return (
    <div className={`fixed inset-0 -z-10 ${className}`}>
      {/* Base gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#0a0a0a] via-[#141210] to-[#0a0a0a]" />

      {/* Subtle noise texture overlay */}
      <div
        className="absolute inset-0 opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />

      {/* Warm accent glow - very subtle */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[#c4a060]/[0.03] rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-[#78716c]/[0.04] rounded-full blur-[100px] pointer-events-none" />
    </div>
  );
}
