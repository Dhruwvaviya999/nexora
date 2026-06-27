"use client";

import * as React from "react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { CommentContent } from "@/components/comments/comment-content";
import { CommentForm } from "@/components/comments/comment-form";
import { useAuth } from "@/providers/auth-provider";
import {
  useDeleteComment,
  useReplyComment,
  useUpdateComment,
} from "@/hooks/use-comments";
import { formatRelativeTime } from "@/lib/format";
import { initialsOf } from "@/lib/initials";
import type { Comment, CommentTargetType } from "@/types/comment";
import type { WorkspaceMember } from "@/types/workspace";

interface CommentItemProps {
  comment: Comment;
  replies?: Comment[];
  members: WorkspaceMember[];
  targetType: CommentTargetType;
  targetId: string;
  isReply?: boolean;
}

export function CommentItem({
  comment,
  replies = [],
  members,
  targetType,
  targetId,
  isReply = false,
}: CommentItemProps) {
  const { user } = useAuth();
  const reply = useReplyComment(targetType, targetId);
  const update = useUpdateComment(targetType, targetId);
  const remove = useDeleteComment(targetType, targetId);

  const [replying, setReplying] = React.useState(false);
  const [editing, setEditing] = React.useState(false);

  const author = comment.author;
  const isAuthor = user?.id === author.id;

  return (
    <div className="flex gap-3">
      <Avatar className="size-8 shrink-0">
        <AvatarImage src={author.avatar || undefined} />
        <AvatarFallback className="text-xs">
          {initialsOf(author.name, author.email)}
        </AvatarFallback>
      </Avatar>

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {author.name || author.email}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(comment.created_at)}
          </span>
          {comment.is_edited && !comment.is_deleted && (
            <span className="text-xs text-muted-foreground">(edited)</span>
          )}
        </div>

        {editing ? (
          <CommentForm
            members={members}
            initialValue={comment.content}
            submitLabel="Save"
            autoFocus
            onCancel={() => setEditing(false)}
            onSubmit={async (content) => {
              await update.mutateAsync({ id: comment.id, content });
              setEditing(false);
              toast.success("Comment updated");
            }}
          />
        ) : comment.is_deleted ? (
          <p className="text-sm italic text-muted-foreground">[deleted]</p>
        ) : (
          <CommentContent content={comment.content} />
        )}

        {!comment.is_deleted && !editing && (
          <div className="flex items-center gap-1">
            {!isReply && (
              <Button
                variant="ghost"
                size="xs"
                onClick={() => setReplying((v) => !v)}
              >
                Reply
              </Button>
            )}
            {isAuthor && (
              <Button variant="ghost" size="xs" onClick={() => setEditing(true)}>
                Edit
              </Button>
            )}
            {isAuthor && (
              <ConfirmDialog
                title="Delete comment?"
                description="This comment will be removed for everyone."
                confirmLabel="Delete"
                onConfirm={async () => {
                  await remove.mutateAsync(comment.id);
                  toast.success("Comment deleted");
                }}
                trigger={
                  <Button variant="ghost" size="xs">
                    Delete
                  </Button>
                }
              />
            )}
          </div>
        )}

        {replying && (
          <div className="pt-1">
            <CommentForm
              members={members}
              submitLabel="Reply"
              placeholder="Write a reply…"
              autoFocus
              onCancel={() => setReplying(false)}
              onSubmit={async (content) => {
                await reply.mutateAsync({ id: comment.id, content });
                setReplying(false);
              }}
            />
          </div>
        )}

        {replies.length > 0 && (
          <div className="mt-3 space-y-4 border-l pl-3">
            {replies.map((r) => (
              <CommentItem
                key={r.id}
                comment={r}
                members={members}
                targetType={targetType}
                targetId={targetId}
                isReply
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
