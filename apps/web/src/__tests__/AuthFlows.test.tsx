import { render, screen, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AuthProvider, useAuth } from '../context/AuthContext';

const TestAuthDashboard: React.FC = () => {
  const {
    session,
    user,
    workspaces,
    isAuthenticated,
    isDemo,
    login,
    register,
    startDemo,
    switchWorkspace,
    logout,
  } = useAuth();

  return (
    <div>
      <span data-testid="auth-status">{isAuthenticated ? 'logged-in' : 'logged-out'}</span>
      <span data-testid="is-demo">{isDemo ? 'yes' : 'no'}</span>
      <span data-testid="user-email">{user?.email || session?.user_id || 'none'}</span>
      <span data-testid="active-workspace">{session?.workspace_id || 'none'}</span>
      <span data-testid="workspaces-count">{workspaces.length}</span>

      <button onClick={() => login('alice@example.com', 'SecurePassword2026!')}>Login</button>
      <button
        onClick={() =>
          register({
            email: 'bob@example.com',
            password: 'SecurePassword2026!',
            fullName: 'Bob Ross',
            cguAccepted: true,
            privacyAccepted: true,
          })
        }
      >
        Register
      </button>
      <button onClick={() => startDemo()}>Start Demo</button>
      <button onClick={() => switchWorkspace('ws_secondary')}>Switch Workspace</button>
      <button onClick={() => logout()}>Logout</button>
    </div>
  );
};

describe('AuthFlows Full Suite', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any) => {
      const urlStr = String(url);

      if (urlStr.includes('/v1/auth/refresh')) {
        // Return 401 on initial refresh so test starts logged out
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: 'No session' }),
        } as Response;
      }

      if (urlStr.includes('/v1/auth/login')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            access_token: 'jwt-access-token-123',
            user_id: 'usr_alice',
            role: 'Owner',
            workspace_id: 'ws_alice',
            user: {
              id: 'usr_alice',
              email: 'alice@example.com',
              full_name: 'Alice Wonderland',
              email_verified: true,
              language: 'fr',
              theme: 'dark',
            },
            workspaces: [
              {
                workspace_id: 'ws_alice',
                name: 'Alice WS',
                role: 'Owner',
                timezone: 'UTC',
                is_owner: true,
              },
              {
                workspace_id: 'ws_secondary',
                name: 'Secondary WS',
                role: 'Editor',
                timezone: 'UTC',
                is_owner: false,
              },
            ],
            is_demo: false,
          }),
        } as Response;
      }

      if (urlStr.includes('/v1/auth/register')) {
        return {
          ok: true,
          status: 201,
          json: async () => ({
            message: 'Compte créé avec succès.',
            user_id: 'usr_bob',
            email: 'bob@example.com',
            requires_verification: true,
          }),
        } as Response;
      }

      if (urlStr.includes('/v1/auth/demo')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            access_token: 'jwt-demo-token-999',
            user_id: 'demo_usr_123',
            role: 'Owner',
            workspace_id: 'ws_demo_123',
            user: {
              id: 'demo_usr_123',
              email: 'demo@demo.contentops.internal',
              full_name: 'Visiteur Démo',
              email_verified: true,
              language: 'fr',
              theme: 'dark',
            },
            workspaces: [
              {
                workspace_id: 'ws_demo_123',
                name: 'Espace Démo',
                role: 'Owner',
                timezone: 'UTC',
                is_owner: true,
                is_demo: true,
              },
            ],
            is_demo: true,
            expires_at: '2026-10-10T19:00:00Z',
          }),
        } as Response;
      }

      if (urlStr.includes('/v1/auth/switch-workspace')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            access_token: 'jwt-switched-token-456',
            user_id: 'usr_alice',
            role: 'Editor',
            workspace_id: 'ws_secondary',
            workspaces: [
              {
                workspace_id: 'ws_alice',
                name: 'Alice WS',
                role: 'Owner',
                timezone: 'UTC',
                is_owner: true,
              },
              {
                workspace_id: 'ws_secondary',
                name: 'Secondary WS',
                role: 'Editor',
                timezone: 'UTC',
                is_owner: false,
              },
            ],
            is_demo: false,
          }),
        } as Response;
      }

      if (urlStr.includes('/v1/auth/logout')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ message: 'Déconnexion réussie.' }),
        } as Response;
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({}),
      } as Response;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('handles login with full user and workspaces profile', async () => {
    render(
      <AuthProvider>
        <TestAuthDashboard />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText('Login').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      expect(screen.getByTestId('user-email')).toHaveTextContent('alice@example.com');
      expect(screen.getByTestId('active-workspace')).toHaveTextContent('ws_alice');
      expect(screen.getByTestId('workspaces-count')).toHaveTextContent('2');
      expect(screen.getByTestId('is-demo')).toHaveTextContent('no');
    });
  });

  it('switches workspace successfully', async () => {
    render(
      <AuthProvider>
        <TestAuthDashboard />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText('Login').click();
    });
    await waitFor(() => {
      expect(screen.getByTestId('active-workspace')).toHaveTextContent('ws_alice');
    });

    await act(async () => {
      screen.getByText('Switch Workspace').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('active-workspace')).toHaveTextContent('ws_secondary');
    });
  });

  it('starts ephemeral demo session with demo flag active', async () => {
    render(
      <AuthProvider>
        <TestAuthDashboard />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText('Start Demo').click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
      expect(screen.getByTestId('is-demo')).toHaveTextContent('yes');
      expect(screen.getByTestId('active-workspace')).toHaveTextContent('ws_demo_123');
    });
  });

  it('logs out and clears session state completely', async () => {
    render(
      <AuthProvider>
        <TestAuthDashboard />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText('Start Demo').click();
    });
    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
    });

    await act(async () => {
      screen.getByText('Logout').click();
    });
    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-out');
      expect(screen.getByTestId('active-workspace')).toHaveTextContent('none');
    });
  });
});
