import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { authApi } from './services/api';
import { User } from './types';

// Layouts
import MainLayout from './layouts/MainLayout';
import AuthLayout from './layouts/AuthLayout';

// Pages
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ApplicationsPage from './pages/ApplicationsPage';
import ApplicationDetailPage from './pages/ApplicationDetailPage';
import EmailActivityPage from './pages/EmailActivityPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';
import NotFoundPage from './pages/NotFoundPage';

import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { SyncProvider } from './context/SyncContext';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated
    const checkAuth = async () => {
      try {
        const response = await authApi.getMe();
        setUser(response.data);
      } catch (error) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-[#0b0f19] flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-indigo-600 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <ToastProvider>
      <SyncProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<AuthLayout><LandingPage /></AuthLayout>} />
            <Route path="/login" element={<LoginPage />} />
            
            {/* Protected routes */}
            <Route
              path="/dashboard"
              element={
                <RequireAuth user={user}>
                  <MainLayout><DashboardPage /></MainLayout>
                </RequireAuth>
              }
            />
            <Route
              path="/applications"
              element={
                <RequireAuth user={user}>
                  <MainLayout><ApplicationsPage /></MainLayout>
                </RequireAuth>
              }
            />
            <Route
              path="/applications/:id"
              element={
                <RequireAuth user={user}>
                  <MainLayout><ApplicationDetailPage /></MainLayout>
                </RequireAuth>
              }
            />
            <Route
              path="/emails"
              element={
                <RequireAuth user={user}>
                  <MainLayout><EmailActivityPage /></MainLayout>
                </RequireAuth>
              }
            />
            <Route
              path="/analytics"
              element={
                <RequireAuth user={user}>
                  <MainLayout><AnalyticsPage /></MainLayout>
                </RequireAuth>
              }
            />
            <Route
              path="/settings"
              element={
                <RequireAuth user={user}>
                  <MainLayout><SettingsPage /></MainLayout>
                </RequireAuth>
              }
            />
            
            {/* 404 */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </SyncProvider>
    </ToastProvider>
  );
}

// Authentication wrapper
function RequireAuth({ user, children }: { user: User | null; children: JSX.Element }) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default App;
