import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiClient, setAuthFailureHandler, ApiError } from '../lib/api';

describe('apiClient hardening (Finding H2)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    setAuthFailureHandler(() => {});
  });

  it('handles HTTP 204 No Content cleanly without JSON parsing error', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(null, {
        status: 204,
        statusText: 'No Content',
      })
    );

    const result = await apiClient('/v1/me', { method: 'DELETE' });
    expect(result).toBeNull();
  });

  it('handles empty response body with content-length 0 without error', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response('', {
        status: 200,
        headers: { 'content-length': '0' },
      })
    );

    const result = await apiClient('/v1/ping');
    expect(result).toBeNull();
  });

  it('does NOT trigger onAuthFailureCallback when retryResponse fails with non-401 error', async () => {
    const onAuthFailure = vi.fn();
    setAuthFailureHandler(onAuthFailure);

    // 1st call: 401 on /v1/data
    // 2nd call: 200 on /v1/auth/refresh (silent refresh)
    // 3rd call: 404 on /v1/data (retry response)
    const mockFetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Token expired' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: 'fresh_jwt_token',
            role: 'Editor',
            workspace_id: 'ws_1',
            user_id: 'usr_1',
          }),
          { status: 200, headers: { 'content-type': 'application/json' } }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Resource not found' }), {
          status: 404,
          headers: { 'content-type': 'application/json' },
        })
      );

    global.fetch = mockFetch;

    await expect(apiClient('/v1/data')).rejects.toThrow(ApiError);
    // Crucial: session must NOT be wiped when retry error is 404
    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it('does NOT trigger onAuthFailureCallback on failed login 401', async () => {
    const onAuthFailure = vi.fn();
    setAuthFailureHandler(onAuthFailure);

    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Identifiants invalides' }), {
        status: 401,
        headers: { 'content-type': 'application/json' },
      })
    );

    await expect(
      apiClient('/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: 'test@example.com', password: 'wrong' }),
      })
    ).rejects.toThrow(ApiError);

    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it('triggers onAuthFailureCallback when authenticated call returns 401 and refresh fails', async () => {
    const onAuthFailure = vi.fn();
    setAuthFailureHandler(onAuthFailure);

    // 1st call: 401 on /v1/workspaces
    // 2nd call: 401 on /v1/auth/refresh
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Token expired' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Refresh expired' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        })
      );

    await expect(apiClient('/v1/workspaces')).rejects.toThrow(ApiError);
    expect(onAuthFailure).toHaveBeenCalledTimes(1);
  });

  it('deduplicates concurrent in-flight GET requests (ANOM-35)', async () => {
    let resolveFirstFetch: (res: Response) => void;
    const fetchPromise = new Promise<Response>((resolve) => {
      resolveFirstFetch = resolve;
    });

    const mockFetch = vi.fn().mockReturnValue(fetchPromise);
    global.fetch = mockFetch;

    // Fire 3 simultaneous GET calls to /v1/inbox
    const call1 = apiClient('/v1/inbox');
    const call2 = apiClient('/v1/inbox');
    const call3 = apiClient('/v1/inbox');

    // Only 1 real network fetch should have been dispatched
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Resolve the promise
    resolveFirstFetch!(
      new Response(JSON.stringify([{ id: 'draft-1' }]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    );

    const [res1, res2, res3] = await Promise.all([call1, call2, call3]);
    expect(res1).toEqual([{ id: 'draft-1' }]);
    expect(res2).toEqual([{ id: 'draft-1' }]);
    expect(res3).toEqual([{ id: 'draft-1' }]);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
