import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
  fullScreen?: boolean;
}

export default function LoadingSpinner({ 
  size = 40, 
  className = 'text-blue-600',
  fullScreen = false 
}: LoadingSpinnerProps) {
  const spinner = (
    <Loader2 
      size={size} 
      className={`animate-spin ${className}`} 
      strokeWidth={2}
    />
  );

  if (fullScreen) {
    return (
      <div className="min-h-[400px] h-full flex flex-col items-center justify-center p-8">
        {spinner}
      </div>
    );
  }

  return <div className="flex justify-center p-4">{spinner}</div>;
}
