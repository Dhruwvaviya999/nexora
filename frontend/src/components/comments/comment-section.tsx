"use client";

import { MessageSquare } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { CommentForm } from "@/components/comments/comment-form";
import { CommentItem } from "@/components/comments/comment-item";
import { useComments, useCreateComment } from "@/hooks/use-comments";
import { useWorkspaceMembers } from "@/hooks/use-workspaces";
import { useWorkspaceContext } from "@/providers/workspace-provider";
import type { CommentTargetType } from "@/types/comment";

interface CommentSectionProps {
  targetType: CommentTargetType;
  targetId: string;
}

/**
 * Reusable discussion thread. Drop it into a project/task/document detail page:
 *   <CommentSection targetType="task" targetId={task.id} />
 */
export function CommentSection({ targetType, targetId }: CommentSectionProps) {
  const { activeWorkspaceId } = useWorkspaceContext();
  const { data: members } = useWorkspaceMembers(activeWorkspaceId ?? "");
  const { data, isLoading } = useComments(targetType, targetId);
  const create = useCreateComment(targetType, targetId);

  const memberList = members ?? [];
  const comments = data?.results ?? [];
  const topLevel = comments.filter((c) => !c.parent);
  const repliesOf = (parentId: string) =>
    comments.filter((c) => c.parent === parentId);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <MessageSquare className="size-4 text-muted-foreground" />
        <h3 className="text-sm font-medium">
          Comments{comments.length ? ` (${comments.length})` : ""}
        </h3>
      </div>

      <CommentForm
        members={memberList}
        onSubmit={(content) => create.mutateAsync(content)}
      />

      {isLoading ? (
        <div className="space-y-4">
          {[0, 1].map((i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="size-8 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-3 w-full" />
              </div>
            </div>
          ))}
        </div>
      ) : topLevel.length === 0 ? (
        <EmptyState
          icon={MessageSquare}
          title="No comments yet"
          description="Start the conversation — mention teammates with @."
        />
      ) : (
        <div className="space-y-5">
          {topLevel.map((c) => (
            <CommentItem
              key={c.id}
              comment={c}
              replies={repliesOf(c.id)}
              members={memberList}
              targetType={targetType}
              targetId={targetId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
