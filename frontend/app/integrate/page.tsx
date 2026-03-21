'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Code, Package, FileText, Terminal, ArrowRight, Copy, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Spotlight } from '@/components/ui/spotlight';
import { BorderBeam } from '@/components/ui/border-beam';

type Framework = 'langgraph' | 'agentkit' | 'olas' | 'custom';

const frameworks: Record<Framework, { name: string; code: string }> = {
  langgraph: {
    name: 'LangGraph',
    code: `from cairn_sdk import CairnClient
from langgraph.prebuilt import create_react_agent

# Initialize CAIRN (Base Sepolia)
cairn = CairnClient(
    rpc_url="https://sepolia.base.org",
    contract="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417"
)

# Wrap your agent with CAIRN protection
@cairn.protect(escrow="0.1 ETH", fallback_agent="0x...")
async def my_agent(state):
    result = await create_react_agent(...)
    cairn.checkpoint(state=state, progress=0.5)
    return result`,
  },
  agentkit: {
    name: 'Coinbase AgentKit',
    code: `import { CairnClient } from '@cairn/sdk';
import { AgentKit } from '@coinbase/agentkit';

// Initialize CAIRN (Base Sepolia)
const cairn = new CairnClient({
  rpcUrl: 'https://sepolia.base.org',
  contract: '0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417'
});

// Create protected agent
const agent = await cairn.protect({
  agent: myAgentKit,
  escrow: '0.1',
  fallbackAgent: '0x...'
});

await agent.execute(task);`,
  },
  olas: {
    name: 'Olas',
    code: `from cairn_sdk import CairnClient
from olas import OlasAgent

# Initialize CAIRN
cairn = CairnClient(
    rpc_url="https://sepolia.base.org",
    contract="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417"
)

# Wrap Olas agent with CAIRN
class ProtectedOlasAgent(OlasAgent):
    @cairn.protect(escrow="0.1 ETH")
    async def execute(self, task):
        # Checkpoint on significant progress
        for step in self.steps:
            await step.run()
            cairn.checkpoint(step=step.id)
        return self.result`,
  },
  custom: {
    name: 'Custom Agent',
    code: `from cairn_sdk import CairnClient

# Initialize CAIRN client
cairn = CairnClient(
    rpc_url="https://sepolia.base.org",
    contract="0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417"
)

# Submit task with escrow
task_id = await cairn.submit_task(
    escrow="0.1 ETH",
    primary_agent="0xYourAgent",
    fallback_agent="0xBackup",
    deadline=3600  # 1 hour
)

# Your agent sends heartbeats
async def agent_loop():
    while running:
        await cairn.heartbeat(task_id)
        # ... your agent logic ...
        await cairn.checkpoint(task_id, state=current_state)`,
  },
};

export default function IntegratePage() {
  const [selectedFramework, setSelectedFramework] = useState<Framework>('langgraph');
  const [copied, setCopied] = useState(false);

  const copyCode = () => {
    navigator.clipboard.writeText(frameworks[selectedFramework].code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="container py-12">
      {/* Hero with Spotlight */}
      <section className="relative max-w-4xl mx-auto text-center mb-16 p-8 rounded-2xl bg-black/[0.96] border border-slate-800 overflow-hidden">
        <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(217, 119, 6, 0.1)" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 text-amber-500 text-sm font-medium mb-6">
            <Code className="h-4 w-4" />
            For Developers
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            3 lines of code.
            <br />
            <span className="text-slate-400">Zero breaking changes.</span>
          </h1>
          <p className="text-lg text-slate-400 mb-8 max-w-2xl mx-auto">
            CAIRN wraps your existing agent with checkpoint-based recovery.
            No architecture changes. No new patterns to learn.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a
              href="https://github.com/MarouaBoud/cairn-protocol/tree/main/sdk#readme"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
            >
              <FileText className="h-5 w-5" />
              Quickstart Guide
              <ArrowRight className="h-4 w-4" />
            </a>
            <a
              href="https://github.com/MarouaBoud/cairn-protocol/tree/main/sdk"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 transition-colors"
            >
              <Package className="h-5 w-5" />
              View SDK
            </a>
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
      </section>

      {/* Install Commands */}
      <section className="mb-16">
        <div className="max-w-2xl mx-auto">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Python</span>
                  <Terminal className="h-4 w-4 text-muted-foreground" />
                </div>
                <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                  pip install cairn-sdk
                </code>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">JavaScript</span>
                  <Terminal className="h-4 w-4 text-muted-foreground" />
                </div>
                <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                  npm i @cairn/sdk
                </code>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Framework Tabs */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">Integration Examples</h2>
        <div className="max-w-4xl mx-auto">
          {/* Tabs */}
          <div className="flex flex-wrap gap-2 mb-4">
            {(Object.keys(frameworks) as Framework[]).map((fw) => (
              <button
                key={fw}
                onClick={() => setSelectedFramework(fw)}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  selectedFramework === fw
                    ? 'bg-amber-600 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                )}
              >
                {frameworks[fw].name}
              </button>
            ))}
          </div>

          {/* Code Block */}
          <div className="relative rounded-lg overflow-hidden">
            <BorderBeam size={200} duration={12} colorFrom="#d97706" colorTo="#c2410c" />
            <pre className="bg-slate-900 rounded-lg p-6 overflow-x-auto">
              <code className="text-sm text-slate-300 font-mono">
                {frameworks[selectedFramework].code}
              </code>
            </pre>
            <button
              onClick={copyCode}
              className="absolute top-4 right-4 p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors z-10"
            >
              {copied ? (
                <Check className="h-4 w-4 text-amber-400" />
              ) : (
                <Copy className="h-4 w-4 text-slate-400" />
              )}
            </button>
          </div>
        </div>
      </section>

      {/* Production Signals */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8">Production Ready</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
          <div className="p-4 rounded-lg bg-muted/50 text-center">
            <div className="font-semibold mb-1 text-amber-500">✓</div>
            <div className="text-sm">TypeScript Types</div>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 text-center">
            <div className="font-semibold mb-1 text-amber-500">✓</div>
            <div className="text-sm">Full Docs</div>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 text-center">
            <div className="font-semibold mb-1 text-amber-500">✓</div>
            <div className="text-sm">95%+ Coverage</div>
          </div>
          <div className="p-4 rounded-lg bg-muted/50 text-center">
            <div className="font-semibold mb-1 text-amber-500">✓</div>
            <div className="text-sm">MIT License</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-4 mt-8 text-sm">
          <span className="px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 font-medium">
            ERC-8183 <span className="text-xs opacity-60">(Phase 4)</span>
          </span>
          <span className="px-3 py-1 rounded-full bg-orange-500/10 text-orange-400 font-medium">
            ERC-8004 <span className="text-xs opacity-60">(Phase 4)</span>
          </span>
          <span className="px-3 py-1 rounded-full bg-stone-500/10 text-stone-400 font-medium">
            ERC-7710 <span className="text-xs opacity-60">(Phase 4)</span>
          </span>
        </div>
      </section>

      {/* CTA */}
      <section className="text-center">
        <h2 className="text-2xl font-bold mb-4">Start Building</h2>
        <p className="text-muted-foreground mb-6">
          Questions? Join our Discord or check the docs.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <a
            href="https://github.com/MarouaBoud/cairn-protocol#readme"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-amber-600 text-white font-semibold hover:bg-amber-700 transition-colors"
          >
            Full Documentation
            <ArrowRight className="h-4 w-4" />
          </a>
          <Link
            href="/explorer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg border hover:bg-muted transition-colors"
          >
            Try Live Demo
          </Link>
        </div>
      </section>
    </div>
  );
}
