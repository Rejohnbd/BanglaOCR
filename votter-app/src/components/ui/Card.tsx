'use client';

import { forwardRef, HTMLAttributes } from 'react';
import { cn } from '@/lib/cn';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'bordered';
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', children, ...props }, ref) => {
    const variants = {
      default:
        'bg-white dark:bg-zinc-900/50 shadow-lg shadow-zinc-200/50 dark:shadow-none',
      glass: 'bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm',
      bordered: 'border border-zinc-200 dark:border-zinc-800',
    };

    return (
      <div
        ref={ref}
        className={cn('rounded-2xl p-6', variants[variant], className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
