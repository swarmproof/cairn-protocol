'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Brain, Search, ArrowRight, Activity, Database, Shield, Zap, Network, Cpu } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CairnStack, IntelligenceLevel } from '@/components/cairn';
import { cn } from '@/lib/utils';
import { Radar, IconContainer } from '@/components/ui/radar';
import { Spotlight } from '@/components/ui/spotlight';
import { GlowCard } from '@/components/ui/glow-card';

interface TaskType {
  id: string;
  name: string;
  cairnCount: number;
  successRate: number;
  recentActivity: string;
  topFailure: string;
}

const mockTaskTypes: TaskType[] = [
  {
    id: 'defi.rebalance',
    name: 'defi.rebalance',
    cairnCount: 47,
    successRate: 87,
    recentActivity: '+3 today',
    topFailure: 'RATE_LIMIT (52%)',
  },
  {
    id: 'api.fetch',
    name: 'api.fetch',
    cairnCount: 34,
    successRate: 91,
    recentActivity: '+1 today',
    topFailure: 'TIMEOUT (41%)',
  },
  {
    id: 'data.report',
    name: 'data.report',
    cairnCount: 23,
    successRate: 94,
    recentActivity: '+0 today',
    topFailure: 'RESOURCE (38%)',
  },
  {
    id: 'ml.inference',
    name: 'ml.inference',
    cairnCount: 12,
    successRate: 78,
    recentActivity: '+2 today',
    topFailure: 'OOM (67%)',
  },
  {
    id: 'defi.trade',
    name: 'defi.trade',
    cairnCount: 8,
    successRate: 82,
    recentActivity: '+1 today',
    topFailure: 'SLIPPAGE (45%)',
  },
  {
    id: 'nft.mint',
    name: 'nft.mint',
    cairnCount: 5,
    successRate: 95,
    recentActivity: '+0 today',
    topFailure: 'GAS (60%)',
  },
];

export default function IntelligencePage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string | null>(null);

  const filteredTypes = mockTaskTypes.filter((t) =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalCairns = mockTaskTypes.reduce((sum, t) => sum + t.cairnCount, 0);

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
            <p className="text-slate-500 text-sm">
              <strong className="text-white">{totalCairns} cairns</strong> across{' '}
              <strong className="text-white">{mockTaskTypes.length}</strong> task types
            </p>
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
          <select className="px-4 py-2 rounded-lg border bg-background">
            <option>All time</option>
            <option>Last 24h</option>
            <option>Last 7d</option>
            <option>Last 30d</option>
          </select>
        </div>
      </section>

      {/* Task Type Grid */}
      <section className="max-w-6xl mx-auto mb-12">
        <h2 className="text-xl font-bold mb-6">Task Types by Intelligence Depth</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTypes.map((taskType) => (
            <GlowCard
              key={taskType.id}
              glowColor={taskType.successRate >= 90 ? 'rgba(34, 197, 94, 0.2)' : taskType.successRate >= 80 ? 'rgba(59, 130, 246, 0.2)' : 'rgba(245, 158, 11, 0.2)'}
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
                        taskType.successRate >= 90 ? 'text-green-500' :
                        taskType.successRate >= 80 ? 'text-blue-500' : 'text-amber-500'
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
      </section>

      {/* Selected Task Type Detail */}
      {selectedType && (
        <section className="max-w-4xl mx-auto mb-12">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="font-mono">{selectedType}</span>
                <span className="text-sm font-normal text-muted-foreground">Intelligence Detail</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-8">
                {/* Known Failure Patterns */}
                <div>
                  <h3 className="font-semibold mb-4 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500" />
                    Known Failure Patterns
                  </h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                      <span className="font-mono text-sm">RATE_LIMIT</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-2 rounded-full bg-muted overflow-hidden">
                          <div className="h-full bg-red-500" style={{ width: '52%' }} />
                        </div>
                        <span className="text-xs text-muted-foreground">52%</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                      <span className="font-mono text-sm">GAS_SPIKE</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-2 rounded-full bg-muted overflow-hidden">
                          <div className="h-full bg-amber-500" style={{ width: '35%' }} />
                        </div>
                        <span className="text-xs text-muted-foreground">35%</span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                      <span className="font-mono text-sm">HEARTBEAT_MISS</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-2 rounded-full bg-muted overflow-hidden">
                          <div className="h-full bg-blue-500" style={{ width: '13%' }} />
                        </div>
                        <span className="text-xs text-muted-foreground">13%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recommendations */}
                <div>
                  <h3 className="font-semibold mb-4 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    Intelligence Insights
                  </h3>
                  <div className="space-y-3 text-sm">
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <strong className="text-amber-500">Avoid:</strong>
                      <span className="text-muted-foreground ml-2">00:00-04:00 UTC (12 failures)</span>
                    </div>
                    <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                      <strong className="text-green-500">Best agent:</strong>
                      <span className="text-muted-foreground ml-2">0x91a2...4b (94% success)</span>
                    </div>
                    <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                      <strong className="text-blue-500">Est. cost:</strong>
                      <span className="text-muted-foreground ml-2">P50: 0.023 ETH</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      )}

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
