import { apiClient } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/constants";
import type { Analytics } from "@/types/analytics";

export const analyticsApi = {
  get: (workspace: string) =>
    apiClient.get<Analytics>(API_ROUTES.analytics, { params: { workspace } }),
};
