"use client";

import { Activity as ActivityIcon } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { ActivityItem } from "@/components/activities/activity-item";
import type { Activity } from "@/types/activity";

export function ActivityTimeline({
  activities,
  isLoading,
}: {
  activities: Activity[];
  isLoading?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="size-8 rounded-full" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3 w-56" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!activities.length) {
    return (
      <EmptyState
        icon={ActivityIcon}
        title="No activity yet"
        description="Actions in this workspace will show up here."
      />
    );
  }

  return (
    <div className="space-y-4">
      {activities.map((a) => (
        <ActivityItem key={a.id} activity={a} />
      ))}
    </div>
  );
}
