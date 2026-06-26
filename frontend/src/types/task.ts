import type { AuthUser } from "@/types/auth";

export type TaskStatus =
  | "todo"
  | "in_progress"
  | "review"
  | "completed"
  | "cancelled";

export type TaskPriority = "low" | "medium" | "high" | "critical";

export interface Task {
  id: string;
  workspace: string;
  project: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  assignee: AuthUser | null;
  reporter: AuthUser | null;
  due_date: string | null;
  start_date: string | null;
  estimated_hours: string | null;
  labels: string[];
  created_by: AuthUser | null;
  updated_by: AuthUser | null;
  created_at: string;
  updated_at: string;
}
