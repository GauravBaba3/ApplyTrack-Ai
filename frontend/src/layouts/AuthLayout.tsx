import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';

function AuthLayout({ children }: { children?: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 flex flex-col transition-colors duration-200">
      {/* Top Navbar */}
      <header className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-base shadow-md shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            A
          </div>
          <span className="font-extrabold text-xl tracking-tight text-slate-900 dark:text-slate-100">
            ApplyTrack <span className="text-indigo-600 dark:text-indigo-400">AI</span>
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link to="/login" className="btn btn-secondary text-xs sm:text-sm px-4 py-2">
            Sign In
          </Link>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {children || <Outlet />}
      </main>
    </div>
  );
}

export default AuthLayout;
