import { API_BASE_URL, API_ROUTES } from "@/lib/constants";
import { tokenStorage } from "@/lib/auth/token-storage";
import type { ApiError } from "@/types";
import type { RefreshResponse } from "@/types/auth";

/**
 * Typed `fetch` wrapper with automatic JWT handling.
 *
 * - Injects `Authorization: Bearer <access>` when a token is present. The
 *   access token is held in memory only; see lib/auth/token-storage.ts.
 * - On a 401, transparently attempts a single token refresh and retries the
 *   request once. Concurrent 401s share one in-flight refresh.
 * - Normalises non-2xx responses into a consistent `ApiError`.
 *
 * Every request is sent with `credentials: "include"` so the browser attaches
 * the httpOnly refresh cookie to the auth endpoints that need it. The cookie is
 * path-scoped server-side (`/api/v1/auth/`), so it is not actually transmitted
 * on ordinary API calls.
 */

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Query string params appended to the URL (null/undefined/"" are skipped). */
  params?: Record<string, string | number | boolean | null | undefined>;
  /** Skip auth header + refresh (used by login/register/refresh themselves). */
  skipAuth?: boolean;
  /** Internal: prevents infinite refresh loops. */
  _isRetry?: boolean;
};

function buildQuery(
  params?: Record<string, string | number | boolean | null | undefined>
): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.append(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

let refreshPromise: Promise<string | null> | null = null;

/**
 * Exchange the httpOnly refresh cookie for a new access token.
 *
 * No body is sent: the token is in a cookie this code cannot read, which is
 * the point. `credentials: "include"` is what makes the browser attach it.
 * Rotation happens server-side and the replacement cookie comes back on the
 * response, so the new refresh token never passes through JavaScript either.
 */
async function refreshAccessToken(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE_URL}${API_ROUTES.auth.refresh}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: "{}",
    });
    if (!res.ok) {
      tokenStorage.clear();
      return null;
    }
    const data: RefreshResponse = await res.json();
    tokenStorage.setAccess(data.access);
    return data.access;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

/**
 * Obtain an access token when none is held in memory.
 *
 * A page reload wipes the in-memory token but leaves the refresh cookie, so
 * the very first request after a reload would otherwise fire without an
 * Authorization header, take a 401, and only then refresh. Doing it up front
 * saves that wasted round trip — and it shares the same single-flight promise,
 * so a burst of first requests still triggers exactly one refresh.
 */
export function ensureAccessToken(): Promise<string | null> {
  const existing = tokenStorage.getAccess();
  if (existing) return Promise.resolve(existing);
  return getRefreshedToken();
}

/** Ensures only one refresh runs at a time across concurrent requests. */
function getRefreshedToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, skipAuth, params, _isRetry, ...rest } = options;

  const authHeaders: Record<string, string> = {};
  if (!skipAuth) {
    const access = tokenStorage.getAccess();
    if (access) authHeaders.Authorization = `Bearer ${access}`;
  }

  // FormData (file uploads) must NOT be JSON-encoded; let the browser set the
  // multipart Content-Type (with boundary) itself.
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const baseHeaders: Record<string, string> = isFormData
    ? {}
    : { "Content-Type": "application/json" };

  const response = await fetch(`${API_BASE_URL}${path}${buildQuery(params)}`, {
    ...rest,
    // Lets the browser attach the httpOnly refresh cookie. It is path-scoped
    // to /api/v1/auth/ server-side, so it rides along only where it is needed.
    credentials: "include",
    headers: {
      ...baseHeaders,
      ...authHeaders,
      ...headers,
    },
    body:
      body === undefined
        ? undefined
        : isFormData
          ? (body as FormData)
          : JSON.stringify(body),
  });

  // Transparent refresh-and-retry on a single 401.
  if (response.status === 401 && !skipAuth && !_isRetry) {
    const newAccess = await getRefreshedToken();
    if (newAccess) {
      return request<T>(path, { ...options, _isRetry: true });
    }
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message:
        (data && (data.detail || data.message)) ||
        response.statusText ||
        "Request failed",
      details: data && typeof data === "object" ? data : undefined,
    };
    throw error;
  }

  return data as T;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
};
