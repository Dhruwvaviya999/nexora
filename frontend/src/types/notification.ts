import type { AuthUser } from "@/types/auth";

export type NotificationType =
  | "mention"
  | "task_assigned"
  | "task_updated"
  | "comment_reply"
  | "workspace_invite"
  | "system";

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  actor: AuthUser | null;
  workspace: string | null;
  created_at: string;
}
