import { UserSession } from '../types/api';

// In-memory token storage strictly preventing XSS exposure (Never stored in localStorage)
let memorySession: UserSession | null = null;
let onAuthFailureCallback: (() => void) | null = null;

export function setMemorySession(session: UserSession | null) {
  memorySession = session;
}

export function getMemorySession(): UserSession | null {
  return memorySession;
}

export function setAuthFailureHandler(callback: () => void) {
  onAuthFailureCallback = callback;
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

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');

  if (memorySession?.token) {
    headers.set('Authorization', `Bearer ${memorySession.token}`);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  const correlationId = response.headers.get('x-correlation-id') || undefined;

  if (response.status === 401) {
    if (onAuthFailureCallback) {
      onAuthFailureCallback();
    }
    const errData = await response.json().catch(() => ({}));
    throw new ApiError(
      401,
      'Session expirée ou non authentifiée',
      errData.detail || 'Authentification requise',
      correlationId
    );
  }

  if (response.status === 403) {
    const errData = await response.json().catch(() => ({}));
    throw new ApiError(
      403,
      'Droits insuffisants pour cette action',
      errData.detail || 'Accès interdit',
      correlationId
    );
  }

  if (response.status === 429) {
    const errData = await response.json().catch(() => ({}));
    throw new ApiError(
      429,
      'Limite de requêtes atteinte (Rate limit)',
      errData.detail || 'Veuillez patienter',
      correlationId
    );
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errData.detail || `Erreur serveur (${response.status})`,
      errData.detail,
      correlationId
    );
  }

  return response.json();
}
