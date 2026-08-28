import React from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ArrowLeft } from 'lucide-react';

function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 p-6 transition-colors duration-200">
      <div className="text-center max-w-md mx-auto p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xl space-y-6">
        <div className="w-16 h-16 bg-rose-50 dark:bg-rose-950/60 border border-rose-100 dark:border-rose-900/60 rounded-2xl flex items-center justify-center mx-auto text-rose-600 dark:text-rose-400">
          <AlertCircle size={32} />
        </div>
        
        <div>
          <h1 className="text-4xl font-black text-slate-900 dark:text-slate-100">404</h1>
          <h2 className="text-lg font-bold text-slate-700 dark:text-slate-300 mt-1">Page Not Found</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
            The page you are looking for does not exist or has been moved.
          </p>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link to="/" className="btn btn-primary">
            <ArrowLeft size={16} />
            <span>Go Home</span>
          </Link>
          <Link to="/dashboard" className="btn btn-secondary">
            <span>Dashboard</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default NotFoundPage;
