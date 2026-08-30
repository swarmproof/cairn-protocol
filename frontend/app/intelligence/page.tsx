'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Brain, Search, ArrowRight, Activity, Database, Shield, Zap, Network, Cpu, Loader2, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CairnStack, IntelligenceLevel } from '@/components/cairn';
import { cn } from '@/lib/utils';
import { Radar, IconContainer } from '@/components/ui/radar';
import { Spotlight } from '@/components/ui/spotlight';
import { GlowCard } from '@/components/ui/glow-card';
import { useTaskTypeStats, useProtocolStats } from '@/hooks/useIntelligence';

interface TaskType {
  id: string;
  name: string;
  cairnCount: number;
  successRate: number;
  recentActivity: string;
  topFailure: string;
}

export default function IntelligencePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string | null>(null);

  // Fetch real data from subgraph
  const { data: taskTypes, isLoading: isLoadingTypes, error: typesError } = useTaskTypeStats();
  const { data: protocolStats, isLoading: isLoadingProtocol } = useProtocolStats();

  // Real data only — no fabricated fallback. Show an honest empty state when the
  // subgraph has not indexed any tasks yet.
  const hasNoData = !taskTypes || taskTypes.length === 0;
  const displayTaskTypes: TaskType[] = useMemo(() => {
    return taskTypes && taskTypes.length > 0 ? taskTypes : [];
  }, [taskTypes]);

  const filteredTypes = displayTaskTypes.filter((t) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalCairns = useMemo(() => {
    if (protocolStats) {
      return Number(protocolStats.totalTasksCreated);
    }
    return displayTaskTypes.reduce((sum, t) => sum + t.cairnCount, 0);
  }, [protocolStats, displayTaskTypes]);

  const isLoading = isLoadingTypes || isLoadingProtocol;

  return (
    <div className="container py-12">
      {/* Hero with Radar Visualization */}
      <section className="relative max-w-4xl mx-auto mb-16">
        <div className="relative overflow-hidden rounded-2xl bg-black/[0.96] border border-slate-800">
          <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(217, 119, 6, 0.1)" />

          {/* Content section - NOT overlapping */}
          <div className="relative z-10 text-center pt-10 pb-6 px-4">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 text-amber-500 text-sm font-medium mb-4">
              <Brain className="h-4 w-4" />
              Collective Intelligence
            </div>
            <h1 className="text-3xl md:text-4xl font-bold mb-3 text-white">
              CAIRN Intelligence Layer
            </h1>
            <p className="text-slate-400 mb-2">
              The collective memory of every agent that came before.
            </p>
            {isLoading ? (
              <div className="flex items-center justify-center gap-2 text-slate-500 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading protocol data...
              </div>
            ) : (
              <p className="text-slate-500 text-sm">
                <strong className="text-white">{totalCairns} cairns</strong> across{' '}
                <strong className="text-white">{displayTaskTypes.length}</strong> task types
                {hasNoData && (
                  <span className="ml-2 text-muted-foreground">(no live data yet)</span>
                )}
              </p>
            )}
          </div>

          {/* Radar visualization section - separate space */}
          <div className="relative h-72 md:h-80">
            {/* Radar in center */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <Radar className="scale-50 md:scale-75 opacity-40" />
            </div>

            {/* Icon containers positioned around radar */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="relative w-full max-w-lg h-full">
                {/* Top row */}
                <div className="absolute top-4 left-1/4 -translate-x-1/2">
                  <IconContainer text="DeFi Tasks" delay={0.2} icon={<Zap className="h-5 w-5 text-amber-400" />} />
                </div>
                <div className="absolute top-4 right-1/4 translate-x-1/2">
                  <IconContainer text="API Calls" delay={0.3} icon={<Network className="h-5 w-5 text-orange-400" />} />
                </div>
                {/* Middle row */}
                <div className="absolute top-1/2 left-2 -translate-y-1/2">
                  <IconContainer text="ML Inference" delay={0.5} icon={<Cpu className="h-5 w-5 text-yellow-500" />} />
                </div>
                <div className="absolute top-1/2 right-2 -translate-y-1/2">
                  <IconContainer text="Data Reports" delay={0.6} icon={<Database className="h-5 w-5 text-amber-500" />} />
                </div>
                {/* Bottom row */}
                <div className="absolute bottom-4 left-1/3 -translate-x-1/2">
                  <IconContainer text="NFT Mints" delay={0.7} icon={<Shield className="h-5 w-5 text-stone-400" />} />
                </div>
                <div className="absolute bottom-4 right-1/3 translate-x-1/2">
                  <IconContainer text="Trading" delay={0.8} icon={<Activity className="h-5 w-5 text-orange-300" />} />
                </div>
              </div>
            </div>
          </div>

          {/* Bottom gradient line */}
          <div className="absolute bottom-0 w-full h-px bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
        </div>
      </section>

      {/* No-data notice */}
      {hasNoData && !isLoading && (
        <section className="max-w-4xl mx-auto mb-8">
          <div className="flex items-center gap-3 p-4 rounded-lg bg-muted/50 border text-muted-foreground">
            <AlertTriangle className="h-5 w-5 flex-shrink-0" />
            <div className="text-sm">
              <strong>No execution intelligence yet.</strong> Patterns appear here once agents
              fail and recover on-chain (Base Sepolia) and the subgraph indexes them. No
              example or placeholder data is shown.
            </div>
          </div>
        </section>
      )}

      {/* Search and Filter */}
      <section className="max-w-4xl mx-auto mb-8">
        <div className="flex flex-wrap gap-4">
          <div className="relative flex-1 min-w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search task types..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </div>
        </div>
      </section>

      {/* Task Type Grid */}
      <section className="max-w-6xl mx-auto mb-12">
        <h2 className="text-xl font-bold mb-6">Task Types by Intelligence Depth</h2>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
          </div>
        ) : filteredTypes.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground border rounded-xl bg-muted/30">
            No task types indexed yet. This grid populates from on-chain activity once
            tasks run on Base Sepolia.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTypes.map((taskType) => (
              <GlowCard
                key={taskType.id}
                glowColor={taskType.successRate >= 90 ? 'rgba(217, 119, 6, 0.25)' : taskType.successRate >= 80 ? 'rgba(217, 119, 6, 0.2)' : 'rgba(217, 119, 6, 0.15)'}
                className="cursor-pointer"
                onClick={() => setSelectedType(selectedType === taskType.id ? null : taskType.id)}
              >
                <Card
                  className={cn(
                    'transition-all hover:border-amber-500/50 h-full',
                    selectedType === taskType.id && 'border-amber-500 ring-2 ring-amber-500/20'
                  )}
                >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-mono">{taskType.name}</CardTitle>
                    <span className="text-xs text-muted-foreground">{taskType.recentActivity}</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-6">
                    <CairnStack count={taskType.cairnCount} type="resource" />
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Success rate</span>
                        <span className={cn(
                          'font-medium',
                          taskType.successRate >= 90 ? 'text-amber-400' :
                          taskType.successRate >= 80 ? 'text-amber-500' : 'text-amber-600'
                        )}>
                          {taskType.successRate}%
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Top failure</span>
                        <span className="font-mono text-xs">{taskType.topFailure}</span>
                      </div>
                      <IntelligenceLevel cairnCount={taskType.cairnCount} />
                    </div>
                  </div>
                </CardContent>
                </Card>
              </GlowCard>
            ))}
          </div>
        )}
      </section>

      {/* Per-type intelligence detail (failure breakdown, recommended agents, cost
          estimates) will render here from real subgraph data once tasks exist. The
          previous hardcoded/always-identical mock pane was removed for honesty. */}

      {/* CTA */}
      <section className="text-center">
        <h2 className="text-2xl font-bold mb-4">Explore Live Tasks</h2>
        <p className="text-muted-foreground mb-6">
          See the intelligence in action with real task data.
        </p>
        <Link
          href="/explorer"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
        >
          Open Task Explorer
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </div>
  );
}
