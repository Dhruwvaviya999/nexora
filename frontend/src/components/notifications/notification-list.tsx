"use client";

import { Bell } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { NotificationItem } from "@/components/notifications/notification-item";
import type { AppNotification } from "@/types/notification";

export function NotificationList({
  notifications,
  isLoading,
  onNavigate,
}: {
  notifications: AppNotification[];
  isLoading?: boolean;
  onNavigate?: () => void;
}) {
  if (isLoading) {
    return (
      <div className="space-y-2 p-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="size-8 rounded-full" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!notifications.length) {
    return (
      <EmptyState
        icon={Bell}
        title="You're all caught up"
        description="No notifications to show."
      />
    );
  }

  return (
    <div className="space-y-1">
      {notifications.map((n) => (
        <NotificationItem key={n.id} notification={n} onNavigate={onNavigate} />
      ))}
    </div>
  );
}
