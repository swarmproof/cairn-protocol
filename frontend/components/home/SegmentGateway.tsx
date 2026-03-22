'use client';

import Link from 'next/link';
import { Cpu, Wrench, ArrowRight, Network, Zap, Code, Package, Bot } from 'lucide-react';
import { cn } from '@/lib/utils';
import { GlowCard } from '@/components/ui/glow-card';
import { BorderBeam } from '@/components/ui/border-beam';

export function SegmentGateway() {
  return (
    <section className="py-16">
      <div className="container">
        <h2 className="text-2xl font-bold text-center mb-2">How will you integrate CAIRN?</h2>
        <p className="text-center text-muted-foreground mb-12">
          CAIRN is agent infrastructure — integrate it into your framework or your agent code
        </p>

        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Framework Integration Card */}
          <GlowCard glowColor="rgba(217, 119, 6, 0.3)" className="group">
            <Link
              href="/operators"
              className={cn(
                'segment-card segment-card-operator relative',
                'flex flex-col h-full'
              )}
            >
              <BorderBeam size={150} duration={15} colorFrom="#d97706" colorTo="#f59e0b" />
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 rounded-xl bg-amber-500/10 flex items-center justify-center group-hover:bg-amber-500/20 transition-colors">
                <Cpu className="h-7 w-7 text-amber-500" />
              </div>
              <div>
                <h3 className="text-xl font-bold">FRAMEWORK TEAMS</h3>
                <p className="text-sm text-muted-foreground">Add CAIRN to your agent system</p>
              </div>
            </div>

            <p className="text-lg text-foreground/90 mb-6 italic">
              "Every agent failure teaches all future agents."
            </p>

            <ul className="space-y-3 mb-8 flex-1">
              <li className="flex items-center gap-3 text-sm">
                <Network className="h-4 w-4 text-amber-500 flex-shrink-0" />
                <span><strong className="text-foreground">Automatic</strong> fallback routing when agents fail</span>
              </li>
              <li className="flex items-center gap-3 text-sm">
                <Bot className="h-4 w-4 text-amber-500 flex-shrink-0" />
                <span><strong className="text-foreground">No human required</strong> — agents handle recovery</span>
              </li>
              <li className="flex items-center gap-3 text-sm">
                <span className="w-4 h-4 flex items-center justify-center text-amber-500 flex-shrink-0">🪨</span>
                <span><strong className="text-foreground">Collective intelligence</strong> from failure patterns</span>
              </li>
            </ul>

            <div className="flex items-center justify-between pt-4 border-t border-amber-500/20">
              <span className="font-semibold text-amber-500 group-hover:text-amber-400 transition-colors">
                View Architecture
              </span>
              <ArrowRight className="h-5 w-5 text-amber-500 group-hover:translate-x-1 transition-transform" />
            </div>
            </Link>
          </GlowCard>

          {/* Agent Developer Card */}
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
                <h3 className="text-xl font-bold">AGENT DEVELOPERS</h3>
                <p className="text-sm text-muted-foreground">Integrate SDK into your agent</p>
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
