import type { AuthUser } from "@/types/auth";

export type ProjectStatus = "planning" | "active" | "on_hold" | "completed";

export interface Project {
  id: string;
  workspace: string;
  name: string;
  slug: string;
  description: string;
  color: string;
  status: ProjectStatus;
  archived: boolean;
  owner: AuthUser | null;
  task_count: number;
  created_by: AuthUser | null;
  updated_by: AuthUser | null;
  created_at: string;
  updated_at: string;
}
