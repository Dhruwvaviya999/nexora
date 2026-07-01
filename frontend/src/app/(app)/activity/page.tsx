"use client";

import { PageHeader } from "@/components/shared/page-header";
import { NoWorkspace } from "@/components/shared/no-workspace";
import { ActivityTimeline } from "@/components/activities/activity-timeline";
import { useActivities } from "@/hooks/use-activities";
import { useWorkspaceContext } from "@/providers/workspace-provider";

export default function ActivityPage() {
  const { activeWorkspaceId, isLoading: wsLoading } = useWorkspaceContext();
  const { data, isLoading } = useActivities({
    workspace: activeWorkspaceId ?? undefined,
  });

  if (!wsLoading && !activeWorkspaceId) return <NoWorkspace />;

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <PageHeader
        title="Activity"
        description="Recent activity across your workspace."
      />
      <ActivityTimeline activities={data?.results ?? []} isLoading={isLoading} />
    </div>
  );
}
