'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { formatAddress, bytes32ToCid, getIpfsUrl } from '@/lib/utils';
import { ExternalLink, FileText, User, Users, Copy, Check } from 'lucide-react';

interface CheckpointInfo {
  index: number;
  cid: `0x${string}`;
  agent: 'primary' | 'fallback';
}

interface CheckpointsProps {
  checkpoints: `0x${string}`[];
  primaryAgent: `0x${string}`;
  fallbackAgent: `0x${string}`;
  primaryCount: number;
  fallbackCount: number;
}

export function Checkpoints({
  checkpoints,
  primaryAgent,
  fallbackAgent,
  primaryCount,
  fallbackCount,
}: CheckpointsProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [copiedCid, setCopiedCid] = useState<string | null>(null);

  // Determine which agent committed each checkpoint
  // Primary commits first N, fallback commits the rest
  const checkpointInfos: CheckpointInfo[] = checkpoints.map((cid, index) => ({
    index,
    cid,
    agent: index < primaryCount ? 'primary' : 'fallback',
  }));

  const handleCopy = async (cid: string) => {
    await navigator.clipboard.writeText(cid);
    setCopiedCid(cid);
    setTimeout(() => setCopiedCid(null), 2000);
  };

  if (checkpoints.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Checkpoints
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">
            No checkpoints committed yet. Checkpoints appear as agents complete subtasks.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Checkpoints
          <Badge variant="secondary" className="ml-2">
            {checkpoints.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Summary */}
        <div className="flex gap-4 text-sm mb-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span>Primary: {primaryCount}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <span>Fallback: {fallbackCount}</span>
          </div>
        </div>

        {/* Checkpoint list */}
        <div className="space-y-2">
          {checkpointInfos.map((cp) => {
            const cidDisplay = bytes32ToCid(cp.cid);
            const isExpanded = expandedIndex === cp.index;

            return (
              <div
                key={cp.index}
                className={`
                  border rounded-lg p-3 transition-all cursor-pointer
                  ${isExpanded ? 'bg-muted/50' : 'hover:bg-muted/30'}
                `}
                onClick={() => setExpandedIndex(isExpanded ? null : cp.index)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`
                      w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                      ${cp.agent === 'primary'
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/50'
                      }
                    `}>
                      {cp.index + 1}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-mono">
                          {cidDisplay.slice(0, 12)}...{cidDisplay.slice(-4)}
                        </code>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCopy(cidDisplay);
                          }}
                        >
                          {copiedCid === cidDisplay ? (
                            <Check className="h-3 w-3 text-green-500" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        {cp.agent === 'primary' ? (
                          <>
                            <User className="h-3 w-3" />
                            <span>Primary Agent</span>
                          </>
                        ) : (
                          <>
                            <Users className="h-3 w-3" />
                            <span>Fallback Agent</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      window.open(getIpfsUrl(cidDisplay), '_blank');
                    }}
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    View
                  </Button>
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t text-sm">
                    <div className="space-y-2">
                      <div>
                        <span className="text-muted-foreground">Full CID: </span>
                        <code className="text-xs">{cp.cid}</code>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Agent: </span>
                        <code className="text-xs">
                          {cp.agent === 'primary' ? primaryAgent : fallbackAgent}
                        </code>
                      </div>
                      <div>
                        <span className="text-muted-foreground">IPFS URL: </span>
                        <a
                          href={getIpfsUrl(cidDisplay)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-400 hover:underline"
                        >
                          {getIpfsUrl(cidDisplay)}
                        </a>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
