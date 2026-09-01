import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle({ showLabel = false, className = '' }: { showLabel?: boolean; className?: string }) {
  const { resolvedTheme, toggleTheme } = useTheme();

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    toggleTheme();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`relative inline-flex items-center justify-center p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all active:scale-95 border border-slate-200/80 dark:border-slate-700/80 shadow-sm cursor-pointer ${className}`}
      title={`Switch to ${resolvedTheme === 'dark' ? 'Light' : 'Dark'} Mode`}
      aria-label="Toggle theme"
    >
      {resolvedTheme === 'dark' ? (
        <Sun size={18} className="text-amber-400 hover:text-amber-300 transition-transform rotate-0 scale-100" />
      ) : (
        <Moon size={18} className="text-indigo-600 hover:text-indigo-700 transition-transform rotate-0 scale-100" />
      )}
      {showLabel && (
        <span className="ml-2 text-xs font-semibold">
          {resolvedTheme === 'dark' ? 'Light Mode' : 'Dark Mode'}
        </span>
      )}
    </button>
  );
}
