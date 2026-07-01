import type { AuthUser } from "@/types/auth";

export interface Activity {
  id: string;
  actor: AuthUser | null;
  /** Dotted action key, e.g. "task.created", "project.archived". */
  action: string;
  target_type: string | null;
  object_id: string | null;
  metadata: Record<string, unknown>;
  workspace: string;
  created_at: string;
}
