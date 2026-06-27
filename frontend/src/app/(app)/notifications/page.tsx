"use client";

import * as React from "react";
import { CheckCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/shared/page-header";
import { NotificationList } from "@/components/notifications/notification-list";
import {
  useMarkAllNotificationsRead,
  useNotifications,
  useUnreadCount,
} from "@/hooks/use-notifications";

export default function NotificationsPage() {
  const [tab, setTab] = React.useState<"all" | "unread">("all");
  const { data, isLoading } = useNotifications(
    tab === "unread" ? { is_read: false } : undefined
  );
  const { data: unread } = useUnreadCount();
  const markAll = useMarkAllNotificationsRead();

  const notifications = data?.results ?? [];

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <PageHeader
        title="Notifications"
        description="Mentions, replies and workspace updates."
      >
        <Button
          variant="outline"
          size="sm"
          onClick={() => markAll.mutate()}
          disabled={!unread?.count}
        >
          <CheckCheck className="size-4" />
          Mark all read
        </Button>
      </PageHeader>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "all" | "unread")}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="unread">
            Unread{unread?.count ? ` (${unread.count})` : ""}
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <NotificationList notifications={notifications} isLoading={isLoading} />
    </div>
  );
}
