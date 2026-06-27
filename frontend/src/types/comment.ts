import type { AuthUser } from "@/types/auth";

/** A commentable resource type (matches the backend whitelist). */
export type CommentTargetType = "project" | "task" | "document";

export interface Comment {
  id: string;
  content: string;
  author: AuthUser;
  parent: string | null;
  reply_count: number;
  is_edited: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

/** Payload for creating a top-level comment. */
export interface CreateCommentInput {
  target_type: CommentTargetType;
  target_id: string;
  content: string;
}
