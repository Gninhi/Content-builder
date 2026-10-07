import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserSession, UserRole } from '../types/api';
import { setMemorySession, setAuthFailureHandler } from '../lib/api';

interface AuthContextType {
  session: UserSession | null;
  isAuthenticated: boolean;
  loginWithDevToken: (userId: string, role: UserRole, workspaceId: string) => Promise<void>;
  logout: () => void;
  isOwner: boolean;
  canEdit: boolean;
  canApprove: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSessionState] = useState<UserSession | null>(null);

  const setSession = (newSession: UserSession | null) => {
    setSessionState(newSession);
    setMemorySession(newSession);
  };

  useEffect(() => {
    setAuthFailureHandler(() => {
      setSession(null);
    });
  }, []);

  const loginWithDevToken = async (userId: string, role: UserRole, workspaceId: string) => {
    const res = await fetch('/v1/auth/dev-token', {
      method: 'POST',
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
    };
    setSession(newSession);
  };

  const logout = () => {
    setSession(null);
  };

  const isOwner = session?.role.toLowerCase() === 'owner';
  const canApprove = isOwner;
  const canEdit = isOwner || session?.role.toLowerCase() === 'editor';

  return (
    <AuthContext.Provider
      value={{
        session,
        isAuthenticated: !!session,
        loginWithDevToken,
        logout,
        isOwner,
        canEdit,
        canApprove,
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
