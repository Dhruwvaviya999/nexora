"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { describeActivity } from "@/lib/activity";
import { formatRelativeTime } from "@/lib/format";
import { initialsOf } from "@/lib/initials";
import type { Activity } from "@/types/activity";

export function ActivityItem({ activity }: { activity: Activity }) {
  const actor = activity.actor;
  const { verb, label } = describeActivity(activity);

  return (
    <div className="flex gap-3">
      <Avatar className="size-8 shrink-0">
        <AvatarImage src={actor?.avatar || undefined} />
        <AvatarFallback className="text-xs">
          {initialsOf(actor?.name, actor?.email)}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <p className="text-sm">
          <span className="font-medium">
            {actor?.name || actor?.email || "Someone"}
          </span>{" "}
          {verb}
          {label && <span className="font-medium"> {label}</span>}
        </p>
        <p className="text-xs text-muted-foreground">
          {formatRelativeTime(activity.created_at)}
        </p>
      </div>
    </div>
  );
}
