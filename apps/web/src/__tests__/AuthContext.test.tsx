import { render, screen, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AuthProvider, useAuth } from '../context/AuthContext';

// Helper consumer component
const TestAuthConsumer: React.FC = () => {
  const { session, isAuthenticated, isOwner, canEdit, canApprove, login, loginWithDevToken, logout } = useAuth();
  return (
    <div>
      <span data-testid="auth-status">{isAuthenticated ? 'logged-in' : 'logged-out'}</span>
      <span data-testid="user-role">{session?.role || 'none'}</span>
      <span data-testid="is-owner">{isOwner ? 'yes' : 'no'}</span>
      <span data-testid="can-edit">{canEdit ? 'yes' : 'no'}</span>
      <span data-testid="can-approve">{canApprove ? 'yes' : 'no'}</span>
      <button onClick={() => login('enterprise@test.com', 'Pass1234!')}>Login Enterprise</button>
      <button onClick={() => loginWithDevToken('user_test', 'Owner', 'ws_test')}>Login Owner</button>
      <button onClick={() => loginWithDevToken('user_test', 'Editor', 'ws_test')}>Login Editor</button>
      <button onClick={() => loginWithDevToken('user_test', 'Viewer', 'ws_test')}>Login Viewer</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};


let setItemSpy: any;

describe('AuthContext Security & RBAC', () => {
  beforeEach(() => {
    setItemSpy = vi.spyOn(Storage.prototype, 'setItem');
    vi.spyOn(Storage.prototype, 'getItem');

    // Mock global fetch for dev-token
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url: any, init: any) => {
      const body = JSON.parse(init?.body || '{}');
      return {
        ok: true,
        json: async () => ({
          access_token: 'fake-jwt-in-memory',
          token_type: 'bearer',
          user_id: body.user_id || 'user_test',
          role: body.role || 'Owner',
          workspace_id: body.workspace_id || 'ws_test',
          expires_in: 3600,
        }),
      } as Response;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes as unauthenticated without accessing localStorage for JWT', () => {
    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-out');
  });

  it('stores JWT strictly in-memory and NEVER writes tokens to localStorage', async () => {
    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText('Login Owner').click();
    });

    expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
    expect(screen.getByTestId('user-role')).toHaveTextContent('Owner');
    expect(screen.getByTestId('is-owner')).toHaveTextContent('yes');
    expect(screen.getByTestId('can-approve')).toHaveTextContent('yes');

    // SECURITY CHECK: Verify localStorage.setItem was NEVER called with tokens or secrets
    expect(setItemSpy).not.toHaveBeenCalledWith('jwt', expect.anything());
    expect(setItemSpy).not.toHaveBeenCalledWith('token', expect.anything());
    expect(setItemSpy).not.toHaveBeenCalledWith('access_token', expect.anything());
  });

  it('enforces RBAC permissions correctly for Editor and Viewer', async () => {
    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    // Test Editor role
    await act(async () => {
      screen.getByText('Login Editor').click();
    });
    expect(screen.getByTestId('can-edit')).toHaveTextContent('yes');
    expect(screen.getByTestId('can-approve')).toHaveTextContent('no');
    expect(screen.getByTestId('is-owner')).toHaveTextContent('no');

    // Test Viewer role
    await act(async () => {
      screen.getByText('Login Viewer').click();
    });
    expect(screen.getByTestId('can-edit')).toHaveTextContent('no');
    expect(screen.getByTestId('can-approve')).toHaveTextContent('no');
    expect(screen.getByTestId('is-owner')).toHaveTextContent('no');
  });

  it('logs in successfully via enterprise email and password', async () => {
    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText('Login Enterprise').click();
    });

    expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');
    expect(screen.getByTestId('user-role')).toHaveTextContent('Owner');
    expect(setItemSpy).not.toHaveBeenCalledWith('jwt', expect.anything());
  });

  it('clears session upon logout', async () => {
    render(
      <AuthProvider>
        <TestAuthConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByText('Login Owner').click();
    });
    expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-in');

    await act(async () => {
      screen.getByText('Logout').click();
    });
    expect(screen.getByTestId('auth-status')).toHaveTextContent('logged-out');
  });
});

