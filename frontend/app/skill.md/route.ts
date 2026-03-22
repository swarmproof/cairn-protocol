import { NextResponse } from 'next/server';
import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * GET /skill.md
 *
 * Quick integration guide for AI agents.
 * Similar to synthesis.md/skill.md pattern.
 *
 * Usage: curl -s https://your-domain.com/skill.md
 */
export async function GET() {
  try {
    const filePath = join(process.cwd(), 'public', 'skill.md');
    const content = readFileSync(filePath, 'utf-8');

    return new NextResponse(content, {
      status: 200,
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
        'Cache-Control': 'public, max-age=3600',
        'X-Robots-Tag': 'noindex',
      },
    });
  } catch (error) {
    console.error('Error reading skill.md:', error);

    return new NextResponse(
      '# Error\n\nFailed to load CAIRN skill guide.',
      {
        status: 500,
        headers: {
          'Content-Type': 'text/markdown; charset=utf-8',
        },
      }
    );
  }
}
