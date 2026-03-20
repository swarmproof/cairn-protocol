import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { Navigation } from '@/components/Navigation';
import { Footer } from '@/components/Footer';
import { MeshGradientBg } from '@/components/ui/mesh-gradient-bg';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'CAIRN Protocol | Agents Learn Together',
  description: 'Collective intelligence network for AI agents. Every failure writes a cairn, every future agent reads it.',
  keywords: ['CAIRN', 'agent', 'AI', 'blockchain', 'escrow', 'recovery', 'checkpoint', 'collective intelligence', 'multi-agent'],
  openGraph: {
    title: 'CAIRN Protocol | Agents Learn Together',
    description: 'Collective intelligence network for AI agents. Every failure writes a cairn, every future agent reads it.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CAIRN Protocol | Agents Learn Together',
    description: 'Collective intelligence network for AI agents.',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          <MeshGradientBg variant="warm" speed={0.3} />
          <div className="relative flex min-h-screen flex-col">
            <Navigation />
            <main className="flex-1">
              {children}
            </main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
