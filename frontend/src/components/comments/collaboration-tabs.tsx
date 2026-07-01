"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CommentSection } from "@/components/comments/comment-section";
import { ActivityTimeline } from "@/components/activities/activity-timeline";
import { useActivities } from "@/hooks/use-activities";
import type { CommentTargetType } from "@/types/comment";

/**
 * Comments + activity for a single project/task/document, as a tabbed panel.
 * Drop onto any detail page:
 *   <CollaborationTabs targetType="task" targetId={task.id} />
 */
export function CollaborationTabs({
  targetType,
  targetId,
}: {
  targetType: CommentTargetType;
  targetId: string;
}) {
  const { data, isLoading } = useActivities({
    target_type: targetType,
    target_id: targetId,
  });

  return (
    <Tabs defaultValue="comments" className="w-full">
      <TabsList>
        <TabsTrigger value="comments">Comments</TabsTrigger>
        <TabsTrigger value="activity">Activity</TabsTrigger>
      </TabsList>
      <TabsContent value="comments" className="pt-4">
        <CommentSection targetType={targetType} targetId={targetId} />
      </TabsContent>
      <TabsContent value="activity" className="pt-4">
        <ActivityTimeline
          activities={data?.results ?? []}
          isLoading={isLoading}
        />
      </TabsContent>
    </Tabs>
  );
}
