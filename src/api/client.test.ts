import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiClient, ApiError } from './client';

describe('ApiClient', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('unwraps the backend envelope and sends bearer plus idempotency headers', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { id: 'animal-1' } }), { status: 201 }),
    );
    vi.stubGlobal('fetch', fetcher);

    const client = new ApiClient('https://api.example.test/api/v1', () => 'access-token');
    await expect(client.post<{ id: string }>('/animals', { tag: 'A-1' })).resolves.toEqual({
      id: 'animal-1',
    });

    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('https://api.example.test/api/v1/animals');
    expect(init.method).toBe('POST');
    const headers = init.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer access-token');
    expect(headers.get('Idempotency-Key')).toMatch(/^[a-f0-9-]{36}$/i);
  });

  it('exposes the backend error code without leaking an opaque HTTP failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: 'INVALID_OTP', message: 'The code is invalid.' } }),
          { status: 401 },
        ),
      ),
    );

    const client = new ApiClient('https://api.example.test/api/v1');
    await expect(client.get('/auth/me')).rejects.toMatchObject({
      status: 401,
      code: 'INVALID_OTP',
      message: 'The code is invalid.',
    });
  });
});
