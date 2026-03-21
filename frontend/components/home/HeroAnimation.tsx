'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Spotlight } from '@/components/ui/spotlight';
import { BorderBeam } from '@/components/ui/border-beam';

type AnimationPhase = 1 | 2 | 3 | 4 | 5;

export function HeroAnimation() {
  const [phase, setPhase] = useState<AnimationPhase>(1);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      setPhase((prev) => {
        if (prev >= 5) {
          return 1; // Loop back to beginning
        }
        return (prev + 1) as AnimationPhase;
      });
    }, 2500); // 2.5 seconds per phase for better visibility

    return () => clearInterval(timer);
  }, [isPlaying]);

  return (
    <div className="relative w-full max-w-3xl mx-auto">
      {/* Animation Container */}
      <div className="aspect-video bg-black/[0.96] rounded-2xl border border-slate-700/50 overflow-hidden relative">
        <Spotlight
          className="-top-40 left-0 md:left-60 md:-top-20"
          fill="rgba(16, 185, 129, 0.12)"
        />
        <BorderBeam size={250} duration={12} delay={0} colorFrom="#10b981" colorTo="#06b6d4" />
        {/* Phase Indicator */}
        <div className="absolute top-4 left-4 flex gap-1 z-10">
          {[1, 2, 3, 4, 5].map((p) => (
            <div
              key={p}
              className={cn(
                'w-2 h-2 rounded-full transition-all duration-300',
                phase >= p ? 'bg-emerald-500' : 'bg-slate-600'
              )}
            />
          ))}
        </div>

        {/* Phase 1: The Solitary Agent */}
        <div
          className={cn(
            'absolute inset-0 flex flex-col items-center justify-center transition-all duration-500',
            phase === 1 ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
          )}
        >
          <div className="relative">
            {/* Agent Icon */}
            <div className="w-16 h-16 rounded-xl bg-slate-700 border border-slate-600 flex items-center justify-center mb-4 mx-auto">
              <span className="text-2xl">🤖</span>
            </div>
            {/* Progress Bar */}
            <div className="w-48 h-2 bg-slate-700 rounded-full overflow-hidden mb-3">
              <div className="h-full bg-cyan-500 rounded-full animate-progress-fail" style={{ width: '65%' }} />
            </div>
            {/* Failure Indicator */}
            <div className="flex items-center justify-center gap-2 text-red-400 animate-pulse">
              <span className="text-xl">❌</span>
              <span className="font-semibold">FAILED</span>
            </div>
            {/* Ripple Effect */}
            <div className="absolute inset-0 -m-8 rounded-full border-2 border-red-500/30 animate-ping" />
          </div>
          <p className="text-slate-400 text-sm mt-6">Agent alone, trying, failing...</p>
        </div>

        {/* Phase 2: The Cairn Appears */}
        <div
          className={cn(
            'absolute inset-0 flex flex-col items-center justify-center transition-all duration-500',
            phase === 2 ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
          )}
        >
          <div className="relative">
            {/* Failed Agent (faded) */}
            <div className="w-12 h-12 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center mb-4 mx-auto opacity-50">
              <span className="text-lg">🤖</span>
            </div>
            {/* Arrow Down */}
            <div className="text-2xl text-slate-500 mb-2 text-center">↓</div>
            {/* Cairn Stack Animation */}
            <div className="flex flex-col items-center animate-stack-grow">
              <div className="w-8 h-3 bg-orange-500/80 rounded mb-0.5 animate-stone-appear delay-100" />
              <div className="w-10 h-3 bg-orange-500/60 rounded mb-0.5 animate-stone-appear delay-200" />
              <div className="w-12 h-3 bg-orange-500/40 rounded animate-stone-appear delay-300" />
            </div>
            {/* Glow Effect */}
            <div className="absolute inset-0 -m-4 bg-orange-500/10 rounded-full blur-xl animate-pulse" />
          </div>
          <p className="text-slate-400 text-sm mt-6">Failure creates a marker...</p>
        </div>

        {/* Phase 3: The Network Awakens */}
        <div
          className={cn(
            'absolute inset-0 flex flex-col items-center justify-center transition-all duration-500',
            phase === 3 ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
          )}
        >
          <div className="relative flex items-center gap-8">
            {/* Left Agents */}
            <div className="flex flex-col gap-3">
              <div className="w-10 h-10 rounded-lg bg-slate-700 border border-slate-600 flex items-center justify-center animate-agent-connect">
                <span>🤖</span>
              </div>
              <div className="w-10 h-10 rounded-lg bg-slate-700 border border-slate-600 flex items-center justify-center animate-agent-connect delay-200">
                <span>🤖</span>
              </div>
            </div>

            {/* Connection Lines */}
            <div className="absolute left-14 top-1/2 w-8 h-px bg-gradient-to-r from-emerald-500 to-transparent animate-line-draw" />
            <div className="absolute left-14 bottom-6 w-8 h-px bg-gradient-to-r from-emerald-500 to-transparent animate-line-draw delay-200" />

            {/* Central Cairn Graph */}
            <div className="relative">
              <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-amber-500/20 to-emerald-500/20 border-2 border-amber-500/50 flex items-center justify-center animate-glow-pulse">
                <div className="flex flex-col items-center">
                  <span className="text-2xl">🪨</span>
                  <span className="text-xs text-amber-400 font-medium">(47)</span>
                </div>
              </div>
              {/* Connecting glow */}
              <div className="absolute inset-0 -m-4 bg-emerald-500/5 rounded-full blur-xl" />
            </div>

            {/* Connection Lines Right */}
            <div className="absolute right-14 top-1/2 w-8 h-px bg-gradient-to-l from-emerald-500 to-transparent animate-line-draw delay-400" />

            {/* Right Agent */}
            <div className="w-10 h-10 rounded-lg bg-slate-700 border border-slate-600 flex items-center justify-center animate-agent-connect delay-400">
              <span>🤖</span>
            </div>
          </div>
          <p className="text-slate-400 text-sm mt-8">Multiple agents connect to the graph...</p>
        </div>

        {/* Phase 4: Intelligence Query */}
        <div
          className={cn(
            'absolute inset-0 flex flex-col items-center justify-center transition-all duration-500',
            phase === 4 ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
          )}
        >
          <div className="relative">
            {/* New Agent */}
            <div className="w-14 h-14 rounded-xl bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center mb-3 mx-auto">
              <span className="text-xl">🤖</span>
            </div>
            {/* Query Arrow */}
            <div className="text-lg text-emerald-400 mb-2 text-center animate-bounce">↓ reads</div>
            {/* Cairn Graph */}
            <div className="w-24 h-16 rounded-lg bg-slate-800 border border-slate-600 flex items-center justify-center mb-3">
              <span className="text-2xl">🪨</span>
            </div>
            {/* Data Flowing Back */}
            <div className="flex justify-center gap-1 text-lg mb-3 animate-data-flow">
              <span>↑</span>
              <span>↑</span>
              <span>↑</span>
            </div>
            {/* Intelligence Insights */}
            <div className="flex flex-wrap gap-2 justify-center max-w-md">
              <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-400 text-xs font-medium animate-insight-appear">
                AVOID 2-4am
              </span>
              <span className="px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs font-medium animate-insight-appear delay-100">
                USE Agent X
              </span>
              <span className="px-2 py-1 rounded bg-cyan-500/20 text-cyan-400 text-xs font-medium animate-insight-appear delay-200">
                COST: 0.05 ETH
              </span>
            </div>
          </div>
          <p className="text-slate-400 text-sm mt-4">Agent queries before execution...</p>
        </div>

        {/* Phase 5: Collective Success */}
        <div
          className={cn(
            'absolute inset-0 flex flex-col items-center justify-center transition-all duration-500',
            phase === 5 ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
          )}
        >
          <div className="relative">
            {/* Success Progress */}
            <div className="w-48 h-3 bg-slate-700 rounded-full overflow-hidden mb-4">
              <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full w-full animate-progress-success" />
            </div>
            <div className="flex items-center justify-center gap-2 text-green-400 mb-6">
              <span className="text-2xl">✅</span>
              <span className="font-bold text-lg">SUCCESS</span>
            </div>
            {/* Growing Network */}
            <div className="flex items-center justify-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-green-500/20 border border-green-500/50 flex items-center justify-center">
                <span className="text-sm">🤖</span>
              </div>
              <div className="w-4 h-px bg-green-500/50" />
              <div className="w-10 h-10 rounded-lg bg-orange-500/20 border border-orange-500/50 flex items-center justify-center animate-pulse">
                <span>🪨</span>
              </div>
              <div className="w-4 h-px bg-green-500/50" />
              <div className="w-8 h-8 rounded-lg bg-green-500/20 border border-green-500/50 flex items-center justify-center">
                <span className="text-sm">🤖</span>
              </div>
            </div>
            {/* Particles */}
            <div className="absolute inset-0 -m-8">
              {[...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className="absolute w-1 h-1 rounded-full bg-green-400 animate-particle"
                  style={{
                    left: `${20 + Math.random() * 60}%`,
                    top: `${20 + Math.random() * 60}%`,
                    animationDelay: `${i * 0.2}s`,
                  }}
                />
              ))}
            </div>
          </div>
          {/* Main Tagline */}
          <div className="text-center mt-4">
            <p className="text-xl font-bold bg-gradient-to-r from-emerald-400 via-cyan-400 to-slate-300 bg-clip-text text-transparent">
              CAIRN: Agents Learn Together
            </p>
            <p className="text-slate-400 text-sm mt-1">Success through collective intelligence</p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-4 mt-4">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>
        <button
          onClick={() => setPhase(1)}
          className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
        >
          ↻ Restart
        </button>
      </div>

      {/* Phase Labels */}
      <div className="flex justify-between text-xs text-slate-500 mt-4 px-4">
        <span className={phase === 1 ? 'text-red-400' : ''}>1. Failure</span>
        <span className={phase === 2 ? 'text-amber-400' : ''}>2. Record</span>
        <span className={phase === 3 ? 'text-cyan-400' : ''}>3. Connect</span>
        <span className={phase === 4 ? 'text-emerald-400' : ''}>4. Query</span>
        <span className={phase === 5 ? 'text-green-400' : ''}>5. Success</span>
      </div>
    </div>
  );
}
