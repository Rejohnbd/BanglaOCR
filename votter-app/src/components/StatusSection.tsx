'use client';

import { Card } from '@/components/ui/Card';
import { Progress } from '@/components/ui/Progress';
import { Badge } from '@/components/ui/Badge';
import { TaskStatus } from '@/types';

interface StatusSectionProps {
  status: TaskStatus;
}

export function StatusSection({ status }: StatusSectionProps) {
  // নিরাপদ ডিফল্ট মান ব্যবহার করুন
  const safeStatus = {
    task_id: status?.task_id || 'unknown',
    status: status?.status || 'processing',
    total_voters: status?.total_voters ?? 0,
    total_page: status?.total_page ?? 0,
    current_page: status?.current_page ?? 0,
    progress_percent: status?.progress_percent ?? 0,
    created_at: status?.created_at,
    completed_at: status?.completed_at,
    error: status?.error,
  };

  const getStatusBadge = () => {
    switch (safeStatus.status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'failed':
        return <Badge variant="error">Failed</Badge>;
      default:
        return <Badge variant="info">Processing</Badge>;
    }
  };

  const getProgressValue = () => {
    if (safeStatus.status === 'completed') return 100;
    if (safeStatus.status === 'failed') return 0;
    return Math.min(safeStatus.progress_percent, 99);
  };

  return (
    <Card variant="glass" key={`status-${safeStatus.task_id}`}>
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full animate-pulse ${safeStatus.status === 'processing'
                ? 'bg-indigo-500'
                : safeStatus.status === 'completed'
                  ? 'bg-green-500'
                  : 'bg-red-500'
              }`}
          />
          <span className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
            Task {safeStatus.task_id.slice(0, 8)}...
          </span>
        </div>
        {getStatusBadge()}
      </div>

      <div className="mb-6">
        <Progress
          value={getProgressValue()}
          showLabel
          label="Extraction Progress"
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl">
          <p className="text-[10px] uppercase font-bold text-zinc-400 mb-1">
            Voters Found
          </p>
          <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            {safeStatus.total_voters}
          </p>
        </div>
        <div className="p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl">
          <p className="text-[10px] uppercase font-bold text-zinc-400 mb-1">
            Current Page
          </p>
          <p className="text-2xl font-bold">
            {safeStatus.current_page}{' '}
            <span className="text-sm text-zinc-400">
              / {safeStatus.total_page}
            </span>
          </p>
        </div>
        <div className="p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl">
          <p className="text-[10px] uppercase font-bold text-zinc-400 mb-1">
            Est. Total
          </p>
          <p className="text-2xl font-bold">
            {(safeStatus.total_page || 0) * 18}
          </p>
        </div>
        <div className="p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-xl">
          <p className="text-[10px] uppercase font-bold text-zinc-400 mb-1">
            Success Rate
          </p>
          <p className="text-2xl font-bold">
            {safeStatus.total_page && safeStatus.total_page > 0
              ? Math.round(
                (safeStatus.total_voters /
                  ((safeStatus.total_page || 1) * 18)) *
                100
              )
              : 0}
            %
          </p>
        </div>
      </div>

      {safeStatus.error && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/30 rounded-xl">
          <p className="text-sm text-red-600 dark:text-red-400">
            ⚠️ {safeStatus.error}
          </p>
        </div>
      )}
    </Card>
  );
}
