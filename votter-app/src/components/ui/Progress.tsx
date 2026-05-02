'use client';

import { cn } from '@/lib/cn';

interface ProgressProps {
  value: number;
  max?: number;
  className?: string;
  showLabel?: boolean;
  label?: string;
}

export function Progress({
  value,
  max = 100,
  className,
  showLabel,
  label,
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between mb-2 text-sm">
          <span className="text-zinc-600 dark:text-zinc-400">
            {label || 'Progress'}
          </span>
          <span className="font-medium text-indigo-600 dark:text-indigo-400">
            {Math.round(percentage)}%
          </span>
        </div>
      )}
      <div className="h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-indigo-600 to-purple-600 transition-all duration-500 ease-out rounded-full"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
