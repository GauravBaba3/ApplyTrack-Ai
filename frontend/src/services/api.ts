import axios from 'axios';

const SESSION_STORAGE_KEY = 'applytrack_session_token';

// Extract session_token from URL query string upon redirect from Google OAuth (cross-domain auth)
if (typeof window !== 'undefined') {
  try {
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('session_token');
    if (tokenFromUrl) {
      localStorage.setItem(SESSION_STORAGE_KEY, tokenFromUrl);
      urlParams.delete('session_token');
      const newQuery = urlParams.toString();
      const cleanUrl = window.location.pathname + (newQuery ? `?${newQuery}` : '') + window.location.hash;
      window.history.replaceState(null, '', cleanUrl);
    }
  } catch (e) {
    // Ignore storage/history errors in restricted environments
  }
}

export const getStoredSessionToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(SESSION_STORAGE_KEY);
};

export const clearStoredSessionToken = (): void => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(SESSION_STORAGE_KEY);
  }
};

// Create axios instance with base URL from environment
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});

let cachedCsrfToken: string | null = null;

// Read cookie helper
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

export const fetchCsrfToken = async (): Promise<string | null> => {
  try {
    const response = await api.get('/auth/csrf/');
    if (response.data?.csrfToken) {
      cachedCsrfToken = response.data.csrfToken;
      return cachedCsrfToken;
    }
  } catch (err) {
    // Ignore error if csrf fetch fails
  }
  return null;
};

// Add request interceptor to handle session authorization and CSRF tokens
api.interceptors.request.use(
  async (config) => {
    // Attach header session token if available for cross-origin authentication
    const sessionToken = getStoredSessionToken();
    if (sessionToken && !config.headers['Authorization']) {
      config.headers['Authorization'] = `Bearer ${sessionToken}`;
    }

    const method = config.method?.toLowerCase();
    if (method === 'post' || method === 'put' || method === 'patch' || method === 'delete') {
      let token = cachedCsrfToken || getCookie('csrftoken');
      if (!token) {
        token = await fetchCsrfToken();
      }
      if (token) {
        config.headers['X-CSRFToken'] = token;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor
api.interceptors.response.use(
  (response) => {
    // Cache CSRF token if returned in response data
    if (response.data?.csrf_token) {
      cachedCsrfToken = response.data.csrf_token;
    } else if (response.data?.csrfToken) {
      cachedCsrfToken = response.data.csrfToken;
    }
    return response;
  },
  async (error) => {
    // Handle specific error cases
    if (error.response) {
      const { status, data } = error.response;
      const originalRequest = error.config;
      
      // Auto-retry once on 403 CSRF failure by refreshing CSRF token
      if (
        status === 403 &&
        typeof data?.detail === 'string' &&
        data.detail.includes('CSRF') &&
        !originalRequest._csrfRetried
      ) {
        originalRequest._csrfRetried = true;
        cachedCsrfToken = null;
        const newToken = await fetchCsrfToken();
        if (newToken) {
          originalRequest.headers['X-CSRFToken'] = newToken;
          return api(originalRequest);
        }
      }

      // Only redirect to login on 401 or DRF 403 (unauthenticated) for protected resource calls, not for the
      // initial auth check (/auth/me/) which is expected to fail when logged out
      const isUnauthenticated = status === 401 || (status === 403 && (data?.detail === 'Authentication credentials were not provided.' || data?.detail === 'Not authenticated.'));
      if (isUnauthenticated) {
        const url = error.config?.url || '';
        const isAuthCheck = url.includes('/auth/me/');
        const isOnLoginPage = window.location.pathname === '/login' || window.location.pathname === '/';
        if (!isAuthCheck && !isOnLoginPage) {
          clearStoredSessionToken();
          window.location.href = '/login';
        }
      }
      
      return Promise.reject({ ...error, message: data?.error || data?.detail || error.message });
    }
    
    // Handle network errors
    if (error.code === 'ECONNREFUSED') {
      return Promise.reject({ ...error, message: 'Failed to connect to server' });
    }
    
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authApi = {
  googleLogin: () => api.get('/auth/google/'),
  googleCallback: (code: string, state: string) => 
    api.get('/auth/google/callback/', { params: { code, state } }),
  getMe: () => api.get('/auth/me/'),
  getCsrf: () => api.get('/auth/csrf/'),
  logout: async () => {
    try {
      return await api.post('/auth/logout/');
    } finally {
      clearStoredSessionToken();
    }
  },
  disconnectGmail: () => api.post('/auth/disconnect-gmail/'),
  getSettings: () => api.get('/auth/settings/'),
  updateSettings: (settings: any) => api.patch('/auth/settings/', settings),
};

// Application endpoints
export const applicationApi = {
  getAll: (params?: any) => api.get('/applications/', { params }),
  getById: (id: number) => api.get(`/applications/${id}/`),
  create: (data: any) => api.post('/applications/', data),
  update: (id: number, data: any) => api.patch(`/applications/${id}/`, data),
  delete: (id: number) => api.delete(`/applications/${id}/`),
  getStats: () => api.get('/applications/stats/'),
  getStatusHistory: (applicationId: number) => 
    api.get(`/applications/${applicationId}/history/`),
  getFollowUps: (applicationId: number) => 
    api.get(`/applications/${applicationId}/followups/`),
  createFollowUp: (applicationId: number, data: any) => 
    api.post(`/applications/${applicationId}/followups/`, data),
  generateFollowUpDraft: (applicationId: number) => 
    api.post(`/applications/${applicationId}/followups/draft/`),
};

// Email endpoints
export const emailApi = {
  getAll: (params?: any) => api.get('/emails/', { params }),
  getById: (id: number) => api.get(`/emails/${id}/`),
  markAsReviewed: (emailId: number) => api.post(`/emails/${emailId}/review/`),
  ignore: (emailId: number) => api.post(`/emails/${emailId}/ignore/`),
  getSyncLogs: () => api.get('/emails/sync-logs/'),
};

// Gmail sync endpoints
export const gmailApi = {
  sync: (options?: { reset?: boolean; page_size?: number }) => 
    api.post('/gmail/sync/', options || {}),
  getStatus: () => api.get('/gmail/sync/status/'),
};

// Analytics endpoints
export const analyticsApi = {
  get: () => api.get('/analytics/'),
};

export default api;
