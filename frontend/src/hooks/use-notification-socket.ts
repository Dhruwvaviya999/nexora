"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";

import { tokenStorage } from "@/lib/auth/token-storage";
import { notificationSocketUrl } from "@/lib/realtime";

/** Reconnect backoff, in milliseconds. Caps out rather than growing forever. */
const RETRY_DELAYS = [1_000, 2_000, 5_000, 10_000, 30_000];
/** Application close code the server uses to reject an unusable token. */
const CLOSE_UNAUTHENTICATED = 4401;
/** Normal closure -- we asked to disconnect, so do not reconnect. */
const CLOSE_NORMAL = 1000;

type Status = "connecting" | "open" | "closed";

/**
 * Live notification updates.
 *
 * Returns whether the socket is currently carrying updates. When it is not --
 * no websocket support, a proxy that strips upgrades, the server running under
 * plain WSGI -- callers keep polling instead, so the feature degrades rather
 * than disappears.
 *
 * The socket only signals *that* something changed; the data still comes from
 * the REST API via an invalidation, so there is one source of truth and no
 * chance of the cache drifting from what the server would return.
 */
export function useNotificationSocket(enabled = true): { isLive: boolean } {
  const queryClient = useQueryClient();
  const [status, setStatus] = React.useState<Status>("closed");

  React.useEffect(() => {
    if (!enabled) return;
    if (typeof window === "undefined" || !("WebSocket" in window)) return;

    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;
    let disposed = false;

    const connect = () => {
      if (disposed) return;

      const token = tokenStorage.getAccess();
      if (!token) {
        // Signed out, or the access token expired between renders. The REST
        // client refreshes it on the next request; try again shortly.
        retryTimer = setTimeout(connect, RETRY_DELAYS[0]);
        return;
      }

      setStatus("connecting");
      try {
        socket = new WebSocket(notificationSocketUrl(token));
      } catch {
        setStatus("closed");
        return;
      }

      socket.onopen = () => {
        attempt = 0;
        setStatus("open");
      };

      socket.onmessage = (event) => {
        let payload: { type?: string };
        try {
          payload = JSON.parse(event.data);
        } catch {
          return;
        }
        if (payload.type === "notification" || payload.type === "unread_count") {
          // Refetch rather than trusting the pushed copy: the list is
          // paginated and filtered server-side.
          queryClient.invalidateQueries({ queryKey: ["notifications"] });
        }
      };

      socket.onclose = (event) => {
        setStatus("closed");
        if (disposed || event.code === CLOSE_NORMAL) return;

        if (event.code === CLOSE_UNAUTHENTICATED) {
          // The token was rejected. Retry at the slowest interval instead of
          // hammering the server with credentials it has already refused.
          retryTimer = setTimeout(connect, RETRY_DELAYS[RETRY_DELAYS.length - 1]);
          return;
        }

        const delay = RETRY_DELAYS[Math.min(attempt, RETRY_DELAYS.length - 1)];
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      };

      // onclose fires after onerror, so reconnection is handled in one place.
      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      disposed = true;
      clearTimeout(retryTimer);
      socket?.close(CLOSE_NORMAL, "component unmounted");
    };
  }, [enabled, queryClient]);

  return { isLive: status === "open" };
}
