'use client';

import Link from 'next/link';
import { Shield, DollarSign, ArrowRight, CheckCircle, AlertTriangle, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Spotlight } from '@/components/ui/spotlight';
import { SplineScene } from '@/components/ui/spline-scene';

export default function OperatorsPage() {
  return (
    <div className="container py-12">
      {/* Hero with Spotlight */}
      <section className="relative max-w-4xl mx-auto text-center mb-16 p-8 rounded-2xl bg-black/[0.96] border border-slate-800 overflow-hidden">
        <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(217, 119, 6, 0.1)" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 text-amber-500 text-sm font-medium mb-6">
            <Shield className="h-4 w-4" />
            For Operations Teams
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            Never lose work.
            <br />
            <span className="text-slate-400">Recover in 20 minutes, not 4 hours.</span>
          </h1>
          <p className="text-lg text-slate-400 mb-8 max-w-2xl mx-auto">
            Your agents fail. That's not the problem.
            Losing escrow, wasting time, starting over — that's the problem.
            CAIRN fixes this.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/explorer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
            >
              <Zap className="h-5 w-5" />
              Try Demo
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="https://github.com/MarouaBoud/cairn-protocol#for-operators"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Read Operator Guide
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
                Your AI Agent,
                <br />
                Protected
              </h2>
              <p className="text-slate-400 max-w-md">
                CAIRN wraps your agent with checkpoint-based recovery.
                When failures happen, the network catches them and routes to fallback agents — automatically.
              </p>
              <div className="flex gap-3 mt-6">
                <Link
                  href="/integrate"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-600 text-white font-medium hover:bg-amber-700 transition-colors text-sm"
                >
                  Start Integrating
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

      {/* Before/After Comparison */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">Before vs After CAIRN</h2>
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Before */}
          <Card className="border-red-500/30 bg-red-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-400">
                <AlertTriangle className="h-5 w-5" />
                Without CAIRN
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <span className="text-red-400">✗</span>
                <div>
                  <p className="font-medium">Agent fails at 3am</p>
                  <p className="text-sm text-muted-foreground">You wake up to a mess</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-red-400">✗</span>
                <div>
                  <p className="font-medium">4 hours to restart</p>
                  <p className="text-sm text-muted-foreground">Debug, find state, retry manually</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-red-400">✗</span>
                <div>
                  <p className="font-medium">Lost escrow</p>
                  <p className="text-sm text-muted-foreground">Partial work = total loss</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-red-400">✗</span>
                <div>
                  <p className="font-medium">Same bug, different day</p>
                  <p className="text-sm text-muted-foreground">No learning across failures</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* After */}
          <Card className="border-amber-500/30 bg-amber-500/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-amber-400">
                <CheckCircle className="h-5 w-5" />
                With CAIRN
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3">
                <span className="text-amber-400">✓</span>
                <div>
                  <p className="font-medium">Auto-detection</p>
                  <p className="text-sm text-muted-foreground">Heartbeat monitoring catches failures instantly</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-amber-400">✓</span>
                <div>
                  <p className="font-medium">21 min average recovery</p>
                  <p className="text-sm text-muted-foreground">Fallback agent resumes from checkpoint</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-amber-400">✓</span>
                <div>
                  <p className="font-medium">Fair settlement</p>
                  <p className="text-sm text-muted-foreground">Escrow split based on verified work</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-amber-400">✓</span>
                <div>
                  <p className="font-medium">Network intelligence</p>
                  <p className="text-sm text-muted-foreground">Every failure teaches all future agents</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ROI Calculator Placeholder */}
      <section className="mb-16">
        <Card className="max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-amber-500" />
              ROI Calculator
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">
                Example savings based on typical agent operations
              </p>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-lg bg-muted">
                  <div className="text-2xl font-bold text-amber-500">$47K</div>
                  <div className="text-xs text-muted-foreground">Example savings</div>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <div className="text-2xl font-bold text-amber-500">98.7%</div>
                  <div className="text-xs text-muted-foreground">Target recovery</div>
                </div>
                <div className="p-4 rounded-lg bg-muted">
                  <div className="text-2xl font-bold text-slate-400">156</div>
                  <div className="text-xs text-muted-foreground">Example tasks</div>
                </div>
              </div>
              <Link
                href="/explorer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
              >
                See Live Data
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* How It Works */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">How It Works</h2>
        <div className="grid md:grid-cols-4 gap-6 max-w-4xl mx-auto">
          {[
            { step: '1', title: 'Submit Task', desc: 'Lock escrow, assign agents' },
            { step: '2', title: 'Monitor', desc: 'Heartbeats + checkpoints' },
            { step: '3', title: 'Recover', desc: 'Auto-failover on miss' },
            { step: '4', title: 'Settle', desc: 'Fair escrow split' },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="w-12 h-12 rounded-full bg-amber-500/10 text-amber-500 font-bold text-xl flex items-center justify-center mx-auto mb-3">
                {item.step}
              </div>
              <h3 className="font-semibold mb-1">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="text-center">
        <h2 className="text-2xl font-bold mb-4">Ready to protect your agents?</h2>
        <p className="text-muted-foreground mb-6">
          Start with a free demo on Base Sepolia testnet.
        </p>
        <Link
          href="/explorer"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
        >
          Launch Demo Dashboard
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </div>
  );
}
