'use client';

import { use } from 'react';
import Link from 'next/link';
import { Header } from '@/components/Header';
import { TaskDetail } from '@/components/TaskDetail';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

interface TaskPageProps {
  params: Promise<{ id: string }>;
}

export default function TaskPage({ params }: TaskPageProps) {
  const { id } = use(params);
  const taskId = id as `0x${string}`;

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container py-8">
        {/* Back button */}
        <div className="mb-6">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>

        {/* Task detail */}
        <TaskDetail taskId={taskId} />
      </div>
    </div>
  );
}
