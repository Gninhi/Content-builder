import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { UserSession, UserRole, UserSummary, WorkspaceMembershipSummary } from '../types/api';
import { setMemorySession, getMemorySession, setAuthFailureHandler, performSilentRefresh } from '../lib/api';

interface RegisterParams {
  email: string;
  password: string;
  fullName: string;
  workspaceName?: string;
  invitationCode?: string;
  cguAccepted: boolean;
  privacyAccepted: boolean;
}

interface AuthContextType {
  session: UserSession | null;
  user: UserSummary | null;
  workspaces: WorkspaceMembershipSummary[];
  isAuthenticated: boolean;
  isInitializing: boolean;
  isDemo: boolean;
  demoExpiresAt: string | null;
  isOwner: boolean;
  canEdit: boolean;
  canApprove: boolean;
  login: (email: string, password: string, workspaceId?: string) => Promise<void>;
  register: (params: RegisterParams) => Promise<{ message: string; requiresVerification: boolean }>;
  verifyEmail: (token: string) => Promise<string>;
  resendVerification: (email: string) => Promise<string>;
  forgotPassword: (email: string) => Promise<string>;
  resetPassword: (token: string, newPassword: string) => Promise<string>;
  startDemo: () => Promise<void>;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  loginWithDevToken: (userId: string, role: UserRole, workspaceId: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const CURRENT_TAB_ID = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSessionState] = useState<UserSession | null>(null);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);
  const sessionRef = useRef<UserSession | null>(null);

  const setSession = useCallback((newSession: UserSession | null) => {
    sessionRef.current = newSession;
    setSessionState(newSession);
    setMemorySession(newSession);
  }, []);

  // Multi-tab synchronization channel
  useEffect(() => {
    let authChannel: BroadcastChannel | null = null;
    try {
      authChannel = new BroadcastChannel('contentops_auth');
      authChannel.onmessage = (event) => {
        if (event.data?.tabId === CURRENT_TAB_ID) {
          return; // Ignore broadcast generated from this local tab
        }
        if (event.data?.type === 'LOGOUT') {
          setSession(null);
        } else if (event.data?.type === 'LOGIN' || event.data?.type === 'WORKSPACE_SWITCH') {
          // Silent refresh to align token and workspace state across tabs
          performSilentRefresh().then((token) => {
            if (!token) {
              setSession(null);
            }
          });
        }
      };
    } catch {
      // BroadcastChannel not available in certain environments
    }

    setAuthFailureHandler(() => {
      setSession(null);
    });

    // Silent session bootstrap on app startup (e.g., F5 page reload)
    const initSession = async () => {
      try {
        const freshToken = await performSilentRefresh();
        if (freshToken) {
          const restoredSession = getMemorySession();
          if (restoredSession) {
            setSession(restoredSession);
          } else if (!sessionRef.current) {
            setSession(null);
          }
        } else {
          if (!sessionRef.current) {
            setSession(null);
          }
        }
      } catch {
        if (!sessionRef.current) {
          setSession(null);
        }
      } finally {
        setIsInitializing(false);
      }
    };

    initSession();

    return () => {
      if (authChannel) {
        authChannel.close();
      }
    };
  }, [setSession]);

  const broadcastEvent = (type: string, payload?: any) => {
    try {
      const channel = new BroadcastChannel('contentops_auth');
      channel.postMessage({ type, tabId: CURRENT_TAB_ID, ...payload });
      channel.close();
    } catch {
      // Fallback
    }
  };

  const login = async (email: string, password: string, workspaceId?: string) => {
    let res: Response;
    try {
      res = await fetch('/v1/auth/login', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          workspace_id: workspaceId || undefined,
        }),
      });
    } catch (networkErr: any) {
      throw new Error("Impossible de joindre le serveur d'authentification. Vérifiez que l'API est démarrée sur le port 8000.");
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 500 || res.status === 502 || res.status === 503 || res.status === 504) {
        throw new Error("Le serveur d'authentification a rencontré une erreur ou est indisponible (500/504).");
      }
      throw new Error(err.detail || 'Email ou mot de passe invalide.');
    }

    const data = await res.json();
    const newSession: UserSession = {
      user_id: data.user_id,
      role: data.role,
      workspace_id: data.workspace_id,
      token: data.access_token,
      user: data.user,
      workspaces: data.workspaces || [],
      is_demo: data.is_demo || false,
      expires_at: data.expires_at || null,
    };
    setSession(newSession);
    broadcastEvent('LOGIN');
  };

  const register = async (params: RegisterParams) => {
    const res = await fetch('/v1/auth/register', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: params.email,
        password: params.password,
        full_name: params.fullName,
        workspace_name: params.workspaceName || undefined,
        invitation_code: params.invitationCode || undefined,
        cgu_accepted: params.cguAccepted,
        privacy_accepted: params.privacyAccepted,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Échec de l'inscription.");
    }

    const data = await res.json();
    return {
      message: data.message || 'Compte créé avec succès.',
      requiresVerification: Boolean(data.requires_verification),
    };
  };

  const verifyEmail = async (token: string): Promise<string> => {
    const res = await fetch('/v1/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Jeton de vérification invalide ou expiré.');
    }

    const data = await res.json();
    return data.message || 'Adresse email vérifiée avec succès.';
  };

  const resendVerification = async (email: string): Promise<string> => {
    const res = await fetch('/v1/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Erreur lors de l'envoi de l'email.");
    }

    const data = await res.json();
    return data.message || 'Lien de confirmation renvoyé.';
  };

  const forgotPassword = async (email: string): Promise<string> => {
    const res = await fetch('/v1/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Erreur lors de l'envoi des instructions.");
    }

    const data = await res.json();
    return data.message || 'Instructions envoyées.';
  };

  const resetPassword = async (token: string, newPassword: string): Promise<string> => {
    const res = await fetch('/v1/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Échec de la réinitialisation du mot de passe.');
    }

    const data = await res.json();
    return data.message || 'Mot de passe réinitialisé avec succès.';
  };

  const startDemo = async () => {
    const res = await fetch('/v1/auth/demo', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Impossible de démarrer la session démo.');
    }

    const data = await res.json();
    const demoSession: UserSession = {
      user_id: data.user_id,
      role: data.role,
      workspace_id: data.workspace_id,
      token: data.access_token,
      user: data.user,
      workspaces: data.workspaces || [],
      is_demo: true,
      expires_at: data.expires_at || null,
    };
    setSession(demoSession);
    broadcastEvent('LOGIN');
  };

  const switchWorkspace = async (workspaceId: string) => {
    if (!session) return;
    const res = await fetch('/v1/auth/switch-workspace', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${session.token}`,
      },
      body: JSON.stringify({ workspace_id: workspaceId }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Impossible de changer d'espace.");
    }

    const data = await res.json();
    const updatedSession: UserSession = {
      ...session,
      workspace_id: data.workspace_id,
      role: data.role,
      token: data.access_token,
      user: data.user || session.user,
      workspaces: data.workspaces || session.workspaces,
      is_demo: data.is_demo || false,
      expires_at: data.expires_at || null,
    };
    setSession(updatedSession);
    broadcastEvent('WORKSPACE_SWITCH', { workspaceId });
  };

  const loginWithDevToken = async (userId: string, role: UserRole, workspaceId: string) => {
    const res = await fetch('/v1/auth/dev-token', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        role,
        workspace_id: workspaceId,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Échec de la génération du jeton');
    }

    const data = await res.json();
    const newSession: UserSession = {
      user_id: userId,
      role: data.role || role,
      workspace_id: data.workspace_id || workspaceId,
      token: data.access_token,
      workspaces: [
        {
          workspace_id: data.workspace_id || workspaceId,
          name: 'Workspace Dev',
          role: data.role || role,
          timezone: 'UTC',
          is_owner: (data.role || role).toLowerCase() === 'owner',
        },
      ],
      is_demo: false,
    };
    setSession(newSession);
    broadcastEvent('LOGIN');
  };

  const logout = async () => {
    try {
      await fetch('/v1/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: session?.token ? { Authorization: `Bearer ${session.token}` } : {},
      });
    } catch {
      // Proceed with local logout regardless of network status
    }
    setSession(null);
    broadcastEvent('LOGOUT');
  };

  const isOwner = session?.role?.toLowerCase() === 'owner';
  const canApprove = isOwner;
  const canEdit = isOwner || session?.role?.toLowerCase() === 'editor';
  const isDemo = Boolean(session?.is_demo);
  const demoExpiresAt = session?.expires_at || null;
  const user = session?.user || null;
  const workspaces = session?.workspaces || [];

  return (
    <AuthContext.Provider
      value={{
        session,
        user,
        workspaces,
        isAuthenticated: !!session,
        isInitializing,
        isDemo,
        demoExpiresAt,
        isOwner,
        canEdit,
        canApprove,
        login,
        register,
        verifyEmail,
        resendVerification,
        forgotPassword,
        resetPassword,
        startDemo,
        switchWorkspace,
        loginWithDevToken,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};
