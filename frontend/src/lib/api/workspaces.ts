import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Paginated } from "@/types";
import type { Workspace, WorkspaceMember } from "@/types/workspace";
import type { WorkspaceValues } from "@/lib/validations/workspace";

/** Workspace API service. */
export const workspacesApi = {
  list: () => apiClient.get<Paginated<Workspace>>(API_ROUTES.workspaces.list),

  get: (id: string) =>
    apiClient.get<Workspace>(API_ROUTES.workspaces.detail(id)),

  create: (data: WorkspaceValues) =>
    apiClient.post<Workspace>(API_ROUTES.workspaces.list, data),

  update: (id: string, data: Partial<WorkspaceValues>) =>
    apiClient.patch<Workspace>(API_ROUTES.workspaces.detail(id), data),

  remove: (id: string) =>
    apiClient.delete<void>(API_ROUTES.workspaces.detail(id)),

  members: (id: string) =>
    apiClient.get<WorkspaceMember[]>(API_ROUTES.workspaces.members(id)),
};
