'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StateBadge } from '@/components/StateBadge';
import { StateMachine } from '@/components/StateMachine';
import { Checkpoints } from '@/components/Checkpoints';
import { Settlement } from '@/components/Settlement';
import { DemoControls } from '@/components/DemoControls';
import { useTask, useCheckpoints, useTaskEvents, Task } from '@/hooks/useCairn';
import { formatAddress, formatEth, formatDeadline, formatRelativeTime } from '@/lib/utils';
import { Clock, Coins, User, Users, Calendar, Activity, Hash } from 'lucide-react';

interface TaskDetailProps {
  taskId: `0x${string}`;
}

export function TaskDetail({ taskId }: TaskDetailProps) {
  const { task, isLoading, refetch } = useTask(taskId);
  const { checkpoints, refetch: refetchCheckpoints } = useCheckpoints(taskId);

  // Watch for real-time events
  useTaskEvents(taskId);

  const handleActionComplete = () => {
    refetch();
    refetchCheckpoints();
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-32 bg-muted rounded-lg" />
        <div className="h-64 bg-muted rounded-lg" />
      </div>
    );
  }

  if (!task) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <p className="text-muted-foreground">Task not found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header card with state machine */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl flex items-center gap-3">
                <Hash className="h-5 w-5 text-muted-foreground" />
                <code className="font-mono">{taskId.slice(0, 18)}...{taskId.slice(-8)}</code>
                <StateBadge state={task.state} size="lg" pulse />
              </CardTitle>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="py-6">
            <StateMachine currentState={task.state} size="lg" />
          </div>
        </CardContent>
      </Card>

      {/* Task details */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Info card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Task Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Coins className="h-4 w-4" />
                <span>Escrow</span>
              </div>
              <span className="font-mono font-bold">{formatEth(task.escrow)} ETH</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-muted-foreground">
                <User className="h-4 w-4" />
                <span>Primary Agent</span>
              </div>
              <code className="text-sm">{formatAddress(task.primaryAgent)}</code>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Users className="h-4 w-4" />
                <span>Fallback Agent</span>
              </div>
              <code className="text-sm">{formatAddress(task.fallbackAgent)}</code>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-muted-foreground">
                <User className="h-4 w-4" />
                <span>Operator</span>
              </div>
              <code className="text-sm">{formatAddress(task.operator)}</code>
            </div>

            <div className="border-t pt-4 mt-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Activity className="h-4 w-4" />
                  <span>Last Heartbeat</span>
                </div>
                <span>{formatRelativeTime(Number(task.lastHeartbeat))}</span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>Deadline</span>
                </div>
                <span>{formatDeadline(Number(task.deadline))}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Demo controls */}
        <DemoControls
          taskId={taskId}
          taskState={task.state}
          onActionComplete={handleActionComplete}
        />
      </div>

      {/* Checkpoints */}
      <Checkpoints
        checkpoints={checkpoints || []}
        primaryAgent={task.primaryAgent}
        fallbackAgent={task.fallbackAgent}
        primaryCount={Number(task.primaryCheckpoints)}
        fallbackCount={Number(task.fallbackCheckpoints)}
      />

      {/* Settlement */}
      <Settlement
        escrow={task.escrow}
        primaryCheckpoints={Number(task.primaryCheckpoints)}
        fallbackCheckpoints={Number(task.fallbackCheckpoints)}
        state={task.state}
      />
    </div>
  );
}
