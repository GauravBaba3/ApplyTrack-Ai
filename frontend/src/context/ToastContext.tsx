import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { CheckCircle2, AlertCircle, Info, XCircle, Loader2, X } from 'lucide-react';

export type ToastType = 'success' | 'info' | 'warning' | 'error' | 'loading';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  isExiting?: boolean;
}

interface ToastContextType {
  toasts: Toast[];
  showToast: (toast: Omit<Toast, 'id' | 'isExiting'>) => void;
  success: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  loading: (title: string, message?: string) => string;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, isExiting: true } : t))
    );
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 240);
  }, []);

  const showToast = useCallback(
    ({ type, title, message, duration = 4500 }: Omit<Toast, 'id' | 'isExiting'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: Toast = { id, type, title, message, duration, isExiting: false };

      setToasts((prev) => [newToast, ...prev]);

      if (duration > 0 && type !== 'loading') {
        setTimeout(() => {
          dismissToast(id);
        }, duration);
      }
      return id;
    },
    [dismissToast]
  );

  const success = useCallback(
    (title: string, message?: string) => {
      showToast({ type: 'success', title, message });
    },
    [showToast]
  );

  const info = useCallback(
    (title: string, message?: string) => {
      showToast({ type: 'info', title, message });
    },
    [showToast]
  );

  const warning = useCallback(
    (title: string, message?: string) => {
      showToast({ type: 'warning', title, message });
    },
    [showToast]
  );

  const error = useCallback(
    (title: string, message?: string) => {
      showToast({ type: 'error', title, message, duration: 6000 });
    },
    [showToast]
  );

  const loading = useCallback(
    (title: string, message?: string) => {
      return showToast({ type: 'loading', title, message, duration: 0 }) as unknown as string;
    },
    [showToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, showToast, success, info, warning, error, loading, dismissToast }}>
      {children}
      {/* Top Drop Toast Notification Container */}
      <div
        className="fixed top-3 inset-x-3 sm:inset-x-auto sm:top-6 sm:right-6 sm:w-full sm:max-w-md z-50 flex flex-col gap-2 pointer-events-none"
        aria-live="polite"
      >
        {toasts.map((toast) => {
          let accentBorder = 'border-slate-200/80 dark:border-white/10';
          let iconBg = 'bg-blue-500/15 text-blue-500 dark:text-blue-400';
          let icon = <Info className="shrink-0" size={18} />;

          if (toast.type === 'success') {
            accentBorder = 'border-emerald-500/30 dark:border-emerald-500/30';
            iconBg = 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
            icon = <CheckCircle2 className="shrink-0" size={18} />;
          } else if (toast.type === 'error') {
            accentBorder = 'border-rose-500/30 dark:border-rose-500/30';
            iconBg = 'bg-rose-500/15 text-rose-600 dark:text-rose-400';
            icon = <XCircle className="shrink-0" size={18} />;
          } else if (toast.type === 'warning') {
            accentBorder = 'border-amber-500/30 dark:border-amber-500/30';
            iconBg = 'bg-amber-500/15 text-amber-600 dark:text-amber-400';
            icon = <AlertCircle className="shrink-0" size={18} />;
          } else if (toast.type === 'loading') {
            accentBorder = 'border-indigo-500/30 dark:border-indigo-500/30';
            iconBg = 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400';
            icon = <Loader2 className="shrink-0 animate-spin" size={18} />;
          }

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto w-full flex items-start gap-3 p-3.5 sm:p-4 rounded-2xl border bg-white/95 dark:bg-[#070d1e]/95 backdrop-blur-2xl shadow-xl shadow-black/15 dark:shadow-black/50 text-slate-900 dark:text-slate-100 ${accentBorder} ${
                toast.isExiting ? 'animate-toast-rise' : 'animate-toast-drop'
              }`}
              role="alert"
            >
              <div className={`p-2 rounded-xl shrink-0 ${iconBg}`}>{icon}</div>
              <div className="flex-1 min-w-0 pt-0.5">
                <p className="text-sm font-bold tracking-tight leading-snug">{toast.title}</p>
                {toast.message && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed break-words">
                    {toast.message}
                  </p>
                )}
              </div>
              <button
                onClick={() => dismissToast(toast.id)}
                className="shrink-0 p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/[0.08] transition-colors -mr-1 -mt-1"
                aria-label="Close notification"
              >
                <X size={15} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
