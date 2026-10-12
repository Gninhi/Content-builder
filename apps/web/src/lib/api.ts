import { UserSession } from '../types/api';

// In-memory token storage strictly preventing XSS exposure (Never stored in localStorage / sessionStorage)
let memorySession: UserSession | null = null;
let onAuthFailureCallback: (() => void) | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setMemorySession(session: UserSession | null) {
  memorySession = session;
}

export function getMemorySession(): UserSession | null {
  return memorySession;
}

export function setAuthFailureHandler(callback: () => void) {
  onAuthFailureCallback = callback;
}

export function extractErrorMessage(errData: any, defaultMsg: string): string {
  if (!errData) return defaultMsg;
  if (typeof errData === 'string') return errData;
  if (typeof errData.detail === 'string' && errData.detail.trim()) return errData.detail;

  if (Array.isArray(errData.detail)) {
    // FastAPI / Pydantic validation errors: [{loc: [...], msg: "...", type: "..."}]
    const formatted = errData.detail
      .map((e: any) => {
        if (!e) return '';
        const field = Array.isArray(e.loc) ? e.loc.filter((p: any) => p !== 'body').join('.') : '';
        return field ? `${field}: ${e.msg || 'Invalide'}` : e.msg || JSON.stringify(e);
      })
      .filter(Boolean)
      .join(' ; ');
    if (formatted) return formatted;
  }

  if (errData.detail && typeof errData.detail === 'object') {
    try {
      return JSON.stringify(errData.detail);
    } catch {
      return defaultMsg;
    }
  }

  if (typeof errData.message === 'string' && errData.message.trim()) {
    return errData.message;
  }

  return defaultMsg;
}

export class ApiError extends Error {
  status: number;
  correlationId?: string;
  detail?: string;

  constructor(status: number, message: string, detail?: string, correlationId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.correlationId = correlationId;
  }
}

/**
 * Performs a silent token refresh using the httpOnly cookie.
 * Queues concurrent callers so only one refresh call is made.
 */
export async function performSilentRefresh(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const res = await fetch('/v1/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!res.ok) {
        return null;
      }

      const data = await res.json();
      if (data && data.access_token) {
        if (memorySession) {
          memorySession = {
            ...memorySession,
            token: data.access_token,
            role: data.role || memorySession.role,
            workspace_id: data.workspace_id || memorySession.workspace_id,
            user: data.user || memorySession.user,
            workspaces: data.workspaces || memorySession.workspaces,
            is_demo: data.is_demo ?? memorySession.is_demo,
            expires_at: data.expires_at ?? memorySession.expires_at,
          };
        } else {
          memorySession = {
            user_id: data.user_id,
            role: data.role,
            workspace_id: data.workspace_id,
            token: data.access_token,
            user: data.user,
            workspaces: data.workspaces,
            is_demo: data.is_demo,
            expires_at: data.expires_at,
          };
        }
        return data.access_token;
      }
      return null;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (memorySession?.token) {
    headers.set('Authorization', `Bearer ${memorySession.token}`);
  }

  let response: Response;
  try {
    response = await fetch(endpoint, {
      ...options,
      headers,
      credentials: 'include',
    });
  } catch (networkErr: any) {
    throw new ApiError(
      0,
      `Erreur de connexion réseau : impossible de joindre le serveur. (${networkErr.message || 'Serveur indisponible'})`,
      networkErr.message
    );
  }

  const correlationId = response.headers.get('x-correlation-id') || undefined;

  // Transparent automatic token refresh on 401 (excluding auth endpoints)
  if (response.status === 401 && !endpoint.includes('/v1/auth/')) {
    const freshToken = await performSilentRefresh();
    if (freshToken) {
      headers.set('Authorization', `Bearer ${freshToken}`);
      try {
        const retryResponse = await fetch(endpoint, {
          ...options,
          headers,
          credentials: 'include',
        });
        if (retryResponse.ok) {
          return retryResponse.json();
        }
      } catch {
        // Fall through to error handling
      }
    }

    if (onAuthFailureCallback) {
      onAuthFailureCallback();
    }
    const errData = await response.json().catch(() => ({}));
    const msg = extractErrorMessage(errData, 'Session expirée ou non authentifiée');
    throw new ApiError(401, msg, msg, correlationId);
  }

  if (response.status === 401) {
    if (onAuthFailureCallback) {
      onAuthFailureCallback();
    }
    const errData = await response.json().catch(() => ({}));
    const msg = extractErrorMessage(errData, 'Session expirée ou non authentifiée');
    throw new ApiError(401, msg, msg, correlationId);
  }

  if (response.status === 403) {
    const errData = await response.json().catch(() => ({}));
    const msg = extractErrorMessage(errData, 'Droits insuffisants pour cette action');
    throw new ApiError(403, msg, msg, correlationId);
  }

  if (response.status === 429) {
    const errData = await response.json().catch(() => ({}));
    const msg = extractErrorMessage(errData, 'Limite de requêtes atteinte (Rate limit)');
    throw new ApiError(429, msg, msg, correlationId);
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const defaultMsg = `Erreur serveur (${response.status})`;
    const msg = extractErrorMessage(errData, defaultMsg);
    throw new ApiError(
      response.status,
      msg,
      typeof errData?.detail === 'string' ? errData.detail : msg,
      correlationId
    );
  }

  return response.json();
}
