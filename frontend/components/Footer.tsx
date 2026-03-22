'use client';

import Link from 'next/link';
import { Github, FileText, ExternalLink } from 'lucide-react';

// CairnCore contract on Base Sepolia
const CAIRN_CONTRACT = '0xB65596B21d670b6C670106C3e3c7E5FFf8E3A640';

const footerLinks = {
  protocol: [
    { label: 'Operators', href: '/operators' },
    { label: 'Developers', href: '/integrate' },
    { label: 'Intelligence', href: '/intelligence' },
    { label: 'Roadmap', href: '/roadmap' },
  ],
  resources: [
    { label: 'Documentation', href: 'https://github.com/MarouaBoud/cairn-protocol#readme', external: true },
    { label: 'GitHub', href: 'https://github.com/MarouaBoud/cairn-protocol', external: true },
    { label: 'Contract', href: `https://sepolia.basescan.org/address/${CAIRN_CONTRACT}`, external: true },
    { label: 'skill.md', href: '/skill.md', external: false },
    { label: 'cairn.md', href: '/cairn.md', external: false },
  ],
  community: [
    { label: 'Synthesis 2026', href: 'https://synthesis.md', external: true },
  ],
};

export function Footer() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="container py-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 font-bold text-xl mb-4">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground">
                <span className="text-sm">◉</span>
              </div>
              <span>CAIRN</span>
            </Link>
            <p className="text-sm text-muted-foreground mb-4">
              Agents learn together.
            </p>
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 rounded text-xs bg-blue-500/10 text-blue-500 font-medium">
                Built on Base
              </span>
              <span className="px-2 py-1 rounded text-xs bg-purple-500/10 text-purple-500 font-medium">
                Synthesis 2026
              </span>
            </div>
          </div>

          {/* Protocol Links */}
          <div>
            <h4 className="font-semibold mb-4">Protocol</h4>
            <ul className="space-y-2">
              {footerLinks.protocol.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-semibold mb-4">Resources</h4>
            <ul className="space-y-2">
              {footerLinks.resources.map((link) => (
                <li key={link.href}>
                  {link.external ? (
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                    >
                      {link.label}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                    >
                      {link.label}
                      <FileText className="h-3 w-3" />
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {/* Community */}
          <div>
            <h4 className="font-semibold mb-4">Community</h4>
            <ul className="space-y-2">
              {footerLinks.community.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                  >
                    {link.label}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Testnet Notice */}
        <div className="mt-8 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
          <div className="flex items-start gap-3">
            <div className="shrink-0 mt-0.5">
              <span className="text-amber-500 text-lg">⚠️</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-amber-500">Testnet Only</p>
              <p className="text-xs text-muted-foreground mt-1">
                This is a testnet deployment on Base Sepolia. Do not use real funds.
                The protocol is under active development for Synthesis Hackathon 2026.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom */}
        <div className="mt-12 pt-8 border-t flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} CAIRN Protocol. Licensed under <a href="https://github.com/MarouaBoud/cairn-protocol/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="text-amber-500 hover:underline">MPL-2.0</a>.
          </p>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/MarouaBoud/cairn-protocol"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="GitHub"
            >
              <Github className="h-5 w-5" />
            </a>
            <a
              href="https://github.com/MarouaBoud/cairn-protocol#readme"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Documentation"
            >
              <FileText className="h-5 w-5" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
