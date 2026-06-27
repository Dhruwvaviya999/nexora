"use client";

import { useRouter } from "next/navigation";
import {
  AtSign,
  Bell,
  MessageSquare,
  SquareCheckBig,
  UserPlus,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/format";
import { useMarkNotificationRead } from "@/hooks/use-notifications";
import type { AppNotification, NotificationType } from "@/types/notification";

const ICONS: Record<NotificationType, LucideIcon> = {
  mention: AtSign,
  comment_reply: MessageSquare,
  workspace_invite: UserPlus,
  task_assigned: SquareCheckBig,
  task_updated: SquareCheckBig,
  system: Bell,
};

export function NotificationItem({
  notification,
  onNavigate,
}: {
  notification: AppNotification;
  onNavigate?: () => void;
}) {
  const router = useRouter();
  const markRead = useMarkNotificationRead();
  const Icon = ICONS[notification.type] ?? Bell;

  function handleClick() {
    if (!notification.is_read) markRead.mutate(notification.id);
    if (notification.link) router.push(notification.link);
    onNavigate?.();
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "flex w-full gap-3 rounded-md p-2 text-left transition-colors hover:bg-accent",
        !notification.is_read && "bg-accent/40"
      )}
    >
      <div className="grid size-8 shrink-0 place-items-center rounded-full bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium leading-snug">{notification.title}</p>
        {notification.message && (
          <p className="truncate text-xs text-muted-foreground">
            {notification.message}
          </p>
        )}
        <p className="mt-0.5 text-xs text-muted-foreground">
          {formatRelativeTime(notification.created_at)}
        </p>
      </div>
      {!notification.is_read && (
        <span className="mt-1 size-2 shrink-0 rounded-full bg-primary" />
      )}
    </button>
  );
}
