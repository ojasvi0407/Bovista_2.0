export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type ApiEnvelope<T> = {
  data: T | null;
  error: { code: string; message: string } | null;
};

type RequestOptions = Omit<RequestInit, 'body' | 'headers'> & {
  body?: unknown;
  headers?: HeadersInit;
  idempotent?: boolean;
};

function requestId(): string {
  return crypto.randomUUID();
}

export class ApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly accessToken?: () => string | null,
  ) {}

  get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'GET' });
  }

  post<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body, idempotent: true });
  }

  async request<T>(path: string, options: RequestOptions): Promise<T> {
    const headers = new Headers(options.headers);
    const token = this.accessToken?.();
    headers.set('X-Request-ID', requestId());
    if (token) headers.set('Authorization', `Bearer ${token}`);
    if (options.body !== undefined) headers.set('Content-Type', 'application/json');
    if (options.idempotent) headers.set('Idempotency-Key', requestId());

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    if (response.status === 204) return undefined as T;

    const payload = (await response.json()) as ApiEnvelope<T>;
    if (!response.ok || payload.error) {
      throw new ApiError(
        response.status,
        payload.error?.code ?? 'REQUEST_FAILED',
        payload.error?.message ?? 'The request could not be completed.',
      );
    }
    return payload.data as T;
  }
}

export const api = new ApiClient(import.meta.env.VITE_API_BASE_URL ?? '/api/v1', () =>
  sessionStorage.getItem('bovista.access_token'),
);
