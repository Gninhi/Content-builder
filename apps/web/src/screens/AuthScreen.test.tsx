import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider } from '../context/AuthContext';
import { LanguageProvider } from '../context/LanguageContext';
import { ThemeProvider } from '../context/ThemeContext';
import { AuthScreen } from './AuthScreen';

function renderAuthScreen() {
  return render(
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <AuthScreen />
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

describe('AuthScreen — Registration, Dev Mailbox & Error Handling', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    try {
      window.localStorage?.clear();
    } catch {}
    window.history.replaceState({}, '', '/');
  });

  it('completes nominal registration and verifies email via controlled local dev mailbox', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any, init?: any) => {
      const url = typeof input === 'string' ? input : input.url;
      if (url.includes('/v1/auth/refresh')) {
        return new Response(JSON.stringify({ detail: 'No session' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        });
      }
      if (url.includes('/v1/auth/register')) {
        return new Response(
          JSON.stringify({
            message: 'Compte créé. Vérifiez votre boîte mail.',
            email: 'sarah@acme.io',
            requires_verification: true,
            email_delivery_status: 'sent',
          }),
          { status: 201, headers: { 'content-type': 'application/json' } }
        );
      }
      if (url.includes('/v1/auth/dev/mailbox')) {
        return new Response(
          JSON.stringify({
            enabled: true,
            messages: [
              {
                type: 'verification',
                to: 'sarah@acme.io',
                token: 'dev_verify_token_abc123456789',
                verify_url: 'http://localhost:3000/?verify_token=dev_verify_token_abc123456789',
              },
            ],
          }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        );
      }
      if (url.includes('/v1/auth/verify-email')) {
        const body = JSON.parse(init?.body || '{}');
        expect(body.token).toBe('dev_verify_token_abc123456789');
        return new Response(
          JSON.stringify({
            message: 'Adresse email vérifiée avec succès. Vous pouvez maintenant vous connecter.',
          }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        );
      }
      return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
    });

    const { container } = renderAuthScreen();

    // Switch to Register tab
    const tabs = screen.getAllByRole('tab');
    fireEvent.click(tabs[1]);

    fireEvent.change(container.querySelector('#reg-name')!, { target: { value: 'Sarah Connor' } });
    fireEvent.change(container.querySelector('#reg-email')!, { target: { value: 'sarah@acme.io' } });
    fireEvent.change(container.querySelector('#reg-password')!, { target: { value: 'StrongPass!2026' } });
    fireEvent.change(container.querySelector('#reg-workspace')!, { target: { value: 'Acme Studio' } });

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    const submitBtn = container.querySelector('button[type="submit"]')!;
    fireEvent.click(submitBtn);

    // Wait for dev mailbox panel to appear with verification button
    await waitFor(() => {
      expect(screen.getByTestId('dev-mailbox-panel')).toBeTruthy();
    });

    const verifyBtn = screen.getByTestId('dev-verify-email-btn');
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      const statuses = screen.getAllByRole('status');
      const hasSuccess = statuses.some(s => s.textContent?.includes('Adresse email vérifiée avec succès'));
      expect(hasSuccess).toBe(true);
    });

    expect(fetchMock).toHaveBeenCalled();
  });

  it('displays explicit backend unavailable message on 500/502 non-JSON proxy error instead of generic form error', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any) => {
      const url = typeof input === 'string' ? input : input.url;
      if (url.includes('/v1/auth/refresh')) {
        return new Response('', { status: 500, headers: { 'content-type': 'text/plain' } });
      }
      if (url.includes('/v1/auth/register')) {
        return new Response('Proxy error: ECONNREFUSED 127.0.0.1:8000', {
          status: 500,
          headers: { 'content-type': 'text/plain' },
        });
      }
      return new Response('{}', { status: 200 });
    });

    const { container } = renderAuthScreen();
    fireEvent.click(screen.getAllByRole('tab')[1]);

    fireEvent.change(container.querySelector('#reg-name')!, { target: { value: 'Sarah Connor' } });
    fireEvent.change(container.querySelector('#reg-email')!, { target: { value: 'sarah@acme.io' } });
    fireEvent.change(container.querySelector('#reg-password')!, { target: { value: 'StrongPass!2026' } });

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    fireEvent.click(container.querySelector('button[type="submit"]')!);

    await waitFor(() => {
      const alertText = screen.getByRole('alert').textContent || '';
      expect(alertText).toContain('indisponible');
      expect(alertText).toContain('8000');
      expect(alertText).not.toContain('[object Object]');
    });
  });

  it('parses 422 Pydantic validation error arrays cleanly without [object Object]', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: any) => {
      const url = typeof input === 'string' ? input : input.url;
      if (url.includes('/v1/auth/refresh')) {
        return new Response('{}', { status: 401, headers: { 'content-type': 'application/json' } });
      }
      if (url.includes('/v1/auth/register')) {
        return new Response(
          JSON.stringify({
            detail: [
              {
                loc: ['body', 'password'],
                msg: 'Value error, Le mot de passe doit contenir au moins un caractère spécial.',
                type: 'value_error',
              },
            ],
          }),
          { status: 422, headers: { 'content-type': 'application/json' } }
        );
      }
      return new Response('{}', { status: 200 });
    });

    const { container } = renderAuthScreen();
    fireEvent.click(screen.getAllByRole('tab')[1]);

    fireEvent.change(container.querySelector('#reg-name')!, { target: { value: 'Sarah Connor' } });
    fireEvent.change(container.querySelector('#reg-email')!, { target: { value: 'sarah@acme.io' } });
    fireEvent.change(container.querySelector('#reg-password')!, { target: { value: 'StrongPass2026' } });

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    fireEvent.click(container.querySelector('button[type="submit"]')!);

    await waitFor(() => {
      const alertText = screen.getByRole('alert').textContent || '';
      expect(alertText).toContain('caractère spécial');
      expect(alertText).not.toContain('[object Object]');
    });
  });

  it('validates password length bounds (min 10, max 128) before calling API', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('{}', { status: 401, headers: { 'content-type': 'application/json' } })
    );

    const { container } = renderAuthScreen();
    fireEvent.click(screen.getAllByRole('tab')[1]);

    fireEvent.change(container.querySelector('#reg-name')!, { target: { value: 'Sarah Connor' } });
    fireEvent.change(container.querySelector('#reg-email')!, { target: { value: 'sarah@acme.io' } });
    fireEvent.change(container.querySelector('#reg-password')!, {
      target: { value: 'A1!' + 'a'.repeat(130) },
    });

    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    fireEvent.click(container.querySelector('button[type="submit"]')!);

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain('128 caractères');
    });

    const registerCalls = fetchSpy.mock.calls.filter(([url]) => String(url).includes('/v1/auth/register'));
    expect(registerCalls.length).toBe(0);
  });
});
