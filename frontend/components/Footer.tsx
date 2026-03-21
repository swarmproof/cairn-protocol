'use client';

import Link from 'next/link';
import { Github, FileText, ExternalLink } from 'lucide-react';

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
    { label: 'Contract', href: 'https://sepolia.basescan.org/address/0x2eFd1De57BfF1Ea3E40b049F70bb58590Ea73417', external: true },
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

        {/* Bottom */}
        <div className="mt-12 pt-8 border-t flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} CAIRN Protocol. MIT License.
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
