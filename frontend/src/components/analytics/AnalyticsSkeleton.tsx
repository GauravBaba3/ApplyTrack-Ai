import React from 'react';
import { SkeletonCard, SkeletonLine } from '../LoadingSkeleton';

export default function AnalyticsSkeleton() {
  return (
    <div className="space-y-6 pb-12 animate-fade-in w-full max-w-full">
      {/* Header Skeleton */}
      <div className="space-y-2">
        <SkeletonLine className="h-7 w-56" />
        <SkeletonLine className="h-4 w-96 max-w-full" />
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>

      {/* 2 Main Chart Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <div className="glass-2 p-6 rounded-3xl space-y-4">
          <SkeletonLine className="h-5 w-48" />
          <div className="h-52 rounded-2xl bg-white/40 dark:bg-white/[0.02] animate-pulse" />
        </div>
        <div className="glass-2 p-6 rounded-3xl space-y-4">
          <SkeletonLine className="h-5 w-48" />
          <div className="h-52 rounded-2xl bg-white/40 dark:bg-white/[0.02] animate-pulse" />
        </div>
      </div>

      {/* Bottom Chart Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        <div className="glass-2 p-6 rounded-3xl space-y-4">
          <SkeletonLine className="h-5 w-48" />
          <div className="h-44 rounded-2xl bg-white/40 dark:bg-white/[0.02] animate-pulse" />
        </div>
        <div className="glass-2 p-6 rounded-3xl space-y-4">
          <SkeletonLine className="h-5 w-48" />
          <div className="h-44 rounded-2xl bg-white/40 dark:bg-white/[0.02] animate-pulse" />
        </div>
      </div>
    </div>
  );
}
