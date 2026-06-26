import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { Task } from "@/types/task";

export type TaskListParams = {
  workspace?: string;
  project?: string;
  status?: string;
  priority?: string;
  assignee?: string;
  search?: string;
  ordering?: string;
  page?: number;
};

/** Payload accepted by create/update (relations sent as ids). */
export interface TaskPayload {
  project?: string;
  title?: string;
  description?: string;
  status?: string;
  priority?: string;
  assignee_id?: string | null;
  due_date?: string | null;
  start_date?: string | null;
  estimated_hours?: string | null;
  labels?: string[];
}

/** Normalise form values (empty strings) into the API payload (nulls). */
export function toTaskPayload(v: {
  project: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  assignee_id?: string;
  due_date?: string;
  start_date?: string;
  estimated_hours?: string;
  labels?: string[];
}): TaskPayload {
  return {
    project: v.project,
    title: v.title,
    description: v.description ?? "",
    status: v.status,
    priority: v.priority,
    assignee_id: v.assignee_id || null,
    due_date: v.due_date || null,
    start_date: v.start_date || null,
    estimated_hours: v.estimated_hours || null,
    labels: v.labels ?? [],
  };
}

export const tasksApi = {
  list: (params: TaskListParams) =>
    apiClient.get<Paginated<Task>>(API_ROUTES.tasks.list, { params }),
  get: (id: string) => apiClient.get<Task>(API_ROUTES.tasks.detail(id)),
  create: (data: TaskPayload) =>
    apiClient.post<Task>(API_ROUTES.tasks.list, data),
  update: (id: string, data: TaskPayload) =>
    apiClient.patch<Task>(API_ROUTES.tasks.detail(id), data),
  remove: (id: string) => apiClient.delete<void>(API_ROUTES.tasks.detail(id)),
};
