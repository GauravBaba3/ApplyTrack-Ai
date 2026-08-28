import React from 'react';

export function SkeletonLine({ className = 'h-4 w-full' }: { className?: string }) {
  return (
    <div className={`bg-slate-200 dark:bg-slate-800/80 animate-pulse rounded-lg ${className}`} />
  );
}

export function SkeletonCard() {
  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <SkeletonLine className="w-12 h-12 rounded-xl" />
        <SkeletonLine className="w-16 h-5 rounded-full" />
      </div>
      <div className="space-y-2">
        <SkeletonLine className="h-8 w-24" />
        <SkeletonLine className="h-4 w-32" />
      </div>
    </div>
  );
}

export function SkeletonTableRow() {
  return (
    <tr className="border-b border-slate-100 dark:border-slate-800 animate-pulse">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <SkeletonLine className="w-9 h-9 rounded-xl shrink-0" />
          <div className="space-y-1.5 flex-1 max-w-[200px]">
            <SkeletonLine className="h-4 w-28" />
            <SkeletonLine className="h-3 w-20" />
          </div>
        </div>
      </td>
      <td className="px-6 py-4">
        <SkeletonLine className="h-4 w-24" />
      </td>
      <td className="px-6 py-4">
        <SkeletonLine className="h-6 w-20 rounded-full" />
      </td>
      <td className="px-6 py-4">
        <SkeletonLine className="h-4 w-20" />
      </td>
      <td className="px-6 py-4 text-right">
        <SkeletonLine className="h-8 w-8 rounded-lg ml-auto" />
      </td>
    </tr>
  );
}
