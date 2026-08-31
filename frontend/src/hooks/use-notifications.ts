"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { notificationsApi } from "@/lib/api/notifications";
import { useNotificationSocket } from "@/hooks/use-notification-socket";

const KEYS = {
  list: (params?: unknown) => ["notifications", "list", params] as const,
  unread: ["notifications", "unread"] as const,
};

export function useNotifications(params?: {
  is_read?: boolean;
  type?: string;
  workspace?: string;
}) {
  return useQuery({
    queryKey: KEYS.list(params),
    queryFn: () => notificationsApi.list(params),
  });
}

/**
 * Unread badge count.
 *
 * Prefers the websocket, which invalidates this query the moment something
 * arrives. Polling is kept as the fallback and switched off while the socket
 * is connected, so a live client makes no periodic requests at all.
 */
export function useUnreadCount() {
  const { isLive } = useNotificationSocket();

  return useQuery({
    queryKey: KEYS.unread,
    queryFn: () => notificationsApi.unreadCount(),
    refetchInterval: isLive ? false : 30_000,
  });
}

function useInvalidateNotifications() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["notifications"] });
}

export function useMarkNotificationRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: invalidate,
  });
}

export function useMarkAllNotificationsRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: invalidate,
  });
}
