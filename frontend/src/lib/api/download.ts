import { API_BASE_URL } from "@/lib/constants";
import { ensureAccessToken } from "@/lib/api/client";
import { tokenStorage } from "@/lib/auth/token-storage";
import type { ApiError } from "@/types";

/**
 * Fetch an authenticated binary endpoint (PDF/CSV/uploaded file) and trigger a
 * browser download. The JSON apiClient can't be used here — these responses
 * are blobs, not JSON.
 *
 * Mirrors the client's auth behaviour: it obtains an access token up front
 * (minting one from the refresh cookie if memory is empty after a reload) and
 * retries once on a 401, so an expired token no longer turns a download into a
 * failure toast.
 */
export async function downloadFile(
  path: string,
  fallbackName: string,
  params?: Record<string, string | undefined>
): Promise<void> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value) search.append(key, value);
  }
  const qs = search.toString();
  const url = `${API_BASE_URL}${path}${qs ? `?${qs}` : ""}`;

  const send = (token: string | null) =>
    fetch(url, {
      credentials: "include",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

  let response = await send(await ensureAccessToken());

  // One transparent retry, matching apiClient's behaviour.
  if (response.status === 401) {
    tokenStorage.clear();
    const refreshed = await ensureAccessToken();
    if (refreshed) response = await send(refreshed);
  }

  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message: response.status === 404 ? "File not found" : "Download failed",
    };
    throw error;
  }

  // Prefer the server-provided filename when present.
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/.exec(disposition);
  const filename = match?.[1] ?? fallbackName;

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
