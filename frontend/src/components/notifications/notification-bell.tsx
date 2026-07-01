"use client";

import * as React from "react";
import Link from "next/link";
import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { NotificationList } from "@/components/notifications/notification-list";
import {
  useMarkAllNotificationsRead,
  useNotifications,
  useUnreadCount,
} from "@/hooks/use-notifications";
import { ROUTES } from "@/lib/constants";

export function NotificationBell() {
  const [open, setOpen] = React.useState(false);
  const { data: unread } = useUnreadCount();
  const { data, isLoading } = useNotifications();
  const markAll = useMarkAllNotificationsRead();

  const count = unread?.count ?? 0;
  const notifications = (data?.results ?? []).slice(0, 8);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
        >
          <Bell className="size-5" />
          {count > 0 && (
            <span className="absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-primary px-1 text-[10px] font-medium text-primary-foreground">
              {count > 9 ? "9+" : count}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between p-3">
          <span className="text-sm font-medium">Notifications</span>
          {count > 0 && (
            <Button variant="ghost" size="xs" onClick={() => markAll.mutate()}>
              Mark all read
            </Button>
          )}
        </div>
        <Separator />
        <ScrollArea className="h-80">
          <div className="p-2">
            <NotificationList
              notifications={notifications}
              isLoading={isLoading}
              onNavigate={() => setOpen(false)}
            />
          </div>
        </ScrollArea>
        <Separator />
        <div className="p-2">
          <Button
            variant="ghost"
            size="sm"
            className="w-full"
            asChild
            onClick={() => setOpen(false)}
          >
            <Link href={ROUTES.notifications}>View all</Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
