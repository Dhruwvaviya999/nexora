import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { Project } from "@/types/project";
import type { ProjectValues } from "@/lib/validations/project";

export type ProjectListParams = {
  workspace?: string;
  status?: string;
  archived?: boolean;
  search?: string;
  ordering?: string;
  page?: number;
};

export const projectsApi = {
  list: (params: ProjectListParams) =>
    apiClient.get<Paginated<Project>>(API_ROUTES.projects.list, { params }),
  get: (id: string) => apiClient.get<Project>(API_ROUTES.projects.detail(id)),
  create: (data: ProjectValues & { workspace: string }) =>
    apiClient.post<Project>(API_ROUTES.projects.list, data),
  update: (id: string, data: Partial<ProjectValues>) =>
    apiClient.patch<Project>(API_ROUTES.projects.detail(id), data),
  remove: (id: string) =>
    apiClient.delete<void>(API_ROUTES.projects.detail(id)),
  archive: (id: string) =>
    apiClient.post<Project>(API_ROUTES.projects.archive(id)),
  restore: (id: string) =>
    apiClient.post<Project>(API_ROUTES.projects.restore(id)),
};
