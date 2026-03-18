'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { Activity } from 'lucide-react';

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-6 w-6 text-cairn-running" />
          <span className="text-xl font-bold">CAIRN Protocol</span>
          <span className="text-xs text-muted-foreground ml-2 px-2 py-0.5 bg-muted rounded">
            Base Sepolia
          </span>
        </div>
        <ConnectButton />
      </div>
    </header>
  );
}
