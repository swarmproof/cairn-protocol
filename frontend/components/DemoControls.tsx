'use client';

import { useState } from 'react';
import { useAccount } from 'wagmi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  useSubmitTask,
  useHeartbeat,
  useDetectFailure,
  useCompleteTask,
  useCommitCheckpoint,
  useIsStale,
} from '@/hooks/useCairn';
import { TaskState } from '@/lib/abi';
import { isDemoMode } from '@/lib/utils';
import {
  Play,
  Heart,
  XCircle,
  CheckCircle,
  FileText,
  AlertTriangle,
  Zap,
} from 'lucide-react';
import { keccak256, toBytes } from 'viem';

interface DemoControlsProps {
  taskId?: `0x${string}`;
  taskState?: TaskState;
  onTaskCreated?: (taskId: `0x${string}`) => void;
  onActionComplete?: () => void;
}

export function DemoControls({
  taskId,
  taskState,
  onTaskCreated,
  onActionComplete,
}: DemoControlsProps) {
  const { address, isConnected } = useAccount();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { submitTask, isPending: isSubmitPending } = useSubmitTask();
  const { heartbeat, isPending: isHeartbeatPending } = useHeartbeat();
  const { detectFailure, isPending: isDetectFailurePending } = useDetectFailure();
  const { completeTask, isPending: isCompletePending } = useCompleteTask();
  const { commitCheckpoint, isPending: isCheckpointPending } = useCommitCheckpoint();
  const { isStale } = useIsStale(taskId);

  // Check if demo mode is enabled
  if (!isDemoMode()) {
    return null;
  }

  const handleSubmitTask = async () => {
    if (!address) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // Generate a random spec hash
      const specHash = keccak256(toBytes(`demo-task-${Date.now()}`));

      // Use connected wallet as both primary and fallback for demo
      const result = await submitTask(
        address, // primary agent
        address, // fallback agent (same for demo)
        specHash,
        BigInt(60), // 60 second heartbeat interval
        BigInt(Math.floor(Date.now() / 1000) + 3600), // 1 hour deadline
        '0.002' // 0.002 ETH escrow
      );

      if (result && onTaskCreated) {
        // The task ID is emitted in the event, we'll need to parse it
        // For now, just trigger refresh
        onActionComplete?.();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit task');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleHeartbeat = async () => {
    if (!taskId) return;
    setError(null);

    try {
      await heartbeat(taskId);
      onActionComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send heartbeat');
    }
  };

  const handleDetectFailure = async () => {
    if (!taskId) return;
    setError(null);

    try {
      await detectFailure(taskId);
      onActionComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to detect failure');
    }
  };

  const handleCommitCheckpoint = async () => {
    if (!taskId) return;
    setError(null);

    try {
      // Generate a demo checkpoint batch
      // For demo purposes: single checkpoint (count=1), same hash for merkle root and CID
      const cid = keccak256(toBytes(`checkpoint-${Date.now()}`));
      await commitCheckpoint(taskId, BigInt(1), cid, cid);
      onActionComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to commit checkpoint');
    }
  };

  const handleCompleteTask = async () => {
    if (!taskId) return;
    setError(null);

    try {
      await completeTask(taskId);
      onActionComplete?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete task');
    }
  };

  return (
    <Card className="border-dashed border-amber-500/50">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Zap className="h-5 w-5 text-amber-500" />
          Demo Controls
          <Badge variant="outline" className="ml-2 text-amber-500 border-amber-500/50">
            Demo Mode
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isConnected ? (
          <p className="text-sm text-muted-foreground">
            Connect your wallet to use demo controls.
          </p>
        ) : (
          <>
            {/* Task creation */}
            {!taskId && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Create a new task with 0.002 ETH escrow
                </p>
                <Button
                  onClick={handleSubmitTask}
                  disabled={isSubmitPending || isSubmitting}
                  className="w-full"
                >
                  <Play className="h-4 w-4 mr-2" />
                  {isSubmitPending ? 'Submitting...' : 'Submit New Task'}
                </Button>
              </div>
            )}

            {/* Task-specific controls */}
            {taskId && (
              <div className="grid grid-cols-2 gap-2">
                {/* Running state controls */}
                {taskState === TaskState.RUNNING && (
                  <>
                    <Button
                      variant="outline"
                      onClick={handleHeartbeat}
                      disabled={isHeartbeatPending}
                    >
                      <Heart className="h-4 w-4 mr-2" />
                      Heartbeat
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleCommitCheckpoint}
                      disabled={isCheckpointPending}
                    >
                      <FileText className="h-4 w-4 mr-2" />
                      Checkpoint
                    </Button>
                    <Button
                      variant="success"
                      onClick={handleCompleteTask}
                      disabled={isCompletePending}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Complete
                    </Button>
                    <Button
                      variant="danger"
                      onClick={handleDetectFailure}
                      disabled={isDetectFailurePending || !isStale}
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      {isStale ? 'Trigger Failure' : 'Not Stale'}
                    </Button>
                  </>
                )}

                {/* Recovering state controls */}
                {taskState === TaskState.RECOVERING && (
                  <>
                    <Button
                      variant="outline"
                      onClick={handleHeartbeat}
                      disabled={isHeartbeatPending}
                    >
                      <Heart className="h-4 w-4 mr-2" />
                      Heartbeat
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleCommitCheckpoint}
                      disabled={isCheckpointPending}
                    >
                      <FileText className="h-4 w-4 mr-2" />
                      Checkpoint
                    </Button>
                    <Button
                      variant="success"
                      onClick={handleCompleteTask}
                      disabled={isCompletePending}
                      className="col-span-2"
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Complete Recovery
                    </Button>
                  </>
                )}

                {/* Failed state controls */}
                {taskState === TaskState.FAILED && (
                  <Button
                    variant="warning"
                    onClick={handleHeartbeat}
                    disabled={isHeartbeatPending}
                    className="col-span-2"
                  >
                    <Heart className="h-4 w-4 mr-2" />
                    Start Recovery (Heartbeat)
                  </Button>
                )}

                {/* Resolved state - already settled */}
                {taskState === TaskState.RESOLVED && (
                  <div className="col-span-2 flex items-center justify-center gap-2 p-3 bg-stone-500/10 rounded-lg border border-stone-500/30">
                    <CheckCircle className="h-4 w-4 text-stone-400" />
                    <span className="text-sm text-stone-400">
                      Task completed & settled
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Stale indicator */}
            {taskId && taskState === TaskState.RUNNING && isStale && (
              <div className="flex items-center gap-2 p-2 bg-red-500/10 rounded-lg border border-red-500/30">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <span className="text-sm text-red-400">
                  Task is stale! Anyone can trigger failure.
                </span>
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="p-2 bg-red-500/10 rounded-lg border border-red-500/30">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
