/**
 * Client-side SessionStorage Cache Service for ApplyTrack AI.
 * 
 * Provides user-scoped, ephemeral caching for UI data that survives page refreshes
 * during the current browser tab session and clears when the tab/session closes.
 */

export const CACHE_TTL = {
  DASHBOARD: 3 * 60 * 1000,       // 3 minutes
  APPLICATIONS: 5 * 60 * 1000,    // 5 minutes
  EMAILS: 3 * 60 * 1000,          // 3 minutes
  ANALYTICS: 10 * 60 * 1000,      // 10 minutes
  SETTINGS: 15 * 60 * 1000,       // 15 minutes
};

interface CacheEntry<T> {
  data: T;
  cachedAt: number;
}

class CacheService {
  private currentUserId: string | null = null;
  private readonly prefix = 'applytrack';

  /**
   * Associate the cache service with the authenticated user.
   */
  public setUser(userId: string | number | null): void {
    const newUserId = userId ? String(userId) : null;
    if (this.currentUserId && newUserId && this.currentUserId !== newUserId) {
      // User switched within same tab session: purge old user's cache
      this.clearUserCache(this.currentUserId);
    }
    this.currentUserId = newUserId;
  }

  /**
   * Build namespaced key scoped to current user.
   */
  private getKey(key: string): string {
    const userScope = this.currentUserId ? `u_${this.currentUserId}` : 'anon';
    return `${this.prefix}:${userScope}:${key}`;
  }

  /**
   * Retrieve cached data if present and valid.
   */
  public get<T>(key: string, maxAgeMs?: number): T | null {
    if (typeof window === 'undefined' || !window.sessionStorage) return null;

    try {
      const fullKey = this.getKey(key);
      const raw = window.sessionStorage.getItem(fullKey);
      if (!raw) return null;

      const entry: CacheEntry<T> = JSON.parse(raw);
      if (!entry || typeof entry.cachedAt !== 'number') {
        this.remove(key);
        return null;
      }

      // Check max age if specified
      if (maxAgeMs && maxAgeMs > 0) {
        const age = Date.now() - entry.cachedAt;
        if (age > maxAgeMs) {
          // Stale beyond allowed window
          return null;
        }
      }

      return entry.data;
    } catch (e) {
      // Invalid/corrupted JSON: remove key gracefully
      this.remove(key);
      return null;
    }
  }

  /**
   * Save data to sessionStorage with current timestamp.
   */
  public set<T>(key: string, data: T): void {
    if (typeof window === 'undefined' || !window.sessionStorage) return;

    try {
      const fullKey = this.getKey(key);
      const entry: CacheEntry<T> = {
        data,
        cachedAt: Date.now(),
      };
      window.sessionStorage.setItem(fullKey, JSON.stringify(entry));
    } catch (e) {
      // Handle quota exceeded or private mode restriction gracefully
      console.warn('Failed to save to sessionStorage cache:', e);
    }
  }

  /**
   * Remove a specific cache entry.
   */
  public remove(key: string): void {
    if (typeof window === 'undefined' || !window.sessionStorage) return;

    try {
      const fullKey = this.getKey(key);
      window.sessionStorage.removeItem(fullKey);
    } catch (e) {
      // Ignore
    }
  }

  /**
   * Get timestamp when key was cached.
   */
  public getTimestamp(key: string): number | null {
    if (typeof window === 'undefined' || !window.sessionStorage) return null;

    try {
      const fullKey = this.getKey(key);
      const raw = window.sessionStorage.getItem(fullKey);
      if (!raw) return null;

      const entry = JSON.parse(raw);
      return typeof entry?.cachedAt === 'number' ? entry.cachedAt : null;
    } catch (e) {
      return null;
    }
  }

  /**
   * Clear all cached keys for a specific user.
   */
  public clearUserCache(userId?: string | number): void {
    if (typeof window === 'undefined' || !window.sessionStorage) return;

    try {
      const targetUserScope = userId ? `u_${userId}` : (this.currentUserId ? `u_${this.currentUserId}` : 'anon');
      const targetPrefix = `${this.prefix}:${targetUserScope}:`;

      const keysToRemove: string[] = [];
      for (let i = 0; i < window.sessionStorage.length; i++) {
        const key = window.sessionStorage.key(i);
        if (key && key.startsWith(targetPrefix)) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach((k) => window.sessionStorage.removeItem(k));
    } catch (e) {
      console.warn('Error clearing user cache:', e);
    }
  }

  /**
   * Clear all applytrack:* cache entries (e.g. on logout).
   */
  public clearAll(): void {
    if (typeof window === 'undefined' || !window.sessionStorage) return;

    try {
      const keysToRemove: string[] = [];
      for (let i = 0; i < window.sessionStorage.length; i++) {
        const key = window.sessionStorage.key(i);
        if (key && key.startsWith(`${this.prefix}:`)) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach((k) => window.sessionStorage.removeItem(k));
    } catch (e) {
      console.warn('Error clearing all cache:', e);
    }
  }
}

export const cacheService = new CacheService();
export default cacheService;
