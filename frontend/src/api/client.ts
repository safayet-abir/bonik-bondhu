// fetch wrapper (TRD §3 "API client"): cookies included, CSRF header on every
// request, error envelope -> ApiError with an i18n message key.

export const API_BASE = "/api/v1";

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly messageKey: string;
  readonly fields: FieldErrors;
  readonly requestId: string | null;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, messageKey: string, fields: FieldErrors = {},
              requestId: string | null = null, details: Record<string, unknown> = {}) {
    super(code);
    this.status = status;
    this.code = code;
    this.messageKey = messageKey;
    this.fields = fields;
    this.requestId = requestId;
    this.details = details;
  }
}

/** Called on 401 SESSION_EXPIRED / AUTH_REQUIRED (router sends user to /login). */
let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(fn: () => void): void {
  onSessionExpired = fn;
}

type Method = "PUT" | "GET" | "POST" | "PATCH" | "DELETE";

type Options = {
  method?: Method;
  body?: unknown;
  /** Don't redirect to /login on 401 (used by the initial "who am I?" probe). */
  quiet401?: boolean;
};

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const { method = "GET", body, quiet401 = false } = options;
  const headers: Record<string, string> = { "X-BB-Client": "web", Accept: "application/json" };
  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res: Response;
  try {
    res = await fetch(API_BASE + path, { method, headers, body: payload, credentials: "include" });
  } catch {
    throw new ApiError(0, "NETWORK", "err.network");
  }

  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);

  if (!res.ok) {
    const err = (data as { error?: Record<string, unknown> } | null)?.error;
    if (!err) throw new ApiError(res.status, "INTERNAL_ERROR", "err.generic");
    const { code, message_key, fields, request_id, ...details } = err as {
      code: string; message_key: string; fields?: FieldErrors; request_id?: string | null;
    } & Record<string, unknown>;
    if (!quiet401 && res.status === 401 && (code === "SESSION_EXPIRED" || code === "AUTH_REQUIRED")) {
      onSessionExpired?.();
    }
    throw new ApiError(res.status, code, message_key, fields ?? {}, request_id ?? null, details);
  }
  return data as T;
}

export type Health = { status: "ok" | "degraded"; db: "ok" | "down"; llm: "configured" | "disabled" };

/** /health returns 503 with a normal body when the DB is down. */
export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_BASE}/health`, { credentials: "include" });
  return (await res.json()) as Health;
}
