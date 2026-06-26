import type { Project } from "@/types/project";
import type { Task } from "@/types/task";
import type { DocumentItem } from "@/types/document";

export interface DashboardStats {
  total_projects: number;
  active_projects: number;
  archived_projects: number;
  total_tasks: number;
  pending_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  total_documents: number;
}

export interface Dashboard {
  stats: DashboardStats;
  recent_projects: Project[];
  recent_tasks: Task[];
  recent_documents: DocumentItem[];
}
