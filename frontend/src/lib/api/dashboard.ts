import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Dashboard } from "@/types/dashboard";

export const dashboardApi = {
  get: (workspace: string) =>
    apiClient.get<Dashboard>(API_ROUTES.dashboard, { params: { workspace } }),
};
