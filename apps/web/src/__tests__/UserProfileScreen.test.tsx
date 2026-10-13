import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { UserProfileScreen } from '../screens/UserProfileScreen';
import { AuthProvider } from '../context/AuthContext';
import { LanguageProvider } from '../context/LanguageContext';
import { ThemeProvider } from '../context/ThemeContext';
import { ToastProvider } from '../context/ToastContext';

const mockProfile = {
  id: 'owner_martial',
  email: 'martial@contentops.internal',
  full_name: 'Martial Martial',
  display_name: 'Martial (CCO)',
  job_title: 'Chief Content Officer',
  avatar_url: null,
  timezone: 'Europe/Paris',
  language: 'fr',
  theme: 'dark',
  notification_preferences: {
    email_critical_alerts: true,
    notify_on_approval: true,
    browser_push: false,
    weekly_digest: true,
  },
  ui_preferences: {
    density: 'comfortable',
    default_view: 'calendar',
  },
  created_at: '2026-10-09T20:00:00Z',
  updated_at: '2026-10-09T20:00:00Z',
  workspaces: [
    {
      workspace_id: 'ws_default',
      name: 'Default Editorial Workspace',
      role: 'Owner',
      timezone: 'UTC',
      is_owner: true,
    },
  ],
};

const mockSessions = [
  {
    id: 'sess_1',
    token_jti: 'jti_1',
    user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    ip_address: '127.0.0.1',
    last_active_at: '2026-10-09T22:00:00Z',
    expires_at: '2026-10-10T22:00:00Z',
    is_current: true,
  },
];

const renderComponent = () => {
  return render(
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <ToastProvider>
            <UserProfileScreen />
          </ToastProvider>
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
};

describe('UserProfileScreen Component', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any, init?: any) => {
      const urlStr = String(url);
      const method = (init?.method || 'GET').toUpperCase();
      if (urlStr.endsWith('/v1/me') && method === 'GET') {
        return {
          ok: true,
          status: 200,
          json: async () => mockProfile,
          headers: new Headers(),
        } as Response;
      }
      if (urlStr.endsWith('/v1/me/sessions') && method === 'GET') {
        return {
          ok: true,
          status: 200,
          json: async () => mockSessions,
          headers: new Headers(),
        } as Response;
      }
      if (urlStr.endsWith('/v1/me') && method === 'PATCH') {
        const body = JSON.parse(init.body || '{}');
        return {
          ok: true,
          status: 200,
          json: async () => ({ ...mockProfile, ...body }),
          headers: new Headers(),
        } as Response;
      }
      if (urlStr.endsWith('/v1/me/export') && method === 'GET') {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            exported_at: '2026-10-09T23:00:00Z',
            user: mockProfile,
            workspaces: mockProfile.workspaces,
            sessions: mockSessions,
            recent_audit_logs: [],
          }),
          headers: new Headers(),
        } as Response;
      }
      return {
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      } as Response;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders user profile details and workspaces accurately', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Martial (CCO)')).toBeInTheDocument();
      expect(screen.getByText('martial@contentops.internal')).toBeInTheDocument();
      expect(screen.getByText('Chief Content Officer')).toBeInTheDocument();
    });
  });

  it('ensures the email field is strictly read-only for security', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Martial (CCO)')).toBeInTheDocument();
    });

    const emailInput = screen.getByDisplayValue('martial@contentops.internal');
    expect(emailInput).toBeDisabled();
    expect(screen.getByText(/Géré par le serveur/i)).toBeInTheDocument();
  });

  it('allows switching between profile tabs', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Martial (CCO)')).toBeInTheDocument();
    });

    // Switch to Preferences tab
    const prefTab = screen.getByRole('button', { name: /Affichage & Langue/i });
    fireEvent.click(prefTab);
    expect(screen.getByText(/Fuseau horaire \(IANA\)/i)).toBeInTheDocument();

    // Switch to Security tab
    const secTab = screen.getByRole('button', { name: /Sécurité & Sessions/i });
    fireEvent.click(secTab);
    expect(screen.getByText(/Changement de Mot de Passe/i)).toBeInTheDocument();
    expect(screen.getByText(/Sessions Actives & Connexions/i)).toBeInTheDocument();

    // Switch to Workspaces tab
    const wsTab = screen.getByRole('button', { name: /Workspaces & Rôles/i });
    fireEvent.click(wsTab);
    expect(screen.getByText('Default Editorial Workspace')).toBeInTheDocument();

    // Switch to GDPR tab
    const gdprTab = screen.getByRole('button', { name: /Conformité RGPD/i });
    fireEvent.click(gdprTab);
    expect(screen.getByText(/Portabilité des Données \(Article 20 RGPD\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Droit à l'Effacement & Suppression de Compte/i)).toBeInTheDocument();
  });

  it('handles personal data export download', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Martial (CCO)')).toBeInTheDocument();
    });

    const exportBtn = screen.getByRole('button', { name: /Export RGPD \(JSON\)/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/v1/me/export', expect.anything());
    });
  });
});
