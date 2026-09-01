import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  Menu, X, BarChart3, Briefcase, Mail, Home, Settings, LogOut, 
  Sparkles, ChevronRight, User as UserIcon, ShieldCheck, Compass 
} from 'lucide-react';
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
    } catch {
      cacheService.clearAll();
      navigate('/login');
    }
  };

  const navSections = [
    {
      title: 'Overview',
      items: [
        { path: '/dashboard', icon: Home, label: 'Dashboard' },
      ]
    },
    {
      title: 'Work & Pipeline',
      items: [
        { path: '/applications', icon: Briefcase, label: 'Applications' },
        { path: '/emails', icon: Mail, label: 'Email Activity' },
      ]
    },
    {
      title: 'Insights',
      items: [
        { path: '/analytics', icon: BarChart3, label: 'Analytics' },
      ]
    },
    {
      title: 'Account',
      items: [
        { path: '/profile', icon: UserIcon, label: 'Profile' },
        { path: '/settings', icon: Settings, label: 'Settings' },
      ]
    }
  ];

  // Dynamic breadcrumb computation
  const allNavItems = navSections.flatMap(s => s.items);
  const currentNav = allNavItems.find(item => location.pathname === item.path || (item.path !== '/dashboard' && location.pathname.startsWith(item.path)));
  const pageTitle = currentNav ? currentNav.label : 'ApplyTrack AI';

  return (
    <div className="min-h-screen flex bg-[#f8fafc] dark:bg-[#050811] text-slate-900 dark:text-slate-100 transition-colors duration-200 relative w-full max-w-full overflow-x-hidden">
      {/* Ambient background glow for glass depth */}
      <div className="fixed top-0 left-1/4 w-[36rem] h-[36rem] max-w-full bg-indigo-500/10 dark:bg-indigo-600/[0.07] rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="fixed bottom-10 right-10 w-[32rem] h-[32rem] max-w-full bg-cyan-500/10 dark:bg-cyan-600/[0.04] rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Mobile top navigation */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-14 sm:h-16 bg-white/90 dark:bg-[#070c18]/90 backdrop-blur-2xl border-b border-slate-200/80 dark:border-white/[0.08] z-30 flex items-center justify-between px-3 sm:px-4 w-full">
        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 sm:p-2 -ml-1 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/[0.08] active:scale-95 transition-transform shrink-0"
            aria-label="Toggle menu"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <Link to="/dashboard" className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-black text-xs shadow-md shadow-indigo-500/25 shrink-0">
              A
            </div>
            <span className="font-extrabold text-slate-900 dark:text-slate-100 tracking-tight text-xs sm:text-sm truncate">
              ApplyTrack <span className="text-indigo-600 dark:text-indigo-400">AI</span>
            </span>
          </Link>
        </div>
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <GlobalSyncIndicator />
          <ThemeToggle />
        </div>
      </div>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 max-w-[80vw] bg-white/95 dark:bg-[#070c18]/95 backdrop-blur-2xl border-r border-slate-200/80 dark:border-white/[0.07]
          transform transition-transform duration-300 ease-in-out lg:translate-x-0 flex flex-col shadow-2xl lg:shadow-none
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-slate-100 dark:border-white/[0.06] shrink-0">
          <Link to="/dashboard" onClick={() => setSidebarOpen(false)} className="flex items-center gap-3 group">
            <div className="w-8 h-8 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-black text-sm shadow-md shadow-indigo-500/25 group-hover:scale-105 transition-transform shrink-0">
              A
            </div>
            <div>
              <h1 className="font-extrabold text-slate-900 dark:text-slate-100 leading-none tracking-tight text-base">
                ApplyTrack <span className="text-indigo-600 dark:text-indigo-400">AI</span>
              </h1>
              <p className="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500 font-bold mt-1">
                Command Center
              </p>
            </div>
          </Link>
        </div>

        {/* Navigation Sections */}
        <nav className="flex-1 px-3.5 py-4 overflow-y-auto space-y-4">
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              <p className="px-3 text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                {section.title}
              </p>
              <ul className="space-y-0.5">
                {section.items.map(({ path, icon: Icon, label }) => {
                  const isActive = location.pathname === path || (path !== '/dashboard' && location.pathname.startsWith(path));
                  return (
                    <li key={path}>
                      <Link
                        to={path}
                        onClick={() => setSidebarOpen(false)}
                        className={`flex items-center gap-3 px-3 py-2 sm:py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all duration-150 ${
                          isActive
                            ? 'bg-indigo-500/10 dark:bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 shadow-sm border border-indigo-500/25 font-bold'
                            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100/80 dark:hover:bg-white/[0.05] hover:text-slate-900 dark:hover:text-slate-100 border border-transparent'
                        }`}
                      >
                        <Icon
                          size={16}
                          strokeWidth={isActive ? 2.4 : 2}
                          className={isActive ? 'text-indigo-600 dark:text-indigo-400 shrink-0' : 'text-slate-400 dark:text-slate-500 shrink-0'}
                        />
                        <span className="truncate">{label}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3.5 border-t border-slate-100 dark:border-white/[0.06] shrink-0 space-y-2">
          <Link
            to="/profile"
            onClick={() => setSidebarOpen(false)}
            className="flex items-center justify-between p-2 rounded-xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200/60 dark:border-white/[0.05] hover:bg-slate-100 dark:hover:bg-white/[0.06] transition-colors"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-6 h-6 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-sm">
                U
              </div>
              <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">My Profile</span>
            </div>
            <ChevronRight size={14} className="text-slate-400 shrink-0" />
          </Link>

          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-1.5 w-full rounded-xl text-xs font-semibold text-slate-500 dark:text-slate-400 hover:bg-rose-500/10 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
          >
            <LogOut size={14} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-30 lg:hidden animate-fade-in"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content area */}
      <main className="flex-1 lg:ml-64 flex flex-col min-h-screen pt-14 sm:pt-16 lg:pt-0 min-w-0 max-w-full overflow-x-hidden">
        {/* Desktop Glass Header */}
        <header className="hidden lg:flex items-center justify-between px-6 xl:px-8 py-3.5 border-b border-slate-200/80 dark:border-white/[0.07] bg-white/70 dark:bg-[#050811]/70 backdrop-blur-xl sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <span className="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
              Workspace
            </span>
            <ChevronRight size={14} className="text-slate-300 dark:text-slate-600" />
            <span className="text-sm font-bold text-slate-900 dark:text-slate-100">{pageTitle}</span>
            <div className="h-4 w-px bg-slate-200 dark:bg-white/10 ml-1" />
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-bold text-[11px] backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live AI Pipeline
            </span>
          </div>
          <div className="flex items-center gap-3">
            <GlobalSyncIndicator />
            <div className="h-4 w-px bg-slate-200 dark:bg-white/10" />
            <ThemeToggle />
          </div>
        </header>

        <div className="flex-1 p-3.5 sm:p-5 lg:p-8 max-w-7xl mx-auto w-full min-w-0 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}

export default MainLayout;
