'use client';

import { CheckCircle, Circle, Clock, Zap, GitBranch, Shield, Brain, Users, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface Phase {
  id: string;
  title: string;
  status: 'complete' | 'current' | 'planned';
  date: string;
  items: string[];
  highlight?: {
    title: string;
    before: string;
    after: string;
    improvement: string;
    description: string;
  };
}

const phases: Phase[] = [
  {
    id: 'phase-1',
    title: 'Phase 1: MVP',
    status: 'complete',
    date: 'March 2026',
    items: [
      '6-state recovery machine (IDLE → RUNNING → FAILED → RECOVERING → DISPUTED → RESOLVED)',
      'IPFS checkpoints with heartbeat monitoring',
      'Proportional escrow settlement',
      'Base Sepolia deployment',
      'Python SDK v0.2.3',
    ],
  },
  {
    id: 'phase-2',
    title: 'Phase 2: Core Recovery',
    status: 'current',
    date: '+2 weeks',
    items: [
      'Failure classification (LIVENESS / RESOURCE / LOGIC)',
      'Recovery scoring formula',
      'ERC-7710 scoped delegation',
      'Agent reputation system',
    ],
  },
  {
    id: 'phase-3',
    title: 'Phase 3: Execution Intelligence',
    status: 'planned',
    date: '+1 month',
    items: [
      'Pre-task intelligence queries',
      'Known failure pattern detection',
      'Agent recommendation engine',
      'Cost estimation from historical data',
    ],
  },
  {
    id: 'phase-6',
    title: 'Phase 6: Production Scaling',
    status: 'planned',
    date: '+3 months',
    items: [
      'Security audit (OpenZeppelin / Trail of Bits)',
      'Mainnet deployment (Base → Ethereum L1)',
      'Protocol DAO governance',
    ],
    highlight: {
      title: 'Merkle Checkpoint Batching',
      before: '~67,000 gas per checkpoint',
      after: '~790 gas per checkpoint (batch of 100)',
      improvement: '89-99% gas savings',
      description: 'Batch checkpoints into Merkle tree, submit only root hash on-chain, prove inclusion on-demand.',
    },
  },
  {
    id: 'phase-future',
    title: 'Future: Arbiter Network',
    status: 'planned',
    date: '+6 months',
    items: [
      'Decentralized dispute resolution',
      'Staked arbiters with slashing',
      'Multi-agent consensus',
      'Cross-chain recovery',
    ],
  },
];

export default function RoadmapPage() {
  return (
    <div className="container py-12">
      {/* Hero */}
      <section className="max-w-4xl mx-auto text-center mb-16">
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          CAIRN Protocol Roadmap
        </h1>
        <p className="text-lg text-muted-foreground">
          From Hackathon MVP to Production Protocol
        </p>
      </section>

      {/* Progress Overview */}
      <section className="max-w-4xl mx-auto mb-12">
        <div className="flex items-center justify-between gap-4 p-4 rounded-xl bg-muted/50">
          {phases.slice(0, 4).map((phase, index) => (
            <div key={phase.id} className="flex items-center gap-2">
              <div className="text-center">
                <div
                  className={cn(
                    'w-12 h-2 rounded-full mb-1',
                    phase.status === 'complete' && 'bg-amber-500',
                    phase.status === 'current' && 'bg-amber-600 animate-pulse',
                    phase.status === 'planned' && 'bg-muted'
                  )}
                />
                <span className="text-xs text-muted-foreground">
                  {phase.status === 'complete' ? '100%' : phase.status === 'current' ? 'Active' : '0%'}
                </span>
              </div>
              {index < 3 && <div className="w-8 h-px bg-border" />}
            </div>
          ))}
        </div>
      </section>

      {/* Timeline */}
      <section className="max-w-4xl mx-auto">
        <div className="space-y-0">
          {phases.map((phase, index) => (
            <div key={phase.id} className="roadmap-phase relative">
              {/* Phase Status Icon */}
              <div
                className={cn(
                  'absolute left-0 top-0 w-4 h-4 -translate-x-1/2 rounded-full border-2 border-background z-10',
                  phase.status === 'complete' && 'bg-amber-500',
                  phase.status === 'current' && 'bg-amber-600 animate-pulse',
                  phase.status === 'planned' && 'bg-muted'
                )}
              />

              <div className="pb-8">
                {/* Phase Header */}
                <div className="flex items-center gap-4 mb-4">
                  <div
                    className={cn(
                      'flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium',
                      phase.status === 'complete' && 'bg-amber-500/10 text-amber-500',
                      phase.status === 'current' && 'bg-amber-600/10 text-amber-600',
                      phase.status === 'planned' && 'bg-muted text-muted-foreground'
                    )}
                  >
                    {phase.status === 'complete' && <CheckCircle className="h-4 w-4" />}
                    {phase.status === 'current' && <Clock className="h-4 w-4" />}
                    {phase.status === 'planned' && <Circle className="h-4 w-4" />}
                    {phase.status === 'complete' ? 'Complete' : phase.status === 'current' ? 'In Progress' : 'Planned'}
                  </div>
                  <span className="text-sm text-muted-foreground">{phase.date}</span>
                </div>

                <h2 className="text-xl font-bold mb-4">{phase.title}</h2>

                {/* Phase Items */}
                <ul className="space-y-2 mb-4">
                  {phase.items.map((item, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="text-muted-foreground/50 mt-1">├──</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>

                {/* Highlight Box (Merkle Optimization) */}
                {phase.highlight && (
                  <Card className="border-amber-500/30 bg-amber-500/5">
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center gap-2 text-amber-500 text-base">
                        <Zap className="h-5 w-5" />
                        {phase.highlight.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Current MVP:</span>
                          <p className="font-mono text-red-400">{phase.highlight.before}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">With Merkle:</span>
                          <p className="font-mono text-amber-400">{phase.highlight.after}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/10">
                        <span className="text-2xl font-bold text-amber-500">{phase.highlight.improvement}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{phase.highlight.description}</p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Current Focus */}
      <section className="max-w-4xl mx-auto mt-12">
        <Card className="border-amber-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-amber-500 animate-pulse" />
              Current Focus: Synthesis Hackathon 2026
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-muted/50 text-center">
                <Shield className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                <h3 className="font-semibold mb-1">Live Demo</h3>
                <p className="text-sm text-muted-foreground">Fully functional on Base Sepolia</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50 text-center">
                <GitBranch className="h-8 w-8 text-stone-400 mx-auto mb-2" />
                <h3 className="font-semibold mb-1">Open Source</h3>
                <p className="text-sm text-muted-foreground">MIT licensed, public repo</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50 text-center">
                <Users className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                <h3 className="font-semibold mb-1">Community</h3>
                <p className="text-sm text-muted-foreground">Building in public</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto mt-12 text-center">
        <h2 className="text-2xl font-bold mb-4">Join the Journey</h2>
        <p className="text-muted-foreground mb-6">
          Follow our progress, contribute to the protocol, or start integrating today.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <a
            href="https://github.com/MarouaBoud/cairn-protocol"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-colors"
          >
            <GitBranch className="h-5 w-5" />
            View on GitHub
          </a>
          <Link
            href="/explorer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border hover:bg-muted transition-colors"
          >
            Try Live Demo
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
