import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { AppNotification } from "@/types/notification";

type ListParams = {
  is_read?: boolean;
  type?: string;
  workspace?: string;
};

export const notificationsApi = {
  list: (params?: ListParams) =>
    apiClient.get<Paginated<AppNotification>>(API_ROUTES.notifications.list, {
      params,
    }),

  unreadCount: () =>
    apiClient.get<{ count: number }>(API_ROUTES.notifications.unreadCount),

  markRead: (id: string) =>
    apiClient.patch<AppNotification>(API_ROUTES.notifications.read(id)),

  markAllRead: () =>
    apiClient.patch<{ updated: number }>(API_ROUTES.notifications.readAll),
};
