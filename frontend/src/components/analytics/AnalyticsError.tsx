import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface AnalyticsErrorProps {
  onRetry: () => void;
}

export default function AnalyticsError({ onRetry }: AnalyticsErrorProps) {
  return (
    <div className="glass-2 p-8 sm:p-12 rounded-3xl text-center max-w-md mx-auto my-12 space-y-4 border-rose-500/25">
      <div className="w-12 h-12 rounded-2xl bg-rose-500/15 text-rose-600 dark:text-rose-400 flex items-center justify-center mx-auto shadow-sm">
        <AlertTriangle size={24} />
      </div>
      <div>
        <h2 className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100">
          Unable to Load Analytics
        </h2>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
          An error occurred while calculating your application and communication metrics.
        </p>
      </div>
      <button
        onClick={onRetry}
        className="btn btn-primary text-xs shadow-md shadow-indigo-500/20 mx-auto"
      >
        <RefreshCw size={14} />
        <span>Retry Loading</span>
      </button>
    </div>
  );
}
