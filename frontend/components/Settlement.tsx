'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatEth, calculateSettlementSplit } from '@/lib/utils';
import { TaskState } from '@/lib/abi';
import { Coins, User, Users, Building2 } from 'lucide-react';

interface SettlementProps {
  escrow: bigint;
  primaryCheckpoints: number;
  fallbackCheckpoints: number;
  state: TaskState;
  primaryShare?: bigint;
  fallbackShare?: bigint;
  protocolFee?: bigint;
  txHash?: string;
}

export function Settlement({
  escrow,
  primaryCheckpoints,
  fallbackCheckpoints,
  state,
  primaryShare,
  fallbackShare,
  protocolFee,
  txHash,
}: SettlementProps) {
  const totalCheckpoints = primaryCheckpoints + fallbackCheckpoints;
  const split = calculateSettlementSplit(primaryCheckpoints, fallbackCheckpoints);

  const isSettled = state === TaskState.RESOLVED && (primaryShare !== undefined || fallbackShare !== undefined);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Coins className="h-5 w-5" />
          Settlement
          {isSettled && (
            <span className="text-xs text-green-400 ml-2">Settled</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Escrow amount */}
        <div className="text-center py-4 bg-muted/30 rounded-lg">
          <p className="text-sm text-muted-foreground mb-1">Total Escrow</p>
          <p className="text-3xl font-bold">{formatEth(escrow)} ETH</p>
        </div>

        {/* Distribution visualization */}
        {totalCheckpoints > 0 ? (
          <div className="space-y-4">
            {/* Progress bar */}
            <div className="h-4 rounded-full bg-muted overflow-hidden flex">
              {split.primaryPercent > 0 && (
                <div
                  className="bg-blue-500 h-full transition-all duration-500"
                  style={{ width: `${split.primaryPercent}%` }}
                />
              )}
              {split.fallbackPercent > 0 && (
                <div
                  className="bg-amber-500 h-full transition-all duration-500"
                  style={{ width: `${split.fallbackPercent}%` }}
                />
              )}
              {split.protocolPercent > 0 && (
                <div
                  className="bg-purple-500 h-full transition-all duration-500"
                  style={{ width: `${split.protocolPercent}%` }}
                />
              )}
            </div>

            {/* Legend */}
            <div className="grid grid-cols-3 gap-4">
              {/* Primary Agent */}
              <div className="text-center p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
                <div className="flex items-center justify-center gap-1 text-blue-400 mb-1">
                  <User className="h-4 w-4" />
                  <span className="text-xs font-medium">Primary</span>
                </div>
                <p className="text-lg font-bold">
                  {isSettled && primaryShare !== undefined
                    ? formatEth(primaryShare)
                    : formatEth(BigInt(Math.floor(Number(escrow) * split.primaryPercent / 100)))
                  } ETH
                </p>
                <p className="text-xs text-muted-foreground">
                  {split.primaryPercent.toFixed(1)}%
                </p>
              </div>

              {/* Fallback Agent */}
              <div className="text-center p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <div className="flex items-center justify-center gap-1 text-amber-400 mb-1">
                  <Users className="h-4 w-4" />
                  <span className="text-xs font-medium">Fallback</span>
                </div>
                <p className="text-lg font-bold">
                  {isSettled && fallbackShare !== undefined
                    ? formatEth(fallbackShare)
                    : formatEth(BigInt(Math.floor(Number(escrow) * split.fallbackPercent / 100)))
                  } ETH
                </p>
                <p className="text-xs text-muted-foreground">
                  {split.fallbackPercent.toFixed(1)}%
                </p>
              </div>

              {/* Protocol Fee */}
              <div className="text-center p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
                <div className="flex items-center justify-center gap-1 text-purple-400 mb-1">
                  <Building2 className="h-4 w-4" />
                  <span className="text-xs font-medium">Protocol</span>
                </div>
                <p className="text-lg font-bold">
                  {isSettled && protocolFee !== undefined
                    ? formatEth(protocolFee)
                    : formatEth(BigInt(Math.floor(Number(escrow) * split.protocolPercent / 100)))
                  } ETH
                </p>
                <p className="text-xs text-muted-foreground">
                  {split.protocolPercent.toFixed(2)}%
                </p>
              </div>
            </div>

            {/* Settlement formula */}
            <div className="text-xs text-muted-foreground text-center pt-2 border-t">
              <p>
                Split based on {primaryCheckpoints} primary + {fallbackCheckpoints} fallback checkpoints
              </p>
              <p className="mt-1">
                Formula: (agent_checkpoints / total_checkpoints) × escrow × (1 - 0.5% fee)
              </p>
            </div>

            {/* Transaction hash link */}
            {txHash && (
              <div className="text-center pt-2">
                <a
                  href={`https://sepolia.basescan.org/tx/${txHash}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-400 hover:underline"
                >
                  View settlement transaction →
                </a>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center text-muted-foreground py-4">
            <p>No checkpoints yet. Settlement will be calculated based on verified work.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
