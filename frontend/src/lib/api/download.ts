import { API_BASE_URL } from "@/lib/constants";
import { tokenStorage } from "@/lib/auth/token-storage";

/**
 * Fetch an authenticated binary endpoint (PDF/CSV) and trigger a browser
 * download. The JSON apiClient can't be used here — these responses are blobs.
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

  const access = tokenStorage.getAccess();
  const response = await fetch(`${API_BASE_URL}${path}${qs ? `?${qs}` : ""}`, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  });
  if (!response.ok) {
    throw { status: response.status, message: "Download failed" };
  }

  // Prefer the server-provided filename when present.
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/.exec(disposition);
  const filename = match?.[1] ?? fallbackName;

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
