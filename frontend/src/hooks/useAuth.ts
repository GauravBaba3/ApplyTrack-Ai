import { useState, useEffect } from 'react';
import { authApi } from '../services/api';
import { User } from '../types';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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

  const logout = async () => {
    try {
      await authApi.logout();
      setUser(null);
      window.location.href = '/login';
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const disconnectGmail = async () => {
    try {
      await authApi.disconnectGmail();
      // Refresh user data
      const response = await authApi.getMe();
      setUser(response.data);
    } catch (error) {
      console.error('Failed to disconnect Gmail:', error);
    }
  };

  return { user, loading, logout, disconnectGmail, setUser };
}
