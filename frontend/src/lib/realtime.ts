/** Derives the websocket endpoint from the configured API URL. */

import { env } from "@/config/env";

/**
 * `/ws/notifications/` on the API host.
 *
 * NEXT_PUBLIC_API_URL points at the REST prefix (…/api/v1); the socket is
 * mounted at the root, so the path is replaced rather than appended. http
 * becomes ws, https becomes wss, which keeps the socket as secure as the page.
 */
export function notificationSocketUrl(token: string): string {
  const api = new URL(env.NEXT_PUBLIC_API_URL);
  api.protocol = api.protocol === "https:" ? "wss:" : "ws:";
  api.pathname = "/ws/notifications/";
  api.search = `?token=${encodeURIComponent(token)}`;
  return api.toString();
}
