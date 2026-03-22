import { NextResponse } from 'next/server';
import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * GET /cairn.md
 *
 * Serves the CAIRN Protocol integration guide for AI agents.
 * Agents can curl this endpoint to learn how to integrate with CAIRN.
 *
 * Usage: curl -s https://your-domain.com/cairn.md
 */
export async function GET() {
  try {
    // Read the markdown file from public directory
    const filePath = join(process.cwd(), 'public', 'cairn.md');
    const content = readFileSync(filePath, 'utf-8');

    return new NextResponse(content, {
      status: 200,
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
        'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
        'X-Robots-Tag': 'noindex', // Don't index in search engines
      },
    });
  } catch (error) {
    console.error('Error reading cairn.md:', error);

    return new NextResponse(
      '# Error\n\nFailed to load CAIRN integration guide. Please try again later.',
      {
        status: 500,
        headers: {
          'Content-Type': 'text/markdown; charset=utf-8',
        },
      }
    );
  }
}
