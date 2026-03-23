'use client';

import Link from 'next/link';
import { Cpu, Network, ArrowRight, CheckCircle, Bot, Zap, BookOpen } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Spotlight } from '@/components/ui/spotlight';
import { SplineScene } from '@/components/ui/spline-scene';

export default function FrameworksPage() {
  return (
    <div className="container py-12">
      {/* Live Status Banner */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="rounded-lg bg-cyan-500/10 border border-cyan-500/30 p-4">
          <div className="flex items-start gap-3">
            <Zap className="h-5 w-5 text-cyan-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-cyan-500">Live on Base Sepolia (testnet)</p>
              <p className="text-sm text-muted-foreground mt-1">
                Full recovery protocol with Merkle checkpoints, automatic settlement, and Python SDK.
                <Link href="/explorer" className="text-cyan-500 hover:underline ml-1">
                  Try the demo →
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Hero with Spotlight */}
      <section className="relative max-w-4xl mx-auto text-center mb-16 p-8 rounded-2xl bg-black/[0.96] border border-slate-800 overflow-hidden">
        <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(6, 182, 212, 0.1)" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500/10 text-cyan-500 text-sm font-medium mb-6">
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
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-cyan-600 text-white font-semibold hover:bg-cyan-700 transition-colors"
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
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
      </section>

      {/* Interactive 3D Agent */}
      <section className="mb-16">
        <Card className="max-w-4xl mx-auto h-[400px] bg-black/[0.96] relative overflow-hidden border-slate-800">
          <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(6, 182, 212, 0.1)" />

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
                  href="/explorer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 text-white font-medium hover:bg-cyan-700 transition-colors text-sm"
                >
                  Try Live Demo
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
          <Card className="border-cyan-500/20 bg-cyan-500/5">
            <CardContent className="p-6">
              <div className="w-12 h-12 rounded-lg bg-cyan-500/10 flex items-center justify-center mb-4">
                <span className="text-2xl">🪨</span>
              </div>
              <h3 className="font-semibold mb-2">Place Cairns</h3>
              <p className="text-sm text-muted-foreground">
                Every failure writes a permanent record — the cause, the context,
                the recovery path. Trail markers for future agents.
              </p>
            </CardContent>
          </Card>

          <Card className="border-teal-500/20 bg-teal-500/5">
            <CardContent className="p-6">
              <div className="w-12 h-12 rounded-lg bg-teal-500/10 flex items-center justify-center mb-4">
                <span className="text-2xl">🔍</span>
              </div>
              <h3 className="font-semibold mb-2">Query Intelligence</h3>
              <p className="text-sm text-muted-foreground">
                Before executing, agents query the graph. Known failure patterns,
                recommended agents, cost estimates — all from historical data.
              </p>
            </CardContent>
          </Card>

          <Card className="border-slate-500/20 bg-slate-500/5">
            <CardContent className="p-6">
              <div className="w-12 h-12 rounded-lg bg-slate-500/10 flex items-center justify-center mb-4">
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

      {/* What's Built */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">What's Live</h2>
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Core Protocol */}
          <Card className="border-cyan-500/30 bg-cyan-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-cyan-400">
                <CheckCircle className="h-5 w-5" />
                Core Protocol
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <span className="text-cyan-400">✓</span>
                <div>
                  <p className="font-medium">6-state recovery machine</p>
                  <p className="text-sm text-muted-foreground">IDLE → RUNNING → FAILED → RECOVERING → DISPUTED → RESOLVED</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-cyan-400">✓</span>
                <div>
                  <p className="font-medium">Merkle checkpoint batching</p>
                  <p className="text-sm text-muted-foreground">89-99% gas savings with batch verification</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-cyan-400">✓</span>
                <div>
                  <p className="font-medium">Automatic settlement</p>
                  <p className="text-sm text-muted-foreground">Proportional split based on checkpoint work</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-cyan-400">✓</span>
                <div>
                  <p className="font-medium">Heartbeat monitoring</p>
                  <p className="text-sm text-muted-foreground">Automatic stale detection & failure triggers</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* SDK & Integration */}
          <Card className="border-teal-500/30 bg-teal-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-teal-400">
                <Bot className="h-5 w-5" />
                SDK & Integration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <span className="text-teal-400">✓</span>
                <div>
                  <p className="font-medium">Python SDK</p>
                  <p className="text-sm text-muted-foreground">CairnClient + CairnAgent wrappers</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-teal-400">✓</span>
                <div>
                  <p className="font-medium">Agent-readable endpoints</p>
                  <p className="text-sm text-muted-foreground">/integrate/skill.md for autonomous integration</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-teal-400">✓</span>
                <div>
                  <p className="font-medium">Event pipeline</p>
                  <p className="text-sm text-muted-foreground">Off-chain listener with Bonfires indexing</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-teal-400">✓</span>
                <div>
                  <p className="font-medium">Verified contract</p>
                  <p className="text-sm text-muted-foreground">Live on Base Sepolia (testnet) with Basescan verification</p>
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
            { step: '1', title: 'Submit Task', desc: 'Escrow + agents + deadline', icon: '📝' },
            { step: '2', title: 'Execute + Checkpoint', desc: 'Batch progress to Merkle tree', icon: '💾' },
            { step: '3', title: 'Heartbeat', desc: 'Prove liveness continuously', icon: '💓' },
            { step: '4', title: 'Auto-Recovery', desc: 'Protocol routes on failure', icon: '🔄' },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="w-12 h-12 rounded-full bg-cyan-500/10 text-2xl flex items-center justify-center mx-auto mb-3">
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
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-cyan-600 text-white font-semibold hover:bg-cyan-700 transition-colors"
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
