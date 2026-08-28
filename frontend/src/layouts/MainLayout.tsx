import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, BarChart3, Briefcase, Mail, Home, Settings, LogOut, Sparkles } from 'lucide-react';
import { authApi } from '../services/api';
import { cacheService } from '../services/cacheService';
import GlobalSyncIndicator from '../components/GlobalSyncIndicator';
import ThemeToggle from '../components/ThemeToggle';

function MainLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      cacheService.clearAll();
      await authApi.logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
      cacheService.clearAll();
      navigate('/login');
    }
  };

  const navItems = [
    { path: '/dashboard', icon: Home, label: 'Dashboard' },
    { path: '/applications', icon: Briefcase, label: 'Applications' },
    { path: '/emails', icon: Mail, label: 'Email Activity' },
    { path: '/analytics', icon: BarChart3, label: 'Analytics' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="min-h-screen flex bg-slate-50 dark:bg-[#0b0f19] text-slate-900 dark:text-slate-100 transition-colors duration-200">
      {/* Mobile top navigation */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800/80 z-30 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 -ml-2 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Toggle menu"
          >
            {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-xs shadow-sm">
              A
            </div>
            <span className="font-bold text-slate-900 dark:text-slate-100 tracking-tight text-sm">ApplyTrack <span className="text-indigo-600 dark:text-indigo-400">AI</span></span>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <GlobalSyncIndicator />
          <ThemeToggle />
        </div>
      </div>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-white dark:bg-[#0d131f] border-r border-slate-200/80 dark:border-slate-800/80 
          transform transition-transform duration-300 ease-in-out lg:translate-x-0 flex flex-col
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="h-16 flex items-center px-6 border-b border-slate-100 dark:border-slate-800/80 shrink-0">
          <Link to="/dashboard" className="flex items-center gap-3 group">
            <div className="w-8 h-8 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-black text-sm shadow-md shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              A
            </div>
            <div>
              <h1 className="font-extrabold text-slate-900 dark:text-slate-100 leading-none tracking-tight text-base">
                ApplyTrack <span className="text-indigo-600 dark:text-indigo-400">AI</span>
              </h1>
              <p className="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500 font-semibold mt-1">
                Tracker
              </p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 px-4 py-6 overflow-y-auto space-y-1.5">
          <div className="px-3 pb-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Navigation</p>
          </div>
          <ul className="space-y-1">
            {navItems.map(({ path, icon: Icon, label }) => {
              const isActive = location.pathname.startsWith(path);
              return (
                <li key={path}>
                  <Link
                    to={path}
                    onClick={() => setSidebarOpen(false)}
                    className={`sidebar-link ${isActive ? 'active' : ''}`}
                  >
                    <Icon size={18} strokeWidth={isActive ? 2.5 : 2} className={isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400 dark:text-slate-500'} />
                    <span>{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-slate-100 dark:border-slate-800/80 shrink-0 space-y-2">
          <div className="flex items-center justify-between px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800/50">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Theme</span>
            <ThemeToggle />
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3.5 py-2.5 w-full rounded-xl text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
          >
            <LogOut size={18} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <main className="flex-1 lg:ml-64 flex flex-col min-h-screen pt-16 lg:pt-0">
        {/* Desktop Header Topbar */}
        <header className="hidden lg:flex items-center justify-between px-8 py-3.5 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/80 dark:bg-[#0d131f]/80 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 font-semibold text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live Monitoring
            </span>
          </div>
          <div className="flex items-center gap-3">
            <GlobalSyncIndicator />
            <div className="h-4 w-px bg-slate-200 dark:bg-slate-800" />
            <ThemeToggle />
          </div>
        </header>

        <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
          {children}
        </div>
      </main>
    </div>
  );
}

export default MainLayout;
