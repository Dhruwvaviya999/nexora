import { API_BASE_URL, API_ROUTES } from "@/lib/constants";
import { tokenStorage } from "@/lib/auth/token-storage";
import type { ApiError } from "@/types";
import type { RefreshResponse } from "@/types/auth";

/**
 * Typed `fetch` wrapper with automatic JWT handling.
 *
 * - Injects `Authorization: Bearer <access>` when a token is present.
 * - On a 401, transparently attempts a single token refresh and retries the
 *   request once. Concurrent 401s share one in-flight refresh.
 * - Normalises non-2xx responses into a consistent `ApiError`.
 */

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Skip auth header + refresh (used by login/register/refresh themselves). */
  skipAuth?: boolean;
  /** Internal: prevents infinite refresh loops. */
  _isRetry?: boolean;
};

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) return null;

  try {
    const res = await fetch(`${API_BASE_URL}${API_ROUTES.auth.refresh}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) {
      tokenStorage.clear();
      return null;
    }
    const data: RefreshResponse = await res.json();
    tokenStorage.set(data.access, data.refresh);
    return data.access;
  } catch {
    tokenStorage.clear();
    return null;
  }
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
  const { body, headers, skipAuth, _isRetry, ...rest } = options;

  const authHeaders: Record<string, string> = {};
  if (!skipAuth) {
    const access = tokenStorage.getAccess();
    if (access) authHeaders.Authorization = `Bearer ${access}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
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
