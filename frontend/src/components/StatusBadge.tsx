import React from 'react';
import { ApplicationStatus } from '../types';

interface StatusBadgeProps {
  status: ApplicationStatus | string;
  className?: string;
  dot?: boolean;
}

export default function StatusBadge({ status, className = '', dot = true }: StatusBadgeProps) {
  const getBadgeClass = (statusString: string) => {
    switch (statusString) {
      case 'Applied': return 'badge-applied';
      case 'Under Review': return 'badge-pending';
      case 'Assessment': return 'badge-assessment';
      case 'Interview': return 'badge-interview';
      case 'Offer': return 'badge-offer';
      case 'Rejected': return 'badge-rejected';
      case 'Withdrawn': return 'badge-no-response';
      case 'Needs Review': return 'badge-needs-review';
      case 'Stale':
      case 'Ghosted':
      case 'No Response': return 'badge-no-response';
      default: return 'badge-no-response';
    }
  };

  const getDotColor = (statusString: string) => {
    switch (statusString) {
      case 'Applied': return 'bg-blue-500';
      case 'Under Review': return 'bg-amber-500';
      case 'Assessment': return 'bg-purple-500';
      case 'Interview': return 'bg-emerald-500';
      case 'Offer': return 'bg-cyan-500';
      case 'Rejected': return 'bg-rose-500';
      case 'Withdrawn': return 'bg-slate-400';
      case 'Needs Review': return 'bg-amber-500 animate-ping';
      case 'Stale': return 'bg-amber-500';
      case 'Ghosted':
      case 'No Response': return 'bg-slate-400';
      default: return 'bg-slate-400';
    }
  };

  return (
    <span className={`badge ${getBadgeClass(status)} gap-1.5 shadow-sm ${className}`}>
      {dot && (
        <span className="relative flex h-2 w-2 items-center justify-center">
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${getDotColor(status)}`} />
        </span>
      )}
      <span className="font-semibold">{status}</span>
    </span>
  );
}

