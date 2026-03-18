'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StateBadge } from '@/components/StateBadge';
import { StateMachineCompact } from '@/components/StateMachine';
import { formatAddress, formatTaskId, formatEth, formatRelativeTime } from '@/lib/utils';
import { TaskState } from '@/lib/abi';
import { Task } from '@/hooks/useCairn';
import { Clock, Coins, User, Users, ChevronRight } from 'lucide-react';

interface TaskListProps {
  tasks: Task[];
  isLoading?: boolean;
}

export function TaskList({ tasks, isLoading }: TaskListProps) {
  const [filter, setFilter] = useState<TaskState | 'all'>('all');

  const filteredTasks = filter === 'all'
    ? tasks
    : tasks.filter(t => t.state === filter);

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-4 bg-muted rounded w-1/3 mb-4" />
              <div className="h-3 bg-muted rounded w-2/3" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <div className="text-muted-foreground">
            <p className="text-lg font-medium">No tasks found</p>
            <p className="text-sm mt-2">
              Submit a new task using the Demo Controls panel to get started.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        <Badge
          variant={filter === 'all' ? 'default' : 'outline'}
          className="cursor-pointer"
          onClick={() => setFilter('all')}
        >
          All ({tasks.length})
        </Badge>
        <Badge
          variant={filter === TaskState.RUNNING ? 'running' : 'outline'}
          className="cursor-pointer"
          onClick={() => setFilter(TaskState.RUNNING)}
        >
          Running ({tasks.filter(t => t.state === TaskState.RUNNING).length})
        </Badge>
        <Badge
          variant={filter === TaskState.FAILED ? 'failed' : 'outline'}
          className="cursor-pointer"
          onClick={() => setFilter(TaskState.FAILED)}
        >
          Failed ({tasks.filter(t => t.state === TaskState.FAILED).length})
        </Badge>
        <Badge
          variant={filter === TaskState.RECOVERING ? 'recovering' : 'outline'}
          className="cursor-pointer"
          onClick={() => setFilter(TaskState.RECOVERING)}
        >
          Recovering ({tasks.filter(t => t.state === TaskState.RECOVERING).length})
        </Badge>
        <Badge
          variant={filter === TaskState.RESOLVED ? 'resolved' : 'outline'}
          className="cursor-pointer"
          onClick={() => setFilter(TaskState.RESOLVED)}
        >
          Resolved ({tasks.filter(t => t.state === TaskState.RESOLVED).length})
        </Badge>
      </div>

      {/* Task cards */}
      <div className="space-y-3">
        {filteredTasks.map((task) => (
          <TaskCard key={task.taskId} task={task} />
        ))}
      </div>
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  const totalCheckpoints = Number(task.primaryCheckpoints) + Number(task.fallbackCheckpoints);

  return (
    <Link href={`/task/${task.taskId}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer group">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              {/* Header row */}
              <div className="flex items-center gap-3 mb-3">
                <code className="text-sm font-mono text-muted-foreground">
                  {formatTaskId(task.taskId)}
                </code>
                <StateBadge state={task.state} pulse={task.state === TaskState.RUNNING} />
                <StateMachineCompact currentState={task.state} />
              </div>

              {/* Details row */}
              <div className="flex items-center gap-6 text-sm text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <Coins className="h-3.5 w-3.5" />
                  <span>{formatEth(task.escrow)} ETH</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5" />
                  <span>Primary: {formatAddress(task.primaryAgent)}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Users className="h-3.5 w-3.5" />
                  <span>Fallback: {formatAddress(task.fallbackAgent)}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  <span>{formatRelativeTime(Number(task.lastHeartbeat))}</span>
                </div>
              </div>

              {/* Checkpoints row */}
              {totalCheckpoints > 0 && (
                <div className="mt-2 flex items-center gap-4 text-xs">
                  <span className="text-muted-foreground">
                    {totalCheckpoints} checkpoint{totalCheckpoints !== 1 ? 's' : ''}
                  </span>
                  {Number(task.primaryCheckpoints) > 0 && (
                    <span className="text-blue-400">
                      Primary: {Number(task.primaryCheckpoints)}
                    </span>
                  )}
                  {Number(task.fallbackCheckpoints) > 0 && (
                    <span className="text-amber-400">
                      Fallback: {Number(task.fallbackCheckpoints)}
                    </span>
                  )}
                </div>
              )}
            </div>

            <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
