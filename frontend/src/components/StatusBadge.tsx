import React from 'react';

export type ApplicationStatus = 
  | 'Applied' 
  | 'Assessment' 
  | 'Interview' 
  | 'Offer' 
  | 'Rejected' 
  | 'Pending' 
  | 'No Response' 
  | 'Ghosted'
  | 'Unknown';

interface StatusBadgeProps {
  status: string;
  className?: string;
  dot?: boolean;
}

export default function StatusBadge({ status, className = '', dot = true }: StatusBadgeProps) {
  const getBadgeClass = (statusString: string) => {
    switch (statusString) {
      case 'Applied': return 'badge-applied';
      case 'Assessment': return 'badge-assessment';
      case 'Interview': return 'badge-interview';
      case 'Offer': return 'badge-offer';
      case 'Rejected': return 'badge-rejected';
      case 'Pending': return 'badge-pending';
      case 'No Response':
      case 'Ghosted': return 'badge-no-response';
      default: return 'badge-no-response';
    }
  };

  const getDotColor = (statusString: string) => {
    switch (statusString) {
      case 'Applied': return 'bg-blue-500';
      case 'Assessment': return 'bg-purple-500';
      case 'Interview': return 'bg-emerald-500';
      case 'Offer': return 'bg-cyan-500';
      case 'Rejected': return 'bg-rose-500';
      case 'Pending': return 'bg-amber-500';
      case 'No Response':
      case 'Ghosted': return 'bg-slate-400';
      default: return 'bg-slate-400';
    }
  };

  return (
    <span className={`badge ${getBadgeClass(status)} gap-1.5 ${className}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${getDotColor(status)}`} />}
      <span>{status}</span>
    </span>
  );
}
