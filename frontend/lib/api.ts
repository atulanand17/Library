const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  requestId: string | null;
  details: unknown;

  constructor(message: string, status: number, requestId: string | null, details: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

type FastApiValidationError = {
  loc?: Array<string | number>;
  msg?: string;
};

type ApiErrorPayload = {
  detail?: string | FastApiValidationError[];
  request_id?: string;
};

function formatValidationErrors(errors: FastApiValidationError[]): string {
  return errors
    .map((error) => {
      const location = Array.isArray(error.loc) ? error.loc.join(' > ') : 'request';
      return `${location}: ${error.msg ?? 'Invalid value'}`;
    })
    .join('; ');
}

function buildErrorMessage(payload: ApiErrorPayload, status: number, requestId: string | null): string {
  let message = `Request failed with status ${status}`;

  if (Array.isArray(payload.detail)) {
    message = formatValidationErrors(payload.detail);
  } else if (typeof payload.detail === 'string' && payload.detail.trim()) {
    message = payload.detail;
  }

  const effectiveRequestId = requestId ?? payload.request_id ?? null;
  return effectiveRequestId ? `${message} (Request ID: ${effectiveRequestId})` : message;
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {}),
      },
      cache: 'no-store',
    });
  } catch {
    throw new ApiError('Unable to reach the server. Please check whether the backend is running.', 0, null, null);
  }

  const requestId = response.headers.get('X-Request-ID');

  if (!response.ok) {
    const errorPayload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    const message = buildErrorMessage(errorPayload, response.status, requestId);
    throw new ApiError(message, response.status, requestId ?? errorPayload.request_id ?? null, errorPayload.detail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
