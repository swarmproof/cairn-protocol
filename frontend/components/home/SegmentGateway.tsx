'use client';

import Link from 'next/link';
import { Building2, Wrench, ArrowRight, Shield, Zap, Code, Package } from 'lucide-react';
import { cn } from '@/lib/utils';
import { GlowCard } from '@/components/ui/glow-card';
import { BorderBeam } from '@/components/ui/border-beam';

export function SegmentGateway() {
  return (
    <section className="py-16">
      <div className="container">
        <h2 className="text-2xl font-bold text-center mb-2">Who are you?</h2>
        <p className="text-center text-muted-foreground mb-12">
          Choose your path to get started with CAIRN
        </p>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Operator Card */}
          <GlowCard glowColor="rgba(59, 130, 246, 0.3)" className="group">
            <Link
              href="/operators"
              className={cn(
                'segment-card segment-card-operator relative',
                'flex flex-col h-full'
              )}
            >
              <BorderBeam size={150} duration={15} colorFrom="#3b82f6" colorTo="#60a5fa" />
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 rounded-xl bg-blue-500/10 flex items-center justify-center group-hover:bg-blue-500/20 transition-colors">
                <Building2 className="h-7 w-7 text-blue-500" />
              </div>
              <div>
                <h3 className="text-xl font-bold">I RUN AGENTS</h3>
                <p className="text-sm text-muted-foreground">Operations & Infrastructure</p>
              </div>
            </div>

            <p className="text-lg text-foreground/90 mb-6 italic">
              "Never lose work. Recover in minutes, not hours."
            </p>

            <ul className="space-y-3 mb-8 flex-1">
              <li className="flex items-center gap-3 text-sm">
                <Shield className="h-4 w-4 text-blue-500 flex-shrink-0" />
                <span><strong className="text-foreground">Automatic</strong> failure detection via heartbeats</span>
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Zap className="h-4 w-4 text-blue-500 flex-shrink-0" />
                <span><strong className="text-foreground">Fair settlement</strong> based on verified work</span>
              </li>
              <li className="flex items-center gap-3 text-sm">
                <span className="w-4 h-4 flex items-center justify-center text-blue-500 flex-shrink-0">⏱</span>
                <span><strong className="text-foreground">Minutes</strong> to resume from checkpoint</span>
              </li>
            </ul>

            <div className="flex items-center justify-between pt-4 border-t border-blue-500/20">
              <span className="font-semibold text-blue-500 group-hover:text-blue-400 transition-colors">
                Protect My Agents
              </span>
              <ArrowRight className="h-5 w-5 text-blue-500 group-hover:translate-x-1 transition-transform" />
            </div>
            </Link>
          </GlowCard>

          {/* Developer Card */}
          <GlowCard glowColor="rgba(16, 185, 129, 0.3)" className="group">
            <Link
              href="/integrate"
              className={cn(
                'segment-card segment-card-developer relative',
                'flex flex-col h-full'
              )}
            >
              <BorderBeam size={150} duration={15} colorFrom="#10b981" colorTo="#34d399" />
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 rounded-xl bg-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
                <Wrench className="h-7 w-7 text-emerald-500" />
              </div>
              <div>
                <h3 className="text-xl font-bold">I BUILD AGENTS</h3>
                <p className="text-sm text-muted-foreground">Development & Integration</p>
              </div>
            </div>

            <p className="text-lg text-foreground/90 mb-6 italic">
              "3 lines of code. Zero breaking changes."
            </p>

            <ul className="space-y-3 mb-8 flex-1">
              <li className="flex items-center gap-3 text-sm">
                <Code className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                <span><strong className="text-foreground">pip install cairn-sdk</strong></span>
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Package className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                <span><strong className="text-foreground">LangGraph, AgentKit, Olas</strong> ready</span>
              </li>
              <li className="flex items-center gap-3 text-sm">
                <span className="w-4 h-4 flex items-center justify-center text-emerald-500 flex-shrink-0">📚</span>
                <span>Full docs + SDK support</span>
              </li>
            </ul>

            <div className="flex items-center justify-between pt-4 border-t border-emerald-500/20">
              <span className="font-semibold text-emerald-500 group-hover:text-emerald-400 transition-colors">
                Start Integrating
              </span>
              <ArrowRight className="h-5 w-5 text-emerald-500 group-hover:translate-x-1 transition-transform" />
            </div>
            </Link>
          </GlowCard>
        </div>
      </div>
    </section>
  );
}
