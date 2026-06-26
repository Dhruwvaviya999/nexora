import { API_BASE_URL } from "@/lib/constants";
import type { ApiError } from "@/types";

/**
 * Thin typed wrapper around `fetch`.
 *
 * - Prefixes every request with the versioned API base URL.
 * - Sends/receives JSON by default.
 * - Normalises non-2xx responses into a consistent `ApiError`.
 *
 * Auth headers and token refresh are intentionally NOT here yet — they slot in
 * during Phase 2 via the `getAuthHeader` hook below.
 */

type RequestOptions = Omit<RequestInit, "body"> & {
  /** JSON-serialisable body; stringified automatically. */
  body?: unknown;
};

/** Placeholder for Phase 2 — returns auth headers once JWT lands. */
function getAuthHeader(): Record<string, string> {
  return {};
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // 204 No Content and other empty bodies.
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
