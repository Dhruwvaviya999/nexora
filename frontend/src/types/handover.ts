import type { AuthUser } from "@/types/auth";

export type HandoverStatus = "pending" | "approved" | "rejected";

export interface Handover {
  id: string;
  workspace: string;
  task: string;
  task_title: string;
  project_id: string;
  from_user: AuthUser | null;
  to_user: AuthUser | null;
  summary: string;
  pending_items: string;
  resources: string;
  status: HandoverStatus;
  reviewer: AuthUser | null;
  review_comment: string;
  reviewed_at: string | null;
  created_by: AuthUser | null;
  updated_by: AuthUser | null;
  created_at: string;
  updated_at: string;
}
