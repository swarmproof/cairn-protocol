'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { CairnLogo } from '@/components/ui/cairn-logo';

const navLinks = [
  { href: '/operators', label: 'Frameworks' },
  { href: '/integrate', label: 'SDK' },
  { href: '/intelligence', label: 'Intelligence' },
  { href: '/explorer', label: 'Explorer' },
  { href: '/roadmap', label: 'Roadmap' },
];

export function Navigation() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center">
            <CairnLogo size="md" variant="full" animated />
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'text-sm font-medium transition-colors hover:text-foreground relative py-1',
                  pathname === link.href
                    ? 'text-foreground nav-link-active'
                    : 'text-muted-foreground'
                )}
              >
                {link.label}
              </Link>
            ))}
            <a
              href="https://github.com/MarouaBoud/cairn-protocol#readme"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              Docs
              <span className="text-xs">↗</span>
            </a>
          </nav>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-4">
          {/* Network Badge */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 text-blue-500 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            Base Sepolia
          </div>

          {/* Connect Button */}
          <ConnectButton
            chainStatus="icon"
            showBalance={false}
          />

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 hover:bg-muted rounded-lg"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t bg-background">
          <nav className="container py-4 flex flex-col gap-2">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                  pathname === link.href
                    ? 'bg-primary/10 text-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )}
              >
                {link.label}
              </Link>
            ))}
            <a
              href="https://github.com/MarouaBoud/cairn-protocol#readme"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-3 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground flex items-center gap-2"
            >
              Docs
              <span className="text-xs">↗</span>
            </a>
          </nav>
        </div>
      )}
    </header>
  );
}
