'use client';

import Link from 'next/link';
import { Cpu, Network, ArrowRight, CheckCircle, Bot, Zap, AlertTriangle, BookOpen } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Spotlight } from '@/components/ui/spotlight';
import { SplineScene } from '@/components/ui/spline-scene';

export default function FrameworksPage() {
  return (
    <div className="container py-12">
      {/* MVP Status Banner */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-amber-500">Phase 1 of 6 — MVP Demo</p>
              <p className="text-sm text-muted-foreground mt-1">
                This is the foundation. Core escrow + checkpoints + heartbeats are live.
                <strong className="text-foreground"> Coming next:</strong> automatic fallback selection,
                collective intelligence layer, arbiter network.
                <Link href="/roadmap" className="text-amber-500 hover:underline ml-1">
                  See full roadmap →
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Hero with Spotlight */}
      <section className="relative max-w-4xl mx-auto text-center mb-16 p-8 rounded-2xl bg-black/[0.96] border border-slate-800 overflow-hidden">
        <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(217, 119, 6, 0.1)" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 text-amber-500 text-sm font-medium mb-6">
            <Cpu className="h-4 w-4" />
            For Agent Framework Teams
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            Agent Infrastructure.
            <br />
            <span className="text-slate-400">Not human monitoring.</span>
          </h1>
          <p className="text-lg text-slate-400 mb-8 max-w-2xl mx-auto">
            CAIRN is infrastructure that agents use autonomously.
            When an agent fails, the protocol routes to a fallback — no human required.
            Your framework just needs to integrate once.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/integrate"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
            >
              <Zap className="h-5 w-5" />
              Integration Guide
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="https://github.com/MarouaBoud/cairn-protocol/blob/main/PRDs/CONSOLIDATED-CONTRACT-SPEC.md"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors"
            >
              <BookOpen className="h-5 w-5" />
              Protocol Spec
            </a>
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
      </section>

      {/* Interactive 3D Agent */}
      <section className="mb-16">
        <Card className="max-w-4xl mx-auto h-[400px] bg-black/[0.96] relative overflow-hidden border-slate-800">
          <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(217, 119, 6, 0.1)" />

          <div className="flex h-full">
            {/* Left content */}
            <div className="flex-1 p-8 relative z-10 flex flex-col justify-center">
              <h2 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-neutral-50 to-neutral-400 mb-4">
                Autonomous
                <br />
                Recovery
              </h2>
              <p className="text-slate-400 max-w-md">
                CAIRN wraps agent execution with checkpoint-based recovery.
                When failures happen, the protocol detects it via heartbeat monitoring
                and routes to the best fallback agent — automatically.
              </p>
              <div className="flex gap-3 mt-6">
                <Link
                  href="/intelligence"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-600 text-white font-medium hover:bg-amber-700 transition-colors text-sm"
                >
                  See Intelligence Layer
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>

            {/* Right content - 3D Robot */}
            <div className="flex-1 relative">
              <SplineScene
                scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
                className="w-full h-full"
              />
            </div>
          </div>
        </Card>
      </section>

      {/* Core Vision */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">The Vision: Agents Learn Together</h2>
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          <Card className="border-amber-500/20 bg-amber-500/5">
            <CardContent className="p-6">
              <div className="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center mb-4">
                <span className="text-2xl">🪨</span>
              </div>
              <h3 className="font-semibold mb-2">Place Cairns</h3>
              <p className="text-sm text-muted-foreground">
                Every failure writes a permanent record — the cause, the context,
                the recovery path. Trail markers for future agents.
              </p>
            </CardContent>
          </Card>

          <Card className="border-amber-500/20 bg-amber-500/5">
            <CardContent className="p-6">
              <div className="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center mb-4">
                <span className="text-2xl">🔍</span>
              </div>
              <h3 className="font-semibold mb-2">Query Intelligence</h3>
              <p className="text-sm text-muted-foreground">
                Before executing, agents query the graph. Known failure patterns,
                recommended agents, cost estimates — all from historical data.
              </p>
            </CardContent>
          </Card>

          <Card className="border-amber-500/20 bg-amber-500/5">
            <CardContent className="p-6">
              <div className="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center mb-4">
                <span className="text-2xl">📈</span>
              </div>
              <h3 className="font-semibold mb-2">Compound Learning</h3>
              <p className="text-sm text-muted-foreground">
                More agents → more cairns → richer intelligence → better outcomes.
                The flywheel that execution history cannot fork.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* What's Built vs What's Coming */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">MVP Status</h2>
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Built */}
          <Card className="border-emerald-500/30 bg-emerald-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-400">
                <CheckCircle className="h-5 w-5" />
                Phase 1: Live Now
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <span className="text-emerald-400">✓</span>
                <div>
                  <p className="font-medium">6-state machine</p>
                  <p className="text-sm text-muted-foreground">IDLE → RUNNING → FAILED → RECOVERING → DISPUTED → RESOLVED</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-emerald-400">✓</span>
                <div>
                  <p className="font-medium">Escrow + settlement</p>
                  <p className="text-sm text-muted-foreground">Proportional split based on checkpoint work</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-emerald-400">✓</span>
                <div>
                  <p className="font-medium">Heartbeat monitoring</p>
                  <p className="text-sm text-muted-foreground">Automatic stale detection</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-emerald-400">✓</span>
                <div>
                  <p className="font-medium">Python SDK</p>
                  <p className="text-sm text-muted-foreground">CairnClient + CairnAgent wrappers</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Coming */}
          <Card className="border-slate-500/30 bg-slate-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-slate-400">
                <Network className="h-5 w-5" />
                Phases 2-6: Coming Next
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <span className="text-slate-500">○</span>
                <div>
                  <p className="font-medium">Automatic fallback selection</p>
                  <p className="text-sm text-muted-foreground">Query pool by task_type + reputation (PRD-04)</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-slate-500">○</span>
                <div>
                  <p className="font-medium">Intelligence layer</p>
                  <p className="text-sm text-muted-foreground">Pre-task queries + failure patterns (PRD-03)</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-slate-500">○</span>
                <div>
                  <p className="font-medium">Failure classification</p>
                  <p className="text-sm text-muted-foreground">LIVENESS / RESOURCE / LOGIC taxonomy (PRD-02)</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-slate-500">○</span>
                <div>
                  <p className="font-medium">Arbiter network</p>
                  <p className="text-sm text-muted-foreground">Decentralized dispute resolution (PRD-05)</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* How It Works (Agent Perspective) */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">How Agents Use CAIRN</h2>
        <div className="grid md:grid-cols-4 gap-6 max-w-4xl mx-auto">
          {[
            { step: '1', title: 'Query Intel', desc: 'Check failure patterns first', icon: '🔍' },
            { step: '2', title: 'Execute + Checkpoint', desc: 'Save progress on-chain', icon: '💾' },
            { step: '3', title: 'Heartbeat', desc: 'Prove liveness continuously', icon: '💓' },
            { step: '4', title: 'Auto-Recovery', desc: 'Protocol routes on failure', icon: '🔄' },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="w-12 h-12 rounded-full bg-amber-500/10 text-2xl flex items-center justify-center mx-auto mb-3">
                {item.icon}
              </div>
              <h3 className="font-semibold mb-1">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="text-center">
        <h2 className="text-2xl font-bold mb-4">Ready to integrate?</h2>
        <p className="text-muted-foreground mb-6">
          Start with the SDK integration guide or explore the live demo.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/integrate"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
          >
            SDK Integration Guide
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/explorer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border hover:bg-muted transition-colors"
          >
            Explore Live Tasks
          </Link>
        </div>
      </section>
    </div>
  );
}
