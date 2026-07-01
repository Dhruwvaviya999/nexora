"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { commentsApi } from "@/lib/api/comments";
import type { CommentTargetType } from "@/types/comment";

const key = (t: CommentTargetType, id: string) => ["comments", t, id] as const;

export function useComments(targetType: CommentTargetType, targetId: string) {
  return useQuery({
    queryKey: key(targetType, targetId),
    queryFn: () => commentsApi.list(targetType, targetId),
    enabled: !!targetId,
  });
}

function useInvalidate(targetType: CommentTargetType, targetId: string) {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: key(targetType, targetId) });
}

export function useCreateComment(targetType: CommentTargetType, targetId: string) {
  const invalidate = useInvalidate(targetType, targetId);
  return useMutation({
    mutationFn: (content: string) =>
      commentsApi.create({ target_type: targetType, target_id: targetId, content }),
    onSuccess: invalidate,
  });
}

export function useReplyComment(targetType: CommentTargetType, targetId: string) {
  const invalidate = useInvalidate(targetType, targetId);
  return useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      commentsApi.reply(id, content),
    onSuccess: invalidate,
  });
}

export function useUpdateComment(targetType: CommentTargetType, targetId: string) {
  const invalidate = useInvalidate(targetType, targetId);
  return useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      commentsApi.update(id, content),
    onSuccess: invalidate,
  });
}

export function useDeleteComment(targetType: CommentTargetType, targetId: string) {
  const invalidate = useInvalidate(targetType, targetId);
  return useMutation({
    mutationFn: (id: string) => commentsApi.remove(id),
    onSuccess: invalidate,
  });
}
